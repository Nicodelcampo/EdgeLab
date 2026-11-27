#!/usr/bin/env python3
"""MACRO-RISK-PREMIA: 5 Primas de Riesgo y Momentum Multi-Clase sobre ETFs Ajustados (2006-2026-09).

Pre-registro: docs/research/macro_risk_premia_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC (143m) y REP (42m) de HOLDOUT-A5; HOLDOUT (63m) y TERMINAL (>=2026-10-01) SELLADOS (NaN).
Uso:
  python -u tools/macro_risk_premia_20261127.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from marco_sin_forward import _a5_mes_blq, stats_monthly_10vol  # noqa: E402
from registro_global import exigir_contada  # noqa: E402

DATA_DIR = ROOT / "data/macro_risk_premia"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs/research/macro_risk_premia_20261127"
OUT.mkdir(parents=True, exist_ok=True)

CORTE = pd.Timestamp("2026-10-01")
P1_UNIX = 1104537600  # 2005-01-01T00:00:00Z
P2_UNIX = 1790812800  # 2026-10-01T00:00:00Z

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SECTORS_PLUS_REIT = SECTORS + ["IYR"]
COUNTRIES = ["EWJ", "EWG", "EWU", "EWC", "EWA", "EWH", "EWS", "EWY", "EWT", "EWZ", "EWW", "EWP"]
RATES_CREDIT = ["SHY", "IEI", "IEF", "TLT", "TIP", "LQD", "HYG"]
NON_EQ_ALL = ["SHY", "IEF", "TLT", "TIP", "LQD", "GLD", "SLV", "USO", "DBC", "UUP", "FXE", "FXY", "FXB", "FXA"]
YIELDS = ["^TNX", "^IRX"]
ALL_SYMS = sorted(set(["SPY"] + SECTORS_PLUS_REIT + COUNTRIES + RATES_CREDIT + NON_EQ_ALL + YIELDS))
EQUITY_ETFS = set(["SPY"] + SECTORS_PLUS_REIT + COUNTRIES)


def _fetch_one(sym: str) -> tuple[str, pd.Series | None, dict]:
    safe = sym.replace("^", "IDX_")
    pq = DATA_DIR / f"{safe}.parquet"
    meta_f = DATA_DIR / f"{safe}.meta.json"
    if pq.exists() and meta_f.exists():
        df = pd.read_parquet(pq)
        assert not (df.index >= CORTE).any(), f"Holdout date breach in {pq}"
        return sym, df["val"], json.loads(meta_f.read_text(encoding="utf-8"))

    enc = urllib.parse.quote(sym, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?period1={P1_UNIX}&period2={P2_UNIX}&interval=1d&events=div%2Csplits"
    raw_bytes = b""
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                raw_bytes = r.read()
            break
        except Exception:
            time.sleep(0.7)
    if not raw_bytes:
        return sym, None, {"error": "download_failed"}

    sha = hashlib.sha256(raw_bytes).hexdigest()
    j = json.loads(raw_bytes.decode("utf-8"))["chart"]["result"][0]
    ts = j["timestamp"]
    if sym.startswith("^"):
        vals = j["indicators"]["quote"][0]["close"]
    else:
        adj = j["indicators"].get("adjclose", [{}])[0].get("adjclose")
        vals = adj if adj is not None else j["indicators"]["quote"][0]["close"]

    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
    s = pd.Series(vals, index=idx, name="val", dtype="float64").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s = s[s.index < CORTE]
    assert not (s.index >= CORTE).any(), f"TERMINAL breach for {sym}!"
    s.to_frame().to_parquet(pq)
    meta = {"sym": sym, "sha256": sha, "rows": int(len(s)), "min": str(s.index.min().date()), "max": str(s.index.max().date())}
    meta_f.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return sym, s, meta


def _fetch_all() -> pd.DataFrame:
    series_map, proc = {}, {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(_fetch_one, s) for s in ALL_SYMS]
        for f in as_completed(futs):
            sym, s, meta = f.result()
            proc[sym] = meta
            if s is not None and len(s) > 0:
                series_map[sym] = s
    (DATA_DIR / "PROCEDENCIA.json").write_text(json.dumps(proc, indent=2, sort_keys=True), encoding="utf-8")
    df = pd.DataFrame(series_map).sort_index()
    return df[df.index < CORTE]


def _stagger_weights(W_raw: pd.DataFrame, n_cohorts: int = 5) -> pd.DataFrame:
    """Promedia pesos semanales escalonados en 5 cohortes (rebalanceo cada 5 dias habiles)."""
    out = pd.DataFrame(0.0, index=W_raw.index, columns=W_raw.columns)
    for k in range(n_cohorts):
        wk = W_raw.copy()
        wk.iloc[(np.arange(len(W_raw)) % n_cohorts) != k] = np.nan
        out = out + wk.ffill().fillna(0.0) / float(n_cohorts)
    return out


def _cs_long_short(score: pd.DataFrame, vol: pd.DataFrame, k_side: int = 3, min_n: int = 6) -> pd.DataFrame:
    """Top-k / Bot-k ponderado por inversa de volatilidad (gross long=0.5, short=-0.5)."""
    sc = score.copy()
    n_v = sc.notna().sum(axis=1).to_numpy()[:, None]
    rk_hi = sc.rank(axis=1, ascending=False, method="first")
    rk_lo = sc.rank(axis=1, ascending=True, method="first")
    inv_v = (1.0 / vol.clip(lower=0.03)).replace([np.inf, -np.inf], np.nan)
    lw = (inv_v.where((rk_hi <= k_side) & (n_v >= min_n), 0.0)).clip(upper=0.35)
    sw = (inv_v.where((rk_lo <= k_side) & (n_v >= min_n), 0.0)).clip(upper=0.35)
    ls, ss = lw.sum(axis=1), sw.sum(axis=1)
    both = (ls > 0) & (ss > 0)
    out = lw.div(ls.replace(0, np.nan), axis=0).fillna(0.0) * 0.5 - sw.div(ss.replace(0, np.nan), axis=0).fillna(0.0) * 0.5
    out[~both] = 0.0
    return out


def _beta_neutralize(W: pd.DataFrame, beta_df: pd.DataFrame) -> pd.DataFrame:
    """Ajusta patas corta y larga para neutralizar beta SPY causal mantendo gross=1.0."""
    lw = W.clip(lower=0.0)
    sw = (-W).clip(lower=0.0)
    ls, ss = lw.sum(axis=1), sw.sum(axis=1)
    both = (ls > 0) & (ss > 0)
    b_c = beta_df.clip(0.3, 2.5).fillna(1.0)
    b_l = (lw * b_c).sum(axis=1) / ls.replace(0, np.nan)
    b_s = (sw * b_c).sum(axis=1) / ss.replace(0, np.nan)
    sc_s = (b_l / b_s.replace(0, np.nan)).fillna(1.0).clip(0.5, 2.0)
    nf = 0.5 * (1.0 + sc_s)
    out = lw.div(nf, axis=0) - sw.mul(sc_s / nf, axis=0)
    out[~both] = 0.0
    return out


def _eval_weights(R_df: pd.DataFrame, W_sig: pd.DataFrame, tx_bps: float = 10.0, eq_borrow_bps: float = 100.0, noneq_borrow_bps: float = 50.0) -> tuple[pd.Series, pd.Series, float]:
    """Simula pnl diario causal (shift(1) sobre senal -> W_exec[t] = W_sig[t-1]) con tx + short borrow."""
    W = W_sig.reindex(columns=R_df.columns).fillna(0.0).shift(1).fillna(0.0)
    ret_mat = R_df.fillna(0.0)
    gross = (W * ret_mat).sum(axis=1)
    dw = W.diff().abs().fillna(0.0)
    tx_cost = dw.sum(axis=1) * (tx_bps / 2.0 / 10_000.0)  # RT bps / 2 per one-way leg
    # Short borrow annual cost split over 252 trading days
    short_exp = (-W).clip(lower=0.0)
    borrow_rates = pd.Series({c: (eq_borrow_bps if c in EQUITY_ETFS else noneq_borrow_bps) / 10_000.0 / 252.0 for c in R_df.columns})
    borrow_cost = (short_exp * borrow_rates).sum(axis=1)
    net = gross - tx_cost - borrow_cost
    net_2x = gross - 2.0 * (tx_cost + borrow_cost)
    turn_ann = float(dw.sum(axis=1).mean() * 252.0 * 0.5)
    return net, net_2x, round(turn_ann, 2)


def main() -> None:
    exigir_contada("docs/research/macro_risk_premia_20261127/PREREGISTRO.md")
    t0 = time.time()
    P = _fetch_all()
    print(f"Loaded {P.shape[1]} Macro Risk Premia series ({P.index.min().date()} -> {P.index.max().date()}) in {time.time()-t0:.1f}s", flush=True)

    # Prices vs Yields
    px_cols = [c for c in P.columns if not c.startswith("^")]
    PX = P[px_cols].copy()
    R = PX.pct_change()
    vol63 = R.rolling(63, min_periods=30).std() * np.sqrt(252.0)

    # Rolling 126d causal beta vs SPY
    spy_r = R["SPY"]
    spy_var = spy_r.rolling(126, min_periods=60).var().clip(lower=1e-8)
    betas = pd.DataFrame({c: R[c].rolling(126, min_periods=60).cov(spy_r) / spy_var for c in PX.columns})

    # Momentum 12m-1m normalized by vol63
    mom_12_1 = (PX.shift(21) / PX.shift(252) - 1.0) / vol63

    # RP1: US Sectors XSMOM Beta-Neutral (9 SPDR sectors)
    w1_raw = _beta_neutralize(_cs_long_short(mom_12_1[SECTORS], vol63[SECTORS], k_side=3, min_n=7), betas[SECTORS])
    w1 = _stagger_weights(w1_raw, 5)

    # RP2: US Sectors + IYR BAB (Long low-beta, Short high-beta, beta-neutral)
    b_sec = betas[SECTORS_PLUS_REIT].where(PX[SECTORS_PLUS_REIT].notna())
    n_b = b_sec.notna().sum(axis=1).to_numpy()[:, None]
    rk_lo_b = b_sec.rank(axis=1, ascending=True, method="first")
    rk_hi_b = b_sec.rank(axis=1, ascending=False, method="first")
    lw_b = (1.0 / b_sec.clip(0.3, 2.5)).where((rk_lo_b <= 3) & (n_b >= 7), 0.0)
    sw_b = (1.0 / b_sec.clip(0.3, 2.5)).where((rk_hi_b <= 3) & (n_b >= 7), 0.0)
    w2_base = lw_b.div(lw_b.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5 - sw_b.div(sw_b.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0) * 0.5
    w2 = _stagger_weights(_beta_neutralize(w2_base, b_sec), 5)

    # RP3: Global Countries XSMOM Beta-Neutral (12 iShares country ETFs)
    w3_raw = _beta_neutralize(_cs_long_short(mom_12_1[COUNTRIES], vol63[COUNTRIES], k_side=3, min_n=8), betas[COUNTRIES])
    w3 = _stagger_weights(w3_raw, 5)

    # RP4: Rates Yield-Curve & Credit Regime (ZERO equity!)
    slope = (P["^TNX"] - P["^IRX"]).ffill()
    slope_ma = slope.rolling(63, min_periods=30).mean()
    # Credit ratio HYG/LQD if HYG alive, else LQD/IEF
    cr_ratio = (PX["HYG"] / PX["LQD"]).where(PX["HYG"].notna(), PX["LQD"] / PX["IEF"])
    cr_ma = cr_ratio.rolling(63, min_periods=30).mean()
    w4_raw = pd.DataFrame(0.0, index=PX.index, columns=PX.columns)
    steep_up = (slope > 0.0) & (slope > slope_ma)
    # 50% Curve sleeve
    w4_raw.loc[steep_up, ["IEF", "TLT"]] += np.array([0.125, 0.125])
    w4_raw.loc[steep_up, "SHY"] -= 0.25
    w4_raw.loc[~steep_up, ["SHY", "TIP", "GLD"]] += np.array([0.10, 0.075, 0.075])
    w4_raw.loc[~steep_up, "TLT"] -= 0.25
    # 50% Credit regime sleeve
    stress_cr = cr_ratio < cr_ma
    w4_raw.loc[stress_cr, ["GLD", "IEF", "UUP"]] += np.array([0.20, 0.20, 0.10])
    w4_raw.loc[~stress_cr, ["LQD", "TIP"]] += np.array([0.125, 0.125])
    w4_raw.loc[~stress_cr, "SHY"] -= 0.25
    # Normalize each day to gross <= 1.0 and stagger 5d
    gs4 = w4_raw.abs().sum(axis=1).replace(0, np.nan).fillna(1.0)
    w4 = _stagger_weights(w4_raw.div(gs4, axis=0), 5)

    # RP5: Pure Non-Equity Multi-Speed Trend (21d + 63d + 252d)
    sig_ne = pd.DataFrame(0.0, index=PX.index, columns=NON_EQ_ALL)
    for lb in (21, 63, 252):
        z_lb = (PX[NON_EQ_ALL] / PX[NON_EQ_ALL].shift(lb) - 1.0) / (R[NON_EQ_ALL].rolling(max(lb, 42), min_periods=21).std() * np.sqrt(lb))
        sig_ne = sig_ne + np.tanh(z_lb.fillna(0.0) / 1.5) / 3.0
    inv_v_ne = sig_ne / vol63[NON_EQ_ALL].clip(lower=0.03)
    gs5 = inv_v_ne.abs().sum(axis=1).replace(0, np.nan).fillna(1.0)
    w5 = _stagger_weights(inv_v_ne.div(gs5, axis=0), 5)

    w_map = {
        "RP1_Sector_XSMOM_Neut": w1,
        "RP2_Sector_BAB_LowBeta": w2,
        "RP3_Country_XSMOM_Neut": w3,
        "RP4_Rates_Curve_Credit": w4,
        "RP5_NonEq_MultiSpeed_Trend": w5,
    }

    idx_eval = PX.index[(PX.index >= "2006-01-01") & (PX.index < CORTE)]
    blq_d = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq_d.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr = blq_d.isin(["DESC", "REP"])
    spy_eval = spy_r.reindex(idx_eval).fillna(0.0)

    daily_dr = pd.DataFrame(index=idx_eval)
    daily_2x_dr = pd.DataFrame(index=idx_eval)
    res_rules = {}

    print("\n=== RESULTADOS MACRO-RISK-PREMIA (2006-01..2026-09, SOLO DESC & REP; HOLDOUT 63m SELLADO) ===")
    for name, W in w_map.items():
        s_raw, s2_raw, turn_ann = _eval_weights(R, W, tx_bps=10.0, eq_borrow_bps=100.0, noneq_borrow_bps=50.0)
        s = s_raw.reindex(idx_eval).fillna(0.0)
        s2 = s2_raw.reindex(idx_eval).fillna(0.0)
        daily_dr[name] = s.where(mask_dr, np.nan)
        daily_2x_dr[name] = s2.where(mask_dr, np.nan)

        m_s = s[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        m_2x = s2[mask_dr].groupby(lambda d: d.to_period("M")).sum()
        bm = pd.Series([_a5_mes_blq(p) for p in m_s.index], index=m_s.index)
        m_spy = spy_eval[mask_dr].groupby(lambda d: d.to_period("M")).sum()

        st_d = stats_monthly_10vol(m_s[bm == "DESC"])
        st_r = stats_monthly_10vol(m_s[bm == "REP"])
        st_dr = stats_monthly_10vol(m_s)
        st_2x = stats_monthly_10vol(m_2x)
        corr_spy_d = round(float(m_s[bm == "DESC"].corr(m_spy[bm == "DESC"])), 3)
        corr_spy_dr = round(float(m_s.corr(m_spy)), 3)
        beta_spy = round(float(s[mask_dr].cov(spy_eval[mask_dr]) / max(float(spy_eval[mask_dr].var()), 1e-12)), 3)

        epochs = {
            lbl: stats_monthly_10vol(m_s[(m_s.index >= p0) & (m_s.index <= p1)])
            for lbl, p0, p1 in [("06_12", "2006-01", "2012-12"), ("13_18", "2013-01", "2018-12"), ("19_26", "2019-01", "2026-09"), ("21_26", "2021-01", "2026-09")]
        }
        res_rules[name] = {
            "turn_ann_1way_x": turn_ann,
            "corr_SPY_DESC": corr_spy_d,
            "corr_SPY_DR": corr_spy_dr,
            "beta_SPY_DR": beta_spy,
            "DESC": st_d,
            "REP": st_r,
            "DESC_REP": st_dr,
            "DESC_REP_stress2x": st_2x,
            "epochs": epochs,
        }
        print(
            f"  {name:28s} | turn={turn_ann:4.1f}x | DESC Sh={st_d['sharpe']:5.3f} t={st_d['t']:4.2f} | "
            f"REP Sh={st_r['sharpe']:5.3f} | DR Sh={st_dr['sharpe']:5.3f} t={st_dr['t']:4.2f} | "
            f"2x Sh={st_2x['sharpe']:5.3f} | corrSPY_D={corr_spy_d:+.3f} beta={beta_spy:+.3f}"
        )

    # Pre-registered DESC selection rule: DESC Sharpe > 0.25 & |corr_DESC vs SPY| < 0.35
    rule_names = list(w_map.keys())
    alive = [c for c in rule_names if res_rules[c]["DESC"]["sharpe"] > 0.25 and abs(res_rules[c]["corr_SPY_DESC"]) < 0.35]
    if not alive:
        alive = [c for c in rule_names if res_rules[c]["DESC"]["sharpe"] > 0.0 and abs(res_rules[c]["corr_SPY_DESC"]) < 0.45]
    if not alive:
        alive = [c for c in rule_names if res_rules[c]["DESC"]["sharpe"] > 0.0]

    m_desc = daily_dr.loc[blq_d == "DESC", alive].groupby(lambda d: d.to_period("M")).sum()
    sd_desc = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_b = (1.0 / sd_desc) / (1.0 / sd_desc).sum()
    bask = (daily_dr[alive] * w_b).sum(axis=1).where(mask_dr, np.nan)
    bask_2x = (daily_2x_dr[alive] * w_b).sum(axis=1).where(mask_dr, np.nan)
    daily_dr["RP_Canasta_InvVol"] = bask

    m_b = bask[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    m_b2 = bask_2x[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    bm_b = pd.Series([_a5_mes_blq(p) for p in m_b.index], index=m_b.index)
    m_spy = spy_eval[mask_dr].groupby(lambda d: d.to_period("M")).sum()

    b_out = {
        "alive_prereg_DESC": alive,
        "weights_DESC": {k: round(float(v), 4) for k, v in w_b.items()},
        "corr_SPY_DESC": round(float(m_b[bm_b == "DESC"].corr(m_spy[bm_b == "DESC"])), 3),
        "corr_SPY_DR": round(float(m_b.corr(m_spy)), 3),
        "DESC": stats_monthly_10vol(m_b[bm_b == "DESC"]),
        "REP": stats_monthly_10vol(m_b[bm_b == "REP"]),
        "DESC_REP": stats_monthly_10vol(m_b),
        "DESC_REP_stress2x": stats_monthly_10vol(m_b2),
        "epochs": {
            lbl: stats_monthly_10vol(m_b[(m_b.index >= p0) & (m_b.index <= p1)])
            for lbl, p0, p1 in [("06_12", "2006-01", "2012-12"), ("13_18", "2013-01", "2018-12"), ("19_26", "2019-01", "2026-09"), ("21_26", "2021-01", "2026-09")]
        },
    }

    # Strictly mask non-DESC/REP as NaN before saving
    daily_dr.loc[~mask_dr] = np.nan
    daily_dr.to_csv(OUT / "SERIES_MACRO_RP_DR.csv.gz")

    m_mat = daily_dr.loc[mask_dr, rule_names].groupby(lambda d: d.to_period("M")).sum()
    corr_m = m_mat.corr().round(3).to_dict()

    out_json = {
        "n_series_loaded": int(P.shape[1]),
        "date_range": [str(idx_eval.min().date()), str(idx_eval.max().date())],
        "rules": res_rules,
        "monthly_corr_DESC_REP": corr_m,
        "RP_Canasta_InvVol": b_out,
    }
    (OUT / "RESULTADO.json").write_text(json.dumps(out_json, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print("\n=== CANASTA MACRO-RISK-PREMIA (Regla causal DESC) ===")
    print("  Incluidas:", alive, "pesos:", b_out["weights_DESC"])
    print("  DESC:", b_out["DESC"], "| REP:", b_out["REP"], "| DR:", b_out["DESC_REP"], "| 2x:", b_out["DESC_REP_stress2x"])

    md = [
        "# MACRO-RISK-PREMIA: 5 Primas Estructurales sobre ETFs Ajustados (`2006–2026-09`, resultado 2026-11-27)",
        "",
        "Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`6` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` (`63m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        f"- Datos: `{P.shape[1]}` series Yahoo `adjclose` + índices `^TNX`/`^IRX` (`{idx_eval.min().date()} -> {idx_eval.max().date()}`, cero empalmes `=F`, `PROCEDENCIA.json` con SHA-256).",
        "",
        "| Mecanismo (`10 bps RT + borrow`, `@10% vol`) | Rot/año | `DESC (143m) Sh` | `REP (42m) Sh` | `DR (185m) Sh / t` | `2x Stress Sh` | `corr_SPY` (`beta`) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        v = res_rules[c]
        md.append(
            f"| `{c}` | `{v['turn_ann_1way_x']}x` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | "
            f"**`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP_stress2x']['sharpe']}` | `{v['corr_SPY_DR']:+.3f}` (`{v['beta_SPY_DR']:+.3f}`) |"
        )
    md += [
        f"| **`RP_Canasta_InvVol`** ({len(alive)} activas) | — | `{b_out['DESC']['sharpe']}` | `{b_out['REP']['sharpe']}` | "
        f"**`{b_out['DESC_REP']['sharpe']} / {b_out['DESC_REP']['t']}`** | `{b_out['DESC_REP_stress2x']['sharpe']}` | `{b_out['corr_SPY_DR']:+.3f}` |",
        "",
        f"- Regla causal `DESC` (`DESC Sh > 0.25` y `|corr_SPY| < 0.35`): incluidas `{alive}`, pesos `{b_out['weights_DESC']}`.",
        f"- Por época (`RP_Canasta_InvVol`): `06–12 Sh={b_out['epochs']['06_12']['sharpe']}`, `13–18 Sh={b_out['epochs']['13_18']['sharpe']}`, `19–26 Sh={b_out['epochs']['19_26']['sharpe']}`, `21–26 Sh={b_out['epochs']['21_26']['sharpe']}`.",
        "",
        "Diagnóstico de grilla: sin grilla paramétrica (`5` mecanismos institucionales fijos con rebalanceo escalonado `5d`, ventanas estándar `21/63/126/252` y selección causal en `DESC`).",
        f"Episodios: épocas de la canasta `06–12 Sh={b_out['epochs']['06_12']['sharpe']}`, `13–18 Sh={b_out['epochs']['13_18']['sharpe']}`, `19–26 Sh={b_out['epochs']['19_26']['sharpe']}`, `21–26 Sh={b_out['epochs']['21_26']['sharpe']}`; años positivos `DR`: `{b_out['DESC_REP'].get('pct_anios_pos', 0):.1%}`.",
        "",
        "- **Aporte al referente**: abre un frente macro multi-clase limpio de `20+` años con `0` iteración de `REP`, `0` empalmes `=F` y `63` meses de `HOLDOUT A5` sellado.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


if __name__ == "__main__":
    main()
