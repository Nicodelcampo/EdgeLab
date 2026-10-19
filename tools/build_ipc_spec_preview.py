#!/usr/bin/env python3
r"""Vista previa CIEGA de la replicación IPC (modo «race» de spec_review.html).

Por cada una de las 23 celdas toma `per_cell` eventos del descubrimiento (muestra con semilla fija) y guarda SOLO las
120 velas de 25t anteriores al evento, el nivel (objetivo de la carrera) y la barrera de fallo. Ningún precio posterior
al evento entra al archivo. El tiempo de las velas es su índice (las velas de 25t comparten segundos).

    .venv\Scripts\python tools\build_ipc_spec_preview.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import tbzx_iter2 as T2  # noqa: E402
from build_spec_preview import spec_sha256  # noqa: E402

SPEC = REPO / "docs" / "specs" / "SPEC_IPC_REPLICACION_20260927.json"
LOOK = 120


def main():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    rep = json.loads((REPO / "artifacts" / "ipc" / "reportA.json").read_text(encoding="utf-8"))
    cells = rep["pasan_B"]
    rng = np.random.default_rng(spec["sample"]["seed"])
    ex, per_session, labels = [], {}, []
    bars = {}
    for ci, c in enumerate(cells):
        D = pd.read_parquet(REPO / "artifacts" / "ipc" / f"A_{c['inst']}.parquet", columns=["kind", "k", "nivel", "virgen", "vol_rel", "ev", "D", "lvl_dist", "far_dist", "detector", "session"])
        g0 = D[D.detector == c["detector"]]
        t1, t2 = g0.vol_rel.quantile([1 / 3, 2 / 3])
        g = g0[(g0.virgen == c["virgen"]) & (g0.k == c["k"]) & (g0.nivel == c["nivel"])]
        g = g[g.vol_rel <= t1] if c["volumen"] == "bajo" else (g[g.vol_rel >= t2] if c["volumen"] == "alto" else g)
        lab = f"{c['inst']} {c['detector']} {'virgen' if c['virgen'] else 'no virgen'} k{c['k']} vol {c['volumen']} {c['nivel']}"
        labels.append(lab)
        for s in g.session:
            per_session[f"{c['inst']}:{s}"] = per_session.get(f"{c['inst']}:{s}", 0) + 1
        for j in rng.choice(len(g), size=min(spec["sample"]["per_cell"], len(g)), replace=False):
            r = g.iloc[int(j)]
            key = (c["inst"], r.session)
            if key not in bars:
                bars[key] = np.load(T2.bars_dir(c["inst"]) / f"{r.session}.npz")
            z = bars[key]; e = int(r.ev); lo = max(0, e - LOOK + 1)
            h, l, cl = z["h"][lo:e + 1], z["l"][lo:e + 1], z["c"][lo:e + 1]
            op = np.r_[z["c"][lo - 1] if lo > 0 else cl[0], cl[:-1]]
            candles = [dict(time=i, open=int(op[i]), high=int(h[i]), low=int(l[i]), close=int(cl[i])) for i in range(len(cl))]
            s = 1 if r.kind == "H" else -1                       # techo: el nivel está arriba
            E = int(cl[-1])
            ex.append(dict(id=f"{ci + 1}.{len([x for x in ex if x['cell'] == lab]) + 1}", cell=lab, session=str(r.session),
                           entry_ts_us=int(float(z["t"][e]) * 1e6), side="LONG" if s > 0 else "SHORT", candles=candles,
                           level_tick=int(round(E + s * r.lvl_dist)), entry_tick=E, stop_tick=int(round(E - s * r.far_dist)),
                           D_ticks=float(r.D), k=int(r.k)))
    body = dict(schema="EDGELAB_SPEC_PREVIEW_V1", spec=spec, spec_sha256=spec_sha256(SPEC), candle_s=1, latency_ms=0, cells=labels,
                examples=ex, summary=dict(sessions=len(per_session), events_total=int(sum(per_session.values())),
                                          events_per_session=per_session, overlap_fraction_by_hold={}, median_range60_ticks=0, median_spread_ticks=1))
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    out = REPO / "viewer" / "nt8_bridge" / "bundles" / f"spec_{spec['spec_id']}.json"
    out.write_text(raw, encoding="utf-8")
    import hashlib
    print(json.dumps(dict(out=str(out), ejemplos=len(ex), celdas=len(labels), spec_sha256=body["spec_sha256"],
                          preview_sha256=hashlib.sha256(raw.encode()).hexdigest())))


if __name__ == "__main__":
    main()
