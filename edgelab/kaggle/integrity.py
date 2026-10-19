"""Chequeos de integridad sobre arrays de ticks decodificados.

Generaliza a los 56 contratos la bateria que en la auditoria local se corrio a
mano sobre 6E (P-14 / P-15: minutos faltantes en horario activo, defectos de
build). Todo es descriptivo y causal-neutro: no toca outcomes, no mira adelante
y no depende de targets. Por eso puede correr con outcomes_accessed=False.

Solo numpy + stdlib.
"""

from __future__ import annotations

import numpy as np

from .sessions_cme import (
    NS_PER_SEC,
    is_maintenance_break,
    minutes_since_session_open,
    trade_date_ymd,
)

NS_PER_MIN = 60 * NS_PER_SEC


def tick_checks(
    *,
    ts_utc_ns: np.ndarray,
    price_ticks: np.ndarray | None = None,
    volume: np.ndarray | None = None,
    bid_ticks: np.ndarray | None = None,
    ask_ticks: np.ndarray | None = None,
    sequence: np.ndarray | None = None,
) -> dict:
    """Chequeos estructurales de un archivo de ticks.

    Devuelve un dict serializable. Ningun chequeo levanta excepcion: el
    veredicto lo decide el notebook contra los gates del contrato.
    """
    ts = np.asarray(ts_utc_ns, dtype=np.int64)
    n = int(ts.size)
    out: dict = {"rows": n}
    if n == 0:
        return out

    d = np.diff(ts)
    out["ts_monotonic_non_decreasing"] = bool((d >= 0).all())
    out["ts_backward_steps"] = int((d < 0).sum())
    out["ts_min_ns"] = int(ts.min())
    out["ts_max_ns"] = int(ts.max())
    out["ts_duplicate_rows"] = int((d == 0).sum())
    if d.size:
        out["gap_max_seconds"] = float(d.max() / NS_PER_SEC)
        out["gap_p999_seconds"] = float(np.quantile(d, 0.999) / NS_PER_SEC)

    if sequence is not None:
        seq = np.asarray(sequence, dtype=np.int64)
        uniq = np.unique(seq)
        out["sequence_rows"] = int(seq.size)
        out["sequence_unique"] = int(uniq.size)
        out["sequence_duplicates"] = int(seq.size - uniq.size)
        ds = np.diff(seq)
        out["sequence_monotonic_increasing"] = bool((ds > 0).all())
        out["sequence_backward_steps"] = int((ds < 0).sum())
        out["sequence_min"] = int(seq.min())
        out["sequence_max"] = int(seq.max())

    if volume is not None:
        vol = np.asarray(volume, dtype=np.int64)
        out["volume_sum"] = int(vol.sum())
        out["volume_non_positive"] = int((vol <= 0).sum())
        out["volume_max"] = int(vol.max())

    if price_ticks is not None:
        px = np.asarray(price_ticks, dtype=np.int64)
        out["price_min_ticks"] = int(px.min())
        out["price_max_ticks"] = int(px.max())
        out["price_non_positive"] = int((px <= 0).sum())

    if bid_ticks is not None and ask_ticks is not None:
        bid = np.asarray(bid_ticks, dtype=np.int64)
        ask = np.asarray(ask_ticks, dtype=np.int64)
        valid = (bid > 0) & (ask > 0)
        out["quote_rows_valid"] = int(valid.sum())
        out["quote_frac_valid"] = float(valid.mean())
        out["quote_crossed"] = int((valid & (bid > ask)).sum())
        spread = np.where(valid, ask - bid, 0)
        if int(valid.sum()):
            sv = spread[valid]
            out["spread_ticks_mean"] = float(sv.mean())
            out["spread_ticks_median"] = float(np.median(sv))
            out["spread_ticks_max"] = int(sv.max())
            out["spread_zero_or_negative"] = int((sv <= 0).sum())
        if price_ticks is not None:
            px = np.asarray(price_ticks, dtype=np.int64)
            inside = valid & (px >= bid) & (px <= ask)
            out["trade_inside_quote_frac"] = float(
                inside.sum() / max(int(valid.sum()), 1)
            )
            out["trade_at_bid"] = int((valid & (px == bid)).sum())
            out["trade_at_ask"] = int((valid & (px == ask)).sum())
            out["trade_outside_quote"] = int((valid & ~inside).sum())
    return out


def session_activity(
    ts_utc_ns: np.ndarray,
    *,
    volume: np.ndarray | None = None,
) -> dict:
    """Actividad por trade date: ticks, volumen, minutos distintos y hueco maximo.

    `minutes_active` cuenta minutos distintos con al menos un tick, excluyendo la
    pausa de mantenimiento. Un dia completo de Globex tiene 1380 minutos
    negociables (23 h); menos que eso no implica defecto (feriados, medias
    sesiones, iliquidez del back month), por eso se reporta el numero y la
    decision queda en el gate del notebook.
    """
    ts = np.asarray(ts_utc_ns, dtype=np.int64)
    if ts.size == 0:
        return {"trade_dates": 0, "by_trade_date": {}}
    td = trade_date_ymd(ts)
    mins = minutes_since_session_open(ts)
    brk = is_maintenance_break(ts)
    vol = None if volume is None else np.asarray(volume, dtype=np.int64)

    out: dict = {}
    order = np.argsort(td, kind="stable")
    td_s = td[order]
    uniq, starts = np.unique(td_s, return_index=True)
    bounds = list(starts) + [td_s.size]
    for i, day in enumerate(uniq):
        sl = order[bounds[i] : bounds[i + 1]]
        t = ts[sl]
        m = mins[sl]
        b = brk[sl]
        active = ~b
        rec = {
            "ticks": int(t.size),
            "ticks_in_maintenance": int(b.sum()),
            "minutes_active": int(np.unique(m[active]).size),
            "first_minute": int(m[active].min()) if int(active.sum()) else None,
            "last_minute": int(m[active].max()) if int(active.sum()) else None,
            "ts_min_ns": int(t.min()),
            "ts_max_ns": int(t.max()),
        }
        if t.size > 1:
            dd = np.diff(np.sort(t))
            rec["gap_max_seconds"] = float(dd.max() / NS_PER_SEC)
        if vol is not None:
            rec["volume"] = int(vol[sl].sum())
        out[int(day)] = rec
    return {"trade_dates": int(uniq.size), "by_trade_date": out}


def missing_active_minutes(
    activity: dict,
    *,
    min_minutes_full_session: int = 1380,
    tolerance_minutes: int = 60,
) -> dict:
    """Resumen de cobertura de minutos por sesion (bateria P-14 / P-15).

    Clasifica cada trade date en:
      * full: minutes_active >= min_minutes_full_session - tolerance_minutes
      * partial: entre 10 % y ese umbral
      * sparse: menos del 10 % (candidato a cuarentena o a back month ilíquido)
    """
    full, partial, sparse = [], [], []
    thr_full = min_minutes_full_session - tolerance_minutes
    thr_sparse = max(int(0.10 * min_minutes_full_session), 1)
    for day, rec in activity.get("by_trade_date", {}).items():
        m = int(rec.get("minutes_active") or 0)
        if m >= thr_full:
            full.append(int(day))
        elif m >= thr_sparse:
            partial.append(int(day))
        else:
            sparse.append(int(day))
    return {
        "threshold_full_minutes": thr_full,
        "threshold_sparse_minutes": thr_sparse,
        "n_full": len(full),
        "n_partial": len(partial),
        "n_sparse": len(sparse),
        "partial_trade_dates": sorted(partial),
        "sparse_trade_dates": sorted(sparse),
    }


def weekday_histogram(activity: dict) -> dict:
    """Distribucion de trade dates por dia de semana (detecta sabados espurios)."""
    from .sessions_cme import ymd_weekday

    hist = {i: 0 for i in range(7)}
    for day in activity.get("by_trade_date", {}):
        hist[ymd_weekday(int(day))] += 1
    return {str(k): v for k, v in hist.items()}
