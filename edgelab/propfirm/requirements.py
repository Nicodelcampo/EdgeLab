"""Requisitos que una estrategia de EdgeLab debe cumplir para que una cuenta de prop firm tenga EV > 0.

Invierte el simulador: para un bracket (TP/SL en ticks), un instrumento (valor del tick, costo), un tamaño y una
cadencia, busca por bisección la tasa de acierto mínima con EV = 0 (y con un EV objetivo) y la traduce a
**ventaja neta por trade en ticks**. Es la cifra que un pre-registro de EdgeLab tiene que superar (con IC inferior > 0)
para que valga la pena llevar la estrategia a esa cuenta. También barre tamaño × cadencia para mostrar dónde la
geometría de la cuenta ayuda o castiga (Hall 2026: la evaluación premia cadencia alta y tamaño agresivo; la fondeada
los castiga).
"""
from __future__ import annotations

from dataclasses import replace

from .ev import Strategy, simulate
from .rules import Rules

# valor del tick (USD) y costo agresivo de ida y vuelta por contrato (USD). Costos: IVC 2026-09-26 (ES 2,4 t) y
# Hall 2026 (micro ≈ 1,12 pt de fricción); ajustables. No transportar costos entre instrumentos sin medirlos.
INSTRUMENTS = {
    "ES": dict(tick_value=12.5, cost_rt=30.0),
    "MES": dict(tick_value=1.25, cost_rt=3.0),
    "NQ": dict(tick_value=5.0, cost_rt=32.0),
    "MNQ": dict(tick_value=0.5, cost_rt=3.2),
    "YM": dict(tick_value=5.0, cost_rt=24.0),
    "MYM": dict(tick_value=0.5, cost_rt=2.4),
}


def strategy_from_ticks(inst: str, tp_ticks: float, sl_ticks: float, p_win: float, trades_per_day: int = 2,
                        contracts: int = 1, cost_rt: float | None = None) -> Strategy:
    spec = INSTRUMENTS[inst]
    tv = spec["tick_value"]
    return Strategy(p_win=p_win, tp=tp_ticks * tv, sl=sl_ticks * tv,
                    cost_rt=spec["cost_rt"] if cost_rt is None else cost_rt,
                    trades_per_day=trades_per_day, contracts=contracts)


def min_win_rate(rules: Rules, base: Strategy, ev_target: float = 0.0, lo: float | None = None, hi: float = 0.95,
                 tol: float = 0.002, **kw) -> float:
    """Tasa de acierto mínima con EV >= ev_target (bisección sobre el simulador)."""
    lo = base.sl / (base.tp + base.sl) - 0.15 if lo is None else lo
    lo = max(lo, 0.01)
    if simulate(rules, replace(base, p_win=hi), **kw)["ev"] < ev_target:
        return float("nan")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if simulate(rules, replace(base, p_win=mid), **kw)["ev"] >= ev_target:
            hi = mid
        else:
            lo = mid
    return hi


def requirement(rules: Rules, inst: str, tp_ticks: float, sl_ticks: float, trades_per_day: int = 2,
                contracts: int = 1, ev_target: float = 0.0, **kw) -> dict:
    """Ventaja neta mínima por trade (ticks y USD por contrato) para EV >= ev_target en esa cuenta."""
    base = strategy_from_ticks(inst, tp_ticks, sl_ticks, 0.5, trades_per_day, contracts)
    p = min_win_rate(rules, base, ev_target=ev_target, **kw)
    s = replace(base, p_win=p) if p == p else base
    edge_usd = s.edge_per_trade() if p == p else float("nan")
    p0 = base.sl / (base.tp + base.sl)
    return dict(firma=rules.key, verificada=rules.verified, instrumento=inst, tp_ticks=tp_ticks, sl_ticks=sl_ticks,
                trades_por_dia=trades_per_day, contratos=contracts, ev_objetivo=ev_target,
                acierto_minimo=p, acierto_sin_ventaja=p0, exceso_pp=(p - p0) * 100 if p == p else float("nan"),
                ventaja_neta_min_usd=edge_usd,
                ventaja_neta_min_ticks=edge_usd / INSTRUMENTS[inst]["tick_value"] if p == p else float("nan"))


def sizing_sweep(rules: Rules, base: Strategy, contracts=(1, 2, 3, 5), cadences=(1, 2, 4, 8), **kw) -> list[dict]:
    """EV del ciclo completo por tamaño y cadencia, a ventaja fija. Muestra el empuje de la geometría."""
    out = []
    for k in contracts:
        for n in cadences:
            r = simulate(rules, replace(base, contracts=k, trades_per_day=n), **kw)
            out.append(dict(contratos=k, trades_por_dia=n, p_pass=r["p_pass"], p_payout=r["p_payout"], ev=r["ev"]))
    return out


def gate(rules: Rules, inst: str, tp_ticks: float, sl_ticks: float, trades_per_day: int, net_ticks_point: float,
         net_ticks_lo: float, **kw) -> dict:
    """Compuerta para un candidato de EdgeLab: evalúa la cuenta con la ventaja **en el límite inferior de su IC**
    (no en el punto), y exige EV > 0 y aporte sobre el control de ventaja cero > 0. Un candidato cuya ventaja sólo
    paga en el valor puntual no pasa: la cuenta amplifica una ventaja real, no la crea."""
    from .ev import report
    tv = INSTRUMENTS[inst]["tick_value"]; c_t = INSTRUMENTS[inst]["cost_rt"] / tv
    out = {}
    for tag, net in (("punto", net_ticks_point), ("ic_inferior", net_ticks_lo)):
        p = (net + c_t + sl_ticks) / (tp_ticks + sl_ticks)
        rep = report(rules, strategy_from_ticks(inst, tp_ticks, sl_ticks, p, trades_per_day=trades_per_day), **kw)
        out[tag] = dict(ticks_netos=net, p_win=p, ev=rep["real"]["ev"], ev_se=rep["real"]["ev_se"],
                        aporte=rep["aporte_estrategia"], p_pass=rep["real"]["p_pass"], p_payout=rep["real"]["p_payout"])
    lo = out["ic_inferior"]
    out["pasa"] = bool(lo["ev"] - 2 * lo["ev_se"] > 0 and lo["aporte"] > 0)
    out["cuenta"] = rules.key; out["verificada"] = rules.verified
    return out
