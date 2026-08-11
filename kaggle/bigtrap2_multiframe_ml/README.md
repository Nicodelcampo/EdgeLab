# Kaggle workspace — BigTrap2 Multiframe ML

**Estado:** scaffolding solamente. No hay Dataset publicado, Notebook ejecutado, outcomes abiertos ni holdout adjunto.

## Misión

Usar Kaggle como laboratorio reproducible para descubrir y refutar información multiframe, manteniendo EdgeLab/NT8 como fuente de verdad semántica y de implementación.

```text
EdgeLab build → Kaggle discovery/validation → EdgeLab reproduction → NT8 parity
```

Referencias canónicas:

- `docs/research/BIGTRAP2_MULTIFRAME_ML_CHARTER_2026-08-11.md`
- `docs/research/BIGTRAP2_MULTIFRAME_ML_PLAN_2026-08-11.md`
- `specs/bigtrap2_multiframe_ml_search_space_v0.json`
- `specs/bigtrap2_multiframe_ml_dataset_contract_v0.json`

## Principio

```text
Explorar amplio → validar estrecho → desplegar sólo neto de costos
```

Kaggle no debe elegir «el mejor backtest». Debe producir predicciones OOF, landscapes completos, incertidumbre, controles negativos, estabilidad y tarjetas auditables de candidatos.

## Dataset privado esperado

```text
edgelab-bigtrap2-multiframe-research/
├── dataset_manifest.json
├── hashes.sha256
├── events_long.parquet
├── windows_ml.parquet
├── folds.parquet
├── feature_dictionary.json
├── target_dictionary.json
└── build_report.json
```

Reglas:

- sólo período research;
- holdout físicamente ausente;
- preferir features derivadas;
- no subir ticks crudos sin licencia confirmada;
- no incluir tokens, `.env`, credenciales, paths locales ni identificadores secretos;
- Dataset versionado y content-addressed;
- inputs de Kaggle tratados como read-only.

## Secuencia de Notebooks planeada

### `00_contract_and_environment`

- verificar hashes y schema;
- registrar entorno y dependencias;
- comprobar ausencia de holdout;
- comprobar causalidad y claves únicas;
- fallar cerrado antes de cualquier análisis.

### `01_data_quality_and_target_free_eda`

- cobertura por sesión/frame;
- duración física de barras;
- densidad y geometría de zonas;
- missingness y drift;
- cero outcomes predictivos.

### `02_label_and_split_audit`

- validar cutoff/available-at;
- labels solapados;
- purga y embargo;
- folds por sesión;
- negative controls y datos truth-known.

### `03_single_frame_baselines`

- rate/time-of-session baselines;
- regresión regularizada;
- un modelo por K;
- OOF, calibración y landscape completo;
- selección por meseta/estabilidad, no máximo.

### `04_multiframe_features`

- coexistencia, consenso/divergencia;
- overlap/containment;
- orden y dispersión temporal;
- persistencia y aporte marginal;
- auditoría de joins causales.

### `05_model_families_nested_cv`

- EBM, RuleFit, boosting y modelos de survival habilitados;
- tuning dentro de inner folds;
- comparación contra baselines simples;
- complejidad penalizada.

### `06_inference_multiplicity_stability`

- permutaciones por sesión;
- SPA/StepM o max-T;
- PBO/CSCV;
- estabilidad por fold/régimen/vecino paramétrico;
- candidatos o abstención.

### `07_economics_GATE_CLOSED`

No existe como Notebook ejecutable hasta protocolo separado. Cuando se abra deberá incluir costos base/adversos/severos, fill, latencia, turnover, capacidad, drawdown y riesgo de ruina.

### `08_candidate_cards`

Por candidato:

- hipótesis y lineage;
- features y modelo;
- OOF completo;
- incertidumbre/multiplicidad;
- fallos por régimen;
- costo computacional;
- razones para promover o rechazar;
- reproducción requerida en EdgeLab/NT8.

### `09_holdout_ONE_SHOT`

No debe vivir en el proyecto exploratorio. Se crea sólo después de congelar candidato, código, métricas y decisión.

## Outputs obligatorios

```text
/kaggle/working/
├── run_manifest.json
├── oof_predictions.parquet
├── metric_landscape.parquet
├── model_cards/
├── candidate_cards/
├── figures/
└── audit_report.json
```

Cada output debe incluir o referenciar:

```text
experiment_id
code_commit
dataset_id
feature_set_id
target_set_id
fold_plan_id
model_id
search_budget_id
```

## Reglas de modelado

- prohibido split aleatorio por filas;
- OOF obligatorio;
- nested purged CV para tuning;
- normalización, imputación y selección aprendidas dentro de cada fold;
- mismo presupuesto por modelo o presupuesto registrado;
- seed y determinismo registrados;
- guardar todos los candidatos, incluidos los malos;
- no usar el holdout para arreglar features;
- SHAP/importance no sustituyen prueba incremental;
- deep learning requiere justificar tamaño efectivo y superar baselines simples.

## Checklist previo al primer Dataset

- [ ] licencia de datos adjudicada;
- [ ] dataset contract validado;
- [ ] tabla larga y tabla de ventanas reproducibles;
- [ ] folds congelados por sesión;
- [ ] holdout ausente;
- [ ] hashes completos;
- [ ] oráculos representativos por `bar_key`;
- [ ] benchmarks de tiempo/RAM;
- [ ] test de barras abiertas y joins `asof` hacia atrás;
- [ ] registro universal de experimentos;
- [ ] criterios de abstención.

## Próximo entregable

Crear validadores locales del contrato y un Notebook `00` que sólo valide manifiesto, schemas, hashes, causalidad y firewall. No entrenar modelos todavía.
