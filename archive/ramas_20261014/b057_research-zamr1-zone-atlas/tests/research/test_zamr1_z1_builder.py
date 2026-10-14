# -*- coding: utf-8 -*-
from types import SimpleNamespace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from edgelab.bridge.ticks import TickSeries
from edgelab.research.zamr1.session_clock import session_date_cme
from edgelab.research.zamr1.z1_builder import (
    CUTOFF,
    payloads,
    resolve_provenance,
    tick_bounds_from_price,
    transform,
)


def fixture(created=1780340400000000000):
    bars = SimpleNamespace(
        param=5,
        end_ns=np.array([created, created + 1]),
        close_t=np.array([20000, 20001]),
        volume=np.array([100.0, 120.0]),
    )
    tk = TickSeries(
        ts_ns=np.array([created]),
        price_ticks=np.array([20000]),
        volume=np.array([1.0]),
        bid_ticks=np.array([19999]),
        ask_ticks=np.array([20000]),
        sequence=np.array([0]),
        tick_size=0.00005,
        instrument="6E",
        contract="06-26",
    )
    zone = {
        "id": "0_B",
        "created_bar": 0,
        "created_ms": created // 1_000_000,
        "ended_ms": None,
        "state": "ACTIVE",
        "end_reason": None,
        "top": 1.000075,
        "bottom": 1.000025,
        "kind": "trapped_buyers",
        "touches": 0,
    }
    result = {
        "zones": [zone],
        "events": [{"seq": 0, "type": "ZONE_CREATED", "ts_ns": created, "bar_index": 0, "zone_id": "0_B"}],
        "csv_lines": ["0|x|ZONE_CREATED|zone_id=0_B;created_bar=0;side=trapped_buyers;lo=1.000025;hi=1.000075;vol=31"],
    }
    return bars, tk, result


def test_payload_parser():
    assert payloads(["7|x|ZONE_CREATED|zone_id=z;vol=31"])[7][1]["vol"] == "31"


def test_cme_session_cutover_is_1700_chicago():
    cutoff_local = datetime.fromtimestamp(CUTOFF / 1e9, tz=timezone.utc).astimezone(ZoneInfo("America/Chicago"))
    assert cutoff_local.hour == 17
    assert session_date_cme(CUTOFF) == "2026-07-01"
    before = CUTOFF - 1_000_000_000
    assert session_date_cme(before) == "2026-06-30"


def test_tick_bounds_invert_half_tick_padding():
    tick_size = 5e-05
    lo_tick, hi_tick = 20000, 20003
    bottom = lo_tick * tick_size - tick_size / 2.0
    top = hi_tick * tick_size + tick_size / 2.0
    assert tick_bounds_from_price(top, bottom, tick_size) == (lo_tick, hi_tick)


def test_transform_target_free_and_no_false_parity_claim():
    bars, tk, result = fixture()
    events, zones = transform(result, bars, tk, {"2026-06-01"}, "run", "params")
    assert len(events) == len(zones) == 1
    assert events[0]["oracle_parity_status"] == zones[0]["oracle_parity_status"] == "NOT_ESTABLISHED"
    assert zones[0]["zone_lo_tick"] == 20001
    assert zones[0]["zone_hi_tick"] == 20001
    forbidden = ("target__", "future_", "outcome_", "pnl_", "return_")
    assert not any(key.startswith(forbidden) for key in events[0])


def test_firewall_fails_closed():
    bars, tk, result = fixture(CUTOFF)
    result["events"][0]["ts_ns"] = CUTOFF
    session = session_date_cme(CUTOFF)
    with pytest.raises(RuntimeError, match="FIREWALL"):
        transform(result, bars, tk, {session}, "run", "params")


def test_offline_provenance_requires_commit_and_clean_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("EDGELAB_CODE_COMMIT", raising=False)
    monkeypatch.setenv("EDGELAB_CODE_DIRTY", "true")
    with pytest.raises(RuntimeError, match="ABSTAIN_PROVENANCE"):
        resolve_provenance(tmp_path)
    (tmp_path / "CODE_COMMIT").write_text("a" * 40)
    monkeypatch.setenv("EDGELAB_CODE_DIRTY", "false")
    head, dirty = resolve_provenance(tmp_path)
    assert head == "a" * 40
    assert dirty is False
