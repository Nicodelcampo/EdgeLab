# ===================================================================================================
# CENSO SIN RETORNOS — impulsos del corredor (DET_NT8, 100T) x zonas HFT (port Python de HFTZonesESPureV2Flat)
# Se concatena DESPUES de Pasada 2 + DET_NT8 + dev addon (sin su main) + el port HFT. No calcula desenlaces: sólo presencia/toque en W <= conf_bar.
# Definicion: docs/research/DEFINICION_INICIAL_CORREDOR_X_HFT_20261016.md
# ===================================================================================================
import os

CENSUS_SPEC = "EXP-CORREDOR-HFT-CENSO-v1"
DISC_START_C, DISC_END_C = 20250718, 20260331
EXT_FIXED = (300, 600, 1200)
HFT_TICK = 0.25


def presence_for_impulse(lo_w, hi_w, b0, cb, zl, zu, mb, ext):
    """lo_w/hi_w: minimos y maximos de las barras de W (indices b0..b0+len-1).
    cb: barra de creacion (primera barra con cierre >= end_ts) de cada zona HFT; zl/zu: limites; mb: barra de mitigacion (inf si no hay);
    ext: int (extension fija en barras) | 'mit' (activa hasta la primera barra que cruza toda la zona) | 'first' (activa hasta su primer toque).
    Devuelve (n_activas_en_W, n_tocadas_en_W, n_tocadas_y_dentro_al_final)."""
    if len(cb) == 0:
        return 0, 0, 0
    b = (b0 + np.arange(len(lo_w)))[:, None]
    active = b > cb[None, :]
    if isinstance(ext, int):
        active &= b <= (cb[None, :] + ext)
    elif ext == "mit":
        active &= b <= mb[None, :]
    touch = (lo_w[:, None] <= zu[None, :]) & (hi_w[:, None] >= zl[None, :])
    if ext == "first":
        t_any = active & touch
        first_t = np.where(t_any.any(0), t_any.argmax(0), len(lo_w))
        idx = np.arange(len(lo_w))[:, None]
        active = active & (idx <= first_t[None, :])
    act_any = active.any(0)
    touched = (active & touch).any(0)
    inside_end = touched & (lo_w[-1] >= zl) & (hi_w[-1] <= zu)
    return int(act_any.sum()), int(touched.sum()), int(inside_end.sum())


def mitigation_bars(lo, hi, cb, zl, zu, s_start, s_end):
    """Primera barra > cb que cruza toda la zona (low<=zl y high>=zu) dentro de la sesion; inf si no hay."""
    out = np.full(len(cb), 10 ** 9, dtype=np.int64)
    for k in range(len(cb)):
        a = int(cb[k]) + 1
        if a >= s_end:
            continue
        m = (lo[a:s_end] <= zl[k]) & (hi[a:s_end] >= zu[k])
        if m.any():
            out[k] = a + int(m.argmax())
    return out


def run_census(sessions_list, out_dir):
    t0 = time.time()
    B, sess_td = dev_build_bars(sessions_list, 100)
    sid_b, ts_end, hi_b, lo_b = B["sid"], B["ts_end"], B["h"], B["l"]
    # bordes de sesion en indices globales
    s_first, s_last = {}, {}
    for i, s in enumerate(sid_b):
        s_last[int(s)] = i + 1
        s_first.setdefault(int(s), i)
    # zonas HFT por sesion (port Flat; sin absorb)
    hft = {}
    n_hft_total = 0
    prm = HFT_Params(mostrar_absorb=False)
    for s in sessions_list:
        zs = hft_run(s["ts_utc_ns"], s["prices"], s["vol"], HFT_TICK, prm)
        zs = [z for z in zs if "ABSORB" not in str(z.bucket).upper()]
        if not zs:
            hft[s["session_id"]] = None
            continue
        end_ns = np.array([z.end_ts for z in zs], dtype=np.int64) * 1_000_000
        lo_z = np.array([min(z.price_lower, z.price_upper) for z in zs]); hi_z = np.array([max(z.price_lower, z.price_upper) for z in zs])
        dr = np.array([z.dir for z in zs])
        hft[s["session_id"]] = (end_ns, lo_z, hi_z, dr)
        n_hft_total += len(zs)
    print(f"sesiones={len(sessions_list)} zonas HFT (sin absorb)={n_hft_total} ({time.time() - t0:.0f}s)", flush=True)
    presets = {1: (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72),
               2: (60, 45, 12, 65, 24, 0.85, 0.84, 0.030, 0.88, 0.80, 1.05, 0.44, 0.46, 0.64)}
    rows = []
    variants = [("fix300", 300), ("fix600", 600), ("fix1200", 1200), ("dyn_mit", "mit"), ("dyn_first", "first")]
    for pid, pc in presets.items():
        state, score_s, ema_a, atr_a, zones_mat, s_start_b, s_end_b = detect_zones_nt8_numba(
            B["o"], B["h"], B["l"], B["c"], B["sid"], B["cid"], 200, 100,
            pc[0], pc[1], pc[2], pc[3], pc[4], pc[5], pc[6], pc[7], pc[8], pc[9], pc[10], pc[11], pc[12], pc[13], 40, 5, 1.60, TICK_ES)
        cache = {}
        for z in zones_mat:
            sid = int(z[13]); ob, cf = int(z[2]), int(z[4])
            if cf <= ob + 1 or sid not in s_first:
                continue
            w_end = ob + (cf - ob) // 2
            lo_w, hi_w = lo_b[ob:w_end + 1], hi_b[ob:w_end + 1]
            row = dict(preset=pid, session_id=sid, trade_date=sess_td.get(sid), zone_id=int(z[0]), imp_dir=int(z[1]), origin_bar=ob, conf_bar=cf,
                       conf_len=cf - ob, w_bars=w_end - ob + 1, h_ticks=float(z[10]), score=float(z[12]))
            h = hft.get(sid)
            if h is None:
                for name, _ in variants:
                    row.update({f"{name}_n_act": 0, f"{name}_n_touch": 0, f"{name}_inside": 0})
                rows.append(row); continue
            if sid not in cache:
                end_ns, lo_z, hi_z, dr = h
                cb = np.searchsorted(ts_end, end_ns, side="left")            # primera barra con cierre >= end_ts (disponible)
                cb = np.minimum(cb, s_last[sid] - 1)
                mb = mitigation_bars(lo_b, hi_b, cb, lo_z, hi_z, s_first[sid], s_last[sid])
                cache[sid] = (cb, lo_z, hi_z, mb)
            cb, lo_z, hi_z, mb = cache[sid]
            sel = cb < w_end                                              # solo zonas conocidas antes del final de W
            for name, ext in variants:
                na, nt, ni = presence_for_impulse(lo_w, hi_w, ob, cb[sel], lo_z[sel], hi_z[sel], mb[sel], ext)
                row.update({f"{name}_n_act": na, f"{name}_n_touch": nt, f"{name}_inside": ni})
            rows.append(row)
        print(f"preset {pid}: impulsos={sum(1 for r in rows if r['preset'] == pid)} ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    # --- resumen y potencia aproximada (sin desenlaces) ---
    summ = {"spec": CENSUS_SPEC, "sesiones": len(sessions_list), "zonas_hft_total": int(n_hft_total),
            "zonas_hft_por_sesion_media": round(n_hft_total / max(len(sessions_list), 1), 1), "presets": {}}
    for pid in sorted(df.preset.unique()):
        d = df[df.preset == pid]
        info = {"impulsos": int(len(d)), "impulsos_por_sesion_media": round(len(d) / d.session_id.nunique(), 2), "sesiones_con_impulsos": int(d.session_id.nunique()), "variantes": {}}
        for name, _ in variants:
            tocado = d[f"{name}_n_touch"] > 0
            activa = d[f"{name}_n_act"] > 0
            n1, n0 = int(tocado.sum()), int((~tocado).sum())
            # MDE80 aprox. para diferencia de proporciones (potencia 80 %, alfa 5 % bilateral) con efecto de diseno 2 por clustering; p0 de referencia 0.2 y 0.4
            mde = {}
            for p0 in (0.2, 0.4):
                if n1 > 0 and n0 > 0:
                    se = np.sqrt(2.0 * (p0 * (1 - p0)) * (1.0 / n1 + 1.0 / n0))
                    mde[f"p0={p0}"] = round(float(2.8 * se * 100), 1)
            info["variantes"][name] = dict(prevalencia_activa=round(float(activa.mean()), 4), prevalencia_tocada=round(float(tocado.mean()), 4),
                                           n_tocada=n1, n_control_sin_toque=n0, activa_sin_toque=int((activa & ~tocado).sum()),
                                           termina_dentro_de_zona=int((d[f"{name}_inside"] > 0).sum()), mde80_pp_aprox=mde,
                                           n_tocadas_mediana_cond=float(d.loc[tocado, f"{name}_n_touch"].median()) if n1 else None)
        summ["presets"][str(pid)] = info
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "CENSO_CORREDOR_X_HFT_IMPULSOS.csv", index=False)
    (out / "CENSO_CORREDOR_X_HFT_RESUMEN.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print("=== CENSO_CORREDOR_HFT_START ===", flush=True)
    print(json.dumps(summ, indent=1), flush=True)
    print("=== CENSO_CORREDOR_HFT_END ===", flush=True)
    return summ


def main_census():
    pfile = locate_es_parquet()
    sessions_list, cmap, has_vol = dev_load_sessions(pfile)
    sessions_list = [s for s in sessions_list if DISC_START_C <= s["trade_date"] <= DISC_END_C]
    print(f"{CENSUS_SPEC}: {len(sessions_list)} sesiones de descubrimiento", flush=True)
    run_census(sessions_list, os.environ.get("CENSUS_OUT", "/kaggle/working"))
