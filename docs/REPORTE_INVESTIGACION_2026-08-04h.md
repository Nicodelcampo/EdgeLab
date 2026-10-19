# Reporte de investigación (8) — población outcome-free de primeros toques

## Frente independiente

Mientras Claude regenera y audita los datos limpios, se avanzó sobre el bloqueo
de población detectado entre el censo de creaciones y la ESPEC de EXPLORE-001.

BigTrap2 ya emite lifecycle suficiente para reconstruir la población correcta:
`ZONE_CREATED`, `ZONE_TOUCHED`, `zone_id`, `bar_index`, `unix_ms` y
`touch_count`. No hace falta acceder a outcomes.

## Implementación

`edgelab/research/first_touch_population.py` extrae exactamente un evento por
zona: el `ZONE_TOUCHED` con `touch_count == 1`.

La extracción falla cerrado ante:

- primer toque sin creación correspondiente;
- creación o primer toque duplicados;
- toque en la misma barra o antes de la barra creadora;
- timestamp de toque no posterior a la creación;
- lifecycle o tipos incompletos.

Cada fila resultante declara `outcomes_accessed=false` y conserva identidad de
zona, barras, timestamps y clase de zona.

Se agregaron regresiones para primer toque válido, zona nunca tocada,
anti-look-ahead, huérfanos y duplicados.

## Alcance

Esto todavía no ejecuta el censo completo ni decide `sep_min` para la nueva
población. El extractor permite medir la tasa primaria declarada sin cambiar la
ESPEC. La política de decongestión debe quedar explícita antes de usar estas
tasas para congelar H1–H3; no se heredó silenciosamente la de creaciones.

**Aporte al referente:** la población primaria dejó de ser sólo prosa. Existe
una reconstrucción ejecutable y fail-closed que puede auditarse antes de mirar
resultados.
