# -*- coding: utf-8 -*-
from types import SimpleNamespace
import numpy as np
import pytest
from edgelab.bridge.ticks import TickSeries
from edgelab.research.zamr1.z1_builder import CUTOFF, payloads, transform


def fixture(created=1780340400000000000):
    bars=SimpleNamespace(param=5,end_ns=np.array([created,created+1]),close_t=np.array([20000,20001]),volume=np.array([100.,120.]))
    tk=TickSeries(ts_ns=np.array([created]),price_ticks=np.array([20000]),volume=np.array([1.]),bid_ticks=np.array([19999]),ask_ticks=np.array([20000]),sequence=np.array([0]),tick_size=.00005,instrument="6E",contract="06-26")
    z={"id":"0_B","created_bar":0,"created_ms":created//1000000,"ended_ms":None,"state":"ACTIVE","end_reason":None,"top":1.000075,"bottom":1.000025,"kind":"trapped_buyers","touches":0}
    r={"zones":[z],"events":[{"seq":0,"type":"ZONE_CREATED","ts_ns":created,"bar_index":0,"zone_id":"0_B"}],"csv_lines":["0|x|ZONE_CREATED|zone_id=0_B;created_bar=0;side=trapped_buyers;lo=1.000025;hi=1.000075;vol=31"]}
    return bars,tk,r


def test_payload_parser():
    assert payloads(["7|x|ZONE_CREATED|zone_id=z;vol=31"])[7][1]["vol"]=="31"


def test_transform_target_free_and_no_false_parity_claim():
    b,tk,r=fixture(); e,z=transform(r,b,tk,{"2026-06-01"},"run","params")
    assert len(e)==len(z)==1
    assert e[0]["oracle_parity_status"]==z[0]["oracle_parity_status"]=="NOT_ESTABLISHED"
    assert z[0]["zone_lo_tick"]<=z[0]["zone_hi_tick"]
    forbidden=("target__","future_","outcome_","pnl_","return_")
    assert not any(k.startswith(forbidden) for k in e[0])


def test_firewall_fails_closed():
    b,tk,r=fixture(CUTOFF); r["events"][0]["ts_ns"]=CUTOFF
    with pytest.raises(RuntimeError,match="FIREWALL"):
        transform(r,b,tk,{"2026-07-01"},"run","params")
