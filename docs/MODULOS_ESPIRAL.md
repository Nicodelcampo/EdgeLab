# Catálogo Oficial de Módulos y Arquitectura en Espiral de EdgeLab (`docs/MODULOS_ESPIRAL.md`)

Estado: **VIGENTE** (generado y verificado por `edgelab/research/catalogo_espiral.py`).
Propósito: Dar acceso inmediato y ordenado a todos los módulos, herramientas, primitivas `@njit` y hallazgos empíricos
para que los agentes del Debian (`Arquitecto Opus 4.6`, `Ingeniero Opus 4.6`, `Auditor Sonnet 4.6`) construyan cada
familia nueva apoyándose en las anteriores.

## 1. Las 6 Capas Jerárquicas de EdgeLab (`L0` a `L5`)

| Capa | Descripción y Responsabilidad |
|---|---|
| `L0_NUCLEO_SELLADO` | Contratos inmutables: holdout_guard, costos canónicos, identidad de activos, puente Drive/Kaggle y árbol limpio. |
| `L1_DATOS_Y_DETECTORES_PARIDAD` | Lectores de ticks CME/Dukascopy y detectores causales con paridad C# NinjaTrader 8 o test_causal estricto. |
| `L2_PRIMITIVAS_Y_REGIMEN` | Bloques componibles @njit/vectorizados: cajas amarillas, racimos de zonas, ciclo de vida de gaps, ventanas DST, líneas stopping-time y variables de régimen. |
| `L3_MOTOR_GRILLA_Y_SIMULACION` | Barrido vectorizado en 1 pasada (grilla_generica, grilla_masiva), niveles_lote, simulador tick a tick (sim.py) y analizador. |
| `L4_INFERENCIA_EMBUDO_Y_CANASTA` | Escalera del embudo (PREFLIGHT..HOLDOUT), FDR BH-Storey, Romano-Wolf, LORD++ (LibroLord), linajes y canasta de régimen. |
| `L5_AUTOPILOT_MULTIAGENTE_ESPIRAL` | Orquestador multi-agente Debian (Capataz Python + 2 Opus 4.6 + 1 Sonnet 4.6), sincronizador de ramas, auditor de alineación y memoria en espiral. |

## 2. Inventario Clasificado de Módulos y Primitivas Reutilizables

| ID Módulo | Ruta | Capa | Categoría | Primitivas Exportadas | Se Apoya En | Estado / Evidencia Empírica |
|---|---|---|---|---|---|---|
| `holdout_guard` | `edgelab/research/holdout_guard.py` | `L0_NUCLEO_SELLADO` | `inferencia_embudo_multiagente` | `HOLDOUT_PRIMERA_SESION_INT`, `verificar_corte_holdout` | — | **NUCLEO** |
| `costos` | `edgelab/costos.py` | `L0_NUCLEO_SELLADO` | `motor_grilla_simulacion` | `friccion_viaje`, `COSTOS_CANONICOS` | — | **NUCLEO** |
| `fuentes_ticks` | `edgelab/research/fuentes_ticks.py` | `L1_DATOS_Y_DETECTORES_PARIDAD` | `motor_grilla_simulacion` | `contexto_m1`, `bloques_dukascopy`, `sesiones_disponibles` | `holdout_guard` | **NUCLEO** |
| `zonas_gaps` | `edgelab/research/zonas_gaps.py` | `L1_DATOS_Y_DETECTORES_PARIDAD` | `sensores_zonas_volumen_gaps` | `_detectar_gaps_y_clusters_nb`, `disparos`, `niveles`, `niveles_lote` | `fuentes_ticks`, `grilla_generica` | **ACTIVO**: ZGAP-NQ: 18/20 pistas positivas (+5,2 pts/sesión, p=0,04); base de CVGAP-NQ y CVGAP-CFD-NQ. |
| `corredor_vol_gaps` | `edgelab/research/corredor_vol_gaps.py` | `L1_DATOS_Y_DETECTORES_PARIDAD` | `detectores_impulso_corredor` | `_extraer_cajas_amarillas_nb`, `_precomputar_eventos_nb`, `disparos`, `niveles`, `niveles_lote` | `zonas_gaps`, `fuentes_ticks`, `grilla_generica` | **PROMOVIDO_ACTA**: CVGAP-NQ (+19,13 USD/op OOS, ACTA_HOLDOUT) y CVGAP-CFD-NQ (+10,50 USD/op OOS, ACTA_HOLDOUT); CVGAP-ES PISTAS_VIVAS (+24,47 pts/op en p3). |
| `u1_racimos_grilla` | `edgelab/research/u1_racimos_grilla.py` | `L1_DATOS_Y_DETECTORES_PARIDAD` | `sensores_zonas_volumen_gaps` | `racimos_desde_zonas`, `disparos`, `niveles`, `niveles_lote` | `u1_zonas`, `u1_indaga`, `u1_oro` | **PROMOVIDO_ACTA**: U1-RACIMOS-GRILLA-NQ (+32,83 pts/op OOS, ACTA_HOLDOUT) y U1-RACIMOS-GRILLA-ES (+5,95 pts/op, ACTA_HOLDOUT). |
| `u1_zonas_bt2` | `edgelab/research/u1_zonas_bt2.py` | `L1_DATOS_Y_DETECTORES_PARIDAD` | `sensores_zonas_volumen_gaps` | `disparos`, `niveles`, `niveles_lote` | `u1_zonas`, `u1_indaga` | **PROMOVIDO_ACTA**: U1-ZONAS-BT2-ES (+2,47 pts/op OOS, ACTA_HOLDOUT) y U1-ZONAS-BT2-NQ (+15,02 pts/op, ACTA_HOLDOUT). |
| `otr_930_sweep` | `edgelab/research/otr_930_sweep.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `rangos_sesiones_horarios` | `_offset_ny_segundos_nb`, `_extraer_eventos_otr930_nb`, `disparos`, `niveles`, `niveles_lote` | `zonas_gaps`, `corredor_vol_gaps`, `u1_oro` | **PISTAS_VIVAS**: OTR930-NQ (+5,12 pts/op canasta OOS, mejor pista +29,97 pts/op) y OTR930-CFD-NQ (+3,03 pts/op canasta OOS, PISTAS_VIVAS). |
| `oro_almuerzo_ruptura` | `edgelab/research/oro_almuerzo_ruptura.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `rangos_sesiones_horarios` | `_offset_madrid_segundos_nb`, `_extraer_eventos_almuerzo_oro_nb`, `disparos`, `niveles`, `niveles_lote` | `u1_oro`, `zonas_gaps` | **PISTAS_VIVAS**: ORO-ALM-CFD (+0,42 pts/op canasta OOS, pista +13,62 USD/op p=0,0386) y ORO-ALM-GC (+14,00 USD/op en mejor pista OOS). |
| `tori_trend_toque3` | `edgelab/research/tori_trend_toque3.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `lineas_tendencia_estructura` | `_extraer_eventos_tori_trend_nb`, `disparos`, `niveles`, `niveles_lote` | `zonas_gaps`, `corredor_vol_gaps`, `u1_oro` | **ACTIVO**: Implementado desde TORI_TRADES_STOPPING_TIME_TRENDLINES_20261026.md con controles sintéticos y causalidad. |
| `asia_bos_gaps` | `edgelab/research/asia_bos_gaps.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `rangos_sesiones_horarios` | `_extraer_eventos_asia_bos_nb`, `disparos`, `niveles`, `niveles_lote` | `otr_930_sweep`, `zonas_gaps`, `corredor_vol_gaps`, `u1_oro` | **ACTIVO**: Implementado desde el catálogo de guardados de Instagram (Tier-1 #2 y #11). |
| `confluencia_cvgap_racimos` | `edgelab/research/confluencia_cvgap_racimos.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `detectores_impulso_corredor` | `_extraer_confluencia_cvgap_racimos_nb`, `disparos`, `niveles`, `niveles_lote` | `corredor_vol_gaps`, `u1_racimos_grilla`, `u1_zonas_bt2`, `otr_930_sweep`, `zonas_gaps` | **ACTIVO**: Híbrido directo de las 6 campañas con ACTA_HOLDOUT (CVGAP-NQ, CVGAP-CFD-NQ, RACIMOS-NQ/ES, BT2-NQ/ES) y OTR930. |
| `regimen` | `edgelab/research/agente/regimen.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `filtros_regimen_macro_escala` | `VARIABLES_REGIMEN`, `por_vela`, `agregar` | `grilla_generica` | **NUCLEO** |
| `u1_oro_escala` | `edgelab/research/u1_oro.py` | `L2_PRIMITIVAS_Y_REGIMEN` | `filtros_regimen_macro_escala` | `escala_por_mes`, `RANGO_M1_202609` | — | **NUCLEO** |
| `grilla_generica` | `edgelab/research/grilla_generica.py` | `L3_MOTOR_GRILLA_Y_SIMULACION` | `motor_grilla_simulacion` | `Variable`, `correr`, `simular_ops`, `n_celdas`, `resumen_e0` | `grilla_masiva`, `sim`, `costos` | **NUCLEO** |
| `embudo` | `edgelab/research/embudo.py` | `L4_INFERENCIA_EMBUDO_Y_CANASTA` | `inferencia_embudo_multiagente` | `Embudo`, `problemas_campana`, `avanzar_todas` | `grilla_generica`, `linaje`, `holdout_ventanas`, `libro_lord` | **NUCLEO** |
| `orquestador_multiagente` | `edgelab/autopilot/orquestador_multiagente.py` | `L5_AUTOPILOT_MULTIAGENTE_ESPIRAL` | `inferencia_embudo_multiagente` | `TOPOLOGIA_DEBIAN_V2`, `armar_contexto_amplio_espiral`, `evaluar_velocidad_cuidado`, `auditar_propuesta_sonnet` | `sincronizador_ramas`, `auditor_alineacion`, `catalogo_espiral` | **NUCLEO** |

## 3. Vía Concreta de Reutilización, Traslado y Unión de Módulos en Espiral

1. **Consulta Obligatoria Pre-Diseño (`catalogo_espiral.resumen_rapido_para_agente()` + `tools/existente.py buscar`)**:
   Antes de proponer o programar un módulo, el agente consulta qué detectores (`L1`), primitivas de sesión/estructura (`L2`) y variables de régimen (`regimen.py`) ya existen y qué celdas sobrevivieron en `APRENDIZAJES_ESPIRAL.md`.
2. **Traslado Multi-Instrumento (`Cross-Asset & Cross-Feed Transfer`)**:
   Toda primitiva validada en un activo (ej. `corredor_vol_gaps` en `NQ`) se traslada parametrizando sus cortes por cuantiles empíricos de `E0` (`Variable(..., cuantiles=3)`) o por `u1_oro.escala_por_mes(ctx)` para conservar invarianza de escala en `ES`, `GC`, `YM`, `6E` y cruces `CFD -> Futuro`.
3. **Unión y Composición de Primitivas (`L1 + L2 -> Nueva Familia`)**:
   Un experimento nuevo une en su pre-cómputo `@njit` dos o más primitivas ortogonales ya probadas (por ejemplo, `confluencia_cvgap_racimos.py` une la Caja Amarilla de `corredor_vol_gaps.py` con la densidad de racimos de `u1_racimos_grilla.py` y el barrido `otr_930_sweep.py`).
4. **Promoción Automática al Catálogo (`promover_bloque_espiral`)**:
   Cuando una campaña alcanza `ACTA_HOLDOUT.json` o `PISTAS_VIVAS` con media positiva en OOS, sus funciones `@njit` y su firma de régimen quedan promovidas en `CATALOGO_MODULOS_ESPIRAL.json` y en `APRENDIZAJES_ESPIRAL.md`.
