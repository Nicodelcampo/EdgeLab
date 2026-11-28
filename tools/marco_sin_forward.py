#!/usr/bin/env python3
"""Paso 3 (Post-Auditoria): Marco Estadistico Sin Forward Corregido + Kernel Kaggle CSCV/DSR/Bayes 20k.

Correcciones respecto a la v1 tras Iteraciones 1 y 2 de auditoria forense:
  1. Cero spike de lunes y cero descalce de ventanas SD: integracion y HRP calculados sobre retornos
     SEMANALES (W-FRI) y MENSUALES (M) con mapeo de fin de semana estricto intra-mes.
  2. Comparacion 100% a VOLATILIDAD IDENTICA (10% anual propia de cada cartera), eliminando la
     ilusion de MDD por escala de riesgo, tanto en historia observada como en Bootstrap 20k semanal.
  3. Exclusion explicita de Futuros No-Equity v2 del nucleo por datos Yahoo =F sin back-adjustment.
  4. CSCV separado en 3 bloques: Carril 2 limpio (16 reglas, 176m), No-CME limpio (21 reglas, 48m),
     y Descriptivo con CME (etiquetado upstream_selection_caveat=True por muestra del vendedor).
  5. Escenario de estres por contraccion realista de CME (0.5x) vs Carril 2 / Cripto (0.5x y 0.7x).

Reune ESTRICTAMENTE en DESC + REP (< 2026-10-01, CERO lectura de HOLDOUT A5 sellado).
Uso:
  python -u tools/marco_sin_forward.py
"""
from __future__ import annotations

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

from edgelab.holdout import a5_bloque, a5_meses  # noqa: E402

def _a5_mes_blq(p: pd.Period) -> str:
    return "TERMINAL" if p >= pd.Period("2026-10", "M") else a5_meses(int(p.year))[int(p.month)]

OUT = ROOT / "docs/research/auditoria_claude_20261127"
OUT.mkdir(parents=True, exist_ok=True)
CSCV_DIR = OUT / "kaggle_cscv"
CSCV_DIR.mkdir(parents=True, exist_ok=True)


def _phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def stats_monthly_10vol(m_s: pd.Series) -> dict:
    """Estadisticas sobre retornos mensuales (y su curva exacta normalizada a 10% vol anual)."""
    m = m_s.dropna()
    n = len(m)
    if n < 3 or float(m.std(ddof=1)) == 0.0:
        return {"meses": int(n), "sharpe": 0.0, "t": 0.0, "p_una_cola": 0.5}
    mu = float(m.mean())
    sd = float(m.std(ddof=1))
    t = mu / (sd / np.sqrt(n))
    sh = (mu / sd) * np.sqrt(12.0)
    m10 = m / (sd * np.sqrt(12.0)) * 10.0
    eq10 = m10.cumsum()
    mdd10 = float((eq10 - eq10.cummax()).min())
    ret10 = float(m10.mean() * 12.0)
    calmar10 = ret10 / abs(mdd10) if mdd10 < 0 else 99.0
    a = m.groupby(lambda p: p.year).sum()
    return {
        "meses": int(n),
        "sharpe": round(sh, 3),
        "t": round(t, 2),
        "p_una_cola": round(1.0 - _phi(t), 4),
        "pct_meses_pos": round(float((m > 0).mean()), 3),
        "pct_anios_pos": round(float((a > 0).mean()), 3),
        "ret_ann_10pct_vol": round(ret10, 2),
        "mdd_at_10pct_vol": round(mdd10, 2),
        "calmar_at_10pct_vol": round(calmar10, 2),
    }


def _hrp_weights(ret: pd.DataFrame) -> np.ndarray:
    arr = ret.fillna(0.0).to_numpy(float)
    if LedoitWolf is None or arr.shape[1] < 2 or len(arr) < 12:
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
    mapped_dates = []
    keep_idx = []
    for dt in cr_valid.index:
        pm = dt.to_period("M")
        cand = month_bdays.get(pm)
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


def load_all_fronts_desc_rep() -> dict:
    bidx_long = pd.bdate_range("2006-01-01", "2026-09-29")
    blq_long = pd.Series([a5_bloque(int(d.strftime("%Y%m%d"))) for d in bidx_long], index=bidx_long)
    assert not blq_long.isin(["TERMINAL"]).any(), "TERMINAL breach!"
    mask_dr_long = blq_long.isin(["DESC", "REP"])

    # ---- Frente 1: CME Intradia ----
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

    # ---- Frente 2: Carril 2 Swing (ESTRICTAMENTE DESC + REP, CERO HOLDOUT) ----
    c2_raw = pd.concat([pd.read_csv(ROOT / f"docs/research/carril2_extension_20261126/OPS_LOTE{k}.csv.gz") for k in (1, 2)], ignore_index=True)
    c2_raw = c2_raw[~c2_raw["definicion"].str.endswith("N") & (c2_raw["fecha"] < 20261001)].copy()
    c2_raw["blq"] = [a5_bloque(int(x)) for x in c2_raw["fecha"]]
    c2_raw = c2_raw[c2_raw["blq"].isin(["DESC", "REP"])].copy()
    c2_raw["dia"] = pd.to_datetime(c2_raw["fecha"].astype(str))
    c2_raw["k"] = c2_raw["definicion"] + "_" + c2_raw["inst"]
    c2_piv = c2_raw.pivot_table(index="dia", columns="k", values="R", aggfunc="sum").fillna(0.0)

    pesos_c2_sellada = json.loads((ROOT / "docs/research/canasta_amplia_20261127/PESOS_CARRIL2_SELLADA.json").read_text(encoding="utf-8"))
    c2_16_cols = [c for c in pesos_c2_sellada if c in c2_piv.columns]
    c2_sellada = (c2_piv[c2_16_cols].reindex(bidx_long, fill_value=0.0) * pd.Series(pesos_c2_sellada)).sum(axis=1)
    c2_16_df = c2_piv[c2_16_cols].reindex(bidx_long, fill_value=0.0)
    c2_16_df = c2_16_df.where(mask_dr_long, np.nan)

    # ---- Frente 3: Futuros No-Equity v2 (EXCLUIDO del nucleo por roll no ajustado Yahoo =F) ----
    fut_df = pd.read_csv(OUT / "SERIES_FUTUROS_NO_EQUITY_V2_DR.csv.gz", index_col=0, parse_dates=True)

    # ---- Frente 4: Cripto PIT v2 auditada (ex-TradFi, Staggered, intra-month mapped) ----
    cr_df = pd.read_csv(OUT / "SERIES_CRIPTO_PIT_V2_DR.csv.gz", index_col=0, parse_dates=True)
    cr_valid = cr_df.dropna(subset=["CR2_Core_XSMOM_ResidMom"])
    cr_mapped = _map_crypto_intra_month(cr_valid, bidx_long, mask_dr_long)

    # Build daily sleeves frame (ONLY DESC + REP, NaN otherwise)
    daily_sleeves = pd.DataFrame(index=bidx_long)
    daily_sleeves["F1_CME_Intradia8"] = np.where(mask_dr_long, cme_intra8.reindex(bidx_long), np.nan)
    daily_sleeves["F1_CME_Div10"] = np.where(mask_dr_long, cme_div10.reindex(bidx_long), np.nan)
    daily_sleeves["F1_CME_TRZV"] = np.where(mask_dr_long, cme_trzv.reindex(bidx_long), np.nan)
    daily_sleeves["F2_Carril2_Sell16"] = np.where(mask_dr_long, c2_sellada, np.nan)
    daily_sleeves["F3_FutNoEq_v2"] = fut_df["FUT_Canasta_InvVol"].reindex(bidx_long)
    daily_sleeves["F4_Cripto_Core_Stag"] = cr_mapped["CR2_Core_XSMOM_ResidMom"]
    daily_sleeves["F4_Cripto_InvVol"] = cr_mapped["CR2_Canasta_InvVol"]
    daily_sleeves["F4_Cripto_XSMOM_Stag5d"] = cr_mapped["CR2_XSMOM_Stag5d"]

    # Individual mechanisms matrix (separated clean non-CME vs CME!)
    cme_ind = pd.DataFrame(index=bidx_long)
    for c in ["T_NQ", "R_NQ", "Z_NQ", "V_NQ", "RQ5_NQ", "FR_NQ", "RQ5_ES", "ES5N_ES"]:
        cme_ind[f"CME_{c}"] = np.where(mask_dr_long, sd_raw[c].reindex(bidx_long), np.nan)
    cme_ind["CME_N_NQ"] = np.where(mask_dr_long, n_s.reindex(bidx_long), np.nan)
    cme_ind["CME_SOM_eod"] = np.where(mask_dr_long, som_eod.reindex(bidx_long), np.nan)

    cr_ind = pd.DataFrame(index=bidx_long)
    for c in ["CR2_TSMOM_Blend_1D", "CR2_Donchian_30_15", "CR2_XSMOM_Stag5d", "CR2_ResidMom_Stag5d", "CR2_Funding_Carry_Stag3d"]:
        if c in cr_mapped:
            cr_ind[c] = cr_mapped[c]

    return {
        "bidx_long": bidx_long,
        "blq_long": blq_long,
        "mask_dr_long": mask_dr_long,
        "daily_sleeves": daily_sleeves,
        "c2_16_df": c2_16_df,
        "cr_ind": cr_ind,
        "cme_ind": cme_ind,
    }


def compute_carril2_epochs(c2_d: pd.Series, blq: pd.Series) -> dict:
    out = {}
    for lbl, y0, y1 in [("2006_2012", "2006-01-01", "2012-12-31"), ("2013_2018", "2013-01-01", "2018-12-31"), ("2019_2026", "2019-01-01", "2026-09-30"), ("2021_2026", "2021-01-01", "2026-09-30")]:
        sub = c2_d[(c2_d.index >= y0) & (c2_d.index <= y1)].dropna()
        sb = blq.reindex(sub.index)
        m_dr = sub.groupby(sub.index.to_period("M")).sum()
        m_d = sub[sb == "DESC"].groupby(sub[sb == "DESC"].index.to_period("M")).sum()
        m_r = sub[sb == "REP"].groupby(sub[sb == "REP"].index.to_period("M")).sum()
        out[lbl] = {
            "DESC_REP": stats_monthly_10vol(m_dr),
            "DESC": stats_monthly_10vol(m_d),
            "REP": stats_monthly_10vol(m_r),
        }
    return out


def compute_pooled_holdout_power(daily_sleeves: pd.DataFrame, blq: pd.Series) -> dict:
    """Potencia estadistica TEORICA (SIN ABRIR HOLDOUT!) sobre bloques HOLDOUT A5 sellados."""
    def _pwr(m_s: pd.Series, n_sealed: int) -> dict:
        m = m_s.dropna()
        if len(m) < 6 or float(m.std(ddof=1)) == 0.0:
            return {"sr_dr": 0.0}
        sr = float(m.mean() / m.std(ddof=1) * np.sqrt(12.0))
        return {
            "meses_DESC_REP": int(len(m)),
            "sr_anual_DR": round(sr, 3),
            "n_holdout_sellado": n_sealed,
            "potencia_sh05": round(_phi(sqrt(n_sealed / 12.0) * (0.5 * sr) - 1.6448536), 3),
            "potencia_sh07": round(_phi(sqrt(n_sealed / 12.0) * (0.7 * sr) - 1.6448536), 3),
            "potencia_sh10": round(_phi(sqrt(n_sealed / 12.0) * sr - 1.6448536), 3),
        }

    # Aggregate strictly by calendar month (DESC+REP only -> 0 holdout months! Day-level EMBARGO already masked in daily_sleeves)
    m_all = daily_sleeves.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1)
    blq_m = pd.Series([_a5_mes_blq(p) for p in m_all.index], index=m_all.index)
    dr_m = blq_m.isin(["DESC", "REP"])
    m_all = m_all[dr_m]
    blq_m = blq_m[dr_m]

    def _std_desc_m(col: str, min_p: str | None = None) -> pd.Series:
        s = m_all[col].dropna()
        if min_p:
            s = s[s.index >= min_p]
        sd = float(s[blq_m.reindex(s.index) == "DESC"].std(ddof=1))
        return s / (sd if sd > 0 else 1.0)

    c2_long = _std_desc_m("F2_Carril2_Sell16")
    c2_21 = _std_desc_m("F2_Carril2_Sell16", "2021-01")
    fut_long = _std_desc_m("F3_FutNoEq_v2")
    cr_inv = _std_desc_m("F4_Cripto_InvVol", "2021-01")
    cr_core = _std_desc_m("F4_Cripto_Core_Stag", "2021-01")

    pool_c2_crcore_21 = pd.concat([c2_21, cr_core], axis=1).mean(axis=1)
    pool_c2_crinv_21 = pd.concat([c2_21, cr_inv], axis=1).mean(axis=1)
    pool_c2_crcore_dyn = pd.concat([c2_long, cr_core], axis=1).mean(axis=1)

    return {
        "1_Carril2_Sellada16_06_26": _pwr(c2_long, 63),
        "2_Cripto_Core_Stag_21_26": _pwr(cr_core, 18),
        "3_Cripto_InvVol_21_26": _pwr(cr_inv, 18),
        "4_Pooled_Carril2_plus_CriptoCore_21_26": _pwr(pool_c2_crcore_21, 18),
        "5_Pooled_Carril2_plus_CriptoInvVol_21_26": _pwr(pool_c2_crinv_21, 18),
        "6_Pooled_Carril2_plus_CriptoCore_Dyn_06_26": _pwr(pool_c2_crcore_dyn, 63),
        "7_FutNoEq_v2_YahooSinBackAdjust_INVALIDADO": _pwr(fut_long, 63),
    }


def compute_shrinkage_stress(m21: pd.DataFrame, blq_m21: pd.Series) -> dict:
    """Estres realista de contraccion de CME (0.5x) vs Carril2 y Cripto (0.5x y 0.7x) a igual 10% vol."""
    desc_m = blq_m21 == "DESC"
    # Normalize each front to unit DESC monthly SD in 2021-2026
    fn = m21.copy()
    for c in m21.columns:
        fn[c] = m21[c] / float(m21.loc[desc_m, c].std(ddof=1))

    ports = {
        "CME_TRZV_solo": fn["CME_TRZV"],
        "CME_Div10_solo": fn["CME_Div10"],
        "Super_3Core_EQ_Div10": (fn["CME_Div10"] + fn["Carril2_Sell16"] + fn["Cripto_Core_Stag"]) / 3.0,
        "Super_3Core_EQ_TRZV": (fn["CME_TRZV"] + fn["Carril2_Sell16"] + fn["Cripto_Core_Stag"]) / 3.0,
        "CME50_C2_25_Cripto25_TRZV": 0.50 * fn["CME_TRZV"] + 0.25 * fn["Carril2_Sell16"] + 0.25 * fn["Cripto_Core_Stag"],
    }
    res = {}
    for cme_sh, oth_sh in [(1.0, 1.0), (0.5, 0.7), (0.5, 0.5)]:
        sc_lbl = f"CME_{cme_sh}x__C2_CR_{oth_sh}x"
        res[sc_lbl] = {}
        # Build adjusted component series (shift mean while keeping realized monthly covariance!)
        fn_adj = fn.copy()
        for c in ("CME_TRZV", "CME_Div10"):
            fn_adj[c] = fn[c] - (1.0 - cme_sh) * float(fn[c].mean())
        for c in ("Carril2_Sell16", "Cripto_Core_Stag", "Cripto_InvVol"):
            fn_adj[c] = fn[c] - (1.0 - oth_sh) * float(fn[c].mean())
        p_adj = {
            "CME_TRZV_solo": fn_adj["CME_TRZV"],
            "CME_Div10_solo": fn_adj["CME_Div10"],
            "Super_3Core_EQ_Div10": (fn_adj["CME_Div10"] + fn_adj["Carril2_Sell16"] + fn_adj["Cripto_Core_Stag"]) / 3.0,
            "Super_3Core_EQ_TRZV": (fn_adj["CME_TRZV"] + fn_adj["Carril2_Sell16"] + fn_adj["Cripto_Core_Stag"]) / 3.0,
            "CME50_C2_25_Cripto25_TRZV": 0.50 * fn_adj["CME_TRZV"] + 0.25 * fn_adj["Carril2_Sell16"] + 0.25 * fn_adj["Cripto_Core_Stag"],
        }
        for pname, s in p_adj.items():
            res[sc_lbl][pname] = stats_monthly_10vol(s)
    return res


def generate_kaggle_cscv_kernel(
    m_c2_only: pd.DataFrame,
    m_non_cme_21: pd.DataFrame,
    m_all_21: pd.DataFrame,
    w_boot: pd.DataFrame,
    pooled_m: pd.DataFrame,
    caveat_map: dict[str, bool],
) -> None:
    """Empaqueta matrices limpias (sin spike de lunes) para Kaggle CSCV + DSR + Bayes + Bootstrap 20k semanal a 10% vol."""
    payload = {
        "c2_cols": list(m_c2_only.columns),
        "c2_vals": np.round(m_c2_only.to_numpy(float), 4).tolist(),
        "non_cme_cols": list(m_non_cme_21.columns),
        "non_cme_vals": np.round(m_non_cme_21.to_numpy(float), 4).tolist(),
        "all_cols": list(m_all_21.columns),
        "all_vals": np.round(m_all_21.to_numpy(float), 4).tolist(),
        "w_boot_cols": list(w_boot.columns),
        "w_boot_vals": np.round(w_boot.to_numpy(float), 4).tolist(),
        "pooled_m_cols": list(pooled_m.columns),
        "pooled_m_vals": np.round(pooled_m.to_numpy(float), 4).tolist(),
        "caveat_map": caveat_map,
    }
    b64 = base64.b64encode(gzip.compress(json.dumps(payload).encode("utf-8"))).decode("ascii")

    script = f'''#!/usr/bin/env python3
"""Kaggle Kernel v2 (Auditado): CSCV limpio (Carril2 & No-CME) vs Descriptivo CME, DSR (N=1..5000), Bayes y Boot 20k semanal a 10% vol."""
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
    skew = float(np.mean(z ** 3))
    kurt = float(np.mean(z ** 4))
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
    z_dsr = (sr_m - sr0_m) * sqrt(T - 1.0) / denom
    return {{"sr_anual": round(sr_ann, 3), "skew": round(skew, 3), "kurt": round(kurt, 3), "dsr": round(phi(z_dsr), 4)}}


def run_cscv(mat_m, S=16, tag="CLEAN"):
    T, K = mat_m.shape
    blk_len = T // S
    usable = blk_len * S
    mat = mat_m[:usable]
    blocks = [mat[i * blk_len : (i + 1) * blk_len] for i in range(S)]
    all_idx = set(range(S))
    logits, oos_srs_best, oos_srs_ew, is_srs_best = [], [], [], []
    for comb in itertools.combinations(range(S), S // 2):
        oos_idx = sorted(all_idx - set(comb))
        IS = np.vstack([blocks[i] for i in comb])
        OOS = np.vstack([blocks[i] for i in oos_idx])
        sd_is = np.std(IS, axis=0, ddof=1)
        mu_is = np.mean(IS, axis=0)
        sr_is = np.where(sd_is > 1e-9, mu_is / sd_is, 0.0) * sqrt(12.0)
        sd_oos = np.std(OOS, axis=0, ddof=1)
        mu_oos = np.mean(OOS, axis=0)
        sr_oos = np.where(sd_oos > 1e-9, mu_oos / sd_oos, 0.0) * sqrt(12.0)
        n_star = int(np.argmax(sr_is))
        is_srs_best.append(float(sr_is[n_star]))
        oos_srs_best.append(float(sr_oos[n_star]))
        rank = float(np.sum(sr_oos <= sr_oos[n_star])) / (K + 1.0)
        rank = min(max(rank, 1.0 / (K + 1.0)), K / (K + 1.0))
        logits.append(float(np.log(rank / (1.0 - rank))))
        ew_oos = np.mean(OOS / np.where(sd_is > 1e-9, sd_is, 1.0), axis=1)
        oos_srs_ew.append(float(np.mean(ew_oos) / max(np.std(ew_oos, ddof=1), 1e-9) * sqrt(12.0)))
    logits_a = np.asarray(logits)
    oos_best_a = np.asarray(oos_srs_best)
    oos_ew_a = np.asarray(oos_srs_ew)
    return {{
        "tag": tag,
        "n_splits": len(logits),
        "T_months_used": usable,
        "K_strategies": K,
        "PBO_prob_overfit": round(float(np.mean(logits_a <= 0.0)), 4),
        "best_single_IS_SR_median": round(float(np.median(is_srs_best)), 3),
        "best_single_OOS_SR_median": round(float(np.median(oos_best_a)), 3),
        "best_single_P_OOS_pos": round(float(np.mean(oos_best_a > 0.0)), 4),
        "basket_1N_OOS_SR_median": round(float(np.median(oos_ew_a)), 3),
        "basket_1N_OOS_SR_p10": round(float(np.percentile(oos_ew_a, 10)), 3),
        "basket_1N_P_OOS_pos": round(float(np.mean(oos_ew_a > 0.0)), 4),
        "basket_1N_P_OOS_gt_05": round(float(np.mean(oos_ew_a > 0.5)), 4),
        "basket_1N_P_OOS_gt_10": round(float(np.mean(oos_ew_a > 1.0)), 4),
    }}


@njit
def block_bootstrap_20k_weekly_10vol(y_w_10pct, n_paths, block_len, seed):
    L = len(y_w_10pct)
    srs = np.zeros(n_paths)
    rets = np.zeros(n_paths)
    mdds = np.zeros(n_paths)
    for k in range(n_paths):
        s = (seed + k * 2654435761) & 0xFFFFFFFF
        pos = 0
        rem = 0
        eq = 0.0
        pk = 0.0
        mdd = 0.0
        sum_y = 0.0
        sum_y2 = 0.0
        for step in range(52):
            if rem == 0:
                s = (1664525 * s + 1013904223) & 0xFFFFFFFF
                pos = int(s % L)
                rem = block_len
            idx = (pos + (block_len - rem)) % L
            rem -= 1
            val = y_w_10pct[idx]
            sum_y += val
            sum_y2 += val * val
            eq += val
            if eq > pk:
                pk = eq
            if eq - pk < mdd:
                mdd = eq - pk
        mu = sum_y / 52.0
        var = max(1e-12, (sum_y2 / 52.0) - mu * mu)
        srs[k] = (mu / sqrt(var)) * sqrt(52.0)
        rets[k] = eq
        mdds[k] = mdd
    return srs, rets, mdds


def empirical_bayes_posterior(sr_obs, T_m, caveat, prior_mu=0.0, prior_sd=0.65):
    se = sqrt(12.0 / max(1, T_m))
    post_var = 1.0 / (1.0 / (prior_sd ** 2) + 1.0 / (se ** 2))
    post_mu = post_var * (prior_mu / (prior_sd ** 2) + sr_obs / (se ** 2))
    post_sd = sqrt(post_var)
    return {{
        "sr_obs": round(sr_obs, 3),
        "T_months": int(T_m),
        "upstream_selection_caveat": bool(caveat),
        "post_mean": round(post_mu, 3),
        "post_sd": round(post_sd, 3),
        "P_true_gt_0": round(1.0 - phi((0.0 - post_mu) / post_sd), 4),
        "P_true_gt_05": round(1.0 - phi((0.5 - post_mu) / post_sd), 4),
        "P_true_gt_10": round(1.0 - phi((1.0 - post_mu) / post_sd), 4),
    }}


def main():
    t0 = time.time()
    m_c2 = np.asarray(D["c2_vals"], dtype=np.float64)
    m_nc = np.asarray(D["non_cme_vals"], dtype=np.float64)
    m_al = np.asarray(D["all_vals"], dtype=np.float64)
    w_bt = np.asarray(D["w_boot_vals"], dtype=np.float64)
    w_cols = D["w_boot_cols"]
    p_m = np.asarray(D["pooled_m_vals"], dtype=np.float64)
    p_cols = D["pooled_m_cols"]
    cav = D["caveat_map"]

    cscv_out = {{
        "1_clean_carril2_16rules": run_cscv(m_c2, S=16, tag="LIMPIO_SIN_CME"),
        "2_clean_non_cme_21rules": run_cscv(m_nc, S=16, tag="LIMPIO_SIN_CME"),
        "3_descriptive_with_cme": run_cscv(m_al, S=16, tag="DESCRIPTIVO_SESGO_VENDEDOR_CME"),
    }}

    dsr_out = {{}}
    eb_out = {{}}
    for j, cname in enumerate(p_cols):
        col_v = p_m[:, j]
        col_v = col_v[np.isfinite(col_v)]
        dsr_out[cname] = {{f"N_{{nt}}": dsr_prob(col_v, nt) for nt in (1, 10, 50, 200, 500, 5000)}}
        dsr_out[cname]["upstream_selection_caveat"] = bool(cav.get(cname, True))
        sr_obs = float(np.mean(col_v) / max(np.std(col_v, ddof=1), 1e-9) * sqrt(12.0))
        eb_out[cname] = empirical_bayes_posterior(sr_obs, len(col_v), cav.get(cname, True))

    boot_out = {{}}
    for j, cname in enumerate(w_cols):
        yw = w_bt[:, j]
        yw = yw[np.isfinite(yw)]
        sd_w = float(np.std(yw, ddof=1))
        # Exact 10% annualized vol scaling BEFORE 52-week block bootstrap!
        yw_10 = yw / (sd_w * sqrt(52.0)) * 10.0 if sd_w > 0 else yw
        srs, rets, mdds = block_bootstrap_20k_weekly_10vol(yw_10, 20000, 4, 202611 + j)
        boot_out[cname] = {{
            "weeks": len(yw),
            "target_ann_vol_pct": 10.0,
            "upstream_selection_caveat": bool(cav.get(cname, True)),
            "sr_1yr_p50": round(float(np.median(srs)), 3),
            "sr_1yr_p10": round(float(np.percentile(srs, 10)), 3),
            "P_yr_pos": round(float(np.mean(rets > 0.0)), 4),
            "ret_1yr_p50_pct": round(float(np.median(rets)), 2),
            "mdd_p50_pct": round(float(np.median(mdds)), 2),
            "mdd_p95_pct": round(float(np.percentile(mdds, 5)), 2),
            "calmar_median": round(float(np.median(rets) / max(abs(np.median(mdds)), 1e-6)), 2),
        }}

    res = {{
        "elapsed_s": round(time.time() - t0, 2),
        "cscv": cscv_out,
        "dsr_by_trials": dsr_out,
        "empirical_bayes": eb_out,
        "bootstrap_20k_weekly_10pct_vol": boot_out,
    }}
    out_p = Path("/kaggle/working/KAGGLE_CSCV_RESUMEN.json") if os.path.isdir("/kaggle/working") else Path("KAGGLE_CSCV_RESUMEN.json")
    out_p.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"DONE CSCV+DSR+20kBootWeekly in {{time.time() - t0:.1f}}s", flush=True)


if __name__ == "__main__":
    main()
'''
    (CSCV_DIR / "kaggle_cscv.py").write_text(script, encoding="utf-8")
    meta = {
        "id": "nicolasbuttaro/edgelab-sin-forward-cscv-20261127",
        "title": "edgelab-sin-forward-cscv-20261127",
        "code_file": "kaggle_cscv.py",
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
    (CSCV_DIR / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("Generated Kaggle CSCV kernel v2:", CSCV_DIR / "kaggle_cscv.py", f"({len(script)//1024} KB)")


def main() -> None:
    loaded = load_all_fronts_desc_rep()
    blq = loaded["blq_long"]
    dr = loaded["mask_dr_long"]
    daily_sl = loaded["daily_sleeves"]
    idx = daily_sl.index

    # Monthly & Weekly aggregations ONLY inside DESC + REP (2021-01 -> 2026-09)
    m_all = daily_sl.dropna(how="all").groupby(lambda d: d.to_period("M")).sum(min_count=1)
    blq_m_all = pd.Series([_a5_mes_blq(p) for p in m_all.index], index=m_all.index)
    m_all = m_all[blq_m_all.isin(["DESC", "REP"])]
    blq_m_all = blq_m_all[blq_m_all.isin(["DESC", "REP"])]

    m21 = m_all.loc[m_all.index >= "2021-01"].copy()
    blq_m21 = blq_m_all.loc[m21.index]
    # Rename for clean presentation
    fronts_m21 = pd.DataFrame({
        "CME_Intradia8": m21["F1_CME_Intradia8"],
        "CME_Div10": m21["F1_CME_Div10"],
        "CME_TRZV": m21["F1_CME_TRZV"],
        "Carril2_Sell16": m21["F2_Carril2_Sell16"],
        "Cripto_Core_Stag": m21["F4_Cripto_Core_Stag"],
        "Cripto_InvVol": m21["F4_Cripto_InvVol"],
        "Cripto_XSMOM_Stag5d": m21["F4_Cripto_XSMOM_Stag5d"],
    }).dropna()

    # Standardize each front by its OWN DESC monthly SD in common 2021-2026 window (39m)
    desc_m21 = blq_m21.reindex(fronts_m21.index) == "DESC"
    sd_m_21 = {c: float(fronts_m21.loc[desc_m21, c].std(ddof=1)) for c in fronts_m21.columns}

    # Weekly aggregation inside 2021-2026 DESC+REP (zeros Monday spike completely!)
    d21 = daily_sl.loc[dr & (idx >= "2021-01-01"), [
        "F1_CME_Intradia8", "F1_CME_Div10", "F1_CME_TRZV", "F2_Carril2_Sell16",
        "F4_Cripto_Core_Stag", "F4_Cripto_InvVol", "F4_Cripto_XSMOM_Stag5d",
    ]].copy()
    d21.columns = list(fronts_m21.columns)
    # Normalize daily rows by their respective DESC 21-26 monthly SD before summing into weeks/months
    d21_norm = d21 / pd.Series(sd_m_21)
    # Aggregate weekly only keeping weeks whose Friday/days are inside DESC+REP (strictly keep valid non-HOLDOUT weeks!)
    w21_norm = d21_norm.resample("W-FRI").sum(min_count=1).dropna(how="all")
    # Filter weeks whose period month is strictly in blq_m21 (blocks edge weeks touching HOLDOUT months!)
    dr_periods = set(m21.index)
    keep_w = [
        (pd.Period(d, "M") in dr_periods) and (pd.Period(d - pd.Timedelta(days=6), "M") in dr_periods)
        for d in w21_norm.index
    ]
    w21_norm = w21_norm.loc[keep_w].fillna(0.0)
    blq_w21 = pd.Series([_a5_mes_blq(pd.Period(d, "M")) for d in w21_norm.index], index=w21_norm.index)

    # Fit Weekly HRP weights strictly on DESC weeks across the 3 core fronts (no F3_FutNoEq_v2!)
    w_hrp_cols = ["CME_Div10", "Carril2_Sell16", "Cripto_Core_Stag"]
    w_hrp_arr = _hrp_weights(w21_norm.loc[blq_w21 == "DESC", w_hrp_cols])
    hrp_weights = {c: round(float(v), 4) for c, v in zip(w_hrp_cols, w_hrp_arr)}

    # Build weekly portfolio frame
    w_port = pd.DataFrame({
        "CME_Intradia8": w21_norm["CME_Intradia8"],
        "CME_Div10": w21_norm["CME_Div10"],
        "CME_TRZV": w21_norm["CME_TRZV"],
        "Carril2_Sell16": w21_norm["Carril2_Sell16"],
        "Cripto_Core_Stag": w21_norm["Cripto_Core_Stag"],
        "Cripto_InvVol": w21_norm["Cripto_InvVol"],
        "Super_3Core_EQ": w21_norm[w_hrp_cols].mean(axis=1),
        "Super_3Core_HRP_Weekly": (w21_norm[w_hrp_cols] * w_hrp_arr).sum(axis=1),
        "Super_3Core_TRZV_EQ": w21_norm[["CME_TRZV", "Carril2_Sell16", "Cripto_Core_Stag"]].mean(axis=1),
        "CME50_C2_25_Cripto25": 0.50 * w21_norm["CME_TRZV"] + 0.25 * w21_norm["Carril2_Sell16"] + 0.25 * w21_norm["Cripto_Core_Stag"],
    })

    # Monthly portfolio frame (exact same portfolios summed from fronts_m21 / sd_m_21!)
    m21_norm = fronts_m21 / pd.Series(sd_m_21)
    m_port = pd.DataFrame({
        "CME_Intradia8": m21_norm["CME_Intradia8"],
        "CME_Div10": m21_norm["CME_Div10"],
        "CME_TRZV": m21_norm["CME_TRZV"],
        "Carril2_Sell16": m21_norm["Carril2_Sell16"],
        "Cripto_Core_Stag": m21_norm["Cripto_Core_Stag"],
        "Cripto_InvVol": m21_norm["Cripto_InvVol"],
        "Super_3Core_EQ": m21_norm[w_hrp_cols].mean(axis=1),
        "Super_3Core_HRP_Weekly": (m21_norm[w_hrp_cols] * w_hrp_arr).sum(axis=1),
        "Super_3Core_TRZV_EQ": m21_norm[["CME_TRZV", "Carril2_Sell16", "Cripto_Core_Stag"]].mean(axis=1),
        "CME50_C2_25_Cripto25": 0.50 * m21_norm["CME_TRZV"] + 0.25 * m21_norm["Carril2_Sell16"] + 0.25 * m21_norm["Cripto_Core_Stag"],
    })

    caveat_map = {
        "CME_Intradia8": True,
        "CME_Div10": True,
        "CME_TRZV": True,
        "Carril2_Sell16": False,
        "Cripto_Core_Stag": False,
        "Cripto_InvVol": False,
        "Super_3Core_EQ": True,
        "Super_3Core_HRP_Weekly": True,
        "Super_3Core_TRZV_EQ": True,
        "CME50_C2_25_Cripto25": True,
    }

    # Summary table (DESC, REP, DESC_REP at equal 10% own annualized vol!)
    front_stats = {}
    for col in m_port.columns:
        s_m = m_port[col]
        b_m = blq_m21.reindex(s_m.index)
        front_stats[col] = {
            "upstream_selection_caveat": caveat_map[col],
            "DESC": stats_monthly_10vol(s_m[b_m == "DESC"]),
            "REP": stats_monthly_10vol(s_m[b_m == "REP"]),
            "DESC_REP": stats_monthly_10vol(s_m),
        }

    print("\n=== TABLA AUDITADA A VOLATILIDAD IDENTICA (10% ANUAL PROPIA, 2021-2026 DESC+REP, HOLDOUT SELLADO) ===")
    for k, v in front_stats.items():
        dr_s, rep_s = v["DESC_REP"], v["REP"]
        tag = "[SESGO CME]" if v["upstream_selection_caveat"] else "[LIMPIO]   "
        print(
            f"  {tag} {k:24s} | Sh={dr_s['sharpe']:5.3f} t={dr_s['t']:4.2f} | "
            f"REP Sh={rep_s['sharpe']:5.3f} | MDD_10%={dr_s['mdd_at_10pct_vol']:6.2f}% | "
            f"Calmar_10%={dr_s['calmar_at_10pct_vol']:4.2f}"
        )

    corr_m = m_port[["CME_TRZV", "CME_Div10", "Carril2_Sell16", "Cripto_Core_Stag", "Cripto_InvVol"]].corr().round(3).to_dict()
    corr_w = w_port[["CME_TRZV", "CME_Div10", "Carril2_Sell16", "Cripto_Core_Stag", "Cripto_InvVol"]].corr().round(3).to_dict()

    c2_epochs = compute_carril2_epochs(daily_sl["F2_Carril2_Sell16"], blq)
    pooled_pwr = compute_pooled_holdout_power(daily_sl, blq)
    stress_cme = compute_shrinkage_stress(fronts_m21, blq_m21)

    print("\n=== CARRIL 2 SELLADA 16 POR EPOCA (SOLO DESC+REP, CERO HOLDOUT) ===")
    for ep, ev in c2_epochs.items():
        print(f"  {ep}: DR Sh={ev['DESC_REP']['sharpe']:5.2f} t={ev['DESC_REP']['t']:4.2f} | DESC Sh={ev['DESC']['sharpe']:5.2f} | REP Sh={ev['REP']['sharpe']:5.2f}")

    print("\n=== ESTRES CONTRACCION CME 0.5x A IGUAL 10% VOLATILIDAD ===")
    for sc, sv in stress_cme.items():
        print(f"  {sc}:")
        for p, pv in sv.items():
            print(f"    {p:26s}: Sh={pv['sharpe']:4.2f} | MDD_10%={pv['mdd_at_10pct_vol']:6.2f}% | Calmar={pv['calmar_at_10pct_vol']:4.2f}")

    # Build the 3 CSCV matrices (monthly, strictly non-HOLDOUT!)
    # 1) Clean Carril 2 16 rules (2006-2026 DESC+REP -> 186m, usable 176m)
    c2_16_m = loaded["c2_16_df"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    c2_blq = pd.Series([_a5_mes_blq(p) for p in c2_16_m.index], index=c2_16_m.index)
    c2_16_m = c2_16_m[c2_blq.isin(["DESC", "REP"])].fillna(0.0)

    # 2) Clean non-CME 21-26 (16 Carril 2 + 5 Cripto v2 = 21 rules, 51m -> usable 48m)
    cr_ind_m = loaded["cr_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    c2_21_m = c2_16_m.loc[c2_16_m.index >= "2021-01"]
    m_non_cme_21 = pd.concat([c2_21_m, cr_ind_m.reindex(c2_21_m.index)], axis=1).fillna(0.0)
    m_non_cme_21 = m_non_cme_21.loc[:, m_non_cme_21.std(ddof=1) > 1e-8]

    # 3) Descriptive 21-26 with CME survivors (caveated!)
    cme_ind_m = loaded["cme_ind"].dropna(how="all").groupby(lambda d: d.to_period("M")).sum()
    cme_ind_m = cme_ind_m.loc[cme_ind_m.index >= "2021-01"]
    m_all_21 = pd.concat([cme_ind_m.reindex(c2_21_m.index), m_non_cme_21], axis=1).fillna(0.0)
    m_all_21 = m_all_21.loc[:, m_all_21.std(ddof=1) > 1e-8]

    generate_kaggle_cscv_kernel(c2_16_m, m_non_cme_21, m_all_21, w_port, m_port, caveat_map)

    # Save strictly sealed SERIES_4_FRENTES_DR.csv.gz (normalized daily DESC+REP 21-26 for reproducible charting)
    d21_save = pd.DataFrame({
        "CME_Intradia8": d21_norm["CME_Intradia8"],
        "CME_Div10": d21_norm["CME_Div10"],
        "CME_TRZV": d21_norm["CME_TRZV"],
        "Carril2_Sell16": d21_norm["Carril2_Sell16"],
        "Cripto_Core_Stag": d21_norm["F4_Cripto_Core_Stag"] if "F4_Cripto_Core_Stag" in d21_norm else d21_norm["Cripto_Core_Stag"],
        "Cripto_InvVol": d21_norm["Cripto_InvVol"],
        "Super_3Core_EQ": d21_norm[w_hrp_cols].mean(axis=1),
        "Super_3Core_HRP_Weekly": (d21_norm[w_hrp_cols] * w_hrp_arr).sum(axis=1),
        "CME50_C2_25_Cripto25": 0.50 * d21_norm["CME_TRZV"] + 0.25 * d21_norm["Carril2_Sell16"] + 0.25 * d21_norm["Cripto_Core_Stag"],
    })
    blq_d21 = blq.reindex(d21_save.index)
    d21_save.loc[~blq_d21.isin(["DESC", "REP"])] = np.nan
    d21_save.to_csv(OUT / "SERIES_4_FRENTES_DR.csv.gz")

    summary = {
        "F3_excluido_motivo": "datos_yahoo_sin_back_adjustment",
        "hrp_weights_weekly_3core_DESC": hrp_weights,
        "corr_monthly_21_26_DR": corr_m,
        "corr_weekly_21_26_DR": corr_w,
        "front_and_super_stats_10pct_vol": front_stats,
        "carril2_sellada16_by_epoch": c2_epochs,
        "shrinkage_stress_10pct_vol": stress_cme,
        "pooled_sealed_holdout_power": pooled_pwr,
        "cscv_shapes": {
            "clean_carril2_16rules": list(c2_16_m.shape),
            "clean_non_cme_21_26": list(m_non_cme_21.shape),
            "descriptive_all_21_26": list(m_all_21.shape),
        },
    }
    (OUT / "MARCO_SIN_FORWARD.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\nSaved:", OUT / "MARCO_SIN_FORWARD.json")


if __name__ == "__main__":
    main()
