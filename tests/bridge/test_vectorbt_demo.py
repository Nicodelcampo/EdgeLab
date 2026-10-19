"""Demo vectorbt sobre zonas del store (F8).

El demo combina zonas de 2 indicadores SIN importar kernels. El test de
no-importar-kernels corre siempre; el que ejecuta vectorbt está detrás del
marcador `vectorbt` (extra opcional pesado, deselected por defecto).
"""
import os
import sys

import numpy as np
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))


def _import_lines(path):
    out = []
    for ln in open(path):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            out.append(s)
    return out


def test_demo_does_not_import_kernels():
    # inspeccionar SOLO sentencias import (el docstring puede mencionar el nombre)
    imps = _import_lines(os.path.join(REPO, "tools", "demo_vectorbt_zones.py"))
    assert not any("bridge.indicators" in s or "import gaps2" in s or
                   "import bigtrap2" in s for s in imps), imps


def test_build_signals_combines_two_indicators(tmp_path):
    # store mínimo con 2 indicadores (Gaps2 + BigTrap2) sobre datos sintéticos,
    # publicado vía el store; build_signals los combina sin ejecutar kernels.
    from edgelab.bridge import bars as B, identity as idy, store
    from edgelab.bridge.indicators import gaps2, bigtrap2
    from edgelab.bridge.ticks import make_synthetic
    import demo_vectorbt_zones as demo

    tk = make_synthetic(n_sessions=1, ticks_per_session=6000)
    bars = B.build_time_bars(tk, 1); fps = B.build_footprints(tk, bars)
    root = tmp_path / "store"
    for name, res in (("Gaps2", gaps2.run(tk, bars, params={"min_gap_ticks": 3})),
                      ("BigTrap2", bigtrap2.run(tk, bars, fps, params={"imbalance_ratio": 1.5}))):
        kid = idy.kernel_id(name)
        cid = idy.config_id(name, res["params"], "time_1", "UTC", kid)
        dsid = idy.dataset_id(tk, tz_interpretation="synthetic")
        store.publish_run(root, kernel_result=res, indicator=name, tick_size=tk.tick_size,
                          instrument="SYN", contract="SYN 06-26", bar_key="time_1",
                          dataset_id=dsid, kernel_id=kid, config_id=cid,
                          run_id=idy.run_id(dsid, cid, "s", "e"), params=res["params"],
                          source=dict(kind="synthetic"), generated_utc="x")

    index_ms = (bars.end_ns // 1_000_000).astype(np.int64)
    price = bars.close_t.astype(float) * tk.tick_size
    entries, exits, za, zb = demo.build_signals(str(root), "SYN 06-26", index_ms, price)
    assert len(entries) == len(index_ms) and len(exits) == len(index_ms)
    assert entries.dtype == bool and exits.dtype == bool
    assert len(za) > 0 and len(zb) > 0                 # zonas de ambos indicadores
    # sin kernels en la ruta de consumo: features.py no importa indicators
    import edgelab.bridge.features as F
    assert "indicators" not in open(F.__file__).read()


@pytest.mark.vectorbt
def test_run_demo_portfolio(tmp_path):
    vbt = pytest.importorskip("vectorbt")
    from edgelab.bridge import bars as B, identity as idy, store
    from edgelab.bridge.indicators import gaps2, bigtrap2
    from edgelab.bridge.ticks import make_synthetic
    import demo_vectorbt_zones as demo

    tk = make_synthetic(n_sessions=1, ticks_per_session=6000)
    bars = B.build_time_bars(tk, 1); fps = B.build_footprints(tk, bars)
    root = tmp_path / "store"
    for name, res in (("Gaps2", gaps2.run(tk, bars, params={"min_gap_ticks": 3})),
                      ("BigTrap2", bigtrap2.run(tk, bars, fps, params={"imbalance_ratio": 1.5}))):
        kid = idy.kernel_id(name); cid = idy.config_id(name, res["params"], "time_1", "UTC", kid)
        dsid = idy.dataset_id(tk, tz_interpretation="synthetic")
        store.publish_run(root, kernel_result=res, indicator=name, tick_size=tk.tick_size,
                          instrument="SYN", contract="SYN 06-26", bar_key="time_1",
                          dataset_id=dsid, kernel_id=kid, config_id=cid,
                          run_id=idy.run_id(dsid, cid, "s", "e"), params=res["params"],
                          source=dict(kind="synthetic"), generated_utc="x")
    index_ms = (bars.end_ns // 1_000_000).astype(np.int64)
    price = bars.close_t.astype(float) * tk.tick_size
    pf = demo.run_demo(str(root), "SYN 06-26", index_ms, price)
    assert pf is not None
