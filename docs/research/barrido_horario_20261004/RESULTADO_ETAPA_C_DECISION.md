# Etapa C — decisión única de la celda GC 04:15 en oro spot (2026-07-01 a 2026-09-30)

Reglas: `PREREGISTRO_ETAPA_C_GC_SPOT.md` (con enmiendas C1 y C2) y enmienda C3 de `docs/research/REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md` (fuente: dataset unificado de Dukascopy). Herramienta: `tools/barrido_horario_etapa_c_parquet.py` (reutiliza la función `one` de la etapa C). Salida cruda: `etapaC_spot_decision.json`. Celda congelada (`config/gc_cell_0415/gc_cell_v1.json`), semilla 20261008, 20.000 sorteos, unilateral, **una sola vez** sobre la ventana completa. No se leyó el 1 de octubre ni nada posterior (holdout formal).

## Paso 1 — calibración de la fuente (reincorporado)
La enmienda C1 lo había omitido por falta de datos; el dataset unificado ya cubre abril a junio de 2026, así que se hizo **antes** de mirar la ventana de decisión, tal como estaba en el pre-registro original.

| Criterio | Umbral | Resultado | Pasa |
|---|---|---|---|
| Concordancia del signo de «subida de los 15 min previos» (62 sesiones) | ≥ 85 % | **96,8 %** | sí |
| Correlación del neto de las sesiones en que ambas fuentes disparan (34 operaciones) | ≥ 0,6 | **0,997** | sí |

La fuente spot es equivalente a GC para esta celda (consistente con `RESULTADO_EQUIVALENCIA_M1.md`).

## Paso 2 — prueba principal: **REPLICA**
66 sesiones elegibles (ninguna descartada; demora máxima de salida 2,6 s; spread mediano USD 0,57, ≈ 5,7 ticks de GC, aproximadamente el doble del de COMEX).

| | Operaciones | Neto medio (ticks de GC) | Desvío | Aciertos | z | p (unilateral) |
|---|---:|---:|---:|---:|---:|---:|
| **Celda congelada** (corto tras subida de 15 min) | 40 | **+25,6** | 39,1 | 75 % | 4,00 | **5,0 × 10⁻⁵** |

Regla: media neta > 0 y p ≤ 0,05 → **Replica**. Por mes (descriptivo): julio +16,7 (14 operaciones), agosto +32,2 (13), septiembre +28,7 (13).

## Pruebas secundarias (descriptivas, sin regla de decisión)
| | Operaciones | Neto medio | Observación |
|---|---:|---:|---|
| Corto **sin condición** a las 04:15 | 66 | **+24,1** | z = 4,98, p = 5,0 × 10⁻⁵ |
| Largo tras bajada (espejo) | 26 | −34,0 | consistente con un sesgo vendedor en la franja |

## Lectura
1. **La celda replica fuera de muestra** (datos que no se usaron para elegirla, otro mercado de oro). Es un resultado favorable pre-registrado, con potencia razonable (40 operaciones).
2. **La condición «tras subida» no es lo que genera el efecto.** El corto sin condición rinde casi igual (+24,1 contra +25,6) con más operaciones y más z, y el largo tras bajada pierde. Lo que se repite parece un **sesgo vendedor de la franja 04:15 CT (10:15 en Londres)**, no el filtro. Era la advertencia de `REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md` y el resultado la refuerza.
3. El costo del spot es más duro que el de futuros: un neto positivo aquí es conservador en costo, pero la ejecución real en GC o MGC no está probada (spread, deslizamiento, fills).
4. Las sesiones del 1 al 9 de julio y del 14 al 30 de septiembre ya se habían mirado en las lecturas intermedias R1 y R2 (descriptivas, enmienda C2); la decisión se aplica una sola vez a la ventana completa, como se pre-registró.

## Qué sigue
- **No es un edge confirmado:** es una réplica en spot de una celda seleccionada con GC; falta la prueba en futuros operables. Los datos de MGC de julio (líder `MGC_08-26`, con huecos) son una vía; la otra es exportar GC de julio a septiembre desde NinjaTrader.
- Pruebas pendientes ya pre-registradas y que esperan el OK explícito: H1/H2 sobre la muestra nueva 2022-07 a 2025-07 (enmienda P1), que además separa la celda del sesgo vendedor sin condición.
- Contador global de pruebas: +2 (campaña `ETAPA-C-DECISION-spot-2026Q3`).
