"""Traduccion Python de SessionOpenMomentum.ex5 (v2.2, framework QuantLab).

Reglas verificadas al 100% en MetaTrader 5 build 5956 (`som_agent_run1.log`):
1. Opera internamente en barras M5 independientemente del timeframe de entrada.
2. Evalúa 1 vez por dia al cierre de la primera barra M5 de `open_ny` (`16:30` -> ejecuta `16:35:00`).
3. Maximo 1 posicion abierta simultanea (`only one Momentum trade at a time`).
4. Senal direccional: `Close_M5(16:30) > EMA(fast_ema=12)` -> Long; `< EMA` -> Short.
5. Stop Loss inicial (`1 R`) = `8.0 * iATR(PERIOD_M5, 14)[1]`, sin Take Profit fijo.
6. Trailing Stop: tras alcanzar ganancia >= `trail_start_r * R` (`+0.50 R`), mueve SL a
   `EMA_M5(trail_ema=120)[1]` a favor del trade (throttle >= 300s = 1 barra M5).
7. Adaptive Risk: escala el riesgo entre `[vol_risk_floor, vol_risk_cap]` proporcional
   a la volatilidad relativa reciente en M5 (aproximado por ATR(20)/EMA(ATR(20), 180)).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

try:
    from .contracts import (
        InstrumentSpec,
        SessionOpenMomentumConfig,
        TRADE_COLUMNS,
        TradeRecord,
        resolve_instrument,
        trades_to_df,
    )
    from .indicators import compute_lot_size, mql5_atr, mql5_ema, resample_ohlc
except ImportError:  # pragma: no cover - soporte de import directo
    from contracts import (
        InstrumentSpec,
        SessionOpenMomentumConfig,
        TRADE_COLUMNS,
        TradeRecord,
        resolve_instrument,
        trades_to_df,
    )
    from indicators import compute_lot_size, mql5_atr, mql5_ema, resample_ohlc

MODULO_SOM = "SOM"


def _parse_hhmm_min(hhmm: str) -> int:
    hh, mm = hhmm.strip().split(":")
    return int(hh) * 60 + int(mm)


def compute_adaptive_volatility_factors(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    cfg: SessionOpenMomentumConfig,
) -> np.ndarray:
    """Factor de volatilidad adaptativo [vol_risk_floor .. vol_risk_cap].

    Nota: la formula base (`ATR corto / EMA larga de ATR en M5`) es inferida
    a partir de los factores observados (`0.522x..1.998x`, `MAE ~ 0.10` en junio 2026).
    """
    n = len(close)
    if not cfg.use_adaptive_risk:
        return np.ones(n, dtype=np.float64)
    atr_short = mql5_atr(high, low, close, cfg.adaptive_short_window)
    valid_mask = np.isfinite(atr_short) & (atr_short > 0)
    base = np.full(n, np.nan, dtype=np.float64)
    if np.any(valid_mask):
        first_idx = int(np.argmax(valid_mask))
        ema_tail = mql5_ema(atr_short[first_idx:], cfg.adaptive_base_window)
        base[first_idx:] = ema_tail

    factors = np.ones(n, dtype=np.float64)
    good = np.isfinite(atr_short) & np.isfinite(base) & (base > 0)
    factors[good] = np.clip(atr_short[good] / base[good], cfg.vol_risk_floor, cfg.vol_risk_cap)
    return factors


def _finalize_som_trade(
    pos: Dict[str, Any],
    exit_ts_ns: int,
    exit_px: float,
    exit_name: str,
    bars_held: int,
    spec: InstrumentSpec,
) -> tuple[TradeRecord, float]:
    side = int(pos["side"])
    lots = float(pos["qty"])
    entry_px = float(pos["entry_price"])
    pnl_pts = (exit_px - entry_px) * side
    pnl_usd = pnl_pts * lots * spec.usd_per_price_unit_per_lot
    rec = TradeRecord(
        module=MODULO_SOM,
        side=side,
        qty=lots,
        entry_time_utc=int(pos["entry_ts_ns"]),
        exit_time_utc=int(exit_ts_ns),
        entry_price=spec.round_price(entry_px),
        exit_price=spec.round_price(exit_px),
        stop_price=spec.round_price(pos["init_sl"]),
        target_price=float("nan"),
        entry_name=str(pos["entry_name"]),
        exit_name=exit_name,
        pnl_pts=round(float(pnl_pts), spec.digits + 1),
        pnl_usd=round(float(pnl_usd), 2),
        mae_usd=round(float(pos["mae_pts"] * lots * spec.usd_per_price_unit_per_lot), 2),
        mfe_usd=round(float(pos["mfe_pts"] * lots * spec.usd_per_price_unit_per_lot), 2),
        bars=int(bars_held),
    )
    return rec, pnl_usd


def correr_session_open_momentum(
    df_ohlc: pd.DataFrame,
    config: Optional[SessionOpenMomentumConfig] = None,
    instrument: str | InstrumentSpec = "EURUSD",
    adaptive_overrides: Optional[Dict[int, float]] = None,
    return_diagnostics: bool = False,
    permitir=None,
) -> pd.DataFrame | tuple[pd.DataFrame, Dict[str, Any]]:
    """Simula SessionOpenMomentum.ex5 sobre barras OHLC (resampleadas causalmente a M5)."""
    cfg = config or SessionOpenMomentumConfig()
    spec = resolve_instrument(instrument)

    m5 = resample_ohlc(df_ohlc, 5)
    if m5.empty:
        empty = trades_to_df([])
        return (empty, {"skipped_still_open": 0, "final_balance": cfg.initial_balance}) if return_diagnostics else empty

    ts_ns = m5["ts_ns"].to_numpy(dtype=np.int64)
    times = pd.to_datetime(ts_ns, unit="ns", utc=True)
    minutes_of_day = (times.hour.to_numpy(dtype=np.int32) * 60 + times.minute.to_numpy(dtype=np.int32))
    weekdays = times.dayofweek.to_numpy(dtype=np.int32)
    day_keys = (times.year.to_numpy(dtype=np.int32) * 1000 + times.dayofyear.to_numpy(dtype=np.int32))

    opens = m5["open"].to_numpy(dtype=np.float64)
    highs = m5["high"].to_numpy(dtype=np.float64)
    lows = m5["low"].to_numpy(dtype=np.float64)
    closes = m5["close"].to_numpy(dtype=np.float64)

    ema_fast = mql5_ema(closes, cfg.fast_ema)
    ema_trail = mql5_ema(closes, cfg.trail_ema)
    atr14 = mql5_atr(highs, lows, closes, cfg.atr_period)
    adapt_factors = compute_adaptive_volatility_factors(highs, lows, closes, cfg)

    open_ny_min = _parse_hhmm_min(cfg.open_ny)
    entry_min = (open_ny_min + 5) % 1440
    eod_min = _parse_hhmm_min(cfg.eod_time)

    balance = float(cfg.initial_balance)
    peak_equity = balance
    halted = False
    pos: Optional[Dict[str, Any]] = None
    blocked_day: int = -1
    skipped_still_open = 0
    trail_mod_count = 0
    trades: list[TradeRecord] = []

    warmup = max(cfg.trail_ema, cfg.atr_period) + 2
    n = len(m5)

    for i in range(1, n):
        cur_ts = int(ts_ns[i])
        cur_min = int(minutes_of_day[i])
        cur_day = int(day_keys[i])
        o, h, l, c = float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i])

        # 0. Rotación (mejora EdgeLab 2026-11-16): a la hora de entrada se cierra la posición a la apertura y se evalúa la señal del día
        if pos is not None and cfg.rotar and cur_min == entry_min and not halted and i >= warmup:
            rec, pnl = _finalize_som_trade(pos, cur_ts, o, "ROTACION", i - pos["entry_idx"] + 1, spec)
            trades.append(rec); balance += pnl; pos = None

        # Regla del EA (revisión Antigravity 2026-11-17, 7 casos en USATECH 2024–26): si a la apertura de la vela de las 16:30 hay una
        # posición abierta, el día queda bloqueado aunque esa posición cierre por stop dentro de esa misma vela.
        if pos is not None and cur_min == open_ny_min and blocked_day != cur_day and not cfg.rotar:
            blocked_day = cur_day
            skipped_still_open += 1

        # 1. Protecciones de equidad / cierre de posicion activa
        if pos is not None:
            side = int(pos["side"])
            sl = float(pos["cur_sl"])
            epx = float(pos["entry_price"])
            lots = float(pos["qty"])

            # MAE / MFE acumulado antes de salida
            fav_bar = (h - epx) if side > 0 else (epx - l)
            adv_bar = (epx - l) if side > 0 else (h - epx)
            pos["mfe_pts"] = max(pos["mfe_pts"], max(0.0, fav_bar))
            pos["mae_pts"] = max(pos["mae_pts"], max(0.0, adv_bar))

            # Chequeo de Equity target / stop-out / MaxEquityDDPct
            mtm_eq = balance + ((o - epx) * side) * lots * spec.usd_per_price_unit_per_lot
            peak_equity = max(peak_equity, mtm_eq)
            eq_stop = (
                (cfg.close_at_equity > 0 and mtm_eq >= cfg.close_at_equity)
                or (cfg.stop_at_equity > 0 and mtm_eq <= cfg.stop_at_equity)
                or (cfg.max_equity_dd_pct > 0 and (peak_equity - mtm_eq) / peak_equity * 100.0 >= cfg.max_equity_dd_pct)
            )
            if eq_stop:
                rec, pnl = _finalize_som_trade(pos, cur_ts, o, "EQUITY_GUARD", i - pos["entry_idx"] + 1, spec)
                trades.append(rec)
                balance += pnl
                pos = None
                halted = True
                continue

            # Cierre EOD opcional
            if (cfg.close_eod or (cfg.close_weekend and weekdays[i] == 4)) and cur_min >= eod_min:
                rec, pnl = _finalize_som_trade(pos, cur_ts, o, "EOD_CLOSE", i - pos["entry_idx"] + 1, spec)
                trades.append(rec)
                balance += pnl
                pos = None
                continue

            # Impacto contra Stop Loss (inicial o trailing) dentro de barra i
            sl_hit = (l <= sl) if side > 0 else (h >= sl)
            if sl_hit:
                exit_label = "TRAIL_SL" if pos["trailed"] else "INIT_SL"
                px = min(o, sl) if side > 0 else max(o, sl)           # 2026-11-16: si abre con gap más allá del stop, llena a la apertura
                rec, pnl = _finalize_som_trade(pos, cur_ts, px, exit_label, i - pos["entry_idx"] + 1, spec)
                trades.append(rec)
                balance += pnl
                pos = None
                continue

            # Regla verificada at NY open (16:30): si hay posicion abierta, bloquea entrada hoy

            # Activacion de Trailing Stop (+trail_start_r * init_R) y actualizacion con EMA120(shift=1)
            init_r = float(pos["init_r"])
            if fav_bar >= cfg.trail_start_r * init_r:
                pos["trail_active"] = True
            if pos["trail_active"] and np.isfinite(ema_trail[i]):
                cand_sl = spec.round_price(float(ema_trail[i]))
                if side > 0 and cand_sl > sl + spec.point and cand_sl < c:
                    pos["cur_sl"] = cand_sl
                    pos["trailed"] = True
                    trail_mod_count += 1
                elif side < 0 and cand_sl < sl - spec.point and cand_sl > c:
                    pos["cur_sl"] = cand_sl
                    pos["trailed"] = True
                    trail_mod_count += 1
            continue

        # 2. Evaluacion de nueva entrada (flat) en apertura de barra entry_min (16:35:00)
        if halted or i < warmup:
            continue
        if cur_min != entry_min or blocked_day == cur_day:
            continue

        sig_bar = i - 1  # Barra M5 de las 16:30 recien cerrada
        e12 = float(ema_fast[sig_bar])
        a14 = float(atr14[sig_bar])
        c_sig = float(closes[sig_bar])
        if not (np.isfinite(e12) and np.isfinite(a14) and a14 > 0):
            continue

        if c_sig > e12:
            side = 1
        elif c_sig < e12:
            side = -1
        else:
            continue
        if permitir is not None and not permitir(cur_ts, side):      # filtro de contexto externo (mejora EdgeLab); causal: lo decide el llamador
            blocked_day = cur_day
            continue

        sl_dist = spec.round_price(cfg.sl_atr_mult * a14)
        if sl_dist <= 0:
            continue

        adapt_f = (
            float(adaptive_overrides[cur_ts])
            if adaptive_overrides is not None and cur_ts in adaptive_overrides
            else float(adapt_factors[sig_bar])
        )
        lots = compute_lot_size(
            balance=balance,
            sl_dist=sl_dist,
            risk_mode=cfg.risk_mode,
            risk_percent=cfg.risk_percent,
            risk_money=cfg.risk_money,
            fixed_lot=cfg.fixed_lot,
            usd_per_price_unit=spec.usd_per_price_unit_per_lot,
            min_lot=spec.min_lot,
            lot_step=spec.lot_step,
            max_lot=spec.max_lot,
            allow_min_fallback=True,
            risk_multiplier=adapt_f,
        )
        if lots <= 0:
            continue

        entry_px = o + (0.5 * cfg.spread_price * side)
        init_sl = spec.round_price(entry_px - side * sl_dist)
        blocked_day = cur_day
        pos = {
            "side": side,
            "qty": lots,
            "entry_ts_ns": cur_ts,
            "entry_idx": i,
            "entry_price": entry_px,
            "init_sl": init_sl,
            "cur_sl": init_sl,
            "init_r": sl_dist,
            "trail_active": False,
            "trailed": False,
            "mfe_pts": 0.0,
            "mae_pts": 0.0,
            "entry_name": f"SOM_{'BUY' if side > 0 else 'SELL'}_x{adapt_f:.2f}",
        }
        if (l <= init_sl) if side > 0 else (h >= init_sl):           # 2026-11-16: el stop también vale en la vela de entrada
            pos["mae_pts"] = abs(entry_px - init_sl); pos["mfe_pts"] = max(0.0, (h - entry_px) if side > 0 else (entry_px - l))   # 2026-11-17
            rec, pnl = _finalize_som_trade(pos, cur_ts, init_sl, "INIT_SL", 1, spec)
            trades.append(rec); balance += pnl; pos = None

    # Cierre al final del periodo si quedo abierta
    if pos is not None:
        rec, pnl = _finalize_som_trade(pos, int(ts_ns[-1]), float(closes[-1]), "END_OF_DATA", n - pos["entry_idx"], spec)
        trades.append(rec)
        balance += pnl

    out_df = trades_to_df(trades)
    if not return_diagnostics:
        return out_df
    diag = {
        "trades": len(out_df),
        "skipped_still_open": skipped_still_open,
        "trail_mod_count": trail_mod_count,
        "final_balance": round(balance, 2),
        "bars_m5": n,
    }
    return out_df, diag
