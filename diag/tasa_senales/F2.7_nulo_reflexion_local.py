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
def resolve_data_root():
    try:
        dr = f11.data_root()
        if dr.exists():
            return dr
    except Exception:
        pass
    p_venv = Path(sys.prefix).resolve()
    if (p_venv.parent / "data").exists():
        return p_venv.parent / "data"
    local = REPO_PATH / "data"
    if local.exists():
        return local
    raise RuntimeError("data_root not found")


data_root = resolve_data_root
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

def decidir_etiqueta_reflexion(ic, frac_resueltos, frac_empate_tecnico, n_sesiones_con_zonas=None, cobertura=None):
    """Decision labels per spec v2."""
    if n_sesiones_con_zonas is not None and n_sesiones_con_zonas != REQUIRED_SOURCE_SESSIONS:
        return "ABSTAIN_REFLECTION_COVERAGE"
    if cobertura is not None and cobertura < REFLECTION_COVERAGE_MIN:
        return "ABSTAIN_REFLECTION_COVERAGE"
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


def parquet_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def pip_freeze_sha256() -> str | None:
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
        return hashlib.sha256(out.encode("utf-8")).hexdigest()
    except Exception:
        return None


def script_sha256() -> str:
    raw = Path(__file__).read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def construir_bar_start_ends(tk_ts_ns, bar_start_ns, bar_end_ns):
    bar_starts = np.searchsorted(tk_ts_ns, bar_start_ns, side="left")
    bar_ends = np.searchsorted(tk_ts_ns, bar_end_ns, side="right")
    return list(zip(bar_starts, bar_ends))


def correr_formal():
    head_start = git_head()
    dirty_start = git_dirty()
    if dirty_start:
        print("ABSTAIN_PROVENANCE: el árbol de trabajo está sucio antes de empezar la corrida formal")
        return 5

    ns_hash = north_star_body_sha256()
    if ns_hash != NORTH_STAR_BODY_SHA256_EXPECTED:
        print(f"ABSTAIN_PROVENANCE: hash de NORTH_STAR.md no coincide ({ns_hash} != {NORTH_STAR_BODY_SHA256_EXPECTED})")
        return 3

    sp_hash = spec_sha256()
    if sp_hash != SPEC_SHA256_EXPECTED:
        print(f"ABSTAIN_PROVENANCE: hash de spec v2 no coincide ({sp_hash} != {SPEC_SHA256_EXPECTED})")
        return 4

    print("=== F2.7 CORRIDA FORMAL (201 SESIONES) ===")
    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]

    corte_utc = corte_del_sello()
    corte_utc_ns = int(corte_utc.value)

    total_zonas_excluidas = 0
    total_zonas_elegibles = 0
    exclusion_reasons = Counter()
    distancias_elegibles = []
    widths_elegibles = []
    all_zone_intervals = []
    file_hashes = {}
    file_max_timestamps = {}
    file_max_timestamps_iso = {}
    race_results = []
    universo_todas = []
    sesiones_con_zonas_set = set()

    for arch, fechas in plan:
        fechas_research = [f for f in fechas if f <= RESEARCH_END_INCLUSIVE]
        if not fechas_research:
            continue
        print(f"\nProcesando {arch} ({len(fechas_research)} sesiones)...", flush=True)

        ini = (pd.Timestamp(fechas_research[0] + " 00:00:00", tz="America/Chicago")
               - pd.Timedelta(days=LEAD_DAYS))
        fin_contrato = (pd.Timestamp(fechas_research[-1] + " 00:00:00", tz="America/Chicago")
                        + pd.Timedelta(days=1))
        fin = min(fin_contrato.tz_convert("UTC"), corte_utc)

        pq_path = data_root() / "nt8" / "6E" / arch
        file_hashes[arch] = parquet_file_sha256(pq_path)

        tk = ticks_mod.load_canonical_parquet(
            str(pq_path),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))

        max_ts = int(np.max(tk.ts_ns))
        assert max_ts < corte_utc_ns, f"FIREWALL VIOLATED in {arch}: max ts {max_ts} >= {corte_utc_ns}"
        file_max_timestamps[arch] = max_ts
        file_max_timestamps_iso[arch] = pd.Timestamp(max_ts, unit="ns", tz="UTC").isoformat()

        print(f"  Max timestamp cargado: {file_max_timestamps_iso[arch]} (< {corte_utc.isoformat()})")

        b = bars_mod.build_time_bars(tk, 1)
        n_bars = len(b)
        bar_end = np.asarray(b.end_ns)
        high_t = np.asarray(b.high_t)
        low_t = np.asarray(b.low_t)
        close_t = np.asarray(b.close_t)

        bar_start_ends = construir_bar_start_ends(
            np.asarray(tk.ts_ns), np.asarray(b.start_ns), np.asarray(b.end_ns))
        tk_price_ticks = np.asarray(tk.price_ticks, dtype=np.int64)

        fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
        mod = REGISTRY[INDICADOR]
        r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None else mod.run(tk, b, chart_tz=TZ_CHART)
        kernel_zones = r.get("zones") or []

        fechas_disponibles = sorted(set(session_date_ct(int(ns // 1_000_000)) for ns in b.start_ns))
        ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas_disponibles)

        universo, _creadoras = construir_universo_zonas(
            kernel_zones, ses_de_barra, rango_sesion, fechas_research,
            tk.tick_size, n_bars)

        print(f"  Zonas universo en archivo: {len(universo)}")

        for z in universo:
            sesiones_con_zonas_set.add(z["session_date"])
            reflejo = construir_reflejo(z, close_t)
            universo_todas.append(dict(zona=z, reflejo=reflejo, archivo=arch))
            all_zone_intervals.append((z["lo_tick"], z["hi_tick"], z["created_bar"], arch))

            if not reflejo["is_eligible"]:
                total_zonas_excluidas += 1
                exclusion_reasons[reflejo["exclusion_reason"]] += 1
                continue

            total_zonas_elegibles += 1
            distancias_elegibles.append(reflejo["distance_ticks"])
            widths_elegibles.append(reflejo["width_ticks"])

            carrera = first_passage_race(
                z, reflejo, z["created_bar"], high_t, low_t, close_t, n_bars,
                tk_price_ticks=tk_price_ticks, bar_start_ends=bar_start_ends)
            race_results.append(dict(zona=z, reflejo=reflejo, carrera=carrera, archivo=arch))

    # Overlap diagnostic
    mirror_overlaps_with_other_zones = 0
    for res in race_results:
        z = res["zona"]
        m_lo, m_hi = res["reflejo"]["mirror_lo_tick"], res["reflejo"]["mirror_hi_tick"]
        arch = res["archivo"]
        for (lo_o, hi_o, cb_o, arch_o) in all_zone_intervals:
            if arch_o == arch and cb_o == z["created_bar"]:
                continue
            if m_lo <= hi_o and m_hi >= lo_o:
                mirror_overlaps_with_other_zones += 1
                break

    total_zonas_universo = len(universo_todas)
    cobertura_elegibilidad = (total_zonas_elegibles / total_zonas_universo) if total_zonas_universo > 0 else 0.0
    n_sesiones_con_zonas = len(sesiones_con_zonas_set)

    n_real_first = sum(1 for res in race_results if res["carrera"]["category"] == "real_first")
    n_mirror_first = sum(1 for res in race_results if res["carrera"]["category"] == "mirror_first")
    n_empate_tecnico = sum(1 for res in race_results if res["carrera"]["category"] == "empate_tecnico")
    n_doble_censura = sum(1 for res in race_results if res["carrera"]["category"] == "double_censoring")

    frac_resueltos = (n_real_first + n_mirror_first) / total_zonas_elegibles if total_zonas_elegibles > 0 else 0.0
    frac_doble_censura = n_doble_censura / total_zonas_elegibles if total_zonas_elegibles > 0 else 0.0
    frac_empate_tecnico = n_empate_tecnico / total_zonas_elegibles if total_zonas_elegibles > 0 else 0.0

    n_real_touched_v1 = sum(1 for res in race_results if res["carrera"]["real_lifecycle"]["touched_before_removal"])
    n_mirror_touched_v1 = sum(1 for res in race_results if res["carrera"]["mirror_lifecycle"]["touched_before_removal"])
    frac_real_touched_v1 = n_real_touched_v1 / total_zonas_elegibles if total_zonas_elegibles > 0 else 0.0
    frac_mirror_touched_v1 = n_mirror_touched_v1 / total_zonas_elegibles if total_zonas_elegibles > 0 else 0.0

    residuales = [(res["zona"]["session_date"], res["carrera"]["r_i"]) for res in race_results]
    por_sesion = agregar_por_sesion(residuales)
    r_s_cronologico = [por_sesion[ses] for ses in sorted(por_sesion)]

    ic = hac_bartlett_ic(r_s_cronologico)

    per_session_race_counts = {}
    r_por_lado_por_sesion = {}

    todas_sesiones_investigacion = sorted(info["sesiones_investigacion"])
    for s in todas_sesiones_investigacion:
        res_s = [r for r in race_results if r["zona"]["session_date"] == s]
        all_u_s = [u for u in universo_todas if u["zona"]["session_date"] == s]
        per_session_race_counts[s] = dict(
            n_zonas=len(all_u_s),
            n_elegibles=len(res_s),
            n_real_first=sum(1 for r in res_s if r["carrera"]["category"] == "real_first"),
            n_mirror_first=sum(1 for r in res_s if r["carrera"]["category"] == "mirror_first"),
            n_empate_tecnico=sum(1 for r in res_s if r["carrera"]["category"] == "empate_tecnico"),
            n_doble_censura=sum(1 for r in res_s if r["carrera"]["category"] == "double_censoring"),
            mean_r_s=por_sesion.get(s),
        )
        bull_r = [r["carrera"]["r_i"] for r in race_results if r["zona"]["session_date"] == s and r["zona"]["is_bull"]]
        bear_r = [r["carrera"]["r_i"] for r in race_results if r["zona"]["session_date"] == s and not r["zona"]["is_bull"]]
        r_por_lado_por_sesion[s] = dict(
            mean_r_bull=float(np.mean(bull_r)) if bull_r else None,
            n_bull=len(bull_r),
            mean_r_bear=float(np.mean(bear_r)) if bear_r else None,
            n_bear=len(bear_r),
        )

    etiqueta = decidir_etiqueta_reflexion(
        ic, frac_resueltos, frac_empate_tecnico,
        n_sesiones_con_zonas=n_sesiones_con_zonas, cobertura=cobertura_elegibilidad)

    if n_sesiones_con_zonas != REQUIRED_SOURCE_SESSIONS:
        missing = sorted(set(info["sesiones_investigacion"]) - sesiones_con_zonas_set)
        print(f"GATE FAIL: sesiones con zonas ({n_sesiones_con_zonas}) != {REQUIRED_SOURCE_SESSIONS}.")
        print(f"Sesiones faltantes: {missing}")
        etiqueta = "ABSTAIN_REFLECTION_COVERAGE"

    head_end = git_head()
    dirty_end = git_dirty()
    if dirty_start or dirty_end or head_start != head_end:
        print("ABSTAIN_PROVENANCE: el árbol de trabajo está sucio o HEAD se movió durante la corrida")
        return 5

    payload = dict(
        schema_version=SCHEMA_VERSION,
        status="FORMAL_RUN",
        protocolo="docs/research/BIGTRAP2_LOCAL_REFLECTION_NULL_PROTOCOL_2026-08-12.md",
        spec_path=str(SPEC_PATH.relative_to(REPO_PATH)),
        spec_sha256=SPEC_SHA256_EXPECTED,
        north_star_body_sha256=NORTH_STAR_BODY_SHA256_EXPECTED,
        kernel_sha256=huella_del_codigo([INDICADOR]),
        script_sha256=script_sha256(),
        pip_freeze_sha256=pip_freeze_sha256(),
        sys_prefix=sys.prefix,
        data_file_hashes=file_hashes,
        data_max_timestamps=file_max_timestamps,
        data_max_timestamps_iso=file_max_timestamps_iso,
        firewall_corte_iso=str(corte_utc),
        head_start=head_start,
        head_end=head_end,
        dirty_start=dirty_start,
        dirty_end=dirty_end,
        n_sesiones_con_zonas=n_sesiones_con_zonas,
        required_source_sessions=REQUIRED_SOURCE_SESSIONS,
        n_zonas_universo=total_zonas_universo,
        n_zonas_elegibles=total_zonas_elegibles,
        n_zonas_excluidas=total_zonas_excluidas,
        exclusion_reasons=dict(exclusion_reasons),
        cobertura_elegibilidad=cobertura_elegibilidad,
        cobertura_min_gate=REFLECTION_COVERAGE_MIN,
        cobertura_gate_pass=cobertura_elegibilidad >= REFLECTION_COVERAGE_MIN,
        mde_delta=MDE_DELTA,
        etiqueta=etiqueta,
        estimand_primario=dict(
            delta_reflection=ic["mean"],
            se_hac=ic["se_hac"],
            ci95_lower=ic["ci95_lower"],
            ci95_upper=ic["ci95_upper"],
            mde=ic["mde"],
            hac_lag=ic["lag"],
            n_sessions=ic["n_sessions"],
            abstain_inferencia=ic["abstain_inferencia"],
        ),
        secundarios_declarados=dict(
            binary_touch_before_removal_v1_descriptivo=dict(
                frac_real_touched=frac_real_touched_v1,
                frac_mirror_touched=frac_mirror_touched_v1,
                n_real_touched=n_real_touched_v1,
                n_mirror_touched=n_mirror_touched_v1,
                n_elegibles=total_zonas_elegibles,
            ),
            frac_resueltos=frac_resueltos,
            frac_doble_censura=frac_doble_censura,
            frac_empate_tecnico=frac_empate_tecnico,
            denominadores=dict(
                n_real_first=n_real_first,
                n_mirror_first=n_mirror_first,
                n_empate_tecnico=n_empate_tecnico,
                n_doble_censura=n_doble_censura,
                n_elegibles=total_zonas_elegibles,
            ),
        ),
        diagnostics=dict(
            mirror_overlap_with_other_zones_count=mirror_overlaps_with_other_zones,
            distancia_ticks_distribution=dict(
                min=int(min(distancias_elegibles)) if distancias_elegibles else None,
                p25=float(np.percentile(distancias_elegibles, 25)) if distancias_elegibles else None,
                p50=float(np.percentile(distancias_elegibles, 50)) if distancias_elegibles else None,
                p75=float(np.percentile(distancias_elegibles, 75)) if distancias_elegibles else None,
                max=int(max(distancias_elegibles)) if distancias_elegibles else None,
                frac_le_2=float((np.array(distancias_elegibles) <= 2).mean()) if distancias_elegibles else None,
                frac_le_3=float((np.array(distancias_elegibles) <= 3).mean()) if distancias_elegibles else None,
                frac_le_5=float((np.array(distancias_elegibles) <= 5).mean()) if distancias_elegibles else None,
            ) if distancias_elegibles else None,
            per_session_race_counts=per_session_race_counts,
            r_por_lado_por_sesion=r_por_lado_por_sesion,
        ),
        por_sesion=por_sesion,
        outcomes_accessed=False,
    )

    payload_raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    payload_sha256 = hashlib.sha256(payload_raw).hexdigest()
    payload["payload_sha256"] = payload_sha256

    out_filename = f"F2.7_formal_{payload_sha256[:12]}.json"
    out_path = REPO_PATH / "diag" / "tasa_senales" / out_filename
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n[CORRIDA FORMAL REPORTE]")
    print(f"Artefacto: {out_path}")
    print(f"Etiqueta: {etiqueta}")
    print(f"Delta_reflection: {ic['mean']} (SE_HAC: {ic['se_hac']}, IC95: [{ic['ci95_lower']}, {ic['ci95_upper']}])")
    print(f"Sesiones con zonas: {n_sesiones_con_zonas} / {REQUIRED_SOURCE_SESSIONS}")
    print(f"Payload SHA256: {payload_sha256}")
    return 0


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
    3) <data_root().parent>/.venv (entorno gobernado de datos)
    """
    if sys.prefix == sys.base_prefix:
        print("ABSTAIN_PROVENANCE: no se está ejecutando dentro de un entorno virtual (.venv)")
        return False

    prefix_path = Path(sys.prefix).resolve()
    local_venv = (REPO_PATH / ".venv").resolve()
    main_venv = (main_checkout_path() / ".venv").resolve()

    try:
        data_venv = (data_root().parent / ".venv").resolve()
    except Exception:
        data_venv = None

    permitidos = {local_venv, main_venv}
    if data_venv is not None:
        permitidos.add(data_venv)

    if prefix_path in permitidos:
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
    parser.add_argument("--formal", action="store_true",
                        help="Ejecución formal adjudicadora de 201 sesiones")
    args = parser.parse_args(argv)

    if not validar_entorno_venv():
        return 2

    if args.formal:
        return correr_formal()

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

