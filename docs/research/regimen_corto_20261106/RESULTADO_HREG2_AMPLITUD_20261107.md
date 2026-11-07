# Resultado — H-REG-2, tercil del rango de la sesión previa

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / `regimen_corto_20261106`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: pre-registro `PREREGISTRO_HREG2_AMPLITUD_20261107.md`, escrito antes de unir el rango con el R. Corrida `python tools/hreg2_amplitud.py`. Rangos: `rangos_sesion_preholdout.json` (NQ 265, ES 280, YM 246, GC 258 sesiones de pre-holdout; ninguna `>= 20261001`). Crudo: `resultado_hreg2_amplitud.json`. Semilla 20261107, 200 permutaciones.

## Decisión

**No pasa.** El filtro congelado (ruptura y compresión sólo en el tercil bajo; absorción sólo en el tercil alto) no sube el R/op por encima de operar siempre.

| | R/op | n |
| --- | ---: | ---: |
| Siempre, en sesiones con estado | 0,037 | 1046 |
| Sólo el tercil del mapa | 0,015 | 341 |
| Delta | −0,021 |  |
| p del nulo | 0,56 |  |

Las cuatro condiciones del pre-registro no se cumplen: el delta no es positivo y p no llega a 0,05. La corrida está completa: las seis reglas del mapa en `series_cand` tienen rango de su instrumento (NQ, ES, GC). YM entra en el archivo de rangos y no entra en este test, porque `DOBLE_RETROCESO` no tiene tercil asignado.

Los números por regla no rescatan el primario. En la descripción, `PREAPERTURA-ES` y `ABSORCION-GC-2R` se ven mejor dentro de su tercil; `PREAPERTURA-NQ`, `ABSORCION-NQ-3R` y `COMPRESION-NR-GC` se ven peor. Elegir esas dos después de verlas sería otro test.

## Qué queda cerrado y qué no

Queda cerrado que, con este estado y este mapa, condicionar esas seis celdas no mejora el R/op. No queda cerrado el R diario contra ticks: el rango de la sesión no identifica la celda. El holdout no se abrió y no hay fila nueva en `docs/holdout_access_log.md`.
