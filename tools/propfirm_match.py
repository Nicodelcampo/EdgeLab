#!/usr/bin/env python3
"""La cuenta que mejor le calza a una estrategia (camino inverso del universo): dado instrumento, σ de la operación (ticks) y z bruto por operación (esperanza bruta / σ),
ordena las cuentas del catálogo por aporte sobre el control sin ventaja y EV del ciclo completo.
  python tools/propfirm_match.py --inst GC --sigma 110 --z 0.08 --tpd 1"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import universe as U
ap = argparse.ArgumentParser(); ap.add_argument("--inst", required=True); ap.add_argument("--sigma", type=float, required=True); ap.add_argument("--z", type=float, required=True); ap.add_argument("--tpd", type=int, default=2); ap.add_argument("--paths", type=int, default=3000); a = ap.parse_args()
print(f"{a.inst}: σ {a.sigma} ticks, z bruto {a.z}, costo/σ = {U.cost_ratio(a.inst, a.sigma):.3f}")
for r in U.best_accounts(a.inst, a.sigma, a.z, U.catalog(), a.tpd, a.paths): print(f"{r['cuenta']:<42} EV {r['ev']:8.1f} ±{r['ev_se']:.1f}  aporte {r['aporte']:8.1f}  pase {r['p_pass']:.3f}  pago {r['p_payout']:.3f}  cuota {r['eval_fee']}  {'(sin verificar)' if not r['verificada'] else ''}")
