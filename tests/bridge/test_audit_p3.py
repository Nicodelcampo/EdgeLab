"""Gate P3 — auditor adversarial (F6.3).

Un auditor que solo vio datos sanos no es evidencia: acá se corrompen copias a
propósito y se exige que audit_partition/audit_all las detecten (ok=False). Los
9 casos del contrato + el verde sobre un store sano.
"""
import json
import os

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from edgelab.bridge import audit, bars as B, identity as idy, store
from edgelab.bridge.indicators import REGISTRY, BAR_DRIVEN
from edgelab.bridge.ticks import make_synthetic


# --------------------------- helpers de publicación ------------------------ #
def _publish(root, name, params, tk, bars, fps, run_id=None):
    mod = REGISTRY[name]
    res = (mod.run(tk, bars, fps, params=params) if name in BAR_DRIVEN
           else mod.run(tk, bars, params=params))
    bkey = f"{bars.kind}_{bars.param}"
    kid = idy.kernel_id(name)
    cid = idy.config_id(name, res["params"], bkey, "UTC", kid)
    dsid = idy.dataset_id(tk, tz_interpretation="synthetic")
    rid = run_id or idy.run_id(dsid, cid, "2026-06-01", "2026-06-03")
    man = store.publish_run(
        root, kernel_result=res, indicator=name, tick_size=tk.tick_size,
        instrument=tk.instrument, contract=tk.contract, bar_key=bkey,
        dataset_id=dsid, kernel_id=kid, config_id=cid, run_id=rid,
        params=res["params"], source=dict(kind="synthetic"), generated_utc="x")
    return man


@pytest.fixture
def store_root(tmp_path):
    tk = make_synthetic(n_sessions=2, ticks_per_session=6000)
    bars = B.build_time_bars(tk, minutes=1)
    fps = B.build_footprints(tk, bars)
    root = tmp_path / "store"
    m1 = _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps)
    m2 = _publish(root, "BigTrap2", {"imbalance_ratio": 1.5}, tk, bars, fps)
    return root, m1, m2, (tk, bars, fps)


def _pdir(root, man):
    return store.partition_dir(
        root, instrument=man["instrument"], contract=man["contract"],
        indicator=man["indicator"], kernel_id=man["kernel_id"],
        bar_key=man["bar_key"], config_id=man["config_id"], run_id=man["run_id"])


def _part_row(root, run_id):
    return store.get_partitions(root, run_id=run_id)[0]


def _rewrite_zones(pdir, mutate):
    rows = store.read_zone_rows(pdir)
    rows = mutate(rows)
    data = {c: [r.get(c) for r in rows] for c in store._ZONE_COLS}
    pq.write_table(pa.table(data), os.path.join(pdir, "zones.parquet"))


# --------------------------- store sano: verde ----------------------------- #
def test_healthy_store_passes(store_root):
    root, m1, m2, _ = store_root
    rep = audit.audit_all(root)
    assert rep["ok"], rep
    assert rep["n_partitions"] == 2
    assert all(r["ok"] for r in rep["partitions"])


# --------------------------- 9 corrupciones -------------------------------- #
def test_1_zona_borrada(store_root):
    root, m1, _, _ = store_root
    _rewrite_zones(_pdir(root, m1), lambda rows: rows[:-1])
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["roundtrip"]["code"] == "DIGEST_MISMATCH"


def test_2_lower_tick_mutado(store_root):
    root, m1, _, _ = store_root
    def mut(rows):
        rows[0]["lower_tick"] += 1
        return rows
    _rewrite_zones(_pdir(root, m1), mut)
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["roundtrip"]["code"] == "DIGEST_MISMATCH"


def test_3_estado_cambiado(store_root):
    root, m1, _, _ = store_root
    def mut(rows):
        rows[0]["final_state"] = "ZZZ"
        return rows
    _rewrite_zones(_pdir(root, m1), mut)
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["roundtrip"]["code"] == "DIGEST_MISMATCH"


def test_4_parametro_manifest_alterado(store_root):
    root, m1, _, _ = store_root
    pdir = _pdir(root, m1)
    man = json.load(open(os.path.join(pdir, "manifest.json")))
    man["params"] = dict(man["params"])
    man["params"]["min_gap_ticks"] = 999          # param alterado, config_id no
    json.dump(man, open(os.path.join(pdir, "manifest.json"), "w"))
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["identity"]["code"] == "MANIFEST_TAMPERED"


def test_5_config_duplicada(store_root):
    root, _, _, data = store_root
    tk, bars, fps = data
    # misma config publicada bajo OTRO run_id -> (dataset,config) en 2 runs
    _publish(root, "Gaps2", {"min_gap_ticks": 3}, tk, bars, fps, run_id="dup_run_id")
    cc = audit.verify_cross_config(root)
    assert not cc["ok"]
    assert any(d["code"] == "DUPLICATE_CONFIG" for d in cc["diagnostics"])


def test_6_config_eliminada_de_campana(store_root):
    root, m1, m2, _ = store_root
    campaign = dict(campaign_id="c1", dataset_id=m1["dataset_id"],
                    expected_config_ids=[m1["config_id"], m2["config_id"], "config_fantasma"])
    c = audit.check_campaign(root, campaign)
    assert not c["ok"] and "config_fantasma" in c["missing"]


def test_7_fila_de_otro_contrato(store_root):
    root, m1, _, _ = store_root
    def mut(rows):
        rows[0]["contract"] = "OTRO 12-99"
        return rows
    _rewrite_zones(_pdir(root, m1), mut)
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["identity"]["code"] == "FOREIGN_ROW"


def test_8_parquet_truncado(store_root):
    root, m1, _, _ = store_root
    zp = os.path.join(_pdir(root, m1), "zones.parquet")
    sz = os.path.getsize(zp)
    with open(zp, "r+b") as fh:
        fh.truncate(sz // 2)
    rep = audit.audit_partition(root, _part_row(root, m1["run_id"]))
    assert not rep["ok"] and rep["checks"]["roundtrip"]["code"] in ("PARQUET_UNREADABLE", "DIGEST_MISMATCH")


def test_9_api_fila_incorrecta(store_root, monkeypatch):
    root, m1, _, _ = store_root
    real = store.get_zones

    def fake(root_, **kw):
        rows = real(root_, **kw)
        if rows:
            rows = [dict(r) for r in rows]
            rows[0]["lower_tick"] = rows[0]["lower_tick"] + 7   # fila incorrecta
        return rows
    monkeypatch.setattr(store, "get_zones", fake)
    res = audit.verify_api(root, json.load(open(os.path.join(_pdir(root, m1), "manifest.json"))))
    assert not res["ok"] and res["code"] == "API_DIGEST_MISMATCH"


# --------------------------- P3.3 recompute + P3.0 verde ------------------- #
def test_campaign_complete_is_ok(store_root):
    root, m1, m2, _ = store_root
    campaign = dict(campaign_id="c1", dataset_id=m1["dataset_id"],
                    expected_config_ids=[m1["config_id"], m2["config_id"]])
    assert audit.check_campaign(root, campaign)["ok"]


def test_recompute_stale_when_kernel_id_differs(store_root):
    root, m1, _, _ = store_root
    man = json.load(open(os.path.join(_pdir(root, m1), "manifest.json")))
    man = dict(man); man["kernel_id"] = "kernel_id_viejo"
    res = audit.verify_recompute(root, man)
    assert res["code"] == "STALE"


def test_recompute_unavailable_for_synthetic(store_root):
    root, m1, _, _ = store_root
    man = json.load(open(os.path.join(_pdir(root, m1), "manifest.json")))
    res = audit.verify_recompute(root, man)
    assert res["code"] == "UNAVAILABLE"          # fuente sintética no recomputable
