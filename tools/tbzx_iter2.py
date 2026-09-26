#!/usr/bin/env python3
r"""TBZX iteración 2 (manifiesto §8): lo que puede engañar y lo que da robustez.

    .venv\Scripts\python tools\tbzx_iter2.py bars --inst NQ --workers 2
    .venv\Scripts\python tools\tbzx_iter2.py measure --inst ES
    .venv\Scripts\python tools\tbzx_iter2.py measure --inst NQ
    .venv\Scripts\python tools\tbzx_iter2.py report

Reutiliza el detector y las métricas de `tbzx_espejo.py` (paridad con el visor y tests). Nulos:
- N-VOL: otra sesión, misma hora (± 1 h), misma actividad previa (rango y duración de las últimas maxBars velas ± 25 %).
- N-REV: otra sesión, misma hora, tramo del mismo tamaño que también acaba de retroceder 0,3, con sus propios A y B,
  que NO califica como impulso (tardó más de maxBars velas o eficiencia < 0,6).
- N-VOLSTR (sólo configuración de referencia): N-VOL con el mismo estiramiento alineado respecto de la EMA20 (± 0,5 ATR).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import tbz_e2 as TB  # noqa: E402
import tbzx_espejo as TX  # noqa: E402

NS = TX.NS
OUT = TX.OUT
DOC = TX.DOC
LEDGER = TX.LEDGER
H, PEN = TX.H, TX.PEN_BARS
GRIDS = {"ES": TX.GRID, "NQ": [(mb, mw) for mb in (10, 20, 40) for mw in (12, 17, 24, 34, 48, 68)]}
REF = (20, 17)                    # configuración de Nico en ES
CAP = 20000
N_PH = 3
TOD = 3600
TOL = 0.25
STR_TOL = 0.5
SEED = 20260926


def bars_dir(inst):
    return OUT / "bars" if inst == "ES" else OUT / f"bars_{inst}"


def _bars_session(args):
    inst, s = args
    from edgelab.bridge.bars import build_tick_bars
    from edgelab.bridge.ticks import load_canonical_parquet
    f = bars_dir(inst) / f"{s['trade_date']}.npz"
    if f.exists():
        return s["trade_date"], "EXISTE"
    tk = load_canonical_parquet(s["path"], contract=s["contract"], start_utc_ns=s["start"], end_utc_ns=s["end"])
    ts = tk.ts_ns.astype(np.int64)
    if len(ts) < 5000 or bool((np.diff(ts) < 0).any()):
        return s["trade_date"], "POCA_ACTIVIDAD_O_NO_MONOTONO"
    if int(ts[-1]) >= TB.HOLDOUT_NS:
        raise ValueError("holdout decodificado")
    b = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
    f.parent.mkdir(parents=True, exist_ok=True)
    np.savez(f, t=(b.end_ns / NS).astype(np.float64), h=b.high_t.astype(np.int32), l=b.low_t.astype(np.int32),
             c=b.close_t.astype(np.int32), v=b.volume.astype(np.float32), contract=s["contract"])
    return s["trade_date"], "OK"


def canonical_sessions(inst):
    """Contrato por sesión con la regla canónica (edgelab/data/contract_regime.py): para el día D, el líder de la
    sesión COMPLETA anterior (D-1), sólo hacia adelante, empate conserva el vigente. Proxy de volumen: ticks por
    sesión de los manifiestos de bundles (no traen volumen). Reemplaza la regla vieja «más ticks el mismo día»."""
    if inst == "MYM":
        cat_file = REPO / "docs" / "research" / "contract_regimes" / "MYM_canonical_sessions_catalog_20260925.json"
        cat = json.loads(cat_file.read_text(encoding="utf-8"))
        out = []
        for s in cat["sessions"]:
            if int(s["end"]) > TB.HOLDOUT_NS:
                continue
            out.append(dict(trade_date=str(s["trade_date"]), path=s["path"], contract=s["contract"],
                            start=int(s["start"]), end=int(s["end"]), ticks=int(s.get("ticks", 0))))
        return out
    import glob
    from collections import defaultdict
    per = defaultdict(dict)
    for f in glob.glob(str(TB.BUNDLES / f"{inst}_[0-9]*_25T_HFT.manifest.json")):
        m = json.loads(Path(f).read_text(encoding="utf-8"))
        for s in m["sessions"]:
            if int(s["end_utc_ns"]) > TB.HOLDOUT_NS:
                continue
            per[str(s["trade_date"])][m["contract"]] = dict(trade_date=str(s["trade_date"]), path=m["source_path"], contract=m["contract"],
                                                             start=int(s["start_utc_ns"]), end=int(s["end_utc_ns"]), ticks=int(s.get("ticks", 0)))
    key = lambda c: (int(c.split()[1][3:]), int(c.split()[1][:2]))
    days, cur, out = sorted(per), None, []
    for i, d in enumerate(days):
        if i == 0:
            cur = max(per[d], key=lambda c: per[d][c]["ticks"])     # sin sesión previa: arranque (se documenta)
        else:
            prev = per[days[i - 1]]
            lead = max(prev, key=lambda c: prev[c]["ticks"])
            if key(lead) > key(cur) and prev[lead]["ticks"] > prev.get(cur, {}).get("ticks", 0):
                cur = lead
        if cur in per[d]:
            out.append(per[d][cur])
    return out


def step_bars(inst, workers):
    ss = [s for s in canonical_sessions(inst) if s["trade_date"] <= TB.EXP_END]
    for s in ss:                                  # caché con otro contrato: se aparta (no se borra) y se reconstruye
        f = bars_dir(inst) / f"{s['trade_date']}.npz"
        if f.exists() and str(np.load(f)["contract"]) != s["contract"]:
            f.rename(f.with_suffix(".npz.otro_contrato"))
            print("REEMPLAZA", s["trade_date"], s["contract"], flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for fu in as_completed([ex.submit(_bars_session, (inst, s)) for s in ss]):
            print(*fu.result(), flush=True)


def load(inst):
    S = {}
    for f in sorted(bars_dir(inst).glob("*.npz")):
        z = np.load(f)
        t = z["t"]
        et = pd.to_datetime(t, unit="s", utc=True).tz_convert(TB.ET)
        clock = ((et.hour * 3600 + et.minute * 60 + et.second).to_numpy() - 18 * 3600) % 86400
        S[f.stem] = dict(t=t, h=z["h"].astype(np.int64), l=z["l"].astype(np.int64), c=z["c"].astype(np.int64),
                         v=z["v"].astype(np.float64), clock=clock.astype(np.int64))
    return S


def declare(inst, keys):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    part = f"P-TBZX-{inst}-EXP"
    if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
        return part
    with measurement_episode(LEDGER, f"EP-TBZX-PARTICION-{inst}-20260926", goal=f"declarar partición TBZX {inst} antes de medir",
                             recorded_by="tools/tbzx_iter2.py measure", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_partition(part, "EXPLORATION", f"{inst} 25T jul-2025 a mar-2026", [f"{inst}:{k}" for k in keys])
    return part


def rev_pool(S, keys, mb):
    """Tramos del mismo tipo de fin (retroceso 0,3) sin exigir velocidad ni eficiencia, ventana 3·mb. Por ancho W."""
    rows = []
    for s in keys:
        x = S[s]
        sw = TX.detect(x["t"], x["h"], x["l"], x["c"], x["v"], 3 * mb, 4, 0.0, TX.R_END)
        n = len(x["c"])
        for b in sw:
            d, A, B, i0, iext, iend = int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(b[4]), int(b[5])
            if iend + H > n - 1:
                continue
            path = np.abs(np.diff(x["c"][i0:iext + 1])).sum()
            eff = abs(x["c"][iext] - x["c"][i0]) / path if path > 0 else 0.0
            qual = (iext - i0) <= mb and eff >= TX.E0
            rows.append((abs(B - A), int(x["clock"][iend]), s, iend, d, A, B, qual, x[f"rg{mb}"][iend], x[f"sec{mb}"][iend]))
    P = pd.DataFrame(rows, columns=["W", "clock", "s", "iend", "d", "A", "B", "qual", "rg", "sec"])
    P = P[~P.qual].sort_values(["W", "clock"])
    return {w: g.reset_index(drop=True) for w, g in P.groupby("W")}


def pick_rev(pool, W, clock, s, rng, rg0=None, sec0=None):
    tol = max(1, int(round(0.1 * W)))
    parts = []
    for w in range(W - tol, W + tol + 1):
        g = pool.get(w)
        if g is None:
            continue
        a, b = np.searchsorted(g.clock.to_numpy(), clock - TOD), np.searchsorted(g.clock.to_numpy(), clock + TOD)
        if b > a:
            parts.append(g.iloc[a:b])
    if not parts:
        return []
    C = pd.concat(parts)
    C = C[C.s != s]
    if rg0 is not None:                                   # N-REVVOL: además, la misma actividad previa (± 25 %)
        C = C[(np.abs(C.rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(C.sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))]
    if C.empty:
        return []
    return [C.iloc[int(i)] for i in rng.choice(len(C), size=min(N_PH, len(C)), replace=False)]


def pick_vol(S, keys, s, mb, clock, rg0, sec0, rng, str0=None, d=0):
    others = [k for k in keys if k != s]
    for _ in range(40):
        o = others[int(rng.integers(len(others)))]
        y = S[o]
        a, b = np.searchsorted(y["clock"], clock - TOD), np.searchsorted(y["clock"], clock + TOD)
        if b <= a:
            continue
        rg, sec = y[f"rg{mb}"][a:b], y[f"sec{mb}"][a:b]
        ok = (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
        ok &= (np.arange(a, b) + H < len(y["c"]) - 1)
        if str0 is not None:
            ok &= np.abs(d * y["str"]["ema20"][a:b] - str0) <= STR_TOL
        idx = np.flatnonzero(ok)
        if len(idx):
            return o, a + int(idx[int(rng.integers(len(idx)))])
    return None, None


def step_measure(inst):
    S = load(inst)
    keys = sorted(S)
    assert keys and max(keys) <= TB.EXP_END
    part = declare(inst, keys)
    grid = GRIDS[inst]
    for k in keys:
        for mb in sorted({g[0] for g in grid}):
            S[k][f"rg{mb}"], S[k][f"sec{mb}"] = TX.trailing(S[k], mb)
        S[k]["str"] = TX.stretch_context(S[k])
    det = {(mb, mw): {s: TX.detect(S[s]["t"], S[s]["h"], S[s]["l"], S[s]["c"], S[s]["v"], mb, mw, TX.E0, TX.R_END) for s in keys}
           for mb, mw in grid}
    per_day = {f"B{mb}_W{mw}": sum(len(v) for v in det[(mb, mw)].values()) / len(keys) for mb, mw in grid}
    if inst == "ES":
        ref = REF
    else:                                          # equivalente: sólo por conteo (manifiesto §8, B3)
        es = json.loads((OUT / "iter2_counts_ES.json").read_text(encoding="utf-8"))
        target = es[f"B{REF[0]}_W{REF[1]}"]
        ref = min(((20, mw) for mb, mw in grid if mb == 20), key=lambda g: abs(per_day[f"B{g[0]}_W{g[1]}"] - target))
    (OUT / f"iter2_counts_{inst}.json").write_text(json.dumps(dict(per_day, ref=f"B{ref[0]}_W{ref[1]}"), indent=1), encoding="utf-8")
    print("referencia", ref, {k: round(v, 1) for k, v in per_day.items()}, flush=True)
    pools = {mb: rev_pool(S, keys, mb) for mb in sorted({g[0] for g in grid})}
    rng = np.random.default_rng(SEED)
    rows = []
    for mb, mw in grid:
        cfg = f"B{mb}_W{mw}"
        isref = (mb, mw) == tuple(ref)
        total = sum(len(v) for v in det[(mb, mw)].values())
        frac = min(1.0, CAP / max(total, 1))
        for s in keys:
            x = S[s]
            for bi, b in enumerate(det[(mb, mw)][s]):
                d, A, B, i0, iext, iend = int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(b[4]), int(b[5])
                if iend + H > len(x["c"]) - 1:
                    continue
                if rng.random() >= frac:
                    continue
                W = abs(B - A)
                clock = int(x["clock"][iend])
                base = dict(inst=inst, cfg=cfg, ref=isref, session=s, band=bi, dir=d, W=W, clock=clock, t_end=float(x["t"][iend]),
                            phase=TB.phase_et(int(x["t"][iend] * NS)), imp_bars=max(iext - i0, 1), imp_vpt=float(b[7]) / W,
                            str_ema20_i0=float(d * x["str"]["ema20"][i0]), str_ema20_end=float(d * x["str"]["ema20"][iend]))

                def run(y, e, dd, AA, BB, WW, kind, **extra):
                    m = TX.path_metrics(y["t"], y["h"], y["l"], y["c"], y["v"], e, dd, AA, BB, WW, H, PEN)
                    row = dict(base, kind=kind, **extra, **dict(zip(TX.MET, m)))
                    if isref:
                        for pb in (20, 100):
                            row[f"reach_opp_p{pb}"] = TX.path_metrics(y["t"], y["h"], y["l"], y["c"], y["v"], e, dd, AA, BB, WW, H, pb)[9]
                    rows.append(row)

                run(x, iend, d, A, B, W, "real")
                c_e = int(x["c"][iend])
                rg0, sec0 = x[f"rg{mb}"][iend], x[f"sec{mb}"][iend]
                for _ in range(N_PH):
                    o, q = pick_vol(S, keys, s, mb, clock, rg0, sec0, rng)
                    if o is None:
                        break
                    sh = int(S[o]["c"][q]) - c_e
                    run(S[o], q, d, A + sh, B + sh, W, "fantasma_vol", ph_session=o, ph_t=float(S[o]["t"][q]))
                for p in pick_rev(pools[mb], W, clock, s, rng):
                    run(S[p.s], int(p.iend), int(p.d), int(p.A), int(p.B), int(abs(p.B - p.A)), "fantasma_rev",
                        ph_session=p.s, ph_t=float(S[p.s]["t"][int(p.iend)]))
                for p in pick_rev(pools[mb], W, clock, s, rng, rg0, sec0):
                    run(S[p.s], int(p.iend), int(p.d), int(p.A), int(p.B), int(abs(p.B - p.A)), "fantasma_revvol",
                        ph_session=p.s, ph_t=float(S[p.s]["t"][int(p.iend)]))
                if isref and np.isfinite(base["str_ema20_end"]):
                    for _ in range(N_PH):
                        o, q = pick_vol(S, keys, s, mb, clock, rg0, sec0, rng, str0=base["str_ema20_end"], d=d)
                        if o is None:
                            break
                        sh = int(S[o]["c"][q]) - c_e
                        run(S[o], q, d, A + sh, B + sh, W, "fantasma_volstr", ph_session=o, ph_t=float(S[o]["t"][q]))
        print(cfg, "franjas", sum(1 for r in rows if r["cfg"] == cfg and r["kind"] == "real"), flush=True)
    D = pd.DataFrame(rows)
    D.to_parquet(OUT / f"iter2_{inst}.parquet", index=False)
    print("filas", len(D), "partición", part)


# ------------------------------------------------------------------ reporte
PRIM = TX.PRIMARY + [("reachA_viaB", "salió por B y llegó a A")]


def prep(D):
    D = D.copy()
    D["out_vol_rel"] = np.nan
    D["reachA_viaB"] = np.where(D.side_B == 1, D.reach_opp, np.nan)
    for pb in (20, 100):
        if f"reach_opp_p{pb}" in D:
            D[f"reachA_viaB_p{pb}"] = np.where(D.side_B == 1, D[f"reach_opp_p{pb}"], np.nan)
    return D


def pair(D, col, null):
    R = D[D.kind == "real"].set_index(["cfg", "session", "band"])[col]
    P = D[D.kind == null].groupby(["cfg", "session", "band"])[col].mean()
    return pd.concat([R.rename("r"), P.rename("p")], axis=1).dropna()


def cell(J, rng, **kw):
    if len(J) < 30:
        return dict(kw, n=int(len(J)), status="POCOS")
    obs, lo, hi, se, p = TX._boot(J, rng)
    ses = J.index.get_level_values("session")
    by = (J.r - J.p).groupby(ses).mean()
    return dict(kw, n=int(len(J)), sessions=int(by.size), real=float(J.r.mean()), null_mean=float(J.p.mean()),
                diff=float(obs), ci=[float(lo), float(hi)], mde=float(2.8 * se), p=float(p),
                sessions_pos=float((by > 0).mean()), status="OK")


def report_inst(inst, rng):
    D = prep(pd.read_parquet(OUT / f"iter2_{inst}.parquet"))
    ref = D[D.ref].cfg.iloc[0]
    cells = []
    for cfg, g in D.groupby("cfg", sort=False):
        for null in ("fantasma_vol", "fantasma_rev", "fantasma_revvol"):
            for col, lab in PRIM:
                if col == "out_vol_rel":
                    continue
                cells.append(cell(pair(g, col, null), rng, cfg=cfg, null=null, metric=col, label=lab))
    for null in ("fantasma_vol", "fantasma_rev", "fantasma_revvol"):
        oo = [c for c in cells if c["status"] == "OK" and c["null"] == null]
        for c, f in zip(oo, TX._bh([c["p"] for c in oo])):
            c["fdr"] = bool(f)
    g = D[D.cfg == ref]
    robust = {}
    months = pd.to_datetime(g.session, format="%Y%m%d")
    g = g.assign(half=np.where(months < "2025-12-01", "jul-nov", "dic-mar"), month=months.dt.strftime("%Y-%m"))
    for col in ("reachA_viaB", "pen_W", "exc_W", "re_tpb"):
        for null in ("fantasma_vol", "fantasma_rev", "fantasma_revvol", "fantasma_volstr"):
            robust[f"{col}|{null}|todo"] = cell(pair(g, col, null), rng)
            for h, gh in g.groupby("half"):
                robust[f"{col}|{null}|{h}"] = cell(pair(gh, col, null), rng)
            if null != "fantasma_volstr":
                ms = {}
                for mth, gm in g.groupby("month"):
                    J = pair(gm, col, null)
                    ms[mth] = round(float((J.r - J.p).mean()), 4) if len(J) >= 30 else None
                robust[f"{col}|{null}|por_mes"] = ms
    for pb in (20, 100):
        robust[f"reachA_viaB_p{pb}|fantasma_vol|todo"] = cell(pair(g, f"reachA_viaB_p{pb}", "fantasma_vol"), rng)
    # estiramiento extremo con nulo emparejado por estiramiento
    q90 = g[g.kind == "real"].str_ema20_end.quantile(0.9)
    ext = g[g.groupby(["session", "band"]).str_ema20_end.transform("first") >= q90]
    for col in ("reachA_viaB", "pen_W", "exc_W", "reach_mirror"):
        for null in ("fantasma_vol", "fantasma_volstr"):
            robust[f"estirado_d10|{col}|{null}"] = cell(pair(ext, col, null), rng)
    return dict(ref=ref, cells=cells, robust=robust)


def step_report():
    rng = np.random.default_rng(SEED)
    body = dict(schema="EDGELAB_TBZX_ITER2_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")))
    for inst in ("ES", "NQ"):
        if (OUT / f"iter2_{inst}.parquet").exists():
            body[inst] = report_inst(inst, rng)
    if "NQ" in body and "ES" in body:
        verdict = {}
        for col in ("reachA_viaB", "pen_W"):
            es = body["ES"]["robust"][f"{col}|fantasma_vol|todo"]; nq = body["NQ"]["robust"][f"{col}|fantasma_vol|todo"]
            same = np.sign(es.get("diff", 0)) == np.sign(nq.get("diff", 0))
            excl = nq.get("status") == "OK" and (nq["ci"][0] > 0 or nq["ci"][1] < 0)
            verdict[col] = dict(es=es.get("diff"), nq=nq.get("diff"), nq_ci=nq.get("ci"), replica=bool(same and excl))
        body["replica_NQ"] = verdict
    audit_rows = []
    for inst in ("ES", "NQ"):
        f = OUT / f"iter2_{inst}.parquet"
        if f.exists():
            X = pd.read_parquet(f, columns=["kind", "session", "ph_session", "t_end", "ph_t"])
            audit_rows.append(X[X.kind != "real"])
    A = pd.concat(audit_rows)
    from edgelab.edge_brain.control_guard import audit_event_controls
    audit = audit_event_controls((A.t_end * 1e6).astype(np.int64).to_numpy(), (A.ph_t * 1e6).astype(np.int64).to_numpy(), H * 60.0,
                                 same_session=(A.session == A.ph_session).to_numpy())
    body["control_audit"] = audit
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "report_iter2.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    with measurement_episode(LEDGER, "EP-TBZX-ITER2-ES-REVVOL-20260926", goal="TBZX iteración 2: N-REV, N-VOLSTR, estabilidad, réplica NQ",
                             recorded_by="tools/tbzx_iter2.py report", repo=REPO, prereg_ref=DOC) as ep:
        parts = [f"P-TBZX-{i}-EXP" for i in ("ES", "NQ") if i in body]
        ep.store.record_observation("OBS-TBZX-ITER2-ES-REVVOL", "franja TBZX: afuera y reingreso, nulos estrictos y réplica", "RESPONSE_PROFILE",
                                    parts, {f"{i}|{k}": (v.get("diff"), v.get("ci")) for i in ("ES", "NQ") if i in body
                                            for k, v in body[i]["robust"].items() if isinstance(v, dict) and "status" in v},
                                    {"horizon_bars": H}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], audit=audit["status"], replica=body.get("replica_NQ")), ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["bars", "measure", "report"])
    ap.add_argument("--inst", default="ES")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args(argv)
    if a.step == "bars":
        step_bars(a.inst, a.workers)
    elif a.step == "measure":
        step_measure(a.inst)
    else:
        step_report()


if __name__ == "__main__":
    main()
