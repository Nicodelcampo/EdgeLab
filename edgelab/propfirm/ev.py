"""Monte Carlo del ciclo completo de una cuenta de prop firm y esperanza matemática del participante.

Modelo de estrategia (bracket): cada trade gana `tp` o pierde `sl` (USD por contrato), con probabilidad de acierto
`p_win`, y paga `cost_rt` por contrato por ida y vuelta. Camino intradía del trade (para el piso intradía): el
perdedor baja directo a −sl; el ganador puede retroceder antes hasta −u·sl con u ~ U(0, `mae_win`) y después sube a
+tp. Se opera `trades_per_day` trades por día con `contracts` contratos.

Reglas simuladas (ver `Rules`): objetivo de beneficio, piso de pérdida estático / trailing al cierre / trailing
intradía con bloqueo, límite de pérdida diaria (corta el día o elimina la cuenta), regla de consistencia (ningún día
puede aportar más de `consistency_cap` del beneficio total), días mínimos, cuota periódica, activación, retiros con
días mínimos, beneficio mínimo, fracción retirable, split, tope por retiro y cantidad máxima.

Lo que el reporte siempre incluye (Hall 2026, §2.4): el mismo pipeline con **ventaja cero** (p_win = sl/(tp+sl),
mismos costos y tamaño). Sin ese control, una tasa de pase no dice nada: mezcla el valor de opción de la cuenta con
lo que aporta la estrategia.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from numba import njit

from .rules import Rules

_DD = {"static": 0, "eod_trailing": 1, "intraday_trailing": 2}
_NOCAPS = np.zeros(0, dtype=np.float64)


@dataclass
class Strategy:
    p_win: float
    tp: float                  # USD por contrato
    sl: float                  # USD por contrato
    cost_rt: float             # USD por contrato por ida y vuelta (comisión + slippage)
    trades_per_day: int = 2
    contracts: int = 1
    mae_win: float = 0.5       # retroceso máximo de un ganador antes de ir al TP, como fracción de sl

    def edge_per_trade(self) -> float:
        """Esperanza neta por trade y por contrato, USD."""
        return self.p_win * self.tp - (1 - self.p_win) * self.sl - self.cost_rt

    def zero_edge(self) -> "Strategy":
        """Mismo bracket, tamaño y costos, sin ventaja bruta."""
        d = asdict(self); d["p_win"] = self.sl / (self.tp + self.sl)
        return Strategy(**d)


@njit(cache=True)
def _stage(rng_u, ptr, n_days, p_win, tp, sl, cost, n_tr, k, mae, target, max_loss, ddk, lock, dll, dll_fail,
           cons, min_days, funded, pay_min_days, pay_min_profit, pay_frac, split, pay_cap, pay_max,
           pay_caps, pay_min_amt, day_min_profit, buffer, basis_total, pay_cons, close_at_max):
    """Simula una etapa. Evaluación (funded=0): devuelve (1 pase / 0 falla / -1 horizonte, días, 0).
    Fondeada (funded=1): devuelve (n retiros, días, suma de pagos al participante). `rng_u` es un vector de
    uniformes compartido; `ptr` el índice de arranque."""
    bal = 0.0; peak = 0.0; floor = -max_loss; locked = False
    best_day = 0.0; total_green = 0.0; days = 0
    cycle_start = 0.0; days_in_cycle = 0; n_pay = 0; paid = 0.0; best_cycle = 0.0
    for d in range(n_days):
        day_pnl = 0.0; days += 1
        for t in range(n_tr):
            u1 = rng_u[ptr]; ptr += 1
            u2 = rng_u[ptr]; ptr += 1
            win = u1 < p_win
            # mínimo intradía del trade (para el piso intradía y el límite diario)
            dip = -sl * k if not win else -(u2 * mae) * sl * k
            if bal + dip <= floor:
                return (0 if funded == 0 else n_pay), days, paid
            if dll > 0 and day_pnl + dip <= -dll:
                if dll_fail == 1:
                    return (0 if funded == 0 else n_pay), days, paid
                pnl = max(dip, -dll - day_pnl)            # el broker corta en el límite
                bal += pnl - cost * k; day_pnl += pnl - cost * k
                break
            pnl = (tp if win else -sl) * k - cost * k
            bal += pnl; day_pnl += pnl
            if ddk == 2 and not locked:                   # intradía: el pico cuenta el flotante a favor
                if bal > peak:
                    peak = bal; floor = max(floor, peak - max_loss)
            if bal <= floor:
                return (0 if funded == 0 else n_pay), days, paid
            if funded == 0 and bal >= target and cons <= 0 and days >= min_days:
                return 1, days, 0.0
        # cierre del día
        if ddk == 1 and not locked and bal > peak:
            peak = bal; floor = max(floor, peak - max_loss)
        if lock > 0 and not locked and bal >= lock:
            locked = True; floor = max(floor, 0.0 + (lock - max_loss if lock - max_loss > 0 else 0.0))
        if day_pnl > 0:
            total_green += day_pnl
            if day_pnl > best_day:
                best_day = day_pnl
        if funded == 0:
            if bal >= target and days >= min_days and (cons <= 0 or best_day <= cons * bal):
                return 1, days, 0.0
        else:
            # día que cuenta para el retiro: cualquiera si no hay umbral, o el que gana al menos `day_min_profit`
            if day_min_profit <= 0 or day_pnl >= day_min_profit:
                days_in_cycle += 1
            if day_pnl > best_cycle:
                best_cycle = day_pnl
            prof = bal - cycle_start
            ok = days_in_cycle >= pay_min_days and prof >= pay_min_profit and prof > 0
            if ok and pay_cons > 0 and best_cycle > pay_cons * prof:   # consistencia desde el último retiro
                ok = False
            if ok:
                base = bal if basis_total == 1 else prof
                gross = base * pay_frac
                room = bal - buffer                                 # no se retira el colchón
                if gross > room:
                    gross = room
                cap = pay_cap
                if pay_caps.shape[0] > 0:
                    cap = pay_caps[min(n_pay, pay_caps.shape[0] - 1)]
                if cap > 0 and gross > cap:                         # el tope es sobre el monto pedido
                    gross = cap
                if gross >= pay_min_amt and gross > 0:
                    paid += gross * split; bal -= gross; n_pay += 1
                    cycle_start = bal; days_in_cycle = 0; best_cycle = 0.0
                    if n_pay >= pay_max and close_at_max == 1:
                        return n_pay, days, paid
    return (-1 if funded == 0 else n_pay), days, paid


def simulate(rules: Rules, strat: Strategy, n_paths: int = 20000, eval_days: int = 60, funded_days: int = 120,
             fee_period_days: int | None = None, daily_loss_fails: bool = False, seed: int = 20260926) -> dict:
    """Ciclo completo por intento. Devuelve probabilidades, pagos, costos y EV por intento (USD)."""
    f = rules.funded()
    rng = np.random.default_rng(seed)
    if rules.eval_access_days:                            # acceso en días corridos → días hábiles (~5/7)
        eval_days = min(eval_days, int(rules.eval_access_days * 5 / 7))
    dll_fail = int(daily_loss_fails or rules.daily_loss_mode == "fail")
    caps = np.asarray(rules.payout_caps or [], dtype=np.float64)
    need = 2 * strat.trades_per_day * (eval_days + funded_days) + 8
    passed = np.zeros(n_paths, np.int8); ev_days = np.zeros(n_paths); n_pay = np.zeros(n_paths); paid = np.zeros(n_paths)
    for i in range(n_paths):
        u = rng.random(need)
        r, dd, _ = _stage(u, 0, eval_days, strat.p_win, strat.tp, strat.sl, strat.cost_rt, strat.trades_per_day,
                          strat.contracts, strat.mae_win, rules.profit_target, rules.max_loss, _DD[rules.drawdown_kind],
                          rules.lock_at_profit or 0.0, rules.daily_loss_limit or 0.0, dll_fail,
                          rules.consistency_cap or 0.0, rules.min_trading_days, 0, 0, 0.0, 0.0, 0.0, 0.0, 0,
                          _NOCAPS, 0.0, 0.0, 0.0, 0, 0.0, 1)
        passed[i] = r; ev_days[i] = dd
        if r == 1:
            k, _, pay = _stage(u, 2 * strat.trades_per_day * eval_days, funded_days, strat.p_win, strat.tp, strat.sl,
                               strat.cost_rt, strat.trades_per_day, strat.contracts, strat.mae_win, 1e18, f.max_loss,
                               _DD[f.drawdown_kind], f.lock_at_profit or 0.0, f.daily_loss_limit or 0.0,
                               dll_fail, 0.0, 1, 1, rules.payout_min_days, rules.payout_min_profit,
                               rules.payout_fraction, rules.payout_split, rules.payout_cap or 0.0, rules.payout_max_count,
                               caps, rules.payout_min_amount, rules.payout_day_min_profit, rules.payout_buffer,
                               int(rules.payout_basis == "total"), f.consistency_cap or 0.0,
                               int(rules.close_after_max_payouts))
            n_pay[i] = k; paid[i] = pay
    periods = np.ceil(ev_days / fee_period_days) if fee_period_days else np.ones(n_paths)
    fees = rules.eval_fee * periods + rules.activation_fee * (passed == 1)
    ev = paid - fees
    p_pass = float((passed == 1).mean())
    return dict(p_pass=p_pass, p_fail=float((passed == 0).mean()), p_horizonte=float((passed == -1).mean()),
                p_payout=float((n_pay > 0).mean()), p_payout_si_pasa=float((n_pay[passed == 1] > 0).mean()) if p_pass else 0.0,
                pagos_medios=float(paid.mean()), costo_medio=float(fees.mean()), ev=float(ev.mean()),
                ev_se=float(ev.std() / np.sqrt(n_paths)), dias_eval=float(ev_days.mean()),
                costo_por_fondeada=float(fees.mean() / p_pass) if p_pass else float("inf"),
                techo_geometrico=rules.geometric_ceiling(), edge_por_trade=strat.edge_per_trade() * strat.contracts)


def report(rules: Rules, strat: Strategy, **kw) -> dict:
    """La estrategia y su control de ventaja cero por el mismo pipeline (Hall 2026, §2.4)."""
    real = simulate(rules, strat, **kw)
    zero = simulate(rules, strat.zero_edge(), **kw)
    return dict(firma=rules.key, verificada=rules.verified, estrategia=asdict(strat), real=real, ventaja_cero=zero,
                aporte_estrategia=real["ev"] - zero["ev"])
