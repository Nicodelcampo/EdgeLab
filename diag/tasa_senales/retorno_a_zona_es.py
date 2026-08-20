"""Retorno a zona — HFTZonesESPureV2 sobre ES. TARGET-FREE.

QUÉ MIDE
========
Después de que termina el barrido que crea la zona, ¿el precio **vuelve** a
`[price_lower, price_upper]`? ¿Cuándo? ¿Cuántas veces? ¿Cuánto tiempo y volumen deja
adentro?

Todo eso es **geometría y microestructura**: toques de nivel, no resultados.

QUÉ NO MIDE
===========
Si el precio **rechaza o rompe** — eso es dirección. Ni MFE, ni MAE, ni P&L. Y menos
todavía con la población sesgada: el censo descriptivo midió **92 % de zonas bajistas**
por el `isDown`-first, así que cualquier estadístico direccional sobre esta población
mide el orden de dos `if`.

EL CONTROL — la lección de H-ASIA-1
===================================
Un dwell bajo no dice nada sin saber cuánto vale en un nivel cualquiera de la misma
sesión. Y un control mal emparejado es peor que ninguno: en H-ASIA-1 el espejo estaba
emparejado por distancia al centro pero **anti-emparejado** por distancia al extremo
roto, y produjo un efecto de `z = 5,2` que se disolvió al condicionar.

Acá cada zona se compara contra **dos controles construidos en su misma sesión**:

- **espejo**: misma altura, misma distancia al precio de creación, **del otro lado**.
  Empareja distancia exactamente, que es la dimensión que manda para "¿llega?".
- **placebo**: misma altura, desplazamiento aleatorio con semilla fija dentro del rango
  de la sesión. No empareja distancia: sirve para ver cuánto de lo que se mide es sólo
  "hay una banda en algún lado".

El estimando es el **contraste zona − control**, nunca el valor absoluto.

CONTEXTO (P-55)
===============
Se guarda por zona: hora dentro de la sesión, rango de la sesión, distancia relativa al
precio de creación, bucket y dirección. **No se condiciona nada acá** — se guarda para
que preguntar por contexto después no obligue a re-correr.

Sin outcomes. Holdout excluido.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (minutes_since_session_open,  # noqa: E402
                                         session_bounds_utc_ns, trade_date_ymd)

SCHEMA_VERSION = "retorno_a_zona_es_v2_exige_salir_primero"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2_ES_snapshot.sqlite"
HOLDOUT_FIRST_TRADE_DATE = 20260701
CUTOFF_MS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0] // 1_000_000
SEMILLA = 20260819

# contrato -> parquet. La ventana la empuja pyarrow, asi que ES entra sin problema.
PARQUETS = {
    "ES 03-26": "ES_03-26_ticks.parquet",
    "ES 06-26": "ES_06-26_ticks.parquet",
    "ES 09-26": "ES_09-26_ticks.parquet",
}
DIR_ES = REPO / "data" / "nt8" / "ES_parquet"


def zonas_por_sesion(snapshot):
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    filas = con.execute(
        "SELECT id, instrument, start_ts, end_ts, bucket, dir, price_upper, price_lower "
        "FROM hft_zones WHERE start_ts < ? ORDER BY start_ts", (CUTOFF_MS,)).fetchall()
    con.close()
    out = {}
    for f in filas:
        td = int(trade_date_ymd(np.array([f[2] * 1_000_000], dtype=np.int64))[0])
        out.setdefault((f[1], td), []).append(f)
    return out


def medir_banda(px_t, ts, lo_t, hi_t):
    """Primer RETORNO a la banda, exigiendo que el precio haya SALIDO antes.

    v1 medía desde el primer tick posterior al barrido, y daba `t = 0` y `llega = 100 %`
    en zona y espejo: la zona la acaba de crear un barrido que terminó ahí, así que el
    precio **ya está adentro**. Eso no es un retorno, es "todavía no se fue".

    Ahora: primero se busca la salida de la banda; el retorno es la primera reentrada
    **después** de esa salida. Todo lo demás —dwell, reentradas— se mide desde la salida,
    no desde el barrido.

    Devuelve None si nunca sale (la zona nunca se abandona) o si sale y no vuelve.
    """
    dentro = (px_t >= lo_t) & (px_t <= hi_t)
    fuera = np.flatnonzero(~dentro)
    if len(fuera) == 0:
        return dict(nunca_sale=True)
    s0 = int(fuera[0])                       # primera salida
    post = dentro[s0:]
    if not post.any():
        return dict(nunca_sale=False, vuelve=False,
                    t_hasta_salida_ms=float((ts[s0] - ts[0]) / 1e6))
    i0 = s0 + int(np.argmax(post))           # primera reentrada tras salir
    reentradas = int(np.flatnonzero(post[1:] & ~post[:-1]).size + (1 if post[0] else 0))
    dt = np.diff(ts, append=ts[-1])
    return dict(nunca_sale=False, vuelve=True,
                t_hasta_salida_ms=float((ts[s0] - ts[0]) / 1e6),
                t_hasta_retorno_ms=float((ts[i0] - ts[s0]) / 1e6),
                n_retornos=reentradas,
                dwell_ms=float(dt[s0:][post].sum() / 1e6),
                n_ticks_dentro=int(post.sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--max-sesiones", type=int, default=0, help="0 = todas")
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "retorno_a_zona_es.json"))
    a = ap.parse_args()

    print("retorno a zona  ·  %s" % SCHEMA_VERSION)
    zs = zonas_por_sesion(pathlib.Path(a.snapshot))
    claves = sorted(zs)
    if a.max_sesiones:
        claves = claves[:a.max_sesiones]
    print("  %d (contrato, sesion) con zonas" % len(claves))

    rng = np.random.default_rng(SEMILLA)
    filas, sin_parquet, sin_post = [], 0, 0

    for k, (contrato, td) in enumerate(claves):
        pq_path = DIR_ES / PARQUETS.get(contrato, "")
        if not pq_path.exists():
            sin_parquet += 1
            continue
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(pq_path, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            sin_parquet += 1
            continue
        ts, px = tk.ts_ns, tk.price_ticks
        tsz = tk.tick_size
        rango_lo, rango_hi = int(px.min()), int(px.max())

        for (zid, _inst, st, en, bucket, dr, pu, pl) in zs[(contrato, td)]:
            if pu is None or pl is None:
                continue
            hi_t, lo_t = int(round(pu / tsz)), int(round(pl / tsz))
            alto = hi_t - lo_t
            # ventana POSTERIOR al barrido: desde end_ts hasta el fin de sesion
            j = int(np.searchsorted(ts, (en or st) * 1_000_000, side="right"))
            if len(ts) - j < 100:
                sin_post += 1
                continue
            pxp, tsp = px[j:], ts[j:]
            p_creacion = int(px[max(j - 1, 0)])

            # --- controles construidos en la MISMA sesion -------------------------
            d_centro = ((hi_t + lo_t) // 2) - p_creacion          # con signo
            esp_c = p_creacion - d_centro                          # del otro lado
            esp_lo, esp_hi = esp_c - alto // 2, esp_c - alto // 2 + alto
            off = int(rng.integers(-(rango_hi - rango_lo) // 2, (rango_hi - rango_lo) // 2 + 1))
            pl_lo, pl_hi = lo_t + off, hi_t + off

            z = medir_banda(pxp, tsp, lo_t, hi_t)
            e = medir_banda(pxp, tsp, esp_lo, esp_hi)
            p = medir_banda(pxp, tsp, pl_lo, pl_hi)

            filas.append(dict(
                id=zid, contrato=contrato, trade_date=td, bucket=bucket, dir=int(dr),
                alto_ticks=alto,
                dist_al_precio_de_creacion=int(abs(d_centro)),
                # --- contexto guardado, sin condicionar (P-55) --------------------
                minuto_sesion=float(minutes_since_session_open(np.array([st * 1_000_000]))[0]),
                rango_sesion_ticks=int(rango_hi - rango_lo),
                n_ticks_post=int(len(pxp)),
                # --- medidas -------------------------------------------------------
                zona=z, espejo=e, placebo=p,
                llega_zona=bool(z and z.get("vuelve")),
                llega_espejo=bool(e and e.get("vuelve")),
                llega_placebo=bool(p and p.get("vuelve")),
                nunca_sale_zona=bool(z and z.get("nunca_sale"))))
        if (k + 1) % 20 == 0:
            print("    %d/%d sesiones  ·  %d zonas medidas" % (k + 1, len(claves), len(filas)))

    print("  %d zonas medidas  (sin parquet: %d, sin ventana posterior: %d)"
          % (len(filas), sin_parquet, sin_post))

    def agr(campo, sub):
        v = [f[campo][sub] for f in filas if f[campo] and sub in f[campo]]
        if not v:
            return {}
        v = np.array(v, dtype=np.float64)
        return dict(n=len(v), mediana=round(float(np.median(v)), 3),
                    **{("p%02d" % q): round(float(np.percentile(v, q)), 3)
                       for q in (25, 75)})

    # por SESION, que es la unidad
    por_ses = {}
    for f in filas:
        por_ses.setdefault(f["trade_date"], []).append(f)
    llega_ses = {k_: (np.mean([x["llega_zona"] for x in v]),
                      np.mean([x["llega_espejo"] for x in v]),
                      np.mean([x["llega_placebo"] for x in v]))
                 for k_, v in por_ses.items()}
    lz = np.array([v[0] for v in llega_ses.values()])
    le = np.array([v[1] for v in llega_ses.values()])
    lp = np.array([v[2] for v in llega_ses.values()])

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]

    out = dict(
        schema_version=SCHEMA_VERSION,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        advertencia_poblacion=(
            "el censo descriptivo midio 92% de zonas bajistas por el bug isDown-first. "
            "NINGUNA lectura direccional de estos numeros es valida hasta regenerar el "
            "oraculo con HFTZonesESPureV2Flat."),
        controles=dict(
            espejo="misma altura y misma distancia al precio de creacion, del otro lado",
            placebo="misma altura, desplazamiento aleatorio con semilla fija en el rango de la sesion",
            estimando="contraste zona - control, nunca el valor absoluto",
            semilla=SEMILLA),
        universo=dict(n_zonas=len(filas), n_sesiones=len(por_ses),
                      sin_parquet=sin_parquet, sin_ventana_posterior=sin_post,
                      zonas_que_nunca_se_abandonan=sum(1 for f in filas if f["nunca_sale_zona"])),
        definicion_retorno=("el precio debe SALIR de la banda antes de que un reingreso "
                            "cuente como retorno. Sin eso, la zona da t=0 y 100% por "
                            "construccion: el barrido que la crea termina adentro."),
        tiempo_hasta_salida=dict(
            zona=agr("zona", "t_hasta_salida_ms"), espejo=agr("espejo", "t_hasta_salida_ms"),
            placebo=agr("placebo", "t_hasta_salida_ms")),
        llega=dict(
            zona_por_sesion=dict(mediana=round(float(np.median(lz)), 4),
                                 media=round(float(lz.mean()), 4)),
            espejo_por_sesion=dict(mediana=round(float(np.median(le)), 4),
                                   media=round(float(le.mean()), 4)),
            placebo_por_sesion=dict(mediana=round(float(np.median(lp)), 4),
                                    media=round(float(lp.mean()), 4)),
            contraste_vs_espejo=round(float(np.median(lz) - np.median(le)), 4),
            contraste_vs_placebo=round(float(np.median(lz) - np.median(lp)), 4),
            n_sesiones=len(lz)),
        cuando_llega=dict(
            zona=agr("zona", "t_hasta_retorno_ms"), espejo=agr("espejo", "t_hasta_retorno_ms"),
            placebo=agr("placebo", "t_hasta_retorno_ms")),
        dwell_ms=dict(zona=agr("zona", "dwell_ms"), espejo=agr("espejo", "dwell_ms"),
                      placebo=agr("placebo", "dwell_ms")),
        n_retornos=dict(zona=agr("zona", "n_retornos"), espejo=agr("espejo", "n_retornos"),
                        placebo=agr("placebo", "n_retornos")),
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            snapshot=str(a.snapshot),
            archivos_sucios=sorted(sucios), alcance_comprometida=["edgelab/", "diag/"],
            medicion_comprometida=bool([f for f in sucios if f.startswith(("edgelab/", "diag/"))])),
        zonas=filas)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print()
    print("  LLEGA (fraccion por sesion, mediana)")
    print("    zona    %.3f" % np.median(lz))
    print("    espejo  %.3f   contraste %+.3f" % (np.median(le), np.median(lz) - np.median(le)))
    print("    placebo %.3f   contraste %+.3f" % (np.median(lp), np.median(lz) - np.median(lp)))
    for nom, campo in (("t hasta retorno (ms)", "cuando_llega"), ("dwell (ms)", "dwell_ms"),
                       ("n retornos", "n_retornos")):
        z_, e_, p_ = out[campo]["zona"], out[campo]["espejo"], out[campo]["placebo"]
        if z_:
            print("  %-22s zona %10.1f   espejo %10.1f   placebo %10.1f"
                  % (nom, z_["mediana"], e_.get("mediana", -1), p_.get("mediana", -1)))
    print("  escrito %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
