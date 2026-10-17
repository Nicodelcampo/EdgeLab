
# ======================================================================================
# F0 — EJECUCION PASIVA EN ES (manifiesto pre-registrado:
# docs/research/F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md). Sin estrategia, sin busqueda.
# T1 = cierre de cada barra 100T (primaria). T2 = cierre de impulso del corredor preset 1 (secundaria).
# ======================================================================================
F0_START_D, F0_SPLIT_D, F0_END_D = 20250718, 20260331, 20260930
F0_TAUS = (10, 60, 300)
F0_HS = (10, 60, 300)
F0_RULES = ("TT", "TOUCH")          # indice 0 = R_TT (primaria), 1 = R_TOUCH (cota)
F0_PRIMARY = (60, 60, 0)            # (tau s, h s, regla)
F0_STRATA = ("ALL", "S1_with", "S1_against", "S2_spread1", "S2_spread2p", "S3_open30", "S3_rest",
             "SIDE_buy", "SIDE_sell")
F0_NS = 1_000_000_000


@njit(cache=False)
def f0_scan_fills(ts, px, i_dec, bid0, ask0, tau_max_ns):
    """Primer fill causal por (decision, lado, regla). j > i y ts[j] <= ts[i] + tau_max. -1 = sin fill."""
    n = len(i_dec)
    out = -np.ones((n, 2, 2), dtype=np.int64)
    N = len(ts)
    for d in range(n):
        i = i_dec[d]
        t_lim = ts[i] + tau_max_ns
        b = bid0[d]
        a = ask0[d]
        found = 0
        j = i + 1
        while j < N and ts[j] <= t_lim and found < 4:
            p = px[j]
            if out[d, 0, 0] < 0 and p <= b - 1:
                out[d, 0, 0] = j
                found += 1
            if out[d, 0, 1] < 0 and p <= b:
                out[d, 0, 1] = j
                found += 1
            if out[d, 1, 0] < 0 and p >= a + 1:
                out[d, 1, 0] = j
                found += 1
            if out[d, 1, 1] < 0 and p >= a:
                out[d, 1, 1] = j
                found += 1
            j += 1
    return out


def f0_load_sessions(pfile):
    """Generador de sesiones (una por trade_date, contrato primario) con cotizaciones L1. trade_date < 20261001."""
    pf = pq.ParquetFile(pfile)
    names = [pf.metadata.row_group(0).column(i).path_in_schema for i in range(pf.metadata.row_group(0).num_columns)]
    col_idx = {nm: i for i, nm in enumerate(names)}
    need = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "outside_regular", "volume"]
    for c in need:
        assert c in col_idx, "falta columna %s en el parquet (%s)" % (c, names)
    td_col = col_idx["trade_date"]
    c_col = col_idx.get("contract", -1)
    sel_col = col_idx.get("session_selected", -1)
    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st = md.column(td_col).statistics
        if st is not None and st.has_min_max and int(st.min) >= HOLDOUT_TRADE_DATE:
            continue
        key = int(st.min) if (st is not None and st.has_min_max and st.min == st.max) else -1
        rg_by_td[key].append(rg)
    for td in sorted(k for k in rg_by_td if F0_START_D <= k <= F0_END_D):
        rgs = rg_by_td[td]
        rows_by_c, rgs_by_c = defaultdict(int), defaultdict(list)
        for rg_i in rgs:
            md_i = pf.metadata.row_group(rg_i)
            if sel_col >= 0:
                ss = md_i.column(sel_col).statistics
                if ss is not None and ss.has_min_max and ss.max is False:
                    continue
            sc = md_i.column(c_col).statistics if c_col >= 0 else None
            cn = str(sc.min) if (sc is not None and sc.has_min_max) else "ES_PRIM"
            rows_by_c[cn] += md_i.num_rows
            rgs_by_c[cn].append(rg_i)
        if not rows_by_c:
            continue
        prim = max(rows_by_c.items(), key=lambda x: x[1])[0]
        tbl = pf.read_row_groups(rgs_by_c[prim], columns=need)
        ts = tbl["ts_utc_ns"].to_numpy()
        if len(ts) < 1000:
            continue
        order = np.argsort(ts, kind="mergesort") if (np.diff(ts) < 0).any() else None
        cols = [tbl[c].to_numpy() for c in need[1:]]
        if order is not None:
            ts = ts[order]
            cols = [c[order] for c in cols]
        if ts[-1] >= HOLDOUT_UTC_NS:
            m = ts < HOLDOUT_UTC_NS
            ts = ts[m]
            cols = [c[m] for c in cols]
        yield td, prim, ts.astype(np.int64), cols[0].astype(np.int64), cols[1].astype(np.int64), \
            cols[2].astype(np.int64), cols[3].astype(np.int8), cols[4].astype(np.float64)


def _f0_new_acc():
    return defaultdict(list)


def f0_process_session(ts, px, bid, ask, outreg, i_dec, acc, samples, full_grid):
    n = len(ts)
    qv = (bid > 0) & (ask >= bid)
    idx = np.where(qv, np.arange(n), 0)
    idx = np.maximum.accumulate(idx)
    mid2 = (bid + ask)[idx]                        # medios ticks (cotizacion valida mas reciente)
    i_dec = i_dec[(i_dec >= 199) & (i_dec < n - 1)]
    if len(i_dec) == 0:
        return
    b0, a0 = bid[i_dec], ask[i_dec]
    ok = (b0 > 0) & (a0 >= b0)
    i_dec, b0, a0 = i_dec[ok], b0[ok], a0[ok]
    if len(i_dec) == 0:
        return
    fills = f0_scan_fills(ts, px, i_dec, b0, a0, max(F0_TAUS) * F0_NS)
    t_end = ts[-1]
    t0 = ts[i_dec]
    prev = np.sign(px[i_dec] - px[i_dec - 100])
    spread = a0 - b0
    rth_idx = np.where(outreg == 0)[0]
    rth_start = ts[rth_idx[0]] if len(rth_idx) else None
    open30 = (np.zeros(len(i_dec), dtype=bool) if rth_start is None
              else (outreg[i_dec] == 0) & (t0 - rth_start <= 1800 * F0_NS))
    sides = (0, 1)
    for side in sides:
        entry_a = (a0 if side == 0 else b0).astype(np.float64)
        sgn = 1.0 if side == 0 else -1.0
        with_dir = (prev > 0) if side == 0 else (prev < 0)
        against = (prev < 0) if side == 0 else (prev > 0)
        smask = {"ALL": np.ones(len(i_dec), dtype=bool), "S1_with": with_dir, "S1_against": against,
                 "S2_spread1": spread == 1, "S2_spread2p": spread >= 2, "S3_open30": open30,
                 "S3_rest": ~open30, "SIDE_buy": np.full(len(i_dec), side == 0), "SIDE_sell": np.full(len(i_dec), side == 1)}
        for ti, tau in enumerate(F0_TAUS):
            win_ok = (t0 + tau * F0_NS) <= t_end
            for ri in (0, 1):
                j = fills[:, side, ri]
                tf = np.where(j >= 0, ts[np.maximum(j, 0)], 0)
                filled = (j >= 0) & ((tf - t0) <= tau * F0_NS) & win_ok
                for h in F0_HS:
                    is_primary = (tau, h, ri) == F0_PRIMARY
                    if not full_grid and not is_primary:
                        continue
                    th_a = t0 + h * F0_NS
                    th_p = tf + h * F0_NS
                    okh = filled & (th_a <= t_end) & (th_p <= t_end)
                    ia = np.searchsorted(ts, th_a, side="right") - 1
                    ip = np.searchsorted(ts, np.minimum(th_p, t_end), side="right") - 1
                    mid_a = mid2[np.clip(ia, 0, n - 1)] / 2.0
                    mid_p = mid2[np.clip(ip, 0, n - 1)] / 2.0
                    Ma = sgn * (mid_a - entry_a)
                    Mp = sgn * (mid_p - (b0 if side == 0 else a0).astype(np.float64))
                    A = Mp - Ma
                    for sname, sm in smask.items():
                        if not full_grid and not is_primary:
                            continue
                        if not (sname == "ALL" or is_primary):
                            continue
                        m_obs = sm & win_ok
                        m_fill = m_obs & filled
                        m_a = sm & okh
                        m_all = sm & (th_a <= t_end)          # referencia agresiva INCONDICIONAL (todas las decisiones)
                        acc[(tau, h, ri, sname)].append(np.array([
                            m_obs.sum(), m_fill.sum(), m_a.sum(),
                            A[m_a].sum(), Mp[m_a].sum(), Ma[m_a].sum(),
                            m_all.sum(), Ma[m_all].sum()], dtype=np.float64))
                    if is_primary and full_grid:
                        m_a = okh
                        samples["A"].append(A[m_a].astype(np.float32))
                        samples["Mp"].append(Mp[m_a].astype(np.float32))
                        samples["Ma"].append(Ma[m_a].astype(np.float32))
                        samples.setdefault("MaAll", []).append(Ma[th_a <= t_end].astype(np.float32))
                        samples["adv2"].append(np.array([(Mp[m_a] <= -2.0).sum(), m_a.sum()], dtype=np.float64))


def _merge_sides(rows):
    """Cada sesion aporta DOS filas consecutivas (compra, venta). El cluster es la SESION: se suman antes de la linealizacion."""
    R = np.asarray(rows, dtype=np.float64)
    if len(R) % 2 == 0 and len(R) > 0:
        R = R.reshape(-1, 2, R.shape[1]).sum(axis=1)
    return R


def f0_cluster(rows, num_col, den_col):
    """Razon sum(num)/sum(den) con SE clusterizado por sesion (linealizacion, Liang-Zeger)."""
    R = _merge_sides(rows)
    num, den = R[:, num_col], R[:, den_col]
    N = den.sum()
    if N <= 0 or len(R) < 2:
        return float("nan"), float("nan"), int(len(R)), 0
    m = num.sum() / N
    c = (num - m * den) / N
    G = len(R)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(m), se, G, int(N)


def f0_contrast(rows1, rows2):
    """Diferencia de A* entre dos estratos (mismas sesiones, mismo orden): SE por linealizacion."""
    a1, _s1, c1 = f0_astar(rows1)
    a2, _s2, c2 = f0_astar(rows2)
    if a1 != a1 or a2 != a2 or len(c1) != len(c2):
        return float("nan"), float("nan")
    c = c1 - c2
    G = len(c)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(a1 - a2), se


def f0_astar(rows):
    """A* = mean(Mp | fill) - mean(Ma sobre TODAS las decisiones). Linealizacion por sesion de la diferencia de dos razones."""
    R = _merge_sides(rows)
    nF, sMp = R[:, 2], R[:, 4]
    nAll, sMa = R[:, 6], R[:, 7]
    NF, NA = nF.sum(), nAll.sum()
    if NF <= 0 or NA <= 0 or len(R) < 2:
        return float("nan"), float("nan"), np.zeros(len(R))
    mMp, mMa = sMp.sum() / NF, sMa.sum() / NA
    c = (sMp - mMp * nF) / NF - (sMa - mMa * nAll) / NA
    G = len(R)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(mMp - mMa), se, c


def f0_summarize(acc):
    out = {}
    for (tau, h, ri, sname), rows in acc.items():
        if not rows:
            continue
        F, seF, G, nobs = f0_cluster(rows, 1, 0)
        A, seA, _, nA = f0_cluster(rows, 3, 2)
        Mp, seMp, _, _ = f0_cluster(rows, 4, 2)
        Ma, seMa, _, _ = f0_cluster(rows, 5, 2)
        Astar, seAs, _ = f0_astar(rows)
        MaAll, _, _, _ = f0_cluster(rows, 7, 6)
        out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)] = {
            "F_fill": F, "se_F": seF, "n_obs": nobs, "A_ticks": A, "se_A": seA, "n_A": nA,
            "Mp_ticks": Mp, "Ma_paired_filled_ticks": Ma, "MaAll_ticks": MaAll, "n_sessions": G,
            "A_paired_filled_ticks_DIAGNOSTIC_equals_spread_by_construction": A,
            "Astar_ticks": Astar, "se_Astar": seAs,
            "Astar_lo975_onesided": Astar - 1.96 * seAs if seAs == seAs else float("nan"),
            "Astar_hi975_onesided": Astar + 1.96 * seAs if seAs == seAs else float("nan")}
        if F == F and F < 1 and Astar == Astar:
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["g_star_breakeven_edge_ticks"] = F * Astar / (1.0 - F)
        # valor por intento si no hay edge: F*Mp (no llena = 0) contra Ma incondicional
        if F == F and Mp == Mp and MaAll == MaAll:
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["value_per_intent_passive_ticks"] = F * Mp
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["value_per_intent_aggressive_ticks"] = MaAll
    return out


def f0_sanity_tests(pfile):
    """Causalidad del fill (perturbacion de futuro) y prefijo de la decision. Aborta si algo difiere."""
    n_cases, n_fill_checked = 0, 0
    rng = np.random.default_rng(20261017)
    for td, prim, ts, px, bid, ask, outreg, _vol in f0_load_sessions(pfile):
        if td < F0_START_D + 40:
            continue
        i_dec = np.arange(199, len(ts) - 30000, 100)
        pick = rng.choice(i_dec, size=min(150, len(i_dec)), replace=False)
        for i in pick:
            b0, a0 = bid[i], ask[i]
            if not (b0 > 0 and a0 >= b0):
                continue
            lo, hi = i - 100, min(len(ts), i + 30000)
            ts_w, px_w = ts[lo:hi], px[lo:hi]
            ii = np.array([i - lo], dtype=np.int64)
            f_a = f0_scan_fills(ts_w, px_w, ii, np.array([b0]), np.array([a0]), 60 * F0_NS)
            px_p = px_w.copy()
            px_p[ts_w > ts[i] + 60 * F0_NS] = -10 ** 6      # futuro tras t0+tau perturbado
            f_b = f0_scan_fills(ts_w, px_p, ii, np.array([b0]), np.array([a0]), 60 * F0_NS)
            assert np.array_equal(f_a, f_b), "FILL NO CAUSAL (td=%s i=%s)" % (td, i)
            n_fill_checked += int((f_a >= 0).any())
            # prefijo: bid/ask/signo de la barra previa solo dependen de indices <= i
            assert (bid[:i + 1][-1], ask[:i + 1][-1], np.sign(px[:i + 1][-1] - px[:i + 1][-101])) == \
                   (b0, a0, np.sign(px[i] - px[i - 100]))
            n_cases += 1
        if n_cases >= 600:
            break
    assert n_cases >= 200, "pruebas causales insuficientes: %d" % n_cases
    return {"n_cases": n_cases, "n_cases_with_fill": n_fill_checked, "max_abs_diff": 0.0}


def main_f0():
    t0 = time.time()
    pfile = locate_es_parquet()
    sanity = f0_sanity_tests(pfile)
    print("F0_SANITY_PASS", json.dumps(sanity), flush=True)

    acc_d, acc_c = _f0_new_acc(), _f0_new_acc()
    acc_t2d, acc_t2c = _f0_new_acc(), _f0_new_acc()
    samples = {"A": [], "Mp": [], "Ma": [], "adv2": []}
    n_sess_d = n_sess_c = 0
    n_q_valid = n_q_tot = 0
    t2_err, t2_ok = 0, 0
    pc1 = (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72)
    for td, prim, ts, px, bid, ask, outreg, vol_s in f0_load_sessions(pfile):
        assert ts[-1] < HOLDOUT_UTC_NS and td < 20261001, "HOLDOUT"
        n_q_tot += len(ts)
        n_q_valid += int(((bid > 0) & (ask >= bid)).sum())
        is_disc = td <= F0_SPLIT_D
        n_sess_d += 1 if is_disc else 0
        n_sess_c += 0 if is_disc else 1
        i_dec = np.arange(99, len(ts), 100)
        f0_process_session(ts, px, bid, ask, outreg, i_dec, acc_d if is_disc else acc_c,
                           samples if is_disc else {"A": [], "Mp": [], "Ma": [], "adv2": []}, True)
        # T2: cierres de impulso del corredor (preset 1)
        try:
            s_k = {"session_id": 1, "trade_date": td, "contract_id": 1, "contract": prim,
                   "prices": px.astype(np.float64) * TICK_ES, "ts_utc_ns": ts,
                   "is_rth": (outreg == 0).astype(np.int8), "vol": vol_s,
                   "utc_off_s": int(datetime.fromtimestamp(int(ts[len(ts) // 2]) / 1e9, CHI).utcoffset().total_seconds())}
            Bs, _sd = dev_build_bars([s_k], 100)
            _, _, _, _, zc, _, _ = detect_zones_nt8_numba(
                Bs["o"], Bs["h"], Bs["l"], Bs["c"], Bs["sid"], Bs["cid"], 200, 100,
                pc1[0], pc1[1], pc1[2], pc1[3], pc1[4], pc1[5], pc1[6], pc1[7], pc1[8], pc1[9], pc1[10], pc1[11],
                pc1[12], pc1[13], 40, 5, 1.60, TICK_ES)
            if len(zc) > 0:
                cls_b = np.asarray([int(z[5]) for z in zc], dtype=np.int64)
                ts_end = Bs["ts_end"][cls_b]
                i_imp = np.unique(np.searchsorted(ts, ts_end, side="right") - 1)
                f0_process_session(ts, px, bid, ask, outreg, i_imp, acc_t2d if is_disc else acc_t2c,
                                   {"A": [], "Mp": [], "Ma": [], "adv2": []}, False)
            t2_ok += 1
        except Exception as e:  # T2 es secundaria: se declara el fallo, no se oculta
            t2_err += 1
            if t2_err <= 3:
                print("F0_T2_ERROR", td, repr(e)[:300], flush=True)
        if (n_sess_d + n_sess_c) % 25 == 0:
            print("F0 sesiones", n_sess_d + n_sess_c, "t=%.0fs" % (time.time() - t0), flush=True)

    q_frac = n_q_valid / max(n_q_tot, 1)
    print("F0 sesiones disc=%d conf=%d, fraccion cotizacion valida=%.5f" % (n_sess_d, n_sess_c, q_frac), flush=True)
    if q_frac < 0.99:
        print("F0_ABORT_QUOTES_INVALID", q_frac, flush=True)
        return
    if n_sess_d < 170 or n_sess_c < 80:
        print("F0_ABORT_SESSIONS_INSUFFICIENT", n_sess_d, n_sess_c, flush=True)
        return

    S_d, S_c = f0_summarize(acc_d), f0_summarize(acc_c)
    pk = "tau60_h60_TT"
    prim_d, prim_c = S_d[pk + "_ALL"], S_c[pk + "_ALL"]
    # contrastes S1-S3 (Holm sobre 3) en descubrimiento, ventana primaria
    pairs = (("S1_against_vs_with", "S1_against", "S1_with"), ("S2_spread1_vs_2p", "S2_spread1", "S2_spread2p"),
             ("S3_open30_vs_rest", "S3_open30", "S3_rest"))
    cont = {}
    pvals = []
    for nm, a, b in pairs:
        d, se = f0_contrast(acc_d[(60, 60, 0, a)], acc_d[(60, 60, 0, b)])
        z = d / se if se == se and se > 0 else float("nan")
        p = float(math.erfc(abs(z) / math.sqrt(2.0))) if z == z else float("nan")
        cont[nm] = {"diff_A_ticks": d, "se": se, "z": z, "p_raw": p}
        pvals.append((nm, p))
    ordered = sorted([x for x in pvals if x[1] == x[1]], key=lambda x: x[1])
    for rank, (nm, p) in enumerate(ordered):
        cont[nm]["p_holm"] = min(1.0, p * (len(ordered) - rank))

    A_all = np.concatenate(samples["A"]) if samples["A"] else np.zeros(0, dtype=np.float32)
    Mp_all = np.concatenate(samples["Mp"]) if samples["Mp"] else np.zeros(0, dtype=np.float32)
    Ma_all = np.concatenate(samples["Ma"]) if samples["Ma"] else np.zeros(0, dtype=np.float32)
    adv = np.sum(samples["adv2"], axis=0) if samples["adv2"] else np.zeros(2)
    qs = (5, 25, 50, 75, 95)
    dist = {"A_q": [float(np.percentile(A_all, q)) for q in qs] if len(A_all) else [],
            "Mp_q": [float(np.percentile(Mp_all, q)) for q in qs] if len(Mp_all) else [],
            "Ma_paired_filled_q": [float(np.percentile(Ma_all, q)) for q in qs] if len(Ma_all) else [],
            "MaAll_q": [float(np.percentile(np.concatenate(samples["MaAll"]), q)) for q in qs] if samples.get("MaAll") else [],
            "frac_fills_adverse_ge_2ticks": float(adv[0] / max(adv[1], 1.0))}

    F, lo, hi = prim_d["F_fill"], prim_d["Astar_lo975_onesided"], prim_d["Astar_hi975_onesided"]
    sign_stable = bool(prim_c["Astar_ticks"] == prim_c["Astar_ticks"] and prim_c["Astar_ticks"] > 0)
    if F >= 0.30 and lo > 0.25 and sign_stable:
        verdict = "PASIVO_RECUPERA"
    elif hi < 0.25 or F < 0.10:
        verdict = "PASIVO_NO_CONVIENE"
    else:
        verdict = "ABSTENCION"
    buy, sell = S_d[pk + "_SIDE_buy"]["Astar_ticks"], S_d[pk + "_SIDE_sell"]["Astar_ticks"]
    summary = {
        "spec_id": "EXP-F0-EJECUCION-PASIVA-ES-V1-A1", "manifest": "F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md",
        "windows": {"discovery": [F0_START_D, F0_SPLIT_D], "confirmation": [F0_SPLIT_D + 1, F0_END_D]},
        "n_sessions": {"discovery": n_sess_d, "confirmation": n_sess_c}, "quote_valid_fraction": q_frac,
        "sanity": sanity, "holdout_touched": False, "primary_discovery": prim_d, "primary_confirmation": prim_c,
        "VERDICT_PRIMARY": verdict, "sign_stable_confirmation": sign_stable,
        "side_symmetry_check": {"Astar_buy": buy, "Astar_sell": sell, "abs_diff": abs(buy - sell),
                                 "flag_gt_0.2tick": bool(abs(buy - sell) > 0.2)},
        "contrasts_discovery_holm3": cont, "distribution_primary_discovery": dist,
        "grid_discovery": S_d, "grid_confirmation": S_c,
        "T2_impulse_closes": {"sessions_ok": t2_ok, "sessions_error": t2_err,
                              "discovery": f0_summarize(acc_t2d), "confirmation": f0_summarize(acc_t2c)},
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    print("=== EXP_F0_SUMMARY_START ===", flush=True)
    print(json.dumps(summary, indent=1, default=float), flush=True)
    print("=== EXP_F0_SUMMARY_END ===", flush=True)
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "EXP_F0_EXEC_PASIVA_ES_RESULTS.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")


main_f0()
