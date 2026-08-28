"""Acumulador streaming de integridad para archivos de ticks grandes.

Motivo: un contrato de ES tiene ~60 M ticks; leer 6 columnas int64 completas son
~3 GB de RAM por archivo. El presupuesto contractual es peak RSS <= 20 GB para
TODA la corrida, asi que la validacion se hace por batches con estado O(dias).

Diseno: `TickStreamAccumulator.update()` recibe arrays numpy de un batch (en
orden temporal) y mantiene contadores exactos, no aproximados. `finalize()`
devuelve las MISMAS claves que `integrity.tick_checks` / `session_activity`
para las metricas compartidas, de modo que existe un test de paridad
streaming vs batch. Si las dos rutas discrepan, la corrida se abstiene.

No requiere pyarrow: recibe arrays, no archivos. Eso lo hace testeable fuera de
Kaggle (por ejemplo alimentandolo desde un .npz en un sandbox sin pyarrow).
"""

from __future__ import annotations

import numpy as np

from . import seal as seal_mod
from .sessions_cme import (
    NS_PER_SEC,
    is_maintenance_break,
    minutes_since_session_open,
    trade_date_ymd,
)

MINUTES_PER_DAY = 1440


class _DayState:
    __slots__ = (
        "ticks",
        "maint",
        "volume",
        "minutes",
        "ts_min",
        "ts_max",
        "gap_max",
        "last_ts",
    )

    def __init__(self) -> None:
        self.ticks = 0
        self.maint = 0
        self.volume = 0
        self.minutes = np.zeros(MINUTES_PER_DAY, dtype=bool)
        self.ts_min: int | None = None
        self.ts_max: int | None = None
        self.gap_max = 0
        self.last_ts: int | None = None


class TickStreamAccumulator:
    """Estado O(dias) sobre un stream de ticks ordenado por tiempo."""

    def __init__(self, *, open_holdout_token: str | None = None) -> None:
        self.open_holdout_token = open_holdout_token
        self.rows = 0
        self.ts_min: int | None = None
        self.ts_max: int | None = None
        self.ts_backward_steps = 0
        self.ts_duplicate_rows = 0
        self.gap_max_ns = 0
        self._last_ts: int | None = None
        self.seq_min: int | None = None
        self.seq_max: int | None = None
        self.seq_backward_steps = 0
        self.seq_non_increasing = 0
        self._last_seq: int | None = None
        self.volume_sum = 0
        self.volume_non_positive = 0
        self.volume_max = 0
        self.price_min: int | None = None
        self.price_max: int | None = None
        self.price_non_positive = 0
        self.quote_rows_valid = 0
        self.quote_crossed = 0
        self.spread_sum = 0
        self.spread_max = 0
        self.spread_zero_or_negative = 0
        self.trade_at_bid = 0
        self.trade_at_ask = 0
        self.trade_outside_quote = 0
        self.days: dict[int, _DayState] = {}
        self._seal_reports: list[seal_mod.SealReport] = []
        self.batches = 0

    # ------------------------------------------------------------------ update
    def update(
        self,
        *,
        ts_utc_ns: np.ndarray,
        price_ticks: np.ndarray | None = None,
        volume: np.ndarray | None = None,
        bid_ticks: np.ndarray | None = None,
        ask_ticks: np.ndarray | None = None,
        sequence: np.ndarray | None = None,
    ) -> None:
        ts = np.asarray(ts_utc_ns, dtype=np.int64)
        n = int(ts.size)
        if n == 0:
            return
        self.batches += 1
        self.rows += n

        # --- tiempo (con continuidad entre batches)
        self.ts_min = int(ts[0]) if self.ts_min is None else min(self.ts_min, int(ts.min()))
        self.ts_max = int(ts.max()) if self.ts_max is None else max(self.ts_max, int(ts.max()))
        seq_ts = ts if self._last_ts is None else np.concatenate(([self._last_ts], ts))
        d = np.diff(seq_ts)
        if d.size:
            self.ts_backward_steps += int((d < 0).sum())
            self.ts_duplicate_rows += int((d == 0).sum())
            self.gap_max_ns = max(self.gap_max_ns, int(d.max()))
        self._last_ts = int(ts[-1])

        # --- sequence
        if sequence is not None:
            sq = np.asarray(sequence, dtype=np.int64)
            self.seq_min = int(sq.min()) if self.seq_min is None else min(self.seq_min, int(sq.min()))
            self.seq_max = int(sq.max()) if self.seq_max is None else max(self.seq_max, int(sq.max()))
            sseq = sq if self._last_seq is None else np.concatenate(([self._last_seq], sq))
            ds = np.diff(sseq)
            if ds.size:
                self.seq_backward_steps += int((ds < 0).sum())
                self.seq_non_increasing += int((ds <= 0).sum())
            self._last_seq = int(sq[-1])

        # --- volumen y precio
        vol = None
        if volume is not None:
            vol = np.asarray(volume, dtype=np.int64)
            self.volume_sum += int(vol.sum())
            self.volume_non_positive += int((vol <= 0).sum())
            self.volume_max = max(self.volume_max, int(vol.max()))
        px = None
        if price_ticks is not None:
            px = np.asarray(price_ticks, dtype=np.int64)
            self.price_min = int(px.min()) if self.price_min is None else min(self.price_min, int(px.min()))
            self.price_max = int(px.max()) if self.price_max is None else max(self.price_max, int(px.max()))
            self.price_non_positive += int((px <= 0).sum())

        # --- cotizaciones
        if bid_ticks is not None and ask_ticks is not None:
            bid = np.asarray(bid_ticks, dtype=np.int64)
            ask = np.asarray(ask_ticks, dtype=np.int64)
            valid = (bid > 0) & (ask > 0)
            nv = int(valid.sum())
            self.quote_rows_valid += nv
            if nv:
                self.quote_crossed += int((valid & (bid > ask)).sum())
                sv = (ask - bid)[valid]
                self.spread_sum += int(sv.sum())
                self.spread_max = max(self.spread_max, int(sv.max()))
                self.spread_zero_or_negative += int((sv <= 0).sum())
                if px is not None:
                    inside = valid & (px >= bid) & (px <= ask)
                    self.trade_at_bid += int((valid & (px == bid)).sum())
                    self.trade_at_ask += int((valid & (px == ask)).sum())
                    self.trade_outside_quote += int((valid & ~inside).sum())

        # --- sello del holdout (contadores por batch, se agregan al final)
        _, rep = seal_mod.apply_seal(ts, open_holdout_token=self.open_holdout_token)
        self._seal_reports.append(rep)

        # --- actividad por trade date
        td = trade_date_ymd(ts)
        mins = minutes_since_session_open(ts)
        brk = is_maintenance_break(ts)
        for day in np.unique(td):
            m = td == day
            st = self.days.get(int(day))
            if st is None:
                st = _DayState()
                self.days[int(day)] = st
            t = ts[m]
            st.ticks += int(t.size)
            st.maint += int(brk[m].sum())
            if vol is not None:
                st.volume += int(vol[m].sum())
            active = ~brk[m]
            if int(active.sum()):
                st.minutes[mins[m][active]] = True
            tmin, tmax = int(t.min()), int(t.max())
            st.ts_min = tmin if st.ts_min is None else min(st.ts_min, tmin)
            st.ts_max = tmax if st.ts_max is None else max(st.ts_max, tmax)
            ts_day = np.sort(t)
            seq_day = (
                ts_day if st.last_ts is None else np.concatenate(([st.last_ts], ts_day))
            )
            dd = np.diff(seq_day)
            if dd.size:
                st.gap_max = max(st.gap_max, int(dd.max()))
            st.last_ts = int(ts_day[-1])

    # ---------------------------------------------------------------- finalize
    def tick_checks(self) -> dict:
        out: dict = {"rows": self.rows}
        if not self.rows:
            return out
        out["ts_monotonic_non_decreasing"] = self.ts_backward_steps == 0
        out["ts_backward_steps"] = self.ts_backward_steps
        out["ts_min_ns"] = self.ts_min
        out["ts_max_ns"] = self.ts_max
        out["ts_duplicate_rows"] = self.ts_duplicate_rows
        out["gap_max_seconds"] = float(self.gap_max_ns / NS_PER_SEC)
        if self.seq_min is not None:
            out["sequence_rows"] = self.rows
            out["sequence_monotonic_increasing"] = self.seq_non_increasing == 0
            out["sequence_backward_steps"] = self.seq_backward_steps
            out["sequence_min"] = self.seq_min
            out["sequence_max"] = self.seq_max
            # Con sequence estrictamente creciente no puede haber duplicados;
            # si no lo es, se reporta el conteo de pasos no crecientes.
            out["sequence_non_increasing_steps"] = self.seq_non_increasing
        if self.volume_sum or self.volume_max:
            out["volume_sum"] = self.volume_sum
            out["volume_non_positive"] = self.volume_non_positive
            out["volume_max"] = self.volume_max
        if self.price_min is not None:
            out["price_min_ticks"] = self.price_min
            out["price_max_ticks"] = self.price_max
            out["price_non_positive"] = self.price_non_positive
        if self.quote_rows_valid:
            out["quote_rows_valid"] = self.quote_rows_valid
            out["quote_frac_valid"] = float(self.quote_rows_valid / self.rows)
            out["quote_crossed"] = self.quote_crossed
            out["spread_ticks_mean"] = float(self.spread_sum / self.quote_rows_valid)
            out["spread_ticks_max"] = self.spread_max
            out["spread_zero_or_negative"] = self.spread_zero_or_negative
            out["trade_at_bid"] = self.trade_at_bid
            out["trade_at_ask"] = self.trade_at_ask
            out["trade_outside_quote"] = self.trade_outside_quote
            out["trade_inside_quote_frac"] = float(
                (self.quote_rows_valid - self.trade_outside_quote)
                / self.quote_rows_valid
            )
        return out

    def activity(self) -> dict:
        by: dict = {}
        for day, st in sorted(self.days.items()):
            idx = np.flatnonzero(st.minutes)
            rec = {
                "ticks": st.ticks,
                "ticks_in_maintenance": st.maint,
                "minutes_active": int(idx.size),
                "first_minute": int(idx.min()) if idx.size else None,
                "last_minute": int(idx.max()) if idx.size else None,
                "ts_min_ns": st.ts_min,
                "ts_max_ns": st.ts_max,
            }
            if st.ticks > 1:
                rec["gap_max_seconds"] = float(st.gap_max / NS_PER_SEC)
            if st.volume:
                rec["volume"] = st.volume
            by[int(day)] = rec
        return {"trade_dates": len(by), "by_trade_date": by}

    def seal_report(self) -> seal_mod.SealReport:
        return seal_mod.merge_reports(self._seal_reports)

    def finalize(self) -> dict:
        return {
            "batches": self.batches,
            "tick_checks": self.tick_checks(),
            "activity": self.activity(),
            "seal": self.seal_report().to_dict(),
        }
