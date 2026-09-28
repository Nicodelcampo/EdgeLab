#!/usr/bin/env python3
r"""ESPEJO-VOLLIMP-100T — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_ESPEJO_VOLUMEN_LIMPIEZA_100T_20260928.md

Mismo objeto, evento, resultado y nulo N1 que ESPEJO-NICO-100T (reusa `espejo_nico_descubrimiento.session_events`).
Rasgos: R-VOL (vol/tick vuelta ÷ vol/tick ida), R-LIMP (eficiencia vuelta ÷ ida), R-VL y R-VL-INV (conjunciones).
24 pruebas bilaterales, BH q = 0,10, bootstrap por sesión. Descriptivo: control por velocidad de la vuelta.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import espejo_nico_descubrimiento as E  # noqa: E402
import tbz_e2 as TB  # noqa: E402
import tbzx_iter2 as T2  # noqa: E402

OUT = REPO / "artifacts" / "espejo" / "vollimp_100t"
XS = (0.25, 0.5, 0.75)
N_BOOT, SEED = 1000, 20260929


def boot_diff(exc, ses, g1, g2, rng):
    u = np.unique(ses); idx = {s: np.flatnonzero(ses == s) for s in u}; out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        ii = np.concatenate([idx[s] for s in rng.choice(u, len(u))])
        a, c = ii[g1[ii]], ii[g2[ii]]
        out[b] = (exc[a].mean() if len(a) else np.nan) - (exc[c].mean() if len(c) else np.nan)
    return out


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    fr = json.loads(E.FROZEN.read_text(encoding="utf-8"))
    ss = [s["trade_date"] for s in T2.canonical_sessions("ES") if s["trade_date"] <= TB.EXP_END and (E.MID / f"{s['trade_date']}.npz").exists()]
    rows, prev = [], None
    for i, s in enumerate(ss):
        r, prev = E.session_events(s, prev, fr, xs=XS); rows += r
        if i % 30 == 0:
            print(s, i + 1, "/", len(ss), len(rows), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eventos.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    ev = [r for r in rows if r["p0"] is not None and r["vol_ratio"] == r["vol_ratio"]]
    rng = np.random.default_rng(SEED)
    cells, desc = [], {}
    for x in XS:
        X = [r for r in ev if r["x"] == x]
        v = np.array([r["vol_ratio"] for r in X]); e = np.array([r["eff_ratio"] for r in X]); vel = np.array([r["velas_vuelta"] for r in X])
        qv = np.quantile(v, [1 / 3, 2 / 3]); qe = np.quantile(e, [1 / 3, 2 / 3]); qs = np.quantile(vel, [1 / 3, 2 / 3])
        for r, vv, ee, ww in zip(X, v, e, vel):
            r["tv"] = 0 if vv <= qv[0] else (2 if vv > qv[1] else 1)
            r["te"] = 0 if ee <= qe[0] else (2 if ee > qe[1] else 1)
            r["ts"] = 0 if ww <= qs[0] else (2 if ww > qs[1] else 1)
        for estr in ("TBZ", "otros"):
            F = [r for r in X if r["estrato"] == estr]
            exc = np.array([(r["res_mid"] == "completa") - r["p0"]["completa"] for r in F], float)
            ses = np.array([r["session"] for r in F])
            tv = np.array([r["tv"] for r in F]); te = np.array([r["te"] for r in F]); ts = np.array([r["ts"] for r in F])
            vl = (tv == 2) & (te == 0); vli = (tv == 0) & (te == 2)
            for name, g1, g2 in (("R-VOL", tv == 2, tv == 0), ("R-LIMP", te == 0, te == 2), ("R-VL", vl, ~vl), ("R-VL-INV", vli, ~vli)):
                bs = boot_diff(exc, ses, g1, g2, rng); est = exc[g1].mean() - exc[g2].mean()
                p2 = float(min(1.0, 2 * min(np.mean(bs <= 0), np.mean(bs >= 0))))
                cells.append(dict(prueba=name, x=x, estrato=estr, n1=int(g1.sum()), n2=int(g2.sum()), estimado=float(est),
                                  ic90=[float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))], ee=float(np.nanstd(bs)),
                                  p_bilateral=p2, mde80=2.8 * float(np.nanstd(bs)),
                                  exceso_g1=float(exc[g1].mean()), exceso_g2=float(exc[g2].mean())))
            # descriptivos: extremos de R-VOL (>1 / <1) y control por velocidad
            desc[f"x{x}_{estr}"] = dict(
                n=len(F), vuelta_mas_vol=dict(n=int(np.sum(v_ := np.array([r['vol_ratio'] for r in F]) > 1)), exceso=float(exc[v_].mean()) if v_.any() else None),
                ida_mas_vol=dict(n=int(np.sum(~v_)), exceso=float(exc[~v_].mean()) if (~v_).any() else None),
                limp_por_velocidad={f"vel{k}": dict(n=int(((ts == k)).sum()),
                                                    sucia_menos_limpia=float(exc[(ts == k) & (te == 0)].mean() - exc[(ts == k) & (te == 2)].mean())
                                                    if ((ts == k) & (te == 0)).any() and ((ts == k) & (te == 2)).any() else None) for k in (0, 1, 2)})
    rej = E.bh([c["p_bilateral"] for c in cells])
    for c, r in zip(cells, rej):
        c["bh_q10"] = bool(r)
    rep = dict(manifiesto="docs/research/MANIFIESTO_ESPEJO_VOLUMEN_LIMPIEZA_100T_20260928.md", code_commit=head, tree_dirty=dirty,
               sesiones=len(ss), eventos=len(rows), eventos_usados=len(ev), pruebas=cells,
               sobreviven=[f"{c['prueba']} x={c['x']} {c['estrato']}" for c in cells if c["bh_q10"]], descriptivo=desc)
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print("sobreviven", rep["sobreviven"], "eventos", len(ev))
    for c in cells:
        print(c["prueba"], c["x"], c["estrato"], c["n1"], c["n2"], round(c["estimado"], 3), [round(t, 3) for t in c["ic90"]], round(c["p_bilateral"], 3), round(c["mde80"], 3))


if __name__ == "__main__":
    main()
