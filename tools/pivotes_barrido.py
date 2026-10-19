#!/usr/bin/env python3
r"""PIVOTES-BARRIDO-MES — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_PIVOTES_BARRIDO_MES_20260928.md

Censo de pivotes (zigzag R congelado del IPC-NIVEL), evento en la confirmación, carrera barre vs alejarse d, nulo por
evento, rasgos F1–F5, 12 pruebas BH.

    .venv\Scripts\python tools\pivotes_barrido.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import ipc_nivel_run as B  # noqa: E402
import ipc_nivel_regreso as RG  # noqa: E402
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

OUT = REPO / "artifacts" / "pivotes_barrido"
N_NULL = 1000


def rth(ts):
    """08:30–15:00 CT con CT = UTC−5 (CDT, ago–oct) o UTC−6 (CST): se usa la hora ET−1 aproximada por mes."""
    import datetime as dt
    d = dt.datetime.utcfromtimestamp(ts)
    off = 5 if 3 <= d.month <= 10 else 6
    m = (d.hour - off) % 24 * 60 + d.minute
    return 510 <= m < 900


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    fr = json.loads(B.FROZEN.read_text(encoding="utf-8"))["elegido"]; R, tol = fr["R"], fr["tol"]
    allses, times = {}, {}
    for m in B.MONTHS:
        mt = load_times(m)
        for k, v in RG.load_month(m).items():
            if k <= "20260331" and (k not in allses or len(v[2]) > len(allses[k][2])):
                allses[k] = v; times[k] = mt.get((v[0], k))
        print(m, len(allses), flush=True)
    rows, prev_trip = [], None
    for key in sorted(allses):
        asset, O, H, L, C, V = allses[key]; T = times[key]
        trip = np.column_stack([C - O, H - O, L - O]); n = len(C)
        piv = B.zigzag(H, L, R)
        zone_piv = {p for e in B.zone_events(piv, H, L, tol) for p in e["picos"]}
        for q, p in enumerate(piv):
            idx, kind, price, j = p
            if j >= n - 2:
                continue
            s = 1 if kind == "H" else -1
            d = s * (price - C[j])
            if d < 2:
                continue
            end = min(j + B.HZ, n - 1)
            target = price + s * B.SWEEP; away = C[j] - s * d
            res = B.race(H, L, j, target, away, s, end)
            pool = trip[:j]
            if len(pool) < 50 and prev_trip is not None:
                pool = np.vstack([prev_trip[-(200 - len(pool)):], pool])
            if len(pool) < 50:
                continue
            seed = int(hashlib.sha256(f"{key}|{idx}|{kind}".encode()).hexdigest()[:8], 16)
            p0 = simulate_null(C[j], target, away, s, pool, end - j, n=N_NULL, seed=seed, bars_per_step=1)["completa"]
            prev_opp = piv[q - 1][2] if q > 0 else np.nan
            rows.append(dict(session=key, kind=kind, res=res, p0=p0, zona=idx in zone_piv,
                             F1=float(abs(price - prev_opp)) if q > 0 else np.nan, F2=int(j - idx), F3=float(d),
                             F4=float(V[max(idx - 2, 0):idx + 3].sum() / (5 * max(float(np.median(V[:max(idx - 2, 20)])), 1.0))),
                             F5=bool(rth(T[idx])) if T is not None else None))
        prev_trip = trip
        if len(rows) and int(key) % 7 == 0:
            print(key, len(rows), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eventos.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    rng = np.random.default_rng(B.SEED); cells = []

    def boot(g1, g2, exc, ses):
        u = np.unique(ses); idx = {x: np.flatnonzero(ses == x) for x in u}; out = np.empty(B.N_BOOT)
        for bi in range(B.N_BOOT):
            a = np.concatenate([idx[x] for x in rng.choice(u, len(u))])
            out[bi] = exc[a][g1[a]].mean() - (exc[a][g2[a]].mean() if g2 is not None else 0.0)
        return out
    for kind in ("H", "L"):
        E = [r for r in rows if r["kind"] == kind]
        exc = np.array([(r["res"] == "barre") - r["p0"] for r in E]); ses = np.array([r["session"] for r in E])
        allm = np.ones(len(E), bool)
        tests = [("P0 global", allm, None)]
        for f in ("F1", "F2", "F3", "F4"):
            x = np.array([r[f] for r in E], float); q = np.nanquantile(x, [1 / 3, 2 / 3])
            tests.append((f"{f} alto-bajo", x > q[1], x <= q[0]))
        f5 = np.array([bool(r["F5"]) for r in E]); tests.append(("F5 RTH-ETH", f5, ~f5))
        for name, g1, g2 in tests:
            bs = boot(g1, g2, exc, ses)
            est = exc[g1].mean() - (exc[g2].mean() if g2 is not None else 0.0)
            p = float(min(1.0, 2 * min(np.mean(bs <= 0), np.mean(bs >= 0))))
            cells.append(dict(prueba=name, lado=kind, n1=int(g1.sum()), n2=int(g2.sum()) if g2 is not None else None, estimado=float(est),
                              ic90=[float(np.quantile(bs, .05)), float(np.quantile(bs, .95))], p_bilateral=p, mde80=2.8 * float(np.std(bs)),
                              exceso_g1=float(exc[g1].mean()), exceso_g2=float(exc[g2].mean()) if g2 is not None else None))
    ps = np.array([c["p_bilateral"] for c in cells]); o = np.argsort(ps); m = len(ps)
    okk = ps[o] <= 0.10 * np.arange(1, m + 1) / m; kmax = (np.max(np.flatnonzero(okk)) + 1) if okk.any() else 0
    surv = set(o[:kmax].tolist())
    for i, c in enumerate(cells):
        c["bh_q10"] = i in surv
    rep = dict(manifiesto="docs/research/MANIFIESTO_PIVOTES_BARRIDO_MES_20260928.md", code_commit=head, tree_dirty=dirty,
               sesiones=len(allses), pivotes=len(rows), en_zona=int(sum(r["zona"] for r in rows)), pruebas=cells,
               sobreviven=[f"{c['prueba']} {c['lado']}" for c in cells if c["bh_q10"]],
               barre_global={k: float(np.mean([r["res"] == "barre" for r in rows if r["kind"] == k])) for k in ("H", "L")},
               p0_global={k: float(np.mean([r["p0"] for r in rows if r["kind"] == k])) for k in ("H", "L")})
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "pruebas"}, indent=1, ensure_ascii=False))
    for c in cells:
        print(c["prueba"], c["lado"], c["n1"], c["n2"], round(c["estimado"], 3), [round(x, 3) for x in c["ic90"]], round(c["p_bilateral"], 4),
              round(c["exceso_g1"], 3), c["exceso_g2"] and round(c["exceso_g2"], 3))


def load_times(month):
    out = {}
    for c in B.CONTRACTS:
        f = B.VIEW / f"MES_{c}_{month}_25T_HFT.json"
        if not f.exists():
            continue
        b = json.loads(f.read_text(encoding="utf-8")); cd = b["bar_series"]["tick_25"]["candles"]; del b
        t = np.array([x["time"] for x in cd], float); del cd
        cuts = np.r_[0, np.flatnonzero(np.diff(t) > 1800) + 1, len(t)]
        for a0, b0 in zip(cuts[:-1], cuts[1:]):
            if b0 - a0 < 500:
                continue
            key = str(np.datetime64(int(t[a0] + 8 * 3600), "s").astype("datetime64[D]")).replace("-", "")
            out[(f"MES_{c}_{month}", key)] = t[a0:b0]
    return out


if __name__ == "__main__":
    main()
