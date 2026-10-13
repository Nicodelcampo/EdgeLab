#!/usr/bin/env python3
r"""OU-2 — ¿la reversión de ZB a 5-15 min sobrevive con el precio medio bid/ask? (descarta el rebote bid-ask). SOLO información.
Pre-registro: docs/autopilot/OU2_PREREGISTRO_20261013.md = drafts/OU-2.md (escrito y committeado antes de correr).

Serie de minuto: último trade del minuto («last») y punto medio bid/ask del ÚLTIMO tick del minuto con libro válido («mid»), de ticks ZB aprobados.
Estadístico (idéntico a OU-1 Parte A): X_t = ln P_t − SMA_N(ln P_t) dentro de sesión; b = pendiente de (X_{t+1}−X_t) sobre X_t agrupada.
Nulo: signo aleatorio independiente por retorno de barra, z = (b − media_nulo)/sd_nulo, bilateral. Pruebas (4, Holm 4): mid en celdas (5,60), (5,240), (15,240), (60,240) [min por barra, ventana SMA min].
Descriptivo (no cuenta): las mismas celdas con «last» sobre los MISMOS minutos, y por mitades de sesiones.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog"))
    OUT = Path(os.environ.get("OU2_OUT", "/tmp/ou2_out"))
OUT.mkdir(parents=True, exist_ok=True); os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
CFG = json.loads(os.environ.get("OU2_CFG", "{}")); SYNTH = os.environ.get("OU2_SYNTH") == "1"
INST = CFG.get("inst", "ZB"); DESDE = CFG.get("desde", "2025-07-01"); HASTA = CFG.get("hasta", "2026-09-30")
CELLS = [tuple(c) for c in CFG.get("cells", [[5, 60], [5, 240], [15, 240], [60, 240]])]
NPERM = int(CFG.get("nperm", 5000)); SEED = int(CFG.get("seed", 20261019)); MIN = 60_000_000_000


def minute_series(ts, px, bid, ask, sd):
    """ticks (orden temporal) → una fila por (sesión, minuto): último trade y mid del último tick con libro válido (0 < bid ≤ ask) de ese minuto."""
    m = ts // MIN; key = np.r_[True, m[1:] != m[:-1]]; st = np.flatnonzero(key); en = np.r_[st[1:], len(ts)] - 1
    valid = (bid > 0) & (ask >= bid); idx = np.where(valid, np.arange(len(ts)), -1)
    lastv = np.maximum.reduceat(idx, st)                                           # último tick válido dentro de cada minuto (-1 si ninguno)
    mid = np.where(lastv >= 0, (bid[np.maximum(lastv, 0)] + ask[np.maximum(lastv, 0)]) / 2.0, np.nan)
    return pd.DataFrame(dict(ts=m[st] * MIN, last=px[en].astype(float), mid=mid, sd=sd[en]))


def make_bars(df, s, col):
    b = df.ts.to_numpy() // (s * MIN); key = df.sd.to_numpy().astype(np.int64) * 10_000_000_000 + b.astype(np.int64)
    last = np.r_[key[1:] != key[:-1], True]
    return df.sd.to_numpy()[last], np.log(df[col].to_numpy()[last])


def b_stat(r, first, N):
    c = np.cumsum(r); n = len(c)
    pos = np.arange(n) - np.maximum.accumulate(np.where(first, np.arange(n), 0))
    cs = np.r_[0.0, np.cumsum(c)]; sma = np.full(n, np.nan); idx = np.arange(N - 1, n); sma[idx] = (cs[idx + 1] - cs[idx + 1 - N]) / N
    X = np.where(pos >= N - 1, c - sma, np.nan); x, y = X[:-1], X[1:] - X[:-1]
    ok = np.isfinite(x) & np.isfinite(y) & ~first[1:]; x, y = x[ok], y[ok]; x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum()), int(ok.sum())


def cell(df, col, s, W, rng, nperm=NPERM):
    d = df[np.isfinite(df[col].to_numpy())]; sd, lp = make_bars(d, s, col); N = W // s; first = np.r_[True, sd[1:] != sd[:-1]]
    r = np.where(first, 0.0, np.r_[0.0, np.diff(lp)])
    if len(r) < 20 * N or (~first).sum() < 1000: return dict(col=col, bar_min=s, win_min=W, n=int(len(r)), evaluable=False)
    b, nn = b_stat(r, first, N); nul = np.array([b_stat(r * rng.choice([-1.0, 1.0], len(r)), first, N)[0] for _ in range(nperm)])
    z = (b - nul.mean()) / nul.std(); p = (1 + np.sum(np.abs(nul - nul.mean()) >= abs(b - nul.mean()))) / (1 + nperm)
    return dict(col=col, bar_min=s, win_min=W, n=int(len(r)), sessions=int(first.sum()), b=b, null_mean=float(nul.mean()), null_sd=float(nul.std()), z=float(z), p=float(p), evaluable=True, sign="reversion" if z < 0 else "momentum")


def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); mx = 0.0
    for rank, i in enumerate(o): mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); adj[i] = mx
    return adj


def synth(kind="rw", n_sess=200, bounce=0.0):
    rng = np.random.default_rng(3); rows = []
    for s in range(n_sess):
        n = 20000; lp = np.cumsum(rng.standard_normal(n) * 2e-5); p = 115 * np.exp(lp); half = bounce * rng.choice([-1.0, 1.0], n) * 0.0156
        t0 = (1_700_000_000 + s * 86400) * 10**9; ts = t0 + np.arange(n) * 1_000_000_000
        rows.append((ts, p + half, p - 0.0156, p + 0.0156, np.full(n, 20250101 + s)))
    return [np.concatenate(x) for x in zip(*rows)]


def load_minutes():
    if SYNTH:
        ts, px, bid, ask, sd = synth(bounce=float(os.environ.get("OU2_BOUNCE", "0"))); return minute_series(ts, px, bid, ask, sd), []
    import edgelab_data as ed
    ed.check_inputs((INST, DESDE, HASTA)); parts, errors = [], []
    edges = pd.date_range(DESDE, HASTA, freq="MS").strftime("%Y-%m-%d").tolist() + [HASTA]
    for a, b in zip(edges[:-1], [(pd.Timestamp(x) - pd.Timedelta(days=1)).strftime("%Y-%m-%d") for x in edges[1:-1]] + [HASTA]):
        try:
            t = ed.load_ticks(INST, a, b, columns=["price_ticks", "bid_ticks", "ask_ticks"])
            if t.empty: continue
            sdv = pd.to_datetime(t.session_date).dt.strftime("%Y%m%d").astype(int).to_numpy()
            parts.append(minute_series(t.ts_utc_ns.to_numpy(), t.price_ticks.to_numpy(), t.bid_ticks.to_numpy(), t.ask_ticks.to_numpy(), sdv)); del t
        except Exception as e:
            import traceback; errors.append(dict(window=[a, b], err=traceback.format_exc()[-1500:])); print("ERROR", a, e, flush=True)
    return (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()), errors


def main():
    t0 = time.time(); rng = np.random.default_rng(SEED); df, errors = load_minutes()
    if df.empty:
        (OUT / "ERROR.json").write_text(json.dumps(dict(errors=errors), indent=1)); print("sin datos"); return
    df = df.sort_values(["ts"], kind="stable").reset_index(drop=True); cover = float(np.isfinite(df["mid"]).mean()); print("minutos", len(df), "con mid", round(cover, 4), flush=True)
    tests = [cell(df, "mid", s, W, rng) for s, W in CELLS]
    for r in tests:
        r["test"] = "ou2/mid_%d_%d" % (r["bar_min"], r["win_min"])
        if r["evaluable"]: r["p_two_sided"] = r["p"]; r["p"] = r["p"] if r["z"] < 0 else 1.0          # «sobrevive» exige reversión (z < 0); un z > 0 no cuenta como hallazgo
    ev = [r for r in tests if r["evaluable"]]
    for r, h in zip(ev, holm(np.array([r["p"] for r in ev]))): r["p_holm_%d" % len(ev)] = float(h)
    both = df[np.isfinite(df["mid"])].reset_index(drop=True); desc = [cell(both, "last", s, W, rng, 2000) for s, W in CELLS] + [cell(both, "mid", s, W, rng, 2000) for s, W in CELLS]
    sds = np.sort(both.sd.unique()); h1, h2 = both[both.sd <= sds[len(sds) // 2]], both[both.sd > sds[len(sds) // 2]]
    halves = [dict(half=k, **cell(h, c, s, W, rng, 1000)) for k, h in (("first", h1), ("second", h2)) for c in ("last", "mid") for s, W in CELLS[:3]]
    res = dict(campaign="OU-2", inst=INST, seed=SEED, nperm=NPERM, cells=CELLS, minutes=int(len(df)), mid_coverage=cover, results_flat=tests, descriptive=dict(same_minutes=desc, halves=halves), errors=errors, seconds=round(time.time() - t0))
    (OUT / ("OU2_SYNTH.json" if SYNTH else "STUDY_RESULTS.json")).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
