"""H-ASIA-1 · costo de pasaje por `asia_close`, TARGET-FREE.

Protocolo: `docs/research/H-ASIA-1_COSTO_DE_PASAJE_PROTOCOLO.md` (P-54).

PREGUNTA
========
Nico: «cuanto más rompió el precio —por tiempo, por volumen, por ticks— el camino a
través del último precio comerciado en la sesión asiática ofrece menos resistencia».

QUÉ SE MIDE Y QUÉ NO
====================
Se mide el **costo de pasaje** por una banda `[nivel ± k]` ticks durante el viaje de
vuelta: `dwell_ns`, `dwell_volumen`, `n_reentradas`. Todo microestructura, sin
dirección.

NO se mide si el precio atraviesa o rebota (eso es dirección: la pregunta de reversión
con otro nombre), ni MFE/MAE/retornos/P&L. Esa parte espera manifiesto + STOP.

EL CONTROL — por qué NO es un placebo suelto
============================================
El confundidor declarado en el protocolo es que las tres magnitudes de ruptura
correlacionan con **volatilidad**, y la volatilidad **baja el dwell en cualquier
nivel**. Un placebo elegido a mano no lo resuelve del todo: hay que emparejarlo por
sesión, por trayecto y por posición.

Se usa un control **dentro de la sesión**: se mide el mismo costo de pasaje en **todos
los niveles enteros** del rango asiático, sobre **el mismo viaje de vuelta**, y se
reporta el **percentil** de `asia_close` dentro de esa distribución.

Eso empareja la volatilidad de forma exacta —es la misma sesión, el mismo trayecto y
los mismos ticks— y deja un nulo limpio: **si `asia_close` no tiene nada especial, su
percentil se distribuye uniforme y su mediana es 50 %.**

SEGUNDO CONFUNDIDOR, encontrado al implementar
==============================================
El percentil crudo **no es interpretable solo**: los niveles del medio del rango
acumulan más dwell que los de los bordes, y `asia_close` no cae en una posición
uniforme dentro del rango. Un percentil alto podría ser sólo «`asia_close` suele estar
en el medio».

Por eso se publican tres cosas y no una:

1. `percentil_dwell` de `asia_close` entre todos los niveles.
2. `posicion_en_rango` de `asia_close` (0 = mínimo, 1 = máximo), para poder condicionar.
3. **`espejo`** = `asia_high + asia_low − asia_close`, el reflejo sobre el punto medio:
   misma posición relativa, precio sin significado. Su percentil es la línea base
   emparejada por posición.

Y la hipótesis se lee en la **TENDENCIA del percentil a través de los terciles de
magnitud**, no en su nivel absoluto. Se publica además la correlación entre posición y
magnitud: si es ~0, la posición no puede sesgar la tendencia.

Target-free: sin outcomes, sin P&L, holdout excluido por firewall.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import session_bounds_utc_ns  # noqa: E402
from edgelab.sessions import NEW_YORK_TZ  # noqa: E402

SCHEMA_VERSION = "costo_pasaje_asia_v1_targetfree"

ASIA_INI_MIN = 18 * 60        # 18:00 NY, apertura CME
ASIA_FIN_MIN = 3 * 60         # 03:00 NY, apertura Londres
POST_FIN_MIN = 17 * 60        # 17:00 NY, cierre de la sesion

K_BANDA = (1, 2, 3, 5)        # semiancho de la banda, en ticks. Grilla declarada.
MIN_TICKS_ASIA = 200
MAX_NIVELES = 400             # rangos mas anchos se reportan y no se censan (costo)

HOLDOUT_FIRST_TRADE_DATE = 20260701
FIREWALL_CUTOFF_NS = session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]


def sha256_archivo(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolver_dir(instrumento, explicito):
    if explicito:
        return pathlib.Path(explicito)
    base = REPO / "data" / "nt8"
    for cand in (base / instrumento, base / ("%s_parquet" % instrumento)):
        if cand.is_dir() and any(cand.glob("%s_*ticks*.parquet" % instrumento)):
            return cand
    raise SystemExit("ABORTA: sin parquets de %s" % instrumento)


def cargar_ticks(d_in, instrumento):
    hashes = {}
    ts, px, vol = [], [], []
    for f in sorted(d_in.glob("%s_*ticks*.parquet" % instrumento)):
        hashes[f.name] = dict(sha256=sha256_archivo(f), canon_disponible=False)
        p = load_canonical_parquet(f, instrument=instrumento)
        print("  %-26s %9d ticks" % (f.name, len(p.ts_ns)))
        ts.append(p.ts_ns)
        px.append(p.price_ticks)
        vol.append(p.volume)
        del p
    ts = np.concatenate(ts)
    px = np.concatenate(px)
    vol = np.concatenate(vol)
    gc.collect()
    orden = np.argsort(ts, kind="stable")
    ts, px, vol = ts[orden], px[orden], vol[orden]
    del orden
    keep = ts < FIREWALL_CUTOFF_NS
    n0 = len(ts)
    ts, px, vol = ts[keep], px[keep], vol[keep]
    print("  ticks   %d brutos -> %d tras firewall" % (n0, len(ts)))
    gc.collect()
    return ts, px, vol, hashes


def costo_por_nivel(px, vol, dt_ns, lo, hi, k):
    """Dwell en ns, volumen y reentradas para CADA nivel entero de `[lo, hi]`.

    Un tick de precio `p` pertenece a la banda de todo nivel `L` con `|p - L| <= k`, o
    sea a los `2k+1` niveles de `[p-k, p+k]`. Eso permite acumular con `np.add.at` sobre
    una ventana chica en vez de recorrer niveles x ticks.

    Las reentradas se cuentan por diferencia de intervalos entre ticks consecutivos: los
    niveles que ENTRAN son los de `[p_{i+1}-k, p_{i+1}+k]` que no estaban en
    `[p_i-k, p_i+k]`. Como los dos son intervalos, la diferencia son a lo sumo dos
    tramos contiguos.
    """
    n_niv = hi - lo + 1
    dwell = np.zeros(n_niv, dtype=np.float64)
    dvol = np.zeros(n_niv, dtype=np.float64)
    reent = np.zeros(n_niv, dtype=np.int64)

    a = np.clip(px - k, lo, hi) - lo
    b = np.clip(px + k, lo, hi) - lo
    dentro = (px + k >= lo) & (px - k <= hi)

    # acumulacion por diferencias: sumar en [a, b] equivale a +v en a y -v en b+1
    ac_d = np.zeros(n_niv + 1)
    ac_v = np.zeros(n_niv + 1)
    idx = np.flatnonzero(dentro)
    np.add.at(ac_d, a[idx], dt_ns[idx])
    np.add.at(ac_d, b[idx] + 1, -dt_ns[idx])
    np.add.at(ac_v, a[idx], vol[idx])
    np.add.at(ac_v, b[idx] + 1, -vol[idx])
    dwell = np.cumsum(ac_d)[:n_niv]
    dvol = np.cumsum(ac_v)[:n_niv]

    # reentradas: tramos de [a1,b1] que no estan en [a0,b0]
    ac_r = np.zeros(n_niv + 1)
    a0, b0, d0 = a[:-1], b[:-1], dentro[:-1]
    a1, b1, d1 = a[1:], b[1:], dentro[1:]
    activo = np.flatnonzero(d1)
    for lo_i, hi_i in ((a1, np.minimum(b1, a0 - 1)), (np.maximum(a1, b0 + 1), b1)):
        li, hi2 = lo_i[activo], hi_i[activo]
        sin_previo = ~d0[activo]
        li = np.where(sin_previo, a1[activo], li)
        hi2 = np.where(sin_previo, b1[activo], hi2)
        val = li <= hi2
        np.add.at(ac_r, li[val], 1)
        np.add.at(ac_r, hi2[val] + 1, -1)
    reent = np.cumsum(ac_r)[:n_niv].astype(np.int64)
    return dwell, dvol, reent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrumento", default="6J")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    print("H-ASIA-1 costo de pasaje (TARGET-FREE)  ·  %s  ·  %s"
          % (SCHEMA_VERSION, a.instrumento))
    d_in = _resolver_dir(a.instrumento, a.dir)
    ts, px, vol, hashes = cargar_ticks(d_in, a.instrumento)

    ny = pd.to_datetime(ts, unit="ns", utc=True).tz_convert(NEW_YORK_TZ)
    minuto = np.asarray(ny.hour * 60 + ny.minute, dtype=np.int64)
    fecha = np.asarray(ny.normalize().view("int64"), dtype=np.int64)
    del ny
    gc.collect()

    # etiqueta de trade date: la ventana arranca 18:00 y cruza medianoche, asi que los
    # ticks anteriores a las 03:00 pertenecen al dia ANTERIOR.
    UN_DIA = 86_400_000_000_000
    en_asia = (minuto >= ASIA_INI_MIN) | (minuto < ASIA_FIN_MIN)
    en_post = (minuto >= ASIA_FIN_MIN) & (minuto < POST_FIN_MIN)
    etiqueta = np.where(minuto < ASIA_FIN_MIN, fecha - UN_DIA, fecha)
    # BUG CORREGIDO 2026-08-19, verificado contra los datos y no razonado.
    #
    # La ventana de Asia va de las 18:00 del dia d a las 03:00 del dia d+1, asi que su
    # POSTERIOR (03:00-17:00) cae en el dia calendario d+1, NO en el d. La version
    # anterior etiquetaba el posterior con `fecha` y seleccionaba `fecha == d`, o sea
    # las 03:00-17:00 del dia d -- que terminan CINCO HORAS ANTES de que la ventana de
    # Asia empiece. Medido en 6J_12-25, dia 2025-10-05:
    #
    #   ASIA            2025-10-05 18:00 -> 2025-10-06 02:59   51.405 ticks
    #   POST (mal)      2025-10-05 13:40 -> 2025-10-05 15:50        2 ticks
    #   POST (bien)     2025-10-06 03:00 -> 2025-10-06 16:59   66.415 ticks
    #
    # O sea: se detectaban "rupturas del rango asiatico" sobre ticks ANTERIORES al
    # rango. Los 52 descartes por `sin_post` eran el sintoma visible.
    #
    # El censo de rango de Asia NO tiene este defecto porque usa UNA sola llamada a
    # `minute_window_matrices` partida por indice de minuto, justamente para que Asia y
    # su posterior sean la misma fila. Ese diseno se abandono al escribir este runner a
    # mano, y el error volvio por la puerta que ese diseno cerraba.
    etiqueta_post = fecha - UN_DIA
    del minuto, fecha

    dias = np.unique(etiqueta[en_asia])
    print("  dias con ventana de Asia: %d" % len(dias))

    filas, descartes = [], {"pocos_ticks_asia": 0, "sin_post": 0, "sin_ruptura": 0,
                            "no_vuelve": 0, "rango_muy_ancho": 0}
    for d in dias:
        ia = np.flatnonzero(en_asia & (etiqueta == d))
        if len(ia) < MIN_TICKS_ASIA:
            descartes["pocos_ticks_asia"] += 1
            continue
        ip = np.flatnonzero(en_post & (etiqueta_post == d))
        if len(ip) < 100:
            descartes["sin_post"] += 1
            continue
        pa = px[ia]
        alto, bajo, cierre = int(pa.max()), int(pa.min()), int(pa[-1])
        rango = alto - bajo
        if rango < 4 or rango > MAX_NIVELES:
            descartes["rango_muy_ancho"] += 1
            continue

        pp, vp, tp = px[ip], vol[ip], ts[ip]
        fuera_alto = np.flatnonzero(pp > alto)
        fuera_bajo = np.flatnonzero(pp < bajo)
        i_alto = int(fuera_alto[0]) if len(fuera_alto) else None
        i_bajo = int(fuera_bajo[0]) if len(fuera_bajo) else None
        if i_alto is None and i_bajo is None:
            descartes["sin_ruptura"] += 1
            continue
        if i_bajo is None or (i_alto is not None and i_alto < i_bajo):
            lado, i_rup, extremo = "alto", i_alto, alto
        else:
            lado, i_rup, extremo = "bajo", i_bajo, bajo

        # excursion: desde la ruptura hasta el PRIMER regreso al rango
        afuera = (pp > alto) if lado == "alto" else (pp < bajo)
        vuelve = np.flatnonzero(~afuera[i_rup:])
        if len(vuelve) == 0:
            descartes["no_vuelve"] += 1
            continue
        i_vue = i_rup + int(vuelve[0])

        tramo = slice(i_rup, i_vue)
        m1_ns = int(tp[i_vue] - tp[i_rup])
        m2_vol = float(vp[tramo].sum())
        m3_tk = int(abs(pp[tramo] - extremo).max()) if i_vue > i_rup else 0

        # viaje de vuelta: desde el regreso al rango hasta el fin de la ventana
        rp, rv, rt = pp[i_vue:], vp[i_vue:], tp[i_vue:]
        if len(rp) < 50:
            continue
        dt = np.diff(rt, append=rt[-1])

        espejo = alto + bajo - cierre
        pos = (cierre - bajo) / rango
        fila = dict(dia=int(d), lado=lado, alto=alto, bajo=bajo, cierre=cierre,
                    rango_ticks=rango, posicion_en_rango=round(float(pos), 4),
                    m1_minutos_fuera=round(m1_ns / 6e10, 3),
                    m2_volumen_fuera=m2_vol, m3_excursion_ticks=m3_tk,
                    n_ticks_vuelta=int(len(rp)), bandas={})
        for k in K_BANDA:
            dw, dv, re = costo_por_nivel(rp, rv, dt, bajo, alto, k)
            j = cierre - bajo
            je = int(np.clip(espejo - bajo, 0, rango))
            orden = np.argsort(dw, kind="stable")
            rank = np.empty(len(dw)); rank[orden] = np.arange(len(dw))
            fila["bandas"]["k%d" % k] = dict(
                dwell_min=round(float(dw[j]) / 6e10, 4),
                dwell_vol=float(dv[j]), reentradas=int(re[j]),
                percentil_dwell=round(float(rank[j]) / max(len(dw) - 1, 1), 4),
                percentil_dwell_espejo=round(float(rank[je]) / max(len(dw) - 1, 1), 4),
                dwell_min_mediana_niveles=round(float(np.median(dw)) / 6e10, 4))
        filas.append(fila)

    print("  sesiones censadas %d   descartes %s" % (len(filas), descartes))

    # --- agregacion: la hipotesis se lee en la TENDENCIA, no en el nivel -------------
    agregado = {}
    if filas:
        for nombre, campo in (("M1_tiempo", "m1_minutos_fuera"),
                              ("M2_volumen", "m2_volumen_fuera"),
                              ("M3_ticks", "m3_excursion_ticks")):
            m = np.array([f[campo] for f in filas], dtype=np.float64)
            q1, q2 = np.percentile(m, [33.333, 66.667])
            grupo = np.where(m <= q1, 0, np.where(m <= q2, 1, 2))
            pos = np.array([f["posicion_en_rango"] for f in filas])
            corr = float(np.corrcoef(m, pos)[0, 1]) if len(m) > 2 else None
            agregado[nombre] = dict(
                cortes_terciles=[float(q1), float(q2)],
                corr_magnitud_vs_posicion=round(corr, 4) if corr is not None else None,
                terciles={})
            for k in K_BANDA:
                por_t = []
                for g in (0, 1, 2):
                    sel = [filas[i]["bandas"]["k%d" % k] for i in np.flatnonzero(grupo == g)]
                    if not sel:
                        por_t.append(None); continue
                    pc = np.array([s["percentil_dwell"] for s in sel])
                    pe = np.array([s["percentil_dwell_espejo"] for s in sel])
                    por_t.append(dict(
                        n=len(sel),
                        percentil_mediana=round(float(np.median(pc)), 4),
                        percentil_media=round(float(pc.mean()), 4),
                        espejo_mediana=round(float(np.median(pe)), 4),
                        contraste_vs_espejo=round(float(np.median(pc) - np.median(pe)), 4),
                        dwell_min_mediana=round(float(np.median(
                            [s["dwell_min"] for s in sel])), 4)))
                agregado[nombre]["terciles"]["k%d" % k] = por_t

    porcelain = subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines()
    sucios = [l[3:].strip() for l in porcelain if l[:2] != "??"]
    criticos = [f for f in sucios if f.startswith(("edgelab/", "diag/"))]

    payload = dict(
        schema_version=SCHEMA_VERSION, instrumento=a.instrumento,
        outcomes_accessed=False, pnl_accessed=False,
        nulo=("control DENTRO de la sesion: el percentil de asia_close entre TODOS los "
              "niveles del rango, sobre el mismo viaje. Nulo = uniforme, mediana 0,5. "
              "El espejo (alto+bajo-cierre) es la linea base emparejada por posicion."),
        advertencia=("la hipotesis se lee en la TENDENCIA del percentil a traves de los "
                     "terciles de magnitud, NO en su nivel absoluto: los niveles del "
                     "medio del rango acumulan mas dwell que los de los bordes."),
        parametros=dict(k_banda=list(K_BANDA), asia="18:00-03:00 NY",
                        post="03:00-17:00 NY", min_ticks_asia=MIN_TICKS_ASIA,
                        max_niveles=MAX_NIVELES),
        firewall=dict(holdout_first_trade_date=HOLDOUT_FIRST_TRADE_DATE,
                      holdout_included=False),
        procedencia=dict(contratos=hashes,
                         head_commit=subprocess.check_output(
                             ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
                         runner_blob=subprocess.check_output(
                             ["git", "-C", str(REPO), "hash-object", str(pathlib.Path(__file__))],
                             text=True).strip(),
                         archivos_sucios=sorted(sucios), sucios_criticos=sorted(criticos),
                         medicion_comprometida=bool(criticos)),
        descartes=descartes, n_sesiones=len(filas),
        agregado=agregado, sesiones=filas)
    pathlib.Path(a.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    for nombre in agregado:
        ag = agregado[nombre]
        print("  %s  (corr magnitud vs posicion: %s)"
              % (nombre, ag["corr_magnitud_vs_posicion"]))
        for k in K_BANDA:
            t = ag["terciles"]["k%d" % k]
            if all(t):
                print("    k=%d  percentil por tercil: %.3f -> %.3f -> %.3f   "
                      "contraste vs espejo: %+.3f -> %+.3f -> %+.3f"
                      % (k, t[0]["percentil_mediana"], t[1]["percentil_mediana"],
                         t[2]["percentil_mediana"], t[0]["contraste_vs_espejo"],
                         t[1]["contraste_vs_espejo"], t[2]["contraste_vs_espejo"]))
    print("  medicion_comprometida %s" % bool(criticos))
    print("  informe %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
