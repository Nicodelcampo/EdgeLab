"""HFT-GC-P10-VETO (2026-11-05, Programa R): Entradas HFT de `GC` filtradas por camino despejado de Barreras HFT (`VETO_PURO`).

Pre-registro: `docs/research/hft_gc_p10_20261105/PREREGISTRO_BARRERAS_HFT_R.md`.

Evalúa sobre las señales de `HFTZonesGCClusterP10` en Oro COMEX (`GC`) el veto causal de entradas cuando existe una barrera
HFT delante en la dirección de la operación, parametrizando:
  - `mecanismo`:    `0: B2_RETEST_GRIS` · `1: B1_FLECHA_CONT` · `2: A1_CLUSTER_FADE` · `3: A2_CLUSTER_PULLBACK`
  - `franja_ny`:    `0: Asia` · `1: Londres` · `2: COMEX Mañana` · `3: NY Tarde` · `4: cualquiera`
  - `tipo_barrera`: `0: TODAS_HFT` · `1: FUERTE_VOL_ABS` · `2: BORDE_GRIS_OPUESTO` · `3: SOLO_CLUSTER_P10`
  - `antiguedad`:   `0: 5m` · `1: 15m` · `2: 60m` · `3: 180m` · `4: sesion`
  - `mitigacion`:   `0: VIRGEN` · `1: NO_ATRAVESADA`
  - `rango_libre`:  `>= 1.0R` · `>= 2.0R` · `>= 4.0R` (cielo abierto amplio de cara a la entrada)
  - `ejecución`:    `("S3_ATR", 2.0)` · `("S3_ATR", 3.0)`
"""
from __future__ import annotations

import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from edgelab.bridge.indicators import hft_gc_cluster_p10 as HGC
from edgelab.research import barreras_hft as BH, hft_gc_cluster_p10 as BASE_EXP
from edgelab.research.contexto_comun import atr_sesion
from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import lineas_salida  # noqa: F401
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "HFT-GC-P10-VETO"
INDICADORES = ["HFT-GC-CLUSTER-P10"]
NORMALIZAR = "riesgo"
PREFLIGHT_T0_S = 1_760_047_200
LINEAS_SOLO_TIEMPO = True
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)

CORTES_LIBRE_R = (1.0, 2.0, 4.0)
VARIABLES = [
    Variable("mecanismo", "mec", "grupo", categoria=len(BASE_EXP.MECANISMOS)),
    Variable("franja_ny", "franja", "eq_any", categoria=4),
    Variable("tipo_barrera", "t_bar", "grupo", categoria=len(BH.TIPOS_BARRERA)),
    Variable("antiguedad", "edad", "grupo", categoria=len(BH.ANTIGUEDADES)),
    Variable("mitigacion", "mit", "grupo", categoria=len(BH.MITIGACIONES)),
    Variable("rango_libre", "d_lib_r", "ge", cortes=CORTES_LIBRE_R, piso=True),
]
EJES_ORDINALES = (5,)
EJECUCIONES = [("S3_ATR", 2.0), ("S3_ATR", 3.0)]
BASE = {
    "mecanismo": 1,
    "franja_ny": 2,
    "tipo_barrera": 0,
    "antiguedad": 2,
    "mitigacion": 1,
    "rango_libre": 1,
    "ejecución": 0,
}
VACIO = ["k", "ses", "lado", "mec", "franja", "t_bar", "edad", "mit", "d_lib_r", "d_lib_px", "ent", "sl", "riesgo"]


def _fuente_sintetica_liviana(ctx: dict) -> Dict[str, pd.DataFrame]:
    """SOLO preflight y controles sintéticos (cuando no hay `sensor`): genera rachas causales espaciadas para mantener
    potencia estadística (`>= 30` ops por celda) sin multiplicar por 40 decenas de miles de velas sintéticas."""
    t = np.asarray(ctx["t"], np.int64)
    o = np.asarray(ctx["o"], float)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    c = np.asarray(ctx["c"], float)
    v = np.asarray(ctx["v"], float)
    tick = float(ctx["tick"])
    n = len(c)
    if n < 10:
        return HGC.ejecutar_detector_completo(
            np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, float), np.zeros(0, np.int64), tick, 50
        )

    dt = np.diff(t, prepend=t[0]).astype(float)
    mc = np.cumsum(np.minimum(np.maximum(dt, 0.0), 300.0))
    rng_tk = np.round((h - l) / tick).astype(np.int64)
    body_tk = np.round(np.abs(c - o) / tick).astype(np.int64)
    idx_all = np.arange(n)
    cand = np.flatnonzero((idx_all >= 5) & (rng_tk >= 4) & ((idx_all % 16) == 0))
    if not len(cand):
        return HGC.ejecutar_detector_completo(
            np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, float), np.zeros(0, np.int64), tick, 50
        )

    z_dir = np.where(c[cand] >= o[cand], 1, -1).astype(np.int64)
    es_abs = body_tk[cand] <= np.maximum(1, rng_tk[cand] // 2)
    z_bkt = np.where(es_abs, 3, np.where(v[cand] >= v[cand - 1], 0, 1)).astype(np.int64)
    lo_px = np.where(z_dir == 1, l[cand], np.minimum(o[cand], c[cand]))
    hi_px = np.where(z_dir == 1, np.maximum(o[cand], c[cand]), h[cand])
    hi_px = np.maximum(hi_px, lo_px + tick)
    lo_tk = np.round(lo_px / tick).astype(np.int64)
    hi_tk = np.maximum(lo_tk + 1, np.round(hi_px / tick).astype(np.int64))
    lo_px = lo_tk.astype(float) * tick
    hi_px = hi_tk.astype(float) * tick
    z_vol = v[cand] + 0.17 * rng_tk[cand].astype(float) + 0.03 * (cand % 7).astype(float)
    t_avail_ns = t[cand] * 10**9

    cl_cols, clust_df = HGC.evaluar_clusters_p10_causal(
        cand, cand, t_avail_ns, lo_tk, hi_tk, z_bkt, z_vol, mc[cand],
        tick=tick, min_zonas_cluster=4, vigencia_zona_min=360.0,
        ventana_grupos=100, min_grupos_warmup=12, percentil_altura=20.0,
        comparacion_estricta=False, extension_cluster_barras=360,
    )
    b_end_ns = t * 10**9
    aw_code, aw_dir, _, aw_ns = HGC.resolver_alejamiento_barras_nb(
        cand, lo_px, hi_px, z_dir, z_bkt, c[cand],
        b_end_ns, h, l, tick,
        alejamiento_ticks=10, excluir_vshape=0, vshape_pct=50.0, excluir_absorb=0, max_barras=0,
    )
    if len(clust_df):
        c_eb = clust_df["confirmed_bar"].to_numpy(np.int64)
        c_lo = clust_df["lo"].to_numpy(float)
        c_hi = clust_df["hi"].to_numpy(float)
        c_aw_code, c_aw_dir, _, c_aw_ns = HGC.resolver_alejamiento_barras_nb(
            c_eb, c_lo, c_hi, np.ones(len(clust_df), np.int64), np.full(len(clust_df), 3, np.int64), c_lo,
            b_end_ns, h, l, tick,
            alejamiento_ticks=10, excluir_vshape=0, vshape_pct=50.0, excluir_absorb=0, max_barras=0,
        )
        clust_df["away_res_code"] = c_aw_code
        clust_df["away_dir"] = c_aw_dir
        clust_df["t_away_ns"] = c_aw_ns
    else:
        clust_df["away_res_code"] = np.zeros(0, np.int64)
        clust_df["away_dir"] = np.zeros(0, np.int64)
        clust_df["t_away_ns"] = np.zeros(0, np.int64)

    zones_df = pd.DataFrame(dict(
        zone_id=np.arange(1, len(cand) + 1, dtype=np.int64),
        t_ns=t_avail_ns,
        lo=lo_px,
        hi=hi_px,
        dir=z_dir,
        bucket=z_bkt,
        total_vol=z_vol,
        market_clock_sec=mc[cand],
        in_cluster=cl_cols["in_cluster"],
        first_in_cluster_ns=cl_cols["first_in_cluster_ns"],
        away_res_code=aw_code,
        away_dir=aw_dir,
        t_away_ns=aw_ns,
    ))
    return {"HFTGCP10": zones_df, "HFTGCP10_CLUST": clust_df}


def cargar_fuente_barreras_gc(ctx: dict) -> Dict[str, pd.DataFrame]:
    if "zonas_hftgc" in ctx:
        return ctx["zonas_hftgc"]
    sensor = ctx.get("sensor") or os.environ.get("SENSOR")
    if not sensor:
        return _fuente_sintetica_liviana(ctx)
    return BASE_EXP.cargar_fuente_gc(ctx)


def candidatos_s3_gc(ctx: dict, fuente: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Genera las entradas candidatas base `(k, ses, lado, mec, franja, ent, sl, riesgo)` bajo `S3_ATR`."""
    cols = ["k", "ses", "lado", "mec", "franja", "ent", "sl", "riesgo"]
    t = np.asarray(ctx["t"], np.int64)
    if not len(t):
        return pd.DataFrame(columns=cols)
    h = np.asarray(ctx["h"], float)
    l = np.asarray(ctx["l"], float)
    c = np.asarray(ctx["c"], float)
    ses = np.asarray(ctx["ses"], np.int64)
    tick = float(ctx["tick"])
    n = len(c)

    atr_raw = atr_sesion(h, l, c, ses, 14)
    atr_ok = np.isfinite(atr_raw)
    atr = np.where(atr_ok, np.maximum(atr_raw, tick), tick)
    franjas = BASE_EXP._franja_oro_ny(minuto_ny(t - 60))

    Z = fuente["HFTGCP10"]
    C = fuente["HFTGCP10_CLUST"]
    t_min_ns = (int(t[0]) - 60) * 10**9
    t_max_ns = int(t[-1]) * 10**9

    raw = []
    if len(Z):
        aw_ok = (
            (Z["away_res_code"].to_numpy(np.int64) == 1)
            & (Z["t_away_ns"].to_numpy(np.int64) > t_min_ns)
            & (Z["t_away_ns"].to_numpy(np.int64) <= t_max_ns)
        )
        Za = Z.loc[aw_ok]
        if len(Za):
            ks = np.searchsorted(t, np.ceil(Za["t_away_ns"].to_numpy(np.int64) / 1e9).astype(np.int64), side="left")
            zlo_a = Za["lo"].to_numpy(float)
            zhi_a = Za["hi"].to_numpy(float)
            adir_a = Za["away_dir"].to_numpy(np.int64)
            for i in range(len(ks)):
                k = int(ks[i])
                if k < 1 or k >= n or not atr_ok[k]:
                    continue
                fr = int(franjas[k])
                lado = int(adir_a[i])
                if fr < 0 or lado == 0:
                    continue
                zlo, zhi, ak, sk = float(zlo_a[i]), float(zhi_a[i]), float(atr[k]), int(ses[k])
                raw.append((k, sk, lado, 0, fr, zlo, zhi, ak))
                raw.append((k, sk, lado, 1, fr, zlo, zhi, ak))

    if len(C):
        c_new = C.loc[(C["event_type"] == "NEW") & (C["t_ns"].to_numpy(np.int64) <= t_max_ns)]
        if len(c_new):
            k_conf = np.searchsorted(t, np.ceil(c_new["t_ns"].to_numpy(np.int64) / 1e9).astype(np.int64), side="left")
            clo_a = c_new["lo"].to_numpy(float)
            chi_a = c_new["hi"].to_numpy(float)
            c_aw_code = c_new["away_res_code"].to_numpy(np.int64)
            c_aw_dir = c_new["away_dir"].to_numpy(np.int64)
            c_aw_ns = c_new["t_away_ns"].to_numpy(np.int64)
            for i in range(len(k_conf)):
                kc = int(k_conf[i])
                clo, chi = float(clo_a[i]), float(chi_a[i])
                hc = max(chi - clo, 10.0 * tick)
                if 0 <= kc < n:
                    t_lim = int(t[kc]) + 360 * 60
                    tup = tlo = False
                    for j in range(kc + 1, n):
                        if int(t[j]) > t_lim:
                            break
                        if c[j] > chi + 1e-9 or c[j] < clo - 1e-9:
                            lado_f = -1 if c[j] > chi else 1
                            exc = (c[j] - chi) if lado_f == -1 else (clo - c[j])
                            fr = int(franjas[j])
                            if atr_ok[j] and fr >= 0:
                                aj = float(atr[j])
                                if exc <= max(8.0 * hc, 6.0 * aj):
                                    raw.append((j, int(ses[j]), lado_f, 2, fr, clo, chi, aj))
                            break
                        if h[j] >= chi - 1e-9:
                            tup = True
                        if l[j] <= clo + 1e-9:
                            tlo = True
                        if tup and tlo:
                            break

                if int(c_aw_code[i]) == 1 and t_min_ns < int(c_aw_ns[i]) <= t_max_ns:
                    kaw = int(np.searchsorted(t, int(np.ceil(c_aw_ns[i] / 1e9)), side="left"))
                    lado_p = int(c_aw_dir[i])
                    if 1 <= kaw < n and atr_ok[kaw] and lado_p != 0:
                        fr = int(franjas[kaw])
                        if fr >= 0:
                            raw.append((kaw, int(ses[kaw]), lado_p, 3, fr, clo, chi, float(atr[kaw])))

    if not raw:
        return pd.DataFrame(columns=cols)

    R = pd.DataFrame(raw, columns=["k", "ses", "lado", "mec", "franja", "zlo", "zhi", "atr"])
    R = R.sort_values(["k", "mec", "lado", "zlo", "zhi"], kind="stable").reset_index(drop=True)

    k_v = R["k"].to_numpy(np.int64)
    s_v = R["lado"].to_numpy(np.int64)
    mec_v = R["mec"].to_numpy(np.int64)
    zlo_v = R["zlo"].to_numpy(np.float64)
    zhi_v = R["zhi"].to_numpy(np.float64)
    atr_v = R["atr"].to_numpy(np.float64)
    c_k = c[k_v]
    h_k = h[k_v]
    l_k = l[k_v]

    ancho_z = np.maximum(zhi_v - zlo_v, tick)
    holgura = np.maximum(16.0 * tick, 0.50 * atr_v)
    piso_tk = 24.0 * tick
    es_lim = (mec_v == 0) | (mec_v == 3)
    es_b1 = mec_v == 1

    ent_raw = np.where(es_lim, np.where(s_v == 1, zhi_v, zlo_v), c_k)
    borde_op = np.where(s_v == 1, zlo_v, zhi_v)
    dist_b1 = (ent_raw - borde_op) * s_v
    extremo_v = np.where(s_v == 1, l_k, h_k)
    dist_a1 = np.maximum((ent_raw - extremo_v) * s_v, 2.0 * tick)

    dist_stop = np.where(
        es_lim,
        np.maximum(piso_tk, ancho_z + holgura),
        np.where(
            es_b1,
            np.maximum(piso_tk + 3.0 * tick, np.maximum(dist_b1, 4.0 * tick) + holgura),
            np.maximum(piso_tk, dist_a1 + holgura),
        ),
    )
    ent = np.round(ent_raw / tick) * tick
    st_raw = ent - s_v * dist_stop
    sl = np.where(s_v == 1, np.floor(st_raw / tick), np.ceil(st_raw / tick)) * tick
    riesgo = np.abs(ent - sl)
    ok = ((~es_b1) | (dist_b1 > -4.0 * tick)) & (riesgo >= tick)

    out = pd.DataFrame(dict(
        k=k_v[ok], ses=R["ses"].to_numpy(np.int64)[ok], lado=s_v[ok],
        mec=mec_v[ok], franja=R["franja"].to_numpy(np.int64)[ok],
        ent=ent[ok], sl=sl[ok], riesgo=riesgo[ok],
    ))
    return out.reset_index(drop=True)


def disparos(ctx: dict) -> pd.DataFrame:
    fuente = cargar_fuente_barreras_gc(ctx)
    B = candidatos_s3_gc(ctx, fuente)
    if not len(B):
        return pd.DataFrame(columns=VACIO)

    inv = BH.preparar_inventario_barreras(fuente["HFTGCP10"], ctx, fuente["HFTGCP10_CLUST"])
    k_b = B["k"].to_numpy(np.int64)
    s_b = B["lado"].to_numpy(np.int64)
    e_b = B["ent"].to_numpy(np.float64)
    r_b = B["riesgo"].to_numpy(np.float64)

    partes = []
    for ti in range(len(BH.TIPOS_BARRERA)):
        for ei in range(len(BH.ANTIGUEDADES)):
            for mi in range(len(BH.MITIGACIONES)):
                d_px = BH.evaluar_distancia_frontal(inv, k_b, s_b, e_b, r_b, ti, ei, mi)
                d_r = np.minimum(d_px / r_b, 100.0)
                partes.append(B.assign(t_bar=ti, edad=ei, mit=mi, d_lib_r=d_r, d_lib_px=d_px))

    D = pd.concat(partes, ignore_index=True)
    return D[VACIO].sort_values(["k", "mec", "lado", "t_bar", "edad", "mit"], kind="stable").reset_index(drop=True)


def niveles(fila: dict, ej: tuple, ctx: dict):
    _, mult_tp = ej
    k = int(fila["k"])
    s = int(fila["lado"])
    mec = int(fila["mec"])
    ent = float(fila["ent"])
    sl = float(fila["sl"])
    riesgo = float(fila["riesgo"])
    tick = float(ctx["tick"])
    limite = 1 if mec in (0, 3) else 2
    objetivo = float(np.round((ent + s * float(mult_tp) * riesgo) / tick) * tick)
    if (objetivo - ent) * s < tick:
        return None
    return (k, limite, s, ent, sl, objetivo, 0, (0 if s == 1 else 1), 0.0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    m = len(D)
    out = np.full((m, 9), np.nan, dtype=np.float64)
    if m == 0:
        return out
    _, mult_tp = ej
    tick = float(ctx["tick"])
    k = D["k"].to_numpy(np.int64)
    s = D["lado"].to_numpy(np.int64)
    mec = D["mec"].to_numpy(np.int64)
    ent = D["ent"].to_numpy(np.float64)
    sl = D["sl"].to_numpy(np.float64)
    riesgo = D["riesgo"].to_numpy(np.float64)

    limite = np.where((mec == 0) | (mec == 3), 1.0, 2.0)
    objetivo = np.round((ent + s * float(mult_tp) * riesgo) / tick) * tick
    valido = ((objetivo - ent) * s) >= tick

    out[valido, 0] = k[valido]
    out[valido, 1] = limite[valido]
    out[valido, 2] = s[valido]
    out[valido, 3] = ent[valido]
    out[valido, 4] = sl[valido]
    out[valido, 5] = objetivo[valido]
    out[valido, 6] = 0.0
    out[valido, 7] = np.where(s[valido] == 1, 0.0, 1.0)
    out[valido, 8] = 0.0
    return out

