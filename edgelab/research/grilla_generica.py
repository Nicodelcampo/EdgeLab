"""Conductor GENÉRICO de grilla masiva (2026-10-23): cualquier experimento de «disparos × perillas × ejecuciones» corre igual.

Pedido de Nico: que el agente del Debian pueda diseñar sus propias corridas de barrido (con los indicadores con paridad o con
indicadores propios) sin reescribir el conductor. Un EXPERIMENTO es un módulo chico con:
  NOMBRE                      str
  disparos(ctx) -> DataFrame  una fila por decisión: columna `k` (vela M1 de decisión) + variables que usan SÓLO el pasado de k
  VARIABLES                   [Variable]: cómo se discretiza cada perilla
  EJECUCIONES                 lista de tuplas (entrada, objetivo, stop, BE, ...: lo que el experimento necesite)
  niveles(fila, ej, ctx)      -> None | (start, limite, s, entrada, stop, objetivo, be)   (limite: 0 cierre, 1 límite, 2 tick siguiente)
  EJES_ORDINALES              índices de perilla para la meseta (la ejecución es siempre la última perilla)
  BASE (opcional)             {nombre_perilla: nivel}: celda de referencia para las marginales de la indagación
ctx (lo arma `contexto_m1`): o,h,l,c,v por vela M1, t (cierre, s), ses, seg, tpx/tstart (ticks por vela), vp_start/vp_px/vp_vol
(perfil de volumen por minuto y precio), tick.

Modos: E0 (sólo disparos y variables: target-free), DESC (tensor -> tamiz FDR -> Romano-Wolf por sesiones en dos canales
`total`/`reciente` -> pistas distintas -> marginales alrededor de BASE), REP (celdas y cortes congelados, sin tamiz).
El simulador es `areas_expansion.simular` (genérico: llenado declarado por operación, ambigüedad M1 resuelta con ticks).
Reglas: docs/research/GUIA_GRILLA_MASIVA.md. Un experimento nuevo trae test_control_ruido y test_control_plantado.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import grilla_masiva as GM

MIN_OPS, MIN_SESIONES, RATIO_MOV_FRICCION = 30, 20, 3.0
MESES_RECIENTES, B_RW, ALFA_RW, K_PISTAS = 3, 200, 0.10, 20


@dataclass(frozen=True)
class Variable:
    """Una perilla. `cuantiles` = k niveles con cortes desde el E0 de la misma fuente (nunca a ojo); `cortes` = fijos con
    significado (p. ej. A/H >= 4, 8, 16); `categoria` = la columna ya es un entero 0..n-1. `piso`: lo que queda debajo del
    primer corte sale de la celda (índice -1). Un dato faltante nunca cae en un nivel real."""
    nombre: str
    columna: str
    modo: str = "grupo"
    cuantiles: int = 0
    cortes: tuple = ()
    categoria: int = 0
    piso: bool = False

    def niveles(self, cortes=None) -> int:
        if self.categoria: return self.categoria
        n = len(cortes if cortes is not None else self.cortes) + 1
        return n - 1 if self.piso else n


def cortes_e0(D, variables) -> dict:
    """Cortes por cuantiles (sólo para las variables `cuantiles`), desde los disparos de la fuente y período del descubrimiento."""
    out = {}
    for v in variables:
        if v.cuantiles:
            x = D[v.columna].to_numpy(float); x = x[np.isfinite(x)]
            out[v.nombre] = [float(np.quantile(x, i / v.cuantiles)) for i in range(1, v.cuantiles)] if len(x) else [np.nan] * (v.cuantiles - 1)
    return out


def discretizar(D, variables, cortes) -> list:
    idx = []
    for v in variables:
        x = D[v.columna].to_numpy(float)
        if v.categoria:
            b = np.where(np.isfinite(x), x, -1).astype(int); b[(b < 0) | (b >= v.categoria)] = -1
        else:
            cs = np.asarray(cortes.get(v.nombre, v.cortes) if v.cuantiles else v.cortes, float)
            b = np.searchsorted(cs, np.where(np.isfinite(x), x, -np.inf), side="right") - (1 if v.piso else 0)
            b = np.where(np.isfinite(x), b, -1)
        idx.append(b.astype(np.int64))
    return idx


def perillas(exp, cortes):
    return [GM.Perilla(v.nombre, v.niveles(cortes.get(v.nombre) if v.cuantiles else None), v.modo) for v in exp.VARIABLES] + \
           [GM.Perilla("ejecución", len(exp.EJECUCIONES), "grupo")]


def n_celdas(exp, cortes=None) -> int:
    """Lo que se registra en el contador global antes de correr."""
    return int(np.prod([p.tamano_celdas() for p in perillas(exp, cortes or {v.nombre: [0.0] * (v.cuantiles - 1) for v in exp.VARIABLES if v.cuantiles})]))


def contexto_m1(bloques, tick):
    from edgelab.research.areas_expansion_run import m1_y_perfil
    t, M, vpp, vpv, vps, tpx, tstart = m1_y_perfil(bloques)
    return dict(t=t, o=M.o.to_numpy(float), h=M.h.to_numpy(float), l=M.l.to_numpy(float), c=M.c.to_numpy(float), v=M.v.to_numpy(float),
                ses=M.ses.to_numpy().astype(np.int64), seg=M.seg.to_numpy(), vp_px=vpp, vp_vol=vpv, vp_start=vps, tpx=tpx, tstart=tstart,
                tick=float(tick))


def simular_ops(exp, D, ctx):
    """Cada (disparo, ejecución) se simula una vez. Devuelve (di, ei, pnl, amb, dist_objetivo)."""
    filas = D.to_dict("records"); ops = []
    for i, r in enumerate(filas):
        for ei, ej in enumerate(exp.EJECUCIONES):
            nv = exp.niveles(r, ej, ctx)
            if nv is not None: ops.append((i, ei) + tuple(nv))
    if not ops: return (np.zeros(0, int),) * 2 + (np.zeros(0),) * 3
    O = np.array(ops, float)
    st0, lim, s, e, sl, tp, be = (O[:, j] for j in range(2, 9))
    pnl, amb = AX.simular(st0.astype(np.int64), s.astype(np.int64), lim.astype(np.int64), e, sl, tp, be.astype(np.int64),
                          ctx["o"], ctx["h"], ctx["l"], ctx["c"], ctx["ses"], ctx["tick"], ctx["tpx"], ctx["tstart"])
    return O[:, 0].astype(int), O[:, 1].astype(int), pnl, amb, np.abs(tp - e)


def ejecuciones_equivalentes(di, ei, pnl, ejecuciones) -> list:
    """Grupos de ejecuciones con EXACTAMENTE el mismo P&L en todos los disparos (perillas muertas: p. ej. un BE que nunca se arma
    porque el objetivo queda antes de 1R). Duplican celdas y pruebas contadas sin agregar información: se publican para
    rediseñar la grilla. Error real de U1-INDAGA (2026-10-23): BE 0/1 idénticos en las 96 ejecuciones."""
    n_d = int(di.max()) + 1 if len(di) else 0; firmas = {}
    for e in range(len(ejecuciones)):
        m = ei == e; v = np.full(n_d, np.nan); v[di[m]] = pnl[m]
        firmas.setdefault(np.round(np.nan_to_num(v, nan=1e18), 9).tobytes(), []).append(e)
    return [[list(ejecuciones[e]) for e in g] for g in firmas.values() if len(g) > 1]


def evaluar(cel, cx, *, friccion, extra_adverso, bootstrap=2000):
    from edgelab.funnel.escalera import economia, resumen_sesiones
    P, idx, net, st = cx["perillas"], cx["indices"], cx["net"], cx["st"]
    m = GM.mascara(P, idx, cel) & np.isfinite(net)
    if m.sum() < MIN_OPS: return None
    rs = resumen_sesiones(net[m], cx["ses"][m], n_boot=bootstrap)
    ms = GM.meseta(st, cel, P, cx["ejes"])
    eco = economia(net[m], net[m] - extra_adverso, cx["ses"][m], periodos=cx["mes"][m])
    rel = float(np.median(cx["dist"][m])) / friccion if friccion > 0 else np.inf
    ok = bool(ms["meseta"] and eco["pasa"] and rs["ic"][0] > 0 and rs["n_sesiones"] >= MIN_SESIONES and rel >= RATIO_MOV_FRICCION)
    from edgelab.funnel.escalera import _N, recorte_t
    t_ses = _N.inv_cdf(1 - min(max(rs["p_unilateral"], 1e-12), 1 - 1e-12))
    rc = recorte_t(t_ses, float(cx.get("n_pruebas", 1)))                # error 11: lo mejor de muchas celdas siempre baja fuera de muestra
    return dict(celda=list(cel), n=int(m.sum()), media_neta=float(net[m].mean()), sesiones=rs["n_sesiones"], ic90=rs["ic"],
                p_sesiones=rs["p_unilateral"], meseta=bool(ms["meseta"]), economico=eco["duros"], regimen_reciente=eco.get("regimen_reciente"),
                ratio_mov_friccion=round(rel, 2), pasa=ok, n_pruebas=float(cx.get("n_pruebas", 1)), conservado=rc["conservado"],
                media_esperada_fuera=float(net[m].mean()) * rc["conservado"])


MIN_OPS_MARGINAL = 10


def _evaluar_mascara(m, cx, *, bootstrap=500):
    from edgelab.funnel.escalera import resumen_sesiones
    net = cx["net"]; m = m & np.isfinite(net); n = int(m.sum())
    if n < MIN_OPS_MARGINAL: return dict(n=n)
    rs = resumen_sesiones(net[m], cx["ses"][m], n_boot=bootstrap)
    return dict(n=n, media_neta=float(net[m].mean()), sesiones=rs["n_sesiones"], ic90=rs["ic"], p_sesiones=rs["p_unilateral"],
                chica=bool(n < MIN_OPS or rs["n_sesiones"] < MIN_SESIONES))


def marginales(exp, cx, *, friccion, extra_adverso):
    """Indagación (pedido de Nico, 2026-10-23: «no pasar a un P&L sin más: indagar»): desde la celda BASE, mover UNA perilla
    por vez por todos sus niveles. Muestra qué variable mueve el retorno y cuál filtra, en vez de un único ganador.
    `MARGINALES_POOL` (opcional): perillas sobre las que se agrega (unión de niveles) para ganar potencia cuando la pregunta es
    otra variable; se publica con y sin agregación. Desde MIN_OPS_MARGINAL operaciones se informa con `chica` = True si no
    llega a MIN_OPS / MIN_SESIONES (el dato no se esconde, se marca)."""
    base = getattr(exp, "BASE", None)
    if not base: return {}
    P, idx = cx["perillas"], cx["indices"]; nombres = [p.nombre for p in P]
    b = tuple(base.get(n, P[i].tamano_celdas() - 1) for i, n in enumerate(nombres))
    pool = [nombres.index(n) for n in getattr(exp, "MARGINALES_POOL", ()) if n in nombres]

    def masc(celda, agregar=()):
        if not agregar: return GM.mascara(P, idx, celda)
        m = np.zeros(len(cx["net"]), bool)
        import itertools
        for combo in itertools.product(*[range(P[a].tamano_celdas()) for a in agregar]):
            c = list(celda)
            for a, v in zip(agregar, combo): c[a] = v
            m |= GM.mascara(P, idx, tuple(c))
        return m

    out = dict(base=list(b), por_perilla={}, agregado_sobre=[nombres[a] for a in pool])
    for ax, p in enumerate(P):
        filas = []
        for lv in range(p.tamano_celdas()):
            c = list(b); c[ax] = lv
            fila = dict(nivel=lv, **_evaluar_mascara(masc(tuple(c)), cx))
            if pool and ax not in pool: fila["agregado"] = _evaluar_mascara(masc(tuple(c), [a for a in pool if a != ax]), cx)
            filas.append(fila)
        out["por_perilla"][p.nombre] = filas
    return out


def canales(exp, cx, *, friccion, extra_adverso, q=0.10, log=print):
    """Canal `total` y canal `reciente` (últimos MESES_RECIENTES meses, declarados antes): tamiz, Romano-Wolf y pistas."""
    P, idx, net, mes = cx["perillas"], cx["indices"], cx["net"], cx["mes"]
    meses = sorted(set(mes.tolist())); rec = np.isin(mes, meses[-MESES_RECIENTES:]); out = {}
    for nombre, msk in (("total", None), ("reciente", rec)):
        v = net if msk is None else np.where(msk, net, np.nan)
        st = cx["st"] if msk is None else GM.estadisticas(*GM.tensor(P, idx, v))
        cr = GM.criba(st, q=q); rw = GM.romano_wolf(P, idx, v, cx["ses"], st, B=B_RW, alfa=ALFA_RW, seed=7)
        c2 = dict(cx, net=v, st=st)
        ev = [r for r in (evaluar(c, c2, friccion=friccion, extra_adverso=extra_adverso) for c in GM.pistas(st, rw["t"], k=3 * K_PISTAS)) if r]
        for r in ev: r["t_rw"] = float(rw["t"][tuple(r["celda"])])
        rel = sorted([r for r in ev if r["sesiones"] >= MIN_SESIONES and r["ratio_mov_friccion"] >= RATIO_MOV_FRICCION], key=lambda r: -r["ic90"][0])
        out[nombre] = dict(meses=meses if msk is None else meses[-MESES_RECIENTES:], nominadas_fdr=len(cr["nominadas"]), evaluables=cr["evaluables"],
                           nominadas=[list(c) for c in cr["nominadas"][:300]],
                           romano_wolf={k: rw[k] for k in ("B", "alfa", "umbral", "umbrales", "t_max", "p_rw_del_maximo", "nula_max_q")},
                           rechazadas_rw=[list(c) for c in rw["rechazadas"][:300]], n_rechazadas_rw=len(rw["rechazadas"]), pistas=rel[:K_PISTAS],
                           nulo=GM.resumen_nulo(st, P, q=q, referencia=friccion))
        log(f"canal {nombre}: FDR {len(cr['nominadas'])}, RW umbral {rw['umbral']:.2f} t_max {rw['t_max']:.2f} rechazadas {len(rw['rechazadas'])}, pistas {len(rel[:K_PISTAS])}")
    return out


def resumen_e0(D, variables, cortes):
    q = lambda s: {p: round(float(np.nanquantile(s, p)), 4) for p in (0.1, 0.25, 0.5, 0.75, 0.9)} if np.isfinite(s).any() else {}
    out = dict(disparos=int(len(D)), sesiones=int(D.ses.nunique()) if "ses" in D else None, cortes=cortes, variables={})
    for v in variables:
        x = D[v.columna].to_numpy(float)
        out["variables"][v.nombre] = dict(faltantes=int((~np.isfinite(x)).sum()), cuantiles=q(x),
                                          **({"conteo": {int(k): int(n) for k, n in zip(*np.unique(x[np.isfinite(x)], return_counts=True))}} if v.categoria else {}))
    return out


def correr(exp, ctx, *, modo, friccion, extra_adverso, cortes=None, celdas=None, q=0.10, log=print):
    t0 = time.time()
    D = exp.disparos(ctx).reset_index(drop=True); log(f"{exp.NOMBRE}: {len(D)} disparos ({time.time() - t0:.0f}s)")
    if "ses" not in D: D["ses"] = ctx["ses"][D.k.to_numpy()]
    cortes = cortes or cortes_e0(D, exp.VARIABLES)
    res = dict(experimento=exp.NOMBRE, modo=modo, E0=resumen_e0(D, exp.VARIABLES, cortes))
    if modo == "E0" or not len(D): return res, D
    if modo == "REP" and not celdas: raise ValueError("REP exige celdas y cortes CONGELADOS del descubrimiento")
    di, ei, pnl, amb, dist = simular_ops(exp, D, ctx)
    res["ejecuciones_equivalentes"] = ejecuciones_equivalentes(di, ei, pnl, exp.EJECUCIONES)
    if res["ejecuciones_equivalentes"]: log(f"AVISO: {len(res['ejecuciones_equivalentes'])} grupos de ejecuciones idénticas (perillas muertas)")
    res["ambiguedad_M1"] = dict(resueltas_con_ticks=int((amb == 1).sum()), sin_ticks_stop=int((amb == 2).sum()), operaciones=int(len(amb)))
    net = pnl - friccion; log(f"operaciones {len(net)}, con llenado {int(np.isfinite(pnl).sum())} ({time.time() - t0:.0f}s)")
    P = perillas(exp, cortes); idx = [b[di] for b in discretizar(D, exp.VARIABLES, cortes)] + [ei]
    mes = pd.to_datetime(ctx["t"][D.k.to_numpy()[di]], unit="s", utc=True).strftime("%Y%m").to_numpy()
    S, Q, C = GM.tensor(P, idx, net); st = GM.estadisticas(S, Q, C)
    cx = dict(perillas=P, indices=idx, net=net, st=st, ses=D.ses.to_numpy()[di], mes=mes, dist=dist, ejes=tuple(getattr(exp, "EJES_ORDINALES", ())),
              k=D.k.to_numpy()[di], t=ctx["t"][D.k.to_numpy()[di]])
    cx["n_pruebas"] = len(celdas) if modo == "REP" else int(st["evaluable"].sum())          # para el recorte de la maldición del ganador
    res.update(operaciones=int(len(net)), con_llenado=int(np.isfinite(pnl).sum()), celdas=int(S.size),
               perillas=[(p.nombre, p.niveles, p.modo) for p in P], ejecuciones=[list(e) for e in exp.EJECUCIONES])
    if modo == "REP":
        res["replica"] = [evaluar(tuple(c), cx, friccion=friccion, extra_adverso=extra_adverso)
                          or dict(celda=list(c), **_evaluar_mascara(GM.mascara(P, idx, tuple(c)), cx), nota=f"< {MIN_OPS} operaciones: no evaluable")
                          for c in celdas]                         # el n real, no 0 (error de reporte del 2026-10-23)
        return res, cx
    res["canales"] = canales(exp, cx, friccion=friccion, extra_adverso=extra_adverso, q=q, log=log)
    res["indagacion"] = marginales(exp, cx, friccion=friccion, extra_adverso=extra_adverso)
    log(f"listo ({time.time() - t0:.0f}s)")
    return res, cx


def operaciones_de(cx, celdas):
    """Serie por operación de cada celda congelada, en orden de tiempo (lo que necesita un seguimiento secuencial: réplica,
    holdout o paper). Columnas: celda (índice en `celdas`), t (cierre de la vela de decisión, s), ses, k, neto."""
    filas = []
    for i, c in enumerate(celdas):
        m = GM.mascara(cx["perillas"], cx["indices"], tuple(c)) & np.isfinite(cx["net"])
        filas.append(pd.DataFrame(dict(celda=i, t=cx["t"][m], ses=cx["ses"][m], k=cx["k"][m], neto=cx["net"][m])))
    return pd.concat(filas).sort_values(["t", "celda"], kind="stable").reset_index(drop=True) if filas else pd.DataFrame()


def para_autopilot(res, fuente):
    """results_flat: pistas como informativas; réplica `/rep/` es lo único que puede contar como acierto."""
    nom = lambda c: "_".join(str(x) for x in c); exp = res.get("experimento", "GRILLA")
    flat = [dict(test=f"{exp}/{fuente}/{nom(r['celda'])}/pista_{k}", p=r["p_sesiones"], evaluable=False, diff=r["media_neta"])
            for k, c in (res.get("canales") or {}).items() for r in c.get("pistas", [])]
    flat += [dict(test=f"{exp}/{fuente}/{nom(r['celda'])}/rep/1", p=r.get("p_sesiones"), evaluable="p_sesiones" in r, diff=r.get("media_neta"))
             for r in res.get("replica", [])]
    return dict(results_flat=flat, schema="grilla_generica_v1")
