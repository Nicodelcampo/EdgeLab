#!/usr/bin/env python3
"""GEX a fondo (pre-registro docs/research/gex_tendencia_20261118/PREREGISTRO.md): variantes de gamma, desenlaces continuos y momentum
intradía condicionado a gamma (Baltussen et al. 2021). Fase 1 SÓLO en meses DESC de A5; el holdout se abre una vez, aparte.

Reusa `dia_tendencia._dia` (día RTH, ATR20, E1/E3, p1000) y `_rank`, `fundedsync_tanda2._auc`, `a5.diferencia`, `holdout.a5_bloque`.

  python tools/gex_tendencia.py tabla     # DESC: filas (instrumento, día) con gamma y desenlaces -> TABLA_DESC.csv.gz
  python tools/gex_tendencia.py explorar  # 54 medidas exploratorias -> EXPLORACION.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/gex_tendencia_20261118"
INST = ("NQ", "ES", "YM", "RTY")
PRED = ("g_rank250", "g_rank60", "g_neg", "g_z20", "g_chg", "g_esc", "dix_rank250")
SIGNO_ECON = {"g_rank250": -1, "g_rank60": -1, "g_neg": 1, "g_z20": -1, "g_chg": -1, "g_esc": -1, "dix_rank250": 0}   # menos gamma -> más tendencia


def gamma(bloques=("DESC",)) -> pd.DataFrame:
    """Variantes de gamma del cierre de d−1, indexadas por el día d."""
    from dia_tendencia import _rank
    G = pd.read_csv(ROOT / "data/DIX_squeezemetrics_20261108.csv", parse_dates=["date"]).set_index("date").sort_index()
    X = pd.DataFrame(index=G.index)
    X["g_rank250"] = _rank(G.gex, 250); X["g_rank60"] = _rank(G.gex, 60); X["g_neg"] = (G.gex < 0).astype(float)
    X["g_z20"] = (G.gex - G.gex.rolling(20).mean()) / G.gex.rolling(20).std()
    X["g_chg"] = X.g_rank250.diff(); X["g_esc"] = _rank(G.gex / G.price ** 2, 250); X["dix_rank250"] = _rank(G.dix, 250)
    return X.shift(1)                                                             # el dato de d−1 para el día d


def _dia_ext(inst):
    from datos import ruta
    from edgelab.research.m1_intradia import leer_m1nt8
    from dia_tendencia import _dia
    day = _dia(inst)
    D = leer_m1nt8(Path(ruta("M1NT8")) / f"{inst}_M1_nonadj_utc.parquet"); m = D.index.hour * 60 + D.index.minute
    q = D[m == 929]; day["p1530"] = q.c.groupby(q.index.normalize()).last().reindex(day.index)
    a = day.atr20
    day["Y1"] = (day.c - day.o).abs() / a; day["Y2"] = (day.h - day.l) / a
    day["Y4"] = np.sign(day.p1530 - day.o) * (day.c - day.p1530) / a
    day["Y5"] = np.sign(day.p1000 - day.o) * (day.c - day.p1000) / a
    day["vol20_t"] = pd.qcut(a.rank(method="first"), 3, labels=False)
    day["gap_t"] = pd.qcut(((day.o - day.c.shift(1)).abs() / a).rank(method="first"), 3, labels=False)
    return day


def tabla():
    from edgelab.holdout import a5_bloque
    g = gamma(); partes = []
    for inst in INST:
        d = _dia_ext(inst).join(g, how="left"); d["inst"] = inst; partes.append(d); print(inst, len(d), flush=True)
    T = pd.concat(partes); T["fecha"] = T.index.strftime("%Y%m%d").astype(int)
    T["bloque"] = [a5_bloque(int(f)) for f in T.fecha]
    T = T[(T.bloque == "DESC") & (T.fecha <= 20250731) & T.g_rank250.notna()]   # SÓLO DESC (REP consumido, HOLDOUT sellado)
    cols = ["fecha", "inst", "bloque", "E1", "E3", "Y1", "Y2", "Y4", "Y5", "vol20_t", "gap_t"] + list(PRED)
    DIR.mkdir(parents=True, exist_ok=True); T[cols].to_csv(DIR / "TABLA_DESC.csv.gz", index=False); print("DESC", len(T), T.fecha.nunique(), "días")


def _boot_dif(T, mask_a, mask_b, y, B=2000, seed=7):
    from edgelab.research.a5 import diferencia
    a, b = T[mask_a], T[mask_b]
    return diferencia(a.fecha.to_numpy(np.int64), a[y].to_numpy(float), b.fecha.to_numpy(np.int64), b[y].to_numpy(float), B=B, seed=seed)


def explorar():
    from fundedsync_tanda2 import _auc
    T = pd.read_csv(DIR / "TABLA_DESC.csv.gz"); out = {}
    for p in PRED:
        t = T.dropna(subset=[p]); s = SIGNO_ECON[p] or 1
        for y in ("Y1", "Y2"):
            r = t[[p, y]].rank().corr().iloc[0, 1] * s
            por = {i: float(g[[p, y]].rank().corr().iloc[0, 1] * s) for i, g in t.groupby("inst")}
            out[f"{p}|{y}"] = dict(spearman_signo_econ=float(r), por_inst=por)
        for y in ("E1", "E3"):
            out[f"{p}|{y}"] = dict(auc_signo_econ=_auc(s * t[p].values, t[y].values.astype(bool)),
                                  por_inst={i: _auc(s * g[p].values, g[y].values.astype(bool)) for i, g in t.groupby("inst")})
        for y in ("Y4", "Y5"):                                                    # bajo gamma (tercil "más tendencia") − alto
            q = pd.qcut((s * t[p]).rank(method="first"), 3, labels=False)
            d, se, pv = _boot_dif(t, q.values == 2, q.values == 0, y)
            out[f"{p}|{y}"] = dict(media_tercil=[float(t[y][q.values == k].mean()) for k in (0, 1, 2)], dif_mas_menos=d, se=se, p=pv,
                                  por_inst={i: float(g[y][(q[g.index] == 2).values].mean() - g[y][(q[g.index] == 0).values].mean()) for i, g in t.groupby("inst")})
    for z in ("vol20_t", "gap_t"):                                                # interacciones de g_rank250 con vol20 y gap
        for k in (0, 1, 2):
            t = T[T[z] == k].dropna(subset=["g_rank250"])
            out[f"g_rank250@{z}={k}|Y1"] = dict(spearman_signo_econ=float(-t[["g_rank250", "Y1"]].rank().corr().iloc[0, 1]))
            out[f"g_rank250@{z}={k}|E1"] = dict(auc_signo_econ=_auc(-t.g_rank250.values, t.E1.values.astype(bool)))
    (DIR / "EXPLORACION.json").write_text(json.dumps(dict(nota="EF2 exploratorio en DESC: no confirmatorio", medidas=len(out), resultados=out), indent=1, default=float))
    for k, v in out.items(): print(k, {a: (round(b, 4) if isinstance(b, float) else (None if b is None else (b if not isinstance(b, (list, dict)) else "…"))) for a, b in v.items() if a != "por_inst"})


if __name__ == "__main__":
    {"tabla": tabla, "explorar": explorar}[sys.argv[1]]()
