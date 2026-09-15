#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/build_hp007_preregistration.py
====================================
FASE 3: Preregistro inmutable de la campaña formal HP007-CAMP-001 y Ledger de Variantes.
Fija la métrica primaria única, grilla congelada, N_eff y separación de parámetros.
"""

import json
import hashlib
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
OUT_MANIFEST = REPO_DIR / "docs" / "research" / "HP007_CAMPAIGN_PREREGISTRATION_2026-09-15.json"
OUT_LEDGER = REPO_DIR / "docs" / "research" / "HP007_VARIANTS_LEDGER_2026-09-15.json"

def canonical_sha256(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def main():
    # 1. Manifiesto Principal de la Campaña
    manifest = {
        "schema_version": "hp007_campaign_manifest_v1",
        "campaign_id": "HP007-CAMP-001",
        "fecha_preregistro": "2026-09-15T17:50:00Z",
        "rama": "work/hp007-causal-campaign-v1-20260915",
        "base_commit": "20f2de397db7427893630bc626c4d4966b1122cf",
        "autor": "Nico del Campo / EdgeLab Causal Research",
        "metrica_primaria_unica": "delta_net_R = mean_session(net_R_corridor - net_R_control_matched)",
        "regla_de_rechazo_critica": "Si control_mean_net_R >= corridor_mean_net_R -> FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL",
        "activos_aptos_certificados": ["6E 03-26", "6E 06-26"],
        "cross_asset_continuo_status": "ABSTAIN (Certificación previous_complete_session_volume_leader_monotonic_v1 pendiente)",
        "firewall_holdout": {
            "fecha_corte": "2026-07-01T00:00:00Z",
            "estado": "SEALED_UNTOUCHED",
            "guard_module": "edgelab.research.holdout_guard"
        },
        "headline_specification": {
            "definition": {
                "forward_density_max": 0.28,
                "backstop_density_min": 0.70,
                "min_width_ticks": 4,
                "max_width_ticks": 7
            },
            "target_ticks": 10,
            "stop_ticks": 3,
            "horizon_ns": 3600_000_000_000,
            "cooldown_ns": 60_000_000_000,
            "friction_scenario": "base",
            "friction_ticks_round_turn": 2.768,
            "n_eff_declared": 29
        }
    }

    manifest["manifest_sha256"] = canonical_sha256(manifest)

    # 2. Ledger Completo de Variantes
    variants = []
    
    forward_thresholds = [
        ("V1_HEADLINE", 0.28, "Observado previamente en análisis exploratorio 6E"),
        ("V2_PERMISIVO", 0.35, "Exploración de umbral más relajado"),
        ("V3_ESTRICTO", 0.20, "Exploración de vacío puro de ultrabaja fricción")
    ]
    
    backstop_thresholds = [
        ("B1_BACKSTOP_HEADLINE", 0.70, "Pared protectora densa a la espalda observada previamente"),
        ("B2_SIN_BACKSTOP", 0.00, "Corredor agnóstico sin restricción de espalda"),
        ("B3_BACKSTOP_MODERADO", 0.50, "Pared protectora intermedia")
    ]
    
    width_intervals = [
        ("W1_ANGOSTO_4_7", 4, 7, "Punto dulce observado en dinamica pared a pared"),
        ("W2_MEDIO_8_14", 8, 14, "Corredores medianos de travesía amplia"),
        ("W3_COMBINADO_4_14", 4, 14, "Rango completo operable")
    ]
    
    target_stop_configs = [
        ("TS1_HEADLINE_10_3", 10, 3, 3.33, "Ratio R:R 3.33:1 exploratorio original"),
        ("TS2_AJUSTADO_6_3", 6, 3, 2.00, "Ratio R:R 2.0:1 para corredores angostos")
    ]

    var_id = 1
    for v_name, v_fwd, v_desc in forward_thresholds:
        for b_name, b_bsp, b_desc in backstop_thresholds:
            for w_name, w_min, w_max, w_desc in width_intervals:
                for ts_name, t_t, s_t, rr, ts_desc in target_stop_configs:
                    is_headline = (v_name == "V1_HEADLINE" and b_name == "B1_BACKSTOP_HEADLINE" and w_name == "W1_ANGOSTO_4_7" and ts_name == "TS1_HEADLINE_10_3")
                    variants.append({
                        "variant_id": f"VAR_{var_id:03d}",
                        "is_headline": is_headline,
                        "tipo": "EXPLORATORIA_PREVIA" if is_headline else "NUEVA_ESTRUCTURAL",
                        "forward_density_max": v_fwd,
                        "backstop_density_min": b_bsp,
                        "min_width_ticks": w_min,
                        "max_width_ticks": w_max,
                        "target_ticks": t_t,
                        "stop_ticks": s_t,
                        "rr_ratio": rr,
                        "cooldown_ns": 60_000_000_000,
                        "horizon_ns": 3600_000_000_000,
                        "status": "PREREGISTERED_LOCKED"
                    })
                    var_id += 1

    ledger = {
        "schema_version": "hp007_variants_ledger_v1",
        "campaign_id": "HP007-CAMP-001",
        "n_total_variants": len(variants),
        "n_eff_declared": 29,
        "metodologia_n_eff": "Cheverud-Nyholt estimador sobre matriz de correlacion cruzada de contrastes de grilla",
        "separacion_parametros": {
            "mecanicos": ["forward_density_max", "backstop_density_min", "min_width_ticks", "max_width_ticks", "cooldown_ns"],
            "economicos": ["target_ticks", "stop_ticks", "friction_ticks_round_turn"],
            "heredados_exploratorios": ["0.28", "0.70", "ancho 4-7", "stop 3", "target 10"]
        },
        "variantes": variants
    }
    ledger["ledger_sha256"] = canonical_sha256(ledger)

    with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifiesto guardado en {OUT_MANIFEST} (SHA256: {manifest['manifest_sha256'][:16]}...)")

    with open(OUT_LEDGER, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)
    print(f"Ledger guardado en {OUT_LEDGER} ({len(variants)} variantes, SHA256: {ledger['ledger_sha256'][:16]}...)")

if __name__ == "__main__":
    main()
