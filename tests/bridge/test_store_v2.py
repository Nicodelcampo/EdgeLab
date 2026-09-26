"""Store v2 (F6.2): 3 tablas, inmutable, content-addressed, 2 ejes de estado.

Verifica las reglas duras: publicación atómica, idempotencia, error de
determinismo, cero zonas válido, reconstrucción zones-desde-events, catálogo
DuckDB y los dos ejes de estado (reemplazo del booleano trusted).
"""
import os

import pytest

from edgelab.bridge import bars as B
from edgelab.bridge import identity as idy
from edgelab.bridge import store
from edgelab.bridge.indicators import REGISTRY, BAR_DRIVEN
from edgelab.bridge.ticks import make_synthetic


def _run_kernel(name, tk, bars, fps, params):
    mod = REGISTRY[name]
    if name in BAR_DRIVEN:
        return mod.run(tk, bars, fps, params=params)
    return mod.run(tk, bars, params=params)


def _publish(root, name, params, tk, bars, fps, parity=None):
    res = _run_kernel(name, tk, bars, fps, params)
    bkey = B and f"{bars.kind}_{bars.param}"
    kid = idy.kernel_id(name)
    cid = idy.config_id(name, res["params"], bkey, "UTC", kid)
    dsid = idy.dataset_id(tk, tz_interpretation="synthetic")
    rid = idy.run_id(dsid, cid, "2026-06-01", "2026-06-03")
    return store.publish_run(
        root, kernel_result=res, indicator=name, tick_size=tk.tick_size,
        instrument=tk.instrument, contract=tk.contract, bar_key=bkey,
        dataset_id=dsid, kernel_id=kid, config_id=cid, run_id=rid,
        params=res["params"], source=dict(kind="synthetic"), chart_tz="UTC",
        parity=parity, generated_utc="2026-06-03T00:00:00Z"), res, rid


@pytest.fixture
def data():
    tk = make_synthetic(n_sessions=2, ticks_per_session=6000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    return tk, bars, fps


def test_publish_creates_three_tables_and_catalog(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    man, res, rid = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    pdir = store.partition_dir(
        root, instrument=tk.instrument, contract=tk.contract, indicator="Gaps2",
        kernel_id=man["kernel_id"], bar_key=man["bar_key"],
        config_id=man["config_id"], run_id=rid)
    for f in ("observations.parquet", "events.parquet", "zones.parquet",
              "manifest.json", "validation.json", "parity.json"):
        assert os.path.exists(os.path.join(pdir, f)), f
    assert man["integrity_state"] == "roundtrip_verified"
    assert man["parity_state"] == "parity_pending"        # sin oráculo
    cat = store.catalog_df(root)
    assert len(cat) == 1 and cat[0]["run_id"] == rid
    assert cat[0]["n_zones"] == man["counts"]["n_zones"]


def test_idempotent_republish(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    m1, _, rid = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    m2, _, _ = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    assert m1["digests"] == m2["digests"]
    assert len(store.catalog_df(root)) == 1                # no duplica


def test_determinism_error_on_divergent_rewrite(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    man, res, rid = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    # un resultado VÁLIDO pero distinto (otros params) publicado bajo el MISMO
    # run_id -> internamente consistente (pasa P3.1) pero digests distintos.
    other = _run_kernel("Gaps2", tk, bars, fps, {"min_gap_ticks": 3, "export_floor_ticks": 4})
    assert store.zones_core_digest_from_kernel(other["zones"], tk.tick_size) != \
        man["digests"]["zone_core"]
    with pytest.raises(store.DeterminismError):
        store.publish_run(
            root, kernel_result=other, indicator="Gaps2", tick_size=tk.tick_size,
            instrument=tk.instrument, contract=tk.contract, bar_key=man["bar_key"],
            dataset_id=man["dataset_id"], kernel_id=man["kernel_id"],
            config_id=man["config_id"], run_id=rid, params=other["params"],
            source=dict(kind="synthetic"), generated_utc="x")


def test_zero_zones_is_valid(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    # aVolCellPOI2 con historia pobre -> 0 zonas (resultado válido, no ausencia)
    man, res, rid = _publish(root, "aVolCellPOI2", {}, tk, bars, fps)
    assert man["counts"]["n_zones"] == 0
    cat = store.catalog_df(root)
    assert cat and cat[0]["n_zones"] == 0                  # partición presente


def test_roundtrip_digests_match_manifest(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    man, _, rid = _publish(root, "BigTrap2", {"imbalance_ratio": 1.5}, tk, bars, fps)
    pdir = store.partition_dir(
        root, instrument=tk.instrument, contract=tk.contract, indicator="BigTrap2",
        kernel_id=man["kernel_id"], bar_key=man["bar_key"],
        config_id=man["config_id"], run_id=rid)
    rt = store._roundtrip_digests(pdir)
    assert rt["event"] == man["digests"]["event"]
    assert rt["zone"] == man["digests"]["zone"]
    assert rt["observation"] == man["digests"]["observation"]


def test_parity_state_from_gate(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    m_pass, _, _ = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps,
                            parity=dict(gate="PASS"))
    assert m_pass["parity_state"] == "parity_exact"
    m_fail, _, _ = _publish(root, "Gaps2", {"min_gap_ticks": 4}, tk, bars, fps,
                            parity=dict(gate="FAIL"))
    assert m_fail["parity_state"] == "parity_failed"


def test_set_state_updates_axes_without_touching_parquets(tmp_path, data):
    tk, bars, fps = data
    root = tmp_path / "store"
    man, _, rid = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    pdir = store.partition_dir(
        root, instrument=tk.instrument, contract=tk.contract, indicator="Gaps2",
        kernel_id=man["kernel_id"], bar_key=man["bar_key"],
        config_id=man["config_id"], run_id=rid)
    z_before = os.path.getmtime(os.path.join(pdir, "zones.parquet"))
    store.set_state(root, rid, integrity_state="api_verified", parity_state="parity_exact")
    cat = {c["run_id"]: c for c in store.catalog_df(root)}[rid]
    assert cat["integrity_state"] == "api_verified"
    assert cat["parity_state"] == "parity_exact"
    assert os.path.getmtime(os.path.join(pdir, "zones.parquet")) == z_before  # inmutable
    with pytest.raises(ValueError):
        store.set_state(root, rid, integrity_state="nonsense")


def test_zones_reconstructable_from_events_all_kernels(tmp_path, data):
    tk, bars, fps = data
    for name in REGISTRY:
        res = _run_kernel(name, tk, bars, fps, {})
        dk = store.zones_core_digest_from_kernel(res["zones"], tk.tick_size)
        de = store.zones_core_digest_from_events(
            res["csv_lines"], res.get("header"), res.get("params_line"),
            name, "UTC", tk.tick_size)
        assert dk == de, f"{name}: zones no reconstruibles desde events"
