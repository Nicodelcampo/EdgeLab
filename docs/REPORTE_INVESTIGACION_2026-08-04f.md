# Reporte de investigación (6) — población censada vs población primaria

## Hallazgo

El censo `post_sepmin.py` cuenta `created_ms` de zonas y aplica decongestión a
las creaciones. La ESPEC vigente de EXPLORE-001 §1.1 define otra población:
primer toque de cada zona, excluyendo el toque en la barra de creación.

Por lo tanto, aun un censo COMPLETE no puede usarse automáticamente para
congelar H1–H3 de la ESPEC actual. Son tasas de poblaciones distintas. Hacerlo
convertiría una medición de frecuencia de creación en una estimación de
frecuencia de eventos primarios.

## Contención implementada

El manifiesto del censo declara ahora:

```
event_anchor_policy = zone_created_ms
population_note = cuenta creaciones; no equivale automaticamente a first_touch
```

Se agregó `explore_preflight.audit_event_policy()`. El preflight devuelve
`BLOCKED_EVENT_POLICY_MISMATCH` y `may_freeze_hypotheses=false` cuando la
población primaria no coincide con la censada.

Regresiones cubren el bloqueo creaciones→primer toque y el PASS cuando ambas
políticas son idénticas.

Verificación sandbox:

```
py_compile: PASS
EXPLORE_EVENT_POLICY_PREFLIGHT_PASS
```

## Decisión pendiente

No corresponde elegir silenciosamente entre:

1. mantener la ESPEC de primer toque y volver a medir tasas sobre primeros
toques admisibles;
2. enmendar la ESPEC para usar creación como evento primario, justificando qué
regularidad económica se prueba y cómo se evita entrada no operable;
3. usar el censo de creaciones sólo para capacidad computacional, sin emplearlo
para seleccionar H1–H3.

La opción 1 conserva mejor la hipótesis existente y es la recomendación
provisional, pero exige un censo outcome-free de primeros toques.

**Aporte al referente:** se impidió iniciar la primera campaña con una tasa de
otra población. Esto evita congelar hipótesis sobre un denominador que no
corresponde al evento que luego decidirá el edge.
