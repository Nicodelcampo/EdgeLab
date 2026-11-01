"""OTR-930-SWEEP (2026-10-28): «9:30 Cheat Code / OTR Range Breakout Return» parametrizada al estilo EdgeLab.

Hipótesis física y microestructural (desglose de video RoboQuant + cruce con primitivas EdgeLab):
  1. En los futuros de índices estadounidenses (`MNQ`/`NQ` y `MES`/`ES`), la hora previa a la apertura de contado de Nueva York
     define un rango de referencia pre-market `[lo_rng, hi_rng]` de altura `H_rng = hi_rng - lo_rng`. Se evalúan 3 definiciones
     de ventana pre-market (`ventana_rango` en hora `America/New_York` con ajuste DST exacto EDT/EST):
     - `0 = 08:12–09:12 ET`: ventana literal del setup «9:30 Cheat Code / OTR Range Breakout Return».
     - `1 = 08:00–09:15 ET`: ventana pre-market extendida (incluye apertura de las 08:00 ET y dato macro de las 08:30 ET).
     - `2 = 08:30–09:29 ET`: ventana post-noticia macro 08:30 ET hasta el minuto previo al toque de campana 09:30 ET.
  2. A partir de la apertura de contado (`09:30 ET`), el flujo minorista e institucional barre uno de los extremos del rango
     (`High > hi_rng` -> `lado_barrido = +1`; `Low < lo_rng` -> `lado_barrido = -1`).
  3. Se parametrizan 3 mecánicas causales de disparo tras el barrido (`gatillo_retorno`):
     - `0 = REINGRESO_CIERRE`: tras barrer `hi_rng` o `lo_rng`, primera vela M1 `k` que vuelve a cerrar dentro de `[lo_rng, hi_rng]`
       (confirmación de falso quiebre / trampa de apertura).
     - `1 = EXCURSION_U1_25`: tras una excursión exterior `A_exc >= 0.12 * H_rng`, el precio gira desde el extremo `E_exc` y
       completa el primer 25% de regreso hacia el borde barrido (`D_exc <= 0.75 * A_exc`, mecánica U1).
     - `2 = RECHAZO_MECHA_SWEEP`: la propia vela `k` que marca o extiende el barrido exterior rechaza en la misma barra y cierra
       dejando mecha de absorción >= 30% del rango de la vela hacia el interior del rango.
  4. Cruce con indicadores y hallazgos de EdgeLab (`VARIABLES`):
     - `excursion_rel` (`ge`, cortes `0.08, 0.20`): excursión máxima fuera del rango `A_exc / H_rng`.
     - `sweep_gate_k36` (`eq_any`, 2 niveles): firma `SweepGate` de `k36` (mecha de rechazo >= 35% + volumen relativo >= 1.15x).
     - `gap_barrido` (`eq_any`, cortes `0.05, 1.0`): puntaje continuo `ZONAS-GAPS` de gaps previos barridos/mitigados en la excursión.
     - `gap_iman_rango` (`eq_any`, cortes `0.05, 1.0`): puntaje continuo `ZONAS-GAPS` de gaps vivos dentro del rango `[lo_rng, hi_rng]`
       que actúan como imán hacia el extremo opuesto.
     - `corredor_ema` (`eq_any`, 3 niveles): alineación del corredor `EMA(20)/EMA(60)` (`EmaCorridorTrendVolW2`) con el retorno.
     - `tamano_rango` (`extremos`, 3 terciles): altura relativa `H_rng / ATR14` en la apertura.
     - `vwap_al` (`eq_any`, 2 niveles): si el `VWAP` de la sesión está del lado del objetivo (imán gravitacional) o detrás.
  5. Matriz de Ejecuciones (`EJECUCIONES`, 24 variantes = 2 direcciones × 2 entradas × 3 objetivos × 2 stops):
     - Dirección: `RETORNO` (apuesta al relleno del rango hacia el extremo opuesto, setup original) vs `CONTINUACION` (control).
     - Entrada: `CIERRE` (`limite=0`) vs `SIG` (`limite=2`, primer tick de la barra siguiente).
     - Objetivo: `OPUESTO_100` (`1.00 * H_rng`, el otro lado del rango `08:12–09:12 ET` como en el video), `POC_65` (`0.65 * H_rng`,
       variante de alto Win Rate al nodo central/VA del rango), `MID_50` (`0.50 * H_rng`, equilibrio del 50%).
     - Stop: `S_SWEEP` (detrás del extremo barrido `E_exc`, con piso `0.30 * H_rng`) vs `S_RANGO55` (`0.55 * H_rng` estructural).
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

NOMBRE = "OTR-930-SWEEP"
INDICADORES = ["OTR-930-SWEEP", "ZONAS-GAPS", "EmaCorridorTrendVolW2"]

# --- Perillas de la grilla (1.119.744 celdas por canal = 3 × 3 × 3 × 3 × 4 × 4 × 4 × 3 × 3 × 24) ----------------------------
VARIABLES = [
    Variable("ventana_rango", "v_rng", "grupo", categoria=3),              # 0: 08:12-09:12 ET · 1: 08:00-09:15 ET · 2: 08:30-09:29 ET
    Variable("gatillo_retorno", "gat", "grupo", categoria=3),              # 0: REINGRESO_CIERRE · 1: EXCURSION_U1_25 · 2: RECHAZO_MECHA_SWEEP
    Variable("excursion_rel", "exc_rel", "ge", cortes=(0.08, 0.20)),       # 0: >= 0 · 1: >= 0.08 H_rng · 2: >= 0.20 H_rng
    Variable("sweep_gate_k36", "sw_gate", "eq_any", categoria=2),          # 0: sin SweepGate · 1: con SweepGate k36 · 2: cualquiera
    Variable("gap_barrido", "g_tom", "eq_any", cortes=(0.05, 1.00)),       # 0: sin gap · 1: 1 gap · 2: multi-gap · 3: cualquiera
    Variable("gap_iman_rango", "g_cam", "eq_any", cortes=(0.05, 1.00)),    # 0: sin imán · 1: 1 gap imán · 2: multi-imán · 3: cualquiera
    Variable("corredor_ema", "ema_al", "eq_any", categoria=3),             # 0: contra EMA20/60 · 1: comprimido · 2: a favor · 3: cualquiera
    Variable("tamano_rango", "tam_rng", "extremos", cuantiles=3),          # H_rng / ATR14 (terciles causales: estrecho, amplio, cualquiera)
    Variable("vwap_al", "vwap_al", "eq_any", categoria=2),                 # 0: lejos de VWAP · 1: hacia VWAP (imán) · 2: cualquiera
]
EJES_ORDINALES = (2, 4, 5)

MODOS_DIR = ("RETORNO", "CONTINUACION")
ENTRADAS = ("CIERRE", "SIG")
TARGETS = ("OPUESTO_100", "POC_65", "MID_50")
STOPS = ("S_SWEEP", "S_RANGO55")
EJECUCIONES = [(md, ent, tp, sl) for md in MODOS_DIR for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "ventana_rango": 0,
    "gatillo_retorno": 0,
    "excursion_rel": 0,
    "sweep_gate_k36": 2,
    "gap_barrido": 3,
    "gap_iman_rango": 3,
    "corredor_ema": 3,
    "tamano_rango": 2,
    "vwap_al": 2,
    "ejecución": EJECUCIONES.index(("RETORNO", "CIERRE", "OPUESTO_100", "S_SWEEP")),
}


@njit(cache=False)
def _es_bisiesto(y: int) -> int:
    return 1 if ((y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)) else 0


@njit(cache=False)
def _offset_ny_seg_nb(t_utc: int) -> int:
    """Devuelve el offset en segundos de America/New_York (-14400 en EDT, -18000 en EST) para un timestamp UTC."""
    dias = t_utc // 86400
    # Algoritmo civil (Howard Hinnant) desde 1970-01-01
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
    if m < 3 or m > 11:
        return -18000
    if 3 < m < 11:
        return -14400
    # Día de la semana: 1970-01-01 fue jueves (4); 0 = domingo .. 6 = sábado
    dow = (dias + 4) % 7
    # Primer domingo del mes:
    dom1 = ((d - dow - 1) % 7) + 1
    hora_utc = (t_utc % 86400) // 3600
    if m == 3:
        dom2 = dom1 + 7
        if d < dom2 or (d == dom2 and hora_utc < 7):
            return -18000
        return -14400
    else:  # m == 11 (primer domingo de noviembre a las 06:00 UTC)
        if d < dom1 or (d == dom1 and hora_utc < 6):
            return -14400
        return -18000


@njit(cache=False)
def _extraer_disparos_otr_nb(t, o, h, l, c, v, ses, tick):
    """Escaneo causal por sesión de las 3 ventanas pre-market NY y los 3 gatillos post-09:30 ET."""
    n = len(c)
    max_out = max(n // 4, 256)
    out_k = np.empty(max_out, dtype=np.int64)
    out_vrng = np.empty(max_out, dtype=np.int64)
    out_gat = np.empty(max_out, dtype=np.int64)
    out_lado = np.empty(max_out, dtype=np.int64)
    out_lo = np.empty(max_out, dtype=np.float64)
    out_hi = np.empty(max_out, dtype=np.float64)
    out_hrng = np.empty(max_out, dtype=np.float64)
    out_eexc = np.empty(max_out, dtype=np.float64)
    out_excrel = np.empty(max_out, dtype=np.float64)
    out_swgate = np.empty(max_out, dtype=np.int64)
    out_gtom = np.empty(max_out, dtype=np.float64)
    out_gcam = np.empty(max_out, dtype=np.float64)
    out_ema = np.empty(max_out, dtype=np.int64)
    out_tam = np.empty(max_out, dtype=np.float64)
    out_vwap = np.empty(max_out, dtype=np.int64)
    cnt = 0

    # Ventanas en minutos del día ET: (inicio_min, fin_min, apertura_min, cierre_busqueda_min)
    v_ini = np.array([492, 480, 510], dtype=np.int64)   # 08:12, 08:00, 08:30 ET
    v_fin = np.array([552, 555, 570], dtype=np.int64)   # 09:12, 09:15, 09:30 ET
    v_open = 570                                        # 09:30 ET
    v_max_open = 750                                    # 12:30 ET

    # Estado causal global (ATR14, EMA20, EMA60, y memoria de gaps M1 confirmados)
    atr = max(h[0] - l[0], tick)
    ema20 = c[0]
    ema60 = c[0]
    a20 = 2.0 / 21.0
    a60 = 2.0 / 61.0

    MAX_GAPS = 256
    g_lo = np.zeros(MAX_GAPS, dtype=np.float64)
    g_hi = np.zeros(MAX_GAPS, dtype=np.float64)
    g_bar = np.zeros(MAX_GAPS, dtype=np.int64)
    g_toq = np.zeros(MAX_GAPS, dtype=np.int64)
    g_act = np.zeros(MAX_GAPS, dtype=np.int64)
    n_gaps = 0
    g_ptr = 0

    vol_ses_prev = 100.0
    i = 0
    while i < n:
        s_actual = ses[i]
        s_ini = i
        while i < n and ses[i] == s_actual:
            i += 1
        s_fin = i
        if s_fin - s_ini < 30:
            continue

        # Estado por cada una de las 3 ventanas pre-market dentro de esta sesión
        rng_lo = np.full(3, 1e18, dtype=np.float64)
        rng_hi = np.full(3, -1e18, dtype=np.float64)
        rng_cnt = np.zeros(3, dtype=np.int64)

        # Para cada (v_rng, lado_barrido in {0: abajo (-1), 1: arriba (+1)}):
        # seguimiento de excursión exterior después de las 09:30 ET
        barrido_activo = np.zeros((3, 2), dtype=np.int64)
        ext_px = np.zeros((3, 2), dtype=np.float64)
        bar_inicio_sw = np.zeros((3, 2), dtype=np.int64)
        gtom_acc = np.zeros((3, 2), dtype=np.float64)
        disparado = np.zeros((3, 3, 2), dtype=np.int64)  # (v_rng, gat, lado_idx)

        pv_ses = 0.0
        vol_ses = 0.0

        for k in range(s_ini, s_fin):
            # Actualizar ATR, EMA20, EMA60, VWAP de forma estrictamente causal hasta k
            if k > 0:
                pc = c[k - 1]
                tr = max(h[k] - l[k], abs(h[k] - pc), abs(l[k] - pc))
                atr = 0.9285714 * atr + 0.0714286 * max(tr, tick)
                ema20 = a20 * c[k] + (1.0 - a20) * ema20
                ema60 = a60 * c[k] + (1.0 - a60) * ema60

            typ = (h[k] + l[k] + c[k]) / 3.0
            vk = max(v[k], 1.0)
            pv_ses += typ * vk
            vol_ses += vk
            vwap_k = pv_ses / vol_ses

            # Actualizar mitigación/toques de gaps previos con la vela k-1 antes de evaluar k, y registrar gap en k-1
            if k > s_ini + 1:
                km1 = k - 1
                # Mitigación / toque en km1 de gaps nacidos antes de km1
                for gi in range(n_gaps):
                    if g_act[gi] == 1 and g_bar[gi] < km1:
                        if l[km1] <= g_hi[gi] and h[km1] >= g_lo[gi]:
                            g_toq[gi] += 1
                            if (l[km1] <= g_lo[gi] and h[km1] >= g_hi[gi]) or g_toq[gi] >= 4:
                                g_act[gi] = 0
                # Detectar nuevo gap confirmado (3 barras: km1-1 a km1)
                if km1 >= s_ini + 1:
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

            # Hora local America/New_York
            t_et = int(t[k]) + _offset_ny_seg_nb(int(t[k]))
            min_et = (t_et % 86400) // 60
            pos_rel = k - s_ini

            for vr in range(3):
                # Acumular rango de referencia pre-market (o fallback posicional si la sesión empieza fuera de horario estándar)
                en_rango = (min_et >= v_ini[vr] and min_et < v_fin[vr])
                if not en_rango and rng_cnt[vr] == 0 and min_et > v_max_open and pos_rel >= 10 + vr * 10 and pos_rel < 70 + vr * 10:
                    en_rango = True
                if en_rango:
                    if l[k] < rng_lo[vr]:
                        rng_lo[vr] = l[k]
                    if h[k] > rng_hi[vr]:
                        rng_hi[vr] = h[k]
                    rng_cnt[vr] += 1
                    continue

                # Evaluar ventana operativa post-09:30 ET
                post_open = (min_et >= v_open and min_et <= v_max_open) or (rng_cnt[vr] >= 15 and pos_rel >= 75 + vr * 10 and pos_rel <= 320)
                if not post_open or rng_cnt[vr] < 10:
                    continue

                lo_r = rng_lo[vr]
                hi_r = rng_hi[vr]
                H_r = hi_r - lo_r
                if H_r < 4.0 * tick:
                    continue

                # Revisar ambos lados de barrido: li=1 (arriba: High > hi_r, fade short s=-1) y li=0 (abajo: Low < lo_r, fade long s=+1)
                for li in range(2):
                    lado = 1 if li == 1 else -1
                    borde = hi_r if lado == 1 else lo_r
                    opuesto = lo_r if lado == 1 else hi_r

                    # ¿La barra k inicia o extiende el barrido fuera del borde?
                    excursion_k = (h[k] - hi_r) if lado == 1 else (lo_r - l[k])
                    if excursion_k >= tick:
                        if barrido_activo[vr, li] == 0:
                            barrido_activo[vr, li] = 1
                            ext_px[vr, li] = h[k] if lado == 1 else l[k]
                            bar_inicio_sw[vr, li] = k
                            gtom_acc[vr, li] = 0.0
                        else:
                            if lado == 1 and h[k] > ext_px[vr, li]:
                                ext_px[vr, li] = h[k]
                            elif lado == -1 and l[k] < ext_px[vr, li]:
                                ext_px[vr, li] = l[k]

                        # Acumular puntaje de gaps barridos en esta vela durante la excursión exterior
                        for gi in range(n_gaps):
                            if g_act[gi] == 1 and g_bar[gi] < bar_inicio_sw[vr, li]:
                                if lado == 1 and g_hi[gi] > hi_r and h[k] >= g_lo[gi] and l[k] <= g_hi[gi]:
                                    edad = max(float(k - g_bar[gi]), 1.0)
                                    w_toq = 1.35 if g_toq[gi] == 1 else (1.0 if g_toq[gi] == 0 else 0.7)
                                    gtom_acc[vr, li] += math.exp(-edad / 180.0) * w_toq
                                elif lado == -1 and g_lo[gi] < lo_r and l[k] <= g_hi[gi] and h[k] >= g_lo[gi]:
                                    edad = max(float(k - g_bar[gi]), 1.0)
                                    w_toq = 1.35 if g_toq[gi] == 1 else (1.0 if g_toq[gi] == 0 else 0.7)
                                    gtom_acc[vr, li] += math.exp(-edad / 180.0) * w_toq

                    if barrido_activo[vr, li] == 0:
                        continue

                    E_actual = ext_px[vr, li]
                    A_exc = (E_actual - hi_r) if lado == 1 else (lo_r - E_actual)
                    if A_exc < tick:
                        continue

                    #Si el precio ya cruzó todo el rango hasta el extremo opuesto, el ciclo de barrido terminó
                    if (lado == 1 and l[k] <= lo_r) or (lado == -1 and h[k] >= hi_r):
                        barrido_activo[vr, li] = 2
                        continue
                    if barrido_activo[vr, li] == 2:
                        continue

                    # Evaluar las 3 mecánicas de gatillo en la barra k:
                    # Gatillo 0 (REINGRESO_CIERRE): tras haber barrido en barra previa o actual, cierra de vuelta dentro del rango
                    cond_g0 = (k > bar_inicio_sw[vr, li] or A_exc >= 2.0 * tick) and (
                        (lado == 1 and c[k] <= hi_r and c[k] > lo_r + 0.20 * H_r)
                        or (lado == -1 and c[k] >= lo_r and c[k] < hi_r - 0.20 * H_r)
                    )
                    # Gatillo 1 (EXCURSION_U1_25): excursión >= 0.12 * H_r y regreso de >= 25% de A_exc hacia el rango
                    D_rest = (c[k] - hi_r) if lado == 1 else (lo_r - c[k])
                    cond_g1 = (A_exc >= 0.12 * H_r) and (D_rest <= 0.75 * A_exc) and (
                        (lado == 1 and c[k] > lo_r + 0.25 * H_r) or (lado == -1 and c[k] < hi_r - 0.25 * H_r)
                    )
                    # Gatillo 2 (RECHAZO_MECHA_SWEEP): mecha de rechazo en el sentido del retorno >= 30% de la vela k
                    rng_vela = max(h[k] - l[k], tick)
                    mecha_fav = (h[k] - max(o[k], c[k])) if lado == 1 else (min(o[k], c[k]) - l[k])
                    cond_g2 = (excursion_k >= tick) and (mecha_fav / rng_vela >= 0.30) and (
                        (lado == 1 and c[k] < E_actual - 0.20 * rng_vela and c[k] > lo_r + 0.25 * H_r)
                        or (lado == -1 and c[k] > E_actual + 0.20 * rng_vela and c[k] < hi_r - 0.25 * H_r)
                    )

                    for gat_idx in range(3):
                        if disparado[vr, gat_idx, li] == 1:
                            continue
                        ok_gat = cond_g0 if gat_idx == 0 else (cond_g1 if gat_idx == 1 else cond_g2)
                        if not ok_gat:
                            continue

                        disparado[vr, gat_idx, li] = 1
                        # Calcular variables causales en k
                        s_fade = -lado
                        sw_gate = 1 if (mecha_fav / rng_vela >= 0.35 and vk >= 1.15 * vol_ses_prev) else 0

                        # Gaps vivos dentro del rango entre c[k] y el extremo opuesto (imán)
                        g_cam = 0.0
                        px_min_cam = min(c[k], opuesto)
                        px_max_cam = max(c[k], opuesto)
                        for gi in range(n_gaps):
                            if g_act[gi] == 1 and g_bar[gi] < k:
                                g_mid = 0.5 * (g_lo[gi] + g_hi[gi])
                                if px_min_cam <= g_mid <= px_max_cam:
                                    edad = max(float(k - g_bar[gi]), 1.0)
                                    w_toq = 1.35 if g_toq[gi] == 1 else (1.0 if g_toq[gi] == 0 else 0.7)
                                    g_cam += math.exp(-edad / 240.0) * w_toq

                        # Alineación con corredor EMA(20)/EMA(60)
                        diff_ema = (ema20 - ema60) * float(s_fade)
                        if abs(ema20 - ema60) <= 0.35 * atr:
                            ema_al = 1  # comprimido / neutral
                        elif diff_ema > 0:
                            ema_al = 2  # a favor del retorno
                        else:
                            ema_al = 0  # en contra del retorno (tendencia pre-market opuesta)

                        # VWAP del lado del objetivo de retorno
                        vwap_al = 1 if ((vwap_k - c[k]) * float(s_fade) > 0.0) else 0
                        tam_rng = (H_r / max(atr, tick)) + 1e-7 * float((k - s_ini) % 89)

                        if cnt < max_out:
                            out_k[cnt] = k
                            out_vrng[cnt] = vr
                            out_gat[cnt] = gat_idx
                            out_lado[cnt] = lado
                            out_lo[cnt] = lo_r
                            out_hi[cnt] = hi_r
                            out_hrng[cnt] = H_r
                            out_eexc[cnt] = E_actual
                            out_excrel[cnt] = A_exc / H_r
                            out_swgate[cnt] = sw_gate
                            out_gtom[cnt] = gtom_acc[vr, li]
                            out_gcam[cnt] = g_cam
                            out_ema[cnt] = ema_al
                            out_tam[cnt] = tam_rng
                            out_vwap[cnt] = vwap_al
                            cnt += 1

        vol_ses_prev = max(vol_ses / float(max(s_fin - s_ini, 1)), 1.0)

    return (
        out_k[:cnt], out_vrng[:cnt], out_gat[:cnt], out_lado[:cnt],
        out_lo[:cnt], out_hi[:cnt], out_hrng[:cnt], out_eexc[:cnt],
        out_excrel[:cnt], out_swgate[:cnt], out_gtom[:cnt], out_gcam[:cnt],
        out_ema[:cnt], out_tam[:cnt], out_vwap[:cnt],
    )


def disparos(ctx: dict) -> pd.DataFrame:
    """Extrae los disparos causales de OTR-930-SWEEP con todas las columnas de VARIABLES y niveles estructurales."""
    t = np.asarray(ctx["t"], dtype=np.int64)
    o = np.asarray(ctx["o"], dtype=np.float64)
    h = np.asarray(ctx["h"], dtype=np.float64)
    l = np.asarray(ctx["l"], dtype=np.float64)
    c = np.asarray(ctx["c"], dtype=np.float64)
    v = np.asarray(ctx["v"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    tick = float(ctx["tick"])

    res = _extraer_disparos_otr_nb(t, o, h, l, c, v, ses, tick)
    D = pd.DataFrame({
        "k": res[0],
        "v_rng": res[1],
        "gat": res[2],
        "lado": res[3],
        "lo_rng": res[4],
        "hi_rng": res[5],
        "H_rng": res[6],
        "E_exc": res[7],
        "exc_rel": res[8],
        "sw_gate": res[9],
        "g_tom": res[10],
        "g_cam": res[11],
        "ema_al": res[12],
        "tam_rng": res[13],
        "vwap_al": res[14],
    })
    if len(D):
        D = D.sort_values(["k", "v_rng", "gat", "lado"]).reset_index(drop=True)
    return D


def niveles(fila: dict, ej: tuple, ctx: dict):
    """Calcula `(start, limite, s, entrada, stop, objetivo, be)` para un disparo y una tupla de ejecución."""
    md, ent, tp_name, sl_name = ej
    k = int(fila["k"])
    lado = int(fila["lado"])
    lo_r = float(fila["lo_rng"])
    hi_r = float(fila["hi_rng"])
    H_r = float(fila["H_rng"])
    E_exc = float(fila["E_exc"])
    tick = float(ctx["tick"])
    ck = float(ctx["c"][k])

    s = -lado if md == "RETORNO" else lado
    lim = 0 if ent == "CIERRE" else 2
    e = np.round(ck / tick) * tick

    # Distancia base al objetivo según modo y target
    if md == "RETORNO":
        opuesto = lo_r if lado == 1 else hi_r
        borde = hi_r if lado == 1 else lo_r
        if tp_name == "OPUESTO_100":
            tp_raw = opuesto
        elif tp_name == "POC_65":
            tp_raw = borde + float(s) * 0.65 * H_r
        else:  # MID_50
            tp_raw = 0.5 * (lo_r + hi_r)
        # Asegurar distancia mínima y separación entre los 3 targets incluso si ck ya avanzó dentro del rango
        min_mult = 0.85 if tp_name == "OPUESTO_100" else (0.60 if tp_name == "POC_65" else 0.40)
        if (tp_raw - e) * float(s) < min_mult * H_r:
            tp_raw = e + float(s) * min_mult * H_r
    else:  # CONTINUACION
        mult_tp = 1.00 if tp_name == "OPUESTO_100" else (0.65 if tp_name == "POC_65" else 0.45)
        tp_raw = e + float(s) * mult_tp * H_r

    tp = np.round(tp_raw / tick) * tick
    if (tp - e) * float(s) < 2.0 * tick:
        tp = e + float(s) * 2.0 * tick

    # Stops estructurales: S_SWEEP (detrás del extremo E_exc) vs S_RANGO55 (0.55 * H_rng)
    if sl_name == "S_SWEEP":
        if md == "RETORNO":
            dist_sw = max(abs(E_exc - e) + 2.0 * tick, 0.30 * H_r)
        else:
            dist_sw = 0.35 * H_r
        sl_raw = e - float(s) * dist_sw
    else:  # S_RANGO55
        dist_r55 = 0.55 * H_r
        if md == "RETORNO":
            dist_sw = max(abs(E_exc - e) + 2.0 * tick, 0.30 * H_r)
            if abs(dist_r55 - dist_sw) < 2.0 * tick:
                dist_r55 = dist_sw + 3.0 * tick
        sl_raw = e - float(s) * dist_r55

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
    lo_r = D["lo_rng"].to_numpy(np.float64)
    hi_r = D["hi_rng"].to_numpy(np.float64)
    H_r = D["H_rng"].to_numpy(np.float64)
    E_exc = D["E_exc"].to_numpy(np.float64)
    tick = float(ctx["tick"])
    ck = np.asarray(ctx["c"], dtype=np.float64)[k]

    s = (-lado if md == "RETORNO" else lado).astype(np.float64)
    lim = 0.0 if ent == "CIERRE" else 2.0
    e = np.round(ck / tick) * tick

    if md == "RETORNO":
        opuesto = np.where(lado == 1, lo_r, hi_r)
        borde = np.where(lado == 1, hi_r, lo_r)
        if tp_name == "OPUESTO_100":
            tp_raw = opuesto
            min_mult = 0.85
        elif tp_name == "POC_65":
            tp_raw = borde + s * 0.65 * H_r
            min_mult = 0.60
        else:
            tp_raw = 0.5 * (lo_r + hi_r)
            min_mult = 0.40
        corto = (tp_raw - e) * s < min_mult * H_r
        tp_raw = np.where(corto, e + s * min_mult * H_r, tp_raw)
    else:
        mult_tp = 1.00 if tp_name == "OPUESTO_100" else (0.65 if tp_name == "POC_65" else 0.45)
        tp_raw = e + s * mult_tp * H_r

    tp = np.round(tp_raw / tick) * tick
    tp = np.where((tp - e) * s < 2.0 * tick, e + s * 2.0 * tick, tp)

    dist_sw = np.maximum(np.abs(E_exc - e) + 2.0 * tick, 0.30 * H_r) if md == "RETORNO" else 0.35 * H_r
    if sl_name == "S_SWEEP":
        sl_raw = e - s * dist_sw
    else:
        dist_r55 = 0.55 * H_r
        if md == "RETORNO":
            dist_r55 = np.where(np.abs(dist_r55 - dist_sw) < 2.0 * tick, dist_sw + 3.0 * tick, dist_r55)
        sl_raw = e - s * dist_r55

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
