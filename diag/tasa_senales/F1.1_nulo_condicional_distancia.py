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
from collections import Counter
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

SCHEMA_VERSION = "F1.1_nulo_condicional_distancia_v4"  # v4 = F2.3: sd_ref
# recalculado POOLED WITHIN-STRATUM (archivo x minuto_de_sesion, estimador
# ANOVA-MSE) en vez de pooleado globalmente entre estratos -- v3/F2.2 metia
# varianza ENTRE minutos en el denominador mientras el numerador es
# intra-estrato, deflactando todos los SMD; muestra_pre_matching ahora
# reusa construir_pool_candidatos() (la MISMA funcion del matcher) en vez de
# "toda barra no creadora del archivo", que inyectaba estacionalidad
# intradiaria entera; smd_pre_within_estrato como diagnostico decisivo de
# soporte comun; gate de procedencia fail-fast en dirty_start (auditoria
# 2026-08-12, cuarta ronda -- los dos defectos de fondo son ambiguedad de la
# propia instruccion F2.2 del auditor, no bugs de implementacion).
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
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_distance_matched_null_v3.json"


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
    return hashlib.sha256(data[:idx].replace(b"\r\n", b"\n")).hexdigest()


def spec_sha256():
    return hashlib.sha256(SPEC_PATH.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def data_root():
    """`data/` esta gitignoreado (CLAUDE.md: dato local) y por eso NINGUNA
    worktree lo tiene -- solo el checkout principal o DATA_DIR resuelto."""
    from edgelab.config import DATA_DIR
    if Path(DATA_DIR).exists():
        return Path(DATA_DIR)
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
    sep_min, sin condicionar por toque ni desenlace (protocolo Seccion 4).

    `creadoras` (F1, fix 2026-08-11): se puebla en un paso INDEPENDIENTE de
    los filtros de `universo`, con TODA zona del kernel que tenga
    `created_bar` valido (0<=cb<n_bars) -- sin importar `top`/`created_ms`
    faltantes ni si su sesion cae fuera de `fechas_universo`. Antes,
    `creadoras.add(cb)` vivia DESPUES de esos filtros: una zona excluida del
    universo (p.ej. `top is None`, o de una sesion que este archivo no
    cubre) no marcaba su propia barra, asi que esa barra podia colarse como
    candidato de control -- contaminando la definicion de 'barra sin evento
    BigTrap2' que el protocolo (Seccion 7.1) exige."""
    setf = set(fechas_universo)
    creadoras = set()
    for z in kernel_zones:
        cb_raw = z.get("created_bar")
        if cb_raw is None:
            continue
        cb = int(cb_raw)
        if 0 <= cb < n_bars:
            creadoras.add(cb)

    universo = []
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


def smd_con_sd_ref(media_a, media_b, sd_ref):
    """SMD con denominador CONGELADO externamente (sd_ref), NUNCA la varianza
    del conjunto que se esta comparando. F2.2 (tercera auditoria
    independiente, 2026-08-11, sobre el propio fix de F2.1): F2.1 pedia
    smd_matched_sets(fuente, promedio_de_controles) estandarizado con la
    varianza de ESE MISMO conjunto ya matcheado -- promediar K controles
    encoge Var(promedio) respecto a Var(control individual) en un factor
    entre 1/K y 1 (segun correlacion intra-set), asi que el denominador se
    achica y el SMD reportado se infla de una forma que depende de
    K/caliper/pool, no solo del desbalance real. Si mañana cambia el
    matcher, cambian numerador Y denominador, y las variantes dejan de ser
    comparables entre si o contra otra corrida. sd_ref viene de
    calcular_sd_ref_insumos()/agregar_balance_global(): la muestra
    PRE-matching completa (fuentes del universo union pool completo de
    candidatos, pooleada globalmente), fija ANTES de que ningun matcher
    seleccione nada -- la misma vara para smd_pre, las tres variantes de
    smd_post y el SMD por-archivo."""
    if sd_ref is None or not math.isfinite(sd_ref) or sd_ref <= 0:
        return None
    if media_a is None or media_b is None:
        return None
    return float((media_a - media_b) / sd_ref)


def muestra_pre_matching(zonas_matched, por_minuto, creadoras, cov_por_barra, n_bars):
    """F2.3 -- muestra CRUDA pre-matching, ESTRATIFICADA por minuto de sesion.

    El estrato es (archivo, minuto_de_sesion): exactamente la celda dentro de
    la cual el matcher puede elegir. construir_pool_candidatos exige mismo
    minuto de sesion, otra sesion, no creadora y >= H_i barras futuras; nada
    fuera de esa celda es alcanzable por ningun matcher, asi que nada de eso
    puede entrar en la vara con la que se mide el desbalance.

    F2.2 llamaba "pool completo de candidatos" a TODA barra no creadora del
    archivo -- sin el filtro de minuto, sin el de sesion y sin el de
    horizonte. Eso metia la estacionalidad intradiaria entera en sd_ref
    (varianza ENTRE minutos, inexplotable por construccion) y hacia que
    smd_pre midiera composicion horaria en vez de desbalance. Consecuencia
    doble: sd_ref inflado (deflactando TODOS los SMD, siempre en la direccion
    de pasar el gate) y smd_pre - smd_post sobreestimando lo que compro el
    matching.

    Se reusa `construir_pool_candidatos` -- la MISMA funcion que usa el
    matcher -- para que la muestra pre-matching no pueda derivar de lo que el
    matcher realmente ve. Barras deduplicadas dentro del estrato.

    Fuentes: TODA zona del universo con covariables finitas, sin filtrar por
    el resultado del matching (una zona que abstuvo por pool<min_controls
    sigue perteneciendo a la poblacion cuyo balance se esta midiendo).

    (F2.3, cuarta auditoria independiente 2026-08-12, sobre la propia
    instruccion F2.2 del auditor -- ambiguedad de pre-registro, no bug de
    implementacion: "pool completo de candidatos" nunca definio el alcance
    del pooling ni que cuenta como pool.)"""
    estratos = {}
    for z in zonas_matched:
        e = estratos.setdefault(z["minute_of_session"], dict(
            fuentes_s60=[], fuentes_lv=[], pool_s60=[], pool_lv=[], _barras=set()))
        cov_f = cov_por_barra.get(z["created_bar"])
        if cov_f is not None:
            e["fuentes_s60"].append(cov_f[0])
            e["fuentes_lv"].append(cov_f[1])
        for _ses, bar_idx in construir_pool_candidatos(
                z, por_minuto, creadoras, n_bars, z["horizon_i"]):
            if bar_idx in e["_barras"]:
                continue
            cov_c = cov_por_barra.get(bar_idx)
            if cov_c is None:
                continue
            e["_barras"].add(bar_idx)
            e["pool_s60"].append(cov_c[0])
            e["pool_lv"].append(cov_c[1])
    for e in estratos.values():
        del e["_barras"]
    return estratos


_COVARIABLES_SOPORTE_COMUN = ("log1p_sigma60_ticks", "log1p_bar_volume")


def diagnostico_soporte_comun(zonas_matched, por_minuto, creadoras, cov_por_barra, n_bars):
    """F2.4 (auditoria 2026-08-12, sobre la interpretacion del diagnostico
    F2.3): smd_pre_within_estrato ~= smd_post NO distingue "no hay
    solapamiento" de "K es demasiado grande para el pool". Si el matcher
    selecciona una fraccion alta del pool disponible (pool tipico ~9.6,
    K=8 -> ~83% seleccionado), mean(controles) ~= mean(pool) queda forzado
    ARITMETICAMENTE por la seleccion casi-censal, haya o no solapamiento
    real -- las dos hipotesis predicen el mismo numero.

    Este diagnostico mide directamente donde cae CADA fuente relativo al
    RANGO de su propio pool real (via construir_pool_candidatos -- la MISMA
    funcion que usa el matcher, no una aproximacion): por-encima-del-maximo,
    por-debajo-del-minimo, o el percentil (pct = fraccion de valores del
    pool estrictamente menores que la fuente) dentro del pool. Target-free:
    solo geometria de covariables, ningun endpoint.

    Devuelve CRUDO (conteos y listas, sin fracciones/percentiles todavia) --
    main() lo poolea entre archivos con resumir_soporte_comun() antes de
    reducir a ninguna fraccion, mismo principio que sd_ref/smd (F2/F2.1/
    F2.2/F2.3): nunca promediar resumenes ya reducidos por archivo."""
    def _nuevo():
        return dict(n_zonas=0, n_sin_pool=0, tamanos_pool=[],
                   por_covariable={c: dict(above=0, below=0, pcts=[]) for c in _COVARIABLES_SOPORTE_COMUN})

    crudo_todas, crudo_ok = _nuevo(), _nuevo()
    for z in zonas_matched:
        zona_cov = z["covariables_fuente"]
        if zona_cov[0] is None:
            continue
        destinos = [crudo_todas] + ([crudo_ok] if z["match"]["estado"] == "OK" else [])
        for d in destinos:
            d["n_zonas"] += 1

        candidatos = construir_pool_candidatos(z, por_minuto, creadoras, n_bars, z["horizon_i"])
        pool_covs = [cov_por_barra[bar_idx] for _ses, bar_idx in candidatos
                    if cov_por_barra.get(bar_idx) is not None]
        for d in destinos:
            d["tamanos_pool"].append(len(pool_covs))
        if not pool_covs:
            for d in destinos:
                d["n_sin_pool"] += 1
            continue

        for idx, nombre in enumerate(_COVARIABLES_SOPORTE_COMUN):
            x = zona_cov[idx]
            vals = [c[idx] for c in pool_covs]
            above = x > max(vals)
            below = x < min(vals)
            pct = sum(1 for v in vals if v < x) / len(vals)
            for d in destinos:
                dc = d["por_covariable"][nombre]
                if above:
                    dc["above"] += 1
                if below:
                    dc["below"] += 1
                dc["pcts"].append(pct)

    return dict(todas_las_zonas=crudo_todas, solo_ok=crudo_ok)


def resumir_soporte_comun(diagnosticos_por_archivo):
    """F2.4: poolea los crudos de diagnostico_soporte_comun entre TODOS los
    archivos ANTES de calcular ninguna fraccion/percentil."""
    def _nuevo():
        return dict(n_zonas=0, n_sin_pool=0, tamanos_pool=[],
                   por_covariable={c: dict(above=0, below=0, pcts=[]) for c in _COVARIABLES_SOPORTE_COMUN})

    total_todas, total_ok = _nuevo(), _nuevo()
    for diag in diagnosticos_por_archivo:
        for total, crudo in ((total_todas, diag["todas_las_zonas"]), (total_ok, diag["solo_ok"])):
            total["n_zonas"] += crudo["n_zonas"]
            total["n_sin_pool"] += crudo["n_sin_pool"]
            total["tamanos_pool"].extend(crudo["tamanos_pool"])
            for c in _COVARIABLES_SOPORTE_COMUN:
                total["por_covariable"][c]["above"] += crudo["por_covariable"][c]["above"]
                total["por_covariable"][c]["below"] += crudo["por_covariable"][c]["below"]
                total["por_covariable"][c]["pcts"].extend(crudo["por_covariable"][c]["pcts"])

    def _resumen(total):
        out = dict(n_zonas=total["n_zonas"], n_sin_pool=total["n_sin_pool"])
        tam = total["tamanos_pool"]
        out["tamano_pool_p50"] = float(np.percentile(tam, 50)) if tam else None
        out["tamano_pool_p90"] = float(np.percentile(tam, 90)) if tam else None
        out["por_covariable"] = {}
        for c in _COVARIABLES_SOPORTE_COMUN:
            dc = total["por_covariable"][c]
            pcts = dc["pcts"]
            n = len(pcts)
            deciles = [0] * 10
            for p in pcts:
                deciles[min(9, int(p * 10))] += 1
            out["por_covariable"][c] = dict(
                frac_above_max=(dc["above"] / n) if n else None,
                frac_below_min=(dc["below"] / n) if n else None,
                frac_fuera_de_rango=((dc["above"] + dc["below"]) / n) if n else None,
                frac_pct_mayor_o_igual_0_90=(sum(1 for p in pcts if p >= 0.90) / n) if n else None,
                pct_p50=float(np.percentile(pcts, 50)) if pcts else None,
                pct_p90=float(np.percentile(pcts, 90)) if pcts else None,
                histograma_pct_deciles=deciles,
            )
        return out

    return dict(todas_las_zonas=_resumen(total_todas), solo_ok=_resumen(total_ok))


def calcular_balance_cobertura(zonas_matched, cov_por_barra):
    """cobertura = fraccion de zonas del universo con >=MIN_CONTROLS
    controles. `estado`: "SIN_ZONAS" si este archivo no tiene NINGUNA zona
    BigTrap2 (n_total_zonas==0 -- un contrato sin eventos no es lo mismo que
    un archivo con datos rotos: ver agregar_balance_global) o "OK" en
    cualquier otro caso, incluido cobertura baja.

    Ya NO calcula ningun SMD (F2.2, tercera auditoria independiente
    2026-08-11): expone las listas crudas (reales/controles) CON sus pesos
    (1/k_efectivo por control), los pares (fuente, promedio_de_sus_controles)
    por zona con su session_date, SIN agregar entre zonas -- porque el SMD ya
    no se calcula por-archivo con la varianza de este archivo, se calcula
    GLOBALMENTE en agregar_balance_global() con un sd_ref congelado pooleado
    entre TODOS los archivos ANTES de que ningun matcher seleccione nada."""
    n_total = len(zonas_matched)
    n_ok = sum(1 for z in zonas_matched if z["match"]["estado"] == "OK")
    cobertura = (n_ok / n_total) if n_total else 0.0
    estado = "SIN_ZONAS" if n_total == 0 else "OK"

    reales_s60, reales_lv = [], []
    controles_s60, controles_lv, pesos_controles = [], [], []
    fuente_ms_s60, control_mean_s60 = [], []
    fuente_ms_lv, control_mean_lv = [], []
    fuente_ms_session = []  # sesion de cada par matched-set -- insumo del peso_sesion
    for z in zonas_matched:
        if z["match"]["estado"] != "OK":
            continue
        zs60, zlv = z["covariables_fuente"]
        reales_s60.append(zs60)
        reales_lv.append(zlv)
        elegidos = z["match"]["elegidos"]
        k_i = len(elegidos)
        peso_i = (1.0 / k_i) if k_i else 0.0
        ctrl_s60, ctrl_lv = [], []
        for ctrl in elegidos:
            cs60, clv = cov_por_barra[ctrl["bar_index"]]
            controles_s60.append(cs60)
            controles_lv.append(clv)
            pesos_controles.append(peso_i)
            ctrl_s60.append(cs60)
            ctrl_lv.append(clv)
        if ctrl_s60:  # "OK" implica elegidos no vacio en produccion (igual
            # que asume p0_i mas abajo); guardia solo para no ensuciar con
            # NaN los fixtures sinteticos de test que construyen OK a mano
            # con elegidos=[].
            fuente_ms_s60.append(zs60)
            control_mean_s60.append(float(np.mean(ctrl_s60)))
            fuente_ms_lv.append(zlv)
            control_mean_lv.append(float(np.mean(ctrl_lv)))
            fuente_ms_session.append(z["session_date"])

    return dict(
        estado=estado, n_total_zonas=n_total, n_zonas_ok=n_ok, cobertura=cobertura,
        crudo_reales_s60=reales_s60, crudo_controles_s60=controles_s60,
        crudo_reales_lv=reales_lv, crudo_controles_lv=controles_lv,
        pesos_controles=pesos_controles,
        fuente_matched_sets_s60=fuente_ms_s60, control_mean_s60=control_mean_s60,
        fuente_matched_sets_lv=fuente_ms_lv, control_mean_lv=control_mean_lv,
        fuente_matched_sets_session=fuente_ms_session,
    )


_ARCHIVO_AUSENTE = object()  # centinela: distinto de None (None = ABSTAIN explicito)


def agregar_balance_global(cobertura_por_archivo, muestra_por_archivo, archivos_planificados):
    """F2 -> F2.1 -> F2.2 (tres auditorias independientes, todas 2026-08-11,
    cada una sobre el fix anterior): agrega balance ENTRE archivos sin
    promediar SMDs ya reducidos, y con un denominador CONGELADO que no
    depende del matcher.

    Paso 1 -- sd_ref: desvio poblacional de la muestra PRE-matching completa
    (fuentes del universo union pool completo de candidatos de
    muestra_por_archivo), pooleada globalmente entre TODOS los archivos, con
    su propio hash. Este es el denominador de TODO lo que sigue -- nunca la
    varianza de un conjunto ya matcheado (F2.1 estandarizaba
    smd_matched_sets con la varianza del propio conjunto matcheado, que se
    encoge al promediar K controles y hace que el numero dependa de
    K/caliper/pool en vez de solo del desbalance real).

    Paso 2 -- smd_pre: fuentes del universo vs pool completo de candidatos,
    con sd_ref. Es el desbalance ANTES de matchear.

    Paso 3 -- smd_post, tres variantes, TODAS con el mismo sd_ref:
    - global_pooled: fuentes (peso 1) vs controles individuales pooleados
      (peso 1/k_efectivo cada uno) de TODOS los archivos.
    - matched_sets: fuentes vs promedio_de_sus_propios_controles por zona.
    - peso_sesion: igual que matched_sets, pero cada zona pesa
      1/n_zonas_de_su_sesion -- la MISMA medida en la que pesa el estimand
      primario (agregar_por_sesion), para que el gate de balance no pueda
      pasar con pesos-zona mientras el estimand esta desbalanceado con
      pesos-sesion.

    Paso 4 -- SMD por-archivo (diagnostico + max_abs_por_archivo), con el
    MISMO sd_ref global -- nunca la varianza propia del archivo.

    Fail-closed: cualquier archivo planificado ausente del dict, con
    cobertura None (ABSTAIN), con estado SIN_ZONAS, o con un SMD por-archivo
    no finito, hace fallar el gate de esa covariable con motivo explicito en
    *_archivos_invalidos. max_abs_por_archivo devuelve
    {valor, completo, archivos_excluidos} -- nunca un maximo silenciosamente
    filtrado presentado como escalar suelto."""
    # ---- sd_ref: POOLED WITHIN-STRATUM (F2.3), no global. ----
    # El matching es intra-archivo e intra-minuto. Con un denominador que
    # incluye la varianza ENTRE estratos, el numerador es intra-estrato y el
    # denominador no: todos los SMD quedan deflactados, siempre en la
    # direccion de pasar el gate. El umbral convencional 0.10 (Stuart 2010,
    # Austin 2009) esta definido sobre la SD DENTRO del estrato de
    # comparacion; con otra vara el numero deja de significar lo que se cree
    # que significa. Estimador: pooled within-group (ANOVA MSE),
    # sqrt(SS_within / (N - G)), que generaliza el pooled SD de dos grupos
    # que usa smd().
    def _acumular_within(clave):
        ss, gl, n_obs, n_estratos, n_singleton = 0.0, 0, 0, 0, 0
        for arch in archivos_planificados:
            for _m, e in (muestra_por_archivo.get(arch) or {}).items():
                xs = [x for x in (list(e["fuentes_" + clave]) + list(e["pool_" + clave]))
                      if math.isfinite(x)]
                n_obs += len(xs)
                n_estratos += 1
                if len(xs) < 2:
                    n_singleton += 1
                    continue
                arr = np.asarray(xs, dtype=np.float64)
                ss += float(np.sum((arr - arr.mean()) ** 2))
                gl += len(arr) - 1
        sd = math.sqrt(ss / gl) if gl > 0 else None
        return (sd if (sd is not None and sd > 0) else None), dict(
            n_estratos=n_estratos, n_estratos_singleton=n_singleton,
            n_obs=n_obs, grados_libertad=gl)

    sd_ref_s60, diag_sd_s60 = _acumular_within("s60")
    sd_ref_lv, diag_sd_lv = _acumular_within("lv")

    # Diagnostico, NO denominador: la SD global (definicion F2.2). Se reporta
    # solo para dejar MEDIDO cuanto deflactaba la version anterior.
    def _sd_global(clave):
        todo = []
        for arch in archivos_planificados:
            for _m, e in (muestra_por_archivo.get(arch) or {}).items():
                todo.extend(e["fuentes_" + clave])
                todo.extend(e["pool_" + clave])
        todo = [x for x in todo if math.isfinite(x)]
        if len(todo) < 2:
            return None
        sd = float(np.std(np.asarray(todo, dtype=np.float64), ddof=0))
        return sd if sd > 0 else None

    sd_global_s60, sd_global_lv = _sd_global("s60"), _sd_global("lv")

    def _ratio(g, w):
        return float(g / w) if (g is not None and w is not None and w > 0) else None

    def _sd_within_de_archivo(arch, clave):
        ss, gl = 0.0, 0
        for _m, e in (muestra_por_archivo.get(arch) or {}).items():
            xs = [x for x in (list(e["fuentes_" + clave]) + list(e["pool_" + clave]))
                  if math.isfinite(x)]
            if len(xs) < 2:
                continue
            arr = np.asarray(xs, dtype=np.float64)
            ss += float(np.sum((arr - arr.mean()) ** 2))
            gl += len(arr) - 1
        return math.sqrt(ss / gl) if gl > 0 else None

    sd_ref_por_archivo = {
        a: dict(log1p_sigma60_ticks=_sd_within_de_archivo(a, "s60"),
                log1p_bar_volume=_sd_within_de_archivo(a, "lv"))
        for a in archivos_planificados}

    sd_ref_sha256 = hashlib.sha256(json.dumps(dict(
        definicion="pooled_within_stratum(archivo x minuto_de_sesion)",
        sd_ref_log1p_sigma60_ticks=sd_ref_s60, sd_ref_log1p_bar_volume=sd_ref_lv,
        diag_log1p_sigma60_ticks=diag_sd_s60, diag_log1p_bar_volume=diag_sd_lv,
    ), sort_keys=True).encode()).hexdigest()

    def _plano(clave, campo):
        xs = []
        for arch in archivos_planificados:
            for _m, e in (muestra_por_archivo.get(arch) or {}).items():
                xs.extend(e[campo + "_" + clave])
        return [x for x in xs if math.isfinite(x)]

    muestra_fuentes_s60_g, muestra_pool_s60_g = _plano("s60", "fuentes"), _plano("s60", "pool")
    muestra_fuentes_lv_g, muestra_pool_lv_g = _plano("lv", "fuentes"), _plano("lv", "pool")

    def _media(xs):
        return float(np.mean(xs)) if xs else None

    def _media_ponderada(xs, ws):
        if not xs or len(xs) != len(ws) or sum(ws) <= 0:
            return None
        return float(np.average(xs, weights=ws))

    smd_pre_s60 = smd_con_sd_ref(_media(muestra_fuentes_s60_g), _media(muestra_pool_s60_g), sd_ref_s60)
    smd_pre_lv = smd_con_sd_ref(_media(muestra_fuentes_lv_g), _media(muestra_pool_lv_g), sd_ref_lv)

    # smd_pre_within_estrato: el desbalance pre-matching que NO es composicion
    # de estratos -- promedio de (media_fuentes_estrato - media_pool_estrato)
    # ponderado por el numero de fuentes del estrato. Es la parte que el
    # matching NO puede comprar reordenando minutos. Diagnostico decisivo:
    # si smd_pre_within ~= smd_post, el problema es falta de solapamiento
    # DENTRO del estrato y ningun matcher lo va a arreglar -- ahi hay que ir
    # a A) recorte a soporte comun, B) pesos de solapamiento o C) controles
    # de casi-evento, no a otra vuelta de tuning.
    def _pre_within(clave):
        num, den = 0.0, 0.0
        for arch in archivos_planificados:
            for _m, e in (muestra_por_archivo.get(arch) or {}).items():
                f = [x for x in e["fuentes_" + clave] if math.isfinite(x)]
                p = [x for x in e["pool_" + clave] if math.isfinite(x)]
                if not f or not p:
                    continue
                num += len(f) * (float(np.mean(f)) - float(np.mean(p)))
                den += len(f)
        return (num / den) if den > 0 else None

    smd_pre_within_s60 = smd_con_sd_ref(_pre_within("s60"), 0.0, sd_ref_s60)
    smd_pre_within_lv = smd_con_sd_ref(_pre_within("lv"), 0.0, sd_ref_lv)

    # ---- insumos post-matching, globales y por-archivo. ----
    reales_s60_g, controles_s60_g, pesos_s60_g = [], [], []
    reales_lv_g, controles_lv_g, pesos_lv_g = [], [], []
    fuente_ms_s60_g, control_mean_ms_s60_g = [], []
    fuente_ms_lv_g, control_mean_ms_lv_g = [], []
    fuente_ms_session_g = []
    smd_s60_por_archivo, smd_lv_por_archivo = {}, {}
    invalidos_s60, invalidos_lv = [], []

    for arch in archivos_planificados:
        cob = cobertura_por_archivo.get(arch, _ARCHIVO_AUSENTE)
        if cob is _ARCHIVO_AUSENTE:
            smd_s60_por_archivo[arch] = None
            smd_lv_por_archivo[arch] = None
            invalidos_s60.append((arch, "archivo planificado ausente de cobertura_por_archivo"))
            invalidos_lv.append((arch, "archivo planificado ausente de cobertura_por_archivo"))
            continue
        if cob is None:
            smd_s60_por_archivo[arch] = None
            smd_lv_por_archivo[arch] = None
            invalidos_s60.append((arch, "archivo sin observaciones comparables (ABSTAIN)"))
            invalidos_lv.append((arch, "archivo sin observaciones comparables (ABSTAIN)"))
            continue
        if cob["estado"] == "SIN_ZONAS":
            smd_s60_por_archivo[arch] = None
            smd_lv_por_archivo[arch] = None
            invalidos_s60.append((arch, "archivo sin ninguna zona BigTrap2 (SIN_ZONAS) -- "
                                        "decision de tratamiento pendiente, ver PENDIENTE.md"))
            invalidos_lv.append((arch, "archivo sin ninguna zona BigTrap2 (SIN_ZONAS) -- "
                                       "decision de tratamiento pendiente, ver PENDIENTE.md"))
            continue

        s60_arch = smd_con_sd_ref(
            _media(cob["crudo_reales_s60"]), _media_ponderada(cob["crudo_controles_s60"], cob["pesos_controles"]),
            sd_ref_s60)
        lv_arch = smd_con_sd_ref(
            _media(cob["crudo_reales_lv"]), _media_ponderada(cob["crudo_controles_lv"], cob["pesos_controles"]),
            sd_ref_lv)
        smd_s60_por_archivo[arch] = s60_arch
        smd_lv_por_archivo[arch] = lv_arch
        if s60_arch is None or not math.isfinite(s60_arch):
            invalidos_s60.append((arch, "smd_log1p_sigma60_ticks no finito (None/NaN/Inf)"))
        if lv_arch is None or not math.isfinite(lv_arch):
            invalidos_lv.append((arch, "smd_log1p_bar_volume no finito (None/NaN/Inf)"))

        reales_s60_g.extend(cob["crudo_reales_s60"])
        controles_s60_g.extend(cob["crudo_controles_s60"])
        pesos_s60_g.extend(cob["pesos_controles"])
        reales_lv_g.extend(cob["crudo_reales_lv"])
        controles_lv_g.extend(cob["crudo_controles_lv"])
        pesos_lv_g.extend(cob["pesos_controles"])
        fuente_ms_s60_g.extend(cob["fuente_matched_sets_s60"])
        control_mean_ms_s60_g.extend(cob["control_mean_s60"])
        fuente_ms_lv_g.extend(cob["fuente_matched_sets_lv"])
        control_mean_ms_lv_g.extend(cob["control_mean_lv"])
        fuente_ms_session_g.extend(cob["fuente_matched_sets_session"])

    smd_s60_global = smd_con_sd_ref(_media(reales_s60_g), _media_ponderada(controles_s60_g, pesos_s60_g), sd_ref_s60)
    smd_lv_global = smd_con_sd_ref(_media(reales_lv_g), _media_ponderada(controles_lv_g, pesos_lv_g), sd_ref_lv)
    smd_s60_ms = smd_con_sd_ref(_media(fuente_ms_s60_g), _media(control_mean_ms_s60_g), sd_ref_s60)
    smd_lv_ms = smd_con_sd_ref(_media(fuente_ms_lv_g), _media(control_mean_ms_lv_g), sd_ref_lv)

    # peso_sesion: cada zona pesa 1/n_zonas_de_su_sesion -- la misma medida
    # en la que agregar_por_sesion() promedia el estimand primario.
    conteo_sesion = Counter(fuente_ms_session_g)
    pesos_sesion_g = [1.0 / conteo_sesion[s] for s in fuente_ms_session_g]
    smd_s60_peso_sesion = smd_con_sd_ref(
        _media_ponderada(fuente_ms_s60_g, pesos_sesion_g),
        _media_ponderada(control_mean_ms_s60_g, pesos_sesion_g), sd_ref_s60)
    smd_lv_peso_sesion = smd_con_sd_ref(
        _media_ponderada(fuente_ms_lv_g, pesos_sesion_g),
        _media_ponderada(control_mean_ms_lv_g, pesos_sesion_g), sd_ref_lv)

    def _max_abs_dict(smd_por_archivo):
        excluidos = sorted(a for a, v in smd_por_archivo.items() if v is None or not math.isfinite(v))
        validos = [abs(v) for v in smd_por_archivo.values() if v is not None and math.isfinite(v)]
        return dict(valor=(max(validos) if validos else None),
                   completo=(len(excluidos) == 0), archivos_excluidos=excluidos)

    max_abs_s60 = _max_abs_dict(smd_s60_por_archivo)
    max_abs_lv = _max_abs_dict(smd_lv_por_archivo)

    def _finito_y_dentro(v):
        return v is not None and math.isfinite(v) and abs(v) <= MAX_ABS_SMD

    smd_sigma60_ok = (not invalidos_s60 and _finito_y_dentro(smd_s60_global) and _finito_y_dentro(smd_s60_ms)
                      and _finito_y_dentro(smd_s60_peso_sesion) and max_abs_s60["completo"]
                      and max_abs_s60["valor"] is not None and max_abs_s60["valor"] <= MAX_ABS_SMD)
    smd_bar_volume_ok = (not invalidos_lv and _finito_y_dentro(smd_lv_global) and _finito_y_dentro(smd_lv_ms)
                         and _finito_y_dentro(smd_lv_peso_sesion) and max_abs_lv["completo"]
                         and max_abs_lv["valor"] is not None and max_abs_lv["valor"] <= MAX_ABS_SMD)

    return dict(
        sd_ref_log1p_sigma60_ticks=sd_ref_s60, sd_ref_log1p_bar_volume=sd_ref_lv, sd_ref_sha256=sd_ref_sha256,
        sd_ref_definicion="pooled_within_stratum(archivo x minuto_de_sesion)",
        sd_ref_diagnostico=dict(log1p_sigma60_ticks=diag_sd_s60, log1p_bar_volume=diag_sd_lv),
        sd_ref_por_archivo=sd_ref_por_archivo,
        sd_global_log1p_sigma60_ticks=sd_global_s60, sd_global_log1p_bar_volume=sd_global_lv,
        sd_ratio_global_sobre_within=dict(
            log1p_sigma60_ticks=_ratio(sd_global_s60, sd_ref_s60),
            log1p_bar_volume=_ratio(sd_global_lv, sd_ref_lv)),
        smd_log1p_sigma60_ticks_pre=smd_pre_s60, smd_log1p_bar_volume_pre=smd_pre_lv,
        smd_log1p_sigma60_ticks_pre_within_estrato=smd_pre_within_s60,
        smd_log1p_bar_volume_pre_within_estrato=smd_pre_within_lv,
        smd_log1p_sigma60_ticks_global_pooled=smd_s60_global,
        smd_log1p_sigma60_ticks_matched_sets=smd_s60_ms,
        smd_log1p_sigma60_ticks_peso_sesion=smd_s60_peso_sesion,
        smd_log1p_sigma60_ticks_max_abs_por_archivo=max_abs_s60,
        smd_log1p_sigma60_ticks_archivos_invalidos=invalidos_s60,
        smd_sigma60_ok=smd_sigma60_ok,
        smd_log1p_bar_volume_global_pooled=smd_lv_global,
        smd_log1p_bar_volume_matched_sets=smd_lv_ms,
        smd_log1p_bar_volume_peso_sesion=smd_lv_peso_sesion,
        smd_log1p_bar_volume_max_abs_por_archivo=max_abs_lv,
        smd_log1p_bar_volume_archivos_invalidos=invalidos_lv,
        smd_bar_volume_ok=smd_bar_volume_ok,
        smd_por_archivo=dict(log1p_sigma60_ticks=smd_s60_por_archivo, log1p_bar_volume=smd_lv_por_archivo),
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
    ordenado por fecha de sesion (orden causal, no aleatorio).

    `abstain_inferencia=True` (F2.2, auditoria 2026-08-11) si la varianza
    HAC de largo plazo (var_lr, antes de recortar a >=0 por ruido numerico)
    da <=0: devolver SE=0 en ese caso produciria un IC degenerado
    (ci95_lower == mean), y si mean>0 eso clasificaria RESIDUAL_POSITIVE de
    forma espuria -- una precision que la serie no tiene, no evidencia real."""
    x = np.asarray(r_s_cronologico, dtype=np.float64)
    n = len(x)
    if n == 0:
        return dict(n_sessions=0, mean=None, se_hac=None, ci95_lower=None,
                    ci95_upper=None, mde=None, lag=None, abstain_inferencia=None)
    mean = float(np.mean(x))
    resid = x - mean
    lag = max(1, int(math.ceil(math.sqrt(n))))
    gamma0 = float(np.mean(resid * resid))
    var_lr = gamma0
    for L in range(1, min(lag, n - 1) + 1):
        w = 1.0 - L / (lag + 1.0)  # kernel de Bartlett
        gamma_l = float(np.mean(resid[L:] * resid[:-L]))
        var_lr += 2.0 * w * gamma_l
    if var_lr <= 0:
        return dict(n_sessions=n, mean=mean, se_hac=None, ci95_lower=None,
                    ci95_upper=None, mde=None, lag=lag, abstain_inferencia=True)
    se_hac = math.sqrt(var_lr / n)
    z_alpha = 1.959963984540054  # qnorm(0.975)
    z_power = 0.8416212335729143  # qnorm(0.80)
    ci_lower = mean - z_alpha * se_hac
    ci_upper = mean + z_alpha * se_hac
    mde = (z_alpha + z_power) * se_hac
    return dict(n_sessions=n, mean=mean, se_hac=se_hac,
                ci95_lower=ci_lower, ci95_upper=ci_upper, mde=mde, lag=lag,
                abstain_inferencia=False)


def decidir_etiqueta(ic):
    if ic["n_sessions"] == 0:
        return "ABSTAIN_MATCHING"
    if ic.get("abstain_inferencia"):
        return "ABSTAIN_INFERENCE"
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
                              n_bars, horizontes_secundarios=(1, 2, 5, 10, 20, 60, 120),
                              calcular_endpoint=True):
    """`calcular_endpoint=False` (F0, modo `--solo-estructural`): la
    geometria reanclada (source_anchor_tick, rel_lo/hi_tick,
    control_anchor_tick/control_lo_tick/control_hi_tick por control) SIEMPRE
    se calcula -- es diagnostico de matching, no el estimand. Lo que se
    OMITE por completo cuando es False es `zone_lifecycle`/`endpoint_binario`
    (y_i, p0_i, r_i, y_ctrl, secundarios_touch_by_horizon): eso es
    literalmente el efecto que el pre-registro exige no mirar antes de que
    pasen los gates de balance/cobertura. No se computa -- no es que se
    calcule y se oculte despues."""
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

    sesion_idx = {f: i for i, f in enumerate(sorted(set(fechas_universo)))}
    resultados = []
    for z in zonas_matched:
        if z["match"]["estado"] != "OK":
            continue
        # Geometria reanclada: SIEMPRE se calcula (diagnostico de matching,
        # no el estimand -- F3 la necesita en modo estructural tambien).
        source_anchor_tick = int(close_t[z["created_bar"]])
        rel_lo_tick = z["lo_tick"] - source_anchor_tick
        rel_hi_tick = z["hi_tick"] - source_anchor_tick
        p0_controles = []
        controles_ledger = []
        for ctrl in z["match"]["elegidos"]:
            j = ctrl["bar_index"]
            control_anchor_tick = int(close_t[j])
            _rl, _rh, control_lo_tick, control_hi_tick = reanclar_geometria(
                z["lo_tick"], z["hi_tick"], source_anchor_tick, control_anchor_tick)
            # F3: diagnosticos de matching, siempre presentes (target-free).
            entry = dict(
                session_date=ctrl["session_date"], bar_index=j, score=ctrl["score"],
                control_anchor_tick=control_anchor_tick,
                control_lo_tick=control_lo_tick, control_hi_tick=control_hi_tick,
                session_offset=sesion_idx.get(ctrl["session_date"], None) - sesion_idx.get(z["session_date"], 0)
                if ctrl["session_date"] in sesion_idx and z["session_date"] in sesion_idx else None,
                anchor_distance_ticks=abs(control_anchor_tick - source_anchor_tick),
                bounds_igual_a_fuente=(control_lo_tick == z["lo_tick"] and control_hi_tick == z["hi_tick"]),
            )
            if calcular_endpoint:
                lc_ctrl = zone_lifecycle(control_lo_tick, control_hi_tick, z["is_bull"], j,
                                         high_t, low_t, close_t, n_bars, horizon_cap=z["horizon_i"])
                y_ctrl = endpoint_binario(lc_ctrl)
                entry["y_ctrl"] = y_ctrl
                p0_controles.append(y_ctrl)
            controles_ledger.append(entry)

        fila = dict(
            zone_id=z["zone_id"], session_date=z["session_date"],
            created_bar=z["created_bar"], k_efectivo=z["match"]["k_efectivo"],
            source_anchor_tick=source_anchor_tick,
            rel_lo_tick=rel_lo_tick, rel_hi_tick=rel_hi_tick,
            controles_ledger=controles_ledger,
        )
        # Endpoint (F0): el efecto en si -- SOLO si calcular_endpoint=True.
        # No se calcula y se esconde: directamente no se llama.
        if calcular_endpoint:
            lc_real = zone_lifecycle(z["lo_tick"], z["hi_tick"], z["is_bull"], z["created_bar"],
                                     high_t, low_t, close_t, n_bars, horizon_cap=z["horizon_i"])
            y_i = endpoint_binario(lc_real)
            p0_i = float(np.mean(p0_controles))
            r_i = y_i - p0_i
            secundarios = {}
            for k in horizontes_secundarios:
                hc = min(k, z["horizon_i"])
                lc_k = zone_lifecycle(z["lo_tick"], z["hi_tick"], z["is_bull"], z["created_bar"],
                                      high_t, low_t, close_t, n_bars, horizon_cap=hc)
                secundarios[k] = 1.0 if (lc_k["first_touch_age"] is not None and lc_k["first_touch_age"] <= hc) else 0.0
            # F4 (multiplicidad, auditoria 2026-08-11): estos horizontes NO
            # tienen contraparte de control -- p0_controles/y_ctrl solo se
            # calculan al horizonte PRIMARIO (z["horizon_i"]), nunca a
            # 1/2/5/10/20/60/120 barras. Sin control no hay residual (y_i-p0_i)
            # que adjudicar, solo la tasa de toque cruda de la zona real.
            # Marcado explicito para que nadie lo trate como un test
            # adicional (inflaria el numero efectivo de hipotesis sin la
            # comparacion pareada que lo haria valido).
            fila.update(y_i=y_i, p0_i=p0_i, r_i=r_i, lifecycle_real=lc_real,
                       secundarios_touch_by_horizon=dict(
                           valores=secundarios, adjudicable=False,
                           motivo="solo zona real, sin contraparte de control en estos "
                                  "horizontes -- descriptivo, no un residual"))
        resultados.append(fila)

    return dict(universo=universo, zonas_matched=zonas_matched, resultados=resultados,
                cobertura=calcular_balance_cobertura(zonas_matched, cov_por_barra),
                muestra_pre_matching=muestra_pre_matching(
                    zonas_matched, por_minuto, creadoras, cov_por_barra, n_bars),
                diagnostico_soporte_comun=diagnostico_soporte_comun(
                    zonas_matched, por_minuto, creadoras, cov_por_barra, n_bars))


def instrumentacion_f3(zonas_matched, resultados):
    """Diagnosticos target-free de matching, INDEPENDIENTES del estimand:
    histograma de n_pool, histograma de k_efectivo, desglose de abstenciones
    por motivo, distribucion del offset de sesion control-fuente, distancia
    de anclaje |control_anchor_tick - source_anchor_tick|, y el centinela
    frac_control_bounds_iguales_a_fuente (debe ser ~0, y solo distinto de 0
    cuando el anchor del control coincide exactamente con el de la fuente --
    si se dispara sin esa coincidencia, el reanclaje se rompio de nuevo)."""
    hist_n_pool = Counter(z["match"].get("n_pool", 0) for z in zonas_matched)
    hist_k_efectivo = Counter(z["match"]["k_efectivo"] for z in zonas_matched if z["match"]["estado"] == "OK")
    abstenciones_por_motivo = Counter(
        z["match"].get("motivo", "sin_motivo_declarado")
        for z in zonas_matched if z["match"]["estado"] != "OK")

    offsets, distancias, bounds_iguales, bounds_total = [], [], 0, 0
    for fila in resultados:
        for ctrl in fila["controles_ledger"]:
            if ctrl["session_offset"] is not None:
                offsets.append(ctrl["session_offset"])
            distancias.append(ctrl["anchor_distance_ticks"])
            bounds_total += 1
            if ctrl["bounds_igual_a_fuente"]:
                bounds_iguales += 1
                # el centinela solo es INOCENTE si el anchor coincide -- si no,
                # es exactamente el bug de reanclaje reapareciendo. `raise`
                # explicito (F2.2, auditoria 2026-08-11), no `assert`: un
                # centinela anti-regresion no puede depender de correr sin
                # `python -O` (que elimina los `assert` del bytecode).
                if ctrl["anchor_distance_ticks"] != 0:
                    raise ValueError(
                        "centinela: control_lo_tick==z.lo_tick con anchors DISTINTOS -- "
                        "el reanclaje no esta conectado (regresion del bug corregido en 6b76e34)")

    def resumen_num(xs):
        if not xs:
            return dict(n=0, p50=None, p90=None, media=None, min=None, max=None)
        arr = np.asarray(xs, dtype=np.float64)
        return dict(n=len(arr), p50=float(np.percentile(arr, 50)), p90=float(np.percentile(arr, 90)),
                   media=float(np.mean(arr)), min=float(arr.min()), max=float(arr.max()))

    return dict(
        histograma_n_pool=dict(sorted(hist_n_pool.items())),
        histograma_k_efectivo=dict(sorted(hist_k_efectivo.items())),
        abstenciones_por_motivo=dict(abstenciones_por_motivo),
        offset_sesion_control_menos_fuente=resumen_num(offsets),
        distancia_anclaje_ticks=resumen_num(distancias),
        frac_control_bounds_iguales_a_fuente=(bounds_iguales / bounds_total) if bounds_total else None,
        n_controles_evaluados=bounds_total,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke-archivo", default=None,
                    help="si se da, corre SOLO ese archivo (smoke pre-interpretacion). "
                         "IMPLICA --solo-estructural (F2.2, auditoria 2026-08-11): antes, "
                         "un archivo balanceado en modo smoke podia filtrar el estimand "
                         "sobre pocas sesiones -- sesiones_ok queda en None en smoke y la "
                         "condicion de abstencion chequea `is False`, no falsy, asi que "
                         "solo los gates de SMD lo tapaban por casualidad.")
    ap.add_argument("--solo-estructural", action="store_true",
                    help="F0: suprime el estimand por completo -- no se llama "
                         "agregar_por_sesion/hac_bartlett_ic/decidir_etiqueta, no se "
                         "imprime mean/se/ic/mde/etiqueta, y el payload omite "
                         "y_i/p0_i/r_i/y_ctrl/secundarios_touch_by_horizon. Para smoke "
                         "pre-interpretacion: valida universo/matching/cobertura/SMD "
                         "sin exponer el efecto.")
    a = ap.parse_args(argv)
    calcular_endpoint = not (a.solo_estructural or a.smoke_archivo)

    from edgelab.audit import validar_entorno_venv
    if not validar_entorno_venv(REPO_PATH):
        return 2

    head_start = git_head()
    dirty_start = git_dirty()
    if dirty_start:
        print("ABSTAIN_PROVENANCE: el arbol de trabajo esta sucio ANTES de empezar "
              "(`git status --porcelain` no vacio) -- se aborta ACA, sin computar ni "
              "imprimir ningun diagnostico. F2.2 registraba dirty_start al inicio pero "
              "recien lo evaluaba al final de main(), despues de imprimir GATES DE "
              "BALANCE/COBERTURA e INSTRUMENTACION: una corrida con procedencia "
              "invalida no debe producir numeros mirables, por el mismo motivo por el "
              "que el hash de NORTH_STAR.md ya abortaba de entrada (return 3).")
        return 5
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
    archivos_planificados = [x for x, _fs in plan]  # F2.1: fail-closed necesita el plan COMPLETO

    print("F1.1 NULO CONDICIONAL POR DISTANCIA -- adjudicacion geometrica exacta")
    print("  universo %d sesiones | K=%d min_controls=%d | max_age_bars=%d"
          % (ns_sesiones, K_CONTROLS, MIN_CONTROLS, MAX_AGE_BARS))

    residuales = []  # (session_date, r_i)
    todos_resultados = []
    todos_zonas_matched = []
    cobertura_acumulada = dict(n_total_zonas=0, n_zonas_ok=0)
    coberturas_por_archivo = {}  # F2/F2.2: agregar_balance_global() poolea esto DESPUES del loop
    muestras_pre_matching_por_archivo = {}  # F2.2: insumo de sd_ref, tambien pooleado despues
    diagnosticos_soporte_comun_por_archivo = []  # F2.4: resumir_soporte_comun() poolea esto despues
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
            coberturas_por_archivo[arch] = None  # F2.1: registrar el ABSTAIN, no dejarlo ausente
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
            ses_de_barra, rango_sesion, fechas, tk.tick_size, n_bars,
            calcular_endpoint=calcular_endpoint)

        if calcular_endpoint:
            for fila in res["resultados"]:
                residuales.append((fila["session_date"], fila["r_i"]))
        todos_resultados.extend(res["resultados"])
        todos_zonas_matched.extend(res["zonas_matched"])
        cobertura_acumulada["n_total_zonas"] += res["cobertura"]["n_total_zonas"]
        cobertura_acumulada["n_zonas_ok"] += res["cobertura"]["n_zonas_ok"]
        coberturas_por_archivo[arch] = res["cobertura"]
        muestras_pre_matching_por_archivo[arch] = res["muestra_pre_matching"]
        diagnosticos_soporte_comun_por_archivo.append(res["diagnostico_soporte_comun"])
        crudo[arch] = dict(estado="OK", sesiones=len(fechas),
                           n_zonas=res["cobertura"]["n_total_zonas"],
                           n_zonas_ok=res["cobertura"]["n_zonas_ok"])
        print("   zonas=%d  zonas_ok(>=%d controles)=%d"
              % (res["cobertura"]["n_total_zonas"], MIN_CONTROLS, res["cobertura"]["n_zonas_ok"]))

    cobertura_global = (cobertura_acumulada["n_zonas_ok"] / cobertura_acumulada["n_total_zonas"]
                        if cobertura_acumulada["n_total_zonas"] else 0.0)
    # F2/F2.1/F2.2: nunca promedio de SMDs por-archivo, sd_ref congelado pre-matching, fail-closed.
    smd_agregado = agregar_balance_global(coberturas_por_archivo, muestras_pre_matching_por_archivo,
                                          archivos_planificados)

    # sesiones_con_al_menos_una_zona: de zonas_matched (SIEMPRE tiene
    # session_date), no de `residuales` -- residuales queda vacio a proposito
    # en modo --solo-estructural, y este conteo tiene que seguir siendo
    # correcto en los dos modos.
    sesiones_con_zona = len(set(z["session_date"] for z in todos_zonas_matched))
    gates = dict(
        cobertura_global=cobertura_global, cobertura_ok=cobertura_global >= MIN_ZONE_COVERAGE,
        **smd_agregado,
        sesiones_con_al_menos_una_zona=sesiones_con_zona,
        sesiones_ok=(sesiones_con_zona >= REQUIRED_SOURCE_SESSIONS) if not a.smoke_archivo else None,
    )
    print("\n" + "=" * 70)
    print("GATES DE BALANCE/COBERTURA")
    for k, v in gates.items():
        print("  %s: %r" % (k, v))

    instrumentacion = instrumentacion_f3(todos_zonas_matched, todos_resultados)
    # F2.4: soporte comun -- pooleado entre archivos ANTES de reducir a
    # ninguna fraccion/percentil, mismo principio que sd_ref/smd.
    instrumentacion["soporte_comun"] = resumir_soporte_comun(diagnosticos_soporte_comun_por_archivo)
    print("\nINSTRUMENTACION (F3, target-free -- matching, no efecto)")
    for k, v in instrumentacion.items():
        print("  %s: %r" % (k, v))

    # F2.2 (auditoria 2026-08-11): gate de procedencia REAL, no solo
    # registrado. dirty_start/dirty_end/head_start/head_end se guardaban en
    # el payload desde el principio pero nunca se evaluaban -- solo el hash
    # de NORTH_STAR.md abortaba la corrida. Un arbol que se ensucia o un HEAD
    # que se mueve MIENTRAS la corrida esta en curso (otro proceso
    # commiteando, por ejemplo) invalida la procedencia igual que un hash
    # que no coincide -- mismo criterio que ya declaraba
    # specs/.../v1.json::decision_labels.ABSTAIN_PROVENANCE
    # ("dirty_or_head_changed_or_hash_missing"), nunca implementado del todo.
    head_end = git_head()
    dirty_end = git_dirty()
    if dirty_start or dirty_end or head_start != head_end:
        print("\nABSTAIN_PROVENANCE: arbol sucio o HEAD se movio durante la corrida "
              "(dirty_start=%r dirty_end=%r head_start=%s head_end=%s)"
              % (dirty_start, dirty_end, head_start, head_end))
        return 5

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F1.1_nulo_condicional_distancia",
        status="SMOKE" if a.smoke_archivo else "FORMAL_RUN",
        protocolo="docs/research/BIGTRAP2_DISTANCE_MATCHED_NULL_PROTOCOL_2026-08-11.md",
        spec_path=str(SPEC_PATH.relative_to(REPO_PATH)), spec_sha256=spec_sha256(),
        north_star_body_sha256=ns_hash,
        head_start=head_start, head_end=head_end, dirty_start=dirty_start, dirty_end=dirty_end,
        k_controls=K_CONTROLS, min_controls=MIN_CONTROLS,
        min_zone_coverage=MIN_ZONE_COVERAGE, max_abs_smd=MAX_ABS_SMD,
        required_source_sessions=REQUIRED_SOURCE_SESSIONS,
        max_age_bars=MAX_AGE_BARS, invalidation_mode=INVALIDATION_MODE, max_touches=MAX_TOUCHES,
        session_count=ns_sesiones, max_fecha_universo=peor, firewall_max_fecha=MAX_FECHA,
        firewall_corte_iso=str(corte_del_sello()), universe_filter_report=info,
        outcomes_accessed=False, holdout_opened=False, estimand_suppressed=(not calcular_endpoint),
        n_zonas_universo=cobertura_acumulada["n_total_zonas"],
        n_zonas_matched_ok=cobertura_acumulada["n_zonas_ok"],
        gates=gates, instrumentacion=instrumentacion,
        resultados_por_zona=todos_resultados,
        por_contrato=crudo,
        code_commit=head_end,  # ya verificado == head_start arriba (gate de procedencia)
        measurement_code_sha256=huella_del_codigo([INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))

    # F0: el estimand (agregacion por sesion + HAC + etiqueta de decision) NO
    # se calcula ni se imprime ni se serializa si --solo-estructural. No es
    # "se calcula y no se muestra": la funcion directamente no se llama.
    if calcular_endpoint:
        abstain = (not gates["cobertura_ok"] or not gates["smd_sigma60_ok"] or not gates["smd_bar_volume_ok"]
                  or (gates["sesiones_ok"] is False))
        por_sesion = agregar_por_sesion(residuales)
        r_s_cronologico = [por_sesion[ses] for ses in sorted(por_sesion)]
        ic = hac_bartlett_ic(r_s_cronologico) if not abstain else dict(
            n_sessions=len(por_sesion), mean=None, se_hac=None, ci95_lower=None,
            ci95_upper=None, mde=None, lag=None, abstain_inferencia=None)
        etiqueta = "ABSTAIN_MATCHING" if abstain else decidir_etiqueta(ic)
        print("\nESTIMAND: Delta_matched (mean_s(R_s), peso igual por sesion)")
        print("  n_sesiones_con_zona=%d  mean=%s  se_hac=%s  ic95=[%s, %s]  mde=%s"
              % (ic["n_sessions"], ic["mean"], ic["se_hac"], ic["ci95_lower"], ic["ci95_upper"], ic["mde"]))
        print("  ETIQUETA: %s" % etiqueta)
        payload["etiqueta"] = etiqueta
        payload["estimand_primario"] = ic
        payload["por_sesion"] = por_sesion
    else:
        print("\nESTIMAND: SUPRIMIDO (--solo-estructural) -- no calculado, no impreso, no serializado.")
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
