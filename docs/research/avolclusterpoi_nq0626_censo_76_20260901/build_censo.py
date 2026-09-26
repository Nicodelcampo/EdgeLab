# -*- coding: utf-8 -*-
"""Censo reproducible de residuos aVolClusterPOI NQ 06-26.

Target-free. No corre el gate, no abre outcomes y no cambia tolerancias.
Conserva las 124 filas residuales del gate (19 GEOMETRY_DIFF,
57 MISSING_IN_NT8, 48 MISSING_IN_PYTHON), prueba unicidad de los cruces,
separa diferencias de input/algoritmo/matcher y falla cerrado ante ambigüedad.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

TICK_SIZE = 0.25
CHART_UTC_OFFSET_HOURS = -3
HARD_MATCHER_CEILING_TICKS = 8.0
EXPECTED_COUNTS = {"GEOMETRY_DIFF": 19, "MISSING_IN_NT8": 57, "MISSING_IN_PYTHON": 48}


def find_repo(start):
    for candidate in (start, *start.parents):
        if (candidate / "edgelab").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError("no se encontro la raiz del repo desde {}".format(start))


HERE = Path(__file__).resolve().parent
REPO = find_repo(HERE)
EVIDENCE = REPO / "docs/research/avolclusterpoi_nq0626_evidencia_extractos_20260901"
DEFAULT_GATE = REPO / "docs/research/avolclusterpoi_nq0626_reports_20260901/paridad_avolclusterpoi_nq0626.json"
DEFAULT_ORACLE = REPO / "data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv"
DEFAULT_DIAG = REPO / "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
DEFAULT_PY_ZONES = EVIDENCE / "00_raw_zones.json"
DEFAULT_PY_CREATION_BLOCKS = EVIDENCE / "00_raw_creation_blocks.json"


def load_json(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def as_float(value):
    return None if value in (None, "") else float(value)


def as_int(value):
    return None if value in (None, "") else int(value)


def parse_cells(raw):
    if raw is None:
        return None
    if isinstance(raw, dict):
        return {int(k): float(v) for k, v in raw.items()}
    cells = {}
    for token in str(raw or "").split("|"):
        if token:
            tick, volume = token.split(":", 1)
            cells[int(tick)] = float(volume)
    return cells


def parse_clusters(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        result = []
        for cluster in raw:
            if isinstance(cluster, dict):
                result.append({"lower_tick": int(cluster["lower_tick"]),
                               "upper_tick": int(cluster["upper_tick"]),
                               "score": float(cluster["score"]), "count": int(cluster["count"])})
            else:
                ticks, score = cluster
                result.append({"lower_tick": int(ticks[0]), "upper_tick": int(ticks[-1]),
                               "score": float(score), "count": len(ticks)})
        return result
    result = []
    for token in str(raw or "").split("|"):
        if token:
            lower, upper, score, count = token.split(":")
            result.append({"lower_tick": int(lower), "upper_tick": int(upper),
                           "score": float(score), "count": int(count)})
    return result


def median_upper(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else None


def cluster_cells(cells, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2):
    if cells is None or len(cells) < 3:
        return None, None, []
    median = median_upper(cells.values())
    hot_threshold = median * float(median_multiplier)
    hot = sorted(t for t, v in cells.items() if v >= hot_threshold)
    groups, current = [], []
    for tick in hot:
        if not current or tick - current[-1] - 1 <= int(max_gap_ticks):
            current.append(tick)
        else:
            if len(current) >= int(min_cluster_ticks):
                groups.append(current)
            current = [tick]
    if len(current) >= int(min_cluster_ticks):
        groups.append(current)
    records = [{"lower_tick": int(g[0]), "upper_tick": int(g[-1]),
                "score": float(sum(cells[t] for t in g)), "count": len(g)} for g in groups]
    return median, hot_threshold, records


def replay_on_nt8_cells(diag_row, cells):
    median, hot_threshold, clusters = cluster_cells(cells)
    threshold = as_float(diag_row.get("threshold"))
    if cells is None:
        return {"status": "NOT_AVAILABLE", "diffs": ["cells missing"]}
    if len(cells) < 3:
        decision, selected = "ABSTAIN_FEW_CELLS", None
    elif threshold is None:
        decision, selected = "ABSTAIN_NO_HISTORY", None
    elif not clusters:
        decision, selected = "ABSTAIN_NO_CLUSTER", None
    else:
        passing = [c for c in clusters if threshold > 0 and c["score"] >= threshold]
        if not passing:
            decision, selected = "ABSTAIN_BELOW_THRESHOLD", None
        else:
            decision, selected = "CREATE", max(passing, key=lambda c: c["score"])
    exported_clusters = parse_clusters(diag_row.get("clusters"))
    exported_selected = None
    if diag_row.get("selected_lower_tick") not in (None, ""):
        exported_selected = {"lower_tick": int(diag_row["selected_lower_tick"]),
                             "upper_tick": int(diag_row["selected_upper_tick"]),
                             "score": float(diag_row["selected_score"]),
                             "count": int(diag_row["selected_count"])}
    diffs = []
    if median != as_float(diag_row.get("median")): diffs.append("median")
    if hot_threshold != as_float(diag_row.get("hot_threshold")): diffs.append("hot_threshold")
    if clusters != exported_clusters: diffs.append("clusters")
    if decision != diag_row.get("decision"): diffs.append("decision")
    if selected != exported_selected: diffs.append("selected_cluster")
    return {"status": "DIFF" if diffs else "MATCH", "diffs": diffs,
            "decision": decision, "selected_cluster": selected,
            "best_candidate_score": max((c["score"] for c in clusters), default=0.0)}


def contiguous(values):
    values = sorted(values)
    return not values or values == list(range(values[0], values[-1] + 1))


def edge_set_difference(py_only, nt8_only, shared):
    """True only if every exclusive run is contiguous and touches a shared-hull edge."""
    if not (py_only or nt8_only) or not shared:
        return False
    lo, hi = min(shared), max(shared)
    for exclusive in (py_only, nt8_only):
        below = sorted(t for t in exclusive if t < lo)
        above = sorted(t for t in exclusive if t > hi)
        if any(lo <= t <= hi for t in exclusive):
            return False
        if below and (not contiguous(below) or below[-1] != lo - 1):
            return False
        if above and (not contiguous(above) or above[0] != hi + 1):
            return False
    return True


def classify_inputs(py_cells, nt8_cells):
    if py_cells is None or nt8_cells is None:
        return {"input_diff": "NOT_AVAILABLE", "py_only_ticks": [], "nt8_only_ticks": [],
                "py_only_vol": 0.0, "nt8_only_vol": 0.0,
                "n_shared_value_diffs": None, "shared_value_diffs": []}
    py_ticks, nt_ticks = set(py_cells), set(nt8_cells)
    py_only, nt_only = sorted(py_ticks - nt_ticks), sorted(nt_ticks - py_ticks)
    shared = sorted(py_ticks & nt_ticks)
    value_diffs = [[t, py_cells[t], nt8_cells[t]] for t in shared
                   if py_cells[t] != nt8_cells[t]]
    labels = []
    if py_only or nt_only:
        labels.append("EDGE_LEVEL_SET_DIFF" if edge_set_difference(py_only, nt_only, shared)
                      else "CELL_LEVEL_SET_DIFF")
    if value_diffs:
        labels.append("SHARED_CELL_VALUE_NOISE")
    return {"input_diff": "+".join(labels) if labels else "NONE",
            "py_only_ticks": py_only, "nt8_only_ticks": nt_only,
            "py_only_vol": sum(py_cells[t] for t in py_only),
            "nt8_only_vol": sum(nt8_cells[t] for t in nt_only),
            "n_shared_value_diffs": len(value_diffs), "shared_value_diffs": value_diffs}


def py_zone_ticks(zone):
    return (int(round(float(zone["bottom"]) / TICK_SIZE + 0.5)),
            int(round(float(zone["top"]) / TICK_SIZE - 0.5)))


def geometry_diff_ticks(py_zone, nt8_zone):
    py_lower, py_upper = py_zone_ticks(py_zone)
    return max(abs(py_lower - int(nt8_zone["lower_tick"])),
               abs(py_upper - int(nt8_zone["upper_tick"])))


def local_time_from_created_ms(created_ms):
    utc = dt.datetime.fromtimestamp(int(created_ms) / 1000.0, tz=dt.timezone.utc)
    local = utc.astimezone(dt.timezone(dt.timedelta(hours=CHART_UTC_OFFSET_HOURS)))
    return local.strftime("%Y-%m-%dT%H:%M:%S.") + "{:03d}".format(local.microsecond // 1000)


def local_time_from_block(block):
    if block.get("block_end_ns") is not None:
        return local_time_from_created_ms(int(block["block_end_ns"]) // 1_000_000)
    if block.get("created_ms") is not None:
        return local_time_from_created_ms(block["created_ms"])
    raise KeyError("block_end_ns")


def load_nt8_oracle(path):
    with path.open(encoding="utf-8", newline="") as fh:
        meta = fh.readline().rstrip("\n")
        rows = [r for r in csv.DictReader(fh) if r.get("event_type") == "ZONE_CREATED"]
    return meta, rows


def load_diag(path):
    with path.open(encoding="utf-8", newline="") as fh:
        meta = fh.readline().rstrip("\n")
        rows = list(csv.DictReader(fh))
    by_time, by_time_bar = defaultdict(list), defaultdict(list)
    for row in rows:
        by_time[row["bar_close_time"]].append(row)
        by_time_bar[(row["bar_close_time"], row["bar_index"])].append(row)
    duplicate_times = {k: len(v) for k, v in by_time.items() if len(v) > 1}
    duplicate_composite = {k: len(v) for k, v in by_time_bar.items() if len(v) > 1}
    if duplicate_composite:
        raise RuntimeError("claves NT8 (timestamp,bar_index) duplicadas: {}".format(len(duplicate_composite)))
    return meta, rows, by_time, by_time_bar, duplicate_times


def one_exact(index, key):
    matches = index.get(key, [])
    if len(matches) == 1: return matches[0], "DIRECT"
    if not matches: return None, "TIME_MATCH_NOT_FOUND"
    return None, "TIME_MATCH_AMBIGUOUS"


def load_py_all_blocks(path):
    payload = load_json(path)
    blocks = payload.get("block_trace", []) if isinstance(payload, dict) else payload
    by_time = defaultdict(list)
    for block in blocks:
        by_time[local_time_from_block(block)].append(block)
    duplicates = {k: len(v) for k, v in by_time.items() if len(v) > 1}
    return blocks, by_time, duplicates


def add_comparison(row, py_cells, diag_row):
    nt8_cells = parse_cells(diag_row.get("cells"))
    row.update(classify_inputs(py_cells, nt8_cells))
    clusters = parse_clusters(diag_row.get("clusters"))
    row.update({"py_n_cells": None if py_cells is None else len(py_cells),
                "nt8_n_cells": len(nt8_cells),
                "py_median": None if py_cells is None else median_upper(py_cells.values()),
                "nt8_median": as_float(diag_row.get("median")),
                "nt8_hot_threshold": as_float(diag_row.get("hot_threshold")),
                "nt8_threshold": as_float(diag_row.get("threshold")),
                "nt8_history_samples": as_int(diag_row.get("hist_samples")),
                "nt8_decision": diag_row.get("decision"),
                "nt8_best_candidate_score": max((c["score"] for c in clusters), default=0.0),
                "nt8_best_candidate_score_source": "clusters"})
    replay = replay_on_nt8_cells(diag_row, nt8_cells)
    row["algorithm_replay_status"] = replay["status"]
    row["algorithm_replay_diffs"] = replay["diffs"]


def build(args):
    gate = load_json(args.gate)
    diagnostics = gate["diagnostics"]
    residuals = {code: [d for d in diagnostics if d["code"] == code]
                 for code in EXPECTED_COUNTS}
    counts = {code: len(items) for code, items in residuals.items()}
    if counts != EXPECTED_COUNTS:
        raise RuntimeError("conteos del gate inesperados: {}".format(counts))
    py_zones = load_json(args.py_zones)
    py_zone_by_id = {str(z["id"]): z for z in py_zones}
    py_creation_by_zone = {}
    for block in load_json(args.py_creation_blocks):
        for zone_id in block.get("zone_ids", []):
            py_creation_by_zone[str(zone_id)] = block
    diag_meta, diag_rows, diag_by_time, diag_by_time_bar, duplicate_diag_times = load_diag(args.diag)
    _meta, nt8_zones = load_nt8_oracle(args.oracle)
    nt8_zone_by_id = {str(z["zone_id"]): z for z in nt8_zones}
    nt8_zone_by_time = defaultdict(list)
    for zone in nt8_zones:
        nt8_zone_by_time[zone["bar_close_time"]].append(zone)
    missing_py_ids = {str(d["nt8_id"]) for d in residuals["MISSING_IN_PYTHON"]}
    all_blocks, py_all_by_time, duplicate_py_times = None, {}, {}
    if args.py_all_blocks is not None:
        all_blocks, py_all_by_time, duplicate_py_times = load_py_all_blocks(args.py_all_blocks)
    rows, split_pairs = [], {}

    for d in residuals["GEOMETRY_DIFF"]:
        py_id, nt8_id = str(d["py_id"]), str(d["nt8_id"])
        py_zone, nt8_zone = py_zone_by_id.get(py_id), nt8_zone_by_id.get(nt8_id)
        row = {"gate_code": "GEOMETRY_DIFF", "py_id": py_id, "nt8_id": nt8_id,
               "event_group_id": "PY{}__NT8{}".format(py_id, nt8_id),
               "gate_detail": d.get("detail")}
        if py_zone is None or nt8_zone is None:
            row["evidence_level"] = "ZONE_NOT_FOUND"; rows.append(row); continue
        diag_row, evidence = one_exact(diag_by_time_bar,
                                       (nt8_zone["bar_close_time"], nt8_zone["bar_index"]))
        row["evidence_level"] = evidence
        row["geometry_diff_ticks"] = geometry_diff_ticks(py_zone, nt8_zone)
        if diag_row is not None:
            py_block = py_creation_by_zone.get(py_id)
            add_comparison(row, parse_cells(py_block.get("cells")) if py_block else None, diag_row)
        rows.append(row)

    for d in residuals["MISSING_IN_NT8"]:
        py_id = str(d["py_id"])
        py_zone, py_block = py_zone_by_id.get(py_id), py_creation_by_zone.get(py_id)
        row = {"gate_code": "MISSING_IN_NT8", "py_id": py_id, "nt8_id": None,
               "event_group_id": "PY{}".format(py_id), "matcher_rejection": "UNKNOWN"}
        if py_zone is None or py_block is None:
            row["evidence_level"] = "PY_ZONE_OR_BLOCK_NOT_FOUND"; rows.append(row); continue
        local_time = local_time_from_created_ms(py_zone["created_ms"])
        diag_row, evidence = one_exact(diag_by_time, local_time)
        row["evidence_level"] = evidence
        if diag_row is None:
            rows.append(row); continue
        add_comparison(row, parse_cells(py_block.get("cells")), diag_row)
        row["py_best_candidate_score"] = as_float(py_block.get("best_score"))
        row["py_threshold"] = as_float(py_block.get("threshold"))
        row["py_ratio"] = (row["py_best_candidate_score"] / row["py_threshold"]
                           if row["py_threshold"] else None)
        row["py_history_samples"] = as_int(py_block.get("history_samples",
                                                        py_block.get("n_history_scores")))
        if diag_row.get("decision") == "CREATE":
            selected = (as_int(diag_row.get("selected_lower_tick")),
                        as_int(diag_row.get("selected_upper_tick")))
            created = [z for z in nt8_zone_by_time.get(local_time, [])
                       if (int(z["lower_tick"]), int(z["upper_tick"])) == selected]
            if len(created) == 1:
                nt8_zone, nt8_id = created[0], str(created[0]["zone_id"])
                row["nt8_id"] = nt8_id
                row["event_group_id"] = "PY{}__NT8{}".format(py_id, nt8_id)
                gd = geometry_diff_ticks(py_zone, nt8_zone)
                ceiling = max(float(gate.get("summary", {}).get("tol_geom_ticks", 0)),
                              HARD_MATCHER_CEILING_TICKS)
                row["geometry_diff_ticks"] = gd
                row["matcher_candidacy_ceiling_ticks"] = ceiling
                row["nt8_id_also_missing_in_python"] = nt8_id in missing_py_ids
                row["matcher_rejection"] = ("GEOMETRY_CANDIDACY_CEILING" if gd > ceiling
                                            else "NOT_EXPLAINED_BY_GEOMETRY_CEILING")
                split_pairs[nt8_id] = py_id
            elif not created:
                row["matcher_rejection"] = "NT8_CREATED_ZONE_NOT_FOUND"
            else:
                row["matcher_rejection"] = "NT8_CREATED_ZONE_AMBIGUOUS"
        rows.append(row)

    for d in residuals["MISSING_IN_PYTHON"]:
        nt8_id = str(d["nt8_id"])
        nt8_zone = nt8_zone_by_id.get(nt8_id)
        row = {"gate_code": "MISSING_IN_PYTHON", "py_id": None, "nt8_id": nt8_id,
               "event_group_id": "NT8{}".format(nt8_id)}
        if nt8_id in split_pairs:
            py_id = split_pairs[nt8_id]
            row.update({"py_id": py_id, "event_group_id": "PY{}__NT8{}".format(py_id, nt8_id),
                        "evidence_level": "LINKED_MATCHER_SPLIT",
                        "duplicate_gate_row_of": "MISSING_IN_NT8:PY{}".format(py_id),
                        "matcher_rejection": "GEOMETRY_CANDIDACY_CEILING"})
            rows.append(row); continue
        if nt8_zone is None:
            row["evidence_level"] = "NT8_ZONE_NOT_FOUND"; rows.append(row); continue
        diag_row, evidence = one_exact(diag_by_time_bar,
                                       (nt8_zone["bar_close_time"], nt8_zone["bar_index"]))
        if diag_row is None:
            row["evidence_level"] = evidence; rows.append(row); continue
        if all_blocks is None:
            row["evidence_level"] = "NOT_YET_AVAILABLE"
            row["required_input"] = "Python all-block trace"
            rows.append(row); continue
        py_block, evidence = one_exact(py_all_by_time, nt8_zone["bar_close_time"])
        row["evidence_level"] = evidence
        if py_block is not None:
            add_comparison(row, parse_cells(py_block.get("cells")), diag_row)
            row["py_best_candidate_score"] = as_float(py_block.get("best_score"))
            row["py_threshold"] = as_float(py_block.get("threshold"))
            row["py_history_samples"] = as_int(py_block.get("history_samples",
                                                            py_block.get("n_history_scores")))
            row["py_decision"] = py_block.get("decision")
        rows.append(row)

    if len(rows) != 124:
        raise RuntimeError("el censo debe preservar 124 filas; obtuvo {}".format(len(rows)))
    result = {"scope": "target_free_preholdout", "gate_status_unchanged": gate.get("gate", "FAIL"),
              "gate_row_counts": counts, "n_gate_residual_rows": len(rows),
              "n_unique_residual_event_groups": len({r["event_group_id"] for r in rows}),
              "matcher_split_pairs": [{"py_id": py_id, "nt8_id": nt8_id}
                                      for nt8_id, py_id in sorted(split_pairs.items(), key=lambda x: int(x[0]))],
              "n_nt8_diag_blocks": len(diag_rows),
              "n_python_all_blocks": None if all_blocks is None else len(all_blocks),
              "block_count_difference": None if all_blocks is None else len(all_blocks) - len(diag_rows),
              "nt8_diag_duplicate_timestamp_count": len(duplicate_diag_times),
              "nt8_diag_duplicate_timestamp_rows": sum(duplicate_diag_times.values()),
              "python_all_block_duplicate_timestamp_count": len(duplicate_py_times),
              "nt8_history_samples_exact_below_min":
                  "hist_samples_semantics=actual_even_below_min" in diag_meta,
              "evidence_counts": dict(Counter(r.get("evidence_level") for r in rows)),
              "input_diff_counts": dict(Counter(r.get("input_diff") for r in rows if r.get("input_diff"))),
              "algorithm_replay_counts": dict(Counter(r.get("algorithm_replay_status") for r in rows
                                                       if r.get("algorithm_replay_status"))),
              "rows": rows}
    return result


def csv_value(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False) if isinstance(value, (list, dict)) else value


def write_outputs(result, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = out_dir / "censo_124_residuos.json", out_dir / "censo_124_residuos.csv"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    columns = sorted({key for row in result["rows"] for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns); writer.writeheader()
        for row in result["rows"]:
            writer.writerow({key: csv_value(row.get(key)) for key in columns})
    return json_path, csv_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--diag", type=Path, default=DEFAULT_DIAG)
    parser.add_argument("--py-zones", type=Path, default=DEFAULT_PY_ZONES)
    parser.add_argument("--py-creation-blocks", type=Path, default=DEFAULT_PY_CREATION_BLOCKS)
    parser.add_argument("--py-all-blocks", type=Path, default=None,
                        help="all_blocks.json producido por avolclusterpoi_tracedump_full_runner.py")
    parser.add_argument("--out-dir", type=Path, default=HERE)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    result = build(args)
    json_path, csv_path = write_outputs(result, args.out_dir)
    print("gate_rows=", result["n_gate_residual_rows"])
    print("unique_event_groups=", result["n_unique_residual_event_groups"])
    print("split_pairs=", result["matcher_split_pairs"])
    print("evidence_counts=", result["evidence_counts"])
    print("diag_duplicate_timestamps=", result["nt8_diag_duplicate_timestamp_count"])
    print("algorithm_replay_counts=", result["algorithm_replay_counts"])
    print("json=", json_path); print("csv=", csv_path)


if __name__ == "__main__":
    main()
