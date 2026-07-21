"""Rutas de EdgeLab. Las fuentes externas son SOLO LECTURA y ya validadas."""
from pathlib import Path

ROOT = Path(r"C:\ProyectosQuant\EdgeLab")
DATA_DIR = ROOT / "data"
RUNS_DIR = ROOT / "runs"

# --- fuentes validadas del ecosistema (read-only) ---
ES_TICKS = Path(r"C:\$AVectorBTecosistema\ES_ticks.parquet")        # 148.8M ticks, bid/ask, dic30-jul10
ES_M1 = Path(r"C:\$AVectorBTecosistema\data\es_m1_candles.parquet")  # regeneradas de ticks, indice ns

# --- fuentes crudas NQ (exports por contrato, NT8, orden cronologico) ---
NQ_RAW_DIR = Path(r"D:\A  Trading")
NQ_CONTRACTS = ["NQ 09-25.Last.txt", "NQ 12-25.Last.txt", "NQ 03-26.Last.txt",
                "NQ 06-26.Last.txt", "NQ 09-26.Last.txt"]

# --- artefactos propios (se generan con databuild/, gate de validacion previo) ---
NQ_TICKS_CLEAN = DATA_DIR / "nq_ticks_clean.parquet"
NQ_M1_CLEAN = DATA_DIR / "nq_m1_clean.parquet"
EURUSD_TICKS_RAW = Path(r"C:\Users\nicoc\JForex4\viewer\data\EURUSD_ticks.csv")
EURUSD_TICKS = DATA_DIR / "eurusd_ticks.parquet"

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

DATA_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)
