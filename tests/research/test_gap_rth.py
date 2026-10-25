import numpy as np
import pandas as pd

from edgelab.research import gap_rth as X


def _ctx(dias=40, seed=0, cierra=False, gap=40.0):
    """M1 sintético en hora de Nueva York (EDT fijo, UTC−4: muestra de junio), 3 ticks por vela (apertura, medio, cierre). Cada día
    abre con un salto de ±`gap` a las 09:29; con `cierra` el precio vuelve linealmente al cierre previo entre 09:30 y 10:30."""
    rng = np.random.default_rng(seed); t, o, h, l, c, tpx = [], [], [], [], [], []; p = 1000.0; prev = p
    d0 = pd.Timestamp("2024-06-03").value // 10**9
    for k in range(dias):
        dia = d0 + 86400 * k
        if pd.Timestamp(dia, unit="s").dayofweek >= 5: continue
        salto = gap * rng.choice([-1, 1])
        for m in range(9 * 60, 16 * 60):
            oo = p
            if m == 9 * 60 + 29: p = prev + salto
            elif cierra and 9 * 60 + 30 <= m < 10 * 60 + 30: p = p + (prev - (prev + salto)) / 60 + rng.normal(0, 0.05)
            else: p = p + rng.normal(0, 0.5)
            mid = (oo + p) / 2
            t.append(dia + 4 * 3600 + 60 * m + 60); o.append(oo); h.append(max(oo, p)); l.append(min(oo, p)); c.append(p)
            tpx += [oo, mid, p]
        prev = p
    n = len(t)
    return dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h), l=np.array(l), c=np.array(c), tpx=np.array(tpx),
                tstart=np.arange(0, 3 * n + 1, 3, dtype=np.int64), ses=(np.array(t) // 86400).astype(np.int64), tick=0.01)


def test_dias_y_atr_causal():
    D = X.dias(_ctx())
    assert (D.c929.notna()).all() and D.atr.iloc[: X.ATR_N].isna().all()            # el ATR usa sólo los 14 días previos
    assert np.allclose(D.cierre_prev.iloc[1:].to_numpy(), D.cierre.iloc[:-1].to_numpy())


def test_plantado_gana_y_ruido_no():
    con = X.operaciones(_ctx(cierra=True, seed=1)); sin = X.operaciones(_ctx(cierra=False, seed=1))
    c = (0.15, 1.0, 999, 0.0)
    a = con[con.celda == c]; b = sin[sin.celda == c]
    assert len(a) > 10 and (a.motivo == 2).mean() > 0.9 and a.bruto.mean() > 30        # el gap se cierra: objetivo
    assert abs(b.bruto.mean()) < 15                                                    # paseo aleatorio: sin ventaja


def test_lado_contrario_al_gap_y_stop():
    O = X.operaciones(_ctx(cierra=False, seed=2))
    assert (np.sign(O.gap) == -O.lado).all()
    st = O[O.celda.map(lambda c: c[3] == 1.0)]
    assert (st[st.motivo == 1].bruto <= -st[st.motivo == 1].gap.abs() + 1e-9).all()  # el stop pierde al menos un gap
