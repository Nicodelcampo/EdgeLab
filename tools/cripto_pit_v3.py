#!/usr/bin/env python3
"""CRIPTO-PIT v3 (Pre-registrado): Microestructura Basis (premiumIndexKlines) + Beta-Neutralizacion + 5 Mecanismos Escalonados.

Pre-registro: docs/research/cripto_pit_v3_20261127/PREREGISTRO.md (K51 exigido antes de correr).
Evalua ESTRICTAMENTE sobre A5 DESC (39m) y REP (12m), manteniendo HOLDOUT A5 (18m) y TERMINAL (>=2026-10-01) SELLADOS (NaN).
Uso:
  python -u tools/cripto_pit_v3.py
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List

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
    VIS,
    _get,
    _normalize_active_neutral,
    _pnl,
    _safe_close_returns,
    _stagger_weights,
    _sym_months_from_pit,
    build_eligibility,
    fetch_all_pit_fast,
    stats_serie,
)

BASIS_DIR = ROOT / "data" / "crypto_binance_pit_basis_1d"
BASIS_DIR.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs" / "research" / "cripto_pit_v3_20261127"
OUT.mkdir(parents=True, exist_ok=True)


def _dl_one_premium(args: tuple[str, str]) -> tuple[str, pd.DataFrame | None]:
    sym, ym = args
    from urllib.parse import quote
    b = _get(quote(f"{VIS}/data/futures/um/monthly/premiumIndexKlines/{sym}/1d/{sym}-1d-{ym}.zip", safe=":/"), timeout=12)
    if b is None:
        return sym, None
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
        raw = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(raw.iloc[0, 0]).isdigit():
            raw = raw.iloc[1:]
        raw = raw.iloc[:, :5].astype(float)
        raw.columns = ["t", "open", "high", "low", "close"]
        return sym, raw
    except Exception:
        return sym, None


def fetch_all_basis_fast(u: pd.DataFrame, syms_allowed: set[str]) -> Dict[str, pd.DataFrame]:
    sym_months = {s: ms for s, ms in _sym_months_from_pit(u).items() if s in syms_allowed}
    basis: Dict[str, pd.DataFrame] = {}
    todo = []
    for sym, ms in sym_months.items():
        pq = BASIS_DIR / f"{sym}_basis_1d.parquet"
        if pq.exists():
            df = pd.read_parquet(pq)
            if len(df) and df.index.max() < CORTE_TS:
                basis[sym] = df
            continue
        for ym in ms:
            todo.append((sym, ym))

    if todo:
        print(f"  Descargando {len(todo)} archivos mensuales premiumIndexKlines/1d (32 hilos)...", flush=True)
        acc: Dict[str, list] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            for sym, part in ex.map(_dl_one_premium, todo):
                if part is not None:
                    acc.setdefault(sym, []).append(part)
        for sym in sym_months:
            if sym in basis:
                continue
            pq = BASIS_DIR / f"{sym}_basis_1d.parquet"
            parts = acc.get(sym, [])
            if not parts:
                pd.DataFrame().to_parquet(pq)
                continue
            k = pd.concat(parts, ignore_index=True).drop_duplicates("t").sort_values("t")
            k["dt"] = pd.to_datetime(k["t"].astype("int64"), unit="ms", utc=True).dt.normalize()
            k = k[k["dt"] < CORTE_TS].drop_duplicates("dt").set_index("dt")[["open", "high", "low", "close"]]
            assert not (k.index >= CORTE_TS).any(), f"Holdout breach in basis {sym}!"
            k.to_parquet(pq)
            if len(k):
                basis[sym] = k
    return basis


def _beta_scale_legs(raw_pos: pd.DataFrame, vol_inv: pd.DataFrame, beta_btc: pd.DataFrame, max_w: float = 0.20) -> pd.DataFrame:
    """Patas activas escaladas por inversa de volatilidad y ajustadas por beta causal vs BTC (gross=1.0)."""
    lw = (raw_pos.clip(lower=0.0) * vol_inv).clip(upper=max_w)
    sw = ((-raw_pos).clip(lower=0.0) * vol_inv).clip(upper=max_w)
    lsum = lw.sum(axis=1)
    ssum = sw.sum(axis=1)
    both = (lsum > 0) & (ssum > 0)
    lw_u = lw.div(lsum.replace(0, np.nan), axis=0).fillna(0.0) * 0.5
    sw_u = sw.div(ssum.replace(0, np.nan), axis=0).fillna(0.0) * 0.5
    b_long = (lw_u * beta_btc.clip(0.3, 2.5)).sum(axis=1) * 2.0
    b_short = (sw_u * beta_btc.clip(0.3, 2.5)).sum(axis=1) * 2.0
    scale_s = (b_long / b_short.replace(0, np.nan)).fillna(1.0).clip(0.6, 1.5)
    # Match portfolio betas within [0.6, 1.5] while preserving exact total gross = 1.0
    norm_f = 0.5 * (1.0 + scale_s)
    out = lw_u.div(norm_f, axis=0) - sw_u.mul(scale_s / norm_f, axis=0)
    out[~both] = 0.0
    return out


def _residual_2f(r1d: pd.DataFrame, f1: pd.Series, f2: pd.Series, win: int = 30) -> pd.DataFrame:
    """Residuo diario causal OLS rolling contra 2 factores (BTC + ETH), shift(1) para evitar look-ahead."""
    f1a = f1.fillna(0.0).to_numpy(float)
    f2a = f2.fillna(0.0).to_numpy(float)
    n_t = len(r1d)
    resid = pd.DataFrame(np.nan, index=r1d.index, columns=r1d.columns)
    X_full = np.column_stack([np.ones(n_t), np.nan_to_num(f1a, nan=0.0), np.nan_to_num(f2a, nan=0.0)])
    # Precompute rolling X'X^-1 X' for fast causal 2-factor betas
    eye3 = np.eye(3) * 1e-6
    for s in r1d.columns:
        y = r1d[s].to_numpy(float)
        b_prev = np.array([0.0, 1.0, 0.0])
        out_r = np.full(n_t, np.nan)
        for t in range(win, n_t):
            yw = y[t - win : t]
            ok = np.isfinite(yw)
            if ok.sum() >= 15:
                Xw = X_full[t - win : t][ok]
                try:
                    coef = np.linalg.solve(Xw.T @ Xw + eye3, Xw.T @ yw[ok])
                    b_prev = np.array([coef[0], float(np.clip(coef[1], -2.0, 4.0)), float(np.clip(coef[2], -2.0, 4.0))])
                except np.linalg.LinAlgError:
                    pass
            if np.isfinite(y[t]):
                out_r[t] = y[t] - (b_prev[1] * f1a[t] + b_prev[2] * f2a[t])
        resid[s] = out_r
    return resid


def compute_cripto_v3_daily(universo_csv: Path | None = None, desde: str = "2021-01-01", hasta: str = CORTE) -> dict:
    """Calcula las 5 series diarias de CRIPTO-PIT v3 a 10/20/30/40 bps + funding en < 2026-10-01. Por defecto, igual que la corrida
    pre-registrada; `universo_csv`, `desde` y `hasta` sólo los cambia cripto_v3_2019.py (período 2019-10 → 2020-12)."""
    u = pd.read_csv(universo_csv or ROOT / "docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv")
    ascii_syms = {s for s in u["simbolo"].unique() if str(s).isascii() and s not in TRADFI_EXCLUDE}
    bars = {s: df for s, df in fetch_all_pit_fast(u).items() if s in ascii_syms}
    basis_map = fetch_all_basis_fast(u, set(bars.keys()))

    C = pd.DataFrame({s: df["close"] for s, df in bars.items()}).sort_index()
    H = pd.DataFrame({s: df["high"] for s, df in bars.items()}).reindex(C.index)
    L = pd.DataFrame({s: df["low"] for s, df in bars.items()}).reindex(C.index)
    F = pd.DataFrame({s: df["funding"] for s, df in bars.items()}).reindex(C.index).fillna(0.0)
    B = pd.DataFrame({s: df["close"] for s, df in basis_map.items()}).reindex(C.index)
    for df in (C, H, L, F, B):
        df.index = df.index.tz_localize(None)
    C = C[C.index < CORTE]
    H, L, F, B = H.reindex(C.index), L.reindex(C.index), F.reindex(C.index), B.reindex(C.index)

    r_safe = _safe_close_returns(C, max_gap=5)
    tr = np.maximum(H - L, np.maximum((H - C.shift(1)).abs(), (L - C.shift(1)).abs()))
    vol1 = (tr.rolling(20, min_periods=10).mean() / C).clip(lower=0.01)
    inv_vol = (0.01 / vol1).clip(upper=0.25)

    vol60 = r_safe.rolling(60, min_periods=30).std() * np.sqrt(365.0)
    vol30 = r_safe.rolling(30, min_periods=15).std() * np.sqrt(365.0)
    live60 = (C.notna().rolling(60, min_periods=60).sum() >= 60) & (vol60 >= 0.25)
    E_hyst = build_eligibility(C.index, C.columns, u, top_k=20, hysteresis_exit=25) & live60

    btc = r_safe["BTCUSDT"].fillna(0.0) if "BTCUSDT" in r_safe else r_safe.mean(axis=1)
    eth = r_safe["ETHUSDT"].fillna(0.0) if "ETHUSDT" in r_safe else btc
    btc_var = btc.rolling(30, min_periods=15).var().replace(0.0, np.nan)
    beta_btc_df = pd.DataFrame(1.0, index=C.index, columns=C.columns)
    for s in C.columns:
        cov_b = r_safe[s].rolling(30, min_periods=15).cov(btc)
        beta_btc_df[s] = (cov_b / btc_var).shift(1).fillna(1.0)

    ret_21 = C.pct_change(21, fill_method=None)

    sc21 = (ret_21 / vol1).where(E_hyst)
    rk21 = sc21.rank(axis=1, ascending=False, method="first")
    n21 = sc21.notna().sum(axis=1).to_numpy()[:, None]
    p1 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p1[(rk21 <= 4) & (n21 >= 10)] = 1.0
    p1[(rk21 >= n21 - 3) & (n21 >= 10)] = -1.0
    w1 = _stagger_weights(_normalize_active_neutral(p1, inv_vol, max_w=0.20), E_hyst, 5)
    w2 = _stagger_weights(_beta_scale_legs(p1, inv_vol, beta_btc_df, max_w=0.20), E_hyst, 5)

    b5 = B.rolling(5, min_periods=2).mean().where(E_hyst)
    f5 = F.rolling(5, min_periods=2).mean().where(E_hyst)
    zb = b5.sub(b5.mean(axis=1), axis=0).div(b5.std(axis=1, ddof=1).replace(0.0, np.nan), axis=0).clip(-3.0, 3.0).fillna(0.0)
    zf = f5.sub(f5.mean(axis=1), axis=0).div(f5.std(axis=1, ddof=1).replace(0.0, np.nan), axis=0).clip(-3.0, 3.0).fillna(0.0)
    carry_sc = (zb + zf).where(E_hyst & (b5.notna() | f5.notna()))
    rkc = carry_sc.rank(axis=1, ascending=False, method="first")
    nc = carry_sc.notna().sum(axis=1).to_numpy()[:, None]
    squeeze = C > H.shift(1).rolling(10).max()
    p3 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p3[(rkc <= 4) & (~squeeze) & (nc >= 10)] = -1.0
    p3[(rkc >= nc - 3) & (nc >= 10)] = 1.0
    w3 = _stagger_weights(_normalize_active_neutral(p3, inv_vol, max_w=0.20), E_hyst, 5)

    v_sc = vol30.where(E_hyst)
    rkv = v_sc.rank(axis=1, ascending=True, method="first")
    nv = v_sc.notna().sum(axis=1).to_numpy()[:, None]
    p4 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p4[(rkv <= 4) & (nv >= 10)] = 1.0
    p4[(rkv >= nv - 3) & (nv >= 10)] = -1.0
    w4 = _stagger_weights(_beta_scale_legs(p4, inv_vol, beta_btc_df, max_w=0.20), E_hyst, 5)

    resid_2f = _residual_2f(r_safe, btc, eth, win=30)
    res21 = (resid_2f.rolling(21, min_periods=12).sum() / vol1).where(E_hyst)
    rkr = res21.rank(axis=1, ascending=False, method="first")
    nr = res21.notna().sum(axis=1).to_numpy()[:, None]
    p5 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p5[(rkr <= 4) & (nr >= 10)] = 1.0
    p5[(rkr >= nr - 3) & (nr >= 10)] = -1.0
    w5 = _stagger_weights(_normalize_active_neutral(p5, inv_vol, max_w=0.20), E_hyst, 5)

    w_map = {
        "CR3_XSMOM_21d_Stag5d": w1,
        "CR3_XSMOM_BetaNeut_Stag5d": w2,
        "CR3_Basis_Carry_Stag5d": w3,
        "CR3_BAB_LowVol_Stag5d": w4,
        "CR3_ResidMom_21d_2F_Stag5d": w5,
    }

    idx_eval = C.index[(C.index >= desde) & (C.index < hasta)]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    btc_eval = btc.reindex(idx_eval).fillna(0.0)

    daily_by_bps = {bps: pd.DataFrame(index=idx_eval) for bps in (10, 20, 30, 40)}
    shock30 = pd.DataFrame(index=idx_eval)
    meta_rules = {}
    for name, W in w_map.items():
        meta_rules[name] = {}
        for bps in (10, 20, 30, 40):
            s_raw, s_st_raw, turn_m, dh = _pnl(C, W, F, bps / 10_000.0, r_override=r_safe)
            daily_by_bps[bps][name] = s_raw.reindex(idx_eval).fillna(0.0)
            if bps == 20:
                shock30[name] = s_st_raw.reindex(idx_eval).fillna(0.0)
                meta_rules[name] = {"turnover_x_mes": turn_m, "delist_hits": dh}

    return {
        "n_coins_loaded": len(bars),
        "n_basis_series_loaded": len(basis_map),
        "idx_eval": idx_eval,
        "blq": blq,
        "btc_eval": btc_eval,
        "daily_by_bps": daily_by_bps,
        "shock30": shock30,
        "meta_rules": meta_rules,
    }


def main() -> None:
    from registro_global import exigir_contada
    exigir_contada("docs/research/cripto_pit_v3_20261127/PREREGISTRO.md")

    t0 = time.time()
    core = compute_cripto_v3_daily()
    idx_eval, blq, btc_eval = core["idx_eval"], core["blq"], core["btc_eval"]
    daily_by_bps, shock30, meta_rules = core["daily_by_bps"], core["shock30"], core["meta_rules"]
    print(f"=== CRIPTO-PIT v3: {core['n_coins_loaded']} monedas crypto PIT + {core['n_basis_series_loaded']} Basis ({time.time() - t0:.1f}s) ===", flush=True)

    mask_dr = blq.isin(["DESC", "REP"])

    def _extras(s: pd.Series, sub_m: pd.Series) -> dict:
        sd_r = s[sub_m]
        bt_r = btc_eval[sub_m]
        corr_b = round(float(sd_r.corr(bt_r)), 3) if sd_r.std(ddof=1) > 0 and bt_r.std(ddof=1) > 0 else 0.0
        beta_b = round(float((sd_r / 10_000.0).cov(bt_r) / max(bt_r.var(), 1e-12)), 3)
        tot = float(sd_r.sum())
        top5 = float(sd_r.nlargest(5).sum())
        return {
            "corr_BTC": corr_b,
            "beta_BTC": beta_b,
            "top5_days_share": round(top5 / tot, 3) if tot > 1e-6 else None,
            "yearly_usd": {str(k): round(float(v), 1) for k, v in sd_r.groupby(sd_r.index.year).sum().items()},
        }

    results = {
        "n_coins_loaded": core["n_coins_loaded"],
        "n_basis_series_loaded": core["n_basis_series_loaded"],
        "costs_tested_bps": [10, 20, 30, 40],
        "rules": {},
    }
    base_df = pd.DataFrame(index=idx_eval)
    rule_names = list(daily_by_bps[20].columns)

    print("\n=== RESULTADOS CRIPTO-PIT v3 (20 bps RT + funding + basis, SOLO DESC & REP; HOLDOUT SELLADO) ===")
    for name in rule_names:
        results["rules"][name] = {}
        for bps in (10, 20, 30, 40):
            s = daily_by_bps[bps][name]
            s_st = shock30[name]
            entry = {
                "DESC": stats_serie(s[blq == "DESC"]),
                "REP": stats_serie(s[blq == "REP"]),
                "DESC_REP": stats_serie(s[mask_dr]),
            }
            if bps == 20:
                base_df[name] = s
                results["rules"][name]["turnover_x_mes"] = meta_rules[name]["turnover_x_mes"]
                results["rules"][name]["delist_hits"] = meta_rules[name]["delist_hits"]
                desc_tot = float(s[blq == "DESC"].sum())
                desc_top5 = float(s[blq == "DESC"].nlargest(5).sum())
                results["rules"][name]["top5_days_share_DESC"] = round(desc_top5 / desc_tot, 3) if desc_tot > 1e-6 else 9.99
                entry["DESC_REP_22_26"] = stats_serie(s[mask_dr & (idx_eval >= "2022-01-01")])
                entry["DESC_REP_shock30"] = stats_serie(s_st[mask_dr])
                entry.update(_extras(s, mask_dr))
            results["rules"][name][f"bps_{bps}"] = entry
        b20 = results["rules"][name]["bps_20"]
        print(
            f"  {name:28s} | turn={results['rules'][name]['turnover_x_mes']:4.1f}x | "
            f"DESC Sh={b20['DESC']['sharpe']:5.2f} t={b20['DESC']['t_mes']:4.2f} | "
            f"REP Sh={b20['REP']['sharpe']:5.2f} t={b20['REP']['t_mes']:4.2f} | "
            f"DR Sh={b20['DESC_REP']['sharpe']:4.2f} t={b20['DESC_REP']['t_mes']:4.2f} | "
            f"beta={b20['beta_BTC']:+.3f} | top5_D={results['rules'][name]['top5_days_share_DESC']} | dh={results['rules'][name]['delist_hits']}"
        )

    # Monthly correlation matrix in DESC+REP
    m_mat = base_df.loc[mask_dr].groupby(base_df.loc[mask_dr].index.to_period("M")).sum()
    corr_m = m_mat.corr().round(3).to_dict()
    print("\n=== CORRELACION MENSUAL ENTRE MECANISMOS CRIPTO-PIT v3 (DESC+REP) ===")
    print(m_mat.corr().round(3).to_string())

    # Pre-registered basket inclusion rule: DESC usd_mes > 0 AND top5_days_share_DESC < 0.65
    alive = [
        c for c in rule_names
        if results["rules"][c]["bps_20"]["DESC"]["usd_mes"] > 0
        and results["rules"][c]["top5_days_share_DESC"] < 0.65
    ]
    if not alive:
        alive = [c for c in rule_names if results["rules"][c]["bps_20"]["DESC"]["usd_mes"] > 0]
    m_desc = base_df.loc[blq == "DESC", alive].groupby(base_df.loc[blq == "DESC"].index.to_period("M")).sum()
    sd_d = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_b = (1.0 / sd_d) / (1.0 / sd_d).sum()
    bask = (base_df[alive] * w_b).sum(axis=1)
    base_df["CR3_Canasta_InvVol"] = bask

    # Also evaluate sensitivity across bps for basket
    save_dr = base_df.copy()
    save_dr.loc[~mask_dr] = np.nan
    save_dr.to_csv(OUT / "SERIES_CRIPTO_PIT_V3_DR.csv.gz")

    b_out = {
        "DESC": stats_serie(bask[blq == "DESC"]),
        "REP": stats_serie(bask[blq == "REP"]),
        "DESC_REP": stats_serie(bask[mask_dr]),
        "DESC_REP_22_26": stats_serie(bask[mask_dr & (idx_eval >= "2022-01-01")]),
    }
    b_out.update(_extras(bask, mask_dr))

    results["monthly_corr_DESC_REP"] = corr_m
    results["basket_included_prereg"] = alive
    results["basket_inv_vol_weights_DESC"] = {k: round(float(v), 4) for k, v in w_b.items()}
    results["CR3_Canasta_InvVol_bps20"] = b_out

    print("\n=== CANASTA CRIPTO-PIT v3 (Regla fija PREREGISTRO, 20 bps + funding + basis) ===")
    print("  Incluidas:", alive, "pesos:", results["basket_inv_vol_weights_DESC"])
    print("  Canasta  :", b_out["DESC_REP"], "| REP:", b_out["REP"], "| beta_BTC:", b_out["beta_BTC"], "| top5:", b_out["top5_days_share"])

    (OUT / "RESULTADO.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    # Write markdown report
    md = [
        "# CRIPTO-PIT v3: Microestructura Basis (`premiumIndex`) + Beta-Neutralización + 5 Mecanismos (resultado, 2026-11-27)",
        "",
        f"Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](file:///{(OUT / 'PREREGISTRO.md').as_posix()}) (`6` pruebas contadas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` (`18m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        f"- Universo: `{len(bars)}` monedas crypto PIT reales (ex-TradFi, `vol60 >= 25%`, histéresis `<=20 / >25`) + `{len(basis_map)}` series `premiumIndexKlines/1d`.",
        "",
        "| Mecanismo (`20 bps + funding`, `DESC+REP 51m`) | Rot. | `DESC (39m)` `Sh / t` | `REP (12m)` `Sh / t` | `DESC+REP (51m)` `Sh / t` | `22–26` `Sh` | `beta_BTC` / `Top5_D` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        b20 = results["rules"][c]["bps_20"]
        md.append(
            f"| `{c}` | `{results['rules'][c]['turnover_x_mes']}x` | `{b20['DESC']['sharpe']} / {b20['DESC']['t_mes']}` | "
            f"`{b20['REP']['sharpe']} / {b20['REP']['t_mes']}` | **`{b20['DESC_REP']['sharpe']} / {b20['DESC_REP']['t_mes']}`** | "
            f"`{b20['DESC_REP_22_26']['sharpe']}` | `{b20['beta_BTC']:+.3f}` / `{results['rules'][c]['top5_days_share_DESC']}` |"
        )
    md.append(
        f"| **`CR3_Canasta_InvVol`** ({', '.join(alive)}) | — | `{b_out['DESC']['sharpe']} / {b_out['DESC']['t_mes']}` | "
        f"`{b_out['REP']['sharpe']} / {b_out['REP']['t_mes']}` | **`{b_out['DESC_REP']['sharpe']} / {b_out['DESC_REP']['t_mes']}`** | "
        f"`{b_out['DESC_REP_22_26']['sharpe']}` | `{b_out['beta_BTC']:+.3f}` / `{b_out['top5_days_share']}` |"
    )
    md += [
        "",
        f"- Pesos `1/sd` ajustados en `DESC`: `{results['basket_inv_vol_weights_DESC']}`.",
        "- **Aporte al referente**: evalúa 3 mecanismos ortogonales nuevos (`Basis_Carry`, `BAB_LowVol`, `ResidMom_2F`) + beta-neutralización explícita sobre universo PIT sin supervivencia ni fugas de holdout.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


if __name__ == "__main__":
    main()
