#!/usr/bin/env python3
"""CRIPTO-OFI-PIT: Flujo de Ordenes Taker Buy/Sell (No-OHLC) en 226 Perpetuos PIT (2021-2026-09).

Pre-registro: docs/research/cripto_ofi_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC (39m) y REP (12m); HOLDOUT A5 (18m) y >=2026-10-01 SELLADOS (NaN).
Uso:
  python -u tools/cripto_ofi_20261127.py
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
import zipfile
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
from cripto_pit_v2 import (  # noqa: E402
    CORTE,
    CORTE_TS,
    TRADFI_EXCLUDE,
    _normalize_active_neutral,
    _pnl,
    _stagger_weights,
    fetch_all_pit_fast,
    stats_serie,
)
from registro_global import exigir_contada  # noqa: E402

MONTHS = [f"{y:04d}-{m:02d}" for y in range(2020, 2027) for m in range(1, 13) if (y < 2026 or m <= 9)]
OFI_DIR = ROOT / "data/crypto_binance_pit_ofi_1d"
OFI_DIR.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs/research/cripto_ofi_20261127"
OUT.mkdir(parents=True, exist_ok=True)


def _dl_one_ofi_month(sym: str, ym: str) -> pd.DataFrame | None:
    u = f"https://data.binance.vision/data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{ym}.zip"
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            zf = zipfile.ZipFile(io.BytesIO(r.read()))
            raw = pd.read_csv(zf.open(zf.namelist()[0]), header=None)
        if not str(raw.iloc[0, 0]).isdigit():
            raw = raw.iloc[1:].reset_index(drop=True)
        # Cols: 0=open_time, 7=quote_volume, 8=count, 9=taker_buy_vol, 10=taker_buy_quote_vol
        df = pd.DataFrame({
            "t": pd.to_numeric(raw.iloc[:, 0], errors="coerce"),
            "qvol": pd.to_numeric(raw.iloc[:, 7], errors="coerce"),
            "count": pd.to_numeric(raw.iloc[:, 8], errors="coerce"),
            "taker_qvol": pd.to_numeric(raw.iloc[:, 10], errors="coerce"),
        }).dropna()
        return df
    except Exception:
        return None


def fetch_all_ofi_fast(u_df: pd.DataFrame, syms: set[str]) -> dict[str, pd.DataFrame]:
    """Descarga y cachea flujo taker diario < 2026-10-01 por moneda PIT."""
    m_start = u_df.groupby("simbolo")["mes"].min().to_dict()
    m_end = u_df.groupby("simbolo")["mes"].max().to_dict()
    to_dl = []
    out = {}
    for sym in sorted(syms):
        pq = OFI_DIR / f"{sym}_ofi_1d.parquet"
        if pq.exists():
            df = pd.read_parquet(pq)
            assert not (df.index >= CORTE_TS).any(), f"Holdout breach in {pq}!"
            if len(df):
                out[sym] = df
            continue
        ym0 = m_start.get(sym, "2020-01")
        p0 = max(pd.Period(ym0, "M") - 2, pd.Period("2020-01", "M"))
        p1 = min(pd.Period(m_end.get(sym, "2026-09"), "M") + 2, pd.Period("2026-09", "M"))
        for ym in [m for m in MONTHS if p0 <= pd.Period(m, "M") <= p1]:
            to_dl.append((sym, ym))

    if to_dl:
        print(f"  Descargando {len(to_dl)} archivos mensuales klines/1d OFI (32 hilos)...", flush=True)
        by_sym: dict[str, list[pd.DataFrame]] = {}
        with ThreadPoolExecutor(max_workers=32) as ex:
            futs = {ex.submit(_dl_one_ofi_month, s, ym): (s, ym) for s, ym in to_dl}
            for f in as_completed(futs):
                s, _ = futs[f]
                df = f.result()
                if df is not None and len(df):
                    by_sym.setdefault(s, []).append(df)
        for sym in sorted(syms):
            pq = OFI_DIR / f"{sym}_ofi_1d.parquet"
            if pq.exists():
                continue
            parts = by_sym.get(sym, [])
            if not parts:
                pd.DataFrame(columns=["qvol", "count", "taker_qvol"]).to_parquet(pq)
                continue
            k = pd.concat(parts, ignore_index=True).drop_duplicates("t").sort_values("t")
            k["dt"] = pd.to_datetime(k["t"].astype("int64"), unit="ms", utc=True).dt.normalize()
            k = k[k["dt"] < CORTE_TS].drop_duplicates("dt").set_index("dt")[["qvol", "count", "taker_qvol"]]
            assert not (k.index >= CORTE_TS).any(), f"Holdout breach in OFI {sym}!"
            k.to_parquet(pq)
            if len(k):
                out[sym] = k
    return out


def main() -> None:
    exigir_contada("docs/research/cripto_ofi_20261127/PREREGISTRO.md")
    t0 = time.time()
    u = pd.read_csv(ROOT / "docs/research/cripto_pit_20261127/UNIVERSO_PIT.csv")
    ascii_syms = {s for s in u["simbolo"].unique() if str(s).isascii() and s not in TRADFI_EXCLUDE}
    print(f"=== CRIPTO-OFI-PIT: {len(ascii_syms)} monedas crypto PIT (taker buy/sell order flow) ===", flush=True)

    bars = {s: df for s, df in fetch_all_pit_fast(u).items() if s in ascii_syms}
    ofi_map = fetch_all_ofi_fast(u, set(bars.keys()))
    print(f"Cargadas {len(bars)} monedas + {len(ofi_map)} series OFI en {time.time() - t0:.1f}s", flush=True)

    C = pd.DataFrame({s: df["close"] for s, df in bars.items()}).sort_index()
    F = pd.DataFrame({s: df["funding"] for s, df in bars.items()}).reindex(C.index).fillna(0.0)
    QV = pd.DataFrame({s: df["qvol"] for s, df in ofi_map.items()}).reindex(C.index)
    CNT = pd.DataFrame({s: df["count"] for s, df in ofi_map.items()}).reindex(C.index)
    TQV = pd.DataFrame({s: df["taker_qvol"] for s, df in ofi_map.items()}).reindex(C.index)
    for df in (C, F, QV, CNT, TQV):
        df.index = df.index.tz_localize(None)
    C = C[C.index < CORTE]
    F, QV, CNT, TQV = F.reindex(C.index), QV.reindex(C.index), CNT.reindex(C.index), TQV.reindex(C.index)

    r1d = C.pct_change()
    r_safe = r1d.where(r1d.abs() <= 2.5, 0.0)
    vol60 = r_safe.rolling(60, min_periods=30).std() * np.sqrt(365.0)
    vol30 = r_safe.rolling(30, min_periods=15).std() * np.sqrt(365.0)
    inv_vol = (1.0 / vol30.clip(lower=0.15)).replace([np.inf, -np.inf], np.nan)

    # Dynamic PIT membership with hysteresis (same frozen rule as v2/v3)
    mkey = C.index.to_period("M").astype(str)
    top_map = {m: set(g["simbolo"]) for m, g in u.groupby("mes")}
    pit_m = pd.DataFrame(False, index=C.index, columns=C.columns)
    for i, m in enumerate(mkey):
        if m in top_map:
            cols_ok = [c for c in top_map[m] if c in pit_m.columns]
            pit_m.iloc[i, pit_m.columns.get_indexer(cols_ok)] = True
    rk_vol = QV.rolling(30, min_periods=15).mean().rank(axis=1, ascending=False, method="first")
    cand = pit_m & (vol60 >= 0.25) & C.notna()
    E_hyst = pd.DataFrame(False, index=C.index, columns=C.columns)
    prev = pd.Series(False, index=C.columns)
    for i in range(len(C)):
        in_top20 = cand.iloc[i] & (rk_vol.iloc[i] <= 20)
        stay = prev & (rk_vol.iloc[i] <= 25) & cand.iloc[i]
        cur = in_top20 | stay
        E_hyst.iloc[i] = cur
        prev = cur

    # Non-OHLC Order-Flow features (all shifted 1d causally!)
    ofi = ((2.0 * TQV - QV) / QV.clip(lower=1e-6)).clip(-1.0, 1.0)
    avg_sz = np.log((QV / CNT.clip(lower=1.0)).clip(lower=1.0))

    # M1: OFI1_TakerFlow_21d_Stag5d
    ofi21 = (ofi.rolling(21, min_periods=10).mean() / ofi.rolling(21, min_periods=10).std().clip(lower=1e-4)).where(E_hyst)
    rk1 = ofi21.rank(axis=1, ascending=False, method="first")
    n1 = ofi21.notna().sum(axis=1).to_numpy()[:, None]
    p1 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p1[(rk1 <= 4) & (n1 >= 10)] = 1.0
    p1[(rk1 >= n1 - 3) & (n1 >= 10)] = -1.0
    w1 = _stagger_weights(_normalize_active_neutral(p1, inv_vol, max_w=0.20), E_hyst, 5)

    # M2: OFI2_FlowReturn_Div_14d_Stag5d (z_cs(OFI_14d) - z_cs(Ret_14d))
    o14 = ofi.rolling(14, min_periods=8).mean().where(E_hyst)
    r14 = r_safe.rolling(14, min_periods=8).sum().where(E_hyst)
    z_o = o14.sub(o14.mean(axis=1), axis=0).div(o14.std(axis=1).replace(0, np.nan), axis=0)
    z_r = r14.sub(r14.mean(axis=1), axis=0).div(r14.std(axis=1).replace(0, np.nan), axis=0)
    div = (z_o - z_r).where(E_hyst)
    rk2 = div.rank(axis=1, ascending=False, method="first")
    n2 = div.notna().sum(axis=1).to_numpy()[:, None]
    p2 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p2[(rk2 <= 4) & (n2 >= 10)] = 1.0
    p2[(rk2 >= n2 - 3) & (n2 >= 10)] = -1.0
    w2 = _stagger_weights(_normalize_active_neutral(p2, inv_vol, max_w=0.20), E_hyst, 5)

    # M3: OFI3_WhaleFlow_14d_Stag5d (ofi weighted by cross-sectional ticket size rank)
    sz_rk = avg_sz.where(E_hyst).rank(axis=1, pct=True)
    wf14 = ((ofi * sz_rk).rolling(14, min_periods=8).mean() / ofi.rolling(14, min_periods=8).std().clip(lower=1e-4)).where(E_hyst)
    rk3 = wf14.rank(axis=1, ascending=False, method="first")
    n3 = wf14.notna().sum(axis=1).to_numpy()[:, None]
    p3 = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    p3[(rk3 <= 4) & (n3 >= 10)] = 1.0
    p3[(rk3 >= n3 - 3) & (n3 >= 10)] = -1.0
    w3 = _stagger_weights(_normalize_active_neutral(p3, inv_vol, max_w=0.20), E_hyst, 5)

    w_map = {
        "OFI1_TakerFlow_21d_Stag5d": w1,
        "OFI2_FlowReturn_Div_14d_Stag5d": w2,
        "OFI3_WhaleFlow_14d_Stag5d": w3,
    }

    idx_eval = C.index[(C.index >= "2021-01-01") & (C.index < CORTE)]
    blq = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in idx_eval], index=idx_eval)
    assert not blq.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr = blq.isin(["DESC", "REP"])
    btc_eval = r_safe["BTCUSDT"].reindex(idx_eval).fillna(0.0) if "BTCUSDT" in r_safe else pd.Series(0.0, index=idx_eval)

    # Load CR3_XSMOM & CR3_BAB exclusively on DESC+REP to measure true orthogonality
    cr3_p = ROOT / "docs/research/cripto_pit_v3_20261127/SERIES_CRIPTO_PIT_V3_DR.csv.gz"
    cr3_df = pd.read_csv(cr3_p, index_col=0, parse_dates=True).reindex(idx_eval) if cr3_p.exists() else pd.DataFrame(index=idx_eval)

    results = {"n_coins_loaded": len(bars), "n_ofi_loaded": len(ofi_map), "rules": {}}
    base_df = pd.DataFrame(index=idx_eval)

    print("\n=== RESULTADOS CRIPTO-OFI-PIT (20 bps RT + funding, SOLO DESC & REP; HOLDOUT SELLADO) ===")
    for name, W in w_map.items():
        results["rules"][name] = {}
        for bps in (10, 20, 30, 40):
            s_raw, _, turn_m, dh = _pnl(C, W, F, bps / 10_000.0, r_override=r_safe)
            s = s_raw.reindex(idx_eval).fillna(0.0)
            entry = {
                "DESC": stats_serie(s[blq == "DESC"]),
                "REP": stats_serie(s[blq == "REP"]),
                "DESC_REP": stats_serie(s[mask_dr]),
            }
            if bps == 20:
                base_df[name] = s
                results["rules"][name]["turnover_x_mes"] = turn_m
                results["rules"][name]["delist_hits"] = dh
                desc_tot = float(s[blq == "DESC"].sum())
                desc_top5 = float(s[blq == "DESC"].nlargest(5).sum())
                results["rules"][name]["top5_days_share_DESC"] = round(desc_top5 / desc_tot, 3) if desc_tot > 1e-6 else 9.99
                m_s = s[mask_dr].groupby(lambda d: d.to_period("M")).sum()
                for ref_c in ("CR3_XSMOM_21d_Stag5d", "CR3_BAB_LowVol_Stag5d"):
                    if ref_c in cr3_df:
                        m_ref = cr3_df.loc[mask_dr, ref_c].groupby(lambda d: d.to_period("M")).sum()
                        entry[f"corr_m_{ref_c}"] = round(float(m_s.corr(m_ref)), 3)
                entry["beta_BTC"] = round(float((s[mask_dr] / 10_000.0).cov(btc_eval[mask_dr]) / max(btc_eval[mask_dr].var(), 1e-12)), 3)
            results["rules"][name][f"bps_{bps}"] = entry
        b20 = results["rules"][name]["bps_20"]
        print(
            f"  {name:32s} | turn={results['rules'][name]['turnover_x_mes']:4.1f}x | "
            f"DESC Sh={b20['DESC']['sharpe']:5.2f} t={b20['DESC']['t_mes']:4.2f} | REP Sh={b20['REP']['sharpe']:5.2f} | "
            f"DR Sh={b20['DESC_REP']['sharpe']:5.2f} t={b20['DESC_REP']['t_mes']:4.2f} | corr_XSMOM={b20.get('corr_m_CR3_XSMOM_21d_Stag5d', 0):+.3f} | top5_D={results['rules'][name]['top5_days_share_DESC']}"
        )

    rule_names = list(w_map.keys())
    alive = [c for c in rule_names if results["rules"][c]["bps_20"]["DESC"]["usd_mes"] > 0 and results["rules"][c]["top5_days_share_DESC"] < 0.65]
    if not alive:
        alive = [c for c in rule_names if results["rules"][c]["bps_20"]["DESC"]["usd_mes"] > 0]
    if alive:
        m_desc = base_df.loc[blq == "DESC", alive].groupby(lambda d: d.to_period("M")).sum()
        sd_d = m_desc.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
        w_b = (1.0 / sd_d) / (1.0 / sd_d).sum()
        bask = (base_df[alive] * w_b).sum(axis=1)
    else:
        w_b = pd.Series(dtype=float)
        bask = pd.Series(0.0, index=idx_eval)
    base_df["OFI_Canasta_InvVol"] = bask

    save_dr = base_df.copy()
    save_dr.loc[~mask_dr] = np.nan
    save_dr.to_csv(OUT / "SERIES_CRIPTO_OFI_DR.csv.gz")

    m_b = bask[mask_dr].groupby(lambda d: d.to_period("M")).sum()
    b_out = {
        "DESC": stats_serie(bask[blq == "DESC"]),
        "REP": stats_serie(bask[blq == "REP"]),
        "DESC_REP": stats_serie(bask[mask_dr]),
        "beta_BTC": round(float((bask[mask_dr] / 10_000.0).cov(btc_eval[mask_dr]) / max(btc_eval[mask_dr].var(), 1e-12)), 3),
        "corr_m_CR3_XSMOM": round(float(m_b.corr(cr3_df.loc[mask_dr, "CR3_XSMOM_21d_Stag5d"].groupby(lambda d: d.to_period("M")).sum())), 3) if "CR3_XSMOM_21d_Stag5d" in cr3_df else None,
        "corr_m_CR3_BAB": round(float(m_b.corr(cr3_df.loc[mask_dr, "CR3_BAB_LowVol_Stag5d"].groupby(lambda d: d.to_period("M")).sum())), 3) if "CR3_BAB_LowVol_Stag5d" in cr3_df else None,
    }
    results["basket_included_prereg"] = alive
    results["basket_weights_DESC"] = {k: round(float(v), 4) for k, v in w_b.items()}
    results["OFI_Canasta_InvVol_bps20"] = b_out
    (OUT / "RESULTADO.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    md = [
        "# CRIPTO-OFI-PIT: Flujo Taker Buy/Sell No-OHLC en 226 Perpetuos PIT (resultado, 2026-11-27)",
        "",
        "Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` (`18m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "| Mecanismo (`20 bps + funding`) | Rot. | `DESC (39m) Sh / t` | `REP (12m) Sh / t` | `DR (51m) Sh / t` | `corr_XSMOM` | `top5_D` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for c in rule_names:
        b20 = results["rules"][c]["bps_20"]
        md.append(
            f"| `{c}` | `{results['rules'][c]['turnover_x_mes']}x` | `{b20['DESC']['sharpe']} / {b20['DESC']['t_mes']}` | "
            f"`{b20['REP']['sharpe']} / {b20['REP']['t_mes']}` | **`{b20['DESC_REP']['sharpe']} / {b20['DESC_REP']['t_mes']}`** | "
            f"`{b20.get('corr_m_CR3_XSMOM_21d_Stag5d', 0):+.3f}` | `{results['rules'][c]['top5_days_share_DESC']}` |"
        )
    md += [
        f"| **`OFI_Canasta_InvVol`** ({', '.join(alive) if alive else 'ninguna'}) | — | `{b_out['DESC']['sharpe']} / {b_out['DESC']['t_mes']}` | "
        f"`{b_out['REP']['sharpe']} / {b_out['REP']['t_mes']}` | **`{b_out['DESC_REP']['sharpe']} / {b_out['DESC_REP']['t_mes']}`** | "
        f"`{b_out['corr_m_CR3_XSMOM']}` | `beta={b_out['beta_BTC']:+.3f}` |",
        "",
        "Diagnóstico de grilla: sin grilla paramétrica (`3` reglas de flujo `taker` escalonadas a `5d`, patas `top-4/bot-4` + canasta causal `DESC`).",
        f"Episodios: `DESC` (`39m`, `Sh={b_out['DESC']['sharpe']}`), `REP` (`12m`, `Sh={b_out['REP']['sharpe']}`), correlación mensual vs `XSMOM` `{b_out['corr_m_CR3_XSMOM']}` y vs `BAB` `{b_out['corr_m_CR3_BAB']}`.",
        "",
        "- **Aporte al referente**: mide de forma limpia y pre-registrada si el flujo agresor `taker buy/sell` no-OHLC aporta ventaja y ortogonalidad real frente a `XSMOM`.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


if __name__ == "__main__":
    main()
