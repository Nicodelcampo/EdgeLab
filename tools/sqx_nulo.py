#!/usr/bin/env python3
"""Nulo de la búsqueda para corridas de SQX (2026-11-14): una serie SINTÉTICA con la misma volatilidad, estacionalidad intrasemanal
y colas que el activo real, pero sin la estructura de más largo plazo que una regla podría explotar. El Builder corre IGUAL sobre ella;
cuántas estrategias «pasan» y con qué t da el umbral (p95 del máximo) contra el que se mide la corrida real (contrato de calidad,
edgelab/research/sqx_calidad.py). Sin run_python ni execute_shell en la laptop: barras por MCP (read_bars), síntesis acá, subida
con write_file e importación con sqcli (-data action=import).

  python tools/sqx_nulo.py crear SIMBOLO TF SEMILLA [--desde 2012.01.01] [--hasta 2019.12.31] [--modo semanas|barras]

modo semanas: bloques de 1–4 semanas completas del propio activo, re-encadenados (conserva hora del día, día de la semana, volatilidad
y su agrupamiento dentro del bloque; destruye tendencias/reversiones de más de un mes). modo barras: bloques de 24–120 barras sin
alinear (destruye también la estacionalidad: nulo para ideas de calendario).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "tools"))
import mcp_cliente as MC  # noqa: E402

TOPE = "2026.09.29"


def leer(c, simbolo, tf, desde, hasta) -> pd.DataFrame:
    filas, pos = [], 0
    while True:
        r = c.llamar("read_bars", {"symbol": simbolo, "timeframe": tf, "start": pos, "count": 1000})
        rows = r.get("rows", [])
        if not rows: break
        filas += rows; pos += len(rows)
        if rows[-1]["date"][:10] > hasta or pos >= r.get("total_count", 0): break
    D = pd.DataFrame(filas); D["t"] = pd.to_datetime(D.date, format="%Y.%m.%d %H:%M:%S")
    for k in ("open", "high", "low", "close"): D[k] = D[k].astype(float)
    return D[(D.date.str[:10] >= desde) & (D.date.str[:10] <= hasta)].reset_index(drop=True)


def sintetizar(D: pd.DataFrame, semilla: int, modo: str = "semanas") -> pd.DataFrame:
    rng = np.random.default_rng(semilla); prev = D.close.shift(1).fillna(D.open.iloc[0]).to_numpy()
    rel = np.column_stack([D[k].to_numpy() / prev for k in ("open", "high", "low", "close")])     # barra relativa al cierre previo
    if modo == "semanas":
        sem = D.t.dt.to_period("W").to_numpy(); ini = np.r_[0, np.flatnonzero(sem[1:] != sem[:-1]) + 1]; fin = np.r_[ini[1:], len(D)]
        bloques = list(zip(ini, fin)); orden = []
        while sum(f - i for i, f in orden) < len(D):
            j = rng.integers(len(bloques)); L = rng.integers(1, 5); orden += bloques[j:j + L]
        idx = np.concatenate([np.arange(i, f) for i, f in orden])[:len(D)]
    else:
        idx = []
        while len(idx) < len(D):
            i = rng.integers(len(D) - 120); idx += list(range(i, i + rng.integers(24, 121)))
        idx = np.array(idx[:len(D)])
    R = rel[idx]; c = D.open.iloc[0] * np.cumprod(R[:, 3])
    p0 = np.r_[D.open.iloc[0], c[:-1]]
    S = pd.DataFrame(dict(t=D.t, open=p0 * R[:, 0], high=p0 * R[:, 1], low=p0 * R[:, 2], close=c, volume=D.volume.to_numpy()[idx]))
    S["high"] = S[["open", "high", "low", "close"]].max(axis=1); S["low"] = S[["open", "high", "low", "close"]].min(axis=1)
    return S


def crear(simbolo, tf, semilla):
    a = sys.argv; arg = lambda k, d: a[a.index(k) + 1] if k in a else d
    desde, hasta, modo = arg("--desde", "2012.01.01"), arg("--hasta", "2019.12.31"), arg("--modo", "semanas")
    if hasta.replace(".", "") > TOPE.replace(".", ""): raise SystemExit("pasa el tope del holdout")
    c = MC.Cliente("sqx"); D = leer(c, simbolo, tf, desde, hasta); S = sintetizar(D, int(semilla), modo)
    dec = 5 if S.close.iloc[0] < 50 else 3
    txt = "\n".join(f"{t:%Y.%m.%d},{t:%H:%M},{o:.{dec}f},{h:.{dec}f},{l:.{dec}f},{cl:.{dec}f},{int(v)}"
                    for t, o, h, l, cl, v in zip(S.t, S.open, S.high, S.low, S.close, S.volume))
    nom = f"NULO_{simbolo}_{tf}_{modo[0]}{semilla}"; ruta = f"user/mcp-work/nulos/{nom}.csv"
    c.llamar("write_file", {"path": ruta, "content": txt + "\n"})
    inst = c.llamar("list_data", {"filter": simbolo, "detail": True})["data"][0]["instrument"]
    out = c.llamar("run_cli_command", {"command": f'-data action=import symbol={nom} filepath="{ruta}" format="Generic bar format (comma delimited)" '
                                                  f'instrument={inst} timeframe={tf} bartype=startofbar'})
    man = ROOT / "sqx/nulos" / f"{nom}.json"; man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps(dict(simbolo_nulo=nom, origen=simbolo, timeframe=tf, semilla=int(semilla), modo=modo, desde=desde, hasta=hasta,
                                   barras=len(S), instrumento=inst, importacion=str(out)[:500], creado=dt.datetime.now(dt.UTC).isoformat()), indent=1), encoding="utf-8")
    print(nom, len(S), "barras;", str(out)[:300])


if __name__ == "__main__":
    if sys.argv[1:2] == ["crear"]: crear(*sys.argv[2:5])
    else: raise SystemExit(__doc__)
