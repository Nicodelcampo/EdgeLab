#!/usr/bin/env python3
"""Registro retroactivo en el contador GLOBAL de las campanias con desenlaces corridas entre 2026-10-20 y 2026-10-22
(LUX-IMB, ORB0100/ORB-HORARIOS, EURUSD escalonadas). Se habian corrido sin registrarse (ver
docs/research/AUDITORIA_EMBUDO_Y_SPRINT_20261020_22.md). Idempotente.

    python tools/registrar_campanias_20261020.py
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402

L = "docs/research/luximb_parity_20261020/"; O = "docs/research/orb0100_20261021/"; E = "docs/research/eurusd_escalonadas_20261021/"
CAMPANIAS = [
    ("luximb_20261020/M1-M3", "LUXIMB_IMPULSOS", 7, "rebalanceo/control/continuacion; Holm 7; " + L + "PREREGISTRO_M1_M2_M3_LUXIMB_NQ_20261020.md"),
    ("luximb_20261020/M4", "LUXIMB_IMPULSOS", 10, "penetracion 5 alturas x 2; Holm 10; " + L + "PREREGISTRO_M4_PENETRACION_LUXIMB_NQ_20261020.md"),
    ("luximb_20261020/M5", "LUXIMB_IMPULSOS", 6, "vuelta al inicio cargado; Holm 6; " + L + "PREREGISTRO_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md"),
    ("luximb_20261020/M6", "LUXIMB_ESCALONADAS_AREA", 6, "ruptura escalonadas 150t NQ; Holm 6; " + L + "PREREGISTRO_M6_ESCALONADAS_LUXIMB_NQ_20261020.md"),
    ("luximb_20261020/M7", "LUXIMB_ESCALONADAS_AREA", 4, "ES area cargada; Holm 4; " + L + "MANIFIESTO_M7_ES_AREA_CARGADA_FRENA_20261020.md"),
    ("luximb_20261020/M7b", "LUXIMB_ESCALONADAS_AREA", 2, "control vol previa; Holm 2; " + L + "MANIFIESTO_M7B_CONTROL_VOLATILIDAD_ES_20261020.md"),
    ("luximb_20261020/M8", "LUXIMB_IMPULSOS", 5, "franjas desbalance 4 vidas + GBM; Holm 5; " + L + "MANIFIESTO_M8_FRANJAS_DESBALANCE_LUXIMB_20261020.md"),
    ("luximb_20261020/M9", "LUXIMB_IMPULSOS", 8, "distancia/tiempo/zonas; Holm 8 + 1 ES; " + L + "MANIFIESTO_M9_DISTANCIA_TIEMPO_ZONAS_TOMADAS_20261020.md"),
    ("luximb_20261020/M10", "LUXIMB_IMPULSOS", 4, "6 activos, 3 hipotesis + control M10b; " + L + "MANIFIESTO_M10_MULTIACTIVO_LUXIMB_20261020.md"),
    ("luximb_20261020/M11", "LUXIMB_FADE_VISOR", 40, "grilla SL/TP/BE IS/OOS/ES; " + L + "MANIFIESTO_M11_GRILLA_SLTP_FADE_20261020.md"),
    ("luximb_20261021/variantes_visor", "LUXIMB_FADE_VISOR", 5, "TP/SL/BE explorados por periodo (sin preregistro); " + L + "AUDITORIA_ENTRADA_LOOKAHEAD_Y_BE_20261021.md"),
    ("luximb_20261021/holdout_exploratorio", "LUXIMB_FADE_VISOR", 1, "mirada exploratoria holdout NQ n=14 (consume apertura de esas sesiones); " + L + "CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md"),
    ("orb0100_20261021/grilla", "ORB0100", 48, "48 celdas NQ IS/OOS + ES; " + O + "MANIFIESTO_ORB0100_20261021.md"),
    ("orb0100_20261021/V2", "ORB0100", 25, "24 variantes + partida x 8 activos (combinado); Holm 25; " + O + "MANIFIESTO_ORB0100_V2_MULTIACTIVO_20261021.md"),
    ("orb0100_20261021/replicacion_NQ", "ORB0100", 1, "replicacion NQ abr-sep; " + O + "REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md"),
    ("orb0100_20261021/franjas_ogvi", "ORB0100", 3, "franjas OG/VI como filtro; Holm 3; " + O + "MANIFIESTO_ORB0100_FRANJAS_OGVI_20261021.md"),
    ("orb0100_20261021/horarios", "ORB_HORARIOS", 704, "44 ventanas x 2 reglas x 8 activos; BH 10 %; " + O + "MANIFIESTO_ORB_HORARIOS_20261021.md"),
    ("orb0100_20261021/gc_nocturno", "ORB_HORARIOS", 1, "replica GC abr-jun (racimo); " + O + "PREREGISTRO_GC_NOCTURNO_20261021.md"),
    ("eurusd_escalonadas_20261021/grilla", "EURUSD_ESCALONADAS", 648, "grilla MNQ, max-T 648; " + E + "MANIFIESTO_EURUSD_ESCALONADAS_ESCALAS_20261021.md"),
    ("eurusd_escalonadas_20261021/visor", "EURUSD_ESCALONADAS", 7, "simulaciones visuales sin preregistro (mitad, ult2, pri2 x escalas); " + E + "INDICADOR_ESCALONADAS_OGVI_EURUSD_20261021.md"),
]


def main():
    g = TrialRegistry(REPO / "docs" / "research" / "TRIAL_REGISTRY_GLOBAL.jsonl")
    nuevos = sum(bool(g.ensure(c, f, n, note)) for c, f, n, note in CAMPANIAS)
    print(json.dumps(dict(registradas_ahora=nuevos, campanias=g.n_campaigns(), pruebas_totales=g.total(),
                          pruebas_de_este_sprint=sum(n for _, _, n, _ in CAMPANIAS))))


if __name__ == "__main__":
    main()
