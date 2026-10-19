#!/usr/bin/env python3
r"""OU-1 — diagnóstico de reversión (Ornstein-Uhlenbeck) por activo × escala, y chequeo de mecanismo en las celdas de GC.
Pre-registro: docs/research/ou_20261012/PREREGISTRO_OU1.md (escrito antes de correr). SOLO información: no genera estrategias.

Parte A (36 pruebas, Holm 36): X_t = ln P_t − SMA_N(ln P_t) dentro de sesión; b = pendiente de (X_{t+1}−X_t) sobre X_t, agrupado.
  Nulo: signo aleatorio independiente por retorno de barra (martingala con la misma volatilidad); estadístico z = (b − media_nulo)/sd_nulo, bilateral.
  (ADF/Hurst sobre X NO se usan como prueba: X es estacionaria por construcción, ver el pre-registro.)
Parte B (6 pruebas, Holm 6): corr(r15 previo, r15 siguiente) en las franjas CT 04:30, 19:30, 04:15 de GC (spot 2022-07→2025-06 y futuro 2025-07→2026-09); unilateral negativa.
"""
from __future__ import annotations

import json
import os
import sys
import time
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
    OUT = Path(os.environ.get("OU_OUT", "/tmp/ou1_out"))
OUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
SYNTH = os.environ.get("OU_SYNTH") == "1"
if not SYNTH:
    import edgelab_data as ed  # noqa: E402

SEED = 20261012
NPERM_A, NPERM_B = int(os.environ.get("OU_NPERM_A", 5000)), int(os.environ.get("OU_NPERM_B", 20000))
CT = "America/Chicago"
FUT = ["ES", "NQ", "YM", "GC", "ZB", "6E", "6J"]
FUT_RANGE = ("2025-07-01", "2026-09-30")
SPOT = {"GC_spot": ("GC", "2022-07-01", "2025-06-30"), "ES_spot": ("ES", "2018-01-01", "2025-06-30")}
CELLS = [(5, 60), (5, 240), (15, 240), (60, 240)]          # (minutos por barra, ventana SMA en minutos)
SLOTS = ["04:30", "19:30", "04:15"]


def session_date(ts_ns: np.ndarray) -> np.ndarray:
    um, inv = np.unique(ts_ns // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT) + pd.Timedelta(hours=7)
    codes = (c.year * 10000 + c.month * 100 + c.day).to_numpy()
    return codes[inv]


def load_series(name):
    """Devuelve DataFrame minuto: ts (inicio de minuto, ns UTC), open, close (precio real), sd (código fecha de sesión)."""
    if SYNTH:
        return synth()
    if name in FUT:
        m = ed.load_m1(name, *FUT_RANGE); k = float(m.attrs["tick_size"])
        return pd.DataFrame(dict(ts=m.minute.to_numpy(), open=m.open.to_numpy() * k, close=m.close.to_numpy() * k,
                                 sd=pd.to_datetime(m.session_date).dt.strftime("%Y%m%d").astype(int).to_numpy()))
    inst, a, b = SPOT[name]
    t = ed.load_spot(inst, a, b, "m1"); mid = lambda c: ((t["bid_" + c] + t["ask_" + c]) / 2).to_numpy()
    ts = t.time_utc_ns.to_numpy()
    return pd.DataFrame(dict(ts=ts, open=mid("open"), close=mid("close"), sd=session_date(ts)))


def synth(n_sess=300, kind=None):
    kind = kind or os.environ.get("OU_KIND", "rw"); rng = np.random.default_rng(1); rows = []
    base = pd.Timestamp("2025-01-06 23:00", tz="UTC").value
    for s in range(n_sess):
        n = 1380; r = rng.standard_normal(n) * 1e-4; x = np.zeros(n); lp = np.zeros(n)
        if kind == "ou":
            for i in range(1, n): x[i] = x[i - 1] * (1 - 0.01) + r[i]
            lp = x
        else:
            lp = np.cumsum(r)
        p = 100 * np.exp(lp); ts = base + s * 86_400_000_000_000 + np.arange(n) * 60_000_000_000
        rows.append(pd.DataFrame(dict(ts=ts, open=p, close=p, sd=20250106 + s)))
    return pd.concat(rows, ignore_index=True)


def make_bars(df, s):
    b = df.ts.to_numpy() // (s * 60_000_000_000)
    key = df.sd.to_numpy().astype(np.int64) * 10_000_000_000 + b.astype(np.int64)
    last = np.r_[key[1:] != key[:-1], True]                   # última fila de cada (sesión, barra)
    return df.sd.to_numpy()[last], np.log(df.close.to_numpy()[last])


def b_stat(r, first, N):
    """r: retornos de barra (0 en la primera barra de sesión); first: bool inicio de sesión. Devuelve la pendiente b agrupada."""
    c = np.cumsum(r); n = len(c)
    pos = np.arange(n) - np.maximum.accumulate(np.where(first, np.arange(n), 0))     # posición dentro de la sesión
    cs = np.r_[0.0, np.cumsum(c)]
    sma = np.full(n, np.nan); idx = np.arange(N - 1, n)
    sma[idx] = (cs[idx + 1] - cs[idx + 1 - N]) / N
    X = np.where(pos >= N - 1, c - sma, np.nan)
    x, y = X[:-1], X[1:] - X[:-1]
    ok = np.isfinite(x) & np.isfinite(y) & ~first[1:]
    x, y = x[ok], y[ok]; x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum()), int(ok.sum())


def part_a(name, df, rng):
    out = []
    for s, W in CELLS:
        sd, lp = make_bars(df, s); N = W // s
        first = np.r_[True, sd[1:] != sd[:-1]]
        r = np.where(first, 0.0, np.r_[0.0, np.diff(lp)])
        if len(r) < 20 * N or (~first).sum() < 1000:
            out.append(dict(asset=name, bar_min=s, win_min=W, n=int(len(r)), evaluable=False)); continue
        b, nn = b_stat(r, first, N); nul = np.empty(NPERM_A)
        for i in range(NPERM_A):
            nul[i] = b_stat(r * rng.choice([-1.0, 1.0], len(r)), first, N)[0]
        z = (b - nul.mean()) / nul.std(); p = (1 + np.sum(np.abs(nul - nul.mean()) >= abs(b - nul.mean()))) / (1 + NPERM_A)
        hl = float(np.log(2) / -np.log(1 + b) * s) if -1 < b < 0 else None
        out.append(dict(asset=name, bar_min=s, win_min=W, n=int(len(r)), sessions=int(first.sum()), b=b, null_mean=float(nul.mean()), null_sd=float(nul.std()),
                        z=float(z), p=float(p), evaluable=True, half_life_min_desc=hl, sign="reversion" if z < 0 else "momentum"))
        print(name, s, W, round(b, 5), "z", round(z, 2), "p", round(p, 4), flush=True)
    return out


def part_b(name, df, rng):
    ts = df.ts.to_numpy(); op = df.open.to_numpy(); look = pd.Series(op, index=ts)
    look = look[~look.index.duplicated()]
    sd = df.sd.to_numpy(); out = []
    local = pd.to_datetime(ts, utc=True).tz_convert(CT)
    for slot in SLOTS:
        hh, mm = map(int, slot.split(":")); sel = (local.hour == hh) & (local.minute == mm)
        t0 = ts[sel]; need = np.r_[t0 - 900 * 10**9, t0, t0 + 900 * 10**9]
        v = look.reindex(need).to_numpy().reshape(3, -1)
        ok = np.isfinite(v).all(0)
        if ok.sum() < 100:
            out.append(dict(source=name, slot=slot, n=int(ok.sum()), evaluable=False)); continue
        rp, rn = np.log(v[1][ok] / v[0][ok]), np.log(v[2][ok] / v[1][ok])
        c = float(np.corrcoef(rp, rn)[0, 1]); nul = np.array([np.corrcoef(rp, rn * rng.choice([-1.0, 1.0], len(rn)))[0, 1] for _ in range(NPERM_B)])
        p = (1 + np.sum(nul <= c)) / (1 + NPERM_B)
        out.append(dict(source=name, slot=slot, n=int(ok.sum()), corr=c, null_sd=float(nul.std()), p_one_sided_neg=float(p), evaluable=True))
        print("B", name, slot, round(c, 4), "p", round(p, 4), flush=True)
    return out


def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); mx = 0.0
    for rank, i in enumerate(o):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); adj[i] = mx
    return adj


def main():
    t0 = time.time(); rng = np.random.default_rng(SEED); A, B = [], []; dropped = []
    names = ["SYN"] if SYNTH else FUT + list(SPOT)
    for nm in names:
        try:
            df = load_series(nm)
        except Exception as e:
            dropped.append((nm, repr(e))); print("sin datos", nm, e, flush=True); continue
        if df is None or df.empty:
            dropped.append((nm, "vacío")); continue
        A += part_a(nm, df, rng)
        if nm in ("GC", "GC_spot", "SYN"):
            B += part_b(nm, df, rng)
    ev = [r for r in A if r["evaluable"]]
    for r, h in zip(ev, holm(np.array([r["p"] for r in ev]))): r["p_holm_%d" % len(ev)] = float(h)
    evb = [r for r in B if r["evaluable"]]
    for r, h in zip(evb, holm(np.array([r["p_one_sided_neg"] for r in evb]))): r["p_holm_%d" % len(evb)] = float(h)
    res = dict(campaign="OU-1", prereg="docs/research/ou_20261012/PREREGISTRO_OU1.md", seed=SEED, nperm_a=NPERM_A, nperm_b=NPERM_B, cells=CELLS,
               part_a=A, part_b=B, dropped=dropped, seconds=round(time.time() - t0))
    (OUT / ("OU1_SYNTH.json" if SYNTH else "OU1_RESULTADOS.json")).write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
