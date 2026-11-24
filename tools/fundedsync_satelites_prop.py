"""Quantified Monte Carlo & Portfolio proposals to monetize excluded profitable strategies.

Evaluates 5 concrete monetization mechanisms using synchronized 2,000-path bootstraps
across `REP 100%`, `REP 60%` (edge haircut), and `HOLDOUT` (POST_2020 `2020-01..2026-09`):
  1. Split Call-Option Architecture: Isolate lower-Calmar profitable sleeves (`V + W`) on
     low-fee futures accounts (`Bulenox Opt2 150K`, `FundedNext 50K`, `LucidFlex 50K`)
     instead of merging them into Primary `Core5_AltaConv` (`2x LucidFlex 150K + 2x Tradeify 150K`).
  2. Overnight Unlock on CFD (`O` overnight NQ on `FTMO Swing 100K` / `The5ers HighStakes 100K`).
  3. Zero-Commission `ES / US500` CFD Satellite (`ES` adapted modules, `$0` comm, pure spread).
  4. `R_maeATR25` High-Payoff Swap & `SingleModule` Lifecycle Specialization (`T` -> `Core5` -> `R+Z`).
  5. Uncapped Personal Broker Blend (`Core5 + V+W + O + ES`) + orthogonal `cartera_20261116`.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

import fundedsync_integracion_multiprop as MP
import fundedsync_iter2_cartera as IT2
import fundedsync_multiactivo_oro as MA
import fundedsync_post_il_cadena as IL
from edgelab.holdout import a5_bloque

OUT_DIR = REPO / "docs" / "research" / "fundedsync_satelites_prop_20261123"
ARTIFACT_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")
CATALOGO_JSON = REPO / "docs" / "research" / "fundedsync_deploy_multiprop_20261122" / "catalogo_multiprop_20261122.json"
PHASE_SHIFT_CFD_CSV = REPO / "docs" / "research" / "fundedsync_bar_phase_shift_20261123" / "cfd_usatech_spread_and_comparison.csv"
CARTERA_20261116_MD = REPO / "docs" / "research" / "cartera_20261116" / "RESULTADO.md"

BG_FIG = "#0d1316"
BG_AX = "#11191c"
GRID_COL = "#243137"
FG_TEXT = "#e6eef2"
MUTED_TEXT = "#9ab0ba"
ACCENT_TEAL = "#2ec4b6"
ACCENT_GOLD = "#f4b942"
ACCENT_CORAL = "#e76f51"
ACCENT_BLUE = "#5fa8d3"
ACCENT_GREEN = "#80ed99"

plt.rcParams["text.parse_math"] = False

# Frozen causal preset weights matching EdgeLabFundedSyncCfdCore.cs verbatim
WEIGHTS_CORE5 = {
    "R_osc30_end660_ATR50::NQ": 1.802134,
    "Z_b15_e20_eff40_ATR50::NQ": 2.277168,
    "T_stop100_BE15R_calFalse::NQ": 0.709531,
    "N_d5_fbTrue_ATR25::NQ": 1.261968,
    "SOMEOD_ext_NQ::NQ": 0.848629,
}
WEIGHTS_CORE5_R25 = {
    "R_osc30_end660_ATR25::NQ": 1.802134,
    "Z_b15_e20_eff40_ATR50::NQ": 2.277168,
    "T_stop100_BE15R_calFalse::NQ": 0.709531,
    "N_d5_fbTrue_ATR25::NQ": 1.261968,
    "SOMEOD_ext_NQ::NQ": 0.848629,
}
WEIGHTS_P7 = {
    "R_osc30_end660_ATR50::NQ": 1.653354,
    "Z_b15_e20_eff40_ATR50::NQ": 1.965598,
    "T_stop100_BE15R_calFalse::NQ": 0.768284,
    "V_nm25_noCap_mae30::NQ": 1.019769,
    "W_slope_allowReFalse_ATR25::NQ": 0.915674,
    "N_d5_fbTrue_ATR25::NQ": 1.252428,
    "SOMEOD_ext_NQ::NQ": 0.911410,
}
WEIGHTS_VW_SAT = {
    "V_nm25_noCap_mae30::NQ": 0.65,
    "W_slope_allowReFalse_ATR25::NQ": 0.60,
}
WEIGHTS_T_ONLY = {
    "T_stop100_BE15R_calFalse::NQ": 1.00,
}
WEIGHTS_SNIPERS_RZ = {
    "R_osc30_end660_ATR50::NQ": 0.732985,
    "Z_b15_e20_eff40_ATR50::NQ": 1.613336,
}


def _load_calibrated_nq_cfd_spread() -> float:
    """Read real median USATECHIDXUSD open/core weighted spread if Exp C output exists, else conservative 1.15."""
    if PHASE_SHIFT_CFD_CSV.exists():
        df = pd.read_csv(PHASE_SHIFT_CFD_CSV)
        sp = df[df.get("section", pd.Series(dtype=str)) == "SPREAD"]
        if not sp.empty:
            all_med = sp[sp["window"] == "ALL"]["median_pts"]
            if len(all_med):
                return float(all_med.iloc[0])
    return 1.15


def _load_all_streams() -> dict[str, Any]:
    """Load NQ Core7+SOMEOD, NQ R_ATR25, NQ O overnight, and ES adapted satellite streams."""
    t0 = time.perf_counter()
    print("[1/5] Loading NQ Core7 + SOMEOD streams (cached IL)...", flush=True)
    ops_all, atr_nq, orb_raw_nq, m1_arr_pre, meta = MP.construir_ops_todos_modulos_pre(workers=2)
    fric_nq, fric_mnq = IL.friccion_instrumento_puntos("NQ")
    pv_nq = float(meta["pv_nq"])

    # Build R_osc30_end660_ATR25 via M1 overlay with sl_atr_k=0.25
    r_spec = MP.CORE7_SPECS["R_osc30_end660_ATR50"]
    r_raw = IL._cargar_trades_cacheados(IL._cache_key("NQ", "R", r_spec["params"]))
    ops_all["R_osc30_end660_ATR25"] = MP.overlay_m1_por_particion(
        r_raw,
        "R",
        atr_nq,
        orb_raw_nq,
        m1_arr_pre,
        fric_nq,
        fric_mnq,
        particiones_ok=("DESC", "REP", "HOLDOUT", "EMBARGO"),
        permitir_terminal=False,
        sl_atr_k=0.25,
    )

    # Load NQ Overnight O (2008..2025-10-13)
    print("[2/5] Loading NQ Overnight (O) and ES adapted satellite modules...", flush=True)
    df_o_nq = pd.read_pickle(IL.CACHE_DIR / "NQ_fabrica_O.pkl")
    ops_o_50 = MA.convertir_ops_activo(df_o_nq, "O", "NQ", atr_nq, orb_raw_nq, pv_nq, stop_atr_k=0.50)
    ops_o_25 = MA.convertir_ops_activo(df_o_nq, "O", "NQ", atr_nq, orb_raw_nq, pv_nq, cap_mae_atr_k=0.25)

    # Load ES adapted satellite modules from MA.specs_etapa_b2_indices() + ES_fabrica_O
    atr_es, _, pv_es, _ = IL._cargar_series_sesion("ES")
    orb_es_map = MA.cargar_orb_ventanas("ES", [(570, 585)])
    orb_es = orb_es_map[(570, 585)]
    fric_es_mini, fric_es_micro = IL.friccion_instrumento_puntos("ES")

    es_wanted = {"ES__T_scaled_100", "ES__R_osc20_ATR50", "ES__V_scaled_nm30", "ES__N_scaled_ATR25", "ES__W_eod_ATR35", "ES__Z_eff35_ATR50"}
    es_specs = [sp for sp in MA.specs_etapa_b2_indices() if sp["variante"] in es_wanted]
    ops_es_map: dict[str, pd.DataFrame] = {}
    for sp in es_specs:
        cn = IL._cache_key("ES", sp["modulo"], sp["params"])
        df_t = IL._cargar_trades_cacheados(cn)
        ops_es_map[f"{sp['variante']}::ES"] = MA.convertir_ops_activo(
            df_t,
            sp["modulo"],
            "ES",
            atr_es,
            orb_es,
            pv_es,
            stop_atr_k=sp["stop_atr_k"],
            cap_mae_atr_k=sp["cap_mae_atr_k"],
            stop_orb_mult=sp["stop_orb_mult"],
            stop_min_pts=sp["stop_min_pts"],
            stop_max_pts=sp["stop_max_pts"],
        )

    df_o_es = pd.read_pickle(IL.CACHE_DIR / "ES_fabrica_O.pkl")
    ops_es_map["ES__O_overnight::ES"] = MA.convertir_ops_activo(df_o_es, "O", "ES", atr_es, orb_es, pv_es, stop_atr_k=0.50)

    # Build canonical session date lists (>= 20200101, <= 20260930) for DESC, REP, HOLDOUT
    all_nq_dates = sorted({
        int(x) for x in atr_nq.index.strftime("%Y%m%d").astype(int)
        if 20200101 <= int(x) <= 20260930 and a5_bloque(int(x)) in ("DESC", "REP", "HOLDOUT")
    })
    ses_by_part = {
        p: [d for d in all_nq_dates if a5_bloque(d) == p]
        for p in ("DESC", "REP", "HOLDOUT")
    }
    print(f"  Loaded in {time.perf_counter() - t0:.1f}s | sessions POST_2020: DESC={len(ses_by_part['DESC'])}, REP={len(ses_by_part['REP'])}, HOLDOUT={len(ses_by_part['HOLDOUT'])}", flush=True)
    return {
        "ops_all": ops_all,
        "ops_o_50": ops_o_50,
        "ops_o_25": ops_o_25,
        "ops_es_map": ops_es_map,
        "ses_by_part": ses_by_part,
        "fric_nq": fric_nq,
        "fric_mnq": fric_mnq,
        "fric_es": (fric_es_mini, fric_es_micro),
    }


def _extract_portfolio_tr(
    ops_all: Mapping[str, pd.DataFrame],
    weights: Mapping[str, float],
    fric_nq: float,
    part: str,
    cap_r: float = 3.0,
) -> pd.DataFrame:
    """Wrap MP.extraer_tr_particion using raw module keys extracted from `'mod::NQ'`."""
    mod_names = [k.split("::")[0] for k in weights]
    tr, _ = MP.extraer_tr_particion(ops_all, mod_names, weights, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=cap_r)
    return tr


def _daily_cfd_series(
    tr_df: pd.DataFrame,
    sesiones: list[int],
    spread_pts: float,
    usd_1r_cfd: float,
    contr_mult: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert coordinated trade stream to exact fractional CFD daily (P, LO, HI) in USD ($0 comm, pure spread)."""
    n_s = len(sesiones)
    idx_map = {int(s): i for i, s in enumerate(sesiones)}
    P = np.zeros(n_s, dtype=np.float64)
    LO = np.zeros(n_s, dtype=np.float64)
    HI = np.zeros(n_s, dtype=np.float64)
    if tr_df is None or tr_df.empty:
        return P, LO, HI

    df = tr_df[tr_df["w_eff"] > 1e-9].copy()
    if df.empty:
        return P, LO, HI

    rp = np.maximum(df["riesgo_pts"].to_numpy(np.float64), 1e-6)
    r_net_cfd = df["R_bruto"].to_numpy(np.float64) - (float(spread_pts) / rp)
    usd_j = r_net_cfd * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)
    if contr_mult != 1.0 and len(usd_j):
        usd_j = usd_j - (1.0 - float(contr_mult)) * float(np.mean(usd_j))

    mae_r = np.maximum(df["mae_pts"].to_numpy(np.float64) / rp, 0.0) if "mae_pts" in df.columns else np.maximum(-r_net_cfd, 0.0)
    mfe_r = np.maximum(df["mfe_pts"].to_numpy(np.float64) / rp, 0.0) if "mfe_pts" in df.columns else np.maximum(r_net_cfd, 0.0)
    adv_j = (mae_r + float(spread_pts) / rp) * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)
    fav_j = np.maximum(0.0, (mfe_r - float(spread_pts) / rp)) * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)

    fe = df["fecha_int"].to_numpy(np.int64)
    en = df["en_ns"].to_numpy(np.int64)
    ex = df["ex_ns"].to_numpy(np.int64)
    order = np.argsort(fe * 10**13 + (en % 10**13), kind="mergesort")
    fe, en, ex, usd_j, adv_j, fav_j = fe[order], en[order], ex[order], usd_j[order], adv_j[order], fav_j[order]

    pos = 0
    n = len(fe)
    while pos < n:
        f_cur = int(fe[pos])
        end = pos + 1
        while end < n and int(fe[end]) == f_cur:
            end += 1
        si = idx_map.get(f_cur, -1)
        if si >= 0:
            tot = float(np.sum(usd_j[pos:end]))
            lo_min = min(0.0, tot)
            hi_max = max(0.0, tot)
            for j in range(pos, end):
                tj = int(en[j])
                realized = 0.0
                open_a = float(adv_j[j])
                open_f = float(fav_j[j])
                for k in range(pos, j):
                    if int(ex[k]) <= tj:
                        realized += float(usd_j[k])
                    else:
                        open_a += float(adv_j[k])
                        open_f += float(fav_j[k])
                lo_min = min(lo_min, realized - open_a)
                hi_max = max(hi_max, realized + open_f)
            P[si] = tot
            LO[si] = lo_min
            HI[si] = hi_max
        pos = end
    return P, LO, HI


@nb.njit(cache=True)
def _sim_cfd_2phase_numba(
    P: np.ndarray,
    LO: np.ndarray,
    HI: np.ndarray,
    j_seq: np.ndarray,
    fee_usd: float,
    tgt_p1: float,
    tgt_p2: float,
    max_dd: float,
    dll: float,
    min_days_eval: int,
    payout_cycle: int,
    min_payout: float,
    split: float,
    refund_fee: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simulate 2-phase static-DD CFD prop challenge & funded payouts over synchronized j_seq paths."""
    N, H = j_seq.shape
    c12 = np.zeros(N, dtype=np.float64)
    c24 = np.zeros(N, dtype=np.float64)
    cmin = np.zeros(N, dtype=np.float64)
    r12 = np.zeros(N, dtype=np.float64)
    evals_tot = np.zeros(N, dtype=np.float64)

    t12_idx = min(251, H - 1)
    for n in range(N):
        phase = 1
        eq = 0.0
        active_days = 0
        fund_days = 0
        refunded = False
        cash = -fee_usd
        evals = 1.0
        min_cash = cash
        rets_12 = 0.0

        for t in range(H):
            j = j_seq[n, t]
            p = P[j]
            lo = LO[j]
            hi = HI[j]
            is_act = (p != 0.0) or (lo != 0.0) or (hi != 0.0)

            day_min_eq = eq + lo
            day_max_eq = eq + hi
            end_eq = eq + p
            breached = (day_min_eq <= -max_dd) or (lo <= -dll)

            if breached:
                phase = 1
                eq = 0.0
                active_days = 0
                fund_days = 0
                refunded = False
                cash -= fee_usd
                evals += 1.0
            else:
                if is_act:
                    active_days += 1
                    if phase == 3:
                        fund_days += 1

                if phase == 1:
                    if end_eq >= tgt_p1 and active_days >= min_days_eval:
                        phase = 2
                        eq = 0.0
                        active_days = 0
                    else:
                        eq = end_eq
                elif phase == 2:
                    if end_eq >= tgt_p2 and active_days >= min_days_eval:
                        phase = 3
                        eq = 0.0
                        active_days = 0
                        fund_days = 0
                        refunded = False
                    else:
                        eq = end_eq
                else:
                    eq = end_eq
                    if fund_days >= payout_cycle and eq >= min_payout:
                        pay = split * eq
                        if refund_fee and not refunded:
                            pay += fee_usd
                            refunded = True
                        cash += pay
                        if t <= t12_idx:
                            rets_12 += pay
                        eq = 0.0
                        fund_days = 0

            if cash < min_cash:
                min_cash = cash
            if t == t12_idx:
                c12[n] = cash
                r12[n] = rets_12

        c24[n] = cash
        cmin[n] = min_cash
        evals_tot[n] = evals
    return c12, c24, cmin, r12, evals_tot


def _eval_lifecycle_switch(
    cfg: Mapping[str, Any],
    tr_ev: pd.DataFrame,
    tr_fd: pd.DataFrame,
    sesiones: list[int],
    fric_nq: float,
    fric_mnq: float,
    part: str,
    contr_nom: str,
    contr_mult: float,
    j_seq: np.ndarray,
    label: str,
) -> dict[str, Any]:
    """Evaluate SingleModule role specialization (tr_ev in Eval phase -> tr_fd in Funded phase)."""
    max_mic = int(cfg["max_micros"])
    hib = bool(cfg.get("hibrido", True))
    pol = str(cfg.get("politica_colision", "independiente"))
    P_ev, LO_ev, HI_ev, _ = MP.construir_serie_intradia_prop_v2(
        tr_ev, sesiones, float(cfg["usd_ev"]), max_mic, hib, fric_nq, fric_mnq, contr_mult=contr_mult, politica_colision=pol
    )
    P_fd, LO_fd, HI_fd, _ = MP.construir_serie_intradia_prop_v2(
        tr_fd, sesiones, float(cfg["usd_fund"]), max_mic, hib, fric_nq, fric_mnq, contr_mult=contr_mult, politica_colision=pol
    )
    kw = MP._norm_multiprop_cfg(cfg)
    c12, c24, cmin, r12, r24, b12, _, _ = MP._trayectoria_multiprop_numba(P_ev, LO_ev, HI_ev, P_fd, LO_fd, HI_fd, j_seq, **kw)
    net12 = float(np.mean(c12))
    p10 = float(np.quantile(cmin, 0.10))
    return {
        "modo": label,
        "config_id": str(cfg["config_id"]),
        "particion": part,
        "regimen_media": contr_nom,
        "neto12_medio_usd": round(net12, 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "retiros_12m": round(float(np.mean(r12)), 2),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "caja_min_p10_usd": round(p10, 1),
        "ratio_net12_p10": round(net12 / max(abs(p10), 100.0), 3),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CATALOGO_JSON, "r", encoding="utf-8") as f:
        cat = json.load(f)
    cfg_map = {c["config_id"]: c for c in cat["perfiles_simulacion_etapa_c"]}

    data = _load_all_streams()
    ops_all = data["ops_all"]
    ops_es_map = data["ops_es_map"]
    ses_by_part = data["ses_by_part"]
    fric_nq, fric_mnq = data["fric_nq"], data["fric_mnq"]
    fric_es_fut, _ = data["fric_es"]
    spread_nq_cfd = _load_calibrated_nq_cfd_spread()
    spread_es_cfd = 0.35  # US500 pure spread conservative
    print(f"  Using calibrated CFD spreads: NQ/USATECH={spread_nq_cfd:.3f} pts, ES/US500={spread_es_cfd:.2f} pts", flush=True)

    # ------------------------------------------------------------------
    # Section 1: Daily return correlations & Personal Uncapped Blend
    # ------------------------------------------------------------------
    print("[3/5] Computing cross-sleeve correlations & Personal Account blend...", flush=True)
    eval_dates_rep_hold = sorted(ses_by_part["REP"] + ses_by_part["HOLDOUT"])

    def _sleeve_daily_r(tr_df: pd.DataFrame, idx: list[int], spread_pts: float | None = None) -> pd.Series:
        if tr_df.empty:
            return pd.Series(0.0, index=idx)
        w = tr_df["w_eff"].to_numpy(np.float64)
        if spread_pts is not None:
            r_u = (tr_df["R_bruto"].to_numpy(np.float64) - spread_pts / np.maximum(tr_df["riesgo_pts"].to_numpy(np.float64), 1e-6)) * w
        else:
            r_u = tr_df["R_neto_mini"].to_numpy(np.float64) * w
        return pd.Series(r_u, index=tr_df["fecha_int"]).groupby(level=0).sum().reindex(idx, fill_value=0.0)

    es_keys_core = [k for k in ops_es_map if "O_overnight" not in k]
    es_w = {k: 1.0 / max(len(es_keys_core), 1) for k in es_keys_core}

    # Combine REP + HOLDOUT daily series per sleeve
    ser_map: dict[str, list[pd.Series]] = {k: [] for k in ["Core5_NQ", "Core5_R25_NQ", "VW_NQ", "T_Only_NQ", "Snipers_RZ_NQ", "O_NQ_50", "O_NQ_25", "ES_Core_Fut", "ES_Core_CFD"]}
    for part in ("DESC", "REP", "HOLDOUT"):
        ses_p = ses_by_part[part]
        tr_c5 = _extract_portfolio_tr(ops_all, WEIGHTS_CORE5, fric_nq, part, cap_r=3.0)
        tr_c5_25 = _extract_portfolio_tr(ops_all, WEIGHTS_CORE5_R25, fric_nq, part, cap_r=3.0)
        tr_vw = _extract_portfolio_tr(ops_all, WEIGHTS_VW_SAT, fric_nq, part, cap_r=2.0)
        tr_t = _extract_portfolio_tr(ops_all, WEIGHTS_T_ONLY, fric_nq, part, cap_r=1.5)
        tr_rz = _extract_portfolio_tr(ops_all, WEIGHTS_SNIPERS_RZ, fric_nq, part, cap_r=2.0)

        es_sub = {k: v[(v["a5"] == part) & (v["fecha_int"] >= 20200101) & (v["fecha_int"] <= 20260930)].copy() for k, v in ops_es_map.items() if k in es_keys_core}
        tr_es, _ = IT2.aplicar_tope_concurrencia_causal(es_sub, es_w, None, cap_r=2.0)
        tr_es = MP._reinyectar_campos_ops(tr_es, es_sub, fric_es_fut)

        o50_sub = data["ops_o_50"][(data["ops_o_50"]["a5"] == part) & (data["ops_o_50"]["fecha_int"] >= 20200101)]
        o25_sub = data["ops_o_25"][(data["ops_o_25"]["a5"] == part) & (data["ops_o_25"]["fecha_int"] >= 20200101)]
        tr_o50, _ = IT2.aplicar_tope_concurrencia_causal({"O::NQ": o50_sub}, {"O::NQ": 1.0}, None, cap_r=1.0)
        tr_o50 = MP._reinyectar_campos_ops(tr_o50, {"O::NQ": o50_sub}, fric_nq)
        tr_o25, _ = IT2.aplicar_tope_concurrencia_causal({"O::NQ": o25_sub}, {"O::NQ": 1.0}, None, cap_r=1.0)
        tr_o25 = MP._reinyectar_campos_ops(tr_o25, {"O::NQ": o25_sub}, fric_nq)

        if part in ("REP", "HOLDOUT"):
            ser_map["Core5_NQ"].append(_sleeve_daily_r(tr_c5, ses_p))
            ser_map["Core5_R25_NQ"].append(_sleeve_daily_r(tr_c5_25, ses_p))
            ser_map["VW_NQ"].append(_sleeve_daily_r(tr_vw, ses_p))
            ser_map["T_Only_NQ"].append(_sleeve_daily_r(tr_t, ses_p))
            ser_map["Snipers_RZ_NQ"].append(_sleeve_daily_r(tr_rz, ses_p))
            ser_map["O_NQ_50"].append(_sleeve_daily_r(tr_o50, ses_p))
            ser_map["O_NQ_25"].append(_sleeve_daily_r(tr_o25, ses_p))
            ser_map["ES_Core_Fut"].append(_sleeve_daily_r(tr_es, ses_p))
            ser_map["ES_Core_CFD"].append(_sleeve_daily_r(tr_es, ses_p, spread_pts=spread_es_cfd))

    df_oos = pd.DataFrame({k: pd.concat(v).sort_index() for k, v in ser_map.items()})
    # Correlation over overlapping active period <= 20251013 so O zeros after 2025-10-13 do not bias corr
    df_corr_win = df_oos[df_oos.index <= 20251013]
    corr_mat = df_corr_win[["Core5_NQ", "VW_NQ", "O_NQ_50", "O_NQ_25", "ES_Core_CFD", "Core5_R25_NQ"]].corr()
    corr_mat.to_csv(OUT_DIR / "correlacion_satelites.csv")

    # Personal Uncapped Blend over OOS active window <= 20251013 and full 2020-2026
    pers_rows = []
    # Normalize each sleeve to daily target risk = 1.0 (sum w = 1) or compare personal dollar/R curves
    blend_1 = 0.50 * df_oos["Core5_NQ"] + 0.25 * df_oos["VW_NQ"] + 0.25 * df_oos["ES_Core_CFD"]
    blend_full_win = (0.45 * df_corr_win["Core5_NQ"] + 0.20 * df_corr_win["VW_NQ"] + 0.15 * df_corr_win["O_NQ_25"] + 0.20 * df_corr_win["ES_Core_CFD"])
    for label, s_r in [
        ("Core5_NQ (2020-26 OOS)", df_oos["Core5_NQ"]),
        ("VW_NQ (2020-26 OOS)", df_oos["VW_NQ"]),
        ("ES_Core_CFD (2020-26 OOS)", df_oos["ES_Core_CFD"]),
        ("Personal_3_Sleeves (2020-26 OOS)", blend_1),
        ("Core5_NQ (<=2025-10 OOS)", df_corr_win["Core5_NQ"]),
        ("O_Overnight_Cap25 (<=2025-10 OOS)", df_corr_win["O_NQ_25"]),
        ("Personal_4_Sleeves+O (<=2025-10 OOS)", blend_full_win),
    ]:
        arr = s_r.to_numpy(np.float64)
        tot = float(arr.sum())
        std_d = float(arr.std(ddof=1)) if len(arr) > 1 else 1e-9
        sh = (float(arr.mean()) / max(std_d, 1e-9)) * math.sqrt(252.0)
        eq = np.cumsum(arr)
        dd = float((eq - np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]).min())
        meses = max(len(arr) / 21.0, 1.0)
        cal = (tot / (meses / 12.0)) / max(abs(dd), 1e-6)
        pers_rows.append({
            "sleeve": label,
            "n_dias": len(arr),
            "sum_R_equiv": round(tot, 2),
            "R_mes": round(tot / meses, 3),
            "Sharpe": round(sh, 2),
            "MaxDD_R": round(dd, 2),
            "Calmar": round(cal, 2),
        })
    pers_df = pd.DataFrame(pers_rows)
    pers_df.to_csv(OUT_DIR / "personal_blend_resumen.csv", index=False)

    # ------------------------------------------------------------------
    # Section 2: Futures Multi-Prop Synced MC (N=2000, H=504)
    # ------------------------------------------------------------------
    print("[4/5] Running Futures Multi-Prop Synced Monte Carlo (2000 paths x 504d)...", flush=True)
    arch_rows = []
    single_fut_rows = []
    lifecycle_rows = []

    regimes = [("REP", "100%", 1.0), ("REP", "60%", 0.60), ("HOLDOUT", "100%", 1.0)]
    for part, cnom, cmult in regimes:
        ses_p = ses_by_part[part]
        j_seq = MP.generar_j_seq_bootstrap(len(ses_p), N=2000, H=504, seed=20261122)

        tr_c5 = _extract_portfolio_tr(ops_all, WEIGHTS_CORE5, fric_nq, part, cap_r=3.0)
        tr_p7 = _extract_portfolio_tr(ops_all, WEIGHTS_P7, fric_nq, part, cap_r=3.0)
        tr_c5_25 = _extract_portfolio_tr(ops_all, WEIGHTS_CORE5_R25, fric_nq, part, cap_r=3.0)
        tr_vw = _extract_portfolio_tr(ops_all, WEIGHTS_VW_SAT, fric_nq, part, cap_r=2.0)
        tr_t = _extract_portfolio_tr(ops_all, WEIGHTS_T_ONLY, fric_nq, part, cap_r=1.5)
        tr_rz = _extract_portfolio_tr(ops_all, WEIGHTS_SNIPERS_RZ, fric_nq, part, cap_r=2.0)

        # Primary 4 accounts (2x LucidFlex 150K + 2x Tradeify 150K)
        r_luc_c5, f_luc_c5 = MP.evaluar_config_multiprop(cfg_map["MP_LucidFlex_150K_promo"], tr_c5, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_trd_c5, f_trd_c5 = MP.evaluar_config_multiprop(cfg_map["MP_Tradeify_150K_promo"], tr_c5, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)

        r_luc_p7, f_luc_p7 = MP.evaluar_config_multiprop(cfg_map["MP_LucidFlex_150K_promo"], tr_p7, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_trd_p7, f_trd_p7 = MP.evaluar_config_multiprop(cfg_map["MP_Tradeify_150K_promo"], tr_p7, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)

        r_luc_r25, f_luc_r25 = MP.evaluar_config_multiprop(cfg_map["MP_LucidFlex_150K_promo"], tr_c5_25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_trd_r25, f_trd_r25 = MP.evaluar_config_multiprop(cfg_map["MP_Tradeify_150K_promo"], tr_c5_25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)

        # Cheap accounts running V+W satellite independently
        r_bul_vw, f_bul_vw = MP.evaluar_config_multiprop(cfg_map["MP_Bulenox_Opt2_150K_promo"], tr_vw, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_fn_vw, f_fn_vw = MP.evaluar_config_multiprop(cfg_map["MP_FundedNext_50K_promo"], tr_vw, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_l50_vw, f_l50_vw = MP.evaluar_config_multiprop(cfg_map["MP_LucidFlex_50K_promo"], tr_vw, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)
        r_ts_vw, f_ts_vw = MP.evaluar_config_multiprop(cfg_map["MP_Topstep_NoAct_50K"], tr_vw, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq)

        for r_item, s_name in [(r_bul_vw, "VW_Bulenox150 ($65)"), (r_fn_vw, "VW_FundedNext50 ($80)"), (r_l50_vw, "VW_Lucid50 ($95)"), (r_ts_vw, "VW_Topstep50 ($95)")]:
            single_fut_rows.append({
                "sleeve_account": s_name,
                "particion": part,
                "regimen_media": cnom,
                "fee_sim": r_item["fee_sim_usd"],
                "act_fee": r_item["act_fee_usd"],
                "neto12_medio_usd": r_item["neto12_medio_usd"],
                "neto24_medio_usd": r_item["neto24_medio_usd"],
                "p_neto12_pos_pct": r_item["p_neto12_pos_pct"],
                "caja_min_p10_usd": r_item["caja_min_p10_usd"],
                "retiros_12m": r_item["retiros_12m"],
            })

        # Multi-firm architectures (4 base accounts vs +2 cheap V+W accounts vs R25 vs P7)
        arch_rows.append(MP.agregar_arquitectura_multifirma(
            "A0_Core5_4CTA", "Base Core5_AltaConv (2 Lucid150 + 2 Tradeify150)",
            [(r_luc_c5, 2.0, f_luc_c5), (r_trd_c5, 2.0, f_trd_c5)], part, cnom
        ))
        arch_rows.append(MP.agregar_arquitectura_multifirma(
            "A0_P7_4CTA", "Merged P_OPT_SF_v2 (2 Lucid150 + 2 Tradeify150)",
            [(r_luc_p7, 2.0, f_luc_p7), (r_trd_p7, 2.0, f_trd_p7)], part, cnom
        ))
        arch_rows.append(MP.agregar_arquitectura_multifirma(
            "A1_Core5_plus_VW_BulFN", "Core5 (4 CTA) + V+W Sat (1 Bulenox150 + 1 FundedNext50)",
            [(r_luc_c5, 2.0, f_luc_c5), (r_trd_c5, 2.0, f_trd_c5), (r_bul_vw, 1.0, f_bul_vw), (r_fn_vw, 1.0, f_fn_vw)], part, cnom
        ))
        arch_rows.append(MP.agregar_arquitectura_multifirma(
            "A1b_Core5_plus_VW_Lucid50", "Core5 (4 CTA) + V+W Sat (2 LucidFlex 50K)",
            [(r_luc_c5, 2.0, f_luc_c5), (r_trd_c5, 2.0, f_trd_c5), (r_l50_vw, 2.0, f_l50_vw)], part, cnom
        ))
        arch_rows.append(MP.agregar_arquitectura_multifirma(
            "A2_Core5_R25_4CTA", "Core5 swap R_ATR25 (2 Lucid150 + 2 Tradeify150)",
            [(r_luc_r25, 2.0, f_luc_r25), (r_trd_r25, 2.0, f_trd_r25)], part, cnom
        ))

        # Lifecycle SingleModule Specialization on MP_LucidFlex_150K_promo
        luc150 = cfg_map["MP_LucidFlex_150K_promo"]
        lifecycle_rows.append(_eval_lifecycle_switch(luc150, tr_c5, tr_c5, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Base: Core5 -> Core5"))
        lifecycle_rows.append(_eval_lifecycle_switch(luc150, tr_t, tr_c5, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "SpeedEval: T_Only -> Core5"))
        lifecycle_rows.append(_eval_lifecycle_switch(luc150, tr_c5, tr_rz, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "CushionFund: Core5 -> SnipersRZ"))
        lifecycle_rows.append(_eval_lifecycle_switch(luc150, tr_t, tr_rz, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "T_Only -> SnipersRZ"))

    # ------------------------------------------------------------------
    # Section 3: 2-Phase Static-DD CFD Simulator (FTMO Swing 100K & The5ers HS 100K)
    # ------------------------------------------------------------------
    print("[5/5] Running 2-phase static-DD CFD Prop MC (FTMO Swing 100K + The5ers 100K)...", flush=True)
    cfd_rows = []
    cfd_firms = [
        ("FTMO_Swing_100K", 540.0, 10000.0, 5000.0, 10000.0, 5000.0, 4, 14, 500.0, 0.80, True),
        ("The5ers_HighStakes_100K", 495.0, 8000.0, 5000.0, 10000.0, 5000.0, 3, 14, 500.0, 0.80, True),
    ]
    # Compare: (a) Full 2020-2026 REP & HOLDOUT for Core5 vs ES_Core vs Core5+ES;
    # (b) <=2025-10-13 REP & HOLDOUT for Core5 vs Core5+O vs O_Solo vs Master (Core5+O+ES)!
    for win_tag, max_fecha in [("FULL_2020_2026", 20260930), ("O_WINDOW_2020_202510", 20251013)]:
        for part in ("REP", "HOLDOUT"):
            ses_p = [d for d in ses_by_part[part] if d <= max_fecha]
            j_seq = MP.generar_j_seq_bootstrap(len(ses_p), N=2000, H=504, seed=20261123)

            tr_c5 = _extract_portfolio_tr(ops_all, WEIGHTS_CORE5, fric_nq, part, cap_r=3.0)
            tr_c5 = tr_c5[tr_c5["fecha_int"] <= max_fecha]

            es_sub = {k: v[(v["a5"] == part) & (v["fecha_int"] >= 20200101) & (v["fecha_int"] <= max_fecha)].copy() for k, v in ops_es_map.items() if k in es_keys_core}
            tr_es, _ = IT2.aplicar_tope_concurrencia_causal(es_sub, es_w, None, cap_r=2.0)
            tr_es = MP._reinyectar_campos_ops(tr_es, es_sub, fric_es_fut)

            P_c5, LO_c5, HI_c5 = _daily_cfd_series(tr_c5, ses_p, spread_nq_cfd, usd_1r_cfd=550.0)
            P_es, LO_es, HI_es = _daily_cfd_series(tr_es, ses_p, spread_es_cfd, usd_1r_cfd=550.0)

            configs_cfd = [
                ("CFD_Core5_NQ", P_c5, LO_c5, HI_c5),
                ("CFD_ES_US500_Core", P_es, LO_es, HI_es),
                ("CFD_NQ_plus_ES", P_c5 + 0.55 * P_es, LO_c5 + 0.55 * LO_es, HI_c5 + 0.55 * HI_es),
            ]
            if max_fecha == 20251013:
                o25_sub = data["ops_o_25"][(data["ops_o_25"]["a5"] == part) & (data["ops_o_25"]["fecha_int"] >= 20200101) & (data["ops_o_25"]["fecha_int"] <= max_fecha)]
                tr_o, _ = IT2.aplicar_tope_concurrencia_causal({"O::NQ": o25_sub}, {"O::NQ": 1.0}, None, cap_r=1.0)
                tr_o = MP._reinyectar_campos_ops(tr_o, {"O::NQ": o25_sub}, fric_nq)
                P_o, LO_o, HI_o = _daily_cfd_series(tr_o, ses_p, spread_nq_cfd, usd_1r_cfd=550.0)
                # O is strictly overnight (16:00 -> 09:30), disjoint intrabar from Core5 RTH!
                configs_cfd.append(("CFD_O_Overnight_Solo", P_o, LO_o, HI_o))
                configs_cfd.append(("CFD_Core5_plus_O", P_c5 + P_o, np.minimum(LO_c5, P_c5 + LO_o), np.maximum(HI_c5, P_c5 + HI_o)))
                configs_cfd.append(("CFD_Master_NQ_O_ES", P_c5 + P_o + 0.55 * P_es, np.minimum(LO_c5 + 0.55 * LO_es, P_c5 + P_o + 0.55 * LO_es), np.maximum(HI_c5 + 0.55 * HI_es, P_c5 + P_o + 0.55 * HI_es)))

            for firm_name, fee, t1, t2, mdd, dll, mdays, cyc, minp, sp, ref in cfd_firms:
                if win_tag == "FULL_2020_2026" and firm_name == "The5ers_HighStakes_100K" or True:
                    pass
                for cname, Pc, LOc, HIc in configs_cfd:
                    c12, c24, cmin, r12, evals = _sim_cfd_2phase_numba(
                        Pc, LOc, HIc, j_seq, fee, t1, t2, mdd, dll, mdays, cyc, minp, sp, ref
                    )
                    net12 = float(np.mean(c12))
                    p10 = float(np.quantile(cmin, 0.10))
                    cfd_rows.append({
                        "window": win_tag,
                        "particion": part,
                        "firm": firm_name,
                        "strategy": cname,
                        "neto12_medio_usd": round(net12, 1),
                        "neto24_medio_usd": round(float(np.mean(c24)), 1),
                        "retiros_12m_usd": round(float(np.mean(r12)), 1),
                        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
                        "caja_min_p10_usd": round(p10, 1),
                        "evals_24m_media": round(float(np.mean(evals)), 2),
                        "ratio_net12_p10": round(net12 / max(abs(p10), 100.0), 3),
                    })

    arch_df = pd.DataFrame(arch_rows)
    single_df = pd.DataFrame(single_fut_rows)
    life_df = pd.DataFrame(lifecycle_rows)
    cfd_df = pd.DataFrame(cfd_rows)

    all_mc = pd.concat([
        arch_df.assign(tabla="FUTURES_ARCH"),
        single_df.assign(tabla="FUTURES_VW_CHEAP"),
        life_df.assign(tabla="LIFECYCLE_SPEC"),
        cfd_df.assign(tabla="CFD_2PHASE"),
    ], ignore_index=True)
    all_mc.to_csv(OUT_DIR / "mc_arquitecturas_satelites.csv", index=False)

    _plot_satellites(corr_mat, arch_df, cfd_df, df_oos, df_corr_win)
    _write_report(corr_mat, pers_df, arch_df, single_df, life_df, cfd_df, spread_nq_cfd, spread_es_cfd)
    print(f"DONE -> {OUT_DIR}", flush=True)
    return 0


def _plot_satellites(
    corr_mat: pd.DataFrame,
    arch_df: pd.DataFrame,
    cfd_df: pd.DataFrame,
    df_oos: pd.DataFrame,
    df_corr_win: pd.DataFrame,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.8), facecolor=BG_FIG)
    fig.subplots_adjust(hspace=0.35, wspace=0.24, top=0.90, bottom=0.08, left=0.07, right=0.97)
    fig.suptitle(
        "Monetizacion de Estrategias Excluidas: Satelites Futuros, Overnight CFD, US500 y Personal (OOS REP+HOLDOUT)",
        color=FG_TEXT,
        fontsize=13.5,
        fontweight="bold",
    )
    for ax in axes.flat:
        ax.set_facecolor(BG_AX)
        ax.tick_params(colors=MUTED_TEXT, labelsize=8.5)
        ax.grid(True, color=GRID_COL, alpha=0.45, linewidth=0.7)
        for sp in ax.spines.values():
            sp.set_color("#2e3f47")

    # 1. Correlation Heatmap
    ax = axes[0, 0]
    ax.grid(False)
    labels = ["Core5", "V+W", "O (0.5)", "O (0.25)", "ES CFD", "Core5 R25"]
    mat = corr_mat.to_numpy(np.float64)
    im = ax.imshow(mat, cmap="coolwarm", vmin=-0.3, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, rotation=22, fontsize=8.5)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels, fontsize=8.5)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", color="#0b0f12" if mat[i, j] > 0.45 else FG_TEXT, fontsize=8.5, fontweight="bold")
    ax.set_title("Correlacion Diaria OOS (<=2025-10-13)", color=FG_TEXT, fontsize=11, fontweight="bold")

    # 2. Futures Architectures REP 100% vs HOLDOUT 100% Net 12m
    ax = axes[0, 1]
    order_a = ["A0_Core5_4CTA", "A0_P7_4CTA", "A1_Core5_plus_VW_BulFN", "A1b_Core5_plus_VW_Lucid50", "A2_Core5_R25_4CTA"]
    lbl_a = ["Core5 (4)", "P7 Merged (4)", "Core5 + VW\n(Bul+FN)", "Core5 + VW\n(Luc50)", "Core5 R25 (4)"]
    rep_v = arch_df[(arch_df["particion"] == "REP") & (arch_df["regimen_media"] == "100%")].set_index("arquitectura").reindex(order_a)["neto12_medio_usd"].to_numpy()
    hld_v = arch_df[(arch_df["particion"] == "HOLDOUT") & (arch_df["regimen_media"] == "100%")].set_index("arquitectura").reindex(order_a)["neto12_medio_usd"].to_numpy()
    x = np.arange(len(order_a))
    ax.bar(x - 0.18, rep_v / 1000.0, width=0.35, color=ACCENT_TEAL, label="REP 100%")
    ax.bar(x + 0.18, hld_v / 1000.0, width=0.35, color=ACCENT_GOLD, label="HOLDOUT 100%")
    ax.axhline(0.0, color="#6c7d86", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(lbl_a, fontsize=8)
    ax.set_title("Prop Futuros: Neto Medio 12m (Miles USD, 2000 paths)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Neto 12m (k USD)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # 3. CFD 2-Phase Static-DD (FTMO Swing 100K, O window)
    ax = axes[1, 0]
    sub_cfd = cfd_df[(cfd_df["window"] == "O_WINDOW_2020_202510") & (cfd_df["firm"] == "FTMO_Swing_100K")]
    strats = ["CFD_Core5_NQ", "CFD_O_Overnight_Solo", "CFD_Core5_plus_O", "CFD_ES_US500_Core", "CFD_Master_NQ_O_ES"]
    s_lbl = ["Core5 CFD", "O Solo", "Core5 + O", "ES/US500", "Master\nNQ+O+ES"]
    r_cfd = sub_cfd[sub_cfd["particion"] == "REP"].set_index("strategy").reindex(strats)["neto12_medio_usd"].to_numpy()
    h_cfd = sub_cfd[sub_cfd["particion"] == "HOLDOUT"].set_index("strategy").reindex(strats)["neto12_medio_usd"].to_numpy()
    x2 = np.arange(len(strats))
    ax.bar(x2 - 0.18, r_cfd / 1000.0, width=0.35, color=ACCENT_BLUE, label="REP")
    ax.bar(x2 + 0.18, h_cfd / 1000.0, width=0.35, color=ACCENT_GREEN, label="HOLDOUT")
    ax.axhline(0.0, color="#6c7d86", lw=0.8)
    ax.set_xticks(x2)
    ax.set_xticklabels(s_lbl, fontsize=8)
    ax.set_title("CFD FTMO Swing 100K (0 comm + spread real): Neto 12m", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_ylabel("Neto 12m (k USD)", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.5)

    # 4. Personal Uncapped Account cumulative OOS curves (normalized R equiv <= 20251013)
    ax = axes[1, 1]
    blend = 0.45 * df_corr_win["Core5_NQ"] + 0.20 * df_corr_win["VW_NQ"] + 0.15 * df_corr_win["O_NQ_25"] + 0.20 * df_corr_win["ES_Core_CFD"]
    ax.plot(df_corr_win["Core5_NQ"].cumsum().to_numpy(), color=ACCENT_TEAL, lw=1.8, label="Core5 NQ")
    ax.plot(df_corr_win["VW_NQ"].cumsum().to_numpy(), color=ACCENT_CORAL, lw=1.4, label="V + W NQ")
    ax.plot(df_corr_win["O_NQ_25"].cumsum().to_numpy(), color=ACCENT_GOLD, lw=1.4, label="O Overnight (cap 0.25)")
    ax.plot(df_corr_win["ES_Core_CFD"].cumsum().to_numpy(), color=ACCENT_BLUE, lw=1.4, label="ES / US500 CFD")
    ax.plot(blend.cumsum().to_numpy(), color="#ffffff", lw=2.2, ls="--", label="Blend Personal (4 sleeves)")
    ax.set_title("Cuenta Personal Sin Tope DD: Curvas OOS (<=2025-10-13)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax.set_xlabel("Sesiones OOS (REP + HOLDOUT)", color=MUTED_TEXT, fontsize=9)
    ax.set_ylabel("R Equivalentes Acumulados", color=MUTED_TEXT, fontsize=9)
    ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8)

    p1 = OUT_DIR / "satelites_monetizacion_prop.png"
    p2 = ARTIFACT_DIR / "satelites_monetizacion_prop.png"
    fig.savefig(p1, dpi=150, facecolor=BG_FIG)
    shutil.copy2(p1, p2)
    plt.close(fig)


def _write_report(
    corr_mat: pd.DataFrame,
    pers_df: pd.DataFrame,
    arch_df: pd.DataFrame,
    single_df: pd.DataFrame,
    life_df: pd.DataFrame,
    cfd_df: pd.DataFrame,
    spread_nq_cfd: float,
    spread_es_cfd: float,
) -> None:
    lines = [
        "# Propuestas Cuantificadas para Monetizar Estrategias Rentables Excluidas de Core5_AltaConv",
        "",
        f"- **Universo evaluado**: Simulaciones Monte Carlo sincronizadas (`N=2000`, `H=504` dias = 24 meses, misma matriz `j_seq` por particion) sobre `POST_2020` (`2020-01-01..2026-09-30` en `REP 100%`, `REP 60%` y `HOLDOUT`), y ventana `<= 2025-10-13` para analisis exacto del modulo overnight `O` (`NQ_fabrica_O.pkl`).",
        f"- **Friccion CFD calibrada**: `$0` comision + spread mediano `USATECHIDXUSD = {spread_nq_cfd:.3f}` pts en NQ CFD (`US500 = {spread_es_cfd:.2f}` pts en ES CFD).",
        "",
        "## 1. Matriz de Correlacion OOS entre Sleeves (<= 2025-10-13, REP + HOLDOUT)",
        "",
        corr_mat.round(3).to_markdown(),
        "",
        "## 2. Propuesta 1: Cuentas 'Call-Option' Separadas (`V + W`) vs Fusionar en `P_OPT_SF_v2`",
        "",
        "| Arquitectura | Part | Regimen | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Retiros 12m | Caja Min p10 (USD) | Neto/p10 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in arch_df.iterrows():
        lines.append(
            f"| `{r['arquitectura']}` | {r['particion']} | {r['regimen_media']} | {r['neto12_medio_usd']:,.1f} | {r['neto24_medio_usd']:,.1f} | {r['p_neto12_pos_pct']:.1f}% | {r['retiros_12m']:.2f} | {r['caja_min_p10_usd']:,.1f} | {r['ratio_net12_p10']:.3f} |"
        )
    lines += [
        "",
        "### Desempeno Aislado de `(V + W)` en Cuentas Promo Baratas",
        "",
        "| Cuenta / Sleeve | Part | Regimen | Fee Eval | Act Fee | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Caja p10 (USD) | Ret 12m |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in single_df[single_df["regimen_media"] == "100%"].iterrows():
        lines.append(
            f"| `{r['sleeve_account']}` | {r['particion']} | {r['regimen_media']} | {r['fee_sim']:.2f} | {r['act_fee']:.2f} | {r['neto12_medio_usd']:,.1f} | {r['neto24_medio_usd']:,.1f} | {r['p_neto12_pos_pct']:.1f}% | {r['caja_min_p10_usd']:,.1f} | {r['retiros_12m']:.2f} |"
        )

    lines += [
        "",
        "## 3. Propuestas 2 y 3: Desbloquear `O` Overnight y Satelite `ES/US500` en Props CFD Static-DD",
        "",
        "| Ventana | Firma CFD | Part | Estrategia | Neto 12m (USD) | Neto 24m (USD) | Retiros 12m (USD) | P(Net>0) | Caja p10 (USD) | Evals 24m |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in cfd_df.iterrows():
        lines.append(
            f"| {r['window']} | `{r['firm']}` | {r['particion']} | `{r['strategy']}` | {r['neto12_medio_usd']:,.1f} | {r['neto24_medio_usd']:,.1f} | {r['retiros_12m_usd']:,.1f} | {r['p_neto12_pos_pct']:.1f}% | {r['caja_min_p10_usd']:,.1f} | {r['evals_24m_media']:.2f} |"
        )

    lines += [
        "",
        "## 4. Propuesta 4: Swap `R_maeATR25` y Especializacion de Ciclo de Vida (`EdgeLabFundedSyncSingleModule`)",
        "",
        "| Modo Ciclo de Vida (`LucidFlex 150K`) | Part | Regimen | Neto 12m (USD) | Neto 24m (USD) | P(Net>0) | Retiros 12m | Caja p10 (USD) | Neto/p10 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in life_df[life_df["regimen_media"] == "100%"].iterrows():
        lines.append(
            f"| `{r['modo']}` | {r['particion']} | {r['regimen_media']} | {r['neto12_medio_usd']:,.1f} | {r['neto24_medio_usd']:,.1f} | {r['p_neto12_pos_pct']:.1f}% | {r['retiros_12m']:.2f} | {r['caja_min_p10_usd']:,.1f} | {r['ratio_net12_p10']:.3f} |"
        )

    lines += [
        "",
        "## 5. Propuesta 5: Cuenta Personal Sin Topes DD + Cartera Ortogonal `cartera_20261116`",
        "",
        "| Sleeve / Blend Personal | N dias OOS | Sum R Equiv | R / mes | Sharpe | MaxDD R | Calmar |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in pers_df.iterrows():
        lines.append(
            f"| `{r['sleeve']}` | {int(r['n_dias'])} | {r['sum_R_equiv']:+.2f} | {r['R_mes']:+.3f} | {r['Sharpe']:.2f} | {r['MaxDD_R']:+.2f} | {r['Calmar']:.2f} |"
        )
    lines += [
        "",
        "- **Bloque ortogonal externo (`cartera_20261116`)**: 8 reglas multi-indice/multi-activo (`NQ, ES, YM, RTY, CL, MGC`) con correlacion cruzada cercana a cero (`rho ~= -0.02`) y `+15.9 R` en el holdout reciente de oct-nov 2026 segun `docs/research/cartera_20261116/RESULTADO.md`, aplicable como manga paralela en cuentas personales o satelite futuros.",
    ]

    (OUT_DIR / "RESULTADO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
