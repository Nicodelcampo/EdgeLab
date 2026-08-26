# 03 — Puerta L2: auditoría y contrato contextual

**Estado:** `PILOT_IMPLEMENTED_REAL_EXTRACTION_CLAIMED_EVIDENCE_INCOMPLETE`  
**Outcomes autorizados:** no.

## 1. Base implementada

```text
branch = work/futures-l2-context-foundation-20260825
tip = 0a1283f97a0ccee2802bd77617e4c0abbdc3290a
implementation = a9f85db83455d7b85257f3dc4c49e2fedda26550
claimed_real_run = ced33dd4235da2882f5e334c87c84b7f3249dc7d
```

Existe:

- reconstrucción L2 ordenada por `source_row`;
- features por minuto con instante de disponibilidad;
- train/evaluation separados;
- HMM3 `forward_filter_only`;
- estados `calm`, `normal`, `volatile`;
- overlay `toxic` target-free y sticky;
- grupos `G-operable=calm|normal` y `G-stress=volatile|toxic`;
- join estricto `available_source_row < event_source_row`;
- tests de prefijo y as-of.

El nombre `l2_flow_toxicity_overlay_not_vpin` es correcto: no se implementó VPIN.

## 2. Estado probatorio

La corrida nocturna terminó con exit code 0, pero usó `--allow-dirty` y no versionó el
paquete local. Antes de congelar CTX-3 deben recuperarse:

```text
run_manifest.json
gate_l2_context_model.json
gate_l2_target_free_report.json
gate_l2_context_labels.parquet
features/*.parquet
```

El reporte formal debe derivar, no copiar a mano:

- hashes de inputs, outputs y código;
- `dirty_start/dirty_end`;
- `code_commit_start/end`;
- model id;
- sesiones train/evaluation/excluidas;
- conteos por estado y grupo;
- cobertura y as-of;
- persistencia y flip rate;
- fallos de libro;
- correlación con ancho de zona.

Hasta entonces:

```text
REAL_EXTRACTION_CLAIMED=true
FORMAL_EXTRACTION_VERIFIED=false
```

## 3. Bloqueos de datos

El piloto tiene 13 sesiones GC 06-26, ocho train y cinco evaluation. El preregistro
exige al menos 40 sesiones en cada celda primary: no puede pasar.

El Event Store all5 no resuelve esto. Sus `source_row` pertenecen a los Parquets L1 de
Gate 1; el contexto L2 sólo puede unirse si proviene de la misma captura mixta. La
investigación previa descartó el join de `.Last` externo por timestamp/precio.

La muestra L2 de junio GC 06-26 tampoco coincide con la muestra analítica all5 del
mismo contrato. Por lo tanto:

```text
GATE1_ALL5_L2_COVERAGE=false
EVENT_JOIN_READY=false
MIN_SESSIONS_PER_CELL=false
```

## 4. Pregunta y estimando

L2 no pregunta otra vez si K_ABS predice. Pregunta si el efecto definido por P2 cambia
según contexto pre-evento.

Una vez congelado `theta_p2`, el primary es:

```text
Delta_interaction =
  [(K_ABS - N_RAND) | G-operable]
  -
  [(K_ABS - N_RAND) | G-stress]
```

Hipótesis bilateral:

```text
H0: Delta_interaction = 0
H1: Delta_interaction != 0
```

Se prueba la interacción directamente. “Significativo en un grupo y no en otro” no es
prueba de diferencia.

Secundarios con Holm separado:

```text
(K_ABS - K_ABS_SHUFFLE) × contexto
(K_ABS - K_BT2) × contexto
context labels shuffled dentro de sesión
```

## 5. Features v2

Se conservan las actuales:

- OFI BBO normalizado;
- profundidad top-5;
- spread;
- add/remove/replenishment/depletion;
- tape imbalance;
- tasa de eventos;
- RV 15m;
- efficiency ratio.

Se proponen como aditivas, todavía no congeladas:

```text
queue_imbalance_l1
depth_imbalance_top3
depth_imbalance_top5
microprice_minus_mid_ticks
add_intensity_bid / add_intensity_ask
cancel_intensity_bid / cancel_intensity_ask
replenishment_after_depletion
book_age_or_time_since_resync
```

Toda feature debe usar sólo filas anteriores o iguales a su
`feature_available_at_source_row`. No se permite usar el outcome P2 para elegirlas.

## 6. Gates target-free

Antes de abrir outcomes deben pasar todos:

1. hashes y manifests completos;
2. árbol limpio o corrida repetida limpia;
3. misma captura/`source_row` para contexto y eventos;
4. cobertura de contexto >= 99 %;
5. `available_source_row < event_source_row` en cada join;
6. ocupación publicada por estado y grupo;
7. al menos 40 sesiones por celda primary;
8. book invalid/locked/crossed dentro del umbral declarado;
9. persistencia y flip rate dentro del rango declarado;
10. estabilidad de estados frente a inicializaciones/alineación de etiquetas;
11. invariancia de prefijo sobre datos reales;
12. `abs(corr(context_group, zone_width_ticks)) < 0.20`;
13. identidad exacta de detector, config, evento, datos y modelo;
14. autorización explícita después del STOP target-free.

## 7. Uso del HMM

El HMM es una compresión causal de features, no un generador de edge. Se permite:

- entrenamiento sólo en bloque anterior;
- probabilidades filtradas forward-only;
- nombres de estados alineados por volatilidad/depth para evitar label switching;
- overlay toxic separado y explícito.

Se prohíbe:

- smoothing retrospectivo;
- reentrenar mirando P2;
- cambiar umbrales para mejorar un grupo;
- asumir que `G-operable` debe ser mejor por su nombre.

## 8. Relación con el sweep de 99 configs

El contexto primary se evalúa sólo sobre la configuración headline congelada. Las
otras 98 configuraciones no crean 98 hipótesis L2 nuevas. Pueden usarse después como
sensibilidad target-free de cobertura/identidad, nunca para escoger la combinación
config × estado con mejor outcome.

## 9. Inferencia y lectura

- unidad: sesión CME;
- bootstrap por sesiones completas;
- igual peso por sesión dentro de cada contraste;
- un test de interacción primary;
- MDE y ocupación publicados antes de outcomes;
- ninguna relajación de grupos si falta potencia.

Lecturas permitidas:

```text
CONTEXT_HETEROGENEITY_SUPPORTED
CONTEXT_HETEROGENEITY_NOT_SUPPORTED
CONTEXT_INCONCLUSIVE_LOW_POWER
ABSTAIN_CONTEXT_DATA
```

Aun con heterogeneidad supported:

```text
EDGE_DECLARED=false
```

## 10. Datos que faltan

Se necesita una captura L1/L2/trades con orden común para sesiones que no hayan sido
usadas para elegir la puerta. Debe cubrir suficientes sesiones y conservar:

```text
contract
cme_session
source_row
ts_utc_ns o reloj documentado
L1 bid/ask/trades
L2 depth operations
```

Como piso operativo se buscan al menos 40 sesiones efectivas en cada grupo; en la
práctica se necesitan más por ocupación desigual y para alimentar después el G2
calendarizado.
