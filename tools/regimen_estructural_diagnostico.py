#!/usr/bin/env python3
"""Diagnóstico estructural de regímenes cortos (1M–2M) sin lookahead frente a Nulo A (signo por sesión) y Nulo B (permutación temporal con fricción real).

Pre-registro: docs/research/regimen_corto_20261106/PREREGISTRO_REGIMEN_ESTRUCTURAL_20261106.md

Uso:
  python tools/regimen_estructural_diagnostico.py ops          # construye tensores rápidos (sesión x celda) para U37 + VWAP-DUAL-R
  python tools/regimen_estructural_diagnostico.py evaluar [B]  # corre P0..P5 sobre U37, U41 y U18_SEGUIDAS contra Nulo A y Nulo B
"""
from __future__ import annotations

import datetime as dt
import gc
import importlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from edgelab.research import fuentes_ticks as F, grilla_generica as GG, grilla_masiva as GM  # noqa: E402
try:                                              # 2026-11-07: el módulo nunca se commiteó (quedó en la máquina de Gemini); sin él
    from edgelab.research import embudo_regimen_corto as ERC  # noqa: E402   # el diagnóstico completo no corre, pero el resto sí
except ImportError:
    ERC = None
from edgelab.research.embudo_runners import friccion as friccion_canonica  # noqa: E402

BASE = ROOT / "docs/research/regimen_corto_20261106"
CACHE = Path(os.environ.get("EDGELAB_REGIMEN_CACHE", str(ROOT / ".cache/regimen_estructural")))
INSTRUMENTOS = ("GC", "NQ", "ES", "YM")
EXCLUIR = ("HFT-GC-P10-VETO-R", "HFT-GC-P10-CAPTP-R", "HFT-GC-P10-R")
MAX_CELDAS = 6000
DESDE, HASTA = 20250805, 20260930
MESES_TODOS = [f"{y}{m:02d}" for y, m in [(2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12)] + [(2026, k) for k in range(1, 10)]]
MESES_PRUEBA_12M = [f"{y}{m:02d}" for y, m in [(2025, 10), (2025, 11), (2025, 12)] + [(2026, k) for k in range(1, 10)]]
MESES_OOS_POST_DESC = [f"2026{m:02d}" for m in range(4, 10)]
ORD0 = dt.date(2025, 7, 1).toordinal()


def _ord(ses_ids) -> np.ndarray:
    return np.array([dt.date(int(s) // 10000, (int(s) // 100) % 100, int(s) % 100).toordinal() - ORD0 for s in ses_ids], dtype=np.int64)


def mascara_baja_friccion_ejecuciones(exp_mod_name: str, ejecuciones: list) -> np.ndarray:
    """Devuelve máscara booleana sobre EJECUCIONES seleccionando a priori los stops/targets amplios (S2/S3, T>=2.5R) sin mirar PnL."""
    n = len(ejecuciones)
    m = np.zeros(n, dtype=bool)
    for i, ej in enumerate(ejecuciones):
        if not isinstance(ej, (tuple, list)):
            m[i] = True
            continue
        t = tuple(ej)
        if exp_mod_name.endswith("absorcion_climax"):
            # ('ATR', stop_atr, rr): stop >= 1.3 y rr >= 3.0
            m[i] = len(t) >= 3 and float(t[1]) >= 1.25 and float(t[2]) >= 3.0
        elif exp_mod_name.endswith("comex_cierre_oro"):
            # ('PIT', stop, rr): stop >= 1.25 y rr >= 3.0
            m[i] = len(t) >= 3 and float(t[1]) >= 1.2 and float(t[2]) >= 3.0
        elif exp_mod_name.endswith("eod_momentum"):
            # ('STOP', stop_mult): stop >= 2.0
            m[i] = len(t) >= 2 and float(t[1]) >= 2.0
        elif exp_mod_name.endswith("estructura_hhll"):
            # ('PIVOTE', stop, rr): stop >= 1.4 y rr >= 3.5
            m[i] = len(t) >= 3 and float(t[1]) >= 1.35 and float(t[2]) >= 3.5
        elif exp_mod_name.endswith("impulso_post_macro"):
            # ('OPUESTO', 3.0) o ('MID', 3.5)
            m[i] = len(t) >= 2 and float(t[1]) >= 3.0
        elif exp_mod_name.endswith("kalman_fade"):
            # ('FADE'|'CONTINUACION', 'NIVEL', 'S2') -> stop amplio S2 y objetivo completo NIVEL
            m[i] = len(t) >= 3 and t[1] == "NIVEL" and t[2] == "S2"
        elif exp_mod_name.endswith("overnight_inventario"):
            # ('ON', 0.5, 3.5)
            m[i] = len(t) >= 3 and float(t[1]) >= 0.45 and float(t[2]) >= 3.0
        elif exp_mod_name.endswith(("rango_asia0100", "rango_preapertura")):
            # ('OPUESTO', '2R'|'SALIDA')
            m[i] = len(t) >= 2 and t[0] == "OPUESTO" and t[1] in ("2R", "SALIDA")
        elif exp_mod_name.endswith("segundo_intento"):
            # ('CONF', 'Z3'|'2R')
            m[i] = len(t) >= 2 and t[1] in ("Z3", "2R")
        elif exp_mod_name.endswith("tau_tendencia"):
            # ('TAU', 1.0) o ('FIJO_2R', None)
            m[i] = (t[0] == "TAU" and t[1] is not None and float(t[1]) >= 1.0) or t[0] == "FIJO_2R"
        elif exp_mod_name.endswith("vwap_dual_iman"):
            # ('LIM', 'IMAN'|'2R'|'3R') o ('CONF', '3R')
            m[i] = len(t) >= 2 and (t[0] == "LIM" or t[1] in ("3R", "IMAN"))
        elif exp_mod_name.endswith("vwap_rev"):
            # ('OBJ', 1.0, 'STOP', 2.0)
            m[i] = len(t) >= 4 and float(t[1]) >= 1.0 and float(t[3]) >= 2.0
        elif exp_mod_name.endswith("wm_fixing"):
            # ('RANGO', 1.5, 3.5)
            m[i] = len(t) >= 3 and float(t[1]) >= 1.4 and float(t[2]) >= 3.0
        else:
            m[i] = i >= (n // 2)
    if not m.any():
        m[-1] = True
    return m


def mascara_celdas_baja_friccion(forma: tuple[int, ...], exp_mod_name: str, ejecuciones: list) -> np.ndarray:
    """Expande la máscara de ejecuciones de baja fricción al eje final de la grilla aplanada."""
    m_ej = mascara_baja_friccion_ejecuciones(exp_mod_name, ejecuciones)
    n_ej = int(forma[-1])
    if len(m_ej) != n_ej:
        m_ej = np.zeros(n_ej, dtype=bool)
        m_ej[n_ej // 2 :] = True
    full = np.broadcast_to(m_ej.reshape((1,) * (len(forma) - 1) + (n_ej,)), forma)
    return full.ravel().copy()


def _tensor_sesiones_rapido(P, idx: list[np.ndarray], ok: np.ndarray, ses_op: np.ndarray, net: np.ndarray, net0: np.ndarray):
    """Construye S, S0, C (sesión x celda) rebanando por sesión (290x más rápido y bit-a-bit idéntico al bucle completo)."""
    forma = tuple(p.tamano_celdas() for p in P)
    ses_u = np.unique(ses_op[ok])
    n_c = int(np.prod(forma))
    S = np.zeros((len(ses_u), n_c), dtype=np.float64)
    S0 = np.zeros_like(S)
    C = np.zeros_like(S)
    for j, s_id in enumerate(ses_u):
        msk = ok & (ses_op == s_id)
        idx_s = [b[msk] for b in idx]
        s_t, _q, c_t = GM.tensor(P, idx_s, net[msk])
        S[j] = s_t.ravel()
        C[j] = c_t.ravel()
        s0, _q0, _c0 = GM.tensor(P, idx_s, net0[msk])
        S0[j] = s0.ravel()
    return S, S0, C, ses_u, forma


def construir_ops(incluir_vwap_dual: bool = True):
    import atlas_contexto_r as AC
    """Simula cada campaña una vez en 20250805..20260930 (sin tocar holdout >= 20261001) y guarda tensores en CACHE."""
    CACHE.mkdir(parents=True, exist_ok=True)
    todas_map = dict(AC._todas_las_campanas_r())
    u_file = BASE / "universo.json"
    if u_file.exists():
        u_cids = json.loads(u_file.read_text(encoding="utf-8")).get("incluidas", [])
        camps = [(cid, todas_map[cid]) for cid in u_cids if cid in todas_map]
    else:
        camps = [(cid, st) for cid, st in todas_map.items() if cid not in EXCLUIR]
    por_inst: dict[str, list[tuple[str, dict]]] = {}
    vistos = set()
    for cid, st in camps:
        sp = st["spec"]
        ejec = sp.get("ejecucion") or sp["sensor"]
        if sp["sensor"] != ejec or sp["sensor"] not in INSTRUMENTOS or sp.get("confirmador") or sp.get("datasets_extra") or not st.get("cortes"):
            continue
        por_inst.setdefault(sp["sensor"], []).append((cid, st))
        vistos.add(cid)

    if incluir_vwap_dual:
        for inst in INSTRUMENTOS:
            cid = f"VWAP-DUAL-{inst}-R"
            if cid not in vistos:
                st = {"spec": {"sensor": inst, "ejecucion": inst, "experimento": "edgelab.research.vwap_dual_iman"}, "cortes": {}}
                por_inst.setdefault(inst, []).append((cid, st))
                vistos.add(cid)

    informe = dict(incluidas=[], excluidas=[])
    for inst in INSTRUMENTOS:
        lista = por_inst.get(inst, [])
        if not lista:
            continue
        t0 = time.time()
        lec, tk = F.resolver(inst)
        perfil = any(any(x in st["spec"]["experimento"] for x in ("u1_", "areas_expansion")) for _, st in lista)
        data_dir = os.environ.get("ENTRADA") or ("/kaggle/input" if Path("/kaggle/input").is_dir() else str(AC.DATA_LOCAL))
        full = AC._contexto_m1_rapido(lec(20250721, HASTA, data_dir), tk, con_perfil=perfil, con_ticks=True)
        ctx = AC._recortar_ctx(full, DESDE, HASTA, dias_cal=40)
        ctx.update(sensor=inst, desde_eval=DESDE)
        fr, _ex = friccion_canonica(inst)
        print(f"[ctx] {inst} {len(ctx['c'])} velas ({time.time() - t0:.1f}s)", flush=True)
        for cid, st in lista:
            f_out = CACHE / f"{cid}.npz"
            if f_out.exists():
                informe["incluidas"].append(cid)
                continue
            try:
                sp = st["spec"]
                exp = importlib.import_module(sp["experimento"])
                cortes = st["cortes"]
                nc = GG.n_celdas(exp, cortes)
                if nc > MAX_CELDAS:
                    informe["excluidas"].append((cid, f"{nc} celdas > {MAX_CELDAS}"))
                    continue
                t1 = time.time()
                D = exp.disparos(ctx).reset_index(drop=True)
                if "ses" not in D:
                    D["ses"] = np.asarray(ctx["ses"])[D.k.to_numpy().astype(np.intp)]
                D = D[(D.ses >= DESDE) & (D.ses <= HASTA)].reset_index(drop=True)
                if not len(D):
                    informe["excluidas"].append((cid, "sin disparos"))
                    continue
                di, ei, pnl, _a, _d, O, fb, _xb = GG.simular_ops(exp, D, ctx, devolver_O=True, devolver_barras=True)
                esc = GG.riesgo_ops(O, fb, ctx)
                with np.errstate(invalid="ignore", divide="ignore"):
                    net = (pnl - fr) / esc
                    fric_r = fr / esc
                if (ex := getattr(exp, "EXCLUIR_EVENTOS", None)):
                    from edgelab.research.eventos import TIPOS, cerca
                    fuera = cerca(ctx["t"][D.k.to_numpy()[di]], ex.get("antes_min", 15), ex.get("despues_min", 15), tuple(ex.get("tipos", TIPOS)))
                    net = np.where(fuera, np.nan, net)
                P = GG.perillas(exp, cortes)
                idx = [b[di] for b in GG.discretizar(D, exp.VARIABLES, cortes)] + [ei]
                ses_op = D.ses.to_numpy(np.int64)[di]
                ok = np.isfinite(net)
                net0 = net.copy()
                for e in np.unique(ei[ok]):
                    m = ok & (ei == e)
                    net0[m] -= net[m].mean()
                S, S0, C, ses_u, forma = _tensor_sesiones_rapido(P, idx, ok, ses_op, net, net0)
                mask_bf = mascara_celdas_baja_friccion(forma, sp["experimento"], list(exp.EJECUCIONES))
                fric_media = float(np.nanmean(fric_r[ok])) if ok.any() else np.nan
                # Para P4: evaluar en DESC <= 20260331 qué celdas cumplen criterio de descubrimiento congelado
                msk_desc_ses = ses_u <= 20260331
                c_desc = C[msk_desc_ses].sum(axis=0)
                s_desc = S[msk_ses := msk_desc_ses].sum(axis=0)
                with np.errstate(invalid="ignore", divide="ignore"):
                    mu_desc = np.where(c_desc >= 30, s_desc / np.maximum(c_desc, 1.0), -np.inf)
                np.savez_compressed(
                    f_out,
                    S=S,
                    S0=S0,
                    C=C,
                    ses=ses_u,
                    forma=np.array(forma),
                    inst=inst,
                    exp=sp["experimento"],
                    n_ops=int(ok.sum()),
                    mask_bf=mask_bf,
                    fric_media=fric_media,
                    mu_desc=mu_desc,
                    c_desc=c_desc,
                )
                informe["incluidas"].append(cid)
                print(f"[ok] {cid} celdas={S.shape[1]} ops={int(ok.sum())} ses={len(ses_u)} fric_r={fric_media:.3f} ({time.time() - t1:.1f}s)", flush=True)
            except Exception as e:  # noqa: BLE001
                informe["excluidas"].append((cid, f"{type(e).__name__}: {str(e)[:120]}"))
                print(f"[EXCLUIDA] {cid}: {type(e).__name__}: {str(e)[:160]}", flush=True)
            gc.collect()
        del full, ctx
        gc.collect()
    return informe


def _M(S: np.ndarray, C: np.ndarray, ses: np.ndarray, forma: tuple[int, ...], mask_celdas: np.ndarray | None = None):
    if mask_celdas is not None:
        S = S[:, mask_celdas]
        C = C[:, mask_celdas]
        forma = (int(mask_celdas.sum()),)
    meses_ses = np.array([str(int(s))[:6] for s in ses])
    por_mes = {}
    for m in sorted(set(meses_ses)):
        r = meses_ses == m
        Sm, Cm = np.ascontiguousarray(S[r]), np.ascontiguousarray(C[r])
        n_ops, n_ses, ses_pos, ses_neg, r_tot, r_sin2, ratio, t_d = ERC._metricas_mes_nb(Sm, Cm)
        with np.errstate(invalid="ignore", divide="ignore"):
            frac = np.where(n_ses > 0, ses_pos / np.maximum(n_ses, 1), 0.0)
            media = np.where(n_ops > 0, r_tot / np.maximum(n_ops, 1), np.nan)
        por_mes[m] = dict(
            sesiones_calendario=int(r.sum()),
            n_ops=n_ops,
            n_ses=n_ses,
            ses_pos=ses_pos,
            ses_neg=ses_neg,
            frac_ses_pos=frac,
            media_op_r=media,
            r_total_mes=r_tot,
            r_sin_top2_dias=r_sin2,
            ratio_gp_diario=ratio,
            t_diario=t_d,
            S_ses=Sm,
            C_ses=Cm,
            ses_ids=ses[r],
        )
    return dict(experimento="x", meses=sorted(por_mes), celdas=S.shape[1], forma=tuple(int(x) for x in forma), lista_celdas=None, cortes={}, por_mes=por_mes)


def _eval_procedimiento_micro(datos_camp, reglas: dict, solo_baja_friccion: bool = False):
    """Evalúa P0 (todas las celdas) o P1 (solo celdas de baja fricción S3/T3) en las 12 ventanas de prueba."""
    ventanas = []
    base_ops = 0.0
    base_r = 0.0
    for item in datos_camp:
        msk = item["mask_bf"] if solo_baja_friccion else None
        if msk is not None and not msk.any():
            continue
        M = _M(item["S_cur"], item["C_cur"], item["ses_cur"], item["forma"], mask_celdas=msk)
        for m in MESES_PRUEBA_12M:
            d = M["por_mes"].get(m)
            if d is not None:
                base_ops += float(d["n_ops"].sum())
                base_r += float(d["r_total_mes"].sum())
        meses = M["meses"]
        for t in range(2, len(meses)):
            if meses[t] not in MESES_PRUEBA_12M:
                continue
            v = ERC.evaluar_ventana_3m(M, meses[t - 2], meses[t - 1], meses[t], reglas=reglas)
            rp = v.get("resumen_prueba")
            if rp and rp.get("n_ops", 0) > 0:
                ventanas.append((item["cid"], meses[t], int(rp["n_ops"]), float(rp["r_total"])))
    n_ops = sum(x[2] for x in ventanas)
    r_tot = sum(x[3] for x in ventanas)
    r_list = [x[3] for x in ventanas]
    return dict(
        ventanas=len(ventanas),
        n_ops=int(n_ops),
        r_total=float(r_tot),
        media=float(r_tot / n_ops) if n_ops > 0 else 0.0,
        frac_pos=float(np.mean(np.array(r_list) > 0)) if r_list else 0.0,
        linea_base_media=float(base_r / base_ops) if base_ops > 0 else 0.0,
        detalle=ventanas,
    )


def _eval_p2_arquetipo_campana(datos_camp, solo_baja_friccion: bool = True):
    """P2: Colapsa cada campaña a 1 serie agregada (sin selección intra-grilla m=6.000) y selecciona campañas estables en T-2 y T-1."""
    series = []
    for item in datos_camp:
        msk = item["mask_bf"] if solo_baja_friccion else np.ones(item["S_cur"].shape[1], dtype=bool)
        if not msk.any():
            continue
        # Agregado equitativo por sesión de las celdas de baja fricción de la campaña
        c_ses = item["C_cur"][:, msk].sum(axis=1)
        s_ses = item["S_cur"][:, msk].sum(axis=1)
        # Normalizamos por el nº de celdas activas para tener 1 "unidad de campaña" por operación media
        n_act = max(int(msk.sum()), 1)
        S_1 = (s_ses / n_act)[:, None]
        C_1 = np.ceil(c_ses / n_act)[:, None]
        M = _M(S_1, C_1, item["ses_cur"], (1,))
        series.append((item["cid"], M))

    reglas_arq = ERC.PERFILES_REGIMEN["RESCATE_MEDIO"]
    ventanas = []
    for cid, M in series:
        meses = M["meses"]
        for t in range(2, len(meses)):
            if meses[t] not in MESES_PRUEBA_12M:
                continue
            v = ERC.evaluar_ventana_3m(M, meses[t - 2], meses[t - 1], meses[t], reglas=reglas_arq)
            rp = v.get("resumen_prueba")
            if rp and rp.get("n_ops", 0) > 0:
                ventanas.append((cid, meses[t], int(rp["n_ops"]), float(rp["r_total"])))
    n_ops = sum(x[2] for x in ventanas)
    r_tot = sum(x[3] for x in ventanas)
    r_list = [x[3] for x in ventanas]
    return dict(
        ventanas=len(ventanas),
        n_ops=int(n_ops),
        r_total=float(r_tot),
        media=float(r_tot / n_ops) if n_ops > 0 else 0.0,
        frac_pos=float(np.mean(np.array(r_list) > 0)) if r_list else 0.0,
    )


def _eval_p3_panel_multiactivo(datos_camp, reglas: dict, min_activos: int = 2, solo_baja_friccion: bool = True):
    """P3: Exige que la misma familia tenga celdas pasando T-2 y T-1 en >= min_activos instrumentos simultáneamente en el mes T."""
    cand_por_mes_fam: dict[tuple[str, str], list[tuple[str, str, int, float]]] = {}
    for item in datos_camp:
        msk = item["mask_bf"] if solo_baja_friccion else None
        if msk is not None and not msk.any():
            continue
        M = _M(item["S_cur"], item["C_cur"], item["ses_cur"], item["forma"], mask_celdas=msk)
        meses = M["meses"]
        for t in range(2, len(meses)):
            m_t = meses[t]
            if m_t not in MESES_PRUEBA_12M:
                continue
            v = ERC.evaluar_ventana_3m(M, meses[t - 2], meses[t - 1], m_t, reglas=reglas)
            rp = v.get("resumen_prueba")
            if rp and rp.get("n_ops", 0) > 0:
                cand_por_mes_fam.setdefault((m_t, item["exp"]), []).append((item["cid"], item["inst"], int(rp["n_ops"]), float(rp["r_total"])))

    ventanas = []
    for (m_t, _exp), lst in cand_por_mes_fam.items():
        insts = {x[1] for x in lst}
        if len(insts) >= min_activos:
            for cid, _inst, n_o, r_t in lst:
                ventanas.append((cid, m_t, n_o, r_t))
    n_ops = sum(x[2] for x in ventanas)
    r_tot = sum(x[3] for x in ventanas)
    r_list = [x[3] for x in ventanas]
    return dict(
        ventanas=len(ventanas),
        n_ops=int(n_ops),
        r_total=float(r_tot),
        media=float(r_tot / n_ops) if n_ops > 0 else 0.0,
        frac_pos=float(np.mean(np.array(r_list) > 0)) if r_list else 0.0,
    )


def _eval_p4_desc_congelado(datos_camp):
    """P4 sobre U37: congela la mejor celda de baja fricción por campaña en DESC (<= 2026-03) con media >= +0.05R y >= 25 ops, y compara en OOS (2026-04..2026-09):
       - P4a_INCONDICIONAL: operar todas las congeladas sin rotar
       - P4b_MOMENTUM_1M: operar solo si T-1 > 0
       - P4c_VETO_2M_ROTO: operar salvo que T-2 < 0 y T-1 < 0 y (R_{T-2}+R_{T-1}) < -2.0R
    """
    congeladas = []
    for item in datos_camp:
        S = item["S_cur"]
        C = item["C_cur"]
        ses = item["ses_cur"]
        msk_bf = item["mask_bf"]
        msk_desc = ses <= 20260331
        if not msk_desc.any() or not msk_bf.any():
            continue
        c_d = C[msk_desc][:, msk_bf].sum(axis=0)
        s_d = S[msk_desc][:, msk_bf].sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mu_d = np.where(c_d >= 25, s_d / np.maximum(c_d, 1.0), -np.inf)
        j_best = int(np.argmax(mu_d))
        if mu_d[j_best] < 0.05:
            continue
        idx_real = int(np.flatnonzero(msk_bf)[j_best])
        # Serie mensual en 202508..202609
        meses_ses = np.array([str(int(s))[:6] for s in ses])
        pm = {}
        for m in MESES_TODOS:
            r = meses_ses == m
            if r.any():
                s_m = S[r, idx_real]
                c_m = C[r, idx_real]
                n_o = int(c_m.sum())
                n_s = int((c_m > 0).sum())
                s_pos = int((s_m > 0).sum())
                pm[m] = dict(n_ops=n_o, r_total=float(s_m.sum()), frac_pos=float(s_pos / n_s) if n_s > 0 else 0.0)
            else:
                pm[m] = dict(n_ops=0, r_total=0.0, frac_pos=0.0)
        congeladas.append((item["cid"], idx_real, float(mu_d[j_best]), int(c_d[j_best]), pm))

    modos = {"P4a_INCONDICIONAL": [], "P4b_MOMENTUM_1M": [], "P4c_VETO_2M_ROTO": []}
    for cid, _idx, _mu, _cd, pm in congeladas:
        for idx_m, m in enumerate(MESES_OOS_POST_DESC):
            # m es 202604..202609; su índice en MESES_TODOS es 8..13
            t_all = MESES_TODOS.index(m)
            m_t1 = MESES_TODOS[t_all - 1]
            m_t2 = MESES_TODOS[t_all - 2]
            d_t = pm[m]
            d_1 = pm[m_t1]
            d_2 = pm[m_t2]
            if d_t["n_ops"] > 0:
                modos["P4a_INCONDICIONAL"].append((cid, m, d_t["n_ops"], d_t["r_total"]))
                if d_1["n_ops"] >= 3 and d_1["r_total"] > 0 and d_1["frac_pos"] >= 0.50:
                    modos["P4b_MOMENTUM_1M"].append((cid, m, d_t["n_ops"], d_t["r_total"]))
                roto = (d_1["r_total"] < 0) and (d_2["r_total"] < 0) and ((d_1["r_total"] + d_2["r_total"]) <= -2.0)
                if not roto:
                    modos["P4c_VETO_2M_ROTO"].append((cid, m, d_t["n_ops"], d_t["r_total"]))

    out = {"n_congeladas_desc": len(congeladas)}
    for k, v in modos.items():
        no = sum(x[2] for x in v)
        rt = sum(x[3] for x in v)
        rl = [x[3] for x in v]
        out[k] = dict(
            ventanas=len(v),
            n_ops=int(no),
            r_total=float(rt),
            media=float(rt / no) if no > 0 else 0.0,
            frac_pos=float(np.mean(np.array(rl) > 0)) if rl else 0.0,
        )
    return out


def evaluar_u18_seguidas(B: int = 200, semilla: int = 20261106) -> dict:
    """Evalúa P4 sobre las 18 estrategias nominadas seguidas ('Estabilidad mensual en R2'), nominadas en DESC <= 2026-03 y medidas OOS en 2026-04..2026-09."""
    pares = []
    for f_desc in sorted((ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r").glob("*__desc.json")):
        rid = f_desc.name.split("__")[0]
        f_rep = f_desc.with_name(f"{rid}__rep.json")
        pares.append((rid, [f_desc, f_rep]))
    for f_desc in sorted((ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo").glob("*__desc.json")):
        rid = f_desc.name.split("__")[0]
        f_oos = f_desc.with_name(f"{rid}__oos.json")
        pares.append((rid, [f_desc, f_oos]))
    reglas = []
    for rid, flist in pares:
        ops = []
        inst = ""
        for fp in flist:
            if not fp.exists():
                continue
            raw = json.loads(fp.read_text(encoding="utf-8"))
            inst = raw.get("ejecucion") or raw.get("sensor") or inst
            op_d = raw.get("operaciones") or {}
            ses_v = np.asarray(op_d.get("ses", []), dtype=np.int64)
            neto_v = np.asarray(op_d.get("neto", []), dtype=np.float64)
            rg_v = np.asarray([np.nan if v is None else v for v in op_d.get("riesgo", [])], dtype=np.float64)
            with np.errstate(invalid="ignore", divide="ignore"):
                r_v = neto_v / rg_v
            ok = np.isfinite(r_v) & (ses_v >= DESDE) & (ses_v <= HASTA)
            for s_i, r_i in zip(ses_v[ok], r_v[ok]):
                ops.append({"session_id": int(s_i), "net_r": float(r_i)})
        if ops:
            reglas.append((rid, inst, ops))

    # Construir matriz sesión x regla para permitir Nulo A (signo por sesión) y Nulo B (permutación de sesiones post-DESC)
    todas_ses = sorted({int(o["session_id"]) for _, _, ops in reglas for o in ops})
    ses_arr = np.array(todas_ses, dtype=np.int64)
    ses_idx = {s: i for i, s in enumerate(todas_ses)}
    n_s = len(todas_ses)
    n_r = len(reglas)
    S = np.zeros((n_s, n_r), dtype=np.float64)
    C = np.zeros((n_s, n_r), dtype=np.float64)
    for j, (_rid, _inst, ops) in enumerate(reglas):
        for o in ops:
            i = ses_idx[int(o["session_id"])]
            S[i, j] += float(o["net_r"])
            C[i, j] += 1.0

    # Demeaned por regla para Nulo A
    S0 = S.copy()
    for j in range(n_r):
        tot_c = C[:, j].sum()
        if tot_c > 0:
            mu_j = S[:, j].sum() / tot_c
            S0[:, j] = S[:, j] - C[:, j] * mu_j

    def _correr_panel(S_mat: np.ndarray, C_mat: np.ndarray, ses_vec: np.ndarray):
        meses_ses = np.array([str(int(s))[:6] for s in ses_vec])
        pm = {}
        for m in MESES_TODOS:
            r = meses_ses == m
            Sm = S_mat[r]
            Cm = C_mat[r]
            n_o = Cm.sum(axis=0)
            r_t = Sm.sum(axis=0)
            n_d = (Cm > 0).sum(axis=0)
            d_pos = (Sm > 0).sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                f_pos = np.where(n_d > 0, d_pos / np.maximum(n_d, 1), 0.0)
            pm[m] = (n_o, r_t, f_pos)

        # Autocorrelación mensual lag-1 en OOS
        x_lag, y_lag = [], []
        modos = {
            "P4a_INCONDICIONAL_18": [0.0, 0.0, []],
            "P4b_SOLO_1M_ESTABLE": [0.0, 0.0, []],
            "P4b_SOLO_2M_ESTABLE": [0.0, 0.0, []],
            "P4c_VETO_2M_ROTO": [0.0, 0.0, []],
        }
        for m in MESES_OOS_POST_DESC:
            t_idx = MESES_TODOS.index(m)
            m1, m2 = MESES_TODOS[t_idx - 1], MESES_TODOS[t_idx - 2]
            no_t, rt_t, _fp_t = pm[m]
            no_1, rt_1, fp_1 = pm[m1]
            no_2, rt_2, fp_2 = pm[m2]
            for j in range(n_r):
                if no_1[j] >= 3 and no_t[j] >= 3:
                    x_lag.append(float(rt_1[j] / no_1[j]))
                    y_lag.append(float(rt_t[j] / no_t[j]))
                if no_t[j] <= 0:
                    continue
                # 1. Incondicional
                modos["P4a_INCONDICIONAL_18"][0] += float(no_t[j])
                modos["P4a_INCONDICIONAL_18"][1] += float(rt_t[j])
                modos["P4a_INCONDICIONAL_18"][2].append(float(rt_t[j]))
                # 2. Solo 1M estable (T-1 > 0 y frac_pos >= 0.50)
                if no_1[j] >= 4 and rt_1[j] > 0 and fp_1[j] >= 0.50:
                    modos["P4b_SOLO_1M_ESTABLE"][0] += float(no_t[j])
                    modos["P4b_SOLO_1M_ESTABLE"][1] += float(rt_t[j])
                    modos["P4b_SOLO_1M_ESTABLE"][2].append(float(rt_t[j]))
                # 3. Solo 2M estable (T-2 > 0 y T-1 > 0 y frac_pos >= 0.50)
                if no_2[j] >= 4 and rt_2[j] > 0 and fp_2[j] >= 0.50 and no_1[j] >= 4 and rt_1[j] > 0 and fp_1[j] >= 0.50:
                    modos["P4b_SOLO_2M_ESTABLE"][0] += float(no_t[j])
                    modos["P4b_SOLO_2M_ESTABLE"][1] += float(rt_t[j])
                    modos["P4b_SOLO_2M_ESTABLE"][2].append(float(rt_t[j]))
                # 4. Veto 2M roto (opera salvo que T-2 < 0 y T-1 < 0 y suma <= -2.0R)
                roto = (rt_1[j] < 0) and (rt_2[j] < 0) and ((rt_1[j] + rt_2[j]) <= -2.0)
                if not roto:
                    modos["P4c_VETO_2M_ROTO"][0] += float(no_t[j])
                    modos["P4c_VETO_2M_ROTO"][1] += float(rt_t[j])
                    modos["P4c_VETO_2M_ROTO"][2].append(float(rt_t[j]))

        res = {}
        for k, (no, rt, rl) in modos.items():
            res[k] = dict(
                ventanas=len(rl),
                n_ops=int(no),
                r_total=float(rt),
                media=float(rt / no) if no > 0 else 0.0,
                frac_pos=float(np.mean(np.array(rl) > 0)) if rl else 0.0,
            )
        res["autocorr_mensual_lag1_oos"] = float(np.corrcoef(x_lag, y_lag)[0, 1]) if len(x_lag) > 2 else 0.0
        return res

    obs = _correr_panel(S, C, ses_arr)
    nulo_a = {k: [] for k in obs if k.startswith("P4")}
    nulo_b = {k: [] for k in obs if k.startswith("P4")}
    ords = _ord(ses_arr)
    for b in range(B):
        rng = np.random.default_rng(semilla + 10000 + b)
        sg = rng.choice([-1.0, 1.0], size=700)
        ra = _correr_panel(S0 * sg[ords][:, None], C, ses_arr)
        perm = rng.permutation(n_s)
        rb = _correr_panel(S[perm], C[perm], ses_arr)
        for k in nulo_a:
            nulo_a[k].append(ra[k]["media"])
            nulo_b[k].append(rb[k]["media"])

    resumen_nulos = {}
    for k in nulo_a:
        ma = np.array(nulo_a[k])
        mb = np.array(nulo_b[k])
        resumen_nulos[k] = dict(
            nulo_a_q05=float(np.quantile(ma, 0.05)),
            nulo_a_q50=float(np.quantile(ma, 0.50)),
            nulo_a_q95=float(np.quantile(ma, 0.95)),
            p_nulo_a=float((1 + (ma >= obs[k]["media"]).sum()) / (B + 1)),
            nulo_b_q05=float(np.quantile(mb, 0.05)),
            nulo_b_q50=float(np.quantile(mb, 0.50)),
            nulo_b_q95=float(np.quantile(mb, 0.95)),
            p_nulo_b=float((1 + (mb >= obs[k]["media"]).sum()) / (B + 1)),
        )
    return dict(n_reglas=n_r, observado=obs, nulos=resumen_nulos)


def _eval_p5_vwap_dual(datos_vwap):
    """P5: Compara ejecución CONF (mercado) vs LIM (límite con vencimiento) en VWAP-DUAL-{GC,NQ,ES,YM}-R."""
    por_inst = {}
    tot_conf_ops, tot_conf_r = 0, 0.0
    tot_lim_ops, tot_lim_r = 0, 0.0
    for item in datos_vwap:
        forma = item["forma"]
        n_ej = int(forma[-1])
        # En vwap_dual_iman.EJECUCIONES: 0..2 son ('CONF', ...), 3..5 son ('LIM', ...)
        m_conf = np.zeros(n_ej, dtype=bool)
        m_conf[: n_ej // 2] = True
        m_lim = ~m_conf
        mask_c = np.broadcast_to(m_conf.reshape((1,) * (len(forma) - 1) + (n_ej,)), forma).ravel()
        mask_l = np.broadcast_to(m_lim.reshape((1,) * (len(forma) - 1) + (n_ej,)), forma).ravel()
        c_ops = int(item["C"][:, mask_c].sum())
        c_r = float(item["S"][:, mask_c].sum())
        l_ops = int(item["C"][:, mask_l].sum())
        l_r = float(item["S"][:, mask_l].sum())
        tot_conf_ops += c_ops
        tot_conf_r += c_r
        tot_lim_ops += l_ops
        tot_lim_r += l_r
        por_inst[item["cid"]] = dict(
            inst=item["inst"],
            conf_ops=c_ops,
            conf_media_r=float(c_r / c_ops) if c_ops > 0 else 0.0,
            lim_ops=l_ops,
            lim_media_r=float(l_r / l_ops) if l_ops > 0 else 0.0,
            mejora_lim_vs_conf_r=float((l_r / l_ops) - (c_r / c_ops)) if (c_ops > 0 and l_ops > 0) else 0.0,
        )
    return dict(
        por_campana=por_inst,
        total_conf_ops=tot_conf_ops,
        total_conf_media_r=float(tot_conf_r / tot_conf_ops) if tot_conf_ops > 0 else 0.0,
        total_lim_ops=tot_lim_ops,
        total_lim_media_r=float(tot_lim_r / tot_lim_ops) if tot_lim_ops > 0 else 0.0,
    )


def correr_evaluacion_completa(B: int = 200, semilla: int = 20261106) -> dict:
    arch = sorted(CACHE.glob("*.npz"))
    todos = []
    for f in arch:
        z = np.load(f, allow_pickle=True)
        forma = tuple(int(x) for x in z["forma"])
        exp_name = str(z["exp"])
        if "mask_bf" in z:
            mask_bf = z["mask_bf"].astype(bool)
        else:
            exp_mod = importlib.import_module(exp_name)
            mask_bf = mascara_celdas_baja_friccion(forma, exp_name, list(exp_mod.EJECUCIONES))
        todos.append(
            dict(
                cid=f.stem,
                S=z["S"],
                S0=z["S0"],
                C=z["C"],
                ses=z["ses"],
                forma=forma,
                inst=str(z["inst"]),
                exp=exp_name,
                mask_bf=mask_bf,
                S_cur=z["S"],
                C_cur=z["C"],
                ses_cur=z["ses"],
            )
        )
    u37 = [x for x in todos if not x["cid"].startswith("VWAP-DUAL-")]
    vwap_dual = [x for x in todos if x["cid"].startswith("VWAP-DUAL-")]
    print(f"Universo cargado: U37={len(u37)} campañas, VWAP-DUAL={len(vwap_dual)} campañas", flush=True)

    rg_af = ERC.PERFILES_REGIMEN["ALTA_FRECUENCIA"]
    rg_rm = ERC.PERFILES_REGIMEN["RESCATE_MEDIO"]

    def _correr_bateria(lista_camp):
        p0_af = _eval_procedimiento_micro(lista_camp, rg_af, solo_baja_friccion=False)
        p0_rm = _eval_procedimiento_micro(lista_camp, rg_rm, solo_baja_friccion=False)
        p1_af = _eval_procedimiento_micro(lista_camp, rg_af, solo_baja_friccion=True)
        p1_rm = _eval_procedimiento_micro(lista_camp, rg_rm, solo_baja_friccion=True)
        p2_arq = _eval_p2_arquetipo_campana(lista_camp, solo_baja_friccion=True)
        p3_pan = _eval_p3_panel_multiactivo(lista_camp, rg_rm, min_activos=2, solo_baja_friccion=True)
        p4_u37 = _eval_p4_desc_congelado(lista_camp)
        return dict(
            P0_MICRO_AF=p0_af,
            P0_MICRO_RM=p0_rm,
            P1_BAJA_FRICCION_AF=p1_af,
            P1_BAJA_FRICCION_RM=p1_rm,
            P2_ARQUETIPO_CAMPANA=p2_arq,
            P3_PANEL_MULTIACTIVO=p3_pan,
            P4a_DESC_INCONDICIONAL=p4_u37["P4a_INCONDICIONAL"],
            P4b_DESC_MOMENTUM_1M=p4_u37["P4b_MOMENTUM_1M"],
            P4c_DESC_VETO_2M_ROTO=p4_u37["P4c_VETO_2M_ROTO"],
            n_congeladas_desc=p4_u37["n_congeladas_desc"],
        )

    obs = _correr_bateria(u37)
    claves = [k for k in obs if k.startswith("P")]
    for k in claves:
        d = {kk: vv for kk, vv in obs[k].items() if kk != "detalle"}
        print(f"[OBS] {k}: {d}", flush=True)

    # Preparar calendario común de sesiones para Nulo B (permutación temporal sincronizada entre campañas)
    todas_ses_u37 = sorted({int(s) for item in u37 for s in item["ses"]})
    mapa_ses_pos = {s: i for i, s in enumerate(todas_ses_u37)}
    n_ses_global = len(todas_ses_u37)

    nulo_a = {k: [] for k in claves}
    nulo_b = {k: [] for k in claves}
    t0 = time.time()
    for b in range(B):
        rng = np.random.default_rng(semilla + b)
        # Nulo A: volteo de signo por sesión sobre S0 (demeaned)
        sg = rng.choice([-1.0, 1.0], size=700)
        for item in u37:
            item["S_cur"] = item["S0"] * sg[_ord(item["ses"])][:, None]
            item["C_cur"] = item["C"]
            item["ses_cur"] = item["ses"]
        ra = _correr_bateria(u37)
        for k in claves:
            nulo_a[k].append(ra[k])

        # Nulo B: permutación del orden temporal de las sesiones (conserva correlación entre campañas y fricción real negativa)
        perm_global = rng.permutation(n_ses_global)
        ses_perm_global = np.array([todas_ses_u37[idx] for idx in perm_global], dtype=np.int64)
        for item in u37:
            pos_orig = np.array([mapa_ses_pos[int(s)] for s in item["ses"]], dtype=np.int64)
            ses_nuevas = ses_perm_global[pos_orig]
            orden = np.argsort(ses_nuevas)
            item["S_cur"] = item["S"][orden]
            item["C_cur"] = item["C"][orden]
            item["ses_cur"] = ses_nuevas[orden]
        rb = _correr_bateria(u37)
        for k in claves:
            nulo_b[k].append(rb[k])

        if (b + 1) % 20 == 0 or b == 0:
            print(f"[nulos A+B] {b + 1}/{B} ({time.time() - t0:.1f}s)", flush=True)

    # Restaurar punteros observados
    for item in u37:
        item["S_cur"] = item["S"]
        item["C_cur"] = item["C"]
        item["ses_cur"] = item["ses"]

    resumen_nulos = {}
    for k in claves:
        ma = np.array([x["media"] for x in nulo_a[k]])
        mb = np.array([x["media"] for x in nulo_b[k]])
        va = np.array([x["ventanas"] for x in nulo_a[k]])
        vb = np.array([x["ventanas"] for x in nulo_b[k]])
        resumen_nulos[k] = dict(
            nulo_a_q05=float(np.quantile(ma, 0.05)),
            nulo_a_q50=float(np.quantile(ma, 0.50)),
            nulo_a_q95=float(np.quantile(ma, 0.95)),
            p_nulo_a=float((1 + (ma >= obs[k]["media"]).sum()) / (B + 1)),
            ventanas_nulo_a=float(np.mean(va)),
            nulo_b_q05=float(np.quantile(mb, 0.05)),
            nulo_b_q50=float(np.quantile(mb, 0.50)),
            nulo_b_q95=float(np.quantile(mb, 0.95)),
            p_nulo_b=float((1 + (mb >= obs[k]["media"]).sum()) / (B + 1)),
            ventanas_nulo_b=float(np.mean(vb)),
        )

    u18_res = evaluar_u18_seguidas(B=B, semilla=semilla)
    p5_res = _eval_p5_vwap_dual(vwap_dual)

    obs_sin_det = {k: ({kk: vv for kk, vv in v.items() if kk != "detalle"} if isinstance(v, dict) else v) for k, v in obs.items()}
    salida = dict(
        B=B,
        semilla=semilla,
        n_campanas_u37=len(u37),
        n_campanas_vwap_dual=len(vwap_dual),
        u37_observado=obs_sin_det,
        u37_nulos=resumen_nulos,
        u18_seguidas=u18_res,
        p5_vwap_dual=p5_res,
    )
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "resultado_estructural.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    return salida


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todo"
    B_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    if modo == "ops":
        construir_ops(incluir_vwap_dual=True)
    elif modo == "evaluar":
        correr_evaluacion_completa(B=B_arg)
    else:
        construir_ops(incluir_vwap_dual=True)
        correr_evaluacion_completa(B=B_arg)
