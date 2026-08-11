# -*- coding: utf-8 -*-
"""F1.1 — nulo condicional por geometria exactamente igualada (distance-matched).

Pregunta pre-registrada (docs/research/BIGTRAP2_DISTANCE_MATCHED_NULL_PROTOCOL_2026-08-11.md):
manteniendo exactamente la geometria relativa de cada zona BigTrap2 y
comparandola con tiempos de control de la misma hora y regimen causal, la
probabilidad de primer toque antes de la eliminacion sigue siendo mayor en el
timestamp donde ocurrio el evento BigTrap2?

Sin direccion, sin P&L, sin stop/target, sin holdout, sin tick:25.
`outcomes_accessed=False`.

## Diez capas separadas (protocolo Seccion 5, orden de implementacion)

1. `construir_universo_zonas` -- zonas elegibles con geometria en TICKS ENTEROS
   (reversion del padding de medio tick, misma convencion que
   F1.1_seguimiento.py: lo_t = round(bottom/tick_size + 0.5), hi_t =
   round(top/tick_size - 0.5)).
2. `calcular_covariables_causales` -- sigma60_ticks y log1p(bar_volume) por
   barra, vectorizado, solo con informacion disponible al cierre de esa barra.
3. `construir_pool_candidatos` -- barras de otra sesion, mismo minuto de
   sesion, sin creacion BigTrap2, con >= H_i barras futuras.
4. `emparejar_controles` -- K=8 vecinos mas cercanos por distancia euclidea
   robustamente estandarizada (MAD del pool candidato; MAD=0 => esa
   covariable aporta 0), desempate (score, session_date, bar_index).
5. `calcular_balance_cobertura` -- cobertura de zonas con >=5 controles, SMD
   por covariable.
6. `reanclar_geometria` + `zone_lifecycle`. `reanclar_geometria` reancla
   rel_lo/rel_hi (calculados UNA vez contra el anchor de la zona fuente,
   close_t en su propia barra de creacion) sobre el anchor PROPIO de cada
   control (close_t en su propia barra J) -- protocolo Seccion 6. Cada
   control se evalua con SU PROPIA geometria reanclada, nunca con los
   limites absolutos de la zona fuente (bug real encontrado por el smoke del
   2026-08-11 y corregido antes de aceptar ningun resultado: la version
   original pasaba lo_tick/hi_tick de la fuente sin reanclar a
   `zone_lifecycle` para los controles). `zone_lifecycle` es una funcion
   pura, PRECEDENCIA IDENTICA al kernel (bigtrap2.py::update_zones):
   expiracion (con `continue`: el toque de esa misma barra NO cuenta) ->
   toque -> invalidacion (FirstTouch/CloseThrough/max_touches). Corrige el
   bug A de F1_nulo_zonas_aleatorias.py (max_age nunca alcanzable) usando
   b1 = created_bar + max_age_bars + 1. Corrige el bug B de
   F1.1_seguimiento.py (tocada_en_horizonte no respeta lifecycle) evaluando
   el lifecycle completo y truncando en el primer evento terminal. No hay
   truncamiento por frontera de sesion: `bigtrap2.py::update_zones` no tiene
   ninguna nocion de sesion (verificado leyendo el kernel completo de nuevo);
   una zona real y sus controles se evaluan sobre el array continuo de
   barras, igual que el kernel.
7. `agregar_por_sesion` -- R_s = mean(r_i) por sesion, peso igual por sesion.
8. `hac_bartlett_ic` -- SE/IC95%/MDE, lag=ceil(sqrt(n_sesiones)).
9. `construir_payload` -- serializacion del artefacto content-addressed.
10. `construir_manifiesto` -- procedencia (HEAD, dirty, hashes, comando).

No se modifica `edgelab/bridge/indicators/bigtrap2.py`. No se usa `tick:25`.
No se abre el holdout. No se leen retornos, P&L, direccion, stops ni targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.F1_nulo_zonas_aleatorias import sesiones_de_barras  # noqa: E402
from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F1.1_nulo_condicional_distancia_v1"
INDICADOR = "BigTrap2"
SEMILLA = 20260811  # solo para desempates deterministas si hiciera falta; el
                     # matching en si es determinista (sin sorteo aleatorio).

MAX_AGE_BARS = int(DEFAULTS["max_age_bars"])
INVALIDATION_MODE = str(DEFAULTS["invalidation_mode"])
MAX_TOUCHES = int(DEFAULTS["max_touches"])

K_CONTROLS = 8
MIN_CONTROLS = 5
MIN_ZONE_COVERAGE = 0.95
MAX_ABS_SMD = 0.10
REQUIRED_SOURCE_SESSIONS = 201
SIGMA60_WINDOW = 60

NORTH_STAR_BODY_SHA256_EXPECTED = (
    "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1")
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_distance_matched_null_v1.json"


# ======================================================================
# Capa 0 -- procedencia (no es una de las 10, pero la necesitan todas)
# ======================================================================

def git_dirty():
    out = subprocess.check_output(
        ["git", "-C", str(REPO_PATH), "status", "--porcelain"], text=True)
    return bool(out.strip())


def north_star_body_sha256():
    p = REPO_PATH / "docs" / "NORTH_STAR.md"
    data = p.read_bytes()
    marker = b"<!-- SHA256-BODY-ABOVE -->"
    idx = data.index(marker)
    return hashlib.sha256(data[:idx]).hexdigest()


def spec_sha256():
    return hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()


def data_root():
    """`data/` esta gitignoreado (CLAUDE.md: dato local) y por eso NINGUNA
    worktree lo tiene -- solo el checkout principal. `REPO_PATH` es correcto
    para todo archivo TRACKEADO (spec, protocolo, git de esta rama), pero no
    para datos. Se prueba primero `REPO_PATH/data` (por si algun dia corre
    desde el checkout principal directamente); si no existe, se resuelve el
    checkout principal via `git worktree list --porcelain` (su primera linea
    es siempre el worktree principal -- comportamiento documentado de git,
    no una convencion de este repo) y se usa su `data/`."""
    local = REPO_PATH / "data"
    if local.exists():
        return local
    out = subprocess.check_output(
        ["git", "-C", str(REPO_PATH), "worktree", "list", "--porcelain"], text=True)
    primera_worktree = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            primera_worktree = Path(line[len("worktree "):].strip())
            break
    if primera_worktree is None:
        raise RuntimeError("no se pudo resolver el checkout principal via `git worktree list`")
    candidato = primera_worktree / "data"
    if not candidato.exists():
        raise RuntimeError("`data/` no existe ni en esta worktree ni en el checkout "
                           "principal resuelto (%s)" % candidato)
    return candidato


# ======================================================================
# Capa 1 -- universo de zonas (geometria en TICKS ENTEROS)
# ======================================================================

def tick_bounds_from_price(top, bottom, tick_size):
    """Revierte el padding de medio tick (bigtrap2.py: zone_lo = lo_tick*ts -
    ts/2, zone_hi = hi_tick*ts + ts/2). Misma convencion que
    F1.1_seguimiento.py:113-114 -- NO es un round() independiente por lado,
    es la inversa exacta de la formula del kernel."""
    lo_tick = round(float(bottom) / tick_size + 0.5)
    hi_tick = round(float(top) / tick_size - 0.5)
    return int(lo_tick), int(hi_tick)


def construir_universo_zonas(kernel_zones, ses_de_barra, rango_sesion, fechas_universo, tick_size, n_bars):
    """Todas las zonas creadas por BigTrap2 en sesiones del universo, sin
    sep_min, sin condicionar por toque ni desenlace (protocolo Seccion 4)."""
    setf = set(fechas_universo)
    universo = []
    creadoras = set()
    for z in kernel_zones:
        if z.get("top") is None or z.get("created_ms") is None:
            continue
        cb = int(z["created_bar"])
        if not (0 <= cb < n_bars):
            continue
        ses = session_date_ct(int(z["created_ms"]))
        if ses not in setf or ses not in rango_sesion:
            continue
        j0, _j1 = rango_sesion[ses]
        lo_tick, hi_tick = tick_bounds_from_price(z["top"], z["bottom"], tick_size)
        is_bull = (z.get("kind") == "trapped_buyers")
        universo.append(dict(
            zone_id=z["id"], created_bar=cb, session_date=ses,
            minute_of_session=cb - j0, is_bull=is_bull,
            lo_tick=lo_tick, hi_tick=hi_tick,
        ))
        creadoras.add(cb)
    return universo, creadoras


# ======================================================================
# Capa 2 -- covariables causales
# ======================================================================

def calcular_covariables_causales(close_t, bar_volume):
    """sigma60_ticks[i] = sqrt(mean(diff(close)^2)) sobre las 60 diferencias
    que TERMINAN en la barra i (o sea usa close_t[i-60..i], informacion
    disponible al cierre de i). NaN si no hay 60 diffs previos (i<60).
    log1p_bar_volume[i] = log1p(bar_volume[i]), siempre disponible al cierre."""
    close_t = np.asarray(close_t, dtype=np.float64)
    bar_volume = np.asarray(bar_volume, dtype=np.float64)
    n = len(close_t)
    sigma60 = np.full(n, np.nan, dtype=np.float64)
    if n > SIGMA60_WINDOW:
        diffs = np.diff(close_t)
        sq = diffs * diffs
        csum = np.concatenate([[0.0], np.cumsum(sq)])
        idx = np.arange(SIGMA60_WINDOW, n)
        window_sum = csum[idx] - csum[idx - SIGMA60_WINDOW]
        sigma60[idx] = np.sqrt(window_sum / SIGMA60_WINDOW)
    log1p_vol = np.log1p(np.maximum(bar_volume, 0.0))
    return dict(sigma60_ticks=sigma60, log1p_bar_volume=log1p_vol,
                log1p_sigma60_ticks=np.log1p(np.maximum(sigma60, 0.0)))


# ======================================================================
# Capa 3 -- pool de candidatos por zona
# ======================================================================

def indexar_por_minuto(ses_de_barra, rango_sesion, n_bars):
    """dict minuto_de_sesion -> lista de (session_date, bar_index), para
    localizar en O(1) las barras candidatas de cada zona por su minuto."""
    por_minuto = {}
    for ses, (j0, j1) in rango_sesion.items():
        for bar_idx in range(j0, j1 + 1):
            m = bar_idx - j0
            por_minuto.setdefault(m, []).append((ses, bar_idx))
    return por_minuto


def horizonte_zona(created_bar, n_bars, max_age_bars=MAX_AGE_BARS):
    """H_i = min(max_age_bars, barras futuras disponibles para la zona)."""
    disponibles = (n_bars - 1) - created_bar
    return max(0, min(max_age_bars, disponibles))


def construir_pool_candidatos(zona, por_minuto, creadoras, n_bars, horizon_i):
    """Barras candidatas: otra sesion, mismo minuto de sesion, sin creacion
    BigTrap2, con >= horizon_i barras futuras disponibles."""
    m = zona["minute_of_session"]
    ses_fuente = zona["session_date"]
    candidatos = []
    for ses, bar_idx in por_minuto.get(m, ()):
        if ses == ses_fuente:
            continue
        if bar_idx in creadoras:
            continue
        disponibles = (n_bars - 1) - bar_idx
        if disponibles < horizon_i:
            continue
        candidatos.append((ses, bar_idx))
    return candidatos


# ======================================================================
# Capa 4 -- matching determinista K=8
# ======================================================================

def _mad(values):
    values = np.asarray(values, dtype=np.float64)
    med = np.median(values)
    return float(np.median(np.abs(values - med)))


def emparejar_controles(zona_cov, candidatos, cov_por_barra, k=K_CONTROLS, min_controls=MIN_CONTROLS):
    """zona_cov: (log1p_sigma60, log1p_vol) de la barra fuente.
    candidatos: lista de (session_date, bar_index).
    cov_por_barra: dict bar_index -> (log1p_sigma60, log1p_vol), o None si
    la covariable no esta disponible (sigma60 con NaN) -- esos candidatos NO
    entran al pool (covariable causal indisponible)."""
    pool = []
    for ses, bar_idx in candidatos:
        cov = cov_por_barra.get(bar_idx)
        if cov is None:
            continue
        s60, lv = cov
        if not (math.isfinite(s60) and math.isfinite(lv)):
            continue
        pool.append((ses, bar_idx, s60, lv))
    if len(pool) < min_controls:
        return dict(estado="ABSTAIN", motivo="pool<min_controls", n_pool=len(pool), elegidos=[])

    s60_pool = np.array([p[2] for p in pool])
    lv_pool = np.array([p[3] for p in pool])
    mad_s60 = _mad(s60_pool)
    mad_lv = _mad(lv_pool)

    zs60, zlv = zona_cov
    scored = []
    for (ses, bar_idx, s60, lv) in pool:
        d_s60 = 0.0 if mad_s60 == 0 else ((s60 - zs60) / mad_s60) ** 2
        d_lv = 0.0 if mad_lv == 0 else ((lv - zlv) / mad_lv) ** 2
        score = math.sqrt(d_s60 + d_lv)
        scored.append((score, ses, bar_idx))
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    elegidos = scored[:k]
    if len(elegidos) < min_controls:
        return dict(estado="ABSTAIN", motivo="elegidos<min_controls", n_pool=len(pool), elegidos=[])
    return dict(estado="OK", n_pool=len(pool), k_efectivo=len(elegidos),
                elegidos=[dict(session_date=s, bar_index=b, score=sc) for sc, s, b in elegidos],
                mad_sigma60=mad_s60, mad_bar_volume=mad_lv)


# ======================================================================
# Capa 5 -- balance y cobertura
# ======================================================================

def smd(real_values, control_values):
    """Standardized mean difference: (media_real - media_control) /
    sqrt((var_real+var_control)/2). Poblacion (ddof=0), como es estandar
    para SMD de balance de matching."""
    r = np.asarray(real_values, dtype=np.float64)
    c = np.asarray(control_values, dtype=np.float64)
    if len(r) == 0 or len(c) == 0:
        return None
    var_pool = (np.var(r, ddof=0) + np.var(c, ddof=0)) / 2.0
    if var_pool <= 0:
        return 0.0 if np.mean(r) == np.mean(c) else None
    return float((np.mean(r) - np.mean(c)) / math.sqrt(var_pool))


def calcular_balance_cobertura(zonas_matched, cov_por_barra):
    """cobertura = fraccion de zonas del universo con >=MIN_CONTROLS
    controles. SMD compara la covariable de las barras FUENTE contra el
    promedio de covariables de sus controles elegidos, agregado sobre todas
    las zonas con match OK."""
    n_total = len(zonas_matched)
    n_ok = sum(1 for z in zonas_matched if z["match"]["estado"] == "OK")
    cobertura = (n_ok / n_total) if n_total else 0.0

    reales_s60, reales_lv = [], []
    controles_s60, controles_lv = [], []
    for z in zonas_matched:
        if z["match"]["estado"] != "OK":
            continue
        zs60, zlv = z["covariables_fuente"]
        reales_s60.append(zs60)
        reales_lv.append(zlv)
        for ctrl in z["match"]["elegidos"]:
            cs60, clv = cov_por_barra[ctrl["bar_index"]]
            controles_s60.append(cs60)
            controles_lv.append(clv)

    return dict(
        n_total_zonas=n_total, n_zonas_ok=n_ok, cobertura=cobertura,
        smd_log1p_sigma60_ticks=smd(reales_s60, controles_s60),
        smd_log1p_bar_volume=smd(reales_lv, controles_lv),
    )


# ======================================================================
# Capa 6 -- lifecycle truth-known (endpoint)
# ======================================================================

def zone_lifecycle(lo_tick, hi_tick, is_bull, created_bar, high_t, low_t, close_t, n,
                    max_age_bars=MAX_AGE_BARS, invalidation_mode=INVALIDATION_MODE,
                    max_touches=MAX_TOUCHES, horizon_cap=None):
    """Replica pura y exacta de bigtrap2.py::update_zones, PRECEDENCIA POR
    BARRA:
      1. expiracion si age > max_age_bars -- `continue`: el toque de ESA
         MISMA barra NO se registra (el kernel chequea touched despues del
         `continue`, nunca lo alcanza).
      2. registrar toque (si high>=lo_tick y low<=hi_tick).
      3. invalidar por FirstTouch (touched), CloseThrough (adverse_close;
         "close_through" si tambien touched esa barra, "close_through_gap"
         si no) o max_touches (touches acumulados >= max_touches).
    Devuelve first_touch_age / removed_age / removed_reason /
    touched_before_removal / censored. `censored=True` si el rango
    disponible (horizonte, max_age_bars o fin de datos) se agota sin que
    ninguna barra dispare expiracion/invalidacion.

    horizon_cap: tope adicional de barras futuras (protocolo #8: H_i =
    min(max_age_bars, barras futuras disponibles); el mismo H_i debe usarse
    para la zona real y para cada control). No cambia la regla de
    max_age_bars -- es un recorte de VENTANA, igual de principio que el
    recorte por fin de datos.
    """
    b0 = created_bar + 1
    # el +1 es la correccion del bug A (F1_nulo_zonas_aleatorias.py::vida_de_zona):
    # sin el +1, "age > max_age_bars" nunca es alcanzable dentro del slice.
    b1 = created_bar + max_age_bars + 1
    b1 = min(b1, n - 1)
    if horizon_cap is not None:
        b1 = min(b1, created_bar + horizon_cap)
    if b0 > b1:
        return dict(first_touch_age=None, removed_age=None, removed_reason=None,
                    touched_before_removal=False, censored=True)

    ages = np.arange(b0, b1 + 1) - created_bar
    h = np.asarray(high_t[b0:b1 + 1])
    l = np.asarray(low_t[b0:b1 + 1])
    c = np.asarray(close_t[b0:b1 + 1])

    touched = (h >= lo_tick) & (l <= hi_tick)
    adverse = (c > hi_tick) if is_bull else (c < lo_tick)
    expired = ages > max_age_bars

    expired_idx = int(np.argmax(expired)) if expired.any() else None

    reason_at = np.full(len(ages), False)
    if invalidation_mode == "FirstTouch":
        reason_at = touched.copy()
    elif invalidation_mode == "CloseThrough":
        reason_at = adverse.copy()
    if max_touches and max_touches > 0:
        running_touches = np.cumsum(touched)
        reason_at = reason_at | (running_touches >= max_touches)
    reason_idx = int(np.argmax(reason_at)) if reason_at.any() else None

    if expired_idx is not None and (reason_idx is None or expired_idx <= reason_idx):
        k = expired_idx
        touched_hasta = touched[:k]  # EXCLUYE la barra k: el `continue` del kernel
        first_touch_idx = int(np.argmax(touched_hasta)) if touched_hasta.any() else None
        return dict(
            first_touch_age=int(ages[first_touch_idx]) if first_touch_idx is not None else None,
            removed_age=int(ages[k]), removed_reason="max_age",
            touched_before_removal=bool(touched_hasta.any()), censored=False)

    if reason_idx is not None:
        k = reason_idx
        touched_hasta = touched[:k + 1]  # INCLUYE la barra k: el toque se registra antes de invalidar
        first_touch_idx = int(np.argmax(touched_hasta)) if touched_hasta.any() else None
        if invalidation_mode == "FirstTouch" and touched[k]:
            razon = "first_touch"
        elif invalidation_mode == "CloseThrough" and adverse[k]:
            razon = "close_through" if touched[k] else "close_through_gap"
        else:
            razon = "max_touches"
        return dict(
            first_touch_age=int(ages[first_touch_idx]) if first_touch_idx is not None else None,
            removed_age=int(ages[k]), removed_reason=razon,
            touched_before_removal=bool(touched_hasta.any()), censored=False)

    # se agoto el rango disponible sin expiracion ni invalidacion -> censura
    first_touch_idx = int(np.argmax(touched)) if touched.any() else None
    return dict(
        first_touch_age=int(ages[first_touch_idx]) if first_touch_idx is not None else None,
        removed_age=None, removed_reason=None,
        touched_before_removal=bool(touched.any()), censored=True)


def reanclar_geometria(lo_tick, hi_tick, source_anchor_tick, target_anchor_tick):
    """Protocolo Seccion 6 -- geometria relativa EXACTA. rel_lo/rel_hi se
    computan UNA vez contra el anchor de la zona fuente (close_t en su propia
    barra de creacion); el control usa el MISMO desplazamiento relativo sobre
    SU PROPIO anchor (close_t en su propia barra J), nunca los limites
    absolutos de la zona fuente:

        rel_lo = source_lo_tick - source_anchor_tick
        rel_hi = source_hi_tick - source_anchor_tick
        control_lo_tick = control_anchor_tick + rel_lo
        control_hi_tick = control_anchor_tick + rel_hi

    Devuelve (rel_lo, rel_hi, target_lo_tick, target_hi_tick)."""
    rel_lo = lo_tick - source_anchor_tick
    rel_hi = hi_tick - source_anchor_tick
    return rel_lo, rel_hi, target_anchor_tick + rel_lo, target_anchor_tick + rel_hi


def endpoint_binario(lifecycle_result):
    """y_i = 1 si la zona toca antes de remocion/censura dentro de H_i
    (protocolo Seccion 9.1). `touched_before_removal` ya es exactamente eso."""
    return 1.0 if lifecycle_result["touched_before_removal"] else 0.0


# ======================================================================
# Capa 7 -- agregacion por sesion (peso igual)
# ======================================================================

def agregar_por_sesion(residuales_por_zona):
    """residuales_por_zona: lista de (session_date, r_i). R_s = mean(r_i)
    por sesion; las sesiones tienen igual peso (una sesion con mas zonas no
    gana mas peso)."""
    por_sesion = {}
    for ses, r in residuales_por_zona:
        por_sesion.setdefault(ses, []).append(r)
    return {ses: float(np.mean(rs)) for ses, rs in por_sesion.items()}


# ======================================================================
# Capa 8 -- inferencia HAC Bartlett
# ======================================================================

def hac_bartlett_ic(r_s_cronologico, alpha=0.05, power=0.80):
    """SE HAC (kernel Bartlett), lag = ceil(sqrt(n)). IC 95% bilateral y MDE
    = (z_alpha/2 + z_power) * SE_HAC. `r_s_cronologico` ya debe venir
    ordenado por fecha de sesion (orden causal, no aleatorio)."""
    x = np.asarray(r_s_cronologico, dtype=np.float64)
    n = len(x)
    if n == 0:
        return dict(n_sessions=0, mean=None, se_hac=None, ci95_lower=None,
                    ci95_upper=None, mde=None, lag=None)
    mean = float(np.mean(x))
    resid = x - mean
    lag = max(1, int(math.ceil(math.sqrt(n))))
    gamma0 = float(np.mean(resid * resid))
    var_lr = gamma0
    for L in range(1, min(lag, n - 1) + 1):
        w = 1.0 - L / (lag + 1.0)  # kernel de Bartlett
        gamma_l = float(np.mean(resid[L:] * resid[:-L]))
        var_lr += 2.0 * w * gamma_l
    var_lr = max(var_lr, 0.0)
    se_hac = math.sqrt(var_lr / n)
    z_alpha = 1.959963984540054  # qnorm(0.975)
    z_power = 0.8416212335729143  # qnorm(0.80)
    ci_lower = mean - z_alpha * se_hac
    ci_upper = mean + z_alpha * se_hac
    mde = (z_alpha + z_power) * se_hac
    return dict(n_sessions=n, mean=mean, se_hac=se_hac,
                ci95_lower=ci_lower, ci95_upper=ci_upper, mde=mde, lag=lag)


def decidir_etiqueta(ic):
    if ic["n_sessions"] == 0:
        return "ABSTAIN_MATCHING"
    if ic["ci95_lower"] > 0:
        return "RESIDUAL_POSITIVE"
    if ic["ci95_upper"] < 0:
        return "RESIDUAL_NEGATIVE"
    return "COMPATIBLE_WITH_ZERO"


# ======================================================================
# Orquestacion (usa las capas 1-8; capas 9-10 en main())
# ======================================================================

def procesar_zonas_de_archivo(kernel_zones, high_t, low_t, close_t, bar_volume,
                              ses_de_barra, rango_sesion, fechas_universo, tick_size,
                              n_bars, horizontes_secundarios=(1, 2, 5, 10, 20, 60, 120)):
    universo, creadoras = construir_universo_zonas(
        kernel_zones, ses_de_barra, rango_sesion, fechas_universo, tick_size, n_bars)
    cov = calcular_covariables_causales(close_t, bar_volume)
    cov_por_barra = {}
    for i in range(n_bars):
        s60, lv = cov["log1p_sigma60_ticks"][i], cov["log1p_bar_volume"][i]
        if math.isfinite(s60) and math.isfinite(lv):
            cov_por_barra[i] = (float(s60), float(lv))
    por_minuto = indexar_por_minuto(ses_de_barra, rango_sesion, n_bars)

    zonas_matched = []
    for zona in universo:
        cb = zona["created_bar"]
        horizon_i = horizonte_zona(cb, n_bars)
        zona_cov = cov_por_barra.get(cb)
        if zona_cov is None:
            zonas_matched.append(dict(**zona, horizon_i=horizon_i,
                                      covariables_fuente=(None, None),
                                      match=dict(estado="ABSTAIN", motivo="covariable_fuente_no_disponible",
                                                n_pool=0, elegidos=[])))
            continue
        candidatos = construir_pool_candidatos(zona, por_minuto, creadoras, n_bars, horizon_i)
        match = emparejar_controles(zona_cov, candidatos, cov_por_barra)
        zonas_matched.append(dict(**zona, horizon_i=horizon_i,
                                  covariables_fuente=zona_cov, match=match))

    resultados = []
    for z in zonas_matched:
        if z["match"]["estado"] != "OK":
            continue
        source_anchor_tick = int(close_t[z["created_bar"]])
        rel_lo_tick = z["lo_tick"] - source_anchor_tick
        rel_hi_tick = z["hi_tick"] - source_anchor_tick
        lc_real = zone_lifecycle(z["lo_tick"], z["hi_tick"], z["is_bull"], z["created_bar"],
                                 high_t, low_t, close_t, n_bars, horizon_cap=z["horizon_i"])
        y_i = endpoint_binario(lc_real)
        p0_controles = []
        controles_ledger = []
        for ctrl in z["match"]["elegidos"]:
            j = ctrl["bar_index"]
            control_anchor_tick = int(close_t[j])
            _rl, _rh, control_lo_tick, control_hi_tick = reanclar_geometria(
                z["lo_tick"], z["hi_tick"], source_anchor_tick, control_anchor_tick)
            lc_ctrl = zone_lifecycle(control_lo_tick, control_hi_tick, z["is_bull"], j,
                                     high_t, low_t, close_t, n_bars, horizon_cap=z["horizon_i"])
            y_ctrl = endpoint_binario(lc_ctrl)
            p0_controles.append(y_ctrl)
            controles_ledger.append(dict(
                session_date=ctrl["session_date"], bar_index=j, score=ctrl["score"],
                control_anchor_tick=control_anchor_tick,
                control_lo_tick=control_lo_tick, control_hi_tick=control_hi_tick,
                y_ctrl=y_ctrl))
        p0_i = float(np.mean(p0_controles))
        r_i = y_i - p0_i
        secundarios = {}
        for k in horizontes_secundarios:
            hc = min(k, z["horizon_i"])
            lc_k = zone_lifecycle(z["lo_tick"], z["hi_tick"], z["is_bull"], z["created_bar"],
                                  high_t, low_t, close_t, n_bars, horizon_cap=hc)
            secundarios[k] = 1.0 if (lc_k["first_touch_age"] is not None and lc_k["first_touch_age"] <= hc) else 0.0
        resultados.append(dict(
            zone_id=z["zone_id"], session_date=z["session_date"],
            created_bar=z["created_bar"], k_efectivo=z["match"]["k_efectivo"],
            source_anchor_tick=source_anchor_tick,
            rel_lo_tick=rel_lo_tick, rel_hi_tick=rel_hi_tick,
            y_i=y_i, p0_i=p0_i, r_i=r_i,
            lifecycle_real=lc_real, controles_ledger=controles_ledger,
            secundarios_touch_by_horizon=secundarios,
        ))

    return dict(universo=universo, zonas_matched=zonas_matched, resultados=resultados,
                cobertura=calcular_balance_cobertura(zonas_matched, cov_por_barra))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke-archivo", default=None,
                    help="si se da, corre SOLO ese archivo (smoke pre-interpretacion)")
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    head_start = git_head()
    dirty_start = git_dirty()
    ns_hash = north_star_body_sha256()
    if ns_hash != NORTH_STAR_BODY_SHA256_EXPECTED:
        print("ABSTAIN_PROVENANCE: hash de NORTH_STAR.md no coincide (%s != %s)"
              % (ns_hash, NORTH_STAR_BODY_SHA256_EXPECTED))
        return 3

    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    if a.smoke_archivo:
        plan = [(x, f) for x, f in plan if x == a.smoke_archivo]
        if not plan:
            print("archivo de smoke no encontrado en el plan: %s" % a.smoke_archivo)
            return 4
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= MAX_FECHA, "FIREWALL: %s > %s" % (peor, MAX_FECHA)
    ns_sesiones = sum(len(fs) for _x, fs in plan)

    print("F1.1 NULO CONDICIONAL POR DISTANCIA -- adjudicacion geometrica exacta")
    print("  universo %d sesiones | K=%d min_controls=%d | max_age_bars=%d"
          % (ns_sesiones, K_CONTROLS, MIN_CONTROLS, MAX_AGE_BARS))

    residuales = []  # (session_date, r_i)
    todos_resultados = []
    cobertura_acumulada = dict(n_total_zonas=0, n_zonas_ok=0)
    smd_s60_vals, smd_lv_vals = [], []
    crudo = {}

    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        ini = (pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
               - pd.Timedelta(days=LEAD_DAYS))
        fin_contrato = (pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                        + pd.Timedelta(days=1))
        fin = min(fin_contrato.tz_convert("UTC"), corte_del_sello())
        tk = ticks_mod.load_canonical_parquet(
            str(data_root() / "nt8" / "6E" / arch),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
        if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
            crudo[arch] = dict(estado="ABSTAIN", motivo="`sequence` no es orden total")
            continue

        b = bars_mod.build_time_bars(tk, 1)
        n_bars = len(b)
        bar_end = np.asarray(b.end_ns)
        high_t, low_t, close_t = (np.asarray(b.high_t), np.asarray(b.low_t), np.asarray(b.close_t))
        bar_volume = np.asarray(b.volume, dtype=np.float64)
        fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
        mod = REGISTRY[INDICADOR]
        r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None else mod.run(tk, b, chart_tz=TZ_CHART)

        ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas)
        res = procesar_zonas_de_archivo(
            r.get("zones") or [], high_t, low_t, close_t, bar_volume,
            ses_de_barra, rango_sesion, fechas, tk.tick_size, n_bars)

        for fila in res["resultados"]:
            residuales.append((fila["session_date"], fila["r_i"]))
        todos_resultados.extend(res["resultados"])
        cobertura_acumulada["n_total_zonas"] += res["cobertura"]["n_total_zonas"]
        cobertura_acumulada["n_zonas_ok"] += res["cobertura"]["n_zonas_ok"]
        if res["cobertura"]["smd_log1p_sigma60_ticks"] is not None:
            smd_s60_vals.append(res["cobertura"]["smd_log1p_sigma60_ticks"])
        if res["cobertura"]["smd_log1p_bar_volume"] is not None:
            smd_lv_vals.append(res["cobertura"]["smd_log1p_bar_volume"])
        crudo[arch] = dict(estado="OK", sesiones=len(fechas),
                           n_zonas=res["cobertura"]["n_total_zonas"],
                           n_zonas_ok=res["cobertura"]["n_zonas_ok"])
        print("   zonas=%d  zonas_ok(>=%d controles)=%d"
              % (res["cobertura"]["n_total_zonas"], MIN_CONTROLS, res["cobertura"]["n_zonas_ok"]))

    cobertura_global = (cobertura_acumulada["n_zonas_ok"] / cobertura_acumulada["n_total_zonas"]
                        if cobertura_acumulada["n_total_zonas"] else 0.0)
    smd_s60 = float(np.mean(smd_s60_vals)) if smd_s60_vals else None
    smd_lv = float(np.mean(smd_lv_vals)) if smd_lv_vals else None

    sesiones_con_zona = len(set(ses for ses, _r in residuales))
    gates = dict(
        cobertura_global=cobertura_global, cobertura_ok=cobertura_global >= MIN_ZONE_COVERAGE,
        smd_log1p_sigma60_ticks=smd_s60, smd_sigma60_ok=(smd_s60 is not None and abs(smd_s60) <= MAX_ABS_SMD),
        smd_log1p_bar_volume=smd_lv, smd_bar_volume_ok=(smd_lv is not None and abs(smd_lv) <= MAX_ABS_SMD),
        sesiones_con_al_menos_una_zona=sesiones_con_zona,
        sesiones_ok=(sesiones_con_zona >= REQUIRED_SOURCE_SESSIONS) if not a.smoke_archivo else None,
    )
    print("\n" + "=" * 70)
    print("GATES DE BALANCE/COBERTURA")
    for k, v in gates.items():
        print("  %s: %r" % (k, v))

    abstain = (not gates["cobertura_ok"] or not gates["smd_sigma60_ok"] or not gates["smd_bar_volume_ok"]
              or (gates["sesiones_ok"] is False))

    por_sesion = agregar_por_sesion(residuales)
    r_s_cronologico = [por_sesion[ses] for ses in sorted(por_sesion)]
    ic = hac_bartlett_ic(r_s_cronologico) if not abstain else dict(
        n_sessions=len(por_sesion), mean=None, se_hac=None, ci95_lower=None,
        ci95_upper=None, mde=None, lag=None)
    etiqueta = "ABSTAIN_MATCHING" if abstain else decidir_etiqueta(ic)

    print("\nESTIMAND: Delta_matched (mean_s(R_s), peso igual por sesion)")
    print("  n_sesiones_con_zona=%d  mean=%s  se_hac=%s  ic95=[%s, %s]  mde=%s"
          % (ic["n_sessions"], ic["mean"], ic["se_hac"], ic["ci95_lower"], ic["ci95_upper"], ic["mde"]))
    print("  ETIQUETA: %s" % etiqueta)

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1_nulo_condicional_distancia",
        status="SMOKE" if a.smoke_archivo else "FORMAL_RUN",
        protocolo="docs/research/BIGTRAP2_DISTANCE_MATCHED_NULL_PROTOCOL_2026-08-11.md",
        spec_path=str(SPEC_PATH.relative_to(REPO_PATH)), spec_sha256=spec_sha256(),
        north_star_body_sha256=ns_hash,
        head_start=head_start, head_end=git_head(), dirty_start=dirty_start, dirty_end=git_dirty(),
        k_controls=K_CONTROLS, min_controls=MIN_CONTROLS,
        min_zone_coverage=MIN_ZONE_COVERAGE, max_abs_smd=MAX_ABS_SMD,
        required_source_sessions=REQUIRED_SOURCE_SESSIONS,
        max_age_bars=MAX_AGE_BARS, invalidation_mode=INVALIDATION_MODE, max_touches=MAX_TOUCHES,
        session_count=ns_sesiones, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()), universe_filter_report=info,
        outcomes_accessed=False, holdout_opened=False,
        n_zonas_universo=cobertura_acumulada["n_total_zonas"],
        n_zonas_matched_ok=cobertura_acumulada["n_zonas_ok"],
        gates=gates, etiqueta=etiqueta,
        estimand_primario=ic,
        por_sesion=por_sesion,
        resultados_por_zona=todos_resultados,
        por_contrato=crudo,
        code_commit=git_head(),
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F1.1_nulo_condicional_distancia__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
