"""Workspace paths only; importing this module never creates directories.

Set EDGELAB_ROOT explicitly for data operations. Without it the current working
folder is used, NOT a developer's Windows installation or site-packages.
Legacy sources must be selected explicitly; these defaults grant no permission
and do not certify any source. Campaign manifests remain authoritative.
"""
import os
from pathlib import Path


def _path(name, default):
    value = os.environ.get(name)
    if value is not None and not value.strip():
        raise ValueError(f"{name} must not be empty")
    return Path(value if value is not None else default).expanduser().resolve()


ROOT = _path("EDGELAB_ROOT", Path.cwd())
DATA_DIR = _path("EDGELAB_DATA_DIR", ROOT / "data")
RUNS_DIR = _path("EDGELAB_RUNS_DIR", ROOT / "runs")

# Paths are not evidence of validity or authorization. No source is read here.
ES_TICKS = _path("EDGELAB_ES_TICKS", DATA_DIR / "es_ticks.parquet")
ES_M1 = _path("EDGELAB_ES_M1", DATA_DIR / "es_m1_candles.parquet")
NQ_RAW_DIR = _path("EDGELAB_NQ_RAW_DIR", DATA_DIR / "nt8_raw")
NQ_CONTRACTS = ["NQ 09-25.Last.txt", "NQ 12-25.Last.txt", "NQ 03-26.Last.txt",
                "NQ 06-26.Last.txt", "NQ 09-26.Last.txt"]
NQ_TICKS_CLEAN = _path("EDGELAB_NQ_TICKS_CLEAN", DATA_DIR / "nq_ticks_clean.parquet")
NQ_M1_CLEAN = _path("EDGELAB_NQ_M1_CLEAN", DATA_DIR / "nq_m1_clean.parquet")
EURUSD_TICKS_RAW = _path("EDGELAB_EURUSD_TICKS_RAW", DATA_DIR / "EURUSD_ticks.csv")
EURUSD_TICKS = _path("EDGELAB_EURUSD_TICKS", DATA_DIR / "eurusd_ticks.parquet")


def prepare_workspace():
    """Explicit directory setup only; never loads or validates market data."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


# --- VENTANAS ENVENENADAS de ES_ticks.parquet (hallazgo EXP-044) ---
# En las semanas de roll la cinta entrelaza DOS contratos (~55 pts aparte,
# mismo ms): 670k saltos >5pt en mar-16..20 y 478k en jun-11..15. Toda señal
# tick-level generada ahi es artefactual. Se excluyen mecanicamente via
# poison_mask(); el fix real requiere re-export por contrato (como el NQ).
ES_POISON_WINDOWS = [("2026-03-15", "2026-03-21"),
                     ("2026-06-11", "2026-06-16")]


def poison_mask(times_ms, windows=None):
    """bool[]: True si el timestamp cae en una ventana envenenada."""
    import numpy as np
    import pandas as pd
    if windows is None:
        windows = ES_POISON_WINDOWS
    t = np.asarray(times_ms, dtype=np.int64)
    out = np.zeros(len(t), dtype=bool)
    for a, b in windows:
        a_ms = int(pd.Timestamp(a).value // 10**6)
        b_ms = int(pd.Timestamp(b).value // 10**6)
        out |= (t >= a_ms) & (t < b_ms)
    return out
