#!/usr/bin/env python3
r"""L2 Fase 2 — informacion condicional del libro tras la latencia (GC 08-26, pre-holdout).

Implementa EXACTAMENTE `docs/research/PREREG_L2_FASE2_INFO_CONDICIONAL_GC_20260923.md` (commit aa080a1, congelado
antes de mirar retornos). Cualquier desvio es un bug, no una decision: el pre-registro manda.

Resumen: muestreo de estado continuo por segundo; features M0 (solo trades) y M1 (M0 + L2) calculados con el libro y
los trades hasta t-L; etiqueta mid(t+h)-mid(t) (direccional) y |.| (no direccional), h en {30,60,300}s; ridge
alpha=1 sobre features estandarizados en train; IC de Spearman por sesion; DeltaIC = IC(M1)-IC(M0); bootstrap por
sesion; Bonferroni 6 pruebas. Desarrollo = primeras 20 sesiones (walk-forward 4 pliegues, embargo 1 sesion, MDE);
test = ultimas 10, una sola apertura.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from statistics import NormalDist  # noqa: E402

from edgelab.research.holdout_guard import L2_HOLDOUT_START_ISO as HOLDOUT_START_ISO  # enmienda L2 2026-09-24  # noqa: E402
from edgelab.research.l2_phase0 import (ASK, BID, BOOTSTRAP_S, EDGE_RESYNC, INVALID, LEVELS,  # noqa: E402
                                        apply_event, defect_reasons)

HOLDOUT_YMD = int(HOLDOUT_START_ISO[:10].replace("-", ""))
HORIZONS = (30, 60, 300)
N_DEV, N_TEST = 20, 10
ALPHA_RIDGE = 1.0
HALT_ART = (18 * 3600, 19 * 3600)          # pausa CME en reloj de pared ART
M0 = ["delta5", "delta30", "delta60", "ntr30", "rv60"] + [f"hb{i}" for i in range(1, 6)]
L2F = ["ofi5", "ofi30", "mofi30", "qi1", "qi5", "micro", "spread", "dep1", "dep10"]
M1 = M0 + L2F
US = 1_000_000


def session_arrays(base: Path, s: str):
    """Recorre la sesion (libro + trades, orden source_row) y devuelve series por cierre de pseudo-evento y por trade."""
    l2 = pq.read_table(base / "l2_depth" / f"{s}.parquet",
                       columns=["side", "operation", "level", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    l1 = pq.read_table(base / "l1_quotes" / f"{s}.parquet",
                       columns=["side", "price_tick", "size", "ts_us", "source_row"]).to_pandas()
    l2 = l2.sort_values("source_row", kind="stable"); t1 = l1[l1.side == 2].sort_values("source_row", kind="stable")
    sd, op, lv, tk, sz, ts, r2 = (l2[c].to_numpy() for c in ("side", "operation", "level", "price_tick", "size", "ts_us", "source_row"))
    tr_row, tr_tick, tr_size, tr_ts = (t1[c].to_numpy() for c in ("source_row", "price_tick", "size", "ts_us"))
    asks, bids = [], []
    g = {k: [] for k in ("t", "bid", "ask", "qb", "qa", "sb5", "sa5", "d10", "e1", "e5")}
    trs = {"t": [], "signed": []}
    prev5 = None
    invalid = resync = inversions = crossed = groups = 0
    full_since = None
    ti, nt, N, prev_t = 0, len(tr_row), len(ts), None
    for i in range(N):
        t = int(ts[i])
        if prev_t is not None and t < prev_t:
            inversions += 1
        prev_t = t
        while ti < nt and tr_row[ti] < r2[i]:
            if bids and asks:
                p = int(tr_tick[ti]); a0, b0 = asks[0][0], bids[0][0]
                sgn = 1 if p >= a0 else (-1 if p <= b0 else 0)
                trs["t"].append(int(tr_ts[ti])); trs["signed"].append(sgn * int(tr_size[ti]))
            ti += 1
        rc = apply_event(asks if sd[i] == ASK else bids, int(op[i]), int(lv[i]), int(tk[i]), int(sz[i]), int(sd[i]))
        if rc == INVALID:
            invalid += 1
        elif rc == EDGE_RESYNC:
            resync += 1
        if i != N - 1 and int(ts[i + 1]) == t:
            continue                                   # dentro de un pseudo-evento: no se lee el libro
        groups += 1
        if full_since is None and len(asks) >= LEVELS and len(bids) >= LEVELS:
            full_since = t
        if not (asks and bids) or bids[0][0] >= asks[0][0]:
            crossed += 1 if (asks and bids) else 0
            continue
        cur5 = ([x[0] for x in bids[:5]], [x[1] for x in bids[:5]], [x[0] for x in asks[:5]], [x[1] for x in asks[:5]])
        e1 = e5 = 0.0
        if prev5 is not None:
            for k in range(min(5, len(cur5[0]), len(prev5[0]), len(cur5[2]), len(prev5[2]))):
                pb, qb, pa, qa = cur5[0][k], cur5[1][k], cur5[2][k], cur5[3][k]
                pbp, qbp, pap, qap = prev5[0][k], prev5[1][k], prev5[2][k], prev5[3][k]
                e = (qb if pb >= pbp else 0) - (qbp if pb <= pbp else 0) - (qa if pa <= pap else 0) + (qap if pa >= pap else 0)
                e5 += e
                if k == 0:
                    e1 = e
        prev5 = cur5
        g["t"].append(t); g["bid"].append(bids[0][0]); g["ask"].append(asks[0][0])
        g["qb"].append(bids[0][1]); g["qa"].append(asks[0][1])
        g["sb5"].append(sum(cur5[1])); g["sa5"].append(sum(cur5[3]))
        g["d10"].append(sum(x[1] for x in bids[:LEVELS]) + sum(x[1] for x in asks[:LEVELS]))
        g["e1"].append(e1); g["e5"].append(e5)
    qa = dict(l2_events=N, groups=groups, invalid_events=invalid, edge_resync_events=resync,
              clock_inversions=inversions, crossed_group_ratio=crossed / max(1, groups),
              bootstrap_complete=full_since is not None, snapshots=0)
    G = {k: np.asarray(v, dtype=np.int64 if k in ("t", "bid", "ask") else float) for k, v in g.items()}
    T = {k: np.asarray(v, dtype=np.int64) for k, v in trs.items()}
    return G, T, qa, full_since


def features(G, T, full_since, L_ms: int):
    """Grilla de 1 s; features con estado hasta t-L; etiquetas desde t."""
    t0 = (full_since // US + BOOTSTRAP_S + 60 + 1) * US
    t1 = int(G["t"][-1])
    grid = np.arange(t0, t1 - max(HORIZONS) * US, US, dtype=np.int64)
    tau = grid - L_ms * 1000
    gi = np.searchsorted(G["t"], tau, side="right") - 1
    gi_now = np.searchsorted(G["t"], grid, side="right") - 1
    ok = (gi >= 0) & (gi_now >= 0)
    mid2 = G["bid"] + G["ask"]
    cum1, cum5 = np.cumsum(G["e1"]), np.cumsum(G["e5"])
    dmid = np.diff(mid2 / 2.0, prepend=mid2[0] / 2.0)
    cumsq = np.cumsum(dmid ** 2)
    ct, cs = T["t"], np.cumsum(T["signed"])

    def win(cum, times, end, secs):
        a = np.searchsorted(times, end - secs * US, side="right") - 1
        b = np.searchsorted(times, end, side="right") - 1
        va = np.where(a >= 0, cum[np.clip(a, 0, None)], 0.0)
        vb = np.where(b >= 0, cum[np.clip(b, 0, None)], 0.0)
        return vb - va

    X = {}
    X["delta5"], X["delta30"], X["delta60"] = (win(cs, ct, tau, w) for w in (5, 30, 60))
    X["ntr30"] = win(np.arange(1, len(ct) + 1), ct, tau, 30)
    X["rv60"] = np.sqrt(np.maximum(win(cumsq, G["t"], tau, 60), 0))
    sod = (tau // US) % 86400
    hb = np.minimum(sod // (4 * 3600), 5)
    for i in range(1, 6):
        X[f"hb{i}"] = (hb == i).astype(float)
    X["ofi5"], X["ofi30"] = win(cum1, G["t"], tau, 5), win(cum1, G["t"], tau, 30)
    X["mofi30"] = win(cum5, G["t"], tau, 30)
    j = np.clip(gi, 0, None)
    qb, qa_ = G["qb"][j], G["qa"][j]
    X["qi1"] = (qb - qa_) / np.maximum(qb + qa_, 1)
    X["qi5"] = (G["sb5"][j] - G["sa5"][j]) / np.maximum(G["sb5"][j] + G["sa5"][j], 1)
    b, a = G["bid"][j].astype(float), G["ask"][j].astype(float)
    X["micro"] = (a * qb + b * qa_) / np.maximum(qb + qa_, 1) - (a + b) / 2
    X["spread"] = a - b
    X["dep1"], X["dep10"] = qb + qa_, G["d10"][j]
    Y = {}
    m_now = mid2[np.clip(gi_now, 0, None)] / 2.0
    sod_now = (grid // US) % 86400
    for h in HORIZONS:
        k = np.searchsorted(G["t"], grid + h * US, side="right") - 1
        Y[h] = mid2[np.clip(k, 0, None)] / 2.0 - m_now
        # excluir si la ventana [tau-60, t+h] toca la pausa CME
        s0, s1 = (tau // US - 60) % 86400, (grid // US + h) % 86400
        touch = ((s0 < HALT_ART[1]) & (s1 >= HALT_ART[0])) & (s0 <= s1)
        ok_h = ok & ~touch
        Y[f"ok{h}"] = ok_h
    df = pd.DataFrame(X)
    for h in HORIZONS:
        df[f"y{h}"] = Y[h]; df[f"ok{h}"] = Y[f"ok{h}"]
    df["sod"] = sod_now
    return df


def ridge_fit(X, y, alpha=ALPHA_RIDGE):
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = (X - mu) / sd
    A = Z.T @ Z + alpha * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (y - y.mean()))
    return dict(mu=mu, sd=sd, w=w, b=y.mean())


def ridge_pred(m, X):
    return ((X - m["mu"]) / m["sd"]) @ m["w"] + m["b"]


def session_ic(pred, y):
    if len(y) < 100 or np.std(pred) == 0 or np.std(y) == 0:
        return np.nan
    # Spearman = Pearson sobre rangos (promedio en empates), sin scipy
    rp, ry = pd.Series(pred).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rp, ry)[0, 1])


def fit_eval(train, test, cols, h, channel):
    tr = pd.concat([d[d[f"ok{h}"]] for d in train])
    ytr = tr[f"y{h}"].to_numpy() if channel == "dir" else np.abs(tr[f"y{h}"].to_numpy())
    m = ridge_fit(tr[cols].to_numpy(float), ytr)
    out = []
    for d in test:
        d = d[d[f"ok{h}"]]
        y = d[f"y{h}"].to_numpy() if channel == "dir" else np.abs(d[f"y{h}"].to_numpy())
        out.append((session_ic(ridge_pred(m, d[cols].to_numpy(float)), y), m, d))
    return out


def boot_ci(x, level, n=10000, seed=20260923):
    x = np.asarray([v for v in x if np.isfinite(v)])
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    a = (1 - level) / 2
    return float(x.mean()), float(np.quantile(bs, a)), float(np.quantile(bs, 1 - a))


def _git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=Path(r"E:\DatosNT8\gc_aug26_canonical_parquets"))
    ap.add_argument("--out", type=Path, default=REPO / "artifacts" / "l2_phase2")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    prov = dict(prereg="docs/research/PREREG_L2_FASE2_INFO_CONDICIONAL_GC_20260923.md@aa080a1",
                code_commit=_git("rev-parse", "HEAD"), tree_dirty=bool(_git("status", "--porcelain")))
    sessions = sorted(p.stem for p in (a.base / "l2_depth").glob("*.parquet") if int(p.stem) < HOLDOUT_YMD)
    data = {L: {} for L in (250, 0, 500)}
    qa_log = []
    for s in sessions:
        G, T, qa, full = session_arrays(a.base, s)
        if full is not None:
            qa["snapshots"] = int((G["t"][-1] - full) // US)
        reasons = defect_reasons(qa)
        qa_log.append(dict(session=s, **qa, defect_reasons=reasons))
        print(json.dumps(dict(session=s, usable=not reasons, reasons=reasons)), flush=True)
        if reasons:
            continue
        for L in data:
            data[L][s] = features(G, T, full, L)
    usable = sorted(data[250])
    if len(usable) < N_DEV + N_TEST:
        raise SystemExit(f"solo {len(usable)} sesiones usables; el pre-registro exige {N_DEV + N_TEST}")
    usable = usable[:N_DEV + N_TEST]
    dev, test = usable[:N_DEV], usable[N_DEV:]
    res = dict(provenance=prov, dev_sessions=dev, test_sessions=test, qa=qa_log, primary={}, mde={}, ablations={},
               folds={})
    level = 1 - 0.05 / 6
    zc = NormalDist().inv_cdf(1 - 0.05 / 12) + NormalDist().inv_cdf(0.8)
    D = data[250]
    for h in HORIZONS:
        for ch in ("dir", "abs"):
            key = f"h{h}_{ch}"
            # --- desarrollo: walk-forward 4 pliegues (chunks de 4), embargo 1 sesion -> MDE
            chunks = [dev[i * 4:(i + 1) * 4] for i in range(5)]
            dfold = []
            for k in range(1, 5):
                trn = [D[x] for c in chunks[:k] for x in c]
                tst = [D[x] for x in chunks[k][1:]]                     # embargo: se salta la primera sesion
                i0 = [r[0] for r in fit_eval(trn, tst, M0, h, ch)]
                i1 = [r[0] for r in fit_eval(trn, tst, M1, h, ch)]
                dfold += [b - c for b, c in zip(i1, i0)]
            sd = float(np.nanstd(dfold, ddof=1))
            res["folds"][key] = dict(delta_ic=dfold, mean=float(np.nanmean(dfold)))
            res["mde"][key] = float(zc * sd / np.sqrt(N_TEST))
            # --- test: una sola apertura
            trn = [D[x] for x in dev]; tst = [D[x] for x in test]
            r0 = fit_eval(trn, tst, M0, h, ch); r1 = fit_eval(trn, tst, M1, h, ch)
            ic0 = [r[0] for r in r0]; ic1 = [r[0] for r in r1]
            dic = [b - c for b, c in zip(ic1, ic0)]
            mean, lo, hi = boot_ci(dic, level)
            prim = dict(ic_m0=ic0, ic_m1=ic1, delta_ic=dic, mean=mean, ci_lo=lo, ci_hi=hi, ci_level=level,
                        rejects_h0=bool(lo > 0), weights_m1=dict(zip(M1, r1[0][1]["w"].round(5).tolist())))
            # traduccion economica (solo si rechaza a 300s direccional)
            if h == 300 and ch == "dir" and lo > 0:
                hits = tot = 0
                for (ic, m, d) in r1:
                    p = ridge_pred(m, d[M1].to_numpy(float)); y = d[f"y{h}"].to_numpy()
                    thr = np.quantile(np.abs(p), 0.9); sel = np.abs(p) >= thr
                    nz = sel & (y != 0)
                    hits += int((np.sign(p[nz]) == np.sign(y[nz])).sum()); tot += int(nz.sum())
                prim["top_decile_sign_accuracy"] = hits / max(1, tot)
                prim["top_decile_n"] = tot
            res["primary"][key] = prim
            # --- ablaciones (diagnosticas)
            abl = {}
            for L in (0, 500):
                trn = [data[L][x] for x in dev]; tst = [data[L][x] for x in test]
                i0 = [r[0] for r in fit_eval(trn, tst, M0, h, ch)]; i1 = [r[0] for r in fit_eval(trn, tst, M1, h, ch)]
                abl[f"L{L}"] = float(np.nanmean(np.subtract(i1, i0)))
            nohb = [c for c in M1 if not c.startswith("hb")]; nohb0 = [c for c in M0 if not c.startswith("hb")]
            i0 = [r[0] for r in fit_eval([D[x] for x in dev], [D[x] for x in test], nohb0, h, ch)]
            i1 = [r[0] for r in fit_eval([D[x] for x in dev], [D[x] for x in test], nohb, h, ch)]
            abl["no_hour_blocks"] = float(np.nanmean(np.subtract(i1, i0)))
            # placebo: columnas L2 de OTRA sesion de test, alineadas por segundo del dia
            plac = []
            for i, s in enumerate(test):
                d = D[s].copy(); o = D[test[(i + 1) % len(test)]].set_index("sod")[L2F]
                o = o[~o.index.duplicated()]
                d = d.join(o, on="sod", rsuffix="_o").dropna(subset=[f"{c}_o" for c in L2F])
                for c in L2F:
                    d[c] = d[f"{c}_o"]
                plac.append(d[M1 + [f"y{h}", f"ok{h}"]])
            i1p = [r[0] for r in fit_eval([D[x] for x in dev], plac, M1, h, ch)]
            i0p = [r[0] for r in fit_eval([D[x] for x in dev], plac, M0, h, ch)]
            abl["placebo_other_session_book"] = float(np.nanmean(np.subtract(i1p, i0p)))
            res["ablations"][key] = abl
            print(json.dumps(dict(key=key, mean=round(mean, 4), ci=[round(lo, 4), round(hi, 4)], mde=round(res["mde"][key], 4),
                                  rejects=bool(lo > 0), abl={k: round(v, 4) for k, v in abl.items()})), flush=True)
    (a.out / "results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
