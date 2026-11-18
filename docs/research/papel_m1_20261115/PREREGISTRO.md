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

## Enmienda 1 (2026-11-15, antes de ver resultados; Nico: «son de régimen, no van a replicar hacia atrás»)
Principio «edges actuales» (ATJ-24, 2026-10-22): el pasado no mata. Se reemplaza el punto 2:
- El largo **NO es criterio de baja**. Ninguna regla sale de papel por rendir mal en 2012–2025; la baja sólo sale de datos recientes no
  usados y del forward (como hasta hoy).
- El largo se usa para lo que sí puede responder, con la regla congelada:
  a. **Mapa de régimen**: rendimiento por trimestre en 12 años y su relación con variables de régimen declaradas ANTES de mirar —
     volatilidad realizada de 20 días (terciles), tendencia de 60 días (signo de la pendiente), rango nocturno relativo y horario
     (DST/no DST)—. Pregunta: ¿en qué estados funciona y en cuáles no?
  b. **Prueba de régimen walk-forward**: con esas variables, una regla de encendido simple (operar sólo en los estados donde el
     rendimiento de los 12 meses previos fue > 0) se evalúa hacia adelante trimestre a trimestre en los 12 años, contra operar siempre y
     contra estados al azar. Si encender por régimen mejora fuera de muestra, la regla tiene un régimen identificable en tiempo real
     (requisito de las «canastas por régimen»); si no, el régimen no se puede detectar a tiempo.
  c. **Frecuencia del régimen**: qué fracción del tiempo histórico estuvo «encendido» (cuánta plata se puede esperar por año).
- Multiplicidad: las 4 variables × 4 reglas se registran en el contador; la prueba (b) usa el motor offline de régimen
  (`edgelab/research/regimen_offline.py`, guía `docs/research/GUIA_REGIMEN_PARA_AGENTE_20261107.md`) con su nulo de signo por sesión.
- La validación de la fuente (punto 1) no cambia.

## Enmienda 2 (2026-11-15): otros mercados
ASIA-NQ y OTR930-NQ congeladas (mismas celdas y cortes) sobre M1 de S&P (`M1DK:SP_M1_dukas`, costos de ES) y Dow (`M1DK:DJ_M1_dukas`,
costos de YM), 2012 → 2026-09 completo. Requisito 7 del contrato (≥ 60 % de los mercados de su clase con R > 0, sin re-optimizar) y
prueba de transferencia del régimen de ASIA: ¿la dosis noche baja < media < alta se repite en S&P y Dow? (pista F-ASIA-NQ-NOCHE-MOVIDA).
Los cortes están en puntos de NQ: en S&P y Dow las celdas que dependen de magnitudes absolutas pueden no ser equivalentes; se informa.

## Enmienda 3 (2026-11-15): ASIA con noche alta en futuros reales y OTR930 en Dow
- ASIA-NQ congelada sobre ticks REALES de YM (`sensor YM`, costos de YM), ago-2025 → sep-2026 (desarrollo; el holdout no se toca): ¿el régimen
  de noche alta (variable del Dow CFD, misma sesión) separa días ganadores de perdedores también en el futuro real? Filtro congelado:
  tercil superior del rango nocturno 18:00→09:30 NY contra los 250 días previos (`edgelab/research/papel_regimen.py::variables`).
- OTR930-NQ congelada en Dow M1 2012 → 2026-09 (otros mercados y mapa de régimen).
- 2 pruebas más en el contador.

## Enmienda K40 (2026-11-18)
- **Qué pasó:** VALIDACION y LARGO se midieron con el motor de la grilla, que cobraba el stop en el pseudo-tick extremo de la vela M1.
- **Corrección:** se relanzan las mismas fichas, tramos y criterios con el motor corregido (stop en su nivel salvo un hueco en la apertura;
  test de calibración `tests/research/test_ejecucion.py::test_motor_grilla_m1_calibrado`).
- **La v1:** queda en `descartada_v1/`.
