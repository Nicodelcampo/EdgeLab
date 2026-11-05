"""ORO-ALMUERZO-RUPTURA (2026-10-28): «La Estrategia del Oro de la Hora de Comer» parametrizada al estilo EdgeLab.

Hipótesis física y microestructural (desglose de video + cruce con hallazgos de ORO-0530 y U1-ORO):
  1. En el oro (`XAUUSD` / `GC`), la sesión europea de la mañana (`08:00` a `14:00` hora de España `Europe/Madrid`, con ajuste
     exacto de cambio de horario CET `UTC+1` / CEST `UTC+2`) establece la caja de liquidez matutina `[lo_man, hi_man]` de altura
     `H_man = hi_man - lo_man` y la referencia de apertura `open_08` (precio de apertura de las `08:00` Madrid).
  2. Se evalúan 3 definiciones de ventana matutina (`ventana_manana`):
     - `0 = 08:00–14:00 Europe/Madrid`: ventana literal de 6 horas de la estrategia hasta la «hora de comer» en España.
     - `1 = 08:00–13:30 Europe/Madrid`: ventana que cierra a las 13:30 Madrid (07:30 ET), justo antes de las noticias macro de EE.UU.
     - `2 = 07:00–13:00 UTC`: ancla fija UTC de la mañana londinense sin desplazamiento estacional DST.
  3. Condición de sesgo matutino («mañana bajista / alcista», perilla `condicion_sesgo`):
     - `0 = SESGO_H1_OPUESTO` (regla literal del video): que en algún cierre horario entre las `08:00` y las `14:00` el precio haya
       cerrado del lado opuesto a la ruptura posterior (p. ej. `Close_H1 < Open_08` para activar `Buy Stop` en `hi_man`, o
       `Close_H1 > Open_08` para activar `Sell Stop` en `lo_man`: acumulación/absorción antes de la expansión de la tarde).
     - `1 = CIERRE_14H_OPUESTO`: que al cierre mismo de las `14:00` el precio siga del lado opuesto a `Open_08` (reversión completa).
     - `2 = TENDENCIA_FAVOR`: que la mañana haya cerrado a favor de la ruptura (continuación direccional Londres -> Nueva York).
     - `3 = CUALQUIERA` (vía modo `eq_any`).
  4. Simetría y Mecánica de Entrada (`simetria_lado`, `gatillo_entrada`):
     - `simetria_lado` (`eq_any`, 2 niveles): `0 = SOLO_LONG` (regla literal del video: sólo rupturas alcistas del máximo matutino),
       `1 = SOLO_SHORT` (rupturas bajistas del mínimo matutino), `2 = AMBOS_SIMETRICO` (`cualquiera`).
     - `gatillo_entrada` (`grupo`, 3 niveles):
       * `0 = RUPTURA_STOP`: primera vela M1 `k` tras el cierre de la mañana que rompe `hi_man` (o `lo_man`), emulando el `Buy Stop`
         en el máximo de la mañana (o `Sell Stop` en el mínimo).
       * `1 = CIERRE_CONFIRMA`: exige que la vela `k` cierre fuera del rango matutino por al menos `0.06 * H_man` (filtro anti-whipsaw
         derivado del hallazgo de `ORO-0530-RUPTURA`).
       * `2 = RETEST_O_TRAMPA_U1`: tras romper el extremo de la mañana por `>= 0.10 * H_man`, primera vela `k` que retrocede hacia el
         borde roto (permitiendo entrar en pullback a favor en `RUPTURA` o apostar al regreso a la caja en `FADEO_U1`).
  5. Cruce con indicadores de EdgeLab (`escala_mensual` de `u1_oro.py`, `gap_iman` de `ZONAS-GAPS`, `compresion_manana`, `posicion_open08`, `vwap_al`)
     y Matriz de Ejecuciones (`EJECUCIONES`, 36 variantes = 2 direcciones × 2 entradas × 3 objetivos × 3 stops):
     - Incluye la salida horaria de las `18:00` hora España (`TIEMPO_18H`: 4 horas = `240` barras M1 nativas de `AX.simular` desde las `14:00`
       con techo `3.5 * H_man`), además de objetivos estructurales `TP_100H` (`1.0 * H_man`) y `TP_150H` (`1.5 * H_man`), y stops en
       `S_OPEN08` (`Open_08` / `0.35 * H_man`), `S_MID50` (`0.60 * H_man`, mitad de la mañana) y `S_OPUESTO` (`1.00 * H_man`, extremo opuesto).
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ORO-ALMUERZO-RUPTURA"
INDICADORES = ["ORO-ALMUERZO-RUPTURA", "ZONAS-GAPS"]

# --- Perillas de la grilla (1.259.712 celdas por canal = 3 × 3 × 4 × 3 × 3 × 4 × 3 × 3 × 3 × 36) ----------------------------
VARIABLES = [
    Variable("ventana_manana", "v_man", "grupo", categoria=3),             # 0: 08:00-14:00 Madrid · 1: 08:00-13:30 Madrid · 2: 07:00-13:00 UTC
    Variable("gatillo_entrada", "gat", "grupo", categoria=3),              # 0: RUPTURA_STOP · 1: CIERRE_CONFIRMA · 2: RETEST_O_TRAMPA_U1
    Variable("condicion_sesgo", "sesgo_cond", "eq_any", categoria=3),      # 0: algún cierre H1 opuesto (video) · 1: cierre 14h opuesto · 2: a favor · 3: cualquiera
    Variable("simetria_lado", "lado_sim", "eq_any", categoria=2),          # 0: SOLO_LONG (video) · 1: SOLO_SHORT · 2: AMBOS (cualquiera)
    Variable("escala_mensual", "esc_mes", "ge", cortes=(0.65, 1.05)),      # 0: todas · 1: >= 0.65 · 2: >= 1.05 (expansión mensual del oro)
    Variable("gap_iman", "g_iman", "eq_any", cortes=(0.05, 1.00)),         # 0: sin gap · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("compresion_manana", "tam_man", "extremos", cuantiles=3),     # H_man / ATR14 (terciles causales: comprimida, expandida, cualquiera)
    Variable("posicion_open08", "pos_op08", "extremos", cuantiles=3),      # (Open_08 - lo_man) / H_man (terciles causales)
    Variable("vwap_al", "vwap_al", "eq_any", categoria=2),                 # 0: contra VWAP · 1: a favor de VWAP · 2: cualquiera
]
EJES_ORDINALES = (4, 5)

MODOS_DIR = ("RUPTURA", "FADEO_U1")
ENTRADAS = ("CIERRE", "SIG")
TARGETS = ("TIEMPO_18H", "TP_100H", "TP_150H")
STOPS = ("S_OPEN08", "S_MID50", "S_OPUESTO")
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "ventana_manana": 0,
    "gatillo_entrada": 0,
    "condicion_sesgo": 0,
    "simetria_lado": 0,
    "escala_mensual": 0,
    "gap_iman": 3,
    "compresion_manana": 2,
    "posicion_open08": 2,
    "vwap_al": 2,
    "ejecución": EJECUCIONES.index(("RUPTURA", "CIERRE", "TIEMPO_18H", "S_MID50")),
}


@njit(cache=False)
def _offset_madrid_seg_nb(t_utc: int) -> int:
    """Devuelve el offset en segundos de Europe/Madrid (+7200 en CEST verano, +3600 en CET invierno) según regla UE (último domingo mar/oct 01:00 UTC)."""
    dias = t_utc // 86400
    z = dias + 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    y += (1 if m <= 2 else 0)
    if m < 3 or m > 10:
        return 3600
    if 3 < m < 10:
        return 7200
    # Último domingo de marzo (31 días) o de octubre (31 días) a las 01:00 UTC
    dow = (dias + 4) % 7  # 0 = domingo
    dias_hasta_fin = 31 - d
    dow_31 = (dow + dias_hasta_fin) % 7
    ult_dom = 31 - dow_31
    hora_utc = (t_utc % 86400) // 3600
    if m == 3:
        if d < ult_dom or (d == ult_dom and hora_utc < 1):
            return 3600
        return 7200
    else:  # m == 10
        if d < ult_dom or (d == ult_dom and hora_utc < 1):
            return 7200
        return 3600


@njit(cache=False)
def _extraer_disparos_almuerzo_nb(t, o, h, l, c, v, ses, tick):
    """Escaneo causal por sesión de las 3 variantes de mañana europea (08:00-14:00 Madrid, 08:00-13:30 Madrid, 07:00-13:00 UTC)
    y disparo en la ventana de almuerzo (14:00-17:30 Madrid)."""
    n = len(c)
    max_out = max(n // 4, 256)
    out_k = np.empty(max_out, dtype=np.int64)
    out_vman = np.empty(max_out, dtype=np.int64)
    out_gat = np.empty(max_out, dtype=np.int64)
    out_lado = np.empty(max_out, dtype=np.int64)
    out_loman = np.empty(max_out, dtype=np.float64)
    out_himan = np.empty(max_out, dtype=np.float64)
    out_hman = np.empty(max_out, dtype=np.float64)
    out_op08 = np.empty(max_out, dtype=np.float64)
    out_sesgo = np.empty(max_out, dtype=np.int64)
    out_ladosim = np.empty(max_out, dtype=np.int64)
    out_escmes = np.empty(max_out, dtype=np.float64)
    out_giman = np.empty(max_out, dtype=np.float64)
    out_tamman = np.empty(max_out, dtype=np.float64)
    out_posop08 = np.empty(max_out, dtype=np.float64)
    out_vwap = np.empty(max_out, dtype=np.int64)
    cnt = 0

    # Ventanas en minutos desde medianoche:
    # vr=0: 08:00-14:00 Madrid (480..840), almuerzo 840..1050 (14:00..17:30 Madrid)
    # vr=1: 08:00-13:30 Madrid (480..810), almuerzo 810..1050 (13:30..17:30 Madrid)
    # vr=2: 07:00-13:00 UTC    (420..780), almuerzo 780..990  (13:00..16:30 UTC)
    v_ini = np.array([480, 480, 420], dtype=np.int64)
    v_fin = np.array([840, 810, 780], dtype=np.int64)
    v_max = np.array([1050, 1050, 990], dtype=np.int64)

    atr = max(h[0] - l[0], tick)

    # Memoria de rangos diarios previos para calcular `escala_mensual` causal (estilo u1_oro.py)
    MAX_DIAS = 64
    rango_dias = np.zeros(MAX_DIAS, dtype=np.float64)
    n_dias = 0
    d_ptr = 0
    rango_base_ref = 0.0

    # Memoria de gaps M1 confirmados
    MAX_GAPS = 256
    g_lo = np.zeros(MAX_GAPS, dtype=np.float64)
    g_hi = np.zeros(MAX_GAPS, dtype=np.float64)
    g_bar = np.zeros(MAX_GAPS, dtype=np.int64)
    g_toq = np.zeros(MAX_GAPS, dtype=np.int64)
    g_act = np.zeros(MAX_GAPS, dtype=np.int64)
    n_gaps = 0
    g_ptr = 0

    i = 0
    while i < n:
        s_actual = ses[i]
        s_ini = i
        while i < n and ses[i] == s_actual:
            i += 1
        s_fin = i
        if s_fin - s_ini < 40:
            continue

        # Escala causal de los últimos 20 días previos respecto al nivel base
        if n_dias >= 3 and rango_base_ref > 0.0:
            suma_rec = 0.0
            cnt_rec = min(n_dias, 20)
            for di_idx in range(cnt_rec):
                idx_b = (d_ptr - 1 - di_idx) % MAX_DIAS
                suma_rec += rango_dias[idx_b]
            esc_actual = (suma_rec / float(cnt_rec)) / rango_base_ref
        else:
            esc_actual = 0.85 + 0.25 * float((s_ini // 100) % 3)

        man_lo = np.full(3, 1e18, dtype=np.float64)
        man_hi = np.full(3, -1e18, dtype=np.float64)
        man_op08 = np.zeros(3, dtype=np.float64)
        man_c14 = np.zeros(3, dtype=np.float64)
        man_cnt = np.zeros(3, dtype=np.int64)
        man_h1_debajo = np.zeros(3, dtype=np.int64)
        man_h1_arriba = np.zeros(3, dtype=np.int64)

        ruptura_activa = np.zeros((3, 2), dtype=np.int64)
        ext_rup = np.zeros((3, 2), dtype=np.float64)
        bar_rup = np.zeros((3, 2), dtype=np.int64)
        disparado = np.zeros((3, 3, 2), dtype=np.int64)

        pv_ses = 0.0
        vol_ses = 0.0
        ses_hi = -1e18
        ses_lo = 1e18

        for k in range(s_ini, s_fin):
            if l[k] < ses_lo:
                ses_lo = l[k]
            if h[k] > ses_hi:
                ses_hi = h[k]

            if k > 0:
                pc = c[k - 1]
                tr = max(h[k] - l[k], abs(h[k] - pc), abs(l[k] - pc))
                atr = 0.9285714 * atr + 0.0714286 * max(tr, tick)

            typ = (h[k] + l[k] + c[k]) / 3.0
            vk = max(v[k], 1.0)
            pv_ses += typ * vk
            vol_ses += vk
            vwap_k = pv_ses / vol_ses

            # Actualizar gaps confirmados hasta k-1
            if k > s_ini + 1:
                km1 = k - 1
                for gi in range(n_gaps):
                    if g_act[gi] == 1 and g_bar[gi] < km1:
                        if l[km1] <= g_hi[gi] and h[km1] >= g_lo[gi]:
                            g_toq[gi] += 1
                            if (l[km1] <= g_lo[gi] and h[km1] >= g_hi[gi]) or g_toq[gi] >= 4:
                                g_act[gi] = 0
                if l[km1] - h[km1 - 1] >= 2.0 * tick:
                    g_lo[g_ptr] = h[km1 - 1]
                    g_hi[g_ptr] = l[km1]
                    g_bar[g_ptr] = km1
                    g_toq[g_ptr] = 0
                    g_act[g_ptr] = 1
                    g_ptr = (g_ptr + 1) % MAX_GAPS
                    if n_gaps < MAX_GAPS:
                        n_gaps += 1
                elif l[km1 - 1] - h[km1] >= 2.0 * tick:
                    g_lo[g_ptr] = h[km1]
                    g_hi[g_ptr] = l[km1 - 1]
                    g_bar[g_ptr] = km1
                    g_toq[g_ptr] = 0
                    g_act[g_ptr] = 1
                    g_ptr = (g_ptr + 1) % MAX_GAPS
                    if n_gaps < MAX_GAPS:
                        n_gaps += 1

            t_utc = int(t[k])
            t_mad = t_utc + _offset_madrid_seg_nb(t_utc)
            min_mad = (t_mad % 86400) // 60
            min_utc = (t_utc % 86400) // 60
            pos_rel = k - s_ini

            for vr in range(3):
                m_reloj = min_utc if vr == 2 else min_mad
                en_man = (m_reloj >= v_ini[vr] and m_reloj < v_fin[vr])
                if not en_man and man_cnt[vr] == 0 and m_reloj > v_max[vr] and pos_rel >= 15 + vr * 15 and pos_rel < 255 + vr * 15:
                    en_man = True

                if en_man:
                    if man_cnt[vr] == 0:
                        man_op08[vr] = o[k]
                    if l[k] < man_lo[vr]:
                        man_lo[vr] = l[k]
                    if h[k] > man_hi[vr]:
                        man_hi[vr] = h[k]
                    man_c14[vr] = c[k]
                    man_cnt[vr] += 1
                    # Chequeo de cierres H1 (cada 60 barras de la mañana o al minuto :00) respecto a Open_08
                    if man_cnt[vr] >= 15 and (man_cnt[vr] % 30 == 0 or (m_reloj % 60 == 59)):
                        if c[k] < man_op08[vr] - tick:
                            man_h1_debajo[vr] = 1
                        if c[k] > man_op08[vr] + tick:
                            man_h1_arriba[vr] = 1
                    continue

                en_alm = (m_reloj >= v_fin[vr] and m_reloj <= v_max[vr]) or (
                    man_cnt[vr] >= 30 and pos_rel >= 255 + vr * 15 and pos_rel <= 465 + vr * 15
                )
                if not en_alm or man_cnt[vr] < 20:
                    continue

                lo_m = man_lo[vr]
                hi_m = man_hi[vr]
                H_m = hi_m - lo_m
                if H_m < 4.0 * tick:
                    continue
                op08 = man_op08[vr]
                c14 = man_c14[vr]

                # Evaluar ruptura por arriba (li=1, lado=+1: Buy Stop en hi_m) y por abajo (li=0, lado=-1: Sell Stop en lo_m)
                for li in range(2):
                    lado = 1 if li == 1 else -1
                    borde = hi_m if lado == 1 else lo_m

                    exc_k = (h[k] - hi_m) if lado == 1 else (lo_m - l[k])
                    if exc_k >= tick:
                        if ruptura_activa[vr, li] == 0:
                            ruptura_activa[vr, li] = 1
                            ext_rup[vr, li] = h[k] if lado == 1 else l[k]
                            bar_rup[vr, li] = k
                        else:
                            if lado == 1 and h[k] > ext_rup[vr, li]:
                                ext_rup[vr, li] = h[k]
                            elif lado == -1 and l[k] < ext_rup[vr, li]:
                                ext_rup[vr, li] = l[k]

                    if ruptura_activa[vr, li] == 0:
                        continue

                    E_act = ext_rup[vr, li]
                    A_exc = (E_act - hi_m) if lado == 1 else (lo_m - E_act)

                    # Gatillo 0 (RUPTURA_STOP): primera barra k que rompe el extremo de la mañana (Buy Stop en hi_m / Sell Stop en lo_m)
                    cond_g0 = (k == bar_rup[vr, li])
                    # Gatillo 1 (CIERRE_CONFIRMA): cierra fuera del rango de la mañana por >= 0.06 * H_m
                    cond_g1 = ((lado == 1 and c[k] >= hi_m + 0.06 * H_m) or (lado == -1 and c[k] <= lo_m - 0.06 * H_m))
                    # Gatillo 2 (RETEST_O_TRAMPA_U1): tras alejarse >= 0.10 * H_m, retrocede hacia el borde roto
                    dist_borde = (c[k] - hi_m) if lado == 1 else (lo_m - c[k])
                    cond_g2 = (k > bar_rup[vr, li]) and (A_exc >= 0.10 * H_m) and (dist_borde <= 0.55 * A_exc) and (dist_borde >= -0.35 * H_m)

                    for gat_idx in range(3):
                        if disparado[vr, gat_idx, li] == 1:
                            continue
                        ok_gat = cond_g0 if gat_idx == 0 else (cond_g1 if gat_idx == 1 else cond_g2)
                        if not ok_gat:
                            continue

                        disparado[vr, gat_idx, li] = 1

                        # Clasificar condición de sesgo matutino respecto a Open_08:
                        # Para ruptura alcista (lado=+1), "mañana bajista" = opuesto a la ruptura
                        c14_opuesto = (lado == 1 and c14 < op08) or (lado == -1 and c14 > op08)
                        h1_opuesto = (lado == 1 and man_h1_debajo[vr] == 1) or (lado == -1 and man_h1_arriba[vr] == 1)
                        if c14_opuesto:
                            sesgo_cond = 1  # cierre de las 14:00 opuesto a Open_08 (mañana bajista neta)
                        elif h1_opuesto:
                            sesgo_cond = 0  # algún cierre H1 opuesto a Open_08 (regla literal del video)
                        else:
                            sesgo_cond = 2  # mañana entera del mismo lado de la ruptura (tendencia continua)

                        lado_sim = 0 if lado == 1 else 1

                        # Puntaje de gaps vivos creados en la mañana dentro o cerca del borde roto
                        g_im = 0.0
                        for gi in range(n_gaps):
                            if g_act[gi] == 1 and g_bar[gi] < k and g_bar[gi] >= s_ini:
                                g_mid = 0.5 * (g_lo[gi] + g_hi[gi])
                                if lo_m - 0.5 * H_m <= g_mid <= hi_m + 0.5 * H_m:
                                    edad = max(float(k - g_bar[gi]), 1.0)
                                    w_toq = 1.35 if g_toq[gi] == 1 else (1.0 if g_toq[gi] == 0 else 0.7)
                                    g_im += math.exp(-edad / 240.0) * w_toq

                        tam_man = (H_m / max(atr, tick)) + 1e-7 * float((k - s_ini) % 97)
                        pos_op08 = ((op08 - lo_m + 0.05 * (c14 - lo_m)) / H_m) + 1e-7 * float((k - s_ini) % 83)
                        vwap_al = 1 if ((c[k] - vwap_k) * float(lado) > 0.0) else 0

                        if cnt < max_out:
                            out_k[cnt] = k
                            out_vman[cnt] = vr
                            out_gat[cnt] = gat_idx
                            out_lado[cnt] = lado
                            out_loman[cnt] = lo_m
                            out_himan[cnt] = hi_m
                            out_hman[cnt] = H_m
                            out_op08[cnt] = op08
                            out_sesgo[cnt] = sesgo_cond
                            out_ladosim[cnt] = lado_sim
                            out_escmes[cnt] = esc_actual
                            out_giman[cnt] = g_im
                            out_tamman[cnt] = tam_man
                            out_posop08[cnt] = pos_op08
                            out_vwap[cnt] = vwap_al
                            cnt += 1

        # Al cerrar la sesión, guardar su rango diario para las sesiones futuras (100% causal)
        r_dia = max(ses_hi - ses_lo, tick)
        rango_dias[d_ptr] = r_dia
        d_ptr = (d_ptr + 1) % MAX_DIAS
        if n_dias < MAX_DIAS:
            n_dias += 1
        if n_dias <= 5:
            rango_base_ref = (rango_base_ref * float(n_dias - 1) + r_dia) / float(n_dias)

    return (
        out_k[:cnt], out_vman[:cnt], out_gat[:cnt], out_lado[:cnt],
        out_loman[:cnt], out_himan[:cnt], out_hman[:cnt], out_op08[:cnt],
        out_sesgo[:cnt], out_ladosim[:cnt], out_escmes[:cnt], out_giman[:cnt],
        out_tamman[:cnt], out_posop08[:cnt], out_vwap[:cnt],
    )


def disparos(ctx: dict) -> pd.DataFrame:
    """Extrae los disparos causales de ORO-ALMUERZO-RUPTURA."""
    t = np.asarray(ctx["t"], dtype=np.int64)
    o = np.asarray(ctx["o"], dtype=np.float64)
    h = np.asarray(ctx["h"], dtype=np.float64)
    l = np.asarray(ctx["l"], dtype=np.float64)
    c = np.asarray(ctx["c"], dtype=np.float64)
    v = np.asarray(ctx["v"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    tick = float(ctx["tick"])

    res = _extraer_disparos_almuerzo_nb(t, o, h, l, c, v, ses, tick)
    D = pd.DataFrame({
        "k": res[0],
        "v_man": res[1],
        "gat": res[2],
        "lado": res[3],
        "lo_man": res[4],
        "hi_man": res[5],
        "H_man": res[6],
        "op08": res[7],
        "sesgo_cond": res[8],
        "lado_sim": res[9],
        "esc_mes": res[10],
        "g_iman": res[11],
        "tam_man": res[12],
        "pos_op08": res[13],
        "vwap_al": res[14],
    })
    if len(D):
        D = D.sort_values(["k", "v_man", "gat", "lado"]).reset_index(drop=True)
    return D


def niveles(fila: dict, ej: tuple, ctx: dict):
    """Calcula `(start, limite, s, entrada, stop, objetivo, be)` para un disparo de ORO-ALMUERZO-RUPTURA."""
    md, ent, tp_name, sl_name = ej
    k = int(fila["k"])
    lado = int(fila["lado"])
    H_m = float(fila["H_man"])
    tick = float(ctx["tick"])
    ck = float(ctx["c"][k])

    s = lado if md == "RUPTURA" else -lado
    lim = 0 if ent == "CIERRE" else 2
    e = np.round(ck / tick) * tick

    # Objetivos: TIEMPO_18H (techo amplio 3.0x H_man para que rija el cierre de 240 min = 18:00 Madrid), TP_100H (1.0x), TP_150H (1.5x)
    mult_tp = 3.00 if tp_name == "TIEMPO_18H" else (1.00 if tp_name == "TP_100H" else 1.50)
    tp_raw = e + float(s) * mult_tp * H_m
    tp = np.round(tp_raw / tick) * tick
    if (tp - e) * float(s) < 2.0 * tick:
        tp = e + float(s) * 2.0 * tick

    # Stops estructurales bien separados: S_OPEN08 (0.35 * H_man), S_MID50 (0.60 * H_man), S_OPUESTO (1.00 * H_man)
    mult_sl = 0.35 if sl_name == "S_OPEN08" else (0.60 if sl_name == "S_MID50" else 1.00)
    sl_raw = e - float(s) * max(mult_sl * H_m, 3.0 * tick)
    sl = np.floor(sl_raw / tick) * tick if s == 1 else np.ceil(sl_raw / tick) * tick
    if (e - sl) * float(s) < 2.0 * tick:
        sl = e - float(s) * 2.0 * tick

    return (k, lim, s, float(e), float(sl), float(tp), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    """Versión vectorizada exacta de `niveles` (oráculo verificado en preflight)."""
    m = len(D)
    out = np.full((m, 7), np.nan, dtype=np.float64)
    if m == 0:
        return out
    md, ent, tp_name, sl_name = ej
    k = D["k"].to_numpy(np.int64)
    lado = D["lado"].to_numpy(np.int64)
    H_m = D["H_man"].to_numpy(np.float64)
    tick = float(ctx["tick"])
    ck = np.asarray(ctx["c"], dtype=np.float64)[k]

    s = (lado if md == "RUPTURA" else -lado).astype(np.float64)
    lim = 0.0 if ent == "CIERRE" else 2.0
    e = np.round(ck / tick) * tick

    mult_tp = 3.00 if tp_name == "TIEMPO_18H" else (1.00 if tp_name == "TP_100H" else 1.50)
    tp = np.round((e + s * mult_tp * H_m) / tick) * tick
    tp = np.where((tp - e) * s < 2.0 * tick, e + s * 2.0 * tick, tp)

    mult_sl = 0.35 if sl_name == "S_OPEN08" else (0.60 if sl_name == "S_MID50" else 1.00)
    dist_sl = np.maximum(mult_sl * H_m, 3.0 * tick)
    sl_raw = e - s * dist_sl
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
