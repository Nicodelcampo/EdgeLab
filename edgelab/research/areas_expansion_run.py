"""Conductor de AREAS-EXP-1 (corre dentro del kernel de Kaggle; autocontenido junto con areas_expansion y escalera).

modo "E0": sólo eventos y variables (target-free) -> conteos, distribuciones y cortes de v_rel. No simula nada.
modo "DESC": además simula todas las ejecuciones y arma el tensor de celdas -> tamiz FDR -> E2 sobre sobrevivientes.
modo "REP": réplica pre-registrada: sólo las celdas congeladas (`celdas`), con los cortes congelados del descubrimiento.
Entrada: un iterador de bloques de ticks (DataFrame con ts_ns, px, vol, sesion, segmento) ordenados en el tiempo.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX


def m1_y_perfil(bloques):
    """Velas M1 (marca de cierre), sesión y segmento por vela; perfil de volumen disperso (minuto, precio, volumen)."""
    ms, vps, tps, tts = [], [], [], []
    for b in bloques:
        if not len(b): continue
        mc = (b.ts_ns.to_numpy() // 60_000_000_000 + 1) * 60          # cierre del minuto (s)
        df = pd.DataFrame(dict(t=mc, p=b.px.to_numpy(), v=b.vol.to_numpy(), ses=b.sesion.to_numpy(), seg=b.segmento.to_numpy()))
        g = df.groupby("t", sort=True)
        ms.append(pd.DataFrame(dict(o=g.p.first(), h=g.p.max(), l=g.p.min(), c=g.p.last(), v=g.v.sum(), ses=g.ses.last(), seg=g.seg.last())))
        vps.append(df.groupby(["t", "p"], sort=True).v.sum().reset_index())
        tps.append(df.p.to_numpy(float)); tts.append(mc)                    # ticks en orden (para resolver ambigüedad SL/TP en M1)
    M = pd.concat(ms).sort_index()
    dup = int(M.index.duplicated().sum())
    if dup: raise ValueError(f"{dup} minutos repetidos entre bloques: los bloques deben ser días de trading completos (no se descarta en silencio)")
    VP = pd.concat(vps).groupby(["t", "p"], sort=True).v.sum().reset_index()
    t = M.index.to_numpy(np.int64); mi = np.searchsorted(t, VP.t.to_numpy())
    start = np.searchsorted(mi, np.arange(len(t) + 1))
    tpx = np.concatenate(tps); tmin = np.searchsorted(t, np.concatenate(tts)); orden = np.argsort(tmin, kind="stable")
    tpx = tpx[orden]; tstart = np.searchsorted(tmin[orden], np.arange(len(t) + 1)).astype(np.int64)
    return t, M, VP.p.to_numpy(float), VP.v.to_numpy(float), start, tpx, tstart


def para_autopilot(res, fuente):
    """Formato `results_flat` que lee el ciclo autónomo (analyze.records / confirmacion escalera_v1). Descubrimiento: las celdas
    evaluadas en E2 (p por sesiones), nombradas `GRILLA/<fuente>/<celda>/disc`. Réplica: `.../rep/...`, que es lo único que
    puede contar como acierto. `n_planned` del RunSpec = celdas de la grilla (todas cuentan, aunque no se evalúen)."""
    nombre = lambda c: "_".join(str(x) for x in c)
    flat = [dict(test=f"GRILLA/{fuente}/{nombre(r['celda'])}/disc", p=r["p_sesiones"], evaluable=True, diff=r["media_neta"]) for r in res.get("E2", [])]
    flat += [dict(test=f"GRILLA/{fuente}/{nombre(r['celda'])}/rep/1", p=r.get("p_sesiones"), evaluable="p_sesiones" in r, diff=r.get("media_neta"))
             for r in res.get("replica", [])]
    return dict(results_flat=flat, schema="grilla_masiva_v1")


def disparos_y_variables(t, M, vp_px, vp_vol, vp_start, G):
    """Por segmento (contrato): zonas, áreas, disparos y variables. Devuelve DataFrame de disparos (target-free)."""
    o, h, l, c = (M[k].to_numpy(float) for k in "ohlc"); seg = M.seg.to_numpy(); ses = M.ses.to_numpy()
    vol_ses = M.groupby("ses").v.sum() / M.groupby("ses").size()          # volumen medio por minuto de cada sesión
    ses_u = np.array(sorted(vol_ses.index)); prev = {s: (vol_ses[ses_u[i - 1]] if i else np.nan) for i, s in enumerate(ses_u)}
    filas = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a, b = idx[0], idx[-1] + 1          # segmento contiguo
        Z = AX.zonas(t[a:b], o[a:b], h[a:b], l[a:b], c[a:b]); V = AX.visitas_acumuladas(Z, h[a:b], l[a:b])
        EV = AX.eventos(Z, t[a:b], G)
        for (n_, w_), lista in EV.items():
            ni, wi = AX.NS.index(n_), AX.WS.index(w_)
            for ev in lista:
                for d in AX.disparos(ev, h[a:b], l[a:b], c[a:b], t[a:b], fin=int(Z["zfin"][ev[3]].max())):
                    dg = dict(d, m=d["m"] + a, k=d["k"] + a)
                    filas.append(dict(dg, ni=ni, wi=wi, N=len(ev[3]), seg=sg, ses=ses[dg["k"]], t_k=int(t[dg["k"]]),
                                      com=AX.visitas_en(V, Z, ev[3], d["k"]), A_H=dg["A"] / dg["H"], hora=int((t[dg["k"]] // 3600) % 24)))
    D = pd.DataFrame(filas)
    if not len(D): return D
    borde = np.where(D.lado.to_numpy() == 1, D.hi.to_numpy(), D.lo.to_numpy())
    pv, vc, pvp = AX.perfiles_volumen(D.m.to_numpy(np.int64), D.k.to_numpy(np.int64), D.lado.to_numpy(np.int64), borde.astype(float),
                                      D.A.to_numpy(float), vp_start.astype(np.int64), vp_px, vp_vol)                 # en lote, compilado
    base = D.ses.map(prev).to_numpy(float) * np.maximum(D.k.to_numpy() - D.m.to_numpy(), 1)
    D["p_vol"], D["p_vol_precio"] = pv, pvp
    D["v_rel"] = np.where(np.isfinite(base) & (base > 0), vc / np.where(base > 0, base, 1), np.nan)
    return D


def e0(D):
    """Resumen target-free: conteos por N y x, distribuciones y cortes de v_rel (terciles de descubrimiento)."""
    vr = D.v_rel[np.isfinite(D.v_rel)]
    cortes = [float(np.quantile(vr, 1 / 3)), float(np.quantile(vr, 2 / 3))] if len(vr) else [np.nan, np.nan]
    com_c = [float(np.quantile(D.com, q_)) for q_ in (0.25, 0.5, 0.75)]
    q = lambda s: {p: round(float(np.nanquantile(s, p)), 4) for p in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(s) else {}
    if not len(D): return dict(disparos=0)
    return dict(disparos=int(len(D)), eventos=int(D.drop_duplicates(["ni", "wi", "m"]).shape[0]), sesiones=int(D.ses.nunique()),
                eventos_por_dia=round(D.drop_duplicates(["ni", "wi", "m"]).shape[0] / max(D.ses.nunique(), 1), 2),
                por_N_W_x={f"N>={AX.NS[n]}/W={AX.WS[w]}/x={AX.XS[x]}": int(((D.ni == n) & (D.wi == w) & (D.xi == x)).sum())
                           for n in range(len(AX.NS)) for w in range(len(AX.WS)) for x in range(len(AX.XS))},
                A_H=q(D.A_H), comercio=q(D.com), p_vol=q(D.p_vol.dropna()), v_rel=q(vr), v_rel_cortes=cortes,
                lado_arriba=float((D.lado == 1).mean()) if len(D) else None, comercio_cortes=com_c)


def _vecino_stop(celda):
    e = celda[2]; st = (e // 2) % 3                                    # EJEC = dir/obj × entrada × stop × BE: stop = (e // 2) % 3
    return [tuple(celda[:2]) + (e + 2 * d,) + tuple(celda[3:]) for d in (-1, 1) if 0 <= st + d < 3]


MIN_OPS, MIN_SESIONES, RATIO_MOV_FRICCION = 30, 20, 3.0


def evaluar_celda(cel, ctx, *, extra_adverso, friccion, bootstrap=2000):
    """Inferencia cara de UNA celda: IC por sesiones, meseta, económico y relevancia (distancia al objetivo / fricción)."""
    from edgelab.funnel.escalera import economia, resumen_sesiones
    from edgelab.research import grilla_masiva as GM
    P, idx, net, st = ctx["perillas"], ctx["indices"], ctx["net"], ctx["st"]
    m = GM.mascara(P, idx, cel) & np.isfinite(net)
    if m.sum() < MIN_OPS: return None
    rs = resumen_sesiones(net[m], ctx["ses"][m], n_boot=bootstrap)
    ms = GM.meseta(st, cel, P, AX.EJES_ORDINALES)
    vs = [st["media"][v] for v in _vecino_stop(cel) if st["n"][v] >= MIN_OPS]
    mes_ok = ms["meseta"] and (not vs or np.mean(np.array(vs) > 0) >= 0.5)
    eco = economia(net[m], net[m] - extra_adverso, ctx["ses"][m], periodos=ctx["mes"][m])
    dist = float(np.median(ctx["dist_obj"][m])); rel = dist / friccion if friccion > 0 else np.inf
    ok = bool(mes_ok and eco["pasa"] and rs["ic"][0] > 0 and rs["n_sesiones"] >= MIN_SESIONES and rel >= RATIO_MOV_FRICCION)
    return dict(celda=list(cel), ejecucion=list(AX.EJEC[cel[2]]), n=int(m.sum()), media_neta=float(net[m].mean()), sesiones=rs["n_sesiones"],
                ic90=rs["ic"], p_sesiones=rs["p_unilateral"], meseta=bool(mes_ok), vecinos=ms["vecinos"], economico=eco["duros"],
                dist_objetivo_mediana=dist, ratio_mov_friccion=round(rel, 2), pasa=ok)


def e2(nominadas, ctx, *, extra_adverso, friccion, max_replica=3):
    """Sobre las nominadas: evaluar_celda. Pasa con IC>0, meseta, económico, >= 20 sesiones y objetivo >= 3x fricción.
    Elige hasta `max_replica` por cota inferior del IC (no por P&L máximo)."""
    out = [r for r in (evaluar_celda(c, ctx, extra_adverso=extra_adverso, friccion=friccion) for c in nominadas) if r]
    pasan = sorted([x for x in out if x["pasa"]], key=lambda x: -x["ic90"][0])
    return out, pasan[:max_replica]


def correr(bloques, *, modo, G, tick, friccion, extra_adverso, vr_cortes=None, com_cortes=None, celdas=None, q=0.10, log=print):
    t0 = time.time(); t, M, vpp, vpv, vps, tpx, tstart = m1_y_perfil(bloques); log(f"M1 {len(t)} velas, perfil {len(vpp)} filas ({time.time() - t0:.0f}s)")
    D = disparos_y_variables(t, M, vpp, vpv, vps, G); log(f"disparos {len(D)} ({time.time() - t0:.0f}s)")
    res = dict(modo=modo, E0=e0(D))
    if modo == "E0": return res, D
    if modo == "REP" and not (vr_cortes and com_cortes and celdas): raise ValueError("REP exige celdas y cortes CONGELADOS del descubrimiento")
    cortes = vr_cortes or res["E0"]["v_rel_cortes"]; com_c = com_cortes or res["E0"]["comercio_cortes"]
    D = D.reset_index(drop=True); ops = []
    o, h, l, c = (M[k].to_numpy(float) for k in "ohlc"); ses = M.ses.to_numpy().astype(np.int64)
    for i, r in enumerate(D.to_dict("records")):
        for ei, ej in enumerate(AX.EJEC):
            nv = AX.niveles(r, ej, r["p_vol_precio"], tick, c)
            if nv is not None: ops.append((i, ei) + tuple(nv))
    O = np.array(ops, float); di = O[:, 0].astype(int)
    pnl, amb = AX.simular(D.k.to_numpy()[di].astype(np.int64), O[:, 3].astype(np.int64), O[:, 2].astype(np.int64), O[:, 4], O[:, 5], O[:, 6],
                          O[:, 7].astype(np.int64), o, h, l, c, ses, float(tick), tpx, tstart)
    res["ambiguedad_M1"] = dict(resueltas_con_ticks=int((amb == 1).sum()), sin_ticks_stop=int((amb == 2).sum()), operaciones=int(len(amb)))
    net = pnl - friccion; log(f"operaciones {len(O)} simuladas, {int(np.isfinite(pnl).sum())} con llenado ({time.time() - t0:.0f}s)")
    ab, cb, pb, vb = AX.bins_variables(D.A_H.to_numpy()[di], D.com.to_numpy()[di], D.p_vol.to_numpy()[di], D.v_rel.to_numpy()[di], cortes, com_c)
    from edgelab.research import grilla_masiva as GM
    P = AX.perillas(); idx = [D.ni.to_numpy()[di] * len(AX.WS) + D.wi.to_numpy()[di], D.xi.to_numpy()[di], O[:, 1].astype(int), ab, cb, pb, vb]
    S, Q, C = GM.tensor(P, idx, net); st = GM.estadisticas(S, Q, C); cr = GM.criba(st, q=q)
    log(f"celdas {cr['celdas']}, evaluables {cr['evaluables']}, nominadas {len(cr['nominadas'])} ({time.time() - t0:.0f}s)")
    res.update(celdas=cr["celdas"], evaluables=cr["evaluables"], nominadas=len(cr["nominadas"]), pi0=cr["pi0"], v_rel_cortes=cortes, comercio_cortes=com_c,
               operaciones=int(len(O)), con_llenado=int(np.isfinite(pnl).sum()), perillas=[(p.nombre, p.niveles, p.modo) for p in P])
    res["nulo"] = GM.resumen_nulo(st, P, q=q, referencia=friccion)       # MDE por zona de la grilla (manifiesto: «si no pasa ninguna»)
    mes = pd.to_datetime(D.t_k.to_numpy(), unit="s", utc=True).strftime("%Y%m").to_numpy()[di]          # mes calendario (por disparo)
    ctx = dict(D=D, O=O, net=net, perillas=P, indices=idx, st=st, ses=D.ses.to_numpy()[di], mes=mes, dist_obj=np.abs(O[:, 6] - O[:, 4]))
    if modo == "REP":                                                   # réplica: sólo las celdas congeladas, sin tamiz
        res["replica"] = [dict(evaluar_celda(tuple(c), ctx, extra_adverso=extra_adverso, friccion=friccion) or dict(celda=list(c), n=0, nota="< 30 operaciones"))
                          for c in (celdas or [])]
        log(f"REP: {len(res['replica'])} celdas evaluadas ({time.time() - t0:.0f}s)"); return res, ctx
    res["E2"], res["a_replica"] = e2(cr["nominadas"], ctx, extra_adverso=extra_adverso, friccion=friccion)
    res["nominadas_top"] = [dict(celda=list(c), ejecucion=list(AX.EJEC[c[2]]), n=int(st["n"][c]), media_neta=float(st["media"][c]), t=float(st["t"][c]))
                            for c in cr["nominadas"][:300]]
    log(f"E2: {len(res['E2'])} evaluadas, {sum(x['pasa'] for x in res['E2'])} pasan, {len(res['a_replica'])} a réplica ({time.time() - t0:.0f}s)")
    return res, ctx
