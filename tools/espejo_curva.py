"""Diagnóstico de la curva de ESPEJO-MACRO al 75 % (2026-09-27, pedido de Nico: «¿la curva parece pareja?»).

Sólo describe eventos ya medidos (`eventos.json` de `tools/espejo_macro.py`). No elige nada:
- ES: neto en ticks (costo 2,4 t, deslizamiento 1 t en el stop; manifiesto §5).
- NQ, YM y SPY: bruto en W. No se transportan costos entre instrumentos.

Orden: por sesión (dentro de la sesión, el orden de detección). Es en muestra, no es la curva de una estrategia validada.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np

CFGS = ("5m_12_3", "5m_12_4", "5m_24_4")
COST, SLIP = 2.4, 1.0


def trades(rows, x=0.75, neto=True):
    out = []
    for r in sorted((r for r in rows if r["x"] == x and r["res"] in (1, 2)), key=lambda r: r["sesion"]):
        f, W = r["f_cierre"], r["W"]
        g = ((1 - f) * W if r["res"] == 1 else -f * W - SLIP) - COST if neto else ((1 - f) if r["res"] == 1 else -f)
        out.append((r["sesion"], float(g)))
    return out


def stats(t):
    g = np.array([v for _, v in t])
    c = g.cumsum()
    dd = float((np.maximum.accumulate(np.r_[0, c])[1:] - c).max()) if len(g) else 0.0
    racha = m = 0
    for v in g:
        racha = racha + 1 if v < 0 else 0
        m = max(m, racha)
    anual = len({s[:4] for s, _ in t}) > 3
    per = collections.defaultdict(float)
    for s, v in t:
        per[s[:4] if anual else s[:7]] += v
    top = np.sort(g)[::-1][:max(1, len(g) // 10)].sum() / g.sum() if g.sum() > 0 else None
    return dict(n=len(g), total=float(g.sum()), medio=float(g.mean()) if len(g) else None, gana=float(np.mean(g > 0)),
                caida_max=dd, racha_perdedora=m, periodo="año" if anual else "mes",
                periodos_pos=int(sum(v > 0 for v in per.values())), periodos=len(per),
                top10_sobre_total=None if top is None else float(top), por_periodo={k: float(v) for k, v in sorted(per.items())},
                curva=[float(v) for v in c])


def svg(curva, titulo, unidad, w=640, h=220, pad=36):
    if not curva:
        return ""
    y = np.r_[0.0, curva]; lo, hi = float(min(y.min(), 0)), float(max(y.max(), 0))
    sx = (w - 2 * pad) / max(len(y) - 1, 1); sy = (h - 2 * pad) / (hi - lo or 1)
    pts = " ".join(f"{pad + i * sx:.1f},{h - pad - (v - lo) * sy:.1f}" for i, v in enumerate(y))
    z = h - pad - (0 - lo) * sy
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif" font-size="11">'
            f'<rect width="100%" height="100%" fill="#fff"/><text x="{pad}" y="18">{titulo}</text>'
            f'<line x1="{pad}" x2="{w - pad}" y1="{z:.1f}" y2="{z:.1f}" stroke="#bbb" stroke-dasharray="3 3"/>'
            f'<polyline points="{pts}" fill="none" stroke="#2563eb" stroke-width="1.5"/>'
            f'<text x="{w - pad}" y="{h - 10}" text-anchor="end">eventos → ({unidad}; máx {hi:.1f}, mín {lo:.1f})</text></svg>')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eventos", required=True, help="carpeta con <SERIE>/eventos.json")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    src, out = Path(a.eventos), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    series = {"ES_RTH": True, "ES_FULL": True, "NQ_RTH": False, "YM_RTH": False, "SPY": False}
    res, L = {}, ["# ESPEJO-MACRO al 75 % — diagnóstico de curva (en muestra)", "",
                  "ES: neto en ticks (2,4 t + 1 t de deslizamiento en el stop). NQ, YM y SPY: bruto en W, sin costos.", "",
                  "| serie | config | n | total | caída máx | gana | períodos + | top 10 % / total |", "|---|---|---|---|---|---|---|---|"]
    for s, neto in series.items():
        data = json.loads((src / s / "eventos.json").read_text())
        for cfg in CFGS:
            st = stats(trades(data.get(cfg, []), neto=neto))
            res[f"{s}/{cfg}"] = st
            u = "t" if neto else "W"
            top = "—" if st["top10_sobre_total"] is None else f"{st['top10_sobre_total']:.2f}"
            L.append(f"| {s} | {cfg} | {st['n']} | {st['total']:+.1f} {u} | {st['caida_max']:.1f} {u} | {st['gana']:.0%} | "
                     f"{st['periodos_pos']}/{st['periodos']} ({st['periodo']}) | {top} |")
            (out / f"curva_{s}_{cfg}.svg").write_text(svg(st["curva"], f"{s} {cfg} x=0,75", u))
    (out / "curva.json").write_text(json.dumps(res, indent=1))
    (out / "curva.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
