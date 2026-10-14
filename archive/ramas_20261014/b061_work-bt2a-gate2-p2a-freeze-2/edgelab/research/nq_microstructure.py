"""Herramientas de microestructura, reloj y velocidad de cinta específicas para NQ.

NQ presenta una dinámica de microestructura radicalmente diferente a GC o ZB:
- 1 tick = 0.25 puntos ($5.00 mini / $0.50 micro).
- Gran dispersión de velocidad: desde 1-5 ticks/segundo en Globex hasta >500 ticks/segundo en RTH Open.
- La absorción institucional real se manifiesta como persistencia (dwell time) en un bracket
  de 2 a 4 ticks, mientras que las barridas de stops (flash sweeps) atraviesan el nivel sin frenar.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple
import numpy as np
import pandas as pd


# ── Regímenes de Reloj CME (America/Chicago) ──────────────────────────────────
# En Chicago (CT):
# - 08:30 CT = 09:30 ET (Apertura de contado de Nueva York)
# - 09:30 CT = 10:30 ET (Fin de la primera hora de alta volatilidad)
# - 14:15 CT = 15:15 ET (Inicio de la ventana de rebalanceo/cierre MOC)
# - 15:00 CT = 16:00 ET (Cierre de contado de Nueva York)
# - 15:00 a 17:00 CT = Mantenimiento / pausa
# - 17:00 CT a 08:30 CT = Globex / Overnight / Sesión Europea
CLOCK_RTH_OPEN = "RTH_OPEN"      # 08:30 - 09:30 CT
CLOCK_RTH_CORE = "RTH_CORE"      # 09:30 - 14:15 CT
CLOCK_RTH_CLOSE = "RTH_CLOSE"    # 14:15 - 15:00 CT
CLOCK_GLOBEX = "GLOBEX"          # Cualquier otro horario (ETH)

ALL_CLOCK_REGIMES = [CLOCK_RTH_OPEN, CLOCK_RTH_CORE, CLOCK_RTH_CLOSE, CLOCK_GLOBEX]


def classify_cme_clock_regime(ts_ns: np.ndarray, tz_name: str = "America/Chicago") -> np.ndarray:
    """Clasifica un array de timestamps en nanosegundos en los 4 regímenes de reloj CME.

    Devuelve un array de strings con el régimen correspondiente para cada timestamp.
    """
    if len(ts_ns) == 0:
        return np.array([], dtype=object)

    dts = pd.to_datetime(ts_ns, unit="ns", utc=True).tz_convert(tz_name)
    minutes = dts.hour * 60 + dts.minute

    # 08:30 CT = 510 min; 09:30 CT = 570 min; 14:15 CT = 855 min; 15:00 CT = 900 min
    cond_open = (minutes >= 510) & (minutes < 570)
    cond_core = (minutes >= 570) & (minutes < 855)
    cond_close = (minutes >= 855) & (minutes < 900)

    regimes = np.full(len(ts_ns), CLOCK_GLOBEX, dtype=object)
    regimes[cond_open] = CLOCK_RTH_OPEN
    regimes[cond_core] = CLOCK_RTH_CORE
    regimes[cond_close] = CLOCK_RTH_CLOSE

    return regimes


def compute_tape_speed_per_tick(ts_ns: np.ndarray, window_ms: int = 1000) -> np.ndarray:
    """Calcula la velocidad del tape (ticks por segundo) para cada tick en una ventana causal.

    Parámetros:
        ts_ns: Array 1D de timestamps de ticks en nanosegundos (estrictamente no decrecientes).
        window_ms: Ventana retrospectiva en milisegundos (por defecto 1000 ms = 1 seg).

    Devuelve:
        Array 1D float64 con la tasa instantánea de ticks/segundo.
    """
    n = len(ts_ns)
    if n == 0:
        return np.array([], dtype=np.float64)

    window_ns = window_ms * 1_000_000
    speeds = np.empty(n, dtype=np.float64)

    # Búsqueda binaria causal del índice de inicio de ventana para cada tick
    left_indices = np.searchsorted(ts_ns, ts_ns - window_ns, side="left")
    counts = np.arange(n) - left_indices + 1
    duration_s = np.maximum((ts_ns - ts_ns[left_indices]) / 1e9, 0.05)  # piso 50ms para evitar div por 0
    speeds = counts / duration_s

    return speeds


def compute_dwell_and_speed_at_extreme(
    ts_ns: np.ndarray,
    price_t: np.ndarray,
    volume: np.ndarray,
    ask_ticks: np.ndarray | None,
    bid_ticks: np.ndarray | None,
    start_idx: int,
    end_idx: int,
    extreme_lo_t: int,
    extreme_hi_t: int,
    target_side: int,
) -> Tuple[float, float, float, float]:
    """Calcula las métricas de permanencia (dwell time) y deceleración en el extremo de la vela.

    Parámetros:
        ts_ns, price_t, volume, ask_ticks, bid_ticks: Arrays de la serie de ticks.
        start_idx, end_idx: Rango [start_idx, end_idx) de ticks correspondientes a la barra.
        extreme_lo_t, extreme_hi_t: Rango de ticks del extremo (mecha).
        target_side: +1 para compradores atrapados (Ask), -1 para vendedores atrapados (Bid).

    Devuelve:
        (dwell_ms, dwell_volume, tape_speed_extreme, dwell_density)
    """
    if start_idx >= end_idx:
        return 0.0, 0.0, 0.0, 0.0

    p_slice = price_t[start_idx:end_idx]
    in_extreme = (p_slice >= extreme_lo_t) & (p_slice <= extreme_hi_t)

    if not np.any(in_extreme):
        return 0.0, 0.0, 0.0, 0.0

    ext_indices = np.where(in_extreme)[0]
    first_i = start_idx + ext_indices[0]
    last_i = start_idx + ext_indices[-1]

    t_first = ts_ns[first_i]
    t_last = ts_ns[last_i]
    dwell_ms = max(0.0, (t_last - t_first) / 1e6)

    # Clasificar el lado de agresión en los ticks del extremo
    v_slice = volume[start_idx:end_idx][in_extreme]
    p_ext = p_slice[in_extreme]

    if ask_ticks is not None and bid_ticks is not None:
        a_ext = ask_ticks[start_idx:end_idx][in_extreme]
        b_ext = bid_ticks[start_idx:end_idx][in_extreme]
        has_ba = (a_ext > 0) & (b_ext > 0) & (a_ext >= b_ext)
        if target_side == 1:
            # Comprador agresivo: p >= ask (o tick rule si no hay quote)
            target_mask = (has_ba & (p_ext >= a_ext)) | (~has_ba)
        else:
            # Vendedor agresivo: p <= bid (o tick rule si no hay quote)
            target_mask = (has_ba & (p_ext <= b_ext)) | (~has_ba)
    else:
        # Fallback sin quotes: todo el volumen en el extremo califica
        target_mask = np.ones(len(p_ext), dtype=bool)

    dwell_vol = float(np.sum(v_slice[target_mask]))

    # Velocidad en el extremo (ticks totales / duración)
    dur_s = max(dwell_ms / 1000.0, 0.05)
    tape_speed_extreme = len(ext_indices) / dur_s
    dwell_density = dwell_vol / dur_s

    return dwell_ms, dwell_vol, tape_speed_extreme, dwell_density


class CausalRVolTracker:
    """Rastreador causal de volumen relativo (RVol) por régimen de reloj y sesión.

    Evita el look-ahead: solo utiliza las estadísticas de barras anteriores de la misma sesión
    o el historial móvil de sesiones previas.
    """
    def __init__(self, baseline_vol_by_regime: Dict[str, float] | None = None):
        # Baselines conservadores de NQ (volumen mediano aproximado por barra de 1 min)
        self.baseline = baseline_vol_by_regime or {
            CLOCK_RTH_OPEN: 1800.0,
            CLOCK_RTH_CORE: 750.0,
            CLOCK_RTH_CLOSE: 1200.0,
            CLOCK_GLOBEX: 250.0,
        }
        self.session_counts: Dict[str, list[float]] = {r: [] for r in ALL_CLOCK_REGIMES}

    def record_bar_volume(self, regime: str, volume: float):
        if regime in self.session_counts:
            self.session_counts[regime].append(volume)

    def get_rvol(self, regime: str, bar_vol: float) -> float:
        """Calcula el ratio de volumen respecto a la mediana causal."""
        hist = self.session_counts.get(regime, [])
        if len(hist) >= 10:
            # Usar mediana rodante causal de la sesión actual
            med = float(np.median(hist[-50:]))
        else:
            med = self.baseline.get(regime, 500.0)
        return float(bar_vol / max(med, 1.0))
