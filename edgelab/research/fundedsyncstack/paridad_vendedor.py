"""Evaluacion morfológica de paridad, perfiles y utilidades OOS para `fundedsyncstack`.

Separa estrictamente:
- `il_fabrica`: defaults 1:1 extraidos de `FUNDEDSYNCSTACK5.dll` (sin tocar).
- `vendedor_calibrado`: adaptaciones promovidas solo tras mejorar `score_pre` (2022-2024)
  y validar OOS (`r_nivel_25_26 >= 0.80`) contra los tramos limpios v2 del vendedor.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from edgelab.holdout import (
    HOLDOUT_APERTURA_UTC_ISO,
    HOLDOUT_PRIMERA_SESION,
    es_holdout_trade_date,
)

ROOT = Path(__file__).resolve().parents[3]
PARIDAD_DIR = ROOT / "docs/research/fundedsyncstack_20261115/paridad_vendedor"
DEFAULT_CSV_V2 = PARIDAD_DIR / "curvas_extraidas_v2_limpias.csv"
DEFAULT_CSV_GEMINI = PARIDAD_DIR / "curvas_extraidas_segmentos_claros_gemini.csv"

PERFILES_DISPONIBLES: tuple[str, ...] = ("il_fabrica", "vendedor_calibrado")
TEAL_IDENTIDAD_DEFAULT: dict[str, str] = {"T": "TEAL_UPPER", "S": "TEAL_LOWER"}

# Poblado con adaptaciones validadas OOS (2022-2024 IS + >=0.80 OOS 2025-2026) por el barrido de paridad.
VENDOR_PARITY_OVERRIDES: dict[str, dict[str, Any]] = {
    "O": {
        "parametros": {"use_rth_range_filter": False},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "calibrado_oos",
        "validacion_oos": {"score_pre": 0.8640, "r_nivel_22_24": 0.957, "r_delta_22_24": 0.725, "r_nivel_25_26": 0.965, "r_total": 0.986},
    },
    "S": {
        "parametros": {"st_mult": 3.0, "use_eod_close": False},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "calibrado_oos",
        "validacion_oos": {"score_pre": 0.6150, "r_nivel_22_24": 0.731, "r_delta_22_24": 0.441, "r_nivel_25_26": 0.876, "r_total": 0.824},
    },
    "W": {
        "parametros": {"use_cooldown_filter": False},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "calibrado_oos",
        "validacion_oos": {"score_pre": 0.4352, "r_nivel_22_24": 0.938, "r_delta_22_24": -0.319, "r_nivel_25_26": 0.860, "r_total": 0.953},
    },
    "C": {
        "parametros": {"minimum_gap_points": 10.0},
        "modo_serie": "edge_1cto",
        "serie_datos": "nonadj",
        "estado": "calibrado_oos",
        "validacion_oos": {"score_pre": 0.7310, "r_nivel_22_24": 0.853, "r_delta_22_24": 0.548, "r_nivel_25_26": 0.920, "r_total": 0.694},
    },
    "P": {
        "parametros": {},
        "modo_serie": "usd_dll",
        "serie_datos": "backadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.8617, "r_nivel_22_24": 0.982, "r_delta_22_24": 0.681, "r_nivel_25_26": 0.948, "r_total": 0.990},
    },
    "A20": {
        "parametros": {},
        "modo_serie": "nt8_1cto",
        "serie_datos": "nonadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.8441, "r_nivel_22_24": 0.968, "r_delta_22_24": 0.658, "r_nivel_25_26": 0.913, "r_total": 0.981},
    },
    "T": {
        "parametros": {},
        "modo_serie": "edge_1cto",
        "serie_datos": "backadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.7957, "r_nivel_22_24": 0.981, "r_delta_22_24": 0.518, "r_nivel_25_26": 0.917, "r_total": 0.980},
    },
    "V": {
        "parametros": {},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.7295, "r_nivel_22_24": 0.971, "r_delta_22_24": 0.367, "r_nivel_25_26": 0.955, "r_total": 0.976},
    },
    "Q": {
        "parametros": {},
        "modo_serie": "usd_dll",
        "serie_datos": "backadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.5513, "r_nivel_22_24": 0.878, "r_delta_22_24": 0.062, "r_nivel_25_26": 0.933, "r_total": 0.963},
    },
    "A1": {
        "parametros": {},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.3926, "r_nivel_22_24": 0.686, "r_delta_22_24": -0.047, "r_nivel_25_26": 0.843, "r_total": 0.939},
    },
    "R": {
        "parametros": {},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "paridad_alta_il_fabrica",
        "validacion_oos": {"score_pre": 0.5382, "r_nivel_22_24": 0.603, "r_delta_22_24": 0.442, "r_nivel_25_26": 0.965, "r_total": 0.830},
    },
    "F": {
        "parametros": {},
        "modo_serie": "bruto_1cto",
        "serie_datos": "nonadj",
        "estado": "parcial_sin_tick_delta",
        "validacion_oos": {"score_pre": 0.4804, "r_nivel_22_24": 0.540, "r_delta_22_24": 0.390, "r_nivel_25_26": 0.754, "r_total": 0.597},
    },
    "E": {
        "parametros": {},
        "modo_serie": "bruto_1cto",
        "serie_datos": "backadj",
        "estado": "rango_plano_sin_mejora_oos",
        "validacion_oos": {"score_pre": 0.5897, "r_nivel_22_24": 0.835, "r_delta_22_24": 0.222, "r_nivel_25_26": 0.637, "r_total": 0.801},
    },
    "Z": {
        "parametros": {},
        "modo_serie": "edge_1cto",
        "serie_datos": "backadj",
        "estado": "pendiente_datos_pre2024",
        "validacion_oos": {"score_pre": 0.3243, "r_nivel_22_24": 0.123, "r_delta_22_24": 0.626, "r_nivel_25_26": 0.554, "r_total": 0.750},
    },
}


def filtrar_outliers_salto(
    df: pd.DataFrame,
    *,
    max_jump: float = 0.75,
    window: int = 5,
    max_island_len: int = 8,
) -> pd.DataFrame:
    """Descarta puntos e islas aisladas que saltan abruptamente respecto del trazo adyacente."""
    if len(df) < 5 or "y_vendedor" not in df.columns:
        return df.copy()
    sub = df.sort_values("fecha").reset_index(drop=True)
    ys = sub["y_vendedor"].to_numpy(dtype=float)

    # Paso 1: remover islas cortas delimitadas por saltos > max_jump
    if len(ys) >= 12:
        cortes = [0] + [i + 1 for i in range(len(ys) - 1) if abs(ys[i + 1] - ys[i]) > float(max_jump)] + [len(ys)]
        bloques = [ys[cortes[k] : cortes[k + 1]] for k in range(len(cortes) - 1)]
        if len(bloques) >= 3:
            keep_mask = np.ones(len(ys), dtype=bool)
            for k, blk in enumerate(bloques):
                if len(blk) <= int(max_island_len) and 0 < k < len(bloques) - 1:
                    med_b = float(np.median(blk))
                    med_l = float(np.median(bloques[k - 1][-min(len(bloques[k - 1]), 5) :]))
                    med_r = float(np.median(bloques[k + 1][: min(len(bloques[k + 1]), 5)]))
                    if abs(med_b - med_l) > float(max_jump) and abs(med_b - med_r) > float(max_jump):
                        keep_mask[cortes[k] : cortes[k + 1]] = False
            if not keep_mask.all():
                sub = sub.loc[keep_mask].reset_index(drop=True)
                ys = sub["y_vendedor"].to_numpy(dtype=float)

    # Paso 2: remover picos aislados de 1-2 puntos respecto de mediana movil
    med = pd.Series(ys).rolling(window=window, center=True, min_periods=2).median().to_numpy(dtype=float)
    keep = np.abs(ys - med) <= float(max_jump)
    if not keep.all():
        sub = sub.loc[keep].reset_index(drop=True)
    return sub


def cargar_curva_vendedor(
    csv_path: str | Path | None = None,
    modulo: str = "V",
    *,
    filtrar_saltos: bool = True,
    max_jump: float = 0.75,
    teal_map: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Carga tramos limpios de un modulo desde el CSV del vendedor (`v2` o Gemini)."""
    ruta = DEFAULT_CSV_V2 if csv_path is None else Path(csv_path)
    raw = pd.read_csv(ruta, encoding="utf-8")
    raw["_mod"] = raw["estrategia"].astype(str).apply(lambda s: s.split("·")[-1].strip())
    disponibles = set(raw["_mod"].unique())

    objetivo = str(modulo).strip().upper()
    mapa = dict(TEAL_IDENTIDAD_DEFAULT if teal_map is None else teal_map)
    if objetivo not in disponibles and objetivo in mapa and mapa[objetivo] in disponibles:
        objetivo = mapa[objetivo]

    sub = raw[raw["_mod"] == objetivo]
    if sub.empty:
        raise ValueError(f"Modulo {modulo!r} no encontrado en {csv_path}. Disponibles: {sorted(disponibles)}")

    out = pd.DataFrame({
        "fecha": pd.to_datetime(sub["fecha"]),
        "y_vendedor": sub["y_grid_unidades"].astype(float),
    }).sort_values("fecha").drop_duplicates("fecha").reset_index(drop=True)
    if filtrar_saltos:
        out = filtrar_outliers_salto(out, max_jump=max_jump)
    return out


def _metricas_tramo(
    fecha: np.ndarray,
    y_vend: np.ndarray,
    y_edge: np.ndarray,
) -> tuple[float, float, int]:
    """Correlacion de nivel y deltas a ~30d dentro de segmentos continuos (<=60d)."""
    n = len(fecha)
    if n < 8 or float(np.std(y_vend)) < 1e-9 or float(np.std(y_edge)) < 1e-9:
        return np.nan, np.nan, n
    r_niv = float(np.corrcoef(y_vend, y_edge)[0, 1])

    t_days = (fecha - fecha[0]).astype("timedelta64[D]").astype(float)
    dy_v: list[float] = []
    dy_e: list[float] = []
    for i in range(n):
        j = int(np.searchsorted(t_days, t_days[i] + 28.0))
        if j < n and 20.0 <= (t_days[j] - t_days[i]) <= 60.0:
            dy_v.append(float(y_vend[j] - y_vend[i]))
            dy_e.append(float(y_edge[j] - y_edge[i]))
    if len(dy_v) >= 5 and float(np.std(dy_v)) > 1e-9 and float(np.std(dy_e)) > 1e-9:
        r_del = float(np.corrcoef(dy_v, dy_e)[0, 1])
    else:
        r_del = np.nan
    return r_niv, r_del, n


def serie_diaria_desde_trades(
    df_trades: pd.DataFrame,
    *,
    modo: str = "bruto_1cto",
    desde: str = "2021-09-01",
    hasta: str = "2026-09-30",
    commission_roundturn: float = 4.28,
    slippage_ticks_roundturn: float = 2.0,
    tick_usd: float = 5.0,
) -> pd.DataFrame:
    """Convierte trades de EdgeLab en serie diaria `pnl_diario` bloqueando holdout HOLDOUT-A4."""
    desde_str = pd.Timestamp(desde).strftime("%Y-%m-%d")
    hasta_str = pd.Timestamp(hasta).strftime("%Y-%m-%d")
    if es_holdout_trade_date(desde_str) or es_holdout_trade_date(hasta_str):
        raise ValueError(
            f"Acceso al holdout HOLDOUT-A4 bloqueado en paridad_vendedor: "
            f"desde={desde_str!r}, hasta={hasta_str!r} (>= {HOLDOUT_PRIMERA_SESION})."
        )

    slip_usd = float(slippage_ticks_roundturn) * float(tick_usd)
    comm = float(commission_roundturn)
    idx_cal = pd.date_range(desde_str, hasta_str, freq="D")

    if df_trades is None or len(df_trades) == 0:
        return pd.DataFrame({"fecha": idx_cal, "pnl_diario": 0.0})

    work = df_trades.copy()
    ex_utc = pd.to_datetime(work["exit_time_utc"], utc=True)
    holdout_cut = pd.Timestamp(HOLDOUT_APERTURA_UTC_ISO, tz="UTC")
    work = work[ex_utc < holdout_cut].copy()
    if work.empty:
        return pd.DataFrame({"fecha": idx_cal, "pnl_diario": 0.0})

    ex_ct = pd.to_datetime(work["exit_time_utc"], utc=True).dt.tz_convert("America/Chicago")
    # Sesion CME Futures abre 17:00 CT: +7h asigna cada fill a su trade_date correcto
    work["fecha"] = (ex_ct + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()
    work = work[(work["fecha"] >= pd.Timestamp(desde_str)) & (work["fecha"] <= pd.Timestamp(hasta_str))]

    qty = work["qty"].abs().astype(float) if "qty" in work.columns else pd.Series(1.0, index=work.index)
    if modo == "bruto_1cto":
        pnl = work["pnl_pts"].astype(float) * 20.0
    elif modo == "nt8_1cto":
        pnl = work["pnl_pts"].astype(float) * 20.0 - comm
    elif modo == "edge_1cto":
        pnl = work["pnl_pts"].astype(float) * 20.0 - (comm + slip_usd)
    elif modo == "usd_dll":
        pnl = work["pnl_usd"].astype(float)
    elif modo == "usd_dll_nt8":
        pnl = work["pnl_usd"].astype(float) - comm * qty
    elif modo == "usd_dll_edge":
        pnl = work["pnl_usd"].astype(float) - (comm + slip_usd) * qty
    else:
        raise ValueError(f"Modo de serie desconocido: {modo!r}")

    work["_pnl"] = pnl
    diario = work.groupby("fecha")["_pnl"].sum().reindex(idx_cal, fill_value=0.0)
    return pd.DataFrame({"fecha": diario.index, "pnl_diario": diario.to_numpy(dtype=float)})


def evaluar_paridad_variantes(
    modulo: str,
    variantes: Mapping[str, pd.DataFrame],
    csv_vendedor: str | Path | None = None,
    fecha_split: str = "2025-01-01",
    *,
    teal_map: Mapping[str, str] | None = None,
    filtrar_saltos: bool = True,
) -> pd.DataFrame:
    """Rankea variantes de EdgeLab por correlacion morfologica pre (2022-24) y validacion OOS (2025-26)."""
    csv_src = DEFAULT_CSV_V2 if csv_vendedor is None else csv_vendedor
    vend = cargar_curva_vendedor(csv_src, modulo, filtrar_saltos=filtrar_saltos, teal_map=teal_map)
    t_vend = vend["fecha"].to_numpy(dtype="datetime64[D]")
    y_vend = vend["y_vendedor"].to_numpy(dtype=float)
    t_split = np.datetime64(fecha_split, "D")

    filas: list[dict[str, Any]] = []
    for nombre, df_edge in variantes.items():
        if df_edge is None or len(df_edge) == 0:
            continue
        s = df_edge.sort_values("fecha").copy()
        s["fecha"] = pd.to_datetime(s["fecha"])
        s["equity"] = s["pnl_diario"].astype(float).cumsum()
        t_e = s["fecha"].to_numpy(dtype="datetime64[D]")
        y_e = s["equity"].to_numpy(dtype=float)

        msk = (t_vend >= t_e.min()) & (t_vend <= t_e.max())
        tv, yv = t_vend[msk], y_vend[msk]
        if len(tv) < 12:
            continue
        ye = np.interp(tv.astype(float), t_e.astype(float), y_e)

        r_all, d_all, n_all = _metricas_tramo(tv, yv, ye)
        m_pre = tv < t_split
        m_post = tv >= t_split
        r_pre, d_pre, n_pre = _metricas_tramo(tv[m_pre], yv[m_pre], ye[m_pre])
        r_post, d_post, n_post = _metricas_tramo(tv[m_post], yv[m_post], ye[m_post])

        sv, se = float(np.std(yv)), float(np.std(ye))
        if sv > 1e-9 and se > 1e-9:
            zv = (yv - float(np.mean(yv))) / sv
            ze = (ye - float(np.mean(ye))) / se
            rmse_z = float(np.sqrt(np.mean((zv - ze) ** 2)))
        else:
            rmse_z = np.nan

        if not np.isnan(r_pre) and not np.isnan(d_pre):
            score_pre = float(0.6 * r_pre + 0.4 * d_pre)
        else:
            score_pre = r_pre

        pasa_oos = bool(not np.isnan(r_post) and r_post >= 0.80)
        filas.append({
            "config": str(nombre),
            "score_pre": round(float(score_pre), 4) if not np.isnan(score_pre) else np.nan,
            "r_nivel_22_24": round(r_pre, 3) if not np.isnan(r_pre) else np.nan,
            "r_delta_22_24": round(d_pre, 3) if not np.isnan(d_pre) else np.nan,
            "n_pre": int(n_pre),
            "r_nivel_25_26": round(r_post, 3) if not np.isnan(r_post) else np.nan,
            "r_delta_25_26": round(d_post, 3) if not np.isnan(d_post) else np.nan,
            "n_post": int(n_post),
            "r_total": round(r_all, 3) if not np.isnan(r_all) else np.nan,
            "r_delta_total": round(d_all, 3) if not np.isnan(d_all) else np.nan,
            "rmse_zscore": round(rmse_z, 3) if not np.isnan(rmse_z) else np.nan,
            "pasa_oos": pasa_oos,
            "pts": int(n_all),
        })

    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas).sort_values(
        ["score_pre", "r_nivel_25_26", "r_total"], ascending=False
    ).reset_index(drop=True)


def resolver_identidad_teal(
    serie_s: pd.DataFrame,
    serie_t: pd.DataFrame,
    csv_vendedor: str | Path | None = None,
) -> dict[str, Any]:
    """Desambigua por matriz 2x2 cual track (`TEAL_UPPER` vs `TEAL_LOWER`) corresponde a S y T."""
    csv_src = DEFAULT_CSV_V2 if csv_vendedor is None else csv_vendedor
    pistas: dict[str, pd.DataFrame] = {}
    for mod, track in (("S", "TEAL_LOWER"), ("T", "TEAL_UPPER")):
        rows_m = []
        for cand_mod, cand_serie in (("S", serie_s), ("T", serie_t)):
            df_ev = evaluar_paridad_variantes(
                track, {cand_mod: cand_serie}, csv_vendedor=csv_src
            )
            if not df_ev.empty:
                rows_m.append(df_ev.iloc[0].to_dict())
        pistas[track] = pd.DataFrame(rows_m)

    def _get_score(track: str, cfg: str) -> float:
        df = pistas.get(track, pd.DataFrame())
        sub = df[df["config"] == cfg] if not df.empty else pd.DataFrame()
        if sub.empty:
            return np.nan
        sc = float(sub["score_pre"].iloc[0])
        return sc if not np.isnan(sc) else float(sub["r_total"].iloc[0])

    diag = np.nansum([_get_score("TEAL_LOWER", "S"), _get_score("TEAL_UPPER", "T")])
    anti = np.nansum([_get_score("TEAL_LOWER", "T"), _get_score("TEAL_UPPER", "S")])
    asignacion = {"S": "TEAL_LOWER", "T": "TEAL_UPPER"} if diag >= anti else {"S": "TEAL_UPPER", "T": "TEAL_LOWER"}
    return {"asignacion": asignacion, "matriz": {k: v.to_dict(orient="records") for k, v in pistas.items()}}


def obtener_config_modulo(
    tag: str,
    perfil: str = "il_fabrica",
    override: Any = None,
) -> Any:
    """Devuelve la instancia Config para el modulo (`il_fabrica` o `vendedor_calibrado`)."""
    p = str(perfil).strip().lower()
    if p not in PERFILES_DISPONIBLES:
        raise ValueError(f"Perfil desconocido {perfil!r}. Disponibles: {PERFILES_DISPONIBLES}")
    if override is not None:
        return override

    from edgelab.research.fundedsyncstack import CONFIG_CLASSES

    key = str(tag).strip().upper()
    cls = CONFIG_CLASSES[key]
    base = cls()
    if p == "vendedor_calibrado" and key in VENDOR_PARITY_OVERRIDES:
        params = dict(VENDOR_PARITY_OVERRIDES[key].get("parametros", {}))
        if params:
            return dataclasses.replace(base, **params)
    return base


def obtener_configs_perfil(
    perfil: str = "il_fabrica",
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye el diccionario completo `tag -> Config` para todos los modulos."""
    from edgelab.research.fundedsyncstack import MODULOS

    ov = dict(overrides or {})
    return {tag: obtener_config_modulo(tag, perfil=perfil, override=ov.get(tag)) for tag in MODULOS}
