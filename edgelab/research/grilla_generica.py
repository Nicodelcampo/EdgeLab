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
  niveles_lote(D, ej, ctx)    (opcional, eficiencia) lo mismo que `niveles` para TODOS los disparos a la vez: arreglo (len(D), 7)
                              con NaN en la columna 0 donde `niveles` daría None. Si existe, se usa; el preflight exige
                              que coincida exactamente con `niveles` (oráculo) antes de lanzar.
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
MESES_RECIENTES, B_RW, ALFA_RW, K_PISTAS = 3, 1000, 0.10, 20     # B_RW 200 -> 1000 (decisión 2026-10-24)


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


def aplicar_tope(e: float, s: int, st: float, tp: float, tope, tick: float) -> float:
    """Tope de pérdida por construcción: el stop no queda más lejos que `tope` de la entrada (("pts", x) o ("mult", k) × la
    distancia al objetivo). None = stop original. Redondeo siempre hacia la entrada (nunca se afloja)."""
    if tope is None: return st
    kind, v = tope; d_max = v if kind == "pts" else v * abs(tp - e)
    if abs(e - st) <= d_max: return st
    st2 = e - s * d_max
    return np.ceil(st2 / tick) * tick if s == 1 else np.floor(st2 / tick) * tick


def aplicar_tope_lote(e, s, st, tp, tope, tick):
    """`aplicar_tope` para arreglos (misma regla y mismo redondeo; oráculo: test_aplicar_tope_lote_igual_al_escalar)."""
    st = np.asarray(st, float)
    if tope is None: return st.copy()
    e, s, tp = np.asarray(e, float), np.asarray(s, float), np.asarray(tp, float)
    kind, v = tope; d_max = np.full(len(e), float(v)) if kind == "pts" else v * np.abs(tp - e)
    st2 = e - s * d_max
    st2 = np.where(s == 1, np.ceil(st2 / tick) * tick, np.floor(st2 / tick) * tick)
    return np.where(np.abs(e - st) <= d_max, st, st2)


def _trasladar_bucle(O, ctx, cx_ej, retraso):
    """Señal calculada en `ctx` (sensor), orden ejecutada en `cx_ej`: el inicio pasa a la vela del mismo minuto en la ejecución
    (+ `retraso` velas) y los precios se trasladan con la base (cierre ejecución − cierre sensor en ese minuto), redondeados al
    tick de la ejecución, el stop siempre hacia afuera. Si en el retraso el precio ya tocó objetivo o stop, no se opera."""
    t_ej, tk = cx_ej["t"], cx_ej["tick"]; n = len(O); ok = np.zeros(n, bool); O2 = O.copy()
    for r in range(n):
        k = int(O[r, 2]); j = int(np.searchsorted(t_ej, ctx["t"][k]))
        if j >= len(t_ej) or t_ej[j] != ctx["t"][k]: continue
        jj = j + retraso
        if jj >= len(t_ej) - 1 or cx_ej["ses"][jj] != cx_ej["ses"][j]: continue
        base = cx_ej["c"][j] - ctx["c"][k]; s = int(O[r, 4]); e, st, tp = O[r, 5] + base, O[r, 6] + base, O[r, 7] + base
        tp = np.round(tp / tk) * tk; e = np.round(e / tk) * tk
        st = np.floor(st / tk) * tk if s == 1 else np.ceil(st / tk) * tk
        if retraso:
            hi, lo = cx_ej["h"][j + 1:jj + 1].max(), cx_ej["l"][j + 1:jj + 1].min()
            if (s == 1 and (hi >= tp or lo <= st)) or (s == -1 and (lo <= tp or hi >= st)): continue
            if O[r, 3] != 1: e = cx_ej["c"][jj]                       # a mercado: la entrada es la del momento real
        if (e - tp) * -s < tk or (e - st) * s < tk: continue
        O2[r, 2], O2[r, 5], O2[r, 6], O2[r, 7] = jj, e, st, tp; ok[r] = True
    return O2, ok


def _trasladar(O, ctx, cx_ej, retraso):
    """Versión vectorizada de `_trasladar_bucle` (la regla está documentada ahí; oráculo: test_trasladar_igual_al_bucle)."""
    t_ej, tk, n_ej = cx_ej["t"], cx_ej["tick"], len(cx_ej["t"]); O2 = O.copy()
    k = O[:, 2].astype(np.int64); tk_s = ctx["t"][k]; j = np.searchsorted(t_ej, tk_s); jc = np.minimum(j, n_ej - 1)
    ok = (j < n_ej) & (t_ej[jc] == tk_s)
    jj = j + retraso; jjc = np.clip(jj, 0, n_ej - 1)
    ok &= (jj < n_ej - 1) & (cx_ej["ses"][jjc] == cx_ej["ses"][jc])
    base = cx_ej["c"][jc] - ctx["c"][k]; s = O[:, 4].astype(np.int64)
    e, st, tp = O[:, 5] + base, O[:, 6] + base, O[:, 7] + base
    tp = np.round(tp / tk) * tk; e = np.round(e / tk) * tk
    st = np.where(s == 1, np.floor(st / tk) * tk, np.ceil(st / tk) * tk)
    if retraso:
        hi = np.full(len(O), -np.inf); lo = np.full(len(O), np.inf)
        for q in range(1, retraso + 1):
            jq = np.clip(j + q, 0, n_ej - 1); hi = np.maximum(hi, cx_ej["h"][jq]); lo = np.minimum(lo, cx_ej["l"][jq])
        toco = np.where(s == 1, (hi >= tp) | (lo <= st), (lo <= tp) | (hi >= st))
        ok &= ~toco
        e = np.where(O[:, 3] != 1, cx_ej["c"][jjc], e)                 # a mercado: la entrada es la del momento real
    ok &= ~(((e - tp) * -s < tk) | ((e - st) * s < tk))
    O2[ok, 2], O2[ok, 5], O2[ok, 6], O2[ok, 7] = jj[ok], e[ok], st[ok], tp[ok]
    return O2, ok


def _ops_lote(exp, D, ctx):
    """Filas (i, ei, start, limite, s, entrada, stop, objetivo, be) en el MISMO orden que el bucle por disparo y ejecución."""
    partes = []
    for ei, ej in enumerate(exp.EJECUCIONES):
        X = np.asarray(exp.niveles_lote(D, ej, ctx), float)
        if X.shape != (len(D), 7): raise ValueError(f"niveles_lote debe devolver ({len(D)}, 7); devolvió {X.shape}")
        i = np.flatnonzero(np.isfinite(X[:, 0]))
        partes.append(np.column_stack([i, np.full(len(i), ei), X[i]]))
    O = np.concatenate(partes) if partes else np.zeros((0, 9))
    return O[np.lexsort((O[:, 1], O[:, 0]))] if len(O) else O


def ops_por_fila(exp, D, ctx):
    """El camino de referencia (una llamada a `niveles` por disparo y ejecución). Lo usa el oráculo de `niveles_lote`."""
    filas = D.to_dict("records"); ops = []
    for i, r in enumerate(filas):
        for ei, ej in enumerate(exp.EJECUCIONES):
            nv = exp.niveles(r, ej, ctx)
            if nv is not None: ops.append((i, ei) + tuple(nv))
    return np.array(ops, float) if ops else np.zeros((0, 9))


def simular_ops(exp, D, ctx, cx_ej=None, retraso: int = 0, tope=None, devolver_O: bool = False, devolver_barras: bool = False):
    """Cada (disparo, ejecución) se simula una vez. Devuelve (di, ei, pnl, amb, dist_objetivo).
    `devolver_barras` agrega al final (fill, exit): índices de vela en el instrumento de ejecución, -1 sin llenado.
    `cx_ej`: contexto M1 de OTRO instrumento donde se ejecuta (señal en un activo, operación en otro; mismo minuto, base
    trasladada). `retraso`: velas de demora en la entrada (control de latencia). `tope`: pérdida máxima por construcción."""
    O = _ops_lote(exp, D, ctx) if hasattr(exp, "niveles_lote") else ops_por_fila(exp, D, ctx)
    if not len(O):
        return (np.zeros(0, int),) * 2 + (np.zeros(0),) * 3 + ((np.zeros((0, 9)),) if devolver_O else ()) + ((np.zeros(0, np.int64),) * 2 if devolver_barras else ())
    if tope is not None: O[:, 6] = aplicar_tope_lote(O[:, 5], O[:, 4], O[:, 6], O[:, 7], tope, ctx["tick"])
    sim = ctx; ok = np.ones(len(O), bool)
    if cx_ej is not None or retraso:
        O, ok = _trasladar(O, ctx, cx_ej if cx_ej is not None else ctx, retraso); sim = cx_ej if cx_ej is not None else ctx
    pnl = np.full(len(O), np.nan); amb = np.zeros(len(O), np.int8); fb = np.full(len(O), -1, np.int64); xb = fb.copy()
    if ok.any():
        st0, lim, s, e, sl, tp, be = (O[ok, j] for j in range(2, 9))
        p_, a_, f_, x_ = AX.simular_cierre(st0.astype(np.int64), s.astype(np.int64), lim.astype(np.int64), e, sl, tp, be.astype(np.int64),
                                           sim["o"], sim["h"], sim["l"], sim["c"], sim["ses"], sim["tick"], sim["tpx"], sim["tstart"])
        pnl[ok], amb[ok], fb[ok], xb[ok] = p_, a_, f_, x_
    out = (O[:, 0].astype(int), O[:, 1].astype(int), pnl, amb, np.abs(O[:, 7] - O[:, 5]))
    return out + ((O,) if devolver_O else ()) + ((fb, xb) if devolver_barras else ())


def hora_de_barra(t, barras):
    """Cierre (s) de cada vela de `t`; NaN donde `barras` es -1 (sin llenado)."""
    return np.where(barras >= 0, np.asarray(t, float)[np.maximum(barras, 0)], np.nan)


def ejecuciones_equivalentes(di, ei, pnl, ejecuciones) -> list:
    """Grupos de ejecuciones con EXACTAMENTE el mismo P&L en todos los disparos (perillas muertas: p. ej. un BE que nunca se arma
    porque el objetivo queda antes de 1R). Duplican celdas y pruebas contadas sin agregar información: se publican para
    rediseñar la grilla. Error real de U1-INDAGA (2026-10-23): BE 0/1 idénticos en las 96 ejecuciones."""
    n_d = int(di.max()) + 1 if len(di) else 0; firmas = {}
    for e in range(len(ejecuciones)):
        m = ei == e; v = np.full(n_d, np.nan); v[di[m]] = pnl[m]
        firmas.setdefault(np.round(np.nan_to_num(v, nan=1e18), 9).tobytes(), []).append(e)
    return [[list(ejecuciones[e]) for e in g] for g in firmas.values() if len(g) > 1]


def evaluar(cel, cx, *, friccion, extra_adverso, bootstrap=2000, resolucion=None):
    """`resolucion` = {nivel, m} (2026-10-24): el p tiene que poder resolver nivel/m (umbral más exigente del lote en LORD++):
    sube B o usa el p analítico por sesión (`escalera.resumen_resuelto`). Sin resolución, B = `bootstrap` como antes."""
    from edgelab.funnel.escalera import economia, resumen_resuelto
    P, idx, net, st = cx["perillas"], cx["indices"], cx["net"], cx["st"]
    m = GM.mascara(P, idx, cel) & np.isfinite(net)
    if m.sum() < MIN_OPS: return None
    rz = resolucion or {}
    rs = resumen_resuelto(net[m], cx["ses"][m], nivel=rz.get("nivel"), m=int(rz.get("m", 1)), n_boot=bootstrap)
    ms = GM.meseta(st, cel, P, cx["ejes"])
    eco = economia(net[m], net[m] - extra_adverso, cx["ses"][m], periodos=cx["mes"][m])
    rel = float(np.median(cx["dist"][m])) / friccion if friccion > 0 else np.inf
    ok = bool(ms["meseta"] and eco["pasa"] and rs["ic"][0] > 0 and rs["n_sesiones"] >= MIN_SESIONES and rel >= RATIO_MOV_FRICCION)
    from edgelab.funnel.escalera import _N, recorte_t
    t_ses = _N.inv_cdf(1 - min(max(rs["p_unilateral"], 1e-12), 1 - 1e-12))
    rc = recorte_t(t_ses, float(cx.get("n_pruebas", 1)))                # error 11: lo mejor de muchas celdas siempre baja fuera de muestra
    return dict(celda=list(cel), n=int(m.sum()), media_neta=float(net[m].mean()), sesiones=rs["n_sesiones"], ic90=rs["ic"],
                p_sesiones=rs["p_unilateral"], meseta=bool(ms["meseta"]), economico=eco["duros"], regimen_reciente=eco.get("regimen_reciente"),
                ratio_mov_friccion=round(rel, 2), pasa=ok, n_pruebas=float(cx.get("n_pruebas", 1)), n_pruebas_metodo=cx.get("n_pruebas_metodo", "bruto"),
                conservado=rc["conservado"], media_esperada_fuera=float(net[m].mean()) * rc["conservado"],
                n_boot=rs["n_boot"], piso_p=rs["piso_p"], metodo_p=rs["metodo_p"])


MIN_OPS_MARGINAL = 10


def _evaluar_mascara(m, cx, *, bootstrap=500, resolucion=None):
    """`resolucion` = {nivel, m}: en una réplica en lote (PISTAS/OOS) la celda chica también entra a LORD++, así que su p tiene que
    poder resolver nivel/m como las demás (2026-10-25: con B=500 una pista de < 30 operaciones no podía confirmarse nunca)."""
    from edgelab.funnel.escalera import resumen_resuelto
    net = cx["net"]; m = m & np.isfinite(net); n = int(m.sum())
    if n < MIN_OPS_MARGINAL: return dict(n=n)
    rz = resolucion or {}
    rs = resumen_resuelto(net[m], cx["ses"][m], nivel=rz.get("nivel"), m=int(rz.get("m", 1)), n_boot=bootstrap)
    return dict(n=n, media_neta=float(net[m].mean()), sesiones=rs["n_sesiones"], ic90=rs["ic"], p_sesiones=rs["p_unilateral"],
                chica=bool(n < MIN_OPS or rs["n_sesiones"] < MIN_SESIONES), n_boot=rs["n_boot"], piso_p=rs["piso_p"], metodo_p=rs["metodo_p"])


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
    """Canal `total` y canal `reciente` (últimos MESES_RECIENTES meses, declarados antes): tamiz, Romano-Wolf y pistas.
    Se evalúan (2026-10-24, falsos negativos) las top 3·K_PISTAS distintas por t de Romano-Wolf Y TODAS las celdas nominadas por
    el FDR (antes sólo las 60 primeras por t de RW: una nominada fuera de ese corte nunca se evaluaba). `k_evaluadas` declara
    cuántas de cada origen. Las nominadas relevantes van todas a `pistas` (marcadas); las no nominadas, las K_PISTAS mejores."""
    P, idx, net, mes = cx["perillas"], cx["indices"], cx["net"], cx["mes"]
    meses = sorted(set(mes.tolist())); rec = np.isin(mes, meses[-MESES_RECIENTES:]); out = {}
    for nombre, msk in (("total", None), ("reciente", rec)):
        v = net if msk is None else np.where(msk, net, np.nan)
        st = cx["st"] if msk is None else GM.estadisticas(*GM.tensor(P, idx, v))
        cr = GM.criba(st, q=q); rw = GM.romano_wolf(P, idx, v, cx["ses"], st, B=B_RW, alfa=ALFA_RW, seed=7)
        c2 = dict(cx, net=v, st=st)
        por_rw = GM.pistas(st, rw["t"], k=3 * K_PISTAS)
        nom_todas = [tuple(int(x) for x in np.unravel_index(f_, st["n"].shape)) for f_ in np.flatnonzero(cr["q_valores"].ravel() <= q)]
        a_evaluar = list(dict.fromkeys(por_rw + nom_todas))                      # sin repetir, primero el orden por RW
        ev = [r for r in (evaluar(c, c2, friccion=friccion, extra_adverso=extra_adverso) for c in a_evaluar) if r]
        for r in ev:
            r["t_rw"] = float(rw["t"][tuple(r["celda"])])
            # decisión 2026-10-24: la nominación FDR (q 0,10) es compuerta dura de DESC; se marca por pista con el conjunto completo
            # (la lista `nominadas` tiene tope). m_fdr = celdas EVALUABLES (filtrado independiente); `celdas_canal` = todas.
            r.update(canal=nombre, q_fdr=float(cr["q_valores"][tuple(r["celda"])]), nominada_fdr=bool(cr["q_valores"][tuple(r["celda"])] <= q),
                     pi0_fdr=float(cr["pi0"]), m_fdr=int(cr["m"]), m_fdr_sobre=cr["m_sobre"], celdas_canal=int(cr["celdas"]))
        rel = sorted([r for r in ev if r["sesiones"] >= MIN_SESIONES and r["ratio_mov_friccion"] >= RATIO_MOV_FRICCION], key=lambda r: -r["ic90"][0])
        nom_rel = [r for r in rel if r["nominada_fdr"]]
        pistas_canal = nom_rel + [r for r in rel if not r["nominada_fdr"]][:K_PISTAS]
        out[nombre] = dict(meses=meses if msk is None else meses[-MESES_RECIENTES:], nominadas_fdr=int(cr["n_nominadas"]), evaluables=cr["evaluables"],
                           m_fdr=int(cr["m"]), celdas=int(cr["celdas"]), nominadas=[list(c) for c in cr["nominadas"][:300]],
                           k_evaluadas=dict(por_romano_wolf=len(por_rw), nominadas_fdr=len(nom_todas), total=len(a_evaluar), evaluables_30ops=len(ev)),
                           romano_wolf={k: rw[k] for k in ("B", "alfa", "umbral", "umbrales", "t_max", "p_rw_del_maximo", "nula_max_q")},
                           rechazadas_rw=[list(c) for c in rw["rechazadas"][:300]], n_rechazadas_rw=len(rw["rechazadas"]), pistas=pistas_canal,
                           nulo=GM.resumen_nulo(st, P, q=q, referencia=friccion))
        log(f"canal {nombre}: FDR {cr['n_nominadas']} (m {cr['m']} evaluables de {cr['celdas']}), RW umbral {rw['umbral']:.2f} t_max {rw['t_max']:.2f} "
            f"rechazadas {len(rw['rechazadas'])}, evaluadas {len(a_evaluar)}, pistas {len(pistas_canal)} ({len(nom_rel)} nominadas)")
    return out


def resumen_e0(D, variables, cortes):
    q = lambda s: {p: round(float(np.nanquantile(s, p)), 4) for p in (0.1, 0.25, 0.5, 0.75, 0.9)} if np.isfinite(s).any() else {}
    out = dict(disparos=int(len(D)), sesiones=int(D.ses.nunique()) if "ses" in D else None, cortes=cortes, variables={})
    for v in variables:
        x = D[v.columna].to_numpy(float) if v.columna in D else np.array([], float)   # 2026-10-27: 0 disparos sin columnas (U1 en CONTEO)
        out["variables"][v.nombre] = dict(faltantes=int((~np.isfinite(x)).sum()), cuantiles=q(x),
                                          **({"conteo": {int(k): int(n) for k, n in zip(*np.unique(x[np.isfinite(x)], return_counts=True))}} if v.categoria else {}))
    return out


NORMALIZACIONES = ("rango_sesion_previa",)


def escala_ops(metodo: str, ses_ops, ctx_ej) -> np.ndarray:
    """Escala causal por operación (2026-10-26, POTENCIA_MISMOS_DATOS §2): `rango_sesion_previa` = máximo − mínimo de la sesión
    ANTERIOR a la de la operación en el instrumento de ejecución (conocido antes de operar). Sin sesión anterior: NaN (la operación
    queda fuera, como un llenado imposible). Un experimento la activa declarando `NORMALIZAR` en su módulo, antes de correr."""
    if metodo not in NORMALIZACIONES: raise ValueError(f"NORMALIZAR {metodo!r}: {NORMALIZACIONES}")
    s = pd.DataFrame(dict(ses=ctx_ej["ses"], h=ctx_ej["h"], l=ctx_ej["l"])).groupby("ses").agg(h=("h", "max"), l=("l", "min")).sort_index()
    previo = (s.h - s.l).shift(1); previo = previo.where(previo > 0)
    return pd.Series(np.asarray(ses_ops)).map(previo).to_numpy(float)


def correr(exp, ctx, *, modo, friccion, extra_adverso, cortes=None, celdas=None, q=0.10, log=print, cx_ej=None, retraso=0, tope=None,
           resolucion=None):
    t0 = time.time()
    D = exp.disparos(ctx).reset_index(drop=True); log(f"{exp.NOMBRE}: {len(D)} disparos ({time.time() - t0:.0f}s)")
    if "ses" not in D: D["ses"] = np.asarray(ctx["ses"])[D.k.to_numpy().astype(np.intp)] if "k" in D else np.array([], np.intp)   # 2026-10-27 (O13): con 0 disparos `k` no es entera
    if ctx.get("desde_eval") and len(D): D = D[D.ses >= int(ctx["desde_eval"])].reset_index(drop=True)                           # calentamiento previo a `desde_eval` no cuenta disparos ni operaciones
    cortes = cortes or cortes_e0(D, exp.VARIABLES)
    res = dict(experimento=exp.NOMBRE, modo=modo, E0=resumen_e0(D, exp.VARIABLES, cortes))
    if modo == "E0" or not len(D): return res, D
    if modo == "REP" and not celdas: raise ValueError("REP exige celdas y cortes CONGELADOS del descubrimiento")
    di, ei, pnl, amb, dist, O, fb, xb = simular_ops(exp, D, ctx, cx_ej=cx_ej, retraso=retraso, tope=tope, devolver_O=True, devolver_barras=True)
    t_ej = (cx_ej if cx_ej is not None else ctx)["t"]                                      # f y x son velas de la ejecución; k, del sensor
    res["ejecuciones_equivalentes"] = ejecuciones_equivalentes(di, ei, pnl, exp.EJECUCIONES)
    if res["ejecuciones_equivalentes"]: log(f"AVISO: {len(res['ejecuciones_equivalentes'])} grupos de ejecuciones idénticas (perillas muertas)")
    res["ambiguedad_M1"] = dict(resueltas_con_ticks=int((amb == 1).sum()), sin_ticks_stop=int((amb == 2).sum()), operaciones=int(len(amb)))
    net = pnl - friccion; log(f"operaciones {len(net)}, con llenado {int(np.isfinite(pnl).sum())} ({time.time() - t0:.0f}s)")
    if (norm := getattr(exp, "NORMALIZAR", None)):                                         # 2026-10-26: estadístico declarado en el módulo
        esc = escala_ops(norm, D.ses.to_numpy()[di], cx_ej if cx_ej is not None else ctx)
        med = float(np.nanmedian(esc)) if np.isfinite(esc).any() else float("nan")
        net = net / esc; extra_adverso = extra_adverso / med
        res["normalizado"] = dict(metodo=norm, escala_mediana=med, sin_escala=int((~np.isfinite(esc)).sum()),
                                  nota="P&L neto en unidades de la escala; × escala_mediana ≈ puntos (extra_adverso escalado por la mediana)")
    if (ex := getattr(exp, "EXCLUIR_EVENTOS", None)):                                    # 2026-10-26: filtro declarado en el módulo
        from edgelab.research.eventos import TIPOS, cerca
        fuera = cerca(ctx["t"][D.k.to_numpy()[di]], ex.get("antes_min", 15), ex.get("despues_min", 15), tuple(ex.get("tipos", TIPOS)))
        net = np.where(fuera, np.nan, net); res["excluidas_eventos"] = dict(ex, n=int(fuera.sum()))
    P = perillas(exp, cortes); idx = [b[di] for b in discretizar(D, exp.VARIABLES, cortes)] + [ei]
    mes = pd.to_datetime(ctx["t"][D.k.to_numpy()[di]], unit="s", utc=True).strftime("%Y%m").to_numpy()
    S, Q, C = GM.tensor(P, idx, net); st = GM.estadisticas(S, Q, C)
    cx = dict(perillas=P, indices=idx, net=net, st=st, ses=D.ses.to_numpy()[di], mes=mes, dist=dist, ejes=tuple(getattr(exp, "EJES_ORDINALES", ())), O=O,
              k=D.k.to_numpy()[di], t=ctx["t"][D.k.to_numpy()[di]], t_fill=hora_de_barra(t_ej, fb), t_exit=hora_de_barra(t_ej, xb))
    cx["n_pruebas"] = len(celdas) if modo == "REP" else int(st["evaluable"].sum())          # para el recorte de la maldición del ganador
    cx["n_pruebas_metodo"] = "bruto"
    if modo == "REP" and len(celdas) >= 2:                                                  # 2026-10-24: Li-Ji con la matriz sesión x celda
        from edgelab.funnel.escalera import n_efectivo_o_bruto
        ne = n_efectivo_o_bruto(len(celdas), matriz_sesiones(cx, celdas)); cx["n_pruebas"], cx["n_pruebas_metodo"] = ne["n"], ne["metodo"]
    elif modo != "REP":
        res["aviso_n_pruebas"] = "n_pruebas bruto (celdas evaluables): sin matriz de P&L de todas las celdas, Li-Ji no aplicable"
    res.update(operaciones=int(len(net)), con_llenado=int(np.isfinite(pnl).sum()), celdas=int(S.size),
               perillas=[(p.nombre, p.niveles, p.modo) for p in P], ejecuciones=[list(e) for e in exp.EJECUCIONES])
    if modo == "REP":
        res["n_pruebas"] = dict(n=float(cx["n_pruebas"]), metodo=cx["n_pruebas_metodo"], bruto=len(celdas))
        res["replica"] = [evaluar(tuple(c), cx, friccion=friccion, extra_adverso=extra_adverso, resolucion=resolucion)
                          or dict(celda=list(c), **_evaluar_mascara(GM.mascara(P, idx, tuple(c)), cx, resolucion=resolucion), nota=f"< {MIN_OPS} operaciones: no evaluable")
                          for c in celdas]                         # el n real, no 0 (error de reporte del 2026-10-23)
        return res, cx
    res["canales"] = canales(exp, cx, friccion=friccion, extra_adverso=extra_adverso, q=q, log=log)
    res["indagacion"] = marginales(exp, cx, friccion=friccion, extra_adverso=extra_adverso)
    log(f"listo ({time.time() - t0:.0f}s)")
    return res, cx


def matriz_sesiones(cx, celdas):
    """P&L neto sumado por sesión (filas) y celda (columnas), 0 donde la celda no operó: la matriz para Li-Ji."""
    us, inv = np.unique(cx["ses"], return_inverse=True); M = np.zeros((len(us), len(celdas)))
    for j, c in enumerate(celdas):
        m = GM.mascara(cx["perillas"], cx["indices"], tuple(c)) & np.isfinite(cx["net"])
        M[:, j] = np.bincount(inv[m], weights=cx["net"][m], minlength=len(us))
    return M


def operaciones_de(cx, celdas):
    """Serie por operación de cada celda congelada, en orden de tiempo (lo que necesita un seguimiento secuencial: réplica,
    holdout o paper). Columnas: celda (índice en `celdas`), t (cierre de la vela de decisión, s), ses, k, neto, t_fill y t_exit
    (cierre de las velas de llenado y salida en el instrumento de ejecución, s). El orden sigue siendo por t, no por t_exit."""
    filas = []
    for i, c in enumerate(celdas):
        m = GM.mascara(cx["perillas"], cx["indices"], tuple(c)) & np.isfinite(cx["net"])
        filas.append(pd.DataFrame(dict(celda=i, t=cx["t"][m], ses=cx["ses"][m], k=cx["k"][m], neto=cx["net"][m],
                                  t_fill=cx["t_fill"][m], t_exit=cx["t_exit"][m])))
    return pd.concat(filas).sort_values(["t", "celda"], kind="stable").reset_index(drop=True) if filas else pd.DataFrame()


def para_autopilot(res, fuente):
    """results_flat: pistas como informativas; réplica `/rep/` es lo único que puede contar como acierto."""
    nom = lambda c: "_".join(str(x) for x in c); exp = res.get("experimento", "GRILLA")
    flat = [dict(test=f"{exp}/{fuente}/{nom(r['celda'])}/pista_{k}", p=r["p_sesiones"], evaluable=False, diff=r["media_neta"])
            for k, c in (res.get("canales") or {}).items() for r in c.get("pistas", [])]
    flat += [dict(test=f"{exp}/{fuente}/{nom(r['celda'])}/rep/1", p=r.get("p_sesiones"), evaluable="p_sesiones" in r, diff=r.get("media_neta"))
             for r in res.get("replica", [])]
    return dict(results_flat=flat, schema="grilla_generica_v1")
