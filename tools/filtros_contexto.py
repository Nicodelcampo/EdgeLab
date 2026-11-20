#!/usr/bin/env python3
"""FILTROS-CONTEXTO (2026-11-20): ¿algún indicador de contexto diario (VIX, VVIX, GEX, DIX, SKEW, estructura VIX9D/VIX, COT) separa
los días buenos de los malos en A20, T, R, Z-banda (NQ) y la fábrica de RQ5? Pre-registro: docs/research/filtros_contexto_20261120/PREREGISTRO.md.

Cada indicador se lleva a su percentil móvil causal (252 observaciones diarias; 52 semanas el COT) y a cada sesión se le asigna el último
valor publicado ANTES de la sesión (el COT del martes se usa desde las sesiones posteriores al viernes de publicación). Terciles fijos del
percentil (1/3, 2/3). Prueba: media de R neto del tercil alto menos la del tercil bajo, bootstrap por sesión, dos colas, BH q 0,10 sobre
las 35 pruebas, en los meses DESC de A5 entre 2018-01-01 y 2025-07-31; la réplica, en los meses REP. HOLDOUT y EMBARGO se descartan sin leerse.

  python tools/filtros_contexto.py conteo     # operaciones por tercil, sin desenlaces (para el pre-registro)
  python tools/filtros_contexto.py correr     # lectura pre-registrada (exige la campaña contada, K51)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
DIR = ROOT / "docs/research/filtros_contexto_20261120"
CAMPANA = "FILTROS-CONTEXTO-20261120"
DESDE, HASTA = 20180101, 20250731
INDICADORES = ("VIX", "VVIX", "GEX", "DIX", "SKEW", "TERM", "COT")
ESTRATEGIAS = ("A20", "T", "R", "ZB", "RQ5")
B, SEMILLA, Q = 4000, 20261120, 0.10


def _ses(x) -> pd.Series:
    return pd.to_datetime(pd.Series(x).astype(str)).dt.strftime("%Y%m%d").astype(int).to_numpy()


def operaciones() -> pd.DataFrame:
    """R neto por operación de cada estrategia (las mismas reglas y medidas que sus actas), con su sesión e instrumento."""
    from edgelab.research.embudo_runners import friccion
    fr = {i: float(friccion(i)[0]) for i in ("NQ", "ES", "YM", "RTY")}
    RZ = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); RZ = RZ[RZ.inst == "NQ"]
    partes = []
    a = RZ[(RZ.modulo == "A20") & (RZ.variante == "A20_7_2_2.5_1.5") & (RZ.riesgo > 0)]
    partes.append(pd.DataFrame(dict(est="A20", inst="NQ", ses=_ses(a.ses), R=(a.pnl_pts - fr["NQ"]) / a.riesgo)))
    t = pd.read_csv(ROOT / "docs/research/m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz"); t = t[t.riesgo > 0]
    partes.append(pd.DataFrame(dict(est="T", inst="NQ", ses=_ses(t.dia), R=t.neto / t.riesgo)))
    r = RZ[(RZ.modulo == "R") & (RZ.variante == "R_21_100_2.5_660")]; rg = 0.25 * r.atr20
    br = np.where(r.mae_pts >= rg, -rg, r.pnl_pts); ok = (rg > 0).to_numpy()
    partes.append(pd.DataFrame(dict(est="R", inst="NQ", ses=_ses(r.ses)[ok], R=((br - fr["NQ"]) / rg).to_numpy()[ok])))
    banda = [f"Z_{a_}_{b_}_{e}" for (a_, b_) in ((10, 30), (15, 20), (30, 10)) for e in (35, 45, 55)]
    z = RZ[(RZ.modulo == "Z") & RZ.variante.isin(banda)].copy(); z["rg"] = 0.25 * z.atr20
    z["br"] = np.where(z.mae_pts >= z.rg, -z.rg, z.pnl_pts); z = z[z.rg > 0].groupby("ses")[["br", "rg"]].mean().reset_index()
    partes.append(pd.DataFrame(dict(est="ZB", inst="NQ", ses=_ses(z.ses), R=(z.br - fr["NQ"]) / z.rg)))
    O = pd.read_csv(ROOT / "docs/research/rq5_regimen_20261119/OPS_DESC_REP.csv.gz"); en = "P_obj_s0.45_tp2_stop_s0.45_tp2_fin"
    O = O[O["L60_m1_c689"].astype(bool) & O.inst.isin(list(fr)) & O[f"r_{en}"].notna() & (O[f"k_{en}"] > 0)]
    partes.append(pd.DataFrame(dict(est="RQ5", inst=O.inst, ses=O.ses.astype(int), R=O[f"r_{en}"] - O.inst.map(fr) / O[f"k_{en}"])))
    from edgelab.holdout import a5_bloque
    X = pd.concat(partes, ignore_index=True); X = X[(X.ses >= DESDE) & (X.ses <= HASTA)]
    X["bloque"] = [a5_bloque(int(s)) for s in X.ses]
    return X[X.bloque.isin(["DESC", "REP"])].reset_index(drop=True)          # HOLDOUT y EMBARGO fuera, sin leerse


def _pct_movil(s: pd.Series, n: int) -> pd.Series:
    """Percentil del valor de hoy entre las últimas n observaciones (incluida la de hoy): causal."""
    return s.rolling(n, min_periods=max(20, n // 2)).apply(lambda w: (w <= w[-1]).mean(), raw=True)


def indicadores() -> dict[str, pd.Series]:
    """Serie diaria del percentil de cada indicador, indexada por la FECHA DE PUBLICACIÓN (después de la cual ya se conoce)."""
    v = pd.read_parquet(ROOT / "data/m1nt8/cboe_volatility_daily.parquet"); v.index = pd.to_datetime(v.index)
    rd = lambda f, c: pd.read_csv(ROOT / f, parse_dates=["DATE"]).set_index("DATE")[c].astype(float)
    dx = pd.read_csv(ROOT / "data/DIX_squeezemetrics_20261108.csv", parse_dates=["date"]).set_index("date")
    s = dict(VIX=v.vix_close, VVIX=rd("data/cboe_extra/VVIX.csv", "VVIX"), GEX=dx.gex.astype(float), DIX=dx.dix.astype(float),
             SKEW=rd("data/cboe_extra/SKEW.csv", "SKEW"), TERM=v.vix9d_close / v.vix_close)
    out = {k: _pct_movil(x.dropna().sort_index(), 252) for k, x in s.items()}
    for inst, cod in (("NQ", "209742"), ("ES", "13874A")):
        c = pd.DataFrame(json.load(open(ROOT / f"data/cot/legacy_{cod}.json")))
        f = pd.to_datetime(c.report_date_as_yyyy_mm_dd)
        net = (c.noncomm_positions_long_all.astype(float) - c.noncomm_positions_short_all.astype(float)) / c.open_interest_all.astype(float)
        p = _pct_movil(pd.Series(net.to_numpy(), index=f).sort_index(), 52)
        p.index = p.index + pd.Timedelta(days=3)                       # martes del informe → viernes de publicación
        out[f"COT_{inst}"] = p
    return out


def asignar(X: pd.DataFrame, P: dict) -> pd.DataFrame:
    """A cada operación, el último percentil publicado estrictamente antes de su fecha de sesión; y su tercil (0 bajo, 1, 2 alto)."""
    X = X.copy(); fs = pd.to_datetime(X.ses.astype(str))
    for k in INDICADORES:
        if k == "COT":
            val = np.full(len(X), np.nan)
            for inst in ("NQ", "ES"):
                m = (X.inst == inst).to_numpy(); s = P[f"COT_{inst}"].dropna()
                idx = s.index.searchsorted(fs[m], side="left") - 1     # publicación < fecha de sesión
                val[m] = np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan)
        else:
            s = P[k].dropna(); idx = s.index.searchsorted(fs, side="left") - 1
            val = np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan)
        X[f"p_{k}"] = val; X[f"t_{k}"] = np.where(np.isnan(val), -1, np.digitize(val, [1 / 3, 2 / 3]))
    return X


def _boot_dif(alto: pd.DataFrame, bajo: pd.DataFrame, rng) -> tuple[float, float]:
    """Diferencia de medias (alto − bajo) y p de dos colas por bootstrap de sesiones dentro de cada grupo (centrado en 0)."""
    def sumas(g):
        a = g.groupby("ses").R.agg(["sum", "count"]); return a["sum"].to_numpy(), a["count"].to_numpy()
    sa, ca = sumas(alto); sb, cb = sumas(bajo); d = alto.R.mean() - bajo.R.mean()
    ia = rng.integers(0, len(sa), (B, len(sa))); ib = rng.integers(0, len(sb), (B, len(sb)))
    db = sa[ia].sum(1) / ca[ia].sum(1) - sb[ib].sum(1) / cb[ib].sum(1)
    return float(d), float(min(1.0, 2 * min(((db - d) >= abs(d)).mean() + 1 / B, ((db - d) <= -abs(d)).mean() + 1 / B)))


def _mes(g):
    m = g.groupby(pd.to_datetime(g.ses.astype(str)).dt.to_period("M")).R.sum()
    return dict(R_mes=float(m.mean()), t_mes=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))) if len(m) > 2 else None,
                pct_meses_pos=float((m > 0).mean()), meses=int(len(m)))


def conteo() -> dict:
    X = asignar(operaciones(), indicadores()); out = {}
    for e in ESTRATEGIAS:
        for k in INDICADORES:
            g = X[(X.est == e) & (X[f"t_{k}"] >= 0)]
            out[f"{e}|{k}"] = {b: {str(t): int(((g.bloque == b) & (g[f"t_{k}"] == t)).sum()) for t in (0, 1, 2)} for b in ("DESC", "REP")}
    cor = X[[f"p_{k}" for k in INDICADORES]].drop_duplicates().corr(method="spearman").round(2)
    ev = np.linalg.eigvalsh(cor.fillna(0).to_numpy()); n_ef = float(ev.sum() ** 2 / (ev ** 2).sum())
    res = dict(n_por_tercil=out, spearman_indicadores=cor.to_dict(), n_efectivo_indicadores=n_ef)
    (DIR / "CONTEO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False)); return res


def correr() -> dict:
    sys.path.insert(0, str(ROOT / "tools")); from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    from edgelab.discovery.scan import benjamini_hochberg
    X = asignar(operaciones(), indicadores()); rng = np.random.default_rng(SEMILLA); filas = []
    for e in ESTRATEGIAS:
        for k in INDICADORES:
            g = X[(X.est == e) & (X[f"t_{k}"] >= 0)]; D, R_ = g[g.bloque == "DESC"], g[g.bloque == "REP"]
            ter = {str(t): dict(n=int((D[f"t_{k}"] == t).sum()), R=float(D[D[f"t_{k}"] == t].R.mean())) for t in (0, 1, 2)}
            d, p = _boot_dif(D[D[f"t_{k}"] == 2], D[D[f"t_{k}"] == 0], rng)
            sd = float(D.R.std()); n0, n2 = ter["0"]["n"], ter["2"]["n"]
            filas.append(dict(est=e, ind=k, dif=d, p=p, terciles=ter, mde80=float(2.8 * sd * np.sqrt(1 / max(n0, 1) + 1 / max(n2, 1))),
                              monotono=bool((ter["0"]["R"] - ter["1"]["R"]) * (ter["1"]["R"] - ter["2"]["R"]) > 0), _D=D, _R=R_, _k=k))
    padj = benjamini_hochberg([f["p"] for f in filas]); rej = padj <= Q
    for f, r_, pa in zip(filas, rej, padj):
        f["p_bh"] = float(pa); f["nominada"] = bool(r_); D, R_, k = f.pop("_D"), f.pop("_R"), f.pop("_k")
        peor = 0 if f["terciles"]["0"]["R"] < f["terciles"]["2"]["R"] else 2; f["tercil_excluido"] = peor
        f["sin_filtro_desc"] = _mes(D); f["con_filtro_desc"] = _mes(D[D[f"t_{k}"] != peor])
        if f["nominada"]:
            d2, p2 = _boot_dif(R_[R_[f"t_{k}"] == 2], R_[R_[f"t_{k}"] == 0], rng)
            f["rep"] = dict(dif=d2, p_una_cola=p2 / 2 if np.sign(d2) == np.sign(f["dif"]) else 1 - p2 / 2,
                            n={str(t): int((R_[f"t_{k}"] == t).sum()) for t in (0, 1, 2)},
                            sin_filtro=_mes(R_), con_filtro=_mes(R_[R_[f"t_{k}"] != peor]))
            f["rep"]["replica"] = bool(f["rep"]["p_una_cola"] < 0.05 and f["rep"]["con_filtro"]["R_mes"] >= f["rep"]["sin_filtro"]["R_mes"])
            g = D.assign(an=D.ses // 10000); f["por_anio"] = {int(a): float(x[x[f"t_{k}"] == 2].R.mean() - x[x[f"t_{k}"] == 0].R.mean())
                                                              for a, x in g.groupby("an")}
    res = dict(campana=CAMPANA, pruebas=len(filas), nominadas=sum(f["nominada"] for f in filas),
               replicadas=sum(f.get("rep", {}).get("replica", False) for f in filas), filas=filas)
    res["veredicto"] = "FILTRO_REPLICADO" if res["replicadas"] else ("NOMINADO_SIN_REPLICA" if res["nominadas"] else "SIN_FILTRO")
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float)); return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "conteo"
    r = {"conteo": conteo, "correr": correr}[cmd]()
    print(json.dumps({k: v for k, v in r.items() if k != "filas"} if cmd == "correr" else r, indent=1, ensure_ascii=False)[:6000])
