#!/usr/bin/env python3
"""T-MECANISMO-ETF-APALANCADOS (`PLAN_ESPIRAL_20261127 #2`): prueba si la ventaja de T (apertura NT8) sigue el flujo de
rebalanceo de ETFs apalancados 3x (Baltussen et al. 2021) en serie temporal, presión causal t-1 -> t y orden entre índices.

Pre-registro: docs/research/t_mecanismo_etf_apalancados_20261127/PREREGISTRO.md (K32/K51/K60/A5).
Evalua ESTRICTAMENTE sobre DESC + REP (< 2026-10-01); nada de HOLDOUT ni TERMINAL.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque, exigir_sin_holdout_no_abierto, mascara_a5_limpia  # noqa: E402
from edgelab.research.m1_intradia import leer_m1nt8  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

PRE = "docs/research/t_mecanismo_etf_apalancados_20261127/PREREGISTRO.md"
DATA = ROOT / "data/etf_apalancados"
DATA.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs/research/t_mecanismo_etf_apalancados_20261127"
OUT.mkdir(parents=True, exist_ok=True)

CORTE_TS = pd.Timestamp("2026-10-01")
ETF_GROUPS = {
    "NQ": ["TQQQ", "SQQQ"],
    "ES": ["UPRO", "SPXL", "SPXU", "SPXS"],
    "YM": ["UDOW", "SDOW"],
    "RTY": ["TNA", "TZA"],
}
MULTS = {"NQ": 20.0, "ES": 50.0, "YM": 5.0, "RTY": 50.0, "EMD": 100.0}
Phi = lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _fetch_yahoo_etf(sym: str) -> pd.DataFrame:
    pq = DATA / f"{sym}.parquet"
    if pq.exists():
        df = pd.read_parquet(pq)
        if len(df) and df.index.max() < CORTE_TS:
            return df
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=1262304000&period2={int(CORTE_TS.timestamp())}&interval=1d"
    b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    j = json.loads(b)["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    off = int(j["meta"].get("gmtoffset", 0))
    idx = (pd.to_datetime(j["timestamp"], unit="s") + pd.Timedelta(seconds=off)).normalize()
    df = pd.DataFrame({"c": q["close"], "v": q["volume"]}, index=idx).dropna()
    df = df[~df.index.duplicated(keep="last") & (df.index < CORTE_TS)]
    df["dvol"] = df["c"].astype(float) * df["v"].astype(float)
    df.to_parquet(pq)
    return df


def _load_fut_daily() -> dict[str, pd.DataFrame]:
    pq = DATA / "fut_daily_v1.parquet"
    if pq.exists():
        raw = pd.read_parquet(pq)
        return {s: raw[raw["sym"] == s].drop(columns=["sym"]) for s in MULTS}
    frames = []
    for sym, mult in MULTS.items():
        D = leer_m1nt8(ROOT / f"data/m1nt8/{sym}_M1_nonadj_utc.parquet")
        D = D[(D.index >= "2010-01-01") & (D.index < CORTE_TS) & (D.index.dayofweek < 5)]
        d_idx = D.index.normalize()
        hhmm = D.index.hour * 100 + D.index.minute
        rth = D[(hhmm >= 930) & (hhmm <= 1600)]
        px_c = rth.groupby(rth.index.normalize())["c"].last()
        vol_tot = D.groupby(d_idx)["v"].sum()
        df = pd.DataFrame({"px": px_c, "vol": vol_tot.reindex(px_c.index).fillna(0.0)})
        df["dvol_fut"] = df["px"] * df["vol"] * mult
        df["ret_1d"] = df["px"] / df["px"].shift(1) - 1.0
        df["sym"] = sym
        frames.append(df)
    all_f = pd.concat(frames)
    all_f.to_parquet(pq)
    return {s: all_f[all_f["sym"] == s].drop(columns=["sym"]) for s in MULTS}


def _welch_t(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 5 or len(b) < 5:
        return 0.0, 1.0
    se = sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    t = float((a.mean() - b.mean()) / se) if se > 0 else 0.0
    return round(t, 2), round(1.0 - Phi(t), 5)


def main() -> int:
    exigir_contada(PRE)
    etfs = {sym: _fetch_yahoo_etf(sym) for grp in ETF_GROUPS.values() for sym in grp}
    futs = _load_fut_daily()

    # Build daily ratio_3x and lagged pressure per index (ONLY DESC+REP dates exposed for P&L; ratios are volume-only)
    panel = {}
    for sym, df_f in futs.items():
        if sym in ETF_GROUPS:
            etf_dv = sum(etfs[s]["dvol"].reindex(df_f.index).fillna(0.0) for s in ETF_GROUPS[sym])
        else:
            etf_dv = pd.Series(0.0, index=df_f.index)
        df = df_f.copy()
        df["etf_dvol"] = etf_dv
        df["ratio_3x"] = (df["etf_dvol"] / df["dvol_fut"].replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
        df["ratio_60d_lag"] = df["ratio_3x"].rolling(60, min_periods=20).mean().shift(1)
        df["pressure_lag"] = (df["ret_1d"].abs() * df["ratio_3x"]).shift(1)
        df["ret_lag"] = df["ret_1d"].shift(1)
        panel[sym] = df

    # Cross-sectional table 2021-2026-09 (volume-only DESC+REP mask)
    xs_rows = {}
    for sym, df in panel.items():
        d_int = np.asarray([int(d.strftime("%Y%m%d")) for d in df.index], dtype=int)
        msk_dr = mascara_a5_limpia(d_int)
        sub_pre = df.loc[msk_dr & (df.index >= "2010-03-01") & (df.index < "2021-01-01"), "ratio_3x"].dropna()
        sub_21 = df.loc[msk_dr & (df.index >= "2021-01-01"), "ratio_3x"].dropna()
        xs_rows[sym] = {
            "ratio_2010_2020_pct": round(float(sub_pre.mean() * 100), 2) if len(sub_pre) else 0.0,
            "ratio_2021_2026_pct": round(float(sub_21.mean() * 100), 2) if len(sub_21) else 0.0,
            "salto_x": round(float(sub_21.mean() / max(sub_pre.mean(), 1e-6)), 2) if len(sub_pre) and sub_pre.mean() > 0 else 0.0,
            "etf_dvol_2021_2026_musd": round(float(df.loc[msk_dr & (df.index >= "2021-01-01"), "etf_dvol"].mean() / 1e6), 1),
        }

    # Load T_NQ & T_ES daily R (SERIES_DIARIAS) and T_NQ trade ops (FUNDEDSYNC_OPS) masked strictly to DESC+REP
    sd = pd.read_csv(ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz", parse_dates=["dia"]).set_index("dia")
    sd_int = np.asarray([int(d.strftime("%Y%m%d")) for d in sd.index], dtype=int)
    msk_sd = mascara_a5_limpia(sd_int)
    sd_dr = sd.loc[msk_sd].copy()
    exigir_sin_holdout_no_abierto([int(d.strftime("%Y%m%d")) for d in sd_dr.index], "T_MECANISMO_ETF_APALANCADOS")

    ops = pd.read_csv(ROOT / "docs/research/fundedsyncstack_20261115/cadena/FUNDEDSYNC_OPS.csv.gz")
    t_ops = ops[(ops["modulo"] == "T") & (ops["riesgo"] > 0)].copy()
    t_ops["dia_int"] = pd.to_datetime(t_ops["dia"]).dt.strftime("%Y%m%d").astype(int)
    t_ops = t_ops[mascara_a5_limpia(t_ops["dia_int"])].copy()
    t_ops["R"] = t_ops["neto"] / t_ops["riesgo"]
    t_ops["d"] = pd.to_datetime(t_ops["dia"]).dt.normalize()
    exigir_sin_holdout_no_abierto(t_ops["dia_int"], "T_MECANISMO_ETF_APALANCADOS")

    ts_res = {}
    for sym, col_sd in [("NQ", "T_NQ"), ("ES", "T_ES")]:
        df_s = pd.DataFrame({"R": sd_dr[col_sd]}).join(panel[sym][["ratio_3x", "ratio_60d_lag", "pressure_lag", "ret_lag"]], how="inner").dropna(subset=["R", "ratio_60d_lag"])
        # Monthly Spearman rank correlation
        m_r = df_s["R"].groupby(lambda d: d.to_period("M")).sum()
        m_rat = df_s["ratio_60d_lag"].groupby(lambda d: d.to_period("M")).mean()
        rho = float(m_r.rank().corr(m_rat.rank()))
        # Pre-2021 vs Post-2021
        pre = df_s[df_s.index < "2021-01-01"]
        post = df_s[df_s.index >= "2021-01-01"]
        # Causal day-to-day pressure split on active T days (expanding median after 60d warmup)
        act = df_s[(df_s["R"] != 0) & df_s["pressure_lag"].notna()].copy()
        act["med_p"] = act["pressure_lag"].expanding(min_periods=30).median().shift(1)
        act_v = act.dropna(subset=["med_p"])
        hi = act_v.loc[act_v["pressure_lag"] >= act_v["med_p"], "R"].to_numpy()
        lo = act_v.loc[act_v["pressure_lag"] < act_v["med_p"], "R"].to_numpy()
        t_hl, p_hl = _welch_t(hi, lo)

        res_sym = {
            "meses_DR": int(len(m_r)),
            "spearman_mensual_R_vs_ratio60_lag": round(rho, 3),
            "pre_2021": {"n_dias": int(len(pre)), "R_dia_medio": round(float(pre["R"].mean()), 4), "ratio_pct": round(float(pre["ratio_3x"].mean() * 100), 2)},
            "post_2021": {"n_dias": int(len(post)), "R_dia_medio": round(float(post["R"].mean()), 4), "ratio_pct": round(float(post["ratio_3x"].mean() * 100), 2)},
            "presion_causal_alta_vs_baja": {
                "n_alta": int(len(hi)),
                "R_alta": round(float(hi.mean()), 4) if len(hi) else 0.0,
                "n_baja": int(len(lo)),
                "R_baja": round(float(lo.mean()), 4) if len(lo) else 0.0,
                "t_welch": t_hl,
                "p_una_cola": p_hl,
            },
        }
        if sym == "NQ":
            # Also check side alignment in FUNDEDSYNC_OPS: side==1 (long) when ret_lag > 0 (ETFs must buy at close/next open?)
            to_j = t_ops.merge(panel["NQ"][["ret_lag", "pressure_lag", "ratio_3x"]], left_on="d", right_index=True, how="inner").dropna(subset=["ret_lag"])
            same_sign = to_j[((to_j["side"] > 0) & (to_j["ret_lag"] > 0)) | ((to_j["side"] < 0) & (to_j["ret_lag"] < 0))]["R"].to_numpy()
            opp_sign = to_j[((to_j["side"] > 0) & (to_j["ret_lag"] < 0)) | ((to_j["side"] < 0) & (to_j["ret_lag"] > 0))]["R"].to_numpy()
            t_dir, p_dir = _welch_t(same_sign, opp_sign)
            res_sym["ops_side_vs_ret_lag"] = {
                "n_mismo_signo": int(len(same_sign)),
                "R_mismo_signo": round(float(same_sign.mean()), 4),
                "n_signo_opuesto": int(len(opp_sign)),
                "R_signo_opuesto": round(float(opp_sign.mean()), 4),
                "t_welch": t_dir,
            }
        ts_res[sym] = res_sym

    res = {"cross_sectional_ratio_3x": xs_rows, "time_series_y_presion": ts_res}
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [
        "# T-MECANISMO-ETF-APALANCADOS (`PLAN_ESPIRAL_20261127 #2`, `2010–2026-09`, `DESC+REP`)",
        "",
        "Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` pruebas, `T_MECANISMO_ETF_APALANCADOS`). **`HOLDOUT A5` y `TERMINAL` excluidos (`mascara_a5_limpia`).**",
        "",
        "## 1. Orden cross-seccional `DollarVol ETFs 3x / DollarVol Futuro` (`DESC+REP`)",
        "| Índice | `2010–2020 (%)` | `2021–2026 (%)` | Salto | Vol ETF 3x `2021+ (M USD/d)` | Resultado conocido de `T` |",
        "| :--- | :---: | :---: | :---: | :---: | :--- |",
    ]
    t_notes = {"NQ": "Fuerte desde 2021 (+0,13/+0,22 R)", "ES": "Positivo menor que NQ", "YM": "Positivo", "RTY": "Débil / nulo", "EMD": "Nulo (sin ETF 3x relevantes)"}
    for sym in ("NQ", "ES", "YM", "RTY", "EMD"):
        x = xs_rows[sym]
        md.append(f"| `{sym}` | `{x['ratio_2010_2020_pct']}%` | **`{x['ratio_2021_2026_pct']}%`** | `{x['salto_x']}x` | `{x['etf_dvol_2021_2026_musd']}` | {t_notes[sym]} |")

    md.extend([
        "",
        "## 2. Serie temporal y presión causal `t-1 → t` (`DESC+REP`)",
        "| Índice | `Spearman mens R vs ratio60` | `R/día pre-2021` | `R/día 2021+` | `R(presión alta) vs R(baja)` | `t_Welch` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ])
    for sym, d in ts_res.items():
        pr = d["presion_causal_alta_vs_baja"]
        md.append(
            f"| `{sym}` (`{d['meses_DR']}m`) | **`{d['spearman_mensual_R_vs_ratio60_lag']}`** | `{d['pre_2021']['R_dia_medio']}` | "
            f"`{d['post_2021']['R_dia_medio']}` | `{pr['R_alta']} vs {pr['R_baja']}` | **`{pr['t_welch']}`** |"
        )
    if "ops_side_vs_ret_lag" in ts_res["NQ"]:
        od = ts_res["NQ"]["ops_side_vs_ret_lag"]
        md.append(f"- **`NQ` ops (`FUNDEDSYNC_OPS`) lado `T` vs signo retorno previo `t-1`:** mismo signo `R={od['R_mismo_signo']}` (`n={od['n_mismo_signo']}`) vs opuesto `R={od['R_signo_opuesto']}` (`n={od['n_signo_opuesto']}`, `t={od['t_welch']}`).")

    md.extend([
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (`3` pruebas de mecanismo sin optimizar perillas).",
        "Episodios: comparado `2010–2020` vs `2021–2026-09` en `DESC+REP`.",
        "",
        "Aporte al referente: mide con datos reales `DESC+REP` si la huella temporal y cross-seccional del volumen en ETFs apalancados `3x` explica el patrón geográfico/temporal de `T`.",
    ])
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
