"""Exportador store -> bundle del visor v2 (F6.5). El visor es pasivo: solo se
testea que el bundle tenga la estructura que los 3 modos consumen."""
import json
import os
import sys

import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import identity as idy
from edgelab.bridge import store
from edgelab.bridge.indicators import gaps2
from edgelab.bridge.ticks import load_canonical_parquet

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import build_viewer  # noqa: E402

PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-25_ticks.parquet")
pytestmark = pytest.mark.skipif(not os.path.exists(PARQUET),
                                reason="parquet 6E no disponible")


def _iso_ns(s):
    import datetime as dt
    return int(dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp() * 1e9)


def _mini_store(root):
    tk = load_canonical_parquet(PARQUET, contract="6E 09-25",
                                start_utc_ns=_iso_ns("2025-08-05T00:00:00"),
                                end_utc_ns=_iso_ns("2025-08-05T03:00:00"))
    bars = B.build_time_bars(tk, 1)
    src = dict(path=PARQUET, sha256="x", rows=len(tk),
               range_start_utc="2025-08-05T00:00:00", range_end_utc="2025-08-05T03:00:00",
               kind="parquet_f2")
    kid = idy.kernel_id("Gaps2")
    dsid = idy.dataset_id(tk, tz_interpretation="canonical_utc_verified")
    for params in ({"min_gap_ticks": 5}, {"min_gap_ticks": 8}):
        res = gaps2.run(tk, bars, params=params)
        cid = idy.config_id("Gaps2", res["params"], "time_1", "UTC", kid)
        rid = idy.run_id(dsid, cid, "2025-08-05T00:00:00", "2025-08-05T03:00:00")
        store.publish_run(root, kernel_result=res, indicator="Gaps2", tick_size=tk.tick_size,
                          instrument="6E", contract="6E 09-25", bar_key="time_1",
                          dataset_id=dsid, kernel_id=kid, config_id=cid, run_id=rid,
                          params=res["params"], source=src, generated_utc="x")


def _load_bundle(out_dir):
    txt = open(os.path.join(out_dir, "store_data.js"), encoding="utf-8").read()
    return json.loads(txt[txt.index("=") + 1:].rstrip().rstrip(";"))


def test_bundle_has_three_mode_data(tmp_path):
    root = tmp_path / "store"
    _mini_store(root)
    out = tmp_path / "viewer"
    rv = build_viewer.main(["--store", str(root), "--out", str(out)])
    assert rv == 0
    assert os.path.exists(os.path.join(str(out), "index.html"))
    b = _load_bundle(str(out))
    # AUDIT: catálogo con estados
    assert len(b["catalog"]) == 2
    assert all("integrity_state" in r and "parity_state" in r for r in b["catalog"])
    # ATLAS/PARITY: configs con zonas + candles
    assert len(b["configs"]) == 2
    c = b["configs"][0]
    assert c["candles_key"] in b["bar_series"]
    assert b["bar_series"][c["candles_key"]]["candles"]        # velas presentes
    assert c["zones"] and all(z["source"] == "python" for z in c["zones"])
    assert "config_id" in c and "params" in c and "digests" in c


def test_configs_differ_by_param(tmp_path):
    root = tmp_path / "store"
    _mini_store(root)
    out = tmp_path / "viewer"
    build_viewer.main(["--store", str(root), "--out", str(out)])
    b = _load_bundle(str(out))
    cids = {c["config_id"] for c in b["configs"]}
    assert len(cids) == 2                       # dos configs distintas -> Atlas puede comparar
    params = [c["params"]["min_gap_ticks"] for c in b["configs"]]
    assert set(params) == {5, 8}
