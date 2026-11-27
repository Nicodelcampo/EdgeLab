#!/usr/bin/env python3
"""SUPERCARTERA v3: Pozo Limpio 63m Cero-Iteracion + CRIPTO-OFI + HRP Corregido + Kaggle CSCV.

Pre-registro: docs/research/supercartera_v3_20261127/PREREGISTRO.md (K51).
Evalua ESTRICTAMENTE sobre DESC y REP (< 2026-10-01); HOLDOUT A5 y TERMINAL SELLADOS (NaN).
Uso:
  python -u tools/supercartera_v3_20261127.py --prepare
  python -u tools/supercartera_v3_20261127.py --finalize
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
except ImportError:
    leaves_list = linkage = squareform = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_meses  # noqa: E402
from marco_sin_forward import _a5_mes_blq, _map_crypto_intra_month, stats_monthly_10vol  # noqa: E402
from registro_global import exigir_contada  # noqa: E402
from supercartera_v2_20261127 import load_all_fronts as _load_v2_fronts  # noqa: E402

OUT = ROOT / "docs/research/supercartera_v3_20261127"
OUT.mkdir(parents=True, exist_ok=True)
KDIR = OUT / "kaggle_super_v3"
KDIR.mkdir(parents=True, exist_ok=True)


def _phi_local(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def hrp_sample_reg(ret: pd.DataFrame, reg: float = 0.15) -> np.ndarray:
    """HRP con covarianza muestral regularizada (0.85*S + 0.15*diag(S)) para evitar colapso a identidad."""
    arr = ret.fillna(0.0).to_numpy(float)
    if leaves_list is None or arr.shape[1] < 2 or len(arr) < 12:
        sd = ret.std(ddof=1).replace(0.0, np.nan).fillna(1.0).to_numpy()
        w = 1.0 / sd
        return w / w.sum()
    S = np.cov(arr, rowvar=False, ddof=1)
    d = np.diag(np.clip(np.diag(S), 1e-8, None))
    cov = (1.0 - reg) * S + reg * d
    sd = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
    corr = cov / np.outer(sd, sd)
    np.fill_diagonal(corr, 1.0)
    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, 1.0))
    np.fill_diagonal(dist, 0.0)
    order = leaves_list(linkage(squareform(dist, checks=False), "single"))
    w = np.ones(len(sd))
    clusters = [list(order)]
    while clusters:
        c = clusters.pop()
        if len(c) <= 1:
            continue
        a, b = c[: len(c) // 2], c[len(c) // 2 :]

        def _cvar(ix):
            cc = cov[np.ix_(ix, ix)]
            iv = 1.0 / np.clip(np.diag(cc), 1e-8, None)
            iv /= iv.sum()
            return float(iv @ cc @ iv)

        va, vb = _cvar(a), _cvar(b)
        al = 1.0 - va / (va + vb) if (va + vb) > 0 else 0.5
        w[a] *= al
        w[b] *= 1.0 - al
        clusters += [a, b]
    return w / w.sum()


def load_v3_universe() -> dict:
    v2 = _load_v2_fronts()
    bidx = v2["bidx_long"]
    blq = v2["blq_long"]
    dr = v2["mask_dr_long"]
    ds = v2["daily_sleeves"].copy()

    # Load MACRO_RISK_PREMIA (2006-2026-09 DESC+REP, NaN outside)
    mrp_raw = pd.read_csv(ROOT / "docs/research/macro_risk_premia_20261127/SERIES_MACRO_RP_DR.csv.gz", index_col=0, parse_dates=True)
    mrp_cols = ["RP1_Sector_XSMOM_Neut", "RP2_Sector_BAB_LowBeta", "RP3_Country_XSMOM_Neut", "RP4_Rates_Curve_Credit", "RP5_NonEq_MultiSpeed_Trend"]
    mrp_ind = mrp_raw[mrp_cols].reindex(bidx).where(dr, np.nan)
    ds["Macro_RP_Canasta"] = np.where(dr, mrp_raw["RP_Canasta_InvVol"].reindex(bidx).fillna(0.0), np.nan)

    # Diagnostic equal inv-vol DESC across positive Macro RP mechanisms (RP2+RP4+RP5)
    mrp_pos = ["RP2_Sector_BAB_LowBeta", "RP4_Rates_Curve_Credit", "RP5_NonEq_MultiSpeed_Trend"]
    m_mp = mrp_ind.loc[blq == "DESC", mrp_pos].groupby(lambda d: d.to_period("M")).sum()
    sd_mp = m_mp.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_mp = (1.0 / sd_mp) / (1.0 / sd_mp).sum()
    ds["Macro_RP_Diag_3Pos"] = np.where(dr, (mrp_ind[mrp_pos].fillna(0.0) * w_mp).sum(axis=1), np.nan)

    # Load CRIPTO_OFI_PIT (mapped strictly intra-month, zero cross-block leak)
    ofi_p = ROOT / "docs/research/cripto_ofi_20261127/SERIES_CRIPTO_OFI_DR.csv.gz"
    ofi_j_p = ROOT / "docs/research/cripto_ofi_20261127/RESULTADO.json"
    ofi_ok = False
    ofi_ind = pd.DataFrame(index=bidx)
    if ofi_p.exists() and ofi_j_p.exists():
        ofi_raw = pd.read_csv(ofi_p, index_col=0, parse_dates=True).dropna(how="all")
        ofi_j = json.loads(ofi_j_p.read_text(encoding="utf-8"))
        ofi_mapped = _map_crypto_intra_month(ofi_raw, bidx, dr)
        for c in ["OFI1_TakerFlow_21d_Stag5d", "OFI2_FlowReturn_Div_14d_Stag5d", "OFI3_WhaleFlow_14d_Stag5d"]:
            if c in ofi_mapped:
                ofi_ind[c] = ofi_mapped[c]
        can = ofi_j.get("OFI_Canasta_InvVol_bps20", {})
        corr_xs = can.get("corr_m_CR3_XSMOM")
        desc_usd = can.get("DESC", {}).get("usd_mes", 0.0)
        if desc_usd > 0 and (corr_xs is None or abs(float(corr_xs)) < 0.60) and "OFI_Canasta_InvVol" in ofi_mapped:
            ds["Cripto_OFI_Canasta"] = ofi_mapped["OFI_Canasta_InvVol"]
            ofi_ok = True
        elif "OFI_Canasta_InvVol" in ofi_mapped:
            ds["Cripto_OFI_Diag"] = ofi_mapped["OFI_Canasta_InvVol"]

    return {
        "bidx": bidx,
        "blq": blq,
        "dr": dr,
        "ds": ds,
        "c2_16_df": v2["c2_16_df"],
        "cr3_ind": v2["cr3_ind"],
        "cme_ind": v2["cme_ind"],
        "mrp_ind": mrp_ind,
        "ofi_ind": ofi_ind,
        "ofi_ok": ofi_ok,
    }


def build_v3_analysis(uni: dict) -> dict:
    bidx, blq, dr, ds = uni["bidx"], uni["blq"], uni["dr"], uni["ds"]

    m_all = ds.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1).sort_index()
    blq_m = pd.Series([_a5_mes_blq(p) for p in m_all.index], index=m_all.index)
    m_all = m_all[blq_m.isin(["DESC", "REP"])]
    blq_m = blq_m[blq_m.isin(["DESC", "REP"])]
    dr_periods = set(m_all.index)

    # ---- BLOCK A: Long-History Pure Zero-Iteration 63m Clean Pool (2006-01..2026-09, 186m DR) ----
    long_cols = ["Carril2_Sell16", "Macro_RP_Canasta"]
    m_long = m_all[long_cols + ["Macro_RP_Diag_3Pos"]].dropna().copy()
    blq_ml = blq_m.reindex(m_long.index)
    sd_long = {c: float(m_long.loc[blq_ml == "DESC", c].std(ddof=1)) for c in m_long.columns}
    m_long_n = m_long / pd.Series(sd_long)

    d_long = ds.loc[dr, m_long.columns] / pd.Series(sd_long)
    w_long = d_long.resample("W-FRI").sum(min_count=1).dropna(how="all")
    keep_wl = [(pd.Period(d, "M") in dr_periods) and (pd.Period(d - pd.Timedelta(days=6), "M") in dr_periods) for d in w_long.index]
    w_long = w_long.loc[keep_wl].fillna(0.0)
    blq_wl = pd.Series([_a5_mes_blq(pd.Period(d, "M")) for d in w_long.index], index=w_long.index)

    w_hrp_63m = hrp_sample_reg(w_long.loc[blq_wl == "DESC", long_cols], reg=0.15)
    m_long_port = pd.DataFrame({
        "Carril2_Sell16_06_26": m_long_n["Carril2_Sell16"],
        "Macro_RP_Canasta_06_26": m_long_n["Macro_RP_Canasta"],
        "Macro_RP_Diag_3Pos_06_26": m_long_n["Macro_RP_Diag_3Pos"],
        "Super_v3_Clean63m_EQ": m_long_n[long_cols].mean(axis=1),
        "Super_v3_Clean63m_HRP": (m_long_n[long_cols] * w_hrp_63m).sum(axis=1),
        "Super_v3_Clean63m_Diag3Pos_EQ": m_long_n[["Carril2_Sell16", "Macro_RP_Diag_3Pos"]].mean(axis=1),
    })
    w_long_port = pd.DataFrame({
        "Carril2_Sell16_06_26": w_long["Carril2_Sell16"],
        "Macro_RP_Canasta_06_26": w_long["Macro_RP_Canasta"],
        "Super_v3_Clean63m_EQ": w_long[long_cols].mean(axis=1),
        "Super_v3_Clean63m_HRP": (w_long[long_cols] * w_hrp_63m).sum(axis=1),
    })

    long_stats = {}
    for c in m_long_port.columns:
        s = m_long_port[c]
        long_stats[c] = {
            "DESC": stats_monthly_10vol(s[blq_ml == "DESC"]),
            "REP": stats_monthly_10vol(s[blq_ml == "REP"]),
            "DESC_REP": stats_monthly_10vol(s),
        }

    # ---- BLOCK B: Multi-Front 2021-2026 Pool (51m DR) ----
    nocme_cols = ["Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta"]
    if uni["ofi_ok"]:
        nocme_cols.append("Cripto_OFI_Canasta")
    core_cols = ["CME_TRZV"] + nocme_cols
    all_21_cols = list(dict.fromkeys(["CME_TRZV", "CME_Div10", "Global_VolComp_M1DK", "Macro_RP_Diag_3Pos"] + nocme_cols))

    m21 = m_all.loc[m_all.index >= "2021-01", all_21_cols].dropna().copy()
    blq_m21 = blq_m.reindex(m21.index)
    sd_21 = {c: float(m21.loc[blq_m21 == "DESC", c].std(ddof=1)) for c in m21.columns}
    m21_n = m21 / pd.Series(sd_21)

    d21 = ds.loc[dr & (bidx >= "2021-01-01"), all_21_cols] / pd.Series(sd_21)
    w21 = d21.resample("W-FRI").sum(min_count=1).dropna(how="all")
    keep_w21 = [(pd.Period(d, "M") in dr_periods) and (pd.Period(d - pd.Timedelta(days=6), "M") in dr_periods) for d in w21.index]
    w21 = w21.loc[keep_w21].fillna(0.0)
    blq_w21 = pd.Series([_a5_mes_blq(pd.Period(d, "M")) for d in w21.index], index=w21.index)

    w_hrp_nc = hrp_sample_reg(w21.loc[blq_w21 == "DESC", nocme_cols], reg=0.15)
    w_hrp_core = hrp_sample_reg(w21.loc[blq_w21 == "DESC", core_cols], reg=0.15)

    def _asm21(df_n: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({
            "CME_TRZV": df_n["CME_TRZV"],
            "Carril2_Sell16": df_n["Carril2_Sell16"],
            "Macro_RP_Canasta": df_n["Macro_RP_Canasta"],
            "Cripto_v3_Canasta": df_n["Cripto_v3_Canasta"],
            "Global_VolComp_M1DK": df_n["Global_VolComp_M1DK"],
            "Super_v3_Clean63m_EQ_21_26": df_n[long_cols].mean(axis=1),
            "Super_v3_NoCME_EQ": df_n[nocme_cols].mean(axis=1),
            "Super_v3_NoCME_HRP": (df_n[nocme_cols] * w_hrp_nc).sum(axis=1),
            "Super_v3_NoCME_plus_GlobalVol_Diag": df_n[nocme_cols + ["Global_VolComp_M1DK"]].mean(axis=1),
            "Super_v3_Core_TRZV_EQ": df_n[core_cols].mean(axis=1),
            "Super_v3_Core_TRZV_HRP": (df_n[core_cols] * w_hrp_core).sum(axis=1),
        })

    m21_port = _asm21(m21_n)
    w21_port = _asm21(w21)
    # Merge long weekly series (2006-2026) and 2021-2026 weekly series for Kaggle bootstrap
    w_boot = pd.concat([w_long_port[["Super_v3_Clean63m_EQ", "Super_v3_Clean63m_HRP", "Carril2_Sell16_06_26", "Macro_RP_Canasta_06_26"]], w21_port], axis=1)
    m_boot = pd.concat([m_long_port[["Super_v3_Clean63m_EQ", "Super_v3_Clean63m_HRP", "Carril2_Sell16_06_26", "Macro_RP_Canasta_06_26"]], m21_port], axis=1)

    cav = {c: c.startswith("CME_") or "Core_TRZV" in c for c in m_boot.columns}

    stats_21 = {}
    for c in m21_port.columns:
        s = m21_port[c]
        stats_21[c] = {
            "upstream_selection_caveat": cav[c],
            "DESC": stats_monthly_10vol(s[blq_m21 == "DESC"]),
            "REP": stats_monthly_10vol(s[blq_m21 == "REP"]),
            "DESC_REP": stats_monthly_10vol(s),
        }

    # Sealed Holdout A5 Theoretical Power (ZERO reads!)
    def _n_sealed(p0: str) -> int:
        return sum(1 for p in pd.period_range(p0, "2026-09", freq="M") if _a5_mes_blq(p) == "HOLDOUT")

    def _pwr(ms: pd.Series, n_seal: int, tag: str) -> dict:
        m = ms.dropna()
        sr = float(m.mean() / m.std(ddof=1) * sqrt(12.0))
        return {
            "nota": tag,
            "meses_DR": int(len(m)),
            "sr_DR": round(sr, 3),
            "n_holdout_sellado": int(n_seal),
            "pot_05x": round(_phi_local(sqrt(n_seal / 12.0) * (0.5 * sr) - 1.6448536), 3),
            "pot_07x": round(_phi_local(sqrt(n_seal / 12.0) * (0.7 * sr) - 1.6448536), 3),
            "pot_10x": round(_phi_local(sqrt(n_seal / 12.0) * sr - 1.6448536), 3),
        }

    dyn_nocme = pd.concat([m_long_n["Carril2_Sell16"], m_long_n["Macro_RP_Canasta"], m21_n["Cripto_v3_Canasta"]], axis=1).mean(axis=1)
    pooled_pwr = {
        "1_Carril2_Sell16_06_26": _pwr(m_long_port["Carril2_Sell16_06_26"], _n_sealed("2006-01"), "LIMPIO_0_ITER_REP"),
        "2_Macro_RP_Canasta_06_26": _pwr(m_long_port["Macro_RP_Canasta_06_26"], _n_sealed("2006-01"), "LIMPIO_0_ITER_REP"),
        "3_Pool_Clean_63m_ZeroIter": _pwr(m_long_port["Super_v3_Clean63m_EQ"], _n_sealed("2006-01"), "LIMPIO_0_ITER_REP_SOLO_CARRIL2_Y_MACRO_RP"),
        "4_Pool_Clean_63m_HRP": _pwr(m_long_port["Super_v3_Clean63m_HRP"], _n_sealed("2006-01"), "LIMPIO_0_ITER_REP_HRP"),
        "5_Pool_NoCME_Dyn_63m": _pwr(dyn_nocme, _n_sealed("2006-01"), "INCLUYE_CRIPTO_V3_CON_REP_ITERADA"),
    }

    # Shrinkage stress (CME 0.5x vs Clean 0.7x/0.5x)
    stress = {}
    for cme_sh, oth_sh in [(1.0, 1.0), (0.5, 0.7), (0.5, 0.5)]:
        lbl = f"CME_{cme_sh}x__Oth_{oth_sh}x"
        adj = m21_n.copy()
        for c in ("CME_TRZV", "CME_Div10"):
            if c in adj:
                adj[c] = adj[c] - (1.0 - cme_sh) * float(adj[c].mean())
        for c in nocme_cols:
            adj[c] = adj[c] - (1.0 - oth_sh) * float(adj[c].mean())
        stress[lbl] = {
            "CME_TRZV": stats_monthly_10vol(adj["CME_TRZV"]),
            "Super_v3_Clean63m_EQ_21_26": stats_monthly_10vol(adj[long_cols].mean(axis=1)),
            "Super_v3_NoCME_EQ": stats_monthly_10vol(adj[nocme_cols].mean(axis=1)),
            "Super_v3_Core_TRZV_EQ": stats_monthly_10vol(adj[core_cols].mean(axis=1)),
            "Super_v3_Core_TRZV_HRP": stats_monthly_10vol((adj[core_cols] * w_hrp_core).sum(axis=1)),
        }

    # CSCV Matrices (ZERO HOLDOUT)
    c2_16_m = uni["c2_16_df"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    c2_16_m = c2_16_m[[_a5_mes_blq(p) in ("DESC", "REP") for p in c2_16_m.index]].fillna(0.0)
    mrp_m = uni["mrp_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    mrp_m = mrp_m[[_a5_mes_blq(p) in ("DESC", "REP") for p in mrp_m.index]].fillna(0.0)
    m_clean_06_26 = pd.concat([c2_16_m, mrp_m.reindex(c2_16_m.index)], axis=1).fillna(0.0)
    m_clean_06_26 = m_clean_06_26.loc[:, m_clean_06_26.std(ddof=1) > 1e-8]

    c2_21_m = c2_16_m.loc[c2_16_m.index >= "2021-01"]
    cr3_m = uni["cr3_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    ofi_m = uni["ofi_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum() if len(uni["ofi_ind"].columns) else pd.DataFrame(index=c2_21_m.index)
    m_nocme_21 = pd.concat([c2_21_m, mrp_m.reindex(c2_21_m.index), cr3_m.reindex(c2_21_m.index), ofi_m.reindex(c2_21_m.index)], axis=1).fillna(0.0)
    m_nocme_21 = m_nocme_21.loc[:, m_nocme_21.std(ddof=1) > 1e-8]

    cme_m = uni["cme_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    m_all_21 = pd.concat([cme_m.loc[cme_m.index >= "2021-01"].reindex(c2_21_m.index), m_nocme_21], axis=1).fillna(0.0)
    m_all_21 = m_all_21.loc[:, m_all_21.std(ddof=1) > 1e-8]

    d21_save = _asm21(d21)
    d21_save.loc[~blq.reindex(d21_save.index).isin(["DESC", "REP"])] = np.nan
    d21_save.to_csv(OUT / "SERIES_SUPERCARTERA_V3_DR.csv.gz")

    d_long_save = d_long.copy()
    d_long_save["Super_v3_Clean63m_EQ"] = d_long_save[long_cols].mean(axis=1)
    d_long_save["Super_v3_Clean63m_HRP"] = (d_long_save[long_cols] * w_hrp_63m).sum(axis=1)
    d_long_save.loc[~blq.reindex(d_long_save.index).isin(["DESC", "REP"])] = np.nan
    d_long_save.to_csv(OUT / "SERIES_CLEAN63M_06_26_DR.csv.gz")

    return {
        "long_stats_06_26": long_stats,
        "stats_21_26": stats_21,
        "hrp_63m_weights": {c: round(float(v), 4) for c, v in zip(long_cols, w_hrp_63m)},
        "hrp_nocme_weights": {c: round(float(v), 4) for c, v in zip(nocme_cols, w_hrp_nc)},
        "hrp_core_trzv_weights": {c: round(float(v), 4) for c, v in zip(core_cols, w_hrp_core)},
        "corr_m_long_06_26": m_long_n.corr().round(3).to_dict(),
        "corr_m_21_26": m21_n[["CME_TRZV", "Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Global_VolComp_M1DK"]].corr().round(3).to_dict(),
        "pooled_pwr": pooled_pwr,
        "stress": stress,
        "cscv_mats": {"1_clean_long_06_26": m_clean_06_26, "2_clean_nocme_21_26": m_nocme_21, "3_desc_all_21_26": m_all_21},
        "w_boot": w_boot,
        "m_boot": m_boot,
        "caveat_map": cav,
        "ofi_included": uni["ofi_ok"],
        "nocme_cols": nocme_cols,
        "core_cols": core_cols,
    }


def write_kaggle_kernel_v3(info: dict) -> None:
    mats = info["cscv_mats"]
    payload = {
        "cscv_items": [(k, list(v.columns), np.round(v.to_numpy(float), 4).tolist()) for k, v in mats.items()],
        "wb_cols": list(info["w_boot"].columns),
        "wb_vals": np.round(info["w_boot"].fillna(np.nan).to_numpy(float), 4).tolist(),
        "pm_cols": list(info["m_boot"].columns),
        "pm_vals": np.round(info["m_boot"].fillna(np.nan).to_numpy(float), 4).tolist(),
        "cav": info["caveat_map"],
    }
    b64 = base64.b64encode(gzip.compress(json.dumps(payload).encode("utf-8"))).decode("ascii")
    script = f'''#!/usr/bin/env python3
"""Kaggle Kernel v3: CSCV Clean Long (06-26), Clean NoCME (21-26), Descriptive CME + DSR + Bayes + Boot 20k semanal @ 10% vol."""
import base64, gzip, itertools, json, os, time
from math import erf, sqrt
from pathlib import Path
import numpy as np
from numba import njit

D = json.loads(gzip.decompress(base64.b64decode("{b64}")).decode("utf-8"))


def phi(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def dsr_p(ret_m, nt):
    rm = ret_m[np.isfinite(ret_m)]
    T = len(rm)
    if T < 6 or np.std(rm, ddof=1) == 0:
        return {{"sr_anual": 0.0, "dsr": 0.0}}
    srm = float(np.mean(rm) / np.std(rm, ddof=1))
    z = (rm - np.mean(rm)) / np.std(rm, ddof=1)
    sk, ku = float(np.mean(z ** 3)), float(np.mean(z ** 4))
    if nt <= 1:
        sr0 = 0.0
    else:
        eg = 0.5772156649
        def inv(p):
            lo, hi = -6.0, 6.0
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                if phi(mid) < p: lo = mid
                else: hi = mid
            return 0.5 * (lo + hi)
        sr0 = ((1.0 - eg) * inv(1.0 - 1.0 / nt) + eg * inv(1.0 - 1.0 / (nt * np.e))) / sqrt(T)
    den = sqrt(max(1e-8, 1.0 - sk * srm + ((ku - 1.0) / 4.0) * (srm ** 2)))
    return {{"sr_anual": round(srm * sqrt(12.0), 3), "dsr": round(phi((srm - sr0) * sqrt(T - 1.0) / den), 4)}}


def cscv_run(mat_m, S=16, tag="LIMPIO"):
    T, K = mat_m.shape
    bl = T // S
    us = bl * S
    blocks = [mat_m[:us][i * bl : (i + 1) * bl] for i in range(S)]
    all_i = set(range(S))
    lg, ob, oe, ib = [], [], [], []
    for cb in itertools.combinations(range(S), S // 2):
        oo = sorted(all_i - set(cb))
        IS, OOS = np.vstack([blocks[i] for i in cb]), np.vstack([blocks[i] for i in oo])
        sdi = np.std(IS, axis=0, ddof=1)
        sri = np.where(sdi > 1e-9, np.mean(IS, axis=0) / sdi, 0.0) * sqrt(12.0)
        sdo = np.std(OOS, axis=0, ddof=1)
        sro = np.where(sdo > 1e-9, np.mean(OOS, axis=0) / sdo, 0.0) * sqrt(12.0)
        ns = int(np.argmax(sri))
        ib.append(float(sri[ns])); ob.append(float(sro[ns]))
        rk = min(max(float(np.sum(sro <= sro[ns])) / (K + 1.0), 1.0 / (K + 1.0)), K / (K + 1.0))
        lg.append(float(np.log(rk / (1.0 - rk))))
        ew = np.mean(OOS / np.where(sdi > 1e-9, sdi, 1.0), axis=1)
        oe.append(float(np.mean(ew) / max(np.std(ew, ddof=1), 1e-9) * sqrt(12.0)))
    return {{
        "tag": tag, "n_splits": len(lg), "T_months": us, "K_strategies": K,
        "PBO": round(float(np.mean(np.asarray(lg) <= 0.0)), 4),
        "best_IS_SR_med": round(float(np.median(ib)), 3),
        "best_OOS_SR_med": round(float(np.median(ob)), 3),
        "basket_1N_OOS_SR_med": round(float(np.median(oe)), 3),
        "basket_1N_P_pos": round(float(np.mean(np.asarray(oe) > 0.0)), 4),
        "basket_1N_P_gt_05": round(float(np.mean(np.asarray(oe) > 0.5)), 4),
    }}


@njit
def boot_20k(yw, npa, bl, seed):
    L = len(yw)
    srs, rets, mdds = np.zeros(npa), np.zeros(npa), np.zeros(npa)
    for k in range(npa):
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        pos, rem, eq, pk, mdd, sy, sy2 = 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0
        for _ in range(52):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = bl
            idx = (pos + (bl - rem)) % L
            rem -= 1
            v = yw[idx]
            sy += v; sy2 += v * v; eq += v
            if eq > pk: pk = eq
            if eq - pk < mdd: mdd = eq - pk
        mu = sy / 52.0
        srs[k] = (mu / sqrt(max(1e-12, (sy2 / 52.0) - mu * mu))) * sqrt(52.0)
        rets[k] = eq; mdds[k] = mdd
    return srs, rets, mdds


def main():
    t0 = time.time()
    cscv_out = {{}}
    for k, _, vals in D["cscv_items"]:
        tag = "DESCRIPTIVO_SESGO_CME" if "desc" in k else "LIMPIO_SIN_CME"
        cscv_out[k] = cscv_run(np.asarray(vals, dtype=np.float64), S=16, tag=tag)
    pm = np.asarray(D["pm_vals"], dtype=np.float64)
    wb = np.asarray(D["wb_vals"], dtype=np.float64)
    cav = D["cav"]
    dsr_out, eb_out, bt_out = {{}}, {{}}, {{}}
    for j, c in enumerate(D["pm_cols"]):
        cv = pm[:, j]; cv = cv[np.isfinite(cv)]
        dsr_out[c] = {{f"N_{{nt}}": dsr_p(cv, nt) for nt in (1, 10, 50, 500, 5000)}}
        sro = float(np.mean(cv) / max(np.std(cv, ddof=1), 1e-9) * sqrt(12.0))
        se = sqrt(12.0 / max(1, len(cv)))
        pv = 1.0 / (1.0 / (0.65 ** 2) + 1.0 / (se ** 2))
        pmu, psd = pv * (sro / (se ** 2)), sqrt(pv)
        eb_out[c] = {{"sr_obs": round(sro, 3), "T_m": len(cv), "caveat": bool(cav.get(c, True)), "post_mean": round(pmu, 3), "P_gt_05": round(1.0 - phi((0.5 - pmu) / psd), 4)}}
    for j, c in enumerate(D["wb_cols"]):
        yw = wb[:, j]; yw = yw[np.isfinite(yw)]
        sdw = float(np.std(yw, ddof=1))
        yw10 = yw / (sdw * sqrt(52.0)) * 10.0 if sdw > 0 else yw
        srs, rets, mdds = boot_20k(yw10, 20000, 4, 202611 + j)
        bt_out[c] = {{
            "weeks": len(yw), "sr_1y_p50": round(float(np.median(srs)), 3),
            "P_yr_pos": round(float(np.mean(rets > 0.0)), 4),
            "mdd_p50": round(float(np.median(mdds)), 2), "mdd_p95": round(float(np.percentile(mdds, 5)), 2),
            "calmar_p50": round(float(np.median(rets) / max(abs(np.median(mdds)), 1e-6)), 2),
        }}
    res = {{"elapsed_s": round(time.time() - t0, 2), "cscv": cscv_out, "dsr": dsr_out, "bayes": eb_out, "boot_20k": bt_out}}
    out_p = Path("/kaggle/working/KAGGLE_SUPER_V3_RESUMEN.json") if os.path.isdir("/kaggle/working") else Path("KAGGLE_SUPER_V3_RESUMEN.json")
    out_p.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"DONE SUPER_V3 KAGGLE in {{time.time() - t0:.1f}}s", flush=True)


if __name__ == "__main__":
    main()
'''
    (KDIR / "kaggle_super_v3.py").write_text(script, encoding="utf-8")
    print("Generated Kaggle v3 kernel:", KDIR / "kaggle_super_v3.py")


def write_summary_v3(info: dict, k_res: dict | None) -> None:
    out_j = {k: v for k, v in info.items() if k not in ("cscv_mats", "w_boot", "m_boot")}
    out_j["kaggle_summary"] = k_res
    (OUT / "SUPERCARTERA_V3.json").write_text(json.dumps(out_j, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    ls, s21 = info["long_stats_06_26"], info["stats_21_26"]
    md = [
        "# SUPERCARTERA v3: Pozo Limpio 63m Cero-Iteración + HRP Corregido + CSCV (resultado, 2026-11-27)",
        "",
        "Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "## 1. Pozo Limpio 63m Cero-Iteración (`2006–2026-09 DESC 144m + REP 42m`, `@10% vol`)",
        "| Cartera / Frente (`186m DR`, cero sesgo CME ni iteración REP) | `DESC Sh` | `REP Sh` | `DR Sh / t` | `MDD@10%` | `Calmar@10%` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k in ["Carril2_Sell16_06_26", "Macro_RP_Canasta_06_26", "Super_v3_Clean63m_EQ", "Super_v3_Clean63m_HRP", "Macro_RP_Diag_3Pos_06_26", "Super_v3_Clean63m_Diag3Pos_EQ"]:
        v = ls[k]
        md.append(f"| `{k}` | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP']['mdd_at_10pct_vol']}%` | `{v['DESC_REP']['calmar_at_10pct_vol']}` |")

    md += [
        "",
        f"- **Pesos HRP corregidos (`0.85*S + 0.15*diag(S)`, semanas `DESC`)**: `Clean63m = {info['hrp_63m_weights']}`, `NoCME 21-26 = {info['hrp_nocme_weights']}`, `Core_TRZV = {info['hrp_core_trzv_weights']}`.",
        f"- **Correlación mensual `Carril2_Sell16` vs `Macro_RP_Canasta` (`06–26`)**: `{info['corr_m_long_06_26']['Carril2_Sell16']['Macro_RP_Canasta']}` (`21–26`: `{info['corr_m_21_26']['Carril2_Sell16']['Macro_RP_Canasta']}`).",
        "",
        "## 2. Frentes `2021–2026-09` (`51m DR`, `@10% vol`) y Estrés `CME 0.5x`",
        "| Cartera / Frente | Sesgo CME | `DESC Sh` | `REP Sh` | `DR Sh / t` | `MDD@10%` | `Calmar@10%` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k in ["CME_TRZV", "Carril2_Sell16", "Macro_RP_Canasta", "Cripto_v3_Canasta", "Global_VolComp_M1DK", "Super_v3_Clean63m_EQ_21_26", "Super_v3_NoCME_EQ", "Super_v3_NoCME_HRP", "Super_v3_Core_TRZV_EQ", "Super_v3_Core_TRZV_HRP"]:
        v = s21[k]
        tag = "Sí (`upstream`)" if v["upstream_selection_caveat"] else "**NO (Limpio)**"
        md.append(f"| `{k}` | {tag} | `{v['DESC']['sharpe']}` | `{v['REP']['sharpe']}` | **`{v['DESC_REP']['sharpe']} / {v['DESC_REP']['t']}`** | `{v['DESC_REP']['mdd_at_10pct_vol']}%` | `{v['DESC_REP']['calmar_at_10pct_vol']}` |")

    md += [
        "",
        "## 3. Potencia Teórica Conjunta sobre `HOLDOUT A5` Sellado (sin abrir holdouts)",
        "| Bloque / Pool | Meses `DR` | `SR_DR` | `N_sellado` | Pot. `0.5x` | Pot. `0.7x` | Pot. `1.0x` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for pk, pv in info["pooled_pwr"].items():
        md.append(f"| `{pk}` | `{pv['meses_DR']}` | `{pv['sr_DR']}` | `{pv['n_holdout_sellado']}` | `{pv['pot_05x']}` | `{pv['pot_07x']}` | `{pv['pot_10x']}` |")

    if k_res:
        md += ["", "## 4. Kaggle CSCV (`12,870` splits), Bootstrap 20k Semanal y Bayes"]
        for ck, cv in k_res["cscv"].items():
            md.append(f"- **`{ck}`** (`{cv['tag']}`, `T={cv['T_months']}m`, `K={cv['K_strategies']}`): `PBO={cv['PBO']}`, `best OOS={cv['best_OOS_SR_med']}`, **`1/N OOS Sh med={cv['basket_1N_OOS_SR_med']}` (`P>0={cv['basket_1N_P_pos']}`)**.")
        md.append("")
        md.append("| Cartera (`Boot 20k @ 10% vol`) | `SR 1y p50` | `P(año>0)` | `MDD p50` | `MDD p95` | `Calmar p50` | `Bayes P(>0.5)` | `DSR(N=5000)` |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for c in ["Carril2_Sell16_06_26", "Macro_RP_Canasta_06_26", "Super_v3_Clean63m_EQ", "Super_v3_Clean63m_HRP", "Super_v3_NoCME_EQ", "Super_v3_NoCME_HRP", "Super_v3_Core_TRZV_EQ", "Super_v3_Core_TRZV_HRP", "CME_TRZV"]:
            bt, eb, ds = k_res["boot_20k"][c], k_res["bayes"][c], k_res["dsr"][c]["N_5000"]["dsr"]
            md.append(f"| `{c}` | `{bt['sr_1y_p50']}` | `{bt['P_yr_pos']:.1%}` | `{bt['mdd_p50']}%` | `{bt['mdd_p95']}%` | `{bt['calmar_p50']}` | `{eb['P_gt_05']}` | `{ds}` |")

    md += [
        "",
        "Diagnóstico de grilla: sin grilla paramétrica (`CSCV` sobre `K` mecanismos ya fijados en `Clean Long`, `NoCME` y `CME`). `HRP` muestral regularizado (`0.85*S + 0.15*diag`) produce pesos distintos de `1/N` cuando difiere la covarianza entre frentes.",
        f"Episodios: en `2006–2026-09`, `Super_v3_Clean63m_EQ` (`Carril 2 + Macro_RP`) logra `DR Sh={ls['Super_v3_Clean63m_EQ']['DESC_REP']['sharpe']}` (`DESC={ls['Super_v3_Clean63m_EQ']['DESC']['sharpe']}`, `REP={ls['Super_v3_Clean63m_EQ']['REP']['sharpe']}`) y `Boot 20k P(año>0)={k_res['boot_20k']['Super_v3_Clean63m_EQ']['P_yr_pos']:.1%}`." if k_res else "Episodios: pendiente salida de Kaggle.",
        "",
        "- **Aporte al referente**: separa un pozo limpio `63m` verdaderamente libre de sesgo CME y de iteración de `REP` (`Carril 2 + MACRO_RISK_PREMIA`) y corrige `HRP` frente a `LedoitWolf = I`.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args()
    exigir_contada("docs/research/supercartera_v3_20261127/PREREGISTRO.md")
    uni = load_v3_universe()
    info = build_v3_analysis(uni)

    print("\n=== BLOQUE A: POZO LIMPIO 63m CERO-ITERACION (2006-2026-09 DR) ===")
    for k, v in info["long_stats_06_26"].items():
        print(f"  {k:30s} | DESC={v['DESC']['sharpe']:5.3f} | REP={v['REP']['sharpe']:5.3f} | DR Sh={v['DESC_REP']['sharpe']:5.3f} t={v['DESC_REP']['t']:4.2f} | MDD={v['DESC_REP']['mdd_at_10pct_vol']:6.2f}% | Cal={v['DESC_REP']['calmar_at_10pct_vol']:4.2f}")
    print("  HRP weights:", info["hrp_63m_weights"], info["hrp_nocme_weights"], info["hrp_core_trzv_weights"])
    print("\n=== BLOQUE B: 2021-2026 DR ===")
    for k, v in info["stats_21_26"].items():
        print(f"  {k:34s} | DR Sh={v['DESC_REP']['sharpe']:5.3f} t={v['DESC_REP']['t']:4.2f} | REP={v['REP']['sharpe']:5.3f} | MDD={v['DESC_REP']['mdd_at_10pct_vol']:6.2f}% | Cal={v['DESC_REP']['calmar_at_10pct_vol']:4.2f}")
    print("\n=== POTENCIA POOLS SELLADOS ===")
    for k, v in info["pooled_pwr"].items():
        print(" ", k, v)

    if args.prepare or not args.finalize:
        write_kaggle_kernel_v3(info)
    kf = OUT / "KAGGLE_SUPER_V3_RESUMEN.json"
    if args.finalize:
        write_summary_v3(info, json.loads(kf.read_text(encoding="utf-8")) if kf.exists() else None)


if __name__ == "__main__":
    main()
