"""El núcleo Java de la estrategia JForex U1-CRUZADO (nt8_tools/jforex/EdgeLabU1Cruzado.java) da exactamente las señales de
`u1_cruzado.senales` causal sobre los mismos ticks (tools/paridad_jforex_u1.py)."""
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import paridad_jforex_u1 as P  # noqa: E402


@pytest.mark.skipif(not shutil.which("javac"), reason="sin javac")
def test_nucleo_java_igual_a_python(tmp_path):
    rng = np.random.default_rng(7); n = 60_000
    ms = 1764594000000 + np.cumsum(rng.integers(5_000, 25_000, n))
    px = 20000 + np.cumsum(rng.standard_t(3, n) * 0.8)
    T = pd.DataFrame(dict(time_ms=ms, bid=px - 0.5, ask=px + 0.5, bid_vol=1.0, ask_vol=1.0))
    f = tmp_path / "t.csv"; T.to_csv(f, index=False)
    py = P.senales_python(T, 4.0); jf = P.nucleo_java(str(f), 4.0)
    r = P.comparar(py, jf)
    assert len(py) > 0 and r["ok"], r
