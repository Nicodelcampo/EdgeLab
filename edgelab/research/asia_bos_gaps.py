"""ASIA-BOS-GAPS (2026-10-29): Rango de Compresión Asiático + Ruptura BOS / Barrido con Reingreso IFVG (Posts #18/#23 @alefx_ar, #159 @algo.jan, #110 @tomcampcoaching) acoplado a ZONAS-GAPS y Corredor EMA.

Hipótesis física y microestructural (Catálogo de Guardados de Instagram Tier-1 #2 y #11 + primitivas EdgeLab):
  1. Durante el inicio de la sesión asiática en hora de Nueva York (`America/New_York` con ajuste DST exacto EDT/EST), el flujo
     electrónico en `NQ`, `ES` y `GC` acumula órdenes en una caja de consolidación `[lo_asia, hi_asia]` de altura `H_asia`:
     - `0 = 18:00–20:00 ET`: ventana canónica de 2 horas de `@alefx_ar` (Posts #18 y #23).
     - `1 = 18:00–22:00 ET`: ventana asiática extendida de 4 horas (incluye apertura de Tokio).
     - `2 = 20:00–00:00 ET`: ventana Asia tardía previa a la transición europea.
  2. Una vez cerrada la ventana de referencia asiática, se evalúan 3 gatillos mecánicos causales (`gatillo_asia`):
     - `0 = BOS_CUERPO_FUERTE`: ruptura estructural con vela que cierra fuera de `[lo_asia, hi_asia]` con cuerpo >= 55% del rango
       de la vela (modelo BOS de continuación tras compresión).
     - `1 = BARRIDO_REINGRESO_IFVG`: el precio barre `hi_asia` o `lo_asia` y vuelve a cerrar dentro de `[lo_asia, hi_asia]`
       invirtiendo el gap de ruptura (*IFVG* / *Asian Session Glitch* de `@algo.jan`).
     - `2 = PULLBACK_BORDE_ASIA`: tras romper `[lo_asia, hi_asia]`, el precio retrocede a testear el borde roto (`<= 0.25 * H_asia`)
       y vuelve a rechazar a favor de la ruptura.
  3. Cruce en espiral con primitivas de EdgeLab (`VARIABLES`):
     - `ventana_asia` (`grupo`, 3 niveles).
     - `gatillo_asia` (`grupo`, 3 niveles).
     - `excursion_rel` (`ge`, cortes `(0.08, 0.20)`): excursión relativa fuera del borde asiático.
     - `impulso_vela` (`eq_any`, 2 niveles): cuerpo >= 55% + volumen relativo >= 1.15x.
     - `gap_barrido` (`eq_any`, cortes `(0.05, 1.00)`): puntaje `ZONAS-GAPS` de gaps barridos en el movimiento.
     - `gap_iman` (`eq_any`, cortes `(0.05, 1.00)`): puntaje `ZONAS-GAPS` de gaps abiertos en el camino del objetivo.
     - `corredor_ema` (`eq_any`, 3 niveles): estado del corredor `EMA20/EMA60` (`EmaCorridorTrendVolW2`).
     - `ancho_caja_rel` (`extremos`, 3 terciles causales): compresión relativa `H_asia / ATR14`.
     - `vwap_al` (`eq_any`, 2 niveles): alineación con el `VWAP` de la sesión.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.otr_930_sweep import _offset_ny_seg_nb

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ASIA-BOS-GAPS"
INDICADORES = ["ASIA-BOS-GAPS", "ZONAS-GAPS", "EmaCorridorTrendVolW2"]

VARIABLES = [
    Variable("ventana_asia", "v_asia", "grupo", categoria=3),              # 0: 18:00-20:00 ET · 1: 18:00-22:00 ET · 2: 20:00-00:00 ET
    Variable("gatillo_asia", "gat", "grupo", categoria=3),                 # 0: BOS_CUERPO_FUERTE · 1: BARRIDO_REINGRESO_IFVG · 2: PULLBACK_BORDE
    Variable("excursion_rel", "exc_rel", "ge", cortes=(0.08, 0.20)),       # excursión relativa fuera de la caja asiática
    Variable("impulso_vela", "imp_v", "eq_any", categoria=2),              # 0: normal · 1: cuerpo >= 55% + vol >= 1.15x · 2: cualquiera
    Variable("gap_barrido", "g_tom", "eq_any", cortes=(0.05, 1.00)),       # 0: 0 · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("gap_iman", "g_cam", "eq_any", cortes=(0.05, 1.00)),          # 0: 0 · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("corredor_ema", "ema_al", "eq_any", categoria=3),             # 0: contra · 1: comprimido · 2: a favor · 3: cualquiera
    Variable("ancho_caja_rel", "tam_rng", "extremos", cuantiles=3),        # terciles causales de H_asia / ATR14
    Variable("vwap_al", "vwap_al", "eq_any", categoria=2),                 # 0: lejos de VWAP · 1: hacia VWAP · 2: cualquiera
]
EJES_ORDINALES = (2, 4, 5)

MODOS_DIR = ("CONTINUACION_BOS", "REVERSION_CAJA")
ENTRADAS = ("CIERRE", "SIG")
TARGETS = ("EXT_150", "CAJA_100", "MID_50")
STOPS = ("S_BORDE", "S_CAJA60")
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "ventana_asia": 0,
    "gatillo_asia": 0,
    "excursion_rel": 0,
    "impulso_vela": 2,
    "gap_barrido": 3,
    "gap_iman": 3,
    "corredor_ema": 3,
    "ancho_caja_rel": 2,
    "vwap_al": 2,
    "ejecución": EJECUCIONES.index(("CONTINUACION_BOS", "CIERRE", "CAJA_100", "S_BORDE")),
}


@njit(cache=False)
def _extraer_disparos_asia_nb(t, o, h, l, c, v, ses, tick):
    n = len(c)
    max_out = max(n // 4, 256)
    out_k = np.empty(max_out, dtype=np.int64)
    out_vasia = np.empty(max_out, dtype=np.int64)
    out_gat = np.empty(max_out, dtype=np.int64)
    out_lado = np.empty(max_out, dtype=np.int64)
    out_lo = np.empty(max_out, dtype=np.float64)
    out_hi = np.empty(max_out, dtype=np.float64)
    out_hrng = np.empty(max_out, dtype=np.float64)
    out_eexc = np.empty(max_out, dtype=np.float64)
    out_excrel = np.empty(max_out, dtype=np.float64)
    out_impv = np.empty(max_out, dtype=np.int64)
    out_gtom = np.empty(max_out, dtype=np.float64)
    out_gcam = np.empty(max_out, dtype=np.float64)
    out_ema = np.empty(max_out, dtype=np.int64)
    out_tam = np.empty(max_out, dtype=np.float64)
    out_vwap = np.empty(max_out, dtype=np.int64)
    cnt = 0

    # Minutos desde el inicio de la sesión CME (18:00 ET = minuto 0 del ciclo CME; 00:00 ET = 360; 08:00 ET = 840)
    v_ini = np.array([0, 0, 120], dtype=np.int64)     # 18:00 ET, 18:00 ET, 20:00 ET
    v_fin = np.array([120, 240, 360], dtype=np.int64) # 20:00 ET, 22:00 ET, 00:00 ET
    v_max_eval = 840                                  # hasta las 08:00 ET (apertura NY pre-market)

    MAX_GAPS = 64
    g_lo = np.zeros(MAX_GAPS, dtype=np.float64)
    g_hi = np.zeros(MAX_GAPS, dtype=np.float64)
    g_vivo = np.zeros(MAX_GAPS, dtype=np.int64)
    g_head = 0

    atr = max(h[0] - l[0], tick)
    vol_med = max(v[0], 1.0)
    ema20 = c[0]
    ema60 = c[0]
    a20 = 2.0 / 21.0
    a60 = 2.0 / 61.0

    lo_box = np.full(3, 1e18, dtype=np.float64)
    hi_box = np.full(3, -1e18, dtype=np.float64)
    n_box = np.zeros(3, dtype=np.int64)
    atr_cierre_box = np.zeros(3, dtype=np.float64)
    lado_rup = np.zeros(3, dtype=np.int64)
    ext_rup = np.zeros(3, dtype=np.float64)
    disparado = np.zeros((3, 3), dtype=np.int64)

    ses_act = -1
    vwap_num = 0.0
    vwap_den = 0.0

    for i in range(n):
        if ses[i] != ses_act:
            ses_act = ses[i]
            vwap_num = 0.0
            vwap_den = 0.0
            for w in range(3):
                lo_box[w] = 1e18
                hi_box[w] = -1e18
                n_box[w] = 0
                atr_cierre_box[w] = atr
                lado_rup[w] = 0
                ext_rup[w] = c[i]
                for g_idx in range(3):
                    disparado[w, g_idx] = 0

        if i > 0:
            tr = max(h[i] - l[i], max(abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
            atr = (13.0 * atr + max(tr, tick)) / 14.0
            vol_med = 0.95 * vol_med + 0.05 * max(v[i], 1.0)
            ema20 = a20 * c[i] + (1.0 - a20) * ema20
            ema60 = a60 * c[i] + (1.0 - a60) * ema60

        tp_px = (h[i] + l[i] + c[i]) / 3.0
        vwap_num += tp_px * max(v[i], 1.0)
        vwap_den += max(v[i], 1.0)
        vwap_now = vwap_num / vwap_den if vwap_den > 0.0 else c[i]

        g_tom_bar = 0.0
        for g in range(MAX_GAPS):
            if g_vivo[g] == 1:
                if l[i] <= g_hi[g] and h[i] >= g_lo[g]:
                    g_tom_bar += 0.65
                    if l[i] <= g_lo[g] and h[i] >= g_hi[g]:
                        g_vivo[g] = 0

        if i >= 2:
            if l[i] - h[i - 2] >= 2.0 * tick:
                g_lo[g_head] = h[i - 2]
                g_hi[g_head] = l[i]
                g_vivo[g_head] = 1
                g_head = (g_head + 1) % MAX_GAPS
            elif l[i - 2] - h[i] >= 2.0 * tick:
                g_lo[g_head] = h[i]
                g_hi[g_head] = l[i - 2]
                g_vivo[g_head] = 1
                g_head = (g_head + 1) % MAX_GAPS

        off_ny = _offset_ny_seg_nb(int(t[i]))
        min_et = ((int(t[i]) + off_ny) % 86400) // 60
        # Minuto relativo a las 18:00 ET (1080 min del día)
        min_cme = (min_et - 1080) if min_et >= 1080 else (min_et + 360)

        for w in range(3):
            if v_ini[w] <= min_cme < v_fin[w]:
                if l[i] < lo_box[w]:
                    lo_box[w] = l[i]
                if h[i] > hi_box[w]:
                    hi_box[w] = h[i]
                n_box[w] += 1
                atr_cierre_box[w] = max(atr, tick)
            elif v_fin[w] <= min_cme <= v_max_eval and n_box[w] >= 5:
                H_r = hi_box[w] - lo_box[w]
                if H_r < 2.0 * tick:
                    continue
                tam_rel = H_r / max(atr_cierre_box[w], tick)

                # Detectar primera excursión fuera de la caja asiática
                if lado_rup[w] == 0:
                    if h[i] > hi_box[w]:
                        lado_rup[w] = 1
                        ext_rup[w] = h[i]
                    elif l[i] < lo_box[w]:
                        lado_rup[w] = -1
                        ext_rup[w] = l[i]
                else:
                    if lado_rup[w] == 1 and h[i] > ext_rup[w]:
                        ext_rup[w] = h[i]
                    elif lado_rup[w] == -1 and l[i] < ext_rup[w]:
                        ext_rup[w] = l[i]

                if lado_rup[w] == 0:
                    continue

                lr = lado_rup[w]
                exc_abs = (ext_rup[w] - hi_box[w]) if lr == 1 else (lo_box[w] - ext_rup[w])
                exc_rel = max(exc_abs / H_r, 0.0)
                rng_b = max(h[i] - l[i], tick)
                cuerpo_rel = abs(c[i] - o[i]) / rng_b
                imp_st = 1 if (cuerpo_rel >= 0.55 and v[i] >= 1.15 * vol_med) else 0

                # Evaluar los 3 gatillos
                for gat_id in range(3):
                    if disparado[w, gat_id] == 1:
                        continue
                    ok_gat = 0
                    if gat_id == 0:
                        # BOS_CUERPO_FUERTE: cierra afuera en dirección lr con cuerpo >= 50%
                        if lr == 1 and c[i] > hi_box[w] and c[i] > o[i] and cuerpo_rel >= 0.50:
                            ok_gat = 1
                        elif lr == -1 and c[i] < lo_box[w] and c[i] < o[i] and cuerpo_rel >= 0.50:
                            ok_gat = 1
                    elif gat_id == 1:
                        # BARRIDO_REINGRESO_IFVG: tras barrer, cierra de vuelta adentro de la caja
                        if lr == 1 and ext_rup[w] > hi_box[w] + tick and lo_box[w] <= c[i] <= hi_box[w] and c[i] < o[i]:
                            ok_gat = 1
                        elif lr == -1 and ext_rup[w] < lo_box[w] - tick and lo_box[w] <= c[i] <= hi_box[w] and c[i] > o[i]:
                            ok_gat = 1
                    else:
                        # PULLBACK_BORDE_ASIA: tras romper > 0.15 H_r, retrocede cerca del borde roto y rechaza a favor de lr
                        if lr == 1 and exc_rel >= 0.15 and l[i] <= hi_box[w] + 0.25 * H_r and c[i] > hi_box[w] and c[i] > o[i]:
                            ok_gat = 1
                        elif lr == -1 and exc_rel >= 0.15 and h[i] >= lo_box[w] - 0.25 * H_r and c[i] < lo_box[w] and c[i] < o[i]:
                            ok_gat = 1

                    if ok_gat == 1 and cnt < max_out:
                        disparado[w, gat_id] = 1
                        g_cam_val = 0.0
                        for g in range(MAX_GAPS):
                            if g_vivo[g] == 1:
                                g_mid = 0.5 * (g_lo[g] + g_hi[g])
                                if lr == 1 and c[i] < g_mid <= c[i] + 1.5 * H_r:
                                    g_cam_val += 0.65
                                elif lr == -1 and c[i] - 1.5 * H_r <= g_mid < c[i]:
                                    g_cam_val += 0.65

                        dif_ema = ema20 - ema60
                        if abs(dif_ema) < 0.20 * atr:
                            ema_st = 1
                        elif dif_ema * float(lr) > 0.0:
                            ema_st = 2
                        else:
                            ema_st = 0

                        vwap_st = 1 if (vwap_now - c[i]) * float(lr) > 0.0 else 0

                        out_k[cnt] = i
                        out_vasia[cnt] = w
                        out_gat[cnt] = gat_id
                        out_lado[cnt] = lr
                        out_lo[cnt] = lo_box[w]
                        out_hi[cnt] = hi_box[w]
                        out_hrng[cnt] = H_r
                        out_eexc[cnt] = ext_rup[w]
                        out_excrel[cnt] = exc_rel
                        out_impv[cnt] = imp_st
                        out_gtom[cnt] = g_tom_bar
                        out_gcam[cnt] = g_cam_val
                        out_ema[cnt] = ema_st
                        out_tam[cnt] = tam_rel
                        out_vwap[cnt] = vwap_st
                        cnt += 1

    return (
        out_k[:cnt],
        out_vasia[:cnt],
        out_gat[:cnt],
        out_lado[:cnt],
        out_lo[:cnt],
        out_hi[:cnt],
        out_hrng[:cnt],
        out_eexc[:cnt],
        out_excrel[:cnt],
        out_impv[:cnt],
        out_gtom[:cnt],
        out_gcam[:cnt],
        out_ema[:cnt],
        out_tam[:cnt],
        out_vwap[:cnt],
    )


def disparos(ctx: dict) -> pd.DataFrame:
    t = np.asarray(ctx["t"], dtype=np.int64)
    o = np.asarray(ctx["o"], dtype=np.float64)
    h = np.asarray(ctx["h"], dtype=np.float64)
    l = np.asarray(ctx["l"], dtype=np.float64)
    c = np.asarray(ctx["c"], dtype=np.float64)
    v = np.asarray(ctx["v"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    tick = float(ctx["tick"])

    res = _extraer_disparos_asia_nb(t, o, h, l, c, v, ses, tick)
    k = res[0]
    return pd.DataFrame(
        {
            "k": k,
            "ses": ses[k],
            "v_asia": res[1],
            "gat": res[2],
            "lado": res[3],
            "lo_rng": res[4],
            "hi_rng": res[5],
            "H_rng": res[6],
            "E_exc": res[7],
            "exc_rel": res[8],
            "imp_v": res[9],
            "g_tom": res[10],
            "g_cam": res[11],
            "ema_al": res[12],
            "tam_rng": res[13],
            "vwap_al": res[14],
        }
    )


def niveles(d, ej: tuple, ctx: dict):
    md, ent, tp_name, sl_name = ej
    k = int(d["k"])
    lado = int(d["lado"])
    lo_r = float(d["lo_rng"])
    hi_r = float(d["hi_rng"])
    H_r = float(d["H_rng"])
    E_exc = float(d["E_exc"])
    tick = float(ctx["tick"])
    ck = float(ctx["c"][k])

    s = lado if md == "CONTINUACION_BOS" else -lado
    lim = 0 if ent == "CIERRE" else 2
    e = np.round(ck / tick) * tick

    if md == "CONTINUACION_BOS":
        mult_tp = 1.50 if tp_name == "EXT_150" else (1.00 if tp_name == "CAJA_100" else 0.55)
        tp_raw = e + float(s) * mult_tp * H_r
    else:
        opuesto = lo_r if lado == 1 else hi_r
        if tp_name == "EXT_150":
            tp_raw = opuesto + float(s) * 0.35 * H_r
            min_m = 0.90
        elif tp_name == "CAJA_100":
            tp_raw = opuesto
            min_m = 0.65
        else:
            tp_raw = 0.5 * (lo_r + hi_r)
            min_m = 0.40
        if (tp_raw - e) * float(s) < min_m * H_r:
            tp_raw = e + float(s) * min_m * H_r

    tp = np.round(tp_raw / tick) * tick
    if (tp - e) * float(s) < 2.0 * tick:
        tp = e + float(s) * 2.0 * tick

    dist_borde = max(abs(E_exc - e) + 2.0 * tick, 0.35 * H_r) if md == "REVERSION_CAJA" else 0.40 * H_r
    if sl_name == "S_BORDE":
        sl_raw = e - float(s) * dist_borde
    else:
        dist_60 = 0.65 * H_r
        if abs(dist_60 - dist_borde) < 2.0 * tick:
            dist_60 = dist_borde + 3.0 * tick
        sl_raw = e - float(s) * dist_60

    sl = np.floor(sl_raw / tick) * tick if s == 1 else np.ceil(sl_raw / tick) * tick
    if (e - sl) * float(s) < 2.0 * tick:
        sl = e - float(s) * 2.0 * tick

    return (k, lim, s, float(e), float(sl), float(tp), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    m = len(D)
    out = np.full((m, 7), np.nan, dtype=np.float64)
    if m == 0:
        return out
    md, ent, tp_name, sl_name = ej
    k = D["k"].to_numpy(np.int64)
    lado = D["lado"].to_numpy(np.int64)
    lo_r = D["lo_rng"].to_numpy(np.float64)
    hi_r = D["hi_rng"].to_numpy(np.float64)
    H_r = D["H_rng"].to_numpy(np.float64)
    E_exc = D["E_exc"].to_numpy(np.float64)
    tick = float(ctx["tick"])
    ck = np.asarray(ctx["c"], dtype=np.float64)[k]

    s = (lado if md == "CONTINUACION_BOS" else -lado).astype(np.float64)
    lim = 0.0 if ent == "CIERRE" else 2.0
    e = np.round(ck / tick) * tick

    if md == "CONTINUACION_BOS":
        mult_tp = 1.50 if tp_name == "EXT_150" else (1.00 if tp_name == "CAJA_100" else 0.55)
        tp_raw = e + s * mult_tp * H_r
    else:
        opuesto = np.where(lado == 1, lo_r, hi_r)
        if tp_name == "EXT_150":
            tp_raw = opuesto + s * 0.35 * H_r
            min_m = 0.90
        elif tp_name == "CAJA_100":
            tp_raw = opuesto
            min_m = 0.65
        else:
            tp_raw = 0.5 * (lo_r + hi_r)
            min_m = 0.40
        corto = (tp_raw - e) * s < min_m * H_r
        tp_raw = np.where(corto, e + s * min_m * H_r, tp_raw)

    tp = np.round(tp_raw / tick) * tick
    tp = np.where((tp - e) * s < 2.0 * tick, e + s * 2.0 * tick, tp)

    dist_borde = np.maximum(np.abs(E_exc - e) + 2.0 * tick, 0.35 * H_r) if md == "REVERSION_CAJA" else 0.40 * H_r
    if sl_name == "S_BORDE":
        sl_raw = e - s * dist_borde
    else:
        dist_60 = np.full(m, 0.65, dtype=np.float64) * H_r
        dist_60 = np.where(np.abs(dist_60 - dist_borde) < 2.0 * tick, dist_borde + 3.0 * tick, dist_60)
        sl_raw = e - s * dist_60

    sl = np.where(s == 1.0, np.floor(sl_raw / tick) * tick, np.ceil(sl_raw / tick) * tick)
    sl = np.where((e - sl) * s < 2.0 * tick, e - s * 2.0 * tick, sl)

    out[:, 0] = k.astype(np.float64)
    out[:, 1] = lim
    out[:, 2] = s
    out[:, 3] = e
    out[:, 4] = sl
    out[:, 5] = tp
    out[:, 6] = 0.0
    return out
