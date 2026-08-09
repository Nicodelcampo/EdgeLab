# Incidentes de artefactos — no son evidencia

Lo que está acá **no se cita, no se compara y no cuenta como corrida**. Se
conserva porque borrar un artefacto defectuoso borra también la prueba de que
existió.

## `INCIDENTE_artefacto_declaro_outcomes_sin_leer_precios__f078322ed851.json`

**2026-08-09.** Primera invocación de `--fase outcomes` del runner de H1.

Declara `outcomes_accessed: true` y **no leyó un solo precio**. El runner abortó
en el guard —`bar_close is None`, porque un arreglo de `close_ticks` → `close_t`
no había llegado al archivo— y las únicas lecturas de precio están *después* de
ese guard.

El campo se derivaba de **la fase pedida**, no del hecho. Un campo que dice «se
miraron resultados» cuando no se miró ninguno es peor que no tenerlo: **es el
único registro de haber cruzado la puerta**, y contaminó la trazabilidad del
único cruce que importa.

**Dictamen del auditor:** aborto pre-outcome por defecto del runner, **no**
contacto válido con outcomes. H1 no muere. Cero outcomes observados, holdout
intacto.

Corregido en el runner: `outcomes_accessed = (precios_leidos > 0)`, con
`fase_pedida` y `precios_leidos` publicados por separado.
