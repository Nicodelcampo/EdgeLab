# Canal 032 — autorización de diagnóstico completo de paridad aVolClusterPOI NQ

**Fecha:** 2026-09-01

## Token de autorización

Nico autorizó explícitamente:

`AUTHORIZE_AVOLCLUSTER_NQ_FULL_PARITY_DIAGNOSTIC_PREHOLDOUT_V1`

## Alcance autorizado

Corrida exclusivamente **target-free y pre-holdout** para completar el diagnóstico de
paridad de `aVolClusterPOI` NQ 06-26. Se autoriza:

1. exportar/reconstruir todos los bloques Python, incluidos `CREATE` y `ABSTAIN`;
2. censar los 48 `MISSING_IN_PYTHON` pendientes;
3. corregir el export diagnóstico NT8 para publicar:
   - `best_candidate_score` real aunque el bloque abstenga;
   - `hist_samples` real entre 0 y 19 cuando no alcanza el mínimo;
4. comprobar unicidad de `bar_close_time` o usar clave compuesta sin sobrescritura;
5. repetir el censo de los 19 + 57 con las etiquetas corregidas;
6. comparar los 12 `ABSTAIN_NO_HISTORY` sesión/bucket/FIFO por ambos lados;
7. vincular los dos `CREATE` a `nt8_id`, geometrías en una unidad común y condición
   exacta de rechazo del matcher;
8. ejecutar el replay contrafactual: lógica Python sobre `blockCells`, historial y
   threshold NT8, verificando decisión y geometría NT8;
9. publicar el censo completo de 124 residuos y sus denominadores.

## Correcciones obligatorias antes de leer el resultado

- `build_censo.py` debe usar rutas relativas a los inputs commiteados.
- Ningún diccionario puede sobrescribir timestamps duplicados silenciosamente.
- `EDGE_LEVELS_MISSING` sólo se usa si se verifica que los niveles exclusivos están en
  el borde; de otro modo usar `CELL_LEVEL_SET_DIFF`.
- Distinguir `input_diff`, `history_state_diff`, `algorithm_replay_diff` y
  `matcher_rejection` como dimensiones separadas, no clases mutuamente excluyentes.
- Los 48 `MISSING_IN_PYTHON` forman parte del residual; no llamar “completo” al censo
  que los omita.

## Salidas mínimas

1. JSON/CSV de 124 residuos, una fila por caso.
2. Resumen con denominadores de población y tasas separadas:
   - detección Python→NT8;
   - detección NT8→Python;
   - geometría entre eventos enlazados;
   - warmup/historia;
   - matching;
   - replay algorítmico.
3. Hashes y pins de código/datos.
4. Lista explícita de casos `UNRESOLVED`.

## Fuera de alcance

- outcomes, retornos, MAE/MFE o P&L;
- holdout;
- cambio de comportamiento del `.cs` de producción;
- aprobación de tolerancia;
- reclasificación automática del gate;
- embudo de resultados.

Al terminar, el auditor calcula la distribución residual y presenta una propuesta de
paridad representativa. La decisión de aceptación sigue siendo de Nico.

**Aporte al referente:** autoriza exactamente el cómputo necesario para convertir el
subconjunto 19+57 en un censo de paridad completo, sin abrir outcomes ni permitir que
la instrumentación diagnóstica modifique el contrato que está siendo medido.
