"""CLI end-to-end (sintético, tmp_path): artefactos completos, param grid con
runs separados por param_set_id, zone store parquet, bundle del visor válido."""
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import run_nt8_bridge as cli  # noqa: E402


def test_cli_synthetic_end_to_end(tmp_path):
    out = tmp_path / "demo"
    rc = cli.main(["--synthetic", "--indicator", "Gaps2", "--bars", "time:1",
                   "--param-grid", 'Gaps2=[{"min_gap_ticks":3},{"min_gap_ticks":8,"bars":"tick:50"}]',
                   "--chart-tz", "America/Argentina/Buenos_Aires",
                   "--out", str(out)])
    assert rc == 0
    man = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert len(man["runs"]) == 2
    ids = {r["param_set_id"] for r in man["runs"]}
    assert len(ids) == 2                                  # identidades distintas
    keys = {r["bar_key"] for r in man["runs"]}
    assert keys == {"time_1", "tick_50"}                  # bar spec por param set
    for r in man["runs"]:
        assert (out / r["events_csv"]).exists()
        assert r["p1a"] == "PASS"
        assert r["parity_gate"] is None                   # sin oráculo: jamás PASS implícito

    # zone store: identidad completa por zona
    t = pq.read_table(out / "zones.parquet")
    assert t.num_rows > 0
    cols = set(t.column_names)
    assert {"indicator", "param_set_id", "bar_key", "zone_id", "top_ticks",
            "bottom_ticks", "created_ms", "ended_ms", "state"} <= cols
    assert set(t.column("param_set_id").to_pylist()) == ids

    # bundle del visor: data.js parseable + vendor local copiado
    data_js = (out / "viewer" / "data.js").read_text(encoding="utf-8")
    assert data_js.startswith("window.BRIDGE_DATA = ")
    bundle = json.loads(data_js[len("window.BRIDGE_DATA = "):].rstrip().rstrip(";"))
    assert set(bundle["bar_series"].keys()) == {"time_1", "tick_50"}
    assert len(bundle["runs"]) == 2
    assert all(r["zones"] for r in bundle["runs"])
    assert (out / "viewer" / "index.html").exists()
    assert (out / "viewer" / "vendor" / "lightweight-charts.standalone.production.js").exists()
    assert (out / "p1a_report.json").exists()


def test_cli_param_set_id_stable(tmp_path):
    from edgelab.bridge.viewer_export import param_set_id
    a = param_set_id({"x": 1, "y": 2.0}, "time_1")
    b = param_set_id({"y": 2.0, "x": 1}, "time_1")       # orden de claves irrelevante
    c = param_set_id({"x": 1, "y": 2.0}, "tick_25")      # bar spec cambia la identidad
    assert a == b and a != c and len(a) == 10
