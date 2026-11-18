"""Campañas con la partición HOLDOUT-A5 (2026-11-18): lo común a toda familia que descubre y confirma sobre M1 largo.

Enmienda `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`; primer uso `tools/luximb_a5.py` (de ahí se extrajo).
  bloques(ses)            DESC / REP / HOLDOUT / EMBARGO / TERMINAL de cada sesión (`holdout.a5_bloque`)
  con_desenlace(E)        máscara de eventos cuyos desenlaces se pueden calcular sin acta: sólo DESC y REP
  cluster(ses, r)         media por operación, error estándar agrupado por sesión y p unilateral (H1: media > 0)
  diferencia(...)         celda − control con bootstrap por sesión (comparten sesiones y a veces eventos)
  calibrar_por_sesion     criterio de M1 contra ticks (`papel_m1_20261115/VALIDACION.md`, el de `atras_m1`)
  bh(ps, q)               Benjamini–Hochberg
Los eventos (sin retornos) se calculan de corrido en toda la ventana; los desenlaces de HOLDOUT/EMBARGO sólo con la apertura
registrada (`holdout_ventanas.registrar_apertura`) y la reserva de LORD++.
"""
from __future__ import annotations

from math import erfc, sqrt

import numpy as np
import pandas as pd

VISIBLES = ("DESC", "REP")
MIN_CORR, MIN_SES_COMUNES = 0.5, 30


def bloques(ses) -> np.ndarray:
    from edgelab.holdout import a5_bloque
    ses = np.asarray(ses); u = np.unique(ses); m = {int(s): a5_bloque(int(s)) for s in u}
    return np.array([m[int(s)] for s in ses])


def con_desenlace(E: pd.DataFrame, col: str = "bloque") -> np.ndarray:
    return E[col].isin(VISIBLES).to_numpy()


def sf(z: float) -> float:
    """Cola superior de la normal estándar (sin scipy)."""
    return float(0.5 * erfc(z / sqrt(2)))


def cluster(ses, r):
    """(media por operación, error estándar agrupado por sesión, p unilateral de media > 0)."""
    df = pd.DataFrame(dict(s=np.asarray(ses), r=np.asarray(r, float))); g = df.groupby("s").r.agg(["sum", "count"]); n = g["count"].sum()
    if n == 0: return float("nan"), float("nan"), 1.0
    m = g["sum"].sum() / n; se = float(np.sqrt(((g["sum"] - m * g["count"]) ** 2).sum()) / n)
    return float(m), se, sf(m / se) if se > 0 else 1.0


def diferencia(ses_a, r_a, ses_b, r_b, B: int = 2000, seed: int = 7):
    """(a − b, error estándar, p unilateral de a − b > 0) con bootstrap por sesión."""
    a = pd.DataFrame(dict(s=ses_a, r=r_a)).groupby("s").r.agg(["sum", "count"])
    b = pd.DataFrame(dict(s=ses_b, r=r_b)).groupby("s").r.agg(["sum", "count"])
    S = np.array(sorted(set(a.index) | set(b.index))); a = a.reindex(S, fill_value=0); b = b.reindex(S, fill_value=0)
    obs = a["sum"].sum() / a["count"].sum() - b["sum"].sum() / b["count"].sum()
    rng = np.random.default_rng(seed); A = a.to_numpy(float); Bm = b.to_numpy(float); bs = np.empty(B)
    for i in range(B):
        ix = rng.integers(0, len(S), len(S)); sa, sb = A[ix].sum(0), Bm[ix].sum(0); bs[i] = sa[0] / sa[1] - sb[0] / sb[1]
    se = float(bs.std(ddof=1))
    return float(obs), se, sf(obs / se) if se > 0 else 1.0


def bh(ps, q: float):
    from edgelab.research.banco_eventos import bh as _bh
    return _bh(list(ps), q)


def calibrar_por_sesion(t: dict, m: dict) -> dict:
    """M1 contra ticks por sesión ({sesión: R sumado}): mismo signo, diferencia ≤ 1 EE combinado y correlación > 0,5 en ≥ 30 sesiones."""
    ses = sorted(set(t) | set(m)); x = np.array([t.get(s, 0.0) for s in ses]); y = np.array([m.get(s, 0.0) for s in ses])
    com = sorted(set(t) & set(m))
    ee = float(np.sqrt(x.var(ddof=1) / len(x) + y.var(ddof=1) / len(y))) if len(ses) > 2 else float("nan")
    corr = float(np.corrcoef([t[s] for s in com], [m[s] for s in com])[0, 1]) if len(com) > 2 else float("nan")
    out = dict(sesiones=len(ses), comunes=len(com), ticks_media=float(x.mean()), m1_media=float(y.mean()), ee=ee, corr=corr)
    out["calibra"] = bool(len(com) >= MIN_SES_COMUNES and np.sign(x.mean()) == np.sign(y.mean()) and abs(x.mean() - y.mean()) <= ee
                          and corr > MIN_CORR)
    return out


def frac_anios_positivos(ses, r) -> float:
    s = pd.Series(np.asarray(r, float)).groupby(np.asarray(ses) // 10000).sum()
    return float((s > 0).mean()) if len(s) else float("nan")
