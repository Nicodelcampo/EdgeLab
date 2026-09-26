"""vectorbt es OPCIONAL (extra research-vectorbt). Marcado 'vectorbt':
`pytest -m "not vectorbt"` lo excluye; sin el extra instalado se reporta SKIP.
No usa datos reales ni ejecuta los scripts vectorbt del repo."""
import pytest

pytestmark = pytest.mark.vectorbt


def test_vectorbt_module_apis_exist():
    vbt = pytest.importorskip("vectorbt")
    for cls in ("Portfolio", "MA", "ATR", "BBANDS", "RSI"):
        assert hasattr(vbt, cls), f"falta vbt.{cls}"
    assert hasattr(vbt.Portfolio, "from_signals")
    assert hasattr(vbt.MA, "run")


def test_vectorbt_from_signals_runtime():
    vbt = pytest.importorskip("vectorbt")
    import numpy as np
    import pandas as pd
    idx = pd.date_range("2025-01-01", periods=40, freq="1D")
    close = pd.Series(100 + np.cumsum(np.random.RandomState(0).randn(40)), index=idx)
    entries = pd.Series(False, index=idx); entries.iloc[5] = True
    exits = pd.Series(False, index=idx); exits.iloc[20] = True
    pf = vbt.Portfolio.from_signals(close=close, entries=entries, exits=exits, freq="1D")
    assert int(pf.trades.count()) >= 0
    assert isinstance(float(pf.total_return()), float)
