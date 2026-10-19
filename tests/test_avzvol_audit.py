import copy
import pytest
from edgelab.kaggle.avzvol_audit import (
    AVZVOLAuditError, DISCOVERY, CONFIRMATION, ACTIVITY,
    assign_frozen_bins, audit_covariates, require_baseline_reproduction,
)


def baseline():
    row = {"beta": -.2, "n_real": 300, "n_pseudo": 1500, "n_sesiones": 20}
    return {"evaluables": ["4_500_30"], "O5": {"4_500_30": row}}


def reproduced():
    p = baseline()
    return {"evaluables": p["evaluables"], "O5_sin_control": p["O5"]}


def test_baseline_complete_is_not_permission():
    p, r = baseline(), reproduced(); before = copy.deepcopy((p, r))
    out = require_baseline_reproduction(published=p, reproduced=r)
    assert out["cells_compared"] == 1 and not out["research_authorized"]
    assert (p, r) == before and not out["control_outcomes_opened"]


@pytest.mark.parametrize("side,field", [("published", "O5"), ("reproduced", "O5_sin_control")])
def test_skipped_cell_never_passes(side, field):
    p, r = baseline(), reproduced(); d = p if side == "published" else r
    d[field] = {}
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "0.2", True, -.21])
def test_bad_or_nonreproduced_beta(value):
    p, r = baseline(), reproduced(); r["O5_sin_control"]["4_500_30"]["beta"] = value
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)


def test_no_reference_no_bypass():
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=None, reproduced=reproduced())


def test_duplicate_universe_and_extra_cell():
    p, r = baseline(), reproduced(); r["evaluables"] *= 2
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)
    r = reproduced(); r["O5_sin_control"]["extra"] = {}
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)


def test_changed_sample_even_same_beta_fails():
    p, r = baseline(), reproduced(); r["O5_sin_control"]["4_500_30"]["n_real"] = 301
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)


def test_legacy_predicate_can_skip_a_missing_cell_but_new_guard_cannot():
    p, r = baseline(), reproduced()
    p["evaluables"].append("6_500_30")
    r["evaluables"].append("6_500_30")
    r["O5_sin_control"]["6_500_30"] = copy.deepcopy(r["O5_sin_control"]["4_500_30"])
    # Mirrors the legacy defect: missing published O5[cell] gets skipped.
    dif = {c: abs(r["O5_sin_control"][c]["beta"] - p["O5"][c]["beta"])
           for c in r["evaluables"] if c in p["O5"]}
    legacy_pass = bool(dif and max(dif.values()) <= 1e-9
                       and sorted(p["evaluables"]) == sorted(r["evaluables"]))
    assert legacy_pass
    with pytest.raises(AVZVOLAuditError):
        require_baseline_reproduction(published=p, reproduced=r)


def frame():
    import pandas as pd
    return pd.DataFrame([dict(contract=c, cell="4_500_30", kind=k, session=20250901,
                              occ=1., amp=2., **{a: 1. for a in ACTIVITY})
                         for c in DISCOVERY + CONFIRMATION
                         for k in ["real"]*10+["pseudo"]*40])


def test_covariates_no_outcomes_and_no_mutation():
    t = frame(); before = t.copy(deep=True)
    r = audit_covariates(t)
    assert r["row_count"] == 300 and not r["outcomes_recomputed"]
    assert not r["pair_id_present"] and not r["bias_adjudicated"]
    assert r["contracts"][0]["aggregate_nominal_attainment_pct"] == 80.
    assert r["rank_first_tie_splits"]
    assert t.equals(before)


def test_no_unknown_or_reserved_contract_data():
    t = frame(); t.loc[0, "session"] = 20261001
    with pytest.raises(AVZVOLAuditError): audit_covariates(t)
    t = frame(); t.loc[0, "contract"] = "NQ_09-25"
    with pytest.raises(AVZVOLAuditError): audit_covariates(t)


def test_frozen_bins_preserve_equal_values_and_permutation():
    values = [1., 1., 2., 0., 1.]
    labels = assign_frozen_bins(values, [1., 2.])
    assert labels == [0, 0, 1, 0, 0]
    assert assign_frozen_bins(values[::-1], [1., 2.]) == labels[::-1]


@pytest.mark.parametrize("edges", [[1., 1.], [2., 1.], [float("inf")], [True]])
def test_invalid_frozen_edges_stop(edges):
    with pytest.raises(AVZVOLAuditError): assign_frozen_bins([1.], edges)


def test_missing_covariate_never_imputed_by_new_bins():
    with pytest.raises(AVZVOLAuditError): assign_frozen_bins([float("nan")], [1.])