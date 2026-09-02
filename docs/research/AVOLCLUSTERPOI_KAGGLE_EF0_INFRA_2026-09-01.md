# Infraestructura Kaggle EF0 — aVolClusterPOI NQ 06-26

**Estado:** `CODE_DESIGN_ONLY_NOT_RUN`  
**Alcance:** pre-holdout, target-free, sin outcomes, retornos ni P&L.  
**Indicador:** `aVolClusterPOI` Python; la paridad end-to-end NT8 continúa en `FAIL`.

## 1. Propósito

Implementar el embudo pedido por Nico de forma secuencial: el análisis inicial describe el objeto y produce preguntas para la etapa siguiente, pero no elige una configuración ni dispara otro barrido automáticamente.

La infraestructura aplica `EF0-B` del playbook transversal. Mientras la paridad formal no esté aprobada, sus resultados tienen etiqueta `PROVISIONAL_UNPARITIED_FOR_FORMAL_SELECTION`: sirven para orientar y presupuestar, no para excluir formalmente configuraciones ni atribuir comportamiento a NT8.

## 2. Reutilización del artefacto existente

EF0 no vuelve a procesar 34.203.535 ticks. Consume el bundle inmutable ya producido por `avolclusterpoi_tracedump_full_runner.py`: `all_blocks.json`, `zones.json`, `summary.json` y `sha256_manifest.json`.

Esto implementa ATJ-08: un atlas target-free se construye una vez y se consulta muchas veces. El commit fuente esperado es `eafbc0380253e029acc969e07c17ebb7912ef7ec`.

## 3. Embudo implementado

### EF0-A — contrato e integridad del bundle

Falla cerrado si el scope o commit no coinciden; los conteos o decisiones no cierran; falta una clave diagnóstica; se repite la identidad o timestamp de bloque; `history_samples != n_history_scores`; una zona queda huérfana o duplicada; o aparece cualquier campo de outcomes/P&L/MFE/MAE/precio futuro.

También explicita la semántica correcta:

```text
CREATE candidates = OFF_PRICE zones + AT_PRICE candidates
658               = 414             + 244
```

Los 658 son clusters que superaron el umbral; sólo los 414 `OFF_PRICE` se materializaron en `zones.json`.

### EF0-B — perfil estructural amplio

Mide sin mirar futuro: denominadores y tasas por 100 bloques; taxonomía de decisiones; profundidad histórica por bucket; distribución `best_score / threshold`; cantidad y ancho de clusters; distancia causal entre cierre creador y cluster `OFF_PRICE`; descomposición `AT_PRICE`/`OFF_PRICE`; cobertura/concentración por sesión; y fingerprint por timestamp y geometría.

No usa score compuesto, no rankea configuraciones y no declara una ganadora.

### Salida: tarjetas de preguntas

EF0 produce `Q-HISTORY-STATE`, `Q-THRESHOLD-PRESSURE`, `Q-GEOMETRY`, `Q-ATPRICE-OFFPRICE` y `Q-SESSION-STABILITY`. Cada tarjeta contiene los datos que motivan la pregunta y mediciones posibles. Todas se emiten como:

```text
REVIEW_REQUIRED_NOT_A_GATE
auto_execute = false
outcomes_allowed = false
```

El primer análisis sugiere qué medir después, pero no puede convertir una sugerencia en una corrida.

## 4. Contrato de EF1

Una etapa multiconfiguración futura debe entregar un plan que valide contra `specs/avolclusterpoi_ef1_plan_v1.schema.json` y fije: hash del manifiesto EF0 padre; hashes de artefactos fuente; preguntas elegidas; baseline y perturbaciones; justificación; métricas target-free; reglas de parada; costo/checkpoints; autorización para CPU; y tres cierres `auto_execute=false`, `outcomes_accessed=false`, `holdout_accessed=false`.

La grilla no se fija en esta infraestructura porque debe derivarse de EF0 y revisarse antes de gastar CPU. EF1 seguirá:

```text
baseline → perturbaciones de un eje → fingerprint y efectos marginales
→ sólo interacciones justificadas → nuevo STOP
```

No se reutiliza `edgelab/research/kaggle_multiverse_sweep.py`: abre P&L y ordena por profit factor, por lo que viola el alcance.

## 5. Artefactos EF0 esperados

- `ef0_integrity.json`;
- `ef0_profile.json`;
- `ef0_question_cards.json`;
- `ef0_status.json`;
- `sha256_manifest.json`;
- `avolclusterpoi_ef0_bundle.zip`.

Cada archivo declara población, denominadores, config ID, lineage, estado epistémico y `outcomes_accessed=false`.

## 6. Qué queda fuera

Reacciones posteriores; visitas; carreras de barreras; MFE/MAE; trades/costos/P&L; selección de tolerancia; aprobación de configuración; holdout; y ejecución automática de EF1. Lifecycle y episodios repetidos se diseñan después de EF0; no se presupone que “primer toque” sea la población.

## 7. Cómo podría refutarse

Si el bundle no cierra identidad, EF0 queda `CONTRACT_FAIL`; si el fingerprint no es determinista, la infraestructura no es reutilizable; si las tasas usan denominadores incorrectos, se corrigen antes de EF1; si no separa `AT_PRICE` de zonas materializadas, la población es inválida; y si una pregunta requiere futuro, deja de ser EF1 target-free y requiere STOP de outcomes.

**Aporte al referente:** convierte el trace ya pagado en un primer atlas estructural reutilizable y obliga a que cada análisis posterior nazca de una pregunta observada y revisada, no de un producto cartesiano ni de P&L.
