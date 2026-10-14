"""Target-free aggregate closeout. No provider calls, ticks, labels or models."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def normalized_states(counts):
    """Sparse zero serialization is equivalent, but undeclared states are not."""
    universe = ("A_ONLY", "E_ONLY", "BOTH", "NEITHER", "UNKNOWN")
    if set(counts) - set(universe):
        raise ValueError("undeclared state")
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("invalid state count")
    return {k: counts.get(k, 0) for k in universe}


def run(raw, ops, out):
    raw, ops, out = map(Path, (raw, ops, out))
    out.mkdir(parents=True, exist_ok=True)
    data = (raw / "a-support-receipt.json").read_bytes()
    r = json.loads(data)
    boot = json.loads((raw / "boot-receipt.json").read_bytes())
    previous = json.loads((ops / "GC_AE_HISTORY_RECEIPT.json").read_bytes())
    names = r["conditions_in_bit_order"]
    assert len(names) == 5 and len(set(names)) == 5
    states = ["A_ONLY", "E_ONLY", "BOTH", "NEITHER", "UNKNOWN"]
    assert all(r[k] is False for k in (
        "evaluation_read", "outcomes_requested", "outcomes_computed",
        "thresholds_changed", "models_fitted", "new_calibration",
        "dataset_quality_audit", "raw_exported", "holdout_opened",
        "pnl", "canonical_brain_written"))
    assert hashlib.sha256(data).hexdigest() == boot["a_support_receipt_sha256"]
    old = {s["trade_date"]: s for s in previous["training_sessions"]}
    rows, session_rows, cell_rows = [], [], []
    for scope, census in [("ALL_TRAINING", r["total_training"])] + [
        (s["trade_date"], s) for s in r["sessions"]
    ]:
        assert census["observed_anchors"] == sum(census["state_counts"].values())
        for key, c in census["cells"].items():
            masks = c["joint_condition_mask_counts"]
            assert len(masks) == 32 and sum(masks) == c["eligible_anchors"]
            assert masks[-1] == c["absorption_conjunction_anchors"]
            # Enumerate truth tuples, independent of runner's bitmask predicate.
            for mask, n in enumerate(masks):
                flags = tuple((mask // (2 ** j)) % 2 for j in range(5))
                rows.append(dict(scope=scope, phase_direction=key, mask=mask,
                                 flags="".join(map(str, flags)), anchors=n))
            for j, name in enumerate(names):
                passing = sum(n for mask, n in enumerate(masks)
                              if (mask // (2 ** j)) % 2)
                other4 = sum(n for mask, n in enumerate(masks)
                             if sum((mask // (2 ** k)) % 2
                                    for k in range(5) if k != j) == 4)
                assert passing == c["condition_counts"][name]
                assert other4 == c["passes_all_other_conditions"][name]
                cell_rows.append(dict(scope=scope, phase_direction=key,
                    condition=name, eligible_anchors=c["eligible_anchors"],
                    individual_pass=passing, passes_other_four=other4,
                    full_conjunction=masks[-1]))
        eligible = sum(c["eligible_anchors"] for c in census["cells"].values())
        full = sum(c["absorption_conjunction_anchors"] for c in census["cells"].values())
        assert eligible == census["observed_anchors"] - census["state_counts"]["UNKNOWN"]
        assert full == census["state_counts"]["A_ONLY"] + census["state_counts"]["BOTH"]
        if scope != "ALL_TRAINING":
            prior = old[scope]
            assert prior["ticks"] == census["ticks"]
            assert prior["observed_anchors"] == census["observed_anchors"]
            assert normalized_states(prior["state_counts_before_labels"]) == normalized_states(census["state_counts"])
            session_rows.append(dict(trade_date=scope, ticks=census["ticks"],
                observed_anchors=census["observed_anchors"],
                eligible_anchors=eligible, **census["state_counts"]))
    df = pd.DataFrame(cell_rows)
    assert not df.duplicated(["scope", "phase_direction", "condition"]).any()
    totals = df[df.scope == "ALL_TRAINING"].groupby("condition", sort=False)[
        ["individual_pass", "passes_other_four"]].sum().reindex(names)
    known = sum(r["total_training"]["state_counts"][k] for k in states if k != "UNKNOWN")
    full = r["total_training"]["state_counts"]["A_ONLY"] + r["total_training"]["state_counts"]["BOTH"]
    assert sum(s["ticks"] for s in r["sessions"]) == r["total_ticks"]
    masks_df = pd.DataFrame(rows)
    assert not masks_df.duplicated(["scope", "phase_direction", "mask"]).any()
    assert not pd.DataFrame(session_rows).duplicated(["trade_date"]).any()
    for key in r["total_training"]["cells"]:
        total_masks = masks_df[(masks_df.scope == "ALL_TRAINING") &
                              (masks_df.phase_direction == key)].anchors.to_list()
        per_session = masks_df[(masks_df.scope != "ALL_TRAINING") &
                              (masks_df.phase_direction == key)].groupby("mask").anchors.sum().to_list()
        assert total_masks == per_session
    cell_ranks = []
    for (scope, key), group in df.groupby(["scope", "phase_direction"]):
        maximum = int(group.passes_other_four.max())
        leaders = group[group.passes_other_four == maximum].condition.to_list()
        cell_ranks.append(dict(scope=scope, phase_direction=key,
                               largest_omission_support=maximum, leaders=leaders))
    session_ranks = []
    for scope, group in df.groupby("scope"):
        grouped = group.groupby("condition").passes_other_four.sum()
        session_ranks.append(dict(scope=scope, leaders=grouped[
            grouped == grouped.max()].index.to_list(), counts=grouped.to_dict()))
    assert all(x["leaders"] == ["CURRENT_PRESSURE_HIGH"] for x in session_ranks)
    combined_ranks = [x for x in cell_ranks if x["scope"] == "ALL_TRAINING"]
    assert all(x["leaders"] == ["CURRENT_PRESSURE_HIGH"] for x in combined_ranks)
    evidence = dict(
        schema="gc_a_support_analysis_v1",
        status="TRAINING_TARGET_FREE_SUPPORT_DIAGNOSED_NOT_EDGE",
        receipt_sha256=hashlib.sha256(data).hexdigest(),
        plan_sha256=r["plan_sha256"], calibration_sha256=r["calibration_sha256"],
        window=[s["trade_date"] for s in r["sessions"]],
        total_ticks=r["total_ticks"], observed_anchors=r["total_training"]["observed_anchors"],
        eligible_anchors=known, state_counts=r["total_training"]["state_counts"],
        full_conjunction_anchors=full, full_conjunction_percent_of_eligible=100*full/known,
        condition_counts=totals.individual_pass.to_dict(),
        passes_all_other_conditions=totals.passes_other_four.to_dict(),
        conditional_retention={name: full/int(totals.loc[name, "passes_other_four"])
                               for name in names},
        scope="Overlapping clock anchors, not independent events; original six training dates only",
        independent_check="All 32 masks recounted by integer truth-tuple enumeration; date/cell totals crossfoot",
        prior_training_exact_after_zero_normalization=True,
        profile_resolution="Nested/scalar JSON rejected by tabular profiler; cells, sessions, masks and boot normalized explicitly. Composite keys unique and no dropped records. Condition counts overlap: not unique totals or funnel. Dates parsed by profiler; no time-rate analysis. Profiler divides by 8 calendar days, but study has 6 specified observed sessions; do not use its per-day hints. BOTH=0 is structural. Boot one-row constants and stop_reason=null expected for successful exit, not missing measurements.",
        cell_omission_support_rankings=cell_ranks, session_omission_support_rankings=session_ranks,
        thresholds_and_private_computed_training_quantiles=r["total_training"]["cells"],
        runner_seconds=r["wall_seconds"], boot_wall_seconds=boot["wall_seconds"],
        sampled_child_peak_rss_bytes=boot["sampled_child_peak_rss_bytes"],
        comparison_plan=[
            dict(grain="condition omission", population="44374 eligible training anchors",
                 unit="anchors", finding="Current pressure has largest other-four count in all six sessions and all four pooled phase/direction cells",
                 derivation="Count truth tuples with the four non-omitted conditions true",
                 disposition="chart", reason="Five comparable overlapping counts; not a funnel or actual relaxed run"),
            dict(grain="training census", population="76284 observed anchors",
                 unit="anchors", finding="Only two full conjunction cases, both OTHER:-1; UNKNOWN kept outside eligible denominator",
                 derivation="State census and mask31", disposition="prose",
                 reason="Necessary denominator and caveat; not a broad state composition study"),
            dict(grain="marginal condition", population="44374 eligible anchors",
                 unit="anchors", finding="Rarest individual criterion is not the conditional bottleneck",
                 derivation="Sum masks where selected condition is true", disposition="table",
                 reason="Durable lookup CSV; a second plotted panel would not change the decision"),
            dict(grain="date and phase/direction", population="same training anchors",
                 unit="anchors", finding="Current-pressure ranking survives all dates and pooled cells",
                 derivation="Independent same-grain rankings", disposition="table",
                 reason="Complete CSV/JSON lookup retained; no consequential aggregate reversal"),
            dict(grain="component quantiles", population="known private training arrays",
                 unit="native component units", finding="Quantiles retained, not recomputed or pooled on host",
                 derivation="Frozen runner receipt only", disposition="omit",
                 reason="Cannot independently recover raw-private quantiles; no claim of quantile parity")
        ],
        scientific_interpretation="Joint support mismatch, not absence of physical absorption. Omitting one condition gives at most 170 anchors, still below prior frozen 2000 support requirement. No authorization to drop a filter or reinterpret prior effects.",
        operational_learning="Sparse previous state dictionaries omit zeros; dense new census includes them. Compare the declared state universe with explicit zero normalization, not dict equality; retain both immutable receipts.",
        proposed_next_step="New preregistered target-free continuous representation of pressure versus price progress and explicitly defined intermediate trajectories; verify support before evaluation. Do not tune to prior evaluation.",
        outcomes_computed=False, thresholds_changed=False, raw_exported=False,
        canonical_brain_written=False, confirmation=False, edge_claim=False)
    evidence_path = out / "analysis.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    totals.to_csv(out/"conditions.csv", index_label="condition")
    df.to_csv(out/"condition_cells.csv", index=False)
    pd.DataFrame(session_rows).to_csv(out/"sessions.csv", index=False)
    masks_df.to_csv(out/"masks.csv", index=False)
    pd.DataFrame([boot]).to_csv(out/"boot_profile.csv", index=False)
    labels = ["Presión actual", "Presión previa", "Avance pequeño", "Rango pequeño",
              "Recorrido pequeño", "Todas las cinco"]
    spec = dict(version=1, form="categorical-bars",
        title="La presión actual es el mayor cuello de botella de la conjunción A",
        aside="GC, seis sesiones de training; quitar un requisito es solo un recuento, no una nueva corrida",
        orientation="horizontal", mode="grouped", labels=labels, subjectIndex=0,
        tooltipLabels=[f"Cumplen las otras cuatro, sin exigir: {s}" for s in labels[:-1]] +
                      ["Cumplen las cinco condiciones de absorción A"],
        axis=dict(zero=True),
        derived=True, derivationReason="Enumeración de las 32 combinaciones de condiciones; no son etapas secuenciales",
        series=[dict(label="Anclas que cumplen", valueKind="count", role="subject",
                     data=[int(totals.loc[n,"passes_other_four"]) for n in names] + [full])])
    (out/"chart-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:evidence[k] for k in (
        "status","total_ticks","observed_anchors","eligible_anchors","full_conjunction_anchors",
        "passes_all_other_conditions","runner_seconds")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--ops", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.raw, args.ops, args.out)