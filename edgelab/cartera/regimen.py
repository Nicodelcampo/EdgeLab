"""Régimen diario por instrumento, conocido ANTES de operar el día D (sólo usa cierres hasta D−1).

Rasgos: `rv_rel` = rango medio de 5 días / rango medio de 60 días (expansión o compresión de volatilidad); `t_nw` = t de Newey-West
de los retornos diarios de 20 días (tendencia medida sobre retornos, nunca la t de una regresión en niveles: Prop. 3.6 del paper de
Tori Trades); `er` = eficiencia de Kaufman de 20 días. Etiqueta = volatilidad (BAJA/MEDIA/ALTA por cortes congelados) | dirección
(ALCISTA si t_nw >= T_DIR, BAJISTA si <= −T_DIR, RANGO si no). Los cortes de volatilidad se congelan una vez sobre desarrollo
(`congelar_cortes`) y se guardan en la configuración: nunca se recalculan mirando el período que se opera.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

T_DIR = 1.5
VOLS, DIRS = ("BAJA", "MEDIA", "ALTA"), ("BAJISTA", "RANGO", "ALCISTA")


def t_newey_west(r) -> float:
    r = np.asarray(r, float); r = r[np.isfinite(r)]; n = len(r)
    if n < 5: return np.nan
    u = r - r.mean(); L = int(np.floor(4 * (n / 100.0) ** (2 / 9))); om = (u @ u) / n
    for j in range(1, L + 1): om += 2 * (1 - j / (L + 1)) * (u[j:] @ u[:-j]) / n
    return float(r.mean() / np.sqrt(om / n)) if om > 0 else np.nan


def rasgos_diarios(diario: pd.DataFrame) -> pd.DataFrame:
    """`diario`: columnas fecha (int yyyymmdd), h, l, c, ordenado. Devuelve los rasgos que valen PARA el día de cada fila (calculados
    con los días anteriores: desplazados una fila)."""
    d = diario.sort_values("fecha").reset_index(drop=True)
    rango = (d.h - d.l).astype(float); c = d.c.astype(float); r = np.log(c).diff()
    rv_rel = rango.rolling(5).mean() / rango.rolling(60).mean()
    tnw = r.rolling(20).apply(t_newey_west, raw=True)
    mov = c.diff().abs().rolling(20).sum(); er = (c - c.shift(20)).abs() / mov
    out = pd.DataFrame(dict(fecha=d.fecha, rv_rel=rv_rel.shift(1), t_nw=tnw.shift(1), er=er.shift(1)))
    return out


def congelar_cortes(rasgos: pd.DataFrame, hasta: int) -> dict:
    x = rasgos.loc[rasgos.fecha <= hasta, "rv_rel"].dropna()
    return dict(rv_rel=[float(x.quantile(1 / 3)), float(x.quantile(2 / 3))], t_dir=T_DIR, desarrollo_hasta=int(hasta), n=int(len(x)))


def etiquetar(rasgos: pd.DataFrame, cortes: dict) -> pd.Series:
    a, b = cortes["rv_rel"]; td = cortes.get("t_dir", T_DIR)
    vol = np.where(rasgos.rv_rel < a, 0, np.where(rasgos.rv_rel < b, 1, 2))
    dir_ = np.where(rasgos.t_nw >= td, 2, np.where(rasgos.t_nw <= -td, 0, 1))
    ok = rasgos.rv_rel.notna() & rasgos.t_nw.notna()
    et = [f"{VOLS[v]}|{DIRS[d]}" if k else None for v, d, k in zip(vol, dir_, ok)]
    return pd.Series(et, index=rasgos.fecha.values, name="regimen")


def diario_desde_m1(ctx: dict) -> pd.DataFrame:
    """Barras diarias por sesión CME desde un contexto M1 (`grilla_generica.contexto_m1`)."""
    df = pd.DataFrame(dict(ses=np.asarray(ctx["ses"]), h=ctx["h"], l=ctx["l"], c=ctx["c"]))
    g = df.groupby("ses", sort=True).agg(h=("h", "max"), l=("l", "min"), c=("c", "last")).reset_index()
    return g.rename(columns={"ses": "fecha"})
