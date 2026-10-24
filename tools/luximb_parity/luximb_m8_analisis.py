"""M8 — Parte A (desbalance por vida, ajustado por contexto) y Parte B (GBM franjas vs GBM contexto).
Reglas: MANIFIESTO_M8_FRANJAS_DESBALANCE_LUXIMB_20261020.md. Uso: python tools/luximb_parity/luximb_m8_analisis.py <features.csv> <out.json>"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

VIDAS = (100, 200, 500, 1000); NB = 10000
CTX = ["vol_pre", "atr14", "hora", "R", "velas25", "dir"]
FR = [f"{k}_{v}" for v in VIDAS for k in ("n_ad", "n_at", "n_in", "D", "fog_ad", "dist_ad", "dist_at")]
GBM = dict(max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=40, random_state=0)


def estratos(df, cortes_v, cortes_r):
    return (np.digitize(df.vol_pre, cortes_v).astype(str) + df.cash.map({True: "c", False: "r"}) + np.digitize(df.R, cortes_r).astype(str))


def a1(df, v, cortes, rng):
    lo, hi = cortes                                                   # adelante: D >= max(p80, >0); atras: D <= min(p20, <0)
    d = df.copy(); D = d[f"D_{v}"]
    d["q"] = np.where(D >= max(hi, 1e-9), 4, np.where(D <= min(lo, -1e-9), 0, 2)); d = d[d.q.isin([0, 4])]

    def fn(x):
        tot = acc = 0.0
        for _, g in x.groupby("estr"):
            top, bot = g[g.q == 4], g[g.q == 0]
            if len(top) and len(bot):
                w = len(top) + len(bot); acc += w * (top.y1_tg.mean() - bot.y1_tg.mean()); tot += w
        return acc / tot if tot else np.nan
    days = d.dia.unique(); ix = {k: np.flatnonzero(d.dia.values == k) for k in days}
    full = fn(d); bs = np.array([fn(d.iloc[np.concatenate([ix[k] for k in rng.choice(days, len(days))])]) for _ in range(NB)])
    p2 = 2 * min(np.nanmean(bs <= 0), np.nanmean(bs >= 0))
    return dict(est=round(float(full), 4), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                p_bilateral=float(min(1, p2)), se=float(np.nanstd(bs)), n_top=int((d.q == 4).sum()), n_bot=int((d.q == 0).sum()),
                crudo=round(float(d[d.q == 4].y1_tg.mean() - d[d.q == 0].y1_tg.mean()), 4))


def ll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def cv_mejora(df):
    days = np.array(sorted(df.dia.unique())); folds = np.array_split(days, 5); out = np.full(len(df), np.nan)
    for k, f in enumerate(folds):
        lo, hi = f[0], f[-1]; pos = np.searchsorted(days, [lo, hi])
        purga = set(days[max(0, pos[0] - 1):pos[1] + 2])                  # test + 1 dia a cada lado
        tr = ~df.dia.isin(purga); te = df.dia.isin(set(f))
        mc = HistGradientBoostingClassifier(**GBM).fit(df.loc[tr, CTX], df.loc[tr, "y1_tg"])
        mf = HistGradientBoostingClassifier(**GBM).fit(df.loc[tr, CTX + FR], df.loc[tr, "y1_tg"])
        y = df.loc[te, "y1_tg"].values
        out[np.flatnonzero(te)] = ll(y, mc.predict_proba(df.loc[te, CTX])[:, 1]) - ll(y, mf.predict_proba(df.loc[te, CTX + FR])[:, 1])
    return out


def boot_media(d, col, rng):
    days = d.dia.unique(); ix = {k: np.flatnonzero(d.dia.values == k) for k in days}; v = d[col].values
    bs = np.array([v[np.concatenate([ix[k] for k in rng.choice(days, len(days))])].mean() for _ in range(NB)])
    return dict(est=round(float(v.mean()), 6), ic95=[round(float(np.percentile(bs, 2.5)), 6), round(float(np.percentile(bs, 97.5)), 6)],
                p_unilateral=float(np.mean(bs <= 0)))


def main():
    df = pd.read_csv(sys.argv[1]); df = df[df.vol_pre.notna() & df.atr14.notna()].reset_index(drop=True)
    nq, es = df[df.inst == "NQ"].reset_index(drop=True), df[df.inst == "ES"].reset_index(drop=True)
    rng = np.random.default_rng(20261026)
    cv_v = np.quantile(nq.vol_pre, [.2, .4, .6, .8]); cv_r = np.quantile(nq.R, [1 / 3, 2 / 3])
    for d in (nq, es):
        d["estr"] = estratos(d, cv_v if d is nq else np.quantile(d.vol_pre, [.2, .4, .6, .8]), cv_r if d is nq else np.quantile(d.R, [1 / 3, 2 / 3]))
    A, A_es, qcuts = {}, {}, {}
    for v in VIDAS:
        qc = tuple(float(x) for x in np.quantile(nq[f"D_{v}"], [.2, .8])); qcuts[v] = qc     # cortes de NQ, tambien para ES
        A[f"A1_vida{v}"] = a1(nq, v, qc, rng); A_es[f"A1_vida{v}_ES_descriptivo"] = a1(es, v, qc, rng)
    ps = sorted(A, key=lambda k: A[k]["p_bilateral"]); holm = {}; run = 0.0
    for k, n in enumerate(ps):
        run = max(run, min(1.0, (len(ps) - k) * A[n]["p_bilateral"])); holm[n] = round(run, 4)
    nq["mejora_ll"] = cv_mejora(nq)
    B_nq = boot_media(nq, "mejora_ll", rng)
    mc = HistGradientBoostingClassifier(**GBM).fit(nq[CTX], nq.y1_tg); mf = HistGradientBoostingClassifier(**GBM).fit(nq[CTX + FR], nq.y1_tg)
    es["mejora_ll"] = ll(es.y1_tg.values, mc.predict_proba(es[CTX])[:, 1]) - ll(es.y1_tg.values, mf.predict_proba(es[CTX + FR])[:, 1])
    B_es = boot_media(es, "mejora_ll", rng)
    res = dict(manifiesto="MANIFIESTO_M8_FRANJAS_DESBALANCE_LUXIMB_20261020.md", n_NQ=len(nq), dias_NQ=nq.dia.nunique(), n_ES=len(es), dias_ES=es.dia.nunique(),
               P_Tg_NQ=round(nq.y1_tg.mean(), 4), P_Tg_ES=round(es.y1_tg.mean(), 4),
               cortes_D_p20_p80=qcuts, parteA_NQ=A, parteA_holm=holm, MDE80_A1_pp={k: round(280 * v["se"], 1) for k, v in A.items()}, parteA_ES_descriptivo=A_es,
               parteB=dict(B1_NQ_cv_mejora_logloss=B_nq, B1_ES_externo_mejora_logloss=B_es,
                           pasa=bool(B_nq["ic95"][0] > 0 and B_es["ic95"][0] > 0)),
               ll_base_NQ=round(float(ll(nq.y1_tg.values, np.full(len(nq), nq.y1_tg.mean())).mean()), 5),
               desbalance_medio={f"D_{v}": [round(float(nq[f'D_{v}'].mean()), 4), round(float(es[f'D_{v}'].mean()), 4)] for v in VIDAS})
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
