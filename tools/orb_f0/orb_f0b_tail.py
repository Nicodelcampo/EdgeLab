
# ======================================================================================
# ORB Fase 0B (descriptiva, toca precios posteriores a la ruptura; manifiesto seccion 4).
# E_t = signo(ruptura) x (P_t - nivel_roto) / ancho_del_rango, sin stop ni objetivo. Una celda primaria:
# rango de 15 min, ruptura por toque (primer print fuera del rango), E a 11:30 y a 15:45 ET.
# Nulo (A2): permutacion de signos entre dias conservando el desplazamiento de cada dia. Sin grilla de decision.
# ======================================================================================
NULL_REPS = 2000
HORIZONS = {"1130": 120, "1545": 375}           # minutos desde 09:30


def price_at(ts, px, t):
    """A2: ultimo print ESTRICTAMENTE anterior al reloj t (causal; coincide con el camino por minutos)."""
    i = int(np.searchsorted(ts, t, side="left")) - 1
    return int(px[i]) if i >= 0 else None


def price_at_incl(ts, px, t):
    """Diagnostico A2: convencion anterior (print en t incluido)."""
    i = int(np.searchsorted(ts, t, side="right")) - 1
    return int(px[i]) if i >= 0 else None


def session_ext(td, ts, px):
    open_ns = open_ns_for(int(td))
    sel = (ts >= open_ns) & (ts <= open_ns + 390 * NS_MIN)
    if sel.sum() < 500:
        return None, "sin_rth"
    ts, px = ts[sel], px[sel]
    if not (open_ns <= ts[0] <= open_ns + 300 * 1_000_000_000):
        return None, "primer_print_fuera_de_0930_0935"
    w = ts < open_ns + 60 * NS_MIN
    if (np.diff(ts[w]) > MAX_GAP_NS).any():
        return None, "hueco_mayor_60s_0930_1030"
    if ((ts >= open_ns + 330 * NS_MIN) & (ts < open_ns + 375 * NS_MIN)).sum() < 100:
        return None, "cierre_temprano"
    out = {"td": td}
    # camino 2 (independiente): ultimo precio por minuto (groupby) para P_t
    m = ((ts - open_ns) // NS_MIN).astype(np.int64)
    last_by_min = pd.DataFrame({"m": m, "p": px}).groupby("m")["p"].last()
    for W in OR_MINS:
        tw = open_ns + W * NS_MIN
        inw = ts < tw
        if inw.sum() < 20:
            continue
        hi, lo = int(px[inw].max()), int(px[inw].min())
        width = hi - lo
        if width <= 0:
            continue
        post = ts >= tw
        pts, ppx = ts[post], px[post]
        up, dn = np.flatnonzero(ppx > hi), np.flatnonzero(ppx < lo)
        iu = int(up[0]) if len(up) else -1
        idn = int(dn[0]) if len(dn) else -1
        d = {"width": width, "hi": hi, "lo": lo}
        for tag, mins in HORIZONS.items():
            t = open_ns + mins * NS_MIN
            P = price_at(ts, px, t)
            d["P_" + tag] = P
            P2 = int(last_by_min[last_by_min.index <= mins - 1].iloc[-1]) if (last_by_min.index <= mins - 1).any() else None
            d["P2_" + tag] = P2
            d["Pincl_" + tag] = price_at_incl(ts, px, t)
            d["n_at_t_" + tag] = int((ts == t).sum())
            # contrafactuales con el mismo camino: largo desde hi y corto desde lo
            d["Eup_" + tag] = (P - hi) / width
            d["Edn_" + tag] = (lo - P) / width
        cands = [(pts[i], s, i) for s, i in (("up", iu), ("down", idn)) if i >= 0]
        if cands:
            t_b, side, i_b = min(cands)
            d["side"] = side
            d["entry_px"] = int(ppx[i_b])
            d["t_break_min"] = float((t_b - tw) / NS_MIN)
            for tag, mins in HORIZONS.items():
                if t_b <= open_ns + mins * NS_MIN:
                    sgn = 1.0 if side == "up" else -1.0
                    lvl = hi if side == "up" else lo
                    P = d["P_" + tag]
                    d["E_" + tag] = sgn * (P - lvl) / width
                    d["Eentry_" + tag] = sgn * (P - d["entry_px"]) / width
                    d["Eabs_" + tag] = abs(P - lvl) / width
                    d["s_" + tag] = sgn
                    d["D_" + tag] = (P - lvl) / width
        out[W] = d
    return out, None


def ci_mean(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), float("nan"), n
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    se = sd / math.sqrt(n)
    return mu, se, mu - 1.96 * se, mu + 1.96 * se, n


def summarize_ext(R, W, tag, rng):
    rows = [r[W] for r in R if W in r and ("E_" + tag) in r[W]]
    if not rows:
        return {}
    E = np.array([d["E_" + tag] for d in rows])
    Ee = np.array([d["Eentry_" + tag] for d in rows])
    Ea = np.array([d["Eabs_" + tag] for d in rows])
    mu, se, lo, hi, n = ci_mean(E)
    # A2 - nulo de deriva (manifiesto secc. 4): se PERMUTAN los signos de ruptura entre los dias, conservando el
    # desplazamiento D_i = (P_t - nivel_roto_i)/ancho_i de cada dia (y por tanto la deriva del periodo).
    sg = np.array([d["s_" + tag] for d in rows])
    D = np.array([d["D_" + tag] for d in rows])
    null_means = np.array([float((sg[rng.permutation(len(sg))] * D).mean()) for _ in range(NULL_REPS)])
    p_null = float((1 + np.sum(null_means >= mu)) / (NULL_REPS + 1.0))
    p_two = float((1 + np.sum(np.abs(null_means - null_means.mean()) >= abs(mu - null_means.mean()))) / (NULL_REPS + 1.0))
    eup = np.array([d["Eup_" + tag] for d in rows])
    edn = np.array([d["Edn_" + tag] for d in rows])
    # SD de la extension firmada (insumo del MDE)
    return {"n_days": int(n), "mean_E": mu, "se": se, "ci95": [lo, hi], "sd": float(E.std(ddof=1)),
            "quantiles_E_5_25_50_75_95": [float(np.percentile(E, q)) for q in (5, 25, 50, 75, 95)],
            "mean_E_from_entry_print": float(Ee.mean()), "mean_abs_extension": float(Ea.mean()),
            "frac_E_positive": float((E > 0).mean()),
            "mean_E_long_from_hi_all_days": float(eup.mean()), "mean_E_short_from_lo_all_days": float(edn.mean()),
            "null_sign_permutation": {"mean": float(null_means.mean()), "p975": float(np.percentile(null_means, 97.5)),
                                 "p_value_one_sided": p_null, "p_value_two_sided": p_two},
            "MDE_80pct_2p5onesided_R": float(2.8 * E.std(ddof=1) / math.sqrt(n)),
            "second_path_price_disagreements": int(sum(1 for d in rows if d["P_" + tag] != d["P2_" + tag])),
            "diag_incl_convention_price_differs_from_strict": int(sum(1 for d in rows if d["P_" + tag] != d["Pincl_" + tag])),
            "diag_days_with_print_exactly_at_t": int(sum(1 for d in rows if d["n_at_t_" + tag] > 0))}


def run_asset_b(asset):
    t0 = time.time()
    pfile = locate_parquet(asset)
    recs, disc = [], defaultdict(lambda: defaultdict(int))
    for td, prim, ts, px, bid, ask, vol, outreg in iter_sessions(pfile):
        wn = next((n for n, (a, b) in WINDOWS.items() if a <= td <= b), None)
        if wn is None:
            continue
        r, why = session_ext(td, ts, px)
        if r is None:
            disc[wn][why] += 1
            continue
        r["win"] = wn
        recs.append(r)
    rng = np.random.default_rng(20261017)
    out = {"discards": {k: dict(v) for k, v in disc.items()}}
    for wn in WINDOWS:
        R = [r for r in recs if r["win"] == wn]
        o = {"n_sessions_valid": len(R)}
        for W in OR_MINS:
            for tag in HORIZONS:
                o["W%d_%s" % (W, tag)] = summarize_ext(R, W, tag, rng)
        out[wn] = o
    # veredicto automatico (manifiesto secc. 5) sobre la celda primaria: 15 min, E al cierre 15:45, DISC
    p = out["DISC"]["W%d_1545" % PRIMARY_W]
    cl = out["CLEAN"]["W%d_1545" % PRIMARY_W]
    verdict = "ABSTENCION"
    if p:
        mde_ok = p["MDE_80pct_2p5onesided_R"] <= 0.30
        n_ok = p["n_days"] >= 150
        within = (p["ci95"][0] >= -0.10) and (p["ci95"][1] <= 0.10)
        if p["n_days"] < 100 or (within and p["null_sign_permutation"]["p_value_one_sided"] > 0.10):
            verdict = "NO_GO"
        elif n_ok and mde_ok:
            verdict = "GO_FASE1"
        out["gate_inputs"] = {"n_ok_ge_150": n_ok, "MDE_ok_le_0.30R": mde_ok, "ci95_within_pm0.10R": within,
                              "p_null": p["null_sign_permutation"]["p_value_one_sided"]}
    out["VERDICT_PRIMARY_GATE_0B"] = verdict
    out["clean_window_primary_cell_descriptive"] = cl
    out["elapsed_seconds"] = round(time.time() - t0, 1)
    return out


def main_b():
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"spec_id": "EXP-ORB-F0B-V2-A2", "manifest": "ORB_FASE0_MANIFIESTO_20261017.md (secc. 4 y 5)",
               "windows": WINDOWS, "holdout_touched": False,
               "definition": "E_t = sign(break) * (P_t - broken_level) / OR_width; sin stop ni objetivo; nulo = permutacion de signos entre dias (A2)"}
    for asset in ("ES", "NQ"):
        try:
            summary[asset] = run_asset_b(asset)
        except Exception as e:
            summary[asset] = {"ERROR": repr(e)[:500]}
            print("ORB_F0B_ERROR", asset, repr(e)[:500], flush=True)
    txt = json.dumps(summary, indent=1, default=float)
    print("=== EXP_ORB_F0B_SUMMARY_START ===", flush=True)
    print(txt[:180000], flush=True)
    print("=== EXP_ORB_F0B_SUMMARY_END ===", flush=True)
    (out_dir / "EXP_ORB_F0B_RESULTS.json").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main_b()
