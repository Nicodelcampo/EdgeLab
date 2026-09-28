"""Familia 6E-REGIMES, etapa 1 (target-free): sustituto de profundidad calculable con ticks, su verdad L2 y su
persistencia. Protocolo congelado en `docs/research/FAMILIA_6E_REGIMENES_LIQUIDEZ_20260924.md`.

Nada de este modulo mira retornos: P1 usa cambios del precio medio DENTRO del bloque (estado contemporaneo), nunca
lo que pasa despues.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CHICAGO = "America/Chicago"
NS = 1_000_000_000
HALT_START_MIN, HALT_END_MIN = 16 * 60, 17 * 60      # pausa diaria CME, hora de Chicago


def session_date(ts_utc_ns) -> np.ndarray:
    """Dia de sesion CME como int yyyymmdd: fecha de (hora de Chicago + 7 h). La sesion 17:00-16:00 CT cae entera en
    un dia (el domingo a la tarde abre la sesion del lunes)."""
    loc = pd.to_datetime(np.asarray(ts_utc_ns), utc=True).tz_convert(CHICAGO) + pd.Timedelta(hours=7)
    return (loc.year * 10000 + loc.month * 100 + loc.day).to_numpy()


def block_proxy(ts_utc_ns, volume, bid, ask, block_s: int = 900) -> pd.DataFrame:
    """Un renglon por (sesion, bloque UTC alineado). P1 = contratos / max(1, cambios del precio medio), donde el medio
    se toma del bid/ask vigente en cada trade y un cambio es un trade cuyo bid+ask difiere del trade anterior de la
    MISMA sesion. Marca `halt` si el bloque empieza dentro de la pausa 16:00-17:00 CT (con bloques <= 60 min alineados
    a la hora, es exactamente "toca la pausa"). Entradas en orden de llegada."""
    if 3600 % block_s:
        raise ValueError("block_s must divide 3600 (bloques alineados a la hora)")
    ts = np.asarray(ts_utc_ns, dtype=np.int64)
    if len(ts) and np.any(np.diff(ts) < 0):
        raise ValueError("trades must be in time order")
    sess = session_date(ts)
    mid2 = np.asarray(bid, dtype=np.int64) + np.asarray(ask, dtype=np.int64)
    chg = np.zeros(len(ts), dtype=np.int64)
    if len(ts) > 1:
        chg[1:] = (mid2[1:] != mid2[:-1]) & (sess[1:] == sess[:-1])
    blk = ts // (block_s * NS) * (block_s * NS)
    df = pd.DataFrame(dict(session=sess, block=blk, volume=np.asarray(volume, dtype=np.int64), chg=chg, one=1))
    g = df.groupby(["session", "block"], sort=True).agg(volume=("volume", "sum"), mid_changes=("chg", "sum"),
                                                         trades=("one", "sum")).reset_index()
    g["p1"] = g["volume"] / np.maximum(1, g["mid_changes"])
    g["log_p1"] = np.log(g["p1"])
    loc = pd.to_datetime(g["block"], utc=True).dt.tz_convert(CHICAGO)
    g["hour_ct"] = loc.dt.hour
    mod = loc.dt.hour * 60 + loc.dt.minute
    g["halt"] = (mod >= HALT_START_MIN) & (mod < HALT_END_MIN)
    return g


def truth_blocks(snap_t_utc_ns, bid_sz, ask_sz, block_s: int = 900, levels: int = 5) -> pd.DataFrame:
    """Verdad L2 por bloque: T1 = media de (mejor bid + mejor ask)/2; T2 = media de (suma de `levels` niveles de cada
    lado)/2, sobre las fotos (~1 s) del bloque."""
    t = np.asarray(snap_t_utc_ns, dtype=np.int64)
    b, a = np.asarray(bid_sz, dtype=float), np.asarray(ask_sz, dtype=float)
    df = pd.DataFrame(dict(block=t // (block_s * NS) * (block_s * NS), t1=(b[:, 0] + a[:, 0]) / 2,
                           t2=(b[:, :levels].sum(1) + a[:, :levels].sum(1)) / 2))
    return df.groupby("block").agg(t1=("t1", "mean"), t2=("t2", "mean"), snaps=("t1", "size")).reset_index()


def spearman(x, y) -> float:
    x, y = pd.Series(np.asarray(x, float)), pd.Series(np.asarray(y, float))
    ok = x.notna() & y.notna()
    if ok.sum() < 3:
        return float("nan")
    return float(x[ok].rank().corr(y[ok].rank()))


def hour_profile(blocks: pd.DataFrame, col: str = "log_p1") -> pd.Series:
    """Mediana de `col` por hora de Chicago (perfil horario)."""
    return blocks.groupby("hour_ct")[col].median()


def within_session_autocorr(blocks: pd.DataFrame, col: str, lag: int, block_s: int, min_pairs: int = 10) -> pd.Series:
    """Correlacion de Pearson, por sesion, entre `col` en el bloque k y en el bloque k+lag (mismo dia, ambos
    presentes). Devuelve una serie indexada por sesion (NaN si hay menos de `min_pairs` pares)."""
    step = lag * block_s * NS
    out = {}
    for s, d in blocks.groupby("session"):
        v = d.set_index("block")[col]
        nxt = v.reindex(v.index + step)
        ok = v.notna().to_numpy() & nxt.notna().to_numpy()
        if ok.sum() < min_pairs:
            out[s] = np.nan
            continue
        out[s] = float(np.corrcoef(v.to_numpy()[ok], nxt.to_numpy()[ok])[0, 1])
    return pd.Series(out, dtype=float)


def session_bootstrap_mean(values, n_boot: int = 5000, seed: int = 20260924):
    """Media entre sesiones con IC 95 % por bootstrap de sesiones. [media, lo, hi, n]."""
    x = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if len(x) < 3:
        return None
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (n_boot, len(x)))].mean(1)
    return [float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(len(x))]
