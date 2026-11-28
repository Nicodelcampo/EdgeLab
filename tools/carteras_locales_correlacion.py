#!/usr/bin/env python3
"""CARTERAS-LOCALES-CORRELACION (2026-11-26): correlación y curvas de capital de las carteras de la sesión local (INTRADIA8, INTERDIA3,
C2VZ_2 de cartera_nt8_20261125; P_OPT_SF_v2 de fundedsync_deploy_multiprop_20261122) y la canasta T+R+Z-banda+RQ5 NQ, con todas las
particiones (también HOLDOUT A5; TERMINAL sólo donde ya estaba abierto). Pre-registro: docs/research/carteras_locales_correlacion_20261126/."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "docs/research/carteras_locales_correlacion_20261126"
INTRA8 = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
INTER3 = ["SOMSF_NQ", "C2VZ_NQ", "C2VZ_ES"]


def series() -> pd.DataFrame:
    from edgelab.research.embudo_runners import friccion
    M = pd.read_csv(ROOT / "docs/research/cartera_nt8_20261125/MATRIZ_DIARIA_1MICRO.csv.gz", parse_dates=["dia"]).set_index("dia")
    S = {"INTRADIA8_usd": M[INTRA8].sum(axis=1), "INTERDIA3_usd": M[INTER3].sum(axis=1), "C2VZ_2_usd": M[["C2VZ_NQ", "C2VZ_ES"]].sum(axis=1)}
    P = pd.read_csv(ROOT / "docs/research/fundedsync_deploy_multiprop_20261122/REFERENCIA_PARIDAD_P_OPT_SF_v2.csv")
    P["dia"] = pd.to_datetime(P.fecha_int.astype(str)); S["P_OPT_SF_v2_R"] = (P.w_w5 * P.R_neto_mini).groupby(P.dia).sum()
    fr = float(friccion("NQ")[0]); partes = []
    t = pd.read_csv(ROOT / "docs/research/m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz"); t = t[t.riesgo > 0]
    partes.append(pd.Series((t.neto / t.riesgo).to_numpy(), index=pd.to_datetime(t.dia)))
    RZ = pd.read_csv(ROOT / "docs/research/neto_pistas_20261119/RZ_OPS.csv.gz"); RZ = RZ[RZ.inst == "NQ"]
    r = RZ[(RZ.modulo == "R") & (RZ.variante == "R_21_100_2.5_660")]; rg = 0.25 * r.atr20; ok = (rg > 0).to_numpy()
    partes.append(pd.Series(((np.where(r.mae_pts >= rg, -rg, r.pnl_pts) - fr) / rg).to_numpy()[ok], index=pd.to_datetime(r.ses).to_numpy()[ok]))
    banda = [f"Z_{a}_{b}_{e}" for (a, b) in ((10, 30), (15, 20), (30, 10)) for e in (35, 45, 55)]
    z = RZ[(RZ.modulo == "Z") & RZ.variante.isin(banda)].copy(); z["rg"] = 0.25 * z.atr20
    z["br"] = np.where(z.mae_pts >= z.rg, -z.rg, z.pnl_pts); z = z[z.rg > 0].groupby("ses")[["br", "rg"]].mean()
    partes.append(pd.Series(((z.br - fr) / z.rg).to_numpy(), index=pd.to_datetime(z.index)))
    en = "P_obj_s0.45_tp2_stop_s0.45_tp2_fin"; frr = float(friccion("NQ")[0])
    o = pd.read_csv(ROOT / "docs/research/rq5_regimen_20261119/OPS_DESC_REP.csv.gz")
    o = o[o["L60_m1_c689"].astype(bool) & (o.inst == "NQ") & o[f"r_{en}"].notna() & (o[f"k_{en}"] > 0)]
    partes.append(pd.Series((o[f"r_{en}"] - frr / o[f"k_{en}"]).to_numpy(), index=pd.to_datetime(o.ses.astype(str))))
    h = pd.read_csv(ROOT / "docs/research/rq5_regimen_20261119/HOLDOUT_OPS.csv.gz"); h = h[h.inst == "NQ"]
    partes.append(pd.Series(h.R.to_numpy(), index=pd.to_datetime(h.ses.astype(str))))
    c = pd.concat(partes); S["CANASTA_TRZQ_R"] = c.groupby(level=0).sum()
    D = pd.DataFrame(S).sort_index(); D = D[(D.index >= "2019-07-01") & (D.index <= "2026-11-17")].fillna(0.0)
    D.loc[D.index < "2025-01-01", "P_OPT_SF_v2_R"] = np.nan                       # su referencia empieza en 2025-01
    D.loc[D.index > "2026-09-30", ["INTRADIA8_usd", "INTERDIA3_usd", "C2VZ_2_usd", "CANASTA_TRZQ_R"]] = np.nan   # sin terminal abierto
    return D


def _st(x):
    x = x.dropna(); m = x.groupby(x.index.to_period("M")).sum()
    return dict(por_mes=float(m.mean()), t_mes=float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))) if len(m) > 2 else None,
                pct_meses_pos=float((m > 0).mean()), meses=int(len(m)), caida_max=float((x.cumsum() - x.cumsum().cummax()).min()))


def main():
    from registro_global import exigir_contada
    exigir_contada(DIR / "PREREGISTRO.md")
    from edgelab.holdout import a5_bloque
    D = series(); D.to_csv(DIR / "SERIES_DIARIAS.csv.gz")
    blq = pd.Series([("TERMINAL" if s >= 20261001 else a5_bloque(s)) for s in D.index.strftime("%Y%m%d").astype(int)], index=D.index)
    D = D.T.groupby(level=0).sum(min_count=1).T if False else D
    sin = D.drop(columns="P_OPT_SF_v2_R").loc[:"2026-09-30"]; con = D.loc["2025-01-01":"2026-09-30"]
    res = dict(corr_mensual_2019_2026=sin.groupby(sin.index.to_period("M")).sum().corr().round(3).to_dict(),
               corr_diaria_2019_2026=sin.corr().round(3).to_dict(),
               corr_mensual_2025_2026=con.groupby(con.index.to_period("M")).sum().corr().round(3).to_dict(),
               corr_diaria_2025_2026=con.corr().round(3).to_dict(),
               por_bloque={c: {b: _st(D[c][blq == b]) for b in ("DESC", "REP", "HOLDOUT", "TERMINAL") if D[c][blq == b].notna().any()} | {"TODO": _st(D[c])} for c in D})
    (DIR / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    # las curvas (CURVAS_*.png) se graficaron aparte desde SERIES_DIARIAS.csv.gz: matplotlib no está en el entorno base del repo
    print(pd.DataFrame(res["corr_mensual_2019_2026"]).round(2)); print(pd.DataFrame(res["corr_mensual_2025_2026"]).round(2))
    for c, v in res["por_bloque"].items(): print(c, {b: (round(x["por_mes"], 2), round(x["t_mes"] or 0, 2), round(x["pct_meses_pos"], 2), x["meses"]) for b, x in v.items()})


if __name__ == "__main__":
    main()
