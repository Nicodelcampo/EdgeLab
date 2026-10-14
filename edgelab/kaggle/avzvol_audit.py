"""AVZVOL read-only audit helpers, not a statistical test or research grant.

The baseline comparison is opt-in; it does not retrofit the legacy branch.
Covariate diagnostics do not compute O1/O5, returns, p-values or new trials.
"""
from __future__ import annotations
from bisect import bisect_left
import math

DISCOVERY = ("MNQ_09-25", "MNQ_12-25", "MNQ_03-26", "MNQ_06-26")
CONFIRMATION = ("MNQ_09-26", "MNQ_12-26")
ACTIVITY = ("vol_occ", "vol_100", "dur_occ", "dur_100")
BASELINE_TOLERANCE = 1e-9


class AVZVOLAuditError(ValueError):
    pass


def assign_frozen_bins(values, cutpoints):
    """Future opt-in FE labels from externally frozen finite cutpoints.

    Equal values always share a bin; labels do not depend on row order/kind.
    Never derive edges from confirmation or silently replace a legacy trial.
    This utility does not authenticate approval of the supplied cutpoints.
    """
    edges = list(cutpoints)
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in edges):
        raise AVZVOLAuditError("finite numeric frozen cutpoints required")
    if any(a >= b for a, b in zip(edges, edges[1:])):
        raise AVZVOLAuditError("cutpoints must be strictly increasing")
    result = []
    for value in values:
        if type(value) not in (int, float) or not math.isfinite(value):
            raise AVZVOLAuditError("no implicit missing-value substitution")
        result.append(bisect_left(edges, value))
    return result


def require_baseline_reproduction(*, published, reproduced):
    """Demand every evaluable cell and finite beta/count equality.

    Pure metadata comparison of two already-computed baseline results. No
    control outcomes read here. Missing published cells cannot be skipped.
    Does not verify byte hashes/authority or license opening control results.
    """
    if not isinstance(published, dict) or not isinstance(reproduced, dict):
        raise AVZVOLAuditError("baseline reference and reproduction are mandatory")
    cells = published.get("evaluables")
    if not isinstance(cells, list) or not cells or any(not isinstance(c, str) for c in cells):
        raise AVZVOLAuditError("missing published evaluable universe")
    if len(set(cells)) != len(cells):
        raise AVZVOLAuditError("duplicate evaluable cell")
    got = reproduced.get("evaluables")
    if not isinstance(got, list) or any(not isinstance(c, str) for c in got) or (
        len(set(got)) != len(got) or set(got) != set(cells)
    ):
        raise AVZVOLAuditError("evaluable universe differs")
    ref, new = published.get("O5"), reproduced.get("O5_sin_control")
    if not isinstance(ref, dict) or not isinstance(new, dict) or (
        set(ref) != set(cells) or set(new) != set(cells)
    ):
        raise AVZVOLAuditError("baseline coverage must be exact, no skipped cells")
    differences = []
    for cell in cells:
        a, b = ref[cell], new[cell]
        if not isinstance(a, dict) or not isinstance(b, dict):
            raise AVZVOLAuditError("invalid baseline row")
        for field in ("n_real", "n_pseudo", "n_sesiones"):
            if type(a.get(field)) is not int or type(b.get(field)) is not int or (
                a[field] <= 0 or a[field] != b[field]
            ):
                raise AVZVOLAuditError("baseline sample differs or is undeclared")
        x, y = a.get("beta"), b.get("beta")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (x, y)):
            raise AVZVOLAuditError("baseline beta must be finite numeric")
        delta = abs(x-y)
        if delta > BASELINE_TOLERANCE:
            raise AVZVOLAuditError("baseline beta does not reproduce")
        differences.append(delta)
    return {"status": "PASS_DECLARED_BASELINE_COMPARISON_ONLY", "cells_compared": len(cells),
            "max_absolute_beta_difference": max(differences), "research_authorized": False,
            "control_outcomes_opened": False, "bias_adjudicated": False}


def audit_covariates(frame):
    """Technical diagnostics on historical event covariates, without outcomes.

    Aggregate pseudo/real counts CANNOT reconstruct individual pair coverage.
    Equal-value splits diagnose rank(first) FE bins, not their economic effect.
    """
    import pandas as pd
    required = {"contract", "cell", "kind", "session", "occ", "amp", *ACTIVITY}
    if not required <= set(frame.columns):
        raise AVZVOLAuditError("missing AVZVOL event covariates")
    if frame.empty or not set(frame["kind"]) <= {"real", "pseudo"}:
        raise AVZVOLAuditError("empty or invalid event table")
    if frame["session"].isna().any() or (frame["session"] >= 20261001).any():
        raise AVZVOLAuditError("reserved or undeclared session")
    if frame[list(required)].drop(columns=["amp"]).isna().any().any():
        raise AVZVOLAuditError("missing identity/activity/occupancy")
    if set(frame["contract"]) != set(DISCOVERY + CONFIRMATION):
        raise AVZVOLAuditError("exact six-contract universe required")
    rows = []
    for contract in DISCOVERY + CONFIRMATION:
        t = frame[frame.contract == contract]
        n_real, n_pseudo = int((t.kind == "real").sum()), int((t.kind == "pseudo").sum())
        if n_real == 0:
            raise AVZVOLAuditError("contract has no real events")
        rows.append({"contract": contract, "partition": "discovery" if contract in DISCOVERY else "confirmation",
                     "real_event_rows": n_real, "pseudo_event_rows": n_pseudo,
                     "nominal_five_pseudo_rows": 5*n_real,
                     "aggregate_nominal_attainment_pct": 100*n_pseudo/(5*n_real),
                     "individual_pair_coverage_verified": False})
    tied = []
    for partition, contracts in (("discovery", DISCOVERY), ("confirmation", CONFIRMATION)):
        sub = frame[frame.contract.isin(contracts)]
        for cell, t in sub.groupby("cell", sort=True):
            # Mirrors legacy preprocessing ONLY to inspect equal-value splitting.
            # No FE fitting or outcomes; all inputs remain unchanged.
            for field, q in (("occ", 10), ("amp", 3), *((a, 10) for a in ACTIVITY)):
                values = t[field].fillna(t[field].median())
                if values.isna().any() or len(values) < q:
                    continue
                bins = pd.qcut(values.rank(method="first"), q, labels=False)
                grouped = pd.DataFrame({"value": values.to_numpy(), "bin": bins.to_numpy()})
                split = grouped.groupby("value")["bin"].nunique()
                affected = set(split[split > 1].index)
                if affected:
                    tied.append({"partition": partition, "cell": cell, "field": field,
                                 "equal_value_levels_split": len(affected),
                                 "rows_at_split_equal_values": int(values.isin(affected).sum())})
    return {"schema": "edgelab_avzvol_covariate_audit_v1", "status": "REQUIRES_REVIEW",
            "contracts": rows, "row_count": len(frame), "rank_first_tie_splits": tied,
            "pair_id_present": "pair_id" in frame.columns,
            "outcomes_recomputed": False, "research_authorized": False,
            "bias_adjudicated": False, "original_evidence_modified": False}