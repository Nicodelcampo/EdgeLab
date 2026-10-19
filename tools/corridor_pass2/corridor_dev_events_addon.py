# ===================================================================================================
# ADENDA D — EXTRACCION DE TABLA DE EVENTOS DE DESARROLLO (EXP-CORRIDOR-CONF, ES, 299 sesiones)
# Se concatena DESPUES del script de Pasada 2 (sha256 10e8fa9f...) mediante tools/corridor_pass2/build_dev_script.py.
# No toca holdout (trade_date >= 20261001), ni NQ/YM. Todas las features son causales: usan datos <= cierre de la barra de entrada.
# ===================================================================================================
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

DEV_SPEC_ID = "EXP-CORRIDOR-DEV-D-v1"
CHI = ZoneInfo("America/Chicago")
NAN = float("nan")


def dev_load_sessions(pfile):
    """Igual que load_es_sessions_with_metadata pero conserva volumen por tick (si existe), fecha y offset UTC de Chicago."""
    pf = pq.ParquetFile(pfile)
    names = [pf.schema_arrow.field(i).name for i in range(len(pf.schema_arrow))]
    print("SCHEMA_COLUMNS:", names, flush=True)
    vol_col = next((c for c in ("volume", "size", "qty", "quantity", "trade_size") if c in names), None)
    print("VOLUME_COLUMN:", vol_col, flush=True)
    cols = ["ts_utc_ns", "price_ticks", "outside_regular"] + ([vol_col] if vol_col else [])

    col_idx = {pf.metadata.row_group(0).column(i).path_in_schema: i for i in range(pf.metadata.row_group(0).num_columns)}
    td_col = col_idx["trade_date"]
    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st_td = md.column(td_col).statistics
        if st_td is not None and st_td.has_min_max and int(st_td.min) >= HOLDOUT_TRADE_DATE:
            continue
        td_key = int(st_td.min) if (st_td is not None and st_td.has_min_max and st_td.min == st_td.max) else -1
        rg_by_td[td_key].append(rg)

    sessions_list, contract_to_id = [], {}
    c_col = col_idx.get("contract", -1)
    sel_col = col_idx.get("session_selected", -1)
    for td in sorted(k for k in rg_by_td if 0 < k < HOLDOUT_TRADE_DATE):
        rgs = rg_by_td[td]
        if len(rgs) > 1 and c_col >= 0:
            rows_by_c, rgs_by_c = defaultdict(int), defaultdict(list)
            for rg_i in rgs:
                md_i = pf.metadata.row_group(rg_i)
                if sel_col >= 0:
                    st_sel = md_i.column(sel_col).statistics
                    if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                        continue
                st_c = md_i.column(c_col).statistics
                c_name = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "UNK"
                rows_by_c[c_name] += md_i.num_rows
                rgs_by_c[c_name].append(rg_i)
            if not rows_by_c:
                continue
            prim_c = max(rows_by_c.items(), key=lambda x: x[1])[0]
            rgs = rgs_by_c[prim_c]
        else:
            md_0 = pf.metadata.row_group(rgs[0])
            if sel_col >= 0:
                st_sel = md_0.column(sel_col).statistics
                if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                    continue
            st_c = md_0.column(c_col).statistics if c_col >= 0 else None
            prim_c = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "ES_PRIM"

        tbl = pf.read_row_groups(rgs, columns=cols)
        ts = tbl["ts_utc_ns"].to_numpy()
        px_t = tbl["price_ticks"].to_numpy()
        out_reg = tbl["outside_regular"].to_numpy()
        vol = tbl[vol_col].to_numpy().astype(np.float64) if vol_col else np.ones(len(ts), dtype=np.float64)
        if len(ts) < 100:
            continue
        if ts[-1] >= HOLDOUT_UTC_NS:
            m_h = ts < HOLDOUT_UTC_NS
            ts, px_t, out_reg, vol = ts[m_h], px_t[m_h], out_reg[m_h], vol[m_h]
            if len(ts) < 100:
                continue
        if len(ts) > 1 and (np.diff(ts) < 0).any():
            order = np.argsort(ts, kind="mergesort")
            ts, px_t, out_reg, vol = ts[order], px_t[order], out_reg[order], vol[order]

        if prim_c not in contract_to_id:
            contract_to_id[prim_c] = len(contract_to_id) + 1
        off_s = int(datetime.fromtimestamp(int(ts[len(ts) // 2]) / 1e9, CHI).utcoffset().total_seconds())
        sessions_list.append({
            "session_id": len(sessions_list) + 1,
            "trade_date": td,
            "contract_id": contract_to_id[prim_c],
            "contract": prim_c,
            "prices": px_t.astype(np.float64) * TICK_ES,
            "ts_utc_ns": ts,
            "is_rth": (~out_reg.astype(bool)).astype(np.int8),
            "vol": vol,
            "utc_off_s": off_s,
        })
        del tbl
    return sessions_list, contract_to_id, bool(vol_col)


def dev_build_bars(sessions_list, res):
    """Mismas barras que build_session_strict_bars, mas ts, volumen, minuto de Chicago y primera barra de sesion."""
    L = defaultdict(list)
    base = 0
    sess_trade_date = {}
    for s in sessions_list:
        px, ts, vol = s["prices"], s["ts_utc_ns"], s["vol"]
        nb = len(px) // res
        if nb < 5:
            continue
        n_use = nb * res
        rpx = px[:n_use].reshape((nb, res))
        ts_r = ts[:n_use].reshape((nb, res))
        ts_end, ts_start = ts_r[:, -1], ts_r[:, 0]
        hh = ((ts_end // 1_800_000_000_000) % 48).astype(np.int32)
        L["p_al"].append(px[:n_use])
        L["v_al"].append(vol[:n_use])
        L["o"].append(rpx[:, 0]); L["h"].append(rpx.max(axis=1)); L["l"].append(rpx.min(axis=1)); L["c"].append(rpx[:, -1])
        L["sid"].append(np.full(nb, s["session_id"], dtype=np.int32))
        L["cid"].append(np.full(nb, s["contract_id"], dtype=np.int32))
        L["hh"].append(hh)
        L["rth"].append(((hh >= 27) & (hh <= 40)).astype(np.int32))
        L["ts_end"].append(ts_end); L["ts_start"].append(ts_start)
        L["vol"].append(vol[:n_use].reshape((nb, res)).sum(axis=1))
        L["ctmin"].append(((((ts_end // 1_000_000_000) + s["utc_off_s"]) % 86400) // 60).astype(np.int32))
        L["sess_first"].append(np.full(nb, base, dtype=np.int64))
        sess_trade_date[s["session_id"]] = s["trade_date"]
        base += nb
    return {k: np.concatenate(v) for k, v in L.items()}, sess_trade_date


def _oriented_frac(x, b_lo, b_hi, z_dir):
    H = max(b_hi - b_lo, 1e-9)
    return (x - b_lo) / H if z_dir == 1 else (b_hi - x) / H


def _profile_features(p, w, tick, b_lo, b_hi, z_dir, close_b, opp_edge):
    out = {k: NAN for k in ("poc_frac", "va_lo_frac", "va_hi_frac", "path_share", "outer_share", "node_ratio", "sector_share", "zone_ticks")}
    if len(p) == 0:
        return out
    lv = np.rint(p / tick).astype(np.int64)
    mn, mx = int(lv.min()), int(lv.max())
    v = np.bincount(lv - mn, weights=w, minlength=mx - mn + 1)
    tot = float(v.sum())
    if tot <= 0:
        return out
    n = len(v)
    mid = 0.5 * (b_lo + b_hi)
    poc_i = 0
    for k in range(1, n):
        if v[k] > v[poc_i] or (v[k] == v[poc_i] and abs((mn + k) * tick - mid) < abs((mn + poc_i) * tick - mid)):
            poc_i = k
    acc, a, bb = v[poc_i], poc_i, poc_i
    while acc < 0.70 * tot and (a > 0 or bb < n - 1):
        up = (v[bb + 1] if bb + 1 < n else 0.0) + (v[bb + 2] if bb + 2 < n else 0.0)
        dn = (v[a - 1] if a - 1 >= 0 else 0.0) + (v[a - 2] if a - 2 >= 0 else 0.0)
        if bb < n - 1 and (up >= dn or a == 0):
            acc += up; bb = min(n - 1, bb + 2)
        else:
            acc += dn; a = max(0, a - 2)
    px_of = lambda i: (mn + i) * tick
    f_lo, f_hi = sorted((_oriented_frac(px_of(a), b_lo, b_hi, z_dir), _oriented_frac(px_of(bb), b_lo, b_hi, z_dir)))
    levels = (mn + np.arange(n)) * tick
    fr = np.array([_oriented_frac(x, b_lo, b_hi, z_dir) for x in levels]) if n < 4000 else _oriented_frac(levels, b_lo, b_hi, z_dir)
    lo_p, hi_p = (min(close_b, opp_edge), max(close_b, opp_edge))
    on_path = (levels > lo_p + 1e-9) & (levels < hi_p - 1e-9)
    c_fr = _oriented_frac(close_b, b_lo, b_hi, z_dir)
    out.update(
        poc_frac=_oriented_frac(px_of(poc_i), b_lo, b_hi, z_dir), va_lo_frac=f_lo, va_hi_frac=f_hi,
        path_share=float(v[on_path].sum() / tot),
        outer_share=float(v[fr > c_fr].sum() / tot),
        node_ratio=float(v[on_path].max() / max(v.mean(), 1e-9)) if on_path.any() else 0.0,
        sector_share=float(v[fr >= 0.75].sum() / tot),
        zone_ticks=float(len(p)),
    )
    return out


def dev_extract_features(ev_mat, zones_mat, B, ema, atr, res, tick, race_h, fixed_t, tag):
    """Una fila por evento con labels de Pasada 2 + features causales + P&L con timeouts."""
    p_al, v_al = B["p_al"], B["v_al"]
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    cumv = np.concatenate([[0.0], np.cumsum(v_al)])
    zrow = {int(z[0]): i for i, z in enumerate(zones_mat)}
    # volumen total de cada zona (origen..cierre) y rank frente a las <=50 zonas previas que cerraron antes
    zinfo = {}
    order = np.argsort(zones_mat[:, 5], kind="stable") if len(zones_mat) else []
    prev = []
    for zi in order:
        z = zones_mat[zi]
        ob, cb = int(z[2]), int(z[5])
        tv = float(cumv[(cb + 1) * res] - cumv[ob * res])
        hist = prev[-50:]
        pct = float(np.mean([x < tv for x in hist])) if len(hist) >= 20 else NAN
        zinfo[int(z[0])] = (tv, pct)
        prev.append(tv)

    rows, n_err = [], 0
    for e in ev_mat:
        try:
            zid, fcode = int(e[0]), int(e[1])
            z = zones_mat[zrow[zid]]
            b = int(e[4])
            z_dir = int(z[1]); td = int(e[6])
            ob, eb, cb = int(z[2]), int(z[3]), int(z[5])
            opx, b_lo, b_hi = float(z[6]), float(z[8]), float(z[9])
            H = b_hi - b_lo
            outer, opp = (b_hi, b_lo) if z_dir == 1 else (b_lo, b_hi)
            s_end = int(z[16]); sb = int(B["sess_first"][b])
            a_b = float(atr[b]); cl = float(c[b])
            r = dict(det=tag, res=res, fcode=fcode, zone_id=zid, session_id=int(e[2]), contract_id=int(e[3]), entry_bar=b,
                     z_dir=z_dir, trade_dir=td, rth_pass2=int(e[5]), rth_ct=int(510 <= B["ctmin"][b] <= 930), ct_min=int(B["ctmin"][b]),
                     h_ticks=float(e[7]), score=float(e[8]), slope_ticks=float(e[9]), elapsed=float(e[10]))
            # geometria y retorno
            r.update(zone_len=cb - ob + 1, trend_len=eb - ob + 1, post_ext_len=cb - eb,
                     d_orig_ticks=abs(cl - opp) / tick, d_outer_ticks=abs(cl - outer) / tick, close_frac=_oriented_frac(cl, b_lo, b_hi, z_dir),
                     atr_ticks=a_b / tick, h_over_atr=H / max(a_b, tick), ema_dist_atr=z_dir * (cl - float(ema[b])) / max(a_b, tick))
            seg_c = c[cb + 1:b]; seg_h = h[cb + 1:b]; seg_l = l[cb + 1:b]
            outside = (seg_c > outer) if z_dir == 1 else (seg_c < outer)
            ext = (seg_h - outer) if z_dir == 1 else (outer - seg_l)
            r.update(bars_outside=int(outside.sum()), max_ext_ticks=float(max(ext.max(), 0.0) / tick) if len(ext) else 0.0)
            r.update(bar_range_ticks=float((h[b] - l[b]) / tick), bar_body_ticks=float(td * (cl - o[b]) / tick),
                     speed3=float(td * (cl - c[b - 3]) / tick) if b >= 3 else NAN, speed10=float(td * (cl - c[b - 10]) / tick) if b >= 10 else NAN)
            dur = (B["ts_end"][b] - B["ts_start"][b]) / 1e9
            d5 = (B["ts_end"][b] - B["ts_end"][max(b - 5, 0)]) / 1e9 / 5.0
            zd = (B["ts_end"][cb] - B["ts_start"][ob]) / 1e9 / max(cb - ob + 1, 1)
            r.update(bar_dur_s=float(dur), pace5=float(d5 / zd) if zd > 0 else NAN)
            # volumen y perfil de la zona (conocida desde cb: available_at = cb)
            tv, pct = zinfo.get(zid, (NAN, NAN))
            zvb = tv / max(cb - ob + 1, 1)
            vr5 = float(B["vol"][max(b - 4, 0):b + 1].sum() / (5.0 * zvb)) if zvb > 0 else NAN
            r.update(zone_vol=tv, zone_vol_pct50=pct, vol_ret5_ratio=vr5, vol_bar_ratio=float(B["vol"][b] / zvb) if zvb > 0 else NAN)
            r.update(_profile_features(p_al[ob * res:(cb + 1) * res], v_al[ob * res:(cb + 1) * res], tick, b_lo, b_hi, z_dir, cl, opp))
            # contexto de sesion hasta la barra b
            hs, ls = float(h[sb:b + 1].max()), float(l[sb:b + 1].min())
            rng = max(hs - ls, tick)
            r.update(sess_range_ticks=rng / tick, sess_pos=(cl - ls) / rng, dist_hi_ticks=(hs - cl) / tick, dist_lo_ticks=(cl - ls) / tick,
                     mins_since_open=float((B["ts_end"][b] - B["ts_start"][sb]) / 6e10),
                     rv50_atr=float(np.std(np.diff(c[max(b - 50, sb):b + 1])) / max(a_b, tick)) if b - sb > 5 else NAN)
            r.update(hr_sin=float(np.sin(2 * np.pi * B["ctmin"][b] / 1440.0)), hr_cos=float(np.cos(2 * np.pi * B["ctmin"][b] / 1440.0)))
            # etiquetas de Pasada 2 (R/C/0) y P&L en ticks con timeout marcado a mercado
            ent = cl
            if fcode == 7:
                ent = (b_hi - 0.333333 * H) if z_dir == 1 else (b_lo + 0.333333 * H)
            t0 = (b + 1) * res
            t1 = min(s_end, b + 1 + race_h) * res
            seg = p_al[t0:t1]
            if len(seg):
                delta = td * (seg - ent) / tick
                r.update(mfe_ticks=float(max(delta.max(), 0.0)), mae_ticks=float(max(-delta.min(), 0.0)), ret_end_ticks=float(delta[-1]))
            else:
                r.update(mfe_ticks=NAN, mae_ticks=NAN, ret_end_ticks=NAN)
            d_struct = max(4.0, abs(cl - opp) / tick) if fcode in (1, 2, 3) else 0.8 * (H / tick)
            r.update(out_05H=int(e[11]), exit_05H=int(e[12]), pseudo_05H=float(e[13]), out_10H=int(e[14]), exit_10H=int(e[15]), pseudo_10H=float(e[16]),
                     out_struct=int(e[17]), exit_struct=int(e[18]), pseudo_struct=float(e[19]), out_fixed=int(e[20]), exit_fixed=int(e[21]),
                     out_10H_adv1t=int(e[23]), D_05H=0.5 * H / tick, D_10H=H / tick, D_struct=d_struct, D_fixed=float(fixed_t))
            rows.append(r)
        except Exception as ex:  # no se descarta en silencio: se cuenta y se reporta
            n_err += 1
            if n_err <= 5:
                print("FEATURE_ERROR", tag, res, repr(ex), flush=True)
    print(f"[{tag}|{res}T] eventos={len(ev_mat)} filas={len(rows)} errores={n_err}", flush=True)
    return pd.DataFrame(rows), n_err


def dev_regression_print(ev_mat, tag, res, pid):
    """Regresion contra Pasada 2: F1A, purga no_overlap, barrera 1.0H, ALL y STEEP (mediana global como en Pasada 2)."""
    sub = ev_mat[ev_mat[:, 1] == 1]
    if len(sub) < 15:
        return
    med = float(np.median(sub[:, 9]))
    for name, m in (("ALL", np.ones(len(sub), bool)), ("STEEP", sub[:, 9] >= med)):
        rr = purge_overlapping_events(sub[m], 15)
        res_ = rr[rr[:, 14] != 0]
        print(f"[REGRESION {tag}|{res}T|P{pid}|F1A|{name}] N_purgado={len(rr)} resueltos={len(res_)} wr_1.0H={float(np.mean(res_[:, 14] == 1)) if len(res_) else NAN:.4f}", flush=True)


def main_dev():
    pfile = locate_es_parquet()
    sessions_list, cmap, has_vol = dev_load_sessions(pfile)
    tot = sum(len(s["prices"]) for s in sessions_list)
    print(f"{DEV_SPEC_ID}: {len(sessions_list)} sesiones, {tot:,} ticks, volumen_real={has_vol}", flush=True)
    presets_cfg = {
        1: (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72),
        2: (60, 45, 12, 65, 24, 0.85, 0.84, 0.030, 0.88, 0.80, 1.05, 0.44, 0.46, 0.64),
        3: (48, 36, 12, 50, 28, 0.80, 0.80, 0.024, 0.84, 0.65, 1.25, 0.52, 0.55, 0.55),
    }
    plan = {100: ((1, 2, 3), (1,)), 500: ((2,), (7,))}   # res -> (presets, fcodes a conservar)
    frames, total_err = [], 0
    for res, (pids, fcodes) in plan.items():
        B, sess_td = dev_build_bars(sessions_list, res)
        max_el = 1200 if res == 100 else 500
        race_h = 400 if res == 100 else 200
        fixed_t = 40 if res == 100 else 60
        ema_p = 200 if res == 100 else 100
        atr_p = 100 if res == 100 else 50
        for det, fn in (("PY", detect_zones_session_strict_numba), ("NT8", detect_zones_nt8_numba)):
            for pid in pids:
                pc = presets_cfg[pid]
                state, score_s, ema_a, atr_a, zones_mat, s_start_b, s_end_b = fn(
                    B["o"], B["h"], B["l"], B["c"], B["sid"], B["cid"], ema_p, atr_p,
                    pc[0], pc[1], pc[2], pc[3], pc[4], pc[5], pc[6], pc[7], pc[8], pc[9], pc[10], pc[11], pc[12], pc[13], 40, 5, 1.60, TICK_ES)
                ev_mat = extract_pass2_events_with_matched_pseudos_numba(
                    B["p_al"], B["h"], B["l"], B["c"], ema_a, state, B["sid"], B["cid"], B["hh"], B["rth"], s_end_b,
                    zones_mat, res, max_el, race_h, float(fixed_t), TICK_ES)
                print(f"[{det}|{res}T|P{pid}] zonas={len(zones_mat)} eventos={len(ev_mat)}", flush=True)
                if res == 100 and pid in (1, 2):
                    dev_regression_print(ev_mat, det, res, pid)
                keep = ev_mat[np.isin(ev_mat[:, 1], fcodes)]
                df, n_err = dev_extract_features(keep, zones_mat, B, ema_a, atr_a, res, TICK_ES, race_h, fixed_t, det)
                total_err += n_err
                if len(df):
                    df["preset"] = pid
                    df["trade_date"] = df["session_id"].map(sess_td)
                    frames.append(df)
        del B
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out_dir = Path("/kaggle/working")
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / "ES_CORRIDOR_DEV_EVENTS.csv", index=False)
    summ = {"spec_id": DEV_SPEC_ID, "north_star_hash": NORTH_STAR_HASH, "n_sessions": len(sessions_list), "n_ticks": int(tot), "volume_real": has_vol,
            "rows": int(len(out)), "feature_errors": int(total_err), "elapsed_s": round(time.time() - T0, 1),
            "counts": out.groupby(["det", "res", "preset", "fcode"]).size().reset_index(name="n").to_dict("records") if len(out) else []}
    (out_dir / "ES_CORRIDOR_DEV_SUMMARY.json").write_text(json.dumps(summ, indent=2), encoding="utf-8")
    print("=== EDGELAB_DEV_EVENTS_SUMMARY_START ===", flush=True)
    print(json.dumps(summ, indent=2), flush=True)
    print("=== EDGELAB_DEV_EVENTS_SUMMARY_END ===", flush=True)
