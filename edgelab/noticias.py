"""Calendario de noticias USD de alto impacto y filtro de operaciones que las cruzan (pedido de Nico, 2026-10-25).

«Las operaciones no pueden ser durante noticias, por fricciones y por reglas de prop firms.» Los horarios viven en
`config/noticias/calendario_usd_tier1.csv` (minuto exacto en UTC, una fuente por fila; cómo se armó y qué falta en
`config/noticias/FUENTES.md`, se regenera con `tools/noticias_calendario.py`). Este módulo sólo lo lee y responde.

    from edgelab import noticias
    noticias.cargar()                                   # DataFrame con ts_utc, ts_ns, evento, fuente_url, impacto
    noticias.ventanas_bloqueadas()                      # [evento − 1 min, evento + 1 min] fusionadas, en ns UTC
    noticias.cruza_noticia(entrada_ns, salida_ns)       # bool por operación: True = prohibida
    noticias.minutos_bloqueados_del_dia("2024-03-12")   # minutos del día (reloj CT) a no operar, para kernels

**Ventana por defecto: ±1 minuto**, la regla más estricta que publican las firmas del catálogo que admiten algoritmos.
Es la de LucidDaily fondeada (Lucid admite sistemas, `config/propfirms/catalogo_lucid_50k.json`, `algo_policy:
condicional`): «You must be flat from 1 minute before through 1 minute after the news event. You may not hold or open
new positions through that window», para toda noticia `Impact = High` y `Currency = USD` (carpeta roja de
ForexFactory). Fuente: `artifacts/propfirm/crawl/Lucid/inventario.md` (línea 849) y
`docs/research/PROPFIRM_LUCID_REFERENCIAS_20261013.md`. TakeProfitTrader PRO pide lo mismo (±1 min) pero sólo para
FOMC, NFP y CPI (`artifacts/propfirm/crawl/TakeProfitTrader/inventario.md`). Ninguna otra firma del catálogo da un número
(Tradeify: «restrictions around major economic events»; Apex: permite la estrategia normal; Topstep y MFF: permitido).
El ±1 es el piso REGLAMENTARIO; la fricción alrededor del dato dura más: para el argumento de fricción se pasa una
ventana más ancha explícita (`antes_min`, `despues_min`) y se declara en el manifiesto.

Semántica: la ventana de un evento es el intervalo CERRADO [t − antes, t + después]; una operación [entrada, salida]
(también cerrado) queda prohibida si lo toca en algún punto, incluido el borde: estar posicionado en t − antes ya es
estar posicionado «desde 1 minuto antes». Las solicitudes semanales de subsidio (`INITIAL_JOBLESS_CLAIMS`) son `tier2`:
ForexFactory las marca rojas sólo en algunos tramos (en medium, p. ej., hasta 2023-03-09 y desde 2026-04-09); para cubrir la regla
de Lucid en esos tramos, pasar `impactos=("tier1", "tier2")`.

Cobertura: 2023-01-01 → 2026-12-31 con faltantes declarados en FUENTES.md (p. ej. solicitudes posteriores al
2026-10-22 y minutas del FOMC de nov/dic-2026 aún no fechadas). Fuera del rango de cobertura `cruza_noticia` falla
cerrado (`FueraDeCobertura`) salvo `exigir_cobertura=False`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

RUTA = Path(__file__).resolve().parents[1] / "config" / "noticias" / "calendario_usd_tier1.csv"
VENTANA_DEFAULT_MIN = (1, 1)   # (antes, después): LucidDaily fondeada, la más estricta del catálogo con algoritmos
COBERTURA_DESDE = pd.Timestamp("2023-01-01", tz="UTC")
COBERTURA_HASTA = pd.Timestamp("2027-01-01", tz="UTC")   # exclusivo
IMPACTOS = ("tier1", "tier2")
COLUMNAS = ("ts_utc", "evento", "fuente_url", "impacto")
_NS_MIN = 60 * 1_000_000_000


class FueraDeCobertura(ValueError):
    """Una operación cae fuera del rango que el calendario cubre: no se puede afirmar que no cruza una noticia."""


@lru_cache(maxsize=4)
def _leer(ruta: str) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"{ruta}: faltan columnas {faltan}")
    if (df["fuente_url"].str.strip() == "").any():
        raise ValueError(f"{ruta}: hay filas sin fuente_url")
    malos = sorted(set(df["impacto"]) - set(IMPACTOS))
    if malos:
        raise ValueError(f"{ruta}: impacto desconocido {malos}")
    ts = pd.to_datetime(df["ts_utc"], utc=True, format="%Y-%m-%dT%H:%MZ").dt.as_unit("ns")
    out = df.assign(ts_utc=ts, ts_ns=ts.astype("int64"))
    out = out.sort_values(["ts_ns", "evento"], kind="mergesort").reset_index(drop=True)
    if out.duplicated(["ts_ns", "evento"]).any():
        raise ValueError(f"{ruta}: filas duplicadas (ts_utc, evento)")
    return out[["ts_utc", "ts_ns", "evento", "fuente_url", "impacto"]]


def cargar(ruta: str | Path | None = None) -> pd.DataFrame:
    """Calendario completo, ordenado por hora. `ts_utc` es tz-aware UTC; `ts_ns` el mismo instante en ns epoch."""
    return _leer(str(ruta or RUTA)).copy()


def _filtrar(df: pd.DataFrame, impactos: Iterable[str], eventos: Iterable[str] | None) -> pd.DataFrame:
    impactos = tuple(impactos)
    malos = sorted(set(impactos) - set(IMPACTOS))
    if malos:
        raise ValueError(f"impacto desconocido {malos}; válidos {IMPACTOS}")
    m = df["impacto"].isin(impactos)
    if eventos is not None:
        eventos = tuple(eventos)
        desconocidos = sorted(set(eventos) - set(df["evento"]))
        if desconocidos:
            raise ValueError(f"evento desconocido {desconocidos}")
        m &= df["evento"].isin(eventos)
    return df[m]


def ventanas_bloqueadas(antes_min: float = VENTANA_DEFAULT_MIN[0], despues_min: float = VENTANA_DEFAULT_MIN[1],
                        impactos: Iterable[str] = ("tier1",), eventos: Iterable[str] | None = None,
                        ruta: str | Path | None = None) -> pd.DataFrame:
    """Intervalos cerrados [evento − antes, evento + después] FUSIONADOS (disjuntos y ordenados), en ns UTC.

    Columnas: `inicio_ns`, `fin_ns`, `inicio_utc`, `fin_utc`, `eventos` (los que componen el tramo, separados por '+').
    """
    if antes_min < 0 or despues_min < 0:
        raise ValueError("antes_min y despues_min deben ser >= 0")
    df = _filtrar(cargar(ruta), impactos, eventos)
    ini = df["ts_ns"].to_numpy(np.int64) - int(round(antes_min * _NS_MIN))
    fin = df["ts_ns"].to_numpy(np.int64) + int(round(despues_min * _NS_MIN))
    ev = df["evento"].to_numpy()
    tramos: list[list] = []
    for a, b, e in zip(ini, fin, ev):          # ya viene ordenado por inicio (mismo corrimiento para todas)
        if tramos and a <= tramos[-1][1]:
            tramos[-1][1] = max(tramos[-1][1], b)
            if e not in tramos[-1][2]:
                tramos[-1][2].append(e)
        else:
            tramos.append([a, b, [e]])
    out = pd.DataFrame({"inicio_ns": np.array([t[0] for t in tramos], dtype=np.int64),
                        "fin_ns": np.array([t[1] for t in tramos], dtype=np.int64),
                        "eventos": ["+".join(t[2]) for t in tramos]})
    out.insert(2, "inicio_utc", pd.to_datetime(out["inicio_ns"], utc=True))
    out.insert(3, "fin_utc", pd.to_datetime(out["fin_ns"], utc=True))
    return out


def _a_ns(x) -> np.ndarray:
    """int ns epoch, datetime64 o Timestamps tz-aware -> np.int64 (UTC)."""
    if isinstance(x, (pd.Series, pd.Index)) and isinstance(x.dtype, pd.DatetimeTZDtype):
        return (x.dt.as_unit("ns").astype("int64").to_numpy() if isinstance(x, pd.Series)
                else x.as_unit("ns").asi8)
    arr = np.asarray(x)
    if np.issubdtype(arr.dtype, np.datetime64):
        if np.isnat(arr).any():
            raise ValueError("hay tiempos NaT")
        return arr.astype("datetime64[ns]").astype(np.int64)
    if arr.dtype == object:
        return pd.to_datetime(arr, utc=True).as_unit("ns").asi8
    if not np.issubdtype(arr.dtype, np.integer):
        raise TypeError(f"tiempos en ns enteros o datetime; vino {arr.dtype}")
    return arr.astype(np.int64)


def cruza_noticia(entrada_ns, salida_ns, antes_min: float = VENTANA_DEFAULT_MIN[0],
                  despues_min: float = VENTANA_DEFAULT_MIN[1], impactos: Iterable[str] = ("tier1",),
                  eventos: Iterable[str] | None = None, ventanas: pd.DataFrame | None = None,
                  exigir_cobertura: bool = True, ruta: str | Path | None = None) -> np.ndarray:
    """True por operación si su intervalo cerrado [entrada, salida] toca alguna ventana bloqueada.

    Vectorizado: con las ventanas fusionadas (disjuntas, ordenadas), `fin` también es creciente; el primer tramo con
    `fin >= entrada` sale de `searchsorted` y la operación cruza si ese tramo empieza `<= salida`.
    `ventanas` permite reutilizar el resultado de `ventanas_bloqueadas` en bucles.
    """
    a = _a_ns(entrada_ns).ravel()
    b = _a_ns(salida_ns).ravel()
    if a.shape != b.shape:
        raise ValueError("entrada y salida deben tener el mismo largo")
    if (b < a).any():
        raise ValueError(f"{int((b < a).sum())} operaciones con salida anterior a la entrada")
    if exigir_cobertura and a.size:
        fuera = (a < COBERTURA_DESDE.value) | (b >= COBERTURA_HASTA.value)
        if fuera.any():
            raise FueraDeCobertura(f"{int(fuera.sum())} operaciones fuera de [{COBERTURA_DESDE.date()}, "
                                   f"{COBERTURA_HASTA.date()}): el calendario no las cubre")
    w = ventanas if ventanas is not None else ventanas_bloqueadas(antes_min, despues_min, impactos, eventos, ruta)
    ini = w["inicio_ns"].to_numpy(np.int64)
    fin = w["fin_ns"].to_numpy(np.int64)
    if ini.size == 0:
        return np.zeros(a.shape, dtype=bool)
    i = np.searchsorted(fin, a, side="left")
    ok = i < fin.size
    out = np.zeros(a.shape, dtype=bool)
    out[ok] = ini[i[ok]] <= b[ok]
    return out


def minutos_bloqueados_del_dia(fecha, antes_min: float = VENTANA_DEFAULT_MIN[0],
                               despues_min: float = VENTANA_DEFAULT_MIN[1], impactos: Iterable[str] = ("tier1",),
                               eventos: Iterable[str] | None = None, tz: str = "America/Chicago",
                               ruta: str | Path | None = None) -> np.ndarray:
    """Minutos del día calendario `fecha` en el reloj `tz` (0 = medianoche local) cuya barra de 1 minuto
    [m, m+1) toca alguna ventana bloqueada. Para kernels por minuto: no abrir ni sostener en esos minutos.

    Con ±1 min, un dato de las 08:30 ET bloquea 07:29, 07:30 y 07:31 CT (tres barras).
    """
    d0 = pd.Timestamp(fecha).tz_localize(tz) if pd.Timestamp(fecha).tzinfo is None else pd.Timestamp(fecha).tz_convert(tz)
    d0 = d0.normalize()
    d1 = (d0 + pd.Timedelta(days=1)).normalize()   # normalize en la zona: días de 23/25 h quedan bien
    w = ventanas_bloqueadas(antes_min, despues_min, impactos, eventos, ruta)
    a, b = d0.value, d1.value
    w = w[(w["fin_ns"] >= a) & (w["inicio_ns"] < b)]
    minutos: set[int] = set()
    for s, e in zip(w["inicio_ns"].to_numpy(np.int64), w["fin_ns"].to_numpy(np.int64)):
        s, e = max(s, a), min(e, b - 1)
        m0 = (s - a) // _NS_MIN
        m1 = (e - a) // _NS_MIN
        minutos.update(range(int(m0), int(m1) + 1))
    return np.array(sorted(minutos), dtype=np.int64)
