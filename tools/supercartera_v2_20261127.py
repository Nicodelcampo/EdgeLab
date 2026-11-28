#!/usr/bin/env python3
"""SUPERCARTERA v2: Integracion Multi-Frente Ortogonal + Kernel Kaggle CSCV/DSR/Bayes/Boot20k.

Frentes integrados (ESTRICTAMENTE DESC + REP < 2026-10-01; CERO lectura de HOLDOUT A5):
  1. CME_TRZV & CME_Div10 (descriptivos, upstream_selection_caveat=True)
  2. Carril2_Sell16 (limpio 06-26)
  3. Cripto_v3_Canasta (CRIPTO-PIT v3: XSMOM + BetaNeut + BAB_LowVol, 21-26)
     + diagnostico limpio 2-sleeves Cripto_v3_XSMOM_BAB (XSMOM + BAB sin BetaNeut)
  4. Global_VolComp_M1DK (F-COMPRESION-VOL-CRECE en DAX, EuroStoxx, FTSE, Nikkei, Oro, 14-26)
  5. Diagnostico FundedSync_O_1MNQ (qty=1 fijo, 18-26; marcado upstream_selection_caveat=True)

Uso:
  python -u tools/supercartera_v2_20261127.py --prepare
  python -u tools/supercartera_v2_20261127.py --finalize
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
    from sklearn.covariance import LedoitWolf
except ImportError:
    leaves_list = linkage = squareform = LedoitWolf = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import a5_bloque, a5_meses  # noqa: E402
from registro_global import exigir_contada  # noqa: E402
from marco_sin_forward import stats_monthly_10vol  # noqa: E402  (misma función; test_existente prohíbe copiarla)

OUT = ROOT / "docs/research/supercartera_v2_20261127"
OUT.mkdir(parents=True, exist_ok=True)
KDIR = OUT / "kaggle_super_v2"
KDIR.mkdir(parents=True, exist_ok=True)

GVC_ACTIVE_COLS = [
    "C2_VZ_DAX", "C2_EVRP_DAX", "C2_VZ_EuroStoxx", "C2_VZ_FTSE",
    "C2_VZ_Nikkei", "C2_EVRP_Nikkei", "C2_EVRP_Oro",
]


def _a5_mes_blq(p: pd.Period) -> str:
    return "TERMINAL" if p >= pd.Period("2026-10", "M") else a5_meses(int(p.year))[int(p.month)]


def _phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def _hrp_weights(ret: pd.DataFrame) -> np.ndarray:
    arr = ret.fillna(0.0).to_numpy(float)
    if LedoitWolf is None or leaves_list is None or arr.shape[1] < 2 or len(arr) < 12:
        sd = ret.std(ddof=1).replace(0.0, np.nan).fillna(1.0).to_numpy()
        w = 1.0 / sd
        return w / w.sum()
    cov = LedoitWolf().fit(arr).covariance_
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

        def v_c(ix):
            cc = cov[np.ix_(ix, ix)]
            iv = 1.0 / np.clip(np.diag(cc), 1e-8, None)
            iv /= iv.sum()
            return float(iv @ cc @ iv)

        va, vb = v_c(a), v_c(b)
        al = 1.0 - va / (va + vb) if (va + vb) > 0 else 0.5
        w[a] *= al
        w[b] *= 1.0 - al
        clusters += [a, b]
    return w / w.sum()


def _map_crypto_intra_month(cr_valid: pd.DataFrame, bidx_long: pd.DatetimeIndex, mask_dr_long: pd.Series) -> pd.DataFrame:
    """Mapea retornos 7d de cripto al dia habil mas cercano DENTRO DEL MISMO MES CALENDARIO (0 fuga entre bloques A5)."""
    valid_bdays = pd.Series(bidx_long, index=bidx_long)
    month_bdays = {m: grp.index for m, grp in valid_bdays.groupby(valid_bdays.index.to_period("M"))}
    mapped_dates, keep_idx = [], []
    for dt in cr_valid.index:
        cand = month_bdays.get(dt.to_period("M"))
        if cand is None or len(cand) == 0:
            continue
        pos = cand.searchsorted(dt, side="left")
        if pos >= len(cand):
            pos = len(cand) - 1
        mapped_dates.append(cand[pos])
        keep_idx.append(dt)
    cr_sub = cr_valid.loc[keep_idx].copy()
    cr_sub["__bday"] = mapped_dates
    out = pd.DataFrame(index=bidx_long)
    for col in cr_valid.columns:
        agg = cr_sub.groupby("__bday")[col].sum().reindex(bidx_long).fillna(0.0)
        out[col] = np.where(mask_dr_long, agg, np.nan)
    return out


def load_all_fronts() -> dict:
    bidx_long = pd.bdate_range("2006-01-01", "2026-09-29")
    blq_long = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in bidx_long], index=bidx_long)
    assert not blq_long.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr_long = blq_long.isin(["DESC", "REP"])

    # ---- CME Intradia ----
    sd_raw = pd.read_csv(ROOT / "docs/research/estabilidad_cartera_20261126/SERIES_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    sd_raw = sd_raw[sd_raw.index < "2026-10-01"]
    intra8_cols = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]
    trzv_cols = ["T_NQ", "R_NQ", "Z_NQ", "V_NQ"]

    arn = pd.read_csv(ROOT / "docs/research/preset_diversificada_20261127/ARNES_N_NQ.csv.gz")
    arn = arn[arn["fecha_int"] < 20261001].copy()
    arn["dia"] = pd.to_datetime(arn["fecha_int"].astype(str))
    arn["usd_1m"] = (arn["pnl_pts"] - 1.9775) * 2.0
    n_s = arn.groupby("dia")["usd_1m"].sum().reindex(sd_raw.index, fill_value=0.0)

    exp_d = pd.read_csv(ROOT / "docs/research/auditoria_cartera_20261126/SERIES_EXPANDIDAS_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    som_eod = exp_d["SOM_eod_NQ"].reindex(sd_raw.index, fill_value=0.0)

    cme_intra8 = sd_raw[intra8_cols].sum(axis=1)
    cme_div10 = cme_intra8 + n_s + som_eod
    cme_trzv = sd_raw[trzv_cols].sum(axis=1)

    cme_ind = pd.DataFrame(index=bidx_long)
    for c in intra8_cols:
        cme_ind[f"CME_{c}"] = np.where(mask_dr_long, sd_raw[c].reindex(bidx_long), np.nan)
    cme_ind["CME_N_NQ"] = np.where(mask_dr_long, n_s.reindex(bidx_long), np.nan)
    cme_ind["CME_SOM_eod"] = np.where(mask_dr_long, som_eod.reindex(bidx_long), np.nan)

    # ---- Carril 2 Swing (DESC + REP, CERO HOLDOUT) ----
    c2_raw = pd.concat([pd.read_csv(ROOT / f"docs/research/carril2_extension_20261126/OPS_LOTE{k}.csv.gz") for k in (1, 2)], ignore_index=True)
    c2_raw = c2_raw[~c2_raw["definicion"].str.endswith("N") & (c2_raw["fecha"] < 20261001)].copy()
    c2_raw["blq"] = [a5_bloque(int(x)) for x in c2_raw["fecha"]]
    c2_raw = c2_raw[c2_raw["blq"].isin(["DESC", "REP"])].copy()
    c2_raw["dia"] = pd.to_datetime(c2_raw["fecha"].astype(str))
    c2_raw["k"] = c2_raw["definicion"] + "_" + c2_raw["inst"]
    c2_piv = c2_raw.pivot_table(index="dia", columns="k", values="R", aggfunc="sum").fillna(0.0)
    pesos_c2 = json.loads((ROOT / "docs/research/canasta_amplia_20261127/PESOS_CARRIL2_SELLADA.json").read_text(encoding="utf-8"))
    c2_cols = [c for c in pesos_c2 if c in c2_piv.columns]
    c2_16_df = c2_piv[c2_cols].reindex(bidx_long, fill_value=0.0).where(mask_dr_long, np.nan)
    c2_sellada = (c2_piv[c2_cols].reindex(bidx_long, fill_value=0.0) * pd.Series(pesos_c2)).sum(axis=1)

    # ---- Cripto PIT v3 (226 coins + basis + BAB, DESC+REP intra-month mapped) ----
    cr3_raw = pd.read_csv(ROOT / "docs/research/cripto_pit_v3_20261127/SERIES_CRIPTO_PIT_V3_DR.csv.gz", index_col=0, parse_dates=True)
    cr3_valid = cr3_raw.dropna(subset=["CR3_Canasta_InvVol"])
    cr3_mapped = _map_crypto_intra_month(cr3_valid, bidx_long, mask_dr_long)

    # Clean 2-sleeve diagnostic (XSMOM_21d + BAB_LowVol inv-vol DESC, dropping 0.947 redundant BetaNeut)
    cr3_m_21 = cr3_mapped[["CR3_XSMOM_21d_Stag5d", "CR3_BAB_LowVol_Stag5d"]].loc[mask_dr_long & (bidx_long >= "2021-01-01")]
    m_cr2_d = cr3_m_21[blq_long.reindex(cr3_m_21.index) == "DESC"].groupby(lambda d: d.to_period("M")).sum()
    sd_cr2 = m_cr2_d.std(ddof=1).replace(0.0, np.nan).fillna(1.0)
    w_cr2 = (1.0 / sd_cr2) / (1.0 / sd_cr2).sum()
    cr3_xsmom_bab = np.where(mask_dr_long, (cr3_mapped[["CR3_XSMOM_21d_Stag5d", "CR3_BAB_LowVol_Stag5d"]].fillna(0.0) * w_cr2).sum(axis=1), np.nan)

    cr3_ind_cols = ["CR3_XSMOM_21d_Stag5d", "CR3_XSMOM_BetaNeut_Stag5d", "CR3_Basis_Carry_Stag5d", "CR3_BAB_LowVol_Stag5d", "CR3_ResidMom_21d_2F_Stag5d"]
    cr3_ind = cr3_mapped[cr3_ind_cols].copy()

    # ---- Frentes Ortogonales: Global VolComp M1DK + FundedSync O qty=1 ----
    fo_raw = pd.read_csv(ROOT / "docs/research/frentes_ortogonales_20261127/SERIES_FRENTES_ORTOGONALES_DR.csv.gz", index_col=0, parse_dates=True)
    gvc_ind = fo_raw[GVC_ACTIVE_COLS].reindex(bidx_long).where(mask_dr_long, np.nan)
    cme_ind["CME_FundedSync_O_1MNQ"] = np.where(mask_dr_long, fo_raw["FundedSync_O_1MNQ"].reindex(bidx_long).fillna(0.0), np.nan)

    daily_sleeves = pd.DataFrame(index=bidx_long)
    daily_sleeves["CME_TRZV"] = np.where(mask_dr_long, cme_trzv.reindex(bidx_long), np.nan)
    daily_sleeves["CME_Div10"] = np.where(mask_dr_long, cme_div10.reindex(bidx_long), np.nan)
    daily_sleeves["Carril2_Sell16"] = np.where(mask_dr_long, c2_sellada, np.nan)
    daily_sleeves["Global_VolComp_M1DK"] = np.where(mask_dr_long, fo_raw["Global_VolComp_M1DK"].reindex(bidx_long), np.nan)
    daily_sleeves["Cripto_v3_Canasta"] = cr3_mapped["CR3_Canasta_InvVol"]
    daily_sleeves["Cripto_v3_XSMOM_BAB"] = cr3_xsmom_bab
    daily_sleeves["FundedSync_O_1MNQ"] = np.where(mask_dr_long, fo_raw["FundedSync_O_1MNQ"].reindex(bidx_long), np.nan)

    return {
        "bidx_long": bidx_long,
        "blq_long": blq_long,
        "mask_dr_long": mask_dr_long,
        "daily_sleeves": daily_sleeves,
        "c2_16_df": c2_16_df,
        "cr3_ind": cr3_ind,
        "gvc_ind": gvc_ind,
        "cme_ind": cme_ind,
        "w_cr2_xsmom_bab": {k: round(float(v), 4) for k, v in w_cr2.items()},
    }


def compute_pooled_holdout_power(daily_sleeves: pd.DataFrame) -> dict:
    """Potencia teorica conjunta SIN abrir ningun HOLDOUT A5."""
    def _n_sealed(p_start: str) -> int:
        return sum(1 for p in pd.period_range(p_start, "2026-09", freq="M") if _a5_mes_blq(p) == "HOLDOUT")

    def _pwr(m_s: pd.Series, n_sealed: int) -> dict:
        m = m_s.dropna()
        if len(m) < 6 or float(m.std(ddof=1)) == 0.0:
            return {"sr_dr": 0.0}
        sr = float(m.mean() / m.std(ddof=1) * np.sqrt(12.0))
        return {
            "meses_DESC_REP": int(len(m)),
            "sr_anual_DR": round(sr, 3),
            "n_holdout_sellado": int(n_sealed),
            "potencia_sh05": round(_phi(sqrt(n_sealed / 12.0) * (0.5 * sr) - 1.6448536), 3),
            "potencia_sh07": round(_phi(sqrt(n_sealed / 12.0) * (0.7 * sr) - 1.6448536), 3),
            "potencia_sh10": round(_phi(sqrt(n_sealed / 12.0) * sr - 1.6448536), 3),
        }

    m_all = daily_sleeves.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1)
    blq_m = pd.Series([_a5_mes_blq(p) for p in m_all.index], index=m_all.index)
    m_all = m_all[blq_m.isin(["DESC", "REP"])]
    blq_m = blq_m[blq_m.isin(["DESC", "REP"])]

    def _std_desc(col: str, p0: str | None = None) -> pd.Series:
        s = m_all[col].dropna()
        if p0:
            s = s[s.index >= p0]
        sd = float(s[blq_m.reindex(s.index) == "DESC"].std(ddof=1))
        return s / (sd if sd > 0 else 1.0)

    c2_06 = _std_desc("Carril2_Sell16")
    c2_21 = _std_desc("Carril2_Sell16", "2021-01")
    gvc_14 = _std_desc("Global_VolComp_M1DK", "2014-07")
    gvc_21 = _std_desc("Global_VolComp_M1DK", "2021-01")
    cr3_21 = _std_desc("Cripto_v3_Canasta", "2021-01")

    pool_nocme_21 = pd.concat([c2_21, gvc_21, cr3_21], axis=1).mean(axis=1)
    pool_nocme_dyn = pd.concat([c2_06, gvc_14, cr3_21], axis=1).mean(axis=1)
    pool_c2_cr3_21 = pd.concat([c2_21, cr3_21], axis=1).mean(axis=1)

    return {
        "1_Carril2_Sell16_06_26": _pwr(c2_06, _n_sealed("2006-01")),
        "2_Global_VolComp_M1DK_14_26": _pwr(gvc_14, _n_sealed("2014-07")),
        "3_Cripto_v3_Canasta_21_26": _pwr(cr3_21, _n_sealed("2021-01")),
        "4_Pooled_C2_plus_Cripto_v3_21_26": _pwr(pool_c2_cr3_21, _n_sealed("2021-01")),
        "5_Pooled_NoCME_3F_21_26": _pwr(pool_nocme_21, _n_sealed("2021-01")),
        "6_Pooled_NoCME_3F_Dyn_06_26": _pwr(pool_nocme_dyn, _n_sealed("2006-01")),
    }


def compute_shrinkage_stress(fronts_m: pd.DataFrame) -> dict:
    res = {}
    for cme_sh, oth_sh in [(1.0, 1.0), (0.5, 0.7), (0.5, 0.5)]:
        lbl = f"CME_{cme_sh}x__Oth_{oth_sh}x"
        adj = fronts_m.copy()
        for c in ("CME_TRZV", "CME_Div10", "FundedSync_O_1MNQ"):
            if c in adj:
                adj[c] = adj[c] - (1.0 - cme_sh) * float(adj[c].mean())
        for c in ("Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"):
            if c in adj:
                adj[c] = adj[c] - (1.0 - oth_sh) * float(adj[c].mean())
        p_adj = {
            "CME_TRZV": adj["CME_TRZV"],
            "CME_Div10": adj["CME_Div10"],
            "Super_v2_NoCME_EQ": adj[["Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]].mean(axis=1),
            "Super_v2_EQ": adj[["CME_Div10", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]].mean(axis=1),
            "Super_v2_Core_TRZV_EQ": adj[["CME_TRZV", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]].mean(axis=1),
        }
        res[lbl] = {k: stats_monthly_10vol(v) for k, v in p_adj.items()}
    return res


def generate_kaggle_kernel(m_c2: pd.DataFrame, m_nocme: pd.DataFrame, m_all: pd.DataFrame, w_port: pd.DataFrame, m_port: pd.DataFrame, caveat_map: dict) -> None:
    payload = {
        "c2_cols": list(m_c2.columns), "c2_vals": np.round(m_c2.to_numpy(float), 4).tolist(),
        "nc_cols": list(m_nocme.columns), "nc_vals": np.round(m_nocme.to_numpy(float), 4).tolist(),
        "al_cols": list(m_all.columns), "al_vals": np.round(m_all.to_numpy(float), 4).tolist(),
        "wb_cols": list(w_port.columns), "wb_vals": np.round(w_port.to_numpy(float), 4).tolist(),
        "pm_cols": list(m_port.columns), "pm_vals": np.round(m_port.to_numpy(float), 4).tolist(),
        "caveat_map": caveat_map,
    }
    b64 = base64.b64encode(gzip.compress(json.dumps(payload).encode("utf-8"))).decode("ascii")
    script = f'''#!/usr/bin/env python3
"""Kaggle Kernel: SUPERCARTERA v2 CSCV (S=16, 12870 splits) + DSR (N=1..5000) + Bayes + Boot 20k semanal @ 10% vol."""
import base64, gzip, itertools, json, os, time
from math import erf, sqrt
from pathlib import Path
import numpy as np
from numba import njit

PAYLOAD_B64 = "{b64}"
D = json.loads(gzip.decompress(base64.b64decode(PAYLOAD_B64)).decode("utf-8"))


def phi(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def dsr_prob(ret_m, n_trials):
    ret_m = ret_m[np.isfinite(ret_m)]
    T = len(ret_m)
    if T < 6 or np.std(ret_m, ddof=1) == 0:
        return {{"sr_anual": 0.0, "dsr": 0.0}}
    sr_m = float(np.mean(ret_m) / np.std(ret_m, ddof=1))
    sr_ann = sr_m * sqrt(12.0)
    z = (ret_m - np.mean(ret_m)) / np.std(ret_m, ddof=1)
    skew, kurt = float(np.mean(z ** 3)), float(np.mean(z ** 4))
    if n_trials <= 1:
        sr0_m = 0.0
    else:
        euler_g = 0.5772156649
        def inv_phi(p):
            lo, hi = -6.0, 6.0
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                if phi(mid) < p: lo = mid
                else: hi = mid
            return 0.5 * (lo + hi)
        z1 = inv_phi(1.0 - 1.0 / n_trials)
        z2 = inv_phi(1.0 - 1.0 / (n_trials * np.e))
        sr0_m = ((1.0 - euler_g) * z1 + euler_g * z2) / sqrt(T)
    denom = sqrt(max(1e-8, 1.0 - skew * sr_m + ((kurt - 1.0) / 4.0) * (sr_m ** 2)))
    return {{"sr_anual": round(sr_ann, 3), "skew": round(skew, 3), "kurt": round(kurt, 3), "dsr": round(phi((sr_m - sr0_m) * sqrt(T - 1.0) / denom), 4)}}


def run_cscv(mat_m, S=16, tag="CLEAN"):
    T, K = mat_m.shape
    blk_len = T // S
    usable = blk_len * S
    mat = mat_m[:usable]
    blocks = [mat[i * blk_len : (i + 1) * blk_len] for i in range(S)]
    all_idx = set(range(S))
    logits, oos_best, oos_ew, is_best = [], [], [], []
    for comb in itertools.combinations(range(S), S // 2):
        oos_idx = sorted(all_idx - set(comb))
        IS = np.vstack([blocks[i] for i in comb])
        OOS = np.vstack([blocks[i] for i in oos_idx])
        sd_is = np.std(IS, axis=0, ddof=1)
        sr_is = np.where(sd_is > 1e-9, np.mean(IS, axis=0) / sd_is, 0.0) * sqrt(12.0)
        sd_oos = np.std(OOS, axis=0, ddof=1)
        sr_oos = np.where(sd_oos > 1e-9, np.mean(OOS, axis=0) / sd_oos, 0.0) * sqrt(12.0)
        ns = int(np.argmax(sr_is))
        is_best.append(float(sr_is[ns]))
        oos_best.append(float(sr_oos[ns]))
        rk = min(max(float(np.sum(sr_oos <= sr_oos[ns])) / (K + 1.0), 1.0 / (K + 1.0)), K / (K + 1.0))
        logits.append(float(np.log(rk / (1.0 - rk))))
        ew = np.mean(OOS / np.where(sd_is > 1e-9, sd_is, 1.0), axis=1)
        oos_ew.append(float(np.mean(ew) / max(np.std(ew, ddof=1), 1e-9) * sqrt(12.0)))
    lg, ob, oe = np.asarray(logits), np.asarray(oos_best), np.asarray(oos_ew)
    return {{
        "tag": tag, "n_splits": len(logits), "T_months_used": usable, "K_strategies": K,
        "PBO_prob_overfit": round(float(np.mean(lg <= 0.0)), 4),
        "best_single_IS_SR_median": round(float(np.median(is_best)), 3),
        "best_single_OOS_SR_median": round(float(np.median(ob)), 3),
        "best_single_P_OOS_pos": round(float(np.mean(ob > 0.0)), 4),
        "basket_1N_OOS_SR_median": round(float(np.median(oe)), 3),
        "basket_1N_OOS_SR_p10": round(float(np.percentile(oe, 10)), 3),
        "basket_1N_P_OOS_pos": round(float(np.mean(oe > 0.0)), 4),
        "basket_1N_P_OOS_gt_05": round(float(np.mean(oe > 0.5)), 4),
        "basket_1N_P_OOS_gt_10": round(float(np.mean(oe > 1.0)), 4),
    }}


@njit
def boot_20k(y_w_10pct, n_paths, block_len, seed):
    L = len(y_w_10pct)
    srs, rets, mdds = np.zeros(n_paths), np.zeros(n_paths), np.zeros(n_paths)
    for k in range(n_paths):
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        pos, rem, eq, pk, mdd, sy, sy2 = 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0
        for _ in range(52):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = block_len
            idx = (pos + (block_len - rem)) % L
            rem -= 1
            val = y_w_10pct[idx]
            sy += val; sy2 += val * val; eq += val
            if eq > pk: pk = eq
            if eq - pk < mdd: mdd = eq - pk
        mu = sy / 52.0
        var = max(1e-12, (sy2 / 52.0) - mu * mu)
        srs[k] = (mu / sqrt(var)) * sqrt(52.0)
        rets[k] = eq; mdds[k] = mdd
    return srs, rets, mdds


def emp_bayes(sr_obs, T_m, caveat, prior_mu=0.0, prior_sd=0.65):
    se = sqrt(12.0 / max(1, T_m))
    pv = 1.0 / (1.0 / (prior_sd ** 2) + 1.0 / (se ** 2))
    pm = pv * (prior_mu / (prior_sd ** 2) + sr_obs / (se ** 2))
    ps = sqrt(pv)
    return {{
        "sr_obs": round(sr_obs, 3), "T_months": int(T_m), "upstream_selection_caveat": bool(caveat),
        "post_mean": round(pm, 3), "post_sd": round(ps, 3),
        "P_true_gt_0": round(1.0 - phi((0.0 - pm) / ps), 4),
        "P_true_gt_05": round(1.0 - phi((0.5 - pm) / ps), 4),
        "P_true_gt_10": round(1.0 - phi((1.0 - pm) / ps), 4),
    }}


def main():
    t0 = time.time()
    cscv_out = {{
        "1_clean_carril2_16rules": run_cscv(np.asarray(D["c2_vals"], dtype=np.float64), S=16, tag="LIMPIO_SIN_CME"),
        "2_clean_non_cme_28rules": run_cscv(np.asarray(D["nc_vals"], dtype=np.float64), S=16, tag="LIMPIO_SIN_CME"),
        "3_descriptive_with_cme": run_cscv(np.asarray(D["al_vals"], dtype=np.float64), S=16, tag="DESCRIPTIVO_SESGO_VENDEDOR_CME"),
    }}
    pm = np.asarray(D["pm_vals"], dtype=np.float64)
    wb = np.asarray(D["wb_vals"], dtype=np.float64)
    cav = D["caveat_map"]
    dsr_out, eb_out, boot_out = {{}}, {{}}, {{}}
    for j, cname in enumerate(D["pm_cols"]):
        cv = pm[:, j]; cv = cv[np.isfinite(cv)]
        dsr_out[cname] = {{f"N_{{nt}}": dsr_prob(cv, nt) for nt in (1, 10, 50, 200, 500, 5000)}}
        dsr_out[cname]["upstream_selection_caveat"] = bool(cav.get(cname, True))
        sr_obs = float(np.mean(cv) / max(np.std(cv, ddof=1), 1e-9) * sqrt(12.0))
        eb_out[cname] = emp_bayes(sr_obs, len(cv), cav.get(cname, True))
    for j, cname in enumerate(D["wb_cols"]):
        yw = wb[:, j]; yw = yw[np.isfinite(yw)]
        sd_w = float(np.std(yw, ddof=1))
        yw_10 = yw / (sd_w * sqrt(52.0)) * 10.0 if sd_w > 0 else yw
        srs, rets, mdds = boot_20k(yw_10, 20000, 4, 202611 + j)
        boot_out[cname] = {{
            "weeks": len(yw), "target_ann_vol_pct": 10.0, "upstream_selection_caveat": bool(cav.get(cname, True)),
            "sr_1yr_p50": round(float(np.median(srs)), 3), "sr_1yr_p10": round(float(np.percentile(srs, 10)), 3),
            "P_yr_pos": round(float(np.mean(rets > 0.0)), 4),
            "ret_1yr_p50_pct": round(float(np.median(rets)), 2),
            "mdd_p50_pct": round(float(np.median(mdds)), 2), "mdd_p95_pct": round(float(np.percentile(mdds, 5)), 2),
            "calmar_median": round(float(np.median(rets) / max(abs(np.median(mdds)), 1e-6)), 2),
        }}
    res = {{"elapsed_s": round(time.time() - t0, 2), "cscv": cscv_out, "dsr_by_trials": dsr_out, "empirical_bayes": eb_out, "bootstrap_20k_weekly_10pct_vol": boot_out}}
    out_p = Path("/kaggle/working/KAGGLE_SUPER_V2_RESUMEN.json") if os.path.isdir("/kaggle/working") else Path("KAGGLE_SUPER_V2_RESUMEN.json")
    out_p.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"DONE SUPER_V2 KAGGLE in {{time.time() - t0:.1f}}s", flush=True)


if __name__ == "__main__":
    main()
'''
    (KDIR / "kaggle_super_v2.py").write_text(script, encoding="utf-8")
    meta = {
        "id": "nicolasbuttaro/edgelab-supercartera-v2-20261127",
        "title": "edgelab-supercartera-v2-20261127",
        "code_file": "kaggle_super_v2.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (KDIR / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Generated Kaggle kernel:", KDIR / "kaggle_super_v2.py", f"({len(script)//1024} KB)")


def build_data() -> dict:
    loaded = load_all_fronts()
    blq = loaded["blq_long"]
    dr = loaded["mask_dr_long"]
    daily_sl = loaded["daily_sleeves"]
    idx = daily_sl.index

    m_all = daily_sl.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1)
    blq_m_all = pd.Series([_a5_mes_blq(p) for p in m_all.index], index=m_all.index)
    m_all = m_all[blq_m_all.isin(["DESC", "REP"])]
    blq_m_all = blq_m_all[blq_m_all.isin(["DESC", "REP"])]

    fronts_m21 = m_all.loc[m_all.index >= "2021-01"].dropna().copy()
    blq_m21 = blq_m_all.loc[fronts_m21.index]
    desc_m21 = blq_m21 == "DESC"
    sd_m_21 = {c: float(fronts_m21.loc[desc_m21, c].std(ddof=1)) for c in fronts_m21.columns}

    # Inv-vol DESC weights for diagnostic CME_TRZV + O
    sd_trzv_o = fronts_m21.loc[desc_m21, ["CME_TRZV", "FundedSync_O_1MNQ"]].std(ddof=1)
    w_trzv_o = (1.0 / sd_trzv_o) / (1.0 / sd_trzv_o).sum()

    # Weekly mapping strictly inside DESC+REP (zeros Monday spike!)
    d21 = daily_sl.loc[dr & (idx >= "2021-01-01"), list(fronts_m21.columns)].copy()
    d21_norm = d21 / pd.Series(sd_m_21)
    w21_norm = d21_norm.resample("W-FRI").sum(min_count=1).dropna(how="all")
    dr_periods = set(m_all.index)
    keep_w = [(pd.Period(d, "M") in dr_periods) and (pd.Period(d - pd.Timedelta(days=6), "M") in dr_periods) for d in w21_norm.index]
    w21_norm = w21_norm.loc[keep_w].fillna(0.0)
    blq_w21 = pd.Series([_a5_mes_blq(pd.Period(d, "M")) for d in w21_norm.index], index=w21_norm.index)

    cols_4f = ["CME_Div10", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]
    cols_nocme = ["Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]
    cols_trzv4 = ["CME_TRZV", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta"]
    cols_5f_o = ["CME_Div10", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "FundedSync_O_1MNQ"]

    w_hrp_4f = _hrp_weights(w21_norm.loc[blq_w21 == "DESC", cols_4f])
    w_hrp_nc = _hrp_weights(w21_norm.loc[blq_w21 == "DESC", cols_nocme])

    def _assemble(df_n: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({
            "CME_TRZV": df_n["CME_TRZV"],
            "CME_Div10": df_n["CME_Div10"],
            "Carril2_Sell16": df_n["Carril2_Sell16"],
            "Global_VolComp_M1DK": df_n["Global_VolComp_M1DK"],
            "Cripto_v3_Canasta": df_n["Cripto_v3_Canasta"],
            "Cripto_v3_XSMOM_BAB": df_n["Cripto_v3_XSMOM_BAB"],
            "FundedSync_O_1MNQ": df_n["FundedSync_O_1MNQ"],
            "CME_TRZV_plus_O": (df_n[["CME_TRZV", "FundedSync_O_1MNQ"]] * w_trzv_o.to_numpy()).sum(axis=1),
            "Super_v2_NoCME_EQ": df_n[cols_nocme].mean(axis=1),
            "Super_v2_NoCME_HRP_Weekly": (df_n[cols_nocme] * w_hrp_nc).sum(axis=1),
            "Super_v2_EQ": df_n[cols_4f].mean(axis=1),
            "Super_v2_HRP_Weekly": (df_n[cols_4f] * w_hrp_4f).sum(axis=1),
            "Super_v2_Core_TRZV_EQ": df_n[cols_trzv4].mean(axis=1),
            "Super_v2_5F_with_O": df_n[cols_5f_o].mean(axis=1),
        })

    w_port = _assemble(w21_norm)
    m21_norm = fronts_m21 / pd.Series(sd_m_21)
    m_port = _assemble(m21_norm)

    caveat_map = {
        "CME_TRZV": True, "CME_Div10": True, "FundedSync_O_1MNQ": True,
        "CME_TRZV_plus_O": True, "Super_v2_EQ": True, "Super_v2_HRP_Weekly": True,
        "Super_v2_Core_TRZV_EQ": True, "Super_v2_5F_with_O": True,
        "Carril2_Sell16": False, "Global_VolComp_M1DK": False,
        "Cripto_v3_Canasta": False, "Cripto_v3_XSMOM_BAB": False,
        "Super_v2_NoCME_EQ": False, "Super_v2_NoCME_HRP_Weekly": False,
    }

    front_stats = {}
    for col in m_port.columns:
        sm = m_port[col]
        bm = blq_m21.reindex(sm.index)
        front_stats[col] = {
            "upstream_selection_caveat": caveat_map[col],
            "DESC": stats_monthly_10vol(sm[bm == "DESC"]),
            "REP": stats_monthly_10vol(sm[bm == "REP"]),
            "DESC_REP": stats_monthly_10vol(sm),
        }

    corr_cols = ["CME_TRZV", "CME_Div10", "FundedSync_O_1MNQ", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "Cripto_v3_XSMOM_BAB"]
    corr_m = m_port[corr_cols].corr().round(3).to_dict()
    corr_w = w_port[corr_cols].corr().round(3).to_dict()

    pooled_pwr = compute_pooled_holdout_power(daily_sl)
    stress = compute_shrinkage_stress(m21_norm)

    # 3 CSCV matrices (strictly DESC+REP, no HOLDOUT!)
    c2_16_m = loaded["c2_16_df"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    c2_blq = pd.Series([_a5_mes_blq(p) for p in c2_16_m.index], index=c2_16_m.index)
    c2_16_m = c2_16_m[c2_blq.isin(["DESC", "REP"])].fillna(0.0)

    c2_21_m = c2_16_m.loc[c2_16_m.index >= "2021-01"]
    cr3_ind_m = loaded["cr3_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    gvc_ind_m = loaded["gvc_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    m_non_cme_28 = pd.concat([c2_21_m, cr3_ind_m.reindex(c2_21_m.index), gvc_ind_m.reindex(c2_21_m.index)], axis=1).fillna(0.0)
    m_non_cme_28 = m_non_cme_28.loc[:, m_non_cme_28.std(ddof=1) > 1e-8]

    cme_ind_m = loaded["cme_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    cme_ind_m = cme_ind_m.loc[cme_ind_m.index >= "2021-01"]
    m_all_39 = pd.concat([cme_ind_m.reindex(c2_21_m.index), m_non_cme_28], axis=1).fillna(0.0)
    m_all_39 = m_all_39.loc[:, m_all_39.std(ddof=1) > 1e-8]

    d21_save = _assemble(d21_norm)
    d21_save.loc[~blq.reindex(d21_save.index).isin(["DESC", "REP"])] = np.nan
    d21_save.to_csv(OUT / "SERIES_SUPERCARTERA_V2_DR.csv.gz")

    return {
        "loaded": loaded, "front_stats": front_stats, "corr_m": corr_m, "corr_w": corr_w,
        "hrp_4f": {c: round(float(v), 4) for c, v in zip(cols_4f, w_hrp_4f)},
        "hrp_nocme": {c: round(float(v), 4) for c, v in zip(cols_nocme, w_hrp_nc)},
        "w_trzv_o": {k: round(float(v), 4) for k, v in w_trzv_o.items()},
        "pooled_pwr": pooled_pwr, "stress": stress, "caveat_map": caveat_map,
        "c2_16_m": c2_16_m, "m_non_cme_28": m_non_cme_28, "m_all_39": m_all_39,
        "w_port": w_port, "m_port": m_port,
    }


def write_summary(info: dict, k_res: dict | None) -> None:
    out = {
        "hrp_weights_weekly_4f_DESC": info["hrp_4f"],
        "hrp_weights_weekly_nocme_DESC": info["hrp_nocme"],
        "w_cr2_xsmom_bab_DESC": info["loaded"]["w_cr2_xsmom_bab"],
        "w_trzv_plus_o_DESC": info["w_trzv_o"],
        "corr_monthly_21_26_DR": info["corr_m"],
        "corr_weekly_21_26_DR": info["corr_w"],
        "front_and_super_stats_10pct_vol": info["front_stats"],
        "shrinkage_stress_10pct_vol": info["stress"],
        "pooled_sealed_holdout_power": info["pooled_pwr"],
        "cscv_shapes": {
            "clean_carril2_16rules": list(info["c2_16_m"].shape),
            "clean_non_cme_28rules": list(info["m_non_cme_28"].shape),
            "descriptive_all": list(info["m_all_39"].shape),
        },
        "kaggle_summary": k_res,
    }
    (OUT / "SUPERCARTERA_V2.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    fs = info["front_stats"]
    md = [
        "# SUPERCARTERA v2: Integración Multi-Frente Ortogonal a Volatilidad Idéntica (`10%`) y CSCV/Bootstrap (resultado, 2026-11-27)",
        "",
        "Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**",
        "",
        "## 1. Desempeño a Volatilidad Idéntica (`10%` anual propia, `2021–2026-09 DESC+REP 51m`, `W-FRI`/`M`)",
        "| Cartera / Frente | Sesgo CME | `DESC (39m) Sh` | `REP (12m) Sh` | `DR (51m) Sh / t` | `Ret@10%` | `MDD@10%` | `Calmar@10%` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    order_show = [
        "CME_TRZV", "CME_Div10", "FundedSync_O_1MNQ", "CME_TRZV_plus_O",
        "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "Cripto_v3_XSMOM_BAB",
        "Super_v2_NoCME_EQ", "Super_v2_NoCME_HRP_Weekly", "Super_v2_EQ",
        "Super_v2_HRP_Weekly", "Super_v2_Core_TRZV_EQ", "Super_v2_5F_with_O",
    ]
    for k in order_show:
        v = fs[k]
        tag = "Sí (`upstream`)" if v["upstream_selection_caveat"] else "**NO (Limpio)**"
        d, r, dr = v["DESC"], v["REP"], v["DESC_REP"]
        md.append(
            f"| `{k}` | {tag} | `{d['sharpe']}` | `{r['sharpe']}` | **`{dr['sharpe']} / {dr['t']}`** | `+{dr['ret_ann_10pct_vol']}%` | `{dr['mdd_at_10pct_vol']}%` | `{dr['calmar_at_10pct_vol']}` |"
        )
    md += [
        "",
        f"- **Pesos HRP semanal (`DESC`) 4 frentes**: `{info['hrp_4f']}`; **3 frentes limpios (`NoCME`)**: `{info['hrp_nocme']}`.",
        f"- **Correlación mensual `Global_VolComp_M1DK` vs `Carril2_Sell16` (`21–26`)**: `{info['corr_m']['Global_VolComp_M1DK']['Carril2_Sell16']}` (semanal: `{info['corr_w']['Global_VolComp_M1DK']['Carril2_Sell16']}`).",
        "",
        "## 2. Estrés de Contracción (`CME 0.5x` vs `Otros 0.5x/0.7x`) a Igual `10%` Volatilidad",
        "| Escenario | `CME_TRZV Sh (Calmar)` | `Super_v2_NoCME_EQ Sh (Calmar)` | `Super_v2_EQ Sh (Calmar)` | `Super_v2_Core_TRZV_EQ Sh (Calmar)` |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for sc, sv in info["stress"].items():
        md.append(
            f"| `{sc}` | `{sv['CME_TRZV']['sharpe']} ({sv['CME_TRZV']['calmar_at_10pct_vol']})` | "
            f"`{sv['Super_v2_NoCME_EQ']['sharpe']} ({sv['Super_v2_NoCME_EQ']['calmar_at_10pct_vol']})` | "
            f"`{sv['Super_v2_EQ']['sharpe']} ({sv['Super_v2_EQ']['calmar_at_10pct_vol']})` | "
            f"`{sv['Super_v2_Core_TRZV_EQ']['sharpe']} ({sv['Super_v2_Core_TRZV_EQ']['calmar_at_10pct_vol']})` |"
        )
    md += [
        "",
        "## 3. Potencia Teórica Conjunta sobre `HOLDOUT A5` Sellado (sin abrir holdouts)",
        "| Bloque / Pool | Meses `DR` | `SR_DR` | `N_sellado` | Pot. `0.5x` | Pot. `0.7x` | Pot. `1.0x` |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for pk, pv in info["pooled_pwr"].items():
        md.append(
            f"| `{pk}` | `{pv['meses_DESC_REP']}` | `{pv['sr_anual_DR']}` | `{pv['n_holdout_sellado']}` | "
            f"`{pv['potencia_sh05']}` | `{pv['potencia_sh07']}` | `{pv['potencia_sh10']}` |"
        )

    if k_res:
        md += ["", "## 4. Resultados Kaggle: CSCV (`12,870` splits), DSR (`N=5000`), Bayes & Bootstrap 20k Semanal"]
        for ck, cv in k_res["cscv"].items():
            md.append(
                f"- **`{ck}`** (`{cv['tag']}`, `T={cv['T_months_used']}m`, `K={cv['K_strategies']}`): `PBO={cv['PBO_prob_overfit']}`, `1/N OOS Sh med={cv['basket_1N_OOS_SR_median']}` (`P>0={cv['basket_1N_P_OOS_pos']}`)."
            )
        md.append("")
        md.append("| Cartera (`Boot 20k semanal @ 10% vol`) | `SR 1y p50` | `P(año>0)` | `MDD p50` | `MDD p95` | `Calmar p50` | `Bayes P(>0.5)` | `DSR(N=5000)` |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
        for k in ["CME_TRZV", "Carril2_Sell16", "Global_VolComp_M1DK", "Cripto_v3_Canasta", "Super_v2_NoCME_EQ", "Super_v2_NoCME_HRP_Weekly", "Super_v2_EQ", "Super_v2_HRP_Weekly", "Super_v2_Core_TRZV_EQ"]:
            bt = k_res["bootstrap_20k_weekly_10pct_vol"][k]
            eb = k_res["empirical_bayes"][k]
            ds = k_res["dsr_by_trials"][k]["N_5000"]["dsr"]
            md.append(
                f"| `{k}` | `{bt['sr_1yr_p50']}` | `{bt['P_yr_pos']:.1%}` | `{bt['mdd_p50_pct']}%` | `{bt['mdd_p95_pct']}%` | `{bt['calmar_median']}` | `{eb['P_true_gt_05']}` | `{ds}` |"
            )

    md += [
        "",
        "- **Aporte al referente**: integra 3 frentes limpios (`Carril 2 + CRIPTO-PIT v3 + Global_VolComp_M1DK`) junto con CME descriptivo a volatilidad idéntica `10%`, reporta CSCV limpio sobre 28 reglas no-CME y cuantifica la ganancia estadística de sumar frentes ortogonales.",
    ]
    (OUT / "RESULTADO.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("Saved:", OUT / "RESULTADO.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args()
    exigir_contada("docs/research/supercartera_v2_20261127/PREREGISTRO.md")
    info = build_data()

    print("\n=== CORRELACION MENSUAL 21-26 DR ===")
    print(pd.DataFrame(info["corr_m"]).to_string())
    print("\n=== TABLA VOLATILIDAD IDENTICA 10% (21-26 DR) ===")
    for k, v in info["front_stats"].items():
        dr = v["DESC_REP"]
        tag = "[SESGO]" if v["upstream_selection_caveat"] else "[LIMPIO]"
        print(f"  {tag:8s} {k:26s} | Sh={dr['sharpe']:5.3f} t={dr['t']:4.2f} | REP={v['REP']['sharpe']:5.3f} | MDD={dr['mdd_at_10pct_vol']:6.2f}% | Calmar={dr['calmar_at_10pct_vol']:4.2f}")

    if args.prepare or not args.finalize:
        generate_kaggle_kernel(info["c2_16_m"], info["m_non_cme_28"], info["m_all_39"], info["w_port"], info["m_port"], info["caveat_map"])

    k_file = OUT / "KAGGLE_SUPER_V2_RESUMEN.json"
    k_res = json.loads(k_file.read_text(encoding="utf-8")) if k_file.exists() else None
    if args.finalize:
        write_summary(info, k_res)


if __name__ == "__main__":
    main()
