#!/usr/bin/env python3
"""Umbrales por cuenta, independientes del instrumento: σ de la operación (USD, ya con el tamaño) × costo/σ → z bruto mínimo y ρ requerido (ρ = z/0,8).
  python tools/propfirm_thresholds.py [--paths 2500] [--tpd 2]     → docs/research/propfirm_thresholds/THRESHOLDS.{json,md}"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import universe as U
SIG = (50, 100, 150, 250, 400, 700, 1200); RAT = (0.01, 0.02, 0.04, 0.08, 0.15)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--paths", type=int, default=2500); ap.add_argument("--tpd", type=int, default=2); a = ap.parse_args()
    cat = U.catalog(); rows = []; t0 = time.time()
    for r in cat:
        for s in SIG:
            for q in RAT: rows.append(U.threshold_usd(r, s, q, a.tpd, n_paths=a.paths))
        print(r.key, f"{time.time() - t0:.0f}s", flush=True)
    out = ROOT / "docs/research/propfirm_thresholds"; out.mkdir(parents=True, exist_ok=True)
    (out / "THRESHOLDS.json").write_text(json.dumps(dict(sigmas_usd=SIG, ratios=RAT, trades_per_day=a.tpd, n_paths=a.paths, accounts=[dict(key=r.key, verified=r.verified, eval_fee=r.eval_fee, profit_target=r.profit_target, max_loss=r.max_loss) for r in cat], rows=rows, cost_model=U.INSTRUMENTS), indent=1, default=float), encoding="utf-8")
    L = ["# Umbrales de cuentas de challenge: ρ requerido por σ de la operación y costo/σ", "", f"{a.tpd} operaciones/día, {a.paths} caminos, evaluación sin tope (400 días). Operación simétrica de desvío σ (USD con el tamaño incluido) y costo de ida y vuelta = (costo/σ)·σ. **ρ requerido** = z*/0,8: correlación mínima de la señal con el retorno siguiente para EV ≥ 0 (cuota incluida). Las cuentas sin verificar se marcan.", ""]
    for r in cat:
        L += [f"## {r.key}{'' if r.verified else ' (sin verificar)'} — cuota {r.eval_fee:.0f}, objetivo {r.profit_target:.0f}, piso {r.max_loss:.0f}", "", "| σ (USD) \\ costo/σ | " + " | ".join(f"{q:.2f}" for q in RAT) + " |", "|---|" + "---:|" * len(RAT)]
        for s in SIG:
            L.append(f"| {s} | " + " | ".join("—" if (v := next(x["rho_requerido"] for x in rows if x["cuenta"] == r.key and x["sigma_usd"] == s and x["ratio"] == q)) != v else f"{v:.2f}" for q in RAT) + " |")
        L.append("")
    (out / "THRESHOLDS.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("listo", f"{time.time() - t0:.0f}s")
if __name__ == "__main__":
    main()
