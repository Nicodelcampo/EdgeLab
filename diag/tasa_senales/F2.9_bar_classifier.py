# -*- coding: utf-8 -*-
"""F2.9 — BigTrap2 as a creator-bar classifier.

Additive runner. Reuses F2.7 race/lifecycle/load/firewall.
Includes r_i=0 in session means. Does not dump ties into double_censor.
Contrasts are paired by session.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_F27_PATH = REPO_PATH / "diag" / "tasa_senales" / "F2.7_nulo_reflexion_local.py"
_spec = importlib.util.spec_from_file_location("f27_nrl", _F27_PATH)
f27 = importlib.util.module_from_spec(_spec)
sys.modules["f27_nrl"] = f27
_spec.loader.exec_module(f27)

construir_universo_zonas = f27.construir_universo_zonas
construir_reflejo = f27.construir_reflejo
first_passage_race = f27.first_passage_race
hac_bartlett_ic = f27.hac_bartlett_ic
dias_research = f27.dias_research
data_root = f27.data_root
git_head = f27.git_head
git_dirty = f27.git_dirty
north_star_body_sha256 = f27.north_star_body_sha256
corte_del_sello = f27.corte_del_sello
parquet_file_sha256 = f27.parquet_file_sha256
construir_bar_start_ends = f27.construir_bar_start_ends
INDICADOR = f27.INDICADOR
REGISTRY = f27.REGISTRY
TZ_CHART = f27.TZ_CHART
LEAD_DAYS = f27.LEAD_DAYS
bars_mod = f27.bars_mod
ticks_mod = f27.ticks_mod
pd = f27.pd
sesiones_de_barras = f27.sesiones_de_barras
session_date_ct = f27.session_date_ct

from edgelab.research.f29.labels import (  # noqa: E402
    decide_labels, probe_interval, probe_side, wick_fracs,
)

SCHEMA = "bigtrap2_f29_bar_classifier_v0"
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_f29_bar_classifier_v0.json"
NORTH_STAR_BODY_SHA256_EXPECTED = (
    "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"
)
RESEARCH_END_INCLUSIVE = "2026-06-30"
REQUIRED_SOURCE_SESSIONS = 201
PARQUET_HASHES_EXPECTED = {
    "6E_12-25_ticks.parquet": "ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336",
    "6E_03-26_ticks.parquet": "b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76",
    "6E_06-26_ticks.parquet": "124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1",
    "6E_09-26_ticks.parquet": "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4",
}


def spec_sha256() -> str:
    return hashlib.sha256(SPEC_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def classify_category(cat: str) -> str:
    if cat == "real_first":
        return "real_first"
    if cat == "mirror_first":
        return "mirror_first"
    if cat in {"empate_tecnico", "same_bar_needs_tick_tiebreak"}:
        return "empate_tecnico"
    return "double_censoring"


def session_mean_map(pairs):
    by_session = {}
    for session, r_i, _cat in pairs:
        by_session.setdefault(session, []).append(float(r_i))
    return {session: float(np.mean(values)) for session, values in by_session.items() if values}


def metrics_from_pairs(pairs):
    counts = Counter(classify_category(cat) for _s, _r, cat in pairs)
    n = len(pairs)
    n_resolved = counts["real_first"] + counts["mirror_first"]
    means = session_mean_map(pairs)
    if not means:
        return dict(
            n_bars=n, n_sessions=0, n_resolved=n_resolved,
            frac_resolved=(n_resolved / n) if n else 0.0,
            frac_empate_tecnico=(counts["empate_tecnico"] / n) if n else 0.0,
            real_first=counts["real_first"], mirror_first=counts["mirror_first"],
            empate_tecnico=counts["empate_tecnico"], double_censoring=counts["double_censoring"],
            delta=None, se_hac=None, ci95_lower=None, ci95_upper=None, mde=None,
            abstain_inferencia=True,
        )
    ic = hac_bartlett_ic([means[s] for s in sorted(means)])
    return dict(
        n_bars=n, n_sessions=len(means), n_resolved=n_resolved,
        frac_resolved=(n_resolved / n) if n else 0.0,
        frac_empate_tecnico=(counts["empate_tecnico"] / n) if n else 0.0,
        real_first=counts["real_first"], mirror_first=counts["mirror_first"],
        empate_tecnico=counts["empate_tecnico"], double_censoring=counts["double_censoring"],
        delta=ic.get("mean"), se_hac=ic.get("se_hac"),
        ci95_lower=ic.get("ci95_lower"), ci95_upper=ic.get("ci95_upper"),
        mde=ic.get("mde"), abstain_inferencia=bool(ic.get("abstain_inferencia")),
    )


def paired_contrast(pairs_a, pairs_b):
    a = session_mean_map(pairs_a)
    b = session_mean_map(pairs_b)
    common = sorted(set(a) & set(b))
    if not common:
        return dict(n_sessions=0, delta=None, se_hac=None, ci95_lower=None, ci95_upper=None, match_rate=0.0)
    diffs = [a[s] - b[s] for s in common]
    ic = hac_bartlett_ic(diffs)
    denom = max(len(set(a) | set(b)), 1)
    return dict(
        n_sessions=len(common),
        delta=ic.get("mean"), se_hac=ic.get("se_hac"),
        ci95_lower=ic.get("ci95_lower"), ci95_upper=ic.get("ci95_upper"),
        match_rate=len(common) / denom,
        abstain_inferencia=bool(ic.get("abstain_inferencia")),
    )


def quintile(values, value):
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0 or not math.isfinite(value):
        return 0
    edges = np.unique(np.quantile(arr, [0.2, 0.4, 0.6, 0.8]))
    return int(np.searchsorted(edges, value, side="right"))


def race_probe(close_t, high_t, low_t, bar, n_bars, tk_price_ticks, bar_start_ends):
    side = probe_side(int(high_t[bar]), int(low_t[bar]), int(close_t[bar]))
    lo, hi = probe_interval(int(close_t[bar]), side)
    zona = dict(lo_tick=lo, hi_tick=hi, is_bull=(side == "bull"), created_bar=int(bar))
    reflejo = construir_reflejo(zona, close_t)
    if not reflejo["is_eligible"]:
        return None
    race = first_passage_race(
        zona, reflejo, int(bar), high_t, low_t, close_t, n_bars,
        tk_price_ticks=tk_price_ticks, bar_start_ends=bar_start_ends,
    )
    return race["r_i"], race["category"], side, lo, hi


def trap_bars(csv_lines):
    found = set()
    for line in csv_lines or []:
        parts = line.split("|", 3)
        if len(parts) < 4 or parts[2] != "TRAP":
            continue
        fields = dict(kv.split("=", 1) for kv in parts[3].split(";") if "=" in kv)
        if "bar" in fields:
            found.add(int(fields["bar"]))
    return found


def portrait_contrast(rows, key):
    diffs = []
    by_session = {}
    for row in rows:
        by_session.setdefault(row["session"], {"c": [], "n": []})
        bucket = "c" if row["creator"] else "n"
        if row[key] is not None and math.isfinite(row[key]):
            by_session[row["session"]][bucket].append(row[key])
    for session in sorted(by_session):
        creators = by_session[session]["c"]
        others = by_session[session]["n"]
        if creators and others:
            diffs.append(float(np.mean(creators) - np.mean(others)))
    if not diffs:
        return dict(n_sessions=0, delta=None, ci95_lower=None, ci95_upper=None)
    ic = hac_bartlett_ic(diffs)
    return dict(n_sessions=len(diffs), delta=ic.get("mean"), ci95_lower=ic.get("ci95_lower"), ci95_upper=ic.get("ci95_upper"))


def make_serializable(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return 0.0 if math.isnan(value) or math.isinf(value) else value
    if isinstance(obj, float):
        return 0.0 if math.isnan(obj) or math.isinf(obj) else obj
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(x) for x in obj]
    return obj


def correr_formal():
    if git_dirty():
        print("ABSTAIN_PROVENANCE: dirty tree")
        return 5
    ns_hash = north_star_body_sha256()
    if ns_hash != NORTH_STAR_BODY_SHA256_EXPECTED:
        print("ABSTAIN_PROVENANCE: NORTH_STAR mismatch")
        return 3
    head_start = git_head()
    dias, info = dias_research()
    por_arch = {}
    for day in dias:
        por_arch.setdefault(day["archivo"], []).append(day["fecha"])
    plan = [(arch, sorted(dates)) for arch, dates in sorted(por_arch.items())]
    corte = corte_del_sello()
    corte_ns = int(corte.value)

    for arch, _dates in plan:
        path = data_root() / "nt8" / "6E" / arch
        if not path.exists():
            print("ABSTAIN_PROVENANCE: missing %s" % path)
            return 6
        actual = parquet_file_sha256(path)
        expected = PARQUET_HASHES_EXPECTED.get(arch)
        if expected and actual != expected:
            print("ABSTAIN_PROVENANCE: hash mismatch %s" % arch)
            return 7

    pairs = {key: [] for key in ("K0", "S0", "S1", "S2", "N0", "F0")}
    persist = {offset: [] for offset in (-2, -1, 1, 2)}
    residual_pairs = []
    portraits = []
    sessions_seen = set()

    for arch, fechas in plan:
        fechas_research = [f for f in fechas if f <= RESEARCH_END_INCLUSIVE]
        if not fechas_research:
            continue
        print("Procesando %s (%d sesiones)" % (arch, len(fechas_research)), flush=True)
        ini = pd.Timestamp(fechas_research[0] + " 00:00:00", tz="America/Chicago") - pd.Timedelta(days=LEAD_DAYS)
        fin_contrato = pd.Timestamp(fechas_research[-1] + " 00:00:00", tz="America/Chicago") + pd.Timedelta(days=1)
        fin = min(fin_contrato.tz_convert("UTC"), corte)
        tk = ticks_mod.load_canonical_parquet(
            str(data_root() / "nt8" / "6E" / arch),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value),
        )
        if int(np.max(tk.ts_ns)) >= corte_ns:
            print("FIREWALL VIOLATED %s" % arch)
            return 8
        bars = bars_mod.build_time_bars(tk, 1)
        high_t = np.asarray(bars.high_t)
        low_t = np.asarray(bars.low_t)
        close_t = np.asarray(bars.close_t)
        volume = np.asarray(bars.volume, dtype=np.float64)
        n_bars = len(bars)
        fp = bars_mod.build_footprints(tk, bars)
        result = REGISTRY[INDICADOR].run(tk, bars, fp, chart_tz=TZ_CHART)
        fechas_disponibles = sorted(set(session_date_ct(int(ns // 1_000_000)) for ns in bars.start_ns))
        _ses, rango = sesiones_de_barras(np.asarray(bars.end_ns), fechas_disponibles)
        universo, creadoras = construir_universo_zonas(
            result.get("zones") or [], _ses, rango, fechas_research, tk.tick_size, n_bars,
        )
        trap = trap_bars(result.get("csv_lines"))
        tk_prices = np.asarray(tk.price_ticks, dtype=np.int64)
        bar_slices = construir_bar_start_ends(np.asarray(tk.ts_ns), np.asarray(bars.start_ns), np.asarray(bars.end_ns))
        kernel_by_bar = {int(z["created_bar"]): z for z in universo}

        for session in fechas_research:
            if session not in rango:
                continue
            sessions_seen.add(session)
            i0, i1 = rango[session]
            session_bars = list(range(i0, i1 + 1))
            feats = []
            for bar in session_bars:
                w = wick_fracs(int(high_t[bar]), int(low_t[bar]), int(close_t[bar]))
                w.update(bar=bar, volume=float(volume[bar]), creator=(bar in creadoras))
                feats.append(w)
            ranges = [f["range_ticks"] for f in feats]
            closes = [f["close_loc"] for f in feats]
            vols = [f["volume"] for f in feats]
            vol_med = float(np.median(vols)) if vols else 0.0
            for feat in feats:
                feat["rq"] = quintile(ranges, feat["range_ticks"])
                feat["cq"] = quintile(closes, feat["close_loc"])
                feat["vq"] = quintile(vols, feat["volume"])
                feat["S0"] = feat["range_ticks"] >= 3 and max(feat["upper_wick_frac"], feat["lower_wick_frac"]) >= 0.30
                feat["S1"] = feat["S0"] and feat["volume"] >= vol_med
                feat["S2"] = feat["S1"] and not (0.40 < feat["close_loc"] < 0.60)
                portraits.append({
                    "session": session, "creator": feat["creator"],
                    "range_ticks": feat["range_ticks"], "close_loc": feat["close_loc"],
                    "log_volume": math.log1p(max(feat["volume"], 0.0)),
                    "upper_wick_frac": feat["upper_wick_frac"],
                    "lower_wick_frac": feat["lower_wick_frac"],
                })

            raced = {}

            def ensure_race(bar):
                if bar not in raced:
                    raced[bar] = race_probe(close_t, high_t, low_t, bar, n_bars, tk_prices, bar_slices)
                return raced[bar]

            noncreators = [f for f in feats if not f["creator"]]
            for feat in feats:
                raced_bar = ensure_race(feat["bar"])
                if raced_bar is None:
                    continue
                r_i, cat, _side, _lo, _hi = raced_bar
                item = (session, r_i, cat)
                if feat["creator"]:
                    pairs["K0"].append(item)
                if feat["S0"]:
                    pairs["S0"].append(item)
                if feat["S1"]:
                    pairs["S1"].append(item)
                if feat["S2"]:
                    pairs["S2"].append(item)
                if feat["bar"] in trap:
                    pairs["F0"].append(item)

            for feat in feats:
                if not feat["creator"]:
                    continue
                candidates = [
                    other for other in noncreators
                    if other["rq"] == feat["rq"] and other["cq"] == feat["cq"] and other["vq"] == feat["vq"]
                ]
                if not candidates:
                    continue
                match = min(candidates, key=lambda other: (abs(other["bar"] - feat["bar"]), other["bar"]))
                raced_match = ensure_race(match["bar"])
                if raced_match is None:
                    continue
                pairs["N0"].append((session, raced_match[0], raced_match[1]))

                kernel_zone = kernel_by_bar.get(feat["bar"])
                raced_creator = ensure_race(feat["bar"])
                if kernel_zone is not None and raced_creator is not None:
                    reflejo = construir_reflejo(kernel_zone, close_t)
                    if reflejo["is_eligible"]:
                        kernel_race = first_passage_race(
                            kernel_zone, reflejo, feat["bar"], high_t, low_t, close_t, n_bars,
                            tk_price_ticks=tk_prices, bar_start_ends=bar_slices,
                        )
                        residual_pairs.append((session, float(kernel_race["r_i"]) - float(raced_creator[0]), kernel_race["category"]))

                for offset in persist:
                    neighbor = feat["bar"] + offset
                    if neighbor < i0 or neighbor > i1:
                        continue
                    raced_n = ensure_race(neighbor)
                    if raced_n is not None:
                        persist[offset].append((session, raced_n[0], raced_n[1]))

    if len(sessions_seen) != REQUIRED_SOURCE_SESSIONS:
        print("FAIL-CLOSED: sessions=%d" % len(sessions_seen))
        return 9

    rungs = {name: metrics_from_pairs(items) for name, items in pairs.items()}
    contrasts = {
        "K0_minus_S1": paired_contrast(pairs["K0"], pairs["S1"]),
        "K0_minus_N0": paired_contrast(pairs["K0"], pairs["N0"]),
        "F0_minus_S1": paired_contrast(pairs["F0"], pairs["S1"]),
        "K0_minus_F0": paired_contrast(pairs["K0"], pairs["F0"]),
    }
    zone_residual = metrics_from_pairs(residual_pairs)
    persistence = {
        ("+%d" % offset if offset > 0 else "%d" % offset): metrics_from_pairs(items)
        for offset, items in persist.items()
    }
    portrait = {
        key: portrait_contrast(portraits, key)
        for key in ("range_ticks", "close_loc", "log_volume", "upper_wick_frac", "lower_wick_frac")
    }
    report = {
        "rungs": rungs,
        "contrasts": contrasts,
        "zone_residual": zone_residual,
        "persistence": persistence,
        "underpowered": False,
    }
    labels = decide_labels(report)
    payload = {
        "schema_version": SCHEMA,
        "status": "FORMAL_RUN_COMPLETE",
        "head_start": head_start,
        "head_end": git_head(),
        "dirty_start": False,
        "dirty_end": git_dirty(),
        "north_star_body_sha256": ns_hash,
        "spec_sha256": spec_sha256(),
        "n_sessions": len(sessions_seen),
        "family_a_portrait": portrait,
        "family_b_rungs": rungs,
        "family_b_contrasts": contrasts,
        "family_c_zone_residual": zone_residual,
        "family_d_persistence": persistence,
        "family_e_included_in_rungs": True,
        "decision_labels": labels,
        "zeros_included_in_session_mean": True,
        "ties_not_dumped_into_double_censor": True,
        "contrasts_paired_by_session": True,
        "outcomes_accessed": False,
        "pnl_accessed": False,
        "universe_filter_report": info,
    }
    if git_dirty() or git_head() != head_start:
        print("ABSTAIN_PROVENANCE: tree moved")
        return 5
    serializable = make_serializable(payload)
    raw = json.dumps(serializable, indent=2, sort_keys=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    out = REPO_PATH / "diag" / "tasa_senales" / ("F2.9_formal_%s.json" % digest)
    out.write_text(raw + "\n", encoding="utf-8")
    assert out.exists(), f"Failed to write artifact: {out}"
    print(json.dumps({"labels": labels, "rungs": {k: {"n": v["n_bars"], "delta": v["delta"], "ci": [v["ci95_lower"], v["ci95_upper"]]} for k, v in rungs.items()}, "artifact": str(out)}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args(argv)
    if args.formal:
        return correr_formal()
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
