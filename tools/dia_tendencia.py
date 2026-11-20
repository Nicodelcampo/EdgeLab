#!/usr/bin/env python3
"""Día de tendencia: predictores causales NUEVOS, E0 sin retornos de estrategia (pre-registro docs/research/dia_tendencia_20261118/PREREGISTRO.md).

Reusa `fundedsync_tanda2.tabla_dia` (etiquetas E1/E2, rango, ATR), `_auc` y `_logit`; `m1_intradia.leer_m1nt8` (M1 real de futuros,
corta en la frontera); `macro_literatura.leer` (DAX H1 del CFD, a hora de NY); `holdout.a5_bloque` (A5: DESC elige el signo, REP prueba,
HOLDOUT sellado) y la copia verificada de `tools/datos.py`.

  python tools/dia_tendencia.py tabla      # tabla por (instrumento, día) con etiquetas y predictores -> TABLA.csv.gz (sin estrategia)
  python tools/dia_tendencia.py probar     # 21 pruebas: signo en DESC, AUC en REP (bootstrap por fecha), BH q 0,10 -> RESULTADO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/dia_tendencia_20261118"
INST = ("NQ", "ES", "YM", "RTY")
PRE_0930 = ("gex", "dix", "opex", "fin_mes", "nr7", "interior", "ubic_prev", "tend_prev", "europa_ef")   # conocidos antes de las 09:30
A_LAS_10 = ("open_drive", "amplitud")                                                                   # conocidos a las 10:00
PRUEBAS = [("E1", p) for p in PRE_0930] + [("E3", p) for p in PRE_0930 + A_LAS_10] + [("E3", "combinado")]


def _rank(x: pd.Series, n=250) -> pd.Series:
    """Percentil del valor contra los n anteriores con dato (causal: incluye el propio valor sólo como el que se rankea)."""
    x = x.dropna(); return x.rolling(n, min_periods=min(120, n)).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)


def _dia(inst):
    from datos import ruta
    from edgelab.research.m1_intradia import leer_m1nt8
    from fundedsync_tanda2 import tabla_dia
    D = leer_m1nt8(Path(ruta("M1NT8")) / f"{inst}_M1_nonadj_utc.parquet"); D = D[D.index >= "2006-01-01"]
    day, _, _ = tabla_dia(D, inst); m = D.index.hour * 60 + D.index.minute; dd = D.index.normalize()
    # E3: continuación del resto del día desde las 10:00 (la dirección de 09:30–10:00 se sostiene y domina la tarde)
    P = D[(m >= 600) & (m < 960)]; dP = P.index.normalize()
    p1000 = D[m == 599].c.groupby(D[m == 599].index.normalize()).last()
    h3, l3 = P.h.groupby(dP).max(), P.l.groupby(dP).min()
    day["p1000"] = p1000.reindex(day.index); day["h3"], day["l3"] = h3.reindex(day.index), l3.reindex(day.index)
    s30 = np.sign(day.p1000 - day.o)
    day["E3"] = (s30 * (day.c - day.p1000) >= 0.6 * (day.h3 - day.l3)) & (s30 != 0)
    # open drive (Dalton): de 09:35 a 10:00 el precio no vuelve a la apertura, del lado del movimiento
    W = D[(m >= 575) & (m < 600)]; dW = W.index.normalize()
    lo, hi = W.l.groupby(dW).min().reindex(day.index), W.h.groupby(dW).max().reindex(day.index)
    day["open_drive"] = (((s30 > 0) & (lo > day.o)) | ((s30 < 0) & (hi < day.o))).astype(float)
    day["s30"] = s30
    # estructura del día previo (todo con .shift(1))
    rango = day.h - day.l
    day["nr7"] = (rango == rango.rolling(7).min()).astype(float).shift(1)
    day["interior"] = ((day.h < day.h.shift(1)) & (day.l > day.l.shift(1))).astype(float).shift(1)
    day["ubic_prev"] = (2 * (day.c - day.l) / rango.replace(0, np.nan) - 1).abs().shift(1)
    day["tend_prev"] = day.E1.astype(float).shift(1)
    # calendario conocido de antemano
    ix = day.index
    day["opex"] = ((ix.dayofweek == 4) & (ix.day >= 15) & (ix.day <= 21)).astype(float)
    mes = pd.Series(ix.to_period("M"), index=ix)
    day["fin_mes"] = ((mes != mes.shift(-1)) | (mes != mes.shift(1))).astype(float)   # último o primer día hábil del mes (calendario)
    return day


def _externos(fechas):
    """GEX y DIX al cierre del día PREVIO (percentil contra sus 250 previos) y la eficiencia de Europa (DAX H1, 03:00→09:00 NY)."""
    from edgelab.research import macro_literatura as ML
    G = pd.read_csv(ROOT / "data/DIX_squeezemetrics_20261108.csv", parse_dates=["date"]).set_index("date").sort_index()
    gex = _rank(G.gex).shift(1); dix = _rank(G.dix).shift(1)             # dato del cierre de d−1 para el día d
    H = ML.leer(ROOT / "data/sqx_barras/DEUIDXEUR_H1.csv"); H.index = H.index - pd.Timedelta(hours=ML.SERVIDOR_MENOS_NY)
    hh = H.index.hour; X = H[(hh >= 3) & (hh < 9)]; dX = X.index.normalize()
    prev = X.close.groupby(dX).shift(1).fillna(X.open)                     # el primer paso de cada día parte de su apertura
    ef = (X.close.groupby(dX).last() - X.open.groupby(dX).first()).abs() / (X.close - prev).abs().groupby(dX).sum().replace(0, np.nan)
    return pd.DataFrame(dict(gex=gex, dix=dix)).reindex(fechas, method=None), ef.reindex(fechas)


def tabla():
    from edgelab.holdout import a5_bloque
    partes = []
    for inst in INST:
        d = _dia(inst); d["inst"] = inst; partes.append(d); print(inst, len(d), flush=True)
    T = pd.concat(partes); fechas = T.index.unique()
    ext, ef = _externos(fechas)
    T = T.join(ext, how="left"); T["europa_ef"] = ef.reindex(T.index).to_numpy()
    s = T.groupby(level=0).s30.apply(lambda x: abs(np.sign(x).sum()) / max(len(x), 1))   # amplitud: acuerdo de dirección 09:30–10:00
    T["amplitud"] = s.reindex(T.index).to_numpy()
    T["fecha"] = T.index.strftime("%Y%m%d").astype(int)
    T["bloque"] = [a5_bloque(int(f)) for f in T.fecha]
    T = T[(T.fecha <= 20250731) & T.bloque.isin(["DESC", "REP"])]           # HOLDOUT y EMBARGO: ni etiquetas ni predictores
    cols = ["fecha", "inst", "bloque", "E1", "E3"] + list(PRE_0930) + list(A_LAS_10)
    DIR.mkdir(parents=True, exist_ok=True); T[cols].to_csv(DIR / "TABLA.csv.gz", index=False)
    print(T.groupby("bloque").size().to_dict())


def _auc_boot(score, y, fechas, B=2000, seed=7):
    """AUC y p unilateral (AUC > 0,5) con bootstrap por fecha (un día de varios índices es un cluster)."""
    from fundedsync_tanda2 import _auc
    a = _auc(score, y); u = np.unique(fechas); pos = {f: i for i, f in enumerate(u)}; idx = np.array([pos[f] for f in fechas])
    grupos = [np.flatnonzero(idx == i) for i in range(len(u))]; rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        sel = np.concatenate([grupos[i] for i in rng.integers(0, len(u), len(u))])
        v = _auc(score[sel], y[sel])
        if v is not None: bs.append(v)
    bs = np.array(bs); return a, float(bs.std(ddof=1)), float((1 + (bs <= 0.5).sum()) / (len(bs) + 1))


def probar():
    from fundedsync_tanda2 import _auc, _logit
    from edgelab.research.a5 import bh
    T = pd.read_csv(DIR / "TABLA.csv.gz"); D, R = T[T.bloque == "DESC"], T[T.bloque == "REP"]; res = {}
    for et, p in PRUEBAS:
        if p == "combinado":
            cs = list(PRE_0930) + list(A_LAS_10); d = D.dropna(subset=cs + [et]); r = R.dropna(subset=cs + [et])
            mu, sd = d[cs].mean(), d[cs].std().replace(0, 1); b = _logit(((d[cs] - mu) / sd).values, d[et].values.astype(float))
            z = np.c_[np.ones(len(r)), ((r[cs] - mu) / sd).values] @ b; sc, y, f = z, r[et].values.astype(bool), r.fecha.values
            signo = 1.0
        else:
            d = D.dropna(subset=[p, et]); r = R.dropna(subset=[p, et])
            signo = 1.0 if (_auc(d[p].values, d[et].values.astype(bool)) or 0.5) >= 0.5 else -1.0      # dirección elegida en DESC
            sc, y, f = signo * r[p].values, r[et].values.astype(bool), r.fecha.values
        a, se, pv = _auc_boot(sc, y, f)
        por = {i: _auc(signo * g[p].values if p != "combinado" else None, g[et].values.astype(bool)) if p != "combinado" else None
               for i, g in r.groupby("inst")} if p != "combinado" else {}
        res[f"{et}|{p}"] = dict(signo_desc=signo, n_rep=int(len(y)), tasa_rep=float(y.mean()), auc_rep=a, se=se, p=pv,
                                auc_desc=_auc(signo * d[p].values, d[et].values.astype(bool)) if p != "combinado" else None,
                                auc_por_inst=por, inst_mismo_signo=int(sum(1 for v in por.values() if v and v > 0.5)))
    nombres = list(res); rech = bh([res[k]["p"] for k in nombres], 0.10)
    for k, rj in zip(nombres, rech):
        v = res[k]; v["bh"] = bool(rj)
        v["sirve"] = bool(rj and (v["auc_rep"] or 0) >= 0.55 and (k.endswith("combinado") or v["inst_mismo_signo"] >= 3))
    out = dict(preregistro="docs/research/dia_tendencia_20261118/PREREGISTRO.md", pruebas=len(res), resultados=res,
               sirven=[k for k in nombres if res[k]["sirve"]])
    (DIR / "RESULTADO.json").write_text(json.dumps(out, indent=1, default=float))
    for k in nombres: print(k, {x: (round(res[k][x], 3) if isinstance(res[k][x], float) else res[k][x]) for x in ("auc_desc", "auc_rep", "p", "inst_mismo_signo", "bh", "sirve")})


if __name__ == "__main__":
    {"tabla": tabla, "probar": probar}[sys.argv[1]]()
