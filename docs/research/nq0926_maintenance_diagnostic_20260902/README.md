# Diagnóstico NQ 09-26 — anomalía de mantenimiento, 2026-09-02

**`execution_status = COMPLETE`. Dos hipótesis descartadas por evidencia; una queda
fuertemente respaldada pero sin confirmación directa.**

Corrida autorizada por Nico. Kernel `nq0926-maintenance-diagnostic-20260902`,
code_commit `e7ec0e4a01f1ae15ff23b098dae26bc76acba3d4`, parquet sha256
`1030715b…fb64f`. Relee sólo `NQ_09-26_ticks.parquet` (6.235.464 filas).
`outcomes_accessed=false`, `holdout_accessed=false`. No toca EF0 ni el indicador.

## Qué mostró el diagnóstico

- **363.601 ticks** (5,83 % del archivo), **398.066 de volumen**, en
  **exactamente 16:00:00–16:59:59 CT**.
- Concentrados en **9 días hábiles consecutivos: 17, 18, 22, 23, 24, 25, 26, 29 y
  30 de junio de 2026**. Ningún fin de semana. Cobertura densa de los 60 minutos
  (700–3.400 ticks por minuto).
- **`ts_local_ns - ts_utc_ns` = 0 en las 6.235.464 filas** (100 %).
- Procedencia: **un solo `source_file`** (`NQ 09-26.Last.txt`), `source_row`
  idéntico a `sequence` (confirma P-28: `sequence` es índice de fila del origen),
  y rangos **contiguos y densos sin huecos** (p. ej. 17-jun: filas 1.394.185 a
  1.480.526 = 86.342, igual al `tick_count`). El archivo **termina** en la fila
  6.235.463, dentro de esa ventana del 30-jun.

## Hipótesis descartadas por evidencia

| hipótesis | veredicto | evidencia |
|---|---|---|
| `UTC_LOCAL_FIELD_SEMANTICS` | **descartada** | `ts_local_ns == ts_utc_ns` en el 100 % de las filas: no hay ningún offset de huso que explique el corrimiento |
| `RECUT_ROW_SELECTION` | **descartada** | el archivo **local pre-recorte** (`data/nt8/NQ_parquet/NQ_09-26_ticks.parquet`, 14,9 M filas, sha distinto) presenta el mismo fenómeno (~6,8 % de ticks en hora 16 CT entre el 17 y el 30 de junio). No lo introdujo el re-corte del holdout |

## Hipótesis dominante (no confirmada directamente)

**El archivo `NQ 09-26.Last.txt` fue exportado de NT8 con una plantilla de sesión
distinta a la de los otros cuatro contratos** — una que no excluye la ventana de
mantenimiento 16:00–17:00 CT.

Comparación de cada contrato **durante su propio período de liderazgo** (muestreo
1/301 sobre los parquets locales, sólo conteo de hora CT, target-free):

| contrato | mes líder | h15 CT | **h16 CT** | h17 CT |
|---|---|---|---|---|
| NQ 09-25 | 08/2025 | 1.098 | **0** | 313 |
| NQ 12-25 | 10/2025 | 1.360 | **0** | 364 |
| NQ 03-26 | 01/2026 | 1.011 | **0** | 396 |
| NQ 06-26 | 04/2026 | 1.228 | **0** | 650 |
| **NQ 09-26** | 06/2026 | 705 | **1.210** | 450 |

Cuatro contratos tienen el hueco 16:00–17:00 CT **perfectamente limpio**; el
quinto no lo tiene, y de hecho registra más actividad a las 16 CT que a las 15 CT.
Es una diferencia estructural **entre archivos**, no de mercado.

**No se adjudica causa formalmente**: confirmarla exige inspeccionar la
configuración de exportación de NT8 y/o el `.Last.txt` original, que no se hizo.
`root_cause_status` sigue en `UNRESOLVED` en el artefacto.

## Consecuencia para el régimen contractual

**El roll del 16-jun-2026 a NQ 09-26 NO está contaminado**: la anomalía arranca el
**17**-jun, y la señal causal de ese roll usa el volumen del **15**-jun (D-1). Ni el
15 ni el 16 aparecen entre las 9 fechas afectadas.

Pero **cualquier medición de volumen o actividad de NQ 09-26 entre el 17 y el 30 de
junio de 2026 no es comparable con la de los otros cuatro contratos sin normalizar
la ventana de sesión** — incluye una hora que los demás archivos no registran. Eso
alcanza al volumen diario que alimenta el manifiesto de régimen para esas 9 fechas.
