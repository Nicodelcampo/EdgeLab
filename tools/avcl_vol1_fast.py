#!/usr/bin/env python3
r"""AVCL-VOL-1 — etapa 1 (no direccional). Manifiesto: docs/research/AVCL_VOL1_MANIFIESTO_20261005.md (OK de Nico).

Por contrato MNQ (uno a la vez, para memoria): ticks del contrato (sin pausa CME, sin holdout) → barras 50t →
footprints con la regla NT8 de subserie 1-tick → avolclusterpoi_full.run_full con los parámetros congelados. Eventos =
creaciones OFF_PRICE / AT_PRICE en sesiones aprobadas donde el contrato es líder (RESOLVER). Controles = bloques cerrados
sin creación, a más de 2H barras de cualquier creación, en las mismas sesiones.
Métricas por H ∈ {10, 50, 200} barras: y_rv = log(RV_adelante / RV_atrás), y_rg = log((rango_adelante+1)/(rango_atrás+1)),
ventanas dentro de la misma sesión. Estratos: contrato × franja 30 min CT × decil de volumen del bloque × decil de RV
previa. Hasta 5 controles por evento por estrato. D = Σ_s n_e,s (media_e,s − media_c,s) / N_e. Nulo: permutación de la
etiqueta dentro de estrato, 20.000 sorteos, semilla 20261005, unilateral (D > 0). Holm sobre 12 (RTH). IC por bootstrap
de sesiones. MDE = (z_{1-0,05/12} + 0,84)·sd(nulo). ETH: descriptivo.
"""
from __future__ import annotations

import dataclasses
import gc
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
    sys.path.insert(0, str(next(p.parent.parent for r in _roots for p in r.glob("edgelab-code-avcl-vol1/**/edgelab/__init__.py"))))
    OUT = Path("/kaggle/working")
else:
    os.environ.setdefault("EDGELAB_DATA_ROOTS", r"E:\_edgelab_roots")
    sys.path.insert(0, r"E:\EdgeLab-vibrant\docs\data_catalog")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    OUT = Path(os.environ.get("AVCL_OUT", r"C:\tmp_avcl_vol1"))
OUT.mkdir(parents=True, exist_ok=True)

import edgelab_data as ed  # noqa: E402
from scipy.stats import norm  # noqa: E402
from edgelab.bridge import bars as B  # noqa: E402
from edgelab.bridge import ticks as T  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi_full import run_full  # noqa: E402
from edgelab.bridge.sessions import session_end_ns  # noqa: E402

PARAMS = dict(window_bars=10, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2, use_session_buckets=True,
              time_bucket_minutes=30, lookback_sessions=20, detection_percentile=95.0, min_samples_per_bucket=20,
              enable_predictive_filter=False, use_topk_hot_cells=False, invalidation_mode="None", max_age_bars=500)
HS = (10, 50, 200)
SEED, NPERM, NBOOT, NTESTS, MAXCTRL = 20261005, int(os.environ.get("AVCL_NPERM", 20000)), 2000, 12, 5
END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value
CT = "America/Chicago"
DESDE, HASTA = os.environ.get("AVCL_DESDE", "2025-07-01"), os.environ.get("AVCL_HASTA", "2026-09-30")


def ct_minute_of_day(ts_ns):
    """Minuto del día en hora de Chicago (hora*60+minuto) de cada instante: se convierte UNA vez por minuto único, no por tick (idéntico resultado)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    um, inv = np.unique(ts // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT)
    return np.asarray(c.hour * 60 + c.minute)[inv]


def session_end_vec(end_ns):
    """Mismo resultado que session_end_ns(int(x)) para cada barra: próximo cierre 16:00 CT lun-vie estrictamente posterior (bucle Python por barra -> searchsorted)."""
    end = np.asarray(end_ns, dtype=np.int64)
    d0 = pd.Timestamp(int(end.min()), tz="UTC").tz_convert(CT).normalize() - pd.Timedelta(days=1)
    d1 = pd.Timestamp(int(end.max()), tz="UTC").tz_convert(CT).normalize() + pd.Timedelta(days=8)
    days = pd.date_range(d0.tz_localize(None), d1.tz_localize(None), freq="D")
    days = days[days.weekday < 5]
    closes = np.sort((days + pd.Timedelta(hours=16)).tz_localize(CT).tz_convert("UTC").asi8)
    return closes[np.searchsorted(closes, end, side="right")]


def contract_rows(c, sess):
    rows = sess[sess.contract == c]
    ds, fl = rows.groupby(["dataset", "file"]).size().idxmax()
    first = pd.Timestamp(rows.date.min()).tz_localize(CT) - pd.Timedelta(days=45)
    last = pd.Timestamp(rows.date.max()).tz_localize(CT) + pd.Timedelta(hours=16)
    return ds, fl, int(first.value), int(min(last.value, END_NS)), set(rows.date)


def process(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    path = ed._path(ds, fl)
    t0 = time.time()
    tk = T.load_canonical_parquet(str(path), start_utc_ns=a, end_utc_ns=b)
    mod = ct_minute_of_day(tk.ts_ns)
    keep = np.asarray(~((mod >= 960) & (mod < 1020)))
    tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None)
                                    for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
    del mod, keep
    bars = B.build_tick_bars(tk, 50)
    fps = B.build_footprints(tk, bars, nt8_subseries=True)
    r = run_full(tk, bars, fps, PARAMS)
    del fps, tk
    gc.collect()
    n = len(bars.close_t)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y-%m-%d"))[uinv]
    mins = ct_minute_of_day(end)
    rth = (mins >= 510) & (mins < 900)
    clockb = mins // 30
    hi, lo = np.asarray(bars.high_t, float), np.asarray(bars.low_t, float)
    lc = np.log(np.asarray(bars.close_t, float))
    ret2 = np.r_[0.0, np.diff(lc) ** 2]
    cs = np.cumsum(ret2)
    created = {}
    for z in r["zones"]:
        created[int(z["created_bar"])] = "OFF" if z["kind"] == "OFF_PRICE" else "AT"
    cbar = np.array(sorted(created), dtype=np.int64)
    blk = pd.DataFrame(r["blocks"], columns=["bar", "vol", "bucket"])
    blk["kind"] = blk.bar.map(created).fillna("CTRL")
    blk = blk[np.isin(sdate[blk.bar], list(dates))]
    blk["voldec"] = pd.qcut(blk.vol.rank(method="first"), 10, labels=False)
    out = []
    for H in HS:
        b0 = blk.bar.to_numpy()
        ok = (b0 - H + 1 >= 0) & (b0 + H < n)
        bb = b0[ok]
        same = send[bb - H + 1] == send[np.minimum(bb + H, n - 1)]
        rv_f = cs[np.minimum(bb + H, n - 1)] - cs[bb]
        rv_b = cs[bb] - cs[np.maximum(bb - H, 0)]
        hs, ls = pd.Series(hi), pd.Series(lo)
        rmax_f = hs.rolling(H).max().shift(-H).to_numpy()[bb]; rmin_f = ls.rolling(H).min().shift(-H).to_numpy()[bb]
        rmax_b = hs.rolling(H).max().to_numpy()[bb]; rmin_b = ls.rolling(H).min().to_numpy()[bb]
        eps = 1e-12
        d = blk[ok].copy()
        d["H"] = H
        d["y_rv"] = np.log((rv_f + eps) / (rv_b + eps))
        d["y_rg"] = np.log((rmax_f - rmin_f + 1) / (rmax_b - rmin_b + 1))
        d["rvb"] = rv_b
        d["valid"] = same
        if len(cbar):                                         # controles lejos (> 2H) de cualquier creación
            j = np.searchsorted(cbar, bb)
            dist = np.minimum(np.abs(bb - cbar[np.clip(j, 0, len(cbar) - 1)]), np.abs(bb - cbar[np.clip(j - 1, 0, len(cbar) - 1)]))
            d["far"] = dist > 2 * H
        else:
            d["far"] = True
        d = d[d.valid & ((d.kind != "CTRL") | d.far)]
        d["rvdec"] = pd.qcut(d.rvb.rank(method="first"), 10, labels=False)
        d["rth"] = rth[d.bar]; d["clock"] = clockb[d.bar]; d["session"] = sdate[d.bar]; d["contract"] = c
        out.append(d[["contract", "session", "bar", "kind", "H", "rth", "clock", "voldec", "rvdec", "y_rv", "y_rg"]])
    del bars, r
    gc.collect()
    print(c, ds, "eventos OFF/AT", int((blk.kind == "OFF").sum()), int((blk.kind == "AT").sum()), "%.0f s" % (time.time() - t0), flush=True)
    return pd.concat(out, ignore_index=True)


def analyze(df, kind, H, ch, rng, formal=True):
    """Igual a la versión original (mismas selecciones de controles, mismas permutaciones y mismo flujo de números aleatorios), sin los cuellos de botella:
    emparejamiento por índices (antes una máscara de texto sobre todos los controles POR ESTRATO) y orden aleatorio con una sola clave (argsort) en vez de lexsort."""
    d = df[(df.H == H) & ((df.kind == kind) | (df.kind == "CTRL"))].copy()
    d["stratum"] = d.contract + "|" + d.clock.astype(str) + "|" + d.voldec.astype(str) + "|" + d.rvdec.astype(str)
    ev = d[d.kind == kind]; ct = d[d.kind == "CTRL"]
    ev_idx = ev.groupby("stratum").indices; ct_idx = ct.groupby("stratum").indices      # posiciones, en el orden original de cada grupo
    ne_rows = len(ev); order = []
    for s_ in sorted(ev_idx):                                                           # mismo orden que ev.groupby("stratum")
        pool = ct_idx.get(s_)
        if pool is None or len(pool) == 0:
            continue
        ge = ev_idx[s_]
        k = min(len(pool), MAXCTRL * len(ge))
        seed = int(rng.integers(1 << 31))
        pick = pool[np.random.RandomState(seed).choice(len(pool), size=k, replace=False)]   # = pool.sample(k, random_state=seed) de pandas
        order.append(ge); order.append(ne_rows + pick)
    if not order:
        return None
    both = pd.concat([ev, ct], ignore_index=True)
    m = both.iloc[np.concatenate(order)].reset_index(drop=True)
    m["is_ev"] = (m.kind == kind).to_numpy()
    y = m[ch].to_numpy(); g = pd.factorize(m.stratum)[0]; ise = m.is_ev.to_numpy()
    ne = np.bincount(g, weights=ise).astype(int); nt = np.bincount(g); nc = nt - ne
    keepg = (ne > 0) & (nc > 0)

    def D(lab):
        se = np.bincount(g, weights=y * lab); st = np.bincount(g, weights=y)
        me = se[keepg] / ne[keepg]; mc = (st[keepg] - se[keepg]) / nc[keepg]
        return float(np.sum(ne[keepg] * (me - mc)) / ne[keepg].sum())
    obs = D(ise)
    res = dict(kind=kind, H=H, channel=ch, n_events=int(ne[keepg].sum()), n_controls=int(nc[keepg].sum()),
               n_strata=int(keepg.sum()), sessions=int(m[m.is_ev].session.nunique()), D=obs)
    st = np.bincount(g, weights=y); se = np.bincount(g, weights=y * ise)
    mc = np.where(nc > 0, (st - se) / np.maximum(nc, 1), np.nan)
    evd = m[m.is_ev].assign(dlt=y[ise] - mc[g[ise]]).dropna(subset=["dlt"])
    sess = evd.groupby("session").dlt.agg(["sum", "count"])
    bs = []
    for _ in range(NBOOT):
        s = sess.sample(len(sess), replace=True, random_state=int(rng.integers(1 << 31)))
        bs.append(s["sum"].sum() / s["count"].sum())
    res["ci95"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    if formal:
        order0 = np.argsort(g, kind="stable"); gs = g[order0]; start = np.r_[0, np.flatnonzero(np.diff(gs)) + 1]
        rank_in = np.arange(len(gs)) - np.repeat(start, np.diff(np.r_[start, len(gs)]))
        take = rank_in < ne[gs]
        gf = g.astype(np.float64)
        nul = np.empty(NPERM)
        for i in range(NPERM):
            u = rng.random(len(g))                                 # mismas 'len(g)' llamadas al generador que la versión original
            o = np.argsort(gf + u, kind="stable")                  # = np.lexsort((u, g)): por estrato y, dentro, por la clave aleatoria
            lab = np.zeros(len(g), bool)
            lab[o[take]] = True
            nul[i] = D(lab)
        res["p"] = float((1 + np.sum(nul >= obs)) / (1 + NPERM))
        res["null_sd"] = float(nul.std())
        res["mde"] = float((norm.ppf(1 - 0.05 / NTESTS) + 0.84) * nul.std())
    return res


def main():
    t0 = time.time()
    sess = ed.sessions("MNQ", DESDE, HASTA)
    print("sesiones aprobadas MNQ", len(sess), "contratos", sorted(sess.contract.unique()), flush=True)
    parts = []
    for c in sorted(sess.contract.unique(), key=lambda x: (x[-2:], x[-5:-3])):
        parts.append(process(c, sess))
        gc.collect()
    df = pd.concat(parts, ignore_index=True)
    df.to_parquet(OUT / "avcl_vol1_eventos_controles.parquet")
    rng = np.random.default_rng(SEED)
    formal, desc = [], []
    for kind in ("OFF", "AT"):
        for H in HS:
            for ch in ("y_rv", "y_rg"):
                r = analyze(df[df.rth], kind, H, ch, rng, True)
                if r: formal.append(r)
                r2 = analyze(df[~df.rth], kind, H, ch, rng, False)
                if r2: desc.append(dict(r2, sesion="ETH"))
                print(kind, H, ch, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in (r or {}).items()}, flush=True)
    ps = [r["p"] for r in formal]; order = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(order):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); formal[i]["p_holm"] = mx
    res = dict(campaign="AVCL-VOL-1 etapa 1", manifest="docs/research/AVCL_VOL1_MANIFIESTO_20261005.md", params=PARAMS,
               horizons=HS, seed=SEED, nperm=NPERM, nboot=NBOOT, n_tests=len(formal), desde=DESDE, hasta=HASTA,
               rth=formal, eth_descriptivo=desc, seconds=round(time.time() - t0))
    (OUT / "AVCL_VOL1_RESULTADOS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
