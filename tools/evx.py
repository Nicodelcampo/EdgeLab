#!/usr/bin/env python3
r"""EVX: cruces EMA × VWAP de sesión. Etapas E0 (censo) y E1 (información, sin P&L).

Manifiesto: docs/research/MANIFIESTO_EVX_E0_E1_20260926.md (escrito antes de medir).

    .venv\Scripts\python tools\evx.py e1 --inst MYM
    .venv\Scripts\python tools\evx.py report

Velas de 25 ticks de la caché de TBZX (`tools/tbzx_iter2.py bars --inst X`, contrato canónico).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "evx"
DOC = "docs/research/MANIFIESTO_EVX_E0_E1_20260926.md"
LEDGER = REPO / "artifacts" / "hippocampus" / "evx_20260926.jsonl"
PERIODS = (21, 55, 144, 377)
HZ = (5, 20, 60, 200)
WARMUP = 50
GAP_S = 1800
ATR_N = 100
N_PH = 3
TOD = 3600
TOL = 0.25
ABS_TOL = 0.1
SEED = 20260926
N_BOOT = 2000
ASSETS = ("MYM", "YM", "ES", "NQ")


def session_arrays(x):
    """Indicadores causales por vela: VWAP de sesión, ATR y actividad de las últimas 20 velas."""
    t, h, l, c, v = x["t"], x["h"].astype(float), x["l"].astype(float), x["c"].astype(float), x["v"].astype(float)
    n = len(c)
    tp = (h + l + c) / 3
    vw = np.cumsum(tp * np.maximum(v, 1)) / np.cumsum(np.maximum(v, 1))
    prev = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    atr = pd.Series(tr).ewm(alpha=1 / ATR_N, adjust=False).mean().to_numpy()
    atr = np.maximum(atr, 1.0)
    rg20, sec20 = T2.TX.trailing(x, 20)
    return dict(vw=vw, atr=atr, rg20=rg20, sec20=sec20, n=n, c=c, o=np.r_[c[0], c[:-1]])


def ema(c, p):
    return pd.Series(c).ewm(span=p, adjust=False).mean().to_numpy()


def events_for(x, A, p):
    """Cruces de la EMA(p) con el VWAP, con filtros del tramo previo y estado en el cruce."""
    c, vw, atr = A["c"], A["vw"], A["atr"]
    e = ema(c, p)
    d = e - vw
    n = len(c)
    rows = []
    last, maxd, vol = -1, 0.0, 0.0
    for i in range(WARMUP, n):
        vol += float(x["v"][i])
        maxd = max(maxd, abs(d[i]) / atr[i])
        if (d[i - 1] <= 0 < d[i]) or (d[i - 1] >= 0 > d[i]):
            side = i - (last if last >= 0 else WARMUP)
            rows.append(dict(i=i, dir=1 if d[i] > 0 else -1, side_bars=side, max_dist=maxd, vol=vol,
                             slope=(e[i] - e[i - 5]) / atr[i], pe=(c[i] - e[i]) / atr[i], ev=d[i] / atr[i]))
            last, maxd, vol = i, 0.0, 0.0
    return rows, e


def fwd(A, i, dr, h):
    """dir · (cierre[i+h] − apertura[i+1]) / ATR[i]. Apertura[i+1] ≈ cierre[i] (las velas de tick son contiguas)."""
    n = A["n"]
    if i + h >= n:
        return np.nan
    return dr * (A["c"][i + h] - A["c"][i]) / A["atr"][i]


def state(A, e, i):
    atr = A["atr"][i]
    return np.array([(e[i] - e[i - 5]) / atr, (A["c"][i] - e[i]) / atr, (e[i] - A["vw"][i]) / atr])


def step_e1(inst):
    S = T2.load(inst)
    keys = [k for k in sorted(S) if k <= TB.EXP_END]
    if not keys:
        raise SystemExit(f"sin velas para {inst}: correr tools/tbzx_iter2.py bars --inst {inst}")
    declare(inst, keys)
    A = {k: session_arrays(S[k]) for k in keys}
    rng = np.random.default_rng(SEED)
    rows = []
    for p in PERIODS:
        E = {k: ema(A[k]["c"], p) for k in keys}
        # estado por vela, para buscar controles: pendiente, precio−EMA, EMA−VWAP (en ATR)
        ST = {}
        for k in keys:
            a, e = A[k], E[k]
            sl = np.r_[np.full(5, np.nan), (e[5:] - e[:-5])] / a["atr"]
            ST[k] = np.vstack([sl, (a["c"] - e) / a["atr"], (e - a["vw"]) / a["atr"]])
        for k in keys:
            evs, _ = events_for(S[k], A[k], p)
            for ev in evs:
                i, dr = ev["i"], ev["dir"]
                base = dict(inst=inst, p=p, session=k, i=i, dir=dr, clock=int(S[k]["clock"][i]),
                            side_bars=ev["side_bars"], max_dist=ev["max_dist"], vol=ev["vol"])
                rows.append(dict(base, kind="real", **{f"r{h}": fwd(A[k], i, dr, h) for h in HZ}))
                s0 = ST[k][:, i]; rg0, sec0 = A[k]["rg20"][i], A[k]["sec20"][i]
                others = [o for o in keys if o != k]
                got = 0
                for _ in range(40):
                    if got >= N_PH:
                        break
                    o = others[int(rng.integers(len(others)))]
                    y = S[o]
                    a_, b_ = np.searchsorted(y["clock"], base["clock"] - TOD), np.searchsorted(y["clock"], base["clock"] + TOD)
                    a_ = max(a_, WARMUP)
                    if b_ <= a_:
                        continue
                    st = ST[o][:, a_:b_]
                    tol = np.maximum(TOL * np.abs(s0)[:, None], ABS_TOL)
                    ok = np.all(np.abs(st - s0[:, None]) <= tol, axis=0)
                    rg, sec = A[o]["rg20"][a_:b_], A[o]["sec20"][a_:b_]
                    ok &= (np.abs(rg - rg0) <= TOL * rg0) & (np.abs(np.log(np.maximum(sec, 1e-3) / max(sec0, 1e-3))) <= np.log(1 + TOL))
                    idx = np.flatnonzero(ok)
                    if not len(idx):
                        continue
                    q = a_ + int(idx[int(rng.integers(len(idx)))])
                    rows.append(dict(base, kind="control", ph_session=o, ph_t=float(y["t"][q]), t_ev=float(S[k]["t"][i]),
                                     **{f"r{h}": fwd(A[o], q, dr, h) for h in HZ}))
                    got += 1
        print(inst, "EMA", p, "eventos", sum(1 for r in rows if r["p"] == p and r["kind"] == "real"), flush=True)
    D = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_parquet(OUT / f"e1_{inst}.parquet", index=False)
    print("filas", len(D), "sesiones", len(keys))


def declare(inst, keys):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    part = f"P-EVX-{inst}-EXP"
    if LEDGER.exists() and part in DurableHippocampus(LEDGER).partitions:
        return
    with measurement_episode(LEDGER, f"EP-EVX-PARTICION-{inst}", goal=f"declarar partición EVX {inst} antes de medir",
                             recorded_by="tools/evx.py e1", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_partition(part, "EXPLORATION", f"{inst} 25T exploración (<= 2026-03-31), contrato canónico",
                                  [f"{inst}:{k}" for k in keys])


def boot(r, c, ses, rng):
    diff = r - c
    u, inv = np.unique(ses, return_inverse=True)
    sums = np.bincount(inv, weights=diff); cnt = np.bincount(inv)
    bs = np.empty(N_BOOT)
    for b in range(N_BOOT):
        w = np.bincount(rng.integers(len(u), size=len(u)), minlength=len(u))
        bs[b] = (w * sums).sum() / max((w * cnt).sum(), 1)
    p = 2 * min((bs <= 0).mean(), (bs >= 0).mean())
    return float(diff.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(2.8 * bs.std()), max(p, 1 / N_BOOT)


def step_report():
    rng = np.random.default_rng(SEED)
    cells, census = [], {}
    for inst in ASSETS:
        f = OUT / f"e1_{inst}.parquet"
        if not f.exists():
            continue
        D = pd.read_parquet(f)
        R = D[D.kind == "real"]
        ndays = R.session.nunique()
        for p, g in R.groupby("p"):
            census[f"{inst}|EMA{p}"] = dict(eventos=int(len(g)), por_dia=round(len(g) / max(ndays, 1), 2),
                                           terciles={c: [float(x) for x in g[c].quantile([1 / 3, 2 / 3])] for c in ("side_bars", "max_dist", "vol")})
        C = D[D.kind == "control"].groupby(["p", "session", "i"])[[f"r{h}" for h in HZ]].mean()
        J = R.set_index(["p", "session", "i"])
        for p in PERIODS:
            key = f"{inst}|EMA{p}"
            if key not in census:
                continue
            e0_ok = census[key]["por_dia"] >= 1 and census[key]["eventos"] >= 300
            g = J.loc[p]
            filt = {"ninguno": np.ones(len(g), bool)}
            for col in ("side_bars", "max_dist", "vol"):
                t1, t2 = census[key]["terciles"][col]
                filt[f"{col}>=T1"] = (g[col] >= t1).to_numpy(); filt[f"{col}>=T2"] = (g[col] >= t2).to_numpy()
            months = pd.to_datetime(g.index.get_level_values("session"), format="%Y%m%d")
            half = np.where(months < pd.Timestamp("2025-12-01"), "h1", "h2")
            for fn, m in filt.items():
                for h in HZ:
                    col = f"r{h}"
                    rr = g[col].to_numpy()[m]
                    cc = C.loc[p][col].reindex(g.index[m]).to_numpy() if p in C.index.get_level_values(0) else np.full(m.sum(), np.nan)
                    ses = g.index.get_level_values("session").to_numpy()[m]
                    hh = half[m]
                    ok = np.isfinite(rr) & np.isfinite(cc)
                    if ok.sum() < 30:
                        cells.append(dict(inst=inst, p=p, filtro=fn, h=h, n=int(ok.sum()), status="POCOS", e0_ok=e0_ok)); continue
                    d, lo, hi, mde, pv = boot(rr[ok], cc[ok], ses[ok], rng)
                    nd = float(np.mean(np.abs(rr[ok])) - np.mean(np.abs(cc[ok])))
                    halves = {k: float(np.mean(rr[ok][hh[ok] == k] - cc[ok][hh[ok] == k])) if (hh[ok] == k).sum() >= 15 else None for k in ("h1", "h2")}
                    cells.append(dict(inst=inst, p=p, filtro=fn, h=h, n=int(ok.sum()), sessions=int(len(set(ses[ok]))), real=float(rr[ok].mean()),
                                      control=float(cc[ok].mean()), diff=d, ci=[lo, hi], mde=mde, pval=pv, no_dir=nd, halves=halves,
                                      status="OK", e0_ok=e0_ok))
    ok = [c for c in cells if c["status"] == "OK" and c["e0_ok"]]
    for c, f in zip(ok, T2.TX._bh([c["pval"] for c in ok])):
        c["fdr"] = bool(f)
    for c in ok:
        hv = [v for v in c["halves"].values() if v is not None]
        c["pasa_E2"] = bool(c["fdr"] and c["diff"] > 0 and len(hv) == 2 and all(v > 0 for v in hv))
    # auditoría de controles
    from edgelab.edge_brain.control_guard import audit_event_controls
    aud_rows = []
    for inst in ASSETS:
        f = OUT / f"e1_{inst}.parquet"
        if f.exists():
            X = pd.read_parquet(f); X = X[X.kind == "control"]; aud_rows.append(X)
    X = pd.concat(aud_rows)
    audit = audit_event_controls((X.t_ev * 1e6).astype(np.int64).to_numpy(), (X.ph_t * 1e6).astype(np.int64).to_numpy(), 200 * 60.0,
                                 same_session=(X.session == X.ph_session).to_numpy())
    body = dict(schema="EDGELAB_EVX_E1_V1", doc=DOC, code_commit=TB._git("rev-parse", "HEAD"),
                tree_dirty=bool(TB._git("status", "--porcelain", "--", "tools", "edgelab")), censo_E0=census, celdas=cells,
                familia_E1=len(ok), fdr=int(sum(c["fdr"] for c in ok)), pasan_E2=[c for c in ok if c["pasa_E2"]], control_audit=audit)
    raw = json.dumps(body, indent=1, default=float, ensure_ascii=False)
    (OUT / "report_e1.json").write_text(raw, encoding="utf-8")
    sha = hashlib.sha256(raw.encode()).hexdigest()
    from edgelab.edge_brain.episode_logger import measurement_episode
    parts = [f"P-EVX-{i}-EXP" for i in ASSETS if (OUT / f"e1_{i}.parquet").exists()]
    with measurement_episode(LEDGER, f"EP-EVX-E1-{sha[:8]}", goal="EVX E1: información del cruce EMA×VWAP contra control de mismo estado",
                             recorded_by="tools/evx.py report", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_observation(f"OBS-EVX-E1-{sha[:8]}", "EVX E1: cruce EMA × VWAP, retorno direccional vs control", "RESPONSE_PROFILE",
                                    parts, {f"{c['inst']}|{c['p']}|{c['filtro']}|{c['h']}": (c["diff"], c["fdr"]) for c in ok},
                                    {"horizons": list(HZ)}, sha, design="EVENT_VS_CONTROL", control_audit=audit)
    print(json.dumps(dict(sha=sha[:12], familia=len(ok), fdr=body["fdr"], pasan_E2=len(body["pasan_E2"]), audit=audit["status"])))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["e1", "report"])
    ap.add_argument("--inst", default="MYM")
    a = ap.parse_args(argv)
    step_e1(a.inst) if a.step == "e1" else step_report()


if __name__ == "__main__":
    main()
