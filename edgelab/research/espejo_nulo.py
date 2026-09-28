"""Nulo simulado del espejo (enmienda N1 del pre-registro ESPEJO-NICO-100T, 28/09; reemplaza P(completar)=f).

Target-free por construcción: sólo usa velas ANTERIORES al evento. Para cada evento se simulan trayectorias sin memoria
que conservan lo que el nulo f ignoraba:
- las barreras reales en ticks (A = completar; un tick más allá de B = fallar),
- la regla de toque por mecha y la agregación 25t -> 100t (4 velas de 25t por vela de 100t),
- el horizonte en velas de 100t (3x la ida, recortado por lo que quede de sesión) y la censura como categoría propia.

Cada paso es una vela de 25t remuestreada (i.i.d., con reposición) de las velas previas al evento, como terna
(cierre - apertura, máximo - apertura, mínimo - apertura) en ticks. Las ternas se centran restando la media de
(cierre - apertura) para no imponer deriva. Remuestrear i.i.d. conserva volatilidad y forma intravela, y destruye la memoria.

Convención de signo: el impulso va de B a A; `direction = +1` si A > B. Todo se traduce a "distancia recorrida hacia A".
Si una misma vela de 100t toca A y el extremo más allá de B, el resultado es `ambigua` (se reporta aparte, como en el kernel).
"""
from __future__ import annotations

import numpy as np

BARS_25_PER_100 = 4


def triples_from_bars(open_, high, low, close, tick):
    """Ternas (dC, dH, dL) en ticks de velas de 25t, con dH >= 0 >= dL relativos a la apertura."""
    o = np.asarray(open_, float); h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    return np.column_stack([(c - o) / tick, (h - o) / tick, (l - o) / tick])


def simulate_null(start, a_level, beyond_b_level, direction, triples, horizon_100t, *, n=2000, seed=0,
                  bars_per_step=BARS_25_PER_100):
    """Probabilidades nulas (completa, falla, ambigua, censurada) para un evento.

    start, a_level, beyond_b_level: precios en ticks (enteros o float) sobre la misma serie que el resultado real
    (midquote en el primario). `beyond_b_level` es el primer nivel que cuenta como extremo nuevo más allá de B.
    """
    if horizon_100t <= 0:
        return dict(completa=0.0, falla=0.0, ambigua=0.0, censurada=1.0, n=n)
    t = np.asarray(triples, float)
    if len(t) < 50:
        raise ValueError("menos de 50 velas previas: el nulo no es estimable para este evento")
    t = t.copy(); mean_c = t[:, 0].mean()
    t[:, 0] -= mean_c; t[:, 1] -= mean_c; t[:, 2] -= mean_c          # centra la deriva sin cambiar la forma
    s = float(direction)
    # distancias en el eje "hacia A": d(A) > 0, d(beyond B) < 0
    to_a = (a_level - start) * s; to_b = (beyond_b_level - start) * s
    rng = np.random.default_rng(seed)
    m = int(bars_per_step)                                  # 28/09: 1 = velas de 25t sin agrupar (IPC-NIVEL, CONT)
    steps = horizon_100t * m
    idx = rng.integers(0, len(t), size=(n, steps))
    dc, dh, dl = t[idx, 0], t[idx, 1], t[idx, 2]
    if s < 0:                                                          # en el eje hacia A, máximo y mínimo se invierten
        dc, dh, dl = -dc, -dl, -dh
    opens = np.cumsum(np.concatenate([np.zeros((n, 1)), dc[:, :-1]], axis=1), axis=1)
    hi = (opens + dh).reshape(n, horizon_100t, m).max(2)
    lo = (opens + dl).reshape(n, horizon_100t, m).min(2)
    hit_a = hi >= to_a; hit_b = lo <= to_b
    first = lambda m: np.where(m.any(1), m.argmax(1), horizon_100t)
    fa, fb = first(hit_a), first(hit_b)
    comp = fa < fb; fail = fb < fa; amb = (fa == fb) & (fa < horizon_100t); cens = (fa == fb) & (fa == horizon_100t)
    return dict(completa=float(comp.mean()), falla=float(fail.mean()), ambigua=float(amb.mean()),
                censurada=float(cens.mean()), n=n)
