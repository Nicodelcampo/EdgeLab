#!/usr/bin/env python3
r"""Capa del visor «Picos robustos» (diseño de Nico 2026-11-19): pares de picos y grupos con puntaje, por variante. M1.

    python tools/picos_robustos_visor.py --asset NQ_M1_2026_ENE_MAR            # todas las variantes
    python tools/picos_robustos_visor.py --asset NQ_M1_2026_ENE_MAR --var B_NIVEL

Lee las velas `time_1m` del bundle del visor y escribe `viewer/nt8_bridge/bundles/picos_rob/<asset>__<variante>.json`
más `picos_rob/index.json` (variantes disponibles por activo). Lógica: `edgelab/research/picos_robustos.py`.
Target-free: no usa retornos ni P&L; sirve para elegir la variante por fidelidad geométrica, mirando.
Se reutiliza `atr_prev` (espejo_impulsos). Zigzag propio porque los existentes (`ipc_nivel_run.zigzag`,
`espejo_picos2._zigzag`) toman un umbral fijo en precio y acá el umbral es r·ATR por vela.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.research import picos_robustos as PR  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge" / "bundles"


def _r(x, n=2):
    return None if x is None else round(float(x), n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True); ap.add_argument("--var", default=None)
    a = ap.parse_args()
    b = json.loads((VIEW / f"{a.asset}.json").read_text(encoding="utf-8"))
    cd = b["bar_series"]["time_1m"]["candles"]; tick = float(b["meta"].get("tick_size", 0.25))
    t = np.array([c["time"] for c in cd], np.int64); h = np.array([c["high"] for c in cd]); l = np.array([c["low"] for c in cd])
    c = np.array([c["close"] for c in cd])
    out_dir = VIEW / "picos_rob"; out_dir.mkdir(exist_ok=True)
    idx_p = out_dir / "index.json"; idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else {}
    for v in ([a.var] if a.var else list(PR.VARIANTES)):
        t0 = time.time(); cfg = PR.config(v); pares, G = PR.calcular(t, h, l, c, cfg, tick)
        T = lambda i: int(t[i])  # noqa: E731
        P = [dict(k=p["k"], a=[p["ia"], T(p["ia"]), p["pa"]], b=[p["ib"], T(p["ib"]), p["pb"]], v=[p["iv"], T(p["iv"]), p["pv"]],
                  o=[p["i0"], T(p["i0"]), p["p0"]], e=[p["i2"], T(p["i2"]), p["p2"]], cf=[p["cf"], T(p["cf"])], A=_r(p["A"]), r=p["r"],
                  L1=_r(p["L1"]), L2c=_r(p["L2c"]), L2f=_r(p["L2f"]), C=_r(p["C"]), d=_r(p["d"]),
                  rho=_r(p["fc"]["rho"]), dl=_r(p["fc"]["delta"]), Sc=_r(p["Sc"], 1), Sf=_r(p["Sf"], 1),
                  g=p.get("g"), gp=_r(p.get("g_pct_c"), 0)) for p in pares]
        GG = [dict(id=g["id"], k=g["k"], n=len(g["picos"]), nivel=_r(g["nivel"]), pct=_r(g.get("pct"), 0), bruto=_r(g.get("bruto"), 3),
                   picos=[[i, T(i), pz] for i, pz in g["picos"]]) for g in G if len(g["picos"]) >= 2]
        Sf = np.array([p["Sf"] for p in pares]) if pares else np.zeros(1)
        orden = np.sort(Sf)                                   # q = percentil de Sf en TODO el período: sólo para dibujar
        for d_, s_ in zip(P, Sf): d_["q"] = int(round(100.0 * np.searchsorted(orden, s_, side="right") / len(orden)))
        dias = max(1, len(set((t // 86400).tolist())))
        out = dict(schema="EDGELAB_PICOS_ROBUSTOS_V1", asset=a.asset, variante=v, descripcion=PR.VARIANTES[v]["desc"],
                   parametros={k: cfg[k] for k in cfg}, n_pares=len(P), n_grupos=len(GG), pares_por_dia=round(len(P) / dias, 1),
                   sf_percentiles={q: _r(np.percentile(Sf, q), 1) for q in (50, 75, 90, 95)}, pares=P, grupos=GG)
        (out_dir / f"{a.asset}__{v}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        idx.setdefault(a.asset, {})[v] = dict(desc=PR.VARIANTES[v]["desc"], n_pares=len(P), n_grupos=len(GG))
        print(f"{v}: {len(P)} pares ({out['pares_por_dia']}/día), {len(GG)} grupos, Sf p50/p90 = {out['sf_percentiles'][50]}/{out['sf_percentiles'][90]}  ({time.time() - t0:.1f}s)")
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
