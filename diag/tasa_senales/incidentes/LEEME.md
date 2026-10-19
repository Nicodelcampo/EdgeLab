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

## `INCIDENTE_altura_de_zona_con_ruido_de_redondeo__*` (2 archivos) y `_v1__*`, `_offbyone_ancho_nulo__*` (3 archivos)

**2026-08-10.** Dos defectos independientes en cómo F1.1 (`F1_nulo_zonas_
aleatorias.py`) y sus derivados (`F1.1_seguimiento.py`,
`F_barspec_tick25.py`) construían la geometría de las zonas **nulas**.

**Defecto 1 — ruido de banker's rounding.** `bigtrap2.py:202-203` construye la
geometría con relleno de MEDIO tick (`zone_lo = lo_tick*ts - ts/2`), así que
para una zona de una fila `top/tick_size` y `bottom/tick_size` caen **exacto**
en el límite de redondeo `.5`. `round(top/ts) - round(bottom/ts)` da 0, 1 **o**
2 para una altura que es SIEMPRE exactamente 1 tick por construcción —
dependiendo de la paridad de la fila y del error de punto flotante al
representar `T ± 0.5`. `store.py::_core()` ya conocía este problema y lo evita
midiendo en unidades de medio-tick; F1.1 no lo hacía.

**Defecto 2 — off-by-one al reconstruir el rango.** Independiente del anterior:
al construir el nulo con `lo_n = centro - alto//2; hi_n = lo_n + alto`, el
rango `[lo_n, hi_n]` tiene `alto + 1` ticks, no `alto` — el nulo quedaba
sistemáticamente un tick más ancho (más fácil de tocar) que la zona real que
debía imitar. La forma correcta es `hi_n = lo_n + alto - 1`.

**Los dos archivos `_v1__*` / `_offbyone_ancho_nulo__*` son el estado
intermedio** (defecto 1 corregido, defecto 2 todavía presente) — se conservan
también, no sólo el original con los dos defectos, porque cada paso de la
corrección es parte de la evidencia de que se verificó y no se asumió.

**Impacto verificado, no asumido:** el defecto 1 solo (comparado contra el
original) movió la tasa de toque del nulo-B **+0,4 puntos porcentuales**
(51,38 % → 51,8 %) — ruido, no un desplazamiento material. El efecto del
defecto 2 se documenta con números en
`docs/CORRECCION_ALTURA_ZONA_2026-08-10.md` una vez cerradas las corridas con
ambos defectos resueltos. Fix aplicado en las tres funciones consumidoras;
`censo_zonas_completo.py` y `F1_supervivencia_y_depletion.py` (F0.2 y F1.2) NO
tenían ninguno de los dos defectos — usan `(top-bottom)/tick_size`, una resta
que cancela el relleno de medio-tick sin necesidad de redondear por separado.
