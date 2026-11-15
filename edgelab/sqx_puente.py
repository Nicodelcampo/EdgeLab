"""Puente SQX → EdgeLab (2026-11-15): t por estrategia de un databank de SQX y comparación real vs nulo (nulo de la búsqueda).

SQX no publica el desvío por operación; con riesgo fijo (R = P/L / RIESGO_USD) se reconstruye la media y el segundo momento de cada
estrategia desde «Net profit», «# of trades», «Avg. Win» y «Avg. Loss» (IS y OOS de SQX, combinados = todo el tramo de construcción):
p = (media − pérdida media) / (ganancia media − pérdida media); E[x²] ≈ p·W² + (1−p)·L². Aproxima la varianza (ignora la dispersión
DENTRO de ganadoras y perdedoras: con SL/TP en ATR es chica) y se aplica IGUAL al real y al nulo, así que la comparación es justa.
Las candidatas que pasan se re-miden exacto con sus operaciones (`tools/sqx_corrida.py exportar`) y `edgelab/research/sqx_calidad.py`."""
from __future__ import annotations

import numpy as np
import pandas as pd

RIESGO_USD = 1000.0
COLS = ["Net profit (IS)", "# of trades (IS)", "Avg. Win (IS)", "Avg. Loss (IS)", "Net profit (OOS)", "# of trades (OOS)", "Avg. Win (OOS)", "Avg. Loss (OOS)"]


def _n(x):
    try: return float(str(x).replace(",", "").replace("$", "").strip())
    except ValueError: return np.nan


def filas(cliente, proyecto: str, databank: str = "Results") -> pd.DataFrame:
    out, off = [], 0
    while True:
        r = cliente.llamar("query_databank", {"name": proyecto, "databank": databank, "columns": ",".join(COLS), "limit": 500, "offset": off})
        rows = r.get("rows", []); out += [[x["strategy"]] + [_n(v) for v in x["values"]] for x in rows]; off += len(rows)
        if not rows or off >= r.get("totalRows", 0): break
    return pd.DataFrame(out, columns=["estrategia"] + COLS)


def t_por_estrategia(D: pd.DataFrame) -> pd.DataFrame:
    def parte(s):
        n, net, W, L = D[f"# of trades ({s})"].fillna(0), D[f"Net profit ({s})"].fillna(0), D[f"Avg. Win ({s})"].fillna(0), D[f"Avg. Loss ({s})"].fillna(0)
        L = -L.abs(); m = np.where(n > 0, net / n.where(n > 0, 1), 0.0)
        p = np.clip(np.where((W - L) > 0, (m - L) / (W - L).where((W - L) > 0, 1), 0.5), 0, 1)
        return n, net, n * (p * W ** 2 + (1 - p) * L ** 2)
    nI, netI, sI = parte("IS"); nO, netO, sO = parte("OOS")
    n = nI + nO; m = (netI + netO) / n.where(n > 0, np.nan) / RIESGO_USD
    var = (sI + sO) / n.where(n > 0, np.nan) / RIESGO_USD ** 2 - m ** 2
    return D.assign(n=n, r=m, t=m / np.sqrt(var.clip(lower=1e-12) / n))


def comparar(real: pd.DataFrame, nulo: pd.DataFrame, n_min: int = 200) -> dict:
    """Umbral = máximo t del NULO (con un solo nulo no hay p95 del máximo: es la vara más estricta disponible) entre las estrategias con
    ≥ n_min operaciones; candidatas = reales por encima. Además los cuantiles de ambos para ver si el real se distingue del ruido."""
    R, N = real[real.n >= n_min], nulo[nulo.n >= n_min]
    q = lambda x: {f"p{k}": round(float(np.nanpercentile(x, k)), 2) for k in (50, 90, 99)} | {"max": round(float(np.nanmax(x)), 2)} if len(x) else {}
    umbral = float(np.nanmax(N.t)) if len(N) else np.inf
    cand = R[R.t > umbral].sort_values("t", ascending=False)
    return dict(n_real=int(len(R)), n_nulo=int(len(N)), t_real=q(R.t), t_nulo=q(N.t), umbral_max_nulo=round(umbral, 2),
                candidatas=cand[["estrategia", "n", "r", "t"]].round(3).to_dict("records"))
