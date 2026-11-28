#!/usr/bin/env python3
"""Kaggle Kernel v2 (Auditado): CSCV limpio (Carril2 & No-CME) vs Descriptivo CME, DSR (N=1..5000), Bayes y Boot 20k semanal a 10% vol."""
import base64, gzip, itertools, json, os, time
from math import erf, sqrt
from pathlib import Path
import numpy as np
from numba import njit

PAYLOAD_B64 = "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"
D = json.loads(gzip.decompress(base64.b64decode(PAYLOAD_B64)).decode("utf-8"))


def phi(z):
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def dsr_prob(ret_m, n_trials):
    ret_m = ret_m[np.isfinite(ret_m)]
    T = len(ret_m)
    if T < 6 or np.std(ret_m, ddof=1) == 0:
        return {"sr_anual": 0.0, "dsr": 0.0}
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
    return {"sr_anual": round(sr_ann, 3), "skew": round(skew, 3), "kurt": round(kurt, 3), "dsr": round(phi(z_dsr), 4)}


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
    return {
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
    }


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
    return {
        "sr_obs": round(sr_obs, 3),
        "T_months": int(T_m),
        "upstream_selection_caveat": bool(caveat),
        "post_mean": round(post_mu, 3),
        "post_sd": round(post_sd, 3),
        "P_true_gt_0": round(1.0 - phi((0.0 - post_mu) / post_sd), 4),
        "P_true_gt_05": round(1.0 - phi((0.5 - post_mu) / post_sd), 4),
        "P_true_gt_10": round(1.0 - phi((1.0 - post_mu) / post_sd), 4),
    }


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

    cscv_out = {
        "1_clean_carril2_16rules": run_cscv(m_c2, S=16, tag="LIMPIO_SIN_CME"),
        "2_clean_non_cme_21rules": run_cscv(m_nc, S=16, tag="LIMPIO_SIN_CME"),
        "3_descriptive_with_cme": run_cscv(m_al, S=16, tag="DESCRIPTIVO_SESGO_VENDEDOR_CME"),
    }

    dsr_out = {}
    eb_out = {}
    for j, cname in enumerate(p_cols):
        col_v = p_m[:, j]
        col_v = col_v[np.isfinite(col_v)]
        dsr_out[cname] = {f"N_{nt}": dsr_prob(col_v, nt) for nt in (1, 10, 50, 200, 500, 5000)}
        dsr_out[cname]["upstream_selection_caveat"] = bool(cav.get(cname, True))
        sr_obs = float(np.mean(col_v) / max(np.std(col_v, ddof=1), 1e-9) * sqrt(12.0))
        eb_out[cname] = empirical_bayes_posterior(sr_obs, len(col_v), cav.get(cname, True))

    boot_out = {}
    for j, cname in enumerate(w_cols):
        yw = w_bt[:, j]
        yw = yw[np.isfinite(yw)]
        sd_w = float(np.std(yw, ddof=1))
        # Exact 10% annualized vol scaling BEFORE 52-week block bootstrap!
        yw_10 = yw / (sd_w * sqrt(52.0)) * 10.0 if sd_w > 0 else yw
        srs, rets, mdds = block_bootstrap_20k_weekly_10vol(yw_10, 20000, 4, 202611 + j)
        boot_out[cname] = {
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
        }

    res = {
        "elapsed_s": round(time.time() - t0, 2),
        "cscv": cscv_out,
        "dsr_by_trials": dsr_out,
        "empirical_bayes": eb_out,
        "bootstrap_20k_weekly_10pct_vol": boot_out,
    }
    out_p = Path("/kaggle/working/KAGGLE_CSCV_RESUMEN.json") if os.path.isdir("/kaggle/working") else Path("KAGGLE_CSCV_RESUMEN.json")
    out_p.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"DONE CSCV+DSR+20kBootWeekly in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
