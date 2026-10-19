"""Propagación de parity_covered (F7c).

Semántica pre-declarada en docs/nt8_indicator_parity_contract.md §8. Estos
tests fijan lo que NUNCA debe cruzar (bar_spec, instrumento, kernel_id),
el anti-autootorgamiento, la idempotencia y la degradación a under_review.
"""
import json

import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import coverage, identity as idy, store
from edgelab.bridge.indicators import gaps2
from edgelab.bridge.ticks import make_synthetic


# --------------------------- helpers --------------------------------------- #
def _publish(root, *, params=None, contract="SYN 06-26", bar_key="time_1",
             chart_tz="UTC", parity=None, kernel_id=None, run_suffix="",
             instrument="SYN", propagate=True):
    tk = make_synthetic(n_sessions=1, ticks_per_session=3000)
    bars = B.build_time_bars(tk, minutes=1)
    res = gaps2.run(tk, bars, params=params or {}, chart_tz=chart_tz)
    kid = kernel_id or idy.kernel_id("Gaps2")
    cid = idy.config_id("Gaps2", res["params"], bar_key, chart_tz, kid)
    dsid = idy.dataset_id(tk, tz_interpretation="synthetic")
    rid = idy.run_id(dsid, cid, "s" + run_suffix, "e" + run_suffix)
    return store.publish_run(
        root, kernel_result=res, indicator="Gaps2", tick_size=tk.tick_size,
        instrument=instrument, contract=contract, bar_key=bar_key,
        dataset_id=dsid, kernel_id=kid, config_id=cid, run_id=rid,
        params=res["params"], source=dict(kind="synthetic"), chart_tz=chart_tz,
        parity=parity, generated_utc="x", propagate_coverage=propagate)


def _state(root, run_id):
    return {r["run_id"]: r for r in store.catalog_df(root)}[run_id]["parity_state"]


PASS_PARITY = dict(gate="PASS", oracle_path="/o/Gaps2.csv", oracle_sha256="abc123")


# --------------------------- camino 1: publicar nueva ---------------------- #
def test_new_partition_gets_covered_by_existing_exact(tmp_path):
    root = tmp_path / "store"
    src = _publish(root, params={"min_gap_ticks": 2}, contract="6E 09-26",
                   parity=PASS_PARITY)
    assert src["parity_state"] == "parity_exact"
    # nueva partición: mismo kernel/bar/instrumento, otro contrato, y difiere
    # SOLO en min_gap_ticks (coverage-neutral para Gaps2, §8.3.1)
    tgt = _publish(root, params={"min_gap_ticks": 8}, contract="6E 09-25",
                   run_suffix="-b")
    assert _state(root, tgt["run_id"]) == "parity_covered"


def test_promoting_to_exact_propagates_to_existing(tmp_path):
    root = tmp_path / "store"
    # primero la pendiente, después llega el oráculo
    tgt = _publish(root, params={"min_gap_ticks": 8}, contract="6E 09-25")
    assert _state(root, tgt["run_id"]) == "parity_pending"
    _publish(root, params={"min_gap_ticks": 2}, contract="6E 09-26",
             parity=PASS_PARITY, run_suffix="-src")
    assert _state(root, tgt["run_id"]) == "parity_covered"


# --------------------------- idempotencia ---------------------------------- #
def test_propagation_is_idempotent(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, contract="6E 09-26", parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 8}, contract="6E 09-25", run_suffix="-b")
    r1 = coverage.propagate_coverage(root)
    r2 = coverage.propagate_coverage(root)
    # la segunda pasada no vuelve a otorgar: ya está cubierta
    assert r1["granted"] == [] and r2["granted"] == []
    assert _state(root, tgt["run_id"]) == "parity_covered"
    # el bloque de evidencia no se duplica ni cambia
    man = json.loads({r["run_id"]: r for r in store.catalog_df(root)}[tgt["run_id"]]["manifest_json"])
    assert isinstance(man["coverage"], dict)
    assert man["coverage"]["rule_version"] == coverage.COVERAGE_RULE_VERSION


# --------------------------- lo que NUNCA cruza (§8.2) --------------------- #
def test_coverage_never_crosses_bar_spec(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, bar_key="time_1", parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 2}, bar_key="tick_25", run_suffix="-t")
    assert _state(root, tgt["run_id"]) == "parity_pending"


def test_coverage_never_crosses_instrument(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, instrument="6E", parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 2}, instrument="ES", run_suffix="-i")
    assert _state(root, tgt["run_id"]) == "parity_pending"


def test_coverage_never_crosses_kernel_digest(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 2}, kernel_id="OTRO_KERNEL_DIGEST",
                   run_suffix="-k")
    assert _state(root, tgt["run_id"]) == "parity_pending"


def test_recompute_param_blocks_coverage(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, parity=PASS_PARITY)
    # export_floor_ticks es clase recompute -> NUNCA cubierto (§8.3)
    tgt = _publish(root, params={"export_floor_ticks": 3}, run_suffix="-r")
    assert _state(root, tgt["run_id"]) == "parity_pending"


def test_lifecycle_param_blocks_coverage(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, parity=PASS_PARITY)
    tgt = _publish(root, params={"reversal_confirm_ticks": 0}, run_suffix="-l")
    assert _state(root, tgt["run_id"]) == "parity_pending"


def test_non_whitelisted_offline_param_blocks_coverage(tmp_path):
    # max_logged_touches es clase 'offline' pero NO está en la lista blanca
    # (§8.3.1: la garantía no es universal por la exclusión de SESSION_END)
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, parity=PASS_PARITY)
    tgt = _publish(root, params={"max_logged_touches": 3}, run_suffix="-o")
    assert _state(root, tgt["run_id"]) == "parity_pending"


# --------------------------- anti-autootorgamiento (§8.4) ------------------ #
def test_no_self_granting():
    exact = dict(run_id="R1", parity_state="parity_exact", indicator="Gaps2",
                 kernel_id="K", instrument="6E", bar_key="time_1", chart_tz="UTC",
                 params={"min_gap_ticks": 2})
    assert any("autootorgamiento" in b for b in coverage.coverage_blockers(exact, exact))


def test_coverage_is_not_transitive():
    # una fuente que solo está parity_covered NO puede cubrir a nadie (§8.4)
    src = dict(run_id="R1", parity_state="parity_covered", indicator="Gaps2",
               kernel_id="K", instrument="6E", bar_key="time_1", chart_tz="UTC",
               params={"min_gap_ticks": 2})
    tgt = dict(src, run_id="R2")
    assert any("no es parity_exact" in b for b in coverage.coverage_blockers(src, tgt))


def test_publish_run_never_writes_covered_directly(tmp_path):
    # publish_run solo deriva pending/exact/failed de su PROPIO gate (§8.4)
    root = tmp_path / "store"
    m = _publish(root, params={"min_gap_ticks": 2}, propagate=False)
    assert m["parity_state"] == "parity_pending"
    m2 = _publish(root, params={"min_gap_ticks": 8}, parity=dict(gate="FAIL"),
                  run_suffix="-f", propagate=False)
    assert m2["parity_state"] == "parity_failed"


# --------------------------- degradación (§8.5) ---------------------------- #
def test_failed_gate_degrades_coverage_to_under_review(tmp_path):
    root = tmp_path / "store"
    _publish(root, params={"min_gap_ticks": 2}, contract="6E 09-26", parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 8}, contract="6E 09-25", run_suffix="-b")
    assert _state(root, tgt["run_id"]) == "parity_covered"
    # aparece un FAIL en OTRA config del MISMO kernel_id
    _publish(root, params={"min_gap_ticks": 12}, contract="6E 12-25",
             parity=dict(gate="FAIL"), run_suffix="-fail")
    assert _state(root, tgt["run_id"]) == "parity_under_review"


def test_under_review_is_a_valid_state():
    assert "parity_under_review" in store.PARITY_STATES


# --------------------------- auditabilidad (§8.6) -------------------------- #
def test_coverage_block_records_source_and_oracle(tmp_path):
    root = tmp_path / "store"
    src = _publish(root, params={"min_gap_ticks": 2}, contract="6E 09-26",
                   parity=PASS_PARITY)
    tgt = _publish(root, params={"min_gap_ticks": 8}, contract="6E 09-25", run_suffix="-b")
    man = json.loads({r["run_id"]: r for r in store.catalog_df(root)}[tgt["run_id"]]["manifest_json"])
    cov = man["coverage"]
    assert cov["source_config_id"] == src["config_id"]
    assert cov["source_run_id"] == src["run_id"]
    assert cov["source_contract"] == "6E 09-26"
    assert cov["oracle_sha256"] == "abc123"
    assert cov["neutral_params_used"] == ["min_gap_ticks"]
    assert cov["granted_utc"]
