# -*- coding: utf-8 -*-
"""F2.10 — Regime window after an extreme bar (S1).

Additive runner. Reuses F2.7 race/lifecycle/load/firewall and F2.9 matching/metrics.
Includes r_i=0 in session means.
P_mode evaluated on the evaluated bar, not on the stamp bar.
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

_F29_PATH = REPO_PATH / "diag" / "tasa_senales" / "F2.9_bar_classifier.py"
_f29_spec = importlib.util.spec_from_file_location("f29_runner", _F29_PATH)
f29 = importlib.util.module_from_spec(_f29_spec)
sys.modules["f29_runner"] = f29
_f29_spec.loader.exec_module(f29)

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

classify_category = f29.classify_category
session_mean_map = f29.session_mean_map
metrics_from_pairs = f29.metrics_from_pairs
paired_contrast = f29.paired_contrast
quintile = f29.quintile
race_probe = f29.race_probe
make_serializable = f29.make_serializable

from edgelab.research.f29.labels import probe_interval, probe_side, wick_fracs  # noqa: E402
from edgelab.research.f210.labels import decide_labels, is_s1, is_t1  # noqa: E402

SCHEMA = "bigtrap2_f210_regime_window_v0"
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_f210_regime_window_v0.json"
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

    arms_pairs = {
        key: [] for key in (
            "T1_all", "T1_not_S1", "T1_and_S1", "S1_isolated",
            "P1", "T1_after_K0", "T1_after_S1", "T2", "T_minus1", "P_minus1"
        )
    }
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
        tk_prices = np.asarray(tk.price_ticks, dtype=np.int64)
        bar_slices = construir_bar_start_ends(np.asarray(tk.ts_ns), np.asarray(bars.start_ns), np.asarray(bars.end_ns))

        for session in fechas_research:
            if session not in rango:
                continue
            sessions_seen.add(session)
            i0, i1 = rango[session]
            session_bars = list(range(i0, i1 + 1))
            feats = {}
            feats_list = []
            for bar in session_bars:
                w = wick_fracs(int(high_t[bar]), int(low_t[bar]), int(close_t[bar]))
                w.update(bar=bar, volume=float(volume[bar]), creator=(bar in creadoras))
                feats_list.append(w)

            ranges = [f["range_ticks"] for f in feats_list]
            closes = [f["close_loc"] for f in feats_list]
            vols = [f["volume"] for f in feats_list]
            vol_med = float(np.median(vols)) if vols else 0.0

            for f in feats_list:
                f["rq"] = quintile(ranges, f["range_ticks"])
                f["cq"] = quintile(closes, f["close_loc"])
                f["vq"] = quintile(vols, f["volume"])
                f["is_s1"] = is_s1(f["range_ticks"], f["upper_wick_frac"], f["lower_wick_frac"], f["volume"], vol_med)
                feats[f["bar"]] = f

            s1_bars = {b for b, f in feats.items() if f["is_s1"]}
            k0_bars = {b for b, f in feats.items() if f["creator"]}
            non_s1_list = [f for f in feats.values() if not f["is_s1"]]

            raced = {}

            def ensure_race(bar):
                if bar not in raced:
                    raced[bar] = race_probe(close_t, high_t, low_t, bar, n_bars, tk_prices, bar_slices)
                return raced[bar]

            for bar in session_bars:
                f = feats[bar]
                # T1_all / T1_after_S1: bar - 1 is S1
                if is_t1(bar, s1_bars, i0, i1):
                    r_item = ensure_race(bar)
                    if r_item is not None:
                        item = (session, r_item[0], r_item[1])
                        arms_pairs["T1_all"].append(item)
                        arms_pairs["T1_after_S1"].append(item)
                        if not f["is_s1"]:
                            arms_pairs["T1_not_S1"].append(item)
                        else:
                            arms_pairs["T1_and_S1"].append(item)

                # S1_isolated: bar is S1 and bar - 1 is not S1
                if f["is_s1"]:
                    prev_b = bar - 1
                    if prev_b < i0 or prev_b not in s1_bars:
                        r_item = ensure_race(bar)
                        if r_item is not None:
                            arms_pairs["S1_isolated"].append((session, r_item[0], r_item[1]))

                # T1_after_K0: bar - 1 is K0
                prev_b = bar - 1
                if i0 <= prev_b <= i1 and prev_b in k0_bars:
                    r_item = ensure_race(bar)
                    if r_item is not None:
                        arms_pairs["T1_after_K0"].append((session, r_item[0], r_item[1]))

                # T2: bar - 2 is S1
                prev2_b = bar - 2
                if i0 <= prev2_b <= i1 and prev2_b in s1_bars:
                    r_item = ensure_race(bar)
                    if r_item is not None:
                        arms_pairs["T2"].append((session, r_item[0], r_item[1]))

                # T_minus1: bar + 1 is S1
                next_b = bar + 1
                if i0 <= next_b <= i1 and next_b in s1_bars:
                    r_item = ensure_race(bar)
                    if r_item is not None:
                        arms_pairs["T_minus1"].append((session, r_item[0], r_item[1]))

            # Placebos matching P1 and P_minus1
            for s_bar in sorted(s1_bars):
                s_feat = feats[s_bar]
                candidates = [
                    other for other in non_s1_list
                    if other["rq"] == s_feat["rq"] and other["cq"] == s_feat["cq"] and other["vq"] == s_feat["vq"]
                ]
                if not candidates:
                    continue
                match = min(candidates, key=lambda other: (abs(other["bar"] - s_bar), other["bar"]))
                m_bar = match["bar"]

                p1_bar = m_bar + 1
                if i0 <= p1_bar <= i1:
                    r_item = ensure_race(p1_bar)
                    if r_item is not None:
                        arms_pairs["P1"].append((session, r_item[0], r_item[1]))

                pm1_bar = m_bar - 1
                if i0 <= pm1_bar <= i1:
                    r_item = ensure_race(pm1_bar)
                    if r_item is not None:
                        arms_pairs["P_minus1"].append((session, r_item[0], r_item[1]))

    if len(sessions_seen) != REQUIRED_SOURCE_SESSIONS:
        print("FAIL-CLOSED: sessions=%d" % len(sessions_seen))
        return 9

    arms_metrics = {name: metrics_from_pairs(items) for name, items in arms_pairs.items()}
    contrasts = {
        "T1_not_S1_minus_P1": paired_contrast(arms_pairs["T1_not_S1"], arms_pairs["P1"]),
        "T1_and_S1_minus_S1_isolated": paired_contrast(arms_pairs["T1_and_S1"], arms_pairs["S1_isolated"]),
        "T1_after_K0_minus_T1_after_S1": paired_contrast(arms_pairs["T1_after_K0"], arms_pairs["T1_after_S1"]),
        "T_minus1_minus_P_minus1": paired_contrast(arms_pairs["T_minus1"], arms_pairs["P_minus1"]),
    }
    report = {
        "arms": arms_metrics,
        "contrasts": contrasts,
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
        "arms": arms_metrics,
        "contrasts": contrasts,
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
    out = REPO_PATH / "diag" / "tasa_senales" / ("F2.10_formal_%s.json" % digest)
    out.write_text(raw + "\n", encoding="utf-8")
    assert out.exists(), f"Failed to write artifact: {out}"
    print(json.dumps({"labels": labels, "arms": {k: {"n": v["n_bars"], "delta": v["delta"], "ci": [v["ci95_lower"], v["ci95_upper"]]} for k, v in arms_metrics.items()}, "artifact": str(out)}, indent=2))
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
