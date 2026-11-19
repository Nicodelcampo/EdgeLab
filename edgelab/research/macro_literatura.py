"""Ideas de la literatura con pocos parámetros, medidas directo sobre barras de Dukascopy exportadas de SQX (2026-11-14, pedido de Nico:
«no usar el Builder para lo que no lo necesita»). Pre-registro: docs/research/macro_literatura_20261114/PREREGISTRO.md.

Reglas (fichas del banco de ideas; nada abierto el fin de semana: decisión de Nico 2026-11-14):
  TSMOM   momentum de serie de tiempo: señal = signo del retorno de L días (L 20/60/120/250) al cierre del viernes; se opera de la
          apertura del lunes al cierre del viernes. Una operación por activo y semana.
  FINMES  cambio de mes (índices): compra al cierre del penúltimo día hábil del mes, vende al cierre del día hábil N del mes siguiente
          (N 1/3); si la ventana cruza un fin de semana, sale el viernes al cierre.
  NOCHE   deriva nocturna (índices, H1): compra al cierre de Nueva York (16:00) y vende a la apertura (09:30) del día siguiente, lunes a jueves.
  IMOM    momentum intradía (índices, H1): signo del retorno 16:00 (día previo) → 10:00; se opera de 15:00 a 16:00 en ese sentido.
Medición en R: retorno de la operación dividido por un riesgo ex ante de 2 desvíos del retorno de esa operación (desvío móvil de 60
operaciones previas, causal), menos el spread de Dukascopy por ida y vuelta. Períodos: DESC hasta 2019, OOS 2020–2023, RECIENTE 2024-01 →
2025-07, PSEUDO 2025-08 → 2026-09-29 (el holdout nunca entra). Nulo: la misma familia de reglas sobre series sintéticas (semanas
completas del activo, re-encadenadas al azar), máximo t de la familia → umbral p95 (nulo de la búsqueda).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PERIODOS = [("DESC", "2000-01-01", "2019-12-31"), ("OOS", "2020-01-01", "2023-12-31"), ("RECIENTE", "2024-01-01", "2025-07-31"),
            ("PSEUDO", "2025-08-01", "2026-09-29")]
INDICES = ("SP_M1_dukas", "NQ_M1_dukas", "DJ_M1_dukas", "USSC2000IDXUSD", "DEUIDXEUR", "JPNIDXJPY", "GBRIDXGBP", "EUSIDXEUR")
SERVIDOR_MENOS_NY = 7                                     # hora del servidor de datos (EST+07) − hora de Nueva York
LOOKBACKS = (20, 60, 120, 250)


def leer(path) -> pd.DataFrame:
    """Barras de SQX: las `*_M1_dukas` vienen en hora del servidor (NY + 7); el resto, en UTC (auditoría 2026-11-16: aperturas de cada mercado
    en UTC en invierno y verano). Se llevan todas a hora del servidor para que `_hora_ny` (− 7 h) dé hora de NY."""
    from pathlib import Path
    D = pd.read_csv(path); t = pd.to_datetime(D.fecha, format="%Y.%m.%d %H:%M:%S")
    if "_M1_dukas" not in Path(str(path)).name:
        t = t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None) + pd.Timedelta(hours=SERVIDOR_MENOS_NY)
    D["t"] = t
    return D.drop(columns="fecha").set_index("t").astype(float)


def _r(ret: pd.Series, costo: pd.Series, ventana: int = 60, minimo: int = 20) -> pd.Series:
    """Retorno → R con riesgo ex ante de 2 desvíos de las operaciones previas (causal) y costo de ida y vuelta."""
    sd = ret.shift(1).rolling(ventana, min_periods=minimo).std(); sd = sd.where(sd > 0)
    return ((ret - costo) / (2 * sd)).dropna()


def tsmom(D: pd.DataFrame, L: int, spread: float) -> pd.Series:
    c = D.close; semana = D.index.to_period("W")
    o_lun = D.open.groupby(semana).first(); c_vie = c.groupby(semana).last()
    sen = np.sign(c_vie / c.shift(L).groupby(semana).last() - 1)
    lado = sen.shift(1)                                    # señal al cierre del viernes previo → se opera la semana siguiente
    ret = lado * (c_vie / o_lun - 1); costo = spread / o_lun
    ret.index = ret.index.to_timestamp(); costo.index = costo.index.to_timestamp()
    return _r(ret.dropna(), costo.reindex(ret.dropna().index))


def finmes(D: pd.DataFrame, N: int, spread: float) -> pd.Series:
    c = D.close; m = D.index.to_period("M"); filas = []
    dias = pd.Series(D.index, index=D.index)
    for per, g in dias.groupby(m):
        if len(g) < 3: continue
        t_ent = g.iloc[-2]; sig = dias[(dias > g.iloc[-1])]
        if len(sig) < N: continue
        t_sal = sig.iloc[N - 1]
        entre = dias[(dias > t_ent) & (dias <= t_sal)]
        vie = entre[entre.dt.dayofweek == 4]
        if len(vie): t_sal = vie.iloc[0]                    # nada abierto el fin de semana
        filas.append((t_ent, c[t_sal] / c[t_ent] - 1, spread / c[t_ent]))
    if not filas: return pd.Series(dtype=float)
    F = pd.DataFrame(filas, columns=["t", "ret", "costo"]).set_index("t")
    return _r(F.ret, F.costo, ventana=24, minimo=12)


def _hora_ny(idx) -> np.ndarray:
    return (idx - pd.Timedelta(hours=SERVIDOR_MENOS_NY))


def noche(H: pd.DataFrame, spread: float) -> pd.Series:
    """H1 con apertura de barra: cierre 16:00 NY = close de la barra 15:00 NY; apertura 09:30 ≈ open de la barra 09:00 NY (más cercana)."""
    ny = _hora_ny(H.index); H = H.set_axis(ny)
    cierre = H.close[H.index.hour == 15]; apertura = H.open[H.index.hour == 9]
    c = cierre.copy(); c.index = c.index.normalize(); a = apertura.copy(); a.index = a.index.normalize() - pd.Timedelta(days=1)
    df = pd.concat([c.rename("c"), a.rename("a")], axis=1).dropna()
    df = df[df.index.dayofweek <= 3]                       # lunes a jueves: nunca el fin de semana
    return _r(df.a / df.c - 1, spread / df.c)


def imom(H: pd.DataFrame, spread: float) -> pd.Series:
    ny = _hora_ny(H.index); H = H.set_axis(ny); d = H.index.normalize()
    c16 = H.close[H.index.hour == 15]; c16.index = c16.index.normalize()
    o10 = H.open[H.index.hour == 10]; o10.index = o10.index.normalize()
    o15 = H.open[H.index.hour == 15]; o15.index = o15.index.normalize()
    df = pd.concat([c16.shift(1).rename("c_prev"), o10.rename("o10"), o15.rename("o15"), c16.rename("c16")], axis=1).dropna()
    lado = np.sign(df.o10 / df.c_prev - 1)
    return _r(lado * (df.c16 / df.o15 - 1), spread / df.o15)


def por_periodo(r: pd.Series) -> dict:
    out = {}
    for nom, a, b in PERIODOS:
        x = r[(r.index >= a) & (r.index <= b)]
        out[nom] = dict(n=int(len(x)), r=float(x.mean()) if len(x) else None, t=float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else None)
    return out


def sintetica(D: pd.DataFrame, semilla: int) -> pd.DataFrame:
    """Semanas completas del propio activo re-encadenadas al azar (mismo método que tools/sqx_nulo.py)."""
    rng = np.random.default_rng(semilla); prev = D.close.shift(1).fillna(D.open.iloc[0]).to_numpy()
    rel = np.column_stack([D[k].to_numpy() / prev for k in ("open", "high", "low", "close")])
    sem = D.index.to_period("W").to_numpy(); ini = np.r_[0, np.flatnonzero(sem[1:] != sem[:-1]) + 1]; fin = np.r_[ini[1:], len(D)]
    B = list(zip(ini, fin)); orden = []
    while sum(f - i for i, f in orden) < len(D):
        j = rng.integers(len(B)); orden += B[j:j + rng.integers(1, 5)]
    idx = np.concatenate([np.arange(i, f) for i, f in orden])[:len(D)]
    R = rel[idx]; c = D.open.iloc[0] * np.cumprod(R[:, 3]); p0 = np.r_[D.open.iloc[0], c[:-1]]
    return pd.DataFrame(dict(open=p0 * R[:, 0], high=p0 * R[:, 1], low=p0 * R[:, 2], close=c, volume=D.volume.to_numpy()[idx]), index=D.index)


def familia(D1: dict, H1: dict, spreads: dict) -> dict:
    """Todas las variantes pre-registradas: {nombre: serie R}."""
    F = {}
    for s, D in D1.items():
        for L in LOOKBACKS: F[f"TSMOM|{s}|L{L}"] = tsmom(D, L, spreads.get(s, 0.0))
        if s in INDICES:
            for N in (1, 3): F[f"FINMES|{s}|N{N}"] = finmes(D, N, spreads.get(s, 0.0))
    for s, H in H1.items():
        if s in INDICES:
            F[f"NOCHE|{s}"] = noche(H, spreads.get(s, 0.0)); F[f"IMOM|{s}"] = imom(H, spreads.get(s, 0.0))
    return F


def canastas(F: dict) -> dict:
    """Canasta de igual riesgo por regla (y por regla+parámetro): el promedio de R de los activos en cada fecha."""
    out = {}
    for clave in sorted({"|".join([k.split("|")[0]] + k.split("|")[2:]) for k in F}):
        regla, *par = clave.split("|")
        miembros = [v for k, v in F.items() if k.split("|")[0] == regla and k.split("|")[2:] == par and len(v)]
        if miembros: out[f"CANASTA|{clave}"] = pd.concat(miembros, axis=1).mean(axis=1).dropna()
    return out
