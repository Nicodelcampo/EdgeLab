#!/usr/bin/env python3
r"""ESPEJO-MACRO: el espejo de impulsos grandes en velas de tiempo (5 y 15 min), SPY descubre y ES replica.

Pre-registro: docs/research/MANIFIESTO_ESPEJO_MACRO_ES_20260926.md (commit 9b22743; OK de Nico 2026-09-26).

    python tools/espejo_macro.py spy --csv spy_1min_2008_2021_cleaned.csv --out DIR/SPY
    python tools/espejo_macro.py es --parquet ES_09-25_ticks.parquet ES_12-25_ticks.parquet ES_03-26_ticks.parquet \
        --referencia DIR/SPY/referencia.json --out DIR/ES_RTH
    python tools/espejo_macro.py e2 --es DIR/ES_RTH --spy DIR/SPY --out DIR/E2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))
import espejo_semejanza as ES  # noqa: E402

HOLDOUT_NS = 1_775_001_600_000_000_000                       # 2026-04-01: ni confirmación ni holdout
ES_LO_NS = int(pd.Timestamp("2025-07-01", tz="UTC").value)
EFF, RETR = 0.6, 0.3
GRID = {5: [(mb, k) for mb in (12, 24, 48) for k in (3, 4, 6)],
        15: [(mb, k) for mb in (4, 8, 16) for k in (3, 4, 6)]}
COST_T, COST_T_ALT, SLIP_T = 2.4, 1.5, 1.0


# ------------------------------------------------------------------ detector con ancho mínimo por vela
@njit(cache=True)
def detect_var(t, H, L, C, W, thr_arr, e0, r):
    """`tools/tbzx_espejo.py::detect` sin cambios salvo el umbral: `thr_arr[j]` en vez de `minW` fijo. El umbral de
    aceptación final es el vigente en la vela que disparó el impulso."""
    n = len(C)
    path = np.zeros(n)
    for i in range(1, n):
        path[i] = path[i - 1] + abs(C[i] - C[i - 1])
    out = np.zeros((n // 2 + 1, 9))
    m = 0
    active = False
    floorI = 0
    d = 0; i0 = 0; a = 0.0; ext = 0.0; iext = 0; itrig = 0; vol = 0.0; thr_t = 0.0
    for j in range(W, n):
        if t[j] - t[j - 1] > 1800:
            active = False
        if not active:
            w0 = max(j - W, floorI)
            if w0 >= j:
                continue
            thr = max(thr_arr[j], 2.0)
            if not thr < 1e17:
                continue
            ia = w0; ib = w0
            for q in range(w0, j + 1):
                if L[q] < L[ia]:
                    ia = q
                if H[q] > H[ib]:
                    ib = q
            found = False; bnet = 0.0
            if ia < j:
                net = C[j] - L[ia]; pp = path[j] - path[ia]
                if net >= thr and pp > 0 and (C[j] - C[ia]) / pp >= e0:
                    found = True; bnet = net; d = 1; i0 = ia; a = L[ia]; ext = H[j]
            if ib < j:
                net2 = H[ib] - C[j]; pp2 = path[j] - path[ib]
                if net2 >= thr and pp2 > 0 and (C[ib] - C[j]) / pp2 >= e0 and ((not found) or net2 > bnet):
                    found = True; d = -1; i0 = ib; a = H[ib]; ext = L[j]
            if found:
                active = True; iext = j; itrig = j; vol = 0.0; thr_t = thr
            continue
        if d == 1 and H[j] > ext:
            ext = H[j]; iext = j
        elif d == -1 and L[j] < ext:
            ext = L[j]; iext = j
        tot = abs(ext - a)
        retr = (ext - L[j]) if d == 1 else (H[j] - ext)
        why = 0
        if retr >= max(2.0, r * tot):
            why = 1
        elif j - i0 >= W:
            why = 2
        if why == 0:
            continue
        if tot >= thr_t:
            out[m, 0] = d; out[m, 1] = a; out[m, 2] = ext; out[m, 3] = i0; out[m, 4] = iext; out[m, 5] = j
            out[m, 6] = itrig; out[m, 7] = vol; out[m, 8] = why
            m += 1
        floorI = iext
        active = False
    return out[:m]


def atr_prev(H, L, C, n=14):
    """ATR(n) simple, cerrado en la vela ANTERIOR (causal). Serie continua entre días; inf hasta tener n velas."""
    pc = np.r_[C[0], C[:-1]]
    tr = np.maximum(H - L, np.maximum(np.abs(H - pc), np.abs(L - pc)))
    cs = np.r_[0.0, np.cumsum(tr)]
    out = np.full(len(C), np.inf)
    for j in range(n + 1, len(C)):
        out[j] = (cs[j] - cs[j - n]) / n
    return out


# ------------------------------------------------------------------ velas RTH
def rth_bars(ts_ns, price_ticks, minutes, volume=None):
    """Velas de `minutes` min en RTH 9:30–16:00 ET, por día. Devuelve DataFrame con day, t (s de fin), O H L C V."""
    et = pd.to_datetime(ts_ns, utc=True).tz_convert("America/New_York")
    mins = et.hour * 60 + et.minute
    keep = (mins >= 570) & (mins < 960)
    df = pd.DataFrame(dict(day=et.date, b=(mins - 570) // minutes, p=price_ticks,
                           v=volume if volume is not None else np.ones(len(price_ticks)), ts=ts_ns))[keep]
    g = df.groupby(["day", "b"], sort=True)
    out = g.agg(O=("p", "first"), H=("p", "max"), L=("p", "min"), C=("p", "last"), V=("v", "sum"), ts=("ts", "last"))
    out = out.reset_index()
    out["t"] = out.ts / 1e9
    return out


def spy_bars(csv, minutes):
    """SPY 1 min (tercero) → velas RTH. Deduplica filas idénticas; aborta si hay minutos repetidos distintos."""
    m = pd.read_csv(csv)
    m.columns = [c.lower() for c in m.columns]
    tcol = "date" if "date" in m.columns else m.columns[0]
    n0 = len(m); m = m.drop_duplicates(); dups = n0 - len(m)
    if m[tcol].duplicated().any():
        raise ValueError("minutos repetidos con valores distintos: no se deduplica a ciegas")
    ts = pd.to_datetime(m[tcol])
    # el archivo está en hora de montaña (7:30 = apertura 9:30 ET; ver tools/ivc_largo.py y el volumen de 07:30)
    ts = ts.dt.tz_localize("America/Denver", ambiguous="NaT", nonexistent="NaT")
    ok = ts.notna().to_numpy(); m = m[ok]; ts = ts[ok].dt.tz_convert("UTC")
    # la vela de 1 min se identifica por su inicio; se usa el cierre del minuto como marca
    ts_ns = ts.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy().astype("datetime64[ns]").astype(np.int64) \
        + 60 * 1_000_000_000 - 1
    rows = []
    for col in ("open", "high", "low", "close"):
        rows.append(np.round(m[col].to_numpy() * 100).astype(np.int64))
    o, h, l, c = rows
    et = pd.to_datetime(ts_ns - 60 * 1_000_000_000 + 1, utc=True).tz_convert("America/New_York")
    mins = et.hour * 60 + et.minute
    keep = (mins >= 570) & (mins < 960)
    df = pd.DataFrame(dict(day=et.date, b=(mins - 570) // minutes, O=o, H=h, L=l, C=c, ts=ts_ns))[keep]
    g = df.groupby(["day", "b"], sort=True)
    out = g.agg(O=("O", "first"), H=("H", "max"), L=("L", "min"), C=("C", "last"), ts=("ts", "last")).reset_index()
    out["t"] = out.ts / 1e9
    return out, dups


def es_bars(parquets, minutes):
    """Velas RTH de ES, un contrato por vez (memoria). Por día se queda el contrato de más volumen RTH (el frente),
    para no mezclar precios de dos vencimientos."""
    import pyarrow.parquet as pq
    allb = []
    for i, p in enumerate(parquets):
        tb = pq.read_table(p, columns=["ts_utc_ns", "price_ticks", "volume"])
        ts = tb["ts_utc_ns"].to_numpy(); k = (ts >= ES_LO_NS) & (ts < HOLDOUT_NS)
        b = rth_bars(ts[k], tb["price_ticks"].to_numpy()[k], minutes, tb["volume"].to_numpy()[k])
        b["contrato"] = i
        allb.append(b); del tb, ts
    b = pd.concat(allb, ignore_index=True)
    vol = b.groupby(["day", "contrato"]).V.sum().reset_index().sort_values("V").groupby("day").tail(1)
    b = b.merge(vol[["day", "contrato"]], on=["day", "contrato"])
    return b.sort_values(["day", "b"]).reset_index(drop=True)


# ------------------------------------------------------------------ eventos
def run_grid(bars, minutes, tick_size_label):
    H = bars.H.to_numpy(np.float64); L = bars.L.to_numpy(np.float64); C = bars.C.to_numpy(np.float64)
    t = bars.t.to_numpy(np.float64); atr = atr_prev(H, L, C)
    days = bars.day.to_numpy()
    cuts = np.r_[0, np.where(days[1:] != days[:-1])[0] + 1, len(days)]
    data = {}
    for mb, k in GRID[minutes]:
        rows = []
        for a, b in zip(cuts[:-1], cuts[1:]):
            if b - a <= mb:
                continue
            imp = detect_var(t[a:b], H[a:b], L[a:b], C[a:b], mb, k * atr[a:b], EFF, RETR)
            for e in ES.eventos(t[a:b], H[a:b], L[a:b], C[a:b], imp):
                e["sesion"] = str(days[a]); rows.append(e)
        data[f"{minutes}m_{mb}_{k}"] = rows
        print(f"{tick_size_label} {minutes}m maxBars={mb} k={k}: {len(rows)} eventos", flush=True)
    return data


def analyze(data, refs_in=None):
    todas, refs = [], {}
    for key, rows in data.items():
        if not rows:
            continue
        if refs_in and key in refs_in:
            ref, cS = refs_in[key]["ref"], refs_in[key]["cortes_S"]
        else:
            ref = ES.referencia(rows); ES.score(rows, ref)
            s = np.array([r["S"] for r in rows if r["S"] == r["S"]])
            cS = [float(np.percentile(s, 33.333)), float(np.percentile(s, 66.667))]
        refs[key] = dict(ref=ref, cortes_S=cS)
        for t_ in ES.analizar(rows, ref, cS):
            t_.update(config=key, eventos=len(rows))
            todas.append(t_)
    ok = ES.bh([t_["est"][3] for t_ in todas])
    for t_, o in zip(todas, ok):
        t_["fdr"] = bool(o)
    return todas, refs


def write(out, name, todas, refs, meta, data):
    out.mkdir(parents=True, exist_ok=True)
    (out / "referencia.json").write_text(json.dumps(refs))
    (out / "eventos.json").write_text(json.dumps(data))
    (out / "reporte.json").write_text(json.dumps(dict(meta, pruebas=todas), indent=1, ensure_ascii=False))
    L = [f"# ESPEJO-MACRO — {name}", "", "```", json.dumps(meta, ensure_ascii=False), "```", "",
         "| config | eventos | x | prueba | n | estimación [IC 95 %] | FDR |", "|---|---|---|---|---|---|---|"]
    for t_ in todas:
        e = t_["est"]
        L.append(f"| {t_['config']} | {t_['eventos']} | {t_['x']} | {t_['prueba']} | {t_.get('n_T3', t_['n'])} | "
                 f"{100 * e[0]:+.1f} pp [{100 * e[1]:+.1f}, {100 * e[2]:+.1f}] | {'sí' if t_['fdr'] else ''} |")
    (out / "reporte.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(todas)} pruebas, {sum(t_['fdr'] for t_ in todas)} pasan FDR")


def sostenidos(spy_rep, es_rep):
    """E1 sostenido (manifiesto §6): la prueba principal pasa FDR en SPY y en ES tiene el mismo signo con IC > 0.
    Regla de lectura (enmienda 1): n >= 30 por tercil en los dos."""
    key = lambda t: (t["config"], t["x"], t["prueba"])
    es = {key(t): t for t in es_rep["pruebas"]}
    out = []
    for t in spy_rep["pruebas"]:
        if not t["prueba"].startswith("S T3 − T1") or not t["fdr"] or t.get("n_T3", 0) < 30:
            continue
        e = es.get(key(t))
        if e is None or e.get("n_T3", 0) < 30:
            continue
        if np.sign(e["est"][0]) == np.sign(t["est"][0]) and e["est"][1] > 0:
            out.append((t["config"], t["x"]))
    return out


def ganancia(rows, cost, slip=SLIP_T):
    """G por evento en ticks (manifiesto §5): entrada al cierre de la vela del evento, objetivo A, stop B."""
    g = []
    for r in rows:
        if r["res"] not in (1, 2):
            continue
        f = r["f_cierre"]; W = r["W"]
        g.append(((1 - f) * W if r["res"] == 1 else -f * W - slip) - cost)
    return np.array(g)


def e2(es_dir, spy_dir, out):
    spy_rep = json.loads((Path(spy_dir) / "reporte.json").read_text())
    es_rep = json.loads((Path(es_dir) / "reporte.json").read_text())
    data = json.loads((Path(es_dir) / "eventos.json").read_text())
    refs = json.loads((Path(spy_dir) / "referencia.json").read_text())
    filas = []
    for cfg, x in sostenidos(spy_rep, es_rep):
        rows = data[cfg]; ES.score(rows, refs[cfg]["ref"])
        hi = [r for r in rows if r["x"] == x and r["S"] == r["S"] and r["S"] > refs[cfg]["cortes_S"][1]]
        rng = np.random.default_rng(20260926)
        for cost in (COST_T, COST_T_ALT):
            ses = sorted({r["sesion"] for r in hi})
            por = {s: ganancia([r for r in hi if r["sesion"] == s], cost) for s in ses}
            tot = np.concatenate(list(por.values())) if por else np.array([])
            bs = []
            for _ in range(1000):
                smp = rng.choice(len(ses), len(ses))
                v = np.concatenate([por[ses[i]] for i in smp])
                bs.append(v.mean() if len(v) else np.nan)
            filas.append(dict(config=cfg, x=x, costo_t=cost, n=int(len(tot)), G_medio_t=float(tot.mean()),
                              ic=[float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))],
                              W_medio_t=float(np.mean([r["W"] for r in hi])),
                              candidato=bool(np.nanpercentile(bs, 2.5) > 0)))
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out / "e2.json").write_text(json.dumps(dict(sostenidos=sostenidos(spy_rep, es_rep), filas=filas), indent=1))
    print(json.dumps(dict(sostenidos=sostenidos(spy_rep, es_rep), filas=filas), indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("spy"); s1.add_argument("--csv", required=True); s1.add_argument("--out", required=True)
    s2 = sub.add_parser("es"); s2.add_argument("--parquet", nargs="+", required=True)
    s2.add_argument("--referencia", required=True); s2.add_argument("--out", required=True)
    s3 = sub.add_parser("e2"); s3.add_argument("--es", required=True); s3.add_argument("--spy", required=True)
    s3.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "e2":
        return e2(a.es, a.spy, a.out)
    if a.cmd == "spy":
        data, dups = {}, 0
        for mn in (5, 15):
            bars, dups = spy_bars(a.csv, mn)
            data.update(run_grid(bars, mn, "SPY"))
        sha = hashlib.sha256(Path(a.csv).read_bytes()).hexdigest()
        todas, refs = analyze(data)
        meta = dict(fuente="SPY 1 min RTH 2008-2021", sha256=sha, filas_duplicadas_eliminadas=dups,
                    dias=int(bars.day.nunique()))
        write(Path(a.out), "SPY (descubrimiento)", todas, refs, meta, data)
    elif a.cmd == "es":
        refs_in = json.loads(Path(a.referencia).read_text())
        data = {}
        for mn in (5, 15):
            bars = es_bars(a.parquet, mn)
            data.update(run_grid(bars, mn, "ES"))
        todas, refs = analyze(data, refs_in)
        meta = dict(fuente="ES RTH 2025-07-01..2026-03-31", parquets=[Path(p).name for p in a.parquet],
                    dias=int(bars.day.nunique()))
        write(Path(a.out), "ES RTH (replicación)", todas, refs, meta, data)


if __name__ == "__main__":
    main()
