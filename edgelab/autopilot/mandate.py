"""Mandato del agente: qué edges importan. Un hallazgo estadístico NO es útil por serlo: tiene que servir para pasar challenges y operar cuentas fondeadas,
lo que exige tamaño neto de costos, estabilidad en el tiempo y margen para diversificar entre varias estrategias. Este módulo es solo lectura para el agente
(el archivo de configuración y este código están en el manifiesto de protegidos)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]


def load(path: Path | None = None) -> dict:
    return json.loads((Path(path) if path else REPO / "config/autopilot/mandate.json").read_text(encoding="utf-8"))


def utility_weight(utility_class: str, cfg: dict | None = None) -> float:
    return (cfg or load())["utility_weight"].get(utility_class, 0.3)


def pass_probability(daily_pnl, rules: dict, n_sims: int = 5000, seed: int = 20261014, block: int = 3) -> dict:
    """Probabilidad de superar un challenge remuestreando días de P&L neto (bloques de `block` días). Modela lo que importa de las reglas (config/autopilot/mandate.json):
    - piso de pérdida: EOD trailing (sobre el cierre de cada día) que se bloquea en saldo inicial + `locked_floor_profit_usd` cuando el pico supera `lock_profit_usd` (None = trailing sin bloqueo);
    - límite diario opcional; días mínimos; consistencia (mayor día ≤ cuota del beneficio total al momento de pasar: si no se cumple se sigue operando);
    - sin límite de tiempo si `max_days` es None (tope de simulación `sim_day_cap`, que cuenta como «timeout»).
    La granularidad diaria es válida para drawdown de fin de día (EOD); para drawdown intradía subestima el riesgo."""
    x = np.asarray(daily_pnl, float); rng = np.random.default_rng(seed); n = len(x)
    tgt, dd = rules["profit_target_usd"], rules["max_trailing_drawdown_usd"]; dl = rules.get("daily_loss_limit_usd"); mind = rules.get("min_trading_days", 1)
    cap = rules.get("max_days") or rules.get("sim_day_cap", 600); lock, lockf = rules.get("lock_profit_usd"), rules.get("locked_floor_profit_usd", 0.0); cons = rules.get("consistency_max_best_day_share")
    res = dict(passed=0, failed_dd=0, timeout=0); days_to_pass = []
    for _ in range(n_sims):
        eq = peak = best = 0.0; d = 0; out = "timeout"
        while d < cap and out == "timeout":
            s0 = int(rng.integers(0, n))
            for v in x[np.arange(s0, s0 + block) % n]:
                d += 1; eq += v; peak = max(peak, eq); best = max(best, v)
                floor = (lockf if (lock is not None and peak >= lock) else peak - dd)
                if (dl is not None and v <= -dl) or eq <= floor: out = "failed_dd"; break
                if eq >= tgt and d >= mind and (cons is None or best <= cons * eq): out = "passed"; break
                if d >= cap: break
        res[out if out != "timeout" else "timeout"] += 1 if out != "passed" else 0
        if out == "passed": res["passed"] += 1; days_to_pass.append(d)
    return dict(p_pass=res["passed"] / n_sims, p_fail_dd=res["failed_dd"] / n_sims, p_timeout=res["timeout"] / n_sims, median_days_to_pass=float(np.median(days_to_pass)) if days_to_pass else None, n_sims=n_sims)


def viability(summary: dict, cfg: dict | None = None) -> dict:
    """summary (todo NETO de costos): daily_pnl_usd (lista), quarterly_pnl_usd (lista), trades_per_month, net_pnl_stress_usd (P&L total con costos × multiplicador),
    corr_with_portfolio (lista de correlaciones de P&L diario con estrategias ya aceptadas, vacía si es la primera), max_drawdown_usd.
    Devuelve cada criterio y si los cumple; `useful` solo si cumple todos."""
    c = cfg or load(); t = c["thresholds"]; ch = c["challenge_reference"]; dp = np.asarray(summary["daily_pnl_usd"], float); q = np.asarray(summary["quarterly_pnl_usd"], float)
    top5 = np.sort(dp)[::-1][:5].sum() / dp.sum() if dp.sum() > 0 else np.inf
    pp = pass_probability(dp, ch)
    crit = {
        "neto_positivo": bool(dp.sum() > 0),
        "resiste_costos_x%.1f" % t["cost_stress_multiplier"]: bool(summary["net_pnl_stress_usd"] > 0),
        "frecuencia": bool(summary["trades_per_month"] >= t["min_trades_per_month"]),
        "trimestres_observados": bool(len(q) >= t["min_quarters_observed"]),
        "trimestres_positivos": bool(len(q) > 0 and (q > 0).mean() >= t["min_fraction_positive_quarters"]),
        "no_depende_de_5_dias": bool(top5 <= t["max_share_of_pnl_top5_days"]),
        "diversifica": bool(all(abs(r) <= t["max_abs_corr_with_portfolio"] for r in summary.get("corr_with_portfolio", []))),
        "drawdown_vs_objetivo": bool(summary["max_drawdown_usd"] <= t["max_drawdown_to_target_ratio"] * ch["profit_target_usd"]),
        "probabilidad_de_pase": bool(pp["p_pass"] >= t["min_pass_probability_single"]),
    }
    return dict(criteria=crit, useful=all(crit.values()), failed=[k for k, v in crit.items() if not v], pass_probability=pp, top5_days_share=float(top5))


def tier(statistically_valid: bool, tradeable_form: bool, via: dict | None, artifact: bool = False) -> str:
    """A: válida y útil. B: válida con forma operable pero falla utilidad. C: información/pista sin forma operable o sin validar. D: artefacto/descartada."""
    if artifact: return "D"
    if statistically_valid and tradeable_form and via and via["useful"]: return "A"
    if statistically_valid and tradeable_form: return "B"
    return "C"
