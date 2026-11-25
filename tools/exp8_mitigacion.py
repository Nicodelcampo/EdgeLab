"""EXP-8 (pre-registro `docs/research/caida_2026_20261125/PREREGISTRO_EXP8_MITIGACION.md`, contado: 24 pruebas).

Parte A: filtro de estado de la apertura (media de 20 sesiones previas vs su mediana expansiva) sobre 8 estrategias.
Parte B: armado de cartera con reglas fijas (descriptivo).

  python tools/exp8_mitigacion.py --out docs/research/caida_2026_20261125/exp8 --corrida 1

Nunca lee el holdout terminal: las operaciones y el M1 cortan en 2026-09-30.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import exp7_estabilizadores as E7  # noqa: E402
from diag_caida_2026 import sesiones  # noqa: E402
from edgelab.holdout import a5_bloque  # noqa: E402

C, N = E7.CAND, E7.NUEVAS
PARTE_A = {"T_NQ": (C / "T" / "NT8_T_NQ_fijo1.csv", "NQ"), "R_NQ": (C / "R" / "NT8_R_NQ_fijo1.csv", "NQ"),
           "Z_NQ": (C / "Z" / "NT8_Z_NQ_fijo1.csv", "NQ"), "V_NQ": (C / "V" / "NT8_V_NQ_fijo1.csv", "NQ"),
           "RQ5_NQ": (N / "NT8_RQ5_NQ.csv", "NQ"), "RQ5_ES": (N / "NT8_RQ5_ES.csv", "ES"),
           "ES5N_ES": (N / "NT8_ES5N_ES.csv", "ES"), "Franklin_NQ": (N / "NT8_Franklin_NQ.csv", "NQ")}
EXTRA_B = {"SOMSF_NQ": E7.ESTAB_NT8["SOMSF_NQ"], "C2VZ_NQ": E7.ESTAB_NT8["C2VZ_NQ"], "C2VZ_ES": E7.ESTAB_NT8["C2VZ_ES"]}
MANANA = ["T_NQ", "RQ5_NQ", "RQ5_ES", "ES5N_ES", "Franklin_NQ"]
VARS = {"cont_orb": 1, "ac5_manana": 1, "frac_noche": -1}      # +1: encendido si >= umbral; -1: si <= umbral
VENTANA, MIN_HIST = 20, 250


def estado(inst: str) -> pd.DataFrame:
    """Por sesión completa k: media de las 20 sesiones que terminan en k y mediana expansiva de esa media (>= 250 valores).
    Se usa para la sesión siguiente (merge_asof estricto): nada de la sesión operada entra en su propio estado."""
    s = sesiones(inst).sort_values("dt").reset_index(drop=True)
    out = pd.DataFrame({"dt": s.dt})
    for v in VARS:
        m = s[v].rolling(VENTANA, min_periods=15).mean()
        out[v + "_20"] = m
        out[v + "_umb"] = m.expanding(min_periods=MIN_HIST).median()
    return out


def con_estado(o: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    o = o.copy(); o["dt"] = pd.to_datetime(o.ses.astype(str)); o = o.sort_values("dt")
    m = pd.merge_asof(o, est, on="dt", direction="backward", allow_exact_matches=False)
    for v, sgn in VARS.items():
        x, u = m[v + "_20"], m[v + "_umb"]
        m["on_" + v] = np.where(x.isna() | u.isna(), np.nan, np.where(sgn * (x - u) >= 0, 1.0, 0.0))
    m["bloque"] = [("2026" if s >= 20260101 else a5_bloque(int(s))) for s in m.ses]
    return m


def dd(x: pd.Series) -> float:
    c = x.cumsum().to_numpy()
    return float((c - np.maximum.accumulate(np.r_[0.0, c])[1:]).min())


def metricas(x: pd.Series) -> dict:
    return dict(R_mes=round(float(x.mean()), 3), sd=round(float(x.std(ddof=1)), 3), meses_neg=int((x < 0).sum()), n_meses=len(x),
                maxDD=round(dd(x), 2), peor_6m=round(float(x.rolling(6).sum().min()), 2),
                R_mes_sobre_DD=round(float(x.mean() / max(-dd(x), 1e-9)), 4))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--corrida", type=int, default=1)
    a = ap.parse_args(argv); a.out.mkdir(parents=True, exist_ok=True)
    est = {i: estado(i) for i in ("NQ", "ES")}
    ops = {k: E7.ops_nt8(p, i) for k, (p, i) in {**PARTE_A, **EXTRA_B}.items()}
    ops19 = {k: o[(o.ses >= 20190101) & (o.ses <= 20260930)] for k, o in ops.items()}
    ops = {k: o[o.ses >= 20200101] for k, o in ops19.items()}
    res_a, pvals, filtradas = {}, {}, {}
    for k, (_, inst) in PARTE_A.items():
        m = con_estado(ops[k], est[inst]); filtradas[k] = m
        for v in VARS:
            r = {}
            for b in ("DESC", "REP", "HOLDOUT", "2026"):
                g = m[(m.bloque == b) & m["on_" + v].notna()]
                if a.corrida >= 2:                     # auditoría: la unidad es la sesión (R sumado del día), no la operación
                    g = g.groupby("ses").agg(R=("R", "sum"), on=("on_" + v, "first")).rename(columns={"on": "on_" + v})
                on, off = g.R[g["on_" + v] == 1], g.R[g["on_" + v] == 0]
                if len(on) > 2 and len(off) > 2:
                    t = stats.ttest_ind(on, off, equal_var=False, alternative="greater")
                    se = np.sqrt(on.var(ddof=1) / len(on) + off.var(ddof=1) / len(off))
                    r[b] = dict(n_on=len(on), n_off=len(off), frac_on=round(len(on) / len(g), 3), R_on=round(on.mean(), 4),
                                R_off=round(off.mean(), 4), dif=round(on.mean() - off.mean(), 4), p=round(float(t.pvalue), 4),
                                mde=round(float(2.49 * se), 4), R_sin=round(g.R.mean(), 4))
                else:
                    r[b] = dict(n_on=len(on), n_off=len(off))
            res_a[f"{k}|{v}"] = r; pvals[f"{k}|{v}"] = r["DESC"].get("p", np.nan)
    nom = E7.bh(pvals, 0.10)
    for key, r in res_a.items():
        rep = r["REP"]; r["BH_DESC"] = nom[key]
        r["confirma_REP"] = bool(nom[key] and rep.get("dif", -1) > 0 and rep.get("p", 1) <= 0.10)
    conf = [k for k, r in res_a.items() if r["confirma_REP"]]

    # Parte B
    mens = pd.DataFrame({k: E7.mensual(o) for k, o in ops.items()})
    todas = list(mens.columns)
    if a.corrida >= 2:                                 # auditoría: la volatilidad de 2020 se estima con 2019
        M19 = pd.period_range("2019-01", "2026-09", freq="M")
        m19 = pd.DataFrame({k: pd.to_datetime(o.ses.astype(str)).dt.to_period("M").pipe(lambda q: o.groupby(q).R.sum()).reindex(M19, fill_value=0.0)
                            for k, o in ops19.items()})
        for k, o in ops19.items():                     # antes de la primera operación de la corrida NT8 no hay historia (no es 0)
            m19.loc[m19.index < pd.Period(str(int(o.ses.min()))[:6], "M"), k] = np.nan
        sd12 = m19.rolling(12, min_periods=12).std(ddof=1).shift(1).reindex(mens.index)
    else:
        sd12 = mens.rolling(12).std(ddof=1).shift(1)
    w = (1 / sd12).replace([np.inf, -np.inf], np.nan)
    w = w.div(w.sum(axis=1), axis=0) * len(todas)
    w = w.clip(0.25, 2.0).fillna(1.0)
    esq = {"IGUAL_MANANA": mens[MANANA].sum(axis=1), "IGUAL_TODAS": mens[todas].sum(axis=1),
           "INV_VOL_TODAS": (mens[todas] * w[todas]).sum(axis=1),
           "MANANA_MAS_C2VZ": mens[MANANA + ["C2VZ_NQ", "C2VZ_ES"]].sum(axis=1)}
    if conf:
        mf = mens.copy()
        for key in conf:
            k, v = key.split("|"); f = filtradas[k]
            mf[k] = E7.mensual(f[f["on_" + v] != 0])
        esq["IGUAL_TODAS_FILTRO"] = mf[todas].sum(axis=1)
    anio = pd.Series([p.year for p in mens.index], index=mens.index)
    res_b = {e: {"2020_2025": metricas(x[anio <= 2025]), "2026": metricas(x[anio == 2026])} for e, x in esq.items()}
    res_b["_correlacion_mensual_2020_2025"] = mens[anio <= 2025].corr().round(2).to_dict()

    # 2026 descriptivo por estrategia: R total con y sin cada filtro
    d26 = {}
    for k, m in filtradas.items():
        g = m[m.bloque == "2026"]
        d26[k] = {"sin": round(float(g.R.sum()), 2), **{v: round(float(g.R[g["on_" + v] == 1].sum()), 2) for v in VARS}}
    out = dict(corrida=a.corrida, parte_a=res_a, nominadas_BH=[k for k, x in nom.items() if x], confirmadas=conf,
               parte_b=res_b, r_2026_por_filtro=d26, pesos_inv_vol_ultimo=w.iloc[-1].round(2).to_dict())
    (a.out / f"EXP8_corrida{a.corrida}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    pd.DataFrame(esq).round(3).to_csv(a.out / f"CARTERAS_MENSUALES_corrida{a.corrida}.csv")
    for key, r in res_a.items():
        d = r["DESC"]; p = r["REP"]
        print(f"{key:24s} DESC on {d.get('R_on')} off {d.get('R_off')} dif {d.get('dif')} p {d.get('p')} mde {d.get('mde')} "
              f"fon {d.get('frac_on')} | REP dif {p.get('dif')} p {p.get('p')} | 26 dif {r['2026'].get('dif')} BH {r['BH_DESC']}")
    print("confirmadas:", conf)
    for e, x in res_b.items():
        if not e.startswith("_"): print(e, x)
    print(json.dumps(d26))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
