"""H-ES-CRUCE-1 - cuanto cuesta ATRAVESAR la zona, contra una banda igual al lado.

LA PREGUNTA
===========
Las dos mediciones anteriores sobre esta familia murieron porque preguntaban si el precio
VUELVE a la zona. Vuelve casi siempre (99,7%) -- y ademas aquel control estaba roto
(ver confundidor 3). Un evento que pasa siempre no es un evento.

Esta pregunta es otra: cuando el precio la cruza, cuanto le cuesta. Distingue "la zona
freno" de "la zona no existio", que es lo mas cerca que se puede estar de la intuicion
original sin mirar resultados.

DEFINICION, CONGELADA ANTES DE MEDIR
====================================
Un cruce es un PRIMER PASAJE de borde a borde:

  1. el precio sale de la banda (queda estrictamente afuera de [lower, upper])
  2. vuelve a tocar el borde mas cercano  -> ahi arranca el cronometro
  3. alcanza el borde OPUESTO             -> ahi termina

Entre 2 y 3 se cuentan ticks, milisegundos y volumen. El costo se publica crudo y
normalizado por el ancho de la banda, porque una banda mas ancha cuesta mas cruzar por
aritmetica y no por el mercado.

TARGET-FREE. No hay retorno, ni P&L, ni MFE/MAE. Es microestructura del camino.

LOS CONFUNDIDORES, ESCRITOS ANTES
=================================
1. ANCHO. Trivialmente, mas ancho = mas caro. El control se empareja por ancho EXACTO,
   asi que el contraste lo controla. Igual se publica normalizado.
2. NIVEL DE ACTIVIDAD DE LA SESION. Una sesion densa da mas ticks por unidad de precio en
   todos lados. Por eso el estimando primario es el contraste DENTRO de cada sesion.
3. EL CONTROL NO PUEDE SER UN ESPEJO GEOMETRICO. v1 usaba "misma altura, misma distancia
   al precio de creacion, del otro lado" y quedo degenerado: la zona ES el rango del
   propio barrido y el barrido termina adentro, asi que la distancia al precio de
   creacion tiene mediana 1 tick y 39% de las zonas la tienen en CERO. Con distancia
   cero el espejo cae exactamente encima de la zona: 630 de 1.601 pares daban valores
   identicos y el ratio daba 1,000 por construccion.
   El control de v2 es el de F2.9 (K0 vs N0): una racha que fallo EXACTAMENTE UNO de los
   cuatro filtros de calidad. Misma geometria, mismo instante, misma sesion, el precio
   estuvo igual de presente -- pero no es zona. Se empareja por ancho exacto y cercania
   temporal.
4. ZONAS DE ALTURA 0. El oraculo tiene zonas con height_ticks = 0: no se pueden cruzar.
   Se excluyen y se cuenta cuantas fueron.

COMO SE REFUTARIA
=================
- El contraste zona - control cruza cero dentro de sesion -> la zona no frena.
- El efecto aparece solo en el canal de ticks y no en volumen ni en tiempo -> es conteo,
  no absorcion.
- El efecto escala con el ancho -> es aritmetica del ancho, no la zona.

POBLACION: oraculo Flat (HFTZonesESPureV2Flat), ES 03-26, 62 sesiones pre-firewall.
Es la poblacion CORREGIDA: 51,8% bajista / 48,2% alcista, contra 8,1% alcista del
original con el bug isDown-first.
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

from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import run_con_casi  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (minutes_since_session_open,  # noqa: E402
                                         session_bounds_utc_ns, trade_date_ymd)

SCHEMA_VERSION = "h_es_cruce_1_primer_pasaje_v3_pareado_y_ventana"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
HOLDOUT_FIRST_TRADE_DATE = 20260701
CUTOFF_MS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0] // 1_000_000
MIN_ZONAS_POR_SESION = 8

# El control tiene que estar CERCA en el tiempo. Sin tope, el emparejamiento por ancho
# tomaba casi-zonas a p90 = 2,2 horas de distancia: mismo ancho, otro regimen.
MAX_SEPARACION_MS = 30 * 60 * 1000


def rangos(x):
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


def zonas_por_sesion(snapshot):
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    filas = con.execute(
        "SELECT id, start_ts, end_ts, bucket, dir, price_upper, price_lower "
        "FROM hft_zones WHERE instrument=? AND start_ts < ? ORDER BY start_ts",
        (CONTRATO, CUTOFF_MS)).fetchall()
    con.close()
    out = {}
    for f in filas:
        td = int(trade_date_ymd(np.array([f[1] * 1_000_000], dtype=np.int64))[0])
        out.setdefault(td, []).append(f)
    return out


def medir_cruce(px, ts, vol, dt, lo, hi):
    """Primer pasaje de borde a borde. None si nunca se completa uno."""
    ancho = hi - lo
    if ancho <= 0:
        return None                                    # altura 0: no hay que cruzar

    fuera_arriba = px > hi
    fuera_abajo = px < lo
    fuera = fuera_arriba | fuera_abajo
    if not fuera.any():
        return dict(sale=False)
    s0 = int(np.argmax(fuera))
    desde_arriba = bool(fuera_arriba[s0])

    # 2. vuelve a tocar el borde mas cercano: ahi arranca el cronometro
    if desde_arriba:
        toca = px[s0:] <= hi
    else:
        toca = px[s0:] >= lo
    if not toca.any():
        return dict(sale=True, entra=False)
    a = s0 + int(np.argmax(toca))

    # 3. alcanza el borde opuesto
    if desde_arriba:
        llega = px[a:] <= lo
    else:
        llega = px[a:] >= hi
    if not llega.any():
        return dict(sale=True, entra=True, cruza=False,
                    ticks_sin_cruzar=int(len(px) - a))
    b = a + int(np.argmax(llega))

    n_ticks = int(b - a + 1)
    ms = float((ts[b] - ts[a]) / 1e6)
    v = float(vol[a:b + 1].sum())
    return dict(
        sale=True, entra=True, cruza=True, desde_arriba=desde_arriba,
        ancho_ticks=int(ancho),
        ticks=n_ticks, ms=round(ms, 1), volumen=v,
        ticks_por_ancho=round(n_ticks / ancho, 4),
        ms_por_ancho=round(ms / ancho, 4),
        vol_por_ancho=round(v / ancho, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(REPO / "docs" / "research" / "h_es_cruce_1.json"))
    a = ap.parse_args()

    print("H-ES-CRUCE-1  -  %s" % SCHEMA_VERSION)
    zs = zonas_por_sesion(pathlib.Path(a.snapshot))
    claves = sorted(zs)
    if a.max_sesiones:
        claves = claves[:a.max_sesiones]
    print("  %d sesiones  -  %s" % (len(claves), CONTRATO))

    filas, sin_pq, altura_cero = [], 0, 0
    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(PARQUET, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            sin_pq += 1
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        dt = np.diff(ts, append=ts[-1])

        zs_ts = {f[0]: f[1] for f in zs[td]}
        for (zid, st, en, bucket, dr, pu, pl) in zs[td]:
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            if hi - lo <= 0:
                altura_cero += 1
                continue
            j = int(np.searchsorted(ts, (en or st) * 1_000_000, side="right"))
            if len(ts) - j < 200:
                continue
            p, t, v, d = pxt[j:], ts[j:], vol[j:], dt[j:]
            alto = hi - lo
            p_cre = int(pxt[max(j - 1, 0)])
            d_c = ((hi + lo) // 2) - p_cre
            filas.append(dict(
                id=zid, trade_date=td, bucket=bucket, dir=int(dr),
                ancho_ticks=alto, dist_al_precio_de_creacion=int(abs(d_c)),
                minuto_sesion=float(minutes_since_session_open(
                    np.array([st * 1_000_000]))[0]),
                zona=medir_cruce(p, t, v, d, lo, hi)))
        # ---- control: casi-zonas de la MISMA sesion, emparejadas por ancho ----
        _z, casi = run_con_casi(ts, pxt * tsz, vol, tsz)
        pool = {}
        for c in casi:
            w = int(round((c["price_upper"] - c["price_lower"]) / tsz))
            if w > 0:
                pool.setdefault(w, []).append(c)
        usadas = set()
        for f in filas:
            if f["trade_date"] != td or "control" in f:
                continue
            cand = pool.get(f["ancho_ticks"], [])
            mejor, mejor_d = None, None
            for idx, c in enumerate(cand):
                if (f["ancho_ticks"], idx) in usadas:
                    continue
                dd = abs(c["start_ts"] - int(zs_ts.get(f["id"], 0)))
                if mejor_d is None or dd < mejor_d:
                    mejor, mejor_d, mejor_i = c, dd, idx
            if mejor is None:
                f["control"] = None
                continue
            if mejor_d is None or mejor_d > MAX_SEPARACION_MS:
                f["control"] = None
                continue
            usadas.add((f["ancho_ticks"], mejor_i))
            clo = int(round(mejor["price_lower"] / tsz))
            chi = int(round(mejor["price_upper"] / tsz))
            jc = int(np.searchsorted(ts, mejor["end_ts"] * 1_000_000, side="right"))
            if len(ts) - jc < 200:
                f["control"] = None
                continue
            f["control"] = medir_cruce(pxt[jc:], ts[jc:], vol[jc:], dt[jc:], clo, chi)
            f["control_motivo"] = mejor["motivo"]
            f["control_delta_ms"] = int(mejor["start_ts"] - zs_ts.get(f["id"], 0))
        if (k + 1) % 10 == 0:
            print("    %d/%d sesiones  -  %d zonas  (casi-zonas en la sesion: %d)"
                  % (k + 1, len(claves), len(filas), len(casi)))

    print("  %d zonas  (altura 0 excluidas: %d, sin parquet: %d)"
          % (len(filas), altura_cero, sin_pq))

    por_ses = {}
    for f in filas:
        por_ses.setdefault(f["trade_date"], []).append(f)

    def contraste(campo):
        """Contraste PAREADO. Cada zona contra SU control emparejado.

        v2 publicaba `mediana(z) - mediana(e)` por sesion, que es una diferencia de dos
        distribuciones y NO el contraste pareado. Sobre 1.457 pares daba +113 ticks
        mientras la diferencia zona-por-zona tenia mediana +0,0 y la zona ganaba el
        49,6% de las veces: la cola derecha de las zonas corria la mediana de medianas.
        El estimando correcto es la diferencia dentro del par.
        """
        med_dif, nz, ne, gana, nses = [], [], [], [], 0
        todas_dif = []
        for fs in por_ses.values():
            par = [(f["zona"], f["control"]) for f in fs
                   if f["zona"] and f["control"]
                   and f["zona"].get("cruza") and f["control"].get("cruza")]
            if len(par) < MIN_ZONAS_POR_SESION:
                continue
            z = np.array([x[0][campo] for x in par], dtype=np.float64)
            e = np.array([x[1][campo] for x in par], dtype=np.float64)
            nses += 1
            nz.append(float(np.median(z)))
            ne.append(float(np.median(e)))
            med_dif.append(float(np.median(z - e)))        # PAREADO
            gana.append(float(np.mean(z > e)))
            todas_dif.extend((z - e).tolist())
        if not med_dif:
            return {}
        t = np.array(todas_dif)
        return dict(n_sesiones=nses, n_pares=len(t),
                    zona_mediana=round(float(np.median(nz)), 3),
                    control_mediana=round(float(np.median(ne)), 3),
                    delta_pareada_mediana=round(float(np.median(med_dif)), 3),
                    delta_pareada_p25=round(float(np.percentile(med_dif, 25)), 3),
                    delta_pareada_p75=round(float(np.percentile(med_dif, 75)), 3),
                    frac_zonas_mas_caras=round(float(np.mean(gana)), 4),
                    dispersion_pares=dict(
                        p05=round(float(np.percentile(t, 5)), 1),
                        p25=round(float(np.percentile(t, 25)), 1),
                        p50=round(float(np.median(t)), 1),
                        p75=round(float(np.percentile(t, 75)), 1),
                        p95=round(float(np.percentile(t, 95)), 1)))

    def tasas(campo):
        z = sum(1 for f in filas if f[campo] and f[campo].get("cruza"))
        e = sum(1 for f in filas if f[campo] and f[campo].get("entra")
                and not f[campo].get("cruza"))
        s = sum(1 for f in filas if f[campo] and not f[campo].get("sale", True))
        return dict(cruzan=z, entran_sin_cruzar=e, nunca_salen=s)

    metricas = {c: contraste(c) for c in
                ("ticks", "ms", "volumen", "ticks_por_ancho", "vol_por_ancho")}

    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        poblacion=("oraculo Flat HFTZonesESPureV2Flat, ES 03-26, pre-firewall. "
                   "CORREGIDA: 51,8%/48,2% por direccion, contra 8,1% alcista del "
                   "original con el bug isDown-first"),
        definicion_cruce=("primer pasaje borde a borde: el precio sale de la banda, "
                          "vuelve a tocar el borde mas cercano (arranca el cronometro) y "
                          "alcanza el borde opuesto (termina)"),
        estimando=("contraste zona - control de la mediana por sesion, sobre las zonas "
                   "que cruzan LAS DOS bandas; nunca el valor absoluto"),
        confundidores_declarados=[
            "ancho: trivialmente mas ancho cuesta mas; el control se empareja por ancho exacto",
            "actividad de sesion: por eso el contraste es dentro de sesion",
            "distancia: el espejo se construye a la misma distancia del precio de creacion",
            "zonas de altura 0: excluidas y contadas"],
        universo=dict(n_zonas=len(filas), n_sesiones=len(por_ses),
                      altura_cero_excluidas=altura_cero, sin_parquet=sin_pq),
        tasas=dict(zona=tasas("zona"), control=tasas("control")),
        metricas=metricas,
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            snapshot=str(a.snapshot), archivos_sucios=sorted(sucios),
            medicion_comprometida=bool([x for x in sucios
                                        if x.startswith(("edgelab/", "diag/"))])),
        zonas=filas)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")

    tz, te = tasas("zona"), tasas("control")
    print("\n  cruzan: zona %d   control %d   (entran sin cruzar: %d / %d)"
          % (tz["cruzan"], te["cruzan"], tz["entran_sin_cruzar"],
             te["entran_sin_cruzar"]))
    print()
    print("  metrica            zona   control   delta PAREADA   %zonas   dispersion p25/p75")
    for c, m in metricas.items():
        if not m:
            print("  %-18s sin datos" % c)
            continue
        d = m["dispersion_pares"]
        print("  %-18s %8.1f %8.1f %+13.1f    %.3f   %+9.1f /%+9.1f"
              % (c, m["zona_mediana"], m["control_mediana"],
                 m["delta_pareada_mediana"], m["frac_zonas_mas_caras"],
                 d["p25"], d["p75"]))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
