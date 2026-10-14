"""Calendario de sesiones DERIVADO DE LOS DATOS (D05, D06). No sustituye al calendario oficial de CME.

Un día laborable puede estar: OPEN (sesión normal), SHORT (cierre temprano / volumen muy bajo), CLOSED (feriado: el mercado
no operó, lo muestran TODOS los activos a la vez) o MISSING_EXPORT (los demás activos operaron y éste no tiene datos:
falta el export, NO es un cero). Los fines de semana no son sesiones.

Un día laborable sin datos en NINGÚN activo no aparece en la tabla y se trata como no-sesión: si fue un hueco de
export de todo el universo, no se distingue de un feriado (límite declarado).

Límite honesto: la derivación usa los volúmenes del propio día para clasificarlo. Eso sirve para saber qué fechas son
sesiones y cuál es D-1; no interviene en la elección del contrato de S (que usa sólo D-1). El calendario oficial histórico
de CME sigue pendiente como evidencia externa.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CLOSED_FRAC = 0.05       # < 5 % del volumen de referencia del activo => cerrado
SHORT_FRAC = 0.50        # < 50 % => sesión corta
PEERS_OPEN_FRAC = 0.60   # si >= 60 % de los demás activos está OPEN y éste no tiene datos => MISSING_EXPORT


def _weekday(td: int) -> int:
    return pd.Timestamp(str(td)).dayofweek


def derive_calendar(daily: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """daily: instrument, trade_date, vol (volumen regular total del activo ese día, 0/ausente si no hay datos).
    Devuelve instrument, trade_date, status, ref_vol, vol."""
    daily = daily.copy()
    alld = sorted(daily["trade_date"].unique())
    insts = sorted(daily["instrument"].unique())
    full = pd.MultiIndex.from_product([insts, alld], names=["instrument", "trade_date"]).to_frame(index=False)
    full = full.merge(daily, on=["instrument", "trade_date"], how="left").fillna({"vol": 0})
    full["weekday"] = full["trade_date"].map(_weekday)
    out = []
    for inst, g in full.groupby("instrument"):
        g = g.sort_values("trade_date").reset_index(drop=True)
        wk = g["weekday"] < 5
        v = g["vol"].where(wk & (g["vol"] > 0))
        # referencia: mediana de las `window` sesiones vecinas con datos (sin mirar el propio día)
        ref = pd.Series(np.nan, index=g.index)
        for i in g.index:
            lo, hi = max(0, i - window), min(len(g), i + window + 1)
            nb = v.iloc[lo:hi].drop(index=i, errors="ignore").dropna()
            ref.iloc[i] = nb.median() if len(nb) >= 3 else np.nan
        g["ref_vol"] = ref
        out.append(g)
    cal = pd.concat(out, ignore_index=True)
    ratio = cal["vol"] / cal["ref_vol"]
    cal["status"] = np.select(
        [cal["weekday"] >= 5, ratio >= SHORT_FRAC, ratio >= CLOSED_FRAC, cal["vol"] > 0],
        ["WEEKEND", "OPEN", "SHORT", "SHORT"], default="NO_DATA")
    # NO_DATA: o feriado (todos cerrados) o export faltante (los pares operaron)
    weekday_rows = cal[cal["weekday"] < 5]
    peers = weekday_rows.assign(open_=weekday_rows["status"].isin(["OPEN", "SHORT"])).groupby("trade_date")["open_"].mean()
    cal["peers_open_frac"] = cal["trade_date"].map(peers)
    nod = cal["status"] == "NO_DATA"
    cal.loc[nod & (cal["peers_open_frac"] >= PEERS_OPEN_FRAC), "status"] = "MISSING_EXPORT"
    cal.loc[nod & (cal["peers_open_frac"] < PEERS_OPEN_FRAC), "status"] = "CLOSED"
    return cal[["instrument", "trade_date", "status", "vol", "ref_vol", "peers_open_frac"]]


def session_days(cal: pd.DataFrame, instrument: str) -> list[int]:
    """Fechas que son sesión para el activo (OPEN/SHORT) o cuyo estado es desconocido (MISSING_EXPORT cuenta como sesión
    con datos desconocidos: no se salta como si fuera feriado, para que D-1 no apunte al día equivocado)."""
    c = cal[(cal["instrument"] == instrument) & cal["status"].isin(["OPEN", "SHORT", "MISSING_EXPORT"])]
    return sorted(int(x) for x in c["trade_date"])
