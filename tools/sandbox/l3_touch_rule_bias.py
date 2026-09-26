# -*- coding: utf-8 -*-
"""L3 audit: cuando la regla de toque rompe el nulo de la carrera simetrica.

El spec prerange_sweep_v0 afirma que E[r]=0 por geometria bajo difusion sin
drift. Los precios reales no son una difusion: viven en grilla de ticks y saltan.
Con saltos hay SOBREPASO de la barrera, y si el sobrepaso es asimetrico entre las
dos barreras el optional stopping deja de dar 50/50:

    E[X_tau] = 0  =>  p_up*(d + E[over_up]) = p_dn*(d + E[over_dn])

Este script construye martingalas EXACTAS (E[dx]=0 verificable a mano) y mide
E[r] con tres reglas de toque:

  A. CONTENCION -> lo que hace reversion_race() hoy: lo <= target <= hi
  B. CRUCE      -> objetivo abajo: lo <= target; arriba: hi >= target
  C. TICK       -> verdad de terreno: primer tick que alcanza un objetivo

Escenarios (todos martingala de media exactamente 0):
  sym : +1 / -1 con p=1/2
  asym: con prob 1/(k+1) salta +k ticks; si no, baja 1 tick. k=8.
        E[dx] = k/(k+1) - k/(k+1) = 0. Subir raro y grande, bajar frecuente y
        chico: la forma tipica de un mercado real.

El barrido sobre window_bars mueve el ratio d/recorrido_de_barra, que es la
variable que decide si la contencion pierde cruces.
"""
import json
import math
import numpy as np

D_FRAC = 0.5
SEED = 20260814
N_ATTEMPTS = 20000
POST_BARS = 400


def make_path(rng, n, mode, k=8):
    if mode == "sym":
        dx = rng.choice(np.array([-1, 1], dtype=np.int64), size=n)
    else:
        up = rng.random(n) < 1.0 / (k + 1.0)
        dx = np.where(up, k, -1).astype(np.int64)
    return np.cumsum(dx) + 100_000


def race(hi, lo, path, bar, i_sweep, revert, cont, rule):
    n = len(hi)
    rev_is_down = revert < cont
    if rule == "tick":
        seg = path[(i_sweep + 1) * bar:]
        if rev_is_down:
            mr, mc = seg <= revert, seg >= cont
        else:
            mr, mc = seg >= revert, seg <= cont
        ir = int(np.argmax(mr)) if mr.any() else None
        ic = int(np.argmax(mc)) if mc.any() else None
        if ir is None and ic is None:
            return 0.0, False
        if ir is None:
            return -1.0, False
        if ic is None:
            return 1.0, False
        return (0.0 if ir == ic else (1.0 if ir < ic else -1.0)), False
    missed = False
    for j in range(i_sweep + 1, n):
        h, l = hi[j], lo[j]
        if rule == "contain":
            hr, hc = (l <= revert <= h), (l <= cont <= h)
            if not hr and ((rev_is_down and h < revert) or (not rev_is_down and l > revert)):
                missed = True
            if not hc and ((not rev_is_down and h < cont) or (rev_is_down and l > cont)):
                missed = True
        else:
            hr = (l <= revert) if rev_is_down else (h >= revert)
            hc = (h >= cont) if rev_is_down else (l <= cont)
        if hr and hc:
            return 0.0, missed
        if hr:
            return 1.0, missed
        if hc:
            return -1.0, missed
    return 0.0, missed


def one_session(rng, mode, bar, window_bars):
    """Replica la logica exacta del runner sobre un camino sintetico."""
    n_ticks = (window_bars + POST_BARS + 5) * bar
    path = make_path(rng, n_ticks, mode)
    nb = len(path) // bar
    m = path[: nb * bar].reshape(nb, bar)
    hi, lo, cl = m.max(axis=1), m.min(axis=1), m[:, -1]
    w_hi, w_lo = int(hi[:window_bars].max()), int(lo[:window_bars].min())
    rngw = w_hi - w_lo
    if rngw <= 0:
        return None
    first_side = i_sweep = second_side = None
    for j in range(window_bars, nb):
        up, dn = hi[j] >= w_hi, lo[j] <= w_lo
        if first_side is None:
            if up and dn:
                return None                      # first_bar_both_sides
            if up:
                first_side = "upper"
            elif dn:
                first_side = "lower"
            continue
        if (first_side == "upper" and dn) or (first_side == "lower" and up):
            second_side = "lower" if first_side == "upper" else "upper"
            i_sweep = j
            break
    if i_sweep is None:
        return None
    d = int(round(rngw * D_FRAC))            # igual que el runner (banker's, ver D2)
    if d < 1:
        return None
    a = int(cl[i_sweep])                     # anchor = close del 2do barrido
    revert, cont = (a - d, a + d) if second_side == "upper" else (a + d, a - d)
    out = {"d": d, "side": second_side,
           "bar_range": float(np.median(hi[window_bars:] - lo[window_bars:]))}
    for rule in ("contain", "cross", "tick"):
        r, missed = race(hi, lo, path, bar, i_sweep, revert, cont, rule)
        out[rule] = r
        if rule == "contain":
            out["missed"] = missed
    return out


def summarize(rs):
    n = len(rs)
    if not n:
        return None
    mean = sum(rs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in rs) / n)
    se = sd / math.sqrt(n)
    dec = [x for x in rs if x != 0.0]
    p = (sum(1 for x in dec if x > 0) / len(dec)) if dec else None
    return dict(mean_r=round(mean, 5), se=round(se, 5),
                ci95=[round(mean - 1.96 * se, 4), round(mean + 1.96 * se, 4)],
                z=round(mean / se, 2) if se else None,
                frac_resolved=round(len(dec) / n, 4),
                p_rev_decided=round(p, 5) if p is not None else None)


def scenario(name, mode, bar, window_bars):
    rng = np.random.default_rng(SEED)
    acc = {"contain": [], "cross": [], "tick": []}
    ds, brs = [], []
    n_used = n_missed = dis_a = dis_b = 0
    for _ in range(N_ATTEMPTS):
        s = one_session(rng, mode, bar, window_bars)
        if s is None:
            continue
        n_used += 1
        for r in acc:
            acc[r].append(s[r])
        n_missed += 1 if s["missed"] else 0
        dis_a += 1 if s["contain"] != s["tick"] else 0
        dis_b += 1 if s["cross"] != s["tick"] else 0
        ds.append(s["d"])
        brs.append(s["bar_range"])
    d_med = float(np.median(ds)) if ds else None
    br_med = float(np.median(brs)) if brs else None
    return dict(
        escenario=name, mode=mode, bar_ticks=bar, window_bars=window_bars,
        n=n_used, d_median=d_med, bar_range_median=br_med,
        ratio_d_over_bar_range=round(d_med / br_med, 3) if br_med else None,
        frac_missed_cross=round(n_missed / n_used, 4) if n_used else None,
        disagree_contain_vs_tick=round(dis_a / n_used, 4) if n_used else None,
        disagree_cross_vs_tick=round(dis_b / n_used, 4) if n_used else None,
        A_contain=summarize(acc["contain"]),
        B_cross=summarize(acc["cross"]),
        C_tick=summarize(acc["tick"]),
    )


def main():
    out = []
    for name, mode, bar, win in (
        ("1_sym_window60", "sym", 30, 60),
        ("2_asym_window60", "asym", 30, 60),
        ("3_sym_window6_rango_angosto", "sym", 30, 6),
        ("4_asym_window6_rango_angosto", "asym", 30, 6),
        ("5_asym_window3_rango_muy_angosto", "asym", 30, 3),
    ):
        r = scenario(name, mode, bar, win)
        out.append(r)
        print(json.dumps(r), flush=True)
    with open("touch_rule_bias2.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
