"""Runner de campañas (F6.4): expansión de grilla, validación, control de
explosión, declaración de costo y cierre P3.0."""
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import run_campaign as rc  # noqa: E402

PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-25_ticks.parquet")
pytestmark = pytest.mark.skipif(not os.path.exists(PARQUET),
                                reason="parquet 6E no disponible")


def test_expand_grid_cartesian():
    grid = {"a": [1, 2], "b": [10, 20]}
    combos = rc._expand_grid(grid)
    assert len(combos) == 4
    assert {"a": 1, "b": 10} in combos and {"a": 2, "b": 20} in combos
    assert rc._expand_grid({}) == [{}]


TZ_CHART = "America/Argentina/Buenos_Aires"   # medido, no supuesto: ver 3.2


def test_plan_rejects_invalid_params():
    camp = dict(chart_tz=TZ_CHART,
                jobs=[dict(indicator="Gaps2", bars=["time:1"],
                           grid={"min_gap_ticks": [0]})])   # 0 < min 1
    planned, tz, errors = rc._plan(camp)
    assert errors and any("min_gap_ticks" in e for e in errors)


def test_plan_rejects_forbidden_param():
    camp = dict(chart_tz=TZ_CHART,
                jobs=[dict(indicator="BigTrap2", bars=["time:1"],
                           grid={"TopPercentFilter": [10]})])
    _, _, errors = rc._plan(camp)
    assert errors and any("forbidden" in e for e in errors)


def test_plan_exige_chart_tz():
    """NT8 emite Time[0] en la tz del chart. Heredar un default corre
    `bar_close_time` 3 h y desalinea la clave de zona sin avisar."""
    camp = dict(jobs=[dict(indicator="Gaps2", bars=["time:1"], grid={})])
    planned, tz, errors = rc._plan(camp)
    assert errors and any("chart_tz" in e for e in errors)
    assert tz is None and planned == []


def _write_campaign(tmp_path, store, max_configs, grid):
    spec = dict(campaign_id="t", store=str(store), chart_tz="UTC",
                max_configs=max_configs,
                data=dict(parquet=PARQUET, contract="6E 09-25",
                          start_utc="2025-08-05T00:00:00", end_utc="2025-08-05T02:00:00"),
                jobs=[dict(indicator="Gaps2", bars=["time:1"], grid=grid)])
    p = tmp_path / "campaign.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return str(p)


def test_dry_run_declares_and_writes_manifest(tmp_path):
    store = tmp_path / "store"
    camp = _write_campaign(tmp_path, store, 40, {"min_gap_ticks": [5, 8]})
    rv = rc.main(["--campaign", camp, "--dry-run"])
    assert rv == 0
    cm = json.load(open(os.path.join(str(store), "campaign_t.json")))
    assert len(cm["expected_config_ids"]) == 2
    assert cm["dataset_id"] and cm["n_planned"] == 2


def test_explosion_abort_over_max(tmp_path):
    store = tmp_path / "store"
    # 3 x 2 = 6 configs con max_configs=2 -> aborta antes de correr
    camp = _write_campaign(tmp_path, store, 2,
                           {"min_gap_ticks": [5, 8, 12], "export_floor_ticks": [2, 3]})
    rv = rc.main(["--campaign", camp, "--dry-run"])
    assert rv == 2                                # control de explosión


def test_full_run_p30_complete(tmp_path):
    store = tmp_path / "store"
    camp = _write_campaign(tmp_path, store, 40, {"min_gap_ticks": [5, 8]})
    rv = rc.main(["--campaign", camp, "--audit"])
    assert rv == 0
    from edgelab.bridge import store as st
    assert len(st.catalog_df(str(store))) == 2
