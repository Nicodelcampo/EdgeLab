"""M7b: control por volatilidad previa de M7-H2. Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M7B_CONTROL_VOLATILIDAD_ES_20261020.md
Uso: python tools/luximb_parity/luximb_m7b.py <eventos_m7_con_vol_pre.csv> <out.json>"""
import json
import sys

import numpy as np
import pandas as pd

NB = 10000


def boot(df, fn, rng):
    days = df.dia.unique(); idx = {d: np.flatnonzero(df.dia.values == d) for d in days}
    full = fn(df); bs = np.empty(NB)
    for k in range(NB):
        bs[k] = fn(df.iloc[np.concatenate([idx[d] for d in rng.choice(days, len(days))])])
    return dict(est=round(float(full), 4), ic95=[round(float(np.nanpercentile(bs, 2.5)), 4), round(float(np.nanpercentile(bs, 97.5)), 4)],
                p_unilateral_menor=float(np.mean(bs >= 0)), se=float(np.nanstd(bs)))


def main():
    df = pd.read_csv(sys.argv[1]); df = df[df.vol_pre.notna() & (df.vol_pre > 0) & df.recorrido_pts.notna()].copy()
    q = np.quantile(df.vol_pre, [.2, .4, .6, .8]); df["qv"] = np.digitize(df.vol_pre, q)
    df["estrato"] = df.qv.astype(str) + df.cash.map({True: "c", False: "r"}); df["ratio"] = df.recorrido_pts / df.vol_pre
    fuera = int(sum(g.esT.sum() for _, g in df.groupby("estrato") if not (~g.esT).any()))

    def estratificado(d):
        tot, acc = 0, 0.0
        for _, g in d.groupby("estrato"):
            nt = int(g.esT.sum())
            if nt and (~g.esT).any(): acc += nt * (g.loc[g.esT, "recorrido_pts"].mean() - g.loc[~g.esT, "recorrido_pts"].mean()); tot += nt
        return acc / tot if tot else np.nan
    rng = np.random.default_rng(20261025)
    crudo = boot(df, lambda d: d.loc[d.esT, "recorrido_pts"].mean() - d.loc[~d.esT, "recorrido_pts"].mean(), rng)
    H = {"H2b_recorrido_estratificado_volpre_x_franja": boot(df, estratificado, rng),
         "H2c_ratio_recorrido_sobre_volpre": boot(df, lambda d: d.loc[d.esT, "ratio"].mean() - d.loc[~d.esT, "ratio"].mean(), rng)}
    ps = sorted(H, key=lambda k: H[k]["p_unilateral_menor"]); holm = {}; run = 0.0
    for k, n in enumerate(ps):
        run = max(run, min(1.0, (len(ps) - k) * H[n]["p_unilateral_menor"])); holm[n] = round(run, 4)
    vp = {g: [round(float(v), 2) for v in x.vol_pre.quantile([.1, .25, .5, .75, .9])] for g, x in df.groupby(df.esT.map({True: "T", False: "C"}))}
    pq_ = df.groupby(["qv", "esT"]).recorrido_pts.agg(["size", "mean"]).round(2).reset_index().to_dict("records")
    out = dict(manifiesto="MANIFIESTO_M7B_CONTROL_VOLATILIDAD_ES_20261020.md", n=len(df), cortes_quintiles_vol_pre=q.round(2).tolist(),
               vol_pre_p10_25_50_75_90=vp, efecto_crudo_M7=crudo, hipotesis=H, p_holm=holm,
               MDE80={k: round(2.8 * v["se"], 3) for k, v in H.items()}, T_fuera_de_estratos=fuera, por_quintil=pq_)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
