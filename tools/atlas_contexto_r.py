#!/usr/bin/env python3
"""Atlas de Contexto Causal Común y Vetos Estructurales en R (2026-11-04).

Pre-registro: `docs/research/programa_r_20261103/PREREGISTRO_CONTEXTO_Y_VETOS_R_20261104.md`.
Cumple los 5 puntos de diseño:
  1. Estima las 7 variables de contexto común (`ctx_*`) y los 4 vetos estructurales (`veto_*`) sobre TODAS las campañas en R
     (etapa `MARGINALES` con `calentamiento_dias=40`), nunca seleccionando sobre las 11 reglas.
  2. Separa el meta-análisis por mecanismo (`REVERSION` vs `CONTINUACION` + `GLOBAL`) y colapsa los pares `Futuro + CFD` del mismo
     activo subyacente y familia base en un único cluster independiente `(familia_base, activo)` antes de DerSimonian-Laird.
  3. Publica el cálculo de potencia / Efecto Mínimo Detectable (MDE al 80 %, α=0,05 unilateral) antes de mirar.
  4. Usa un único estadístico primario pre-registrado (`efecto_R` de DerSimonian-Laird con BH q<=0,10 en DESC y mismo signo +
     p_unilateral < 0,05 en REP).
  5. Evalúa sobre las 11 estrategias seguidas (`DESC` + `REP`, Ago 2025 – Sep 2026; octubre 2026 ya abierto se reporta sólo como
     descriptivo, validación prospectiva limpia desde noviembre 2026) aplicando las 3 compuertas secundarias declaradas:
     consistencia entre reglas, Leave-One-Month-Out (LOMO 14/14 meses) y control nulo mensual emparejado (`EXP-004b`, B=2.000).

Uso:
  python tools/atlas_contexto_r.py correr_local | lanzar | traer | analizar
"""
from __future__ import annotations

import argparse
import datetime as dt
import gc
import glob
import importlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numba as nb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from edgelab.research import contexto_comun as CC, etapas as ET, fuentes_ticks as F, grilla_generica as GG  # noqa: E402
from edgelab.research.embudo_runners import friccion as friccion_canonica  # noqa: E402

SAL = ROOT / "docs/research/programa_r_20261103/contexto_marginales"
CRUDO = SAL / "crudo"
ATLAS_PREV = ROOT / "docs/research/atlas_ideas_r_20261102"
DATA_LOCAL = Path("D:/edgelab_release_work/release_v4/data")

# Clasificación a priori por mecanismo económico del módulo de experimento
MECANISMO_POR_MODULO = {
    # Reversión a la media / agotamiento / absorción
    "edgelab.research.corredor_vol_gaps": "REVERSION",
    "edgelab.research.confluencia_cvgap_racimos": "REVERSION",
    "edgelab.research.expansion_zonas": "REVERSION",
    "edgelab.research.zonas_gaps": "REVERSION",
    "edgelab.research.kalman_fade": "REVERSION",
    "edgelab.research.otr_930_sweep": "REVERSION",
    "edgelab.research.doble_retroceso": "REVERSION",
    "edgelab.research.intento_fallido_hacia_lux": "REVERSION",
    "edgelab.research.intento_fallido_hacia_racimos": "REVERSION",
    "edgelab.research.segundo_intento": "REVERSION",
    "edgelab.research.segundo_intento_avcl": "REVERSION",
    "edgelab.research.vwap_rev": "REVERSION",
    "edgelab.research.absorcion_climax": "REVERSION",
    "edgelab.research.u1_indaga": "REVERSION",
    "edgelab.research.u1_oro": "REVERSION",
    "edgelab.research.u1_cfd": "REVERSION",
    "edgelab.research.u1_6e_fut": "REVERSION",
    "edgelab.research.u1_6e_confirma": "REVERSION",
    "edgelab.research.u1_zonas": "REVERSION",
    "edgelab.research.u1_zonas_avcl": "REVERSION",
    "edgelab.research.u1_zonas_bt2": "REVERSION",
    "edgelab.research.u1_zonas_grilla": "REVERSION",
    "edgelab.research.u1_racimos_grilla": "REVERSION",
    # Ruptura / continuación / tendencia
    "edgelab.research.asia_bos_gaps": "CONTINUACION",
    "edgelab.research.eod_momentum": "CONTINUACION",
    "edgelab.research.modelo_asia": "CONTINUACION",
    "edgelab.research.oro_almuerzo_ruptura": "CONTINUACION",
    "edgelab.research.rango_preapertura": "CONTINUACION",
    "edgelab.research.prerange_base": "CONTINUACION",
    "edgelab.research.prerange_zonas": "CONTINUACION",
    "edgelab.research.rango_asia0100": "CONTINUACION",
    "edgelab.research.tau_tendencia": "CONTINUACION",
    "edgelab.research.tori_trend_toque3": "CONTINUACION",
    "edgelab.research.estructura_hhll": "CONTINUACION",
    "edgelab.research.impulso_post_macro": "CONTINUACION",
    # Bidireccionales (perilla FADE vs CONT en la misma grilla)
    "edgelab.research.wm_fixing": "MIXTO",
    "edgelab.research.comex_cierre_oro": "MIXTO",
    "edgelab.research.overnight_inventario": "MIXTO",
}

ACTIVO_SUBYACENTE = {
    "NQ": "NQ", "MNQ": "NQ", "DK:USATECHIDXUSD": "NQ", "USATECHIDXUSD": "NQ",
    "ES": "ES", "MES": "ES", "DK:USA500IDXUSD": "ES", "USA500IDXUSD": "ES",
    "YM": "YM", "MYM": "YM", "DK:USA30IDXUSD": "YM", "USA30IDXUSD": "YM",
    "GC": "GC", "MGC": "GC", "DK:XAUUSD": "GC", "XAUUSD": "GC",
    "6E": "6E", "DK:EURUSD": "6E", "EURUSD": "6E",
    "6B": "6B", "DK:GBPUSD": "6B", "GBPUSD": "6B",
    "6J": "6J", "DK:USDJPY": "6J", "USDJPY": "6J",
}


def _familia_base(modulo: str) -> str:
    """Agrupa variantes de futuro y CFD de la misma familia lógica para colapsar pares Futuro+CFD del mismo subyacente."""
    m = modulo.split(".")[-1]
    if m in ("u1_oro", "u1_cfd", "u1_6e_fut", "u1_6e_confirma", "u1_indaga"):
        return "u1_luximb"
    return m


def _todas_las_campanas_r() -> list[tuple[str, dict]]:
    """Devuelve todas las campañas en R con `cortes` congelados en `docs/research/*/embudo/*/estado.json`."""
    estados = {}
    for p in sorted(glob.glob(str(ROOT / "docs/research/*/embudo/*/estado.json"))):
        cid = Path(p).parent.name
        try:
            estados[cid] = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
    out = []
    vistos = set()
    # 1. Campañas del relanzamiento en R (usan cortes de su campaña base sin -R si no tienen estado propio con cortes)
    camp_f = ROOT / "docs/research/relanzamiento_R_20261102/CAMPANAS.json"
    if camp_f.exists():
        for cid in json.loads(camp_f.read_text(encoding="utf-8")):
            st = estados.get(cid)
            if not st or not st.get("cortes"):
                st = estados.get(cid[:-2])
            if st and st.get("cortes"):
                out.append((cid, st))
                vistos.add(cid)
    # 2. Campañas adicionales en R con estado y cortes propios (p. ej. DRC, SI, IFH, VWAP, ABSORCION, ESTRUCTURA, WM, COMEX, OVERNIGHT, POST-MACRO)
    for cid, st in sorted(estados.items()):
        if cid.endswith("-R") and cid not in vistos and st.get("cortes"):
            out.append((cid, st))
            vistos.add(cid)
    return out


@nb.njit(cache=True)
def _bloque_m1_nb(mc, px, vol, ses, seg, con_perfil):
    n = len(mc)
    if n == 0:
        z_i = np.zeros(0, np.int64)
        z_f = np.zeros(0, np.float64)
        return z_i, z_f, z_f, z_f, z_f, z_f, z_i, z_i, z_i, z_f, z_f, z_i
    m_cnt = 1
    for i in range(1, n):
        if mc[i] != mc[i - 1]:
            m_cnt += 1
    bounds = np.empty(m_cnt + 1, np.int64)
    bounds[0] = 0
    k = 1
    for i in range(1, n):
        if mc[i] != mc[i - 1]:
            bounds[k] = i
            k += 1
    bounds[m_cnt] = n

    t_out = np.empty(m_cnt, np.int64)
    o_out = np.empty(m_cnt, np.float64)
    h_out = np.empty(m_cnt, np.float64)
    l_out = np.empty(m_cnt, np.float64)
    c_out = np.empty(m_cnt, np.float64)
    v_out = np.empty(m_cnt, np.float64)
    ses_out = np.empty(m_cnt, np.int64)
    seg_out = np.empty(m_cnt, np.int64)
    tcnt_out = np.empty(m_cnt, np.int64)

    for m in range(m_cnt):
        a = bounds[m]
        b = bounds[m + 1]
        t_out[m] = mc[a]
        p0 = px[a]
        o_out[m] = p0
        c_out[m] = px[b - 1]
        ses_out[m] = ses[b - 1]
        seg_out[m] = seg[b - 1]
        tcnt_out[m] = b - a
        hi = p0
        lo = p0
        vv = 0.0
        for i in range(a, b):
            pi = px[i]
            if pi > hi:
                hi = pi
            if pi < lo:
                lo = pi
            vv += vol[i]
        h_out[m] = hi
        l_out[m] = lo
        v_out[m] = vv

    if not con_perfil:
        z_f = np.zeros(0, np.float64)
        z_i = np.zeros(m_cnt, np.int64)
        return t_out, o_out, h_out, l_out, c_out, v_out, ses_out, seg_out, tcnt_out, z_f, z_f, z_i

    p_buf = np.empty(n, np.float64)
    v_buf = np.empty(n, np.float64)
    vpcnt_out = np.empty(m_cnt, np.int64)
    vp_tot = 0
    for m in range(m_cnt):
        a = bounds[m]
        b = bounds[m + 1]
        sub_p = px[a:b]
        sub_v = vol[a:b]
        orden = np.argsort(sub_p)
        p_prev = sub_p[orden[0]]
        v_acc = sub_v[orden[0]]
        c_niv = 1
        for j in range(1, b - a):
            idx = orden[j]
            pj = sub_p[idx]
            if pj == p_prev:
                v_acc += sub_v[idx]
            else:
                p_buf[vp_tot] = p_prev
                v_buf[vp_tot] = v_acc
                vp_tot += 1
                p_prev = pj
                v_acc = sub_v[idx]
                c_niv += 1
        p_buf[vp_tot] = p_prev
        v_buf[vp_tot] = v_acc
        vp_tot += 1
        vpcnt_out[m] = c_niv

    return (
        t_out, o_out, h_out, l_out, c_out, v_out, ses_out, seg_out, tcnt_out,
        p_buf[:vp_tot].copy(), v_buf[:vp_tot].copy(), vpcnt_out,
    )


def _contexto_m1_rapido(bloques, tick: float, con_perfil: bool = True, con_ticks: bool = True) -> dict:
    """Construye el mismo diccionario que `GG.contexto_m1(bloques, tick)` en una sola pasada compilada por bloque diario (sin
    `pd.DataFrame.groupby(["t", "p"])` ni `np.argsort` global sobre 100M de ticks)."""
    partes = []
    for b in bloques:
        if not len(b):
            continue
        mc = (b.ts_ns.to_numpy(np.int64) // 60_000_000_000 + 1) * 60
        px = b.px.to_numpy(np.float64)
        vol = b.vol.to_numpy(np.float64)
        ses = b.sesion.to_numpy(np.int64)
        seg = b.segmento.to_numpy(np.int64)
        if len(mc) > 1 and (np.diff(mc) < 0).any():
            ord_b = np.argsort(mc, kind="stable")
            mc, px, vol, ses, seg = mc[ord_b], px[ord_b], vol[ord_b], ses[ord_b], seg[ord_b]
        res_b = _bloque_m1_nb(mc, px, vol, ses, seg, bool(con_perfil))
        partes.append((int(res_b[0][0]), res_b, px if con_ticks else np.zeros(0, np.float64)))
    if not partes:
        return dict(t=np.zeros(0, np.int64), o=np.zeros(0), h=np.zeros(0), l=np.zeros(0), c=np.zeros(0), v=np.zeros(0),
                    ses=np.zeros(0, np.int64), seg=np.zeros(0, np.int64), vp_px=np.zeros(0), vp_vol=np.zeros(0),
                    vp_start=np.zeros(1, np.int64), tpx=np.zeros(0), tstart=np.zeros(1, np.int64), tick=float(tick))
    partes.sort(key=lambda x: x[0])
    t = np.concatenate([p[1][0] for p in partes])
    if len(t) > 1 and (np.diff(t) <= 0).any():
        raise ValueError("minutos repetidos entre bloques: los bloques deben ser días de trading completos")
    o = np.concatenate([p[1][1] for p in partes])
    h = np.concatenate([p[1][2] for p in partes])
    l = np.concatenate([p[1][3] for p in partes])
    c = np.concatenate([p[1][4] for p in partes])
    v = np.concatenate([p[1][5] for p in partes])
    ses = np.concatenate([p[1][6] for p in partes])
    seg = np.concatenate([p[1][7] for p in partes])
    tcnt = np.concatenate([p[1][8] for p in partes])
    vp_px = np.concatenate([p[1][9] for p in partes]) if con_perfil else np.zeros(0, np.float64)
    vp_vol = np.concatenate([p[1][10] for p in partes]) if con_perfil else np.zeros(0, np.float64)
    vpcnt = np.concatenate([p[1][11] for p in partes])
    vp_start = np.r_[np.int64(0), np.cumsum(vpcnt, dtype=np.int64)]
    tpx = np.concatenate([p[2] for p in partes]) if con_ticks else np.zeros(0, np.float64)
    tstart = np.r_[np.int64(0), np.cumsum(tcnt, dtype=np.int64)] if con_ticks else np.zeros(len(t) + 1, np.int64)
    return dict(t=t, o=o, h=h, l=l, c=c, v=v, ses=ses, seg=seg, vp_px=vp_px, vp_vol=vp_vol,
                vp_start=vp_start, tpx=tpx, tstart=tstart, tick=float(tick))


def _recortar_ctx(ctx_full: dict, desde: int, hasta: int, dias_cal: int = 40) -> dict:
    """Recorta `ctx_full` al rango de sesiones `[desde, hasta]` (idéntico bit a bit a `GG.contexto_m1(lec(desde, hasta))`) y adjunta
    las sesiones previas `[d_cal, desde - 1]` en `ctx["calentamiento"]` para poblar los cuantiles móviles de 20 sesiones desde el día 1."""
    ses = ctx_full["ses"]
    m = (ses >= int(desde)) & (ses <= int(hasta))
    idx = np.flatnonzero(m)
    if not len(idx):
        return dict(t=np.zeros(0, np.int64), o=np.zeros(0), h=np.zeros(0), l=np.zeros(0), c=np.zeros(0), v=np.zeros(0),
                    ses=np.zeros(0, np.int64), seg=np.zeros(0, np.int64), vp_px=np.zeros(0), vp_vol=np.zeros(0),
                    vp_start=np.zeros(1, np.int64), tpx=np.zeros(0), tstart=np.zeros(1, np.int64), tick=ctx_full["tick"])
    i0, i1 = int(idx[0]), int(idx[-1]) + 1
    vp0, vp1 = int(ctx_full["vp_start"][i0]), int(ctx_full["vp_start"][i1])
    ts0, ts1 = int(ctx_full["tstart"][i0]), int(ctx_full["tstart"][i1])
    sub = dict(
        t=ctx_full["t"][i0:i1],
        o=ctx_full["o"][i0:i1],
        h=ctx_full["h"][i0:i1],
        l=ctx_full["l"][i0:i1],
        c=ctx_full["c"][i0:i1],
        v=ctx_full["v"][i0:i1],
        ses=ctx_full["ses"][i0:i1],
        seg=ctx_full["seg"][i0:i1],
        vp_px=ctx_full["vp_px"][vp0:vp1],
        vp_vol=ctx_full["vp_vol"][vp0:vp1],
        vp_start=ctx_full["vp_start"][i0:i1 + 1] - vp0,
        tpx=ctx_full["tpx"][ts0:ts1],
        tstart=ctx_full["tstart"][i0:i1 + 1] - ts0,
        tick=ctx_full["tick"],
    )
    f_d0 = dt.date(int(desde) // 10000, (int(desde) // 100) % 100, int(desde) % 100)
    d_cal = int((f_d0 - dt.timedelta(days=dias_cal)).strftime("%Y%m%d"))
    m_cal = (ses >= d_cal) & (ses < int(desde))
    idx_cal = np.flatnonzero(m_cal)
    if len(idx_cal):
        c0, c1 = int(idx_cal[0]), int(idx_cal[-1]) + 1
        sub["calentamiento"] = {k: ctx_full[k][c0:c1] for k in ("t", "o", "h", "l", "c", "v", "ses")}
    return sub


def correr_local():
    """Ejecuta `ET.ejecutar("MARGINALES", ..., estadistico="R")` localmente sobre todas las campañas de futuros puros cuyo parquet
    canónico está en `D:/edgelab_release_work/release_v4/data`, con calentamiento de 40 días."""
    CRUDO.mkdir(parents=True, exist_ok=True)
    camps = _todas_las_campanas_r()
    # Filtramos las campañas de futuros sin almacenes externos y agrupamos por instrumento para cargar cada parquet una sola vez
    por_inst = defaultdict(list)
    for cid, st in camps:
        sp = st["spec"]
        sensor = sp["sensor"]
        ejec = sp.get("ejecucion") or sensor
        if sensor.startswith("DK:") or ejec.startswith("DK:") or sp.get("confirmador") or sp.get("datasets_extra"):
            continue
        if not (DATA_LOCAL / f"{sensor}_ticks.parquet").exists():
            continue
        por_inst[(sensor, ejec)].append((cid, st))

    SAL.mkdir(parents=True, exist_ok=True)
    meta = json.loads((SAL / "handles.json").read_text(encoding="utf-8")) if (SAL / "handles.json").exists() else {}
    for (sensor, ejec), lista in sorted(por_inst.items()):
        # Si ya están todos los JSON de este par (sensor, ejec), no cargamos el parquet
        pendientes = False
        usa_perfil = False
        for cid, st in lista:
            sp = st["spec"]
            if any(x in sp["experimento"] for x in ("u1_", "areas_expansion")):
                usa_perfil = True
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            for tramo, per in (("desc", sp.get("desc")), ("rep", rep)):
                if not per:
                    continue
                k = f"{cid}/{tramo}"
                out_f = CRUDO / f"{cid}__{tramo}.json"
                if out_f.exists():
                    meta[k] = dict(handle=f"local/{cid}/{tramo}", familia=sp["familia"], experimento=sp["experimento"],
                                   sensor=sensor, ejecucion=ejec)
                else:
                    pendientes = True
        if not pendientes:
            (SAL / "handles.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
            continue

        cache_ctx = {}
        for inst in {sensor, ejec}:
            t0 = time.time()
            lec, tk = F.resolver(inst)
            cache_ctx[inst] = _contexto_m1_rapido(lec(20250721, 20260930, str(DATA_LOCAL)), tk, con_perfil=usa_perfil, con_ticks=True)
            print(f"[ctx] {inst} cargado en {time.time() - t0:.1f}s ({len(cache_ctx[inst]['c'])} velas, perfil={usa_perfil})", flush=True)

        for cid, st in lista:
            sp = st["spec"]
            exp = importlib.import_module(sp["experimento"])
            fr, ex = friccion_canonica(ejec)
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            for tramo, per in (("desc", sp.get("desc")), ("rep", rep)):
                if not per:
                    continue
                k = f"{cid}/{tramo}"
                out_f = CRUDO / f"{cid}__{tramo}.json"
                if out_f.exists():
                    continue
                t1 = time.time()
                d0, d1 = int(per[0]), min(int(per[1]), 20260930)
                ctx = _recortar_ctx(cache_ctx[sensor], d0, d1, dias_cal=40)
                ctx.update(sensor=sensor, desde_eval=d0)
                cx_ej = _recortar_ctx(cache_ctx[ejec], d0, d1, dias_cal=40) if ejec != sensor else None
                res = ET.ejecutar("MARGINALES", exp, ctx, friccion=fr, extra_adverso=ex, cx_ej=cx_ej,
                                  params=dict(cortes=st["cortes"], estadistico="R"), log=lambda s: None)
                out_f.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
                meta[k] = dict(handle=f"local/{cid}/{tramo}", familia=sp["familia"], experimento=sp["experimento"],
                               sensor=sensor, ejecucion=ejec)
                (SAL / "handles.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
                print(f"[ok] {k} ({res.get('operaciones', 0)} ops, {time.time() - t1:.1f}s)", flush=True)
        cache_ctx.clear()
        gc.collect()


def lanzar():
    """Lanza en Kaggle las etapas MARGINALES faltantes (p. ej. campañas con sensor Dukascopy o almacén de zonas) con `calentamiento_dias=40`."""
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None)
    cs = run.cuentas()
    SAL.mkdir(parents=True, exist_ok=True)
    hf = SAL / "handles_kaggle.json"
    hs = json.loads(hf.read_text(encoding="utf-8")) if hf.exists() else {}
    for cid, st in _todas_las_campanas_r():
        sp = st["spec"]
        sensor = sp["sensor"]
        ejec = sp.get("ejecucion") or sensor
        es_local = (
            not sensor.startswith("DK:")
            and not ejec.startswith("DK:")
            and not sp.get("confirmador")
            and not sp.get("datasets_extra")
            and (DATA_LOCAL / f"{sensor}_ticks.parquet").exists()
        )
        if es_local:
            continue
        rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
        for t, per in (("desc", sp.get("desc")), ("rep", rep)):
            k = f"{cid}/{t}"
            out_f = CRUDO / f"{cid}__{t}.json"
            if k in hs or out_f.exists() or not per:
                continue
            try:
                h = run.lanzar(
                    dict(sp, cid=f"{cid}-CTX-{t}", estadistico="R", cuenta_kaggle=cs[len(hs) % len(cs)]),
                    "MARGINALES",
                    dict(cortes=st["cortes"], calentamiento_dias=40),
                    [int(per[0]), int(per[1])],
                )
            except Exception as ex:
                print("no se lanzó", k, str(ex)[-160:], flush=True)
                continue
            hs[k] = dict(handle=h, familia=sp["familia"], experimento=sp["experimento"],
                         sensor=sp["sensor"], ejecucion=sp.get("ejecucion") or sp["sensor"])
            hf.write_text(json.dumps(hs, indent=1, ensure_ascii=False), encoding="utf-8")
            print("lanzada", k, h, flush=True)


def traer():
    from edgelab.research.embudo_runners import KaggleRunner
    run = KaggleRunner(raiz=None)
    hs = {}
    for fn in ("handles.json", "handles_kaggle.json"):
        p = SAL / fn
        if p.exists():
            hs.update(json.loads(p.read_text(encoding="utf-8")))
    pend = 0
    for k, v in hs.items():
        if str(v.get("handle", "")).startswith("local/"):
            continue
        f = CRUDO / (k.replace("/", "__") + ".json")
        if f.exists():
            continue
        e = run.estado(v["handle"])
        if e != "complete":
            pend += 1
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(run.traer(v["handle"]), default=float), encoding="utf-8")
    return pend


def _dl(y, v):
    """DerSimonian-Laird: media contraída hacia la media del grupo, error estándar, tau2, I2."""
    y, v = np.asarray(y, float), np.asarray(v, float)
    w = 1.0 / np.maximum(v, 1e-12)
    mu = float((w * y).sum() / w.sum())
    Q = float((w * (y - mu) ** 2).sum())
    k = len(y)
    denom = float(w.sum() - (w ** 2).sum() / w.sum())
    tau2 = max(0.0, (Q - (k - 1)) / denom) if (k > 1 and denom > 0) else 0.0
    ws = 1.0 / (np.maximum(v, 1e-12) + tau2)
    m = float((ws * y).sum() / ws.sum())
    se = float(np.sqrt(1.0 / ws.sum()))
    I2 = float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0
    return m, se, tau2, I2


def potencia_previa() -> dict:
    """Cálculo explícito de potencia (α=0,05 unilateral, 1-β=0,80 -> z_α + z_β = 2,487) publicado antes de mirar."""
    z_a = 1.6448536
    z_b = 0.8416212
    z_tot = z_a + z_b
    sigma_r = 1.20
    f_veto = 0.30
    # 1. En las 11 reglas solas (N=1100 ops en DESC+REP, ~280 sesiones; N=470 ops en REP)
    se_11_ops = sigma_r * np.sqrt(1.0 / (1100 * f_veto * (1.0 - f_veto)))
    se_11_cartera = sigma_r * np.sqrt(f_veto / (1100 * (1.0 - f_veto))) * 1.15  # factor 1.15 por clustering intradía
    se_11_rep = sigma_r * np.sqrt(f_veto / (470 * (1.0 - f_veto))) * 1.15
    # 2. En el meta-análisis global (K=20 clusters independientes) y por mecanismo (K=10 clusters), s_c=0.12R, tau=0.04R
    sc = 0.12
    tau = 0.04
    se_meta_20 = np.sqrt((sc ** 2 + tau ** 2) / 20.0)
    se_meta_10 = np.sqrt((sc ** 2 + tau ** 2) / 10.0)
    return dict(
        supuestos=dict(alfa_unilateral=0.05, potencia=0.80, sigma_R=sigma_r, fraccion_vetada=f_veto),
        reglas_11_desc_mas_rep=dict(
            n_ops=1100,
            se_diferencia_pasa_vs_vetado_R=round(float(se_11_ops), 4),
            mde_80_pasa_vs_vetado_R=round(float(z_tot * se_11_ops), 4),
            se_mejora_cartera_R=round(float(se_11_cartera), 4),
            mde_80_mejora_cartera_R=round(float(z_tot * se_11_cartera), 4),
        ),
        reglas_11_solo_rep=dict(
            n_ops=470,
            se_mejora_cartera_R=round(float(se_11_rep), 4),
            mde_80_mejora_cartera_R=round(float(z_tot * se_11_rep), 4),
        ),
        meta_global_20_clusters=dict(
            clusters=20,
            se_meta_R=round(float(se_meta_20), 4),
            umbral_sig_p05_R=round(float(z_a * se_meta_20), 4),
            mde_80_R=round(float(z_tot * se_meta_20), 4),
        ),
        meta_mecanismo_10_clusters=dict(
            clusters=10,
            se_meta_R=round(float(se_meta_10), 4),
            umbral_sig_p05_R=round(float(z_a * se_meta_10), 4),
            mde_80_R=round(float(z_tot * se_meta_10), 4),
        ),
    )


def _cargar_marginales_unificadas(tramo: str) -> list[dict]:
    """Une las marginales de `docs/research/programa_r_20261103/contexto_marginales/crudo/` (que traen `ctx_*` y `veto_*`) con las de
    `docs/research/atlas_ideas_r_20261102/crudo/` (para campañas CFD/zonas que sólo corrieron en Kaggle), etiquetando cada una con su
    `cluster_id = (familia_base, activo_subyacente)` y su `mecanismo` (`REVERSION`, `CONTINUACION`, `MIXTO`)."""
    ests = {cid: st for cid, st in _todas_las_campanas_r()}
    cids = set()
    for d in (CRUDO, ATLAS_PREV / "crudo"):
        if d.exists():
            for f in d.glob(f"*__{tramo}.json"):
                cids.add(f.name.split("__")[0])
    registros = []
    for cid in sorted(cids):
        st = ests.get(cid) or ests.get(cid[:-2])
        if not st:
            continue
        sp = st["spec"]
        mod = sp["experimento"]
        sensor = sp["sensor"]
        ejec = sp.get("ejecucion") or sensor
        activo = ACTIVO_SUBYACENTE.get(ejec, ACTIVO_SUBYACENTE.get(sensor, ejec))
        fbase = _familia_base(mod)
        cluster_id = f"{fbase}__{activo}"
        mec = MECANISMO_POR_MODULO.get(mod, "MIXTO")

        mg = {}
        f_prev = ATLAS_PREV / "crudo" / f"{cid}__{tramo}.json"
        if f_prev.exists():
            try:
                mg.update((json.loads(f_prev.read_text(encoding="utf-8")) or {}).get("marginales_globales") or {})
            except Exception:
                pass
        f_new = CRUDO / f"{cid}__{tramo}.json"
        if f_new.exists():
            try:
                mg.update((json.loads(f_new.read_text(encoding="utf-8")) or {}).get("marginales_globales") or {})
            except Exception:
                pass
        tot = mg.get("ejecución") or []
        N = sum(r["n"] for r in tot)
        S = sum(r["suma"] for r in tot)
        if N < 30:
            continue
        registros.append(dict(
            cid=cid,
            cluster_id=cluster_id,
            familia_base=fbase,
            activo=activo,
            mecanismo=mec,
            n=N,
            media_R=S / N,
            mg=mg,
        ))
    return registros


def _efectos_por_estrato(tramo: str, estrato: str, claves: tuple[str, ...]) -> dict[str, list[tuple[str, float, float]]]:
    """Calcula `(cluster_id, d_cluster, var_cluster)` para cada etiqueta `var=nivel`, colapsando primero las campañas que comparten
    `cluster_id = (familia_base, activo)` (p. ej. Futuro + CFD del mismo subyacente) en una sola observación independiente."""
    regs = _cargar_marginales_unificadas(tramo)
    if estrato in ("REVERSION", "CONTINUACION"):
        regs = [r for r in regs if r["mecanismo"] == estrato]
    # Agrupar por (etiqueta, cluster_id) -> lista de (d_i, v_i)
    por_et_cluster = defaultdict(lambda: defaultdict(list))
    for r in regs:
        mu = r["media_R"]
        mg = r["mg"]
        for comp in claves:
            if comp not in mg:
                continue
            et_nombres = mg.get(comp + ".etiquetas") or CC.ETIQUETAS_CONTEXTO.get(comp) or []
            for fila in mg.get(comp, []):
                if fila["n"] < 30 or fila["sesiones"] < 10:
                    continue
                lv = int(fila["nivel"])
                nom_lv = et_nombres[lv] if lv < len(et_nombres) else str(lv)
                m = fila["suma"] / fila["n"]
                var = max(fila["suma2"] / fila["n"] - m * m, 1e-12)
                etiqueta = f"{comp}={nom_lv}"
                por_et_cluster[etiqueta][r["cluster_id"]].append((m - mu, var / fila["sesiones"]))

    # Colapso Futuro + CFD dentro de cada cluster independiente
    out = {}
    for etiqueta, mapa_cl in por_et_cluster.items():
        xs = []
        for cl_id, pares in sorted(mapa_cl.items()):
            d_cl = float(np.mean([p[0] for p in pares]))
            v_cl = float(np.mean([p[1] for p in pares]))
            xs.append((cl_id, d_cl, v_cl))
        out[etiqueta] = xs
    return out


def meta_analizar_claves(claves: tuple[str, ...], min_clusters: int = 4) -> dict:
    """Corre el meta-análisis DerSimonian-Laird en `GLOBAL`, `REVERSION` y `CONTINUACION`, con BH q<=0,10 en DESC y confirmación
    unilateral p<0,05 con mismo signo en REP."""
    from edgelab.funnel.escalera import _N
    res = {}
    for estrato in ("GLOBAL", "REVERSION", "CONTINUACION"):
        tramos = {}
        for tramo in ("desc", "rep"):
            E = _efectos_por_estrato(tramo, estrato, claves)
            filas = []
            for et, xs in E.items():
                if len(xs) < min_clusters:
                    continue
                m, se, tau2, I2 = _dl([x[1] for x in xs], [x[2] for x in xs])
                z = m / se if se > 0 else 0.0
                p_bil = float(2.0 * (1.0 - _N.cdf(abs(z))))
                filas.append(dict(
                    etiqueta=et,
                    estrato=estrato,
                    clusters_independientes=len(xs),
                    efecto_R=round(m, 5),
                    se_R=round(se, 5),
                    ic90=[round(m - 1.645 * se, 5), round(m + 1.645 * se, 5)],
                    z=round(z, 3),
                    p_bilateral=round(p_bil, 6),
                    I2=round(I2, 3),
                    mismo_signo=round(float(np.mean(np.sign([x[1] for x in xs]) == np.sign(m))), 3),
                ))
            tramos[tramo] = sorted(filas, key=lambda r: r["p_bilateral"])
        d = tramos["desc"]
        m_tot = len(d)
        for i, r in enumerate(d):
            r["bh"] = bool(r["p_bilateral"] <= 0.10 * (i + 1) / m_tot) if m_tot else False
        k_max = max([i for i, r in enumerate(d) if r["bh"]], default=-1)
        for i, r in enumerate(d):
            r["descubierta"] = bool(i <= k_max)
        rep_map = {r["etiqueta"]: r for r in tramos["rep"]}
        for r in d:
            q = rep_map.get(r["etiqueta"])
            r["replica"] = q
            r["confirmada"] = bool(
                r["descubierta"]
                and q is not None
                and np.sign(q["efecto_R"]) == np.sign(r["efecto_R"])
                and (q["p_bilateral"] / 2.0) < 0.05
            )
        res[estrato] = tramos
    return res


def _operaciones_11_reglas() -> list[dict]:
    """Carga las operaciones de desarrollo (`DESC` y `REP`, Ago 2025 – Sep 2026) de las 11 estrategias seguidas en
    `Estabilidad_mensual_en_R.html` y las etiqueta causalmente con `contexto_comun.etiquetar_operaciones` sobre su activo de ejecución
    (`ES` o `NQ`, con calentamiento desde 2025-07-21)."""
    if not (DATA_LOCAL / "ES_ticks.parquet").exists() or not (DATA_LOCAL / "NQ_ticks.parquet").exists():
        return []
    cache_sim = {}
    cache_vela = {}
    for inst in ("ES", "NQ"):
        lec, tk = F.resolver(inst)
        sim = _contexto_m1_rapido(lec(20250721, 20260930, str(DATA_LOCAL)), tk, con_perfil=False, con_ticks=False)
        cache_sim[inst] = sim
        cache_vela[inst] = {"contexto_vela": CC.por_vela(sim)}

    ops = []
    # 1. Las 8 reglas con trayectorias completas en `docs/research/programa_r_20261103/trayectorias/`
    for f in sorted((ROOT / "docs/research/programa_r_20261103/trayectorias").glob("*__*.json")):
        regla, tramo = f.stem.split("__")
        inst = "ES" if "ES" in regla else "NQ"
        sim = cache_sim[inst]
        t_sim = sim["t"]
        c_sim = sim["c"]
        trs = json.loads(f.read_text(encoding="utf-8")).get("trayectorias") or []
        if not trs:
            continue
        ks = np.clip(np.searchsorted(t_sim, [tr["t"] for tr in trs]), 0, len(t_sim) - 1)
        lados = np.array([float(tr["lado"]) for tr in trs])
        rgs = np.array([float(tr["riesgo"]) for tr in trs])
        obj_r = np.array([float(tr["objetivo_R"]) for tr in trs])
        e = c_sim[ks]
        st = e - lados * rgs
        tp = e + lados * obj_r * rgs
        O = np.column_stack([np.arange(len(trs)), np.zeros(len(trs)), ks, np.zeros(len(trs)), lados, e, st, tp, np.zeros(len(trs))])
        etq = CC.etiquetar_operaciones(sim, O, cache=cache_vela[inst])
        for idx_op, tr in enumerate(trs):
            ses = int(tr["ses"])
            mes = str(ses)[:6]
            ops.append(dict(
                regla=regla,
                tramo=tramo,
                inst=inst,
                ses=ses,
                mes=mes,
                R=float(tr["R_regla"]),
                **{k: int(etq[k][idx_op]) for k in CC.ETIQUETAS_CONTEXTO},
            ))

    # 2. Las 3 reglas restantes de las 11: U1-CRUZADO, TORI-NQ-R y CONF-CVR-CFD-NQ-R
    extras = [
        ("U1-CRUZADO", ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r/U1-CRUZADO__desc.json", "desc", "NQ", "REVERSION", 2.5),
        ("U1-CRUZADO", ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r/U1-CRUZADO__rep.json", "rep", "NQ", "REVERSION", 2.5),
        ("TORI-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/TORI-NQ-R__desc.json", "desc", "NQ", "CONTINUACION", 2.0),
        ("TORI-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/TORI-NQ-R__oos.json", "rep", "NQ", "CONTINUACION", 2.0),
        ("CONF-CVR-CFD-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/CONF-CVR-CFD-NQ-R__desc.json", "desc", "NQ", "REVERSION", 1.5),
        ("CONF-CVR-CFD-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/CONF-CVR-CFD-NQ-R__oos.json", "rep", "NQ", "REVERSION", 1.5),
    ]
    for regla, ruta, tramo, inst, mec, rr_obj in extras:
        if not ruta.exists():
            continue
        d = json.loads(ruta.read_text(encoding="utf-8")).get("operaciones") or {}
        ts = np.asarray(d.get("t", []), float)
        ses_arr = np.asarray(d.get("ses", []), int)
        neto = np.asarray(d.get("neto", []), float)
        rg = np.asarray([np.nan if v is None else v for v in d.get("riesgo", [])], float)
        R_arr = neto / rg
        ok = np.isfinite(R_arr) & (ts > 0)
        if not ok.any():
            continue
        ts, ses_arr, rg, R_arr = ts[ok], ses_arr[ok], rg[ok], R_arr[ok]
        sim = cache_sim[inst]
        ks = np.clip(np.searchsorted(sim["t"], ts), 0, len(sim["t"]) - 1)
        c_sim = sim["c"]
        # Inferencia causal del lado de la operación a partir del movimiento previo de 30 velas (tendencia en TORI, fade en U1/CONF-CVR)
        k_prev = np.maximum(0, ks - 30)
        mov30 = np.where( c_sim[ks] >= c_sim[k_prev], 1.0, -1.0 )
        lados = mov30 if mec == "CONTINUACION" else -mov30
        e = c_sim[ks]
        st = e - lados * rg
        tp = e + lados * rr_obj * rg
        O = np.column_stack([np.arange(len(ts)), np.zeros(len(ts)), ks, np.zeros(len(ts)), lados, e, st, tp, np.zeros(len(ts))])
        etq = CC.etiquetar_operaciones(sim, O, cache=cache_vela[inst])
        for idx_op in range(len(ts)):
            ses = int(ses_arr[idx_op])
            ops.append(dict(
                regla=regla,
                tramo=tramo,
                inst=inst,
                ses=ses,
                mes=str(ses)[:6],
                R=float(R_arr[idx_op]),
                **{k: int(etq[k][idx_op]) for k in CC.ETIQUETAS_CONTEXTO},
            ))
    return ops


def evaluar_en_11_reglas(ops: list[dict], B_nulo: int = 2000, seed: int = 20261104) -> dict:
    """Evalúa los 4 vetos estructurales y las condiciones de contexto sobre las 11 reglas (`DESC`, `REP` y `TOTAL` Ago 2025 – Sep 2026),
    aplicando las 3 compuertas secundarias declaradas:
      1. Consistencia entre reglas (>= 8/11 o >= 70% de las reglas afectadas mejoran su R medio).
      2. Estabilidad Leave-One-Month-Out (LOMO: 14/14 subperíodos dejando 1 mes afuera mantienen ΔR > 0).
      3. Control nulo mensual (`EXP-004b`: descartar al azar la misma cantidad de operaciones dentro de cada `(regla, mes)`)."""
    if not ops:
        return {}
    df = pd.DataFrame(ops)
    # Definimos los candidatos a veto (1 = vetado, 0 = pasa)
    candidatos = {
        # 1. Los 4 vetos estructurales propuestos a priori
        "veto_horizonte": (df["veto_horizonte"].to_numpy() == 1),
        "veto_muro": (df["veto_muro"].to_numpy() == 1),
        "veto_huida": (df["veto_huida"].to_numpy() == 1),
        "veto_liquidez_macro": (df["veto_liquidez_macro"].to_numpy() == 1),
        "veto_huida_o_horizonte": (df["veto_huida"].to_numpy() == 1) | (df["veto_horizonte"].to_numpy() == 1),
        "veto_contra_tendencia_fuerte": (df["ctx_tendencia_favor"].to_numpy() == 0),
        "veto_eficiencia_contra_alta": (df["ctx_eficiencia_contra"].to_numpy() == 2),
        "veto_vol_diaria_baja": (df["ctx_vol_diaria"].to_numpy() == 0),
        # 2. Los filtros de contexto confirmados en el Atlas global y de REVERSION (BH q<=0,10 en DESC + p_unilateral<0,05 en REP)
        "atlas_veto_atr_rel_bajo": (df["ctx_atr_rel"].to_numpy() == 0),
        "atlas_veto_vol_rel_bajo": (df["ctx_vol_rel"].to_numpy() == 0),
        "atlas_veto_compresion_intradia": (df["ctx_atr_rel"].to_numpy() == 0) & (df["ctx_vol_rel"].to_numpy() == 0),
        "atlas_veto_sin_iman_estructural": (df["veto_muro"].to_numpy() == 0),
        "atlas_veto_sin_iman_en_compresion": (df["veto_muro"].to_numpy() == 0) & ((df["ctx_atr_rel"].to_numpy() == 0) | (df["ctx_vol_rel"].to_numpy() == 0)),
    }
    R = df["R"].to_numpy(float)
    reglas = sorted(df["regla"].unique())
    meses = sorted(df["mes"].unique())
    tramo_arr = df["tramo"].to_numpy()
    regla_arr = df["regla"].to_numpy()
    mes_arr = df["mes"].to_numpy()

    rng = np.random.default_rng(seed)
    # Grupos (regla, mes) para el control nulo mensual EXP-004b
    grupos_rm = []
    for r in reglas:
        for m in meses:
            idx = np.flatnonzero((regla_arr == r) & (mes_arr == m))
            if len(idx):
                grupos_rm.append(idx)

    resultados = {}
    for nombre, vetado in candidatos.items():
        pasa = ~vetado
        n_tot = len(R)
        n_vet = int(vetado.sum())
        n_pasa = int(pasa.sum())
        if n_vet == 0 or n_pasa == 0:
            continue
        r_base = float(R.mean())
        r_pasa = float(R[pasa].mean())
        r_vet = float(R[vetado].mean())
        delta_r = r_pasa - r_base

        # Desglose por tramo (desc vs rep)
        por_tramo = {}
        for tr in ("desc", "rep"):
            mt = (tramo_arr == tr)
            mp = mt & pasa
            mv = mt & vetado
            por_tramo[tr] = dict(
                n_total=int(mt.sum()),
                n_pasa=int(mp.sum()),
                n_vetado=int(mv.sum()),
                R_base=round(float(R[mt].mean()), 4) if mt.any() else None,
                R_pasa=round(float(R[mp].mean()), 4) if mp.any() else None,
                R_vetado=round(float(R[mv].mean()), 4) if mv.any() else None,
                delta_R=round(float(R[mp].mean() - R[mt].mean()), 4) if (mt.any() and mp.any()) else 0.0,
            )

        # Compuerta 1: Consistencia por regla
        por_regla = {}
        reglas_mejoradas = 0
        reglas_afectadas = 0
        for r in reglas:
            mr = (regla_arr == r)
            mp = mr & pasa
            mv = mr & vetado
            rb = float(R[mr].mean())
            rp = float(R[mp].mean()) if mp.any() else rb
            dif_r = rp - rb
            if mv.any():
                reglas_afectadas += 1
                if dif_r > 0:
                    reglas_mejoradas += 1
            por_regla[r] = dict(n_total=int(mr.sum()), n_vetado=int(mv.sum()), R_base=round(rb, 4), R_pasa=round(rp, 4), delta_R=round(dif_r, 4))

        # Compuerta 2: Leave-One-Month-Out (LOMO) en los 14 meses
        lomo_deltas = []
        for m_out in meses:
            mm = (mes_arr != m_out)
            mp = mm & pasa
            lomo_deltas.append(float(R[mp].mean() - R[mm].mean()) if mp.any() else 0.0)
        lomo_positivos = int(sum(d > 0 for d in lomo_deltas))

        # Estabilidad mensual de la cartera (meses rojos y desviación de medias mensuales)
        medias_mes_base = [float(R[mes_arr == m].mean()) for m in meses if (mes_arr == m).any()]
        medias_mes_pasa = [float(R[(mes_arr == m) & pasa].mean()) for m in meses if ((mes_arr == m) & pasa).any()]
        meses_rojos_base = int(sum(x < 0 for x in medias_mes_base))
        meses_rojos_pasa = int(sum(x < 0 for x in medias_mes_pasa))

        # Compuerta 3: Control nulo emparejado por (regla, mes) (EXP-004b, B=2.000)
        # En cada (regla, mes) donde el veto descartó k_g operaciones de n_g, elegimos al azar k_g operaciones de ese mismo (regla, mes)
        sum_total = float(R.sum())
        nulos_delta = np.empty(B_nulo, dtype=float)
        # Pre-filtramos sólo los grupos donde 0 < k_g < n_g o k_g == n_g
        grupos_activos = []
        suma_vet_fija = 0.0
        for idx_g in grupos_rm:
            k_g = int(vetado[idx_g].sum())
            if k_g == 0:
                continue
            if k_g == len(idx_g):
                suma_vet_fija += float(R[idx_g].sum())
            else:
                grupos_activos.append((R[idx_g], k_g))

        suma_vet_sim = np.full(B_nulo, suma_vet_fija, dtype=float)
        for r_g, k_g in grupos_activos:
            n_g = len(r_g)
            # Muestreo sin reemplazo por fila mediante argpartition de uniformes
            u = rng.random((B_nulo, n_g))
            sel = np.argpartition(u, k_g - 1, axis=1)[:, :k_g]
            suma_vet_sim += r_g[sel].sum(axis=1)
        r_pasa_sim = (sum_total - suma_vet_sim) / n_pasa
        nulos_delta = r_pasa_sim - r_base
        p_nulo_mensual = float((nulos_delta >= delta_r).mean())

        resultados[nombre] = dict(
            n_total=n_tot,
            n_pasa=n_pasa,
            n_vetado=n_vet,
            frac_vetada=round(n_vet / n_tot, 4),
            R_base=round(r_base, 4),
            R_pasa=round(r_pasa, 4),
            R_vetado=round(r_vet, 4),
            delta_R=round(delta_r, 4),
            por_tramo=por_tramo,
            compuertas=dict(
                reglas_mejoradas=reglas_mejoradas,
                reglas_afectadas=reglas_afectadas,
                lomo_meses_positivos=lomo_positivos,
                lomo_total_meses=len(meses),
                lomo_min_delta_R=round(float(min(lomo_deltas)), 4),
                p_nulo_mensual_exp004b=round(p_nulo_mensual, 4),
                nulo_q95_delta_R=round(float(np.percentile(nulos_delta, 95)), 4),
                pasa_todas_secundarias=bool(
                    reglas_afectadas > 0
                    and (reglas_mejoradas >= 8 or reglas_mejoradas / max(reglas_afectadas, 1) >= 0.70)
                    and lomo_positivos == len(meses)
                    and p_nulo_mensual < 0.05
                    and por_tramo["desc"]["delta_R"] > 0
                    and por_tramo["rep"]["delta_R"] > 0
                ),
            ),
            estabilidad_mensual=dict(
                meses_rojos_base=meses_rojos_base,
                meses_rojos_pasa=meses_rojos_pasa,
                sd_mensual_base=round(float(np.std(medias_mes_base)), 4),
                sd_mensual_pasa=round(float(np.std(medias_mes_pasa)), 4),
            ),
            por_regla=por_regla,
        )
    return resultados


def analizar() -> dict:
    SAL.mkdir(parents=True, exist_ok=True)
    pot = potencia_previa()
    claves_ctx = tuple(CC.ETIQUETAS_CONTEXTO.keys())
    claves_ejec = ("ejecución.entrada", "ejecución.objetivo", "ejecución.stop", "ejecución.be")

    meta_ctx = meta_analizar_claves(claves_ctx, min_clusters=4)
    meta_ejec = meta_analizar_claves(claves_ejec, min_clusters=4)

    ops_11 = _operaciones_11_reglas()
    eval_11 = evaluar_en_11_reglas(ops_11) if ops_11 else {}

    out = dict(
        fecha="2026-11-04",
        preregistro="docs/research/programa_r_20261103/PREREGISTRO_CONTEXTO_Y_VETOS_R_20261104.md",
        potencia_previa=pot,
        meta_contexto_y_vetos=meta_ctx,
        meta_ejecucion_colapsado_por_mecanismo=meta_ejec,
        evaluacion_11_reglas=eval_11,
    )
    (SAL / "RESULTADO.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    return out


def correr_cola():
    """Corre en paralelo YM y el resto de NQ posterior a ZGAP-NQ-R escribiendo atómicamente por `.tmp -> .json`."""
    CRUDO.mkdir(parents=True, exist_ok=True)
    camps = _todas_las_campanas_r()
    for inst_obj in ("YM", "NQ"):
        lista = []
        for cid, st in camps:
            sp = st["spec"]
            s = sp["sensor"]
            ej = sp.get("ejecucion") or s
            if s != inst_obj or ej != inst_obj or sp.get("confirmador") or sp.get("datasets_extra"):
                continue
            if cid == "ZGAP-NQ-R":
                continue
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            if any(not (CRUDO / f"{cid}__{tr}.json").exists() for tr, p in (("desc", sp.get("desc")), ("rep", rep)) if p):
                lista.append((cid, st))
        if not lista:
            continue
        t0 = time.time()
        lec, tk = F.resolver(inst_obj)
        ctx_full = _contexto_m1_rapido(lec(20250721, 20260930, str(DATA_LOCAL)), tk, con_perfil=False, con_ticks=True)
        print(f"[cola] {inst_obj} cargado en {time.time() - t0:.1f}s ({len(lista)} campanas)", flush=True)
        for cid, st in lista:
            sp = st["spec"]
            exp = importlib.import_module(sp["experimento"])
            fr, ex = friccion_canonica(inst_obj)
            rep = sp.get("oos") or ((st.get("pistas_replica") or {}).get("ventana"))
            for tr, per in (("desc", sp.get("desc")), ("rep", rep)):
                if not per:
                    continue
                out_f = CRUDO / f"{cid}__{tr}.json"
                if out_f.exists():
                    continue
                t1 = time.time()
                d0, d1 = int(per[0]), min(int(per[1]), 20260930)
                ctx = _recortar_ctx(ctx_full, d0, d1, dias_cal=40)
                ctx.update(sensor=inst_obj, desde_eval=d0)
                res = ET.ejecutar("MARGINALES", exp, ctx, friccion=fr, extra_adverso=ex, cx_ej=None,
                                  params=dict(cortes=st["cortes"], estadistico="R"), log=lambda s: None)
                tmp = out_f.with_suffix(".tmp")
                tmp.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
                tmp.replace(out_f)
                print(f"[cola-ok] {cid}/{tr} ({res.get('operaciones', 0)} ops, {time.time() - t1:.1f}s)", flush=True)
        del ctx_full
        gc.collect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("correr_local", "correr_cola", "lanzar", "traer", "analizar"))
    a = ap.parse_args()
    if a.cmd == "correr_local":
        correr_local()
    elif a.cmd == "correr_cola":
        correr_cola()
    elif a.cmd == "lanzar":
        lanzar()
    elif a.cmd == "traer":
        print("pendientes", traer())
    else:
        r = analizar()
        print("=== POTENCIA PREVIA ===")
        print(json.dumps(r["potencia_previa"], indent=2))
        for estrato in ("GLOBAL", "REVERSION", "CONTINUACION"):
            print(f"\n=== META CONTEXTO Y VETOS [{estrato}] (top 12 DESC) ===")
            for x in r["meta_contexto_y_vetos"][estrato]["desc"][:12]:
                rep = x.get("replica") or {}
                print(
                    f"  {x['etiqueta']:36s} | K={x['clusters_independientes']:2d} | DESC {x['efecto_R']:+.4f}R (p={x['p_bilateral']:.4f}, bh={x['bh']}) "
                    f"| REP {rep.get('efecto_R', float('nan')):+.4f}R (p={rep.get('p_bilateral', float('nan')):.4f}) | conf={x['confirmada']}"
                )
        print("\n=== EVALUACION EN LAS 11 REGLAS (DESC + REP) ===")
        for k, v in r["evaluacion_11_reglas"].items():
            c = v["compuertas"]
            print(
                f"  {k:34s} | vet={v['frac_vetada']*100:4.1f}% | dR={v['delta_R']:+.4f}R "
                f"(DESC {v['por_tramo']['desc']['delta_R']:+.4f}R, REP {v['por_tramo']['rep']['delta_R']:+.4f}R) "
                f"| reglas+ {c['reglas_mejoradas']}/{c['reglas_afectadas']} | LOMO {c['lomo_meses_positivos']}/{c['lomo_total_meses']} "
                f"| p_nulo={c['p_nulo_mensual_exp004b']:.4f} | pasa={c['pasa_todas_secundarias']}"
            )
