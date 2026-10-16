#!/usr/bin/env python3
"""Cruza el mapa de volatilidad (UNIVERSE_SIGMA.json) con los umbrales de las cuentas (THRESHOLDS.json): para cada celda instrumento × franja × horizonte elige el tamaño
(minis ≤ 4 o micros ≤ 40) y la cuenta del catálogo que minimizan el ρ requerido (correlación mínima de una señal con el retorno siguiente para que la cuenta deje EV ≥ 0, cuota incluida).
Salida: docs/research/propfirm_thresholds/UNIVERSO.{json,md}.   python tools/universe_design.py --sigma /ruta/UNIVERSE_SIGMA.json"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot.universe import INSTRUMENTS, RHO_PLAUSIBLE
OUT = ROOT / "docs/research/propfirm_thresholds"
MICRO = {"ES": ("MES", 10), "NQ": ("MNQ", 10), "YM": ("MYM", 10), "GC": ("MGC", 10)}      # (símbolo, contratos micro por mini)
def table(th, cuenta):
    S, Q = th["sigmas_usd"], th["ratios"]; g = np.full((len(S), len(Q)), np.nan)
    for r in th["rows"]:
        if r["cuenta"] == cuenta: g[S.index(r["sigma_usd"]), Q.index(r["ratio"])] = r["rho_requerido"]
    return S, Q, g
def rho_at(S, Q, g, sigma, ratio):
    if ratio > Q[-1]: return float("nan"), "costo/σ > %.2f: inviable" % Q[-1]
    col = [np.interp(ratio, Q, g[i]) for i in range(len(S))]
    if any(np.isnan(col)): return float("nan"), "sin dato"
    fl = "ok" if S[0] <= sigma <= S[-1] else ("σ bajo la grilla" if sigma < S[0] else "σ sobre la grilla")
    return float(np.interp(np.log(sigma), np.log(S), col)), fl
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sigma", required=True); a = ap.parse_args()
    sg = json.loads(Path(a.sigma).read_text())["res"]; th = json.loads((OUT / "THRESHOLDS.json").read_text()); tabs = {x["key"]: table(th, x["key"]) for x in th["accounts"]}; cells = []
    for inst, d in sg.items():
        if "error" in d: continue
        variants = [(inst, 1.0, INSTRUMENTS[inst]["cost_rt"], 4)]
        if inst in MICRO and MICRO[inst][0] in INSTRUMENTS: variants.append((MICRO[inst][0], 1 / MICRO[inst][1], INSTRUMENTS[MICRO[inst][0]]["cost_rt"], 40))
        for hk, slots in d.items():
            for r in slots:
                best = None
                for sym, scale, cost, kmax in variants:
                    s1 = r["sd_usd"] * scale; ratio = cost / s1
                    for k in range(1, kmax + 1):
                        for cu, (S, Q, g) in tabs.items():
                            rho, fl = rho_at(S, Q, g, k * s1, ratio)
                            if rho == rho: rho = max(rho * 0.8, ratio) / 0.8      # umbral efectivo: EV ≥ 0 del ciclo Y esperanza neta ≥ 0 (z bruto ≥ costo/σ); no se juega a la opción de la cuenta sin ventaja
                            if rho == rho and (best is None or rho < best["rho_required"]): best = dict(inst=inst, symbol=sym, contracts=k, horizon_min=int(hk[1:]), slot=r["slot"], n=r["n"], sd_ticks=r["sd_ticks"], sd_usd_per_mini=r["sd_usd"], ratio=ratio, sigma_total_usd=k * s1, best_account=cu, rho_required=rho, flag=fl)
                if best: best["plausibility"] = min(1.0, RHO_PLAUSIBLE / best["rho_required"]) if best["rho_required"] > 0 else 1.0; cells.append(best)
    cells.sort(key=lambda c: c["rho_required"]); (OUT / "UNIVERSO.json").write_text(json.dumps(dict(rho_plausible=RHO_PLAUSIBLE, cells=cells), indent=1, default=float))
    L = ["# Universo de corridas guiado por umbrales", "", f"ρ requerido = correlación mínima de una señal con el retorno siguiente para que la mejor cuenta del catálogo deje EV ≥ 0 (cuota incluida), eligiendo tamaño (minis ≤ 4, micros ≤ 40). Plausible si ≲ {RHO_PLAUSIBLE}. Umbral efectivo = máx(EV ≥ 0 del ciclo, esperanza neta ≥ 0): varias cuentas muestran EV ≥ 0 sin ventaja (valor de opción con cuotas y retiros SIN verificar), y EdgeLab no persigue eso. Muestra: sesiones 2025-07 → 2026-09; costos y cuentas supuestos (THRESHOLDS.md); 2 operaciones por día.", ""]
    for inst in sg:
        cc = [c for c in cells if c["inst"] == inst]
        if not cc: continue
        L += [f"## {inst}: 8 celdas con menor ρ requerido", "", "| franja CT | horizonte | σ ticks | contratos | σ total USD | costo/σ | ρ requerido | cuenta | aviso |", "|---|---:|---:|---|---:|---:|---:|---|---|"]
        for c in cc[:8]: L.append(f"| {c['slot']} | {c['horizon_min']} min | {c['sd_ticks']:.0f} | {c['contracts']} {c['symbol']} | {c['sigma_total_usd']:.0f} | {c['ratio']:.3f} | {c['rho_required']:.3f} | {c['best_account']} | {c['flag']} |")
        L.append("")
    L += ["## Resumen por instrumento", "", "| instrumento | ρ requerido mínimo | mediana de las mejores 20 | celdas con ρ ≤ plausible |", "|---|---:|---:|---:|"]
    for inst in sg:
        cc = [c for c in cells if c["inst"] == inst]
        if cc: L.append(f"| {inst} | {cc[0]['rho_required']:.3f} | {np.median([c['rho_required'] for c in cc[:20]]):.3f} | {sum(c['rho_required'] <= RHO_PLAUSIBLE for c in cc)} de {len(cc)} |")
    (OUT / "UNIVERSO.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print(len(cells), "celdas")
if __name__ == "__main__":
    main()
