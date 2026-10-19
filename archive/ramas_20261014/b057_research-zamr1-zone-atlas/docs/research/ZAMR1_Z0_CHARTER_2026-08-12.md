# ZAMR-1 — contrato de implementación Z0

**Fecha:** 2026-08-12  
**Rama:** `research/zamr1-zone-atlas`  
**Base:** `research/bigtrap2-local-displacement-null@1b8e168ebac9ca45d4d998bc6ee66bb920f4c282`  
**Estado:** `Z0_EXECUTABLE_TARGET_FREE`  
**Outcomes/P&L/holdout:** cerrados

## Decisión

ZAMR-1 construirá un atlas multiresolución reutilizable. BigTrap2 es la primera familia. aVolCellPOI2 se registra desde Z0, pero no entra en el piloto Z1 hasta superar su gate propio. La combinación entre indicadores queda cerrada hasta que ambos sobrevivan individualmente.

La fuerza bruta se permite para enumerar y materializar configuraciones registradas. La inferencia no será un producto cartesiano plano: singles, familias de parámetros, pares, tríos y cruces de indicador se habilitan por gates sucesivos.

## Alcance autorizado

- documentación, schemas y tests;
- validación estática fail-closed;
- construcción de `events_long` y `zones_long`;
- benchmarks target-free de tiempo, RAM, disco, cobertura, geometría y lifecycle;
- piloto de 20–30 sesiones en `tick:5,10,25,50,100,200` con BigTrap2 default.

## Prohibido en Z0/Z1

- retornos futuros, targets favorables/adversos y P&L;
- stops, targets, Sharpe o selección económica;
- cualquier fila del holdout;
- mezclar aVolCellPOI2 con BigTrap2;
- seleccionar el mejor frame por un outcome;
- subir ticks a Kaggle sin `license_decision=RAW_ALLOWED`;
- tocar la rama adjudicadora F2.7.

## Correcciones respecto del draft multiframe v1

1. Z0 es estructural: no exige `targets_long`, folds ni OOF antes de que exista un protocolo predictivo.
2. La frontera se alinea con F2.7: `2026-06-30T22:00:00Z`, también materializada como nanosegundos para que el validador no dependa de parseos ambiguos.
3. Se agrega `zones_long` como tabla canónica de lifecycle.
4. La decisión de licencia forma parte de la identidad del dataset.
5. La grilla se expresa como DAG: parámetros inactivos y combinaciones sin sentido son FAIL, no celdas nuevas.
6. Quantile y RobustZ de aVolCellPOI2 son ramas mutuamente excluyentes.
7. El soporte de cola de aVol se valida mecánicamente: `min_cell_samples >= ceil(10/(1-p))`.

## Entregables Z0

- `specs/zamr1_structural_contract_v0.json`;
- `specs/zamr1_parameter_registry_v0.json`;
- `edgelab/research/zamr1/parameter_dag.py`;
- `edgelab/research/zamr1/structural_contract.py`;
- tests truth-known;
- Notebook Kaggle `00` en un commit posterior, después de que los contratos pasen tests locales/CI.

## Gate de salida Z0

Z0 sólo pasa si:

- todos los tests sintéticos pasan;
- cero combinaciones inválidas se canonicalizan;
- la frontera temporal, licencia y flags de outcomes fallan de forma cerrada;
- el contrato puede validarse sin datos reales;
- una auditoría independiente revisa spec, validador y tests antes del piloto.
