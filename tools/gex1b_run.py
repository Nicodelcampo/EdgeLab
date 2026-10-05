#!/usr/bin/env python3
r"""GEX-1b (docs/research/GEX1B_PREREGISTRO_20261005.md): extensión por potencia de GEX-1. Sólo información.

Estado: gex_{t-1} de SqueezeMetrics (DIX.csv) < 0 vs >= 0. Métricas por sesión RTH (08:30-15:00 CT) sobre barras de 5 min:
  I1a rango/rango_prev20 · I1b std(r5)/sigma_prev20               (amplitud)
  I2d pendiente r_last ~ r_rest (gex<0 menos gex>=0) · I2n |r_last|/sigma_prev  (continuación de cierre)
  I3d autocorrelación lag-1 de r5 · I3n autocorrelación lag-1 de |r5|         (autocorrelación intradía)
Fuentes: MES (NT8, edgelab_data, sesiones aprobadas 2025-07 → 2026-09-30) y spot USA500 Dukascopy (2023-01 → 2025-06).
Nulo: permutación por bloques de 20 sesiones de la etiqueta, 20.000 sorteos, semilla 20261006; unilateral (gex<0 mayor).
Holm sobre 12. MDE = (z_{1-0.05/12} + 0.84) · sd(nulo). Control: diferencia dentro de quintiles de sigma_prev.
    .venv\Scripts\python tools\gex1_run.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import norm

os.environ["EDGELAB_ALLOW_MISSING"] = "1"      # decisión de Nico (2026-10-05): sin las sesiones de MES que no tienen fuente; se declaran en el resultado
KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:                                    # en Kaggle: inputs montados (raíz plana o datasets/<owner>/<slug>)
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    SPOT = next(p for r in _roots for p in r.glob("edgelab-dukascopy-es-usa500/**/USA500IDXUSD_m1.parquet"))
    DIX = Path("/kaggle/working/dix.csv")
    import urllib.request
    urllib.request.urlretrieve("https://squeezemetrics.com/monitor/static/DIX.csv", DIX)
    OUT = Path("/kaggle/working/GEX1B_RESULTADOS_20261005")
else:
    os.environ.setdefault("EDGELAB_DATA_ROOTS", r"E:\_edgelab_roots")
    sys.path.insert(0, r"E:\EdgeLab-vibrant\docs\data_catalog")
    DIX = Path(r"C:\Users\Usuario\AppData\Local\Temp\claude\E--EdgeLab\6d978e5c-b269-4cad-a57e-097ee2cbd643\scratchpad\gex\dix.csv")
    SPOT = Path(r"E:\kaggle_dukascopy_USA500IDXUSD\USA500IDXUSD_m1.parquet")
    OUT = Path(__file__).resolve().parents[1] / "docs/research/GEX1B_RESULTADOS_20261005"
import edgelab_data as ed  # noqa: E402

CT = "America/Chicago"
SEED, NPERM, BLOCK, NTESTS = 20261007, 20_000, 20, 24


def session_metrics(m: pd.DataFrame) -> pd.DataFrame:
    """m: columnas ts (UTC ns del inicio del minuto), o,h,l,c en precio. Devuelve una fila por fecha RTH."""
    t = pd.to_datetime(m.ts, utc=True).dt.tz_convert(CT)
    m = m.assign(date=t.dt.strftime("%Y-%m-%d"), mins=t.dt.hour * 60 + t.dt.minute)
    rows = []; prev_close = None
    for d, g in m.groupby("date", sort=True):
        r = g[(g.mins >= 510) & (g.mins < 900)]                      # 08:30 .. 14:59 CT (inicio de minuto)
        if len(r) < 360:                                             # RTH incompleta (390 min): se descarta
            prev_close = None; continue
        c = r.set_index("mins").c
        five = c.reindex(range(514, 900, 5)).ffill()                 # cierre de cada barra de 5 min
        p0 = r.o.iloc[0]; px = np.r_[p0, five.to_numpy()]
        r5 = np.diff(np.log(px))
        p1430 = c.reindex(range(840, 870)).ffill().iloc[-1] if c.index.max() >= 869 else np.nan
        close = c.iloc[-1]
        row = dict(date=d, rng=np.log(r.h.max() / r.l.min()), sd5=np.std(r5, ddof=1),
                   ac1=np.corrcoef(r5[:-1], r5[1:])[0, 1], ac1abs=np.corrcoef(np.abs(r5[:-1]), np.abs(r5[1:]))[0, 1],
                   r_last=np.log(close / p1430) if np.isfinite(p1430) else np.nan,
                   r_rest=np.log(p1430 / prev_close) if prev_close and np.isfinite(p1430) else np.nan)
        rows.append(row); prev_close = close
    s = pd.DataFrame(rows)
    s["rng_prev"] = s.rng.shift(1).rolling(20).mean(); s["sig_prev"] = s.sd5.shift(1).rolling(20).mean()
    s["I1a"] = s.rng / s.rng_prev; s["I1b"] = s.sd5 / s.sig_prev; s["I2n"] = s.r_last.abs() / s.sig_prev
    return s.dropna(subset=["rng_prev", "sig_prev"]).reset_index(drop=True)


def mes_m1():
    parts = []
    for a, b in [("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31"), ("2026-01-01", "2026-03-31"),
                 ("2026-04-01", "2026-06-30"), ("2026-07-01", "2026-09-30")]:
        x = ed.load_m1("MES", a, b)
        tick = x.attrs["tick_size"]
        parts.append(pd.DataFrame(dict(ts=x.minute, o=x.open * tick, h=x.high * tick, l=x.low * tick, c=x.close * tick)))
        print("MES", a, len(x), flush=True)
    return pd.concat(parts).sort_values("ts").drop_duplicates("ts")


def spot_m1():
    t = pq.read_table(SPOT, filters=[("time_utc_ns", ">=", pd.Timestamp("2023-01-01", tz="UTC").value),
                                     ("time_utc_ns", "<", pd.Timestamp("2025-07-01", tz="UTC").value)]).to_pandas()
    mid = lambda k: (t[f"bid_{k}"] + t[f"ask_{k}"]) / 2
    return pd.DataFrame(dict(ts=t.time_utc_ns, o=mid("open"), h=mid("high"), l=mid("low"), c=mid("close")))


def label(s, dix):
    """gex_{t-1} (último gex ANTERIOR a la fecha) y el umbral causal q20 = percentil 20 de todos los gex anteriores a esa fecha (ventana expansiva, mín. 250 días)."""
    g = dix.set_index("date").gex.sort_index()
    idx = g.index.to_numpy(); vals = g.to_numpy()
    prev, thr = [], []
    for d in s.date:
        k = int(np.searchsorted(idx, d, side="left"))                 # filas con fecha < d
        prev.append(vals[k - 1] if k > 0 else np.nan)
        thr.append(np.quantile(vals[:k - 1 + 1], 0.20) if k >= 250 else np.nan)
    s = s.assign(gex_prev=prev, thr_q20=thr).dropna(subset=["gex_prev", "thr_q20"]).reset_index(drop=True)
    return s.assign(low=(s.gex_prev < s.thr_q20).to_numpy())


def _slope(x, y):
    k = np.isfinite(x) & np.isfinite(y)
    return np.polyfit(x[k], y[k], 1)[0] if k.sum() > 5 else np.nan


def stats_Q(s, low):
    out = {}
    for k in ("I1a", "I1b", "I2n", "ac1", "ac1abs"):
        v = s[k].to_numpy(); out[k] = np.nanmean(v[low]) - np.nanmean(v[~low])
    x, y = s.r_rest.to_numpy(), s.r_last.to_numpy()
    out["I2d"] = _slope(x[low], y[low]) - _slope(x[~low], y[~low])
    return out


def stats_C(s, g):
    """Estadísticos con el signo orientado a «menos gamma, más efecto»: -corr(g, métrica); para I2d, -β de la interacción r_rest*g (g estandarizado)."""
    out = {}
    for k in ("I1a", "I1b", "I2n", "ac1", "ac1abs"):
        v = s[k].to_numpy(); m = np.isfinite(v) & np.isfinite(g)
        out[k] = -np.corrcoef(g[m], v[m])[0, 1] if m.sum() > 5 else np.nan
    x, y = s.r_rest.to_numpy(), s.r_last.to_numpy(); m = np.isfinite(x) & np.isfinite(y) & np.isfinite(g)
    if m.sum() > 8:
        gz = (g[m] - g[m].mean()) / g[m].std()
        X = np.c_[np.ones(m.sum()), x[m], gz, x[m] * gz]
        out["I2d"] = -np.linalg.lstsq(X, y[m], rcond=None)[0][3]
    else:
        out["I2d"] = np.nan
    return out


def block_perm(v, rng):
    n = len(v); blocks = [v[i:i + BLOCK] for i in range(0, n, BLOCK)]
    order = rng.permutation(len(blocks)); return np.concatenate([blocks[i] for i in order])


def run_def(name, s, kind):
    """kind 'Q' (etiqueta cuantil) o 'C' (gex continuo)."""
    rng = np.random.default_rng(SEED + (0 if kind == "Q" else 1))
    if kind == "Q":
        v = s.low.to_numpy(); f = lambda z: stats_Q(s, z)
    else:
        v = s.gex_prev.to_numpy().astype(float); f = lambda z: stats_C(s, z)
    obs = f(v); null = {k: [] for k in obs}
    for _ in range(NPERM):
        st = f(block_perm(v, rng))
        for k in obs: null[k].append(st[k])
    zc = norm.ppf(1 - 0.05 / NTESTS); res = {}
    for k, o_ in obs.items():
        nv = np.array(null[k]); nv = nv[np.isfinite(nv)]
        ev = bool(np.isfinite(o_) and len(nv) > 100)                      # un estadístico no finito es «no evaluable», NO tiene p
        res[k] = dict(obs=float(o_) if np.isfinite(o_) else None, evaluable=ev, p=float((1 + np.sum(nv >= o_)) / (1 + len(nv))) if ev else None,
                      null_sd=float(nv.std()) if len(nv) else None, mde=float((zc + 0.84) * nv.std()) if len(nv) else None)
    q = pd.qcut(s.sig_prev, 5, labels=False)                              # control descriptivo por volatilidad previa
    for k in ("I1a", "I1b", "I2n", "ac1", "ac1abs"):
        if kind == "Q":
            d = [s[k][(q == j) & s.low].mean() - s[k][(q == j) & ~s.low].mean() for j in range(5) if ((q == j) & s.low).sum() >= 5 and ((q == j) & ~s.low).sum() >= 5]
        else:
            d = []
            for j in range(5):
                m = (q == j).to_numpy() & s[k].notna().to_numpy()
                if m.sum() >= 15: d.append(-np.corrcoef(s.gex_prev.to_numpy()[m], s[k].to_numpy()[m])[0, 1])
        res[k]["vol_stratified"] = float(np.mean(d)) if d else None
    return dict(source=name, definition=kind, n=int(len(s)), n_low=int(s.low.sum()) if kind == "Q" else None, first=s.date.iloc[0], last=s.date.iloc[-1], tests=res)


def main():
    dix = pd.read_csv(DIX, dtype={"date": str}); dix = dix[dix.date < "2026-10-01"]
    results = []
    for name, m in (("MES_NT8", mes_m1()), ("USA500_spot", spot_m1())):
        s = label(session_metrics(m), dix); s = s[s.date < "2026-10-01"].reset_index(drop=True)
        print(name, "sesiones", len(s), "bajas(q20)", int(s.low.sum()), flush=True)
        for kind in ("Q", "C"):
            results.append(run_def(name, s, kind))
    ps = [(r["source"], r["definition"], k, t["p"]) for r in results for k, t in r["tests"].items() if t["evaluable"]]
    order = sorted(range(len(ps)), key=lambda i: ps[i][3]); m = NTESTS; adj = [None] * len(ps); run_max = 0.0
    for rank, i in enumerate(order):
        run_max = max(run_max, min(1.0, (m - rank) * ps[i][3])); adj[i] = run_max
    for (src, kd, k, _), a in zip(ps, adj):
        next(r for r in results if r["source"] == src and r["definition"] == kd)["tests"][k]["p_holm"] = a
    out = dict(campaign="GEX-1b", prereg="docs/research/GEX1B_PREREGISTRO_20261005.md", seed=SEED, nperm=NPERM, block=BLOCK, n_tests=NTESTS, dropped_sessions=ed.DROPPED,
               generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), results=results)
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for r in results:
        print(r["source"], r["definition"], r["n"], r["n_low"], r["first"], r["last"])
        for k, t in r["tests"].items():
            print(f"  {k:7s} obs={t['obs']} p={t['p']} holm={t.get('p_holm')} mde={t['mde']} vol={t.get('vol_stratified')}")


if __name__ == "__main__":
    main()
