"""Veto de noticias para backtests, igual al que aplica la estrategia en vivo (NT8/MT5).

Regla (decisión de Nico, 2026-11-25): ventana [evento − 2 min, evento + 2 min] para toda noticia tier1 del calendario
canónico (`edgelab.noticias`, 2008-2026) y [evento − 5, evento + 5] para los eventos del FOMC. Dentro de una ventana:
  - no se abre ninguna operación (la que entraría ahí se anula);
  - la posición abierta se CIERRA al abrir la vela de 1 minuto en la que empieza la ventana (orden a mercado),
    no se reabre después (la estrategia en vivo tampoco la reabre).

`aplicar_veto` trabaja sobre la lista de operaciones de cualquier motor (entrada/salida/lado/precios) y una serie de
aperturas M1 del instrumento operado. Es exacto para estrategias que no dependen de su propia operación anterior;
para las que encadenan (una posición a la vez, señales que esperan a que cierre la anterior) es una aproximación: la
integración exacta se hace en cada motor con `en_ventana` / `proximo_inicio`. Cada análisis declara cuál usó.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from edgelab import noticias

_NS_MIN = 60_000_000_000
EVENTOS_FOMC = ("FOMC_DECISION", "FOMC_PRESS_CONFERENCE", "FOMC_MINUTES")


@dataclass(frozen=True)
class Ventana:
    antes_min: float = 2.0
    despues_min: float = 2.0
    fomc_antes_min: float = 5.0
    fomc_despues_min: float = 5.0
    impactos: tuple = ("tier1",)


def ventanas(v: Ventana = Ventana(), ruta=None) -> pd.DataFrame:
    """Tramos vetados fusionados (ns UTC): columnas inicio_ns, fin_ns, eventos."""
    cal = noticias.cargar(ruta)
    cal = cal[cal["impacto"].isin(v.impactos)]
    es_fomc = cal["evento"].isin(EVENTOS_FOMC).to_numpy()
    t = cal["ts_ns"].to_numpy(np.int64)
    ini = t - np.where(es_fomc, v.fomc_antes_min, v.antes_min) * _NS_MIN
    fin = t + np.where(es_fomc, v.fomc_despues_min, v.despues_min) * _NS_MIN
    orden = np.argsort(ini, kind="stable")
    ini, fin, ev = ini[orden].astype(np.int64), fin[orden].astype(np.int64), cal["evento"].to_numpy()[orden]
    tramos: list[list] = []
    for a, b, e in zip(ini, fin, ev):
        if tramos and a <= tramos[-1][1]:
            tramos[-1][1] = max(tramos[-1][1], b)
            if e not in tramos[-1][2]:
                tramos[-1][2].append(e)
        else:
            tramos.append([a, b, [e]])
    return pd.DataFrame({"inicio_ns": np.array([x[0] for x in tramos], dtype=np.int64),
                         "fin_ns": np.array([x[1] for x in tramos], dtype=np.int64),
                         "eventos": ["+".join(x[2]) for x in tramos]})


def en_ventana(ts_ns, V: pd.DataFrame) -> np.ndarray:
    """True si el instante cae dentro de un tramo vetado (intervalo cerrado)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    i = np.searchsorted(V["inicio_ns"].to_numpy(), ts, side="right") - 1
    ok = i >= 0
    out = np.zeros(ts.shape, dtype=bool)
    out[ok] = ts[ok] <= V["fin_ns"].to_numpy()[i[ok]]
    return out


def proximo_inicio(ts_ns, V: pd.DataFrame) -> np.ndarray:
    """Inicio del primer tramo vetado que empieza DESPUÉS de cada instante (int64 max si no hay)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    ini = V["inicio_ns"].to_numpy()
    i = np.searchsorted(ini, ts, side="right")
    out = np.full(ts.shape, np.iinfo(np.int64).max, dtype=np.int64)
    ok = i < len(ini)
    out[ok] = ini[i[ok]]
    return out


def aplicar_veto(ops: pd.DataFrame, aperturas_m1: pd.Series, V: pd.DataFrame | None = None,
                 v: Ventana = Ventana()) -> pd.DataFrame:
    """Aplica el veto a operaciones ya simuladas.

    ops: columnas `entrada_ns`, `salida_ns` (int64 ns UTC), `lado` (+1/−1), `precio_entrada`, `precio_salida`.
    aperturas_m1: apertura de cada vela de 1 minuto, índice = inicio de la vela (DatetimeIndex UTC o naive UTC).
    Devuelve una copia con `veto` ∈ {sin_cambio, anulada, cerrada_por_noticia}, `salida_ns` y `precio_salida`
    corregidas y `pts` = lado × (salida − entrada) (0 para las anuladas, que no existieron).
    """
    V = ventanas(v) if V is None else V
    o = ops.copy()
    ent = o["entrada_ns"].to_numpy(np.int64)
    sal = o["salida_ns"].to_numpy(np.int64)
    estado = np.array(["sin_cambio"] * len(o), dtype=object)
    anulada = en_ventana(ent, V)
    corte = proximo_inicio(ent, V)
    cerrar = ~anulada & (corte <= sal)
    estado[anulada] = "anulada"
    estado[cerrar] = "cerrada_por_noticia"
    if cerrar.any():
        idx = aperturas_m1.index
        idx_ns = (idx.tz_convert("UTC") if idx.tz is not None else idx.tz_localize("UTC")).as_unit("ns").asi8
        # la vela que contiene el inicio del tramo: el cierre a mercado se llena en su apertura
        k = np.searchsorted(idx_ns, corte[cerrar], side="right") - 1
        if (k < 0).any():
            raise ValueError("faltan velas M1 antes del corte de alguna operación")
        sal = sal.copy()
        sal[cerrar] = idx_ns[k]
        px = o["precio_salida"].to_numpy(float).copy()
        px[cerrar] = aperturas_m1.to_numpy(float)[k]
        o["precio_salida"] = px
        o["salida_ns"] = sal
    o["veto"] = estado
    o["pts"] = np.where(anulada, 0.0, o["lado"].to_numpy(float) * (o["precio_salida"].to_numpy(float) - o["precio_entrada"].to_numpy(float)))
    return o


def resumen(o: pd.DataFrame) -> dict:
    """Conteo de operaciones afectadas (para el informe de cada estrategia)."""
    n = len(o)
    c = o["veto"].value_counts()
    return {"n": n, "anuladas": int(c.get("anulada", 0)), "cerradas_por_noticia": int(c.get("cerrada_por_noticia", 0)),
            "pct_afectadas": round(100.0 * (n - int(c.get("sin_cambio", 0))) / n, 2) if n else 0.0}
