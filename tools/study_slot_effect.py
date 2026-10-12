#!/usr/bin/env python3
r"""Estudio paramétrico de efectos por franja horaria (CT) con nulo de signos y Holm. La configuración llega por STUDY_CFG (JSON) y debe figurar TEXTUALMENTE en el pre-registro
(el autopilot lo verifica antes de lanzar). Modos:
  idm        retorno «resto del día» (cierre previo 15:00 CT → 14:30 CT) vs última media hora (14:30 → 15:00 CT); corr; unilateral positiva (momentum). Opcional: diferencia de corr con gamma bajo (DIX/GEX, causal) en la fuente `gamma_source`.
  slot_corr  corr(r previo, r siguiente) de `horizon_min` minutos en cada franja de `slots`; unilateral negativa (reversión).
Fuentes: futuros por load_m1 (2025-07-01→2026-09-30) o spot Dukascopy (spot_ranges). Precio = apertura del minuto indicado. Sin holdout.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
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
    OUT = Path(os.environ.get("STUDY_OUT", "/tmp/study_out"))
OUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
SYNTH = os.environ.get("STUDY_SYNTH") == "1"
if not SYNTH:
    import edgelab_data as ed  # noqa: E402

CFG = json.loads(os.environ["STUDY_CFG"]) if "STUDY_CFG" in os.environ else {}
CT = "America/Chicago"
SEED = int(CFG.get("seed", 20261013))
NPERM = int(os.environ.get("STUDY_NPERM", CFG.get("nperm", 20000)))
BLOCK = 20


def load_source(name):
    if SYNTH:
        return synth(CFG.get("synth_gamma_effect", 0.0))
    if name in CFG.get("spot_ranges", {}):
        inst, a, b = CFG["spot_ranges"][name]
        t = ed.load_spot(inst, a, b, "m1"); mid = ((t.bid_open + t.ask_open) / 2).to_numpy()
        return pd.DataFrame(dict(ts=t.time_utc_ns.to_numpy(), open=mid))
    m = ed.load_m1(name, *CFG.get("futures_range", ["2025-07-01", "2026-09-30"])); k = float(m.attrs["tick_size"])
    return pd.DataFrame(dict(ts=m.minute.to_numpy(), open=m.open.to_numpy() * k))


def synth(gamma_effect=0.0, n_days=600, seed=3):
    """RW intradiaria; si gamma_effect>0, en días de «gamma bajo» (de a bloques) el último 30 min sigue al resto del día."""
    rng = np.random.default_rng(seed); rows = []; d0 = pd.Timestamp("2018-01-02")
    for d in range(n_days):
        day = d0 + pd.Timedelta(days=d)
        if day.dayofweek >= 5: continue
        low = (d // 40) % 3 == 0
        r = rng.standard_normal(24 * 60) * 1e-4
        lp = np.cumsum(r)
        i1430, i1500 = (14 * 60 + 30), 15 * 60                       # minutos desde 00:00 CT del día
        rod = lp[i1430] - lp[0]
        if gamma_effect and low: lp[i1500:] += gamma_effect * rod
        ts = (pd.Timestamp(day, tz=CT) + pd.to_timedelta(np.arange(24 * 60), unit="m")).tz_convert("UTC").tz_localize(None).values.astype("datetime64[ns]").astype("int64")
        rows.append(pd.DataFrame(dict(ts=ts, open=100 * np.exp(lp))))
    return pd.concat(rows, ignore_index=True)


def sessions_table(df, times):
    """DataFrame por fecha local CT con el precio (apertura del minuto) en cada hh:mm de `times` ('prev15' = 15:00 de la sesión anterior)."""
    loc = pd.DatetimeIndex(pd.to_datetime(df.ts.to_numpy(), utc=True)).tz_convert(CT)
    mod = loc.hour * 60 + loc.minute; want = {int(t[:2]) * 60 + int(t[3:]): t for t in times}
    sel = np.isin(mod, list(want))
    t = pd.DataFrame(dict(date=loc[sel].strftime("%Y-%m-%d"), hm=[want[m] for m in mod[sel]], p=df.open.to_numpy()[sel]))
    t = t.drop_duplicates(["date", "hm"]).pivot(index="date", columns="hm", values="p").sort_index()
    return t


def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); mx = 0.0
    for rank, i in enumerate(o):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); adj[i] = mx
    return adj


def signflip_p(x, y, rng, sign):
    """p unilateral de corr(x,y) con nulo de signo aleatorio sobre y. sign=+1: H1 corr>0; -1: H1 corr<0."""
    c = float(np.corrcoef(x, y)[0, 1]); xs = (x - x.mean()) / x.std(); ys = y - y.mean()
    nul = np.empty(NPERM)
    for i in range(NPERM):
        s = rng.choice([-1.0, 1.0], len(y)); z = ys * s; nul[i] = (xs * (z - z.mean())).mean() / z.std()
    return c, float((1 + np.sum(sign * nul >= sign * c)) / (1 + NPERM)), float(nul.std())


def gamma_labels(dates):
    if SYNTH:
        low = np.array([(i // 40) % 3 == 0 for i in range(len(dates))]); return low
    p = Path("/kaggle/working/dix.csv") if KAGGLE else Path(CFG.get("dix_path", "/tmp/dix.csv"))
    if KAGGLE: urllib.request.urlretrieve("https://squeezemetrics.com/monitor/static/DIX.csv", p)
    g = pd.read_csv(p, dtype={"date": str}).set_index("date").gex.sort_index(); idx, vals = g.index.to_numpy(), g.to_numpy(); low = []
    for d in dates:
        k = int(np.searchsorted(idx, d, side="left"))
        low.append(bool(k >= 251 and vals[k - 1] < np.quantile(vals[:k - 1 + 1], 0.20)) if k >= 251 else np.nan)
    return np.array(low, dtype=object)


def block_perm(v, rng):
    blocks = [v[i:i + BLOCK] for i in range(0, len(v), BLOCK)]; return np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])


def mode_idm(rng):
    out, ps, rows = [], [], []
    for name in CFG["sources"]:
        t = sessions_table(load_source(name), ["14:30", "15:00"]); p15 = t["15:00"]; prev = p15.shift(1)
        ok = t["14:30"].notna() & p15.notna() & prev.notna()
        rod, lh = np.log(t["14:30"][ok] / prev[ok]).to_numpy(), np.log(p15[ok] / t["14:30"][ok]).to_numpy()
        if len(rod) < 100: out.append(dict(source=name, n=int(len(rod)), evaluable=False)); continue
        c, p, sd = signflip_p(rod, lh, rng, +1); r = dict(test=f"idm/{name}", source=name, n=int(len(rod)), corr=c, null_sd=sd, p=p, evaluable=True)
        out.append(r); ps.append(p); rows.append(r); print(r, flush=True)
        if name == CFG.get("gamma_source"):
            dates = list(t.index[ok]); low = gamma_labels(dates); good = np.array([x is not np.nan and x == x for x in low]) if low.dtype == object else np.ones(len(low), bool)
            lowb = low[good].astype(bool); a, b = rod[good], lh[good]
            if lowb.sum() >= 30 and (~lowb).sum() >= 30:
                diff = lambda m: np.corrcoef(a[m], b[m])[0, 1] - np.corrcoef(a[~m], b[~m])[0, 1]
                obs = float(diff(lowb)); nul = np.array([diff(block_perm(lowb, rng)) for _ in range(NPERM)])
                pp = float((1 + np.sum(nul >= obs)) / (1 + NPERM))
                r2 = dict(test=f"idm_gamma_diff/{name}", source=name, n_low=int(lowb.sum()), n_high=int((~lowb).sum()), diff=obs, null_sd=float(nul.std()), p=pp, evaluable=True)
                out.append(r2); ps.append(pp); rows.append(r2); print(r2, flush=True)
            else: out.append(dict(test=f"idm_gamma_diff/{name}", evaluable=False, n_low=int(lowb.sum())))
    return out, ps, rows


def mode_slot_corr(rng):
    out, ps, rows = [], [], []; h = int(CFG.get("horizon_min", 15))
    for name in CFG["sources"]:
        df = load_source(name)
        for slot in CFG["slots"]:
            hh, mm = map(int, slot.split(":")); t0 = hh * 60 + mm
            lab = lambda m: f"{(m // 60) % 24:02d}:{m % 60:02d}"
            t = sessions_table(df, [lab(t0 - h), lab(t0), lab(t0 + h)]); ok = t.notna().all(axis=1)
            x = np.log(t[lab(t0)][ok] / t[lab(t0 - h)][ok]).to_numpy(); y = np.log(t[lab(t0 + h)][ok] / t[lab(t0)][ok]).to_numpy()
            if len(x) < 100: out.append(dict(test=f"slot/{name}/{slot}", n=int(len(x)), evaluable=False)); continue
            c, p, sd = signflip_p(x, y, rng, -1); r = dict(test=f"slot/{name}/{slot}", source=name, slot=slot, n=int(len(x)), corr=c, null_sd=sd, p=p, evaluable=True)
            out.append(r); ps.append(p); rows.append(r); print(r, flush=True)
    return out, ps, rows


def main():
    t0 = time.time(); rng = np.random.default_rng(SEED); mode = CFG["mode"]
    out, ps, rows = (mode_idm if mode == "idm" else mode_slot_corr)(rng)
    m = int(CFG.get("n_planned", len(ps)))
    for r, h in zip(rows, holm(np.array(ps)) if ps else []): r["p_holm_%d" % m] = float(min(1.0, h * 1.0))
    # Holm con m planeado (≥ evaluables): reajusta usando m en el denominador
    o = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(o):
        mx = max(mx, min(1.0, (m - rank) * ps[i])); rows[i]["p_holm_%d" % m] = mx
    res = dict(campaign=CFG.get("campaign", "study_slot_effect"), cfg=CFG, nperm=NPERM, results_flat=out, n_planned=m, seconds=round(time.time() - t0))
    (OUT / "STUDY_RESULTS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
