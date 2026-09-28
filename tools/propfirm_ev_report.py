#!/usr/bin/env python3
r"""Reporte de prop firms: para cada cuenta del catálogo, (1) el EV del participante sin ventaja (control de Hall),
(2) la ventaja neta mínima por trade que una estrategia necesita para EV > 0, por instrumento, bracket, tamaño y
cadencia, y (3) el cruce con las ventajas que EdgeLab midió. Escribe artifacts/propfirm/reporte.json y una tabla.

    python tools/propfirm_ev_report.py --catalog config/propfirms --paths 2000
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edgelab.propfirm.ev import report  # noqa: E402
from edgelab.propfirm.requirements import INSTRUMENTS, requirement, strategy_from_ticks  # noqa: E402
from edgelab.propfirm.rules import load_catalog  # noqa: E402

# Ventajas medidas en EdgeLab, con su propio bracket y cadencia: ticks netos por trade con el costo del instrumento.
# La tasa de acierto del modelo se deduce para que la esperanza neta del bracket iguale la medida.
MEDIDAS = [
    dict(nombre="TBZX-R3 sigue r=0 (ES, SL=TP=3, realista)", inst="ES", tp=3, sl=3, n=3, ticks_netos=-1.49,
         fuente="docs/research/TBZX_R3_ACTA_CIERRE_20260926.md"),
    dict(nombre="TBZX-R3 mejor escenario macro (ES, SL=TP=20, descubrimiento, no sostenido)", inst="ES", tp=20, sl=20,
         n=2, ticks_netos=0.19, fuente="tbzx_r3 IT4"),
    dict(nombre="IVC mejor celda de corto plazo (ES, SL=TP=4)", inst="ES", tp=4, sl=4, n=3, ticks_netos=-0.8,
         fuente="docs/research/IVC_RESULTADOS_20260926.md"),
    dict(nombre="IVC-L gap -> 10:00-cierre (ES, SL=TP=40, 1/día, validación, margen IC inf. < 0)", inst="ES", tp=40,
         sl=40, n=1, ticks_netos=0.8, fuente="docs/research/IVC_LARGO_RESULTADOS_20260926.md"),
]
BRACKETS = {"ES": [(8, 8), (16, 16), (24, 16)], "MES": [(40, 40), (80, 80)], "MNQ": [(40, 40), (100, 100)]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="config/propfirms"); ap.add_argument("--out", default="artifacts/propfirm")
    ap.add_argument("--paths", type=int, default=2000)
    a = ap.parse_args(argv)
    kw = dict(n_paths=a.paths, eval_days=60, funded_days=120)
    out = []
    for r in load_catalog(a.catalog):
        base = strategy_from_ticks("MES", 40, 40, 0.5, trades_per_day=2)
        ctrl = report(r, base.zero_edge(), **kw)["real"]
        reqs = []
        for inst, brs in BRACKETS.items():
            for tp, sl in brs:
                for n in (1, 3):
                    q = requirement(r, inst, tp, sl, trades_per_day=n, contracts=1, **kw)
                    reqs.append(q)
        out.append(dict(cuenta=r.key, verificada=r.verified, techo=r.geometric_ceiling(), control_ventaja_cero=ctrl,
                        requisitos=reqs))
        print(f"\n== {r.key}  (verificada={r.verified})  techo L/(T+L)={r.geometric_ceiling():.3f}")
        print(f"   sin ventaja (MES 40/40, 2 trades/día): pase {ctrl['p_pass']:.3f}, pago {ctrl['p_payout']:.3f}, "
              f"EV {ctrl['ev']:+.1f} USD (±{ctrl['ev_se']:.1f}), costo por fondeada {ctrl['costo_por_fondeada']:.0f}")
        for q in reqs:
            print(f"   {q['instrumento']:>3} TP/SL {q['tp_ticks']:>3}/{q['sl_ticks']:<3} {q['trades_por_dia']} tr/día: "
                  f"acierto mín {q['acierto_minimo']:.3f} (sin ventaja {q['acierto_sin_ventaja']:.3f}, +{q['exceso_pp']:.1f} pp)"
                  f" → ventaja neta mín {q['ventaja_neta_min_ticks']:+.2f} t/trade")
    # cruce: cada estrategia medida con su bracket y cadencia, contra su control de ventaja cero
    print("\n== Cruce con ventajas medidas en EdgeLab (EV por intento, USD; aporte = EV − EV sin ventaja)")
    cruce = []
    for r in load_catalog(a.catalog):
        for m in MEDIDAS:
            tv = INSTRUMENTS[m["inst"]]["tick_value"]; c_t = INSTRUMENTS[m["inst"]]["cost_rt"] / tv
            p = (m["ticks_netos"] + c_t + m["sl"]) / (m["tp"] + m["sl"])
            st = strategy_from_ticks(m["inst"], m["tp"], m["sl"], p, trades_per_day=m["n"])
            rep = report(r, st, **kw)
            row = dict(cuenta=r.key, **m, p_win_modelo=p, ev=rep["real"]["ev"], ev_se=rep["real"]["ev_se"],
                       ev_sin_ventaja=rep["ventaja_cero"]["ev"], aporte=rep["aporte_estrategia"],
                       p_pass=rep["real"]["p_pass"], p_payout=rep["real"]["p_payout"])
            cruce.append(row)
            print(f"   {r.key[:34]:<34} {m['nombre'][:58]:<58} EV {row['ev']:+7.1f} (±{row['ev_se']:.1f})  "
                  f"sin ventaja {row['ev_sin_ventaja']:+7.1f}  aporte {row['aporte']:+7.1f}  pase {row['p_pass']:.2f}")
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "reporte.json").write_text(json.dumps(dict(cuentas=out, cruce=cruce, instrumentos=INSTRUMENTS,
                                                              paths=a.paths), indent=1, default=float, ensure_ascii=False))


if __name__ == "__main__":
    main()
