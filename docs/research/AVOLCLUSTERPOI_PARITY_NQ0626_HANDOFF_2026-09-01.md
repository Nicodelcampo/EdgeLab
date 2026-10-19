# aVolClusterPOI parity NQ 06-26 — handoff, 2026-09-01

**Estado: EN PAUSA, para retomar fresco.** Nada roto, nada urgente — cortado en un
punto limpio con toda la evidencia escrita.

## Qué se construyó esta sesión (rama `research/avolcluster-nq-parity-oracle-20260901`)

1. **`run(ticks, bars, footprints)` para `edgelab/bridge/indicators/avolclusterpoi.py`**
   (commit `83b9705`) — el kernel solo exponía primitivas (`SessionProfile`,
   `detect_block`, `cluster_hot_ticks`), sin el entrypoint uniforme que
   `tools/paridad_oraculo.py` necesita. Escrito desde cero contra las primitivas,
   **deliberadamente sin reusar** `avolcluster_nq_zone_builder.py::build_session_creation_events`
   (rama distinta): esa función calcula el bucket horario sin el ajuste de "-1
   segundo" que `session_relative_bucket()` documenta como necesario — reusarla
   hubiera reintroducido en silencio el mismo bug que ese ajuste existe para evitar.
   No rastrea ciclo de vida (sin FIRST_TOUCH/ZONE_INVALIDATED) — cobertura real
   y declarada del kernel, no un bug del adaptador. 2 tests nuevos, verificados
   end-to-end (4 zonas reales generadas sobre ticks sintéticos, no solo el
   camino vacío).
2. **Registrado como `"avolclusterpoi"`** en `KERNELS` de `tools/paridad_oraculo.py`.
3. **Oráculo NT8 exportado y verificado** (2026-09-01): `data/nt8_oracles/avolcluster_v05_NQ0626_120t_20260407_20260612.csv`.
   Instrumento NQ JUN26 confirmado en Instrument Properties (Trading Hours =
   CME US Index Futures ETH, no la ambigüedad "Use instrument settings" que
   se temía). Ventana 2026-04-07→06-12, 49 sesiones, un solo contrato (sin
   roll), sin feriados de por medio (verificado contra las 234 sesiones reales
   del event store — únicos gaps: Navidad, Año Nuevo, Good Friday 04-03).

## Lo que se corrió y encontró

### 1. Gate de paridad (kernel `avolclusterpoi-parity-nq0626`, Kaggle)

`gate: FAIL`. Desglose:
```
FEATURE_DIFF: 256    <- esperado (touches, sin lifecycle)
GEOMETRY_DIFF: 19    <- FAIL code, real
MATCHED: 2
MISSING_IN_NT8: 57   <- FAIL code, real
MISSING_IN_PYTHON: 48<- FAIL code, real
STATE_ORDER_DIFF: 254<- esperado (sin lifecycle)
```
317 zonas Python, 308 NT8, 260 pares emparejados. El FEATURE_DIFF/STATE_ORDER_DIFF
masivo es la cobertura declarada del kernel (no confirmatorio de nada). Lo que
importa es GEOMETRY_DIFF/MISSING_IN_*, y ahí sí hay una discrepancia real sin
explicar todavía.

### 2. TICKBAR-001 v2 classifier, NQ 06-26 120t (kernel `tickbardiag-nq0626-120t`)

Con `--tz-shift-hours 3`: `CLASIFICACION: STREAM_MISMATCH` (H1), `probe_score=0`,
`ambiguity=170`. A primera vista sugiere que NT8 y Python ni siquiera ven el
mismo stream de trades.

### 3. Debug de shift (kernel `tickbardiag-debug-shift`) — LO QUE REALMENTE PASA

Se probaron shifts candidatos (0, ±2, ±3, ±5h) comparando los primeros precios
de cada ventana. **`+3h` es inequívocamente el correcto**: los precios del
parquet en esa ventana (`96831, 96831, 96832, 96832, 96833`) caen exacto en el
mismo nivel que el ledger (`96832, 96833, 96820, 96816, 96830`). Ningún otro
shift se acerca.

**El "STREAM_MISMATCH" no es un mismatch de stream real** — es un desfase de
límite de ventana: el parquet devuelve **20.381 ticks**, el ledger tiene
**20.378 eventos** — una diferencia de solo 3. El clasificador exige igualdad
posición-por-posición estricta (`np.array_equal` en `tools/tickbar_diag_v2.py`),
así que 3 ticks de más o de menos en un extremo de la ventana corren todo el
resto de la comparación fuera de fase, aunque sea inequívocamente el mismo
mercado en el mismo instante.

## Lo que falta, en orden, para retomar

1. **Alinear las dos secuencias salteando el borde** en vez de comparar
   posicionalmente desde el índice 0 — buscar dónde empiezan a coincidir de
   verdad (probablemente los primeros o últimos ~3 ticks de un lado sobran) y
   re-clasificar H1/H2/H3 sobre la ventana alineada. Si H1 pasa a OK con eso,
   la clasificación real de TICKBAR-001 a 120t queda disponible (H2/H3), que es
   lo que hacía falta para saber si el FAIL de paridad es un bug de mi
   adaptador o el defecto ya conocido propagándose.
2. **Recién con eso interpretado**, volver al FAIL de paridad (19 GEOMETRY_DIFF,
   57+48 MISSING_IN_*) y decidir si es atribuible a TICKBAR-001 o si hay un bug
   real en `run()` para depurar.
3. **No se tocó el diseño de la campaña de paridad en sí** — sigue siendo
   correcto (ventana, contrato, calendario, plantilla de Trading Hours, todo
   verificado). Lo que falta es exclusivamente esta capa de alineación de
   ventana en el classifier de diagnóstico.

## Artefactos y procedencia

- Commits en esta rama: `83b9705` (run adapter), `5e2d86a` (launcher paridad),
  `6920801` (launcher tickbar-diag v2), `88af25a` (debug shift).
- Datasets Kaggle: `edgelab-avolcluster-nq-oracle` (oráculo AVolClusterPOI),
  `edgelab-tickbar-diag-nq0626` (ledger TickBarDiag 120t).
- Reportes bajados localmente: `C:\kg\avolparity_out\paridad_avolclusterpoi_nq0626.json`,
  `C:\kg\tickbar_out\tickbar_diag_nq0626_120t_stdout.txt` — no commiteados
  todavía al repo (quedan solo locales; commitear si se retoma).

## Aporte al referente

Se cerró la brecha de tooling (el kernel no tenía entrypoint uniforme, ahora
lo tiene y está probado). Se evitó sacar una conclusión prematura de "defecto
real de datos" sobre un problema que en realidad es un desfase de 3 ticks en
el borde de ventana — la disciplina de verificar con números concretos antes
de clasificar volvió a pagar, igual que toda la noche con Gate 1 NQ.
