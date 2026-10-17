

# ======================================================================================
# ORB H1 - Nivel V (factibilidad, DESCRIPTIVO, sin compuerta ni alfa; manifiesto H1 enmienda A1).
# Futuros ES/NQ (trades con volumen). Se concatena tras orb_f0a_kernel + orb_f0b_tail (sin sus main).
# V1: volumen relativo del rango de 15 min (OR15 vol / mediana de los 20 previos); favorable > 1.
# V2: conductividad del "por donde": densidad de volumen/tick del perfil RTH previo en el corredor de un ancho
#     por delante del nivel roto / densidad media del perfil previo; favorable < 1.
# ======================================================================================
PERM_REPS_V = 2000


def rth_profile(ts, px, vol, o):
    sel = (ts >= o) & (ts <= o + 390 * NS_MIN)
    if sel.sum() < 500:
        return None
    p, v = px[sel], vol[sel]
    pmin = int(p.min())
    arr = np.bincount((p - pmin).astype(np.int64), weights=v)
    return pmin, arr


def corridor_ratio(prof, lvl, width, side):
    pmin, arr = prof
    if side == "up":
        lo_t, hi_t = lvl + 1, lvl + width
    else:
        lo_t, hi_t = lvl - width, lvl - 1
    a, b = lo_t - pmin, hi_t - pmin
    a2, b2 = max(a, 0), min(b, len(arr) - 1)
    vol_in = float(arr[a2:b2 + 1].sum()) if b2 >= a2 else 0.0
    dens = vol_in / max(width, 1)
    ref = float(arr.sum()) / len(arr)
    return dens / ref if ref > 0 else None


def v_test(E, fav, rng):
    n = len(E)
    if fav.sum() < 8 or (~fav).sum() < 8:
        return {"n": int(n), "n_fav": int(fav.sum()), "n_unfav": int((~fav).sum()), "undefined": True}
    a, b = E[fav], E[~fav]
    d = float(a.mean() - b.mean())
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    nm = np.empty(PERM_REPS_V)
    for k in range(PERM_REPS_V):
        pm = rng.permutation(fav)
        nm[k] = E[pm].mean() - E[~pm].mean()
    return {"n": int(n), "n_fav": int(fav.sum()), "n_unfav": int((~fav).sum()), "mean_fav": float(a.mean()), "mean_unfav": float(b.mean()),
            "sd_fav": float(a.std(ddof=1)), "sd_unfav": float(b.std(ddof=1)), "D": d, "D_se": se, "D_ci95": [d - 1.96 * se, d + 1.96 * se],
            "MDE_D_80pct": 2.8 * se, "p_one_sided_DESCRIPTIVE": float((1 + np.sum(nm >= d)) / (PERM_REPS_V + 1.0))}


def run_asset_v(asset):
    t0 = time.time()
    pfile = locate_parquet(asset)
    prev_prof, or15_hist, rows = None, [], []
    for td, prim, ts, px, bid, ask, vol, outreg in iter_sessions(pfile):
        o = open_ns_for(int(td))
        wn = next((n for n, (a, b) in WINDOWS.items() if a <= td <= b), None)
        r, why = session_ext(td, ts, px)
        if r is not None and wn is not None and PRIMARY_W in r and "E_1545" in r[PRIMARY_W] and prev_prof is not None and len(or15_hist) >= 20:
            d = r[PRIMARY_W]
            side, lvl = d["side"], (d["hi"] if d["side"] == "up" else d["lo"])
            rel = float(vol[(ts >= o) & (ts < o + 15 * NS_MIN)].sum()) / float(np.median(or15_hist[-20:]))
            ratio = corridor_ratio(prev_prof, int(lvl), int(d["width"]), side)
            rows.append({"win": wn, "E": d["E_1545"], "relvol": rel, "ratio": ratio})
        pr = rth_profile(ts, px, vol, o)
        if pr is not None:
            prev_prof = pr
            or15_hist.append(float(vol[(ts >= o) & (ts < o + 15 * NS_MIN)].sum()))
    rng = np.random.default_rng(20261017)
    out = {"n_rows": len(rows)}
    for wn in WINDOWS:
        R = [r for r in rows if r["win"] == wn]
        if not R:
            continue
        E = np.array([r["E"] for r in R])
        rel = np.array([r["relvol"] for r in R])
        rt = np.array([np.nan if r["ratio"] is None else r["ratio"] for r in R])
        ok2 = ~np.isnan(rt)
        out[wn] = {"n_days": len(R), "base_mean_E": float(E.mean()), "base_sd": float(E.std(ddof=1)),
                   "V1_relvol_gt_1": v_test(E, rel > 1.0, rng),
                   "V2_corridor_density_lt_1": v_test(E[ok2], (rt < 1.0)[ok2], rng),
                   "relvol_quantiles": [float(np.percentile(rel, q)) for q in (5, 25, 50, 75, 95)],
                   "ratio_quantiles": [float(np.nanpercentile(rt, q)) for q in (5, 25, 50, 75, 95)],
                   "corr_relvol_vs_log_ratio": float(np.corrcoef(np.log(rel[ok2]), np.log(rt[ok2] + 1e-6))[0, 1])}
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def main_v():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"spec_id": "EXP-ORB-H1-V-V1", "manifest": "ORB_CFD_H1_HERRAMIENTAS_MANIFIESTO_20261017.md (enmienda A1, nivel V)",
               "windows": WINDOWS, "holdout_touched": False, "nature": "factibilidad descriptiva, sin compuerta ni alfa"}
    for asset in ("ES", "NQ"):
        try:
            summary[asset] = run_asset_v(asset)
        except Exception as e:
            import traceback
            summary[asset] = {"ERROR": repr(e)[:500], "tb": traceback.format_exc()[-1500:]}
            print("ERR", asset, repr(e)[:500], flush=True)
    txt = json.dumps(summary, indent=1, default=float)
    (out_dir / "EXP_ORB_H1_V_RESULTS.json").write_text(txt, encoding="utf-8")
    print("=== H1V_START ===\n" + txt[:150000] + "\n=== H1V_END ===", flush=True)


if __name__ == "__main__":
    main_v()
