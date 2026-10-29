"""Catálogo Modular y Vía Formal de Crecimiento en Espiral para EdgeLab (`edgelab/research/catalogo_espiral.py`).

Propósito:
  1. Clasificar ordenada y explícitamente todos los módulos de EdgeLab en **6 capas jerárquicas (`L0..L5`)**
     y **7 categorías funcionales componibles**, de modo que el agente del Debian conozca qué hace cada módulo,
     qué funciones/primitivas exporta y cómo reutilizarlas sin duplicar código.
  2. Proveer una **vía concreta y programática (`promover_bloque_espiral`, `bloques_compatibles`, `componer_experimento`)**
     para que cada hallazgo, detector `@njit`, filtro de régimen o mecánica de entrada/salida persista, se traslade
     a otros instrumentos, complemente a otros bloques y se una en nuevas familias, haciendo crecer a EdgeLab en espiral.
  3. Construir un **índice compacto y rápido (`resumen_rapido_para_agente`)** que cabe en `< 8 KB` dentro del paquete
     de contexto de los agentes sin perder visibilidad de ningún módulo.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

RAIZ_REPO = Path(__file__).resolve().parents[2]
RUTA_CATALOGO_JSON = RAIZ_REPO / "config/autopilot/CATALOGO_MODULOS_ESPIRAL.json"

CAPAS_EDGELAB: dict[str, str] = {
    "L0_NUCLEO_SELLADO": "Contratos inmutables: holdout_guard, costos canónicos, identidad de activos, puente Drive/Kaggle y árbol limpio.",
    "L1_DATOS_Y_DETECTORES_PARIDAD": "Lectores de ticks CME/Dukascopy y detectores causales con paridad C# NinjaTrader 8 o test_causal estricto.",
    "L2_PRIMITIVAS_Y_REGIMEN": "Bloques componibles @njit/vectorizados: cajas amarillas, racimos de zonas, ciclo de vida de gaps, ventanas DST, líneas stopping-time y variables de régimen.",
    "L3_MOTOR_GRILLA_Y_SIMULACION": "Barrido vectorizado en 1 pasada (grilla_generica, grilla_masiva), niveles_lote, simulador tick a tick (sim.py) y analizador.",
    "L4_INFERENCIA_EMBUDO_Y_CANASTA": "Escalera del embudo (PREFLIGHT..HOLDOUT), FDR BH-Storey, Romano-Wolf, LORD++ (LibroLord), linajes y canasta de régimen.",
    "L5_AUTOPILOT_MULTIAGENTE_ESPIRAL": "Orquestador multi-agente Debian (Capataz Python + 2 Opus 4.6 + 1 Sonnet 4.6), sincronizador de ramas, auditor de alineación y memoria en espiral.",
}

CATEGORIAS_FUNCIONALES: tuple[str, ...] = (
    "sensores_zonas_volumen_gaps",
    "detectores_impulso_corredor",
    "rangos_sesiones_horarios",
    "lineas_tendencia_estructura",
    "filtros_regimen_macro_escala",
    "motor_grilla_simulacion",
    "inferencia_embudo_multiagente",
)


@dataclass
class ModuloCatalogado:
    id_modulo: str
    ruta: str
    capa: str
    categoria: str
    descripcion: str
    primitivas_exportadas: list[str]
    instrumentos_validados: list[str]
    se_apoya_en: list[str] = field(default_factory=list)
    combinable_con: list[str] = field(default_factory=list)
    evidencia_empirica: str = ""
    estado_espiral: str = "ACTIVO"  # "NUCLEO" | "ACTIVO" | "PROMOVIDO_ACTA" | "PISTAS_VIVAS"

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


MODULOS_CANONICOS: list[ModuloCatalogado] = [
    # --- L0: Núcleo Inmutable ---
    ModuloCatalogado(
        id_modulo="holdout_guard",
        ruta="edgelab/research/holdout_guard.py",
        capa="L0_NUCLEO_SELLADO",
        categoria="inferencia_embudo_multiagente",
        descripcion="Guarda dura que corta toda lectura de desarrollo antes de la sesión 2026-10-01.",
        primitivas_exportadas=["HOLDOUT_PRIMERA_SESION_INT", "verificar_corte_holdout"],
        instrumentos_validados=["TODOS"],
        estado_espiral="NUCLEO",
    ),
    ModuloCatalogado(
        id_modulo="costos",
        ruta="edgelab/costos.py",
        capa="L0_NUCLEO_SELLADO",
        categoria="motor_grilla_simulacion",
        descripcion="Fricción canónica por viaje (comisión + spread + slippage) para futuros CME y CFDs.",
        primitivas_exportadas=["friccion_viaje", "COSTOS_CANONICOS"],
        instrumentos_validados=["ES", "NQ", "YM", "RTY", "GC", "6E", "MBT"],
        estado_espiral="NUCLEO",
    ),
    # --- L1: Datos y Detectores con Paridad ---
    ModuloCatalogado(
        id_modulo="fuentes_ticks",
        ruta="edgelab/research/fuentes_ticks.py",
        capa="L1_DATOS_Y_DETECTORES_PARIDAD",
        categoria="motor_grilla_simulacion",
        descripcion="Lector unificado de ticks de futuros CME (release liquid_tick_v1) y spots Dukascopy con armado de M1 y perfil.",
        primitivas_exportadas=["contexto_m1", "bloques_dukascopy", "sesiones_disponibles"],
        instrumentos_validados=["ES", "NQ", "YM", "GC", "6E", "6B", "DK:USATECHIDXUSD", "DK:USA500IDXUSD", "DK:XAUUSD", "DK:EURUSD"],
        se_apoya_en=["holdout_guard"],
        estado_espiral="NUCLEO",
    ),
    ModuloCatalogado(
        id_modulo="zonas_gaps",
        ruta="edgelab/research/zonas_gaps.py",
        capa="L1_DATOS_Y_DETECTORES_PARIDAD",
        categoria="sensores_zonas_volumen_gaps",
        descripcion="Port causal 1:1 de ZonasDeGaps.cs (50T y M1): gaps puros, vacíos sin rellenar, mitigación con AwayDistanceTicks y clusters compactos.",
        primitivas_exportadas=["_detectar_gaps_y_clusters_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "GC", "DK:USATECHIDXUSD", "DK:USA500IDXUSD"],
        se_apoya_en=["fuentes_ticks", "grilla_generica"],
        combinable_con=["corredor_vol_gaps", "otr_930_sweep", "oro_almuerzo_ruptura", "tori_trend_toque3", "asia_bos_gaps", "confluencia_cvgap_racimos"],
        evidencia_empirica="ZGAP-NQ: 18/20 pistas positivas (+5,2 pts/sesión, p=0,04); base de CVGAP-NQ y CVGAP-CFD-NQ.",
        estado_espiral="ACTIVO",
    ),
    ModuloCatalogado(
        id_modulo="corredor_vol_gaps",
        ruta="edgelab/research/corredor_vol_gaps.py",
        capa="L1_DATOS_Y_DETECTORES_PARIDAD",
        categoria="detectores_impulso_corredor",
        descripcion="Port causal v2 de EmaCorridorTrendVolW2.cs acoplado a ZonasDeGaps.cs: corredor EMA 20/60, sector adelantado BuildVolumeAtPrice (W1=100%/W2=200%), Caja Amarilla P80/P90 (Lookback=50), excursión y regreso con g_tom/g_cam.",
        primitivas_exportadas=["_extraer_cajas_amarillas_nb", "_precomputar_eventos_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "DK:USATECHIDXUSD", "DK:USA500IDXUSD"],
        se_apoya_en=["zonas_gaps", "fuentes_ticks", "grilla_generica"],
        combinable_con=["u1_racimos_grilla", "otr_930_sweep", "tori_trend_toque3", "asia_bos_gaps", "confluencia_cvgap_racimos"],
        evidencia_empirica="CVGAP-NQ (+19,13 USD/op OOS, ACTA_HOLDOUT) y CVGAP-CFD-NQ (+10,50 USD/op OOS, ACTA_HOLDOUT); CVGAP-ES PISTAS_VIVAS (+24,47 pts/op en p3).",
        estado_espiral="PROMOVIDO_ACTA",
    ),
    ModuloCatalogado(
        id_modulo="u1_racimos_grilla",
        ruta="edgelab/research/u1_racimos_grilla.py",
        capa="L1_DATOS_Y_DETECTORES_PARIDAD",
        categoria="sensores_zonas_volumen_gaps",
        descripcion="Detector causal de racimos densos de zonas de volumen (AVZP2 / AVZRG) con mecánica de excursión y regreso U1.",
        primitivas_exportadas=["racimos_desde_zonas", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "YM"],
        se_apoya_en=["u1_zonas", "u1_indaga", "u1_oro"],
        combinable_con=["corredor_vol_gaps", "confluencia_cvgap_racimos"],
        evidencia_empirica="U1-RACIMOS-GRILLA-NQ (+32,83 pts/op OOS, ACTA_HOLDOUT) y U1-RACIMOS-GRILLA-ES (+5,95 pts/op, ACTA_HOLDOUT).",
        estado_espiral="PROMOVIDO_ACTA",
    ),
    ModuloCatalogado(
        id_modulo="u1_zonas_bt2",
        ruta="edgelab/research/u1_zonas_bt2.py",
        capa="L1_DATOS_Y_DETECTORES_PARIDAD",
        categoria="sensores_zonas_volumen_gaps",
        descripcion="Gramática U1 sobre zonas de absorción BigTrap2 (BT2) en ES, NQ y YM.",
        primitivas_exportadas=["disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["ES", "NQ", "YM"],
        se_apoya_en=["u1_zonas", "u1_indaga"],
        combinable_con=["corredor_vol_gaps", "confluencia_cvgap_racimos"],
        evidencia_empirica="U1-ZONAS-BT2-ES (+2,47 pts/op OOS, ACTA_HOLDOUT) y U1-ZONAS-BT2-NQ (+15,02 pts/op, ACTA_HOLDOUT).",
        estado_espiral="PROMOVIDO_ACTA",
    ),
    # --- L2: Primitivas Reutilizables, Horarios, Estructura y Régimen ---
    ModuloCatalogado(
        id_modulo="otr_930_sweep",
        ruta="edgelab/research/otr_930_sweep.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="rangos_sesiones_horarios",
        descripcion="Rango pre-market NY (08:12-09:12 / 08:00-09:15 / 08:30-09:29 ET con ajuste DST exacto) + barrido post-09:30 ET y retorno al extremo opuesto acoplado a ZONAS-GAPS y Caja Amarilla.",
        primitivas_exportadas=["_offset_ny_segundos_nb", "_extraer_eventos_otr930_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "DK:USATECHIDXUSD", "DK:USA500IDXUSD"],
        se_apoya_en=["zonas_gaps", "corredor_vol_gaps", "u1_oro"],
        combinable_con=["confluencia_cvgap_racimos", "asia_bos_gaps"],
        evidencia_empirica="OTR930-NQ (+5,12 pts/op canasta OOS, mejor pista +29,97 pts/op) y OTR930-CFD-NQ (+3,03 pts/op canasta OOS, PISTAS_VIVAS).",
        estado_espiral="PISTAS_VIVAS",
    ),
    ModuloCatalogado(
        id_modulo="oro_almuerzo_ruptura",
        ruta="edgelab/research/oro_almuerzo_ruptura.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="rangos_sesiones_horarios",
        descripcion="Rango matutino europeo 08:00-14:00 Europe/Madrid (CET/CEST exacto) en GC/XAUUSD con sesgo Open_08, ruptura 14:00 y salida horaria 18:00 Madrid.",
        primitivas_exportadas=["_offset_madrid_segundos_nb", "_extraer_eventos_almuerzo_oro_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["GC", "DK:XAUUSD"],
        se_apoya_en=["u1_oro", "zonas_gaps"],
        combinable_con=["oro_0530", "tori_trend_toque3", "asia_bos_gaps"],
        evidencia_empirica="ORO-ALM-CFD (+0,42 pts/op canasta OOS, pista +13,62 USD/op p=0,0386) y ORO-ALM-GC (+14,00 USD/op en mejor pista OOS).",
        estado_espiral="PISTAS_VIVAS",
    ),
    ModuloCatalogado(
        id_modulo="tori_trend_toque3",
        ruta="edgelab/research/tori_trend_toque3.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="lineas_tendencia_estructura",
        descripcion="Teoría de tiempos de parada (Tori Trades Paper + Post #943): pivotes causales confirmados, línea de tendencia en log-precio con ángulo normalizado por ATR, 3er toque con enfriamiento de 4h y ruptura stopping-time con gaps.",
        primitivas_exportadas=["_extraer_eventos_tori_trend_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "GC", "DK:USATECHIDXUSD"],
        se_apoya_en=["zonas_gaps", "corredor_vol_gaps", "u1_oro"],
        combinable_con=["corredor_vol_gaps", "u1_racimos_grilla"],
        evidencia_empirica="TORI-GC (+0,28 pts/op canasta OOS, 16/20 positivas, mejor +2,07 pts/op) y TORI-CFD-NQ (mejor +10,81 pts/op OOS, PISTAS_VIVAS).",
        estado_espiral="PISTAS_VIVAS",
    ),
    ModuloCatalogado(
        id_modulo="asia_bos_gaps",
        ruta="edgelab/research/asia_bos_gaps.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="rangos_sesiones_horarios",
        descripcion="Caja de compresión asiática (18:00-20:00 / 18:00-22:00 ET, Posts #18/#23 @alefx_ar y #159 @algo.jan) acoplada a barrido con reingreso IFVG o ruptura BOS a favor del corredor EMA.",
        primitivas_exportadas=["_extraer_eventos_asia_bos_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "GC", "DK:USATECHIDXUSD"],
        se_apoya_en=["otr_930_sweep", "zonas_gaps", "corredor_vol_gaps", "u1_oro"],
        combinable_con=["oro_0530", "corredor_vol_gaps"],
        evidencia_empirica="ASIA-NQ (+4,38 pts/op canasta OOS, mejor +55,47 pts/op y +19,44 pts/op p=0,0493), ASIA-CFD-NQ (+1,81 pts/op canasta OOS, mejor +23,22 pts/op) y ASIA-GC (mejor +5,87 pts/op OOS, p=0,0894).",
        estado_espiral="PISTAS_VIVAS",
    ),
    ModuloCatalogado(
        id_modulo="confluencia_cvgap_racimos",
        ruta="edgelab/research/confluencia_cvgap_racimos.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="detectores_impulso_corredor",
        descripcion="Síntesis en espiral de las 6 mejores corridas de Olas 1-9: exige simultáneamente Caja Amarilla causal (CVGAP v2) + densidad de racimo de absorción (RACIMOS/BT2) + cuantiles invariantes de gaps + ancla de sesión/apertura (OTR930).",
        primitivas_exportadas=["_extraer_confluencia_cvgap_racimos_nb", "disparos", "niveles", "niveles_lote"],
        instrumentos_validados=["NQ", "ES", "DK:USATECHIDXUSD", "DK:USA500IDXUSD"],
        se_apoya_en=["corredor_vol_gaps", "u1_racimos_grilla", "u1_zonas_bt2", "otr_930_sweep", "zonas_gaps"],
        combinable_con=["regimen", "eventos"],
        evidencia_empirica="CONF-CVR-NQ (mejor +10,97 pts/op OOS, p=0,0156, 38 ses.) y CONF-CVR-CFD-NQ (+0,34 pts/op canasta OOS, 13/20 positivas, mejor +9,84 pts/op p=0,0212).",
        estado_espiral="PISTAS_VIVAS",
    ),
    ModuloCatalogado(
        id_modulo="regimen",
        ruta="edgelab/research/agente/regimen.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="filtros_regimen_macro_escala",
        descripcion="7 variables causales de régimen por vela (vol_ahora, vol_diaria, eficiencia, tendencia_dia, actividad, hora, dia) listas para VARIABLES.",
        primitivas_exportadas=["VARIABLES_REGIMEN", "por_vela", "agregar"],
        instrumentos_validados=["TODOS"],
        se_apoya_en=["grilla_generica"],
        combinable_con=["TODOS"],
        estado_espiral="NUCLEO",
    ),
    ModuloCatalogado(
        id_modulo="u1_oro_escala",
        ruta="edgelab/research/u1_oro.py",
        capa="L2_PRIMITIVAS_Y_REGIMEN",
        categoria="filtros_regimen_macro_escala",
        descripcion="Normalización causal mensual (`escala_por_mes`) con soporte para ventana sellada 202610 (`RANGO_M1_202609`).",
        primitivas_exportadas=["escala_por_mes", "RANGO_M1_202609"],
        instrumentos_validados=["GC", "NQ", "ES", "YM", "6E", "DK:XAUUSD", "DK:USATECHIDXUSD", "DK:USA500IDXUSD"],
        estado_espiral="NUCLEO",
    ),
    # --- L3: Motor de Grilla y Simulación ---
    ModuloCatalogado(
        id_modulo="grilla_generica",
        ruta="edgelab/research/grilla_generica.py",
        capa="L3_MOTOR_GRILLA_Y_SIMULACION",
        categoria="motor_grilla_simulacion",
        descripcion="Motor universal de barrido masivo: 1 simulación por (disparo, ejecución), corte E0 target-free, niveles_lote vectorizado y Romano-Wolf matricial.",
        primitivas_exportadas=["Variable", "correr", "simular_ops", "n_celdas", "resumen_e0"],
        instrumentos_validados=["TODOS"],
        se_apoya_en=["grilla_masiva", "sim", "costos"],
        estado_espiral="NUCLEO",
    ),
    ModuloCatalogado(
        id_modulo="paridad_nt8_canastas",
        ruta="edgelab/research/paridad_nt8_canastas.py",
        capa="L3_MOTOR_GRILLA_Y_SIMULACION",
        categoria="motor_grilla_simulacion",
        descripcion="Verificador de paridad 1-a-1 con NinjaTrader 8 Strategy Analyzer (EntriesPerDirection=1, Flat-Only), curvas de equity con Polars/Pandas y simulador de ejecución de Canastas de Regímenes (Subcuentas Virtuales 1/K y Cuenta Única Flat Global).",
        primitivas_exportadas=["filtrar_solapadas_nt8", "curva_equity_polars_o_pandas", "reporte_paridad_nt8", "simular_canasta_regimen", "exportar_senales_nt8_csv"],
        instrumentos_validados=["NQ", "ES", "GC", "YM", "DK:USATECHIDXUSD", "DK:USA500IDXUSD", "DK:XAUUSD"],
        se_apoya_en=["analizador", "grilla_generica", "areas_expansion"],
        combinable_con=["TODOS"],
        evidencia_empirica="Paridad 98-100% en ASIA, OTR930, ORO-ALM, TORI, CONF-CVR y U1; acoplado a nt8/strategies/EdgeLabSpiralBasketExecutor.cs.",
        estado_espiral="NUCLEO",
    ),
    # --- L4: Inferencia, Embudo y Canasta ---
    ModuloCatalogado(
        id_modulo="embudo",
        ruta="edgelab/research/embudo.py",
        capa="L4_INFERENCIA_EMBUDO_Y_CANASTA",
        categoria="inferencia_embudo_multiagente",
        descripcion="Orquestador determinista de las 9 etapas del embudo (PREFLIGHT -> DESC -> INDAGA -> INTEGRIDAD -> OOS -> TOPES -> ACTA -> CONTEO -> HOLDOUT).",
        primitivas_exportadas=["Embudo", "problemas_campana", "avanzar_todas"],
        instrumentos_validados=["TODOS"],
        se_apoya_en=["grilla_generica", "linaje", "holdout_ventanas", "libro_lord"],
        estado_espiral="NUCLEO",
    ),
    # --- L5: Autopilot Multi-Agente y Espiral ---
    ModuloCatalogado(
        id_modulo="orquestador_multiagente",
        ruta="edgelab/autopilot/orquestador_multiagente.py",
        capa="L5_AUTOPILOT_MULTIAGENTE_ESPIRAL",
        categoria="inferencia_embudo_multiagente",
        descripcion="Coordinador del sistema triádico Debian (Capataz Python + Arquitecto Opus 4.6 + Ingeniero/Doctor Opus 4.6 + Auditor Sonnet 4.6), contexto amplio sin pop() y compuerta velocidad-cuidado.",
        primitivas_exportadas=["TOPOLOGIA_DEBIAN_V2", "armar_contexto_amplio_espiral", "evaluar_velocidad_cuidado", "auditar_propuesta_sonnet"],
        instrumentos_validados=["TODOS"],
        se_apoya_en=["sincronizador_ramas", "auditor_alineacion", "catalogo_espiral"],
        estado_espiral="NUCLEO",
    ),
]


def catalogo_completo() -> dict[str, Any]:
    """Devuelve el diccionario estructurado del catálogo modular en espiral."""
    return {
        "schema": "edgelab_catalogo_modulos_espiral_v2",
        "actualizado": "2026-10-29",
        "capas": CAPAS_EDGELAB,
        "categorias": list(CATEGORIAS_FUNCIONALES),
        "modulos": [m.a_dict() for m in MODULOS_CANONICOS],
    }


def buscar_bloques_por_categoria(categoria: str) -> list[dict[str, Any]]:
    return [m.a_dict() for m in MODULOS_CANONICOS if m.categoria == categoria]


def bloques_compatibles_con(id_modulo: str) -> list[dict[str, Any]]:
    mod_map = {m.id_modulo: m for m in MODULOS_CANONICOS}
    if id_modulo not in mod_map:
        return []
    objetivo = mod_map[id_modulo]
    compat = set(objetivo.combinable_con)
    for m in MODULOS_CANONICOS:
        if id_modulo in m.combinable_con or id_modulo in m.se_apoya_en or "TODOS" in m.combinable_con:
            compat.add(m.id_modulo)
    return [mod_map[k].a_dict() for k in sorted(compat) if k in mod_map]


def resumen_rapido_para_agente(max_chars: int = 8000) -> str:
    """Resumen compacto (< 8 KB) de todos los módulos y primitivas reutilizables para inyectar al prompt de los agentes."""
    lineas = [
        "# Catálogo Rápido de Módulos Reutilizables en Espiral (`catalogo_espiral.py`)",
        "Regla de la espiral: NUNCA reescribir detectores, escalas ni simuladores; importar y combinar las primitivas existentes.",
        "",
    ]
    for capa_id, desc_capa in CAPAS_EDGELAB.items():
        lineas.append(f"## {capa_id}: {desc_capa}")
        for m in MODULOS_CANONICOS:
            if m.capa != capa_id:
                continue
            prims = ", ".join(m.primitivas_exportadas[:4])
            apoyo = f" | apoya_en={m.se_apoya_en}" if m.se_apoya_en else ""
            evid = f" | evidencia: {m.evidencia_empirica}" if m.evidencia_empirica else ""
            lineas.append(f"- `{m.id_modulo}` (`{m.ruta}`) [{m.estado_espiral}]: exports=[{prims}]{apoyo}{evid}")
        lineas.append("")
    texto = "\n".join(lineas)
    return texto[:max_chars]


def escribir_artefactos_catalogo(raiz: Path = RAIZ_REPO) -> tuple[Path, Path]:
    """Escribe `config/autopilot/CATALOGO_MODULOS_ESPIRAL.json` y `docs/MODULOS_ESPIRAL.md`."""
    cat = catalogo_completo()
    json_path = raiz / "config/autopilot/CATALOGO_MODULOS_ESPIRAL.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# Catálogo Oficial de Módulos y Arquitectura en Espiral de EdgeLab (`docs/MODULOS_ESPIRAL.md`)",
        "",
        "Estado: **VIGENTE** (generado y verificado por `edgelab/research/catalogo_espiral.py`).",
        "Propósito: Dar acceso inmediato y ordenado a todos los módulos, herramientas, primitivas `@njit` y hallazgos empíricos",
        "para que los agentes del Debian (`Arquitecto Opus 4.6`, `Ingeniero Opus 4.6`, `Auditor Sonnet 4.6`) construyan cada",
        "familia nueva apoyándose en las anteriores.",
        "",
        "## 1. Las 6 Capas Jerárquicas de EdgeLab (`L0` a `L5`)",
        "",
        "| Capa | Descripción y Responsabilidad |",
        "|---|---|",
    ]
    for k, v in CAPAS_EDGELAB.items():
        md_lines.append(f"| `{k}` | {v} |")

    md_lines.extend(
        [
            "",
            "## 2. Inventario Clasificado de Módulos y Primitivas Reutilizables",
            "",
            "| ID Módulo | Ruta | Capa | Categoría | Primitivas Exportadas | Se Apoya En | Estado / Evidencia Empírica |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for m in MODULOS_CANONICOS:
        prims = ", ".join(f"`{p}`" for p in m.primitivas_exportadas)
        apoyo = ", ".join(f"`{a}`" for a in m.se_apoya_en) or "—"
        evid = f"**{m.estado_espiral}**" + (f": {m.evidencia_empirica}" if m.evidencia_empirica else "")
        md_lines.append(
            f"| `{m.id_modulo}` | `{m.ruta}` | `{m.capa}` | `{m.categoria}` | {prims} | {apoyo} | {evid} |"
        )

    md_lines.extend(
        [
            "",
            "## 3. Vía Concreta de Reutilización, Traslado y Unión de Módulos en Espiral",
            "",
            "1. **Consulta Obligatoria Pre-Diseño (`catalogo_espiral.resumen_rapido_para_agente()` + `tools/existente.py buscar`)**:",
            "   Antes de proponer o programar un módulo, el agente consulta qué detectores (`L1`), primitivas de sesión/estructura (`L2`) y variables de régimen (`regimen.py`) ya existen y qué celdas sobrevivieron en `APRENDIZAJES_ESPIRAL.md`.",
            "2. **Traslado Multi-Instrumento (`Cross-Asset & Cross-Feed Transfer`)**:",
            "   Toda primitiva validada en un activo (ej. `corredor_vol_gaps` en `NQ`) se traslada parametrizando sus cortes por cuantiles empíricos de `E0` (`Variable(..., cuantiles=3)`) o por `u1_oro.escala_por_mes(ctx)` para conservar invarianza de escala en `ES`, `GC`, `YM`, `6E` y cruces `CFD -> Futuro`.",
            "3. **Unión y Composición de Primitivas (`L1 + L2 -> Nueva Familia`)**:",
            "   Un experimento nuevo une en su pre-cómputo `@njit` dos o más primitivas ortogonales ya probadas (por ejemplo, `confluencia_cvgap_racimos.py` une la Caja Amarilla de `corredor_vol_gaps.py` con la densidad de racimos de `u1_racimos_grilla.py` y el barrido `otr_930_sweep.py`).",
            "4. **Promoción Automática al Catálogo (`promover_bloque_espiral`)**:",
            "   Cuando una campaña alcanza `ACTA_HOLDOUT.json` o `PISTAS_VIVAS` con media positiva en OOS, sus funciones `@njit` y su firma de régimen quedan promovidas en `CATALOGO_MODULOS_ESPIRAL.json` y en `APRENDIZAJES_ESPIRAL.md`.",
        ]
    )
    docs_mod_path = raiz / "docs/MODULOS_ESPIRAL.md"
    docs_mod_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, docs_mod_path
