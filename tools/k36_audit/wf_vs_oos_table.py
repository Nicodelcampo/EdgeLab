# -*- coding: utf-8 -*-
"""Tabla lado a lado k36: walk-forward 178 sesiones (2 trades/dia, 'IDEAL') vs
evaluacion de las ultimas 32 sesiones. Solo lee el resumen publicado por el kernel
(docs/research/k36_audit_20261017/k36_summary.json). No recalcula nada."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs/research/k36_audit_20261017/k36_summary.json"
OUT = ROOT / "docs/research/k36_audit_20261017/K36_WF178_VS_OOS32_TABLA.md"

j = json.loads(SRC.read_text(encoding="utf-8"))
COSTS = [("gross_0t", "bruto"), ("net_limit_155t_immediate", "neto limite 1.55t"),
         ("net_passive_tt_state_machine_155t", "neto pasivo realista 1.55t")]


def cell(x, key):
    m = x.get(key, {})
    return "%.2f (z %.2f)" % (m.get("mean_ticks", float("nan")), m.get("z_clust", float("nan")))


lines = ["# k36: walk-forward 178 sesiones vs ultimas 32 sesiones (ticks por trade, z clusterizado por sesion)", "",
         "Fuente: `k36_summary.json` (salida del kernel k36, sin recalcular). WF = `trading_by_daily_frequency_walkforward_oos`, "
         "columna `freq_2.0_per_day_IDEAL`; OOS32 = `assessment_32_sessions_strict_oos_at_2trades_per_day`.", ""]
for uni, r in j["results"].items():
    wf = r["trading_by_daily_frequency_walkforward_oos"]["freq_2.0_per_day_IDEAL"]
    oo = r["assessment_32_sessions_strict_oos_at_2trades_per_day"]
    lines += ["## %s" % uni, "",
              "| config | WF n | WF bruto | WF neto limite | WF neto pasivo | OOS32 n | OOS32 bruto | OOS32 neto limite | OOS32 neto pasivo |",
              "|---|---|---|---|---|---|---|---|---|"]
    for cfg in wf:
        a, b = wf[cfg], oo.get(cfg, {})
        lines.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
            cfg.split("_")[0] + "_" + cfg.split("_")[1][:14], a["n_trades"],
            cell(a, COSTS[0][0]), cell(a, COSTS[1][0]), cell(a, COSTS[2][0]),
            b.get("n_trades", "-"), cell(b, COSTS[0][0]) if b else "-",
            cell(b, COSTS[1][0]) if b else "-", cell(b, COSTS[2][0]) if b else "-"))
    n = r["circular_shift_null_100_reps_C4_at_2trades_per_day"]
    lines += ["", "Nulo de desplazamiento circular (C4, 2 trades/dia): observado neto %.2f vs nulo %.2f, p = %.2f." % (
        n["observed_net_155t_mean_ticks"], n["null_mean_net_155t_ticks"], n["p_circular_shift_net_155t"]), ""]
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", OUT)
