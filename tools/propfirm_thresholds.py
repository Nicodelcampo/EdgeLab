#!/usr/bin/env python3
"""Umbrales por cuenta × instrumento × σ de la operación (símetrico) → z bruto mínimo y ρ requerido. Salida: docs/research/propfirm_thresholds/THRESHOLDS.{json,md}.
  python tools/propfirm_thresholds.py [--paths 3000] [--instruments ES NQ GC ...]"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import universe as U
SIGMAS = (10, 20, 40, 80, 160)           # ticks de σ por operación (para GC 1 tick = 0,10 USD/oz; ES 0,25 pt)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--paths", type=int, default=3000); ap.add_argument("--instruments", nargs="*", default=["ES", "NQ", "YM", "GC", "ZB", "6E", "6J"]); ap.add_argument("--tpd", type=int, default=2); a = ap.parse_args()
    cat = U.catalog(); rows = []; t0 = time.time()
    for r in cat:
        for inst in a.instruments:
            for s in SIGMAS:
                try: rows.append(U.threshold(r, inst, s, a.tpd, n_paths=a.paths))
                except Exception as e: rows.append(dict(cuenta=r.key, inst=inst, sigma_ticks=s, error=repr(e)[:120]))
        print(r.key, f"{time.time() - t0:.0f}s", flush=True)
    out = ROOT / "docs/research/propfirm_thresholds"; out.mkdir(parents=True, exist_ok=True)
    (out / "THRESHOLDS.json").write_text(json.dumps(dict(sigmas_ticks=SIGMAS, trades_per_day=a.tpd, n_paths=a.paths, instruments=a.instruments, rows=rows, cost_assumptions=U.INSTRUMENTS), indent=1, default=float), encoding="utf-8")
    L = ["# Umbrales de cuentas de challenge (z bruto mínimo y ρ requerido)", "", f"Bracket simétrico de σ ticks, {a.tpd} operaciones/día, 1 contrato, {a.paths} caminos, evaluación sin tope de tiempo (400 días). `ρ requerido = z*/0,8`. Costos supuestos en `edgelab/autopilot/universe.py`.", ""]
    for inst in a.instruments:
        L += [f"## {inst} (tick USD {U.INSTRUMENTS[inst]['tick_value']}, costo ida y vuelta {U.INSTRUMENTS[inst]['cost_rt']})", "", "| cuenta | " + " | ".join(f"σ={s} t: ρ*" for s in SIGMAS) + " |", "|---|" + "---:|" * len(SIGMAS)]
        for r in cat:
            cells = []
            for s in SIGMAS:
                x = next((x for x in rows if x["cuenta"] == r.key and x["inst"] == inst and x["sigma_ticks"] == s), {})
                v = x.get("rho_requerido"); cells.append("—" if v is None or v != v else f"{v:.2f}")
            L.append(f"| {r.key}{'' if r.verified else ' (sin verificar)'} | " + " | ".join(cells) + " |")
        L.append("")
    (out / "THRESHOLDS.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("listo", f"{time.time() - t0:.0f}s")
if __name__ == "__main__":
    main()
