"""API de features para vectorbt (F8): get_zones + materialize_features.

La fuerza bruta consume el store por identidad y materializa features as-of, SIN
importar módulos de kernel. El digest de lo consultado == el del manifest.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import features, identity as idy, store
from edgelab.bridge.indicators import gaps2
from edgelab.bridge.ticks import load_canonical_parquet

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARQUET = os.path.join(REPO, "data", "nt8", "6E", "6E_09-25_ticks.parquet")


# --------------------------- materialize (sin store) ----------------------- #
def _ref_features(zones, index_ms, price):
    """Implementación de referencia lenta e independiente (para contrastar)."""
    rows = []
    for i, t in enumerate(index_ms):
        p = price[i]
        active = [z for z in zones if z["created_ms"] <= t and
                  (z["ended_ms"] is None or z["ended_ms"] > t)]
        d = dict(active_zone_count=len(active), inside_zone=False,
                 distance_to_nearest_zone=np.nan, zone_age=np.nan,
                 nearest_zone_side=None)
        if active:
            dists = [(0.0 if z["bottom"] <= p <= z["top"]
                      else min(abs(p - z["top"]), abs(p - z["bottom"])), z) for z in active]
            d["inside_zone"] = any(z["bottom"] <= p <= z["top"] for z in active)
            dd, zz = min(dists, key=lambda x: x[0])
            d["distance_to_nearest_zone"] = dd
            d["zone_age"] = t - zz["created_ms"]
            d["nearest_zone_side"] = zz["side"]
        rows.append(d)
    return rows


def test_materialize_matches_reference():
    zones = [
        dict(created_ms=1000, ended_ms=5000, top=1.10, bottom=1.09, side="bull"),
        dict(created_ms=2000, ended_ms=None, top=1.12, bottom=1.115, side="bear"),
        dict(created_ms=4000, ended_ms=8000, top=1.105, bottom=1.10, side="bull"),
    ]
    df_z = pd.DataFrame(zones)
    index_ms = np.array([500, 1500, 2500, 4500, 6000, 9000])
    price = np.array([1.095, 1.095, 1.118, 1.101, 1.13, 1.10])
    got = features.materialize_features(df_z, index_ms, price=price)
    ref = _ref_features(zones, index_ms, price)
    for i in range(len(index_ms)):
        assert int(got["active_zone_count"].iloc[i]) == ref[i]["active_zone_count"]
        assert bool(got["inside_zone"].iloc[i]) == ref[i]["inside_zone"]
        gs = got["nearest_zone_side"].iloc[i]
        if isinstance(gs, float) and np.isnan(gs):
            gs = None                              # nan == None (sin zona cercana)
        assert gs == ref[i]["nearest_zone_side"]
        a, b = got["distance_to_nearest_zone"].iloc[i], ref[i]["distance_to_nearest_zone"]
        assert (np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-12
        a, b = got["zone_age"].iloc[i], ref[i]["zone_age"]
        assert (np.isnan(a) and np.isnan(b)) or a == b


def test_materialize_no_lookahead():
    # una zona creada en t=2000 NO está activa antes de t=2000
    zones = pd.DataFrame([dict(created_ms=2000, ended_ms=None, top=1.1, bottom=1.09, side="bull")])
    idx = np.array([1000, 1999, 2000, 3000])
    price = np.array([1.095, 1.095, 1.095, 1.095])
    got = features.materialize_features(zones, idx, price=price)
    assert list(got["active_zone_count"]) == [0, 0, 1, 1]   # activa recién en 2000


def test_active_count_without_price():
    zones = pd.DataFrame([dict(created_ms=0, ended_ms=10, top=1, bottom=0, side="x")])
    got = features.materialize_features(zones, [5, 15], features=("active_zone_count",))
    assert list(got["active_zone_count"]) == [1, 0]


def test_price_features_require_price():
    zones = pd.DataFrame([dict(created_ms=0, ended_ms=10, top=1, bottom=0, side="x")])
    with pytest.raises(ValueError):
        features.materialize_features(zones, [5], features=("inside_zone",))


# --------------------------- store query + digest -------------------------- #
@pytest.mark.skipif(not os.path.exists(PARQUET), reason="parquet 6E no disponible")
def test_get_zones_and_digest(tmp_path):
    import datetime as dt
    s = int(dt.datetime(2025, 8, 5, tzinfo=dt.timezone.utc).timestamp() * 1e9)
    e = int(dt.datetime(2025, 8, 5, 3, tzinfo=dt.timezone.utc).timestamp() * 1e9)
    tk = load_canonical_parquet(PARQUET, contract="6E 09-25", start_utc_ns=s, end_utc_ns=e)
    bars = B.build_time_bars(tk, 1)
    res = gaps2.run(tk, bars, params={"min_gap_ticks": 5})
    kid = idy.kernel_id("Gaps2")
    cid = idy.config_id("Gaps2", res["params"], "time_1", "UTC", kid)
    dsid = idy.dataset_id(tk, tz_interpretation="canonical_utc_verified")
    rid = idy.run_id(dsid, cid, "s", "e")
    root = tmp_path / "store"
    man = store.publish_run(root, kernel_result=res, indicator="Gaps2",
                            tick_size=tk.tick_size, instrument="6E", contract="6E 09-25",
                            bar_key="time_1", dataset_id=dsid, kernel_id=kid, config_id=cid,
                            run_id=rid, params=res["params"], source=dict(kind="synthetic"),
                            generated_utc="x")

    # consulta por params (resuelve config_id) == consulta por config_id
    rows = features.get_zone_rows(root, indicator="Gaps2", params={"min_gap_ticks": 5},
                                  bar_key="time_1")
    assert features.resolve_config_id("Gaps2", {"min_gap_ticks": 5}, "time_1") == cid
    assert rows and all(r["config_id"] == cid for r in rows)

    # P3.4: digest de lo consultado == zone_digest del manifest
    assert store.zone_rows_digest(rows) == man["digests"]["zone"]

    # DataFrame fiel (mismo set de zone_key)
    df = features.get_zones_df(root, config_id=cid)
    assert set(df["zone_key"]) == set(r["zone_key"] for r in rows)


def test_features_no_kernel_import():
    # el consumo NO importa ningún kernel: features.py no referencia indicators
    src = open(os.path.join(REPO, "edgelab", "bridge", "features.py")).read()
    assert "indicators" not in src and "import gaps2" not in src
