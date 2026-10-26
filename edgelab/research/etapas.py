"""Etapas del embudo de grilla (2026-10-23): una función por etapa, igual en Kaggle (`tools/kaggle_grilla/embudo_main.py`) que en
local (Debian, datos sellados del holdout). La orquestación y las compuertas están en `edgelab/research/embudo.py`.

Etapa         entra                                   sale
E0            período                                 disparos y variables (target-free) + densidad y régimen por mes
DESC          período                                 tamiz, Romano-Wolf (total/reciente), pistas, nulo, marginales
INDAGA        celda base + cortes + período           marginales alrededor de la celda (una perilla por vez)
REP           celdas + cortes + período (+tope)       réplica por celda + serie por operación
INTEGRIDAD    celdas + cortes + período               alineación (si señal ≠ ejecución), placebo (5 semillas), latencia 1/2/5
TOPES         celdas + cortes + período + topes       réplica por tope
HOLDOUT_CONTEO celdas + cortes + período              SÓLO el número de operaciones (sin P&L): decide cuándo se llegó a N
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import controles as CT
from edgelab.research import grilla_generica as GG
from edgelab.research import grilla_masiva as GM

TOPES_ESTANDAR = [None, ("pts", 50.0), ("pts", 100.0), ("pts", 150.0), ("mult", 2.0), ("mult", 3.0), ("mult", 4.0)]


def _resumen(x, ses):
    from edgelab.funnel.escalera import resumen_sesiones
    x = np.asarray(x, float); ok = np.isfinite(x)
    if ok.sum() < 5: return dict(n=int(ok.sum()))
    rs = resumen_sesiones(x[ok], np.asarray(ses)[ok], n_boot=2000)
    eq = np.cumsum(x[ok])
    return dict(n=int(ok.sum()), media=float(x[ok].mean()), ic90=rs["ic"], p=rs["p_unilateral"], sesiones=rs["n_sesiones"],
                peor=float(x[ok].min()), drawdown_max=float((eq - np.maximum.accumulate(eq)).min()), total=float(x[ok].sum()))


def por_celda(ops, n_celdas, f) -> list:
    """Una entrada por celda congelada, en el orden de `celdas` (índice i = celda i), aunque alguna no tenga operaciones.
    Antes era `[f(g) for _, g in ops.groupby("celda")]`: una celda sin operaciones (p. ej. con latencia o con ejecución en
    otro activo) desaparecía de la lista y las siguientes quedaban corridas un lugar; la compuerta leía la de otra celda."""
    grupos = dict(tuple(ops.groupby("celda"))) if len(ops) else {}
    return [f(grupos[i]) if i in grupos else dict(n=0) for i in range(n_celdas)]


def densidad(ctx, D) -> dict:
    """Por mes: velas, ticks, rango medio diario y disparos. Si los disparos siguen a los ticks y no al rango, es el feed."""
    mes = pd.to_datetime(ctx["t"], unit="s", utc=True).strftime("%Y%m").to_numpy()
    ticks = np.diff(ctx["tstart"]); df = pd.DataFrame(dict(mes=mes, ses=ctx["ses"], h=ctx["h"], l=ctx["l"], ticks=ticks))
    dia = df.groupby("ses").agg(mes=("mes", "first"), rango=("h", "max"), lo=("l", "min"), ticks=("ticks", "sum"))
    dia["rango"] = dia.rango - dia.lo
    m = dia.groupby("mes").agg(dias=("rango", "size"), rango_medio=("rango", "mean"), ticks_dia=("ticks", "mean"))
    if len(D): m["disparos"] = pd.Series(mes[D.k.to_numpy()]).value_counts()
    m = m.fillna(0)
    corr = lambda a: float(np.corrcoef(m[a], m["disparos"])[0, 1]) if "disparos" in m and len(m) > 3 and m[a].std() > 0 and m["disparos"].std() > 0 else None
    return dict(por_mes={k: {c: float(v) for c, v in r.items()} for k, r in m.iterrows()}, corr_disparos_rango=corr("rango_medio"),
                corr_disparos_ticks=corr("ticks_dia"))


def ejecutar(etapa, exp, ctx, *, friccion, extra_adverso, cx_ej=None, params=None, bloques_alineacion=None, log=print) -> dict:
    p = params or {}; celdas = [list(c) for c in p.get("celdas", [])]; cortes = p.get("cortes")
    if etapa == "ANALIZAR":                                                # analizador de estrategias (2026-10-26): el registro se hizo al lanzar
        from edgelab.research import analizador as AN
        class _Hecho:                                                       # el lanzador ya registró las variantes en el contador global
            def ensure(self, *a, **k): return False
        B = AN.barras_de_contexto(cx_ej if cx_ej is not None else ctx)
        return AN.analizar(exp, int(p["desde"]), int(p["hasta"]), registro=_Hecho(), B=B, tick=float((cx_ej or ctx)["tick"]), friccion_pts=friccion)
    if etapa == "PERSIST":                                                 # canasta de régimen: persistencia de toda la grilla (2026-10-26)
        from edgelab.research import persistencia as PE
        return PE.correr(exp, ctx, friccion=friccion, cortes=cortes, cx_ej=cx_ej, log=log, horizontes=p.get("horizontes"),
                         meta_formacion=p.get("meta_formacion"))
    if etapa == "E0":
        res, D = GG.correr(exp, ctx, modo="E0", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, log=log)
        res["densidad"] = densidad(ctx, D); return res
    if etapa == "DESC":
        res, D = GG.correr(exp, ctx, modo="DESC", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, log=log, cx_ej=cx_ej)
        return res
    if etapa == "INDAGA":
        base_viejo = getattr(exp, "BASE", None); nombres = [v.nombre for v in exp.VARIABLES] + ["ejecución"]
        bases = p.get("bases") or [p["base"]]; out = []
        try:
            res, cx = GG.correr(exp, ctx, modo="REP", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, celdas=bases, log=log, cx_ej=cx_ej)
            for b in bases:
                exp.BASE = {n: int(v) for n, v in zip(nombres, b)}
                out.append(dict(base=list(b), indagacion=GG.marginales(exp, cx, friccion=friccion, extra_adverso=extra_adverso)))
        finally:
            exp.BASE = base_viejo
        return dict(por_base=out, indagacion=out[0]["indagacion"], base=out[0]["base"])
    if etapa in ("REP", "HOLDOUT_CONTEO"):
        tope = tuple(p["tope"]) if p.get("tope") else None
        res, cx = GG.correr(exp, ctx, modo="REP", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, celdas=celdas, log=log, cx_ej=cx_ej, tope=tope,
                            resolucion=p.get("resolucion"))              # {nivel, m}: B del bootstrap que resuelve el umbral (2026-10-24)
        if etapa == "HOLDOUT_CONTEO":                                     # sin P&L: sólo cuántas operaciones hay
            return dict(conteo=[int((GM.mascara(cx["perillas"], cx["indices"], tuple(c)) & np.isfinite(cx["net"])).sum()) for c in celdas])
        ops = GG.operaciones_de(cx, celdas)
        res["riesgo"] = por_celda(ops, len(celdas), lambda g: _resumen(g.neto, g.ses))
        from edgelab.research.eventos import diagnostico                     # 2026-10-26: informativo (CPI/NFP/FOMC)
        res["eventos"] = por_celda(ops, len(celdas), lambda g: diagnostico(g.t.to_numpy(), g.neto.to_numpy()))
        res["operaciones"] = ops.to_dict("list"); return res
    if etapa == "TOPES":
        out = {}
        for tp_ in [None if t is None else tuple(t) for t in (p.get("topes") or TOPES_ESTANDAR)]:
            res, cx = GG.correr(exp, ctx, modo="REP", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, celdas=celdas, log=log, cx_ej=cx_ej, tope=tp_)
            ops = GG.operaciones_de(cx, celdas)
            out["sin tope" if tp_ is None else f"{tp_[0]}:{tp_[1]:g}"] = por_celda(
                ops, len(celdas), lambda g: dict(_resumen(g.neto, g.ses), por_mitad=[_resumen(h.neto, h.ses) for h in (g.iloc[:len(g) // 2], g.iloc[len(g) // 2:])]))
        return dict(por_tope=out)
    if etapa == "INTEGRIDAD":
        out = dict(latencia={}, placebo={})
        if cx_ej is not None and bloques_alineacion is not None: out["alineacion"] = CT.alineacion_segundos(*bloques_alineacion)
        for ret in (0, 1, 2, 5):
            res, cx = GG.correr(exp, ctx, modo="REP", friccion=friccion, extra_adverso=extra_adverso, cortes=cortes, celdas=celdas, log=log, cx_ej=cx_ej, retraso=ret)
            ops = GG.operaciones_de(cx, celdas)
            out["latencia"][ret] = por_celda(ops, len(celdas), lambda g: _resumen(g.neto, g.ses))
            if ret == 0:
                sim = cx_ej if cx_ej is not None else ctx
                for i, c in enumerate(celdas):
                    m = GM.mascara(cx["perillas"], cx["indices"], tuple(c)) & np.isfinite(cx["net"])
                    pl = [CT.placebo(cx["O"], m, sim, seed=sd) for sd in range(5)]
                    out["placebo"][i] = [float(np.nanmean(x) - friccion) if np.isfinite(x).any() else float("nan") for x in pl]
        return out
    raise ValueError(f"etapa desconocida: {etapa}")
