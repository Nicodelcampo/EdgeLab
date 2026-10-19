#!/usr/bin/env python3
r"""GC: presión, avance y trayectorias — V2 sobre la release canónica (manifiesto docs/research/GC_PRESSURE_PROGRESS_V2_MANIFIESTO_20261014.md).

Reutiliza SIN CAMBIOS el motor de medición del agente de Notion (`tools/vendor/notion_phenomena.py`) y corrige la capa de datos y de análisis:
release v4 (contrato líder causal por sesión), calibración congelada en las primeras 60 sesiones, atlas en las 61-180, sesiones 181+ SELLADAS
(no se leen), unidad estadística = sesión (bootstrap por cluster), placebo de dirección y contraste interno para P2, correlación parcial.
Información, sin P&L. Todo es PROVISIONAL (release candidata).

Uso: python tools/gc_pressure_atlas_v2.py --release D:/.../release_v4 --out docs/research/gc_pressure_v2_20261014
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import zlib
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from vendor.notion_phenomena import ClockMeasurements  # noqa: E402
import release_io  # noqa: E402

CT = ZoneInfo("America/Chicago")
ASSET = "GC"
PRESSURE_EDGES = np.array([0.5, 1.0, 2.0])
PROGRESS_EDGES = np.array([-4.0, -2.0, 2.0, 4.0])
NONOVERLAP_NS = 40 * 10**9
MIN_CAL = 100
N_CAL, N_ATLAS = 60, 120
MAX_GAP_NS = 10_000_000_000
SESSION_COLS = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "volume", "release_row", "outside_regular", "contract"]
FEATS = ("ts", "dir", "press_cur", "press_pri", "cur_dir", "pri_dir", "abs_prog", "rng", "path", "pratio", "cratio", "cnt", "net_cur", "net_pri")
KEYS = ("RTH:1", "RTH:-1", "OTHER:1", "OTHER:-1")


# ------------------------------------------------------------------ utilidades
def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def phase_array(ts_ns: np.ndarray) -> np.ndarray:
    """1 = RTH (08:30 <= hora de Chicago < 15:00), 0 = OTHER. Mismo reloj que el protocolo original (510 <= minutos < 900)."""
    idx = pd.DatetimeIndex(pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), utc=True)).tz_convert(CT)
    m = idx.hour.to_numpy() * 60 + idx.minute.to_numpy()
    return ((m >= 510) & (m < 900)).astype(np.int8)


def key_array(phase: np.ndarray, direction: np.ndarray) -> np.ndarray:
    return np.array([("RTH" if p else "OTHER") + ":" + str(int(d)) for p, d in zip(phase, direction)])


def pressure_bin(x):
    return np.searchsorted(PRESSURE_EDGES, x, side="right")


def progress_bin(x):
    return np.searchsorted(PROGRESS_EDGES, x, side="right")


def select_nonoverlap(t_ns: np.ndarray) -> np.ndarray:
    """Máscara booleana: primera ancla elegible de la sesión y luego la primera >= 40 s después de la última seleccionada."""
    sel = np.zeros(len(t_ns), dtype=bool)
    last = None
    for i, t in enumerate(t_ns):
        if last is None or t - last >= NONOVERLAP_NS:
            sel[i] = True
            last = t
    return sel


# ------------------------------------------------------------------ datos de sesión
def session_arrays(table) -> dict:
    """Ticks de una sesión sin la pausa 16-17 CT (`outside_regular == False`), con un único contrato."""
    reg = ~np.asarray(table["outside_regular"].to_numpy(zero_copy_only=False), dtype=bool)
    contracts = set(pd.unique(np.asarray(table["contract"].to_pylist())[reg])) if reg.any() else set()
    if len(contracts) != 1:
        raise ValueError(f"se esperaba un único contrato por sesión, hay {sorted(contracts)}")
    a = {k: np.asarray(table[k].to_numpy(zero_copy_only=False))[reg] for k in SESSION_COLS if k not in ("outside_regular", "contract")}
    a["contract"] = next(iter(contracts))
    return a


def dataset_checks(a: dict) -> dict:
    """Integridad del dato por sesión, independiente de la verificación de la release."""
    ts, px, b, k, v = a["ts_utc_ns"], a["price_ticks"], a["bid_ticks"], a["ask_ticks"], a["volume"]
    n = len(ts)
    valid = (b > 0) & (k > 0)
    d = np.diff(ts)
    hours = (ts // 3_600_000_000_000)
    span = int(hours[-1] - hours[0] + 1)
    return dict(contract=a["contract"], ticks=int(n), valid_quote_pct=round(float(valid.mean()) * 100, 3),
                crossed=int((valid & (b > k)).sum()), locked=int((valid & (b == k)).sum()), nonpositive_price=int((px <= 0).sum()),
                duplicate_ts_pct=round(float((d == 0).mean()) * 100, 3) if n > 1 else 0.0, ts_nonmonotonic=int((d < 0).sum()),
                gaps_over_10s=int((d > MAX_GAP_NS).sum()), max_gap_s=round(float(d.max()) / 1e9, 1) if n > 1 else 0.0,
                empty_utc_hours=int(span - len(np.unique(hours))), max_abs_tick_jump=int(np.abs(np.diff(px)).max()) if n > 1 else 0,
                zero_volume_ticks=int((v <= 0).sum()), max_trade_volume=float(v.max()), release_row_strict=bool((np.diff(a["release_row"]) > 0).all()))


def anchor_features(a: dict, trade_date: int) -> tuple[dict, dict]:
    """Corre el motor original por sesión y devuelve arrays por ancla elegible (par medible, cobertura de signo >= 80 %) y conteos de estados."""
    iso = f"{trade_date // 10000:04d}-{trade_date // 100 % 100:02d}-{trade_date % 100:02d}"
    cm = ClockMeasurements(max_ticks=8_000_000, max_anchors=250_000, wall_seconds=3000, max_gap_ns=MAX_GAP_NS)
    rows, counts = [], {}
    bump = lambda s: counts.__setitem__(s, counts.get(s, 0) + 1)
    for r in cm.measure(a["ts_utc_ns"], a["release_row"], a["price_ticks"], a["volume"], a["bid_ticks"], a["ask_ticks"], trade_date=iso):
        bump("ANCHORS")
        w = r["windows"]["20"]
        if w["status"] != "MEASURABLE_PAIR":
            bump("UNKNOWN_PAIR")
            continue
        cur, pri = w["current"], w["prior"]
        cc, pc = cur["signed_volume_coverage"], pri["signed_volume_coverage"]
        if cc is None or pc is None or cc < 0.8 or pc < 0.8:
            bump("SIGNED_COVERAGE_BELOW_80PCT")
            continue
        d = int(w["direction_from_prior"])
        side = "buy_volume" if d == 1 else "sell_volume"
        vals = (float(r["timestamp_ns"]), d, cur[side], pri[side], w["directed_progress_ticks"], w["prior_directed_progress_ticks"],
                abs(w["directed_progress_ticks"]), cur["range_midpoint_ticks"], cur["path_midpoint_ticks"], w["pressure_ratio"], w["trade_count_ratio"],
                cur["count"], d * w["directed_progress_ticks"], d * w["prior_directed_progress_ticks"])
        if any(type(x) not in (int, float) or not math.isfinite(x) or (i in (2, 3, 6, 7, 8) and x < 0) for i, x in enumerate(vals)):
            bump("NONFINITE_DESCRIPTOR")
            continue
        rows.append(vals)
        bump("ELIGIBLE_BEFORE_CALIBRATION")
    arr = np.array(rows, dtype=np.float64).reshape(-1, len(FEATS))
    feats = {k: arr[:, i] for i, k in enumerate(FEATS)}
    feats["ts"] = feats["ts"].astype(np.int64)
    feats["dir"] = feats["dir"].astype(np.int8)
    return feats, counts


# ------------------------------------------------------------------ calibración congelada
def freeze_calibration(per_session: list[tuple[int, dict]]) -> dict:
    pool = {k: {"cur": [], "pri": []} for k in KEYS}
    for _, f in per_session:
        if not len(f["ts"]):
            continue
        keys = key_array(phase_array(f["ts"]), f["dir"])
        for k in KEYS:
            m = keys == k
            pool[k]["cur"].append(f["press_cur"][m])
            pool[k]["pri"].append(f["press_pri"][m])
    cells = {}
    for k in KEYS:
        cur = np.concatenate(pool[k]["cur"]) if pool[k]["cur"] else np.array([])
        pri = np.concatenate(pool[k]["pri"]) if pool[k]["pri"] else np.array([])
        c = {"anchors": int(len(cur)), "supported": bool(len(cur) >= MIN_CAL)}
        if c["supported"]:
            c["current_pressure_q80"] = float(np.quantile(cur, 0.8, method="linear"))
            c["prior_pressure_q80"] = float(np.quantile(pri, 0.8, method="linear"))
            if c["current_pressure_q80"] <= 0 or c["prior_pressure_q80"] <= 0:
                c = {"anchors": c["anchors"], "supported": False, "reason": "NONPOSITIVE_HIGH_PRESSURE_QUANTILE"}
        cells[k] = c
    out = {"schema": "gc_pressure_progress_v2_calibration", "sessions": [int(d) for d, _ in per_session], "minimum_cell_anchors": MIN_CAL,
           "cells": cells, "outcomes_used": False}
    out["sha256"] = digest(out)
    return out


def atlas_session(f: dict, cal: dict) -> dict:
    """Matrices por celda, ventanas no solapadas y descriptores de una sesión, usando la calibración congelada."""
    n = len(f["ts"])
    out = {"eligible": 0, "nonoverlap": 0, "pp_all": {k: np.zeros((4, 5), np.int64) for k in KEYS}, "pc_all": {k: np.zeros((5, 5), np.int64) for k in KEYS},
           "pp_no": {k: np.zeros((4, 5), np.int64) for k in KEYS}, "pc_no": {k: np.zeros((5, 5), np.int64) for k in KEYS}, "rows": None, "unsupported_cell": 0}
    if not n:
        return out
    ph = phase_array(f["ts"])
    keys = key_array(ph, f["dir"])
    sup = np.array([bool(cal["cells"][k]["supported"]) for k in keys])
    out["unsupported_cell"] = int((~sup).sum())
    a80 = np.array([cal["cells"][k].get("current_pressure_q80", np.nan) for k in keys])
    b80 = np.array([cal["cells"][k].get("prior_pressure_q80", np.nan) for k in keys])
    keep = sup
    if not keep.any():
        return out
    pn = f["press_cur"][keep] / a80[keep]
    cb, pbn, prb = progress_bin(f["cur_dir"][keep]), pressure_bin(pn), progress_bin(f["pri_dir"][keep])
    kk = keys[keep]
    for k in KEYS:
        m = kk == k
        np.add.at(out["pp_all"][k], (pbn[m], cb[m]), 1)
        np.add.at(out["pc_all"][k], (prb[m], cb[m]), 1)
    out["eligible"] = int(keep.sum())
    tt = f["ts"][keep]
    no = select_nonoverlap(tt)
    out["nonoverlap"] = int(no.sum())
    for k in KEYS:
        m = no & (kk == k)
        np.add.at(out["pp_no"][k], (pbn[m], cb[m]), 1)
        np.add.at(out["pc_no"][k], (prb[m], cb[m]), 1)
    cols = {"phase": ph[keep][no], "dir": f["dir"][keep][no], "net_cur": f["net_cur"][keep][no], "net_pri": f["net_pri"][keep][no],
            "cur_dir": f["cur_dir"][keep][no], "pri_dir": f["pri_dir"][keep][no], "press": pn[no], "abs_prog": f["abs_prog"][keep][no],
            "pratio": f["pratio"][keep][no], "cnt": f["cnt"][keep][no]}
    out["rows"] = pd.DataFrame(cols)
    return out


# ------------------------------------------------------------------ estadística por cluster
def norm_p(z: float) -> float:
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def holm(pvals: dict) -> dict:
    ks = sorted(pvals, key=pvals.get)
    out, mx = {}, 0.0
    for i, k in enumerate(ks):
        mx = max(mx, min(1.0, (len(ks) - i) * pvals[k]))
        out[k] = mx
    return out


def boot_weights(n_sessions: int, B: int, seed: int) -> np.ndarray:
    """Matriz B x S de multiplicidades de remuestreo por sesión (bootstrap de clusters)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_sessions, size=(B, n_sessions))
    W = np.zeros((B, n_sessions), dtype=np.float64)
    for b in range(B):
        W[b] = np.bincount(idx[b], minlength=n_sessions)
    return W


def placebo_cur(rows: pd.DataFrame) -> np.ndarray:
    """Esperanza exacta, bajo permutación de la dirección dentro de la fase, del avance actual: media de la dirección del grupo x avance neto actual."""
    mean_dir = rows.groupby("phase")["dir"].transform("mean").to_numpy()
    return mean_dir * rows["net_cur"].to_numpy()


def p1_estimates(per_session_rows: list[pd.DataFrame], W: np.ndarray, phase: int | None) -> dict:
    S = len(per_session_rows)
    sc, sp, nn = np.zeros(S), np.zeros(S), np.zeros(S)
    for i, r in enumerate(per_session_rows):
        if r is None or not len(r):
            continue
        if phase is not None:
            r = r[r["phase"] == phase]
            if not len(r):
                continue
        plc = placebo_cur(r)
        sc[i], sp[i], nn[i] = r["cur_dir"].sum(), plc.sum(), len(r)
    tot_n = nn.sum()
    est = (sc.sum() - sp.sum()) / tot_n if tot_n else float("nan")
    bn = W @ nn
    with np.errstate(divide="ignore", invalid="ignore"):
        bd = (W @ sc - W @ sp) / bn
        bm = (W @ sc) / bn
    ok = np.isfinite(bd)
    se = float(np.std(bd[ok], ddof=1)) if ok.sum() > 2 else float("nan")
    lo, hi = (float(np.percentile(bd[ok], 2.5)), float(np.percentile(bd[ok], 97.5))) if ok.sum() > 2 else (float("nan"), float("nan"))
    return dict(delta_ticks=float(est), mean_cur_directed_ticks=float(sc.sum() / tot_n) if tot_n else float("nan"), mean_placebo_ticks=float(sp.sum() / tot_n) if tot_n else float("nan"),
                se=se, ci95=[lo, hi], mde_2p8_se=float(2.8 * se), p=norm_p(est / se) if se and se > 0 else float("nan"), windows=int(tot_n), sessions=int((nn > 0).sum()))


def p2_estimates(per_session_rows: list[pd.DataFrame], W: np.ndarray) -> dict:
    S = len(per_session_rows)
    M = np.zeros((S, 6))   # nA, aA, bA (prior>=4) ; nB, aB, bB (prior en [-2,2))
    for i, r in enumerate(per_session_rows):
        if r is None or not len(r):
            continue
        A, B_ = r[r["pri_dir"] >= 4.0], r[(r["pri_dir"] >= -2.0) & (r["pri_dir"] < 2.0)]
        M[i] = [len(A), (A["cur_dir"] >= 2.0).sum(), (A["cur_dir"] < -2.0).sum(), len(B_), (B_["cur_dir"] >= 2.0).sum(), (B_["cur_dir"] < -2.0).sum()]

    def d(m):
        with np.errstate(divide="ignore", invalid="ignore"):
            return (m[..., 1] - m[..., 2]) / m[..., 0] - (m[..., 4] - m[..., 5]) / m[..., 3]
    tot = M.sum(0)
    est = float(d(tot))
    bd = d(W @ M)
    ok = np.isfinite(bd)
    se = float(np.std(bd[ok], ddof=1)) if ok.sum() > 2 else float("nan")
    return dict(p2=est, d_prior_advance=float((tot[1] - tot[2]) / tot[0]) if tot[0] else float("nan"), d_prior_small=float((tot[4] - tot[5]) / tot[3]) if tot[3] else float("nan"),
                n_prior_advance=int(tot[0]), n_prior_small=int(tot[3]), se=se, ci95=[float(np.percentile(bd[ok], 2.5)), float(np.percentile(bd[ok], 97.5))] if ok.sum() > 2 else [None, None],
                mde_2p8_se=float(2.8 * se), p=norm_p(est / se) if se and se > 0 else float("nan"), sessions=int((M[:, 0] > 0).sum()))


def moments(r: pd.DataFrame, cols: tuple[str, str, str]) -> np.ndarray:
    """Estadísticos suficientes de segundo orden de tres variables: n, sumas (3) y productos cruzados (6)."""
    x, y, z = (r[c].to_numpy(float) for c in cols)
    return np.array([len(x), x.sum(), y.sum(), z.sum(), (x * x).sum(), (y * y).sum(), (z * z).sum(), (x * y).sum(), (x * z).sum(), (y * z).sum()])


def corr_from_moments(m: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pearson r_xy, r_xz, r_yz y la parcial r_xy.z desde momentos agregados (vectorizado sobre filas de m)."""
    n = m[..., 0]
    mx, my, mz = m[..., 1] / n, m[..., 2] / n, m[..., 3] / n
    vx, vy, vz = m[..., 4] / n - mx ** 2, m[..., 5] / n - my ** 2, m[..., 6] / n - mz ** 2
    cxy, cxz, cyz = m[..., 7] / n - mx * my, m[..., 8] / n - mx * mz, m[..., 9] / n - my * mz
    with np.errstate(divide="ignore", invalid="ignore"):
        rxy, rxz, ryz = cxy / np.sqrt(vx * vy), cxz / np.sqrt(vx * vz), cyz / np.sqrt(vy * vz)
        partial = (rxy - rxz * ryz) / np.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return rxy, rxz, partial


def correlation_report(per_session_rows: list[pd.DataFrame], W: np.ndarray, x: str, y: str, z: str) -> dict:
    S = len(per_session_rows)
    M = np.zeros((S, 10))
    for i, r in enumerate(per_session_rows):
        if r is not None and len(r):
            rr = r.assign(lcnt=np.log1p(r["cnt"].to_numpy(float)))
            M[i] = moments(rr, (x, y, "lcnt"))
    tot = M.sum(0)
    rxy, _, par = corr_from_moments(tot[None, :])
    brxy, _, bpar = corr_from_moments(W @ M)
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    return dict(x=x, y=y, controlled_by="log1p(trades de la ventana actual)", pearson=float(rxy[0]), pearson_ci95=ci(brxy), partial=float(par[0]), partial_ci95=ci(bpar), windows=int(tot[0]))


def table_report(rows_counts: dict, label: str) -> dict:
    """Suma de matrices por sesión y lift contra independencia de marginales (sólo para la tabla 5x5)."""
    out = {}
    for name, mats in rows_counts.items():
        tot = sum(mats.values())
        out[name] = {"total": tot.tolist(), "by_cell": {k: m.tolist() for k, m in mats.items()}}
        if name.startswith("pc"):
            n = tot.sum()
            exp = np.outer(tot.sum(1), tot.sum(0)) / n if n else np.zeros_like(tot, float)
            with np.errstate(divide="ignore", invalid="ignore"):
                out[name]["lift_vs_independence"] = np.where(exp > 0, tot / exp, np.nan).tolist()
    return out


# ------------------------------------------------------------------ corrida
def run(release: str, n_cal: int = N_CAL, n_atlas: int = N_ATLAS, boot: int = 2000, log=print) -> dict:
    t0 = time.time()
    sessions = release_io.selected_sessions(release, ASSET)
    cal_s, atl_s = sessions[:n_cal], sessions[n_cal:n_cal + n_atlas]
    sealed = sessions[n_cal + n_atlas:]
    log(f"sesiones GC: {len(sessions)} | calibración {len(cal_s)} | atlas {len(atl_s)} | SELLADAS (no se leen) {len(sealed)}")
    sha_asset = release_io.verify_asset_hash(release, ASSET)
    man_sha = release_io.manifest_sha256(release)

    def read(td):
        t = release_io.read_asset(release, ASSET, td, td, columns=SESSION_COLS, verify_hash=False, purpose="provisional_research")
        return session_arrays(t)

    checks, state_counts, cal_feats = {}, {}, []
    for td, c in cal_s:
        a = read(td)
        checks[td] = dataset_checks(a)
        f, cnt = anchor_features(a, td)
        cal_feats.append((td, f))
        state_counts[td] = cnt
    cal = freeze_calibration(cal_feats)
    log(f"calibración congelada sha256={cal['sha256'][:12]}… celdas={ {k: v['anchors'] for k, v in cal['cells'].items()} }")
    del cal_feats
    atlas = []
    for i, (td, c) in enumerate(atl_s):
        a = read(td)
        checks[td] = dataset_checks(a)
        f, cnt = anchor_features(a, td)
        s = atlas_session(f, cal)
        s["trade_date"], s["contract"] = td, c
        atlas.append(s)
        state_counts[td] = cnt
        if (i + 1) % 20 == 0:
            log(f"  atlas {i + 1}/{len(atl_s)}  ({time.time() - t0:.0f} s)")
    rows_by_session = [s["rows"] for s in atlas]
    S = len(atlas)
    W = boot_weights(S, boot, zlib.crc32(b"gc_pressure_v2"))
    p1_all, p1_rth, p1_oth = (p1_estimates(rows_by_session, W, ph) for ph in (None, 1, 0))
    p2 = p2_estimates(rows_by_session, W)
    hp = holm({"P1_primaria": p1_all["p"], "P1_RTH": p1_rth["p"], "P1_OTHER": p1_oth["p"], "P2": p2["p"]})
    half = S // 2
    Wh = boot_weights(half, boot, zlib.crc32(b"gc_pressure_v2_h1")), boot_weights(S - half, boot, zlib.crc32(b"gc_pressure_v2_h2"))
    split = {"sesiones_1a_mitad": p1_estimates(rows_by_session[:half], Wh[0], None), "sesiones_2a_mitad": p1_estimates(rows_by_session[half:], Wh[1], None)}
    corr = {"presion_vs_avance_absoluto": correlation_report(rows_by_session, W, "press", "abs_prog", "cnt"),
            "presion_vs_avance_dirigido": correlation_report(rows_by_session, W, "press", "cur_dir", "cnt"),
            "razon_presion_vs_avance_dirigido": correlation_report(rows_by_session, W, "pratio", "cur_dir", "cnt")}
    tables = table_report({"pp_no": {k: sum(s["pp_no"][k] for s in atlas) for k in KEYS}, "pc_no": {k: sum(s["pc_no"][k] for s in atlas) for k in KEYS},
                           "pp_all": {k: sum(s["pp_all"][k] for s in atlas) for k in KEYS}, "pc_all": {k: sum(s["pc_all"][k] for s in atlas) for k in KEYS}}, "")
    allrows = pd.concat([r for r in rows_by_session if r is not None and len(r)], ignore_index=True) if any(r is not None and len(r) for r in rows_by_session) else pd.DataFrame()
    per_session_mean = [float(r["cur_dir"].mean()) if r is not None and len(r) else None for r in rows_by_session]
    dc = pd.DataFrame.from_dict(checks, orient="index")
    dataset = {"sesiones_leidas": int(len(dc)), "contrato_unico_por_sesion": True, "contratos_distintos": sorted(dc["contract"].unique().tolist()),
               "valid_quote_pct_min": float(dc["valid_quote_pct"].min()), "crossed_total": int(dc["crossed"].sum()), "locked_total": int(dc["locked"].sum()),
               "nonpositive_price_total": int(dc["nonpositive_price"].sum()), "ts_nonmonotonic_total": int(dc["ts_nonmonotonic"].sum()),
               "release_row_estrictamente_creciente_en_todas": bool(dc["release_row_strict"].all()), "duplicate_ts_pct_max": float(dc["duplicate_ts_pct"].max()),
               "gaps_over_10s_total": int(dc["gaps_over_10s"].sum()), "max_gap_s_max": float(dc["max_gap_s"].max()), "empty_utc_hours_total": int(dc["empty_utc_hours"].sum()),
               "max_abs_tick_jump_max": int(dc["max_abs_tick_jump"].max()), "zero_volume_ticks_total": int(dc["zero_volume_ticks"].sum()),
               "ticks_por_sesion": {"min": int(dc["ticks"].min()), "mediana": int(dc["ticks"].median()), "max": int(dc["ticks"].max())},
               "sesiones_anomalas": [int(td) for td, r in dc.iterrows() if r["valid_quote_pct"] < 99.0 or r["crossed"] or r["ts_nonmonotonic"] or r["max_abs_tick_jump"] > 50]}
    tot_counts = {}
    for cnt in state_counts.values():
        for k, v in cnt.items():
            tot_counts[k] = tot_counts.get(k, 0) + v
    return {"schema": "gc_pressure_progress_v2_results", "status": "DESCRIPTIVO_Y_DE_INFORMACION_PROVISIONAL_NO_EDGE", "purpose": "provisional_research", "pnl": False,
            "release": {"manifest_sha256": man_sha, "gc_parquet_sha256_verificado": sha_asset},
            "particion": {"sesiones_totales": len(sessions), "calibracion": [cal_s[0][0], cal_s[-1][0]] if cal_s else None, "atlas": [atl_s[0][0], atl_s[-1][0]] if atl_s else None,
                          "selladas_no_leidas": len(sealed)},
            "calibracion_congelada": cal, "estados_de_ventana_20s": tot_counts,
            "ventanas": {"anclas_elegibles_atlas": int(sum(s["eligible"] for s in atlas)), "ventanas_no_solapadas_atlas": int(sum(s["nonoverlap"] for s in atlas)),
                         "sesiones_con_30_o_mas_no_solapadas": int(sum(s["nonoverlap"] >= 30 for s in atlas)), "ancla_en_celda_sin_soporte": int(sum(s["unsupported_cell"] for s in atlas))},
            "pruebas_de_informacion": {"P1_primaria": p1_all, "P1_RTH": p1_rth, "P1_OTHER": p1_oth, "P2": p2, "holm_p_ajustado": hp, "n_efectivo_de_pruebas": 4, "bootstrap_remuestreos": boot},
            "estabilidad_por_mitades_P1": split, "correlaciones_no_solapadas": corr, "tablas": tables,
            "distribucion_por_sesion_de_avance_dirigido_actual": {"cuantiles_10_25_50_75_90": [float(x) for x in np.nanquantile([m for m in per_session_mean if m is not None], [0.1, 0.25, 0.5, 0.75, 0.9])]},
            "descriptores_continuos_no_solapados": {c: {"media": float(allrows[c].mean()), "cuantiles_10_25_50_75_90": [float(x) for x in allrows[c].quantile([0.1, 0.25, 0.5, 0.75, 0.9])]}
                                                    for c in ("press", "cur_dir", "pri_dir", "abs_prog", "pratio", "cnt")} if len(allrows) else {},
            "pruebas_del_dataset": dataset, "segundos": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-cal", type=int, default=N_CAL)
    ap.add_argument("--n-atlas", type=int, default=N_ATLAS)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args()
    import shutil
    import subprocess
    git = shutil.which("git") or "git"
    g = lambda *x: subprocess.run([git, "-C", str(HERE.parent), *x], capture_output=True, text=True).stdout.strip()
    head, dirty = g("rev-parse", "HEAD"), bool(g("status", "--porcelain", "--", "tools", "tests"))
    res = run(a.release, a.n_cal, a.n_atlas, a.boot, log=lambda s: print(s, flush=True))
    res["procedencia"] = {"repo_commit": head, "tools_o_tests_con_cambios_sin_commitear": dirty, "manifiesto": "docs/research/GC_PRESSURE_PROGRESS_V2_MANIFIESTO_20261014.md",
                          "motor_original": "tools/vendor/notion_phenomena.py (copia sin cambios; SHA en su cabecera)"}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "GC_PRESSURE_PROGRESS_V2_RESULTADOS.json").write_text(json.dumps(res, indent=1, allow_nan=True, default=float), encoding="utf-8")
    (out / "calibration_frozen.json").write_text(json.dumps(res["calibracion_congelada"], indent=1), encoding="utf-8")
    print("listo:", out)


if __name__ == "__main__":
    main()
