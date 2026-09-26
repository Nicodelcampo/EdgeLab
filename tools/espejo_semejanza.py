#!/usr/bin/env python3
r"""ESPEJO-SIM: ¿la vuelta que se parece al impulso (velocidad y forma de las ondas) completa el espejo?

Pre-registro: docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_MNQ_20260926.md (commit fa7b3bc, antes de medir).
Descubrimiento fija las distribuciones de referencia y los terciles de S (`referencia.json`); la replicación las reusa.

    python tools/espejo_semejanza.py --parquet .../MNQ_09-25_ticks.parquet --contract "MNQ 09-25" --out DIR
    python tools/espejo_semejanza.py --parquet .../MNQ_12-25_ticks.parquet --contract "MNQ 12-25" \
        --referencia DIR/referencia.json --out DIR2
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

HOLDOUT_NS = 1_775_001_600_000_000_000     # 2026-04-01T00:00Z
MAXBARS, MINW, EFF, RETR = 20, 68, 0.6, 0.3
XS = (0.4, 0.5, 0.75)
HZ = 200
NPTS = 20
COMP = ("vel", "efi", "forma", "ondas")
NS = 1_000_000_000


def zigzag_count(y, thr):
    """Cantidad de giros de un camino con umbral `thr` (misma unidad que y)."""
    if len(y) < 2:
        return 0
    n = 0; dirn = 0; ext = y[0]
    for v in y[1:]:
        if dirn >= 0:
            if v > ext:
                ext = v
            elif ext - v >= thr:
                if dirn == 1:
                    n += 1
                dirn = -1; ext = v
            if dirn == 0 and v - y[0] >= thr:
                dirn = 1
        else:
            if v < ext:
                ext = v
            elif v - ext >= thr:
                n += 1; dirn = 1; ext = v
    return n


def _norm_path(y):
    u = np.linspace(0, 1, len(y))
    return np.interp(np.linspace(0, 1, NPTS), u, y)


def eventos(t, H, L, C, imp):
    """Un evento por impulso y por x. Devuelve dicts con semejanza, f alcanzado y desenlace."""
    out = []
    n = len(C)
    for row in imp:
        d, a, ext, i0, iext, iend = int(row[0]), row[1], row[2], int(row[3]), int(row[4]), int(row[5])
        W = abs(ext - a)
        if W <= 0:
            continue
        prog = d * (C[i0:iext + 1] - a) / W                     # avance del impulso por vela (0 → 1)
        done = set()
        for k in range(iext + 1, n):
            if (d == 1 and H[k] > ext) or (d == -1 and L[k] < ext):
                break                                           # extremo nuevo: no hay espejo que medir
            retr = (ext - L[k]) if d == 1 else (H[k] - ext)
            f = min(retr / W, 1.0)
            for x in XS:
                if x in done or f < x:
                    continue
                done.add(x)
                # tramo espejo: última vela del impulso con avance <= 1 - f, hasta el extremo
                idx = np.where(prog <= 1 - f)[0]
                m = i0 + (int(idx[-1]) if len(idx) else 0)
                seg_m = C[m:iext + 1][::-1]; seg_v = C[iext:k + 1]
                dt_m = max(t[iext] - t[m], 1.0); dt_v = max(t[k] - t[iext], 1.0)
                vel = -abs(math.log((f * W / dt_v) / (max(abs(ext - C[m]), 1.0) / dt_m)))
                def efi(s):
                    p = np.abs(np.diff(s)).sum()
                    return abs(s[-1] - s[0]) / p if p > 0 else 1.0
                ym = d * (ext - seg_m) / (f * W); yv = d * (ext - seg_v) / (f * W)
                forma = -float(np.sqrt(np.mean((_norm_path(ym) - _norm_path(yv)) ** 2))) if len(ym) > 1 and len(yv) > 1 else float("nan")
                ondas = -abs(zigzag_count(yv, 0.1 / f) / f - zigzag_count(ym, 0.1 / f) / f)
                # desenlace
                res = 0
                for q in range(k + 1, min(n, k + 1 + HZ)):
                    if (d == 1 and H[q] > ext) or (d == -1 and L[q] < ext):
                        res = 2; break
                    if (d == 1 and ext - L[q] >= W) or (d == -1 and H[q] - ext >= W):
                        res = 1; break
                if f >= 1.0:
                    res = 1
                over = 0.0
                if res == 1:
                    q1 = min(n, k + 1 + HZ)
                    far = (ext - L[k:q1].min()) if d == 1 else (H[k:q1].max() - ext)
                    over = far / W - 1.0
                fc = min(max(((ext - C[k]) if d == 1 else (C[k] - ext)) / W, 0.0), 1.0)
                out.append(dict(x=x, f=f, f_cierre=fc, res=res, vel=vel, efi=-abs(efi(seg_v) - efi(seg_m)), forma=forma,
                                ondas=ondas, W=W, sobrepaso_W=over, velas=k - iext))
            if len(done) == len(XS):
                break
    return out


def collect(parquet, instrument, contract, max_sessions=None):
    import pyarrow.parquet as pq
    from edgelab.bridge.bars import build_tick_bars
    from edgelab.bridge.ticks import load_canonical_parquet
    from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd
    from tbzx_espejo import detect

    ts_all = pq.read_table(parquet, columns=["ts_utc_ns"])["ts_utc_ns"].to_numpy()
    ts_all = ts_all[ts_all < HOLDOUT_NS]
    tds = trade_date_ymd(ts_all); ok = ~is_maintenance_break(ts_all)
    rows = []
    for n, td in enumerate(sorted(np.unique(tds[ok]))):
        if max_sessions and n >= max_sessions:
            break
        m = np.where((tds == td) & ok)[0]
        if len(m) < 5000:
            continue
        tk = load_canonical_parquet(parquet, contract=contract, instrument=instrument,
                                    start_utc_ns=int(ts_all[m[0]]), end_utc_ns=int(ts_all[m[-1]]) + 1)
        b = build_tick_bars(tk, 25, reiniciar_por_sesion=True)
        t = (b.end_ns / NS).astype(np.float64)
        Hh, Ll, Cc = b.high_t.astype(np.float64), b.low_t.astype(np.float64), b.close_t.astype(np.float64)
        imp = detect(t, Hh, Ll, Cc, b.volume.astype(np.float64), MAXBARS, MINW, EFF, RETR)
        ev = eventos(t, Hh, Ll, Cc, imp)
        for e in ev:
            e["sesion"] = int(td)
        rows += ev
        print(f"{td}: {len(imp)} impulsos, {len(ev)} eventos", flush=True)
    return rows


def referencia(rows):
    ref = {}
    for c in COMP:
        v = np.array([r[c] for r in rows if r[c] == r[c]])
        ref[c] = np.percentile(v, np.linspace(0, 100, 101)).tolist()
    return ref


def _pct(ref, v):
    """Rango percentil con empates al medio (medidas como `ondas` tienen muchos valores iguales)."""
    return float((np.searchsorted(ref, v, "left") + np.searchsorted(ref, v, "right")) / 2 / 101)


def score(rows, ref):
    for r in rows:
        ps = [_pct(ref[c], r[c]) for c in COMP if r[c] == r[c]]
        r["S"] = float(np.mean(ps)) if ps else float("nan")
        for c in COMP:
            r[f"p_{c}"] = _pct(ref[c], r[c]) if r[c] == r[c] else float("nan")


def boot(rows_a, rows_b=None, n=1000, seed=20260926, fk="f"):
    """Exceso medio (espejo − f); con rows_b, diferencia de excesos. Bootstrap por sesión."""
    rng = np.random.default_rng(seed)

    def agg(rows):
        d = {}
        for r in rows:
            s = d.setdefault(r["sesion"], [0.0, 0])
            s[0] += (r["res"] == 1) - r[fk]; s[1] += 1
        return d
    A = agg(rows_a); B = agg(rows_b) if rows_b is not None else {}
    ses = sorted(set(A) | set(B))
    if not A or (rows_b is not None and not B):
        return (float("nan"),) * 3 + (1.0,)
    a = np.array([A.get(s, [0, 0]) for s in ses], float); b = np.array([B.get(s, [0, 0]) for s in ses], float)
    idx = rng.integers(0, len(ses), (n, len(ses)))
    ea = a[idx, 0].sum(1) / np.maximum(a[idx, 1].sum(1), 1)
    pt = a[:, 0].sum() / max(a[:, 1].sum(), 1)
    if rows_b is not None:
        ea = ea - b[idx, 0].sum(1) / np.maximum(b[idx, 1].sum(1), 1)
        pt -= b[:, 0].sum() / max(b[:, 1].sum(), 1)
    lo, hi = np.percentile(ea, [2.5, 97.5])
    se = ea.std()
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(pt / se) / math.sqrt(2)))) if se > 0 else 1.0
    return float(pt), float(lo), float(hi), float(p)


def bh(ps, q=0.10):
    p = np.asarray(ps); o = np.argsort(p); n = len(p); ok = np.zeros(n, bool)
    hit = np.where(p[o] <= q * np.arange(1, n + 1) / n)[0]
    if len(hit):
        ok[o[: hit.max() + 1]] = True
    return ok


def analizar(rows, ref, cortes_S):
    score(rows, ref)
    res = [r for r in rows if r["res"] in (1, 2)]
    tests = []
    for x in XS:
        rx = [r for r in res if r["x"] == x]
        base = dict(x=x, n=len(rx), espejo=float(np.mean([r["res"] == 1 for r in rx])) if rx else float("nan"),
                    f_medio=float(np.mean([r["f"] for r in rx])) if rx else float("nan"))
        tests.append(dict(base, prueba="todos: exceso vs f", est=boot(rx)))
        base_c = dict(base, f_medio=float(np.mean([r["f_cierre"] for r in rx])) if rx else float("nan"))
        tests.append(dict(base_c, prueba="todos: exceso vs f al cierre (enmienda 1)", est=boot(rx, fk="f_cierre")))
        for var, lims in [("S", cortes_S)] + [(f"p_{c}", [1 / 3, 2 / 3]) for c in COMP]:
            lo = [r for r in rx if r[var] == r[var] and r[var] <= lims[0]]
            hi = [r for r in rx if r[var] == r[var] and r[var] > lims[1]]
            tipo = "principal" if var == "S" else "secundaria"
            tests.append(dict(base, prueba=f"{var} T3 − T1 ({tipo})", n_T3=len(hi), n_T1=len(lo),
                              espejo_T3=float(np.mean([r["res"] == 1 for r in hi])) if hi else float("nan"),
                              espejo_T1=float(np.mean([r["res"] == 1 for r in lo])) if lo else float("nan"),
                              est=boot(hi, lo)))
            tests.append(dict(base, prueba=f"{var} T3: exceso vs f", n_T3=len(hi), est=boot(hi)))
            if var == "S":
                tests.append(dict(base_c, prueba="S T3: exceso vs f al cierre (enmienda 1)", n_T3=len(hi),
                                  est=boot(hi, fk="f_cierre")))
    ok = bh([t["est"][3] for t in tests])
    for t, o in zip(tests, ok):
        t["fdr"] = bool(o)
    return tests


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True); ap.add_argument("--instrument", default="MNQ")
    ap.add_argument("--contract", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--referencia"); ap.add_argument("--max-sessions", type=int)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cache = out / "eventos.json"
    if cache.exists():
        rows = json.loads(cache.read_text())
    else:
        rows = collect(a.parquet, a.instrument, a.contract, a.max_sessions)
        cache.write_text(json.dumps(rows))
    if a.referencia:
        R = json.loads(Path(a.referencia).read_text()); ref, cS = R["ref"], R["cortes_S"]
    else:
        ref = referencia(rows); score(rows, ref)
        s = np.array([r["S"] for r in rows if r["S"] == r["S"]])
        cS = [float(np.percentile(s, 33.333)), float(np.percentile(s, 66.667))]
    tests = analizar(rows, ref, cS)
    (out / "referencia.json").write_text(json.dumps(dict(ref=ref, cortes_S=cS)))
    cens = sum(r["res"] == 0 for r in rows)
    (out / "reporte.json").write_text(json.dumps(dict(contrato=a.contract, eventos=len(rows), censurados=cens,
                                                      pruebas=tests), indent=1, ensure_ascii=False))
    L = [f"# ESPEJO-SIM — {a.contract} ({len(rows)} eventos, {cens} censurados)", "",
         "| x | prueba | n | espejo | f medio | estimación [IC 95 %] | FDR |", "|---|---|---|---|---|---|---|"]
    for t in tests:
        e = t["est"]
        extra = f" (T3 {t['espejo_T3']:.3f} / T1 {t['espejo_T1']:.3f})" if "espejo_T3" in t else ""
        L.append(f"| {t['x']} | {t['prueba']}{extra} | {t.get('n_T3', t['n'])} | {t['espejo']:.3f} | {t['f_medio']:.3f} | "
                 f"{100 * e[0]:+.1f} pp [{100 * e[1]:+.1f}, {100 * e[2]:+.1f}] | {'sí' if t['fdr'] else ''} |")
    (out / "reporte.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
