"""Conductor de AREAS-EXP-1 (corre dentro del kernel de Kaggle; autocontenido junto con areas_expansion y escalera).

modo "E0": sólo eventos y variables (target-free) -> conteos, distribuciones y cortes de v_rel. No simula nada.
modo "DESC": además simula todas las ejecuciones y arma el tensor de 139.968 celdas -> tamiz FDR -> E2 sobre sobrevivientes.
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
    M = pd.concat(ms); M = M[~M.index.duplicated(keep="last")].sort_index()
    VP = pd.concat(vps).groupby(["t", "p"], sort=True).v.sum().reset_index()
    t = M.index.to_numpy(np.int64); mi = np.searchsorted(t, VP.t.to_numpy())
    start = np.searchsorted(mi, np.arange(len(t) + 1))
    tpx = np.concatenate(tps); tmin = np.searchsorted(t, np.concatenate(tts)); orden = np.argsort(tmin, kind="stable")
    tpx = tpx[orden]; tstart = np.searchsorted(tmin[orden], np.arange(len(t) + 1)).astype(np.int64)
    return t, M, VP.p.to_numpy(float), VP.v.to_numpy(float), start, tpx, tstart


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
                    pv, vc, pvp = AX.perfil_volumen(dg, vp_start, vp_px, vp_vol)
                    base = prev.get(ses[dg["k"]], np.nan) * max(dg["k"] - dg["m"], 1)
                    filas.append(dict(dg, ni=ni, wi=wi, N=len(ev[3]), seg=sg, ses=ses[dg["k"]], t_k=int(t[dg["k"]]),
                                      com=AX.visitas_en(V, Z, ev[3], d["k"]), A_H=dg["A"] / dg["H"], p_vol=pv, p_vol_precio=pvp,
                                      v_rel=(vc / base) if base and np.isfinite(base) and base > 0 else np.nan,
                                      hora=int((t[dg["k"]] // 3600) % 24)))
    return pd.DataFrame(filas)


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
                           for n in range(3) for w in range(3) for x in range(3)},
                A_H=q(D.A_H), comercio=q(D.com), p_vol=q(D.p_vol.dropna()), v_rel=q(vr), v_rel_cortes=cortes,
                lado_arriba=float((D.lado == 1).mean()) if len(D) else None, comercio_cortes=com_c)


def _vecino_stop(celda):
    e = celda[2]; st = (e // 2) % 3
    return [tuple(celda[:2]) + (e + 2 * d,) + tuple(celda[3:]) for d in (-1, 1) if 0 <= st + d < 3]


def e2(nominadas, ctx, *, extra_adverso, max_replica=3):
    """Sobre las nominadas: IC por sesiones, meseta (x, A/H, comercio y stop), económico. Elige hasta `max_replica` por cota
    inferior del IC (no por P&L máximo)."""
    from edgelab.funnel.escalera import economia, resumen_sesiones
    from edgelab.research import grilla_masiva as GM
    P, idx, net, st = ctx["perillas"], ctx["indices"], ctx["net"], ctx["st"]; out = []
    for cel in nominadas:
        m = GM.mascara(P, idx, cel) & np.isfinite(net)
        if m.sum() < 30: continue
        rs = resumen_sesiones(net[m], ctx["ses"][m], n_boot=2000)
        ms = GM.meseta(st, cel, P, AX.EJES_ORDINALES)
        vs = [st["media"][v] for v in _vecino_stop(cel) if st["n"][v] >= 30]
        mes_ok = ms["meseta"] and (not vs or np.mean(np.array(vs) > 0) >= 0.5)
        eco = economia(net[m], net[m] - extra_adverso, ctx["ses"][m], periodos=ctx["mes"][m])
        out.append(dict(celda=list(cel), ejecucion=list(AX.EJEC[cel[2]]), n=int(m.sum()), media_neta=float(net[m].mean()),
                        sesiones=rs["n_sesiones"], ic90=rs["ic"], p_sesiones=rs["p_unilateral"], meseta=bool(mes_ok), vecinos=ms["vecinos"],
                        economico=eco["duros"], pasa=bool(mes_ok and eco["pasa"] and rs["ic"][0] > 0)))
    pasan = sorted([x for x in out if x["pasa"]], key=lambda x: -x["ic90"][0])
    return out, pasan[:max_replica]


def correr(bloques, *, modo, G, tick, friccion, extra_adverso, vr_cortes=None, com_cortes=None, q=0.10, log=print):
    t0 = time.time(); t, M, vpp, vpv, vps, tpx, tstart = m1_y_perfil(bloques); log(f"M1 {len(t)} velas, perfil {len(vpp)} filas ({time.time() - t0:.0f}s)")
    D = disparos_y_variables(t, M, vpp, vpv, vps, G); log(f"disparos {len(D)} ({time.time() - t0:.0f}s)")
    res = dict(modo=modo, E0=e0(D))
    if modo == "E0": return res, D
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
    ab, cb, pb, vb = AX.bins_variables(D.A_H.to_numpy()[di], D.com.to_numpy()[di], D.p_vol.to_numpy()[di], D.v_rel.fillna(-1).to_numpy()[di], cortes, com_c)
    from edgelab.research import grilla_masiva as GM
    P = AX.perillas(); idx = [D.ni.to_numpy()[di] * len(AX.WS) + D.wi.to_numpy()[di], D.xi.to_numpy()[di], O[:, 1].astype(int), ab, cb, pb, vb]
    S, Q, C = GM.tensor(P, idx, net); st = GM.estadisticas(S, Q, C); cr = GM.criba(st, q=q)
    log(f"celdas {cr['celdas']}, evaluables {cr['evaluables']}, nominadas {len(cr['nominadas'])} ({time.time() - t0:.0f}s)")
    res.update(celdas=cr["celdas"], evaluables=cr["evaluables"], nominadas=len(cr["nominadas"]), pi0=cr["pi0"], v_rel_cortes=cortes, comercio_cortes=com_c,
               operaciones=int(len(O)), con_llenado=int(np.isfinite(pnl).sum()), perillas=[(p.nombre, p.niveles, p.modo) for p in P])
    ctx = dict(D=D, O=O, net=net, perillas=P, indices=idx, st=st, ses=D.ses.to_numpy()[di], mes=D.t_k.to_numpy()[di] // (86400 * 30))
    res["E2"], res["a_replica"] = e2(cr["nominadas"], ctx, extra_adverso=extra_adverso)
    res["nominadas_top"] = [dict(celda=list(c), ejecucion=list(AX.EJEC[c[2]]), n=int(st["n"][c]), media_neta=float(st["media"][c]), t=float(st["t"][c]))
                            for c in cr["nominadas"][:300]]
    log(f"E2: {len(res['E2'])} evaluadas, {sum(x['pasa'] for x in res['E2'])} pasan, {len(res['a_replica'])} a réplica ({time.time() - t0:.0f}s)")
    return res, ctx
