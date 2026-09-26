#!/usr/bin/env python3
r"""Cruce de las reglas detalladas por firma (incluidas las «escondidas»: topes por número de retiro, colchón, días
calificados con ganancia mínima, retiro mínimo, consistencia desde el último retiro, cierre tras N retiros, acceso de
30 días, política de algoritmos) con las ventajas que EdgeLab midió. Siempre con el control de ventaja cero.

    python tools/propfirm_reglas_cruce.py --catalog config/propfirms/catalogo_detallado_50k.json --paths 3000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edgelab.propfirm.ev import report  # noqa: E402
from edgelab.propfirm.requirements import INSTRUMENTS, requirement, strategy_from_ticks  # noqa: E402
from edgelab.propfirm.rules import load_catalog  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from propfirm_ev_report import MEDIDAS  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="config/propfirms/catalogo_detallado_50k.json")
    ap.add_argument("--out", default="artifacts/propfirm/cruce_reglas_detalladas.json")
    ap.add_argument("--paths", type=int, default=3000)
    a = ap.parse_args(argv)
    kw = dict(n_paths=a.paths, eval_days=60, funded_days=120)
    out = []
    for r in load_catalog(a.catalog):
        fila = dict(cuenta=r.key, verificada=r.verified, algoritmos=r.algo_policy, aplica_a_edgelab=r.admits_algorithms(),
                    tenencia=r.min_hold_rule, prohibido=r.prohibited, estrategias=[], requisitos=[])
        for m in MEDIDAS:
            c_t = INSTRUMENTS[m["inst"]]["cost_rt"] / INSTRUMENTS[m["inst"]]["tick_value"]
            p = (m["ticks_netos"] + c_t + m["sl"]) / (m["tp"] + m["sl"])
            rep = report(r, strategy_from_ticks(m["inst"], m["tp"], m["sl"], p, trades_per_day=m["n"]), **kw)
            fila["estrategias"].append(dict(nombre=m["nombre"], ev=rep["real"]["ev"], ev_se=rep["real"]["ev_se"],
                                            p_pass=rep["real"]["p_pass"], p_payout=rep["real"]["p_payout"],
                                            ev_ventaja_cero=rep["ventaja_cero"]["ev"], aporte=rep["aporte_estrategia"]))
        for inst, tp, sl, n in (("ES", 16, 16, 2), ("ES", 40, 40, 1), ("MES", 80, 80, 2)):
            q = requirement(r, inst, tp, sl, trades_per_day=n, **kw)
            fila["requisitos"].append({k: q[k] for k in ("instrumento", "tp_ticks", "sl_ticks", "trades_por_dia",
                                                         "acierto_minimo", "acierto_sin_ventaja", "ventaja_neta_min_ticks")})
        out.append(fila)
        print(f"\n== {r.key}  algoritmos={r.algo_policy}  aplica={r.admits_algorithms()}")
        for e in fila["estrategias"]:
            print(f"   {e['nombre'][:60]:<60} EV {e['ev']:+7.0f} (±{e['ev_se']:.0f})  pase {e['p_pass']:.2f}  "
                  f"pago {e['p_payout']:.2f}  sin ventaja {e['ev_ventaja_cero']:+6.0f}  aporte {e['aporte']:+6.0f}")
        for q in fila["requisitos"]:
            print(f"   requisito {q['instrumento']:>3} {q['tp_ticks']}/{q['sl_ticks']} {q['trades_por_dia']}/día: "
                  f"ventaja neta mín {q['ventaja_neta_min_ticks']:+.2f} ticks (acierto {q['acierto_minimo']:.3f})")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
