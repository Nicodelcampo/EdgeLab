"""Gestor de Canastas por Régimen v2 y Compuerta Anti-Aplanamiento / Anti-Sobreajuste OOS (2026-10-29).

Resuelve tres problemas críticos antes de enviar cualquier regla o canasta a ejecución en NinjaTrader 8 o challenges:
1. Compuerta Anti-Aplanamiento OOS (`auditar_aplanamiento_oos`):
   Descarta automáticamente cualquier regla o canasta cuya curva en OOS se aplane en la segunda mitad (`H2 <= 0`),
   tenga baja linealidad (`R² < min_r2`), dependa de <= 3 operaciones atípicas (`sin_top3 <= 0`), o pierda más del
   `75%` de su pendiente respecto de `DESC` (`retencion_oos < 0.25`).
2. Poda Ortogonal y Tope de Exposición Simultánea por Activo (`podar_canasta_ortogonal` + `desduplicar_exposicion_simultanea_activo`):
   - Poda una canasta de 20 pistas seleccionando hasta `max_k` pistas ortogonales (correlación diaria `<= max_corr`, p. ej. `0.35`).
   - Limita la exposición simultánea en un mismo instrumento (`MNQ`, `MES`, `MGC`) a `max_slots_simultaneos_por_activo` (por defecto `2`)
     dentro de la ventana de tenencia (`ventana_solapamiento_s = 900s`), evitando pérdidas correlacionadas cuando varias familias
     disparan en el mismo minuto.
3. Gestor Dinámico Causal Sesión a Sesión v2 (`gestor_dinamico_causal_sesion`):
   - Evalúa de forma estrictamente causal (usando sólo sesiones cerradas `< s`) un freno de sombra (`shadow circuit-breaker`)
     contra aplanamiento en vivo y asigna multiplicadores adaptativos por régimen observable (`COMPRESION_RUPTURA`,
     `EXPANSION_REVERSION`, `CONFLUENCIA_TENDENCIA`) según la dispersión realizada en las sesiones previas.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from edgelab.research import paridad_nt8_canastas as PNC


def auditar_aplanamiento_oos(
    ops_df: pd.DataFrame,
    instrumento: str = "NQ",
    cid: str = "REGLA",
    *,
    duracion_s: int = 900,
    min_pf: float = 1.25,
    min_r2: float = 0.50,
    neto_desc_usd: float | None = None,
    min_retencion_desc: float = 0.25,
) -> dict[str, Any]:
    """Evalúa si una serie OOS (bajo paridad NT8 `Flat-Only`) sostiene su pendiente o si está sobreajustada/aplanada."""
    vp = PNC.VALOR_PUNTO_MICRO.get(instrumento, 2.0)
    df_nt8 = PNC.filtrar_solapadas_nt8(ops_df, duracion_s=duracion_s, una_por_sesion=False)
    if len(df_nt8) < 5:
        return {
            "cid": cid,
            "instrumento": instrumento,
            "n_ops": int(len(df_nt8)),
            "aprobada": False,
            "veredicto": "DESCARTADA_POCAS_OPS",
            "motivos_rechazo": ["n_ops < 5"],
        }

    df_nt8 = df_nt8.sort_values("t", kind="stable").reset_index(drop=True)
    usd = df_nt8["neto"].to_numpy(float) * vp
    df_nt8["usd"] = usd
    df_nt8["mes"] = pd.to_datetime(df_nt8["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m")

    meses_unicos = sorted(df_nt8["mes"].unique().tolist())
    if set(meses_unicos).issubset({"2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"}):
        m_h1 = {"2026-04", "2026-05", "2026-06"}
        m_h2 = {"2026-07", "2026-08", "2026-09"}
        m_late = {"2026-08", "2026-09"}
        h1_usd = float(df_nt8[df_nt8["mes"].isin(m_h1)]["usd"].sum())
        h2_usd = float(df_nt8[df_nt8["mes"].isin(m_h2)]["usd"].sum())
        late_usd = float(df_nt8[df_nt8["mes"].isin(m_late)]["usd"].sum())
    else:
        mitad = len(df_nt8) // 2
        tercio_fin = max(1, (2 * len(df_nt8)) // 3)
        h1_usd = float(usd[:mitad].sum())
        h2_usd = float(usd[mitad:].sum())
        late_usd = float(usd[tercio_fin:].sum())

    tot_usd = float(usd.sum())
    eq = np.cumsum(usd)
    dd_usd = float((eq - np.maximum.accumulate(eq)).min())

    idx = np.arange(1, len(eq) + 1, dtype=float)
    if len(eq) > 2 and np.std(eq) > 1e-9:
        corr = float(np.corrcoef(idx, eq)[0, 1])
        r2 = float(corr ** 2) if corr > 0 else -float(corr ** 2)
    else:
        r2 = 0.0

    vals_sorted = np.sort(usd)
    sin_top3_usd = float(vals_sorted[:-3].sum()) if len(vals_sorted) > 3 else 0.0

    gan = float(usd[usd > 0].sum())
    per = float(-usd[usd < 0].sum())
    pf = float(gan / per) if per > 1e-9 else (99.0 if gan > 0 else 0.0)

    m_sums = df_nt8.groupby("mes")["usd"].sum()
    meses_pos = int((m_sums > 0).sum())
    meses_tot = int(len(m_sums))

    retencion_desc = None
    if neto_desc_usd is not None and neto_desc_usd > 0:
        retencion_desc = float(tot_usd / neto_desc_usd)

    motivos: list[str] = []
    if tot_usd <= 0:
        motivos.append("neto_oos<=0")
    if h1_usd <= 0:
        motivos.append("mitad_1_negativa")
    if h2_usd <= 0:
        motivos.append("aplanada_mitad_2<=0")
    if sin_top3_usd <= 0:
        motivos.append("depende_de_3_outliers")
    if pf < float(min_pf):
        motivos.append(f"pf_bajo({pf:.2f}<{min_pf:.2f})")
    if r2 < float(min_r2):
        motivos.append(f"r2_linealidad_baja({r2:.2f}<{min_r2:.2f})")
    if retencion_desc is not None and retencion_desc < float(min_retencion_desc):
        motivos.append(f"caida_vs_desc({retencion_desc:.2f}<{min_retencion_desc:.2f})")

    aprobada = len(motivos) == 0
    return {
        "cid": cid,
        "instrumento": instrumento,
        "valor_punto_micro_usd": vp,
        "n_ops": int(len(df_nt8)),
        "n_sesiones": int(df_nt8["ses"].nunique()),
        "neto_total_usd": round(tot_usd, 2),
        "h1_usd": round(h1_usd, 2),
        "h2_usd": round(h2_usd, 2),
        "tramo_final_usd": round(late_usd, 2),
        "profit_factor": round(pf, 3),
        "drawdown_max_usd": round(dd_usd, 2),
        "r2_linealidad": round(r2, 4),
        "sin_top3_usd": round(sin_top3_usd, 2),
        "meses_positivos": f"{meses_pos}/{meses_tot}",
        "retencion_vs_desc": round(retencion_desc, 3) if retencion_desc is not None else None,
        "aprobada": aprobada,
        "veredicto": "APROBADA_OOS_SOSTENIDA" if aprobada else "DESCARTADA_SOBREAJUSTE_OOS_PLANO",
        "motivos_rechazo": motivos,
    }


def podar_canasta_ortogonal(
    ops_df: pd.DataFrame,
    n_celdas: int,
    instrumento: str = "NQ",
    cid: str = "CANASTA",
    *,
    max_k: int = 4,
    max_corr: float = 0.35,
    duracion_s: int = 900,
    min_r2_canasta: float = 0.64,
) -> dict[str, Any]:
    """Selecciona un subconjunto de hasta `max_k` pistas ortogonales (`corr <= max_corr`) que no se aplanen en H2."""
    vp = PNC.VALOR_PUNTO_MICRO.get(instrumento, 2.0)
    if ops_df is None or len(ops_df) == 0 or n_celdas <= 0:
        return {"cid": cid, "instrumento": instrumento, "aprobada": False, "motivo": "SIN_OPERACIONES"}

    all_ses = sorted(ops_df["ses"].unique().tolist())
    candidatas: list[tuple[float, int]] = []
    series_diarias: dict[int, np.ndarray] = {}
    ops_por_idx: dict[int, pd.DataFrame] = {}

    for idx in range(int(n_celdas)):
        sub = PNC.filtrar_solapadas_nt8(ops_df[ops_df["celda"] == idx], duracion_s=duracion_s)
        if len(sub) < 8:
            continue
        sub = sub.copy()
        usd = sub["neto"].to_numpy(float) * vp
        sub["usd"] = usd
        sub["mes"] = pd.to_datetime(sub["t"].to_numpy(np.int64), unit="s", utc=True).strftime("%Y-%m")

        meses_u = set(sub["mes"].unique().tolist())
        if meses_u.issubset({"2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"}):
            h1 = float(sub[sub["mes"].isin({"2026-04", "2026-05", "2026-06"})]["usd"].sum())
            h2 = float(sub[sub["mes"].isin({"2026-07", "2026-08", "2026-09"})]["usd"].sum())
        else:
            mit = len(usd) // 2
            h1, h2 = float(usd[:mit].sum()), float(usd[mit:].sum())

        tot = float(usd.sum())
        vals = np.sort(usd)
        sin_top2 = float(vals[:-2].sum()) if len(vals) > 2 else 0.0
        gan = float(usd[usd > 0].sum())
        per = float(-usd[usd < 0].sum())
        pf = float(gan / per) if per > 1e-9 else 99.0

        if tot > 0 and pf >= 1.15 and sin_top2 > 0 and h2 > 0 and h1 >= -100.0:
            eq = np.cumsum(usd)
            r2 = float(np.corrcoef(np.arange(len(eq)), eq)[0, 1] ** 2) if len(eq) > 2 and np.std(eq) > 1e-9 else 0.0
            score = tot * (0.5 + 0.5 * max(0.0, r2)) * min(pf, 3.0)
            candidatas.append((score, idx))
            s_dia = sub.groupby("ses")["usd"].sum().reindex(all_ses, fill_value=0.0).to_numpy(float)
            series_diarias[idx] = s_dia
            ops_por_idx[idx] = sub

    candidatas.sort(reverse=True, key=lambda x: x[0])
    seleccionadas: list[int] = []
    for _, idx in candidatas:
        if not seleccionadas:
            seleccionadas.append(idx)
        else:
            s_cand = series_diarias[idx]
            ok_ort = True
            for sel_idx in seleccionadas:
                s_sel = series_diarias[sel_idx]
                if np.std(s_cand) > 1e-9 and np.std(s_sel) > 1e-9:
                    if float(np.corrcoef(s_cand, s_sel)[0, 1]) > float(max_corr):
                        ok_ort = False
                        break
            if ok_ort:
                seleccionadas.append(idx)
        if len(seleccionadas) >= int(max_k):
            break

    if not seleccionadas:
        return {
            "cid": cid,
            "instrumento": instrumento,
            "n_celdas_originales": int(n_celdas),
            "pistas_seleccionadas": [],
            "aprobada": False,
            "veredicto": "DESCARTADA_SIN_PISTAS_SOSTENIDAS_EN_H2",
        }

    df_comb = pd.concat([ops_por_idx[i] for i in seleccionadas], ignore_index=True).sort_values(["t", "celda"], kind="stable").reset_index(drop=True)
    aud_m2 = auditar_aplanamiento_oos(
        df_comb,
        instrumento=instrumento,
        cid=f"{cid}_CANASTA_ORTOGONAL({len(seleccionadas)}p)",
        duracion_s=duracion_s,
        min_pf=1.25,
        min_r2=min_r2_canasta,
    )
    return {
        "cid": cid,
        "instrumento": instrumento,
        "n_celdas_originales": int(n_celdas),
        "pistas_seleccionadas": seleccionadas,
        "n_pistas_seleccionadas": len(seleccionadas),
        "aprobada": bool(aud_m2["aprobada"]),
        "veredicto": aud_m2["veredicto"],
        "metricas_m2_flat_global": aud_m2,
        "operaciones_m2": PNC.filtrar_solapadas_nt8(df_comb, duracion_s=duracion_s),
    }


def desduplicar_exposicion_simultanea_activo(
    df_ops: pd.DataFrame,
    *,
    max_slots_simultaneos_por_activo: int = 2,
    ventana_solapamiento_s: int = 900,
) -> pd.DataFrame:
    """Limita a `max_slots_simultaneos_por_activo` las posiciones abiertas simultáneamente en un mismo activo (`MNQ`, `MES`, `MGC`)."""
    if df_ops is None or len(df_ops) == 0:
        return pd.DataFrame()
    cols_orden = ["t", "unit_id"] if "unit_id" in df_ops.columns else ["t"]
    df_ord = df_ops.sort_values(cols_orden, kind="stable").reset_index(drop=True)
    active_by_inst: dict[str, list[int]] = {}
    keep: list[int] = []
    cur_ses: int | None = None

    for idx, row in df_ord.iterrows():
        s = int(row["ses"])
        t = int(row["t"])
        inst = str(row.get("inst", "MNQ"))
        if s != cur_ses:
            active_by_inst = {}
            cur_ses = s
        exits = [x for x in active_by_inst.get(inst, []) if x > t]
        if len(exits) < int(max_slots_simultaneos_por_activo):
            exits.append(t + int(ventana_solapamiento_s))
            active_by_inst[inst] = exits
            keep.append(idx)
        else:
            active_by_inst[inst] = exits

    return df_ord.iloc[keep].reset_index(drop=True)


def gestor_dinamico_causal_sesion(
    df_operaciones_unidades: pd.DataFrame,
    *,
    ventana_sesiones_freno: int = 12,
    min_ops_warmup: int = 6,
    umbral_pf_freno: float = 0.85,
    ponderar_regimen_vol: bool = False,
) -> dict[str, Any]:
    """Ejecuta el Gestor Dinámico Causal de Canastas por Régimen v2 sesión a sesión (estrictamente ex-ante, sin look-ahead)."""
    if df_operaciones_unidades is None or len(df_operaciones_unidades) == 0:
        return {"n_ops_totales": 0, "n_ops_ejecutadas": 0, "neto_sin_gestor_usd": 0.0, "neto_con_gestor_usd": 0.0}

    df = df_operaciones_unidades.sort_values(["ses", "t"], kind="stable").reset_index(drop=True)
    sesiones = sorted(df["ses"].unique().tolist())
    unidades = sorted(df["unit_id"].unique().tolist())

    historial_por_unidad: dict[str, list[float]] = {u: [] for u in unidades}
    eq_sombra_por_unidad: dict[str, list[float]] = {u: [] for u in unidades}
    hist_reg_pnl: dict[str, list[float]] = {
        "COMPRESION_RUPTURA": [],
        "EXPANSION_REVERSION": [],
        "CONFLUENCIA_TENDENCIA": [],
    }
    hist_mkt_abs: list[float] = []

    pesos_por_sesion: dict[int, dict[str, float]] = {}
    filas_ejecutadas: list[pd.DataFrame] = []

    for ses in sesiones:
        pesos_hoy: dict[str, float] = {}
        for u in unidades:
            hist = historial_por_unidad[u]
            eq_hist = eq_sombra_por_unidad[u]
            if len(hist) < int(min_ops_warmup):
                pesos_hoy[u] = 1.0
            else:
                rec = np.asarray(hist[-int(ventana_sesiones_freno):], float)
                gan = float(rec[rec > 0].sum())
                per = float(-rec[rec < 0].sum())
                pf_rec = gan / per if per > 1e-9 else (99.0 if gan >= 0 else 0.0)
                ma5 = float(np.mean(eq_hist[-min(5, len(eq_hist)):]))
                eq_actual = float(eq_hist[-1])
                if pf_rec < float(umbral_pf_freno) and eq_actual < ma5:
                    pesos_hoy[u] = 0.0
                else:
                    pesos_hoy[u] = 1.0

        mult_reg: dict[str, float] = {
            "COMPRESION_RUPTURA": 1.0,
            "EXPANSION_REVERSION": 1.0,
            "CONFLUENCIA_TENDENCIA": 1.0,
        }
        if ponderar_regimen_vol and len(hist_mkt_abs) >= 10:
            rec_disp = float(np.mean(hist_mkt_abs[-3:]))
            med_disp = float(np.median(hist_mkt_abs[:-3]))
            if rec_disp < 0.85 * med_disp:
                mult_reg["COMPRESION_RUPTURA"] = 1.25
                mult_reg["CONFLUENCIA_TENDENCIA"] = 1.15
            elif rec_disp > 1.15 * med_disp:
                mult_reg["EXPANSION_REVERSION"] = 1.25
            for rt, h_list in hist_reg_pnl.items():
                if len(h_list) >= 5:
                    arr = np.asarray(h_list[-8:], float)
                    g_r = float(arr[arr > 0].sum())
                    p_r = float(-arr[arr < 0].sum())
                    pf_r = g_r / p_r if p_r > 1e-9 else 99.0
                    if pf_r < 0.80:
                        mult_reg[rt] *= 0.60
                    elif pf_r > 2.00:
                        mult_reg[rt] *= 1.15

        pesos_por_sesion[int(ses)] = pesos_hoy

        df_ses = df[df["ses"] == ses].copy()
        df_ses["peso_causal"] = df_ses["unit_id"].map(pesos_hoy).astype(float)
        if ponderar_regimen_vol and "regimen_tipo" in df_ses.columns:
            df_ses["mult_regimen"] = df_ses["regimen_tipo"].map(lambda x: mult_reg.get(str(x), 1.0)).astype(float)
            df_ses["peso_causal"] = df_ses["peso_causal"] * df_ses["mult_regimen"]
        df_ses["usd_gestionado"] = df_ses["usd"].astype(float) * df_ses["peso_causal"]
        filas_ejecutadas.append(df_ses)

        hist_mkt_abs.append(float(np.abs(df_ses["usd"]).sum()))
        for u, grp_u in df_ses.groupby("unit_id"):
            net_dia = float(grp_u["usd"].sum())
            historial_por_unidad[str(u)].append(net_dia)
            prev_eq = eq_sombra_por_unidad[str(u)][-1] if eq_sombra_por_unidad[str(u)] else 0.0
            eq_sombra_por_unidad[str(u)].append(prev_eq + net_dia)
        if "regimen_tipo" in df_ses.columns:
            for rt, grp_r in df_ses.groupby("regimen_tipo"):
                if str(rt) in hist_reg_pnl:
                    hist_reg_pnl[str(rt)].append(float(grp_r["usd"].sum()))

    df_out = pd.concat(filas_ejecutadas, ignore_index=True)
    activas = df_out[df_out["peso_causal"] > 0]
    return {
        "n_ops_totales": int(len(df_out)),
        "n_ops_ejecutadas": int(len(activas)),
        "n_ops_frenadas_en_sombra": int(len(df_out) - len(activas)),
        "neto_sin_gestor_usd": round(float(df_out["usd"].sum()), 2),
        "neto_con_gestor_usd": round(float(df_out["usd_gestionado"].sum()), 2),
        "pesos_por_sesion": pesos_por_sesion,
        "df_resultado": df_out,
    }
