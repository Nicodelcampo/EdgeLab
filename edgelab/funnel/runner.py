"""Stage-local exploratory outcome runner. Never a confirmation/promotion gate.

Only CPU orchestration is enabled in this integration. Low-level CUDA synthetic
parity tooling remains separate; it does not certify this new end-to-end route.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from validation.pbo import pbo_cscv
from .isolation import bounded_batches, stage_window
from .splits import make_splits, to_dict, validate_split
from .survivors import write_survivors
from .ledger import FunnelLedger

DIRECTION_MULTIPLIERS = {"normal": 1, "inverse": -1, "reverse": -1}


class FunnelRunner:
    def __init__(self, *, trade_dates, signal_idx, signal_dir, high, low,
                 bid_open, ask_open, configs, out_dir, backend="cpu", frozen_split=None):
        if backend != "cpu":
            raise RuntimeError("Stage-local runner is CPU-only pending end-to-end GPU validation; no silent fallback")
        self.td = np.asarray(trade_dates)
        self.si, self.sd = np.asarray(signal_idx), np.asarray(signal_dir)
        # No global price extrema/hash/dtype conversion: D2 values are not inspected.
        self.h, self.l = np.asarray(high), np.asarray(low)
        self.bo, self.ao = np.asarray(bid_open), np.asarray(ask_open)
        if self.td.ndim != 1 or self.td.dtype.kind not in "iu" or not len(self.td) or np.any(self.td[1:] < self.td[:-1]):
            raise ValueError("trade_dates must be chronological integer labels")
        if self.si.ndim != 1 or self.si.dtype.kind not in "iu" or np.any(self.si < 0) or np.any(self.si >= len(self.td)):
            raise ValueError("signal indices must be inside bars")
        if self.sd.ndim != 1 or len(self.si) != len(self.sd) or not np.isin(self.sd, [-1, 1]).all():
            raise ValueError("signal directions must be +/-1 and match signals")
        if any(a.ndim != 1 or len(a) != len(self.td) for a in (self.h, self.l, self.bo, self.ao)):
            raise ValueError("bar lengths/shapes disagree")
        self.cfg = [dict(c) for c in configs]
        if not self.cfg:
            raise ValueError("empty candidate registry")
        ids = [c.get("candidate_id") for c in self.cfg]
        if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError("candidate_id must be unique nonempty strings")
        for c in self.cfg:
            if not isinstance(c.get("family_id"), str) or not c["family_id"]:
                raise ValueError("family_id is required")
            if c.get("direction", "normal") not in DIRECTION_MULTIPLIERS:
                raise ValueError("direction must be normal/inverse (reverse is a legacy alias)")
            for key in ("sl_ticks", "tp_ticks"):
                value = c.get(key)
                if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)) or not np.isfinite(value) or value <= 0 or value != int(value) or value > np.iinfo(np.int32).max:
                    raise ValueError("SL/TP must be positive integral int32 tick distances")
        self.split = validate_split(frozen_split or make_splits(self.td), self.td)
        self.split_source = "FROZEN_SUPPLIED" if frozen_split is not None else "GENERATED_DIAGNOSTIC_ONLY"
        self.out, self.backend = Path(out_dir), backend
        # Output setup is deferred until run/preflight; never overwrite prior runs.

    def run_e1_e3(self, min_trades=30, max_hold_bars=200, max_matrix_bytes=512*1024*1024):
        if isinstance(min_trades, (bool, np.bool_)) or not isinstance(min_trades, (int, np.integer)) or min_trades < 1:
            raise ValueError("min_trades must be a positive integer")
        if isinstance(max_matrix_bytes, (bool, np.bool_)) or not isinstance(max_matrix_bytes, (int, np.integer)) or max_matrix_bytes <= 0:
            raise ValueError("matrix budget must be a positive integer")
        windows = {part: stage_window(self.td, self.si, dates, max_hold_bars)
                   for part, dates in (("D0", self.split.d0_dates), ("D1", self.split.d1_dates))}
        if any(len(w.signal_positions)*8 > max_matrix_bytes for w in windows.values()):
            raise ValueError("matrix budget cannot fit one stage signal column")
        if self.out.exists():
            raise FileExistsError("Output already exists; choose a new directory and preserve prior evidence")
        sl = np.array([c["sl_ticks"] for c in self.cfg])
        tp = np.array([c["tp_ticks"] for c in self.cfg])
        mult = np.array([DIRECTION_MULTIPLIERS[c.get("direction", "normal")] for c in self.cfg], np.int8)

        def batches(part, keep):
            w = windows[part]
            bar = slice(w.bar_start, w.bar_stop)
            return bounded_batches(w.local_signals(self.si), self.sd[w.signal_positions],
                                   self.h[bar], self.l[bar], self.bo[bar], self.ao[bar],
                                   sl[keep], tp[keep], mult[keep], max_hold_bars=max_hold_bars,
                                   backend="cpu", max_matrix_bytes=max_matrix_bytes)

        stats = {part: [(0, None) for _ in self.cfg] for part in windows}
        devices = {}
        keep = np.arange(len(self.cfg))
        for part in windows:
            for first, last, matrix, dev in batches(part, keep):
                devices[part] = dev.__dict__
                for local in range(last-first):
                    finite = matrix[:, local][np.isfinite(matrix[:, local])]
                    stats[part][first+local] = (len(finite), float(finite.mean()) if len(finite) else None)
        rows = []
        for i, config in enumerate(self.cfg):
            n0, a = stats["D0"][i]; n1, b = stats["D1"][i]
            survives = n0 >= min_trades and n1 >= min_trades and a is not None and b is not None and a > 0 and b > 0
            rows.append({**config, "d0_n": n0, "d0_mean": a, "d1_n": n1, "d1_mean": b, "survives_e1_e2": bool(survives)})
        survivors = [row for row in rows if row["survives_e1_e2"]]
        headlines = []
        for family in sorted({row["family_id"] for row in survivors}):
            family_rows = [row for row in survivors if row["family_id"] == family]
            headlines.append(max(family_rows, key=lambda row: min(row["d0_mean"], row["d1_mean"])-abs(row["d0_mean"]-row["d1_mean"])))
        isolation = {"policy": "complete_horizon_stage_local_v1", "scope": "outcome_kernels_only",
                     "max_hold_bars": int(max_hold_bars), "visited_bars_per_horizon": int(max_hold_bars)+1,
                     "d2_prices_passed_to_kernel": False,
                     "boundary_excluded": {p:w.excluded_boundary_signals for p,w in windows.items()},
                     "eligible_signals": {p:len(w.signal_positions) for p,w in windows.items()},
                     "max_matrix_bytes": int(max_matrix_bytes), "budget_scope": "one_output_matrix_not_total_memory"}
        multiplicity = {"status": "NOT_RUN_INSUFFICIENT_SURVIVORS", "pbo": None,
                        "candidates": len(survivors), "scope": "survivors_only_diagnostic", "promotion_allowed": False}
        if len(survivors) >= 2:
            byid = {c["candidate_id"]:i for i,c in enumerate(self.cfg)}
            keep = np.array([byid[row["candidate_id"]] for row in survivors])
            days = self.split.d0_dates + self.split.d1_dates
            positions = {int(day):i for i,day in enumerate(days)}
            daily = np.zeros((len(days), len(keep)), np.float64)
            for part, window in windows.items():
                signal_days = self.td[self.si[window.signal_positions]+1]
                for first, last, matrix, _ in batches(part, keep):
                    for local in range(last-first):
                        for day, value in zip(signal_days, matrix[:, local]):
                            if np.isfinite(value):
                                daily[positions[int(day)], first+local] += value
            pbo = pbo_cscv(daily, S=10)
            raw = float(pbo["pbo"])
            multiplicity.update(status="COMPLETE_DIAGNOSTIC_ONLY", pbo=raw if np.isfinite(raw) else None, splits=int(pbo["n_splits"]))
        self.out.mkdir(parents=True, exist_ok=False)
        ledger = FunnelLedger(self.out / "edge_brain.jsonl")
        metadata = {"schema_version": "stage_local_cpu_v2", "split_hash": self.split.split_hash,
                    "backend": "cpu", "confirmatory": False, "isolation_policy": isolation["policy"]}
        trials = write_survivors(rows, self.out / "trials.parquet", metadata)
        artifact = write_survivors(survivors, self.out / "survivors.parquet", metadata)
        payload = {"schema_version": "stage_local_cpu_v2", "stage": "E1_E2_WITH_E3_IF_ELIGIBLE",
                   "devices": devices, "device": devices.get("D0", devices.get("D1")),
                   "device_scope": "deprecated_cpu_only_alias", "trial_ledger_contract": "funnel_local_hash_chain_not_durable_hippocampus", "split": to_dict(self.split),
                   "split_source": self.split_source, "isolation": isolation, "tested": len(rows),
                   "survivors": len(survivors), "headlines": headlines, "multiplicity": multiplicity,
                   "trial_artifact": trials, "survivor_artifact": artifact, "asserts_edge": False,
                   "holdout_opened": None, "upstream_data_access": "NOT_AUDITED_BY_RUNNER",
                   "runner_d2_outcomes_read": False, "promotion_allowed": False}
        identifier = "FUNNEL-" + hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()[:16]
        ledger.append("trial_recorded", identifier, payload)
        (self.out / "summary.json").write_text(json.dumps(payload, indent=2, allow_nan=False))
        return payload

    def d2_mask(self, unlock_token=None):
        raise PermissionError("This runner never opens D2; split hash is not an approval credential")
