# Reglas de papel congeladas sobre M1 de 12 años (pre-registro, 2026-11-15)

Estado: VIGENTE. Etapa EF4 (confirmación fuera de muestra de reglas CONGELADAS: no hay búsqueda nueva). North Star sha256
16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345. Herramienta: `tools/papel_m1.py`. Fuente: `M1DK:NQ_M1_dukas` (M1 de
Dukascopy USATECH convertidas a 4 ticks por barra en el orden conservador; `edgelab/research/fuentes_ticks.py::bloques_m1dk`), costos de NQ.

## Qué se mide
Las reglas de papel de `config/cartera/altas.json` que dependen sólo del precio, con su módulo, celdas, cortes y tope tal cual:
ASIA-NQ (ASIA_BOS_GAPS), OTR930-NQ (OTR_930_SWEEP), TORI-NQ (TORI_TREND_TOQUE3), RANGO0100-NQ (RANGO_ASIA0100; dada de baja por réplica
≤ 0). Etapa ANALIZAR_REGLA (operaciones por celda y canasta). Quedan afuera las que dependen del perfil de volumen por nivel (CVGAP,
CONF-CVR, U1-ZONAS) y U1-CRUZADO (sus zonas se arman desde ticks; va aparte, con su propia validación).

## Orden y criterio (fijados antes)
1. **Validación de la fuente** (ago-2025 → sep-2026): mismas reglas sobre M1DK contra lo medido sobre ticks reales de NQ en el mismo
   tramo (`ops_desarrollo` de cada ficha y las réplicas). Pasa si la media por operación en R/pts y el signo coinciden dentro del error
   (diferencia < 1 error estándar) y la correlación de P&L por sesión es > 0,5. Si no pasa, esa familia NO se mide en el largo.
2. **Largo** (2012-01 → 2019-12, 2020 → 2023, 2024-01 → 2025-07): una sola vez por regla. Veredicto: media neta > 0 con IC90 por sesiones
   que excluye el cero en el tramo total, y signo positivo en los tres sub-tramos. Una regla que falle en el largo sale de papel.
3. Sin elegir nada por el resultado: las celdas y cortes no cambian; no se suman ni se sacan reglas después de ver.

## Riesgos
CFD (USATECH) en lugar del futuro NQ: diferencia de base y horario; el orden conservador dentro de la barra penaliza a las reglas de
stop corto; volumen de ticks (proxy). Por eso la validación va primero.
