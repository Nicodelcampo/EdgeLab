#!/usr/bin/env python3
"""Viabilidad de reglas operables según el MANDATO (P&L neto, estabilidad, challenge, control sin ventaja). Lee el STUDY_RESULTS.json de un estudio `strategy_pnl`.
  python tools/strategy_viability.py RESULTADOS.json --alpha 0.0098 --out docs/research/autopilot_runs/PNL1_VIABILIDAD.md
Para cada regla × muestra: P&L diario neto; simulación de pase del challenge de referencia (mandate.json) con el tamaño (múltiplos de 1 contrato) que más lo favorece, contra el MISMO P&L con dirección aleatoria
(control sin ventaja); criterios de utilidad; y nivel A/B/C/D (A/B exigen validez estadística confirmatoria)."""
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.autopilot import mandate, universe as U
COST = {"GC": 24.8, "ES": 30.0}; TICK = {"GC": 10.0, "ES": 12.5}; SIZES = (0.1, 0.2, 0.5, 1.0, 2.0)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("results"); ap.add_argument("--alpha", type=float, default=0.05); ap.add_argument("--out", required=True); ap.add_argument("--sims", type=int, default=1500); a = ap.parse_args()
    res = json.loads(Path(a.results).read_text()); cfg = res["cfg"]; daily = res["descriptive"]["daily"]; flat = {r["test"]: r for r in res["results_flat"]}; rules = {r["name"]: r for r in cfg["rules"]}
    ch = mandate.load()["challenge_reference"]; rng = np.random.default_rng(7); rows = []
    for key, d in daily.items():
        name, role, src = key.split("|"); inst = rules[name]["inst"]; g = np.array(d["gross"]); sg = np.array(d["sign"]); cost = COST[inst]; net = g - cost; dates = pd.to_datetime(d["date"])
        q = pd.PeriodIndex(dates, freq="Q").astype(str); res_best = None
        for m in SIZES:
            p_real = mandate.pass_probability(net * m, ch, a.sims)["p_pass"]
            p_pl = np.mean([mandate.pass_probability((g * rng.choice([-1.0, 1.0], len(g)) - cost) * m, ch, 200, seed=int(rng.integers(1 << 30)))["p_pass"] for _ in range(6)])
            if res_best is None or p_real - p_pl > res_best[1] - res_best[2]: res_best = (m, p_real, float(p_pl))
        m, p_real, p_pl = res_best; qs = pd.Series(net * m).groupby(q.to_numpy()).sum()
        months = max(1.0, (dates[-1] - dates[0]).days / 30.4)
        via = mandate.viability(dict(daily_pnl_usd=list(net * m), quarterly_pnl_usd=list(qs.values), trades_per_month=len(net) / months, net_pnl_stress_usd=float((g - 1.5 * cost).sum() * m), corr_with_portfolio=[], max_drawdown_usd=float((np.maximum.accumulate(np.cumsum(net * m)) - np.cumsum(net * m)).max())))
        r = flat.get(f"pnl/{name}/{role}/{src}", {}); valid = bool(role == "oos" and r.get("p_holm_2", r.get("p", 1.0)) <= a.alpha)
        tier = mandate.tier(valid, True, via)
        z = float(g.mean() / g.std()) if g.std() > 0 else 0.0; fit = []
        if z > 0: fit = U.best_accounts(inst, g.std() / TICK[inst], z, U.catalog(), trades_per_day=1, n_paths=1500)[:2]
        rows.append(dict(rule=name, role=role, src=src, n=len(net), mean_net=float(net.mean()), mean_gross=float(g.mean()), hit=float((net > 0).mean()), fpq=float((qs > 0).mean()), top5=via["top5_days_share"], size=m, p_real=p_real, p_placebo=p_pl, failed=via["failed"], tier=tier, valid=valid, fit=fit, p=r.get("p")))
    L = ["# Viabilidad de las reglas según el mandato", "", f"Resultados: `{Path(a.results).name}`. Challenge de referencia: `mandate.json` (simulación por remuestreo de días, tamaño en múltiplos de 1 contrato que mejor aporta sobre el control de dirección aleatoria). Costos: GC 24,80 / ES 30,00 por contrato y operación.", "",
         "| regla | muestra (rol) | n | neto medio USD | bruto medio USD | aciertos | trim. positivos | 5 mejores días | tamaño | pase | pase control | nivel | falla |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in rows: L.append(f"| {r['rule']} | {r['src']} ({r['role']}) | {r['n']} | {r['mean_net']:.1f} | {r['mean_gross']:.1f} | {r['hit']:.2f} | {r['fpq']:.2f} | {('%.2f' % r['top5']) if np.isfinite(r['top5']) else '—'} | {r['size']} | {r['p_real']:.3f} | {r['p_placebo']:.3f} | **{r['tier']}** | {', '.join(r['failed'][:4])} |")
    L += ["", "## Mejor cuenta del catálogo (solo reglas con ventaja bruta positiva; EV y aporte del ciclo completo, cuotas sin verificar)", ""]
    for r in rows:
        if r["fit"]: L.append(f"- **{r['rule']} / {r['src']}**: " + "; ".join(f"{x['cuenta']} EV {x['ev']:.0f} (aporte {x['aporte']:.0f}, pase {x['p_pass']:.2f})" for x in r["fit"]))
    L += ["", "Nivel: A = válida y útil; B = válida con forma operable pero falla algún criterio; C = información / no confirmada; D = artefacto. Solo la muestra `oos` es confirmatoria."]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L[:30]))
if __name__ == "__main__":
    main()
