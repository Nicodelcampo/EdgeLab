#!/usr/bin/env python3
"""Conductor vectorizado para EXTERNAS-ESTRUCTURALES-A5 y auditoría rápida de
los sobrevivientes de Fase 0 de EXTERNAS-28 (`Dual Thrust` X036-X039).

Resuelve el cuello de botella de memoria de `areas_expansion_run.m1_y_perfil` en
Windows (`ArrayMemoryError` al concatenar 18M de filas de perfil de volumen
sintético durante 20 años), construyendo el diccionario `ctx` directamente desde
`<INST>_M1_nonadj_utc.parquet` en ~5 segundos por instrumento y ~400 MB de RAM,
respetando exactamente:
1. Corte estricto en la frontera del holdout (`HOLDOUT_APERTURA_UTC_NS` y
   `_check(desde, hasta)` de `fuentes_ticks.py`).
2. Sesión CME (`America/New_York + 6h`, lunes a viernes) y redondeo al tick del
   futuro (`TICK_FUTURO`).
3. Los 4 ticks sintéticos por barra M1 (`o, l, h, c` si `c >= o`; `o, h, l, c` si
   `c < o`) que consume `edgelab/research/ejecucion.py` (`K40`, `m1_sintetico=True`).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque  # noqa: E402
from edgelab.research import a5 as A5  # noqa: E402
from edgelab.research import ejecucion as X  # noqa: E402
from edgelab.research import externas_estructurales_a5 as MOD  # noqa: E402
from edgelab.research import rasgos_comunes as RC  # noqa: E402
from edgelab.research.embudo_runners import friccion  # noqa: E402
from edgelab.research.fuentes_ticks import (  # noqa: E402
    TICK_FUTURO,
    TICK_M1NT8_EXTRA,
    _check,
)

DEFAULT_M1NT8_DIR = Path(
    os.environ.get(
        "EDGELAB_M1NT8_DIR",
        r"C:\Users\nicoc\OneDrive\Documentos\NinjaTrader 8\exports\edgelab_nt8_m1_parquet",
    )
)
DIR_CAMPANA = ROOT / "docs/research/externas_estructurales_a5_20261118"


def cargar_ctx_m1nt8_rapido(
    simbolo: str,
    desde: int,
    hasta: int,
    carpeta_datos: Path = DEFAULT_M1NT8_DIR,
) -> dict:
    """Construye el mismo `ctx` que `grilla_generica.contexto_m1(bloques_m1nt8(...))`
    pero de forma 100% vectorizada en NumPy, sin el `groupby(['t','p'])` de 18M
    filas de `m1_y_perfil` que agota la RAM en Windows."""
    _check(int(desde), int(hasta))
    tk = float(TICK_FUTURO.get(simbolo) or TICK_M1NT8_EXTRA[simbolo])
    f_pq = Path(carpeta_datos) / f"{simbolo}_M1_nonadj_utc.parquet"
    if not f_pq.exists():
        raise FileNotFoundError(f"No se encontró {f_pq}")

    D = pq.read_table(f_pq).to_pandas()
    t0_ns = (
        D.index.to_numpy() if "datetime" not in D else D["datetime"].to_numpy()
    ).astype("datetime64[ns]").astype(np.int64)

    # 1. Corte estricto de Holdout
    ok = t0_ns < HOLDOUT_APERTURA_UTC_NS
    D, t0_ns = D[ok], t0_ns[ok]

    # 2. Conversión vectorizada por hora única a America/New_York para sesión CME (+6h)
    uh, inv = np.unique(t0_ns // 3_600_000_000_000, return_inverse=True)
    uh_ny = (
        pd.to_datetime(uh * 3_600_000_000_000, unit="ns", utc=True)
        .tz_convert("America/New_York")
        .tz_localize(None)
    )
    uh_td = (uh_ny + pd.Timedelta(hours=6)).strftime("%Y%m%d").astype(np.int64).to_numpy()
    uh_dow = (uh_ny + pd.Timedelta(hours=6)).dayofweek.to_numpy()

    td = uh_td[inv]
    dow = uh_dow[inv]
    keep = (dow < 5) & (td >= int(desde)) & (td <= int(hasta))
    D, t0_ns, td = D[keep], t0_ns[keep], td[keep]

    # Timestamp de cierre del minuto en segundos UTC (igual que m1_y_perfil: (ts_ns // 60e9 + 1) * 60)
    t_sec = (t0_ns // 60_000_000_000 + 1) * 60

    # Ordenar y eliminar posibles duplicados de minuto
    orden = np.argsort(t_sec, kind="stable")
    t_sec = t_sec[orden]
    td = td[orden]
    o = np.round(D["open"].to_numpy(float)[orden] / tk) * tk
    h = np.round(D["high"].to_numpy(float)[orden] / tk) * tk
    l = np.round(D["low"].to_numpy(float)[orden] / tk) * tk
    c = np.round(D["close"].to_numpy(float)[orden] / tk) * tk
    v = D["volume"].to_numpy(float)[orden]

    if len(t_sec) > 1:
        uniq_mask = np.r_[True, t_sec[1:] != t_sec[:-1]]
        if not np.all(uniq_mask):
            t_sec, td = t_sec[uniq_mask], td[uniq_mask]
            o, h, l, c, v = o[uniq_mask], h[uniq_mask], l[uniq_mask], c[uniq_mask], v[uniq_mask]

    n = len(t_sec)
    sube = c >= o
    p1 = np.where(sube, l, h)
    p2 = np.where(sube, h, l)
    tpx = np.column_stack([o, p1, p2, c]).ravel()
    tstart = (np.arange(n + 1, dtype=np.int64) * 4)

    return dict(
        m1_sintetico=True,
        t=t_sec,
        o=o,
        h=h,
        l=l,
        c=c,
        v=v,
        ses=td.astype(np.int64),
        seg=np.zeros(n, dtype=np.int64),
        vp_px=np.zeros(0, dtype=float),
        vp_vol=np.zeros(0, dtype=float),
        vp_start=np.zeros(n + 1, dtype=np.int64),
        tpx=tpx,
        tstart=tstart,
        tick=tk,
        ticks_por_barra=None,
    )


def correr_campana_estructural(carpeta_datos: Path = DEFAULT_M1NT8_DIR) -> dict:
    os.environ["EDGELAB_M1NT8_DIR"] = str(carpeta_datos)
    cfg = json.loads((DIR_CAMPANA / "CAMPANA.json").read_text(encoding="utf-8"))
    defs = list(cfg["definiciones"]) + sorted(set(cfg.get("control", {}).values()))

    ev_list, ops_list, cnt = [], [], {}
    fase0_inst = {}

    for inst in cfg["instrumentos"]:
        t0 = time.time()
        ctx = cargar_ctx_m1nt8_rapido(inst, *cfg["ventana"], carpeta_datos=carpeta_datos)
        E = MOD.eventos(ctx)
        k = E.k.to_numpy(np.int64)
        E["ses"] = np.asarray(ctx["ses"])[k]
        E["t"] = np.asarray(ctx["t"], float)[k]
        E["bloque"] = A5.bloques(E.ses.to_numpy())
        E["inst"] = inst
        ev_list.append(E.drop(columns=[c for c in E.columns if c.startswith(("r_", "k_"))], errors="ignore"))

        # Fase 0 (sin retornos): fricción mediana sobre sesiones DESC
        f_pts = float(friccion(inst)[0])
        f0_d = {}
        E_desc = E[E.bloque == "DESC"]
        for d in defs:
            sub = E_desc[E_desc[d].astype(bool)]
            fr_r = (f_pts / sub["rg"].to_numpy(float)) if len(sub) else np.zeros(0)
            f0_d[d] = dict(
                n_desc=int(len(sub)),
                sesiones_desc=int(sub["ses"].nunique()) if len(sub) else 0,
                friccion_R_mediana=float(np.median(fr_r)) if len(fr_r) else None,
                friccion_R_p90=float(np.quantile(fr_r, 0.90)) if len(fr_r) else None,
                rg_pts_mediana=float(np.median(sub["rg"])) if len(sub) else None,
            )
        fase0_inst[inst] = dict(friccion_pts=f_pts, reglas=f0_d)

        # Desenlaces SÓLO en DESC y REP (HOLDOUT y EMBARGO permanecen sellados)
        vis = E[A5.con_desenlace(E)].reset_index(drop=True)
        O_inst = X.desenlaces(RC.agregar(vis, ctx), ctx, MOD.EJECUCIONES)
        ops_list.append(O_inst)

        cnt[inst] = {
            b: {d: int(E.loc[E.bloque == b, d].astype(bool).sum()) for d in defs}
            for b in ("DESC", "REP", "HOLDOUT", "EMBARGO")
        }
        print(f"[{inst}] {len(E)} eventos en {time.time() - t0:.1f}s | DESC: {cnt[inst]['DESC']}", flush=True)

    # Guardar EVENTOS.csv.gz, OPS_DESC_REP.csv.gz, CORRIDA.json, FASE0.json
    E_all = pd.concat(ev_list, ignore_index=True)
    E_all.to_csv(DIR_CAMPANA / "EVENTOS.csv.gz", index=False)

    O = pd.concat(ops_list, ignore_index=True)
    from a5_campana import columnas_ops
    keep = columnas_ops(O, cfg)
    O = O[keep]
    O.to_csv(DIR_CAMPANA / "OPS_DESC_REP.csv.gz", index=False)

    (DIR_CAMPANA / "CORRIDA.json").write_text(
        json.dumps(
            dict(ventana=cfg["ventana"], instrumentos=cfg["instrumentos"], marcas_por_bloque=cnt),
            indent=1,
        ),
        encoding="utf-8",
    )

    # Resumen global de Fase 0 (canasta ES + NQ + YM + GC)
    fr_map = {i: float(friccion(i)[0]) for i in cfg["instrumentos"]}
    E_desc_all = E_all[E_all.bloque == "DESC"].copy()
    E_desc_all["fric_R"] = E_desc_all["inst"].map(fr_map) / E_desc_all["rg"]
    f0_global = {}
    for d in defs:
        sub = E_desc_all[E_desc_all[d].astype(bool)]
        med = float(np.median(sub["fric_R"])) if len(sub) else None
        ses_n = int(sub["ses"].nunique()) if len(sub) else 0
        f0_global[d] = dict(
            n_desc=int(len(sub)),
            sesiones_desc_unicas=ses_n,
            friccion_R_mediana=med,
            friccion_R_media=float(np.mean(sub["fric_R"])) if len(sub) else None,
            pasa=bool(med is not None and med <= 0.08 and ses_n >= 30),
            por_instrumento={i: fase0_inst[i]["reglas"][d] for i in cfg["instrumentos"]},
        )
    pasan_f0 = [d for d in cfg["definiciones"] if f0_global[d]["pasa"]]
    (DIR_CAMPANA / "FASE0.json").write_text(
        json.dumps(
            dict(
                preregistro=cfg["preregistro"],
                regla="mediana fricción/riesgo <= 0,08 R y >= 30 sesiones DESC",
                pasan=pasan_f0,
                n_pasan=len(pasan_f0),
                reglas=f0_global,
            ),
            indent=1,
        ),
        encoding="utf-8",
    )

    # Evaluar DESC (EF3) + Potencia K49 en días para REP
    for e in cfg["ejecuciones"]:
        O[f"f_{e}"] = O.inst.map(fr_map) / O[f"k_{e}"]
    res_desc = A5.evaluar(
        O, "DESC", cfg["definiciones"], cfg["ejecuciones"], None, cfg.get("control"), cfg.get("limpios"), None
    )
    por_inst = {}
    for inst in cfg["instrumentos"]:
        for e in cfg["ejecuciones"]:
            for d in defs:
                g = O[(O.inst == inst) & (O.bloque == "DESC") & O[d].astype(bool) & O[f"r_{e}"].notna()]
                por_inst[f"{inst}|{d}|{e}"] = dict(
                    n=int(len(g)),
                    sesiones=int(g.ses.nunique()) if len(g) else 0,
                    R_bruto=float(g[f"r_{e}"].mean()) if len(g) else None,
                    R_neto=float((g[f"r_{e}"] - g[f"f_{e}"]).mean()) if len(g) else None,
                    fric_R=float(g[f"f_{e}"].mean()) if len(g) else None,
                )

    # Planes de lectura K49 (potencia en días para REP) para cada definición
    planes_k49 = {}
    for d in cfg["definiciones"]:
        e = cfg["ejecuciones"][0]
        g_desc = O[(O.bloque == "DESC") & O[d].astype(bool) & O[f"r_{e}"].notna()]
        n_rep = int(O[(O.bloque == "REP") & O[d].astype(bool)].ses.nunique())
        planes_k49[f"{d}|{e}"] = A5.plan_lectura(
            cfg["familia"],
            g_desc.ses.to_numpy(),
            (g_desc[f"r_{e}"] - g_desc[f"f_{e}"]).to_numpy(float),
            n_rep,
        )

    nom = A5.nominar(res_desc, 0.10, lambda k: True)
    desc_out = dict(
        preregistro=cfg["preregistro"],
        pruebas=len(res_desc),
        resultados=res_desc,
        por_instrumento=por_inst,
        planes_k49_rep=planes_k49,
        nominadas=nom,
        control=cfg.get("control", {}),
    )
    (DIR_CAMPANA / "DESC.json").write_text(json.dumps(desc_out, indent=1, default=float), encoding="utf-8")
    print("DESC terminado. Nominadas BH q=0.10:", nom, flush=True)
    return desc_out


def auditar_dual_thrust_externas28(carpeta_datos: Path = DEFAULT_M1NT8_DIR) -> dict:
    """Evalúa las 4 variantes de Dual Thrust (`X036`–`X039`) de `EXTERNAS-28` que
    pasan Fase 0 (`<= 0.08 R`) sobre `NQ, ES, YM, GC` (2006–2025 DESC) de forma
    vectorizada para incluir el diagnóstico completo en el reporte a Claude."""
    from edgelab.research import externas_a5 as EXT28
    from edgelab.research.estrategias import dual_thrust_chalek as dt_mod

    variantes_dt = ["X036", "X037", "X038", "X039"]
    mapa_all = {info["definicion"]: info for info in EXT28.mapa()}
    instrumentos = ("NQ", "ES", "YM", "GC")
    fr_map = {i: float(friccion(i)[0]) for i in instrumentos}
    ops_dt = []

    for inst in instrumentos:
        t0 = time.time()
        ctx = cargar_ctx_m1nt8_rapido(inst, 20060106, 20250731, carpeta_datos=carpeta_datos)
        t_arr = np.asarray(ctx["t"], float)
        ts_ms = (t_arr * 1000).astype(np.int64)
        ses_arr = np.asarray(ctx["ses"], np.int64)
        c_arr = np.asarray(ctx["c"], float)
        B = pd.DataFrame(
            dict(ts=ts_ms, o=ctx["o"], h=ctx["h"], l=ctx["l"], c=c_arr, v=ctx["v"], ses=ses_arr)
        )
        fin_ses = pd.Series(np.arange(len(ses_arr), dtype=np.int64), index=ses_arr).groupby(level=0).max().to_dict()

        filas = []
        for vid in variantes_dt:
            params = mapa_all[vid]["parametros"]
            S = dt_mod.senales(B, **params)
            for s in S:
                k = int(np.searchsorted(ts_ms, int(s["available_at"]), side="right") - 1)
                if k < 0 or k >= len(c_arr):
                    continue
                d = int(s["dir"])
                sl = float(s["stop_pts"])
                tp = float(s["target_pts"])
                if d not in (-1, 1) or not (sl > 0 and tp > 0 and np.isfinite(sl) and np.isfinite(tp)):
                    continue
                px = float(c_arr[k])
                filas.append(
                    {
                        "k": k,
                        "lado": d,
                        "ref": px + d * tp,
                        "ext": px - d * sl,
                        "rg": sl,
                        "obj": px + d * tp,
                        "stop": px - d * sl,
                        "fin": int(fin_ses[int(ses_arr[k])]),
                        vid: True,
                    }
                )
        if not filas:
            continue
        E = pd.DataFrame(filas)
        for vid in variantes_dt:
            if vid not in E:
                E[vid] = False
            E[vid] = E[vid].fillna(False).astype(bool)
        E = E.astype({"k": np.int64, "lado": np.int64, "fin": np.int64}).sort_values(["k", "lado"]).reset_index(drop=True)
        k_idx = E.k.to_numpy(np.int64)
        E["ses"] = ses_arr[k_idx]
        E["t"] = t_arr[k_idx]
        E["bloque"] = A5.bloques(E.ses.to_numpy())
        E["inst"] = inst
        vis = E[A5.con_desenlace(E)].reset_index(drop=True)
        O_i = X.desenlaces(vis, ctx, [("PRECIOS", "obj", "stop", "fin")])
        ops_dt.append(O_i)
        print(f"[DualThrust EXTERNAS-28 {inst}] {len(O_i)} ops DESC+REP en {time.time() - t0:.1f}s", flush=True)

    O_all = pd.concat(ops_dt, ignore_index=True)
    O_all["f_P_obj_stop_fin"] = O_all.inst.map(fr_map) / O_all["k_P_obj_stop_fin"]
    res = A5.evaluar(
        O_all, "DESC", variantes_dt, ["P_obj_stop_fin"], None, {}, [20060106, 20111230], None
    )
    por_inst = {}
    for inst in instrumentos:
        for vid in variantes_dt:
            g = O_all[
                (O_all.inst == inst)
                & (O_all.bloque == "DESC")
                & O_all[vid].astype(bool)
                & O_all["r_P_obj_stop_fin"].notna()
            ]
            por_inst[f"{inst}|{vid}"] = dict(
                n=int(len(g)),
                sesiones=int(g.ses.nunique()) if len(g) else 0,
                R_bruto=float(g["r_P_obj_stop_fin"].mean()) if len(g) else None,
                R_neto=float((g["r_P_obj_stop_fin"] - g["f_P_obj_stop_fin"]).mean()) if len(g) else None,
                fric_R_mediana=float(np.median(g["f_P_obj_stop_fin"])) if len(g) else None,
            )
    out = dict(variantes=variantes_dt, resultados_desc=res, por_instrumento=por_inst)
    (DIR_CAMPANA / "AUDITORIA_DUAL_THRUST_EXTERNAS28.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8"
    )
    return out


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if modo in ("estructural", "todo"):
        correr_campana_estructural()
    if modo in ("dualthrust", "todo"):
        auditar_dual_thrust_externas28()
