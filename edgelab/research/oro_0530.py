"""Oro a las 05:30 UTC (02:30 en UTC−3): exploratorio pedido por Nico el 2026-10-24 («al parecer hay una explosión de volumen»).
Pre-registro: docs/research/oro_0530_20261024/PREREGISTRO_ORO_0530_UTC.md.

Lo único nuevo es la tabla por sesión anclada en UTC. Todo lo demás se reutiliza: velas M1 y ticks por vela de
`grilla_generica.contexto_m1`, bootstrap por sesión, tamiz FDR y MDE de `funnel/escalera`, costos de `edgelab/costos`.
Lo que ya había (`tools/study_slot_effect.py`, `tools/universe_sigma.py`, el barrido horario de la etapa A) ancla las franjas en
hora de Chicago: un hecho fijo en UTC cae a las 00:30 CT en verano y a las 23:30 CT en invierno, y esas grillas lo reparten
entre dos franjas. Hipótesis económica declarada: 05:30 UTC = 13:30 en Beijing, reapertura de la tarde de la Shanghai Gold
Exchange y de SHFE tras la pausa del mediodía (China no cambia de hora; Argentina tampoco).

Precio de un minuto m = apertura de la vela M1 que empieza en m (primer tick del minuto). Una decisión que usa la vela que
cierra en m se ejecuta en la apertura de m (el primer tick después de conocerla): no hay llenado en el extremo ni a ojo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ANCLA = 5 * 60 + 30                   # minuto del día UTC
CONTROL = 4 * 60 + 30                 # una hora antes, para el canal no direccional
HOLDS = (5, 15, 30, 60)
CELDAS = [(f, h) for f in ("deriva", "arranque", "previo", "rango") for h in HOLDS]      # 16 por instrumento y ventana
DIRECCIONALES = ("deriva", "arranque", "previo")


def trimestres(d0: int, d1: int):
    """(desde, hasta) por trimestre calendario dentro de [d0, d1] (YYYYMMDD): los kernels leen de a un trimestre para acotar memoria."""
    for a in range(d0 // 10000, d1 // 10000 + 1):
        for q0, q1 in ((101, 331), (401, 630), (701, 930), (1001, 1231)):
            lo, hi = max(a * 10000 + q0, d0), min(a * 10000 + q1, d1)
            if lo <= hi: yield lo, hi


def minutos_utc(ctx) -> pd.DataFrame:
    """Una fila por vela: día UTC, minuto del día UTC de la APERTURA de la vela, o/h/l/c, volumen, ticks."""
    t0 = ctx["t"].astype(np.int64) - 60                                         # `t` es el cierre (s)
    return pd.DataFrame(dict(dia=t0 // 86400, mdd=(t0 % 86400) // 60, o=ctx["o"], h=ctx["h"], l=ctx["l"], c=ctx["c"], v=ctx["v"],
                             ticks=np.diff(ctx["tstart"]).astype(np.int64), ses=ctx["ses"]))


def perfil(M: pd.DataFrame) -> pd.DataFrame:
    """Target-free. Por minuto del día UTC: mediana entre días de la actividad relativa (ticks y volumen de ese minuto sobre la
    mediana por minuto del mismo día). No mira precios."""
    med = M.groupby("dia")[["ticks", "v"]].transform("median").replace(0, np.nan)
    R = M.assign(ticks_rel=M.ticks / med.ticks, vol_rel=M.v / med.v)
    return R.groupby("mdd")[["ticks_rel", "vol_rel"]].median().reindex(range(1440))


def tabla(M: pd.DataFrame) -> pd.DataFrame:
    """Una fila por día UTC hábil con todo lo que piden las 16 celdas; NaN donde falta una vela (se cuenta, no se rellena)."""
    W = M[(M.mdd >= CONTROL - 30) & (M.mdd <= ANCLA + 5 + max(HOLDS))]
    O = W.pivot_table(index="dia", columns="mdd", values="o", aggfunc="first"); C = W.pivot_table(index="dia", columns="mdd", values="c", aggfunc="last")
    H = W.pivot_table(index="dia", columns="mdd", values="h", aggfunc="max"); L = W.pivot_table(index="dia", columns="mdd", values="l", aggfunc="min")
    T = W.pivot_table(index="dia", columns="mdd", values="ticks", aggfunc="sum"); V = W.pivot_table(index="dia", columns="mdd", values="v", aggfunc="sum")
    col = lambda X, m: X[m] if m in X.columns else pd.Series(np.nan, index=X.index)
    rango = lambda m0, h: pd.concat([col(H, m) for m in range(m0, m0 + h)], axis=1).max(axis=1, skipna=False) - \
                          pd.concat([col(L, m) for m in range(m0, m0 + h)], axis=1).min(axis=1, skipna=False)
    D = pd.DataFrame(index=O.index)
    D["dir_arranque"] = np.sign(col(C, ANCLA + 4) - col(O, ANCLA))            # conocida al cierre de la vela 05:34 (no con el llenado)
    D["dir_previo"] = np.sign(col(C, ANCLA - 1) - col(O, ANCLA - 30))          # conocida al cierre de la vela 05:29
    act = lambda X, a, b: pd.concat([col(X, m) for m in range(a, b)], axis=1).sum(axis=1, min_count=b - a)
    D["burst_ticks"] = act(T, ANCLA, ANCLA + 5) / 5 / (act(T, ANCLA - 10, ANCLA) / 10)
    D["burst_vol"] = act(V, ANCLA, ANCLA + 5) / 5 / (act(V, ANCLA - 10, ANCLA) / 10)
    for h in HOLDS:
        D[f"deriva_{h}"] = col(O, ANCLA + h) - col(O, ANCLA)
        D[f"arranque_{h}"] = D.dir_arranque.replace(0, np.nan) * (col(O, ANCLA + 5 + h) - col(O, ANCLA + 5))
        D[f"previo_{h}"] = D.dir_previo.replace(0, np.nan) * (col(O, ANCLA + h) - col(O, ANCLA))
        with np.errstate(divide="ignore", invalid="ignore"):
            D[f"rango_{h}"] = np.log(rango(ANCLA, h) / rango(CONTROL, h)).replace([np.inf, -np.inf], np.nan)
    dias = pd.to_datetime(D.index.to_numpy() * 86400, unit="s")
    D = D[dias.dayofweek < 5]
    D.insert(0, "fecha", pd.to_datetime(D.index.to_numpy() * 86400, unit="s").strftime("%Y%m%d").astype(int))
    return D.reset_index(drop=True)


def evaluar(D: pd.DataFrame, friccion: float, friccion_adversa: float, n_boot: int = 20000, seed: int = 20261024) -> list:
    """Las 16 celdas sobre una ventana: media bruta por sesión con p BILATERAL (bootstrap de sesiones de escalera), MDE y, en
    las direccionales, neto con la fricción canónica de GC. Una celda sin 30 sesiones no es evaluable: p = 1 (se cuenta)."""
    from edgelab.funnel import escalera as ES
    out = []
    for f, h in CELDAS:
        x = D[f"{f}_{h}"].to_numpy(float); ok = np.isfinite(x); x, ses = x[ok], D.fecha.to_numpy()[ok]
        r = dict(celda=f"{f}_{h}", familia=f, hold=h, n=int(ok.sum()), evaluable=bool(ok.sum() >= 30))
        if not r["evaluable"]: out.append(dict(r, p=1.0)); continue
        a = ES.resumen_sesiones(x, ses, n_boot=n_boot, seed=seed); b = ES.resumen_sesiones(-x, ses, n_boot=n_boot, seed=seed)
        r.update(media=a["media"], ic90=a["ic"], se=a["se"], sd=a["sd_por_op"], acierto=float((x > 0).mean()),
                 p=float(min(1.0, 2 * min(a["p_unilateral"], b["p_unilateral"]))), mde=float(ES.mde(a["se"])))
        if f in DIRECCIONALES:
            lado = 1.0 if a["media"] >= 0 else -1.0                              # el canal económico se lee en el lado observado
            r.update(lado=int(lado), neto_base=float(lado * a["media"] - friccion), neto_adverso=float(lado * a["media"] - friccion_adversa))
        out.append(r)
    return out


# ------------------------------------------------------------------------------------------- ruptura direccionalmente neutra
# Pre-registro: docs/research/oro_0530_20261024/PREREGISTRO_RUPTURA_0530.md. Lo nominado del exploratorio es la EXPANSIÓN (16/16), no la
# dirección (0/48): un bracket la cobra sin elegir el lado. Simulador: edgelab/research/bracket.py (el de VTD-BRACKET), tick a tick.
RUPTURA_HOLDS = (15, 30, 60)
RUPTURA_STOPS = ("opuesto", "medio")              # stop en el otro lado del rango previo, o en su mitad
VENTANA_ENTRADA = 15                              # minutos desde las 05:30 para que se llene una de las dos órdenes


def ruptura(ctx) -> pd.DataFrame:
    """Una fila por (sesión, hold, stop). Rango previo = máximo y mínimo de las velas 05:00–05:29 (conocido al cierre de 05:29); a las
    05:30 se colocan compra stop en máximo + 1 tick y venta stop en mínimo − 1 tick; la primera que se llena cancela la otra (OCO).
    Sin objetivo; salida por tiempo (hold desde la vela del llenado) o por stop. `bruto` en precio (NaN si no se llena)."""
    from edgelab.research.bracket import sim
    M = minutos_utc(ctx); t0 = M.index.to_numpy(); tick = float(ctx.get("tick", 0.01)); tpx = ctx["tpx"]; ts = ctx["tstart"]
    if len(tpx) == 0: return pd.DataFrame()
    tick_bar = np.repeat(np.arange(len(ts) - 1), np.diff(ts)); bar_last = np.maximum(ts[1:] - 1, 0)
    filas = []
    for dia, g in M.groupby("dia"):
        pre = g[(g.mdd >= ANCLA - 30) & (g.mdd < ANCLA)]; a = g[g.mdd == ANCLA]
        if len(pre) < 25 or not len(a): continue                                  # rango previo con al menos 25 de 30 velas
        hi, lo = float(pre.h.max()), float(pre.l.min()); R = hi - lo
        if R <= 2 * tick: continue
        b0 = int(a.index[0]); i0 = int(ts[b0])
        ses = int(ctx["ses"][b0]); ult = int(np.flatnonzero(ctx["ses"] == ses).max())
        fecha = int(pd.to_datetime(dia * 86400, unit="s").strftime("%Y%m%d"))
        if pd.to_datetime(dia * 86400, unit="s").dayofweek >= 5: continue
        for stop in RUPTURA_STOPS:
            sl = R + 2 * tick if stop == "opuesto" else R / 2
            for h in RUPTURA_HOLDS:
                en, d, pnl, mot = sim(tpx, tick_bar, bar_last, int(ts[ult + 1] - 1), i0, b0, hi + tick, lo - tick, sl, 1e12, 0.0, VENTANA_ENTRADA, h)
                filas.append(dict(fecha=fecha, stop=stop, hold=h, rango=R, entro=bool(en), lado=int(d), motivo=int(mot), bruto=float(pnl) if en else np.nan))
    return pd.DataFrame(filas)
