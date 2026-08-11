# Carta rectora — BigTrap2 Multiframe ML / Kaggle

**Fecha:** 2026-08-11  
**Estado:** `DRAFT_NON_EXECUTABLE`  
**Rama:** `research/bigtrap2-multiframe-ml`  
**Propósito final:** descubrir, refutar y eventualmente validar un edge real, reproducible, económicamente viable y ejecutable en mercado.

## Referente rector

> Explorar ampliamente posibilidades, parámetros, pruebas, métricas, features, inferencias, predicciones, análisis y modelos; promover únicamente evidencia angosta, causal, reproducible, resistente al sobreajuste, neta de costos y aplicable en tiempo real.

La amplitud es una propiedad del **catálogo de hipótesis**. No autoriza mezclar todas las decisiones en una única corrida ni elegir retrospectivamente el mejor resultado. La regla permanente es:

```text
EXPLORAR AMPLIO → VALIDAR ESTRECHO → DESPLEGAR SÓLO NETO DE COSTOS
```

## Qué significa «edge válido»

Una configuración prometedora no es un edge. Para recibir esa clasificación debe demostrar, en orden:

1. **Validez semántica:** Python, NT8 y el dataset representan el mismo evento causal.
2. **Validez temporal:** cada feature estaba disponible al instante de decisión; cero lookahead.
3. **Información incremental:** mejora fuera de muestra al baseline y al mejor frame individual.
4. **Validez estadística:** efecto con incertidumbre, multiplicidad y dependencia temporal tratadas.
5. **Robustez:** signo, magnitud y calibración estables entre sesiones, contratos, regímenes y vecinos paramétricos razonables.
6. **Viabilidad económica:** expectativa neta positiva bajo costos base, adversos y severos; frecuencia, drawdown, turnover y capacidad aceptables.
7. **Implementabilidad:** la señal puede reproducirse en NT8 en tiempo real con latencia, fill y datos disponibles.
8. **Confirmación:** sobrevive un holdout cerrado de un solo uso y una etapa forward/paper.

Si falla cualquier eslabón, se clasifica con precisión (`descriptivo`, `predictivo no económico`, `sub-fee`, `inestable`, `no implementable`, `refutado` o `abstención`), no se reetiqueta como edge.

## Mapa amplio de posibilidades

El proyecto debe catalogar, sin ejecutar todo simultáneamente:

### Datos y unidades de análisis

- ticks canónicos y clasificación agresora;
- barras time, tick y, en familias futuras, volume/dollar/event bars;
- barras, eventos, zonas, ventanas, estados continuos y secuencias;
- sesión, día, contrato, instrumento y régimen;
- fuentes y vendors alternativos cuando existan.

### Resolución y combinaciones

- frames individuales `tick:K`;
- pares y tríos con roles ordenados;
- coexistencia temporal;
- solapamiento y contención geométrica;
- confirmación posterior;
- persistencia entre escalas;
- consenso, divergencia y fuerza marginal de cada frame;
- ventanas retrospectivas múltiples, siempre causales.

### Parámetros del detector

- construcción de footprint;
- granularidad de precio;
- ratio de imbalance;
- filtros de wick, delta y volumen;
- geometría y lado;
- lifecycle, edad y toques;
- parámetros visuales excluidos del análisis;
- familias de parámetros separadas para evitar confundir detector, lifecycle y ejecución.

### Features

- evento y zona;
- barra y footprint;
- distancia y geometría relativa;
- fuerza, volumen, delta y concentración;
- sincronía y dispersión entre frames;
- edad, persistencia y ordinal de toque;
- volatilidad, actividad, liquidez y tendencia;
- fase de sesión, calendario y noticias cuando sean causales;
- contexto multiinstrumento futuro, con datos sincronizados;
- calidad y disponibilidad de datos;
- interacciones aprendidas y reglas derivadas.

### Predicciones y estimands

- probabilidad de toque o revisita;
- first passage favorable/adverso;
- tiempo hasta evento y competing risks;
- magnitud y cuantiles de excursión;
- retorno futuro con signo y magnitud absoluta;
- volatilidad posterior;
- probabilidad calibrada de cubrir costos;
- abstención/confianza;
- utilidad neta condicionada a ejecución.

Los targets económicos permanecen cerrados hasta su gate específico.

### Modelos

- baselines ingenuos y analíticos;
- regresión lineal/logística regularizada;
- GAM y Explainable Boosting Machine;
- árboles pequeños y RuleFit;
- LightGBM, XGBoost y CatBoost;
- survival/competing-risk models;
- modelos jerárquicos y bayesianos cuando aporten pooling explícito;
- conformal prediction para incertidumbre/abstención;
- modelos secuenciales y deep learning sólo si el tamaño efectivo y el baseline justifican su complejidad;
- ensembles únicamente con predicciones OOF y presupuesto de búsqueda registrado.

### Métricas

- integridad, cobertura, paridad y disponibilidad causal;
- effect size, IC, MDE, potencia y estabilidad;
- log loss, Brier, ROC-AUC, PR-AUC y calibración;
- MAE/RMSE/quantile loss para magnitud;
- concordance/Brier temporal para survival;
- lift incremental contra baseline y single-frame;
- sensibilidad a parámetros y regímenes;
- PBO, DSR, SPA/StepM, max-T/FDR y pruebas por permutación;
- expectativa neta, payoff, hit rate condicionado, turnover, drawdown, Sharpe/Sortino/Calmar con cautela, capacidad y riesgo de ruina;
- latencia, fills, slippage y divergencia research↔NT8.

## Funnel obligatorio

### Fase 0 — contrato y semántica

Datos, identidad, sesiones, rolls, `available_at`, paridad y tests truth-known. Cualquier FAIL bloquea lo posterior.

### Fase 1 — landscape target-free

Densidad, geometría, lifecycle, cobertura, estabilidad y nulos. No se elige edge.

### Fase 2 — información predictiva

Targets predefinidos, OOF, baselines, single-frame y luego multiframe. No se usa P&L para diseñar el detector.

### Fase 3 — selección robusta

Nested purged CV, embargo, estabilidad, permutaciones, multiplicidad y comparación de modelos. Se promueve una familia pequeña, no el máximo observado.

### Fase 4 — economía

Sólo con autorización separada: costos por instrumento, escenarios adversos, latencia, fills, turnover, capacidad y sensibilidad. Un efecto bruto que no paga costos se clasifica `sub-fee`.

### Fase 5 — confirmación

Configuración y código congelados, holdout de un solo uso, auditoría independiente y decisión predefinida.

### Fase 6 — aplicabilidad

Paridad NT8, replay, paper/forward, monitoreo de drift, kill switch y rollback.

## Controles contra sobreajuste y falsos positivos

- particiones por sesión/contrato, nunca split aleatorio de filas correlacionadas;
- purga y embargo al menos iguales al máximo horizonte de etiqueta;
- tuning sólo dentro de folds internos;
- todas las comparaciones mediante predicciones out-of-fold;
- ledger de cada intento, incluido FAIL y resultado nulo;
- conteo de hipótesis y `M_eff` por familia;
- negative controls, labels permutados y tests truth-known;
- estabilidad en vecinos paramétricos y mesetas, no picos aislados;
- complejidad penalizada y baselines simples obligatorios;
- holdout físicamente ausente del Notebook exploratorio;
- ninguna reapertura del holdout por «un pequeño ajuste»;
- auditor distinto del implementador para resultados promovibles;
- separación entre descubrimiento, estimación, confirmación y forward.

## Sesgos que deben auditarse explícitamente

- lookahead y barras todavía abiertas;
- leakage de target, normalización o selección;
- data snooping y garden of forking paths;
- supervivencia de contratos y errores de roll;
- selección visual y publicación selectiva;
- dependencia por sesión y labels solapados;
- drift de régimen e instrumento;
- clasificación imperfecta del agresor;
- vendor/data-quality bias;
- costos, queue position, latencia, slippage e impacto omitidos;
- sesgo por elegir métrica, horizonte o costo después de ver resultados.

## Registro universal de experimentos

Toda corrida debe guardar al menos:

```text
experiment_id, family_id, hypothesis_id
code_commit, dirty_state, dataset_id, manifest_sha256
bar_specs, indicator_params, feature_set_id, target_set_id
fold_plan_id, model_id, search_budget_id
all_metrics, uncertainty, multiplicity_family
runtime, peak_ram, environment
status, abstention_reason, promoted_or_rejected
```

No se borran resultados malos ni se reutiliza un ID para una corrida diferente.

## Papel de Kaggle

Kaggle es un laboratorio reproducible y versionado, no la fuente canónica:

```text
EdgeLab → construye semántica, eventos, features, folds y manifests
Kaggle → ejecuta EDA, modelos, OOF, inferencia y reportes
EdgeLab/NT8 → reproduce candidatos, audita y valida implementación
```

El Dataset Kaggle inicial debe ser privado y contener preferentemente features derivadas. Los ticks crudos sólo pueden subirse después de verificar licencia. Tokens, credenciales, paths locales y holdout quedan fuera.

## Estados del candidato

```text
REGISTERED
SEMANTIC_PASS
DISCOVERY_ONLY
PREDICTIVE_REPLICATED
ECONOMIC_PASS
HOLDOUT_PASS
FORWARD_PASS
DEPLOYABLE
```

Estados terminales igualmente válidos:

```text
ABSTAIN
REFUTED
UNSTABLE
SUB_FEE
NOT_IMPLEMENTABLE
DATA_INSUFFICIENT
```

## Estado de autorización al crear esta carta

- documentación y scaffolding: **autorizados**;
- benchmarks estructurales target-free: **autorizables por protocolo**;
- targets predictivos: **todavía no ejecutados**;
- P&L/economía: **STOP hasta gate separado**;
- holdout: **cerrado y no adjunto**;
- despliegue: **fuera de alcance actual**.
