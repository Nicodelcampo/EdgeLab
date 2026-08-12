# -*- coding: utf-8 -*-
"""F2.7 — nulo local por reflexión de geometría (v2).

Pregunta pre-registrada (docs/research/BIGTRAP2_LOCAL_REFLECTION_NULL_PROTOCOL_2026-08-12.md):
para cada zona BigTrap2, su reflejo geométrico alrededor del cierre de la barra
creadora recibe primer toque con la misma probabilidad que la zona real?

Endpoint primario: carrera de primer pasaje dentro del par (r_i = +1 si la zona
real toca primero, -1 si el espejo toca primero, 0 en empate técnico o doble
censura). Nulo exacto: P(real primero) = P(espejo primero) bajo
intercambiabilidad de ubicaciones.

Sin dirección, sin P&L, sin stop/target, sin holdout, sin tick:25.
`outcomes_accessed=False`.

## Capas separadas

1. `construir_universo_zonas` -- reusada de F1.1 (importada).
2. `construir_reflejo` -- reflexión geométrica exacta (2*anchor - [lo,hi]).
3. `zone_lifecycle` -- reusada de F1.1 (importada). El espejo usa lifecycle
   reflejado (is_bull invertido para las reglas de lifecycle -- fix D2).
4. `carrera_primer_pasaje` -- r_i con tie-break por timestamp de tick.
5. `agregar_por_sesion` -- reusada de F1.1 (importada).
6. `hac_bartlett_ic` -- reusada de F1.1 (importada).
7. `smoke_estructural` -- modo `--solo-estructural` sin computar toques reales.
8. `construir_payload` + `construir_manifiesto` -- procedencia.

No se modifica `edgelab/bridge/indicators/bigtrap2.py`. No se usa `tick:25`.
No se abre el holdout. No se leen retornos, P&L, dirección, stops ni targets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path

import importlib.util

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

from diag.tasa_senales.curva_excursion_ticks import (  # noqa: E402
    BAR_DRIVEN, LEAD_DAYS, MAX_FECHA, REGISTRY, TZ_CHART, bars_mod,
    corte_del_sello, dias_research, git_head, huella_del_codigo, pd, ticks_mod,
)
from diag.tasa_senales.F1_nulo_zonas_aleatorias import sesiones_de_barras  # noqa: E402

# F1.1 has a dot in the filename -- importlib required (same pattern as tests)
_F11_PATH = REPO_PATH / "diag" / "tasa_senales" / "F1.1_nulo_condicional_distancia.py"
_f11_spec = importlib.util.spec_from_file_location("f11_ncd", _F11_PATH)
f11 = importlib.util.module_from_spec(_f11_spec)
sys.modules["f11_ncd"] = f11
_f11_spec.loader.exec_module(f11)

construir_universo_zonas = f11.construir_universo_zonas
tick_bounds_from_price = f11.tick_bounds_from_price
horizonte_zona = f11.horizonte_zona
zone_lifecycle = f11.zone_lifecycle
agregar_por_sesion = f11.agregar_por_sesion
hac_bartlett_ic = f11.hac_bartlett_ic
git_dirty = f11.git_dirty
north_star_body_sha256 = f11.north_star_body_sha256
data_root = f11.data_root
MAX_AGE_BARS = f11.MAX_AGE_BARS
INVALIDATION_MODE = f11.INVALIDATION_MODE
MAX_TOUCHES = f11.MAX_TOUCHES

from edgelab.bridge.indicators.bigtrap2 import DEFAULTS  # noqa: E402
from edgelab.research.first_touch_census import session_date_ct  # noqa: E402

SCHEMA_VERSION = "F2.7_nulo_reflexion_local_v1"
INDICADOR = "BigTrap2"

NORTH_STAR_BODY_SHA256_EXPECTED = (
    "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1")
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_local_reflection_null_v2.json"
SPEC_SHA256_EXPECTED = "7868ff327b240a9e3a8c5a2dc2412f8605f3bd91b371dc828a677755a5e0993b"

# Gates from spec v2
REFLECTION_COVERAGE_MIN = 0.95
REQUIRED_SOURCE_SESSIONS = 201
RESOLUTION_RATE_MIN = 0.30
TECHNICAL_TIES_MAX = 0.01
MDE_DELTA = 0.05

# Research end date (Chicago timezone)
RESEARCH_END_INCLUSIVE = "2026-06-30"


# ======================================================================
# Capa 0 -- procedencia
# ======================================================================

def north_star_body_sha256():
    """SHA-256 of NORTH_STAR.md body with LF line ending normalization (handles Windows git CRLF checkout)."""
    p = REPO_PATH / "docs" / "NORTH_STAR.md"
    data = p.read_bytes()
    marker = b"<!-- SHA256-BODY-ABOVE -->"
    idx = data.index(marker)
    body_raw = data[:idx]
    normalized = body_raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def spec_sha256():
    """SHA-256 of the spec file with LF normalization (the auditor created
    it on Linux)."""
    raw = SPEC_PATH.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


# ======================================================================
# Capa 2 -- construcción del reflejo geométrico
# ======================================================================

def construir_reflejo(zona, close_t):
    """Para la zona real [lo_tick, hi_tick], construye su reflejo geométrico:
    mirror_lo = 2*anchor - hi_tick, mirror_hi = 2*anchor - lo_tick.

    El campo is_bull se preserva como etiqueta semántica; las reglas de
    lifecycle del espejo invierten is_bull (fix D2).

    Returns: dict con mirror_lo_tick, mirror_hi_tick, anchor_tick,
    distance_ticks, is_eligible (el espejo es distinto y disjunto de la zona),
    mirror_is_bull_for_lifecycle (invertido)."""
    anchor_tick = int(close_t[zona["created_bar"]])
    lo, hi = zona["lo_tick"], zona["hi_tick"]

    mirror_lo = 2 * anchor_tick - hi
    mirror_hi = 2 * anchor_tick - lo

    # Distance in ticks from the anchor to the nearest edge of the zone
    # (and by construction, the same distance to the nearest edge of the mirror)
    if zona["is_bull"]:
        # Bull zone is above anchor: distance = lo - anchor
        distance_ticks = lo - anchor_tick
    else:
        # Bear zone is below anchor: distance = anchor - hi
        distance_ticks = anchor_tick - hi

    # Width is preserved by construction
    width_real = hi - lo
    width_mirror = mirror_hi - mirror_lo
    assert width_real == width_mirror, f"Width mismatch: {width_real} vs {width_mirror}"

    # Eligibility: mirror must be disjoint from the real zone
    # (no overlap: mirror_hi < lo or mirror_lo > hi)
    is_disjoint = (mirror_hi < lo) or (mirror_lo > hi)
    # Mirror must be distinct (not identical)
    is_distinct = (mirror_lo != lo) or (mirror_hi != hi)
    is_eligible = is_disjoint and is_distinct

    # For lifecycle rules, the mirror inverts is_bull (fix D2):
    # a bull zone above the anchor has its mirror BELOW the anchor;
    # the mirror's invalidation should be "close through in the direction
    # away from the anchor", which means treating it as a bear zone for
    # lifecycle purposes.
    mirror_is_bull_for_lifecycle = not zona["is_bull"]

    return dict(
        mirror_lo_tick=mirror_lo,
        mirror_hi_tick=mirror_hi,
        anchor_tick=anchor_tick,
        distance_ticks=abs(distance_ticks),
        width_ticks=width_real,
        is_eligible=is_eligible,
        is_disjoint=is_disjoint,
        is_distinct=is_distinct,
        mirror_is_bull_for_lifecycle=mirror_is_bull_for_lifecycle,
        exclusion_reason=(None if is_eligible else
                          ("not_disjoint" if not is_disjoint else "not_distinct")),
    )


# ======================================================================
# Capa 3 -- carrera de primer pasaje dentro del par
# ======================================================================

def resolver_empate_por_tick(zona, reflejo, bar_idx, tk_price_ticks, bar_start_ends):
    """Resuelve empates a nivel barra inspeccionando la secuencia de ticks dentro de la barra de primer toque.
    
    `bar_start_ends`: tupla (i0, i1) o callable bar_idx -> (i0, i1) de la barra en tk_price_ticks.
    Devuelve (r_i, category): (+1.0 'real_first', -1.0 'mirror_first', 0.0 'empate_tecnico').
    """
    if callable(bar_start_ends):
        i0, i1 = bar_start_ends(bar_idx)
    elif isinstance(bar_start_ends, dict):
        i0, i1 = bar_start_ends[bar_idx]
    else:
        i0, i1 = bar_start_ends[bar_idx]

    prices = np.asarray(tk_price_ticks[i0:i1], dtype=np.int64)

    real_lo, real_hi = zona["lo_tick"], zona["hi_tick"]
    mirror_lo, mirror_hi = reflejo["mirror_lo_tick"], reflejo["mirror_hi_tick"]

    real_touches = (prices >= real_lo) & (prices <= real_hi)
    mirror_touches = (prices >= mirror_lo) & (prices <= mirror_hi)

    k_real = int(np.argmax(real_touches)) if real_touches.any() else None
    k_mirror = int(np.argmax(mirror_touches)) if mirror_touches.any() else None

    if k_real is not None and k_mirror is not None:
        if k_real < k_mirror:
            return 1.0, "real_first"
        elif k_mirror < k_real:
            return -1.0, "mirror_first"
        else:
            return 0.0, "empate_tecnico"
    elif k_real is not None:
        return 1.0, "real_first"
    elif k_mirror is not None:
        return -1.0, "mirror_first"
    else:
        return 0.0, "empate_tecnico"


def first_passage_race(zona, reflejo, created_bar, high_t, low_t, close_t, n,
                       max_age_bars=MAX_AGE_BARS,
                       invalidation_mode=INVALIDATION_MODE,
                       max_touches=MAX_TOUCHES, horizon_cap=None,
                       tk_price_ticks=None, bar_start_ends=None):
    """Computes the first-passage race between the real zone and its mirror.

    r_i = +1 if real touches first, -1 if mirror touches first,
    0 if technical tie or double censoring.

    Both arms run with the SAME horizon (spec v2: same_horizon_for_real_and_mirror).

    The mirror uses the REFLECTED lifecycle (is_bull inverted for lifecycle rules),
    fixing defect D2. Same-bar ties are resolved at the tick level if tick arrays are provided.

    Returns dict with r_i, category, real/mirror lifecycle results, etc."""
    # Compute horizon (same for both arms)
    if horizon_cap is None:
        horizon_cap = horizonte_zona(created_bar, n)

    # Real zone lifecycle
    real_lc = zone_lifecycle(
        zona["lo_tick"], zona["hi_tick"], zona["is_bull"],
        created_bar, high_t, low_t, close_t, n,
        max_age_bars=max_age_bars, invalidation_mode=invalidation_mode,
        max_touches=max_touches, horizon_cap=horizon_cap)

    # Mirror lifecycle (is_bull INVERTED for lifecycle rules -- fix D2)
    mirror_lc = zone_lifecycle(
        reflejo["mirror_lo_tick"], reflejo["mirror_hi_tick"],
        reflejo["mirror_is_bull_for_lifecycle"],
        created_bar, high_t, low_t, close_t, n,
        max_age_bars=max_age_bars, invalidation_mode=invalidation_mode,
        max_touches=max_touches, horizon_cap=horizon_cap)

    real_touched = real_lc["touched_before_removal"]
    mirror_touched = mirror_lc["touched_before_removal"]
    real_fta = real_lc["first_touch_age"]
    mirror_fta = mirror_lc["first_touch_age"]

    # Classify the outcome
    if real_touched and mirror_touched:
        if real_fta < mirror_fta:
            r_i = 1.0
            category = "real_first"
        elif mirror_fta < real_fta:
            r_i = -1.0
            category = "mirror_first"
        elif real_fta == mirror_fta:
            b_touch = created_bar + real_fta
            if tk_price_ticks is not None and bar_start_ends is not None:
                r_i, category = resolver_empate_por_tick(
                    zona, reflejo, b_touch, tk_price_ticks, bar_start_ends)
            else:
                r_i = 0.0
                category = "same_bar_needs_tick_tiebreak"
        else:
            r_i = 0.0
            category = "unexpected"
    elif real_touched and not mirror_touched:
        r_i = 1.0
        category = "real_first"
    elif mirror_touched and not real_touched:
        r_i = -1.0
        category = "mirror_first"
    else:
        # Double censoring: neither arm touched
        r_i = 0.0
        category = "double_censoring"

    return dict(
        r_i=r_i,
        category=category,
        real_lifecycle=real_lc,
        mirror_lifecycle=mirror_lc,
        horizon_cap=horizon_cap,
    )


# ======================================================================
# Capa 4 -- decisión y etiquetas
# ======================================================================

def decidir_etiqueta_reflexion(ic, frac_resueltos, frac_empate_tecnico):
    """Decision labels per spec v2."""
    if ic["n_sessions"] == 0:
        return "ABSTAIN_REFLECTION_COVERAGE"
    if ic.get("abstain_inferencia"):
        return "ABSTAIN_INFERENCE"
    if frac_resueltos < RESOLUTION_RATE_MIN:
        return "ABSTAIN_RESOLUTION"
    if frac_empate_tecnico > TECHNICAL_TIES_MAX:
        return "ABSTAIN_TIE_RULE"
    if ic["ci95_lower"] > 0:
        return "REFLECTION_POSITIVE"
    if ic["ci95_upper"] < 0:
        return "REFLECTION_NEGATIVE"
    return "COMPATIBLE_WITH_ZERO"


# ======================================================================
# Smoke estructural (target-free)
# ======================================================================

def smoke_estructural(archivo_parquet, solo_estructural=True):
    """Runs the structural smoke test on a parquet file.

    When solo_estructural=True, does NOT compute the race on real data
    (that would be peeking). Only reports:
    - Eligibility coverage
    - Distance distribution (d in ticks)
    - Width distribution
    - Mirror overlap diagnostics
    - Zones per session
    - Session date filter verification
    - Horizon and censoring structure
    """
    import pyarrow.parquet as pq

    print(f"=== F2.7 Smoke Estructural ===")
    print(f"Archivo: {archivo_parquet}")
    print(f"Modo: {'SOLO ESTRUCTURAL (sin toques)' if solo_estructural else 'COMPLETO'}")
    print()

    # --- Load canonical ticks and build time:1 bars ---
    pq_path = Path(archivo_parquet)
    tk = ticks_mod.load_canonical_parquet(str(pq_path))
    b = bars_mod.build_time_bars(tk, 1)
    n_bars = len(b)
    print(f"Filas de ticks cargadas: {len(tk.sequence)}")
    print(f"Barras time:1: {n_bars}")

    bar_end = np.asarray(b.end_ns)
    high_t = np.asarray(b.high_t)
    low_t = np.asarray(b.low_t)
    close_t = np.asarray(b.close_t)
    bar_volume = np.asarray(b.volume, dtype=np.float64)

    # Run BigTrap2 kernel
    fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
    mod = REGISTRY[INDICADOR]
    r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None else mod.run(tk, b, chart_tz=TZ_CHART)
    kernel_zones = r.get("zones") or []
    tick_size = tk.tick_size
    print(f"\nZonas del kernel (total en archivo): {len(kernel_zones)}")

    # Sessions
    fechas_disponibles = sorted(set(session_date_ct(int(ns // 1_000_000)) for ns in b.start_ns))
    ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas_disponibles)

    # Build universe (only research sessions <= 2026-06-30)
    todas_sesiones = sorted(rango_sesion.keys())
    sesiones_research = [s for s in todas_sesiones if s <= RESEARCH_END_INCLUSIVE]
    sesiones_excluidas = [s for s in todas_sesiones if s > RESEARCH_END_INCLUSIVE]

    print(f"\nSesiones totales en el archivo: {len(todas_sesiones)}")
    print(f"Sesiones dentro del research window (<= {RESEARCH_END_INCLUSIVE}): {len(sesiones_research)}")
    print(f"Sesiones excluidas por filtro de fecha: {len(sesiones_excluidas)}")
    if sesiones_excluidas:
        print(f"  Primera excluida: {sesiones_excluidas[0]}")
        print(f"  Última excluida: {sesiones_excluidas[-1]}")

    fechas_universo = sesiones_research
    universo, creadoras = construir_universo_zonas(
        kernel_zones, ses_de_barra, rango_sesion, fechas_universo,
        tick_size, n_bars)
    print(f"Zonas en el universo de research: {len(universo)}")
    print(f"Sesiones con zonas: {len(set(z['session_date'] for z in universo))}")

    # --- Reflection ---
    n_eligible = 0
    n_excluded = 0
    exclusion_reasons = Counter()
    distances = []
    widths = []
    mirror_overlaps_with_other_zones = 0
    zonas_por_sesion = Counter()
    reflections = []

    # Build a set of all zone intervals for overlap checking
    all_zone_intervals = set()
    for z in universo:
        all_zone_intervals.add((z["lo_tick"], z["hi_tick"], z["created_bar"]))

    for z in universo:
        reflejo = construir_reflejo(z, close_t)
        zonas_por_sesion[z["session_date"]] += 1

        if reflejo["is_eligible"]:
            n_eligible += 1
            distances.append(reflejo["distance_ticks"])
            widths.append(reflejo["width_ticks"])

            # Check if mirror overlaps with any OTHER zone's geometry
            # (from a different creation bar)
            for (lo_other, hi_other, cb_other) in all_zone_intervals:
                if cb_other == z["created_bar"]:
                    continue
                # Overlap check
                if (reflejo["mirror_lo_tick"] <= hi_other and
                        reflejo["mirror_hi_tick"] >= lo_other):
                    mirror_overlaps_with_other_zones += 1
                    break  # count each mirror at most once

            reflections.append(dict(zona=z, reflejo=reflejo))
        else:
            n_excluded += 1
            exclusion_reasons[reflejo["exclusion_reason"]] += 1

    n_total = len(universo)
    cobertura = n_eligible / n_total if n_total > 0 else 0.0

    print(f"\n=== Resultados Estructurales ===")
    print(f"Total zonas en universo: {n_total}")
    print(f"Elegibles para reflexión: {n_eligible}")
    print(f"Excluidas: {n_excluded}")
    if exclusion_reasons:
        for reason, count in exclusion_reasons.items():
            print(f"  - {reason}: {count}")
    print(f"Cobertura de elegibilidad: {cobertura:.4f} (gate >= {REFLECTION_COVERAGE_MIN})")

    if distances:
        d = np.array(distances)
        print(f"\nDistribución de d (ticks):")
        print(f"  min={d.min()}, p25={np.percentile(d, 25):.0f}, "
              f"p50={np.percentile(d, 50):.0f}, p75={np.percentile(d, 75):.0f}, "
              f"max={d.max()}")
        print(f"  d <= 2: {(d <= 2).sum()} ({100*(d<=2).mean():.1f}%)")
        print(f"  d <= 3: {(d <= 3).sum()} ({100*(d<=3).mean():.1f}%)")
        print(f"  d <= 5: {(d <= 5).sum()} ({100*(d<=5).mean():.1f}%)")

    if widths:
        w = np.array(widths)
        print(f"\nDistribución de ancho (ticks):")
        print(f"  min={w.min()}, p50={np.percentile(w, 50):.0f}, "
              f"p75={np.percentile(w, 75):.0f}, max={w.max()}")

    print(f"\nEspejos solapados con zonas de otras creaciones: {mirror_overlaps_with_other_zones}")

    print(f"\nZonas por sesión:")
    for ses in sorted(zonas_por_sesion.keys()):
        print(f"  {ses}: {zonas_por_sesion[ses]}")

    # Horizon and censoring structure (without computing touches)
    if not solo_estructural:
        print("\n=== ADVERTENCIA: modo completo NO implementado en smoke ===")
        print("La carrera solo se computa en la corrida formal.")
    else:
        # Structural horizon info
        horizons = []
        for entry in reflections:
            z = entry["zona"]
            h = horizonte_zona(z["created_bar"], n_bars)
            horizons.append(h)
            truncated = (z["created_bar"] + h >= n_bars - 1)

        horizons = np.array(horizons)
        n_truncated = sum(1 for e in reflections
                         if e["zona"]["created_bar"] + horizonte_zona(e["zona"]["created_bar"], n_bars) >= n_bars - 1)
        print(f"\nHorizonte:")
        print(f"  min={horizons.min()}, p50={np.percentile(horizons, 50):.0f}, "
              f"max={horizons.max()}")
        print(f"  Truncadas por fin de archivo: {n_truncated} ({100*n_truncated/len(reflections):.1f}%)")

    # Summary payload
    payload = dict(
        schema_version=SCHEMA_VERSION,
        mode="smoke_estructural" if solo_estructural else "formal",
        archivo=str(pq_path.name),
        n_bars=n_bars,
        n_zonas_kernel=len(kernel_zones),
        n_zonas_universo=n_total,
        n_zonas_elegibles=n_eligible,
        n_zonas_excluidas=n_excluded,
        exclusion_reasons=dict(exclusion_reasons),
        cobertura_elegibilidad=cobertura,
        cobertura_gate_pass=cobertura >= REFLECTION_COVERAGE_MIN,
        sesiones_total=len(todas_sesiones),
        sesiones_research=len(sesiones_research),
        sesiones_excluidas=len(sesiones_excluidas),
        primera_sesion_excluida=sesiones_excluidas[0] if sesiones_excluidas else None,
        distancia_ticks=dict(
            min=int(min(distances)) if distances else None,
            p25=float(np.percentile(distances, 25)) if distances else None,
            p50=float(np.percentile(distances, 50)) if distances else None,
            p75=float(np.percentile(distances, 75)) if distances else None,
            max=int(max(distances)) if distances else None,
            frac_le_2=float((np.array(distances) <= 2).mean()) if distances else None,
            frac_le_3=float((np.array(distances) <= 3).mean()) if distances else None,
            frac_le_5=float((np.array(distances) <= 5).mean()) if distances else None,
        ) if distances else None,
        ancho_ticks=dict(
            min=int(min(widths)) if widths else None,
            p50=float(np.percentile(widths, 50)) if widths else None,
            max=int(max(widths)) if widths else None,
        ) if widths else None,
        espejos_solapados_con_otras_zonas=mirror_overlaps_with_other_zones,
        zonas_por_sesion={k: v for k, v in sorted(zonas_por_sesion.items())},
        horizonte=dict(
            min=int(horizons.min()) if len(horizons) > 0 else None,
            p50=float(np.percentile(horizons, 50)) if len(horizons) > 0 else None,
            max=int(horizons.max()) if len(horizons) > 0 else None,
            n_truncadas=n_truncated if not solo_estructural or len(reflections) > 0 else None,
        ) if 'horizons' in dir() and len(horizons) > 0 else None,
        outcomes_accessed=False,
    )

    return payload


def main_checkout_path():
    """Resuelve la ruta del checkout principal usando `git worktree list --porcelain`."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO_PATH), "worktree", "list", "--porcelain"], text=True)
        for line in out.splitlines():
            if line.startswith("worktree "):
                return Path(line[len("worktree "):].strip())
    except Exception:
        pass
    return REPO_PATH


def validar_entorno_venv():
    """Verifica que el script corra dentro de un entorno virtual (.venv) gobernado.
    Acepta únicamente:
    1) REPO_PATH/.venv (checkout local o principal)
    2) <main_checkout>/.venv (worktree principal)
    3) <data_root>.parent/.venv (entorno gobernado de datos donde habita data/, p.ej. E:\\EdgeLab\\.venv)
    """
    if sys.prefix == sys.base_prefix:
        print("ABSTAIN_PROVENANCE: no se está ejecutando dentro de un entorno virtual (.venv)")
        return False

    prefix_path = Path(sys.prefix).resolve()
    local_venv = (REPO_PATH / ".venv").resolve()
    main_venv = (main_checkout_path() / ".venv").resolve()

    # Valida si la raíz del .venv contiene la estructura de datos EdgeLab (`data/`)
    es_entorno_datos = (prefix_path.name == ".venv" and (prefix_path.parent / "data").exists())

    if prefix_path in (local_venv, main_venv) or es_entorno_datos:
        return True

    print(f"ABSTAIN_PROVENANCE: entorno virtual no autorizado ({prefix_path})")
    return False


# ======================================================================
# CLI
# ======================================================================

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="F2.7 — nulo local por reflexión de geometría (v2)")
    parser.add_argument("--smoke-archivo", type=str,
                        help="Path to parquet file for structural smoke test")
    parser.add_argument("--solo-estructural", action="store_true",
                        help="Structural-only smoke (no touches computed)")
    args = parser.parse_args(argv)

    if not validar_entorno_venv():
        return 2

    if git_dirty():
        print("ABSTAIN_PROVENANCE: el árbol de trabajo está sucio")
        # En smoke permitimos continuar imprimiendo aviso
        if not args.solo_estructural:
            return 5

    ns_hash = north_star_body_sha256()
    if ns_hash != NORTH_STAR_BODY_SHA256_EXPECTED:
        print(f"ABSTAIN_PROVENANCE: hash de NORTH_STAR.md no coincide ({ns_hash} != {NORTH_STAR_BODY_SHA256_EXPECTED})")
        return 3

    sp_hash = spec_sha256()
    if sp_hash != SPEC_SHA256_EXPECTED:
        print(f"ABSTAIN_PROVENANCE: hash de spec v2 no coincide ({sp_hash} != {SPEC_SHA256_EXPECTED})")
        return 4

    if args.smoke_archivo:
        payload = smoke_estructural(args.smoke_archivo, args.solo_estructural)
        payload["git_head"] = git_head()
        payload["git_dirty"] = git_dirty()
        payload["north_star_sha256"] = ns_hash
        payload["spec_sha256"] = sp_hash
        out_path = REPO_PATH / "diag" / "tasa_senales" / "F2.7_smoke_estructural.json"
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"\nPayload escrito en: {out_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
