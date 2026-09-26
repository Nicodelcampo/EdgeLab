"""Target-free aggregation for the NQ 09-26 maintenance-window anomaly."""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

DIAGNOSTIC_VERSION = "nq0926_maintenance_diagnostic_v1"


class MaintenanceAccumulator:
    def __init__(self) -> None:
        self.total_rows = 0
        self.maintenance_rows = 0
        self.maintenance_volume = 0
        self.per_day: dict[int, dict[str, Any]] = {}
        self.offsets = Counter()

    def update(self, *, ts_utc_ns, ts_local_ns, sequence, volume, source_file,
               source_row, trade_date, minute_since_open, maintenance_mask) -> None:
        arrays = [np.asarray(x) for x in (ts_utc_ns, ts_local_ns, sequence, volume,
            source_file, source_row, trade_date, minute_since_open, maintenance_mask)]
        lengths = {len(x) for x in arrays}
        if len(lengths) != 1:
            raise ValueError("batch columns have different lengths")
        ts, local, seq, vol, src, src_row, days, minute, maint = arrays
        self.total_rows += len(ts)
        self.maintenance_rows += int(maint.sum())
        self.maintenance_volume += int(vol[maint].sum())
        for delta, count in zip(*np.unique(local - ts, return_counts=True)):
            self.offsets[int(delta)] += int(count)
        for day in np.unique(days[maint]):
            m = maint & (days == day)
            rec = self.per_day.setdefault(int(day), {"tick_count": 0, "volume": 0,
                "first_ts_utc_ns": None, "last_ts_utc_ns": None,
                "sequence_min": None, "sequence_max": None,
                "minute_counts": Counter(), "source_files": Counter(),
                "source_row_min": {}, "source_row_max": {}})
            rec["tick_count"] += int(m.sum()); rec["volume"] += int(vol[m].sum())
            lo, hi = int(ts[m].min()), int(ts[m].max())
            rec["first_ts_utc_ns"] = lo if rec["first_ts_utc_ns"] is None else min(lo, rec["first_ts_utc_ns"])
            rec["last_ts_utc_ns"] = hi if rec["last_ts_utc_ns"] is None else max(hi, rec["last_ts_utc_ns"])
            qlo, qhi = int(seq[m].min()), int(seq[m].max())
            rec["sequence_min"] = qlo if rec["sequence_min"] is None else min(qlo, rec["sequence_min"])
            rec["sequence_max"] = qhi if rec["sequence_max"] is None else max(qhi, rec["sequence_max"])
            for value, count in zip(*np.unique(minute[m], return_counts=True)):
                rec["minute_counts"][int(value)] += int(count)
            selected_src, selected_rows = src[m], src_row[m]
            for name in np.unique(selected_src):
                sm = selected_src == name; key = str(name)
                rec["source_files"][key] += int(sm.sum())
                rlo, rhi = int(selected_rows[sm].min()), int(selected_rows[sm].max())
                rec["source_row_min"][key] = min(rlo, rec["source_row_min"].get(key, rlo))
                rec["source_row_max"][key] = max(rhi, rec["source_row_max"].get(key, rhi))

    def finalize(self) -> dict[str, Any]:
        fraction = self.maintenance_rows / self.total_rows if self.total_rows else 0.0
        days = []
        for day, raw in sorted(self.per_day.items()):
            rec = dict(raw)
            rec["trade_date"] = day
            rec["minute_counts"] = {str(k): v for k, v in sorted(raw["minute_counts"].items())}
            rec["source_files"] = dict(sorted(raw["source_files"].items()))
            days.append(rec)
        return {"diagnostic_version": DIAGNOSTIC_VERSION,
            "status": "COMPLETE_WITH_MAINTENANCE_ANOMALY" if self.maintenance_rows else "COMPLETE_NO_MAINTENANCE_TICKS",
            "root_cause_status": "UNRESOLVED",
            "total_rows": self.total_rows,
            "maintenance_tick_count": self.maintenance_rows,
            "maintenance_volume": self.maintenance_volume,
            "maintenance_fraction": fraction,
            "ts_local_minus_ts_utc_ns": {str(k): v for k, v in sorted(self.offsets.items())},
            "per_trade_date": days,
            "hypotheses_not_decided": ["SOURCE_TIMESTAMP_CONTAMINATION",
                "UTC_LOCAL_FIELD_SEMANTICS", "RECUT_ROW_SELECTION", "REAL_SOURCE_ROWS"]}


def flattened_minute_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for day in report["per_trade_date"]:
        for minute, count in day["minute_counts"].items():
            rows.append({"trade_date": day["trade_date"],
                         "minute_since_session_open": int(minute),
                         "tick_count": count})
    return rows
