"""Traduccion Python de QLB_K_XAUUSD_3x_speed_q4_turn.ex5 (v1.8, framework QLBATCH).

Componentes verificados al 100% en MetaTrader 5 (`qlb_agent_run1.log`, 57 entradas):
1. Canasta hedging de 3 slots independientes (MagicBase, +1, +2):
   - Slot 0 (`speed_switch_momentum`): `PERIOD_H4`, Long y Short, `MaxHold = 120` barras H4 (`672h` cal.).
   - Slot 1 (`q4_momentum_breakout`): `PERIOD_H1`, filtro estacional Q4 (Oct-Dic, 0 entradas ene-jun).
   - Slot 2 (`turn_of_month_january_momentum_2`): `PERIOD_H1`, solo Long, `MaxHold = 40` barras H1.
2. Stop Loss y Take Profit unificados (verificados 57/57 con error 0.00):
   - `SL = 2.5 * iATR(slot_tf, 14)[1]` (SMA de True Range en MQL5)
   - `TP = 5.0 * iATR(slot_tf, 14)[1] = 2.00 * SL` (`RR = 2.00`), sin trailing (`trails = 0`).
3. Risk & Prop Firm Safety:
   - Sizing por slot al `0.75%` del balance (riesgo abierto maximo `2.25%` si los 3 coinciden).
   - Freno diario `InpMaxDailyLossPct = 4.0%`, `InpMaxSendsPerDay = 8` por slot y filtro `InpNoHedge`.

Nota sobre señales internas (`[INFERIDO]`):
Las condiciones booleanas exactas de entrada dentro del bytecode protegido de cada slot se
aproximan con detectores causales fieles al comportamiento observado y permiten ademas
inyectar `override_signals` para validar exactamente el libro de MT5 Strategy Tester.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd

try:
    from .contracts import (
        InstrumentSpec,
        QlbBasketConfig,
        TRADE_COLUMNS,
        TradeRecord,
        resolve_instrument,
        trades_to_df,
    )
    from .indicators import compute_lot_size, mql5_atr, mql5_ema, resample_ohlc
except ImportError:  # pragma: no cover
    from contracts import (
        InstrumentSpec,
        QlbBasketConfig,
        TRADE_COLUMNS,
        TradeRecord,
        resolve_instrument,
        trades_to_df,
    )
    from indicators import compute_lot_size, mql5_atr, mql5_ema, resample_ohlc

SLOT_NAMES: Dict[int, str] = {
    0: "QLB_S0_SPEED_H4",
    1: "QLB_S1_Q4_H1",
    2: "QLB_S2_TOM_JAN_H1",
}

SLOT_TIMEFRAMES_MIN: Dict[int, int] = {
    0: 240,  # PERIOD_H4
    1: 60,   # PERIOD_H1
    2: 60,   # PERIOD_H1
}


def _trading_day_of_month(times: pd.DatetimeIndex) -> np.ndarray:
    """Calcula el numero ordinal de dia habil dentro de cada mes (1, 2, 3...)."""
    dates = times.date
    td = np.zeros(len(times), dtype=np.int32)
    cur_ym = None
    last_date = None
    cnt = 0
    for idx, d in enumerate(dates):
        ym = (d.year, d.month)
        if ym != cur_ym:
            cur_ym = ym
            last_date = d
            cnt = 1
        elif d != last_date:
            last_date = d
            cnt += 1
        td[idx] = cnt
    return td


def _slot_signal_inferred(
    slot_id: int,
    i: int,
    bars: Dict[str, np.ndarray],
    ema10: np.ndarray,
    ema50: np.ndarray,
    atr5: np.ndarray,
    atr20: np.ndarray,
) -> int:
    """Genera senal inferida (+1, -1, 0) sobre la barra cerrada `sig = i - 1`."""
    sig = i - 1
    c = bars["close"]
    h = bars["high"]
    month = int(bars["month"][i])
    day = int(bars["day"][i])
    td = int(bars["td"][i])

    if slot_id == 0:
        # [INFERIDO] speed_switch_momentum (H4 Long/Short): EMA(10) vs EMA(50) + aceleracion ATR(5)/ATR(20)
        if sig < 55:
            return 0
        e_diff = ema10[sig] - ema50[sig]
        prev_diff = ema10[sig - 1] - ema50[sig - 1]
        speed = atr5[sig] / max(atr20[sig], 1e-12) if np.isfinite(atr20[sig]) else 1.0
        if e_diff > 0 and prev_diff > 0 and speed >= 0.85:
            return 1
        if e_diff < 0 and prev_diff < 0 and speed >= 0.85:
            return -1
        return 0

    if slot_id == 1:
        # [VERIFICADO] Filtro Q4 (octubre-diciembre) + [INFERIDO] breakout momentum 20 barras H1
        if month not in (10, 11, 12) or sig < 50:
            return 0
        hi20 = float(np.max(h[sig - 20 : sig]))
        lo20 = float(np.min(bars["low"][sig - 20 : sig]))
        if c[sig] > hi20 and ema10[sig] > ema50[sig]:
            return 1
        if c[sig] < lo20 and ema10[sig] < ema50[sig]:
            return -1
        return 0

    if slot_id == 2:
        # [VERIFICADO] Solo Long; ventana Turn-of-Month ampliada en enero (td <= 8 / dia <= 14; resto td <= 5)
        if sig < 24:
            return 0
        season_ok = (month == 1 and day <= 14) or (month != 1 and td <= 5 and day <= 8)
        if not season_ok:
            return 0
        # [INFERIDO] Filtro alcista de corto plazo en H1 (cierre arriba de apertura previa o ruptura EMA10)
        if c[sig] > c[sig - 1] or c[sig] > ema10[sig]:
            return 1
        return 0

    raise ValueError(f"slot_id invalido: {slot_id}")


def _prep_tf_arrays(df_tf: pd.DataFrame) -> Dict[str, np.ndarray]:
    ts = df_tf["ts_ns"].to_numpy(dtype=np.int64)
    times = pd.to_datetime(ts, unit="ns", utc=True)
    return {
        "ts_ns": ts,
        "year": times.year.to_numpy(dtype=np.int32),
        "month": times.month.to_numpy(dtype=np.int32),
        "day": times.day.to_numpy(dtype=np.int32),
        "doy": times.dayofyear.to_numpy(dtype=np.int32),
        "td": _trading_day_of_month(times),
        "open": df_tf["open"].to_numpy(dtype=np.float64),
        "high": df_tf["high"].to_numpy(dtype=np.float64),
        "low": df_tf["low"].to_numpy(dtype=np.float64),
        "close": df_tf["close"].to_numpy(dtype=np.float64),
    }


def _close_slot_trade(
    slot_id: int,
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
        module=SLOT_NAMES[slot_id],
        side=side,
        qty=lots,
        entry_time_utc=int(pos["entry_ts_ns"]),
        exit_time_utc=int(exit_ts_ns),
        entry_price=spec.round_price(entry_px),
        exit_price=spec.round_price(exit_px),
        stop_price=spec.round_price(pos["sl"]),
        target_price=spec.round_price(pos["tp"]),
        entry_name=f"{SLOT_NAMES[slot_id]}_{'BUY' if side > 0 else 'SELL'}",
        exit_name=exit_name,
        pnl_pts=round(float(pnl_pts), spec.digits + 1),
        pnl_usd=round(float(pnl_usd), 2),
        mae_usd=round(float(pos["mae_pts"] * lots * spec.usd_per_price_unit_per_lot), 2),
        mfe_usd=round(float(pos["mfe_pts"] * lots * spec.usd_per_price_unit_per_lot), 2),
        bars=int(bars_held),
    )
    return rec, pnl_usd


def correr_qlb_basket(
    df_ohlc: pd.DataFrame,
    config: Optional[QlbBasketConfig] = None,
    instrument: str | InstrumentSpec = "XAUUSD",
    slots: Iterable[int] = (0, 1, 2),
    override_signals: Optional[Mapping[int, Mapping[int, int]]] = None,
    return_diagnostics: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, Dict[str, Any]]:
    """Ejecuta la canasta multi-slot QLB (`H4` + `H1` + `H1`) respetando hedging/daily-loss/max-hold."""
    cfg = config or QlbBasketConfig()
    spec = resolve_instrument(instrument)
    active_slots = sorted({int(s) for s in slots if (s == 0 and cfg.enable_slot0) or (s == 1 and cfg.enable_slot1) or (s == 2 and cfg.enable_slot2)})

    df_h1 = resample_ohlc(df_ohlc, 60)
    df_h4 = resample_ohlc(df_ohlc, 240)
    if df_h1.empty or df_h4.empty or not active_slots:
        empty = trades_to_df([])
        return (empty, {"final_balance": cfg.initial_balance, "daily_loss_days": 0}) if return_diagnostics else empty

    tf_data = {60: _prep_tf_arrays(df_h1), 240: _prep_tf_arrays(df_h4)}
    tf_ind = {}
    for tf_min, arrs in tf_data.items():
        tf_ind[tf_min] = {
            "atr14": mql5_atr(arrs["high"], arrs["low"], arrs["close"], cfg.atr_period),
            "atr5": mql5_atr(arrs["high"], arrs["low"], arrs["close"], 5),
            "atr20": mql5_atr(arrs["high"], arrs["low"], arrs["close"], 20),
            "ema10": mql5_ema(arrs["close"], 10),
            "ema50": mql5_ema(arrs["close"], 50),
        }

    # Cronologia de eventos H1 ordenada (cierre H1 y aperturas H4 coinciden en H1)
    h1_ts = tf_data[60]["ts_ns"]
    h4_ts_to_idx = {int(t): idx for idx, t in enumerate(tf_data[240]["ts_ns"])}
    h1_ts_to_idx = {int(t): idx for idx, t in enumerate(h1_ts)}

    max_hold_map = {0: cfg.slot0_max_hold_bars, 1: cfg.slot1_max_hold_bars, 2: cfg.slot2_max_hold_bars}
    open_pos: Dict[int, Optional[Dict[str, Any]]] = {s: None for s in active_slots}
    sends_today: Dict[int, int] = {s: 0 for s in active_slots}

    balance = float(cfg.initial_balance)
    cur_day_key = -1
    day_ref_equity = balance
    daily_stopped = False
    daily_stop_days = 0
    hedge_blocked = 0
    halted = False
    trades: list[TradeRecord] = []

    for h1_i, ts in enumerate(h1_ts):
        ts_int = int(ts)
        dkey = int(tf_data[60]["year"][h1_i]) * 1000 + int(tf_data[60]["doy"][h1_i])
        if dkey != cur_day_key:
            cur_day_key = dkey
            # Mark-to-market de equidad al inicio del dia
            eq_open = balance
            px_open = float(tf_data[60]["open"][h1_i])
            for p in open_pos.values():
                if p is not None:
                    eq_open += (px_open - p["entry_price"]) * p["side"] * p["qty"] * spec.usd_per_price_unit_per_lot
            day_ref_equity = eq_open
            daily_stopped = False
            for s in active_slots:
                sends_today[s] = 0

        # Actualizar MTM y frenos de equidad / perdida diaria
        px_h1 = float(tf_data[60]["open"][h1_i])
        eq_now = balance
        for p in open_pos.values():
            if p is not None:
                eq_now += (px_h1 - p["entry_price"]) * p["side"] * p["qty"] * spec.usd_per_price_unit_per_lot

        if (cfg.close_at_equity > 0 and eq_now >= cfg.close_at_equity) or (cfg.stop_at_equity > 0 and eq_now <= cfg.stop_at_equity):
            for s in active_slots:
                p = open_pos[s]
                if p is not None:
                    tf_m = SLOT_TIMEFRAMES_MIN[s]
                    cur_slot_i = h4_ts_to_idx.get(ts_int, p["entry_idx"]) if tf_m == 240 else h1_i
                    rec, pnl = _close_slot_trade(s, p, ts_int, px_h1, "EQUITY_GUARD", max(1, cur_slot_i - p["entry_idx"] + 1), spec)
                    trades.append(rec)
                    balance += pnl
                    open_pos[s] = None
            halted = True
            break

        if cfg.max_daily_loss_pct > 0 and not daily_stopped and eq_now < day_ref_equity * (1.0 - cfg.max_daily_loss_pct / 100.0):
            daily_stopped = True
            daily_stop_days += 1

        # Procesar salidas intra-barra H1 para SL/TP (exacto incluso para posiciones H4)
        hi1 = float(tf_data[60]["high"][h1_i])
        lo1 = float(tf_data[60]["low"][h1_i])
        for s in active_slots:
            p = open_pos[s]
            if p is None:
                continue
            tf_m = SLOT_TIMEFRAMES_MIN[s]
            # Si corresponde bar de salida por MaxHoldBars al abrir esta barra del slot
            if tf_m == 60:
                held = h1_i - int(p["entry_idx"])
            elif ts_int in h4_ts_to_idx:
                held = h4_ts_to_idx[ts_int] - int(p["entry_idx"])
            else:
                held = -1
            if held >= max_hold_map[s]:
                rec, pnl = _close_slot_trade(s, p, ts_int, px_h1, "TIME_CLOSE", held, spec)
                trades.append(rec)
                balance += pnl
                open_pos[s] = None
                continue

            # MAE/MFE en barra H1 actual y chequeo SL/TP
            side = int(p["side"])
            epx = float(p["entry_price"])
            p["mfe_pts"] = max(p["mfe_pts"], max(0.0, (hi1 - epx) if side > 0 else (epx - lo1)))
            p["mae_pts"] = max(p["mae_pts"], max(0.0, (epx - lo1) if side > 0 else (hi1 - epx)))

            sl_hit = (lo1 <= p["sl"]) if side > 0 else (hi1 >= p["sl"])
            tp_hit = (hi1 >= p["tp"]) if side > 0 else (lo1 <= p["tp"])
            if sl_hit:
                slot_i = h4_ts_to_idx.get(ts_int, p["entry_idx"]) if tf_m == 240 else h1_i
                rec, pnl = _close_slot_trade(s, p, ts_int, float(p["sl"]), "SL", max(1, slot_i - p["entry_idx"] + 1), spec)
                trades.append(rec)
                balance += pnl
                open_pos[s] = None
            elif tp_hit:
                slot_i = h4_ts_to_idx.get(ts_int, p["entry_idx"]) if tf_m == 240 else h1_i
                rec, pnl = _close_slot_trade(s, p, ts_int, float(p["tp"]), "TP", max(1, slot_i - p["entry_idx"] + 1), spec)
                trades.append(rec)
                balance += pnl
                open_pos[s] = None

        if halted or daily_stopped:
            continue

        # Procesar nuevas señales al abrir barra del timeframe de cada slot
        for s in active_slots:
            if open_pos[s] is not None:
                continue
            if cfg.max_sends_per_day > 0 and sends_today[s] >= cfg.max_sends_per_day:
                continue

            tf_m = SLOT_TIMEFRAMES_MIN[s]
            if tf_m == 240:
                if ts_int not in h4_ts_to_idx:
                    continue
                slot_i = h4_ts_to_idx[ts_int]
            else:
                slot_i = h1_i
            if slot_i < 2:
                continue

            if override_signals is not None and s in override_signals:
                direction = int(override_signals[s].get(ts_int, 0))
            else:
                arrs = tf_data[tf_m]
                ind = tf_ind[tf_m]
                direction = _slot_signal_inferred(s, slot_i, arrs, ind["ema10"], ind["ema50"], ind["atr5"], ind["atr20"])
            if direction == 0:
                continue

            if cfg.no_hedge and any(p is not None and p["side"] == -direction for p in open_pos.values()):
                hedge_blocked += 1
                continue

            atr_val = float(tf_ind[tf_m]["atr14"][slot_i - 1])
            if not (np.isfinite(atr_val) and atr_val > 0):
                continue

            sl_dist = spec.round_price(cfg.sl_atr_mult * atr_val)
            tp_dist = spec.round_price(cfg.tp_atr_mult * atr_val)
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
                allow_min_fallback=cfg.trade_min_lot,
            )
            if lots <= 0:
                continue

            open_px = float(tf_data[tf_m]["open"][slot_i]) + (0.5 * cfg.spread_price * direction)
            open_pos[s] = {
                "side": direction,
                "qty": lots,
                "entry_ts_ns": ts_int,
                "entry_idx": slot_i,
                "entry_price": open_px,
                "sl": spec.round_price(open_px - direction * sl_dist),
                "tp": spec.round_price(open_px + direction * tp_dist),
                "mfe_pts": 0.0,
                "mae_pts": 0.0,
            }
            sends_today[s] += 1

    # Cierre al final del periodo
    last_ts = int(h1_ts[-1])
    last_px = float(tf_data[60]["close"][-1])
    for s in active_slots:
        p = open_pos[s]
        if p is not None:
            tf_m = SLOT_TIMEFRAMES_MIN[s]
            end_i = len(tf_data[tf_m]["ts_ns"]) - 1
            rec, pnl = _close_slot_trade(s, p, last_ts, last_px, "END_OF_DATA", max(1, end_i - p["entry_idx"] + 1), spec)
            trades.append(rec)
            balance += pnl

    out_df = trades_to_df(trades)
    if not return_diagnostics:
        return out_df
    return out_df, {
        "final_balance": round(balance, 2),
        "daily_loss_days": daily_stop_days,
        "hedge_blocked": hedge_blocked,
        "trades": len(out_df),
    }


def correr_slot_qlb(
    df_ohlc: pd.DataFrame,
    slot_id: int,
    config: Optional[QlbBasketConfig] = None,
    instrument: str | InstrumentSpec = "XAUUSD",
    override_signals: Optional[Mapping[int, int]] = None,
) -> pd.DataFrame:
    """Ejecuta unicamente uno de los 3 slots de QLB (`0=speed_switch`, `1=q4_breakout`, `2=tom_jan`)."""
    ov = {slot_id: override_signals} if override_signals is not None else None
    return correr_qlb_basket(df_ohlc, config=config, instrument=instrument, slots=(slot_id,), override_signals=ov)
