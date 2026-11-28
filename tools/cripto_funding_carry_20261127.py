#!/usr/bin/env python3
"""CRIPTO-FUNDING-CARRY-PIT: Carry de funding 8h, choques y crowding en 226 perpetuos PIT (2021-2026-09).

Pre-registro: docs/research/cripto_funding_carry_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC (39m) y REP (12m); HOLDOUT A5 (18m) y >=2026-10-01 SELLADOS (NaN).
Uso:
  python -u tools/cripto_funding_carry_20261127.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque  # noqa: E402
from cripto_pit_v2 import (  # noqa: E402
    CORTE,
    CORTE_TS,
    TRADFI_EXCLUDE,
    _normalize_active_neutral,
    _pnl,
    _safe_close_returns,
    _stagger_weights,
    build_eligibility,
    fetch_all_pit_fast,
    stats_serie,
)
from registro_global import exigir_contada  # noqa: E402

OUT = ROOT / "docs/research/cripto_funding_carry_20261127"
OUT.mkdir(parents=True, exist_ok=True)


def _rank_top_bot(sc: pd.DataFrame, E: pd.DataFrame, k_leg: int = 4) -> pd.DataFrame:
    sc_e = sc.where(E)
    n_v = sc_e.notna().sum(axis=1).to_numpy()[:, None]
    rk_hi = sc_e.rank(axis=1, ascending=False, method="first")
    rk_lo = sc_e.rank(axis=1, ascending=True, method="first")
    raw = pd.DataFrame(0.0, index=sc.index, columns=sc.columns)
    raw = raw.where(~((rk_hi <= k_leg) & (n_v >= 10)), 1.0)
    raw = raw.where(~((rk_lo <= k_leg) & (n_v >= 10)), -1.0)
    return raw


def _beta_neut_norm(raw: pd.DataFrame, vol_inv: pd.DataFrame, beta_btc: pd.DataFrame, max_w: float = 0.18) -> pd.DataFrame:
    lw = (raw.clip(lower=0.0) * vol_inv).clip(upper=max_w)
    sw = ((-raw).clip(lower=0.0) * vol_inv).clip(upper=max_w)
    ls, ss = lw.sum(axis=1), sw.sum(axis=1)
    both = (ls > 0) & (ss > 0)
    b_c = beta_btc.clip(0.3, 2.5).fillna(1.0)
    b_l = (lw * b_c).sum(axis=1) / ls.replace(0, np.nan)
    b_s = (sw * b_c).sum(axis=1) / ss.replace(0, np.nan)
    sc_s = (b_l / b_s.replace(0, np.nan)).fillna(1.0).clip(0.5, 2.0)
    nf = 0.5 * (1.0 + sc_s)
    out = lw.div(ls.replace(0, np.nan) * nf, axis=0).fillna(0.0) - sw.div(ss.replace(0, np.nan), axis=0).fillna(0.0).mul(sc_s / nf, axis=0)
    out[~both] = 0.0
    return out


def compute_cfc_daily() -> dict:
    """Calcula las 3 estrategias diarias causales de funding carry/shock/crowding en < 2026-10-01."""
    u = pd.read_csv(ROOT / "docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv")
    u = u[~u["simbolo"].isin(TRADFI_EXCLUDE)].copy()
    bars = fetch_all_pit_fast(u)

    idx = pd.date_range("2020-05-01", "2026-09-30", freq="D", tz="UTC")
    assert idx.max() < CORTE_TS
    cols = sorted(bars.keys())
    C = pd.DataFrame({s: bars[s]["close"].reindex(idx) for s in cols}, index=idx)
    F = pd.DataFrame({s: bars[s]["funding"].reindex(idx) for s in cols}, index=idx).fillna(0.0)

    r_1d = _safe_close_returns(C)
    vol60 = r_1d.rolling(60, min_periods=20).std() * np.sqrt(365.0)
    E = build_eligibility(idx, C.columns, u, top_k=25, hysteresis_exit=25) & C.notna() & (vol60 >= 0.25)
    vol_inv = (1.0 / vol60.clip(lower=0.20)).replace([np.inf, -np.inf], np.nan)

    btc_r = r_1d["BTCUSDT"].fillna(0.0)
    btc_var = btc_r.rolling(60, min_periods=25).var().clip(lower=1e-8)
    beta_btc = pd.DataFrame({c: r_1d[c].rolling(60, min_periods=25).cov(btc_r) / btc_var for c in cols}, index=idx)

    # M1: Pure Funding Carry 14d (short high positive funding, long negative/low funding, beta-neutral to BTC)
    f14 = F.rolling(14, min_periods=7).sum().shift(1)
    w1 = _stagger_weights(_beta_neut_norm(_rank_top_bot(-f14, E, 4), vol_inv, beta_btc), E, 5)

    # M2: Funding Shock Reversal (5d - 30d) / std(30d)
    f_shk = ((F.rolling(5, min_periods=3).mean() - F.rolling(30, min_periods=15).mean())
             / F.rolling(30, min_periods=15).std().replace(0.0, np.nan)).shift(1)
    w2 = _stagger_weights(_normalize_active_neutral(_rank_top_bot(-f_shk, E, 4), vol_inv), E, 5)

    # M3: Carry-Filtered XSMOM 21d: z_cs(ret_21d) - 0.5 * z_cs(funding_14d)
    ret21 = (C / C.shift(21) - 1.0).where(E)
    z_ret = ret21.sub(ret21.mean(axis=1), axis=0).div(ret21.std(axis=1).replace(0.0, np.nan), axis=0)
    f14_raw = F.rolling(14, min_periods=7).sum().where(E)
    z_f = f14_raw.sub(f14_raw.mean(axis=1), axis=0).div(f14_raw.std(axis=1).replace(0.0, np.nan), axis=0)
    sc3 = (z_ret - 0.5 * z_f.fillna(0.0)).shift(1)
    w3 = _stagger_weights(_normalize_active_neutral(_rank_top_bot(sc3, E, 4), vol_inv), E, 5)

    w_map = {
        "CFC1_FundingCarry_14d_Stag5d": w1,
        "CFC2_FundingShock_Rev_Stag5d": w2,
        "CFC3_CarryFilt_XSMOM_Stag5d": w3,
    }

    idx_eval = idx[idx >= pd.Timestamp("2021-01-01", tz="UTC")]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"

    daily_by_bps = {}
    meta_20 = {}
    for bps in (10, 20, 30, 40):
        cost_rt = bps / 10_000.0
        df_b = pd.DataFrame(index=idx_eval)
        for name, W in w_map.items():
            pnl, pnl_st, turn_m, dh = _pnl(C, W, F, cost_rt=cost_rt, r_override=r_1d)
            df_b[name] = pnl.reindex(idx_eval).fillna(0.0)
            if bps == 20:
                meta_20[name] = {"turn_m": turn_m, "delist_hits": dh, "stress_sh": stats_serie(pnl_st.reindex(idx_eval)[blq.isin(["DESC", "REP"])])["sharpe"]}
        daily_by_bps[bps] = df_b

    return {
        "n_coins": int(len(cols)),
        "idx_eval": idx_eval,
        "blq": blq,
        "daily_by_bps": daily_by_bps,
        "meta_20": meta_20,
        "btc_r": btc_r.reindex(idx_eval).fillna(0.0),
    }


def main() -> None:
    exigir_contada("docs/research/cripto_funding_carry_20261127/PREREGISTRO.md")
    t0 = time.time()
    core = compute_cfc_daily()
    idx_eval, blq, daily_by_bps = core["idx_eval"], core["blq"], core["daily_by_bps"]
    mask_dr = blq.isin(["DESC", "REP"])
    print(f"Loaded {core['n_coins']} PIT coins for Funding Carry in {time.time()-t0:.1f}s", flush=True)

    # Compare against existing DESC+REP series (ZERO HOLDOUT READ!)
    ho_m = pd.read_csv(ROOT / "docs/research/holdout_a5_nocme_20261127/SERIES_HOLDOUT_A5_NOCME_MENSUAL.csv.gz", index_col=0)
    ho_dr = ho_m[ho_m["bloque"].isin(["DESC", "REP"])].copy()
    ho_dr.index = pd.PeriodIndex(ho_dr.index, freq="M")

    res = {"n_coins": core["n_coins"], "por_costo": {}, "rules_20bps": {}}
    D20 = daily_by_bps[20]
    rule_names = list(D20.columns)
    for c in rule_names:
        s_dr = D20.loc[mask_dr, c]
        s_d = D20.loc[blq == "DESC", c]
        s_r = D20.loc[blq == "REP", c]
        top5 = float(s_d.sort_values(ascending=False).head(5).sum() / max(float(s_d.sum()), 1e-6)) if s_d.sum() > 0 else 1.0
        m_dr = s_dr.groupby(s_dr.index.tz_localize(None).to_period("M")).sum()
        res["rules_20bps"][c] = {
            **core["meta_20"][c],
            "top5_days_share_DESC": round(top5, 3),
            "DESC": stats_serie(s_d),
            "REP": stats_serie(s_r),
            "DESC_REP": stats_serie(s_dr),
            "beta_btc_DR": round(float(s_dr.cov(core["btc_r"][mask_dr]) / max(float(core["btc_r"][mask_dr].var()), 1e-12)), 4),
            "corr_CR3_DR": round(float(m_dr.corr(ho_dr["Cripto_v3_Canasta"].dropna())), 3),
            "corr_OFI_DR": round(float(m_dr.corr(ho_dr["Cripto_OFI_Canasta"].dropna())), 3),
        }
        print(
            f"  {c:30s} | turn={core['meta_20'][c]['turn_m']:4.2f}x/m | DESC Sh={res['rules_20bps'][c]['DESC']['sharpe']:5.2f} | "
            f"REP Sh={res['rules_20bps'][c]['REP']['sharpe']:5.2f} | DR Sh={res['rules_20bps'][c]['DESC_REP']['sharpe']:5.2f} (t={res['rules_20bps'][c]['DESC_REP']['t_mes']:4.2f}) | "
            f"corr_CR3={res['rules_20bps'][c]['corr_CR3_DR']:+.3f} corr_OFI={res['rules_20bps'][c]['corr_OFI_DR']:+.3f}"
        )

    alive = [c for c in rule_names if res["rules_20bps"][c]["DESC"]["usd_mes"] > 0 and res["rules_20bps"][c]["top5_days_share_DESC"] < 0.65]
    if not alive:
        alive = [c for c in rule_names if res["rules_20bps"][c]["DESC"]["usd_mes"] > 0]
    out_series = D20.copy()
    if alive:
        m_desc = D20.loc[blq == "DESC", alive].groupby(D20.loc[blq == "DESC"].index.tz_localize(None).to_period("M")).sum()
        sd_d = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
        w_c = (1.0 / sd_d) / (1.0 / sd_d).sum()
        for bps in (10, 20, 30, 40):
            cana = sum(daily_by_bps[bps][c] * float(w_c[c]) for c in alive)
            res["por_costo"][bps] = {
                "DESC": stats_serie(cana[blq == "DESC"]),
                "REP": stats_serie(cana[blq == "REP"]),
                "DESC_REP": stats_serie(cana[mask_dr]),
            }
        cana20 = sum(D20[c] * float(w_c[c]) for c in alive)
        m_c20 = cana20[mask_dr].groupby(cana20[mask_dr].index.tz_localize(None).to_period("M")).sum()
        res["CFC_Canasta_InvVol"] = {
            "alive_DESC": alive,
            "weights_DESC": {k: round(float(v), 4) for k, v in w_c.items()},
            "corr_CR3_DR": round(float(m_c20.corr(ho_dr["Cripto_v3_Canasta"].dropna())), 3),
            "corr_OFI_DR": round(float(m_c20.corr(ho_dr["Cripto_OFI_Canasta"].dropna())), 3),
            "corr_Carril2_DR": round(float(m_c20.corr(ho_dr["Carril2_Sell16"].dropna())), 3),
            **res["por_costo"][20],
        }
        out_series["CFC_Canasta_InvVol"] = cana20
        print("  CANASTA CFC:", res["CFC_Canasta_InvVol"]["DESC_REP"], "weights:", res["CFC_Canasta_InvVol"]["weights_DESC"])
    else:
        res["CFC_Canasta_InvVol"] = {"alive_DESC": [], "veredicto_DR": "SIN_CANDIDATAS"}

    out_series["bloque"] = blq
    out_series.where(mask_dr, np.nan).to_csv(OUT / "SERIES_DESC_REP.csv.gz")
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    md = [
        "# CRIPTO-FUNDING-CARRY-PIT: Carry de Funding y Crowding en 226 Perpetuos PIT (`2021–2026-09`, resultado 2026-11-27)",
        "",
        "Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas, `CRIPTO_FUNDING_CARRY_PIT`). **`HOLDOUT A5` (`18m`) y `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "| Serie (20 bps RT + funding real) | Rot/mes | `DESC (39m) Sh` | `REP (12m) Sh` | `DR (51m) Sh / t` | `corr CR3` | `corr OFI` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        v = res["rules_20bps"][c]
        md.append(f"| `{c}` | `{v['turn_m']}x` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t_mes']}`** | `{v['corr_CR3_DR']:+.3f}` | `{v['corr_OFI_DR']:+.3f}` |")
    if alive:
        cv = res["CFC_Canasta_InvVol"]
        md.append(f"| **`CFC_Canasta_InvVol`** ({len(alive)} patas) | — | `{cv['DESC']['sharpe']}` | `{cv['REP']['sharpe']}` | **`{cv['DESC_REP']['sharpe']} / {cv['DESC_REP']['t_mes']}`** | `{cv['corr_CR3_DR']:+.3f}` | `{cv['corr_OFI_DR']:+.3f}` |")
        md.append("")
        md.append(f"- Costos 10/20/30/40 bps (`DR Sh`): `{res['por_costo'][10]['DESC_REP']['sharpe']}` / `{res['por_costo'][20]['DESC_REP']['sharpe']}` / `{res['por_costo'][30]['DESC_REP']['sharpe']}` / `{res['por_costo'][40]['DESC_REP']['sharpe']}`.")
    md += [
        "",
        "Diagnóstico de grilla: cero grilla paramétrica (`3` reglas causales escalonadas `5d` con `shift(1)`).",
        "Episodios: detallado por bloques `DESC` (39m) y `REP` (12m) en `RESULTADO.json`; `HOLDOUT A5` permanece intacto.",
        "",
        "Aporte al referente: mide si el diferencial de funding 8h y el momentum filtrado por crowding aportan un segundo/tercer pilar cripto limpio y descorrelacionado de `XSMOM` y `OFI`.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
