r"""HFTZonesNQRangosPctV2 — Espejo Python + Numba de `nt8/user_indicators/HFTZonesNQRangosPctV2.cs`.

**Target-free y 100% Causal (sin look-ahead).**
Traduce a Python / Numba las tres capas del indicador `HFTZonesNQRangosPctV2.cs`:

1. **Capa 1 — Motor de rachas 1-tick (`detectar_candidatos_nb` + `filtrar_zonas_nb`):**
   - Idéntico en reglas de estado a `edgelab.bridge.indicators.hftzones_nq` (`ProcesarSweeps` de
     `HFTZonesNQPureV4.cs` / `HFTZonesNQRangosPctV2.cs`), pero compilado en Numba (`@njit`) para
     procesar trimestres enteros de 1-tick ($10^7-10^8$ ticks) en segundos sin alocar listas por
     candidato.
   - Mantiene la separación arquitectónica de dos etapas:
     a) `detectar_candidatos_nb`: una sola pasada por el stream 1-tick (con soporte de corte de
        sesión `END_OF_SESSION` y `prev_session_close_ticks`) produce el censo tabular completo
        de candidatos con sus 24 estadísticos suficientes.
     b) `filtrar_zonas_nb` / `accept_all`: aplica cualquier combinación de umbrales de
        `GRILLA_ZONA_HFT` en microsegundos ($O(N_{\text{cand}})$) sin releer los ticks.

2. **Capa 2 — Detector Causal de Clusters HFT (`evaluar_clusters_causales_nb`):**
   - Espejo exacto de `EvaluarClusterCausal` en `HFTZonesNQRangosPctV2.cs`:
     - Evalúa cada zona $z_i$ en el instante exacto de su confirmación (`detect_bar = z_i.DetectBar`).
     - Sólo considera zonas ya confirmadas (`w.DetectBar <= detect_bar`) y vigentes
       (`w.VisualEndBar >= detect_bar`).
     - Ordena las zonas vivas por precio medio, toma ventanas de $K = \text{MinZonasCluster}$
       que contienen a $z_i$, y expande la pila contigua mientras el salto vertical no supere
       `maxJoinGap = max(4 * TickSize, 0.35 * avgZoneHeight)` y el ancho total no supere
       `maxAllowedSpanPrice = max(min_span_floor_ticks, escalaVolTicks * max_span_mult) * TickSize`.
     - Mide la **densidad real de solapamiento** (`packing = sumH / spanPrice`), el paso
       normalizado por la altura media de las zonas (`pasoNorm`), el gap libre normalizado
       (`gapNorm`), y el centro de gravedad ponderado por volumen (`POC`).
     - Soporta tanto el modo híbrido del `.cs` (`MODO_V2_HIBRIDO = 0`: alta confluencia directa
       o percentil adaptativo por frecuencia de sesión `PctAngosto`), como los dos modos puros
       para barridos ortogonales (`MODO_PACKING_PURO = 1` y `MODO_PERCENTIL_CAUSAL = 2`).

3. **Capa 3 — Detector Causal de Expansiones Libres de HFT (`evaluar_expansiones_causales_nb`):**
   - Espejo exacto de `NotificarZonaNuevaEnImpulso` + `ActualizarImpulsoYExpansionCausal` +
     `RecortarExpansionesSolapadas` en `HFTZonesNQRangosPctV2.cs`:
     - Rastrea piernas direccionales causales con giro local adaptativo (`escalaVolTicks`),
     - Si una nueva zona HFT se confirma dentro del corredor del impulso, actualiza la expansión
       activa hasta el borde de la zona y divide la pierna hacia adelante,
     - Actualiza in-place la frontera líder de la expansión activa manteniendo `DetectBar` fijo
       (sin apilar rectángulos duplicados ni usar look-ahead), y recorta expansiones previas
       solapadas o mitigadas ($\ge 75\%$).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from numba import njit

from edgelab.bridge.indicators import hftzones_nq as hz_base

NAME = "HFTZonesNQRangosPctV2"
VERSION = "2.0.0"

# Códigos enteros para motivo de cierre de racha en arrays Numba
REASON_REVERSAL = 1
REASON_MAX_PAUSE = 2
REASON_END_OF_SESSION = 3
REASON_CENSORED_END_OF_INPUT = 4

REASON_CODE_TO_STR = {
    REASON_REVERSAL: "REVERSAL",
    REASON_MAX_PAUSE: "MAX_PAUSE",
    REASON_END_OF_SESSION: "END_OF_SESSION",
    REASON_CENSORED_END_OF_INPUT: "CENSORED_END_OF_INPUT",
}

# Códigos enteros para Bucket HFT
BUCKET_PREDATOR = 0
BUCKET_ULTRA = 1
BUCKET_FAST = 2
BUCKET_ABSORB = 3

BUCKET_CODE_TO_STR = {
    BUCKET_PREDATOR: "Predator",
    BUCKET_ULTRA: "Ultra",
    BUCKET_FAST: "Fast",
    BUCKET_ABSORB: "Absorb",
}

# Modos de compresión para EvaluarClusterCausal
MODO_V2_HIBRIDO = 0        # Exacto al .cs V2 (altaConfluenciaDirecta OR percentil adaptativo)
MODO_PACKING_PURO = 1      # Umbral estructural directo sobre packing y span (ideal para grilla)
MODO_PERCENTIL_CAUSAL = 2  # Umbral relativo puro por percentil causal de score

DEFAULTS_V2 = dict(
    # Motor 1-tick base
    tick_resolution=1,
    max_pausa_ms=100.0,
    min_pasos=8,
    min_absorb_pasos=6,
    detect_absorb=True,
    min_sweep_ticks=4,
    max_avg_ms=25.0,
    max_total_ms=500.0,
    min_volume_rate=100.0,
    min_total_volume=50.0,
    max_retroceso_ticks=2.0,
    retroceso_pct_height=50.0,
    predator_avg_ms=5.0,
    ultra_avg_ms=15.0,
    extension_dibujo=400,
    # Eventos infrecuentes (Clusters HFT y Expansiones sin HFT)
    min_zonas_cluster=4,
    pct_angosto=10.0,
    clusters_por_sesion=1.5,
    pct_amplio=5.0,
    exp_por_sesion=1.2,
    min_exp_ticks=24.0,
    zigzag_ticks=40.0,
    pct_min_historia=25,
    pct_extension_bars=300,
    min_packing=0.70,
    max_span_mult=3.2,
    min_span_floor_ticks=88.0,
    max_join_gap_ratio=0.35,
    polaridad_min=0.0,
    modo_compresion=MODO_V2_HIBRIDO,
)

# ==============================================================================
# GRILLAS ORTOGONALES (ETAPA 1: ZONAS HFT, ETAPA 2: CLUSTERS HFT)
# ==============================================================================

def construir_grilla_zona_hft() -> dict[str, dict[str, Any]]:
    """12 definiciones post-hoc de Zona HFT individual aplicables sobre el mismo censo 1-tick.

    Ejes ortogonales:
      - Cadencia máxima (`max_avg_ms`): 15 ms (Ultra/Predator) vs 25 ms (Estándar)
      - Volumen mínimo (`min_total_volume`): 10 (Campaña E0), 30 (Intermedio), 50 (Certificado NT8)
      - Composición (`detect_absorb` / `min_sweep_ticks`):
          * `SW4_ABS`: barridos >= 4t + absorciones >= 6 pasos (default V2)
          * `SW4_PURO`: sólo barridos direccionales >= 4t (sin absorb)
    """
    grilla: dict[str, dict[str, Any]] = {}
    for cad_tag, max_avg in (("V15", 15.0), ("V25", 25.0)):
        for vol_tag, min_vol in (("VOL10", 10.0), ("VOL30", 30.0), ("VOL50", 50.0)):
            for tipo_tag, det_abs in (("ABS1", True), ("ABS0", False)):
                key = f"Z_{cad_tag}_{vol_tag}_{tipo_tag}"
                grilla[key] = dict(
                    min_pasos=8,
                    min_absorb_pasos=6,
                    detect_absorb=det_abs,
                    min_sweep_ticks=4,
                    max_avg_ms=max_avg,
                    max_total_ms=500.0,
                    min_volume_rate=100.0,
                    min_total_volume=min_vol,
                    max_retroceso_ticks=2.0,
                    retroceso_pct_height=50.0,
                )
    return grilla


def construir_grilla_cluster_hft() -> dict[str, dict[str, Any]]:
    """18 definiciones causales de Cluster HFT (3 familias geométricas/estructurales).

    Familias:
      1. Familia P (`MODO_PACKING_PURO`): compresión por densidad real de solapamiento
         (`min_zonas` in {3, 4, 5} x `min_packing` in {0.85, 1.25} x `extension_dibujo` in {150, 400}).
      2. Familia H (`MODO_V2_HIBRIDO`): regla exacta de `HFTZonesNQRangosPctV2.cs`
         (`min_zonas` in {3, 4, 5} x `pct_angosto` in {10, 20}).
    """
    grilla: dict[str, dict[str, Any]] = {}
    # Familia P: 3 x 2 x 2 = 12 definiciones por densidad de solapamiento (packing)
    for k in (3, 4, 5):
        for pack_tag, min_pack in (("PK085", 0.85), ("PK125", 1.25)):
            for viv_tag, ext_viv in (("W150", 150), ("W400", 400)):
                key = f"C_PACK_K{k}_{pack_tag}_{viv_tag}"
                grilla[key] = dict(
                    min_zonas_cluster=k,
                    min_packing=min_pack,
                    extension_dibujo=ext_viv,
                    pct_extension_bars=300,
                    max_span_mult=3.2,
                    min_span_floor_ticks=88.0,
                    max_join_gap_ratio=0.35,
                    polaridad_min=0.0,
                    pct_angosto=10.0,
                    clusters_por_sesion=1.5,
                    pct_min_historia=25,
                    modo_compresion=MODO_PACKING_PURO,
                )
    # Familia H: 3 x 2 = 6 definiciones híbridas V2 (alta confluencia + percentil adaptativo)
    for k in (3, 4, 5):
        for pct in (10, 20):
            key = f"C_V2HIB_K{k}_P{pct}"
            grilla[key] = dict(
                min_zonas_cluster=k,
                min_packing=0.70,
                extension_dibujo=400,
                pct_extension_bars=300,
                max_span_mult=3.2,
                min_span_floor_ticks=88.0,
                max_join_gap_ratio=0.35,
                polaridad_min=0.0,
                pct_angosto=float(pct),
                clusters_por_sesion=1.5,
                pct_min_historia=25,
                modo_compresion=MODO_V2_HIBRIDO,
            )
    return grilla


GRILLA_ZONA_HFT = construir_grilla_zona_hft()
GRILLA_CLUSTER_HFT = construir_grilla_cluster_hft()


# ==============================================================================
# CAPA 1: MOTOR NUMBA DE CANDIDATOS Y ZONAS 1-TICK
# ==============================================================================

@njit(cache=True)
def _calcular_estadisticos_racha_nb(
    i0: int,
    i1: int,
    price_ticks: np.ndarray,
    volume: np.ndarray,
    sign_arr: np.ndarray,
):
    """Calcula CVD, volúmenes buy/sell, slope del delta y niveles sin movimiento en [i0..i1]."""
    n_s = i1 - i0 + 1
    cvd = 0.0
    buy = 0.0
    sell = 0.0
    max_tick_vol = 0.0

    sx = 0.0
    sy = 0.0
    sxy = 0.0
    sxx = 0.0
    cum = 0.0
    d_first = 0.0
    d_second = 0.0
    mitad = n_s // 2

    no_move_ticks = 0
    no_move_vol = 0.0

    for k in range(n_s):
        idx = i0 + k
        v = float(volume[idx])
        s = int(sign_arr[idx])
        sv = s * v
        cvd += sv
        if sv >= 0.0:
            buy += v
        else:
            sell += v
        if v > max_tick_vol:
            max_tick_vol = v

        cum += sv
        fk = float(k)
        sx += fk
        sy += cum
        sxy += fk * cum
        sxx += fk * fk
        if k < mitad:
            d_first += sv
        else:
            d_second += sv

        if k > 0 and price_ticks[idx] == price_ticks[idx - 1]:
            no_move_ticks += 1
            no_move_vol += v

    slope = 0.0
    if n_s >= 2:
        den = float(n_s) * sxx - sx * sx
        if abs(den) > 1e-9:
            slope = (float(n_s) * sxy - sx * sy) / den
    else:
        d_first = 0.0
        d_second = 0.0

    # Frecuencia máxima en un mismo nivel de precio (equivalente exacto a max(freq.values()))
    max_level_ticks = 0
    if n_s == 1:
        max_level_ticks = 1
    elif n_s > 1:
        px_slice = np.sort(price_ticks[i0 : i1 + 1])
        cur_run = 1
        max_level_ticks = 1
        for k in range(1, n_s):
            if px_slice[k] == px_slice[k - 1]:
                cur_run += 1
                if cur_run > max_level_ticks:
                    max_level_ticks = cur_run
            else:
                cur_run = 1

    return (
        cvd,
        buy,
        sell,
        max_tick_vol,
        slope,
        d_first,
        d_second,
        no_move_ticks,
        no_move_vol,
        max_level_ticks,
    )


@njit(cache=True)
def detectar_candidatos_nb(
    ts_ns: np.ndarray,
    price_ticks: np.ndarray,
    volume: np.ndarray,
    session_ids: np.ndarray,
    prim_bar_of_tick: np.ndarray,
    max_pausa_ms: float = 100.0,
    retro_floor_ticks: float = 2.0,
    retro_pct_height: float = 50.0,
    has_prev_session_close: bool = False,
    prev_session_close_ticks: int = 0,
):
    """Extrae en una sola pasada 1-tick todos los candidatos con sus estadísticos suficientes.

    Devuelve dos matrices compactas `(cand_int, cand_flt)`:
      - `cand_int` (N_cand, 15) int64:
          0: idx_start
          1: idx_end
          2: idx_avail
          3: ts_start
          4: ts_end
          5: ts_avail
          6: termination_reason_code (1=REVERSAL, 2=MAX_PAUSE, 3=END_OF_SESSION, 4=CENSORED_END_OF_INPUT)
          7: direction (-1 o +1)
          8: pasos (streak)
          9: valid_steps
         10: sw_hi_tk
         11: sw_lo_tk
         12: n_intervals
         13: no_move_ticks
         14: max_level_ticks
         15: start_prim_bar
         16: end_prim_bar
         17: detect_prim_bar
      - `cand_flt` (N_cand, 13) float64:
          0: height_ticks
          1: total_ms
          2: avg_ms
          3: total_vol
          4: vol_rate
          5: max_retro_ticks
          6: cvd
          7: buy_vol
          8: sell_vol
          9: max_tick_vol
         10: delta_slope
         11: delta_first
         12: delta_second
         13: no_move_vol
    """
    n = len(price_ticks)
    if n == 0:
        return np.empty((0, 18), dtype=np.int64), np.empty((0, 14), dtype=np.float64)

    # Capacidad inicial (máximo teórico <= n // 2 + 2)
    cap = max(64, n // 4 + 4)
    cand_int = np.empty((cap, 18), dtype=np.int64)
    cand_flt = np.empty((cap, 14), dtype=np.float64)
    n_out = 0

    sign_arr = np.zeros(n, dtype=np.int8)

    direccion = 0
    idx0 = 0
    streak = 0
    valid = 0
    sw_hi = 0
    sw_lo = 0
    extremo = 0
    max_retro = 0.0
    total_vol = 0.0
    total_ms = 0.0
    n_intervals = 0
    last_side = 0
    start_prim_bar = 0
    last_prim_bar = 0

    cur_ses = session_ids[0]

    if has_prev_session_close:
        cl0 = int(price_ticks[0])
        vol0 = float(volume[0])
        cl_p = int(prev_session_close_ticks)
        side0 = 1 if cl0 > cl_p else (-1 if cl0 < cl_p else 0)
        if side0 == 0:
            side0 = 1
        last_side = side0
        sign_arr[0] = side0
        is_baja0 = cl0 <= cl_p
        is_alza0 = cl0 >= cl_p
        if is_baja0:
            direccion = -1
        elif is_alza0:
            direccion = 1
        if direccion != 0:
            streak = 1
            valid = 1
            sw_hi = cl0
            sw_lo = cl0
            extremo = cl0
            max_retro = 0.0
            total_vol = vol0
            total_ms = 0.0
            n_intervals = 0
            idx0 = 0
            p_bar0 = int(prim_bar_of_tick[0])
            start_prim_bar = p_bar0
            last_prim_bar = p_bar0

    for i in range(1, n):
        ses_i = session_ids[i]
        # Corte de sesión idéntico a CheckSessionBoundary(tickTime) en NT8
        if ses_i != cur_ses:
            if direccion != 0 and streak > 0:
                if n_out >= cap:
                    new_cap = cap * 2
                    new_int = np.empty((new_cap, 18), dtype=np.int64)
                    new_flt = np.empty((new_cap, 14), dtype=np.float64)
                    new_int[:n_out] = cand_int[:n_out]
                    new_flt[:n_out] = cand_flt[:n_out]
                    cand_int = new_int
                    cand_flt = new_flt
                    cap = new_cap
                i_fin = i - 1
                i_avail = i - 1
                (
                    cvd,
                    buy,
                    sell,
                    max_tv,
                    slope,
                    d1,
                    d2,
                    nm_tk,
                    nm_vol,
                    max_lvl,
                ) = _calcular_estadisticos_racha_nb(idx0, i_fin, price_ticks, volume, sign_arr)
                avg_ms = total_ms / float(max(1, n_intervals))
                dur_sec = max(total_ms, 1.0) / 1000.0
                vol_rate = total_vol / dur_sec
                p_end = max(start_prim_bar, last_prim_bar)
                p_det = max(p_end, int(prim_bar_of_tick[i_avail]))

                cand_int[n_out, 0] = idx0
                cand_int[n_out, 1] = i_fin
                cand_int[n_out, 2] = i_avail
                cand_int[n_out, 3] = ts_ns[idx0]
                cand_int[n_out, 4] = ts_ns[i_fin]
                cand_int[n_out, 5] = ts_ns[i_avail]
                cand_int[n_out, 6] = REASON_END_OF_SESSION
                cand_int[n_out, 7] = direccion
                cand_int[n_out, 8] = streak
                cand_int[n_out, 9] = valid
                cand_int[n_out, 10] = sw_hi
                cand_int[n_out, 11] = sw_lo
                cand_int[n_out, 12] = n_intervals
                cand_int[n_out, 13] = nm_tk
                cand_int[n_out, 14] = max_lvl
                cand_int[n_out, 15] = start_prim_bar
                cand_int[n_out, 16] = p_end
                cand_int[n_out, 17] = p_det

                cand_flt[n_out, 0] = float(sw_hi - sw_lo)
                cand_flt[n_out, 1] = total_ms
                cand_flt[n_out, 2] = avg_ms
                cand_flt[n_out, 3] = total_vol
                cand_flt[n_out, 4] = vol_rate
                cand_flt[n_out, 5] = max_retro
                cand_flt[n_out, 6] = cvd
                cand_flt[n_out, 7] = buy
                cand_flt[n_out, 8] = sell
                cand_flt[n_out, 9] = max_tv
                cand_flt[n_out, 10] = slope
                cand_flt[n_out, 11] = d1
                cand_flt[n_out, 12] = d2
                cand_flt[n_out, 13] = nm_vol
                n_out += 1

            cur_ses = ses_i
            direccion = 0
            streak = 0
            valid = 0
            total_ms = 0.0
            n_intervals = 0
            total_vol = 0.0
            extremo = 0
            max_retro = 0.0

        cl = int(price_ticks[i])
        cl_prev = int(price_ticks[i - 1])
        ms = float(ts_ns[i] - ts_ns[i - 1]) / 1e6
        vol = float(volume[i])

        side = 1 if cl > cl_prev else (-1 if cl < cl_prev else last_side)
        if side == 0:
            side = 1
        last_side = side
        sign_arr[i] = side

        es_baja = cl <= cl_prev
        es_alza = cl >= cl_prev

        if direccion != 0 and ms > max_pausa_ms:
            if n_out >= cap:
                new_cap = cap * 2
                new_int = np.empty((new_cap, 18), dtype=np.int64)
                new_flt = np.empty((new_cap, 14), dtype=np.float64)
                new_int[:n_out] = cand_int[:n_out]
                new_flt[:n_out] = cand_flt[:n_out]
                cand_int = new_int
                cand_flt = new_flt
                cap = new_cap
            i_fin = i - 1
            i_avail = i
            (
                cvd,
                buy,
                sell,
                max_tv,
                slope,
                d1,
                d2,
                nm_tk,
                nm_vol,
                max_lvl,
            ) = _calcular_estadisticos_racha_nb(idx0, i_fin, price_ticks, volume, sign_arr)
            avg_ms = total_ms / float(max(1, n_intervals))
            dur_sec = max(total_ms, 1.0) / 1000.0
            vol_rate = total_vol / dur_sec
            p_end = max(start_prim_bar, last_prim_bar)
            p_det = max(p_end, int(prim_bar_of_tick[i_avail]))

            cand_int[n_out, 0] = idx0
            cand_int[n_out, 1] = i_fin
            cand_int[n_out, 2] = i_avail
            cand_int[n_out, 3] = ts_ns[idx0]
            cand_int[n_out, 4] = ts_ns[i_fin]
            cand_int[n_out, 5] = ts_ns[i_avail]
            cand_int[n_out, 6] = REASON_MAX_PAUSE
            cand_int[n_out, 7] = direccion
            cand_int[n_out, 8] = streak
            cand_int[n_out, 9] = valid
            cand_int[n_out, 10] = sw_hi
            cand_int[n_out, 11] = sw_lo
            cand_int[n_out, 12] = n_intervals
            cand_int[n_out, 13] = nm_tk
            cand_int[n_out, 14] = max_lvl
            cand_int[n_out, 15] = start_prim_bar
            cand_int[n_out, 16] = p_end
            cand_int[n_out, 17] = p_det

            cand_flt[n_out, 0] = float(sw_hi - sw_lo)
            cand_flt[n_out, 1] = total_ms
            cand_flt[n_out, 2] = avg_ms
            cand_flt[n_out, 3] = total_vol
            cand_flt[n_out, 4] = vol_rate
            cand_flt[n_out, 5] = max_retro
            cand_flt[n_out, 6] = cvd
            cand_flt[n_out, 7] = buy
            cand_flt[n_out, 8] = sell
            cand_flt[n_out, 9] = max_tv
            cand_flt[n_out, 10] = slope
            cand_flt[n_out, 11] = d1
            cand_flt[n_out, 12] = d2
            cand_flt[n_out, 13] = nm_vol
            n_out += 1

            direccion = 0
            streak = 0
            continue

        if direccion == 0:
            if es_baja:
                direccion = -1
            elif es_alza:
                direccion = 1
            if direccion != 0:
                streak = 1
                valid = 1
                sw_hi = cl
                sw_lo = cl
                extremo = cl
                max_retro = 0.0
                total_vol = vol
                total_ms = 0.0
                n_intervals = 0
                idx0 = i
                p_bar = int(prim_bar_of_tick[i])
                start_prim_bar = p_bar
                last_prim_bar = p_bar
        elif direccion == -1:
            if es_baja:
                streak += 1
                valid += 1
                if cl > sw_hi:
                    sw_hi = cl
                if cl < sw_lo:
                    sw_lo = cl
                if cl < extremo:
                    extremo = cl
                adv = float(cl - extremo)
                if adv > max_retro:
                    max_retro = adv
                total_ms += ms
                n_intervals += 1
                total_vol += vol
                last_prim_bar = int(prim_bar_of_tick[i])
            else:
                retro = float(cl - extremo)
                permitido = max(retro_floor_ticks, (retro_pct_height / 100.0) * float(sw_hi - sw_lo))
                if retro <= permitido:
                    streak += 1
                    if cl > sw_hi:
                        sw_hi = cl
                    if cl < sw_lo:
                        sw_lo = cl
                    if cl < extremo:
                        extremo = cl
                    adv = float(cl - extremo)
                    if adv > max_retro:
                        max_retro = adv
                    total_ms += ms
                    n_intervals += 1
                    total_vol += vol
                    last_prim_bar = int(prim_bar_of_tick[i])
                else:
                    if n_out >= cap:
                        new_cap = cap * 2
                        new_int = np.empty((new_cap, 18), dtype=np.int64)
                        new_flt = np.empty((new_cap, 14), dtype=np.float64)
                        new_int[:n_out] = cand_int[:n_out]
                        new_flt[:n_out] = cand_flt[:n_out]
                        cand_int = new_int
                        cand_flt = new_flt
                        cap = new_cap
                    i_fin = i - 1
                    i_avail = i
                    (
                        cvd,
                        buy,
                        sell,
                        max_tv,
                        slope,
                        d1,
                        d2,
                        nm_tk,
                        nm_vol,
                        max_lvl,
                    ) = _calcular_estadisticos_racha_nb(idx0, i_fin, price_ticks, volume, sign_arr)
                    avg_ms = total_ms / float(max(1, n_intervals))
                    dur_sec = max(total_ms, 1.0) / 1000.0
                    vol_rate = total_vol / dur_sec
                    p_end = max(start_prim_bar, last_prim_bar)
                    p_det = max(p_end, int(prim_bar_of_tick[i_avail]))

                    cand_int[n_out, 0] = idx0
                    cand_int[n_out, 1] = i_fin
                    cand_int[n_out, 2] = i_avail
                    cand_int[n_out, 3] = ts_ns[idx0]
                    cand_int[n_out, 4] = ts_ns[i_fin]
                    cand_int[n_out, 5] = ts_ns[i_avail]
                    cand_int[n_out, 6] = REASON_REVERSAL
                    cand_int[n_out, 7] = direccion
                    cand_int[n_out, 8] = streak
                    cand_int[n_out, 9] = valid
                    cand_int[n_out, 10] = sw_hi
                    cand_int[n_out, 11] = sw_lo
                    cand_int[n_out, 12] = n_intervals
                    cand_int[n_out, 13] = nm_tk
                    cand_int[n_out, 14] = max_lvl
                    cand_int[n_out, 15] = start_prim_bar
                    cand_int[n_out, 16] = p_end
                    cand_int[n_out, 17] = p_det

                    cand_flt[n_out, 0] = float(sw_hi - sw_lo)
                    cand_flt[n_out, 1] = total_ms
                    cand_flt[n_out, 2] = avg_ms
                    cand_flt[n_out, 3] = total_vol
                    cand_flt[n_out, 4] = vol_rate
                    cand_flt[n_out, 5] = max_retro
                    cand_flt[n_out, 6] = cvd
                    cand_flt[n_out, 7] = buy
                    cand_flt[n_out, 8] = sell
                    cand_flt[n_out, 9] = max_tv
                    cand_flt[n_out, 10] = slope
                    cand_flt[n_out, 11] = d1
                    cand_flt[n_out, 12] = d2
                    cand_flt[n_out, 13] = nm_vol
                    n_out += 1

                    if es_alza:
                        direccion = 1
                        streak = 1
                        valid = 1
                        sw_hi = cl
                        sw_lo = cl
                        extremo = cl
                        max_retro = 0.0
                        total_vol = vol
                        total_ms = 0.0
                        n_intervals = 0
                        idx0 = i
                        p_bar = int(prim_bar_of_tick[i])
                        start_prim_bar = p_bar
                        last_prim_bar = p_bar
                    else:
                        direccion = 0
                        streak = 0
        else:
            if es_alza:
                streak += 1
                valid += 1
                if cl > sw_hi:
                    sw_hi = cl
                if cl < sw_lo:
                    sw_lo = cl
                if cl > extremo:
                    extremo = cl
                adv = float(extremo - cl)
                if adv > max_retro:
                    max_retro = adv
                total_ms += ms
                n_intervals += 1
                total_vol += vol
                last_prim_bar = int(prim_bar_of_tick[i])
            else:
                retro = float(extremo - cl)
                permitido = max(retro_floor_ticks, (retro_pct_height / 100.0) * float(sw_hi - sw_lo))
                if retro <= permitido:
                    streak += 1
                    if cl > sw_hi:
                        sw_hi = cl
                    if cl < sw_lo:
                        sw_lo = cl
                    if cl > extremo:
                        extremo = cl
                    adv = float(extremo - cl)
                    if adv > max_retro:
                        max_retro = adv
                    total_ms += ms
                    n_intervals += 1
                    total_vol += vol
                    last_prim_bar = int(prim_bar_of_tick[i])
                else:
                    if n_out >= cap:
                        new_cap = cap * 2
                        new_int = np.empty((new_cap, 18), dtype=np.int64)
                        new_flt = np.empty((new_cap, 14), dtype=np.float64)
                        new_int[:n_out] = cand_int[:n_out]
                        new_flt[:n_out] = cand_flt[:n_out]
                        cand_int = new_int
                        cand_flt = new_flt
                        cap = new_cap
                    i_fin = i - 1
                    i_avail = i
                    (
                        cvd,
                        buy,
                        sell,
                        max_tv,
                        slope,
                        d1,
                        d2,
                        nm_tk,
                        nm_vol,
                        max_lvl,
                    ) = _calcular_estadisticos_racha_nb(idx0, i_fin, price_ticks, volume, sign_arr)
                    avg_ms = total_ms / float(max(1, n_intervals))
                    dur_sec = max(total_ms, 1.0) / 1000.0
                    vol_rate = total_vol / dur_sec
                    p_end = max(start_prim_bar, last_prim_bar)
                    p_det = max(p_end, int(prim_bar_of_tick[i_avail]))

                    cand_int[n_out, 0] = idx0
                    cand_int[n_out, 1] = i_fin
                    cand_int[n_out, 2] = i_avail
                    cand_int[n_out, 3] = ts_ns[idx0]
                    cand_int[n_out, 4] = ts_ns[i_fin]
                    cand_int[n_out, 5] = ts_ns[i_avail]
                    cand_int[n_out, 6] = REASON_REVERSAL
                    cand_int[n_out, 7] = direccion
                    cand_int[n_out, 8] = streak
                    cand_int[n_out, 9] = valid
                    cand_int[n_out, 10] = sw_hi
                    cand_int[n_out, 11] = sw_lo
                    cand_int[n_out, 12] = n_intervals
                    cand_int[n_out, 13] = nm_tk
                    cand_int[n_out, 14] = max_lvl
                    cand_int[n_out, 15] = start_prim_bar
                    cand_int[n_out, 16] = p_end
                    cand_int[n_out, 17] = p_det

                    cand_flt[n_out, 0] = float(sw_hi - sw_lo)
                    cand_flt[n_out, 1] = total_ms
                    cand_flt[n_out, 2] = avg_ms
                    cand_flt[n_out, 3] = total_vol
                    cand_flt[n_out, 4] = vol_rate
                    cand_flt[n_out, 5] = max_retro
                    cand_flt[n_out, 6] = cvd
                    cand_flt[n_out, 7] = buy
                    cand_flt[n_out, 8] = sell
                    cand_flt[n_out, 9] = max_tv
                    cand_flt[n_out, 10] = slope
                    cand_flt[n_out, 11] = d1
                    cand_flt[n_out, 12] = d2
                    cand_flt[n_out, 13] = nm_vol
                    n_out += 1

                    if es_baja:
                        direccion = -1
                        streak = 1
                        valid = 1
                        sw_hi = cl
                        sw_lo = cl
                        extremo = cl
                        max_retro = 0.0
                        total_vol = vol
                        total_ms = 0.0
                        n_intervals = 0
                        idx0 = i
                        p_bar = int(prim_bar_of_tick[i])
                        start_prim_bar = p_bar
                        last_prim_bar = p_bar
                    else:
                        direccion = 0
                        streak = 0

    # Fin del stream
    if direccion != 0 and streak > 0:
        if n_out >= cap:
            new_cap = cap + 2
            new_int = np.empty((new_cap, 18), dtype=np.int64)
            new_flt = np.empty((new_cap, 14), dtype=np.float64)
            new_int[:n_out] = cand_int[:n_out]
            new_flt[:n_out] = cand_flt[:n_out]
            cand_int = new_int
            cand_flt = new_flt
        i_fin = n - 1
        i_avail = n - 1
        (
            cvd,
            buy,
            sell,
            max_tv,
            slope,
            d1,
            d2,
            nm_tk,
            nm_vol,
            max_lvl,
        ) = _calcular_estadisticos_racha_nb(idx0, i_fin, price_ticks, volume, sign_arr)
        avg_ms = total_ms / float(max(1, n_intervals))
        dur_sec = max(total_ms, 1.0) / 1000.0
        vol_rate = total_vol / dur_sec
        p_end = max(start_prim_bar, last_prim_bar)
        p_det = max(p_end, int(prim_bar_of_tick[i_avail]))

        cand_int[n_out, 0] = idx0
        cand_int[n_out, 1] = i_fin
        cand_int[n_out, 2] = i_avail
        cand_int[n_out, 3] = ts_ns[idx0]
        cand_int[n_out, 4] = ts_ns[i_fin]
        cand_int[n_out, 5] = ts_ns[i_avail]
        cand_int[n_out, 6] = REASON_CENSORED_END_OF_INPUT
        cand_int[n_out, 7] = direccion
        cand_int[n_out, 8] = streak
        cand_int[n_out, 9] = valid
        cand_int[n_out, 10] = sw_hi
        cand_int[n_out, 11] = sw_lo
        cand_int[n_out, 12] = n_intervals
        cand_int[n_out, 13] = nm_tk
        cand_int[n_out, 14] = max_lvl
        cand_int[n_out, 15] = start_prim_bar
        cand_int[n_out, 16] = p_end
        cand_int[n_out, 17] = p_det

        cand_flt[n_out, 0] = float(sw_hi - sw_lo)
        cand_flt[n_out, 1] = total_ms
        cand_flt[n_out, 2] = avg_ms
        cand_flt[n_out, 3] = total_vol
        cand_flt[n_out, 4] = vol_rate
        cand_flt[n_out, 5] = max_retro
        cand_flt[n_out, 6] = cvd
        cand_flt[n_out, 7] = buy
        cand_flt[n_out, 8] = sell
        cand_flt[n_out, 9] = max_tv
        cand_flt[n_out, 10] = slope
        cand_flt[n_out, 11] = d1
        cand_flt[n_out, 12] = d2
        cand_flt[n_out, 13] = nm_vol
        n_out += 1

    return cand_int[:n_out], cand_flt[:n_out]


@njit(cache=True)
def filtrar_zonas_nb(
    cand_int: np.ndarray,
    cand_flt: np.ndarray,
    min_pasos: int = 8,
    min_absorb_pasos: int = 6,
    detect_absorb: bool = True,
    min_sweep_ticks: float = 4.0,
    max_avg_ms: float = 25.0,
    max_total_ms: float = 500.0,
    min_volume_rate: float = 100.0,
    min_total_volume: float = 50.0,
    max_retroceso_ticks: float = 2.0,
    retroceso_pct_height: float = 50.0,
    predator_avg_ms: float = 5.0,
    ultra_avg_ms: float = 15.0,
):
    """Filtra en O(N_cand) los candidatos aceptados como Zonas HFT y clasifica su bucket.

    Devuelve:
      - `accepted_idx`: índices en `cand_int`/`cand_flt` que pasaron las 7 compuertas.
      - `bucket_codes`: código de bucket de cada zona aceptada (`0=Predator, 1=Ultra, 2=Fast, 3=Absorb`).
      - `gate_counts`: conteo de rechazos por cada una de las 7 compuertas en `GATE_ORDER`.
    """
    n_c = len(cand_int)
    accepted_idx = np.empty(n_c, dtype=np.int64)
    bucket_codes = np.empty(n_c, dtype=np.int64)
    gate_counts = np.zeros(7, dtype=np.int64)
    n_ok = 0

    for i in range(n_c):
        valid_steps = cand_int[i, 9]
        height_ticks = cand_flt[i, 0]
        total_ms = cand_flt[i, 1]
        avg_ms = cand_flt[i, 2]
        total_vol = cand_flt[i, 3]
        vol_rate = cand_flt[i, 4]
        max_retro = cand_flt[i, 5]

        is_sweep = height_ticks >= min_sweep_ticks
        is_absorb = (not is_sweep) and detect_absorb
        min_req = min_pasos if is_sweep else min_absorb_pasos

        if valid_steps < min_req:
            gate_counts[0] += 1
            continue
        if not (is_sweep or is_absorb):
            gate_counts[1] += 1
            continue
        if avg_ms > max_avg_ms:
            gate_counts[2] += 1
            continue
        if total_ms > max_total_ms:
            gate_counts[3] += 1
            continue
        if vol_rate < min_volume_rate:
            gate_counts[4] += 1
            continue
        if total_vol < min_total_volume:
            gate_counts[5] += 1
            continue
        if not is_absorb:
            permitido = max(max_retroceso_ticks, (retroceso_pct_height / 100.0) * height_ticks)
            if max_retro > permitido:
                gate_counts[6] += 1
                continue

        if is_absorb:
            b_code = BUCKET_ABSORB
        elif avg_ms <= predator_avg_ms:
            b_code = BUCKET_PREDATOR
        elif avg_ms <= ultra_avg_ms:
            b_code = BUCKET_ULTRA
        else:
            b_code = BUCKET_FAST

        accepted_idx[n_ok] = i
        bucket_codes[n_ok] = b_code
        n_ok += 1

    return accepted_idx[:n_ok], bucket_codes[:n_ok], gate_counts


# ==============================================================================
# CAPA 2: DETECTOR CAUSAL DE CLUSTERS HFT (NUMBA)
# ==============================================================================

@njit(cache=True)
def _percentil_lineal_nb(arr: np.ndarray, n: int, p: float) -> float:
    """Espejo exacto de `Percentil(List<double> v, double p)` en `HFTZonesNQRangosPctV2.cs`."""
    if n <= 0:
        return 0.0
    sub = np.sort(arr[:n])
    p_clamped = max(0.0, min(100.0, p))
    pos = (p_clamped / 100.0) * float(n - 1)
    k = int(math.floor(pos))
    frac = pos - float(k)
    if k + 1 < n:
        return sub[k] * (1.0 - frac) + sub[k + 1] * frac
    return sub[k]


@njit(cache=True)
def evaluar_clusters_causales_nb(
    z_detect_bar: np.ndarray,
    z_detect_ts: np.ndarray,
    z_lower_tk: np.ndarray,
    z_upper_tk: np.ndarray,
    z_total_vol: np.ndarray,
    z_direction: np.ndarray,
    z_bucket: np.ndarray,
    z_session_id: np.ndarray,
    z_escala_vol_ticks: np.ndarray,
    tick_size: float = 0.25,
    mostrar_absorb: bool = True,
    extension_dibujo: int = 400,
    pct_extension_bars: int = 300,
    min_zonas_cluster: int = 4,
    min_packing: float = 0.70,
    max_span_mult: float = 3.2,
    min_span_floor_ticks: float = 88.0,
    max_join_gap_ratio: float = 0.35,
    polaridad_min: float = 0.0,
    pct_angosto: float = 10.0,
    clusters_por_sesion: float = 1.5,
    pct_min_historia: int = 25,
    modo_compresion: int = MODO_V2_HIBRIDO,
    inmutable_en_detect: bool = False,
):
    """Espejo exacto en Numba de `EvaluarClusterCausal` en `HFTZonesNQRangosPctV2.cs`.

    Garantía de Causalidad (0 Look-Ahead):
      - Cuando se evalúa la zona `idx` en `detect_bar = z_detect_bar[idx]`, sólo pueden
        participar zonas `j <= idx` con `z_detect_bar[j] <= detect_bar` y
        `z_detect_bar[j] + extension_dibujo >= detect_bar`.
      - Todo cluster emitido tiene `DetectBar = detect_bar` (el punto exacto en que se
        completó la K-ésima zona de la confluencia) y se proyecta hacia adelante hasta
        `VisualEndBar = detect_bar + pct_extension_bars`.

    Devuelve `(clus_int, clus_flt)`:
      - `clus_int` (N_clus, 6) int64:
          0: detect_bar
          1: visual_end_bar
          2: detect_ts_ns
          3: zone_count
          4: net_dir (-1, 0, +1 según sesgo de volumen direccional de las zonas del cluster)
          5: trigger_zone_idx
      - `clus_flt` (N_clus, 7) float64:
          0: lower (precio)
          1: upper (precio)
          2: poc_price (precio ponderado por volumen de las zonas de la pila)
          3: width_ticks
          4: packing (sumH / spanPrice)
          5: score (puntaje de compresión: menor = más compacto/intenso)
          6: polaridad (|sum(dir * vol)| / sum(vol) en [0, 1])
    """
    n_z = len(z_detect_bar)
    if n_z == 0:
        return np.empty((0, 6), dtype=np.int64), np.empty((0, 7), dtype=np.float64)

    cap = max(32, n_z // 2 + 4)
    clus_int = np.empty((cap, 6), dtype=np.int64)
    clus_flt = np.empty((cap, 7), dtype=np.float64)
    n_clus = 0

    max_hist = 600
    hist_score = np.empty(max_hist, dtype=np.float64)
    n_hist = 0

    escala_vol_zona_mean = 40.0
    sesiones_vistas = 0
    ult_ses = -1

    k_req = max(2, int(min_zonas_cluster))
    ext_viva = max(1, int(extension_dibujo))
    ext_pct = max(10, int(pct_extension_bars))

    # Buffers prealocados para las zonas vivas en cada evaluación
    vivas_idx = np.empty(n_z, dtype=np.int64)
    vivas_mid2 = np.empty(n_z, dtype=np.float64)

    for idx in range(n_z):
        ses_cur = int(z_session_id[idx])
        if ses_cur != ult_ses:
            ult_ses = ses_cur
            sesiones_vistas += 1

        z_vol = max(20.0, float(z_total_vol[idx]))
        escala_vol_zona_mean = 0.96 * escala_vol_zona_mean + 0.04 * z_vol

        if (not mostrar_absorb) and z_bucket[idx] == BUCKET_ABSORB:
            continue

        detect_bar = int(z_detect_bar[idx])
        min_detect_viva = detect_bar - ext_viva

        # 1) Reunir zonas vivas en detect_bar (sólo j <= idx)
        n_vivas = 0
        for j in range(idx, -1, -1):
            db_j = int(z_detect_bar[j])
            if db_j < min_detect_viva:
                break
            if (not mostrar_absorb) and z_bucket[j] == BUCKET_ABSORB:
                continue
            if db_j <= detect_bar and (db_j + ext_viva) >= detect_bar:
                vivas_idx[n_vivas] = j
                vivas_mid2[n_vivas] = float(z_lower_tk[j] + z_upper_tk[j]) * tick_size
                n_vivas += 1

        if n_vivas < k_req:
            continue

        # 2) Ordenar zonas vivas por precio medio ascendente (con desempate estable)
        order = np.argsort(vivas_mid2[:n_vivas], kind="mergesort")
        pos = -1
        for p_i in range(n_vivas):
            if vivas_idx[order[p_i]] == idx:
                pos = p_i
                break
        if pos < 0:
            continue

        escala_vol_tk = max(16.0, float(z_escala_vol_ticks[idx]))
        max_allowed_span_price = max(min_span_floor_ticks, escala_vol_tk * max_span_mult) * tick_size

        mejor_score = 1e308
        best_lo = 0.0
        best_hi = 0.0
        best_poc = 0.0
        best_packing = 0.0
        best_polaridad = 0.0
        best_net_dir = 0
        best_count = 0

        start_min = max(0, pos - k_req + 1)
        for start_idx in range(start_min, pos + 1):
            if start_idx + k_req > n_vivas:
                break
            i0 = start_idx
            i1 = start_idx + k_req - 1
            lo = 1e308
            hi = -1e308
            sum_h = 0.0
            total_band_vol = 0.0
            total_weighted_mid = 0.0
            signed_band_vol = 0.0

            for j_ord in range(i0, i1 + 1):
                zj = vivas_idx[order[j_ord]]
                w_lo = float(min(z_lower_tk[zj], z_upper_tk[zj])) * tick_size
                w_hi = float(max(z_lower_tk[zj], z_upper_tk[zj])) * tick_size
                if w_lo < lo:
                    lo = w_lo
                if w_hi > hi:
                    hi = w_hi
                h_z = max(tick_size * 2.0, w_hi - w_lo)
                sum_h += h_z
                v = max(1.0, float(z_total_vol[zj]))
                total_band_vol += v
                total_weighted_mid += ((w_lo + w_hi) * 0.5) * v
                signed_band_vol += float(z_direction[zj]) * v

            avg_zone_height = sum_h / float(k_req)
            max_join_gap = max(tick_size * 4.0, avg_zone_height * max_join_gap_ratio)

            # Expandir la pila contigua sobre la lista ya ordenada por precio medio
            expanded = True
            while expanded:
                expanded = False
                if i0 > 0:
                    z_prev = vivas_idx[order[i0 - 1]]
                    p_lo = float(min(z_lower_tk[z_prev], z_upper_tk[z_prev])) * tick_size
                    p_hi = float(max(z_lower_tk[z_prev], z_upper_tk[z_prev])) * tick_size
                    new_lo = min(lo, p_lo)
                    new_hi = max(hi, p_hi)
                    if p_hi >= lo - max_join_gap and (new_hi - new_lo) <= max_allowed_span_price:
                        lo = new_lo
                        hi = new_hi
                        i0 -= 1
                        sum_h += max(tick_size * 2.0, p_hi - p_lo)
                        v = max(1.0, float(z_total_vol[z_prev]))
                        total_band_vol += v
                        total_weighted_mid += ((p_lo + p_hi) * 0.5) * v
                        signed_band_vol += float(z_direction[z_prev]) * v
                        expanded = True
                if i1 + 1 < n_vivas:
                    z_next = vivas_idx[order[i1 + 1]]
                    n_lo = float(min(z_lower_tk[z_next], z_upper_tk[z_next])) * tick_size
                    n_hi = float(max(z_lower_tk[z_next], z_upper_tk[z_next])) * tick_size
                    new_lo = min(lo, n_lo)
                    new_hi = max(hi, n_hi)
                    if n_lo <= hi + max_join_gap and (new_hi - new_lo) <= max_allowed_span_price:
                        lo = new_lo
                        hi = new_hi
                        i1 += 1
                        sum_h += max(tick_size * 2.0, n_hi - n_lo)
                        v = max(1.0, float(z_total_vol[z_next]))
                        total_band_vol += v
                        total_weighted_mid += ((n_lo + n_hi) * 0.5) * v
                        signed_band_vol += float(z_direction[z_next]) * v
                        expanded = True

            m_total = i1 - i0 + 1
            span_price = max(tick_size * 2.0, hi - lo)
            if span_price > max_allowed_span_price:
                continue

            packing = sum_h / span_price
            if packing < min_packing:
                continue

            polaridad = abs(signed_band_vol) / max(1.0, total_band_vol)
            if polaridad < polaridad_min:
                continue

            span_ticks = span_price / tick_size
            avg_zone_ticks = max(6.0, (sum_h / float(m_total)) / tick_size)
            paso_norm = (span_ticks / float(m_total)) / avg_zone_ticks
            gap_libre_ticks = max(0.0, span_price - sum_h * 0.75) / tick_size
            gap_norm = (gap_libre_ticks / float(m_total)) / avg_zone_ticks

            bonus_zonas = math.pow(float(m_total) / float(k_req), 0.80)
            bonus_pack = math.sqrt(max(0.6, packing))
            vol_ratio = (total_band_vol / float(m_total)) / max(10.0, escala_vol_zona_mean)
            bonus_vol = 1.0 + 0.15 * min(3.0, vol_ratio)
            score = (paso_norm + 0.65 * gap_norm) / (bonus_zonas * bonus_pack * bonus_vol)

            if score < mejor_score:
                mejor_score = score
                best_lo = lo
                best_hi = hi
                best_count = m_total
                best_packing = packing
                best_polaridad = polaridad
                best_net_dir = 1 if signed_band_vol > 0 else (-1 if signed_band_vol < 0 else 0)
                best_poc = (
                    (total_weighted_mid / total_band_vol)
                    if total_band_vol > 0.0
                    else ((lo + hi) * 0.5)
                )

        if mejor_score >= 1e307:
            continue

        best_width_ticks = (best_hi - best_lo) / tick_size

        # 3) Desduplicar / actualizar si ya hay un cluster activo solapado en detect_bar
        activo_idx = -1
        for c_i in range(n_clus - 1, -1, -1):
            c_det = clus_int[c_i, 0]
            if c_det < detect_bar - ext_pct * 3:
                break
            c_end = clus_int[c_i, 1]
            if c_end < detect_bar:
                continue
            c_lo = clus_flt[c_i, 0]
            c_hi = clus_flt[c_i, 1]
            if c_lo <= best_hi + tick_size * 2.0 and best_lo - tick_size * 2.0 <= c_hi:
                activo_idx = c_i
                break

        if activo_idx >= 0:
            if not inmutable_en_detect:
                c_cnt = clus_int[activo_idx, 3]
                c_sc = clus_flt[activo_idx, 5]
                c_lo = clus_flt[activo_idx, 0]
                c_hi = clus_flt[activo_idx, 1]
                if (
                    best_count > c_cnt
                    or mejor_score < c_sc
                    or best_lo < c_lo
                    or best_hi > c_hi
                ):
                    new_c_lo = min(c_lo, best_lo)
                    new_c_hi = max(c_hi, best_hi)
                    clus_flt[activo_idx, 0] = new_c_lo
                    clus_flt[activo_idx, 1] = new_c_hi
                    clus_flt[activo_idx, 2] = best_poc
                    clus_flt[activo_idx, 3] = (new_c_hi - new_c_lo) / tick_size
                    if best_packing > clus_flt[activo_idx, 4]:
                        clus_flt[activo_idx, 4] = best_packing
                    if mejor_score < c_sc:
                        clus_flt[activo_idx, 5] = mejor_score
                    clus_flt[activo_idx, 6] = best_polaridad
                    clus_int[activo_idx, 1] = max(clus_int[activo_idx, 1], detect_bar + ext_pct)
                    clus_int[activo_idx, 3] = max(c_cnt, best_count)
                    clus_int[activo_idx, 4] = best_net_dir
            continue

        # 4) Registrar en historia acotada de formaciones distintas
        if n_hist < max_hist:
            hist_score[n_hist] = mejor_score
            n_hist += 1
        else:
            for h_i in range(max_hist - 1):
                hist_score[h_i] = hist_score[h_i + 1]
            hist_score[max_hist - 1] = mejor_score

        # 5) Compuerta de confirmación según modo_compresion
        if modo_compresion == MODO_V2_HIBRIDO:
            alta_confluencia = (best_count >= k_req + 1 and best_packing >= 1.35) or (
                best_count >= k_req and best_packing >= 1.65
            )
            if not alta_confluencia:
                if n_hist < max(6, pct_min_historia // 2):
                    continue
                frac_ses = (
                    max(0.5, clusters_por_sesion)
                    * float(max(1, sesiones_vistas))
                    / float(max(1, n_hist))
                )
                pct_ef = max(pct_angosto, min(35.0, 100.0 * frac_ses))
                umbral = _percentil_lineal_nb(hist_score, n_hist, max(5.0, pct_ef))
                if mejor_score > umbral:
                    continue
        elif modo_compresion == MODO_PERCENTIL_CAUSAL:
            if n_hist < max(6, pct_min_historia // 2):
                continue
            umbral = _percentil_lineal_nb(hist_score, n_hist, max(5.0, pct_angosto))
            if mejor_score > umbral:
                continue
        # En MODO_PACKING_PURO, ya superó min_zonas_cluster, min_packing, max_allowed_span_price y polaridad_min

        if n_clus >= cap:
            new_cap = cap * 2
            new_int = np.empty((new_cap, 6), dtype=np.int64)
            new_flt = np.empty((new_cap, 7), dtype=np.float64)
            new_int[:n_clus] = clus_int[:n_clus]
            new_flt[:n_clus] = clus_flt[:n_clus]
            clus_int = new_int
            clus_flt = new_flt
            cap = new_cap

        clus_int[n_clus, 0] = detect_bar
        clus_int[n_clus, 1] = detect_bar + ext_pct
        clus_int[n_clus, 2] = z_detect_ts[idx]
        clus_int[n_clus, 3] = best_count
        clus_int[n_clus, 4] = best_net_dir
        clus_int[n_clus, 5] = idx

        clus_flt[n_clus, 0] = best_lo
        clus_flt[n_clus, 1] = best_hi
        clus_flt[n_clus, 2] = best_poc
        clus_flt[n_clus, 3] = best_width_ticks
        clus_flt[n_clus, 4] = best_packing
        clus_flt[n_clus, 5] = mejor_score
        clus_flt[n_clus, 6] = best_polaridad
        n_clus += 1

    return clus_int[:n_clus], clus_flt[:n_clus]


# ==============================================================================
# CAPA 3: DETECTOR CAUSAL DE EXPANSIONES SIN HFT (NUMBA)
# ==============================================================================

@njit(cache=True)
def _recortar_expansiones_solapadas_nb(
    exp_int: np.ndarray,
    exp_flt: np.ndarray,
    n_exp: int,
    actual_idx: int,
    ext_pct: int,
    tick_size: float,
):
    if actual_idx < 0 or actual_idx >= n_exp:
        return
    act_det = exp_int[actual_idx, 0]
    act_lo = exp_flt[actual_idx, 0]
    act_hi = exp_flt[actual_idx, 1]
    min_bar = act_det - max(10, ext_pct) * 3
    for i in range(n_exp - 1, -1, -1):
        if i == actual_idx:
            continue
        prev_det = exp_int[i, 0]
        if prev_det < min_bar:
            break
        prev_end = exp_int[i, 1]
        if prev_end <= act_det:
            continue
        prev_lo = exp_flt[i, 0]
        prev_hi = exp_flt[i, 1]
        ov = min(prev_hi, act_hi) - max(prev_lo, act_lo)
        if ov >= -tick_size:
            exp_int[i, 1] = min(prev_end, act_det)


@njit(cache=True)
def evaluar_expansiones_causales_nb(
    bar_ts_ns: np.ndarray,
    bar_high: np.ndarray,
    bar_low: np.ndarray,
    bar_close: np.ndarray,
    bar_session_id: np.ndarray,
    z_detect_bar: np.ndarray,
    z_lower_tk: np.ndarray,
    z_upper_tk: np.ndarray,
    z_bucket: np.ndarray,
    tick_size: float = 0.25,
    mostrar_absorb: bool = True,
    pct_amplio: float = 5.0,
    exp_por_sesion: float = 1.2,
    min_exp_ticks: float = 24.0,
    zigzag_ticks: float = 40.0,
    pct_min_historia: int = 25,
    pct_extension_bars: int = 300,
):
    """Espejo exacto en Numba de `NotificarZonaNuevaEnImpulso` + `ActualizarImpulsoYExpansionCausal`
    en `HFTZonesNQRangosPctV2.cs`.

    Devuelve `(exp_int, exp_flt, escala_vol_por_barra)`:
      - `exp_int` (N_exp, 5) int64:
          0: detect_bar (permanece fijo aunque la expansión crezca en barras siguientes)
          1: visual_end_bar (recortado si es mitigada >= 75% o solapada por una nueva)
          2: detect_ts_ns
          3: direction (-1 o +1)
          4: leg_id
      - `exp_flt` (N_exp, 5) float64:
          0: lower
          1: upper
          2: mid_price
          3: height_ticks
          4: efficiency
      - `escala_vol_por_barra` (N_bars,) float64: escala causal de volatilidad en cada barra.
    """
    n_bars = len(bar_close)
    n_zones = len(z_detect_bar)
    escala_vol_arr = np.full(n_bars, 24.0, dtype=np.float64)
    if n_bars == 0:
        return (
            np.empty((0, 5), dtype=np.int64),
            np.empty((0, 5), dtype=np.float64),
            escala_vol_arr,
        )

    cap = max(32, n_bars // 16 + 4)
    exp_int = np.empty((cap, 5), dtype=np.int64)
    exp_flt = np.empty((cap, 5), dtype=np.float64)
    n_exp = 0

    max_hist = 600
    hist_exp = np.empty(max_hist, dtype=np.float64)
    n_hist = 0
    cached_umbral_exp = 1e308
    umbral_dirty = True

    escala_vol_ticks = 24.0
    primera_sin_evaluar = 0
    sesiones_vistas = 0
    ult_ses = -1

    imp_dir = 0
    imp_start_bar = 0
    imp_ext_bar = 0
    imp_leg_id = 0
    imp_start_price = 0.0
    imp_ext_price = 0.0
    imp_sum_range = 0.0
    imp_best_score = 0.0
    imp_active_idx = -1

    ext_pct = max(10, int(pct_extension_bars))

    for b in range(n_bars):
        h = float(bar_high[b])
        l = float(bar_low[b])
        c = float(bar_close[b])
        bar_range_ticks = (h - l) / tick_size
        if bar_range_ticks > 0.0:
            target_scale = max(16.0, bar_range_ticks * 2.5)
            escala_vol_ticks = 0.98 * escala_vol_ticks + 0.02 * target_scale
        escala_vol_arr[b] = escala_vol_ticks

        if b < 2:
            continue

        ses_b = int(bar_session_id[b])
        if ses_b != ult_ses:
            if imp_best_score > 0.15:
                if n_hist < max_hist:
                    hist_exp[n_hist] = imp_best_score
                    n_hist += 1
                else:
                    for h_i in range(max_hist - 1):
                        hist_exp[h_i] = hist_exp[h_i + 1]
                    hist_exp[max_hist - 1] = imp_best_score
                umbral_dirty = True
            imp_best_score = 0.0
            imp_active_idx = -1
            ult_ses = ses_b
            sesiones_vistas += 1
            imp_dir = 0
            imp_start_bar = b
            imp_ext_bar = b
            imp_start_price = c
            imp_ext_price = c
            imp_sum_range = 0.0

        # 1) Procesar zonas recién confirmadas en o antes de la barra b
        while primera_sin_evaluar < n_zones:
            if int(z_detect_bar[primera_sin_evaluar]) > b:
                break
            z_idx = primera_sin_evaluar
            primera_sin_evaluar += 1
            if imp_dir == 0:
                continue
            if (not mostrar_absorb) and z_bucket[z_idx] == BUCKET_ABSORB:
                continue
            zl = float(min(z_lower_tk[z_idx], z_upper_tk[z_idx])) * tick_size
            zh = float(max(z_lower_tk[z_idx], z_upper_tk[z_idx])) * tick_size

            if imp_dir == 1:
                if zh >= imp_start_price and zl <= imp_ext_price + tick_size * 2.0:
                    if (
                        imp_active_idx >= 0
                        and exp_int[imp_active_idx, 4] == imp_leg_id
                        and zl > exp_flt[imp_active_idx, 0] + tick_size * 4.0
                    ):
                        new_up = max(exp_flt[imp_active_idx, 1], zl)
                        exp_flt[imp_active_idx, 1] = new_up
                        exp_flt[imp_active_idx, 2] = (exp_flt[imp_active_idx, 0] + new_up) * 0.5
                        exp_flt[imp_active_idx, 3] = (new_up - exp_flt[imp_active_idx, 0]) / tick_size
                        _recortar_expansiones_solapadas_nb(
                            exp_int, exp_flt, n_exp, imp_active_idx, ext_pct, tick_size
                        )
                    if imp_best_score > 0.15:
                        if n_hist < max_hist:
                            hist_exp[n_hist] = imp_best_score
                            n_hist += 1
                        else:
                            for h_i in range(max_hist - 1):
                                hist_exp[h_i] = hist_exp[h_i + 1]
                            hist_exp[max_hist - 1] = imp_best_score
                        umbral_dirty = True
                    imp_best_score = 0.0
                    imp_active_idx = -1
                    imp_start_price = zh
                    imp_ext_price = max(zh, h)
                    imp_start_bar = b
                    imp_ext_bar = b
                    imp_sum_range = max(tick_size, h - l)
                    imp_leg_id += 1
            elif imp_dir == -1:
                if zl <= imp_start_price and zh >= imp_ext_price - tick_size * 2.0:
                    if (
                        imp_active_idx >= 0
                        and exp_int[imp_active_idx, 4] == imp_leg_id
                        and zh < exp_flt[imp_active_idx, 1] - tick_size * 4.0
                    ):
                        new_lo = min(exp_flt[imp_active_idx, 0], zh)
                        exp_flt[imp_active_idx, 0] = new_lo
                        exp_flt[imp_active_idx, 2] = (new_lo + exp_flt[imp_active_idx, 1]) * 0.5
                        exp_flt[imp_active_idx, 3] = (exp_flt[imp_active_idx, 1] - new_lo) / tick_size
                        _recortar_expansiones_solapadas_nb(
                            exp_int, exp_flt, n_exp, imp_active_idx, ext_pct, tick_size
                        )
                    if imp_best_score > 0.15:
                        if n_hist < max_hist:
                            hist_exp[n_hist] = imp_best_score
                            n_hist += 1
                        else:
                            for h_i in range(max_hist - 1):
                                hist_exp[h_i] = hist_exp[h_i + 1]
                            hist_exp[max_hist - 1] = imp_best_score
                        umbral_dirty = True
                    imp_best_score = 0.0
                    imp_active_idx = -1
                    imp_start_price = zl
                    imp_ext_price = min(zl, l)
                    imp_start_bar = b
                    imp_ext_bar = b
                    imp_sum_range = max(tick_size, h - l)
                    imp_leg_id += 1

        # 2) Mitigar expansiones previas selladas si el precio rellenó >= 75% de su rango
        bar_rng = max(tick_size, h - l)
        min_bar_activa = b - ext_pct * 3
        for e_i in range(n_exp - 1, -1, -1):
            if exp_int[e_i, 0] < min_bar_activa:
                break
            if e_i == imp_active_idx:
                continue
            if exp_int[e_i, 1] <= b:
                continue
            e_lo = exp_flt[e_i, 0]
            e_hi = exp_flt[e_i, 1]
            span = e_hi - e_lo
            if span <= tick_size:
                continue
            e_dir = exp_int[e_i, 3]
            if e_dir == -1 and h >= e_lo + 0.75 * span:
                exp_int[e_i, 1] = b
            elif e_dir == 1 and l <= e_hi - 0.75 * span:
                exp_int[e_i, 1] = b

        # 3) Seguimiento de la pierna actual con giro local adaptativo
        giro_ticks = max(12.0, min(max(12.0, zigzag_ticks), escala_vol_ticks * 2.2))
        giro_req = giro_ticks * tick_size

        if imp_dir == 0:
            if imp_start_price == 0.0:
                imp_start_price = c
                imp_ext_price = c
                imp_start_bar = b
                imp_ext_bar = b
                continue
            imp_sum_range += bar_rng
            if h - imp_start_price >= giro_req:
                imp_dir = 1
                imp_ext_price = h
                imp_ext_bar = b
                imp_leg_id += 1
            elif imp_start_price - l >= giro_req:
                imp_dir = -1
                imp_ext_price = l
                imp_ext_bar = b
                imp_leg_id += 1
            continue

        nuevo_extremo = False
        if imp_dir == 1:
            if h >= imp_ext_price:
                imp_ext_price = h
                imp_ext_bar = b
                imp_sum_range += bar_rng
                nuevo_extremo = True
            elif imp_ext_price - l >= giro_req:
                if imp_best_score > 0.15:
                    if n_hist < max_hist:
                        hist_exp[n_hist] = imp_best_score
                        n_hist += 1
                    else:
                        for h_i in range(max_hist - 1):
                            hist_exp[h_i] = hist_exp[h_i + 1]
                        hist_exp[max_hist - 1] = imp_best_score
                    umbral_dirty = True
                imp_best_score = 0.0
                imp_active_idx = -1
                imp_start_price = imp_ext_price
                imp_start_bar = imp_ext_bar
                imp_dir = -1
                imp_ext_price = l
                imp_ext_bar = b
                imp_sum_range = bar_rng
                imp_leg_id += 1
                nuevo_extremo = True
            else:
                imp_sum_range += bar_rng
        else:
            if l <= imp_ext_price:
                imp_ext_price = l
                imp_ext_bar = b
                imp_sum_range += bar_rng
                nuevo_extremo = True
            elif h - imp_ext_price >= giro_req:
                if imp_best_score > 0.15:
                    if n_hist < max_hist:
                        hist_exp[n_hist] = imp_best_score
                        n_hist += 1
                    else:
                        for h_i in range(max_hist - 1):
                            hist_exp[h_i] = hist_exp[h_i + 1]
                        hist_exp[max_hist - 1] = imp_best_score
                    umbral_dirty = True
                imp_best_score = 0.0
                imp_active_idx = -1
                imp_start_price = imp_ext_price
                imp_start_bar = imp_ext_bar
                imp_dir = 1
                imp_ext_price = h
                imp_ext_bar = b
                imp_sum_range = bar_rng
                imp_leg_id += 1
                nuevo_extremo = True
            else:
                imp_sum_range += bar_rng

        if not nuevo_extremo:
            continue

        lo = min(imp_start_price, imp_ext_price)
        hi = max(imp_start_price, imp_ext_price)
        disp_ticks = (hi - lo) / tick_size
        if disp_ticks < 6.0:
            continue

        # 4) Corredor libre de zonas HFT en la frontera líder [imp_start_bar .. b]
        g_lo = lo
        g_hi = hi
        bloqueado = False
        for j in range(primera_sin_evaluar - 1, -1, -1):
            z_db = int(z_detect_bar[j])
            if z_db < imp_start_bar - 15:
                break
            if z_db > b:
                continue
            if (not mostrar_absorb) and z_bucket[j] == BUCKET_ABSORB:
                continue
            zl = float(min(z_lower_tk[j], z_upper_tk[j])) * tick_size
            zh = float(max(z_lower_tk[j], z_upper_tk[j])) * tick_size
            if zh < lo or zl > hi:
                continue
            if imp_dir == 1:
                if zl <= hi and zh >= hi - tick_size:
                    bloqueado = True
                    break
                if zh > g_lo and zh < hi:
                    g_lo = zh
            else:
                if zh >= lo and zl <= lo + tick_size:
                    bloqueado = True
                    break
                if zl < g_hi and zl > lo:
                    g_hi = zl

        if bloqueado:
            continue

        if imp_active_idx >= 0 and exp_int[imp_active_idx, 4] == imp_leg_id:
            if imp_dir == 1:
                g_lo = exp_flt[imp_active_idx, 0]
                g_hi = max(exp_flt[imp_active_idx, 1], g_hi)
            else:
                g_hi = exp_flt[imp_active_idx, 1]
                g_lo = min(exp_flt[imp_active_idx, 0], g_lo)

        mejor_gap = g_hi - g_lo
        gap_ticks = mejor_gap / tick_size
        if gap_ticks < 6.0:
            continue

        net_move = abs(imp_ext_price - imp_start_price)
        eficiencia = min(1.0, net_move / max(net_move, imp_sum_range * 0.45))
        alto_norm = gap_ticks / max(6.0, escala_vol_ticks)
        score_exp = alto_norm * (0.55 + 0.45 * eficiencia)

        if score_exp > imp_best_score:
            imp_best_score = score_exp

        if gap_ticks < max(8.0, min_exp_ticks):
            continue

        # Si ya estaba activa en esta pierna, actualizar in-place manteniendo DetectBar fijo
        if imp_active_idx >= 0 and exp_int[imp_active_idx, 4] == imp_leg_id:
            exp_flt[imp_active_idx, 0] = g_lo
            exp_flt[imp_active_idx, 1] = g_hi
            exp_flt[imp_active_idx, 2] = (g_lo + g_hi) * 0.5
            exp_flt[imp_active_idx, 3] = gap_ticks
            exp_flt[imp_active_idx, 4] = eficiencia
            exp_int[imp_active_idx, 1] = max(exp_int[imp_active_idx, 1], b + ext_pct)
            _recortar_expansiones_solapadas_nb(
                exp_int, exp_flt, n_exp, imp_active_idx, ext_pct, tick_size
            )
            continue

        if n_hist < max(6, pct_min_historia):
            continue

        if umbral_dirty:
            frac = min(
                pct_amplio / 100.0,
                max(0.1, exp_por_sesion) * float(max(1, sesiones_vistas)) / float(n_hist),
            )
            cached_umbral_exp = _percentil_lineal_nb(hist_exp, n_hist, 100.0 * (1.0 - frac))
            umbral_dirty = False

        if score_exp < cached_umbral_exp:
            continue

        # Evitar expansión redundante contenida en una expansión activa opuesta reciente
        redundante = False
        for e_i in range(n_exp - 1, -1, -1):
            if exp_int[e_i, 0] < b - 45:
                break
            if exp_int[e_i, 1] <= b:
                continue
            inter = min(exp_flt[e_i, 1], g_hi) - max(exp_flt[e_i, 0], g_lo)
            if inter > 0.0 and inter >= 0.70 * mejor_gap and (b - exp_int[e_i, 0]) < 40:
                exp_int[e_i, 1] = b
                redundante = True
                break
        if redundante:
            continue

        if n_exp >= cap:
            new_cap = cap * 2
            new_int = np.empty((new_cap, 5), dtype=np.int64)
            new_flt = np.empty((new_cap, 5), dtype=np.float64)
            new_int[:n_exp] = exp_int[:n_exp]
            new_flt[:n_exp] = exp_flt[:n_exp]
            exp_int = new_int
            exp_flt = new_flt
            cap = new_cap

        exp_int[n_exp, 0] = b
        exp_int[n_exp, 1] = b + ext_pct
        exp_int[n_exp, 2] = bar_ts_ns[b]
        exp_int[n_exp, 3] = imp_dir
        exp_int[n_exp, 4] = imp_leg_id

        exp_flt[n_exp, 0] = g_lo
        exp_flt[n_exp, 1] = g_hi
        exp_flt[n_exp, 2] = (g_lo + g_hi) * 0.5
        exp_flt[n_exp, 3] = gap_ticks
        exp_flt[n_exp, 4] = eficiencia

        imp_active_idx = n_exp
        n_exp += 1
        _recortar_expansiones_solapadas_nb(
            exp_int, exp_flt, n_exp, imp_active_idx, ext_pct, tick_size
        )

    return exp_int[:n_exp], exp_flt[:n_exp], escala_vol_arr


# ==============================================================================
# INTERFAZ DE ALTO NIVEL Y PARIDAD CON `hftzones_nq`
# ==============================================================================

def candidatos_nb_a_dicts(cand_int: np.ndarray, cand_flt: np.ndarray) -> list[dict[str, Any]]:
    """Convierte las matrices `(cand_int, cand_flt)` al formato exacto de `hftzones_nq.detect_candidates`."""
    out: list[dict[str, Any]] = []
    n_c = len(cand_int)
    for i in range(n_c):
        r_code = int(cand_int[i, 6])
        out.append(
            dict(
                idx_start=int(cand_int[i, 0]),
                idx_end=int(cand_int[i, 1]),
                ts_start=int(cand_int[i, 3]),
                ts_end=int(cand_int[i, 4]),
                ts_avail=int(cand_int[i, 5]),
                termination_reason=REASON_CODE_TO_STR.get(r_code, "CENSORED_END_OF_INPUT"),
                direction=int(cand_int[i, 7]),
                pasos=int(cand_int[i, 8]),
                valid_steps=int(cand_int[i, 9]),
                sw_hi_tk=int(cand_int[i, 10]),
                sw_lo_tk=int(cand_int[i, 11]),
                height_ticks=float(cand_flt[i, 0]),
                total_ms=float(cand_flt[i, 1]),
                n_intervals=int(cand_int[i, 12]),
                avg_ms=float(cand_flt[i, 2]),
                total_vol=float(cand_flt[i, 3]),
                vol_rate=float(cand_flt[i, 4]),
                max_retro_ticks=float(cand_flt[i, 5]),
                cvd=float(cand_flt[i, 6]),
                buy_vol=float(cand_flt[i, 7]),
                sell_vol=float(cand_flt[i, 8]),
                max_tick_vol=float(cand_flt[i, 9]),
                delta_slope=float(cand_flt[i, 10]),
                delta_first=float(cand_flt[i, 11]),
                delta_second=float(cand_flt[i, 12]),
                no_move_ticks=int(cand_int[i, 13]),
                no_move_vol=float(cand_flt[i, 13]),
                max_level_ticks=int(cand_int[i, 14]),
            )
        )
    return out


def detect_candidates(
    ts_ns,
    price_ticks,
    volume,
    params: dict[str, Any] | None = None,
    prev_session_close_ticks: int | None = None,
    session_ids: np.ndarray | None = None,
    prim_bar_of_tick: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    """Drop-in replacement acelerado con Numba para `hftzones_nq.detect_candidates`."""
    p = dict(DEFAULTS_V2)
    if params:
        p.update({k: v for k, v in params.items() if v is not None})
    if int(p["tick_resolution"]) != 1:
        raise NotImplementedError("Solo tick_resolution=1 está soportado.")

    ts_arr = np.asarray(ts_ns, dtype=np.int64)
    px_arr = np.asarray(price_ticks, dtype=np.int64)
    vol_arr = np.asarray(volume, dtype=np.float64)
    n = len(px_arr)
    if session_ids is None:
        ses_arr = np.zeros(n, dtype=np.int64)
    else:
        ses_arr = np.asarray(session_ids, dtype=np.int64)
    if prim_bar_of_tick is None:
        pbar_arr = np.arange(n, dtype=np.int64)
    else:
        pbar_arr = np.asarray(prim_bar_of_tick, dtype=np.int64)

    has_prev = prev_session_close_ticks is not None
    prev_tk = int(prev_session_close_ticks) if has_prev else 0

    c_int, c_flt = detectar_candidatos_nb(
        ts_arr,
        px_arr,
        vol_arr,
        ses_arr,
        pbar_arr,
        max_pausa_ms=float(p["max_pausa_ms"]),
        retro_floor_ticks=float(hz_base.ACCEPT_DEFAULTS["max_retroceso_ticks"]),
        retro_pct_height=float(hz_base.ACCEPT_DEFAULTS["retroceso_pct_height"]),
        has_prev_session_close=has_prev,
        prev_session_close_ticks=prev_tk,
    )
    return candidatos_nb_a_dicts(c_int, c_flt)


def accept_all(candidates, thresholds: dict[str, Any] | None = None, tick_size: float = 0.25):
    """Compatibilidad directa con `hftzones_nq.accept_all`."""
    return hz_base.accept_all(candidates, thresholds=thresholds, tick_size=tick_size)


def construir_barras_ticks(
    ts_ns: np.ndarray,
    price_ticks: np.ndarray,
    session_ids: np.ndarray,
    ticks_per_bar: int = 5,
    tick_size: float = 0.25,
):
    """Agrupa el stream 1-tick en barras primarias de `ticks_per_bar` ticks (con reinicio por sesión)."""
    n = len(price_ticks)
    if n == 0:
        return (
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.float64),
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
        )
    tpb = max(1, int(ticks_per_bar))
    prim_bar_of_tick = np.empty(n, dtype=np.int64)
    max_bars = n // tpb + len(np.unique(session_ids)) + 4
    bar_ts_ns = np.empty(max_bars, dtype=np.int64)
    bar_high = np.empty(max_bars, dtype=np.float64)
    bar_low = np.empty(max_bars, dtype=np.float64)
    bar_close = np.empty(max_bars, dtype=np.float64)
    bar_ses = np.empty(max_bars, dtype=np.int64)

    b_idx = 0
    cnt = 0
    cur_ses = int(session_ids[0])
    cur_hi = float(price_ticks[0]) * tick_size
    cur_lo = cur_hi

    for i in range(n):
        s_i = int(session_ids[i])
        px = float(price_ticks[i]) * tick_size
        if s_i != cur_ses or cnt >= tpb:
            # Cerrar barra previa
            bar_ts_ns[b_idx] = ts_ns[i - 1]
            bar_high[b_idx] = cur_hi
            bar_low[b_idx] = cur_lo
            bar_close[b_idx] = float(price_ticks[i - 1]) * tick_size
            bar_ses[b_idx] = cur_ses
            b_idx += 1
            cur_ses = s_i
            cur_hi = px
            cur_lo = px
            cnt = 0
        else:
            if px > cur_hi:
                cur_hi = px
            if px < cur_lo:
                cur_lo = px
        prim_bar_of_tick[i] = b_idx
        cnt += 1

    if cnt > 0:
        bar_ts_ns[b_idx] = ts_ns[n - 1]
        bar_high[b_idx] = cur_hi
        bar_low[b_idx] = cur_lo
        bar_close[b_idx] = float(price_ticks[n - 1]) * tick_size
        bar_ses[b_idx] = cur_ses
        b_idx += 1

    return (
        bar_ts_ns[:b_idx],
        bar_high[:b_idx],
        bar_low[:b_idx],
        bar_close[:b_idx],
        bar_ses[:b_idx],
        prim_bar_of_tick,
    )


def ejecutar_indicador_v2(
    ts_ns: np.ndarray,
    price_ticks: np.ndarray,
    volume: np.ndarray,
    session_ids: np.ndarray | None = None,
    ticks_per_primary_bar: int = 5,
    tick_size: float = 0.25,
    params: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    """Ejecuta las tres capas causales de `HFTZonesNQRangosPctV2` sobre un stream 1-tick.

    Devuelve un dict con tres DataFrames causales:
      - `"zones"`: zonas HFT individuales aceptadas (con `detect_bar`, `ts_avail`, `lower`, `upper`, `bucket`, etc.)
      - `"clusters"`: clusters HFT causales (`detect_bar`, `visual_end_bar`, `t_ns`, `lo`, `hi`, `poc`, `n_zonas`, `width_ticks`, `packing`, `score`, `polaridad`, `net_dir`)
      - `"expansions"`: expansiones libres de HFT causales (`detect_bar`, `visual_end_bar`, `t_ns`, `lo`, `hi`, `mid`, `direction`, `height_ticks`, `efficiency`, `leg_id`)
    """
    p = dict(DEFAULTS_V2)
    if params:
        p.update({k: v for k, v in params.items() if v is not None})

    ts_arr = np.asarray(ts_ns, dtype=np.int64)
    px_arr = np.asarray(price_ticks, dtype=np.int64)
    vol_arr = np.asarray(volume, dtype=np.float64)
    n = len(px_arr)
    if session_ids is None:
        # Día UTC (ns // 86_400_000_000_000) como partición de sesión por defecto
        ses_arr = ts_arr // 86_400_000_000_000
    else:
        ses_arr = np.asarray(session_ids, dtype=np.int64)

    bar_ts, bar_hi, bar_lo, bar_cl, bar_ses, prim_bar_of_tick = construir_barras_ticks(
        ts_arr, px_arr, ses_arr, ticks_per_bar=ticks_per_primary_bar, tick_size=tick_size
    )

    cand_int, cand_flt = detectar_candidatos_nb(
        ts_arr,
        px_arr,
        vol_arr,
        ses_arr,
        prim_bar_of_tick,
        max_pausa_ms=float(p["max_pausa_ms"]),
        retro_floor_ticks=float(p["max_retroceso_ticks"]),
        retro_pct_height=float(p["retroceso_pct_height"]),
        has_prev_session_close=False,
        prev_session_close_ticks=0,
    )

    acc_idx, b_codes, _ = filtrar_zonas_nb(
        cand_int,
        cand_flt,
        min_pasos=int(p["min_pasos"]),
        min_absorb_pasos=int(p["min_absorb_pasos"]),
        detect_absorb=bool(p["detect_absorb"]),
        min_sweep_ticks=float(p["min_sweep_ticks"]),
        max_avg_ms=float(p["max_avg_ms"]),
        max_total_ms=float(p["max_total_ms"]),
        min_volume_rate=float(p["min_volume_rate"]),
        min_total_volume=float(p["min_total_volume"]),
        max_retroceso_ticks=float(p["max_retroceso_ticks"]),
        retroceso_pct_height=float(p["retroceso_pct_height"]),
        predator_avg_ms=float(p["predator_avg_ms"]),
        ultra_avg_ms=float(p["ultra_avg_ms"]),
    )

    z_int = cand_int[acc_idx]
    z_flt = cand_flt[acc_idx]
    z_detect_bar = z_int[:, 17]
    z_detect_ts = z_int[:, 5]
    z_hi_tk = z_int[:, 10]
    z_lo_tk = z_int[:, 11]
    z_dir = z_int[:, 7]
    z_vol = z_flt[:, 3]
    z_ses = ses_arr[z_int[:, 2]] if len(acc_idx) > 0 else np.empty(0, dtype=np.int64)

    # Ejecutar Capa 3 (Expansiones + evolución de escalaVolTicks por barra primaria)
    exp_int, exp_flt, escala_vol_arr = evaluar_expansiones_causales_nb(
        bar_ts,
        bar_hi,
        bar_lo,
        bar_cl,
        bar_ses,
        z_detect_bar,
        z_lo_tk,
        z_hi_tk,
        b_codes,
        tick_size=float(tick_size),
        mostrar_absorb=bool(p["detect_absorb"]),
        pct_amplio=float(p["pct_amplio"]),
        exp_por_sesion=float(p["exp_por_sesion"]),
        min_exp_ticks=float(p["min_exp_ticks"]),
        zigzag_ticks=float(p["zigzag_ticks"]),
        pct_min_historia=int(p["pct_min_historia"]),
        pct_extension_bars=int(p["pct_extension_bars"]),
    )

    z_escala = (
        escala_vol_arr[np.clip(z_detect_bar, 0, max(0, len(escala_vol_arr) - 1))]
        if len(z_detect_bar) > 0 and len(escala_vol_arr) > 0
        else np.full(len(z_detect_bar), 24.0, dtype=np.float64)
    )

    # Ejecutar Capa 2 (Clusters HFT causales)
    clus_int, clus_flt = evaluar_clusters_causales_nb(
        z_detect_bar,
        z_detect_ts,
        z_lo_tk,
        z_hi_tk,
        z_vol,
        z_dir,
        b_codes,
        z_ses,
        z_escala,
        tick_size=float(tick_size),
        mostrar_absorb=bool(p["detect_absorb"]),
        extension_dibujo=int(p["extension_dibujo"]),
        pct_extension_bars=int(p["pct_extension_bars"]),
        min_zonas_cluster=int(p["min_zonas_cluster"]),
        min_packing=float(p["min_packing"]),
        max_span_mult=float(p["max_span_mult"]),
        min_span_floor_ticks=float(p["min_span_floor_ticks"]),
        max_join_gap_ratio=float(p["max_join_gap_ratio"]),
        polaridad_min=float(p["polaridad_min"]),
        pct_angosto=float(p["pct_angosto"]),
        clusters_por_sesion=float(p["clusters_por_sesion"]),
        pct_min_historia=int(p["pct_min_historia"]),
        modo_compresion=int(p["modo_compresion"]),
    )

    df_zones = pd.DataFrame(
        {
            "start_bar": z_int[:, 15],
            "end_bar": z_int[:, 16],
            "detect_bar": z_detect_bar,
            "visual_end_bar": z_detect_bar + int(p["extension_dibujo"]),
            "ts_start": z_int[:, 3],
            "ts_end": z_int[:, 4],
            "ts_avail": z_detect_ts,
            "lower": z_lo_tk.astype(np.float64) * tick_size,
            "upper": z_hi_tk.astype(np.float64) * tick_size,
            "direction": z_dir,
            "bucket": [BUCKET_CODE_TO_STR[int(b)] for b in b_codes],
            "height_ticks": z_flt[:, 0],
            "total_ms": z_flt[:, 1],
            "avg_ms": z_flt[:, 2],
            "total_vol": z_vol,
            "vol_rate": z_flt[:, 4],
            "cvd": z_flt[:, 6],
        }
    )

    df_clusters = pd.DataFrame(
        {
            "detect_bar": clus_int[:, 0],
            "visual_end_bar": clus_int[:, 1],
            "t_ns": clus_int[:, 2],
            "n_zonas": clus_int[:, 3],
            "net_dir": clus_int[:, 4],
            "lo": clus_flt[:, 0],
            "hi": clus_flt[:, 1],
            "poc": clus_flt[:, 2],
            "width_ticks": clus_flt[:, 3],
            "packing": clus_flt[:, 4],
            "score": clus_flt[:, 5],
            "polaridad": clus_flt[:, 6],
        }
    )

    df_expansions = pd.DataFrame(
        {
            "detect_bar": exp_int[:, 0],
            "visual_end_bar": exp_int[:, 1],
            "t_ns": exp_int[:, 2],
            "direction": exp_int[:, 3],
            "leg_id": exp_int[:, 4],
            "lo": exp_flt[:, 0],
            "hi": exp_flt[:, 1],
            "mid": exp_flt[:, 2],
            "height_ticks": exp_flt[:, 3],
            "efficiency": exp_flt[:, 4],
        }
    )

    return {
        "zones": df_zones,
        "clusters": df_clusters,
        "expansions": df_expansions,
    }


def almacen_clusters_hft_grilla(
    ts_ns: np.ndarray,
    price_ticks: np.ndarray,
    volume: np.ndarray,
    session_ids: np.ndarray | None = None,
    ticks_per_primary_bar: int = 5,
    tick_size: float = 0.25,
    grilla_zona: dict[str, dict[str, Any]] | None = None,
    grilla_cluster: dict[str, dict[str, Any]] | None = None,
    inmutable_en_detect: bool = True,
) -> pd.DataFrame:
    """Genera en UNA SOLA PASADA por los ticks el almacén tabular de Clusters HFT causales
    para todas las combinaciones `(def_zona x def_cluster)`.

    Este almacén es directamente consumible por `U1` (tratando cada Cluster HFT causal
    como un Área directa con `[lo, hi, poc, t_ns]`, sin el cuello de botella de doble
    racimo de `U1-RACIMOS-GRILLA`).
    """
    gz = grilla_zona if grilla_zona is not None else GRILLA_ZONA_HFT
    gc = grilla_cluster if grilla_cluster is not None else GRILLA_CLUSTER_HFT

    ts_arr = np.asarray(ts_ns, dtype=np.int64)
    px_arr = np.asarray(price_ticks, dtype=np.int64)
    vol_arr = np.asarray(volume, dtype=np.float64)
    n = len(px_arr)
    if session_ids is None:
        # K8 (2026-11-10): el día UTC NO es la sesión CME (corta rachas y cuenta sesiones mal). Para research pasar `trade_date`.
        raise ValueError("almacen_clusters_hft_grilla: falta session_ids (sesión CME, p. ej. trade_date del release); el día UTC no se usa")
    else:
        ses_arr = np.asarray(session_ids, dtype=np.int64)

    bar_ts, bar_hi, bar_lo, bar_cl, bar_ses, prim_bar_of_tick = construir_barras_ticks(
        ts_arr, px_arr, ses_arr, ticks_per_bar=ticks_per_primary_bar, tick_size=tick_size
    )

    # Escala causal de volatilidad por barra primaria (independiente de los umbrales de zona)
    n_bars = len(bar_cl)
    escala_vol_arr = np.full(n_bars, 24.0, dtype=np.float64)
    esc = 24.0
    for b in range(n_bars):
        escala_vol_arr[b] = esc          # K8 (2026-11-10): escala conocida AL ABRIR la barra b; antes incluía ticks posteriores a la detección
        rng_tk = (bar_hi[b] - bar_lo[b]) / tick_size
        if rng_tk > 0.0:
            esc = 0.98 * esc + 0.02 * max(16.0, rng_tk * 2.5)

    # 1) ÚNICA pasada 1-tick: censo completo de candidatos
    cand_int, cand_flt = detectar_candidatos_nb(
        ts_arr,
        px_arr,
        vol_arr,
        ses_arr,
        prim_bar_of_tick,
        max_pausa_ms=100.0,
        retro_floor_ticks=2.0,
        retro_pct_height=50.0,
        has_prev_session_close=False,
        prev_session_close_ticks=0,
    )

    tablas: list[pd.DataFrame] = []

    # 2) Barrido post-hoc O(N_cand) x O(N_zonas)
    for z_key, z_cfg in gz.items():
        acc_idx, b_codes, _ = filtrar_zonas_nb(
            cand_int,
            cand_flt,
            min_pasos=int(z_cfg.get("min_pasos", 8)),
            min_absorb_pasos=int(z_cfg.get("min_absorb_pasos", 6)),
            detect_absorb=bool(z_cfg.get("detect_absorb", True)),
            min_sweep_ticks=float(z_cfg.get("min_sweep_ticks", 4.0)),
            max_avg_ms=float(z_cfg.get("max_avg_ms", 25.0)),
            max_total_ms=float(z_cfg.get("max_total_ms", 500.0)),
            min_volume_rate=float(z_cfg.get("min_volume_rate", 100.0)),
            min_total_volume=float(z_cfg.get("min_total_volume", 50.0)),
            max_retroceso_ticks=float(z_cfg.get("max_retroceso_ticks", 2.0)),
            retroceso_pct_height=float(z_cfg.get("retroceso_pct_height", 50.0)),
        )
        if len(acc_idx) == 0:
            continue

        z_int = cand_int[acc_idx]
        z_flt = cand_flt[acc_idx]
        z_detect_bar = z_int[:, 17]
        z_detect_ts = z_int[:, 5]
        z_hi_tk = z_int[:, 10]
        z_lo_tk = z_int[:, 11]
        z_dir = z_int[:, 7]
        z_vol = z_flt[:, 3]
        z_ses = ses_arr[z_int[:, 2]]
        z_escala = (
            escala_vol_arr[np.clip(z_detect_bar, 0, max(0, n_bars - 1))]
            if n_bars > 0
            else np.full(len(z_detect_bar), 24.0, dtype=np.float64)
        )

        for c_key, c_cfg in gc.items():
            clus_int, clus_flt = evaluar_clusters_causales_nb(
                z_detect_bar,
                z_detect_ts,
                z_lo_tk,
                z_hi_tk,
                z_vol,
                z_dir,
                b_codes,
                z_ses,
                z_escala,
                tick_size=float(tick_size),
                mostrar_absorb=bool(z_cfg.get("detect_absorb", True)),
                extension_dibujo=int(c_cfg.get("extension_dibujo", 400)),
                pct_extension_bars=int(c_cfg.get("pct_extension_bars", 300)),
                min_zonas_cluster=int(c_cfg.get("min_zonas_cluster", 4)),
                min_packing=float(c_cfg.get("min_packing", 0.70)),
                max_span_mult=float(c_cfg.get("max_span_mult", 3.2)),
                min_span_floor_ticks=float(c_cfg.get("min_span_floor_ticks", 88.0)),
                max_join_gap_ratio=float(c_cfg.get("max_join_gap_ratio", 0.35)),
                polaridad_min=float(c_cfg.get("polaridad_min", 0.0)),
                pct_angosto=float(c_cfg.get("pct_angosto", 10.0)),
                clusters_por_sesion=float(c_cfg.get("clusters_por_sesion", 1.5)),
                pct_min_historia=int(c_cfg.get("pct_min_historia", 25)),
                modo_compresion=int(c_cfg.get("modo_compresion", MODO_PACKING_PURO)),
                inmutable_en_detect=bool(inmutable_en_detect),
            )
            if len(clus_int) == 0:
                continue

            tablas.append(
                pd.DataFrame(
                    {
                        "t_ns": clus_int[:, 2],
                        "detect_bar": clus_int[:, 0],
                        "visual_end_bar": clus_int[:, 1],
                        "lo": clus_flt[:, 0],
                        "hi": clus_flt[:, 1],
                        "poc": clus_flt[:, 2],
                        "n_zonas": clus_int[:, 3],
                        "net_dir": clus_int[:, 4],
                        "width_ticks": clus_flt[:, 3],
                        "packing": clus_flt[:, 4],
                        "score": clus_flt[:, 5],
                        "polaridad": clus_flt[:, 6],
                        "def_zona": z_key,
                        "def_cluster": c_key,
                        "def": f"{z_key}__{c_key}",
                    }
                )
            )

    if not tablas:
        return pd.DataFrame(
            columns=[
                "t_ns",
                "detect_bar",
                "visual_end_bar",
                "lo",
                "hi",
                "poc",
                "n_zonas",
                "net_dir",
                "width_ticks",
                "packing",
                "score",
                "polaridad",
                "def_zona",
                "def_cluster",
                "def",
            ]
        )
    return pd.concat(tablas, ignore_index=True)
