"""TORI-TREND-TOQUE3 (2026-10-29): Teoría de Tiempos de Parada y Líneas de Tendencia por Pivotes Causales (Tori Trades + Post #943) acoplada a ZONAS-GAPS y Corredor EMA.

Hipótesis física y microestructural (Paper Tori Trades 2026-10-26 + cruce en espiral con EdgeLab):
  1. Los pivotes de swing confirmados causalmente con retraso `k_piv` barras (`High[i-k_piv]` máximo local de `[i-2*k_piv .. i]`,
     `Low[i-k_piv]` mínimo local de `[i-2*k_piv .. i]`) definen rectas de soporte ascendente (uniendo dos mínimos crecientes
     `L_1 < L_2`) o de resistencia descendente (uniendo dos máximos decrecientes `H_1 > H_2`).
  2. La pendiente de la recta se normaliza causalmente por la volatilidad local `ATR(14)` (`angulo_norm = |pendiente| / ATR14`),
     descartando rectas degeneradas o verticales.
  3. Se evalúan 3 gatillos mecánicos causales (`gatillo_tori`) al interactuar el precio con la recta proyectada `y(k)` en la barra `k`:
     - `0 = TOQUE3_RECHAZO`: tercer contacto causal con la recta tras un enfriamiento temporal (regla de seguridad de Tori Trades),
       donde la barra `k` penetra o toca la zona de la recta (`<= 0.25 * ATR14`) y cierra respetando el lado de la tendencia.
     - `1 = RUPTURA_STOPPING_TIME`: tiempo de parada `tau` (Proposición 2 del paper), primera barra `k` que cierra quebrando la
       recta por más de un margen estructural `delta * ATR14`, activando la transición de régimen.
     - `2 = THROWBACK_POST_RUPTURA`: tras el quiebre `tau` de la recta, el precio regresa a testear la recta quebrada desde el otro
       lado (mecánica U1 sobre línea estructural) y rechaza.
  4. Cruce en espiral con primitivas de EdgeLab (`VARIABLES`):
     - `orden_pivote` (`grupo`, 3 niveles: `k_piv = 3, 5, 8`).
     - `gatillo_tori` (`grupo`, 3 niveles: `TOQUE3_RECHAZO`, `RUPTURA_STOPPING_TIME`, `THROWBACK_POST_RUPTURA`).
     - `enfriamiento_norm` (`ge`, cortes `(0.50, 1.00)`): separación temporal entre anclas normalizada (regla de las 4h / multi-barra).
     - `absorcion_vol` (`eq_any`, 2 niveles): mecha de rechazo >= 30% + volumen relativo >= 1.15x en la vela de disparo.
     - `gap_barrido` (`eq_any`, cortes `(0.05, 1.00)`): puntaje `ZONAS-GAPS` de gaps barridos en la aproximación a la recta.
     - `gap_iman` (`eq_any`, cortes `(0.05, 1.00)`): puntaje `ZONAS-GAPS` de gaps vivos en la dirección del objetivo.
     - `corredor_ema` (`eq_any`, 3 niveles): estado del corredor `EMA20/EMA60` (`EmaCorridorTrendVolW2`).
     - `angulo_norm` (`extremos`, 3 terciles causales): pendiente normalizada `|pendiente| / ATR14`.
     - `vwap_al` (`eq_any`, 2 niveles): alineación del objetivo con el `VWAP` de la sesión.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "TORI-TREND-TOQUE3"
INDICADORES = ["TORI-TREND-TOQUE3", "ZONAS-GAPS", "EmaCorridorTrendVolW2"]

VARIABLES = [
    Variable("orden_pivote", "ord_piv", "grupo", categoria=3),             # 0: k=3 · 1: k=5 · 2: k=8
    Variable("gatillo_tori", "gat", "grupo", categoria=3),                 # 0: TOQUE3_RECHAZO · 1: RUPTURA_STOPPING_TIME · 2: THROWBACK
    Variable("enfriamiento_norm", "enf_rel", "ge", cortes=(0.50, 1.00)),   # separación temporal normalizada desde el 2do pivote
    Variable("absorcion_vol", "abs_vol", "eq_any", categoria=2),           # 0: normal · 1: mecha + vol >= 1.15x · 2: cualquiera
    Variable("gap_barrido", "g_tom", "eq_any", cortes=(0.05, 1.00)),       # 0: 0 · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("gap_iman", "g_cam", "eq_any", cortes=(0.05, 1.00)),          # 0: 0 · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("corredor_ema", "ema_al", "eq_any", categoria=3),             # 0: contra · 1: comprimido · 2: a favor · 3: cualquiera
    Variable("angulo_norm", "ang_norm", "extremos", cuantiles=3),          # terciles causales de |slope| / ATR14
    Variable("vwap_al", "vwap_al", "eq_any", categoria=2),                 # 0: lejos de VWAP · 1: hacia VWAP · 2: cualquiera
]
EJES_ORDINALES = (2, 4, 5)

MODOS_DIR = ("A_FAVOR_ESTRUCTURA", "REVERSION_PARADA")
ENTRADAS = ("CIERRE", "SIG")
TARGETS = ("SWING_100", "MID_65", "CORTO_45")
STOPS = ("S_LINEA", "S_ESTRUCTURA55")
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "orden_pivote": 0,
    "gatillo_tori": 0,
    "enfriamiento_norm": 0,
    "absorcion_vol": 2,
    "gap_barrido": 3,
    "gap_iman": 3,
    "corredor_ema": 3,
    "angulo_norm": 2,
    "vwap_al": 2,
    "ejecución": EJECUCIONES.index(("A_FAVOR_ESTRUCTURA", "CIERRE", "SWING_100", "S_LINEA")),
}


@njit(cache=False)
def _extraer_disparos_tori_nb(t, o, h, l, c, v, ses, tick):
    n = len(c)
    max_out = max(n // 3, 256)
    out_k = np.empty(max_out, dtype=np.int64)
    out_ord = np.empty(max_out, dtype=np.int64)
    out_gat = np.empty(max_out, dtype=np.int64)
    out_lado = np.empty(max_out, dtype=np.int64)
    out_y = np.empty(max_out, dtype=np.float64)
    out_hs = np.empty(max_out, dtype=np.float64)
    out_eexc = np.empty(max_out, dtype=np.float64)
    out_enf = np.empty(max_out, dtype=np.float64)
    out_absv = np.empty(max_out, dtype=np.int64)
    out_gtom = np.empty(max_out, dtype=np.float64)
    out_gcam = np.empty(max_out, dtype=np.float64)
    out_ema = np.empty(max_out, dtype=np.int64)
    out_ang = np.empty(max_out, dtype=np.float64)
    out_vwap = np.empty(max_out, dtype=np.int64)
    cnt = 0

    k_pivs = np.array([3, 5, 8], dtype=np.int64)

    # Memoria de los 2 últimos pivotes confirmados por cada orden (0..2) y tipo (soporte=1, resistencia=-1)
    p1_idx = np.full((3, 2), -1, dtype=np.int64)
    p1_val = np.zeros((3, 2), dtype=np.float64)
    p2_idx = np.full((3, 2), -1, dtype=np.int64)
    p2_val = np.zeros((3, 2), dtype=np.float64)
    swing_opuesto = np.zeros((3, 2), dtype=np.float64)
    estado_linea = np.zeros((3, 2), dtype=np.int64)  # 0: intacta esperando toque3/ruptura, 1: quebrada esperando throwback, 2: consumida
    bar_quiebre = np.full((3, 2), -1, dtype=np.int64)
    ext_quiebre = np.zeros((3, 2), dtype=np.float64)

    # Buffer circular de gaps M1
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
    ses_act = -1
    vwap_num = 0.0
    vwap_den = 0.0
    disp_ses = np.zeros((3, 3), dtype=np.int64)

    for i in range(1, n):
        if ses[i] != ses_act:
            ses_act = ses[i]
            vwap_num = 0.0
            vwap_den = 0.0
            for a in range(3):
                for b in range(3):
                    disp_ses[a, b] = 0

        tr = max(h[i] - l[i], max(abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
        atr = (13.0 * atr + max(tr, tick)) / 14.0
        vol_med = 0.95 * vol_med + 0.05 * max(v[i], 1.0)
        ema20 = a20 * c[i] + (1.0 - a20) * ema20
        ema60 = a60 * c[i] + (1.0 - a60) * ema60
        tp_px = (h[i] + l[i] + c[i]) / 3.0
        vwap_num += tp_px * max(v[i], 1.0)
        vwap_den += max(v[i], 1.0)
        vwap_now = vwap_num / vwap_den if vwap_den > 0.0 else c[i]

        # Mitigar gaps previos y contar cuántos se barrieron en esta vela
        g_tom_bar = 0.0
        for g in range(MAX_GAPS):
            if g_vivo[g] == 1:
                if l[i] <= g_hi[g] and h[i] >= g_lo[g]:
                    g_tom_bar += 0.65
                    if l[i] <= g_lo[g] and h[i] >= g_hi[g]:
                        g_vivo[g] = 0

        # Registrar nuevo gap de cuerpo/sombra (3 velas)
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

        # 1. Confirmar pivotes causales en idx_p = i - kp
        for o_idx in range(3):
            kp = k_pivs[o_idx]
            if i < 2 * kp + 2:
                continue
            idx_p = i - kp
            es_max = 1
            es_min = 1
            hp = h[idx_p]
            lp = l[idx_p]
            for j in range(idx_p - kp, i + 1):
                if j == idx_p:
                    continue
                if h[j] > hp:
                    es_max = 0
                if l[j] < lp:
                    es_min = 0

            # Soporte ascendente (slot 0: mínimos crecientes)
            if es_min == 1:
                if p2_idx[o_idx, 0] >= 0 and lp > p2_val[o_idx, 0] and (idx_p - p2_idx[o_idx, 0]) >= kp:
                    p1_idx[o_idx, 0] = p2_idx[o_idx, 0]
                    p1_val[o_idx, 0] = p2_val[o_idx, 0]
                    p2_idx[o_idx, 0] = idx_p
                    p2_val[o_idx, 0] = lp
                    # Altura del swing entre p1 y p2
                    h_max_sw = hp
                    for j in range(p1_idx[o_idx, 0], p2_idx[o_idx, 0] + 1):
                        if h[j] > h_max_sw:
                            h_max_sw = h[j]
                    swing_opuesto[o_idx, 0] = max(h_max_sw - p1_val[o_idx, 0], 3.0 * atr)
                    estado_linea[o_idx, 0] = 0
                elif p2_idx[o_idx, 0] < 0 or lp <= p2_val[o_idx, 0]:
                    p2_idx[o_idx, 0] = idx_p
                    p2_val[o_idx, 0] = lp

            # Resistencia descendente (slot 1: máximos decrecientes)
            if es_max == 1:
                if p2_idx[o_idx, 1] >= 0 and hp < p2_val[o_idx, 1] and (idx_p - p2_idx[o_idx, 1]) >= kp:
                    p1_idx[o_idx, 1] = p2_idx[o_idx, 1]
                    p1_val[o_idx, 1] = p2_val[o_idx, 1]
                    p2_idx[o_idx, 1] = idx_p
                    p2_val[o_idx, 1] = hp
                    l_min_sw = lp
                    for j in range(p1_idx[o_idx, 1], p2_idx[o_idx, 1] + 1):
                        if l[j] < l_min_sw:
                            l_min_sw = l[j]
                    swing_opuesto[o_idx, 1] = max(p1_val[o_idx, 1] - l_min_sw, 3.0 * atr)
                    estado_linea[o_idx, 1] = 0
                elif p2_idx[o_idx, 1] < 0 or hp >= p2_val[o_idx, 1]:
                    p2_idx[o_idx, 1] = idx_p
                    p2_val[o_idx, 1] = hp

            # 2. Evaluar interacción de la barra actual `i` con las líneas activas
            for slot in range(2):
                i1 = p1_idx[o_idx, slot]
                i2 = p2_idx[o_idx, slot]
                if i1 < 0 or i2 <= i1 or estado_linea[o_idx, slot] == 2:
                    continue
                dt = float(i2 - i1)
                if dt < 3.0 or (i - i2) > 180:
                    continue
                slope = (p2_val[o_idx, slot] - p1_val[o_idx, slot]) / dt
                ang = abs(slope) / atr
                if ang > 1.5:  # descartar rectas demasiado empinadas
                    continue
                y_i = p2_val[o_idx, slot] + slope * float(i - i2)
                H_sw = max(swing_opuesto[o_idx, slot], 2.5 * atr)
                enf_rel = float(i - i2) / max(dt, 6.0)

                lado_est = 1 if slot == 0 else -1  # +1 soporte alcista, -1 resistencia bajista
                gat_hit = -1
                e_exc_val = l[i] if lado_est == 1 else h[i]

                if estado_linea[o_idx, slot] == 0 and (i - i2) >= kp + 1:
                    if lado_est == 1:
                        # Toque 3 en soporte alcista: toca cerca de y_i y cierra arriba
                        if l[i] <= y_i + 0.25 * atr and c[i] >= y_i and c[i] > o[i]:
                            gat_hit = 0
                            e_exc_val = l[i]
                            estado_linea[o_idx, slot] = 2
                        # Stopping-time break: cierra debajo de y_i - 0.30 * atr
                        elif c[i] < y_i - 0.30 * atr and c[i] < o[i]:
                            gat_hit = 1
                            e_exc_val = h[i]
                            estado_linea[o_idx, slot] = 1
                            bar_quiebre[o_idx, slot] = i
                            ext_quiebre[o_idx, slot] = l[i]
                    else:
                        # Toque 3 en resistencia bajista: toca cerca de y_i y cierra abajo
                        if h[i] >= y_i - 0.25 * atr and c[i] <= y_i and c[i] < o[i]:
                            gat_hit = 0
                            e_exc_val = h[i]
                            estado_linea[o_idx, slot] = 2
                        # Stopping-time break: cierra arriba de y_i + 0.30 * atr
                        elif c[i] > y_i + 0.30 * atr and c[i] > o[i]:
                            gat_hit = 1
                            e_exc_val = l[i]
                            estado_linea[o_idx, slot] = 1
                            bar_quiebre[o_idx, slot] = i
                            ext_quiebre[o_idx, slot] = h[i]
                elif estado_linea[o_idx, slot] == 1:
                    # Throwback post-ruptura dentro de las 25 barras siguientes al quiebre
                    bq = bar_quiebre[o_idx, slot]
                    if i - bq > 25:
                        estado_linea[o_idx, slot] = 2
                    elif i > bq:
                        if lado_est == 1:
                            if h[i] >= y_i - 0.20 * atr and c[i] < y_i and c[i] < o[i]:
                                gat_hit = 2
                                e_exc_val = h[i]
                                estado_linea[o_idx, slot] = 2
                        else:
                            if l[i] <= y_i + 0.20 * atr and c[i] > y_i and c[i] > o[i]:
                                gat_hit = 2
                                e_exc_val = l[i]
                                estado_linea[o_idx, slot] = 2

                if gat_hit >= 0 and disp_ses[o_idx, gat_hit] == 0 and cnt < max_out:
                    disp_ses[o_idx, gat_hit] = 1
                    rng_b = max(h[i] - l[i], tick)
                    mecha_ok = (c[i] - l[i]) / rng_b >= 0.30 if c[i] >= o[i] else (h[i] - c[i]) / rng_b >= 0.30
                    absv = 1 if (mecha_ok and v[i] >= 1.15 * vol_med) else 0

                    # Contar gaps imán hacia el objetivo principal
                    dir_principal = lado_est if gat_hit == 0 else -lado_est
                    g_cam_val = 0.0
                    for g in range(MAX_GAPS):
                        if g_vivo[g] == 1:
                            g_mid = 0.5 * (g_lo[g] + g_hi[g])
                            if dir_principal == 1 and c[i] < g_mid <= c[i] + H_sw:
                                g_cam_val += 0.65
                            elif dir_principal == -1 and c[i] - H_sw <= g_mid < c[i]:
                                g_cam_val += 0.65

                    dif_ema = ema20 - ema60
                    if abs(dif_ema) < 0.20 * atr:
                        ema_st = 1
                    elif dif_ema * float(dir_principal) > 0.0:
                        ema_st = 2
                    else:
                        ema_st = 0

                    vwap_st = 1 if (vwap_now - c[i]) * float(dir_principal) > 0.0 else 0

                    out_k[cnt] = i
                    out_ord[cnt] = o_idx
                    out_gat[cnt] = gat_hit
                    out_lado[cnt] = dir_principal
                    out_y[cnt] = y_i
                    out_hs[cnt] = H_sw
                    out_eexc[cnt] = e_exc_val
                    out_enf[cnt] = enf_rel
                    out_absv[cnt] = absv
                    out_gtom[cnt] = g_tom_bar
                    out_gcam[cnt] = g_cam_val
                    out_ema[cnt] = ema_st
                    out_ang[cnt] = ang
                    out_vwap[cnt] = vwap_st
                    cnt += 1

    return (
        out_k[:cnt],
        out_ord[:cnt],
        out_gat[:cnt],
        out_lado[:cnt],
        out_y[:cnt],
        out_hs[:cnt],
        out_eexc[:cnt],
        out_enf[:cnt],
        out_absv[:cnt],
        out_gtom[:cnt],
        out_gcam[:cnt],
        out_ema[:cnt],
        out_ang[:cnt],
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

    res = _extraer_disparos_tori_nb(t, o, h, l, c, v, ses, tick)
    k = res[0]
    return pd.DataFrame(
        {
            "k": k,
            "ses": ses[k],
            "ord_piv": res[1],
            "gat": res[2],
            "lado": res[3],
            "y_lin": res[4],
            "H_sw": res[5],
            "E_exc": res[6],
            "enf_rel": res[7],
            "abs_vol": res[8],
            "g_tom": res[9],
            "g_cam": res[10],
            "ema_al": res[11],
            "ang_norm": res[12],
            "vwap_al": res[13],
        }
    )


def niveles(d, ej: tuple, ctx: dict):
    md, ent, tp_name, sl_name = ej
    k = int(d["k"])
    lado = int(d["lado"])
    H_sw = float(d["H_sw"])
    E_exc = float(d["E_exc"])
    tick = float(ctx["tick"])
    ck = float(ctx["c"][k])

    s = lado if md == "A_FAVOR_ESTRUCTURA" else -lado
    lim = 0 if ent == "CIERRE" else 2
    e = np.round(ck / tick) * tick

    mult_tp = 1.00 if tp_name == "SWING_100" else (0.65 if tp_name == "MID_65" else 0.45)
    tp_raw = e + float(s) * mult_tp * H_sw
    tp = np.round(tp_raw / tick) * tick
    if (tp - e) * float(s) < 2.0 * tick:
        tp = e + float(s) * 2.0 * tick

    dist_lin = max(abs(E_exc - e) + 2.0 * tick, 0.30 * H_sw) if md == "A_FAVOR_ESTRUCTURA" else 0.35 * H_sw
    if sl_name == "S_LINEA":
        sl_raw = e - float(s) * dist_lin
    else:
        dist_55 = 0.55 * H_sw
        if abs(dist_55 - dist_lin) < 2.0 * tick:
            dist_55 = dist_lin + 3.0 * tick
        sl_raw = e - float(s) * dist_55

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
    H_sw = D["H_sw"].to_numpy(np.float64)
    E_exc = D["E_exc"].to_numpy(np.float64)
    tick = float(ctx["tick"])
    ck = np.asarray(ctx["c"], dtype=np.float64)[k]

    s = (lado if md == "A_FAVOR_ESTRUCTURA" else -lado).astype(np.float64)
    lim = 0.0 if ent == "CIERRE" else 2.0
    e = np.round(ck / tick) * tick

    mult_tp = 1.00 if tp_name == "SWING_100" else (0.65 if tp_name == "MID_65" else 0.45)
    tp_raw = e + s * mult_tp * H_sw
    tp = np.round(tp_raw / tick) * tick
    tp = np.where((tp - e) * s < 2.0 * tick, e + s * 2.0 * tick, tp)

    dist_lin = np.maximum(np.abs(E_exc - e) + 2.0 * tick, 0.30 * H_sw) if md == "A_FAVOR_ESTRUCTURA" else 0.35 * H_sw
    if sl_name == "S_LINEA":
        sl_raw = e - s * dist_lin
    else:
        dist_55 = np.full(m, 0.55, dtype=np.float64) * H_sw
        dist_55 = np.where(np.abs(dist_55 - dist_lin) < 2.0 * tick, dist_lin + 3.0 * tick, dist_55)
        sl_raw = e - s * dist_55

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
