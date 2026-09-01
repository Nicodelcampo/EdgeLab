# -*- coding: utf-8 -*-
"""Censo de los 76 residuos (19 GEOMETRY_DIFF + 57 MISSING_IN_NT8) contra el
export diagnostico real de NT8 (data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv,
blob git 276acc7e0fd7d0dc5ae8ea1fba0254457de8770c). No corre nada del gate,
no toca outcomes -- cruce puro sobre artefactos ya generados.
"""
from __future__ import annotations
import csv, json, datetime as dt
from pathlib import Path

REPO = Path("C:/ProyectosQuant/EdgeLab-avolcluster-parity")
GATE_REPORT = REPO / "docs/research/avolclusterpoi_nq0626_reports_20260901/paridad_avolclusterpoi_nq0626.json"
ZONE_ORACLE = REPO / "data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv"
DIAG_CSV = REPO / "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
PY_ZONES = Path("C:/kg/tracedump_final/zones.json")
PY_BLOCKS = Path("C:/kg/tracedump_final/creation_blocks.json")
OUT_DIR = REPO / "docs/research/avolclusterpoi_nq0626_censo_76_20260901"

TICK_SIZE = 0.25

# ---------------------------------------------------------------- load ----
with open(GATE_REPORT, encoding="utf-8") as f:
    gate = json.load(f)
diag_gate = gate["diagnostics"]
geometry_diff = [d for d in diag_gate if d["code"] == "GEOMETRY_DIFF"]
missing_in_nt8 = [d for d in diag_gate if d["code"] == "MISSING_IN_NT8"]
assert len(geometry_diff) == 19 and len(missing_in_nt8) == 57

with open(PY_ZONES, encoding="utf-8") as f:
    py_zones = json.load(f)
py_zone_map = {z["id"]: z for z in py_zones}

with open(PY_BLOCKS, encoding="utf-8") as f:
    py_blocks = json.load(f)
py_block_by_zone = {}
for b in py_blocks:
    for zid in b["zone_ids"]:
        py_block_by_zone[zid] = b

# zone-level NT8 oracle: nt8_id -> row (has bar_close_time, lower_tick, upper_tick, score, threshold, samples)
nt8_zone_by_id = {}
with open(ZONE_ORACLE, encoding="utf-8") as f:
    lines = f.readlines()
header = lines[1].strip().split(",")
for line in lines[2:]:
    parts = line.strip().split(",")
    row = dict(zip(header, parts))
    if row.get("event_type") == "ZONE_CREATED":
        nt8_zone_by_id[row["zone_id"]] = row

# block-level NT8 diagnostic export: bar_close_time -> row (all 22508 blocks)
diag_by_time = {}
diag_times_sorted = []
with open(DIAG_CSV, encoding="utf-8", newline="") as f:
    r = csv.reader(f)
    next(r)  # meta comment line
    diag_header = next(r)
    for row in r:
        d = dict(zip(diag_header, row))
        diag_by_time[d["bar_close_time"]] = d
        diag_times_sorted.append(d["bar_close_time"])
diag_times_sorted.sort()
diag_dt_sorted = [dt.datetime.fromisoformat(t) for t in diag_times_sorted]


def nearest_diag_time(target_dt):
    import bisect
    keys = diag_dt_sorted
    i = bisect.bisect_left(keys, target_dt)
    candidates = []
    if i < len(keys):
        candidates.append(keys[i])
    if i > 0:
        candidates.append(keys[i - 1])
    if not candidates:
        return None, None
    best = min(candidates, key=lambda k: abs((k - target_dt).total_seconds()))
    delta = (best - target_dt).total_seconds()
    return best, delta


def parse_cells(cells_str):
    out = {}
    if not cells_str:
        return out
    for pair in cells_str.split("|"):
        if not pair:
            continue
        t, v = pair.split(":")
        out[int(t)] = float(v)
    return out


def median_of(vals):
    if not vals:
        return None
    s = sorted(vals)
    return s[len(s) // 2]


def classify(py_cells, nt8_cells):
    if py_cells is None or nt8_cells is None:
        return dict(mechanism="NO_COMPARISON_POSSIBLE", py_only=[], nt8_only=[],
                     py_only_vol=0, nt8_only_vol=0, value_diffs=[], n_value_diffs=0)
    py_only = sorted(set(py_cells) - set(nt8_cells))
    nt8_only = sorted(set(nt8_cells) - set(py_cells))
    shared = sorted(set(py_cells) & set(nt8_cells))
    value_diffs = [(t, py_cells[t], nt8_cells[t]) for t in shared if py_cells[t] != nt8_cells[t]]
    has_missing = bool(py_only) or bool(nt8_only)
    has_noise = bool(value_diffs)
    if has_missing and has_noise:
        mech = "EDGE_LEVELS_MISSING+SHARED_CELL_VALUE_NOISE"
    elif has_missing:
        mech = "EDGE_LEVELS_MISSING"
    elif has_noise:
        mech = "SHARED_CELL_VALUE_NOISE"
    else:
        mech = "NO_CELL_DIFFERENCE_FOUND"
    return dict(mechanism=mech, py_only=py_only, nt8_only=nt8_only,
                py_only_vol=sum(py_cells[t] for t in py_only),
                nt8_only_vol=sum(nt8_cells[t] for t in nt8_only),
                value_diffs=value_diffs, n_value_diffs=len(value_diffs))


def py_side_for_zone(py_id):
    z = py_zone_map.get(py_id)
    b = py_block_by_zone.get(py_id)
    if not z or not b:
        return None
    cells = {int(k): float(v) for k, v in b["cells"].items()}
    return dict(zone=z, block=b, cells=cells, median=median_of(cells.values()),
                n_cells=len(cells))


rows = []

# ---------------------------------------------------------- GEOMETRY_DIFF --
for d in geometry_diff:
    py_id, nt8_id = d["py_id"], d["nt8_id"]
    py_side = py_side_for_zone(py_id)
    nt8_zone = nt8_zone_by_id.get(nt8_id)
    row = dict(case_type="GEOMETRY_DIFF", py_id=py_id, nt8_id=nt8_id, detail=d["detail"])
    if not py_side or not nt8_zone:
        row["evidence_level"] = "PY_OR_NT8_ZONE_NOT_FOUND"
        rows.append(row)
        continue
    bar_close_time = nt8_zone["bar_close_time"]
    diag_row = diag_by_time.get(bar_close_time)
    if diag_row is None:
        row["evidence_level"] = "TIME_MATCH_AMBIGUOUS"
        row["nt8_bar_close_time_expected"] = bar_close_time
        rows.append(row)
        continue
    nt8_cells = parse_cells(diag_row["cells"])
    cmp = classify(py_side["cells"], nt8_cells)
    row.update(
        evidence_level="DIRECT",
        time_delta_seconds=0.0,
        py_n_cells=py_side["n_cells"], nt8_n_cells=len(nt8_cells),
        py_median=py_side["median"], nt8_median=float(diag_row["median"]) if diag_row["median"] else None,
        nt8_hot_threshold=float(diag_row["hot_threshold"]) if diag_row["hot_threshold"] else None,
        py_selected=[py_side["zone"]["bottom"], py_side["zone"]["top"]],
        nt8_selected=[int(nt8_zone["lower_tick"]), int(nt8_zone["upper_tick"])],
        nt8_decision=diag_row["decision"],
        py_only_ticks=cmp["py_only"], nt8_only_ticks=cmp["nt8_only"],
        py_only_vol=cmp["py_only_vol"], nt8_only_vol=cmp["nt8_only_vol"],
        n_value_diffs=cmp["n_value_diffs"], value_diffs=cmp["value_diffs"],
        mechanism=cmp["mechanism"],
    )
    rows.append(row)

# ---------------------------------------------------------- MISSING_IN_NT8 -
for d in missing_in_nt8:
    py_id = d["py_id"]
    py_side = py_side_for_zone(py_id)
    row = dict(case_type="MISSING_IN_NT8", py_id=py_id, nt8_id=None)
    if not py_side:
        row["evidence_level"] = "PY_ZONE_NOT_FOUND"
        rows.append(row)
        continue
    created_ms = py_side["zone"]["created_ms"]
    utc_dt = dt.datetime.utcfromtimestamp(created_ms / 1000.0)
    nt8_local_dt = utc_dt - dt.timedelta(hours=3)
    key = nt8_local_dt.strftime("%Y-%m-%dT%H:%M:%S.") + "{:03d}".format(nt8_local_dt.microsecond // 1000)
    diag_row = diag_by_time.get(key)
    time_delta = 0.0
    if diag_row is None:
        nearest, delta = nearest_diag_time(nt8_local_dt)
        if nearest is not None and abs(delta) <= 0.001:
            key = nearest.strftime("%Y-%m-%dT%H:%M:%S.") + "{:03d}".format(nearest.microsecond // 1000)
            diag_row = diag_by_time.get(key)
            time_delta = delta
        else:
            row["evidence_level"] = "TIME_MATCH_AMBIGUOUS"
            row["nearest_delta_seconds"] = delta
            row["ratio"] = (py_side["block"]["best_score"] / py_side["block"]["threshold"]) if py_side["block"]["threshold"] else None
            rows.append(row)
            continue
    nt8_cells = parse_cells(diag_row["cells"])
    cmp = classify(py_side["cells"], nt8_cells)
    ratio = py_side["block"]["best_score"] / py_side["block"]["threshold"] if py_side["block"]["threshold"] else None
    row.update(
        evidence_level="DIRECT",
        time_delta_seconds=time_delta,
        py_n_cells=py_side["n_cells"], nt8_n_cells=len(nt8_cells),
        py_median=py_side["median"], nt8_median=float(diag_row["median"]) if diag_row["median"] else None,
        nt8_hot_threshold=float(diag_row["hot_threshold"]) if diag_row["hot_threshold"] else None,
        py_best_score=py_side["block"]["best_score"], py_threshold=py_side["block"]["threshold"],
        py_ratio=ratio,
        nt8_best_score=float(diag_row["best_score"]) if diag_row["best_score"] else None,
        nt8_threshold=float(diag_row["threshold"]) if diag_row["threshold"] else None,
        nt8_decision=diag_row["decision"],
        py_only_ticks=cmp["py_only"], nt8_only_ticks=cmp["nt8_only"],
        py_only_vol=cmp["py_only_vol"], nt8_only_vol=cmp["nt8_only_vol"],
        n_value_diffs=cmp["n_value_diffs"], value_diffs=cmp["value_diffs"],
        mechanism=cmp["mechanism"],
    )
    rows.append(row)

# ------------------------------------------------------------- write out --
OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "censo_76_residuos.json").write_text(
    json.dumps(dict(
        source_diag_csv_blob_sha1="276acc7e0fd7d0dc5ae8ea1fba0254457de8770c",
        source_diag_csv_sha256_lf="81f32a97a65a6eee801eb6639f613349f31a2c02354862c128126af1adabf9da",
        source_gate_report_sha256="e654ace265361836d4004f26b6afec905f2a4c20172d1abd5948be4ec871d19d",
        n_geometry_diff=19, n_missing_in_nt8=57, n_total=76,
        rows=rows,
    ), indent=2, default=str),
    encoding="utf-8",
)

# ------------------------------------------------------------- summary ----
from collections import Counter
mech_counts = Counter(r.get("mechanism", r.get("evidence_level")) for r in rows)
decision_counts = Counter(r.get("nt8_decision") for r in rows if r["case_type"] == "MISSING_IN_NT8")
evidence_counts = Counter(r["evidence_level"] for r in rows)

print("=== evidence_level ===")
for k, v in evidence_counts.most_common():
    print("  {}: {}".format(k, v))
print("=== mechanism (rows with DIRECT evidence) ===")
for k, v in mech_counts.most_common():
    print("  {}: {}".format(k, v))
print("=== NT8 decision on MISSING_IN_NT8 (DIRECT only) ===")
for k, v in decision_counts.most_common():
    print("  {}: {}".format(k, v))
print("n_rows total:", len(rows))
