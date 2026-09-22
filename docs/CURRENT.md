# CURRENT — estado vivo

**Fecha:** 2026-09-21  
**Corte:** 2026-09-21  
**Rama del PR #48 (head real, la que ve GitHub):** `feat/unified-nt8-viewer-20260920`.
**Rama de trabajo local (se empuja como fast-forward sobre la de arriba):** `feat/unified-viewer-canonical-20260921`.
Hallazgo de auditoría 2026-09-21: esta sección llamaba "rama viva" solo a la de trabajo local, sin nombrar cuál es
el head real que ve el PR — confuso para cualquiera que solo tenga acceso al repo remoto. Corregido acá.  
**Referente:** `docs/NORTH_STAR.md` · sha256 del cuerpo `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Decisiones vigentes de Nico (2026-09-21)

1. **Una única verdad, una única versión de cada cosa.** Un solo visor (`viewer/nt8_bridge/index.html`) y una sola definición de corredor: `edgelab/research/density_field.py` (HP-007 `D(p,t)`) es la referencia y `viewer/nt8_bridge/density_field.js` su puerto, atado por vectores dorados (`tests/research/test_density_field_js_parity.py`).
2. **Zonas exploratorias visibles por defecto**, con insignia persistente. Luego se sanea y estandariza el visor y se validan todas las paridades: hoy el visor es una maqueta.
3. **El modo de consumo por volumen se mantiene**, rotulado «NO certificado».
4. **Archivados** el visor `hz2a`, `visor_server`, la preview de corredores, los parches `apply_*` y el motor certificado anterior: `archive/viewer_retirado_20260921/README.md`.
5. **El indicador de clusters HFT queda FUERA del proyecto.** Solo se usa el de zonas individuales (`HFTZonesNQPureV4`): `archive/h_cluster_nq_fuera_del_proyecto/README.md`.
6. **Los análisis corren en Kaggle** (antes, por los Workers de Notion). Acceso de escritura verificado el 2026-09-21: crear, ejecutar, leer logs y borrar kernels; crear y borrar datasets. Los bundles del visor **no** se suben (`NO_UPLOAD_VIEWER_BUNDLES`).

## Líneas primarias activas (2026-09-21)

1. **Unificación del visor y de la definición de corredor — HECHA en esta rama.** Detalle y evidencia en `docs/research/VIEWER_UNIFICATION_PROPOSAL_20260921.md`. Paridad Python↔JS: 28 escenarios dorados con pruebas de mutación (17 errores deliberados, todos atrapados) y 12 casos sobre bundles reales de 3 activos con diferencia máxima 0,00 (`tools/verify_density_parity_real_bundle.py`). La paridad sobre datos reales destapó un defecto: zonas con `vol: null`.
2. **Validar la paridad de todos los indicadores en todos los activos — SIGUE.** Después: verlos todos en el visor.
3. **Mejorar la lógica de los corredores de liquidez para incluirla en los análisis — DESPUÉS.** Puntos abiertos ya identificados: la clasificación direccional BULL/BEAR/DUAL (`edgelab/research/corridor_geometry.py`) está `CHARACTERIZATION_UNCERTIFIED`; el dossier HP-007 §3.2 describe un modelo calibrado con constantes distintas a las de `density_field.py`; el consumo por volumen de vela no está certificado.
4. **Cerebro (Edge Brain) y orquestación de análisis en Kaggle.** Revisión y brecha: `docs/research/EDGE_BRAIN_GAP_ANALYSIS_20260921.md`.

5. **HFTZones en los 11 activos — perfil escalado `SCALED_FUNNEL_V1` (2026-09-21).** Mismo motor, umbrales por activo, target-free: la dispersión de densidad de zonas por tick pasó de ~29× a **1,42× en calibración** y **2,09× en validación fuera de muestra** (dos cifras distintas — no resumirlas en un único '1,8×': la corrección la pidió el auditor 2026-09-21) (`docs/research/HFTZONES_ESTANDARIZACION_MULTIACTIVO_20260921.md`, `tools/calibrate_hftzones_universal_profiles.py`, `tools/rebuild_hft_bundles_scaled.py`). Sin paridad con NT8 salvo NQ (`PARITY_ABSTAIN`); deriva fuera de muestra en MES/GC/ZB.
6. **LUX-IMB (OG+VI) reconstruido en Python — validación PARCIAL contra 6E:** 34.179/34.179 zonas exactas (bordes, vencimiento, relleno, toque) con OG cuerpo-a-cuerpo, la geometría del `.cs` (`docs/research/LUX_IMB_VALIDACION_PARCIAL_6E_20260921.md`). Falta: otros activos, barras M1 desde ticks, disponibilidad causal.
7. **L2 en el visor (GC 08-26, 29 sesiones pre-holdout) — ampliado tras la línea 7 original.** Mapa de calor del libro a 1 s de resolución (`tools/build_l2_viewer_bundle.py`); reconstrucción validada contra L1 (bid ≥99,7 %, ask ≥99,99 % en las 29 sesiones). **Reloj de GC resuelto 2026-09-22**: `ts_us` es ART (UTC-3), confirmado con 30/30 sesiones lunes-jueves donde el halt de mantenimiento CME cae exacto a las 18:00 leído como UTC (`docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md`, mismo método que resolvió ES). Lo que sigue sin resolver es la correspondencia absoluta contra los ticks `.Last.txt` (conversor distinto): las velas (5 s y 1 min) siguen saliendo de los trades del mismo feed, nunca por cercanía de timestamp con otra fuente. **Cinta de trades estilo Bookmap:** cada ejecución clasificada por agresor (regla de cotización + tick-test de respaldo, **heurística sin validar contra oráculo**; `meta.trade_classification` publica la fracción por sesión, ~50/50 con <0,03 % neutral en las 29 de GC), agregada por celda tiempo/precio (dibujar cada trade suelto saturaba la pantalla con ráfagas HFT superpuestas — bug real encontrado y corregido) y con radio por percentil (2–15 px) para diferenciar tamaños. **Detectores PROVISIONALES de iceberg y spoofing** (`edgelab/research/l2_manipulation_heuristics.py`, sin ground truth — el feed MBP no trae ID de orden): iceberg = nivel consumido por un trade y rellenado repetidas veces; spoofing = orden grande que aparece y se va rápido sin llenarse. Calibrados por barrido para no marcar el ruido rutinario del touch (4–65 icebergs y 20–300 spoofs por sesión en las 29 de GC); marcados en el visor con signo de pregunta explícito. Base para DeepLOB. **Schema versionado + `price` redundante eliminada (2026-09-22, `edgelab/data/l2.py`):** el parquet L2 queda nombrado `NT8_MBP10_REPLAY_V1` (distinto de `TAPE_LONG_HORIZON_V1` de `.Last.txt` — no se mezclan bajo "ticks"). `price` (float64) se valida fila a fila contra `price_tick*tick_size` (tolerancia 1e-6; residuo real observado ~9,09e-13, puro punto flotante) ANTES de eliminarla — si una fila no cae en grilla, la conversión ABORTA (`PriceRoundtripError`, fail-closed, no escribe nada) en vez de redondear en silencio. Cada sesión ahora escribe `manifests/<sesión>.manifest.json` con procedencia (sha256 fuente+salidas), resultado de la validación y política de redondeo. Ahorro medido: -17 % en el parquet L2 de una sesión real (20260701: 5.982.620 filas L2, 0 violaciones). **Validador de continuidad entre sesiones (2026-09-22, `tools/validate_l2_session_boundaries.py`):** compara cada par de sesiones consecutivas en disco — sin inversión de reloj entre el último evento de un día y el primero del siguiente (`FAIL_CLOCK_INVERSION` si ocurre), clasifica el gap contra el patrón horario **heurístico** medido en GC (empalme <300s lunes-jueves-domingo→día siguiente, fin de semana 6h–4d viernes→siguiente; cualquier otra cosa queda `GAP_UNCLASSIFIED_REVIEW_NEEDED`, nunca aceptada en silencio), y opcionalmente corre `build()` fail-closed sobre el día derecho para exigir `book_status=PASS` antes de declarar la frontera continua. Corrido sobre las 30 sesiones reales de GC 08-26: **29/29 fronteras PASS**, 0 sin clasificar, 0 inversiones. No es un calendario CME certificado (para eso está `edgelab/data/cme_equity_index_calendar.py`, que es de índices y no modela el gap intradiario) — es una heurística explícita, con margen probado contra datos reales. **Orquestador de intake diario (2026-09-22, `tools/l2_daily_intake.py`):** encadena CSV crudo → `convert_l2_session` (price-validado, fail-closed) → chequeo de frontera contra el día anterior → log de custodia append-only (JSONL, un registro por sesión con instrumento/contrato/fecha/downloader/hashes/presencia L1-L2/rango de niveles/resultado) → borrado del CSV **solo si se pide explícitamente** (`--delete-csv-after-validation`, default no borra nada). No baja nada por su cuenta — arranca donde ya existe un CSV, sea que lo bajaste a mano o con un downloader que audites vos (ver Prohibiciones/postura sobre código de terceros en el módulo). **Hallazgo real al probarlo en datos reales de julio (post-holdout, GC 08-26):** la frontera `20260701→20260702` mide un solapamiento de **-5,68 s** (el último evento de un día es más tardío que el primero del siguiente) — el validador lo marcó `FAIL_CLOCK_INVERSION` correctamente en vez de aceptarlo, pero la causa (¿jitter de captura en el corte de NT8? ¿algo más?) queda sin investigar — no es urgente porque ambas sesiones son post-holdout, pero queda registrado para revisar antes de usar esas fechas para cualquier cosa. **Secciones H e I del contrato del visor (2026-09-22, patch externo `edgelab-l2-cells-iceberg-windows.patch`, auditado e integrado):** `trades` publica por celda `trade_count`/`buy_count`/`sell_count`/`neutral_count`/`max_trade_size` (el tooltip mostraba "n/a" honesto porque el builder nunca los calculaba) más `first_ts_us`/`last_ts_us` y el desglose por **método** de clasificación (`method_quote_rule_count`, `method_tick_test_count`, `method_neutral_count`, con sus volúmenes). Sección I (namespacing): `l2` y `trades` quedan versionados y certificados explícitos — `schema=L2_DEPTH_CELLS_V1`/`namespace=l2.depth`/`certification=<book_status>` y `schema=L2_TRADE_CELLS_V2`/`namespace=l2.trades`/`certification=HEURISTIC_AGGRESSOR_UNVALIDATED`. Los percentiles de tamaño de burbuja (`size_tiers`) se calculan en Python por sesión completa (`scale_scope=SESSION`) en vez de en el JS del cliente — estables, no dependientes del viewport (el visor ya sabía consumir `tr.size_tiers` si venía provisto, desde el patch de iteración visual anterior). **Fix real en `IcebergTracker`**: antes solo se guardaba el ÚLTIMO trade atribuido por (lado,tick) — si dos trades golpeaban el mismo nivel dentro de la ventana antes de un descenso, se perdía el volumen del primero. Ahora se suman TODOS los trades en ventana y se limpia la lista tras cada consumo (no se reutiliza el mismo trade en dos descensos). Efecto medido en datos reales (GC 20260615): icebergs bajó de 55 a **43** — menos falsos positivos, no menos cobertura. Verificado: `sum(trade_count) == meta.trades` exacto (92.515), suite completa sin regresiones, confirmado en navegador sin errores de consola y con tooltip mostrando datos reales.
8. **Indicador HFT único en el visor: `HFTZonesNQPureV4`.** Decisión de Nico 2026-09-21. Los bundles del motor `HFTZonesUniversal` se renombran al cargar (`normalizeRuns` en `index.html`) y, si el bundle trae ese indicador, se ocultan las demás corridas (BigTrap2, Gaps2, etc.). El nombre es una etiqueta: la paridad con NT8 sigue siendo solo de NQ.
9. **Bug de origen de zona corregido en los 10 activos con motor `HFTZonesUniversal` (no afecta a NQ).** Con velas de 25 ticks en mercado rápido, varias barras comparten el mismo segundo entero (6B 09-25: 505/28.216); comparar el origen de la zona en nanosegundos crudos contra el arreglo de segundos enteros saltaba esas barras y anclaba la caja lejos de su origen real. Corregido redondeando al segundo antes de buscar.
10. **LUX-IMB (OG+VI) extendido a los 11 activos, sobre barras M1 propias.** `tools/build_lux_imb_m1_bundles.py` arma M1 desde ticks pre-holdout (55 contratos) y corre el detector Python (geometría `body`, validado parcialmente solo en 6E). Sin paridad propia en los otros 10 activos (`PARITY_ABSTAIN`). Disponibles en el visor bajo "Gráfico M1 · LUX-IMB" por activo.

## Resultados de investigación vigentes

1. **HP-008: Clímax HFT Sobre-Extendido con Reversión a la Media y Vuelo Libre en Corredores de Vacío (NQ 25t).**  
   - Dossier: [`docs/research/INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md`](research/INFORME_FALSACION_ABSORCION_HFT_EMA_2026-09-17.md).  
   - Falsación incondicional: la entrada ciega en $t_0$ es perdedora (-1.62 pt) y el micro-scalping muere por fricción CME ($PF=0.75-0.88$).  
   - Razón de Varianzas de Lo-MacKinlay $VR=0.9645$ en 20-50 barras 25t; en días rotacionales con vuelo libre a través de corredores de vacío, +7.30 pt con Win Rate 63.6 %.

2. **HP-007: Corredores de Vacío y Campo de Resistencia Microestructural.**  
   - Dossier: [`docs/research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md`](research/HP-007_DOSSIER_TECNICO_Y_AUDITORIA_CORREDORES_VACIO.md).  
   - El precio viaja 3.03 veces más rápido en tiempo real dentro de corredores de vacío ($D \le 0.28$) frente a congestión ($D \ge 0.70$) ($p = 2.14 \times 10^{-10}$, $Z_{MC} = 5.65$). Backstop: +0.156 R en cortos y +0.076 R en largos.
   - **Ojo:** esas cifras se midieron con el modelo del dossier; el visor ahora muestra `density_field.py`, cuyas constantes difieren (ver línea 3 arriba). No están medidas sobre el objeto exacto que muestra el visor.

## Vector de estado

```text
HP-008_STATUS                           = FALSIFIED_UNCONDITIONAL_SURVIVES_ROTATIONAL_VACUUM
HP-007_STATUS                           = CERTIFIED_MICROSTRUCTURAL_EFFECT (modelo del dossier)
CORRIDOR_DEFINITION                     = density_field.py (reference) + density_field.js (port), DECIDED_2026-09-21
DENSITY_PORT_PARITY                     = 28_golden_scenarios + 12_real_bundle_cases, max_abs_diff=0
CORRIDOR_DIRECTION_CHARACTERIZATION     = CHARACTERIZATION_UNCERTIFIED
H_CLUSTER_NQ                            = OUT_OF_PROJECT (archived)
HOLDOUT_INTEGRITY                       = SEALED_UNTOUCHED (2026-07-01 -> 2026-12-31)
HOLDOUT_BOUNDARY_NS                     = 1782856800000000000
CI_PR48_BEFORE                          = 19_failed_1_error (causas mecanicas)
CI_LOCAL_AFTER_MERGE                    = 1567_passed_1_failed (CURRENT.md, resuelto en este commit)
ULP_TRIAGE                              = 57_entries_PROVISIONAL (lectura, no medicion; medir con tools/ulp_exposure.py)
KAGGLE_WRITE_ACCESS                     = VERIFIED_2026-09-21
CAMPAIGN_OUTCOMES_OPENED                = false
PREEXISTING_OUTCOME_EXPOSURE            = YES
HFT_SCALED_DENSITY_SPREAD_CAL            = 29x -> 1.42x (11 activos, calibracion, ver linea 5)
HFT_SCALED_DENSITY_SPREAD_VAL            = 29x -> 2.09x (11 activos, validacion fuera de muestra, ver linea 5)
HFT_VIEWER_INDICATOR                    = SINGLE_HFTZonesNQPureV4 (motor universal renombrado, paridad solo NQ)
LUX_IMB_PARITY                          = 6E_PARTIAL_34179_of_34179 (otros 10 activos PARITY_ABSTAIN, geometria body)
L2_BOOK_VALIDATION_GC                   = bid>=99.7pct_ask>=99.99pct (29 sesiones pre-holdout)
L2_CLOCK_GC                             = RESOLVED_ART_UTC-3_20260922 (30/30 sesiones, ver RESOLUCION_RELOJ_GC_L2)
L2_CLOCK_GC_VS_LAST_TXT_JOIN            = UNRESOLVED (conversor distinto; join por timestamp prohibido)
L2_TRADE_CLASSIFICATION                 = HEURISTIC_UNVALIDATED (quote_rule + tick_test)
L2_MANIPULATION_DETECTORS               = PROVISIONAL_NO_GROUND_TRUTH (iceberg + spoofing, ver linea 7)
L2_SCHEMA                               = NT8_MBP10_REPLAY_V1 (distinto de TAPE_LONG_HORIZON_V1 de .Last.txt)
L2_PRICE_ROUNDTRIP                      = VALIDATED_FAIL_CLOSED (tolerancia 1e-6, residuo real ~9.09e-13)
L2_SESSION_CONTINUITY_GC                = 29_of_29_boundaries_PASS (heuristica, ver validate_l2_session_boundaries)
L2_DAILY_INTAKE_ORCHESTRATOR             = BUILT_TESTED_NOT_SCHEDULED (l2_daily_intake.py, sin downloader auditado aun)
L2_JUL0701_0702_BOUNDARY_ANOMALY         = MEASURED_EXPLAINED_20260922 (ver L2_BOOTSTRAP_OVERLAP abajo)
L2_BOOTSTRAP_OVERLAP                     = ROOT_CAUSE_MEASURED (rafaga ADD sellada con hora nominal de arranque, no hay evento duplicado, ver SOLAPAMIENTO_FRONTERA_SESIONES_L2)
L2_VIEWER_CONTRACT_SECTION_H              = CLOSED (trade_count/buy_count/sell_count/neutral_count/max_trade_size/method_*)
L2_VIEWER_CONTRACT_SECTION_I              = PARTIAL (schema/namespace/certification en l2.depth y l2.trades; falta leyenda visible en UI)
L2_ICEBERG_MULTI_TRADE_ATTRIBUTION_FIX    = MEASURED (GC 20260615: icebergs 55 -> 43, menos falsos positivos)
```

## Medido: P-68

El volumen del scan v2 ya excluye la ventana de mantenimiento. No hace falta una normalización adicional de NQ 09-26 para calcular los rolls.

Sensibilidad sobre la implementación real:

| Variante | Días | Rolls |
|---|---:|---|
| weekdays | 237 | 2025-09-17, 2025-12-16, 2026-03-17, 2026-06-16 |
| weekdays menos 9 feriados | 229 | las mismas cuatro fechas |

Contratos y ratios `leader_over_current` fueron idénticos a 6 decimales: 3,396162; 1,260126; 1,125767; 2,286790.

**No medido/certificado:** completitud de fuente. La sensibilidad asume `complete_session=True` para aislar el efecto del calendario. Por eso no certifica el manifiesto.

## Bloqueos actuales

1. ~~Obtener las horas oficiales CME.~~ **RESUELTO 2026-09-02 (`4f365bf`)**: el WAF bloquea `curl` y el fetcher, pero el endpoint JSON oficial que la propia página consume (`/services/trading-hours-by-product`) responde 200 desde el origen y **sirve fechas históricas**, así que 2025 también quedó cubierto. Calendario con evidencia hasheada en `docs/research/cme_equity_index_calendar_20260902/`, valida contra el gate. Corrobora el patrón de 1140 min = early close 12:00 CT (7 de 8 early-close dentro de 0-6 min). **Pendiente**: Juneteenth 2026-06-19 (fuente ambigua vs 115.146 ticks observados), por eso corta el 18-jun.
2. Construir cobertura de fuente separada del calendario.
3. Producir evidencia de completitud aprobable.
4. Reconstruir el manifiesto y verificar formalmente los cuatro rolls.
5. Reconstruir los traces por intervalo contractual con reset total.
6. Resolver paridad/lifecycle aVolClusterPOI: 19 `GEOMETRY_DIFF`, 57 `MISSING_IN_NT8`, 48 `MISSING_IN_PYTHON`; primero corregir alineación de borde de ~3 ticks.

## NQ 09-26

Medido: 363.601 ticks y volumen 398.066 en 16:00–17:00 CT, nueve días hábiles del 17 al 30-jun. `ts_local_ns == ts_utc_ns` en todas las 6.235.464 filas. El re-corte no introdujo el fenómeno.

Inferido: plantilla NT8 distinta. Sigue sin confirmación directa y el artefacto conserva `root_cause_status=UNRESOLVED`.

Consecuencia: no afecta la señal causal del roll del 16-jun, que usa D-1. Sí afecta comparaciones crudas de volumen del 17–30 si no se excluye mantenimiento; el scan v2 ya lo excluye.

## Ramas

- **Head real del PR #48:** `feat/unified-nt8-viewer-20260920`. **Rama de trabajo local:** `feat/unified-viewer-canonical-20260921`, se empuja como fast-forward sobre la de arriba.
- `foundation/f0b-compatibility-probe`: integración.
- `audit/notion-ai-sltp-p2b-provenance-20260830`: congelada, no mergear ni borrar.
- Cadena del Edge Brain (#43 → #46 → #52, más #49): sin mergear; arreglo de conexiones sqlite pendiente en `fix/brain-close-sqlite-connections-20260921` (local, no empujada).
- Registro: `docs/BRANCH_REGISTRY_2026-09-02.md`.
- `research/avolcluster-nq-parity-oracle-20260901`: mergeada a `foundation` el 2026-09-03. Índice y reservas: `docs/research/PARIDAD_AVOLCLUSTERPOI_INDICE.md` (P-71). Outcomes: `CAMPAIGN_OUTCOMES_OPENED = false`.
- `research/gate-regime-context`: `FOUNDATION_EXECUTABLE`, `CHECKPOINT_PENDING_REAL_DATA`, `NOT_YET_OPERATIONAL`.
- `work/crypto-context-foundation-20260824`: PR #14 draft; CI roja; no mergear.

## No tocar sin decisión explícita

- outcomes, P&L, MAE/MFE, EF0 o holdout;
- reglas de completitud o tolerancias;
- specs/splits congelados;
- ramas G2 rivales;
- borrado/cierre/merge de ramas;
- parquets, artefactos o cuarentenas publicados.

## Índices canónicos

- `PROJECT_INDEX.md`
- `AUDITOR_START_HERE.md`
- `docs/PROJECT_CHRONOLOGY_2026-09-02.md`
- `docs/BRANCH_REGISTRY_2026-09-02.md`
- `docs/OPEN_IDEAS_INDEX_2026-09-02.md`
- `PENDIENTE.md`

## Aporte al referente

 Un solo visor y una sola definición de corredor con puerto verificado (28 escenarios dorados + 12 casos reales, diferencia 0); Kaggle con acceso de escritura probado de punta a punta; y medido qué le falta al Brain para orquestar análisis con garantías (corredor de episodios con auditoría de holdout). Ampliado en el resto de la sesión (líneas 5–10 y el vector de estado): HFTZones queda con densidad comparable en los 11 activos (29×→1,42× en calibración, 29×→2,09× fuera de muestra) y un único indicador visible en el visor; se corrigió un desfase real de las cajas HFT en 10 activos (origen de zona con múltiples barras por segundo); LUX-IMB se extendió a los 11 activos sobre M1 propio, con validación parcial solo en 6E; y el visor sumó una vista tipo Bookmap de L2 (libro, trades clasificados por agresor, detectores provisionales de iceberg/spoofing) para GC, con todas las heurísticas explícitamente marcadas como no validadas.

**2026-09-22 (reloj GC L2):** se resolvió el reloj de `ts_us` para GC 08-26 (ART, UTC-3) con el mismo método forense que ES, sobre 30/30 sesiones sin excepción — reduce la distancia hacia un pipeline L2 auditable porque saca de "sin resolver" al reloj interno del libro (bloqueo técnico que el auditor externo marcó como prioridad 1 para poder versionar el schema L2 y automatizar la captura diaria). No resuelve la correspondencia GC L2 ↔ `.Last.txt` (sigue prohibido unir por cercanía de timestamp) ni toca `CUTOFF_DATE`/holdout.

**2026-09-22 (schema L2 + `price` eliminada con validación):** siguiendo la segunda prioridad del auditor externo, el parquet L2 queda versionado (`NT8_MBP10_REPLAY_V1`) y `price` (float64, redundante con `price_tick`+`tick_size`) se elimina solo después de validar fila a fila que reconstruye dentro de una tolerancia de punto flotante (1e-6; el residuo real medido es ~9,09e-13) — si una fila no cae en grilla, la conversión aborta en vez de redondear en silencio (`PriceRoundtripError`, fail-closed). Cada sesión ahora queda con manifest propio (procedencia + resultado de la validación). Reduce la distancia hacia automatizar la captura diaria porque cierra el punto que el auditor marcó como condición para tocar `price`: no alcanza con que el cálculo sea autoconsistente, hay que probar que la fila original estaba en grilla.

**2026-09-22 (validador de continuidad entre sesiones):** tercera pieza de la cola del auditor externo. `tools/validate_l2_session_boundaries.py` deja de asumir que diez descargas de fechas consecutivas son diez sesiones continuas — lo mide, por frontera, contra reloj (inversión = fail duro) y contra un patrón horario heurístico explícito (nunca acepta un gap en silencio si no calza). Corrido sobre las 30 sesiones reales de GC: 29/29 fronteras PASS. Reduce la distancia hacia poder automatizar la descarga diaria sin tener que confiar a ciegas en que "llegó el archivo" implica "el libro es reconstruible sin agujeros".

**2026-09-22 (orquestador de intake diario):** cuarta pieza — `tools/l2_daily_intake.py` encadena las tres piezas anteriores (conversión validada, chequeo de frontera, custodia) en un solo paso reproducible, listo para que Task Scheduler lo dispare apenas exista un CSV nuevo. Deliberadamente no baja nada por su cuenta (la descarga sigue siendo responsabilidad de Nico, por la postura del proyecto sobre no ejecutar código de terceros no auditado). Probado de punta a punta con datos reales de julio y encontró algo real sin buscarlo: un solapamiento de -5,68s entre dos sesiones consecutivas que el chequeo de frontera marcó correctamente en vez de aceptar en silencio — queda registrado como hallazgo abierto, no bloqueante. Reduce la distancia hacia automatizar la captura porque ya no falta más que decidir el mecanismo de descarga; todo lo de después está construido y probado.

**2026-09-22 (causa raíz del solapamiento de frontera entre sesiones — antes `MEASURED_UNEXPLAINED`):** al reconvertir GC 12-26 con el pipeline actual, 5 de 6 fronteras lunes-jueves midieron el mismo solapamiento negativo chico (-4,0s a -7,6s) que ya había visto sin explicar en GC 08-26 (20260701→20260702, -5,68s) — dejó de ser un caso raro para ser un patrón sistemático. Inspección fila a fila: no hay ningún evento duplicado (los precios de la cola de un día y la cabeza del siguiente no coinciden) — la ráfaga de bootstrap (ADD) que reconstruye el libro al arrancar el archivo nuevo queda sellada con la hora NOMINAL de arranque de sesión, no con una hora de llegada real, y por eso puede quedar "antes" de la cola genuina de actividad del día anterior. `tools/validate_l2_session_boundaries.py` ahora reconoce este patrón específico (`EXPECTED_BOOTSTRAP_OVERLAP`, margen de -30s calibrado sobre 6 mediciones reales en dos contratos, ~4-7× más laxo que lo medido) sin dejar de fallar duro ante cualquier otra inversión de reloj. Acta: `docs/research/SOLAPAMIENTO_FRONTERA_SESIONES_L2_20260922.md`.

**2026-09-22 (secciones H e I del contrato del visor L2 — auditoría e integración de patch externo):** quinta pieza, retomando lo que había quedado explícitamente sin cerrar en la iteración visual anterior. Audité el patch `edgelab-l2-cells-iceberg-windows.patch` contra el HEAD correcto, revisé la lógica línea por línea, lo reconcilié con mi propia versión más simple de la sección H (la reemplacé, no las dejé superpuestas) y lo integré. Cierra H (conteos/timestamps/método por celda) e I parcialmente (schema/namespace/certification explícitos en `l2.depth` y `l2.trades`) — y de paso corrige un bug real de conteo en `IcebergTracker` que ni mi versión ni la anterior habían tocado (medido: 55→43 icebergs en la misma sesión real, menos falsos positivos).

**2026-09-22 (revisión global con Opus — consolidación antes de research nuevo):** diagnóstico contra el referente: mucha infraestructura de calidad, ningún candidato vivo, y 40 PRs abiertos como riesgo principal de integración. Hecho en esta tanda, en orden: (1) triage objetivo de los 40 PRs (`docs/audits/TRIAGE_PRS_20260922.md`: 3 troncos vivos reales; #28/#29/#31 ya absorbidos por `foundation`; la raíz de la cadena de septiembre `audit/edge-discovery-factory-foundation-20260919` no tiene PR; #51 apunta a `main` — merges/cierres quedan para Nico); (2) primera memoria de mercado del Edge Brain: 7 hipótesis cerradas ingeridas al Hipocampo durable con su condición de reapertura (#56, `86c24b1`); (3) paquete STOP para la próxima campaña (`docs/research/STOP_PAQUETE_PROXIMA_CAMPANA_20260922.md`: recomienda réplica multicontrato de HP-008 condicional — 1 hipótesis — antes que P7 Frontier — 48 políticas —; nada corrido sobre retornos, espera OK); (4) `tools/l2_intake_sweep.py`: todo lo posterior a los dos clics de NT8 (downloader + NRDToCSV) en un comando idempotente. Aporte al referente: bajo el costo de integración y dejó la próxima campaña lista para decisión, en vez de sumar un frente más.
