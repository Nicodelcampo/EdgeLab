import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("tickbar_diag_v2", ROOT / "tools" / "tickbar_diag_v2.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Bars:
    open_t = np.array([10, 20, 30])
    high_t = np.array([12, 22, 32])
    low_t = np.array([9, 19, 29])
    close_t = np.array([11, 21, 31])
    def __len__(self): return 3


def nt(n_events=(7, 13, 10)):
    return [dict(o=10+i*10, h=12+i*10, l=9+i*10, c=11+i*10,
                 n_events=n_events[i]) for i in range(3)]


def test_h2_uses_ohlc_not_n_events():
    # Attribution can differ in every bar while cuts remain exactly equal.
    off, score, _ = mod.align_by_ohlc(nt(), Bars())
    assert off == 0 and score == 3
    assert all(mod.ohlc_equal(b, Bars(), i) for i, b in enumerate(nt()))


def test_attribution_signature_is_reachable():
    assert mod.classify(True, True, False) == "ATTRIBUTION_MISMATCH"


def test_bar_builder_requires_direct_ohlc_disagreement():
    assert mod.classify(True, False, None) == "BAR_BUILDER_MISMATCH"


def test_stream_precedes_other_classifications():
    assert mod.classify(False, False, None) == "STREAM_MISMATCH"
