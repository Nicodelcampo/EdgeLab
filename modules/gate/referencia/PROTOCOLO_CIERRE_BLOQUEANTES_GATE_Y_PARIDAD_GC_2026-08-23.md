# Protocolo de cierre de bloqueantes — GATE GC y paridad BigTrap2Absorption

- **Fecha:** 2026-08-23
- **Rama:** `research/gate-regime-context`
- **Base revisada de GATE:** `e25e58ae13451d6eee45050430572cf84516c875`
- **Base revisada de Puerta 1:** `96416062c25ff39a4d0fe08c96358660d571d06c`
- **Estado:** decisión de diseño basada en research; **no convierte GATE en módulo operativo**.
- **Firewall:** outcomes de Puerta 1 **`NOT_OPENED`**.

Este documento traduce la auditoría independiente, el addendum de verificación y literatura externa en contratos implementables. Su objetivo es eliminar ambigüedades antes de escribir el detector de régimen o usarlo para segmentar resultados.

---

## 1. Veredicto ejecutivo

### 1.1 GATE

El `model_id = gate_tf_causal_bal_v2_feat10_sticky90_vpin055` no debe repararse en el lugar ni conservarse como identidad válida. Mezcla:

1. un pipeline que no arranca desde el layout versionado;
2. barras con look-ahead intrabar;
3. un join as-of fail-open;
4. nombres semánticamente falsos (`ofi_ema_z` y `vpin`);
5. un estado `toxico` definido por una cantidad que no es VPIN;
6. un Transformer sin checkpoint, lineage ni firma reproducible.

**Decisión:** retirarlo como candidato operativo y construir un baseline nuevo, pequeño y auditable:

```text
gate_gc_l1_hmm3_forward_v0
estados: calm / normal / volatile
inferencia: filtro forward causal
features: L1/tape honestas, point-in-time correctas
sin estado toxic hasta implementar y validar una métrica de toxicidad real
```

El Transformer queda como candidato posterior: sólo puede competir después de superar al baseline HMM en un walk-forward congelado y con manifest reproducible.

### 1.2 BigTrap2Absorption / proyecto

La última corrida target-free confirma 157 sesiones con ticks, 152 con `a_thr`, 151 con eventos y 85,0 % de potencia; sin embargo, el spec versionado sigue describiendo el universo viejo y una paridad pendiente de GC 08-26. Esto es deuda documental crítica porque el archivo supuestamente normativo no representa el experimento vigente.

El oráculo GC 02-26 recibido tiene auto-consistencia estructural y aritmética, pero aún falta comparación contra la cinta original. La paridad debe preceder cualquier apertura de outcomes.

---

## 2. Qué resuelve el research

| Bloqueante | Evidencia externa | Decisión para EdgeLab |
|---|---|---|
| `ofi_ema_z` no es OFI | Cont, Kukanov y Stoikov definen OFI desde eventos del best bid/ask, cambios de precio y tamaño, órdenes y cancelaciones | renombrar a `tape_imbalance_ema_z`; OFI real requiere L2/BBO |
| `vpin` no es VPIN | VPIN opera en buckets de volumen; no en una media temporal de barras | retirar `vpin055` y el estado `toxic` de v0 |
| VPIN puede ser actividad disfrazada | Andersen y Bondarenko muestran dependencia mecánica con volumen/volatilidad y sensibilidad al clasificador | exigir valor incremental contra tick rate, volumen y RV, más sensibilidad de clasificación |
| look-ahead intrabar | pandas advierte que defaults `label='left'`, `closed='left'` pueden traer valores posteriores hacia atrás | sellar features en el cierre real del bin y probar causalidad por perturbación futura |
| as-of incompleto | `merge_asof` ofrece `by`, `tolerance` y dirección | join por instrumento+contrato+sesión, backward, tolerancia congelada, fail-closed |
| feature inexistente | point-in-time joins devuelven null cuando no existía valor previo | prohibido rellenar desde otra sesión o desde una antigüedad ilimitada |
| switching artificial | el sticky HMM agrega sesgo de auto-transición para evitar estados redundantes y switching irreal | persistencia estimada/fijada en train-only; no `0.90` arbitrario sin evidencia |
| inferencia offline no causal | el filtro forward usa evidencia disponible hasta `t`; smoothing/Viterbi puede usar observaciones futuras | labels de evento sólo con posterior filtrada online |
| intradía confunde dinámica | la periodicidad intradía altera la dinámica aparente de alta frecuencia | estacionalidad estimada sólo en train; usar residuales point-in-time |
| modelo no reproducible | firmas y checklist requieren schema, código, datos, pesos, dependencias y comando exacto | un `model_id` sólo existe si apunta a manifest y artefactos hashados |
| “significativo aquí/no allá” | la heterogeneidad se prueba con interacción; subgrupos requieren pre-especificación, multiplicidad y potencia | test primario indicador×régimen en modelo conjunto |
| dependencia intrasesión | errores dentro de sesión no son independientes | unidad de cluster = sesión CME; wild cluster/bootstrap-t |
| calendario ad hoc | CME publica horarios por grupo de producto y feriado | calendario COMEX versionado como dato de entrada y hashado |

---

## 3. Contrato temporal obligatorio

Cada feature y cada evento deben conservar cuatro tiempos distintos:

```text
event_time                timestamp del evento BigTrap2Absorption
data_window_end           último tick que participó en la feature
feature_available_at      primer instante en que la feature completa podía conocerse
write_time                instante en que el pipeline la materializó
```

### 3.1 Regla de barra

Para una barra de un minuto que agrega `(t-1m, t]`:

```text
bar_label = t
feature_available_at = t
```

Puede implementarse con semántica equivalente a `closed='right', label='right'`, o agregando explícitamente un minuto a una etiqueta izquierda, pero una sola convención debe quedar congelada y testeada. La alineación debe partir del calendario/sesión CME, no de medianoche UTC.

Un evento `e` sólo puede usar una fila con:

```text
feature_available_at <= e.event_time
feature_available_at >= e.event_time - max_feature_age
instrument, contract y cme_session iguales
```

Para barras de un minuto, **v0 fija `max_feature_age = 1 minute`**. Si no existe una fila completa dentro de ese margen, `as_of_ok = false` y el evento queda sin etiqueta. No se retrocede a otra sesión ni se inventa un proxy.

### 3.2 Join normativo

Semántica equivalente a:

```python
pd.merge_asof(
    events.sort_values("event_time"),
    features.sort_values("feature_available_at"),
    left_on="event_time",
    right_on="feature_available_at",
    by=["instrument", "contract", "cme_session"],
    direction="backward",
    tolerance=pd.Timedelta("1min"),
    allow_exact_matches=True,
)
```

`as_of_ok` debe validar **todas** las features requeridas, el match de claves, la edad y `data_window_end <= event_time`. No alcanza con verificar el timestamp de una sola columna.

### 3.3 Pruebas adversariales mínimas

1. **Future sentinel:** cambiar ticks posteriores a `event_time`; ninguna feature/label anterior puede moverse.
2. **Intrabar spike:** insertar un spike después de un evento dentro del mismo minuto; el evento no puede verlo.
3. **Cross-contract poison:** insertar una barra más cercana de otro contrato; no puede matchear.
4. **Cross-session poison:** insertar una barra de la sesión previa; no puede matchear.
5. **Stale gap:** eliminar dos minutos previos; el resultado debe ser null/fail-closed.
6. **Boundary exact:** probar tick exactamente al cierre del bin y documentar en qué barra entra.
7. **UTC/CME:** los mismos ticks deben producir la misma sesión bajo DST y feriados.

---

## 4. Semántica honesta de features

### 4.1 OFI

`ofi_ema_z` debe desaparecer como nombre. La variable actual usa volumen agresor/tape y no cambios de profundidad en best bid/ask.

- Nombre permitido: `tape_imbalance_ema_z`.
- OFI real requiere por evento: best bid, best ask, tamaño bid, tamaño ask y secuencia de updates/cancelaciones.
- Si los parquets L2 permiten reconstruir BBO, el piloto debe producir `ofi_l1_bbo` con la definición de Cont–Kukanov–Stoikov y conservar la cobertura de updates.
- Su valor se evalúa **incrementalmente** sobre el baseline tape, no reemplazándolo por nombre.

### 4.2 VPIN/toxicidad

La media móvil de `abs(tape_imbalance)` debe llamarse, por ejemplo, `abs_tape_imbalance_ma30`; no `vpin`.

Un candidato VPIN debe declarar y congelar:

1. volumen por bucket;
2. número de buckets de la ventana;
3. clasificación buy/sell (aggressor flag, quote rule, tick rule o BVC);
4. manejo de trades que cruzan el límite del bucket;
5. normalización;
6. warmup y reset de sesión/contrato.

Antes de habilitar `toxic`, debe superar:

```text
VPIN ~ volumen + tick_rate + realized_vol + spread + time_of_day
```

y demostrar contribución incremental out-of-sample. También debe repetirse con al menos dos clasificadores de trades porque la literatura muestra que el resultado puede invertirse según clasificación.

**Decisión v0:** no hay estado `toxic`; sólo `calm`, `normal`, `volatile`.

### 4.3 Estacionalidad intradía

Para cada fold de entrenamiento:

1. estimar mediana y MAD por contrato y bin Chicago de 30 minutos;
2. calcular residuales/robust-z para RV, tick rate, volumen y spread;
3. aplicar esos parámetros congelados al bloque futuro;
4. nunca recalcular normalizadores con test o con la sesión que se etiqueta.

Los features crudos pueden conservarse para auditoría, pero el detector primario usa versiones desestacionalizadas. Se reporta siempre el baseline sólo-hora/actividad para demostrar que el régimen agrega algo más.

---

## 5. Detector v0 recomendado

### 5.1 Arquitectura

Baseline: HMM gaussiano de 3 estados sobre un set pequeño de features point-in-time correctas.

Candidatos iniciales:

```text
rv_robust_z
tick_rate_robust_z
spread_robust_z
tape_imbalance_ema_z
efficiency_ratio
```

La lista final debe congelarse antes de abrir outcomes y cada feature debe pasar el future-sentinel.

### 5.2 Persistencia

La literatura sticky demuestra que un sesgo de auto-transición puede evitar over-segmentation, pero no justifica `0.90` por nombre.

- estimar la matriz de transición en train-only;
- permitir un prior/sesgo de persistencia predeclarado;
- seleccionar entre una grilla pequeña usando sólo likelihood predictivo, estabilidad y duración en validación target-free;
- congelar el valor y su justificación en el manifest;
- reportar duración mediana/p10/p90 por estado y switching por sesión.

### 5.3 Inferencia causal

- entrenamiento puede usar Baum–Welch en el bloque de train;
- etiqueta de cada evento futuro = `argmax P(S_t | x_1...x_t)` del **filtro forward**;
- prohibido usar posterior smoothed, Viterbi sobre la secuencia completa o recalibración con observaciones posteriores;
- el estado debe poder reproducirse tick/bar a tick/bar en streaming.

### 5.4 Identidad semántica y label switching

Los enteros de estado no son semántica. En cada fold, la asignación a `calm/normal/volatile` se fija con una regla entrenada y determinística basada principalmente en RV residual y actividad residual. Esa regla y sus thresholds se guardan. Si dos estados no son separables o intercambian orden de manera inestable, el fold falla; no se renombran mirando outcomes.

### 5.5 Walk-forward target-free

Usar bloques cronológicos; ningún shuffle aleatorio de filas. En cada fold:

1. fit de normalizadores + HMM sólo en pasado;
2. evaluación forward en bloque siguiente;
3. reportar cobertura, nulls, ocupación de estados, duración, entropía, matriz de transición, estabilidad semántica y drift;
4. correr varias seeds/inicializaciones y guardar todas, no sólo la mejor;
5. todavía no medir MFE/MAE ni outcomes de Puerta 1.

El Transformer sólo puede avanzar si mejora métricas target-free preespecificadas y estabilidad frente al HMM, con costo y complejidad justificados.

---

## 6. Contrato de reproducibilidad de `model_id`

Un nombre no es un modelo. Todo `model_id` debe resolver a un manifest inmutable con:

```json
{
  "model_id": "...",
  "git_commit": "...",
  "training_command": "...",
  "code_hashes": {},
  "data_manifest_hash": "...",
  "calendar_hash": "...",
  "feature_schema_hash": "...",
  "config_hash": "...",
  "normalizer_hash": "...",
  "checkpoint_hash": "...",
  "input_signature": {},
  "output_signature": {},
  "input_example_hash": "...",
  "dependencies_lock_hash": "...",
  "random_seeds": [],
  "train_range": {},
  "validation_ranges": [],
  "created_at_utc": "..."
}
```

Además:

- config canónica sin campo de hash autoreferencial;
- checkpoint/pesos y normalizadores versionados;
- schema de inputs y outputs validado al cargar;
- comando exacto que reproduce cada tabla;
- número de runs, seeds, hardware, runtime, métricas con dispersión;
- loader que falle si cualquier hash no coincide;
- smoke desde un clone limpio y desde el layout real del repo.

---

## 7. Diseño estadístico cuando GATE sea elegible

GATE no es una señal ni debe “encontrar un edge”. Es un etiquetador de contexto. Luego de que Puerta 1 se abra legítimamente, la hipótesis confirmatoria debe formularse como una **interacción**.

### 7.1 Estimando primario

Modelo conjunto que estime:

```text
outcome ~ arm + gate_state + arm×gate_state + covariables congeladas
```

- `arm` compara K_ABS con su control emparejado;
- el coeficiente de interacción mide si el valor incremental cambia por régimen;
- no se concluye heterogeneidad porque una celda sea significativa y otra no;
- se mantiene el headline plano para evitar selección por contexto.

### 7.2 Familia confirmatoria mínima

Para v0, no más de dos contrastes de interacción previamente declarados, por ejemplo:

1. `volatile` vs `calm+normal`;
2. `calm` vs `normal+volatile`.

Ajuste Holm para la familia. Cualquier corte adicional queda exploratorio y no puede modificar la decisión de Puerta 1.

### 7.3 Potencia e inferencia

- tabla target-free de sesiones/eventos por celda antes de outcomes;
- MDE/potencia por interacción, no sólo por efecto dentro de celda;
- igual peso por sesión CME;
- wild cluster bootstrap/bootstrap-t por sesión;
- conservar el mismo calendario y definición de sesión que Puerta 1;
- si una celda no alcanza potencia/cobertura, etiquetarla `EXPLORATORY_UNDERPOWERED`, no fusionarla post hoc.

---

## 8. Paridad GC 02-26 — protocolo antes de Puerta 1

### 8.1 Artefactos congelados

```text
oraculo: bt2_absorption__AbsMagnitude__GC0226dic__TW25.csv
bytes: 128331787
sha256: 7c14ebd1463f4d17d4db7957e4fe729a6d1d48b46b3395bc7334a505cf9fce4d
tape requerido: GC 02-26.Last.txt
score_mode: AbsMagnitude
tape_window: 25
absorption_pct: 90
absorption_lookback: 500
min_history: 200
```

Auto-chequeo previo del oráculo:

```text
185697 buckets/scores
4642053 ticks declarados
30 sesiones CME
28 cubetas residuales / 328 ticks
2702 zones / 2702 fills
estructura y aritmetica interna: PASS
paridad contra tape: PENDING
```

### 8.2 Qué debe comparar Claude

1. hashes, bytes, metadatos y cobertura completa de ambos inputs;
2. líneas malformadas, timestamps a 100 ns, orden y duplicados;
3. ancla determinada por `t_start` exacto después del warmup, nunca por un offset manual;
4. secuencia continua post-ancla, documentando todo pre-ancla y sin truncar la cinta;
5. por bucket: `n_ticks`, `signed_flow`, `d_ticks`, `a_score`, `a_thr`, `a_pass`, `n_hist`;
6. ring causal: las residuales no entran al historial de umbral;
7. zones, invalidaciones/expiraciones y fills con pairing por clave robusta, no por orden de listas;
8. timestamps de fills, incluyendo fills en el mismo nanosegundo;
9. ventanas irregulares de Thanksgiving, Nochebuena y fin de año;
10. identidad global de ticks y conteos por sesión.

### 8.3 Calendario adversarial mínimo

Auditar explícitamente:

```text
2025-11-27  Thanksgiving
2025-11-28  post-Thanksgiving
2025-12-24  Christmas Eve
2025-12-25  cerrado
2025-12-31  year-end early close
2026-01-01  cerrado
```

El calendario COMEX/CME usado por el harness debe ser un artefacto versionado y hashado. La fecha UTC de un tick no puede reemplazar la sesión CME.

### 8.4 Criterio de aceptación

`PARITY_GC0226_PASS` sólo si:

```text
coverage post-anchor = 100%
unexplained arithmetic mismatches = 0
causal ring mismatches = 0
residual policy mismatches = 0
zone mismatches = 0
fill/pairing mismatches = 0
session/calendar mismatches = 0
```

ULP o truncamiento temporal deben declararse con regla exacta y no esconderse bajo tolerancias amplias. Ante cualquier mismatch, emitir `FAIL` con primer contraejemplo y no modificar el kernel ni el `.cs` para hacerlo pasar.

---

## 9. Sincronización del spec después de la paridad

`specs/bt2_absorption_gate1_v1.json` en `9641606` sigue con universo y potencia anteriores. Después —no antes— de cerrar la paridad GC 02-26, hacer un commit documental separado que mantenga decisiones pre-outcome y sincronice:

- source tapes: GC 12-25, 02-26, 04-26, 06-26, 08-26;
- contratos analíticos: GC 02-26, 04-26, 06-26, 08-26;
- GC 12-25 como referencia de primer roll, no universo analítico;
- rango 2025-11-26 → 2026-06-30;
- 157 sesiones con ticks, 152 con `a_thr`, `G=151` con eventos;
- potencia 85,0 % para 2,5 ticks;
- cuatro rolls auditados;
- B-9 y capacidad N_RAND completos;
- evidencia de paridad GC 08-26 y GC 02-26 como entradas separadas;
- outcomes aún `NOT_OPENED`.

No cambiar el estimando, null, seeds, horizonte, decisión o controles. Esto es sincronización, no re-preregistro.

---

## 10. Orden de trabajo congelado

```text
P0  validar paridad GC 02-26 y commitear evidencia reproducible
P0b sincronizar spec en commit documental separado
P1  revisión humana del diff y autorización explícita para abrir outcomes
P2  ejecutar Puerta 1 sin GATE
G0  corregir layout + contrato temporal + nombres de features
G1  baseline HMM3 forward target-free + manifest
G2  preregistro de interacción y potencia por celda
G3  sólo entonces evaluar contexto sobre outcomes
```

El orden evita que GATE influya en el test principal o que outcomes retroalimenten el diseño del régimen.

---

## 11. Fuentes autoritativas consultadas

1. Cont, Kukanov y Stoikov, *The Price Impact of Order Book Events*, Journal of Financial Econometrics. DOI: `10.1093/jjfinec/nbt003`.
2. Easley, López de Prado y O'Hara, *Flow Toxicity and Liquidity in a High-frequency World*. DOI: `10.1093/rfs/hhs053`.
3. Andersen y Bondarenko, *Reflecting on the VPIN dispute*. DOI: `10.1016/j.finmar.2013.08.002`.
4. pandas, documentación de `resample` y advertencia de look-ahead por defaults de etiquetado/cierre.
5. pandas, documentación de `merge_asof` (`by`, `tolerance`, `direction`).
6. Databricks, *Point-in-time feature joins*: AS OF anterior y null si no había feature disponible.
7. Fox, Sudderth, Jordan y Willsky, *A sticky HDP-HMM with application to speaker diarization*. DOI: `10.1214/10-AOAS395`.
8. Andersen y Bollerslev, *Intraday periodicity and volatility persistence in financial markets*. DOI: `10.1016/S0927-5398(97)00004-2`.
9. Wang et al., *Statistical Considerations for Subgroup Analyses*. DOI: `10.1016/j.jtho.2020.12.008`.
10. Cameron, Gelbach y Miller, *Bootstrap-Based Improvements for Inference with Clustered Errors*. DOI: `10.1162/rest.90.3.414`.
11. MLflow, *Model Signatures and Input Examples*.
12. Pineau et al., *The Machine Learning Reproducibility Checklist v2.0*.
13. NIST, *AI Risk Management Framework 1.0*, NIST AI 100-1.
14. CME Group, calendarios y horarios oficiales por grupo de producto.

---

## Cierre

Este protocolo salda la ambigüedad de diseño: define qué significa causal, qué features pueden conservar su nombre, qué detector conviene construir primero, cómo se vuelve reproducible y cómo se prueba contexto sin convertir una búsqueda de subgrupos en un edge espurio.

Hasta completar G0–G2, el veredicto del módulo sigue siendo:

```text
FOUNDATION_ONLY / NOT_OPERATIONAL
```

Y hasta que GC 02-26 pase la comparación contra su cinta:

```text
ORACLE_SELF_CONSISTENCY = PASS
FULL_TAPE_PARITY = PENDING
OUTCOMES = NOT_OPENED
```
