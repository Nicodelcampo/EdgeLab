"""Canonical event/store contract for BigTrap2Absorption."""

from edgelab.bridge import oracle, store
from edgelab.bridge.indicators import bigtrap2absorption
from edgelab.bridge.ticks import make_synthetic


PERMISSIVE_PARAMS = {
    "MinHistoryBuckets": 1,
    "AbsorptionLookback": 10,
    "AbsorptionPct": 0,
    "ImbalanceRatio": 1,
    "MinStackedRows": 1,
    "MinTrapFrac": 0,
    "UseWickFilter": False,
    "RequireFlowSideMatch": False,
}


def test_bigtrap2absorption_pipe_events_reconstruct_zone_core():
    ticks = make_synthetic(n_sessions=1, ticks_per_session=1000)
    result = bigtrap2absorption.run(ticks, params=PERMISSIVE_PARAMS)

    required = {
        "indicator",
        "params",
        "header",
        "csv_lines",
        "events",
        "zones",
        "params_line",
    }
    assert required <= result.keys()
    assert result["indicator"] == "BigTrap2Absorption"
    assert result["header"] is None
    assert result["csv_lines"] == result["events"]
    assert result["zones"], "fixture must exercise non-empty reconstruction"

    parsed = oracle.parse_records(
        [result["params_line"], *result["csv_lines"]],
        chart_tz="UTC",
        tick_size=ticks.tick_size,
    )
    assert parsed["indicator"] == "BigTrap2Absorption"
    assert parsed["zones"]

    direct = store.zones_core_digest_from_kernel(
        result["zones"], ticks.tick_size
    )
    reconstructed = store.zones_core_digest_from_events(
        result["csv_lines"],
        result["header"],
        result["params_line"],
        result["indicator"],
        "UTC",
        ticks.tick_size,
    )
    assert direct == reconstructed
