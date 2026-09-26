"""H-ES-VOL-1 - el volumen por tiempo DENTRO de la zona, contra cuanto se aleja despues.

Protocolo pre-registrado: docs/research/H-ES-VOL-1_PROTOCOLO.md (escrito ANTES de medir).

CRUZA EL STOP. El outcome es una excursion posterior, no geometria. `outcomes_accessed`
va en True en el JSON.

DISENO
======
Por zona y por cada R de la grilla declarada:

  predictor   ventana [creacion, separacion) - solo los ticks DENTRO de [lower, upper]:
              tasa = volumen / tiempo (contratos por segundo)
  corte       el primer tick a R ticks del borde. Ni un tick se cuenta en las dos fases.
  outcome     excursion maxima desde el borde, en ticks, de ahi al fin de sesion.

EL CONFUNDIDOR, ESCRITO ANTES
=============================
Una sesion volatil tiene A LA VEZ mas volumen por segundo y excursiones mas grandes.
Correlacionar todas las zonas de todas las sesiones juntas mediria eso y nada mas.

Por eso la inferencia primaria es Spearman DENTRO de cada sesion, y la mediana de esos
rho entre sesiones. El agregado se publica al lado, para mostrar la diferencia.

Y todo se repite en la banda espejo (misma altura, misma distancia al precio de creacion,
del otro lado). Si el espejo da lo mismo, no es de la zona.

El canal direccional se guarda y NO se lee: la poblacion tiene 92% de zonas bajistas por
el bug isDown-first.
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

SCHEMA_VERSION = "h_es_vol_1_tasa_dentro_vs_excursion_v2_horizonte_fijo"
PROTOCOLO = "docs/research/H-ES-VOL-1_PROTOCOLO.md"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2_ES_snapshot.sqlite"
HOLDOUT_FIRST_TRADE_DATE = 20260701
CUTOFF_MS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0] // 1_000_000

R_SEPARACION = (2, 5, 10)      # grilla declarada en el protocolo, seccion 2
MIN_TICKS_DENTRO = 5           # sin ticks adentro no hay tasa que medir
MIN_ZONAS_POR_SESION = 8       # un rho intra-sesion con menos zonas no se interpreta

# HORIZONTE FIJO. v1 media la excursion "hasta el fin de sesion" y eso la ataba al
# reloj: rho(ticks que quedan, excursion) = +0,89 y rho(minuto de creacion, excursion)
# = -0,90. Como la tasa sube hacia el cierre (rho +0,41), el -0,35 que v1 reporto era
# ese camino y no un mecanismo de mercado. Misma familia que H-ASIA-1.
# Con horizonte fijo la zona entra solo si le quedan H_MS completos.
H_MS = 600_000                 # 10 minutos

PARQUETS = {"ES 03-26": "ES_03-26_ticks.parquet",
            "ES 06-26": "ES_06-26_ticks.parquet",
            "ES 09-26": "ES_09-26_ticks.parquet"}
DIR_ES = REPO / "data" / "nt8" / "ES_parquet"


def rangos(x):
    """Rangos con promedio en los empates. exc_abs es entero: los empates importan."""
    n = len(x)
    o = np.argsort(x, kind="mergesort")
    r = np.empty(n, dtype=np.float64)
    r[o] = np.arange(1, n + 1, dtype=np.float64)
    xs = x[o]
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[j + 1] == xs[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    return r


def spearman(x, y):
    if len(x) < 3:
        return None
    a, b = rangos(np.asarray(x, float)), rangos(np.asarray(y, float))
    sa, sb = a.std(), b.std()
    if sa == 0 or sb == 0:
        return None
    return float(np.mean((a - a.mean()) * (b - b.mean())) / (sa * sb))


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


def medir(px_t, ts, vol, dt, lo_t, hi_t, r_sep):
    """Predictor en [0, s0), outcome en [s0, fin). Sin solape."""
    dentro = (px_t >= lo_t) & (px_t <= hi_t)
    d = np.where(px_t > hi_t, px_t - hi_t, np.where(px_t < lo_t, lo_t - px_t, 0))
    lejos = d >= r_sep
    if not lejos.any():
        return None                       # nunca se separa: la zona no entra en esta R
    s0 = int(np.argmax(lejos))

    pre = dentro[:s0]
    if pre.sum() < MIN_TICKS_DENTRO:
        return None                       # sin permanencia adentro no hay tasa
    t_ms = float(dt[:s0][pre].sum() / 1e6)
    if t_ms <= 0:
        return None
    v = float(vol[:s0][pre].sum())

    # outcome en horizonte FIJO: si no entra completo, la zona no se mide
    if ts[-1] - ts[s0] < H_MS * 1_000_000:
        return None
    e1 = int(np.searchsorted(ts, ts[s0] + H_MS * 1_000_000, side="right"))
    post_d = d[s0:e1]
    up = int(px_t[s0:e1].max() - hi_t)
    dn = int(lo_t - px_t[s0:e1].min())
    return dict(
        tasa_vol_por_seg=round(v / (t_ms / 1000.0), 4),
        vol_dentro=v, t_dentro_ms=round(t_ms, 1), n_ticks_dentro=int(pre.sum()),
        t_hasta_separacion_ms=round(float((ts[s0] - ts[0]) / 1e6), 1),
        exc_abs_ticks=int(post_d.max()),
        exc_signed_ticks=int(up if up >= dn else -dn),   # se guarda, NO se lee
        n_ticks_post=int(len(post_d)),
        horizonte_ms=H_MS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "h_es_vol_1.json"))
    a = ap.parse_args()

    print("H-ES-VOL-1  -  %s" % SCHEMA_VERSION)
    print("  protocolo: %s" % PROTOCOLO)
    zs = zonas_por_sesion(pathlib.Path(a.snapshot))
    claves = sorted(zs)
    if a.max_sesiones:
        claves = claves[:a.max_sesiones]
    print("  %d (contrato, sesion) con zonas" % len(claves))

    filas, sin_pq = [], 0
    for k, (contrato, td) in enumerate(claves):
        pq = DIR_ES / PARQUETS.get(contrato, "")
        if not pq.exists():
            sin_pq += 1
            continue
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(pq, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            sin_pq += 1
            continue
        ts, px, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        dt = np.diff(ts, append=ts[-1])
        rlo, rhi = int(px.min()), int(px.max())

        for (zid, _i, st, en, bucket, dr, pu, pl) in zs[(contrato, td)]:
            if pu is None or pl is None:
                continue
            hi_t, lo_t = int(round(pu / tsz)), int(round(pl / tsz))
            alto = hi_t - lo_t
            j = int(np.searchsorted(ts, (en or st) * 1_000_000, side="right"))
            if len(ts) - j < 100:
                continue
            pxp, tsp, vp, dtp = px[j:], ts[j:], vol[j:], dt[j:]
            p_cre = int(px[max(j - 1, 0)])
            d_c = ((hi_t + lo_t) // 2) - p_cre
            e_c = p_cre - d_c
            e_lo = e_c - alto // 2
            e_hi = e_lo + alto

            fila = dict(id=zid, contrato=contrato, trade_date=td, bucket=bucket,
                        dir=int(dr), alto_ticks=alto,
                        dist_al_precio_de_creacion=int(abs(d_c)),
                        rango_sesion_ticks=int(rhi - rlo),
                        minuto_sesion=float(minutes_since_session_open(
                            np.array([st * 1_000_000]))[0]))
            for r in R_SEPARACION:
                fila["z%d" % r] = medir(pxp, tsp, vp, dtp, lo_t, hi_t, r)
                fila["e%d" % r] = medir(pxp, tsp, vp, dtp, e_lo, e_hi, r)
            filas.append(fila)
        if (k + 1) % 10 == 0:
            print("    %d/%d sesiones  -  %d zonas" % (k + 1, len(claves), len(filas)))

    print("  %d zonas  (sin parquet: %d)" % (len(filas), sin_pq))

    por_ses = {}
    for f in filas:
        por_ses.setdefault(f["trade_date"], []).append(f)

    def bloque(pref):
        rhos, nses = [], 0
        tx, ty = [], []
        terc = {1: [], 2: [], 3: []}
        for _td, fs in por_ses.items():
            v = [f[pref] for f in fs if f.get(pref)]
            if len(v) < MIN_ZONAS_POR_SESION:
                continue
            x = np.array([q["tasa_vol_por_seg"] for q in v])
            y = np.array([float(q["exc_abs_ticks"]) for q in v])
            rho = spearman(x, y)
            if rho is None:
                continue
            nses += 1
            rhos.append(rho)
            tx.extend(x.tolist())
            ty.extend(y.tolist())
            # terciles DENTRO de la sesion: el ranking neutraliza el nivel de sesion
            q = rangos(x) / len(x)
            for qi, yi in zip(q, y):
                terc[1 if qi <= 1 / 3 else (2 if qi <= 2 / 3 else 3)].append(float(yi))
        if not rhos:
            return {}
        return dict(
            n_sesiones=nses, n_zonas=len(tx),
            rho_intra_sesion=dict(
                mediana=round(float(np.median(rhos)), 4),
                p25=round(float(np.percentile(rhos, 25)), 4),
                p75=round(float(np.percentile(rhos, 75)), 4),
                frac_sesiones_positivas=round(float(np.mean(np.array(rhos) > 0)), 4)),
            rho_agregado_CONFUNDIDO=round(spearman(np.array(tx), np.array(ty)) or 0, 4),
            exc_abs_mediana_por_tercil_de_tasa={
                "T%d" % t: (round(float(np.median(terc[t])), 2) if terc[t] else None)
                for t in (1, 2, 3)},
            tasa_vol_por_seg=dict(
                p25=round(float(np.percentile(tx, 25)), 3),
                mediana=round(float(np.median(tx)), 3),
                p75=round(float(np.percentile(tx, 75)), 3)))

    por_R = {}
    for r in R_SEPARACION:
        z, e = bloque("z%d" % r), bloque("e%d" % r)
        c = None
        if z and e:
            c = round(z["rho_intra_sesion"]["mediana"]
                      - e["rho_intra_sesion"]["mediana"], 4)
        por_R[str(r)] = dict(zona=z, espejo=e, contraste_rho_zona_menos_espejo=c)

    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()]
    out = dict(
        schema_version=SCHEMA_VERSION, protocolo=PROTOCOLO,
        outcomes_accessed=True,          # SI: la excursion posterior es un outcome
        pnl_accessed=False, holdout_included=False,
        estimando=("Spearman(tasa de volumen DENTRO de la zona antes de separarse, "
                   "excursion maxima despues) medido DENTRO de cada sesion; "
                   "el estimando es el contraste zona - espejo, no el valor absoluto"),
        confundidor_declarado=("volatilidad de sesion: eleva a la vez la tasa y la "
                               "excursion. Por eso rho_agregado_CONFUNDIDO se publica "
                               "para contraste y NO se interpreta"),
        advertencia_poblacion=("92% de zonas bajistas por el bug isDown-first: "
                               "exc_signed_ticks se guarda y NO se lee"),
        piloto=True,
        parametros=dict(grilla_separacion=list(R_SEPARACION),
                        min_ticks_dentro=MIN_TICKS_DENTRO,
                        min_zonas_por_sesion=MIN_ZONAS_POR_SESION,
                        horizonte_outcome_ms=H_MS),
        universo=dict(n_zonas=len(filas), n_sesiones=len(por_ses), sin_parquet=sin_pq),
        por_separacion=por_R,
        procedencia=dict(
            head_commit=subprocess.check_output(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            snapshot=str(a.snapshot), archivos_sucios=sorted(x for x in sucios if x),
            medicion_comprometida=bool([x for x in sucios
                                        if x.startswith(("edgelab/", "diag/"))])),
        zonas=filas)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")

    print()
    print("   R   n_ses  n_zonas   rho intra-sesion        %ses   rho agreg.   "
          "exc_abs por tercil")
    print("                        zona    espejo  contr.   >0    (CONFUND.)   "
          "  T1     T2     T3")
    for r in R_SEPARACION:
        b = por_R[str(r)]
        z, e = b["zona"], b["espejo"]
        if not z:
            print("  %2d   sin datos" % r)
            continue
        t = z["exc_abs_mediana_por_tercil_de_tasa"]
        print("  %2d  %5d  %7d  %+.3f  %+.3f  %+.3f  %.2f    %+.3f      "
              "%6.1f %6.1f %6.1f"
              % (r, z["n_sesiones"], z["n_zonas"], z["rho_intra_sesion"]["mediana"],
                 e["rho_intra_sesion"]["mediana"] if e else float("nan"),
                 b["contraste_rho_zona_menos_espejo"] or 0,
                 z["rho_intra_sesion"]["frac_sesiones_positivas"],
                 z["rho_agregado_CONFUNDIDO"],
                 t["T1"] if t["T1"] is not None else -1,
                 t["T2"] if t["T2"] is not None else -1,
                 t["T3"] if t["T3"] is not None else -1))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
