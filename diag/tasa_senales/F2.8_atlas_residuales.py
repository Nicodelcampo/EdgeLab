# -*- coding: utf-8 -*-
"""F2.8 — Atlas de distancia, ancla, cobertura y residuales.

Pregunta pre-registrada (docs/research/BIGTRAP2_F28_DISTANCE_COVERAGE_PROTOCOL_2026-08-13.md,
spec specs/bigtrap2_f28_distance_coverage_v0.json):
Localizar dónde vive la asimetría de F2.7, qué objeto la produce y qué residual queda
explotable si la atracción de zona no es el mecanismo.

Familias:
  A: Landscape de distancia Δ(d) (d<=2, 3<=d<=5, d>=6, d>3, d>5, global)
  B: Controles de barra creadora (matched_geometry_nontrap, placebo_same_bar_rotated)
  C: Ocupación activa precio x tiempo y colocaciones aleatorias (semilla 20260813)
  D: Residuales y etiquetado de decisión (decide_labels)
  E: Interrupción geométrica estilo Osler (through / bounce / stay, h=5)

Target-free. Sin P&L, sin retornos, sin dirección, sin holdout, sin tick:25.
`outcomes_accessed=False`.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

# Import F2.7 runner via importlib
_F27_PATH = REPO_PATH / "diag" / "tasa_senales" / "F2.7_nulo_reflexion_local.py"
_f27_spec = importlib.util.spec_from_file_location("f27_nrl", _F27_PATH)
f27 = importlib.util.module_from_spec(_f27_spec)
sys.modules["f27_nrl"] = f27
_f27_spec.loader.exec_module(f27)

construir_universo_zonas = f27.construir_universo_zonas
construir_reflejo = f27.construir_reflejo
first_passage_race = f27.first_passage_race
zone_lifecycle = f27.zone_lifecycle
agregar_por_sesion = f27.agregar_por_sesion
hac_bartlett_ic = f27.hac_bartlett_ic
dias_research = f27.dias_research
data_root = f27.data_root
git_head = f27.git_head
git_dirty = f27.git_dirty
north_star_body_sha256 = f27.north_star_body_sha256
corte_del_sello = f27.corte_del_sello
parquet_file_sha256 = f27.parquet_file_sha256
pip_freeze_sha256 = f27.pip_freeze_sha256
script_sha256 = f27.script_sha256
resolver_empate_por_tick = f27.resolver_empate_por_tick
construir_bar_start_ends = f27.construir_bar_start_ends
MAX_AGE_BARS = f27.MAX_AGE_BARS
INVALIDATION_MODE = f27.INVALIDATION_MODE
MAX_TOUCHES = f27.MAX_TOUCHES
INDICADOR = f27.INDICADOR
BAR_DRIVEN = f27.BAR_DRIVEN
REGISTRY = f27.REGISTRY
TZ_CHART = f27.TZ_CHART
LEAD_DAYS = f27.LEAD_DAYS
bars_mod = f27.bars_mod
ticks_mod = f27.ticks_mod
pd = f27.pd
sesiones_de_barras = f27.sesiones_de_barras
session_date_ct = f27.session_date_ct

from edgelab.research.f28.controls import (  # noqa: E402
    eligible_control, match_nontrap_bar, same_side_interval,
)
from edgelab.research.f28.interruption import classify_after_contact  # noqa: E402
from edgelab.research.f28.residual_atlas import (  # noqa: E402
    decide_labels, distance_stratum, isolated, occupancy_union, support_ok,
)

SCHEMA_VERSION = "bigtrap2_f28_distance_coverage_v0"
NORTH_STAR_BODY_SHA256_EXPECTED = (
    "d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1"
)
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_f28_distance_coverage_v0.json"
RESEARCH_END_INCLUSIVE = "2026-06-30"

REQUIRED_SOURCE_SESSIONS = 201
F27_EXPECTED_ZONES_ELIGIBLE = 15947
F27_EXPECTED_DELTA = 0.04815265363200558
REFLECTION_COVERAGE_MIN = 0.95
RESOLUTION_RATE_MIN_GLOBAL = 0.30
TECHNICAL_TIES_MAX = 0.01

PARQUET_HASHES_EXPECTED = {
    "6E_12-25_ticks.parquet": "ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336",
    "6E_03-26_ticks.parquet": "b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76",
    "6E_06-26_ticks.parquet": "124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1",
    "6E_09-26_ticks.parquet": "6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4",
}


def spec_sha256() -> str:
    raw = SPEC_PATH.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def compute_cut_metrics(pairs_list):
    """Computes HAC statistics for a list of (session_date, r_i) pairs."""
    if not pairs_list:
        return dict(
            n_zones=0,
            n_sessions=0,
            n_resolved=0,
            frac_resolved=0.0,
            delta=0.0,
            se_hac=0.0,
            ci95_lower=0.0,
            ci95_upper=0.0,
            mde_observed=0.0,
            real_first=0,
            mirror_first=0,
            double_censor=0,
        )

    by_session = {}
    r_counts = Counter()
    for s_date, r_i, cat in pairs_list:
        by_session.setdefault(s_date, []).append(r_i)
        if cat == "real_first":
            r_counts["real_first"] += 1
        elif cat == "mirror_first":
            r_counts["mirror_first"] += 1
        else:
            r_counts["double_censor"] += 1

    n_zones = len(pairs_list)
    n_resolved_pairs = r_counts["real_first"] + r_counts["mirror_first"]
    frac_resolved = n_resolved_pairs / n_zones if n_zones > 0 else 0.0

    # Session-equal-weighted means for sessions with at least 1 resolved pair
    session_means = []
    for s_date, r_list in sorted(by_session.items()):
        resolved = [r for r in r_list if r != 0.0]
        if resolved:
            session_means.append(float(np.mean(resolved)))

    if not session_means:
        return dict(
            n_zones=n_zones,
            n_sessions=0,
            n_resolved=0,
            frac_resolved=frac_resolved,
            delta=0.0,
            se_hac=0.0,
            ci95_lower=0.0,
            ci95_upper=0.0,
            mde_observed=0.0,
            real_first=r_counts["real_first"],
            mirror_first=r_counts["mirror_first"],
            double_censor=r_counts["double_censor"],
        )

    ic = hac_bartlett_ic(session_means)
    mde = 1.96 * ic["se_hac"]

    return dict(
        n_zones=n_zones,
        n_sessions=len(session_means),
        n_resolved=n_resolved_pairs,
        frac_resolved=frac_resolved,
        delta=ic["media"],
        se_hac=ic["se_hac"],
        ci95_lower=ic["ci95_lower"],
        ci95_upper=ic["ci95_upper"],
        mde_observed=mde,
        real_first=r_counts["real_first"],
        mirror_first=r_counts["mirror_first"],
        double_censor=r_counts["double_censor"],
    )


def correr_formal_f28():
    head_start = git_head()
    dirty_start = git_dirty()
    if dirty_start:
        print("ABSTAIN_PROVENANCE: el árbol de trabajo está sucio antes de empezar la corrida formal")
        return 5, None

    ns_hash = north_star_body_sha256()
    if ns_hash != NORTH_STAR_BODY_SHA256_EXPECTED:
        print(f"ABSTAIN_PROVENANCE: hash de NORTH_STAR.md no coincide ({ns_hash} != {NORTH_STAR_BODY_SHA256_EXPECTED})")
        return 3, None

    print("=== F2.8 CORRIDA FORMAL (201 SESIONES) ===")
    dias, info = dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]

    corte_utc = corte_del_sello()
    corte_utc_ns = int(corte_utc.value)

    # Check parquet hashes
    for arch, _ in plan:
        pq_path = data_root() / "nt8" / "6E" / arch
        if not pq_path.exists():
            print(f"ABSTAIN_PROVENANCE: archivo no encontrado: {pq_path}")
            return 6, None
        h_actual = parquet_file_sha256(pq_path)
        h_expected = PARQUET_HASHES_EXPECTED.get(arch)
        if h_expected and h_actual != h_expected:
            print(f"ABSTAIN_PROVENANCE: hash de {arch} no coincide ({h_actual} != {h_expected})")
            return 7, None

    total_zonas_universo = 0
    total_zonas_elegibles = 0

    # Collections across all 201 sessions
    zone_pairs_by_cut = {
        "d<=2": [],
        "3<=d<=5": [],
        "d>=6": [],
        "d>3": [],
        "d>5": [],
        "global": [],
    }

    # Controls tracking
    control1_pairs_by_cut = {k: [] for k in zone_pairs_by_cut}
    control2_pairs_by_cut = {k: [] for k in zone_pairs_by_cut}
    matched_control1_count_by_cut = Counter()
    matched_control2_count_by_cut = Counter()

    # Active occupancy tracking per session
    session_occupancy_visited = []
    session_occupancy_range = []
    session_isolated_active_instances = 0
    session_total_active_instances = 0
    session_random_occupancy_visited = []

    # Interruption tracking
    interruption_bt2_counts = Counter()

    rng = np.random.default_rng(20260813)

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
        tk = ticks_mod.load_canonical_parquet(
            str(pq_path), start_utc_ns=int(ini.value), end_utc_ns=int(fin.value)
        )

        max_ts = int(np.max(tk.ts_ns))
        assert max_ts < corte_utc_ns, f"FIREWALL VIOLATED in {arch}: max ts {max_ts} >= {corte_utc_ns}"

        b = bars_mod.build_time_bars(tk, 1)
        bar_end = np.asarray(b.end_ns)
        high_t = np.asarray(b.high_t)
        low_t = np.asarray(b.low_t)
        close_t = np.asarray(b.close_t)
        bar_start_ns = np.asarray(b.start_ns)

        fp = bars_mod.build_footprints(tk, b) if INDICADOR in BAR_DRIVEN else None
        mod = REGISTRY[INDICADOR]
        r = mod.run(tk, b, fp, chart_tz=TZ_CHART) if fp is not None else mod.run(tk, b, chart_tz=TZ_CHART)
        kernel_zones = r.get("zones") or []

        fechas_disponibles = sorted(set(session_date_ct(int(ns // 1_000_000)) for ns in b.start_ns))
        ses_de_barra, rango_sesion = sesiones_de_barras(bar_end, fechas_disponibles)

        universo, creadoras = construir_universo_zonas(
            kernel_zones, ses_de_barra, rango_sesion, fechas_research, tk.tick_size, len(b)
        )
        total_zonas_universo += len(universo)

        tk_ts_ns = np.asarray(tk.ts_ns)
        tk_price_ticks = np.asarray(tk.price_ticks, dtype=np.int64)
        bar_starts_ends = construir_bar_start_ends(tk_ts_ns, bar_start_ns, bar_end)

        # Process by session
        universo_by_session = {}
        for z in universo:
            universo_by_session.setdefault(z["session_date"], []).append(z)

        for s_date in fechas_research:
            if s_date not in rango_sesion:
                continue
            idx0, idx1 = rango_sesion[s_date]
            zonas_s = universo_by_session.get(s_date, [])
            if not zonas_s:
                continue

            session_min_tick = int(np.min(low_t[idx0 : idx1 + 1]))
            session_max_tick = int(np.max(high_t[idx0 : idx1 + 1]))
            session_range_span = max(1, session_max_tick - session_min_tick + 1)

            zone_active_info = []
            occupied_by_bar = {}
            creator_bars = set()

            for z in zonas_s:
                reflejo = construir_reflejo(z, close_t)
                cb = z["created_bar"]
                creator_bars.add(cb)
                lo, hi = z["lo_tick"], z["hi_tick"]

                if not reflejo["is_eligible"]:
                    continue

                total_zonas_elegibles += 1

                race = first_passage_race(
                    z, reflejo, cb, high_t, low_t, close_t, len(b),
                    tk_price_ticks=tk_price_ticks, bar_start_ends=bar_starts_ends
                )

                real_lc = race["real_lifecycle"]
                touch_age = real_lc["first_touch_age"] if real_lc["touched_before_removal"] and real_lc["first_touch_age"] is not None else 999999
                rem_age = real_lc["removed_age"] if real_lc["removed_age"] is not None else 999999
                horiz_age = race["horizon_cap"]
                active_bars_count = min(touch_age, rem_age, horiz_age)
                removal_bar = cb + active_bars_count

                info = dict(
                    zona=z,
                    reflejo=reflejo,
                    race=race,
                    cb=cb,
                    removal_bar=removal_bar,
                    lo=lo,
                    hi=hi,
                    d=reflejo["distance_ticks"],
                    w=reflejo["width_ticks"],
                    is_bull=z["is_bull"],
                )
                zone_active_info.append(info)

                for bar_idx in range(cb, removal_bar + 1):
                    occupied_by_bar.setdefault(bar_idx, []).append((lo, hi))

            if not zone_active_info:
                continue

            nontrap_bars = [bar_i for bar_i in range(idx0, idx1 + 1) if bar_i not in creator_bars]

            for info in zone_active_info:
                z = info["zona"]
                reflejo = info["reflejo"]
                race = info["race"]
                d = info["d"]
                w = info["w"]
                cb = info["cb"]
                is_bull = info["is_bull"]
                r_i = race["r_i"]
                cat = race["category"]

                # Distance strata
                cuts = []
                stratum = distance_stratum(d)
                cuts.append(stratum)
                if d > 3:
                    cuts.append("d>3")
                if d > 5:
                    cuts.append("d>5")
                cuts.append("global")

                for c in cuts:
                    zone_pairs_by_cut[c].append((s_date, r_i, cat))

                # --- CONTROL 1: matched_geometry_nontrap ---
                qualifying_nontrap_bars = []
                for b_ctrl in nontrap_bars:
                    anchor_ctrl = close_t[b_ctrl]
                    lo_c, hi_c = same_side_interval(anchor_ctrl, d, w, is_bull)
                    occupied = occupied_by_bar.get(b_ctrl, [])
                    if eligible_control(anchor_ctrl, lo_c, hi_c, occupied):
                        qualifying_nontrap_bars.append(b_ctrl)

                matched_b1 = match_nontrap_bar(qualifying_nontrap_bars, cb, occupied_by_bar)
                if matched_b1 is not None:
                    anchor_c1 = close_t[matched_b1]
                    lo_c1, hi_c1 = same_side_interval(anchor_c1, d, w, is_bull)
                    z_ctrl1 = dict(
                        lo_tick=lo_c1, hi_tick=hi_c1, is_bull=is_bull, created_bar=matched_b1
                    )
                    ref_ctrl1 = construir_reflejo(z_ctrl1, close_t)
                    if ref_ctrl1["is_eligible"]:
                        race_c1 = first_passage_race(
                            z_ctrl1, ref_ctrl1, matched_b1, high_t, low_t, close_t, len(b),
                            tk_price_ticks=tk_price_ticks, bar_start_ends=bar_starts_ends
                        )
                        for c in cuts:
                            control1_pairs_by_cut[c].append((s_date, race_c1["r_i"], race_c1["category"]))
                            matched_control1_count_by_cut[c] += 1

                # --- CONTROL 2: placebo_same_bar_rotated ---
                lo_c2, hi_c2 = (lo + w + 1, hi + w + 1) if is_bull else (lo - w - 1, hi - w - 1)
                occupied_cb = occupied_by_bar.get(cb, [])
                anchor_cb = close_t[cb]
                if eligible_control(anchor_cb, lo_c2, hi_c2, occupied_cb):
                    z_ctrl2 = dict(
                        lo_tick=lo_c2, hi_tick=hi_c2, is_bull=is_bull, created_bar=cb
                    )
                    ref_ctrl2 = construir_reflejo(z_ctrl2, close_t)
                    if ref_ctrl2["is_eligible"]:
                        race_c2 = first_passage_race(
                            z_ctrl2, ref_ctrl2, cb, high_t, low_t, close_t, len(b),
                            tk_price_ticks=tk_price_ticks, bar_start_ends=bar_starts_ends
                        )
                        for c in cuts:
                            control2_pairs_by_cut[c].append((s_date, race_c2["r_i"], race_c2["category"]))
                            matched_control2_count_by_cut[c] += 1

                # --- FAMILY E: Interruption ---
                real_lc = race["real_lifecycle"]
                if real_lc["touched_before_removal"]:
                    b_contact = cb + real_lc["first_touch_age"]
                    inter_outcome = classify_after_contact(
                        reflejo["anchor_tick"], info["lo"], info["hi"], is_bull,
                        b_contact, close_t, high_t, low_t, len(b), h=5
                    )
                    interruption_bt2_counts[inter_outcome] += 1

            # --- FAMILY C: Active Occupancy calculation for session ---
            bar_visited_fracs = []
            bar_range_fracs = []
            session_active_count = 0
            session_isolated_count = 0

            for bar_i in range(idx0, idx1 + 1):
                active_intervals = [(inf["lo"], inf["hi"]) for inf in zone_active_info
                                    if inf["cb"] < bar_i <= inf["removal_bar"]]

                if not active_intervals:
                    bar_visited_fracs.append(0.0)
                    bar_range_fracs.append(0.0)
                    continue

                b_lo, b_hi = int(low_t[bar_i]), int(high_t[bar_i])
                b_span = max(1, b_hi - b_lo + 1)

                intersected = []
                for lo_a, hi_a in active_intervals:
                    i_lo = max(lo_a, b_lo)
                    i_hi = min(hi_a, b_hi)
                    if i_hi >= i_lo:
                        intersected.append((i_lo, i_hi))

                visited_covered = occupancy_union(intersected)
                bar_visited_fracs.append(visited_covered / b_span)

                range_covered = occupancy_union(active_intervals)
                bar_range_fracs.append(range_covered / session_range_span)

                for i_idx, z_int in enumerate(active_intervals):
                    others = active_intervals[:i_idx] + active_intervals[i_idx + 1:]
                    session_active_count += 1
                    if isolated(z_int, others):
                        session_isolated_count += 1

            s_vis_frac = float(np.mean(bar_visited_fracs)) if bar_visited_fracs else 0.0
            s_rng_frac = float(np.mean(bar_range_fracs)) if bar_range_fracs else 0.0

            session_occupancy_visited.append(s_vis_frac)
            session_occupancy_range.append(s_rng_frac)
            session_isolated_active_instances += session_isolated_count
            session_total_active_instances += session_active_count

            # Random Occupancy Control (200 draws per session)
            random_draw_visited = []
            for _ in range(200):
                rnd_zone_info = []
                for inf in zone_active_info:
                    w_z = inf["w"]
                    max_start = max(session_min_tick, session_max_tick - w_z)
                    r_lo = int(rng.integers(session_min_tick, max_start + 1))
                    r_hi = r_lo + w_z
                    rnd_zone_info.append((inf["cb"], inf["removal_bar"], r_lo, r_hi))

                draw_bar_fracs = []
                for bar_i in range(idx0, idx1 + 1):
                    rnd_active = [(r_lo, r_hi) for cb_z, rem_z, r_lo, r_hi in rnd_zone_info
                                  if cb_z < bar_i <= rem_z]
                    if not rnd_active:
                        draw_bar_fracs.append(0.0)
                        continue
                    b_lo, b_hi = int(low_t[bar_i]), int(high_t[bar_i])
                    b_span = max(1, b_hi - b_lo + 1)
                    rnd_intersected = [(max(lo_a, b_lo), min(hi_a, b_hi))
                                       for lo_a, hi_a in rnd_active if min(hi_a, b_hi) >= max(lo_a, b_lo)]
                    draw_bar_fracs.append(occupancy_union(rnd_intersected) / b_span)

                random_draw_visited.append(float(np.mean(draw_bar_fracs)))

            session_random_occupancy_visited.append(float(np.mean(random_draw_visited)))

    # --- Verify Step 1: Reproduction of F2.7 Totals ---
    global_metrics = compute_cut_metrics(zone_pairs_by_cut["global"])
    n_sessions_global = global_metrics["n_sessions"]
    n_zones_eligible_global = global_metrics["n_zones"]
    delta_global = global_metrics["delta"]

    print("\n=== STEP 1: Reproducción de Totales F2.7 ===")
    print(f"Sesiones con soporte: {n_sessions_global} (esperado {REQUIRED_SOURCE_SESSIONS})")
    print(f"Zonas elegibles: {n_zones_eligible_global} (esperado {F27_EXPECTED_ZONES_ELIGIBLE})")
    print(f"Δ global: {delta_global:.6f} (esperado ~{F27_EXPECTED_DELTA:.6f})")

    reproduced_ok = (
        n_sessions_global == REQUIRED_SOURCE_SESSIONS
        and n_zones_eligible_global == F27_EXPECTED_ZONES_ELIGIBLE
        and abs(delta_global - F27_EXPECTED_DELTA) < 1e-4
    )
    if not reproduced_ok:
        print("FAIL-CLOSED: La reproducción de totales F2.7 difiere de lo esperado.")
        return 8, None

    # --- STEP 2: Family A - Landscape de Distancia Δ(d) ---
    print("\n=== STEP 2: Familia A - Landscape de Distancia Δ(d) ===")
    strata_results = {}
    all_cuts = ["d<=2", "3<=d<=5", "d>=6", "d>3", "d>5", "global"]
    for c in all_cuts:
        strata_results[c] = compute_cut_metrics(zone_pairs_by_cut[c])
        res = strata_results[c]
        print(
            f"  Corte {c:7s}: n={res['n_zones']:5d}, n_ses={res['n_sessions']:3d}, "
            f"resuelto={res['frac_resolved']:.3f}, Δ={res['delta']:+.4f}, "
            f"IC95=[{res['ci95_lower']:+.4f}, {res['ci95_upper']:+.4f}]"
        )

    # --- STEP 3: Family C - Active Occupancy ---
    print("\n=== STEP 3: Familia C - Ocupación Activa Precio x Tiempo ===")
    p50_visited = float(np.percentile(session_occupancy_visited, 50))
    p90_visited = float(np.percentile(session_occupancy_visited, 90))
    p50_range = float(np.percentile(session_occupancy_range, 50))
    isolated_rate = (
        session_isolated_active_instances / session_total_active_instances
        if session_total_active_instances > 0 else 0.0
    )
    random_p50_visited = float(np.percentile(session_random_occupancy_visited, 50))

    print(f"  Ocupación visitada p50: {p50_visited:.4f}")
    print(f"  Ocupación visitada p90: {p90_visited:.4f}")
    print(f"  Ocupación rango p50:    {p50_range:.4f}")
    print(f"  Tasa de aislamiento:    {isolated_rate:.4f}")
    print(f"  Control aleatorio p50:  {random_p50_visited:.4f}")

    # --- STEP 4: Family B - Creator-Bar Controls ---
    print("\n=== STEP 4: Familia B - Controles de Barra Creadora ===")
    bt2_minus_control = {}
    match_rates = {}

    for c in all_cuts:
        n_z = strata_results[c]["n_zones"]
        n_c1 = matched_control1_count_by_cut[c]
        match_rate1 = n_c1 / n_z if n_z > 0 else 0.0
        match_rates[c] = match_rate1

        if match_rate1 < 0.40:
            bt2_minus_control[c] = dict(
                abstained=True,
                reason="low_match_rate",
                match_rate=match_rate1,
                ci95_lower=0.0,
                ci95_upper=0.0,
                delta_diff=0.0,
            )
            print(f"  Corte {c:7s}: ABSTAIN contrast (match_rate={match_rate1:.3f} < 0.40)")
        else:
            ctrl_res = compute_cut_metrics(control1_pairs_by_cut[c])
            diff = strata_results[c]["delta"] - ctrl_res["delta"]
            se_diff = math.sqrt(strata_results[c]["se_hac"] ** 2 + ctrl_res["se_hac"] ** 2)
            ci_lo = diff - 1.96 * se_diff
            ci_hi = diff + 1.96 * se_diff
            bt2_minus_control[c] = dict(
                abstained=False,
                match_rate=match_rate1,
                delta_bt2=strata_results[c]["delta"],
                delta_ctrl=ctrl_res["delta"],
                delta_diff=diff,
                se_hac=se_diff,
                ci95_lower=ci_lo,
                ci95_upper=ci_hi,
            )
            print(
                f"  Corte {c:7s}: match_rate={match_rate1:.3f}, Δ_BT2-Δ_ctrl={diff:+.4f}, "
                f"IC95=[{ci_lo:+.4f}, {ci_hi:+.4f}]"
            )

    # --- STEP 5: Family E - Interruption Geometry ---
    print("\n=== STEP 5: Familia E - Interrupción Geométrica estilo Osler ===")
    total_interrupted_touches = sum(interruption_bt2_counts.values())
    through_count = interruption_bt2_counts["through"]
    bounce_count = interruption_bt2_counts["bounce"]
    stay_count = interruption_bt2_counts["stay"]

    through_rate = through_count / total_interrupted_touches if total_interrupted_touches > 0 else 0.0
    bounce_rate = bounce_count / total_interrupted_touches if total_interrupted_touches > 0 else 0.0
    stay_rate = stay_count / total_interrupted_touches if total_interrupted_touches > 0 else 0.0

    print(f"  Toques evaluados para interrupción: {total_interrupted_touches}")
    print(f"  Through (atraviesa): {through_count} ({through_rate:.3f})")
    print(f"  Bounce (rebota):    {bounce_count} ({bounce_rate:.3f})")
    print(f"  Stay (permanece):   {stay_count} ({stay_rate:.3f})")

    net_interruption_diff = bounce_rate - through_rate
    se_inter = math.sqrt(
        (bounce_rate * (1 - bounce_rate) + through_rate * (1 - through_rate))
        / max(1, total_interrupted_touches)
    )
    inter_ci_lo = net_interruption_diff - 1.96 * se_inter
    inter_ci_hi = net_interruption_diff + 1.96 * se_inter

    interruption_report = dict(
        evaluated_touches=total_interrupted_touches,
        through_rate=through_rate,
        bounce_rate=bounce_rate,
        stay_rate=stay_rate,
        net_diff=net_interruption_diff,
        ci95_lower=inter_ci_lo,
        ci95_upper=inter_ci_hi,
    )

    # --- STEP 6: Family D & Decision Labels ---
    print("\n=== STEP 6: Familia D & Etiquetas de Decisión ===")

    fade_cuts = {
        c: dict(
            n_sessions=strata_results[c]["n_sessions"],
            n_resolved=strata_results[c]["n_resolved"],
            ci95_upper=strata_results[c]["ci95_upper"],
        )
        for c in all_cuts
    }

    report_for_decision = {
        "strata": strata_results,
        "bt2_minus_control": bt2_minus_control,
        "occupancy": {
            "p50_visited": p50_visited,
            "p90_visited": p90_visited,
            "p50_range": p50_range,
            "isolated_rate": isolated_rate,
        },
        "holes": {"first_passage_edge": False},
        "fade_cuts": fade_cuts,
        "interruption": interruption_report,
        "global": strata_results["global"],
        "underpowered": False,
    }

    decision_labels = decide_labels(report_for_decision)
    print(f"  Etiquetas de decisión encendidas: {decision_labels}")

    # Build final summary payload
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "FORMAL_RUN_COMPLETE",
        "head_start": head_start,
        "head_end": git_head(),
        "dirty_start": dirty_start,
        "dirty_end": git_dirty(),
        "north_star_body_sha256": ns_hash,
        "spec_sha256": spec_sha256(),
        "reproduced_f27_totals": reproduced_ok,
        "global_metrics": strata_results["global"],
        "family_a_landscape": strata_results,
        "family_b_controls": bt2_minus_control,
        "family_c_occupancy": {
            "p50_visited": p50_visited,
            "p90_visited": p90_visited,
            "p50_range": p50_range,
            "isolated_rate": isolated_rate,
            "random_p50_visited": random_p50_visited,
        },
        "family_e_interruption": interruption_report,
        "family_d_decision_labels": decision_labels,
        "outcomes_accessed": False,
        "pnl_accessed": False,
    }

    def make_serializable(obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(x) for x in obj]
        return obj

    serializable_payload = make_serializable(payload)
    payload_json = json.dumps(serializable_payload, indent=2, sort_keys=True)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:12]
    out_json_path = REPO_PATH / "diag" / "tasa_senales" / f"F2.8_formal_{payload_hash}.json"
    out_json_path.write_text(payload_json, encoding="utf-8")
    print(f"\nArtefacto formal guardado en: {out_json_path}")

    return 0, serializable_payload


def main():
    parser = argparse.ArgumentParser(description="F2.8 Atlas de distancia, ancla, cobertura y residuales.")
    parser.add_argument("--formal", action="store_true", help="Ejecutar corrida formal de 201 sesiones")
    parser.add_argument("--smoke-archivo", type=str, help="Ejecutar smoke estructural sobre un parquet")
    args = parser.parse_args()

    if args.formal:
        code, _ = correr_formal_f28()
        sys.exit(code)
    elif args.smoke_archivo:
        payload = f27.smoke_estructural(args.smoke_archivo, solo_estructural=True)
        print("\nSmoke estructural F2.8 completado.")
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
