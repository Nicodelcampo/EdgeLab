"""U1-CRUZADO (2026-10-23): la señal U1 se calcula sobre USATECH (zonas LUX-IMB del CFD) y se opera en NQ.

Idea de Nico: «como se mueven parecido, podría aplicar la estrategia en el USATECH y operar en el NQ». Manifiesto:
docs/research/areas_expansion_20261022/u1/MANIFIESTO_U1_CRUZADO.md.

Traslado de niveles: en la vela de decisión k (cierre del minuto t), base = cierre NQ(t) − cierre USATECH(t). Objetivo y stop
se trasladan sumando la base y se redondean al tick de NQ (el stop, hacia afuera: nunca más favorable). Se entra en el primer
tick de la vela NQ siguiente y todo se resuelve con NQ (orden de ticks si una vela toca stop y objetivo, hueco al precio real,
fricción canónica de NQ). Una señal sin vela NQ en ese minuto (fuera de la sesión CME) no se opera y se cuenta.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U

CELDA_U1 = dict(ni=0, xi=1, ah_min=8.0)                     # N >= 3, x = 0,25, A/H >= 8 (U1 tal cual)
EJECUCIONES = (("E1A", "T1", "S3"), ("E1A", "T3", "S3"))     # «objetivo: el borde cercano o el lejano»


def senales(ctx_us) -> pd.DataFrame:
    D = U.disparos(ctx_us)
    if not len(D): return D
    return D[(D.ni == CELDA_U1["ni"]) & (D.xi == CELDA_U1["xi"]) & (D.A_H >= CELDA_U1["ah_min"])].reset_index(drop=True)


TOPES = [None, ("pts", 50.0), ("pts", 75.0), ("pts", 100.0), ("pts", 150.0), ("mult", 2.0), ("mult", 3.0), ("mult", 4.0)]


def aplicar_tope(e: float, s: int, st: float, tp: float, tope, tick: float) -> float:
    """Tope de pérdida por construcción: el stop no puede quedar más lejos que `tope` de la entrada (en puntos, o en múltiplos
    de la distancia al objetivo). Sin tope (None) = stop original de U1 (más allá del extremo). Redondeo siempre hacia la entrada
    (el tope nunca se afloja por redondeo)."""
    if tope is None: return st
    kind, v = tope; d_max = v if kind == "pts" else v * abs(tp - e)
    if abs(e - st) <= d_max: return st
    st2 = e - s * d_max
    return np.ceil(st2 / tick) * tick if s == 1 else np.floor(st2 / tick) * tick


def operar(ctx_us, ctx_nq, S=None, retraso: int = 0, tope=None) -> pd.DataFrame:
    """Una fila por (señal, ejecución): base, niveles en NQ, P&L bruto en puntos de NQ (NaN = sin llenado) y motivo si no se opera.
    `retraso` (minutos): la misma orden entra `retraso` velas de NQ más tarde, con los mismos niveles; si en el medio el precio ya
    tocó el objetivo o el stop, no se opera (prueba de latencia: un edge real se degrada suave, no desaparece con 1 minuto)."""
    S = senales(ctx_us) if S is None else S
    t_nq = ctx_nq["t"]; tick = ctx_nq["tick"]; filas = []
    for r in S.to_dict("records"):
        k = int(r["k"]); t = ctx_us["t"][k]; j = int(np.searchsorted(t_nq, t))
        base = None if j >= len(t_nq) or t_nq[j] != t else float(ctx_nq["c"][j] - ctx_us["c"][k])
        d = int(r["lado"]); s = -d; borde, lejos = (r["hi"], r["lo"]) if d == 1 else (r["lo"], r["hi"])
        for en, ob, sl in EJECUCIONES:
            fila = dict(k_us=k, t=t, ses=int(ctx_us["ses"][k]), lado=d, ejecucion=f"{en}/{ob}/{sl}", base=base)
            if base is None: filas.append(dict(fila, motivo="sin vela NQ en ese minuto")); continue
            tp = np.round(((borde if ob == "T1" else lejos) + base) / tick) * tick
            st = r["E"] + base - s * tick
            st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick          # stop hacia afuera
            jj = j + retraso
            if jj >= len(t_nq) or ctx_nq["ses"][jj] != ctx_nq["ses"][j]: filas.append(dict(fila, motivo="retraso fuera de la sesión")); continue
            if retraso:
                hi, lo = ctx_nq["h"][j + 1:jj + 1].max(), ctx_nq["l"][j + 1:jj + 1].min()
                if (s == 1 and (hi >= tp or lo <= st)) or (s == -1 and (lo <= tp or hi >= st)):
                    filas.append(dict(fila, motivo="resolvió antes de entrar")); continue
            e = float(ctx_nq["c"][jj]); st = aplicar_tope(e, s, st, tp, tope, tick)
            if (e - tp) * -s < tick or (e - st) * s < tick: filas.append(dict(fila, motivo="niveles no válidos en NQ")); continue
            filas.append(dict(fila, j_nq=jj, entrada_plan=e, tp=tp, stop=st, motivo=""))
    F = pd.DataFrame(filas)
    if not len(F): return F
    ok = F.motivo.eq("").to_numpy(); F["bruto"] = np.nan; F["amb"] = 0
    if ok.any():
        g = F[ok]
        pnl, amb = AX.simular(g.j_nq.to_numpy(np.int64), np.where(g.lado.to_numpy() == 1, -1, 1).astype(np.int64), np.full(ok.sum(), 2, np.int64),
                              g.entrada_plan.to_numpy(float), g.stop.to_numpy(float), g.tp.to_numpy(float), np.zeros(ok.sum(), np.int64),
                              ctx_nq["o"], ctx_nq["h"], ctx_nq["l"], ctx_nq["c"], ctx_nq["ses"], tick, ctx_nq["tpx"], ctx_nq["tstart"])
        F.loc[ok, "bruto"] = pnl; F.loc[ok, "amb"] = amb
    return F


def placebo(ctx_us, ctx_nq, S=None, seed: int = 0, separacion_min: int = 30) -> pd.DataFrame:
    """Control: por cada señal real, un momento AL AZAR de la misma sesión (a >= `separacion_min` minutos de la señal) y una
    dirección al azar, con la MISMA geometría (distancia al objetivo y al stop) trasladada a NQ. Sin contenido en la señal debe
    dar ≈ −fricción. Si da parecido a la estrategia, el resultado viene de la geometría (o de un sesgo del simulador), no de U1."""
    S = senales(ctx_us) if S is None else S; rng = np.random.default_rng(seed)
    ses_nq = ctx_nq["ses"]; tick = ctx_nq["tick"]; filas = []
    for r in S.to_dict("records"):
        k = int(r["k"]); d = int(r["lado"]); borde, lejos = (r["hi"], r["lo"]) if d == 1 else (r["lo"], r["hi"])
        j0 = int(np.searchsorted(ctx_nq["t"], ctx_us["t"][k]))
        if j0 >= len(ses_nq): continue
        cand = np.flatnonzero((ses_nq == ses_nq[j0]) & (np.abs(np.arange(len(ses_nq)) - j0) >= separacion_min))
        cand = cand[cand < len(ses_nq) - 1]
        if not len(cand): continue
        j = int(rng.choice(cand)); s = int(rng.choice([-1, 1])); e = float(ctx_nq["c"][j]); c_us = float(ctx_us["c"][k])
        for en, ob, sl in EJECUCIONES:
            dtp = abs((borde if ob == "T1" else lejos) - c_us); dst = abs(r["E"] - c_us) + tick
            tp = np.round((e + s * dtp) / tick) * tick; st = e - s * dst
            st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick
            if dtp < tick: continue
            filas.append(dict(k_us=k, j_nq=j, lado_placebo=s, ejecucion=f"{en}/{ob}/{sl}", entrada_plan=e, tp=tp, stop=st, ses=int(ses_nq[j])))
    F = pd.DataFrame(filas)
    if not len(F): return F
    pnl, _ = AX.simular(F.j_nq.to_numpy(np.int64), F.lado_placebo.to_numpy(np.int64), np.full(len(F), 2, np.int64), F.entrada_plan.to_numpy(float),
                        F.stop.to_numpy(float), F.tp.to_numpy(float), np.zeros(len(F), np.int64), ctx_nq["o"], ctx_nq["h"], ctx_nq["l"], ctx_nq["c"],
                        ses_nq, tick, ctx_nq["tpx"], ctx_nq["tstart"])
    F["bruto"] = pnl
    return F


def alineacion_segundos(bloques_us, bloques_nq, max_dias: int = 30, lags=range(-20, 21)) -> dict:
    """Correlación de retornos por segundo entre el CFD y NQ en desfasajes de -20 a +20 s (lag > 0: NQ va detrás del CFD).
    Con relojes alineados el pico está en 0 (o NQ apenas adelante: el futuro lidera al CFD). Un pico con el CFD ADELANTADO
    varios segundos sería sospecha de look-ahead en la señal."""
    def serie(bloques):
        out = []
        for i, b in enumerate(bloques):
            if i >= max_dias: break
            s = pd.Series(b.px.to_numpy(float), index=b.ts_ns.to_numpy() // 1_000_000_000)
            out.append(s.groupby(level=0).last())
        return pd.concat(out) if out else pd.Series(dtype=float)
    a, b = serie(bloques_us), serie(bloques_nq)
    idx = a.index.intersection(b.index)
    if len(idx) < 1000: return dict(segundos_comunes=int(len(idx)))
    grid = np.arange(idx.min(), idx.max() + 1)
    ra = a.reindex(grid).ffill().diff(); rb = b.reindex(grid).ffill().diff()
    viva = pd.Series(grid, index=grid).isin(idx)                          # sólo segundos con trades en los dos
    corr = {}
    for L in lags:
        x, y = ra, rb.shift(-L)
        m = viva & x.notna() & y.notna()
        corr[int(L)] = float(np.corrcoef(x[m], y[m])[0, 1]) if m.sum() > 100 else float("nan")
    pico = max(corr, key=lambda k: corr[k] if np.isfinite(corr[k]) else -9)
    return dict(segundos_comunes=int(len(idx)), corr=corr, pico_lag_s=pico,
                lectura="pico en 0 o negativo (NQ lidera): sin look-ahead" if pico <= 0 else "pico positivo: el CFD adelanta a NQ, revisar relojes")


def operar_propio(ctx_us, S=None, tope=None) -> pd.DataFrame:
    """Las mismas señales operadas en el propio USATECH (para períodos sin NQ), con el mismo tope que en NQ."""
    S = senales(ctx_us) if S is None else S; filas = []
    for r in S.to_dict("records"):
        for en, ob, sl in EJECUCIONES:
            nv = U.niveles(r, (en, ob, sl, 0), ctx_us)
            if nv is None: continue
            k, lim, s, e, st, tp, be = nv
            filas.append(dict(k_us=k, ejecucion=f"{en}/{ob}/{sl}", lim=lim, s=s, e=e, st=aplicar_tope(e, s, st, tp, tope, ctx_us["tick"]), tp=tp,
                              ses=int(ctx_us["ses"][k]), t=ctx_us["t"][k]))
    F = pd.DataFrame(filas)
    if not len(F): return F
    pnl, _ = AX.simular(F.k_us.to_numpy(np.int64), F.s.to_numpy(np.int64), F.lim.to_numpy(np.int64), F.e.to_numpy(float), F.st.to_numpy(float),
                        F.tp.to_numpy(float), np.zeros(len(F), np.int64), ctx_us["o"], ctx_us["h"], ctx_us["l"], ctx_us["c"], ctx_us["ses"],
                        ctx_us["tick"], ctx_us["tpx"], ctx_us["tstart"])
    F["bruto"] = pnl
    return F


def densidad_dia(b) -> dict:
    """Target-free, por día de trading: ticks, minutos con datos, velas M1 con hueco (OG/VI de LUX-IMB), rango del día."""
    t = (b.ts_ns.to_numpy() // 60_000_000_000)
    df = pd.DataFrame(dict(t=t, p=b.px.to_numpy())); g = df.groupby("t").p
    o, h, l, c = g.first().to_numpy(), g.max().to_numpy(), g.min().to_numpy(), g.last().to_numpy()
    z = AX.detect(o, h, l, c)
    return dict(ses=int(b.sesion.iloc[0]), ticks=int(len(b)), minutos=int(len(o)), zonas=int(len(z)), rango=float(h.max() - l.min()) if len(h) else 0.0)
