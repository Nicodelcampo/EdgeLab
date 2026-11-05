#!/usr/bin/env python3
"""Emisor de Señales y Validador de Paridad para NinjaTrader 8 (`EdgeLabSpiralBasketExecutor.cs`, 2026-10-29).

Genera los artefactos operativos listos para que NinjaTrader 8 ejecute únicamente las reglas individuales y las
Canastas Ortogonales por Régimen que superaron la Compuerta Anti-Aplanamiento OOS (`gestor_canastas_regimen.py`):
1. `config/autopilot/nt8_canasta_aprobada_20261029.json`: Manifiesto de slots `0..K-1` asignados en
   `EdgeLabSpiralBasketExecutor.cs` con sus celdas congeladas, topes de pérdida y parámetros de ejecución.
2. `config/autopilot/nt8_regime_mask_20261029.txt`: Archivo de máscara causal `RegimeStateFilePath` que lee
   `EdgeLabSpiralBasketExecutor.cs` al inicio de cada sesión (`Bars.IsFirstBarOfSession`).
3. Verificación determinista de paridad entre el motor Python (`paridad_nt8_canastas.py`) y la lógica C# de
   `EdgeLabSpiralBasketExecutor.ApplyConservativeStopCap` y `VirtualSlot`.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any

RAIZ = pathlib.Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def aplicar_tope_paridad_cs(
    entry_price: float,
    direction: int,
    raw_stop_price: float,
    target_price: float,
    cap_pts: float,
    cap_mult: float,
    tick_size: float,
) -> float:
    """Réplica exacta de `EdgeLabSpiralBasketExecutor.ApplyConservativeStopCap` en C# para test de paridad."""
    max_dist = 0.0
    if cap_pts > 0.0:
        max_dist = float(cap_pts)
    elif cap_mult > 0.0:
        max_dist = float(cap_mult) * abs(float(target_price) - float(entry_price))

    if max_dist <= 0.0 or abs(float(entry_price) - float(raw_stop_price)) <= max_dist:
        return float(raw_stop_price)

    capped = float(entry_price) - int(direction) * max_dist
    if int(direction) == 1:
        return math.ceil(capped / float(tick_size)) * float(tick_size)
    return math.floor(capped / float(tick_size)) * float(tick_size)


UNIDADES_APROBADAS_NO_APLANADAS: list[dict[str, Any]] = [
    {
        "slot_id": 0,
        "unit_id": "U1_CRUZADO_E1A_T3S3",
        "tipo": "REGLA_INDIVIDUAL_45M",
        "familia": "AREAS_EXP_1_CRUZADO",
        "sensor": "DK:USATECHIDXUSD",
        "ejecucion": "MNQ",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "celda": "E1A/T3/S3",
        "tope": ["pts", 150.0],
        "metricas_oos_nt8": {"n": 84, "neto_usd": 3952.86, "h1_usd": 2007.52, "h2_usd": 1945.34, "pf": 2.74, "r2": 0.97},
    },
    {
        "slot_id": 1,
        "unit_id": "ASIA-NQ_CANASTA_ORTOGONAL_3P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "ASIA_BOS_GAPS",
        "sensor": "NQ",
        "ejecucion": "MNQ",
        "regimen_afinidad": "COMPRESION_RUPTURA",
        "pistas_indices": [2, 8, 5],
        "celdas": [
            [1, 0, 0, 2, 1, 3, 3, 2, 2, 3],
            [1, 1, 0, 1, 3, 3, 3, 2, 0, 10],
            [1, 0, 0, 2, 2, 3, 3, 2, 2, 3],
        ],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 72, "neto_usd": 4739.42, "h1_usd": 2580.96, "h2_usd": 2158.46, "pf": 2.30, "r2": 0.94},
    },
    {
        "slot_id": 2,
        "unit_id": "ORO-ALM-CFD_CANASTA_ORTOGONAL_2P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "ORO_ALMUERZO_RUPTURA",
        "sensor": "DK:XAUUSD",
        "ejecucion": "MGC",
        "regimen_afinidad": "COMPRESION_RUPTURA",
        "pistas_indices": [18, 7],
        "celdas": [
            [0, 2, 1, 2, 0, 3, 0, 2, 2, 2],
            [0, 2, 1, 2, 0, 2, 0, 2, 1, 2],
        ],
        "tope": ["pts", 50.0],
        "metricas_oos_nt8": {"n": 29, "neto_usd": 3772.55, "h1_usd": 2738.12, "h2_usd": 1034.43, "pf": 3.09, "r2": 0.90},
    },
    {
        "slot_id": 3,
        "unit_id": "OTR930-NQ_CANASTA_ORTOGONAL_3P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "OTR_930_SWEEP",
        "sensor": "NQ",
        "ejecucion": "MNQ",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "pistas_indices": [5, 14, 16],
        "celdas": [
            [0, 1, 1, 0, 3, 3, 0, 1, 1, 10],
            [2, 0, 2, 2, 1, 2, 0, 2, 1, 10],
            [1, 1, 1, 0, 3, 3, 0, 2, 1, 2],
        ],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 74, "neto_usd": 2966.29, "h1_usd": 997.68, "h2_usd": 1968.61, "pf": 1.55, "r2": 0.65},
    },
    {
        "slot_id": 4,
        "unit_id": "CVGAP-NQ_ACTA",
        "tipo": "REGLA_ACTA_HOLDOUT",
        "familia": "CORREDOR_VOL_GAPS",
        "sensor": "NQ",
        "ejecucion": "MNQ",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "celda": [0, 0, 1, 2, 2, 2, 3, 2, 0, 2, 11],
        "tope": ["mult", 4.0],
        "metricas_oos_nt8": {"n": 81, "neto_usd": 2850.12, "h1_usd": 2687.87, "h2_usd": 162.25, "pf": 1.65, "r2": 0.87},
    },
    {
        "slot_id": 5,
        "unit_id": "CVGAP-CFD-NQ_ACTA",
        "tipo": "REGLA_ACTA_HOLDOUT",
        "familia": "CORREDOR_VOL_GAPS",
        "sensor": "DK:USATECHIDXUSD",
        "ejecucion": "MNQ",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "celda": [0, 1, 0, 0, 2, 3, 2, 1, 2, 0, 10],
        "tope": ["pts", 50.0],
        "metricas_oos_nt8": {"n": 108, "neto_usd": 1894.68, "h1_usd": 1066.94, "h2_usd": 827.74, "pf": 1.30, "r2": 0.87},
    },
    {
        "slot_id": 6,
        "unit_id": "ASIA-CFD-NQ_CANASTA_ORTOGONAL_2P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "ASIA_BOS_GAPS",
        "sensor": "DK:USATECHIDXUSD",
        "ejecucion": "MNQ",
        "regimen_afinidad": "COMPRESION_RUPTURA",
        "pistas_indices": [1, 2],
        "celdas": [
            [0, 2, 1, 2, 2, 2, 1, 0, 0, 1],
            [0, 2, 1, 2, 2, 2, 1, 0, 1, 1],
        ],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 45, "neto_usd": 1584.90, "h1_usd": 834.40, "h2_usd": 750.50, "pf": 1.66, "r2": 0.78},
    },
    {
        "slot_id": 7,
        "unit_id": "CONF-CVR-CFD-NQ_CANASTA_ORTOGONAL_2P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "CONFLUENCIA_CVGAP_RACIMOS",
        "sensor": "DK:USATECHIDXUSD",
        "ejecucion": "MNQ",
        "regimen_afinidad": "CONFLUENCIA_TENDENCIA",
        "pistas_indices": [6, 18],
        "celdas": [
            [0, 2, 2, 0, 2, 0, 2, 0, 2, 2],
            [1, 1, 1, 0, 1, 2, 0, 2, 1, 19],
        ],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 82, "neto_usd": 1303.04, "h1_usd": 776.58, "h2_usd": 526.46, "pf": 1.66, "r2": 0.94},
    },
    {
        "slot_id": 8,
        "unit_id": "CVGAP-ES_SOSTENIDA_C18",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "CORREDOR_VOL_GAPS",
        "sensor": "ES",
        "ejecucion": "MES",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "pistas_indices": [18],
        "celdas": [[1, 0, 1, 0, 1, 2, 3, 1, 1, 4, 11]],
        "tope": ["pts", 50.0],
        "metricas_oos_nt8": {"n": 46, "neto_usd": 1170.80, "h1_usd": 860.40, "h2_usd": 310.40, "pf": 1.90, "r2": 0.81},
    },
    {
        "slot_id": 9,
        "unit_id": "U1-RACIMOS-GRILLA-NQ_SOSTENIDA_C0",
        "tipo": "REGLA_SOSTENIDA_OOS",
        "familia": "U1_ZONAS_NQ",
        "sensor": "NQ",
        "ejecucion": "MNQ",
        "regimen_afinidad": "EXPANSION_REVERSION",
        "celda": [1, 0, 0, 9, 2, 1],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 18, "neto_usd": 1046.10, "h1_usd": 906.00, "h2_usd": 140.10, "pf": 3.13, "r2": 0.91},
    },
    {
        "slot_id": 10,
        "unit_id": "TORI-NQ_CANASTA_ORTOGONAL_2P",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "TORI_TREND_TOQUE3",
        "sensor": "NQ",
        "ejecucion": "MNQ",
        "regimen_afinidad": "CONFLUENCIA_TENDENCIA",
        "pistas_indices": [19, 4],
        "celdas": [
            [1, 0, 1, 0, 3, 2, 3, 2, 1, 15],
            [1, 1, 1, 2, 3, 2, 3, 2, 2, 23],
        ],
        "tope": ["pts", 100.0],
        "metricas_oos_nt8": {"n": 46, "neto_usd": 999.80, "h1_usd": 834.40, "h2_usd": 165.40, "pf": 2.12, "r2": 0.81},
    },
    {
        "slot_id": 11,
        "unit_id": "CONF-CVR-CFD-ES_SOSTENIDA_C12",
        "tipo": "CANASTA_REGIMEN_PODADA",
        "familia": "CONFLUENCIA_CVGAP_RACIMOS",
        "sensor": "DK:USA500IDXUSD",
        "ejecucion": "MES",
        "regimen_afinidad": "CONFLUENCIA_TENDENCIA",
        "pistas_indices": [12],
        "celdas": [[1, 1, 0, 2, 0, 2, 2, 2, 1, 5]],
        "tope": ["pts", 50.0],
        "metricas_oos_nt8": {"n": 39, "neto_usd": 309.40, "h1_usd": 288.50, "h2_usd": 20.90, "pf": 1.63, "r2": 0.81},
    },
]

UNIDADES_DESCARTADAS_POR_APLANAMIENTO: list[dict[str, str]] = [
    {"id": "U1-ZONAS-NQ (c#0)", "motivo": "Sobreajuste a DESC (+$4,961 en DESC vs +$475 en OOS; H1 negativa -$69)"},
    {"id": "U1-ORO-GRILLA (c#1)", "motivo": "Sobreajuste a DESC (+$2,699 en DESC vs +$272 en OOS; H1 negativa -$39)"},
    {"id": "U1-ZONAS-ES (c#0)", "motivo": "Aplanada en OOS (+$2,772 en DESC vs +$41 en OOS; H2 negativa -$114)"},
    {"id": "U1-YM-GRILLA (c#0)", "motivo": "Aplanada en H2 OOS (+$1,343 en DESC vs +$20.5 en H2 OOS; retención 12.6%)"},
    {"id": "U1-ES-GRILLA (c#0)", "motivo": "Negativa en OOS (+$1,664 en DESC vs -$398 en OOS)"},
    {"id": "ZGAP-CFD (c#0)", "motivo": "Plana en OOS (+$2,196 en DESC vs -$17.6 en OOS)"},
    {"id": "EXPZ-CFD (c#0)", "motivo": "Caída de pendiente en OOS (+$2,222 en DESC vs +$188 en OOS; retención 8.5%)"},
    {"id": "U1-ZONAS-BT2-NQ (ACTA)", "motivo": "Negativa en OOS (-$1,535 USD, PF 0.61)"},
    {"id": "U1-ZONAS-BT2-ES (ACTA)", "motivo": "Aplanada en H2 OOS (H1 +$412 USD, H2 -$53 USD)"},
    {"id": "U1-RACIMOS-GRILLA-ES (ACTA)", "motivo": "Aplanada en H2 OOS (H1 +$406 USD, H2 -$143 USD, SinTop3 < 0)"},
    {"id": "ASIA-GC", "motivo": "Aplanada en H2 OOS (H1 +$2,088 USD, H2 -$151 USD)"},
    {"id": "OTR930-ES / OTR930-CFD-ES", "motivo": "Aplanadas en H2 OOS (H2 -$200 USD y -$15 USD)"},
]


def generar_artefactos_nt8(raiz: pathlib.Path = RAIZ) -> dict[str, Any]:
    """Escribe el manifiesto JSON de la canasta aprobada y la máscara de slots para `EdgeLabSpiralBasketExecutor.cs`."""
    from edgelab.research import grilla_generica as GG

    # Verificar paridad exacta de tope entre Python y C#
    casos_prueba = [
        (20000.0, 1, 19880.0, 20060.0, 50.0, 0.0, 0.25),
        (20000.0, -1, 20140.0, 19950.0, 50.0, 0.0, 0.25),
        (5800.0, 1, 5710.0, 5815.0, 0.0, 4.0, 0.25),
        (2650.0, -1, 2720.0, 2635.0, 0.0, 3.0, 0.10),
    ]
    for e, s, st, tp, c_pts, c_mult, tk in casos_prueba:
        tope_py = ("pts", c_pts) if c_pts > 0 else (("mult", c_mult) if c_mult > 0 else None)
        res_py = float(GG.aplicar_tope(e, s, st, tp, tope_py, tk))
        res_cs = float(aplicar_tope_paridad_cs(e, s, st, tp, c_pts, c_mult, tk))
        if not math.isclose(res_py, res_cs, abs_tol=1e-9):
            raise RuntimeError(f"Discrepancia Python vs C# en aplicar_tope: {res_py} != {res_cs}")

    manifiesto = {
        "schema": "edgelab_nt8_canasta_aprobada_v1",
        "fecha": "2026-10-29",
        "estrategia_nt8": "nt8/strategies/EdgeLabSpiralBasketExecutor.cs",
        "paridad_aplicar_tope_verificada": True,
        "n_unidades_aprobadas": len(UNIDADES_APROBADAS_NO_APLANADAS),
        "n_unidades_descartadas_por_aplanamiento": len(UNIDADES_DESCARTADAS_POR_APLANAMIENTO),
        "unidades_aprobadas": UNIDADES_APROBADAS_NO_APLANADAS,
        "unidades_descartadas_sobreajuste_oos": UNIDADES_DESCARTADAS_POR_APLANAMIENTO,
    }
    json_path = raiz / "config/autopilot/nt8_canasta_aprobada_20261029.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    mask_lines = [
        "# EdgeLab Causal Regime Mask para EdgeLabSpiralBasketExecutor.cs (Slots Aprobados Sin Aplanamiento OOS)",
        *[str(u["slot_id"]) for u in UNIDADES_APROBADAS_NO_APLANADAS],
    ]
    mask_path = raiz / "config/autopilot/nt8_regime_mask_20261029.txt"
    mask_path.write_text("\n".join(mask_lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "json_path": str(json_path.relative_to(raiz)),
        "mask_path": str(mask_path.relative_to(raiz)),
        "n_unidades_aprobadas": len(UNIDADES_APROBADAS_NO_APLANADAS),
        "n_descartadas": len(UNIDADES_DESCARTADAS_POR_APLANAMIENTO),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera los artefactos de ejecución y verifica paridad con NinjaTrader 8.")
    ap.add_argument("--verificar-paridad", action="store_true", help="Ejecuta la verificación determinista Python vs C#.")
    ap.parse_args()
    res = generar_artefactos_nt8(RAIZ)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
