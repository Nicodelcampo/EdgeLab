# Reporte de investigación (11) — gate de 200 sesiones y plan de expansión

Mientras se repite el censo de integridad después del purge, se cerró el
segundo bloqueo ya medido: EXPLORE-001 exige 200 sesiones y el universo actual
entrega 193.

`edgelab/research/explore_sample_gate.py` convierte ese requisito en autoridad
ejecutable. Con 193 devuelve:

```
status = BLOCKED_INSUFFICIENT_SESSIONS
observed_sessions = 193
minimum_sessions = 200
deficit_sessions = 7
may_start_explore = false
```

El gate rechaza fechas inválidas y sesiones duplicadas, y declara explícitamente
que holdout, cuarentena y duplicados no pueden rellenar el déficit. No accede a
outcomes.

## Caminos válidos

1. Incorporar al menos siete sesiones históricas limpias anteriores al holdout,
con front-month medido y la batería completa en PASS.
2. Si esa historia no existe, recalibrar potencia de punta a punta y tramitar una
enmienda pre-outcome del mínimo. No se permite cambiar 200 por 193 sólo porque
es lo disponible.

La vía preferida es ampliar historia. Para recuperar 6E 09-25 de forma canónica
haría falta el contrato anterior suficiente para medir su cruce de volumen; no
se debe estipular una fecha por analogía. Otra vía es extender hacia atrás el
primer contrato ya medido, siempre que siga dentro de su ventana front-month y
pase integridad.

## Orden operativo

1. gate de integridad global PASS;
2. universo outcome-free regenerado;
3. gate de tamaño >=200;
4. censo de primeros toques;
5. congelación H1-H3;
6. campaña EXPLORE-001.

**Aporte al referente:** el mínimo dejó de ser prosa vulnerable a una excepción
de conveniencia. El déficit de siete sesiones ahora bloquea mecánicamente la
campaña hasta que exista más evidencia o una enmienda de potencia defendible.
