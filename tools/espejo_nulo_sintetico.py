#!/usr/bin/env python3
"""Auditoría 056 §4/§6: ¿es P(completar)=f el nulo correcto con velas 100t, toque por mecha y horizonte censurado?

Target-free: sólo paseo aleatorio simétrico sintético (ningún dato de mercado). Impulso B->A de L ticks; la vuelta está
en la fracción f al CIERRE de la vela del evento. Se resuelve vela a vela (100 trades por vela, cada trade mueve ±1 tick
con prob. p_mov): completa si la mecha toca A, falla si hace un extremo nuevo más allá de B; una vela que toca ambos es
ambigua; sin resolución al agotar el horizonte (3x la duración del impulso en velas) = censurada.
"""
import json, sys
import numpy as np

def sim(L, f, horizon_bars, n=20000, trades_per_bar=100, p_mov=0.3, seed=7):
    rng = np.random.default_rng(seed)
    # A=0, B=L (impulso bajista para fijar ideas); precio al cierre a distancia f*L de B hacia A => x = L*(1-f)
    x0 = int(round(L * (1 - f)))
    steps = rng.choice([-1, 0, 1], p=[p_mov / 2, 1 - p_mov, p_mov / 2], size=(n, horizon_bars, trades_per_bar)).astype(np.int16)
    path = x0 + np.cumsum(steps.reshape(n, -1), axis=1, dtype=np.int32).reshape(n, horizon_bars, trades_per_bar)
    lo, hi = path.min(2), path.max(2)
    hitA, hitB = lo <= 0, hi > L
    first = lambda m: np.where(m.any(1), m.argmax(1), horizon_bars)
    a, b = first(hitA), first(hitB)
    comp = a < b; fail = b < a; amb = (a == b) & (a < horizon_bars); cens = (a == b) & (a == horizon_bars)
    res = comp.sum() / max(1, (comp | fail).sum())
    return dict(L=L, f=f, horizon=horizon_bars, f_efectiva=round(1 - x0 / L, 4), completa=round(comp.mean(), 4),
                falla=round(fail.mean(), 4), ambigua=round(amb.mean(), 4), censurada=round(cens.mean(), 4),
                p_completar_resueltas=round(res, 4), sesgo_vs_f=round(res - (1 - x0 / L), 4))

if __name__ == "__main__":
    out = [sim(L, f, h) for L in (12, 24, 48) for f in (0.5, 0.75) for h in (3, 9, 30)]
    for r in out: print(r)
    json.dump(out, open(sys.argv[1], "w"), indent=1) if len(sys.argv) > 1 else None
