#!/usr/bin/env python3
r"""IPC-NIVEL-REGRESO (MES) — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_IPC_NIVEL_REGRESO_VIRGEN_MES_20260928.md

Primer regreso a un nivel virgen tras alejarse ≥ 14 t; rasgos D (distancia máx.) y V (volumen relativo) en terciles;
36 pruebas (lado × 9 celdas × {zona − p0, zona − control}), BH q = 0,10, bootstrap por sesión.

    .venv\Scripts\python tools\ipc_nivel_regreso.py
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
from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

OUT = REPO / "artifacts" / "ipc_nivel_regreso"
AWAY, TOUCH, SWEEP, HZ = 14, 2, 2, 200


def load_month(month):
    best = {}
    for c in B.CONTRACTS:
        f = B.VIEW / f"MES_{c}_{month}_25T_HFT.json"
        if not f.exists():
            continue
        b = json.loads(f.read_text(encoding="utf-8")); tick = float(b["meta"]["tick_size"])
        cd = b["bar_series"]["tick_25"]["candles"]; del b
        t = np.array([x["time"] for x in cd], float)
        O, H, L, C = (np.round(np.array([x[k] for x in cd]) / tick) for k in ("open", "high", "low", "close"))
        V = np.array([x["volume"] for x in cd], float); del cd
        cuts = np.r_[0, np.flatnonzero(np.diff(t) > 1800) + 1, len(t)]
        for a0, b0 in zip(cuts[:-1], cuts[1:]):
            if b0 - a0 < 500:
                continue
            key = str(np.datetime64(int(t[a0] + 8 * 3600), "s").astype("datetime64[D]")).replace("-", "")
            if key not in best or (b0 - a0) > len(best[key][2]):
                best[key] = (f"MES_{c}_{month}", O[a0:b0], H[a0:b0], L[a0:b0], C[a0:b0], V[a0:b0])
    return best


def regreso(ref, j0, kind, H, L, V, vmed):
    """(k, D, Vrel, velas_afuera, barre_en_la_vela) del primer regreso virgen, o None."""
    s = 1 if kind == "H" else -1; D = 0.0
    for k in range(j0 + 1, len(H)):
        far = (ref - L[k]) if s == 1 else (H[k] - ref)
        near = (ref - H[k]) if s == 1 else (L[k] - ref)          # distancia del extremo de la vela al ref (≥ 0 si no llegó)
        if D < AWAY:
            if near <= 0:
                return None                                       # tocó el ref antes de alejarse: no es un regreso
            D = max(D, far)
            continue
        if near <= TOUCH:
            swept = (H[k] >= ref + SWEEP) if s == 1 else (L[k] <= ref - SWEEP)
            return k, D, float(V[j0 + 1:k + 1].sum() / vmed), k - j0, bool(swept)
        D = max(D, far)
    return None


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    fr = json.loads(B.FROZEN.read_text(encoding="utf-8"))["elegido"]; R, tol = fr["R"], fr["tol"]
    allses = {}
    for m in B.MONTHS:
        for k, v in load_month(m).items():
            if k <= "20260331" and (k not in allses or len(v[2]) > len(allses[k][2])):
                allses[k] = v
    rows, prev_trip, en_vela = [], None, {"zona": 0, "control": 0}
    for key in sorted(allses):
        asset, O, H, L, C, V = allses[key]
        trip = np.column_stack([C - O, H - O, L - O]); n = len(C)
        piv = B.zigzag(H, L, R)
        evs = B.zone_events(piv, H, L, tol)
        zone_piv = {p for e in evs for p in e["picos"]}
        items = [("zona", e["kind"], e["ref"], e["bar"]) for e in evs]
        items += [("control", p[1], p[2], p[3]) for p in piv if p[0] not in zone_piv]
        for grupo, kind, ref, j0 in items:
            vmed = float(np.median(V[:j0])) if j0 >= 20 else float(np.median(V))
            r = regreso(ref, j0, kind, H, L, V, max(vmed, 1.0))
            if r is None:
                continue
            k, D, Vr, afuera, swept = r
            if swept:
                en_vela[grupo] += 1                               # barre en la misma vela del regreso: sin cierre previo
                continue
            s = 1 if kind == "H" else -1
            end = min(k + HZ, n - 1)
            if end <= k:
                continue
            target = ref + s * SWEEP; away = ref - s * AWAY
            res = B.race(H, L, k, target, away, s, end)
            pool = trip[:k]
            if len(pool) < 50 and prev_trip is not None:
                pool = np.vstack([prev_trip[-(200 - len(pool)):], pool])
            if len(pool) < 50:
                continue
            seed = int(hashlib.sha256(f"{key}|{k}|{grupo}|{ref}".encode()).hexdigest()[:8], 16)
            p0 = simulate_null(C[k], target, away, s, pool, end - k, n=B.N_NULL, seed=seed, bars_per_step=1)
            rows.append(dict(session=key, grupo=grupo, kind=kind, bar=int(k), D=float(D), V=Vr, afuera=int(afuera), res=res, p0=p0["completa"]))
        prev_trip = trip
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eventos.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    Z = [r for r in rows if r["grupo"] == "zona"]
    qD = np.quantile([r["D"] for r in Z], [1 / 3, 2 / 3]); qV = np.quantile([r["V"] for r in Z], [1 / 3, 2 / 3])
    ter = lambda x, q: 0 if x <= q[0] else (2 if x > q[1] else 1)
    for r in rows:
        r["tD"] = ter(r["D"], qD); r["tV"] = ter(r["V"], qV)
    NAMES = ("bajo", "medio", "alto")
    rng = np.random.default_rng(B.SEED); cells = []
    for kind in ("H", "L"):
        for tD in range(3):
            for tV in range(3):
                z = [r for r in rows if r["grupo"] == "zona" and r["kind"] == kind and r["tD"] == tD and r["tV"] == tV]
                c = [r for r in rows if r["grupo"] == "control" and r["kind"] == kind and r["tD"] == tD and r["tV"] == tV]
                ez = np.array([(r["res"] == "barre") - r["p0"] for r in z]); sz = np.array([r["session"] for r in z])
                ec = np.array([(r["res"] == "barre") - r["p0"] for r in c]); sc = np.array([r["session"] for r in c])
                u = np.unique(np.r_[sz, sc]); iz = {x: np.flatnonzero(sz == x) for x in u}; ic = {x: np.flatnonzero(sc == x) for x in u}
                b1 = np.full(B.N_BOOT, np.nan); b2 = np.full(B.N_BOOT, np.nan)
                if len(u):
                    for bi in range(B.N_BOOT):
                        pick = rng.choice(u, len(u))
                        a = np.concatenate([iz[x] for x in pick]); cc = np.concatenate([ic[x] for x in pick])
                        mz = ez[a].mean() if len(a) else np.nan
                        b1[bi] = mz; b2[bi] = mz - (ec[cc].mean() if len(cc) else np.nan)
                for name, est, bs in (("P1", ez.mean() if len(ez) else np.nan, b1),
                                      ("P2", (ez.mean() - ec.mean()) if len(ez) and len(ec) else np.nan, b2)):
                    ok = ~np.isnan(bs)
                    p = float(min(1.0, 2 * min(np.mean(bs[ok] <= 0), np.mean(bs[ok] >= 0)))) if ok.sum() > 50 else 1.0
                    cells.append(dict(prueba=name, lado=kind, distancia=NAMES[tD], volumen=NAMES[tV], n_zona=len(z), n_control=len(c),
                                      estimado=float(est), ic90=[float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))] if ok.any() else None,
                                      p_bilateral=p, mde80=2.8 * float(np.nanstd(bs)) if ok.any() else None,
                                      barre_zona=float(np.mean([r["res"] == "barre" for r in z])) if z else None,
                                      p0_zona=float(np.mean([r["p0"] for r in z])) if z else None,
                                      barre_control=float(np.mean([r["res"] == "barre" for r in c])) if c else None))
    ps = np.array([c["p_bilateral"] for c in cells]); o = np.argsort(ps); m = len(ps)
    okk = ps[o] <= 0.10 * np.arange(1, m + 1) / m; kmax = (np.max(np.flatnonzero(okk)) + 1) if okk.any() else 0
    surv = set(o[:kmax].tolist())
    for i, c in enumerate(cells):
        c["bh_q10"] = i in surv
    rep = dict(manifiesto="docs/research/MANIFIESTO_IPC_NIVEL_REGRESO_VIRGEN_MES_20260928.md", code_commit=head, tree_dirty=dirty,
               sesiones=len(allses), eventos_zona=len(Z), eventos_control=sum(r["grupo"] == "control" for r in rows),
               barre_en_la_vela_del_regreso=en_vela, cortes_D=qD.tolist(), cortes_V=qV.tolist(), pruebas=cells,
               sobreviven=[f"{c['prueba']} {c['lado']} D={c['distancia']} V={c['volumen']}" for c in cells if c["bh_q10"]])
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "pruebas"}, indent=1, ensure_ascii=False))
    for c in cells:
        print(c["prueba"], c["lado"], "D", c["distancia"], "V", c["volumen"], c["n_zona"], c["n_control"], round(c["estimado"], 3),
              [round(x, 3) for x in (c["ic90"] or [])], round(c["p_bilateral"], 3), "barre", c["barre_zona"] and round(c["barre_zona"], 3),
              "p0", c["p0_zona"] and round(c["p0_zona"], 3), "ctrl", c["barre_control"] and round(c["barre_control"], 3))


if __name__ == "__main__":
    main()
