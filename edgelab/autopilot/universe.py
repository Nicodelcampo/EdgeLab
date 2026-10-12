"""Universo de corridas guiado por UMBRALES: qué tiene que superar una estrategia para que una cuenta de challenge deje valor esperado positivo, y dónde (instrumento × ventana × horizonte)
es plausible lograrlo. No decide por sí mismo: ordena y justifica las candidatas del generador.
Conceptos (todo por operación y por contrato, USD):
- bracket simétrico de σ ticks (TP = SL = σ) ≈ una operación con desvío σ; z_bruto = 2·p − 1 = esperanza bruta / σ (un «Sharpe por operación»); con señal de correlación ρ, z ≈ 0,8 ρ.
- umbral de la cuenta: acierto mínimo p* con EV ≥ 0 (simulador del ciclo evaluación → fondeada → retiros de `edgelab.propfirm`) ⇒ z* = 2p* − 1 incluye costos y reglas.
- ρ requerido = z* / 0,8. Una celda es plausible si ρ requerido es menor que lo que suelen dar los efectos intradía reales (≲ 0,10-0,15, ver evidencia propia)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from edgelab.propfirm import requirements as R
from edgelab.propfirm.rules import load_catalog

REPO = Path(__file__).resolve().parents[2]
# valor del tick (USD) y costo de ida y vuelta por contrato = comisión 4,80 (Lucid 2,40/lado) + 2 × deslizamiento de 1 tick. SUPUESTOS DECLARADOS, editables; ES/NQ/YM conservan los de edgelab.propfirm (más altos).
_COMM = 4.8
EXT = {k: dict(tick_value=tv, cost_rt=round(_COMM + 2 * tv, 2)) for k, tv in
       {"GC": 10.0, "MGC": 1.0, "ZB": 31.25, "6E": 6.25, "6J": 6.25, "CL": 10.0}.items()}
EXT["6E"]["cost_rt"] = 4.8 + 2.768 * 6.25 - 4.8 + 0.0            # ≈ 17,3: Lucid 2,40/lado = 2,768 ticks (PLAN_CAMPAÑA 2026-08-06)
for k, v in EXT.items(): R.INSTRUMENTS.setdefault(k, v)
INSTRUMENTS = R.INSTRUMENTS
RHO_PLAUSIBLE = 0.12            # corr típica «generosa» de un efecto intradía real en las muestras propias (los hallazgos grandes fueron episódicos)


def catalog(path: str | Path | None = None, skip_refs: bool = True) -> list:
    cat = load_catalog(Path(path) if path else REPO / "config/propfirms")
    return [r for r in cat if not (skip_refs and r.firm.startswith("Referencia"))]


def threshold(rules, inst: str, sigma_ticks: float, trades_per_day: int = 2, contracts: int = 1, n_paths: int = 3000, eval_days: int = 400, seed: int = 20261015) -> dict:
    """Umbral de una cuenta para un bracket simétrico de σ ticks: p*, z*, ρ requerido y esperanza neta mínima por operación (USD y ticks)."""
    out = R.requirement(rules, inst, sigma_ticks, sigma_ticks, trades_per_day, contracts, n_paths=n_paths, eval_days=eval_days, seed=seed)
    p = out["acierto_minimo"]; z = 2 * p - 1 if p == p else float("nan")
    return dict(cuenta=rules.key, verificada=rules.verified, inst=inst, sigma_ticks=sigma_ticks, trades_por_dia=trades_per_day, contratos=contracts, p_min=p, z_bruto_min=z,
                rho_requerido=z / 0.8 if z == z else float("nan"), ventaja_neta_min_usd=out["ventaja_neta_min_usd"], ventaja_neta_min_ticks=out["ventaja_neta_min_ticks"],
                cost_rt_usd=INSTRUMENTS[inst]["cost_rt"])


def cost_ratio(inst: str, sigma_ticks: float) -> float:
    """Costo de ida y vuelta en unidades de σ: piso absoluto de la esperanza bruta que se necesita (z ≥ esto) aunque la cuenta fuera gratis."""
    return INSTRUMENTS[inst]["cost_rt"] / (INSTRUMENTS[inst]["tick_value"] * sigma_ticks)


def best_accounts(inst: str, sigma_ticks: float, z_gross: float, catalog_rules: list, trades_per_day: int = 2, n_paths: int = 3000) -> list:
    """El camino inverso: dada una estrategia (z bruto por operación y σ), ordena las cuentas del catálogo por EV/aporte del ciclo completo. Es lo que busca «la cuenta que mejor le calza»."""
    out = []
    tv = INSTRUMENTS[inst]["tick_value"]
    for r in catalog_rules:
        s = R.strategy_from_ticks(inst, sigma_ticks, sigma_ticks, 0.5 * (1 + z_gross), trades_per_day)
        from edgelab.propfirm.ev import report
        rep = report(r, s, n_paths=n_paths, eval_days=400)
        out.append(dict(cuenta=r.key, verificada=r.verified, ev=rep["real"]["ev"], ev_se=rep["real"]["ev_se"], aporte=rep["aporte_estrategia"], p_pass=rep["real"]["p_pass"], p_payout=rep["real"]["p_payout"],
                        eval_fee=r.eval_fee))
    return sorted(out, key=lambda x: -x["aporte"])
