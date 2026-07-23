"""Zone store formal (F6): round-trip, flag trusted, filtros y features.

El store es el producto reutilizable del bridge: la fuerza bruta consume zonas
por identidad (indicator, param_set_id, bar_key, contract) SIN recomputar. El
flag `trusted` solo se activa con paridad real P2 (PASS).
"""
import json

from edgelab.bridge import zone_store


def _zone(zid, top, bottom, created_ms, state="ACTIVE", **feats):
    z = dict(id=zid, indicator="HFTZones2", top=top, bottom=bottom,
             created_ms=created_ms, ended_ms=None, state=state, kind="support_fast",
             touches=0, end_reason=None, timeline=[{"ms": created_ms}])
    z.update(feats)
    return z


def test_write_and_query_roundtrip(tmp_path):
    root = tmp_path / "store"
    zones = [_zone("Z000001", 1.1000, 1.0995, 1000, dir=1, bucket="FAST", calib_id=2),
             _zone("Z000002", 1.1010, 1.1005, 2000, dir=-1, bucket="ULTRA", calib_id=2)]
    m = zone_store.write_partition(
        root, indicator="HFTZones2", param_set_id="abc123", bar_key="time_1",
        contract="6E 09-25", instrument="6E", tick_size=0.00005, zones=zones,
        params=dict(min_pasos=8), parity=None)
    assert m["n_zones"] == 2 and m["trusted"] is False
    t = zone_store.query_zones(root)
    assert t.num_rows == 2
    cols = set(t.column_names)
    assert {"zone_id", "top_ticks", "bottom_ticks", "features", "param_set_id"} <= cols
    # features preserva los campos propios del kernel (dir/bucket/calib_id)
    feats = json.loads(t.column("features")[0].as_py())
    assert feats["dir"] == 1 and feats["bucket"] == "FAST" and feats["calib_id"] == 2
    # top_ticks calculado desde tick_size
    assert t.column("top_ticks")[0].as_py() == round(1.1000 / 0.00005)


def test_trusted_only_on_parity_pass(tmp_path):
    root = tmp_path / "store"
    z = [_zone("Z1", 1.1, 1.09, 500)]
    common = dict(indicator="Gaps2", bar_key="time_1", contract="6E 06-26",
                  instrument="6E", tick_size=0.00005, zones=z, params={})
    zone_store.write_partition(root, param_set_id="pass1",
                               parity=dict(gate="PASS"), **common)
    zone_store.write_partition(root, param_set_id="warn1",
                               parity=dict(gate="WARN"), **common)
    zone_store.write_partition(root, param_set_id="none1", parity=None, **common)
    mans = {m["param_set_id"]: m["trusted"] for m in zone_store.list_partitions(root)}
    assert mans == {"pass1": True, "warn1": False, "none1": False}
    # query trusted_only devuelve solo la partición PASS
    t = zone_store.query_zones(root, trusted_only=True)
    assert t.num_rows == 1
    assert set(t.column("param_set_id").to_pylist()) == {"pass1"}


def test_query_filters(tmp_path):
    root = tmp_path / "store"
    zones = [_zone("Z1", 1.1, 1.09, 1000, state="ACTIVE"),
             _zone("Z2", 1.2, 1.19, 5000, state="INVALIDATED"),
             _zone("Z3", 1.3, 1.29, 9000, state="ACTIVE")]
    zone_store.write_partition(
        root, indicator="HFTZones2", param_set_id="p1", bar_key="time_1",
        contract="6E 09-25", instrument="6E", tick_size=0.00005, zones=zones,
        params={}, parity=None)
    # por estado
    assert zone_store.query_zones(root, state="ACTIVE").num_rows == 2
    # por rango de created_ms [2000, 9500)
    t = zone_store.query_zones(root, created_after_ms=2000, created_before_ms=9500)
    assert set(t.column("zone_id").to_pylist()) == {"Z2", "Z3"}
    # por indicador inexistente
    assert zone_store.query_zones(root, indicator="Nope").num_rows == 0


def test_partition_layout_on_disk(tmp_path):
    root = tmp_path / "store"
    zone_store.write_partition(
        root, indicator="BigTrap2", param_set_id="ps9", bar_key="tick_25",
        contract="6E 09-25", instrument="6E", tick_size=0.00005,
        zones=[_zone("7_B", 1.1, 1.09, 1000)], params={}, parity=None)
    pdir = zone_store.partition_dir(root, "BigTrap2", "ps9", "tick_25", "6E 09-25")
    import os
    assert os.path.exists(os.path.join(pdir, "zones.parquet"))
    assert os.path.exists(os.path.join(pdir, "manifest.json"))
    # el contract con espacio se sanitiza en el path pero se preserva en columnas
    assert "6E_09-25" in pdir
    t = zone_store.query_zones(root)
    assert t.column("contract")[0].as_py() == "6E 09-25"


def test_rewrite_partition_is_idempotent(tmp_path):
    root = tmp_path / "store"
    args = dict(indicator="Gaps2", param_set_id="p1", bar_key="time_1",
                contract="6E 09-25", instrument="6E", tick_size=0.00005, params={})
    zone_store.write_partition(root, zones=[_zone("Z1", 1.1, 1.09, 1)], parity=None, **args)
    zone_store.write_partition(root, zones=[_zone("Z1", 1.1, 1.09, 1),
                                            _zone("Z2", 1.2, 1.19, 2)], parity=None, **args)
    # la reescritura reemplaza, no acumula
    assert zone_store.query_zones(root).num_rows == 2
    assert len(zone_store.list_partitions(root)) == 1
