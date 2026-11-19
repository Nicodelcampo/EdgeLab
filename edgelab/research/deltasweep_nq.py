"""DeltaSweep NQ (EdgeLab native port of EdgeLabDeltaSweepLab v2).

Motor 1-tick causal (sin barras volumetricas) para futuros NQ sobre `ts_ns, px, vol, bid, ask, sesion`:
  - Reutiliza `edgelab.data.liquid_release.consolidate.aggressor` (regla D13 bid/ask + respaldo causal TickRule).
  - Reutiliza `edgelab.research.otr_930_sweep._offset_ny_seg_nb` para hora exacta de Nueva York (EST/EDT).
  - Reutiliza `edgelab.costos` (friccion canonica NQ base 6.182t, adverso 8.182t, sin-spread 3.152t + referencia 2.0t).
  - Reutiliza `edgelab.funnel.escalera` (`resumen_sesiones`, `tamiz_fdr`, `economia`) y `edgelab.research.g2_ratio`.

Nota de diseño e invariantes:
  - Cero look-ahead en deteccion de barridos, normalizacion causal rolling, cierre real de barra 150T y fills k+1.
  - Diseno compatible tanto con `preflight`/`indicadores.causal` (via `disparos`/`niveles`) como con simulacion
    1-tick completa sobre `NQ_ticks.parquet` en Kaggle (< Holdout 2026-10-01).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from edgelab import costos
from edgelab.data.liquid_release.consolidate import aggressor as clasificar_agresor_quotes
from edgelab.funnel import escalera as ESC
from edgelab.holdout import HOLDOUT_PRIMERA_SESION_INT
from edgelab.research import g2_ratio as G2
from edgelab.research.grilla_generica import Variable
from edgelab.research.otr_930_sweep import _offset_ny_seg_nb

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]


# --------------------------------------------------------------------------- Metadata EdgeLab (preflight / M1 adapter)
NOMBRE = "DELTASWEEP-NQ"
INDICADORES = ["DELTASWEEP-NQ"]
PREFLIGHT_T0_S = 1_760_047_200

VARIABLES = [
    Variable("variante", "var", "grupo", categoria=4),          # 0: ALL, 1: V2_ABSORB, 2: V3_ADAPTIVE, 3: V4_BURST
    Variable("sesion_ny", "ses", "grupo", categoria=3),         # 0: 24H, 1: NY_RTH (09:30-16:00), 2: NY_AM (09:30-12:00)
    Variable("vwap_filtro", "vwap", "eq_any", categoria=2),     # 0: contra VWAP (-1), 1: a favor (+1), 2: cualquiera
]
EJES_ORDINALES = ()
MODOS_ENTRADA = ("IMM", "BRK_FLECHA_X72", "BRK_PUNTO_X72")
BRACKETS_M1 = ((60, 120), (80, 120), (120, 120), (160, 160))
EJECUCIONES = [(m, sl, tp) for m in MODOS_ENTRADA for (sl, tp) in BRACKETS_M1]
BASE = {"variante": 3, "sesion_ny": 2, "vwap_filtro": 2, "ejecución": 1}

TICK_NQ = 0.25
BAR_TICKS = 150
ARROW_OFFSET_TICKS = 6
DEEP_ARROW_EXTRA_TICKS = 8

# Catalogo de setups y brackets 1-tick
SETUP_NAMES = (
    "IMM",
    "BRK_VELA_X24", "BRK_VELA_X48", "BRK_VELA_X72", "BRK_VELA_X96", "BRK_VELA_X120",
    "BRK_FLECHA_X24", "BRK_FLECHA_X48", "BRK_FLECHA_X72", "BRK_FLECHA_X96", "BRK_FLECHA_X120",
    "BRK_PUNTO_X24", "BRK_PUNTO_X48", "BRK_PUNTO_X72", "BRK_PUNTO_X96", "BRK_PUNTO_X120",
    "LIM_EXT",
    "LIM_FLECHA",
)
# Codigos internos: (kind, param_x)
# kind: 0=IMM, 1=BRK_VELA, 2=BRK_FLECHA, 3=BRK_PUNTO, 4=LIM_EXT, 5=LIM_FLECHA
SETUP_SPECS = (
    (0, 0),
    (1, 24), (1, 48), (1, 72), (1, 96), (1, 120),
    (2, 24), (2, 48), (2, 72), (2, 96), (2, 120),
    (3, 24), (3, 48), (3, 72), (3, 96), (3, 120),
    (4, 0),
    (5, ARROW_OFFSET_TICKS),
)

BRACKET_SPECS = (
    ("40_80", 40, 80, 3600),
    ("60_80", 60, 80, 3600),
    ("60_120", 60, 120, 3600),
    ("80_120", 80, 120, 3600),
    ("120_120", 120, 120, 5400),
    ("80_160", 80, 1600 // 10, 5400),
    ("160_160", 160, 160, 5400),
    ("100_200", 100, 200, 5400),
)
# Ensure clean tuple for Numba
BRACKET_SL = tuple(b[1] for b in BRACKET_SPECS)
BRACKET_TP = tuple(b[2] for b in BRACKET_SPECS)
BRACKET_MAX_NS = tuple(b[3] * 1_000_000_000 for b in BRACKET_SPECS)

VARIANTE_MASKS = (
    ("ALL_PERM", 0),
    ("V1_CLASSIC", 1),
    ("V2_ABSORB", 2),
    ("V3_ADAPTIVE", 4),
    ("V4_BURST", 8),
    ("V5_STOPRUN", 16),
    ("ANY_STRICT", -1),
)

FILTROS_REGIMEN = (
    "ALL_24H",
    "NY_RTH",
    "NY_AM",
    "NY_RTH_SP2",
    "NY_AM_SP2",
    "NY_RTH_SP2_FADE_VWAP",
    "NY_AM_SP2_FADE_VWAP",
    "NY_RTH_CD60_SP2",
    "NY_AM_CD60_SP2",
)


# --------------------------------------------------------------------------- M1 Causal Adapter (para preflight / tests)
def _agg_m1_features(ctx: dict) -> dict[str, np.ndarray]:
    """Calcula proxies causales sobre velas M1 (cuando no hay ticks crudos) manteniendo invariante de prefijo."""
    o = np.asarray(ctx["o"], float)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    c = np.asarray(ctx["c"], float)
    v = np.asarray(ctx["v"], float)
    t = np.asarray(ctx["t"], np.int64)
    ses = np.asarray(ctx["ses"], np.int64)
    n = len(c)

    rng = h - l
    bar_delta = np.zeros_like(v, dtype=float)
    ok_rng = rng > 0.0
    bar_delta[ok_rng] = ((2.0 * c[ok_rng] - h[ok_rng] - l[ok_rng]) / rng[ok_rng]) * v[ok_rng]
    tick = max(float(ctx.get("tick", TICK_NQ)), 1e-9)
    abs_score = np.zeros_like(v, dtype=float)
    abs_score[ok_rng] = np.abs(bar_delta[ok_rng]) / (1.0 + rng[ok_rng] / tick)

    ny_min = np.empty(n, np.int64)
    vwap_al = np.zeros(n, np.int64)
    ses_pv = 0.0
    ses_vol = 0.0
    prev_vwap = np.nan
    for k in range(n):
        tl = int(t[k]) + _offset_ny_seg_nb(int(t[k]))
        ny_min[k] = (tl % 86400) // 60
        if k == 0 or ses[k] != ses[k - 1]:
            ses_pv = 0.0
            ses_vol = 0.0
            prev_vwap = np.nan
        ses_pv += c[k] * max(v[k], 0.0)
        ses_vol += max(v[k], 0.0)
        vw = ses_pv / ses_vol if ses_vol > 0 else c[k]
        if k > 0 and ses[k] == ses[k - 1] and not math.isnan(prev_vwap):
            vwap_al[k] = 1 if vw > prev_vwap else (-1 if vw < prev_vwap else 0)
        prev_vwap = vw

    return {
        "bar_delta": bar_delta,
        "abs_score": abs_score,
        "ny_min": ny_min,
        "vwap_slope": vwap_al,
    }


def disparos(ctx: dict) -> pd.DataFrame:
    """Generador causal de disparos COMPATIBLE con `edgelab.research.indicadores.causal` (para tests/preflight)."""
    c = np.asarray(ctx["c"], float)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    v = np.asarray(ctx["v"], float)
    ses = np.asarray(ctx["ses"], np.int64)
    tick = float(ctx.get("tick", TICK_NQ))
    n = len(c)
    if n < 30:
        return pd.DataFrame(columns=["k", "lado", "variante", "sesion_ny", "vwap_filtro", "atr_ticks"])

    feat = _agg_m1_features(ctx)
    delta = feat["bar_delta"]
    abs_sc = feat["abs_score"]
    ny_min = feat["ny_min"]
    vw_slope = feat["vwap_slope"]

    rows = []
    # Rolling strict causal history window of 100 bars
    last_k = -10
    for k in range(25, n):
        if ses[k] != ses[k - 1]:
            continue
        if (k - last_k) < 3:
            continue
        hist_slice = slice(max(0, k - 100), k)
        med_v = float(np.median(v[hist_slice])) if k > 0 else 1.0
        q75_abs = float(np.quantile(abs_sc[hist_slice], 0.75)) if k >= 20 else 0.0
        # Sweep in k-1 + flip in k (strictly <= k)
        d_prev = delta[k - 1]
        d_now = delta[k]
        fall_ok = (h[k - 1] - l[k - 1]) >= 2.0 * tick
        if not fall_ok:
            continue

        lado = 0
        if d_prev < 0 and d_now > 0 and c[k] > c[k - 1] and abs(d_prev) >= 0.4 * med_v:
            lado = 1
        elif d_prev > 0 and d_now < 0 and c[k] < c[k - 1] and abs(d_prev) >= 0.4 * med_v:
            lado = -1
        if lado == 0:
            continue

        v2 = int(abs_sc[k - 1] >= q75_abs and abs(d_now) >= 0.25 * med_v)
        v3 = int(abs(d_prev) >= 0.9 * med_v and abs(d_now) >= 0.35 * med_v)
        v4 = int(v[k] >= 1.15 * med_v and abs(d_now) >= 0.30 * med_v)
        var_code = 3 if v4 else (2 if v3 else (1 if v2 else 0))

        hm = int(ny_min[k])
        ses_ny = 2 if (570 <= hm < 720) else (1 if (720 <= hm < 960) else 0)
        wf = 1 if vw_slope[k] * lado > 0 else (0 if vw_slope[k] * lado < 0 else 2)
        rows.append(
            dict(
                k=k,
                lado=lado,
                variante=var_code,
                sesion_ny=ses_ny,
                vwap_filtro=wf,
                atr_ticks=max(8.0, float(np.mean(h[max(0, k - 14):k] - l[max(0, k - 14):k])) / tick),
            )
        )
        last_k = k

    if not rows:
        return pd.DataFrame(columns=["k", "lado", "variante", "sesion_ny", "vwap_filtro", "atr_ticks"])
    return pd.DataFrame(rows)


def niveles(disp: dict, ej: tuple, ctx: dict) -> tuple[int, int, int, float, float, float, float]:
    """Devuelve `(k_entrada, sesion_lim, lado, entrada, stop, tp, be)` causal para una fila de `disparos`."""
    k = int(disp["k"])
    lado = int(disp["lado"])
    _, sl_t, tp_t = ej
    tick = float(ctx.get("tick", TICK_NQ))
    c = np.asarray(ctx["c"], float)
    o = np.asarray(ctx["o"], float)
    k_ent = min(k + 1, len(c) - 1)
    entrada = float(o[k_ent]) if k_ent < len(o) else float(c[k])
    stop = entrada - lado * sl_t * tick
    tp = entrada + lado * tp_t * tick
    return (k_ent, 240, lado, entrada, stop, tp, 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    """Version vectorizada de `niveles` para `grilla_generica`."""
    if not len(D):
        return np.empty((0, 7), float)
    _, sl_t, tp_t = ej
    tick = float(ctx.get("tick", TICK_NQ))
    o = np.asarray(ctx["o"], float)
    k = D["k"].to_numpy(np.int64)
    lado = D["lado"].to_numpy(float)
    k_ent = np.minimum(k + 1, len(o) - 1)
    entrada = o[k_ent]
    stop = entrada - lado * sl_t * tick
    tp = entrada + lado * tp_t * tick
    out = np.empty((len(D), 7), float)
    out[:, 0] = k_ent
    out[:, 1] = 240.0
    out[:, 2] = lado
    out[:, 3] = entrada
    out[:, 4] = stop
    out[:, 5] = tp
    out[:, 6] = 0.0
    return out


# --------------------------------------------------------------------------- Motor 1-Tick Causal (Paridad EdgeLabDeltaSweepLab v2)
@njit(cache=False)
def _ny_hhmm_desde_ns(ts_ns: np.int64) -> np.int32:
    t_s = int(ts_ns // 1_000_000_000)
    tl = t_s + _offset_ny_seg_nb(t_s)
    sec_dia = tl % 86400
    hh = sec_dia // 3600
    mm = (sec_dia % 3600) // 60
    return np.int32(hh * 100 + mm)


@njit(cache=False)
def _norm_zscore(ring: np.ndarray, count: int, s: float, s2: float, val: float) -> float:
    if count < 20:
        return 0.0
    mean = s / count
    var = (s2 / count) - (mean * mean)
    if var < 1e-9:
        var = 1e-9
    return (val - mean) / math.sqrt(var)


@njit(cache=False)
def _norm_pctrank(ring: np.ndarray, count: int, val: float) -> float:
    if count < 20:
        return 50.0
    le = 0
    for i in range(count):
        if ring[i] <= val:
            le += 1
    return 100.0 * le / count


@njit(cache=False)
def _norm_push(ring: np.ndarray, head: int, count: int, s: float, s2: float, val: float, cap: int):
    if count == cap:
        old = ring[head]
        s -= old
        s2 -= old * old
    else:
        count += 1
    ring[head] = val
    s += val
    s2 += val * val
    head = (head + 1) % cap
    return head, count, s, s2


@njit(cache=False)
def _agresor_con_tickrule(px_tick: np.ndarray, side_in: np.ndarray) -> np.ndarray:
    """Aplica regla D13 (`side_in`) y cae a TickRule causal cuando `side_in[i] == 0` (paridad NT8)."""
    n = len(px_tick)
    out = np.empty(n, np.int8)
    has_last = False
    last_px = np.int64(0)
    last_dir = np.int8(1)
    for i in range(n):
        s = side_in[i]
        px = px_tick[i]
        if s == 0:
            if has_last:
                if px > last_px:
                    s = 1
                elif px < last_px:
                    s = -1
                else:
                    s = last_dir
            else:
                s = 1
        last_px = px
        last_dir = s
        has_last = True
        out[i] = s
    return out


@njit(cache=False)
def _window_bounds_nb(
    px_ring: np.ndarray,
    ts_ring: np.ndarray,
    ring_cap: int,
    total_ticks: int,
    lookback: int,
    offset_latest: int,
):
    avail = total_ticks - offset_latest
    if avail < 0:
        avail = 0
    if avail > lookback:
        avail = lookback
    if avail <= 0:
        return np.int64(0), np.int64(0), np.int64(0)
    lo = np.int64(9_000_000_000_000)
    hi = np.int64(-9_000_000_000_000)
    first_ns = np.int64(0)
    last_ns = np.int64(0)
    for k in range(avail):
        p = (total_ticks - 1 - offset_latest - k) % ring_cap
        pt = px_ring[p]
        if pt < lo:
            lo = pt
        if pt > hi:
            hi = pt
        if k == 0:
            last_ns = ts_ring[p]
        if k == avail - 1:
            first_ns = ts_ring[p]
    dur_ms = (last_ns - first_ns) // 1_000_000
    if dur_ms < 1:
        dur_ms = 1
    return lo, hi, dur_ms


@njit(cache=False)
def _detectar_eventos_sesion_nb(
    ts_ns: np.ndarray,
    px_tick: np.ndarray,
    vol: np.ndarray,
    side: np.ndarray,
    spread_t: np.ndarray,
    tick_size: float = 0.25,
    base_arm_delta: float = 35.0,
    base_arm_z: float = 1.5,
    base_fall_ticks: int = 2,
    base_flip_delta: float = 15.0,
    base_lift_ticks: int = 1,
    max_arm_expire: int = 120,
    min_cooldown_ticks: int = 10,
    swing_lookback: int = 500,
    norm_cap: int = 500,
    min_history: int = 100,
    classic_arm_delta: float = 80.0,
    classic_fall_ticks: int = 4,
    classic_flip_delta: float = 30.0,
    classic_lift_ticks: int = 2,
    classic_expire: int = 80,
    absorb_min_pct: float = 80.0,
    adaptive_sweep_z: float = 2.0,
    adaptive_flip_z: float = 1.2,
    burst_max_sweep_ms: int = 1200,
    burst_max_flip_ms: int = 600,
    burst_min_volrate_pct: float = 75.0,
    bar_ticks: int = 150,
    arrow_offset_ticks: int = 6,
):
    """Detecta todos los eventos permisivos y etiquetas V1..V5 dentro de UNA sesion (strictly causal 1-tick)."""
    n = len(ts_ns)
    max_ev = max(16, (n // max(1, min_cooldown_ticks)) + 16)

    ev_sig_idx = np.empty(max_ev, np.int64)
    ev_ts_ns = np.empty(max_ev, np.int64)
    ev_dir = np.empty(max_ev, np.int8)
    ev_dot_tick = np.empty(max_ev, np.int64)
    ev_arrow_tick = np.empty(max_ev, np.int64)
    ev_ext_tick = np.empty(max_ev, np.int64)
    ev_bar_close_idx = np.empty(max_ev, np.int64)
    ev_bar_hi = np.empty(max_ev, np.int64)
    ev_bar_lo = np.empty(max_ev, np.int64)
    ev_ny_hhmm = np.empty(max_ev, np.int32)
    ev_spread = np.empty(max_ev, np.float64)
    ev_with_vwap = np.empty(max_ev, np.int8)
    ev_var_mask = np.empty(max_ev, np.int32)
    ev_abs_pct = np.empty(max_ev, np.float64)
    ev_sw_pct = np.empty(max_ev, np.float64)
    ev_vr_pct = np.empty(max_ev, np.float64)
    ev_broke_sw = np.empty(max_ev, np.int8)
    ev_reclaimed = np.empty(max_ev, np.int8)
    ev_cd60_ok = np.empty(max_ev, np.int8)

    # Ring buffers exactos (4096 slots, mismo principio que EdgeLabDeltaSweepLab.cs)
    ring_cap = 4096
    px_ring = np.zeros(ring_cap, np.int64)
    ts_ring = np.zeros(ring_cap, np.int64)
    v_ring = np.zeros(ring_cap, np.float64)
    sv_ring = np.zeros(ring_cap, np.float64)

    # Precomputar cierres de barras de 150 ticks (bar_idx = k // bar_ticks) sin tocar futuros en evaluacion:
    # Un setup BRK_VELA solo consulta (bar_hi, bar_lo) cuando k' > ev_bar_close_idx[e], que ya esta cerrado.
    n_bars = (n + bar_ticks - 1) // bar_ticks
    b_hi_arr = np.empty(n_bars, np.int64)
    b_lo_arr = np.empty(n_bars, np.int64)
    for b in range(n_bars):
        i0 = b * bar_ticks
        i1 = min(n, i0 + bar_ticks)
        hi_v = px_tick[i0]
        lo_v = px_tick[i0]
        for j in range(i0 + 1, i1):
            pv = px_tick[j]
            if pv > hi_v:
                hi_v = pv
            if pv < lo_v:
                lo_v = pv
        b_hi_arr[b] = hi_v
        b_lo_arr[b] = lo_v

    # Buffers de normalizacion causal
    sw_ring = np.zeros(norm_cap, np.float64)
    ab_ring = np.zeros(norm_cap, np.float64)
    vr_ring = np.zeros(norm_cap, np.float64)
    fl_ring = np.zeros(norm_cap, np.float64)
    sw_h = ab_h = vr_h = fl_h = 0
    sw_c = ab_c = vr_c = fl_c = 0
    sw_s = ab_s = vr_s = fl_s = 0.0
    sw_s2 = ab_s2 = vr_s2 = fl_s2 = 0.0

    # Sumas O(1)
    run_d20 = run_v20 = 0.0
    run_d40 = run_v40 = 0.0
    run_d80 = run_v80 = 0.0
    run_fl_d10 = run_fl_v10 = 0.0
    run_fl_d15 = run_fl_v15 = 0.0
    run_fl_d30 = run_fl_v30 = 0.0

    # VWAP causal + hist 200
    ses_pv = 0.0
    ses_vol = 0.0
    vwap_q = np.zeros(205, np.float64)
    vw_head = 0
    vw_cnt = 0

    # Estado bar 0 tracking causal hasta el tick k inclusive
    cur_bar_id = -1
    cur_bar_hi = np.int64(-9_000_000_000_000)
    cur_bar_lo = np.int64(9_000_000_000_000)

    # Detector state machine (0=Idle, 1=ArmedDown, 2=ArmedUp)
    state = 0
    armed_ticks = 0
    sweep_ext_tick = np.int64(0)
    armed_peak_sw_d40 = 0.0
    armed_peak_abs = 0.0
    armed_peak_vr = 0.0
    armed_broke_sw = False
    armed_sw_break_lvl = np.int64(0)
    last_sig_pos = np.int64(-999999)
    last_emit_ts_ns = np.int64(-1)
    total_ticks = 0
    n_ev = 0

    for i in range(n):
        v = vol[i]
        pt = px_tick[i]
        if v <= 0.0 or pt <= 0:
            continue
        t_ns = ts_ns[i]
        s_val = float(side[i]) * v

        b_id = i // bar_ticks
        if b_id != cur_bar_id:
            cur_bar_id = b_id
            cur_bar_hi = pt
            cur_bar_lo = pt
        else:
            if pt > cur_bar_hi:
                cur_bar_hi = pt
            if pt < cur_bar_lo:
                cur_bar_lo = pt

        # VWAP sesion causal
        ses_pv += (pt * tick_size) * v
        ses_vol += v
        vwap_now = (ses_pv / ses_vol) if ses_vol > 0.0 else (pt * tick_size)
        vwap_prev200 = math.nan
        if vw_cnt >= 200:
            vwap_prev200 = vwap_q[vw_head]
        vwap_q[vw_head] = vwap_now
        vw_head = (vw_head + 1) % 200
        if vw_cnt < 200:
            vw_cnt += 1

        # Push tick a ring
        pos = total_ticks
        r_idx = pos % ring_cap

        run_d20 += s_val; run_v20 += v
        if pos >= 20:
            op = (pos - 20) % ring_cap
            run_d20 -= sv_ring[op]; run_v20 -= v_ring[op]

        run_d40 += s_val; run_v40 += v
        if pos >= 40:
            op = (pos - 40) % ring_cap
            run_d40 -= sv_ring[op]; run_v40 -= v_ring[op]

        run_d80 += s_val; run_v80 += v
        if pos >= 80:
            op = (pos - 80) % ring_cap
            run_d80 -= sv_ring[op]; run_v80 -= v_ring[op]

        run_fl_d10 += s_val; run_fl_v10 += v
        if pos >= 10:
            op = (pos - 10) % ring_cap
            run_fl_d10 -= sv_ring[op]; run_fl_v10 -= v_ring[op]

        run_fl_d15 += s_val; run_fl_v15 += v
        if pos >= 15:
            op = (pos - 15) % ring_cap
            run_fl_d15 -= sv_ring[op]; run_fl_v15 -= v_ring[op]

        run_fl_d30 += s_val; run_fl_v30 += v
        if pos >= 30:
            op = (pos - 30) % ring_cap
            run_fl_d30 -= sv_ring[op]; run_fl_v30 -= v_ring[op]

        px_ring[r_idx] = pt
        ts_ring[r_idx] = t_ns
        v_ring[r_idx] = v
        sv_ring[r_idx] = s_val
        total_ticks += 1

        if (total_ticks & 2047) == 0:
            run_d20 = run_v20 = run_d40 = run_v40 = run_d80 = run_v80 = 0.0
            run_fl_d10 = run_fl_v10 = run_fl_d15 = run_fl_v15 = run_fl_d30 = run_fl_v30 = 0.0
            for k in range(1, min(80, total_ticks) + 1):
                rp = (total_ticks - k) % ring_cap
                svk = sv_ring[rp]; vk = v_ring[rp]
                if k <= 10:
                    run_fl_d10 += svk; run_fl_v10 += vk
                if k <= 15:
                    run_fl_d15 += svk; run_fl_v15 += vk
                if k <= 20:
                    run_d20 += svk; run_v20 += vk
                if k <= 30:
                    run_fl_d30 += svk; run_fl_v30 += vk
                if k <= 40:
                    run_d40 += svk; run_v40 += vk
                run_d80 += svk; run_v80 += vk

        if total_ticks < 80:
            continue

        # Actualizar distribucion causal cada 10 ticks
        if (total_ticks % 10) == 0:
            lo40, hi40, dur40 = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, 40, 0)
            rng40 = max(0, hi40 - lo40)
            ad40 = abs(run_d40)
            abs_sc = ad40 / (1.0 + rng40)
            vr = (run_v40 * 1000.0) / max(10.0, float(dur40))
            sw_h, sw_c, sw_s, sw_s2 = _norm_push(sw_ring, sw_h, sw_c, sw_s, sw_s2, ad40, norm_cap)
            ab_h, ab_c, ab_s, ab_s2 = _norm_push(ab_ring, ab_h, ab_c, ab_s, ab_s2, abs_sc, norm_cap)
            vr_h, vr_c, vr_s, vr_s2 = _norm_push(vr_ring, vr_h, vr_c, vr_s, vr_s2, vr, norm_cap)
            fl_h, fl_c, fl_s, fl_s2 = _norm_push(fl_ring, fl_h, fl_c, fl_s, fl_s2, abs(run_fl_d15), norm_cap)

        # EvaluateSweepFlip causal (pos == total_ticks - 1)
        cur_pos = total_ticks - 1
        if state == 0:
            if (cur_pos - last_sig_pos) < min_cooldown_ticks:
                continue
            z_sw = _norm_zscore(sw_ring, sw_c, sw_s, sw_s2, abs(run_d40))
            trig_abs_dn = (run_d40 <= -base_arm_delta) or (run_d20 <= -(base_arm_delta * 0.75))
            trig_z_dn = (sw_c >= min_history) and (run_d40 < 0.0) and (z_sw >= base_arm_z)
            trig_abs_up = (run_d40 >= base_arm_delta) or (run_d20 >= (base_arm_delta * 0.75))
            trig_z_up = (sw_c >= min_history) and (run_d40 > 0.0) and (z_sw >= base_arm_z)
            if not (trig_abs_dn or trig_z_dn or trig_abs_up or trig_z_up):
                continue

            lo40, hi40, dur40 = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, 40, 0)
            rng40 = hi40 - lo40
            if rng40 < base_fall_ticks:
                continue

            abs_sc_now = abs(run_d40) / (1.0 + rng40)
            vr_now = (run_v40 * 1000.0) / max(10.0, float(dur40))
            sw_avail = min(swing_lookback, max(0, total_ticks - 45))
            broke_sw = False
            brk_lvl = np.int64(0)

            if trig_abs_dn or trig_z_dn:
                if pt <= lo40 + 2:
                    if sw_avail >= 50:
                        p_lo, _, _ = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, sw_avail, 45)
                        if lo40 < p_lo:
                            broke_sw = True
                            brk_lvl = p_lo
                    state = 1
                    armed_ticks = 0
                    sweep_ext_tick = lo40
                    armed_peak_sw_d40 = run_d40
                    armed_peak_abs = abs_sc_now
                    armed_peak_vr = vr_now
                    armed_broke_sw = broke_sw
                    armed_sw_break_lvl = brk_lvl
            elif trig_abs_up or trig_z_up:
                if pt >= hi40 - 2:
                    if sw_avail >= 50:
                        _, p_hi, _ = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, sw_avail, 45)
                        if hi40 > p_hi:
                            broke_sw = True
                            brk_lvl = p_hi
                    state = 2
                    armed_ticks = 0
                    sweep_ext_tick = hi40
                    armed_peak_sw_d40 = run_d40
                    armed_peak_abs = abs_sc_now
                    armed_peak_vr = vr_now
                    armed_broke_sw = broke_sw
                    armed_sw_break_lvl = brk_lvl
            continue

        # Estado ARMED
        armed_ticks += 1
        lo40, hi40, dur40 = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, 40, 0)
        rng40 = hi40 - lo40
        abs_sc_now = abs(run_d40) / (1.0 + rng40)
        vr_now = (run_v40 * 1000.0) / max(10.0, float(dur40))

        if state == 1:
            if pt < sweep_ext_tick:
                sweep_ext_tick = pt
            if run_d40 < armed_peak_sw_d40:
                armed_peak_sw_d40 = run_d40
        else:
            if pt > sweep_ext_tick:
                sweep_ext_tick = pt
            if run_d40 > armed_peak_sw_d40:
                armed_peak_sw_d40 = run_d40

        if abs_sc_now > armed_peak_abs:
            armed_peak_abs = abs_sc_now
        if vr_now > armed_peak_vr:
            armed_peak_vr = vr_now

        is_long = (state == 1)
        lift_ticks = (pt - sweep_ext_tick) if is_long else (sweep_ext_tick - pt)
        flip_cond = ((run_fl_d15 >= base_flip_delta or run_fl_d10 >= base_flip_delta) and lift_ticks >= base_lift_ticks) if is_long else ((run_fl_d15 <= -base_flip_delta or run_fl_d10 <= -base_flip_delta) and lift_ticks >= base_lift_ticks)

        if flip_cond:
            # Emision (solo si existe tick siguiente i+1 dentro de la sesion para fill)
            if i + 1 < n and n_ev < max_ev:
                _, _, dur_fl15 = _window_bounds_nb(px_ring, ts_ring, ring_cap, total_ticks, 15, 0)
                sw_r40 = rng40
                abs_sw_d = abs(armed_peak_sw_d40)
                abs_fl_d = abs(run_fl_d15)
                flip_eff = (abs_fl_d / run_fl_v15) if run_fl_v15 > 0.0 else 0.0

                abs_pct = _norm_pctrank(ab_ring, ab_c, armed_peak_abs)
                sw_pct = _norm_pctrank(sw_ring, sw_c, abs_sw_d)
                sw_z = _norm_zscore(sw_ring, sw_c, sw_s, sw_s2, abs_sw_d)
                fl_z = _norm_zscore(fl_ring, fl_c, fl_s, fl_s2, abs_fl_d)
                vr_pct = _norm_pctrank(vr_ring, vr_c, armed_peak_vr)

                v1 = (abs_sw_d >= classic_arm_delta) and (sw_r40 >= classic_fall_ticks) and (abs_fl_d >= classic_flip_delta) and (lift_ticks >= classic_lift_ticks) and (armed_ticks <= classic_expire)
                v2 = (ab_c >= min_history) and (abs_pct >= absorb_min_pct) and (abs_sw_d >= classic_arm_delta * 0.6) and (flip_eff >= 0.30) and (lift_ticks >= 1)
                v3 = (sw_c >= min_history) and (sw_z >= adaptive_sweep_z) and (fl_z >= adaptive_flip_z) and (lift_ticks >= 1)
                v4 = (dur40 <= burst_max_sweep_ms) and (dur_fl15 <= burst_max_flip_ms) and (vr_pct >= burst_min_volrate_pct) and (abs_fl_d >= classic_flip_delta * 0.8)
                v4_med = (dur40 <= 2000) and (dur_fl15 <= 1000) and (vr_pct >= 65.0) and (abs_fl_d >= classic_flip_delta * 0.8)
                v4_wide = (dur40 <= 3000) and (dur_fl15 <= 1500) and (vr_pct >= 55.0) and (abs_fl_d >= classic_flip_delta * 0.67)
                reclaimed = armed_broke_sw and ((pt >= armed_sw_break_lvl) if is_long else (pt <= armed_sw_break_lvl))
                v5 = reclaimed and (lift_ticks >= 2)
                mask = (
                    (1 if v1 else 0)
                    | (2 if v2 else 0)
                    | (4 if v3 else 0)
                    | (8 if v4 else 0)
                    | (16 if v5 else 0)
                    | (32 if v4_med else 0)
                    | (64 if v4_wide else 0)
                )

                w_vwap = np.int8(0)
                if not math.isnan(vwap_prev200):
                    vslope = vwap_now - vwap_prev200
                    if (is_long and vslope > 0.0) or ((not is_long) and vslope < 0.0):
                        w_vwap = np.int8(1)
                    elif (is_long and vslope < 0.0) or ((not is_long) and vslope > 0.0):
                        w_vwap = np.int8(-1)

                dot_pt = px_tick[i + 1]
                bar_hi_s = max(dot_pt, cur_bar_hi)
                bar_lo_s = min(dot_pt, cur_bar_lo)
                arrow_t = (bar_lo_s - arrow_offset_ticks) if is_long else (bar_hi_s + arrow_offset_ticks)
                ext_t = bar_lo_s if is_long else bar_hi_s

                ev_sig_idx[n_ev] = i
                ev_ts_ns[n_ev] = ts_ns[i + 1]
                ev_dir[n_ev] = np.int8(1 if is_long else -1)
                ev_dot_tick[n_ev] = dot_pt
                ev_arrow_tick[n_ev] = arrow_t
                ev_ext_tick[n_ev] = ext_t
                ev_bar_close_idx[n_ev] = min(n - 1, (b_id + 1) * bar_ticks - 1)
                ev_bar_hi[n_ev] = b_hi_arr[b_id]
                ev_bar_lo[n_ev] = b_lo_arr[b_id]
                ev_ny_hhmm[n_ev] = _ny_hhmm_desde_ns(ts_ns[i + 1])
                ev_spread[n_ev] = spread_t[i + 1]
                ev_with_vwap[n_ev] = w_vwap
                ev_var_mask[n_ev] = mask
                ev_abs_pct[n_ev] = abs_pct
                ev_sw_pct[n_ev] = sw_pct
                ev_vr_pct[n_ev] = vr_pct
                ev_broke_sw[n_ev] = np.int8(1 if armed_broke_sw else 0)
                ev_reclaimed[n_ev] = np.int8(1 if reclaimed else 0)
                ev_cd60_ok[n_ev] = np.int8(1 if (last_emit_ts_ns < 0 or (t_ns - last_emit_ts_ns) >= 60_000_000_000) else 0)

                last_emit_ts_ns = t_ns
                n_ev += 1

            last_sig_pos = cur_pos
            state = 0
            armed_ticks = 0
            continue

        if armed_ticks >= max_arm_expire:
            state = 0
            armed_ticks = 0

    return (
        ev_sig_idx[:n_ev],
        ev_ts_ns[:n_ev],
        ev_dir[:n_ev],
        ev_dot_tick[:n_ev],
        ev_arrow_tick[:n_ev],
        ev_ext_tick[:n_ev],
        ev_bar_close_idx[:n_ev],
        ev_bar_hi[:n_ev],
        ev_bar_lo[:n_ev],
        ev_ny_hhmm[:n_ev],
        ev_spread[:n_ev],
        ev_with_vwap[:n_ev],
        ev_var_mask[:n_ev],
        ev_abs_pct[:n_ev],
        ev_sw_pct[:n_ev],
        ev_vr_pct[:n_ev],
        ev_broke_sw[:n_ev],
        ev_reclaimed[:n_ev],
        ev_cd60_ok[:n_ev],
    )


def detectar_eventos_tick(
    ts_ns: np.ndarray,
    px: np.ndarray,
    vol: np.ndarray,
    bid: np.ndarray | None = None,
    ask: np.ndarray | None = None,
    *,
    tick_size: float | None = None,
) -> dict[str, np.ndarray]:
    """Wrapper vectorizado + causal sobre arrays de ticks de una sesion."""
    tick_size = TICK_NQ if tick_size is None else tick_size
    ts_arr = np.ascontiguousarray(ts_ns, dtype=np.int64)
    px_arr = np.ascontiguousarray(px, dtype=np.float64)
    vol_arr = np.ascontiguousarray(vol, dtype=np.float64)
    n = len(ts_arr)
    px_tick = np.rint(px_arr / tick_size).astype(np.int64)

    if bid is not None and ask is not None:
        bid_arr = np.asarray(bid, dtype=np.float64)
        ask_arr = np.asarray(ask, dtype=np.float64)
        side_raw = clasificar_agresor_quotes(px_arr, bid_arr, ask_arr)
        valid_sp = np.isfinite(bid_arr) & np.isfinite(ask_arr) & (bid_arr > 0.0) & (ask_arr >= bid_arr)
        spread_t = np.where(valid_sp, np.rint((ask_arr - bid_arr) / tick_size).astype(np.float64), -1.0)
    else:
        side_raw = np.zeros(n, dtype=np.int8)
        spread_t = np.full(n, -1.0, dtype=np.float64)

    side = _agresor_con_tickrule(px_tick, side_raw)
    res = _detectar_eventos_sesion_nb(ts_arr, px_tick, vol_arr, side, spread_t, tick_size)
    keys = (
        "sig_idx", "ts_ns", "dir", "dot_tick", "arrow_tick", "ext_tick",
        "bar_close_idx", "bar_hi", "bar_lo", "ny_hhmm", "spread_ticks",
        "with_vwap", "var_mask", "abs_pct", "sw_pct", "vr_pct",
        "broke_swing", "reclaimed", "cd60_ok",
    )
    out = dict(zip(keys, res))
    out["px_tick"] = px_tick
    out["spread_at_tick"] = spread_t
    return out


@njit(cache=False)
def _simular_eventos_sesion_nb(
    ts_ns: np.ndarray,
    px_tick: np.ndarray,
    spread_at_tick: np.ndarray,
    sig_idx: np.ndarray,
    ev_dir: np.ndarray,
    ev_dot_tick: np.ndarray,
    ev_arrow_tick: np.ndarray,
    ev_ext_tick: np.ndarray,
    ev_bar_close_idx: np.ndarray,
    ev_bar_hi: np.ndarray,
    ev_bar_lo: np.ndarray,
    ev_var_mask: np.ndarray,
    setup_kind: np.ndarray,
    setup_param_x: np.ndarray,
    sl_arr: np.ndarray,
    tp_arr: np.ndarray,
    max_ns_arr: np.ndarray,
    break_confirm_ticks: int = 1,
    delayed_max_wait_ns: int = 300_000_000_000,
    eval_delayed_all_perm: bool = False,
):
    """Simula en un pase causal los fills (IMM, BRK_*, LIM_*) y los 8 brackets + horizontes IMM 30s/60s/180s.

    Retorna:
      - fill_ok: (E, S) bool/int8 (1 si entro en sesion)
      - gross_t: (E, S, B) float64 ticks brutos al cierre de bracket (NaN si no lleno)
      - fill_spread: (E, S) float64 spread en ticks al momento del fill (-1 si N/A)
      - imm_h_ret: (E, 3) float64 ticks de IMM a +30s, +60s, +180s
    """
    n = len(ts_ns)
    n_ev = len(sig_idx)
    n_setups = len(setup_kind)
    n_brackets = len(sl_arr)

    fill_ok = np.zeros((n_ev, n_setups), np.int8)
    fill_spread = np.full((n_ev, n_setups), -1.0, np.float64)
    gross_t = np.full((n_ev, n_setups, n_brackets), np.nan, np.float64)
    imm_h_ret = np.full((n_ev, 3), np.nan, np.float64)

    horizons = np.array([30_000_000_000, 60_000_000_000, 180_000_000_000], np.int64)

    for e in range(n_ev):
        s_idx = sig_idx[e]
        imm_idx = s_idx + 1
        if imm_idx >= n:
            continue

        d = ev_dir[e]
        dot_t = ev_dot_tick[e]
        imm_ts = ts_ns[imm_idx]

        # Horizontes IMM (+30s, +60s, +180s) por scan rapido desde imm_idx
        h_ptr = 0
        for j in range(imm_idx + 1, n):
            el = ts_ns[j] - imm_ts
            while h_ptr < 3 and el >= horizons[h_ptr]:
                imm_h_ret[e, h_ptr] = float(d * (px_tick[j] - dot_t))
                h_ptr += 1
            if h_ptr >= 3:
                break

        # Decidir que setups se simulan para este evento
        sim_delayed = eval_delayed_all_perm or (ev_var_mask[e] > 0)

        # Paso 1: localizar (fill_idx, fill_tick) de los S setups dentro de delayed_max_wait_ns
        f_idx = np.full(n_setups, -1, np.int64)
        f_tick = np.zeros(n_setups, np.int64)
        # IMM siempre llena en imm_idx
        f_idx[0] = imm_idx
        f_tick[0] = dot_t
        fill_ok[e, 0] = 1
        fill_spread[e, 0] = spread_at_tick[imm_idx]

        if sim_delayed:
            adv_hit = np.zeros(n_setups, np.int8)
            went_past_arrow = np.zeros(n_setups, np.int8)
            pend_fill = np.zeros(n_setups, np.int8)
            arr_t = ev_arrow_tick[e]
            ext_t = ev_ext_tick[e]
            bc_idx = ev_bar_close_idx[e]
            b_hi = ev_bar_hi[e]
            b_lo = ev_bar_lo[e]
            abs_brk_tick = (b_hi + break_confirm_ticks) if d > 0 else (b_lo - break_confirm_ticks)
            arr_brk_tick = (arr_t + break_confirm_ticks) if d > 0 else (arr_t - break_confirm_ticks)
            dot_brk_tick = (dot_t + break_confirm_ticks) if d > 0 else (dot_t - break_confirm_ticks)

            rem_wait = n_setups - 1
            sig_ts = ts_ns[s_idx]
            for j in range(imm_idx + 1, n):
                pt = px_tick[j]
                t_now = ts_ns[j]
                el = t_now - sig_ts
                adv_now = -(d * (pt - dot_t))

                for s in range(1, n_setups):
                    if f_idx[s] >= 0 or pend_fill[s] == -1:
                        continue
                    if pend_fill[s] == 1:
                        f_idx[s] = j
                        f_tick[s] = pt
                        fill_ok[e, s] = 1
                        fill_spread[e, s] = spread_at_tick[j]
                        rem_wait -= 1
                        continue
                    if el > delayed_max_wait_ns:
                        pend_fill[s] = -1
                        rem_wait -= 1
                        continue

                    sk = setup_kind[s]
                    px_lim = arr_t if sk == 5 else ext_t
                    if sk == 4 or sk == 5:
                        hit_lim = (pt <= px_lim) if d > 0 else (pt >= px_lim)
                        if hit_lim:
                            f_idx[s] = j
                            f_tick[s] = px_lim
                            fill_ok[e, s] = 1
                            fill_spread[e, s] = spread_at_tick[j]
                            rem_wait -= 1
                        continue

                    # Breakout setups (1=VELA, 2=FLECHA, 3=PUNTO)
                    if adv_hit[s] == 0 and adv_now >= setup_param_x[s]:
                        adv_hit[s] = 1
                    if sk == 2 and went_past_arrow[s] == 0:
                        if (pt <= arr_t - 1) if d > 0 else (pt >= arr_t + 1):
                            went_past_arrow[s] = 1
                    if adv_hit[s] == 0:
                        continue

                    broke = False
                    if sk == 1:
                        if j > bc_idx:
                            broke = (pt >= abs_brk_tick) if d > 0 else (pt <= abs_brk_tick)
                    elif sk == 2:
                        if went_past_arrow[s] == 1:
                            broke = (pt >= arr_brk_tick) if d > 0 else (pt <= arr_brk_tick)
                    elif sk == 3:
                        broke = (pt >= dot_brk_tick) if d > 0 else (pt <= dot_brk_tick)
                    if broke:
                        pend_fill[s] = 1

                if rem_wait <= 0:
                    break

        # Paso 2: evaluar brackets deduplicando fills identicos (mismo f_idx & f_tick)
        for s in range(n_setups):
            fi = f_idx[s]
            if fi < 0:
                continue
            ft = f_tick[s]
            # Buscar si un setup anterior ya resolvio exactamente este (fi, ft)
            dup = -1
            for s0 in range(s):
                if f_idx[s0] == fi and f_tick[s0] == ft:
                    dup = s0
                    break
            if dup >= 0:
                for b in range(n_brackets):
                    gross_t[e, s, b] = gross_t[e, dup, b]
                continue

            f_ts = ts_ns[fi]
            done = np.zeros(n_brackets, np.int8)
            rem_b = n_brackets
            for j in range(fi + 1, n):
                el_b = ts_ns[j] - f_ts
                signed_t = d * (px_tick[j] - ft)
                for b in range(n_brackets):
                    if done[b] == 1:
                        continue
                    sl = sl_arr[b]
                    tp = tp_arr[b]
                    if signed_t <= -sl:
                        gross_t[e, s, b] = float(-sl)
                        done[b] = 1
                        rem_b -= 1
                    elif signed_t >= tp:
                        gross_t[e, s, b] = float(tp)
                        done[b] = 1
                        rem_b -= 1
                    elif el_b >= max_ns_arr[b]:
                        gross_t[e, s, b] = float(signed_t)
                        done[b] = 1
                        rem_b -= 1
                if rem_b <= 0:
                    break

            # Si termino la sesion antes de cerrar algun bracket, cerrar al ultimo tick de sesion
            if rem_b > 0:
                eod_t = float(d * (px_tick[n - 1] - ft))
                for b in range(n_brackets):
                    if done[b] == 0:
                        gross_t[e, s, b] = eod_t

    return fill_ok, fill_spread, gross_t, imm_h_ret


# --------------------------------------------------------------------------- Evaluador multi-sesion con estadistica EdgeLab
def fricciones_nq_canonicas() -> dict[str, float]:
    """Devuelve diccionario de fricciones RT en ticks desde `edgelab.costos` + referencia 2t NT8."""
    return {
        "nt8_2t": 2.0,
        "base_canon": float(costos.friccion_rt_ticks("NQ", "base", incluye_spread=True)),
        "adverso_canon": float(costos.friccion_rt_ticks("NQ", "adverso", incluye_spread=True)),
        "no_spread_base": float(costos.friccion_rt_ticks("NQ", "base", incluye_spread=False)),
    }


def _mascara_regimen(
    ny_hhmm: np.ndarray,
    spread_ev: np.ndarray,
    with_vwap: np.ndarray,
    cd60_ok: np.ndarray,
) -> dict[str, np.ndarray]:
    ny_rth = (ny_hhmm >= 930) & (ny_hhmm < 1600)
    ny_am = (ny_hhmm >= 930) & (ny_hhmm < 1200)
    sp2 = (spread_ev >= 0.0) & (spread_ev <= 2.0)
    fade_vw = with_vwap == -1
    cd60 = cd60_ok == 1
    return {
        "ALL_24H": np.ones(len(ny_hhmm), dtype=bool),
        "NY_RTH": ny_rth,
        "NY_AM": ny_am,
        "NY_RTH_SP2": ny_rth & sp2,
        "NY_AM_SP2": ny_am & sp2,
        "NY_RTH_SP2_FADE_VWAP": ny_rth & sp2 & fade_vw,
        "NY_AM_SP2_FADE_VWAP": ny_am & sp2 & fade_vw,
        "NY_RTH_CD60_SP2": ny_rth & sp2 & cd60,
        "NY_AM_CD60_SP2": ny_am & sp2 & cd60,
    }


def _mascara_variante(var_mask: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "ALL_PERM": np.ones(len(var_mask), dtype=bool),
        "V1_CLASSIC": (var_mask & 1) > 0,
        "V2_ABSORB": (var_mask & 2) > 0,
        "V3_ADAPTIVE": (var_mask & 4) > 0,
        "V4_BURST": (var_mask & 8) > 0,
        "V5_STOPRUN": (var_mask & 16) > 0,
        "ANY_STRICT": (var_mask & 31) > 0,
    }


def _calc_profit_factor(netos: np.ndarray) -> float:
    gp = float(netos[netos > 0.0].sum())
    gl = float((-netos[netos < 0.0]).sum())
    if gl <= 1e-12:
        return 99.9 if gp > 0 else 0.0
    return gp / gl


def evaluar_sesiones(
    sesiones_iter,
    *,
    split_oos_desde: int = 20260401,
    tick_size: float | None = None,
    eval_delayed_all_perm: bool = False,
    min_ops_desc: int = 20,
    min_ops_oos: int = 10,
    n_boot: int = 1000,
) -> dict:
    """Corre deteccion 1-tick causal y simulacion EdgeLab sobre bloques `(df sesion)` y genera informe completo.

    Cada `df` debe traer columnas `ts_ns, px, vol, sesion` (+ opcional `bid, ask`) de sesiones < `HOLDOUT_PRIMERA_SESION_INT`.
    """
    tick_size = TICK_NQ if tick_size is None else tick_size
    setup_kind = np.array([s[0] for s in SETUP_SPECS], dtype=np.int8)
    setup_param_x = np.array([s[1] for s in SETUP_SPECS], dtype=np.int64)
    sl_arr = np.array(BRACKET_SL, dtype=np.int64)
    tp_arr = np.array(BRACKET_TP, dtype=np.int64)
    max_ns_arr = np.array(BRACKET_MAX_NS, dtype=np.int64)
    fricc = fricciones_nq_canonicas()

    # Acumular eventos y resultados por sesion en memoria compacta
    buf_ses = []
    buf_ny_hhmm = []
    buf_spread = []
    buf_vwap = []
    buf_cd60 = []
    buf_vmask = []
    buf_fill_ok = []
    buf_fill_sp = []
    buf_gross = []
    buf_imm_h = []

    sesiones_vistas = []
    total_ticks = 0

    for df in sesiones_iter:
        if df is None or not len(df):
            continue
        ses_id = int(df["sesion"].iloc[0])
        if ses_id >= HOLDOUT_PRIMERA_SESION_INT:
            raise ValueError(f"HOLDOUT-A4 violado: sesion {ses_id} >= {HOLDOUT_PRIMERA_SESION_INT}")

        sesiones_vistas.append(ses_id)
        total_ticks += len(df)
        bid = df["bid"].to_numpy() if "bid" in df.columns else None
        ask = df["ask"].to_numpy() if "ask" in df.columns else None
        det = detectar_eventos_tick(
            df["ts_ns"].to_numpy(),
            df["px"].to_numpy(),
            df["vol"].to_numpy(),
            bid,
            ask,
            tick_size=tick_size,
        )
        n_e = len(det["sig_idx"])
        if n_e == 0:
            continue

        f_ok, f_sp, g_t, imm_h = _simular_eventos_sesion_nb(
            df["ts_ns"].to_numpy(np.int64),
            det["px_tick"],
            det["spread_at_tick"],
            det["sig_idx"],
            det["dir"],
            det["dot_tick"],
            det["arrow_tick"],
            det["ext_tick"],
            det["bar_close_idx"],
            det["bar_hi"],
            det["bar_lo"],
            det["var_mask"],
            setup_kind,
            setup_param_x,
            sl_arr,
            tp_arr,
            max_ns_arr,
            1,
            300_000_000_000,
            eval_delayed_all_perm,
        )

        buf_ses.append(np.full(n_e, ses_id, dtype=np.int64))
        buf_ny_hhmm.append(det["ny_hhmm"])
        buf_spread.append(det["spread_ticks"])
        buf_vwap.append(det["with_vwap"])
        buf_cd60.append(det["cd60_ok"])
        buf_vmask.append(det["var_mask"])
        buf_fill_ok.append(f_ok)
        buf_fill_sp.append(f_sp)
        buf_gross.append(g_t)
        buf_imm_h.append(imm_h)

    if not buf_ses:
        return {"error": "sin_eventos", "sesiones": len(sesiones_vistas), "total_ticks": int(total_ticks)}

    ses_all = np.concatenate(buf_ses)
    hhmm_all = np.concatenate(buf_ny_hhmm)
    sp_all = np.concatenate(buf_spread)
    vw_all = np.concatenate(buf_vwap)
    cd60_all = np.concatenate(buf_cd60)
    vm_all = np.concatenate(buf_vmask)
    fill_ok = np.concatenate(buf_fill_ok, axis=0)
    fill_sp = np.concatenate(buf_fill_sp, axis=0)
    gross_all = np.concatenate(buf_gross, axis=0)
    imm_h_all = np.concatenate(buf_imm_h, axis=0)

    is_desc = ses_all < split_oos_desde
    is_oos = ses_all >= split_oos_desde
    meses_all = ses_all // 100

    regs = _mascara_regimen(hhmm_all, sp_all, vw_all, cd60_all)
    vars_m = _mascara_variante(vm_all)

    # 1) Tabla IMM drift a 30s / 60s / 180s
    imm_drifts = []
    for r_name in ("ALL_24H", "NY_RTH", "NY_AM"):
        rm = regs[r_name]
        for v_name, vm in vars_m.items():
            m = rm & vm & (fill_ok[:, 0] == 1)
            if int(m.sum()) < 10:
                continue
            rec = {"regimen": r_name, "variante": v_name, "n_total": int(m.sum()), "n_desc": int((m & is_desc).sum()), "n_oos": int((m & is_oos).sum())}
            for hi, h_lbl in enumerate(("30s", "60s", "180s")):
                vals = imm_h_all[m, hi]
                ok = np.isfinite(vals)
                rec[f"ret_{h_lbl}_t"] = round(float(np.mean(vals[ok])), 3) if ok.any() else None
                rec[f"wr_{h_lbl}_pct"] = round(float(np.mean(vals[ok] > 0.0) * 100.0), 1) if ok.any() else None
            imm_drifts.append(rec)

    # 2) Barrido de celdas (variante x regimen x setup x bracket)
    celdas = []
    pvals_desc_canon = []
    # Matriz por periodo mensual para PBO CSCV sobre las candidatas
    meses_unicos = sorted(set(int(x) for x in meses_all.tolist()))
    celda_mes_pnls = []

    for v_name, vm in vars_m.items():
        if int(vm.sum()) < min_ops_desc:
            continue
        is_perm_only = (v_name == "ALL_PERM") and (not eval_delayed_all_perm)
        for r_name, rm in regs.items():
            base_m = vm & rm
            if int(base_m.sum()) < min_ops_desc:
                continue
            for s_idx, s_name in enumerate(SETUP_NAMES):
                if is_perm_only and s_idx > 0:
                    continue
                ms = base_m & (fill_ok[:, s_idx] == 1)
                n_d = int((ms & is_desc).sum())
                n_o = int((ms & is_oos).sum())
                if n_d < min_ops_desc:
                    continue

                f_sp_s = fill_sp[:, s_idx]
                real_fricc_s = np.where(f_sp_s >= 0.0, f_sp_s + fricc["no_spread_base"], fricc["base_canon"])

                for b_idx, (b_name, sl_t, _, _) in enumerate(BRACKET_SPECS):
                    g = gross_all[:, s_idx, b_idx]
                    valid = ms & np.isfinite(g)
                    idx_d = valid & is_desc
                    idx_o = valid & is_oos
                    nd = int(idx_d.sum())
                    no = int(idx_o.sum())
                    if nd < min_ops_desc:
                        continue

                    g_d = g[idx_d]
                    ses_d = ses_all[idx_d]
                    mes_d = meses_all[idx_d]

                    net_d_2t = (g_d - fricc["nt8_2t"]) / sl_t
                    net_d_canon = (g_d - fricc["base_canon"]) / sl_t
                    net_d_adv = (g_d - fricc["adverso_canon"]) / sl_t
                    net_d_real = (g_d - real_fricc_s[idx_d]) / sl_t

                    rs_d_2t = ESC.resumen_sesiones(net_d_2t, ses_d, n_boot=n_boot, seed=20261113)
                    rs_d_canon = ESC.resumen_sesiones(net_d_canon, ses_d, n_boot=n_boot, seed=20261113)

                    pvals_desc_canon.append(float(rs_d_canon["p_unilateral"]))

                    row = {
                        "variante": v_name,
                        "regimen": r_name,
                        "setup": s_name,
                        "bracket": b_name,
                        "sl_t": int(sl_t),
                        "n_desc": nd,
                        "ses_desc": int(rs_d_canon["n_sesiones"]),
                        "expR_desc_2t": round(float(net_d_2t.mean()), 4),
                        "expR_desc_canon": round(float(net_d_canon.mean()), 4),
                        "expT_desc_canon": round(float((g_d - fricc["base_canon"]).mean()), 3),
                        "expR_desc_real": round(float(net_d_real.mean()), 4),
                        "expR_desc_adv": round(float(net_d_adv.mean()), 4),
                        "wr_desc_canon_pct": round(float((net_d_canon > 0.0).mean() * 100.0), 1),
                        "pf_desc_2t": round(_calc_profit_factor(net_d_2t), 3),
                        "pf_desc_canon": round(_calc_profit_factor(net_d_canon), 3),
                        "p_desc_2t": round(float(rs_d_2t["p_unilateral"]), 6),
                        "p_desc_canon": round(float(rs_d_canon["p_unilateral"]), 6),
                        "ic90_desc_canon": [round(float(x), 4) for x in rs_d_canon["ic"]],
                        "n_oos": no,
                    }

                    if no >= min_ops_oos:
                        g_o = g[idx_o]
                        ses_o = ses_all[idx_o]
                        net_o_2t = (g_o - fricc["nt8_2t"]) / sl_t
                        net_o_canon = (g_o - fricc["base_canon"]) / sl_t
                        net_o_adv = (g_o - fricc["adverso_canon"]) / sl_t
                        net_o_real = (g_o - real_fricc_s[idx_o]) / sl_t
                        rs_o_2t = ESC.resumen_sesiones(net_o_2t, ses_o, n_boot=n_boot, seed=20261114)
                        rs_o_canon = ESC.resumen_sesiones(net_o_canon, ses_o, n_boot=n_boot, seed=20261114)
                        econ = ESC.economia(net_d_canon, netos_adverso=net_d_adv, periodos=mes_d.tolist())
                        row.update(
                            ses_oos=int(rs_o_canon["n_sesiones"]),
                            expR_oos_2t=round(float(net_o_2t.mean()), 4),
                            expR_oos_canon=round(float(net_o_canon.mean()), 4),
                            expT_oos_canon=round(float((g_o - fricc["base_canon"]).mean()), 3),
                            expR_oos_real=round(float(net_o_real.mean()), 4),
                            expR_oos_adv=round(float(net_o_adv.mean()), 4),
                            wr_oos_canon_pct=round(float((net_o_canon > 0.0).mean() * 100.0), 1),
                            pf_oos_2t=round(_calc_profit_factor(net_o_2t), 3),
                            pf_oos_canon=round(_calc_profit_factor(net_o_canon), 3),
                            p_oos_2t=round(float(rs_o_2t["p_unilateral"]), 6),
                            p_oos_canon=round(float(rs_o_canon["p_unilateral"]), 6),
                            ic90_oos_canon=[round(float(x), 4) for x in rs_o_canon["ic"]],
                            econ_desc_pasa=bool(econ["pasa"]),
                            econ_desc_sin_top5=round(float(econ["sin_top5_por_op"]), 4),
                            periodos_pos_desc=econ.get("periodos_positivos", ""),
                        )
                    else:
                        row.update(ses_oos=0, expR_oos_2t=None, expR_oos_canon=None)

                    celdas.append(row)

                    # Guardar aporte mensual sobre todas las sesiones para CSCV si tiene buena muestra
                    if len(meses_unicos) >= 8:
                        g_all = g[valid]
                        m_all_c = meses_all[valid]
                        net_all_canon = (g_all - fricc["base_canon"]) / sl_t
                        por_m = {}
                        for mm_id, val in zip(m_all_c.tolist(), net_all_canon.tolist()):
                            s_p, c_p = por_m.get(int(mm_id), (0.0, 0))
                            por_m[int(mm_id)] = (s_p + float(val), c_p + 1)
                        celda_mes_pnls.append((len(celdas) - 1, por_m))

    # 3) Tamiz FDR Storey (q=0.10) en DESC canonico
    if celdas:
        tamiz = ESC.tamiz_fdr(pvals_desc_canon, q=0.10, metodo="storey")
        q_vals = tamiz["q_valores"]
        nom_set = set(tamiz["nominadas"])
        for idx, c in enumerate(celdas):
            c["q_desc_canon"] = round(float(q_vals[idx]), 5)
            c["nominada_fdr"] = idx in nom_set
    else:
        tamiz = {"nominadas": [], "pi0": 1.0, "m": 0}

    # 4) PBO CSCV (g2_ratio) sobre top 30 celdas por ExpR_desc_canon (donde todos los meses tienen >0 trades)
    pbo_info = {"calculable": False}
    if len(celda_mes_pnls) >= 2 and len(meses_unicos) >= 8:
        candidatas_idx = sorted(range(len(celdas)), key=lambda i: celdas[i]["expR_desc_canon"], reverse=True)[:40]
        por_m_map = {ci: mp for ci, mp in celda_mes_pnls if ci in set(candidatas_idx)}
        # Filtrar candidatas que tengan >=1 trade en cada uno de los meses >= 8 bloques
        valid_cands = [ci for ci in candidatas_idx if ci in por_m_map and all(por_m_map[ci].get(m, (0.0, 0))[1] > 0 for m in meses_unicos)]
        if len(valid_cands) >= 2:
            mat = [[G2.RatioCell(*por_m_map[ci][m]) for ci in valid_cands] for m in meses_unicos]
            res_pbo = G2.pbo_ratio_cscv(mat, s=8)
            pbo_info = {
                "calculable": True,
                "n_configs": res_pbo.n_configs,
                "n_meses": res_pbo.n_rows,
                "pbo": round(float(res_pbo.pbo), 4),
                "passed_pbo_le_050": bool(res_pbo.passed),
            }

    # Ordenar rankings claros
    top_canon_desc = sorted(celdas, key=lambda r: (r["expR_desc_canon"], r["n_desc"]), reverse=True)[:40]
    replican_canon = [
        r for r in celdas
        if r.get("expR_oos_canon") is not None and r["expR_desc_canon"] > 0.0 and r["expR_oos_canon"] > 0.0
    ]
    replican_canon.sort(key=lambda r: min(r["expR_desc_canon"], r["expR_oos_canon"]) * math.sqrt(min(r["n_desc"], r["n_oos"])), reverse=True)

    replican_2t = [
        r for r in celdas
        if r.get("expR_oos_2t") is not None and r["expR_desc_2t"] > 0.0 and r["expR_oos_2t"] > 0.0
    ]
    replican_2t.sort(key=lambda r: min(r["expR_desc_2t"], r["expR_oos_2t"]) * math.sqrt(min(r["n_desc"], r["n_oos"])), reverse=True)

    return {
        "nombre": NOMBRE,
        "sesiones_procesadas": len(sesiones_vistas),
        "rango_sesiones": [min(sesiones_vistas), max(sesiones_vistas)] if sesiones_vistas else [],
        "split_oos_desde": int(split_oos_desde),
        "total_ticks": int(total_ticks),
        "total_eventos_permisivos": int(len(ses_all)),
        "total_eventos_strict": int(((vm_all & 31) > 0).sum()),
        "total_eventos_v4_burst": int(((vm_all & 8) > 0).sum()),
        "fricciones_ticks": fricc,
        "n_celdas_evaluadas": len(celdas),
        "tamiz_fdr_desc_canon": {
            "m_pruebas": tamiz["m"],
            "pi0_storey": round(float(tamiz["pi0"]), 4),
            "n_nominadas_q10": len(tamiz["nominadas"]),
        },
        "pbo_cscv_top_canon": pbo_info,
        "imm_horizontes": imm_drifts,
        "n_replican_canon": len(replican_canon),
        "n_replican_2t": len(replican_2t),
        "top_replican_canon": replican_canon[:30],
        "top_replican_2t": replican_2t[:30],
        "top_desc_canon": top_canon_desc[:25],
    }


# --------------------------------------------------------------------------- Campana 2 Focalizada: Solo V4_BURST (Strict / Med / Wide)
V4_SETUP_NAMES = (
    "IMM",
    "BRK_VELA_X24",
    "BRK_VELA_X48",
    "BRK_FLECHA_X24",
    "BRK_FLECHA_X48",
)
V4_SETUP_SPECS = ((0, 0), (1, 24), (1, 48), (2, 24), (2, 48))
V4_BRACKETS = (
    ("80_120", 80, 120, 3600),
    ("120_120", 120, 120, 5400),
    ("100_200", 100, 200, 5400),
)
V4_GATES = (
    ("V4_STRICT", 8),
    ("V4_MED", 32),
    ("V4_WIDE", 64),
)
V4_REGIMES = ("NY_RTH_CD60_SP2", "NY_AM_CD60_SP2", "NY_AM_SP2_FADE_VWAP")


def _aplicar_cooldown_v4(ts_ns: np.ndarray, mask: np.ndarray, cooldown_sec: int = 60) -> np.ndarray:
    """Cooldown causal aplicado solo entre senales de la propia compuerta V4 (sin bloquear por ruido P)."""
    out = np.zeros(len(ts_ns), dtype=bool)
    min_ns = np.int64(cooldown_sec) * np.int64(1_000_000_000)
    last_t = np.int64(-1)
    for idx in np.flatnonzero(mask):
        t = np.int64(ts_ns[idx])
        if last_t < 0 or (t - last_t) >= min_ns:
            out[idx] = True
            last_t = t
    return out


def _simular_prop_oos(net_ticks: np.ndarray, sesiones: np.ndarray, *, usd_por_tick: float = 5.0) -> dict:
    """Metricas de cuenta fondeada ($3k DD ref) sobre trades cronologicos en USD."""
    if not len(net_ticks):
        return {"net_usd": 0.0, "max_dd_usd": 0.0, "max_eod_dd_usd": 0.0, "worst_day_usd": 0.0, "sobrevive_3k_eod": False}
    pnls = net_ticks * usd_por_tick
    eq = np.cumsum(pnls)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    dd_intraday = float(np.max(peak - eq))

    por_dia = {}
    for s, p in zip(sesiones.tolist(), pnls.tolist()):
        por_dia[int(s)] = por_dia.get(int(s), 0.0) + p
    dias_pnl = [por_dia[k] for k in sorted(por_dia)]
    eq_eod = np.cumsum(dias_pnl)
    peak_eod = np.maximum.accumulate(np.concatenate([[0.0], eq_eod]))[1:]
    dd_eod = float(np.max(peak_eod - eq_eod)) if len(eq_eod) else 0.0
    worst_day = float(min(dias_pnl)) if dias_pnl else 0.0
    return {
        "net_usd": round(float(eq[-1]), 1),
        "max_dd_usd": round(dd_intraday, 1),
        "max_eod_dd_usd": round(dd_eod, 1),
        "worst_day_usd": round(worst_day, 1),
        "sobrevive_3k_eod": bool(dd_eod < 3000.0 and eq[-1] > 0.0),
    }


def evaluar_v4_focalizado(
    sesiones_iter,
    *,
    split_oos_desde: int = 20260401,
    tick_size: float | None = None,
    min_ops_desc: int = 20,
    min_ops_oos: int = 15,
    n_boot: int = 2000,
) -> dict:
    """Campana 2 preregistrada: solo compuertas V4 (STRICT/MED/WIDE) para maximizar potencia FDR + CSCV PBO + Walk-Forward."""
    tick_size = TICK_NQ if tick_size is None else tick_size
    setup_kind = np.array([s[0] for s in V4_SETUP_SPECS], dtype=np.int8)
    setup_param_x = np.array([s[1] for s in V4_SETUP_SPECS], dtype=np.int64)
    sl_arr = np.array([b[1] for b in V4_BRACKETS], dtype=np.int64)
    tp_arr = np.array([b[2] for b in V4_BRACKETS], dtype=np.int64)
    max_ns_arr = np.array([b[3] * 1_000_000_000 for b in V4_BRACKETS], dtype=np.int64)
    fricc = fricciones_nq_canonicas()

    buf_ses, buf_ts, buf_hhmm, buf_sp, buf_vw, buf_vm = [], [], [], [], [], []
    buf_fok, buf_fsp, buf_gross, buf_imm = [], [], [], []
    sesiones_vistas = []
    total_ticks = 0
    total_perm = 0

    for df in sesiones_iter:
        if df is None or not len(df):
            continue
        ses_id = int(df["sesion"].iloc[0])
        if ses_id >= HOLDOUT_PRIMERA_SESION_INT:
            raise ValueError(f"HOLDOUT-A4 violado: sesion {ses_id} >= {HOLDOUT_PRIMERA_SESION_INT}")

        sesiones_vistas.append(ses_id)
        total_ticks += len(df)
        bid = df["bid"].to_numpy() if "bid" in df.columns else None
        ask = df["ask"].to_numpy() if "ask" in df.columns else None
        det = detectar_eventos_tick(
            df["ts_ns"].to_numpy(),
            df["px"].to_numpy(),
            df["vol"].to_numpy(),
            bid,
            ask,
            tick_size=tick_size,
        )
        n_e = len(det["sig_idx"])
        total_perm += n_e
        if n_e == 0:
            continue

        # Conservar SOLO eventos que enciendan al menos V4_STRICT (8), V4_MED (32) o V4_WIDE (64)
        v4_any = (det["var_mask"] & (8 | 32 | 64)) > 0
        if not v4_any.any():
            continue

        f_ok, f_sp, g_t, imm_h = _simular_eventos_sesion_nb(
            df["ts_ns"].to_numpy(np.int64),
            det["px_tick"],
            det["spread_at_tick"],
            det["sig_idx"][v4_any],
            det["dir"][v4_any],
            det["dot_tick"][v4_any],
            det["arrow_tick"][v4_any],
            det["ext_tick"][v4_any],
            det["bar_close_idx"][v4_any],
            det["bar_hi"][v4_any],
            det["bar_lo"][v4_any],
            det["var_mask"][v4_any],
            setup_kind,
            setup_param_x,
            sl_arr,
            tp_arr,
            max_ns_arr,
            1,
            300_000_000_000,
            False,
        )

        m_cnt = int(v4_any.sum())
        buf_ses.append(np.full(m_cnt, ses_id, dtype=np.int64))
        buf_ts.append(det["ts_ns"][v4_any])
        buf_hhmm.append(det["ny_hhmm"][v4_any])
        buf_sp.append(det["spread_ticks"][v4_any])
        buf_vw.append(det["with_vwap"][v4_any])
        buf_vm.append(det["var_mask"][v4_any])
        buf_fok.append(f_ok)
        buf_fsp.append(f_sp)
        buf_gross.append(g_t)
        buf_imm.append(imm_h)

    if not buf_ses:
        return {"error": "sin_eventos_v4", "sesiones": len(sesiones_vistas), "total_ticks": int(total_ticks)}

    ses_all = np.concatenate(buf_ses)
    ts_all = np.concatenate(buf_ts)
    hhmm_all = np.concatenate(buf_hhmm)
    sp_all = np.concatenate(buf_sp)
    vw_all = np.concatenate(buf_vw)
    vm_all = np.concatenate(buf_vm)
    fill_ok = np.concatenate(buf_fok, axis=0)
    fill_sp = np.concatenate(buf_fsp, axis=0)
    gross_all = np.concatenate(buf_gross, axis=0)
    imm_h_all = np.concatenate(buf_imm, axis=0)

    is_desc = ses_all < split_oos_desde
    is_oos = ses_all >= split_oos_desde
    meses_all = ses_all // 100

    # Definir 8 bloques cronologicos uniformes sobre sesiones_vistas para CSCV PBO y 4 folds para Walk-Forward
    ses_ord = sorted(set(int(s) for s in sesiones_vistas))
    s_to_b8 = {s: min(7, (idx * 8) // max(1, len(ses_ord))) for idx, s in enumerate(ses_ord)}
    s_to_wf4 = {s: min(3, (idx * 4) // max(1, len(ses_ord))) for idx, s in enumerate(ses_ord)}
    blk8_all = np.array([s_to_b8[int(s)] for s in ses_all.tolist()], dtype=np.int64)
    wf4_all = np.array([s_to_wf4[int(s)] for s in ses_all.tolist()], dtype=np.int64)

    ny_rth = (hhmm_all >= 930) & (hhmm_all < 1600)
    ny_am = (hhmm_all >= 930) & (hhmm_all < 1200)
    sp2 = (sp_all >= 0.0) & (sp_all <= 2.0)
    fade_vw = vw_all == -1

    # 1) Deriva cruda IMM por nivel V4 (control cero grados de libertad)
    imm_resumen = []
    for g_name, g_bit in V4_GATES:
        gm = (vm_all & g_bit) > 0
        for r_name, rm in (("ALL_24H", np.ones(len(gm), bool)), ("NY_RTH", ny_rth), ("NY_AM", ny_am)):
            m = gm & rm & (fill_ok[:, 0] == 1)
            if int(m.sum()) < 10:
                continue
            rec = {"gate": g_name, "regimen": r_name, "n_total": int(m.sum()), "n_desc": int((m & is_desc).sum()), "n_oos": int((m & is_oos).sum())}
            for hi, h_lbl in enumerate(("30s", "60s", "180s")):
                vals = imm_h_all[m, hi]
                ok = np.isfinite(vals)
                rec[f"ret_{h_lbl}_t"] = round(float(np.mean(vals[ok])), 3) if ok.any() else None
                rec[f"wr_{h_lbl}_pct"] = round(float(np.mean(vals[ok] > 0.0) * 100.0), 1) if ok.any() else None
            imm_resumen.append(rec)

    # 2) Grilla preregistrada: 3 compuertas x 3 regimenes x 4 setups BRK x 3 brackets (108 celdas máx)
    celdas = []
    pvals_desc_canon = []
    pvals_desc_2t = []
    por_b8_celdas = []
    por_wf4_celdas = []

    for g_name, g_bit in V4_GATES:
        gm = (vm_all & g_bit) > 0
        gm_cd60 = _aplicar_cooldown_v4(ts_all, gm, cooldown_sec=60)
        reg_map = {
            "NY_RTH_CD60_SP2": gm_cd60 & ny_rth & sp2,
            "NY_AM_CD60_SP2": gm_cd60 & ny_am & sp2,
            "NY_AM_SP2_FADE_VWAP": gm_cd60 & ny_am & sp2 & fade_vw,
        }
        for r_name in V4_REGIMES:
            rm = reg_map[r_name]
            for s_idx in range(1, len(V4_SETUP_NAMES)):
                s_name = V4_SETUP_NAMES[s_idx]
                ms = rm & (fill_ok[:, s_idx] == 1)
                f_sp_s = fill_sp[:, s_idx]
                real_fricc_s = np.where(f_sp_s >= 0.0, f_sp_s + fricc["no_spread_base"], fricc["base_canon"])

                for b_idx, (b_name, sl_t, _, _) in enumerate(V4_BRACKETS):
                    g = gross_all[:, s_idx, b_idx]
                    valid = ms & np.isfinite(g)
                    idx_d = valid & is_desc
                    idx_o = valid & is_oos
                    nd = int(idx_d.sum())
                    no = int(idx_o.sum())
                    if nd < min_ops_desc or no < min_ops_oos:
                        continue

                    g_d, g_o = g[idx_d], g[idx_o]
                    ses_d, ses_o = ses_all[idx_d], ses_all[idx_o]

                    net_d_2t = (g_d - fricc["nt8_2t"]) / sl_t
                    net_d_canon = (g_d - fricc["base_canon"]) / sl_t
                    net_d_adv = (g_d - fricc["adverso_canon"]) / sl_t
                    net_d_real = (g_d - real_fricc_s[idx_d]) / sl_t

                    net_o_2t = (g_o - fricc["nt8_2t"]) / sl_t
                    net_o_canon = (g_o - fricc["base_canon"]) / sl_t
                    net_o_adv = (g_o - fricc["adverso_canon"]) / sl_t
                    net_o_real = (g_o - real_fricc_s[idx_o]) / sl_t

                    rs_d_canon = ESC.resumen_sesiones(net_d_canon, ses_d, n_boot=n_boot, seed=20261113)
                    rs_o_canon = ESC.resumen_sesiones(net_o_canon, ses_o, n_boot=n_boot, seed=20261114)
                    rs_d_2t = ESC.resumen_sesiones(net_d_2t, ses_d, n_boot=n_boot, seed=20261113)
                    rs_o_2t = ESC.resumen_sesiones(net_o_2t, ses_o, n_boot=n_boot, seed=20261114)
                    econ_all = ESC.economia((g[valid] - fricc["base_canon"]) / sl_t, netos_adverso=(g[valid] - fricc["adverso_canon"]) / sl_t, periodos=(meses_all[valid]).tolist())

                    prop_nq_oos = _simular_prop_oos(g_o - fricc["base_canon"], ses_o, usd_por_tick=5.0)
                    prop_mnq2_oos = _simular_prop_oos(g_o - fricc["base_canon"], ses_o, usd_por_tick=1.0)

                    pvals_desc_canon.append(float(rs_d_canon["p_unilateral"]))
                    pvals_desc_2t.append(float(rs_d_2t["p_unilateral"]))

                    row = {
                        "gate": g_name,
                        "regimen": r_name,
                        "setup": s_name,
                        "bracket": b_name,
                        "sl_t": int(sl_t),
                        "n_desc": nd,
                        "ses_desc": int(rs_d_canon["n_sesiones"]),
                        "expR_desc_2t": round(float(net_d_2t.mean()), 4),
                        "expR_desc_canon": round(float(net_d_canon.mean()), 4),
                        "expT_desc_canon": round(float((g_d - fricc["base_canon"]).mean()), 3),
                        "expR_desc_real": round(float(net_d_real.mean()), 4),
                        "expR_desc_adv": round(float(net_d_adv.mean()), 4),
                        "wr_desc_canon_pct": round(float((net_d_canon > 0.0).mean() * 100.0), 1),
                        "pf_desc_canon": round(_calc_profit_factor(net_d_canon), 3),
                        "p_desc_canon": round(float(rs_d_canon["p_unilateral"]), 6),
                        "p_desc_2t": round(float(rs_d_2t["p_unilateral"]), 6),
                        "ic90_desc_canon": [round(float(x), 4) for x in rs_d_canon["ic"]],
                        "n_oos": no,
                        "ses_oos": int(rs_o_canon["n_sesiones"]),
                        "expR_oos_2t": round(float(net_o_2t.mean()), 4),
                        "expR_oos_canon": round(float(net_o_canon.mean()), 4),
                        "expT_oos_canon": round(float((g_o - fricc["base_canon"]).mean()), 3),
                        "expR_oos_real": round(float(net_o_real.mean()), 4),
                        "expR_oos_adv": round(float(net_o_adv.mean()), 4),
                        "wr_oos_canon_pct": round(float((net_o_canon > 0.0).mean() * 100.0), 1),
                        "pf_oos_canon": round(_calc_profit_factor(net_o_canon), 3),
                        "p_oos_canon": round(float(rs_o_canon["p_unilateral"]), 6),
                        "p_oos_2t": round(float(rs_o_2t["p_unilateral"]), 6),
                        "ic90_oos_canon": [round(float(x), 4) for x in rs_o_canon["ic"]],
                        "econ_pasa": bool(econ_all["pasa"]),
                        "econ_sin_top5": round(float(econ_all["sin_top5_por_op"]), 4),
                        "periodos_pos": econ_all.get("periodos_positivos", ""),
                        "prop_1nq_oos": prop_nq_oos,
                        "prop_2mnq_oos": prop_mnq2_oos,
                    }
                    celdas.append(row)

                    net_all_canon = (g[valid] - fricc["base_canon"]) / sl_t
                    b8_map = {}
                    for b_id, val in zip(blk8_all[valid].tolist(), net_all_canon.tolist()):
                        sp, cp = b8_map.get(int(b_id), (0.0, 0))
                        b8_map[int(b_id)] = (sp + float(val), cp + 1)
                    por_b8_celdas.append(b8_map)

                    wf4_map = {}
                    for w_id, val in zip(wf4_all[valid].tolist(), net_all_canon.tolist()):
                        sp, cp = wf4_map.get(int(w_id), (0.0, 0))
                        wf4_map[int(w_id)] = (sp + float(val), cp + 1)
                    por_wf4_celdas.append(wf4_map)

    tamiz_c = ESC.tamiz_fdr(pvals_desc_canon, q=0.10, metodo="storey") if celdas else {"nominadas": [], "q_valores": [], "pi0": 1.0, "m": 0}
    tamiz_2t = ESC.tamiz_fdr(pvals_desc_2t, q=0.10, metodo="storey") if celdas else {"nominadas": [], "q_valores": [], "pi0": 1.0, "m": 0}
    nom_c = set(tamiz_c["nominadas"])
    nom_2t = set(tamiz_2t["nominadas"])
    for idx, c in enumerate(celdas):
        c["q_desc_canon"] = round(float(tamiz_c["q_valores"][idx]), 5)
        c["q_desc_2t"] = round(float(tamiz_2t["q_valores"][idx]), 5)
        c["nominada_fdr_canon"] = idx in nom_c
        c["nominada_fdr_2t"] = idx in nom_2t

    # CSCV PBO (S=8) + Walk-Forward Ratio sobre todas las celdas que cubran los 8 bloques / 4 folds
    pbo_info = {"calculable": False}
    b8_valid = [i for i, mp in enumerate(por_b8_celdas) if all(mp.get(b, (0.0, 0))[1] > 0 for b in range(8))]
    if len(b8_valid) >= 2:
        mat8 = [[G2.RatioCell(*por_b8_celdas[i][b]) for i in b8_valid] for b in range(8)]
        res_pbo = G2.pbo_ratio_cscv(mat8, s=8)
        pbo_info = {
            "calculable": True,
            "n_configs": res_pbo.n_configs,
            "n_bloques": res_pbo.n_rows,
            "pbo": round(float(res_pbo.pbo), 4),
            "passed_pbo_le_050": bool(res_pbo.passed),
        }

    wf_info = {"calculable": False}
    wf4_valid = [i for i, mp in enumerate(por_wf4_celdas) if all(mp.get(f, (0.0, 0))[1] > 0 for f in range(4))]
    if len(wf4_valid) >= 2:
        per_fold = {
            f"{celdas[i]['gate']}|{celdas[i]['regimen']}|{celdas[i]['setup']}|{celdas[i]['bracket']}": {
                f: G2.RatioCell(*por_wf4_celdas[i][f]) for f in range(4)
            }
            for i in wf4_valid
        }
        res_wf = G2.walk_forward_ratio(per_fold, [0, 1, 2, 3])
        wf_info = {
            "calculable": True,
            "n_configs": len(wf4_valid),
            "oos_ratio_R": round(float(res_wf.observed), 4),
            "oos_total_R": round(float(res_wf.total_pnl), 2),
            "oos_trades": int(res_wf.total_n_trades),
            "passed_wf_gt_0": bool(res_wf.passed),
            "selecciones": [
                {"fold": int(s.fold), "config": str(s.selected_config), "oos_R": round(float(s.oos_ratio), 4), "oos_n": int(s.oos_n_trades)}
                for s in res_wf.selections
            ],
        }

    # PBO separado por cada compuerta (V4_STRICT / V4_MED / V4_WIDE)
    pbo_por_gate = {}
    for g_name, _ in V4_GATES:
        g_idx = [i for i in b8_valid if celdas[i]["gate"] == g_name]
        if len(g_idx) >= 2:
            mat_g = [[G2.RatioCell(*por_b8_celdas[i][b]) for i in g_idx] for b in range(8)]
            rp = G2.pbo_ratio_cscv(mat_g, s=8)
            pbo_por_gate[g_name] = {"n_configs": rp.n_configs, "pbo": round(float(rp.pbo), 4), "passed": bool(rp.passed)}

    replican_canon = [r for r in celdas if r["expR_desc_canon"] > 0.0 and r["expR_oos_canon"] > 0.0]
    replican_canon.sort(key=lambda r: min(r["expR_desc_canon"], r["expR_oos_canon"]) * math.sqrt(min(r["n_desc"], r["n_oos"])), reverse=True)

    return {
        "nombre": "DELTASWEEP-NQ-V4-FOCALIZADO",
        "sesiones_procesadas": len(sesiones_vistas),
        "rango_sesiones": [min(sesiones_vistas), max(sesiones_vistas)] if sesiones_vistas else [],
        "split_oos_desde": int(split_oos_desde),
        "total_ticks": int(total_ticks),
        "total_eventos_permisivos": int(total_perm),
        "conteo_compuertas": {
            "V4_STRICT": int(((vm_all & 8) > 0).sum()),
            "V4_MED": int(((vm_all & 32) > 0).sum()),
            "V4_WIDE": int(((vm_all & 64) > 0).sum()),
        },
        "fricciones_ticks": fricc,
        "n_celdas_evaluadas": len(celdas),
        "tamiz_fdr_desc_canon": {
            "m_pruebas": tamiz_c["m"],
            "pi0_storey": round(float(tamiz_c["pi0"]), 4),
            "n_nominadas_q10": len(tamiz_c["nominadas"]),
        },
        "tamiz_fdr_desc_2t": {
            "m_pruebas": tamiz_2t["m"],
            "pi0_storey": round(float(tamiz_2t["pi0"]), 4),
            "n_nominadas_q10": len(tamiz_2t["nominadas"]),
        },
        "pbo_cscv_8bloques": pbo_info,
        "pbo_por_compuerta": pbo_por_gate,
        "walk_forward_4folds": wf_info,
        "imm_horizontes_v4": imm_resumen,
        "n_replican_canon": len(replican_canon),
        "celdas_ordenadas_replica": replican_canon,
        "todas_celdas_top_desc": sorted(celdas, key=lambda r: r["expR_desc_canon"], reverse=True)[:25],
    }


# --------------------------------------------------------------------------- Campana 3: LIM_FLECHA + Secuencias + SL/TP Amplios
LIM_WIDE_BRACKETS = (
    ("120_240", 120, 240, 7200),
    ("160_160", 160, 160, 7200),
    ("160_320", 160, 320, 10800),
    ("200_200", 200, 200, 10800),
    ("200_400", 200, 400, 10800),
)
LIM_TIMEOUTS = (30, 60, 180, 300, 600)
LIM_SEQ_GAPS = (60, 180, 300, 600)
LIM_SEQ_GATES = (
    ("V4_STRICT", 8),
    ("V4_WIDE", 64),
    ("V2_ABSORB", 2),
    ("ANY_STRICT", 31),
)
LIM_SEQ_REGIMES = ("NY_RTH_SP2", "NY_AM_SP2")


@njit(cache=False)
def _simular_lim_flecha_sesion_nb(
    ts_ns: np.ndarray,
    px_tick: np.ndarray,
    spread_at_tick: np.ndarray,
    sig_idx: np.ndarray,
    ev_dir: np.ndarray,
    ev_arrow_tick: np.ndarray,
    sl_arr: np.ndarray,
    tp_arr: np.ndarray,
    max_ns_arr: np.ndarray,
    max_wait_ns: int = 600_000_000_000,
):
    """Simula entrada limite causal en `ev_arrow_tick` hasta `max_wait_ns` y evalua brackets amplios."""
    n = len(ts_ns)
    n_ev = len(sig_idx)
    n_b = len(sl_arr)

    hit_elapsed_s = np.full(n_ev, -1.0, np.float64)
    fill_spread = np.full(n_ev, -1.0, np.float64)
    gross_t = np.full((n_ev, n_b), np.nan, np.float64)
    exit_ts_ns = np.zeros((n_ev, n_b), np.int64)

    for e in range(n_ev):
        imm_idx = sig_idx[e] + 1
        if imm_idx + 1 >= n:
            continue
        d = ev_dir[e]
        arr_t = ev_arrow_tick[e]
        sig_ts = ts_ns[imm_idx]

        fill_j = np.int64(-1)
        for j in range(imm_idx + 1, n):
            el = ts_ns[j] - sig_ts
            if el > max_wait_ns:
                break
            pt = px_tick[j]
            if (pt <= arr_t) if d > 0 else (pt >= arr_t):
                fill_j = j
                hit_elapsed_s[e] = float(el) / 1_000_000_000.0
                fill_spread[e] = spread_at_tick[j]
                break

        if fill_j < 0:
            continue

        f_ts = ts_ns[fill_j]
        done = np.zeros(n_b, np.int8)
        rem_b = n_b
        for k in range(fill_j + 1, n):
            el_b = ts_ns[k] - f_ts
            signed_t = d * (px_tick[k] - arr_t)
            for b in range(n_b):
                if done[b] == 1:
                    continue
                if signed_t <= -sl_arr[b]:
                    gross_t[e, b] = float(-sl_arr[b])
                    exit_ts_ns[e, b] = ts_ns[k]
                    done[b] = 1
                    rem_b -= 1
                elif signed_t >= tp_arr[b]:
                    gross_t[e, b] = float(tp_arr[b])
                    exit_ts_ns[e, b] = ts_ns[k]
                    done[b] = 1
                    rem_b -= 1
                elif el_b >= max_ns_arr[b]:
                    gross_t[e, b] = float(signed_t)
                    exit_ts_ns[e, b] = ts_ns[k]
                    done[b] = 1
                    rem_b -= 1
            if rem_b <= 0:
                break

        if rem_b > 0:
            eod_t = float(d * (px_tick[n - 1] - arr_t))
            eod_ts = ts_ns[n - 1]
            for b in range(n_b):
                if done[b] == 0:
                    gross_t[e, b] = eod_t
                    exit_ts_ns[e, b] = eod_ts

    return hit_elapsed_s, fill_spread, gross_t, exit_ts_ns


def _detectar_secuencias_gate(
    ses_all: np.ndarray,
    ts_all: np.ndarray,
    dir_all: np.ndarray,
    gate_mask: np.ndarray,
    gap_max_sec: int,
) -> dict[str, np.ndarray]:
    """Construye mascaras causales de secuencias (2 seguidas igual, 3 seguidas igual, 2da tras 1ra opuesta)."""
    n_tot = len(ts_all)
    seq2_same = np.zeros(n_tot, dtype=bool)
    seq3_same = np.zeros(n_tot, dtype=bool)
    seq2_rev = np.zeros(n_tot, dtype=bool)
    idx_stream = np.flatnonzero(gate_mask)
    if not len(idx_stream):
        return {"SEQ2_SAME": seq2_same, "SEQ3_SAME": seq3_same, "SEQ2_REV": seq2_rev}

    gap_ns = np.int64(gap_max_sec) * np.int64(1_000_000_000)
    streak = 0
    prev_ses = np.int64(-1)
    prev_ts = np.int64(-1)
    prev_dir = 0

    for idx in idx_stream:
        s = np.int64(ses_all[idx])
        t = np.int64(ts_all[idx])
        d = int(dir_all[idx])
        if s == prev_ses and prev_ts >= 0 and (t - prev_ts) <= gap_ns:
            if d == prev_dir:
                streak += 1
                if streak == 2:
                    seq2_same[idx] = True
                elif streak == 3:
                    seq3_same[idx] = True
            else:
                streak = 1
                seq2_rev[idx] = True
        else:
            streak = 1
        prev_ses = s
        prev_ts = t
        prev_dir = d

    return {"SEQ2_SAME": seq2_same, "SEQ3_SAME": seq3_same, "SEQ2_REV": seq2_rev}


def _simular_prop_secuencial(
    gross_ticks: np.ndarray,
    sesiones: np.ndarray,
    ts_start_ns: np.ndarray,
    ts_exit_ns: np.ndarray,
    fricc_ticks: float,
    usd_por_tick: float = 5.0,
) -> dict:
    """Simula 1 posicion activa a la vez (sin solapamiento temporal) sobre trades ordenados."""
    if not len(gross_ticks):
        return {"n_no_overlap": 0, "net_usd": 0.0, "max_eod_dd_usd": 0.0, "worst_day_usd": 0.0, "expR_equiv": 0.0}

    sel_g = []
    sel_s = []
    busy_until = np.int64(-1)
    last_ses = np.int64(-1)
    for g, s, t0, t1 in zip(gross_ticks.tolist(), sesiones.tolist(), ts_start_ns.tolist(), ts_exit_ns.tolist()):
        if s != last_ses:
            busy_until = np.int64(-1)
            last_ses = np.int64(s)
        if t0 <= busy_until:
            continue
        sel_g.append(g - fricc_ticks)
        sel_s.append(s)
        busy_until = np.int64(t1)

    res = _simular_prop_oos(np.asarray(sel_g, float), np.asarray(sel_s, np.int64), usd_por_tick=usd_por_tick)
    res["n_no_overlap"] = len(sel_g)
    return res


def _resumen_p_adaptativo(netos: np.ndarray, ses: np.ndarray, n_boot: int, seed: int) -> dict:
    """Bootstrap por sesion con refinamiento automatico para evitar piso 1/(B+1) en BH/Storey."""
    rs = ESC.resumen_sesiones(netos, ses, n_boot=n_boot, seed=seed)
    if rs["media"] > 0.0 and rs["p_unilateral"] <= 0.02 and n_boot < 40_000:
        rs = ESC.resumen_sesiones(netos, ses, n_boot=40_000, seed=seed)
    return rs


def evaluar_lim_flecha_secuencias(
    sesiones_iter,
    *,
    split_oos_desde: int = 20260401,
    tick_size: float | None = None,
    min_ops_desc: int = 20,
    min_ops_oos: int = 15,
    n_boot: int = 2000,
) -> dict:
    """Campana 3: Orden limite en precio exacto de flecha + timeouts + SL/TP amplios + secuencias 1/2/3/reversa."""
    tick_size = TICK_NQ if tick_size is None else tick_size
    sl_arr = np.array([b[1] for b in LIM_WIDE_BRACKETS], dtype=np.int64)
    tp_arr = np.array([b[2] for b in LIM_WIDE_BRACKETS], dtype=np.int64)
    max_ns_arr = np.array([b[3] * 1_000_000_000 for b in LIM_WIDE_BRACKETS], dtype=np.int64)
    max_wait_ns = max(LIM_TIMEOUTS) * 1_000_000_000
    fricc = fricciones_nq_canonicas()
    keep_bits = 31 | 64  # V1..V5 + V4_WIDE

    buf_ses, buf_ts, buf_dir, buf_hhmm, buf_sp, buf_vm = [], [], [], [], [], []
    buf_hit_s, buf_fsp, buf_gross, buf_exit = [], [], [], []
    sesiones_vistas = []
    total_ticks = 0
    total_perm = 0

    for df in sesiones_iter:
        if df is None or not len(df):
            continue
        ses_id = int(df["sesion"].iloc[0])
        if ses_id >= HOLDOUT_PRIMERA_SESION_INT:
            raise ValueError(f"HOLDOUT-A4 violado: sesion {ses_id} >= {HOLDOUT_PRIMERA_SESION_INT}")

        sesiones_vistas.append(ses_id)
        total_ticks += len(df)
        bid = df["bid"].to_numpy() if "bid" in df.columns else None
        ask = df["ask"].to_numpy() if "ask" in df.columns else None
        det = detectar_eventos_tick(
            df["ts_ns"].to_numpy(),
            df["px"].to_numpy(),
            df["vol"].to_numpy(),
            bid,
            ask,
            tick_size=tick_size,
        )
        n_e = len(det["sig_idx"])
        total_perm += n_e
        if n_e == 0:
            continue

        keep = (det["var_mask"] & keep_bits) > 0
        if not keep.any():
            continue

        hit_s, f_sp, g_t, ex_ns = _simular_lim_flecha_sesion_nb(
            df["ts_ns"].to_numpy(np.int64),
            det["px_tick"],
            det["spread_at_tick"],
            det["sig_idx"][keep],
            det["dir"][keep],
            det["arrow_tick"][keep],
            sl_arr,
            tp_arr,
            max_ns_arr,
            max_wait_ns=max_wait_ns,
        )

        m_cnt = int(keep.sum())
        buf_ses.append(np.full(m_cnt, ses_id, dtype=np.int64))
        buf_ts.append(det["ts_ns"][keep])
        buf_dir.append(det["dir"][keep])
        buf_hhmm.append(det["ny_hhmm"][keep])
        buf_sp.append(det["spread_ticks"][keep])
        buf_vm.append(det["var_mask"][keep])
        buf_hit_s.append(hit_s.astype(np.float32))
        buf_fsp.append(f_sp.astype(np.float32))
        buf_gross.append(g_t.astype(np.float32))
        buf_exit.append(ex_ns)

    if not buf_ses:
        return {"error": "sin_eventos_lim", "sesiones": len(sesiones_vistas), "total_ticks": int(total_ticks)}

    ses_all = np.concatenate(buf_ses)
    ts_all = np.concatenate(buf_ts)
    dir_all = np.concatenate(buf_dir)
    hhmm_all = np.concatenate(buf_hhmm)
    sp_all = np.concatenate(buf_sp)
    vm_all = np.concatenate(buf_vm)
    hit_s_all = np.concatenate(buf_hit_s)
    fsp_all = np.concatenate(buf_fsp)
    gross_all = np.concatenate(buf_gross, axis=0)
    exit_all = np.concatenate(buf_exit, axis=0)

    is_desc = ses_all < split_oos_desde
    is_oos = ses_all >= split_oos_desde
    meses_all = ses_all // 100

    ses_ord = sorted(set(int(s) for s in sesiones_vistas))
    s_to_b8 = {s: min(7, (idx * 8) // max(1, len(ses_ord))) for idx, s in enumerate(ses_ord)}
    s_to_wf4 = {s: min(3, (idx * 4) // max(1, len(ses_ord))) for idx, s in enumerate(ses_ord)}
    blk8_all = np.array([s_to_b8[int(s)] for s in ses_all.tolist()], dtype=np.int64)
    wf4_all = np.array([s_to_wf4[int(s)] for s in ses_all.tolist()], dtype=np.int64)

    ny_rth_sp2 = (hhmm_all >= 930) & (hhmm_all < 1600) & (sp_all >= 0.0) & (sp_all <= 2.0)
    ny_am_sp2 = (hhmm_all >= 930) & (hhmm_all < 1200) & (sp_all >= 0.0) & (sp_all <= 2.0)
    reg_masks = {"NY_RTH_SP2": ny_rth_sp2, "NY_AM_SP2": ny_am_sp2}
    fill_masks = {t_sec: (hit_s_all >= 0.0) & (hit_s_all <= float(t_sec)) for t_sec in LIM_TIMEOUTS}

    seq_stats = []
    celdas = []
    pvals_canon = []
    pvals_pasivo = []
    por_b8_celdas = []
    por_wf4_celdas = []

    for g_name, g_bit in LIM_SEQ_GATES:
        gm = (vm_all & g_bit) > 0
        seq_patterns = [("SEQ1", 0, _aplicar_cooldown_v4(ts_all, gm, cooldown_sec=60))]
        for gap_s in LIM_SEQ_GAPS:
            seqs = _detectar_secuencias_gate(ses_all, ts_all, dir_all, gm, gap_max_sec=gap_s)
            seq_patterns.append(("SEQ2_SAME", gap_s, seqs["SEQ2_SAME"]))
            seq_patterns.append(("SEQ3_SAME", gap_s, seqs["SEQ3_SAME"]))
            seq_patterns.append(("SEQ2_REV", gap_s, seqs["SEQ2_REV"]))

        for seq_name, gap_s, seq_m in seq_patterns:
            for r_name in LIM_SEQ_REGIMES:
                rm = seq_m & reg_masks[r_name]
                n_trig_tot = int(rm.sum())
                if n_trig_tot == 0:
                    continue
                fill_rates = {
                    f"fill_{t}s_pct": round(float((rm & fill_masks[t]).sum()) * 100.0 / n_trig_tot, 1)
                    for t in LIM_TIMEOUTS
                }
                seq_stats.append({
                    "gate": g_name,
                    "seq": seq_name,
                    "gap_s": gap_s,
                    "regimen": r_name,
                    "n_triggers": n_trig_tot,
                    "n_desc_trig": int((rm & is_desc).sum()),
                    "n_oos_trig": int((rm & is_oos).sum()),
                    **fill_rates,
                })

                for t_sec in LIM_TIMEOUTS:
                    fm = rm & fill_masks[t_sec]
                    if int((fm & is_desc).sum()) < min_ops_desc or int((fm & is_oos).sum()) < min_ops_oos:
                        continue

                    for b_idx, (b_name, sl_t, _, _) in enumerate(LIM_WIDE_BRACKETS):
                        g = gross_all[:, b_idx].astype(np.float64)
                        valid = fm & np.isfinite(g)
                        idx_d = valid & is_desc
                        idx_o = valid & is_oos
                        nd = int(idx_d.sum())
                        no = int(idx_o.sum())
                        if nd < min_ops_desc or no < min_ops_oos:
                            continue

                        g_d, g_o = g[idx_d], g[idx_o]
                        ses_d, ses_o = ses_all[idx_d], ses_all[idx_o]

                        net_d_canon = (g_d - fricc["base_canon"]) / sl_t
                        net_d_pasivo = (g_d - fricc["no_spread_base"]) / sl_t
                        net_d_2t = (g_d - fricc["nt8_2t"]) / sl_t

                        net_o_canon = (g_o - fricc["base_canon"]) / sl_t
                        net_o_pasivo = (g_o - fricc["no_spread_base"]) / sl_t
                        net_o_adv = (g_o - fricc["adverso_canon"]) / sl_t
                        net_o_2t = (g_o - fricc["nt8_2t"]) / sl_t

                        rs_d_c = _resumen_p_adaptativo(net_d_canon, ses_d, n_boot, 20261113)
                        rs_d_p = _resumen_p_adaptativo(net_d_pasivo, ses_d, n_boot, 20261115)
                        rs_o_c = _resumen_p_adaptativo(net_o_canon, ses_o, n_boot, 20261114)
                        rs_o_p = _resumen_p_adaptativo(net_o_pasivo, ses_o, n_boot, 20261116)

                        econ_c = ESC.economia(
                            (g[valid] - fricc["base_canon"]) / sl_t,
                            netos_adverso=(g[valid] - fricc["adverso_canon"]) / sl_t,
                            periodos=(meses_all[valid]).tolist(),
                        )
                        prop_1nq_c = _simular_prop_secuencial(
                            g_o, ses_o, ts_all[idx_o], exit_all[idx_o, b_idx], fricc["base_canon"], usd_por_tick=5.0
                        )
                        prop_1nq_p = _simular_prop_secuencial(
                            g_o, ses_o, ts_all[idx_o], exit_all[idx_o, b_idx], fricc["no_spread_base"], usd_por_tick=5.0
                        )

                        pvals_canon.append(float(rs_d_c["p_unilateral"]))
                        pvals_pasivo.append(float(rs_d_p["p_unilateral"]))

                        celdas.append({
                            "gate": g_name,
                            "seq": seq_name,
                            "gap_s": int(gap_s),
                            "regimen": r_name,
                            "timeout_s": int(t_sec),
                            "bracket": b_name,
                            "sl_t": int(sl_t),
                            "fill_pct": round(float(valid.sum()) * 100.0 / n_trig_tot, 1),
                            "n_desc": nd,
                            "ses_desc": int(rs_d_c["n_sesiones"]),
                            "expR_desc_canon": round(float(net_d_canon.mean()), 4),
                            "expR_desc_pasivo": round(float(net_d_pasivo.mean()), 4),
                            "expR_desc_2t": round(float(net_d_2t.mean()), 4),
                            "expT_desc_pasivo": round(float((g_d - fricc["no_spread_base"]).mean()), 2),
                            "wr_desc_pasivo_pct": round(float((net_d_pasivo > 0.0).mean() * 100.0), 1),
                            "pf_desc_canon": round(_calc_profit_factor(net_d_canon), 3),
                            "pf_desc_pasivo": round(_calc_profit_factor(net_d_pasivo), 3),
                            "p_desc_canon": round(float(rs_d_c["p_unilateral"]), 6),
                            "p_desc_pasivo": round(float(rs_d_p["p_unilateral"]), 6),
                            "n_oos": no,
                            "ses_oos": int(rs_o_c["n_sesiones"]),
                            "expR_oos_canon": round(float(net_o_canon.mean()), 4),
                            "expR_oos_pasivo": round(float(net_o_pasivo.mean()), 4),
                            "expR_oos_adv": round(float(net_o_adv.mean()), 4),
                            "expR_oos_2t": round(float(net_o_2t.mean()), 4),
                            "expT_oos_pasivo": round(float((g_o - fricc["no_spread_base"]).mean()), 2),
                            "wr_oos_pasivo_pct": round(float((net_o_pasivo > 0.0).mean() * 100.0), 1),
                            "pf_oos_canon": round(_calc_profit_factor(net_o_canon), 3),
                            "pf_oos_pasivo": round(_calc_profit_factor(net_o_pasivo), 3),
                            "p_oos_canon": round(float(rs_o_c["p_unilateral"]), 6),
                            "p_oos_pasivo": round(float(rs_o_p["p_unilateral"]), 6),
                            "econ_pasa": bool(econ_c["pasa"]),
                            "periodos_pos": econ_c.get("periodos_positivos", ""),
                            "prop_1nq_oos_canon": prop_1nq_c,
                            "prop_1nq_oos_pasivo": prop_1nq_p,
                        })

                        net_all_c = (g[valid] - fricc["base_canon"]) / sl_t
                        b8_map = {}
                        for b_id, val in zip(blk8_all[valid].tolist(), net_all_c.tolist()):
                            sp_v, cp_v = b8_map.get(int(b_id), (0.0, 0))
                            b8_map[int(b_id)] = (sp_v + float(val), cp_v + 1)
                        por_b8_celdas.append(b8_map)

                        wf4_map = {}
                        for w_id, val in zip(wf4_all[valid].tolist(), net_all_c.tolist()):
                            sp_v, cp_v = wf4_map.get(int(w_id), (0.0, 0))
                            wf4_map[int(w_id)] = (sp_v + float(val), cp_v + 1)
                        por_wf4_celdas.append(wf4_map)

    tamiz_c = ESC.tamiz_fdr(pvals_canon, q=0.10, metodo="storey") if celdas else {"nominadas": [], "q_valores": [], "pi0": 1.0, "m": 0}
    tamiz_p = ESC.tamiz_fdr(pvals_pasivo, q=0.10, metodo="storey") if celdas else {"nominadas": [], "q_valores": [], "pi0": 1.0, "m": 0}
    nom_c = set(tamiz_c["nominadas"])
    nom_p = set(tamiz_p["nominadas"])
    for idx, c in enumerate(celdas):
        c["q_desc_canon"] = round(float(tamiz_c["q_valores"][idx]), 5)
        c["q_desc_pasivo"] = round(float(tamiz_p["q_valores"][idx]), 5)
        c["nominada_fdr_canon"] = idx in nom_c
        c["nominada_fdr_pasivo"] = idx in nom_p

    pbo_info = {"calculable": False}
    b8_valid = [i for i, mp in enumerate(por_b8_celdas) if all(mp.get(b, (0.0, 0))[1] > 0 for b in range(8))]
    if len(b8_valid) >= 2:
        mat8 = [[G2.RatioCell(*por_b8_celdas[i][b]) for i in b8_valid] for b in range(8)]
        res_pbo = G2.pbo_ratio_cscv(mat8, s=8)
        pbo_info = {
            "calculable": True,
            "n_configs": res_pbo.n_configs,
            "pbo": round(float(res_pbo.pbo), 4),
            "passed_pbo_le_050": bool(res_pbo.passed),
        }

    wf_info = {"calculable": False}
    wf4_valid = [i for i, mp in enumerate(por_wf4_celdas) if all(mp.get(f, (0.0, 0))[1] > 0 for f in range(4))]
    if len(wf4_valid) >= 2:
        per_fold = {
            f"{celdas[i]['gate']}|{celdas[i]['seq']}|g{celdas[i]['gap_s']}|{celdas[i]['regimen']}|t{celdas[i]['timeout_s']}|{celdas[i]['bracket']}": {
                f: G2.RatioCell(*por_wf4_celdas[i][f]) for f in range(4)
            }
            for i in wf4_valid
        }
        res_wf = G2.walk_forward_ratio(per_fold, [0, 1, 2, 3])
        wf_info = {
            "calculable": True,
            "n_configs": len(wf4_valid),
            "oos_ratio_R": round(float(res_wf.observed), 4),
            "oos_total_R": round(float(res_wf.total_pnl), 2),
            "oos_trades": int(res_wf.total_n_trades),
            "passed_wf_gt_0": bool(res_wf.passed),
            "selecciones": [
                {"fold": int(s.fold), "config": str(s.selected_config), "oos_R": round(float(s.oos_ratio), 4), "oos_n": int(s.oos_n_trades)}
                for s in res_wf.selections
            ],
        }

    rep_canon = [r for r in celdas if r["expR_desc_canon"] > 0.0 and r["expR_oos_canon"] > 0.0]
    rep_canon.sort(key=lambda r: min(r["expR_desc_canon"], r["expR_oos_canon"]) * math.sqrt(min(r["n_desc"], r["n_oos"])), reverse=True)
    rep_pasivo = [r for r in celdas if r["expR_desc_pasivo"] > 0.0 and r["expR_oos_pasivo"] > 0.0]
    rep_pasivo.sort(key=lambda r: min(r["expR_desc_pasivo"], r["expR_oos_pasivo"]) * math.sqrt(min(r["n_desc"], r["n_oos"])), reverse=True)

    return {
        "nombre": "DELTASWEEP-NQ-LIM-FLECHA-SECUENCIAS",
        "sesiones_procesadas": len(sesiones_vistas),
        "rango_sesiones": [min(sesiones_vistas), max(sesiones_vistas)] if sesiones_vistas else [],
        "split_oos_desde": int(split_oos_desde),
        "total_ticks": int(total_ticks),
        "total_eventos_permisivos": int(total_perm),
        "conteo_compuertas": {g: int(((vm_all & b) > 0).sum()) for g, b in LIM_SEQ_GATES},
        "fricciones_ticks": fricc,
        "seq_fill_stats": seq_stats,
        "n_celdas_evaluadas": len(celdas),
        "tamiz_fdr_desc_canon": {
            "m_pruebas": tamiz_c["m"],
            "pi0_storey": round(float(tamiz_c["pi0"]), 4),
            "n_nominadas_q10": len(tamiz_c["nominadas"]),
        },
        "tamiz_fdr_desc_pasivo": {
            "m_pruebas": tamiz_p["m"],
            "pi0_storey": round(float(tamiz_p["pi0"]), 4),
            "n_nominadas_q10": len(tamiz_p["nominadas"]),
        },
        "pbo_cscv_8bloques": pbo_info,
        "walk_forward_4folds": wf_info,
        "n_replican_canon": len(rep_canon),
        "n_replican_pasivo": len(rep_pasivo),
        "celdas_ordenadas_replica_canon": rep_canon[:50],
        "celdas_ordenadas_replica_pasivo": rep_pasivo[:50],
        "todas_celdas_top_desc_canon": sorted(celdas, key=lambda r: r["expR_desc_canon"], reverse=True)[:25],
    }


