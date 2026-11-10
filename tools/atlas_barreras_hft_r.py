#!/usr/bin/env python3
"""Atlas transversal de Barreras HFT frontales en R (Vía 2, 2026-11-05).

Pre-registro: `docs/research/hft_gc_p10_20261105/PREREGISTRO_BARRERAS_HFT_R.md` (+ adenda de tramo del 2026-11-05).
Pregunta: en TODAS las campañas en R de futuros puros (GC, NQ, ES, YM; sensor == ejecución), ¿las operaciones que tienen camino
despejado de zonas HFT vigentes rinden más en R que el conjunto de operaciones? Separado por mecanismo (CONTINUACION / REVERSION / GLOBAL),
colapsando cada `(familia_base, activo)` en una observación independiente y combinando con DerSimonian-Laird. Compuerta primaria:
BH q <= 0,10 en DESC + p unilateral < 0,05 con el mismo signo en REP (no se mira el holdout).

Dos familias de reglas (todas con tipo_barrera x antigüedad {5m,15m,60m,180m,sesión} x mitigación {VIRGEN,NO_ATRAVESADA}):
  LIBRE  distancia libre frontal a la primera barrera >= 1R / 2R / 4R                                  (120 reglas)
  TRAMO  barreras vigentes entre entrada y objetivo: todo el tramo con N = 0, 1, 2 zonas, o sólo en el
         50 % más alejado de la entrada con N = 1, 2 (pedido de Nico)                                 (200 reglas)
El efecto de cada regla es  media(R | pasa) - media(R | todas las operaciones)  del cluster.
No incluye CAP_TP_DELANTE (requiere re-simular salidas): eso lo cubre la campaña `HFT-GC-P10-CAPTP-R` sólo en GC.

Uso: python tools/atlas_barreras_hft_r.py correr_local [--solo CID] | analizar
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atlas_contexto_r as AC  # noqa: E402
from edgelab.research import barreras_hft as BH, barreras_hft_tramo as BT, fuentes_ticks as F, grilla_generica as GG, perfil_volumen_tramo as PV  # noqa: E402
from edgelab.research.embudo_runners import friccion as friccion_canonica  # noqa: E402

BASE = ROOT / "docs/research/hft_gc_p10_20261105"
SAL = BASE / "atlas_barreras"
CRUDO = SAL / "crudo"
ALM_GC = BASE / "almacen"
ALM_OTROS = BASE / "almacen_otros"
INSTRUMENTOS = ("GC", "NQ", "ES", "YM")
EXCLUIR_CID = ("HFT-GC-P10-VETO-R", "HFT-GC-P10-CAPTP-R")
CORTES_LIBRE = (1.0, 2.0, 4.0)
HASTA = 20260930


def _clave_libre(ti, ei, mi, r):
    return f"LIBRE|t{ti}|e{ei}|m{mi}|r{r:g}"


def _clave_tramo(ti, ei, mi, modo, n):
    return f"TRAMO|t{ti}|e{ei}|m{mi}|{modo}{n}"


def _zonas(inst: str):
    """(zonas, clusters|None) del almacén target-free del instrumento."""
    if inst == "GC":
        return pd.read_parquet(ALM_GC / "ZONAS_HFTGCP10_GC.parquet"), pd.read_parquet(ALM_GC / "ZONAS_HFTGCP10_CLUST_GC.parquet")
    z = pd.read_parquet(ALM_OTROS / f"ZONAS_HFTNQ_{inst}.parquet")
    # ES: 1,4 M zonas de 1 tick; el cálculo causal de Clusters P10 en Python tarda horas -> sin clusters (tipo 3 no se evalúa en ES)
    return z, (pd.DataFrame() if inst == "ES" else None)


def _agg(net, ses, mask):
    x = net[mask]
    return dict(n=int(mask.sum()), suma=float(x.sum()), suma2=float((x * x).sum()), sesiones=int(len(np.unique(ses[mask]))))


def evaluar_ops(ctx: dict, inv: dict, O: np.ndarray, net: np.ndarray, ses: np.ndarray, tipos=range(4)) -> dict:
    """Agrega (n, suma, suma2, sesiones) del R por regla de barrera sobre las operaciones con R finito (filas únicas de nivel)."""
    ok = np.isfinite(net)
    if not ok.any():
        return dict(base=dict(n=0), reglas={})
    O, net, ses = O[ok], net[ok], np.asarray(ses)[ok]
    fila = np.column_stack([O[:, 2], O[:, 4], O[:, 5], O[:, 6], O[:, 7]])
    u, inv_u = np.unique(fila, axis=0, return_inverse=True)
    inv_u = inv_u.ravel()
    nu = np.bincount(inv_u, minlength=len(u)).astype(float)
    su = np.bincount(inv_u, weights=net, minlength=len(u))
    s2u = np.bincount(inv_u, weights=net * net, minlength=len(u))
    ses_u = np.zeros(len(u), np.int64)
    ses_u[inv_u] = ses
    k_u, s_u, e_u, sl_u, tp_u = (u[:, i] for i in range(5))
    k_u = k_u.astype(np.int64)
    s_u = s_u.astype(np.int64)
    r_u = np.abs(e_u - sl_u)
    d_u = np.abs(tp_u - e_u)
    valido = (r_u > 0) & (d_u > 0)

    def agg_u(m):
        m = m & valido
        n = nu[m].sum()
        return dict(n=int(n), suma=float(su[m].sum()), suma2=float(s2u[m].sum()), sesiones=int(len(np.unique(ses_u[m]))))

    out = dict(base=agg_u(np.ones(len(u), bool)), reglas={})
    for ti in tipos:
        if ti == 3 and not len(inv["ci"]):
            continue                                   # sin Clusters P10 en este instrumento: la regla no existe (no se evalúa como "todo pasa")
        for ei in range(len(BH.ANTIGUEDADES)):
            for mi in range(len(BH.MITIGACIONES)):
                d_lib = BH.evaluar_distancia_frontal(inv, k_u, s_u, e_u, r_u, ti, ei, mi)
                for rr in CORTES_LIBRE:
                    out["reglas"][_clave_libre(ti, ei, mi, rr)] = agg_u(d_lib >= rr * r_u)
                n_tot, n_cer = BT.conteo_tramo(inv, k_u, s_u, e_u, r_u, d_u, ti, ei, mi)
                for modo, n_max in BT.REGLAS_TRAMO:
                    out["reglas"][_clave_tramo(ti, ei, mi, modo, n_max)] = agg_u(BT.pasa_regla(n_tot, n_cer, modo, n_max))
    if len(ctx.get("vp_px", ())):
        for nb in PV.N_BARRAS:
            va, vb = PV.vol_rangos(ctx, k_u, s_u, e_u, tp_u, nb)
            ca, cb = PV.conteos_rangos(ctx, k_u, s_u, e_u, tp_u, nb)
            for q in PV.RATIOS:
                out["reglas"][f"PERFIL|n{nb}|q{q:g}"] = agg_u(PV.pasa_perfil(va, vb, q))
                out["reglas"][f"PERFILMEDIA|n{nb}|q{q:g}"] = agg_u(PV.pasa_perfil_media(va, vb, ca, cb, q))
                out["reglas"][f"PERFILVACIO|n{nb}|q{q:g}"] = agg_u(PV.pasa_perfil_vacio(va, vb, q))
    return out


def correr_local(solo=None, inst_solo=None):
    CRUDO.mkdir(parents=True, exist_ok=True)
    camps = [(cid, st) for cid, st in AC._todas_las_campanas_r() if cid not in EXCLUIR_CID]
    por_inst = defaultdict(list)
    for cid, st in camps:
        sp = st["spec"]
        ejec = sp.get("ejecucion") or sp["sensor"]
        if sp["sensor"] != ejec or sp["sensor"] not in INSTRUMENTOS or sp.get("confirmador") or sp.get("datasets_extra"):
            continue
        if solo and cid != solo:
            continue
        por_inst[sp["sensor"]].append((cid, st))
    for inst in INSTRUMENTOS:
        if inst_solo and inst != inst_solo:
            continue
        lista = por_inst.get(inst, [])
        if not lista:
            continue
        pend = False
        for cid, st in lista:
            sp = st["spec"]
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            for tr, per in (("desc", sp.get("desc")), ("rep", rep)):
                if per and not (CRUDO / f"{cid}__{tr}.json").exists():
                    pend = True
        if not pend:
            continue
        t0 = time.time()
        lec, tk = F.resolver(inst)
        usa_perfil = True                                  # el filtro PERFIL-TP necesita el perfil de volumen por vela
        full = AC._contexto_m1_rapido(lec(20250721, 20260930, str(AC.DATA_LOCAL)), tk, con_perfil=usa_perfil, con_ticks=True)
        zonas, clust = _zonas(inst)
        print(f"[ctx] {inst} {len(full['c'])} velas, {len(zonas)} zonas ({time.time() - t0:.0f}s)", flush=True)
        cache_inv = {}
        fr, ex = friccion_canonica(inst)
        for cid, st in lista:
            sp = st["spec"]
            exp = importlib.import_module(sp["experimento"])
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            for tr, per in (("desc", sp.get("desc")), ("rep", rep)):
                f_out = CRUDO / f"{cid}__{tr}.json"
                if not per or f_out.exists():
                    continue
                t1 = time.time()
                d0, d1 = int(per[0]), min(int(per[1]), HASTA)
                ctx = AC._recortar_ctx(full, d0, d1, dias_cal=40)
                ctx.update(sensor=inst, desde_eval=d0)
                try:
                    previo = getattr(exp, "NORMALIZAR", None)
                    exp.NORMALIZAR = "riesgo"
                    try:
                        res, cx = GG.correr(exp, ctx, modo="MARG", friccion=fr, extra_adverso=ex, cortes=st["cortes"], log=lambda s: None)
                    finally:
                        if previo is None:
                            delattr(exp, "NORMALIZAR")
                        else:
                            exp.NORMALIZAR = previo
                    if not len(ctx["t"]) or "O" not in cx or not len(cx["O"]):
                        f_out.write_text(json.dumps(dict(cid=cid, tramo=tr, vacio=True)), encoding="utf-8")
                        continue
                    kw = (inst, d0, d1)
                    if kw not in cache_inv:
                        z = zonas[zonas["t_ns"].to_numpy(np.int64) >= int(ctx["t"][0]) * 10**9]
                        cache_inv[kw] = BH.preparar_inventario_barreras(z, ctx, clust)
                    ev = evaluar_ops(ctx, cache_inv[kw], cx["O"], cx["net"], cx["ses"])
                    ev.update(cid=cid, tramo=tr, inst=inst, familia=sp["familia"], experimento=sp["experimento"], periodo=[d0, d1])
                    f_out.write_text(json.dumps(ev, default=float), encoding="utf-8")
                    print(f"[ok] {cid}/{tr} base n={ev['base']['n']} ({time.time() - t1:.0f}s)", flush=True)
                except Exception as e:  # noqa: BLE001
                    print(f"[ERROR] {cid}/{tr}: {type(e).__name__}: {str(e)[:200]}", flush=True)
                gc.collect()
        del full
        gc.collect()


def _registros(tramo: str):
    ests = {cid: st for cid, st in AC._todas_las_campanas_r()}
    regs = []
    for f in sorted(CRUDO.glob(f"*__{tramo}.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("vacio") or d["base"].get("n", 0) < 30:
            continue
        st = ests.get(d["cid"])
        mod = d["experimento"]
        activo = AC.ACTIVO_SUBYACENTE.get(d["inst"], d["inst"])
        regs.append(dict(cid=d["cid"], cluster=f"{AC._familia_base(mod)}__{activo}", mecanismo=AC.MECANISMO_POR_MODULO.get(mod, "MIXTO"),
                         base=d["base"], reglas=d["reglas"], activo=activo))
    return regs


def _efectos(tramo: str, estrato: str):
    regs = _registros(tramo)
    if estrato in ("REVERSION", "CONTINUACION"):
        regs = [r for r in regs if r["mecanismo"] == estrato]
    por = defaultdict(lambda: defaultdict(list))
    for r in regs:
        b = r["base"]
        mu = b["suma"] / b["n"]
        for clave, a in r["reglas"].items():
            if a["n"] < 30 or a["sesiones"] < 10:
                continue
            m = a["suma"] / a["n"]
            var = max(a["suma2"] / a["n"] - m * m, 1e-12)
            por[clave][r["cluster"]].append((m - mu, var / a["sesiones"]))
    out = {}
    for clave, mapa in por.items():
        out[clave] = [(cl, float(np.mean([p[0] for p in ps])), float(np.mean([p[1] for p in ps]))) for cl, ps in sorted(mapa.items())]
    return out


def meta(min_clusters=4):
    from edgelab.funnel.escalera import _N
    res = {}
    for estrato in ("GLOBAL", "REVERSION", "CONTINUACION"):
        tramos = {}
        for tr in ("desc", "rep"):
            filas = []
            for clave, xs in _efectos(tr, estrato).items():
                if len(xs) < min_clusters:
                    continue
                m, se, tau2, I2 = AC._dl([x[1] for x in xs], [x[2] for x in xs])
                z = m / se if se > 0 else 0.0
                filas.append(dict(regla=clave, clusters=len(xs), efecto_R=round(m, 5), se_R=round(se, 5), z=round(z, 3),
                                  p_bilateral=float(2 * (1 - _N.cdf(abs(z)))), p_uni=float(1 - _N.cdf(z)), I2=round(I2, 3),
                                  mismo_signo=round(float(np.mean(np.sign([x[1] for x in xs]) == np.sign(m))), 3)))
            tramos[tr] = sorted(filas, key=lambda r: r["p_bilateral"])
        d = tramos["desc"]
        for i, r in enumerate(d):
            r["bh"] = bool(r["p_bilateral"] <= 0.10 * (i + 1) / len(d))
        kmax = max([i for i, r in enumerate(d) if r["bh"]], default=-1)
        for i, r in enumerate(d):
            r["bh"] = i <= kmax
        rep = {r["regla"]: r for r in tramos["rep"]}
        for r in d:
            q = rep.get(r["regla"])
            r["rep"] = q
            r["confirmada"] = bool(r["bh"] and r["efecto_R"] > 0 and q and q["efecto_R"] > 0 and q["p_uni"] < 0.05)
        res[estrato] = tramos
    return res


def analizar():
    r = meta()
    SAL.mkdir(parents=True, exist_ok=True)
    (SAL / "meta.json").write_text(json.dumps(r, indent=1, default=float), encoding="utf-8")
    lineas = ["# Atlas de Barreras HFT en R — meta-análisis transversal", "",
              "Efecto = media(R | regla pasa) − media(R | todas) por cluster `(familia_base, activo)`, DerSimonian-Laird. "
              "Compuerta: BH q ≤ 0,10 en DESC y REP con mismo signo y p unilateral < 0,05.", ""]
    for est, tr in r.items():
        d = tr["desc"]
        lineas += [f"## {est}", f"- reglas evaluadas en DESC: {len(d)}; nominadas BH: {sum(x['bh'] for x in d)}; confirmadas en REP: {sum(x['confirmada'] for x in d)}", "",
                   "| regla | clusters | efecto DESC (R) | p | BH | efecto REP (R) | p uni REP | confirmada |", "|---|---|---|---|---|---|---|---|"]
        for x in d[:15]:
            q = x["rep"] or {}
            lineas.append(f"| `{x['regla']}` | {x['clusters']} | {x['efecto_R']:+.3f} | {x['p_bilateral']:.4f} | {'sí' if x['bh'] else 'no'} | "
                          f"{q.get('efecto_R', float('nan')):+.3f} | {q.get('p_uni', float('nan')):.3f} | {'**sí**' if x['confirmada'] else 'no'} |")
        lineas.append("")
    (BASE / "RESULTADO_BARRERAS_HFT_R.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:60]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["correr_local", "analizar"])
    ap.add_argument("--solo", default=None)
    ap.add_argument("--inst", default=None)
    a = ap.parse_args()
    correr_local(a.solo, a.inst) if a.cmd == "correr_local" else analizar()

