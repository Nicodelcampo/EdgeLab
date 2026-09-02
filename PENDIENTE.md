# PENDIENTE — decisiones abiertas

Registro de decisiones que el código señala explícitamente como "pendientes de
Nico/auditor". Ninguna de estas se toma unilateralmente en una implementación.
Cada entrada nombra el punto exacto del código que la referencia.

**Punto de entrada para continuidad**: `docs/research/HANDOFF_AUDITORIA_2026-08-14.md`.

> **Ocho decisiones del 2026-08-15**: `docs/DECISIONES_2026-08-15.md`. Afectan a
> P-07, P-10, P-18, P-25, P-28, P-31, P-32 y P-33. En una línea cada una:
> Kaggle sale del programa (cierra P-07 por reducción de alcance y acota P-18);
> las columnas duplicadas son podables — verificado en **56/56 archivos,
> 1.015.587.419 filas, cero diferencias**; P-28 pasa de indicio a hecho medido;
> `BARRA_PROCESADA` nunca se quitó (era el test el que caducó); P-33 se resuelve
> por hash y no moviendo carpetas; el conjunto de P-32 quedó nombrado con paridad
> representativa para el trío P-16; y de los tres merges de P-10 se mergeó sólo
> `docs/lux-imb-source-correction`.

**Procedencia de P-24…P-29 (asentadas 2026-08-15)**: ninguna de las seis existía en
este board aunque los documentos ya las referenciaban como si existieran —
P-24/P-25/P-26 desde la página de Notion del auditor «Auditoría de los índices
sellados y GO para el re-corte físico (15-ago)» y desde
`docs/research/PRECHECK_HOLDOUT_2026-08-15.md` §2 y §8; P-27/P-28/P-29 desde
`docs/research/RECUT_EXECUTION_2026-08-15.md` §H-5, §H-7, §H-8 y su tabla final.

El patrón se repitió dos veces en el mismo día, así que conviene nombrarlo: **el
auditor numera puntos dentro del informe que escribe, y el board no se entera.**
Un doc que apunta a una entrada inexistente se lee como si la decisión estuviera
registrada cuando no lo está. Regla operativa: **el board es el registro auditable;
Notion y los informes son publicación. Si divergen, manda el board**, y el commit
que introduce un `P-NN` nuevo en un informe asienta la entrada acá en el mismo
commit — es la regla de «registro MEDIDO/NO MEDIDO en el mismo commit» aplicada al
board.

P-30 y P-31 se numeraron después de P-29 justamente para no pisar la numeración que
el auditor ya había publicado en `RECUT_EXECUTION_2026-08-15.md`. **P-32** se asentó
acá el mismo día, desde `docs/research/PROGRAMA_ANALISIS_FEATURES_2026-08-15.md`
(`32fcc271b3f494bcd7fc673ab3b4963604a22b75`): el auditor la abrió en el informe y
declaró explícitamente no tocar el board «para no pisarlo a ciegas» — correcto como
coordinación, pero deja la entrada huérfana hasta que alguien la asienta. Es la
tercera vez en el día.

**P-33 y P-34** salieron del intake de los oráculos de `HFTZones2` / `aVolCellPOI2`
del 15-ago. P-34 documenta una cuarentena que **se levantó con prueba de equivalencia**,
no con un supuesto: los oráculos quedaron habilitados.

**P-35, P-36 y P-37** vienen de la auditoría de debilidades del 15-ago
(`docs/research/AUDITORIA_DEBILIDADES_Y_GATES_2026-08-15.md`). Las reportó el auditor y
**se re-verificaron contra el código** antes de asentarlas: las tres citan archivo y
línea. **P-35 y P-37 son decisiones de semántica de gating — de Nico, nadie más.**

> **Lo que esa auditoría dice del referente, y no conviene enterrar entre P-NN**: el
> proyecto es **fuerte en no engañarse y débil en acercarse a una cuenta**.
> `EDGES_DISCOVERED.md` sigue diciendo *ninguno*; H1 murió en −2,47 ticks/evento; G2
> nunca se ejerció contra una campaña real; no hay costos propios por instrumento (W7);
> F4 constitucional nunca se corrió. **Ninguno de los P-25…P-37 mueve el ítem 1 de la
> jerarquía.** Cerrarlos es higiene, no distancia recorrida.

**Inventario de ramas**: `docs/INVENTARIO_DE_RAMAS_2026-08-15.md` distingue las ramas
*superadas* (contenido ya aplicado, mergearlas duplicaría historia) de las *pendientes*
(traen algo que no está en ningún lado). `tools/estado.py` las marca todas igual.

---

## P-01 · Tratamiento de `SIN_ZONAS` en el gate de balance

**Estado**: RESUELTA (2026-08-13).

Cerrada por la transición hacia el nulo reflectivo F2.7 / F2.8 y la simplificación de micro-régimen F2.9 / F2.10. En el pipeline de matching heredado, la opción neutral (Opción B: exclusión explícita reportada en `archivos_excluidos` sin corromper el balance global de covariables continuas) es la norma adoptada.

---

## P-02 · `removed_reason="max_age"` es inalcanzable

**Estado**: RESUELTA (2026-08-13).

Cerrada por diseño en F2.7 / F2.8: el estimand primario de primer pasaje adopta un horizonte explícito simétrico e idéntico para la zona real y el espejo ($H_i$), eliminando el código muerto de riesgos competidores no identificables y censura asimétrica.

---

## P-03 · Falta de soporte común entre zonas y controles

**Estado**: RESUELTA (2026-08-12).

Cerrada por decisión de la enmienda F2.7. La curva F2.5 demostró que el estimand `v3-local` no posee soporte común medible bajo K-NN sin deflactar la varianza de referencia; sucesora: F2.7 (Nulo Local por Reflexión de Geometría, spec v2).

---

## P-04 · Duplicado de gobernanza en la rama

**Estado**: RESUELTA (2026-08-12).

La rama sucesora fue rehecha sobre `audit/p0-bigtrap2-drift@1916ffa`; el primer commit de la historia corregida es `9fcdd9c` y el ancestro de auditoría es verificable mecánicamente.

---

## P-05 · CI declarada, verificación remota pendiente

**Estado**: ABIERTA — parcialmente resuelta en código.

La rama incorpora `.github/workflows/ci.yml` (instala `requirements/core-bridge-dev.lock`, ejecuta `pytest -q` en push/PR). Falta confirmar en la pestaña Actions que el workflow ejecutó con el lock exacto y terminó verde (los pushes del 2026-08-14 lo dispararon). No relajar pins para forzar un verde.

**Criterio de cierre**: run remoto visible, verde, con el lock exacto; registrar el enlace.

**Nota (2026-08-14)**: el Contrato Kaggle v2 considera que un `Save & Run All` reproducible cumple la función de CI para los notebooks. Eso NO sustituye este punto: los scripts de sandbox que dependen de `/data/p16` viven en `tools/sandbox/` y quedan deliberadamente fuera de `tests/` para no romper `pytest -q`.

**Nota (2026-08-14, builder de Kaggle)**: `tests/test_kaggle_bundle_builder.py` corre el self-test de `tools/build_kaggle_bundle.py` por subproceso. Usa `pytest.importorskip("numpy")` y no toca datos reales ni pyarrow: si el runner de CI no trae numpy, el test se saltea en vez de fallar en falso.

---

## P-06 · El gate `MAX_ABS_SMD ≤ 0.10` no tiene panel de calibración sintético

**Estado**: ABIERTA — anotada, no construida (instrucción explícita: no construir el panel ahora).

El umbral 0.10 es convención de la literatura; no existe panel propio que mida error tipo I ni potencia para este matcher concreto. Queda registrado para decidir con pre-registro propio si se construye antes o después de la corrida formal de 201 sesiones.

---

## P-07 · M0 — decisión de licencia de los datos locales

**Estado**: **CERRADA POR ALCANCE (2026-08-15, D-1)** — no por dictamen legal. Kaggle sale del
programa: si no se publica nada, no hay distribución. El gate `ABSTAIN_LICENSE`
**se conserva** como red contra publicar por accidente. Acta: [`docs/DECISIONES_2026-08-15.md`](DECISIONES_2026-08-15.md) D-1.

**RESIDUAL VIVO, y no lo cierra D-1**: la pregunta legal sobre los datos *locales*
sigue sin respuesta, y la V1 sigue subida (ver P-18).

La plantilla ya existe: `docs/research/DATA_LICENSE_DECISION.md` (2026-08-14), con `status: PENDING`, cuatro campos `<por completar>` (proveedor, responsable, fecha de aprobación, sha256 de los términos) y las cuatro preguntas que hay que responder (§1). Lo que falta es **la decisión**, no el documento. Insumos del 2026-08-14: docs de política CME/Kaggle commiteados en `bda944a`.

**Criterio de cierre**: Nico aporta la fuente de los términos y aprueba el documento.

**Agravante (2026-08-14)**: la Versión 1 del dataset de Kaggle ya contiene ticks crudos subidos antes de cerrar M0, contra la prohibición explícita del contrato ("no subir ticks crudos hasta resolver licencia y política de datos"). El dataset es privado, lo que limita la exposición a terceros, pero no cierra el gate. Ver P-18 y `docs/research/KAGGLE_M1_SELLO_Y_VALIDACION_2026-08-14.md` §4.

**Gate de código (2026-08-14)**: `tools/build_kaggle_bundle.py` lee el bloque legible por máquina `EDGELAB-LICENSE-GATE` de ese documento en cada corrida. Sin `status: APPROVED` el veredicto es `ABSTAIN_LICENSE`: no emite `dataset-metadata.json`, no stagea un solo byte y sale con código 2. Si el documento declarara un nombre de licencia que afirme derechos de redistribución (`CC0-1.0`, `CC-BY-*`, `PDDL`, `ODbL`, `MIT`, `Apache-2.0`, `Unlicense`) el tool **aborta**, no abstiene. El punto sigue ABIERTO: un gate impide publicar por accidente, no reemplaza la decisión humana. Ver P-23.

---

## P-08 · Identidad del `BigTrap2.cs` local vs blobs del repo

**Estado**: RESUELTA (2026-08-14, commit `2ad04ec`; actualizada al blob `62b0c951` tras el fix de P-13).

La copia canónica vive en `nt8/BigTrap2.cs` y es byte-idéntica a la que corre en NT8 (verificado por git-blob). Residual no bloqueante: `nt8/README.md` sigue listando BigTrap2 como v2.1 — actualizar el inventario con el blob `62b0c951` y subir el string `version` del meta (hoy dice 2.5.2 con el código ya cambiado).

---

## P-09 · El JSON formal AVOLT no cierra contra su propio sello

**Estado**: ABIERTA — mecánica.

`diag/tasa_senales/AVOLT_formal_d5c41684e162.json`: el sha256 declarado no cierra y `session_means` trae 176 valores contra 188 declarados. Regenerar desde el runner y recommitear.

---

## P-10 · Merges que cambian semántica de validación, pendientes de decisión

**Estado**: **DECIDIDA (2026-08-15)**, delegada por Nico. Fundamento:
[`docs/research/DECISIONES_P35_P37_P10_2026-08-15.md`](research/DECISIONES_P35_P37_P10_2026-08-15.md).

1. `docs/lux-imb-source-correction` — **ya estaba mergeada** (`830f79e`). El board
   la listaba de mas.
2. `research/ym-prerange-session-window` — **MERGEADA** (`d6e0e2c`). Cero conflictos,
   no toca semantica de gates, 12/12 en `tests/test_sessions.py`.
3. `fix/g2-a1-*` — **NINGUNA de las dos**. No son dos merges: son **dos contratos
   canonicos rivales** que conflictuan en 8 archivos. Se adjudican corriendo la
   validacion diferencial que la propia rama A ya trae
   (`.github/workflows/g2-a1-validation.yml`) contra casos de verdad conocida.
   **Disparador: la primera campana que ejercite G2.** Hoy no hay candidato.

1. `fix/g2-a1-statistical-semantics` + `fix/g2-a1-calibration-hardening` (calendario obligatorio, `MIN_DSR_SESSIONS`, DSR V1/V2).
2. `research/ym-prerange-session-window` (`minute_window_matrices` con calendario explícito).
3. `docs/lux-imb-source-correction` (retracta la premisa de H-COND-1).

**Criterio de cierre**: una decisión merge/no-merge por rama, registrada acá.

---

## P-11 · El oráculo aVol de ES 09-26 no existe (archivo duplicado del 06-26)

**Estado**: RESUELTA (2026-08-14, commit `78de4d6`) — verificada.

Archivo re-exportado: blob `bd8b72652dbf5e6d73686f4014d5cad108353b0d`, meta `instrument=ES 09-26` correcta, 1.066 eventos, ventana 01-may→30-jun, `session_index` arranca en 22 (perfil caliente, sin el defecto H3). Cerrada además por el replay W3 (ver `W3_PARIDAD_SANDBOX_2026-08-14.md`).

---

## P-12 · Faltaba el parquet 6E 09-26 de 90 días (abril incluido)

**Estado**: RESUELTA (2026-08-14) — cerrada con medición.

Llegó el parquet genuino 04-01→06-30 (sha256 `1311bc5ea91a111d…`, 1.131.047 filas, manifiesto coincidente). Replay sandbox del kernel byte-verificado contra el oráculo completo post-fix, ventana abril+mayo (15.339 ticks, back-month):

- **TRAPs: 171/171 EXACT (100 %)** — side, vol, geometría, close, volúmenes, conteos idénticos; 0 field_diff; 0 MISSING_IN_PYTHON; 1 MISSING_IN_NT8 dentro de una cola suprimida documentada (resync del 19-abr).
- **Los 9 TRAPs pre-rotura (01→16-abr), uno por uno: 9/9 EXACT.**
- P1A PASS (5.638 barras, quote_fraction 0,9999, 0 mismatches); ciclo de vida idéntico en conteos (15 creadas / 15 invalidadas / 8 tocadas en ambos lados).

Evidencia completa: `docs/research/W1_PARIDAD_SANDBOX_R2_2026-08-14.md` §3 y el HANDOFF §0.

---

## P-13 · BigTrap2 time:1 — silencio de TRAPs del oráculo después del 16-abr

**Estado**: RESUELTA (2026-08-14, commits `f77a3be` + `c899970`) — medida; etiqueta formal pendiente de la corrida local gobernada.

Raíz: el `return` del camino de tiempo dejaba inalcanzable el reset de `sesionNoConfiable` → supresión permanente tras el primer mismatch (17-abr). Fix verificado sobre el patch. Oráculo nuevo (blob `0837ef7e`, sha256 `4c76a0f2…`): 3.807 TRAPs, 9 resyncs con contadores (1 por sesión marcada del oráculo viejo). Comparación 1:1 junio: **3.628/3.638 EXACT (99,73 %)**, resto 100 % atribuido (128 colas suprimidas documentadas, 1 barra de borde, 2 field_diff de 1 tick entre las dos rutas NT8, 8 del lado Python: 7 = defecto del parquet 25-jun → P-14; 1 = anomalía 06-24 08:56 a investigar local).

Decisiones registradas: (a) Nico decidió que futuras versiones del `.cs` MARCARÁN los eventos en el log en vez de suprimirlos; (b) divergencia semántica medida a decidir en la campaña: la supresión por sesión hace el universo de traps de junio del oráculo 3,4 % menor que el del kernel; (c) borrar la copia vieja `..._completo__Minute1.csv` (blob `fb41f33a`, la filtrada).

---

## P-14 · Defecto del 25-jun en el parquet de junio de 6E 09-26 (`46413432…`)

**Estado**: ABIERTA — causa raíz identificada (2026-08-14), fix pendiente en local.

Al build junio-only le faltan minutos activos del 25-jun (11:02–11:10 ART; el nativo tiene barras de 314–1.893 ahí) y la barra 12:48 ART viene inflada (227 vs 37). **La causa está en el build, no en la fuente**: el build 90d (`1311bc5e…`) SÍ trae esos minutos (sonda medida: 245/849/389 ticks en 11:02/11:05/11:08).

**Criterio de cierre**: adoptar el build 90d (o re-cortar junio desde él), agregar a la batería el chequeo "0 minutos faltantes en horario activo contra la serie nativa", y auditar por qué el build junio-only perdió ese bloque.

**Generalización (2026-08-14)**: la batería quedó implementada y generalizada a los 11 activos en `edgelab/kaggle/integrity.py` (`session_activity`, `missing_active_minutes`, `weekday_histogram`), y la corre `notebooks/kaggle/01_dataset_validation.py` por archivo y por sesión. Aplicar el umbral de sesión completa (1.380 minutos) sólo al front month: en back month la baja cobertura es liquidez, no defecto (medido en 6E 09-26: 11 sesiones completas / 28 parciales / 27 escasas).

---

## P-15 · Defecto del 11-jun en el parquet de junio de ES 09-26 (`e11d664d…`)

**Estado**: ABIERTA (2026-08-14) — detectada por el replay W3.

El replay aVol sobre ES 09-26 diverge en fase de bloques **solo el 11-jun** (sesión 51): mis bloques cierran ~2 min antes que los del oráculo desde la mañana, offset estable durante el RTH → mi serie tiene ~2 barras menos que la de NT8 ese día. El parquet no muestra hueco propio en RTH (19 gaps de 60–93 s, todos en la madrugada ilquida del 10→11 CT). Consecuencia medida: 21 missing + 21 extras ese día y contaminación del historial aVol posterior (Δthreshold/Δsamples en 20 sesiones siguientes). Fuera de eso la paridad es exacta (pre: 119/119; post: 307/311).

También documentado (mismo replay, cosmético): `direction=NEUTRAL` del oráculo vs `None` del kernel en AT_PRICE_CREATED (unificar), y drift de `session_index` desde la frontera domingo 21-jun → lunes 22 (convención de conteo del SessionIterator en domingos; etiqueta, no entra a la matemática).

**Criterio de cierre**: comparación nativo-vs-parquet minuto a minuto del 06-11 en local (misma batería que P-14: "0 minutos faltantes en horario activo"), regeneración del mensual de junio ES, y re-run del replay esperando ≥ 465/467 con los mismos criterios.

---

## P-16 · Réplica de paridad de `AACloseOpenDiffs`, `VolTicksPOC2` y `Gaps2`

**Estado**: RESUELTA (2026-08-14) — réplica del auditor ejecutada en sandbox; mediciones locales confirmadas al detalle.

Se incorporaron los 3 oráculos de 90 días en `data/nt8_oracles/` y Antigravity ejecutó las mediciones de paridad en el entorno local gobernado (`docs/research/PARIDADES_LOCALES_ANTIGRAVITY_2026-08-14.md`). El auditor externo corrió luego la réplica target-free independiente en sandbox sobre el parquet canónico 90d (sha256 `1311bc5e…`, 1.131.047 filas, P1A PASS), con kernels byte-verificados por git-blob y el matcher del repo:

1. **`AACloseOpenDiffs` (v1.2)**: 18.004 MATCHED / 18.020 NT8 — **idéntico al local**, incluidos los residuos (GEOMETRY_DIFF 4, TIMESTAMP_DIFF 1, MISSING_IN_NT8 60, MISSING_IN_PYTHON 11).
2. **`VolTicksPOC2` (v2.1)**: 151 MATCHED + 1 FEATURE_DIFF / 153 NT8 en ventana — reproduce el local (151/152); la zona 153 (creada 30-jun 05:01) es la diferencia de contabilidad documentada en el reporte.
3. **`Gaps2` (v2.0)**: 11.435 MATCHED / 11.442 NT8 — **idéntico al local** (FEATURE_DIFF 2, MISSING_IN_NT8 6, MISSING_IN_PYTHON 5; MATURITY_TAIL 4 vs 3 declaradas).

**Nota de gobernanza**: el gate estructural estricto del repo (`parity.py`: PASS exige cero huérfanas y cero diffs de geometría) etiqueta los tres FAIL; los residuos son los mismos que la medición local documentó (colas de borde, frontera de warmup, cola inmadura). La réplica confirma la **reproducibilidad** de las mediciones por tercero independiente; declarar los indicadores con paridad representativa bajo esos residuos es decisión de Nico.

Evidencia: `docs/research/P16_REPLICA_AUDITOR_2026-08-14.md`.

---

## P-17 · El corte UTC del holdout filtra la sesión del 1-jul (leak medido)

**Estado**: RESUELTA EN CÓDIGO (2026-08-14) — pendiente de ratificación normativa de la enmienda v2.1.

El Contrato Kaggle v2 exige bloquear el holdout "por `session_key` y `session_date` en America/Chicago, no sólo por un timestamp UTC". Un corte por timestamp en `2026-07-01T00:00:00Z` equivale a 2026-06-30 19:00 CT, es decir **dos horas después** de que abriera la sesión del trade date 2026-07-01 (Globex abre a las 17:00 CT del día anterior). Esas filas son holdout y el corte UTC las conserva.

**Medición sobre el parquet canónico `6E_09-26_ticks.parquet`** (sha256 `1311bc5e…`, 1.131.047 ticks):

| Regla | Filas conservadas |
|---|---|
| corte UTC ingenuo (`ts_utc_ns < 2026-07-01T00:00Z`) | 1.128.049 |
| regla de sesión de Chicago (`trade_date ≤ 2026-06-30`) | 1.127.178 |
| **leak del corte UTC** | **871** |

Un solo contrato de 1,13 M ticks filtra 871 filas de holdout. El contrato tipifica "cualquier fila holdout" como causal de invalidación de la versión completa, así que el corte UTC habría contaminado el análisis entero de forma silenciosa.

**Resolución en código**: `edgelab/kaggle/sessions_cme.py` (trade date derivado de la tzdata del sistema, transiciones DST por bisección al segundo, sin reglas hardcodeadas) + `edgelab/kaggle/seal.py` (corte por trade date, conteo de filas cortadas por fecha, métrica explícita `rows_leaked_by_naive_utc_cut`, y apertura del holdout sólo con el token `M8_HOLDOUT_OPENED_ONCE`; sin token, `assert_no_leak` levanta excepción — fail-closed).

**Verificación**: self-test de 7 casos de frontera de trade date + paridad exacta streaming↔batch en 4 tamaños de batch (28 claves de integridad, 594 claves de actividad, 66 trade dates, sello idéntico). Evidencia: `tools/sandbox/kaggle_streaming_parity.py` y `docs/research/KAGGLE_M1_SELLO_Y_VALIDACION_2026-08-14.md` §1 y §5.

**Refuerzo (2026-08-14)**: el sello dejó de ser sólo una biblioteca. `tools/build_kaggle_bundle.py` v2 lo aplica como gate de publicación (`G-HOLDOUT`): un archivo cuyo `ts_max` alcanza `2026-06-30T22:00:00Z` no es elegible, y el corte ingenuo se sigue calculando sólo para reportar el leak que produciría (7.200 s). Verificado al nanosegundo en el self-test (T1, T1b, T1c, T6d).

**Criterio de cierre**: Nico ratifica la cláusula 1 de `docs/research/KAGGLE_ENMIENDA_V2_1_2026-08-14.md` y ningún artefacto formal usa un corte por timestamp UTC.

---

## P-18 · La Versión 1 del dataset de Kaggle incumple la Fase 0 del contrato

**Estado**: **RESUELTA (2026-08-26, `USER_REPORTED`).** Nico borró el dataset de Kaggle
(acción humana que era el único criterio de cierre pendiente). No verificado por API
propia — no hay credencial de Kaggle en este entorno para confirmarlo de forma
independiente; se registra como reportado por el usuario, no como `MEASURED_COMMITTED`.
Ver también `docs/research/CME_Market_Data_Policy_Cloud_Kaggle.html`: la prohibición de
subir ticks reales a Kaggle es contractual (ILA de CME), no una preferencia de diseño —
aplica a cualquier intento futuro, privado o no, y también descarta a Kaggle como
plataforma de **cómputo** sobre datos reales, no sólo de publicación.

**Histórico (ya no aplica, se conserva para trazabilidad)**: Ya no bloquea el pipeline local (Kaggle
sale del programa), pero **el residual es intacto**: la V1 con ticks crudos y
holdout físico sigue publicada. **Acción humana de Nico: borrar el dataset.**
Ninguna herramienta lo hace.

El dataset privado `nicolasbuttaro/edgelab-cme-futures-universe` Versión 1 (17,97 GB, 57 archivos, 728 columnas declaradas por Kaggle) no puede ser el **dataset exploratorio** del contrato. Cuatro incumplimientos, ninguno inferido:

1. **Holdout físicamente presente**. El contrato exige que "el holdout esté FÍSICAMENTE ausente del dataset exploratorio" y tipifica el STOP "cualquier fila holdout: invalidar toda la versión". Los contratos `*_09-26` incluyen julio y agosto de 2026, dentro del holdout 2026-07-01→2026-12-31. El sello en código evita el leak en el análisis, pero no satisface la ausencia física.
2. **Presupuesto de tamaño**: 17,97 GB contra el límite contractual de 10 GB para el input privado v1 → veredicto `ABSTAIN_CAPACITY` (el contrato prohíbe resolverlo partiendo la corrida hasta que entre).
3. **Presupuesto de archivos**: 57 archivos top-level contra el límite contractual de 20. Además, la documentación de Kaggle indica un máximo de 50 archivos de nivel superior; el upload existe con 57, así que se registra la **discrepancia observada** entre documentación y comportamiento, sin afirmar cuál es la regla vigente.
4. **Gate legal M0**: ticks crudos subidos sin `DATA_LICENSE_DECISION.md` (ver P-07).

**Pendiente de reconciliación con dato duro, no con inferencia**: el censo local declara 56 contratos / 16,74 GB / 1.078.414.656 ticks; Kaggle muestra 57 archivos / 17,97 GB. `728 = 56 × 13` sugiere 13 columnas contadas por archivo (contra las 8 del esquema canónico) más un archivo extra. `notebooks/kaggle/00_contract_and_environment.py` identifica el archivo 57 por censo de footer y hash, no por suposición.

**Remediación propuesta** (recomendada, a decidir):

- V1 pasa a **`raw_custody`**: privada, no analítica, en cuarentena documentada; no se adjunta a ningún notebook formal.
- Se construye **`edgelab-cme-research-v2`**: sólo tablas derivadas (`events_long`, `windows_ml`, `targets_long`, `folds_outer`/`folds_inner`, diccionarios), con el sello aplicado en la construcción, ≤ 10 GB, ≤ 20 entradas top-level, particiones Parquet de 128–512 MB.
- El holdout se materializa aparte y **no se sube** hasta M8.

**Mitigación en código (2026-08-14)**: `tools/build_kaggle_bundle.py` v2 ya no puede producir un upload con estos cuatro defectos. Todo archivo cuyo `ts_max` alcance la apertura de la sesión 2026-07-01 queda marcado `RECUT_REQUIRED`, sale del staging y fuerza `ABSTAIN_HOLDOUT` (punto 1); el presupuesto se evalúa con `inventory.budget_gates` y devuelve `ABSTAIN_CAPACITY` (puntos 2 y 3, verificado con una fixture de 12 GiB); y el gate M0 pasó a ser mecánico (punto 4, ver P-07). Lo que **no** resuelve: la V1 ya está subida y no la produjo este script, y falta la herramienta de **re-corte físico** de los parquets que contienen holdout. Ver P-23.

**Criterio de cierre**: existe un dataset de Kaggle cuyo `00_contract_and_environment` devuelve `PASS` en los gates G1 (reconciliación), G2 (presupuesto), G3 (pre-screen de holdout) y G4 (M0).

---

## P-19 · a · P-22 · Defectos medidos del barrido L3 PreRange

**Estado**: ABIERTAS (2026-08-14) — abiertas en el informe de auditoría del barrido L3 (commit `0cf68a0a`), con su evidencia y su aritmética completa ahí. Acá quedan **asentadas para que la numeración no se pise**; el detalle no se duplica.

Los cuatro defectos, medidos y no inferidos, sobre 72.962 sesiones sintéticas en cinco regímenes adversariales:

1. **Inanición de la familia de placebos (bloqueante)**: 14 de los 25 placebos arrancan entre 00:12 y 07:12. Con un M1 sólo-RTH quedan 11 usables contra el mínimo de 19 → `PRERANGE_EDGE` es **inemitible** y el runner reporta `WINDOW_UNSPECIFIC`, que se lee como resultado científico y es cobertura de archivo. Reemplazo propuesto: grilla de 15 min en RTH (23 miembros, piso 0,042).
2. **Regla de toque por contención en vez de cruce**: 0,78 % de misclasificación cuando el rango se comprime — justo el estrato que el análisis original celebraba, así que censura la muestra donde el efecto se buscaba.
3. **Redondeo bancario en `d`**: sesga el empate en la carrera simétrica.
4. **Agrupación por fecha calendario en vez de trade date CME**: vuelve el `p_perm` **anti-conservador** porque mezcla ventanas overnight no exchangeables con la primaria.

Además, discrepancia material de procedencia: el spec corre **08:12–09:12** y el resumen operativo dice **08:30–09:30**. No son la misma ventana (una tiene el dato macro adentro, la otra en el borde de arranque) y cambiarla "porque suena mejor" quema la procedencia — `apply_provenance_cap()` degrada a `WINDOW_UNSPECIFIC` toda ventana elegida mirando estos datos.

Lo que **resistió** la auditoría: el estimand de la carrera simétrica. |E[r]| ≤ 0,008, ningún z sobre 1,07, sesgo del nulo acotado a 0,023 = 15 % del MDE, incluso con saltos asimétricos de 8 vs 1 tick y con `d` menor al recorrido de una barra.

**Criterio de cierre**: los dos fixes de tres líneas aplicados, la familia de placebos reemplazada por la grilla RTH, una sola ventana fijada con su fuente escrita, y **nada corrido sobre datos reales antes de eso** (hoy no cuesta nada; en una semana ya sería p-hacking).

---

## P-23 · El builder del bundle de Kaggle declaraba CC0 y era fail-open

**Estado**: RESUELTA EN CÓDIGO (2026-08-14, commits `50a5881` + `fb3ab8f` + `b68a548`) — con residual explícito.

Artefacto auditado: `tools/build_kaggle_bundle.py` en `56184a3`, blob `df383c0685e5e46a806fb9b650a370bf529928c3`. Cinco defectos, cada uno verificable en ese blob:

1. **`licenses: [{"name": "CC0-1.0"}]`** — dedicación al dominio público declarada por código sobre datos de mercado de terceros, con P-07 abierta y el dataset ya subido.
2. **Identidad prometida y no calculada** — el encabezado anunciaba sha256 y rangos de fechas; el código escribía `num_rows` y bytes. Sin sha256 no se verifica lo subido; sin min/max de `ts_utc_ns` no se certifica ausencia de holdout.
3. **`id` y `OUT_DIR` desalineados del upload real** — `nicodelcampo/edgelab-cme-futures-ticks` vs el dataset existente `nicolasbuttaro/edgelab-cme-futures-universe`, y en `OUT_DIR` sólo se escribía el JSON: **ningún parquet se copiaba ahí**. Los 57 archivos de la v1 los subió otro procedimiento, no versionado (patrón D9, esta vez del lado de los datos).
4. **Fail-open** — `if not folder_path.exists(): continue` y `except Exception as e: print(...)`: un activo entero podía faltar sin cambiar el resultado. Más el filtro silencioso `"all" not in f.name and "prev" not in f.name`.
5. **Tabla de `tick_size`/`multiplier` duplicada a mano** frente a `edgelab/instruments.py`.

Y lo que faltaba por completo: el builder no sabía nada del sello del holdout (ver P-17).

**Reemplazo (v2, blob `33b39364afb31da576a26500ea90dde5a2a9954f`, 47.692 B)**: seis gates —`G-INSTRUMENT`, `G-LAYOUT`, `G-IDENTITY`, `G-HOLDOUT`, `G-BUDGET`, `G-LIC`— con veredictos `PASS` / `FAIL_INSTRUMENTS` / `FAIL_LAYOUT` / `FAIL_INTEGRITY` / `ABSTAIN_LICENSE` / `ABSTAIN_HOLDOUT` / `ABSTAIN_CAPACITY` y exit codes 0 / 1 / 2. Cuarentena con causa nombrada por archivo. `bundle_index.json` se escribe siempre (rastro de auditoría) y sella su propio contenido con `index_sha256`; el staging, `dataset-metadata.json` (`isPrivate: True`, `--dataset-id` obligatorio), el `README.md` con la restricción de uso y la hoja `files.sha256` sólo existen con `PASS`. Cantidades de una sola fuente: `edgelab/instruments.py::CME_UNIVERSE`.

**Evidencia**: self-test de 26 checks, 0 fallas (`python tools/build_kaggle_bundle.py --selftest`, cableado en `tests/test_kaggle_bundle_builder.py`). Los bytes commiteados son los mismos que pasaron el self-test: blob verificado contra el commit. Informe completo: `docs/research/KAGGLE_BUNDLE_BUILDER_AUDITORIA_2026-08-14.md`.

**Residual, que el código no cierra**:

- La **V1 ya está subida y no la produjo un script versionado**: su identidad sigue sin cerrar.
- Falta la herramienta de **re-corte físico** de los parquets con holdout (P-18); v2 los detecta y excluye, no los corta.
- **57 vs 56 archivos** sin reconciliar.
- Existe `--no-hash` para diagnóstico y está prohibido para publicar (sin sha256, `G-IDENTITY` falla).

**Criterio de cierre**: (a) una corrida del builder v2 desde la máquina local gobernada sobre `E:/EdgeLab/data/nt8`, con su `bundle_index.json` commiteado — cualquier veredicto, y si es `ABSTAIN_*` se registra tal cual; y (b) que lo que quede en Kaggle sea **exactamente** el staging que produjo el script, verificable con `sha256sum -c files.sha256`.

**Criterio (a): CERRADO (2026-08-15)**. `docs/research/bundle_index.json` está commiteado (`69eb269`, `index_sha256 6d46269c7e35a8a7…`) y su veredicto `ABSTAIN_LICENSE` es reproducible desde el repo. El criterio (b) sigue abierto. Ver `docs/research/PRECHECK_HOLDOUT_2026-08-15.md` §8.

---

## P-24 · `edgelab/kaggle/streaming.py` está sin revisar y sin sellar

**Estado**: ABIERTA (2026-08-15).

El módulo apareció en el repo pero **`load_repo_modules` no lo carga**, así que no entra en el bloque `code_identity` de los manifiestos. Es código que participa del pipeline de Kaggle sin quedar cubierto por la verificación de identidad que sí cubre a `identity.py`, `inventory.py`, `sessions_cme.py` e `instruments.py`.

Identidad al momento de abrir el punto: blob `08e3cee410f9d92b3a11df0405254b7956efbc18`, 11.100 B en LF (11.371 B en working tree con CRLF — ver P-26).

**Criterio de cierre**: auditoría línea por línea del módulo, y o bien se agrega a `load_repo_modules` para que quede sellado, o se documenta por escrito por qué queda deliberadamente fuera.

---

## P-25 · Decisión humana de presupuesto para `research-v2`

**Estado**: **CERRADA POR ALCANCE (2026-08-15, D-1/D-2)** como requisito de publicación: sin
publicación no hay compuertas de capacidad que satisfacer. La poda de columnas
queda como **higiene local** (D-2), no como gate.

**Medición que sobrevive**: 41,70 % de bytes duplicados exactos; RAM por contrato 9,67 →
**~5,64 GiB estimados** (`9,67 × (1 − 0,4170)`). El «~5,80» que circulaba **no
cierra aritmeticamente** — correccion del auditor aceptada; el propio auditor ya
lo habia marcado en su entrada 003 y la correccion no habia llegado al board. Eso sí importa: era el único cuello real del programa local.

Medido en `docs/research/PRECHECK_HOLDOUT_2026-08-15.md` §5: el árbol post-re-corte tendrá **60 archivos top-level y ≈15,7 GiB**, contra límites contractuales de 20 archivos / 10 GiB (y 50 archivos del lado de Kaggle). **El re-corte mejora la legalidad del holdout y empeora el cuadro de capacidad**: el gate `top_level_files_kaggle` pasa de `pass` (49 ≤ 50) a fallar (60 > 50).

Y un corolario que cambia el orden de prioridades: como `VERDICT_PRECEDENCE` es un `if/elif` con `ABSTAIN_LICENSE` antes que `ABSTAIN_HOLDOUT` y `ABSTAIN_CAPACITY`, **aprobar la licencia (P-07) no produce un `PASS`** — produce el siguiente veredicto de la cadena. Los tres gates fallan hoy; el veredicto sólo muestra el primero.

Cuatro opciones, ninguna gratis, y las cuatro cambian el objeto de estudio:

1. **Enmendar el presupuesto** del Contrato Kaggle v2 (subir los 10 GiB / 20 archivos), con justificación escrita y firmada.
2. **Publicar sólo el front month por activo** — menos archivos y menos GiB, a costa de cobertura. Ojo: recortar por contrato **no** equivale a recortar por solapamiento con el holdout (dos de los 11 en cuarentena son `GC_08-26` y `MBT_07-26`, no 09-26).
3. **Pre-registrar un subconjunto de activos** y publicar sólo esos.
4. **Podar columnas** del esquema para bajar bytes por tick.

**Criterio de cierre**: Nico elige una y queda escrita acá antes de cualquier publicación.

---

## P-26 · Normalización de fin de línea y aviso de pausa en los manifiestos

**Estado**: ABIERTA — mecánica, aditiva.

Dos campos que faltan, medidos en `docs/research/PRECHECK_HOLDOUT_2026-08-15.md` §2 y §4:

1. **`git_blob_sha1_lf` en `edgelab/kaggle/identity.py`**, de forma **aditiva** (sin mutar la clave existente). `identity.git_blob_sha1` hashea los bytes del working tree, así que en un checkout Windows con `core.autocrlf` **nunca** iguala el blob commiteado: el manifiesto acusaba deriva de código en cuatro módulos donde no la había. Se probó con hash, no con hipótesis (LF → CRLF sobre `sessions_cme.py` reproduce exactamente el blob declarado). `tools/verify_indices.py` ya tolera esto clasificando `LF_EXACTO` / `CRLF_NORMALIZADO` / `DERIVA`; falta que el manifiesto lo traiga de fábrica.
2. **`rows_in_maintenance_break` por archivo en `tools/recut_holdout.py`**. Dos de los 11 archivos conservan ticks dentro de la pausa diaria 16:00–17:00 CT (`NQ_09-26` y `MBT_07-26`). No es leak —por la regla congelada esos ticks son del trade date 20260630— pero son impresiones de pre-apertura, settlement o skew de reloj, y hoy ningún chequeo de integridad las cuenta.

---

## P-27 · `verify_indices.py` extrapola bytes en vez de leer los medidos

**Estado**: ABIERTA (2026-08-15) — defecto de herramienta, no de corrida.

Post-corrida, `verify_indices.py` sigue estimando el tamaño del árbol como
`source_bytes × keep/total` en lugar de leer `output_bytes`, que el manifiesto real
**ya trae medido**. Error sobre el total: 0,9 % (15,752 GiB estimados vs 15,895
medidos); sobre la porción re-cortada: **+18,8 %** (816.834.273 estimados vs
970.254.030 medidos). Ver `docs/research/RECUT_EXECUTION_2026-08-15.md` H-5.

**Criterio de cierre**: la herramienta usa `output_bytes` cuando existe, y reporta
estimación vs medición cuando las dos están disponibles.

---

## P-28 · Columnas redundantes y semántica de `sequence`

**Estado**: **MEDIDA Y PRE-REGISTRADA (2026-08-15, D-3)** — sube de indicio a hecho. Verificado
columna a columna en **56/56 archivos, 1.015.587.419 filas, 0 diferencias**
(`docs/research/verif_columnas_duplicadas_2026-08-15.json`).

**Queda como LIMITACIÓN PERMANENTE, no como tarea**: `sequence` **no es secuencia
del exchange** sino índice de fila del origen, y `ts_local_ns` duplica a
`ts_utc_ns`. Cualquier análisis de microestructura que asuma orden intra-timestamp
**no está soportado por estos datos**.

Los digestos por columna del manifiesto prueban, en **11/11 archivos** (22 igualdades
de sha256 independientes):

- `digest(ts_utc_ns) == digest(ts_local_ns)` — `ts_local_ns` es un duplicado; si fuera
  hora de Chicago diferiría en 5–6 h.
- `digest(sequence) == digest(source_row)` — **`sequence` no es un número de secuencia
  del exchange**, es casi con certeza el índice de fila del origen.

La consecuencia que importa para research, no para el presupuesto: **cualquier análisis
de microestructura que asuma secuenciación del mercado** (orden de eventos dentro del
mismo timestamp, detección de huecos) **no está soportado por estos datos** y debe
pre-registrarse como limitación. El esquema tiene 11 columnas informativas de 13
(`instrument` y `contract` son constantes por archivo, ya presentes en ruta y nombre).

**Criterio de cierre**: confirmar con `verify_tree.py --columns` (los digestos prueban
indistinguibilidad bajo la función de digesto, la comparación directa lo zanja),
documentar el esquema real y pre-registrar la limitación. Ver `RECUT_EXECUTION_2026-08-15.md` H-7.

---

## P-29 · Los 45 archivos limpios comparten inodo con el árbol de origen inmutable

**Estado**: ABIERTA (2026-08-15) — riesgo de integridad, no defecto actual.

`linked_clean[*].method = "hardlink"` en 45/45. El árbol `research-v2` no es una copia
física: ocupa ~0,97 GiB de datos nuevos, no 15,9 GiB. **Cualquier escritura in-place
sobre uno de esos 45 archivos mutaría el parquet inmutable de origen.** Hoy la
inmutabilidad depende de que nadie escriba in-place, no de una barrera.

**Criterio de cierre**: quitar el bit de escritura en los dos árboles y verificarlo
(`verify_tree.py` ya lo chequea y avisa). Ver `RECUT_EXECUTION_2026-08-15.md` H-8.

---

## P-30 · `nt8/BigTrap2OptimizerStrategy.cs` — optimizador de SL/TP sin decisión previa

**Estado**: RESUELTA (2026-08-15, commit `438ef1b`) — asentada para que quede el registro, no para reabrirla.

El 2026-08-14 entraron dos commits (`d1133c1` "add BigTrap2OptimizerStrategy for pure SL and TP optimization", `7a8a6c8` "fix GetAsk/GetBid syntax") con un archivo nuevo que **optimiza stop-loss y take-profit**. Eso es búsqueda sobre P&L, no sobre estructura, y choca con dos cosas del marco: la regla STOP (nada sobre retornos sin manifiesto de campaña y OK explícito) y el hecho de que una grilla de SL/TP sobre histórico es la máquina de sobreajuste más clásica que existe — sin corrección por multiplicidad ni placebos, cualquier máximo que encuentre es indistinguible de ruido.

El defecto de gobernanza no era la estrategia en sí (puede tener un propósito legítimo, p. ej. medir sensibilidad en vez de elegir parámetros): era que **entró por un commit de sintaxis, sin quedar nombrada ni decidida**.

**Resolución**: `438ef1b` ("chore(nt8): remove SchermanQuantReversion and BigTrap2OptimizerStrategy to keep repo strictly scoped to EdgeLab research") borró los dos archivos, −791 líneas. Si alguna vez se reintroduce, entra con su propósito declarado por escrito y su decisión previa, no en un commit de otra cosa.

---

## P-31 · La rama viva no está verde: 6 fallas + 1 error en la suite

**Estado**: **ABIERTA — parcialmente cerrada.** Ítem 6 (`BARRA_PROCESADA`) **cerrado por D-4**:
el evento nunca se quitó, cambió la emisora a `LogEventAt(s.Time, …)`; era el test
el que caducó, y se reescribió para verificar el invariante en vez del literal.

**Siguen abiertos** (2026-08-15, medido desde la máquina local con el `.venv` del
repo): 6 candidatos ULP de `Gaps2` sin medir; `verify_tree.py --selftest` con
`PermissionError` de Windows; `test_prerange_sweep_formal.py` con fixture `null_out`
inexistente y dos tests que hacen `return dict` en vez de `assert`.

**El conteo de la suite NO es transportable.** En el sandbox del auditor da 2
failed / 952 passed; en esta máquina, sobre `tests/ --ignore=tests/research`, da
**539 passed, 26 failed, 13 errors**. Las 39 rojas caen todas en `tests/bridge/` y
`verify_tree`, y **se atribuyen al store ausente segun diagnostico local** — el
desglose sale del cache de pytest, **no de un artefacto versionado**. Correccion
del auditor aceptada (`REVISION_ENTRADA_005` §5): sin JUnit commiteado esto es
evidencia de maquina resumida, no un hecho reproducible del repo. Lo que si se
sostiene sin artefacto: «la suite esta verde» es una afirmacion sobre una maquina.

Corrida completa sobre `research/bigtrap2-local-displacement-null@4b9611a`
(`pytest tests -m "not vectorbt" -q`, `.venv` del clon principal):
**6 failed, 940 passed, 33 skipped, 3 deselected, 2 xfailed, 1 error en 172 s.**

Ninguna la causó el commit de ordenamiento del board (ese diff es sólo `.md`).
Se listan con causa raíz porque la regla permanente es **causa raíz obligatoria para
todo WARN/FAIL**, y porque P-05 pide un verde con el lock exacto: hoy ese verde no
existe ni local ni remotamente.

| # | Test | Causa raíz |
| --- | --- | --- |
| 1 | `test_data_root_resuelve_data_gitignoreado_desde_una_worktree` | **Regresión real.** Ver abajo. |
| 2 | `test_selftest_verify_tree` | `PermissionError [WinError 5]` en `verify_tree.py::_fixture` (línea ~659): hace `os.remove()` sobre un archivo que el propio fixture dejó **read-only** para ejercitar la auditoría de protección de escritura (P-29). En Windows no se puede borrar un read-only; falta `os.chmod(p, stat.S_IWRITE)` antes del `remove`. Es incompatibilidad de plataforma del fixture, **no** de la lógica de verificación. |
| 3 | `test_cada_cs_declara_version_en_el_meta[ExportM1Bars.cs]` | El `.cs` no declara `version=`. Regla permanente («cada corrección de `.cs` viaja con su versión»). |
| 4 | `test_cada_cs_declara_version_en_el_meta[YMPreRangeSweep.cs]` | Idem. |
| 5 | `test_todo_candidato_actual_esta_triajeado` | `YMPreRangeSweep.cs` introduce comparaciones de precio (`High[0] >= rangeHigh`, `Low[0] <= rangeLow`) que son candidatos ULP sin medir ni sellar en `tools/ulp_sweep_baseline.json`. Un candidato no es un bug — los bordes a medio tick son inmunes por construcción — pero el que no se mide, no se sabe. |
| 6 | `test_H2_el_cs_emite_BARRA_PROCESADA_en_el_camino_de_tick` | `nt8/BigTrap2.cs` ya no contiene `LogEvent("BARRA_PROCESADA"`. El `.cs` cambió 83 líneas en el fix de frontera de sesión (`f77a3be`, P-13). **Hay que decidir cuál de las dos cosas es cierta**: el evento se quitó (y entonces el denominador de esa medición desapareció, que es lo que el test existe para impedir) o el test quedó viejo. No son intercambiables. |
| E | `test_placebos_and_gates` (ERROR) | `tests/research/test_prerange_sweep_formal.py` pide la fixture `null_out`, que no está definida en ninguna parte. El mismo archivo además tiene dos tests que hacen `return dict` en vez de `assert` (`PytestReturnNotNoneWarning`), así que **no evalúan nada**: pasan siempre. El módulo no es un test válido de pytest. |

### Detalle del ítem 1 — la regresión

`data_root()` devuelve el `data/` de la worktree en vez de resolver el del checkout
principal vía `git worktree list`, y el test lo caza exactamente como fue escrito para
hacerlo («si no, `data_root()` encontró un directorio `data` equivocado — falso
positivo silencioso»).

La causa es un cambio de invariante, no un cambio de código: `.gitignore` líneas 34–36
son `/data/*` + `!/data/nt8_oracles/`, y desde que se commitearon los 11 CSV de
`data/nt8_oracles/`, **toda worktree tiene un `data/`** — con los oráculos, sin
`data/nt8/`. `data_root()` lo encuentra, lo da por bueno y devuelve un árbol sin los
parquets. `CLAUDE.md` declara «`/data/` es dato local (gitignorado)»; esa premisa dejó
de ser cierta y el resolvedor la seguía asumiendo.

**Consecuencia que importa**: cualquier medición corrida desde una worktree puede
resolver a un `data/` sin parquets. Falla ruidosamente en este test, pero un script que
sólo pida `data_root()` y liste lo que encuentre puede quedarse en silencio.

**Criterio de cierre**: `data_root()` valida que el directorio elegido contenga de
verdad `nt8/` antes de devolverlo (falla cerrado si no), o los oráculos salen de
`data/`. Decidir cuál, no las dos a medias.

---

## P-32 · Nombrar el conjunto de indicadores del programa de análisis

**Estado**: **NOMBRADA (2026-08-15, D-6)** — Nico declaró el conjunto y aceptó **paridad
representativa** para el trío P-16. Acta: [`docs/DECISIONES_2026-08-15.md`](DECISIONES_2026-08-15.md) D-6.

`BigTrap2` y `aVolClusterPOI` v0.5 entran como **paridad exacta**; `Gaps2` v2.0,
`AACloseOpenDiffs` v1.2 y `VolTicksPOC2` v2.1 como **representativa**;
`HFTZones2` v2.3 y `aVolCellPOI2` v2.0 **pendientes de paridad NT8 formal**.
`YMPreRangeSweep` **no entra**.

**Marca vigente**: las configs `tick:N` de `VolTicksPOC2` y `aVolCellPOI2` entran
como features fijadas pero **no se promueve nada desde ellas** sin resolver el
secuenciador causal.

**Advertencia que P-37 agrega**: «representativa» **no es consumible en G2+**.
Hoy `parity_covered` es inalcanzable para 4 de 5 kernels, así que el trío
representativo queda fuera del consumo formal aunque esté nombrado.

Abierta en `docs/research/PROGRAMA_ANALISIS_FEATURES_2026-08-15.md`
(commit `32fcc271b3f494bcd7fc673ab3b4963604a22b75`, 137 líneas, estado
`PROGRAM_REGISTERED` — no ejecutado). Es el paso 2 de su orden de ejecución.

**No hay «6 indicadores con paridad comprobada» como bloque homogéneo.** Cada uno
entra con su estado, y mezclarlos junta tres cosas distintas: P2 formal, réplica
P-16 con residuos, y P1A/warmup.

| Indicador | Medido | Falta |
| --- | --- | --- |
| BigTrap2 | 3.628/3.638 EXACT junio; 171/171 abr+may. Imán cerrado. | `tick:5/10`. Cruce con aVol prohibido. |
| aVolClusterPOI v0.5 | 6E 72/72, Δscore=0. ES 100 % pre-11-jun. | Nulo propio. P-15. |
| Gaps2 v2.0 | P-16: 11.435/11.442. P2 histórico 1.316/1.316. | Esa ventana corta cae en el holdout. Gate estructural FAIL por bordes. |
| AACloseOpenDiffs v1.2 | P-16: 18.004/18.020, idéntico al local. | FAIL estructural. «Paridad representativa» es decisión de Nico. |
| VolTicksPOC2 v2.1 | P-16: 151 MATCHED + 1 FEATURE_DIFF. | Mismo FAIL. Secuenciador causal no portado en `tick:N`. |
| HFTZones2 v2.3 | P1A + PASS 1.599 con warmup. | No está en P-16. |
| aVolCellPOI2 v2.0 | P1A, 140 zonas con warmup. | Paridad NT8 formal. |
| YMPreRangeSweep | 72,5 % doble barrido; nulo 54–76 % → no es edge. | P-19…P-22 bloquean L3 real. |

**Criterio de cierre**: Nico nombra el conjunto y, si corresponde, declara por escrito
«paridad representativa» del trío P-16 (`Gaps2`, `AACloseOpenDiffs`, `VolTicksPOC2`),
cuyos residuos son de borde/warmup pero hacen fallar el gate estructural estricto.

---

## P-33 · `verify_tree.py` resuelve la fuente por nombre de archivo y da `FAIL_FUENTE` en 6E

**Estado**: **DECIDIDA POR (a) (2026-08-15, D-5), IMPLEMENTACIÓN PENDIENTE.** Se resuelve la
fuente por carpeta declarada o por `source_sha256`, **no** moviendo carpetas: (b)
dejaría el resolvedor buscando por nombre y volvería a fallar con el próximo par de
homónimos. (a) es además más estricto — sólo acepta el candidato que cierra por
hash contra el manifiesto.

**Falta aplicarlo a `tools/verify_tree.py`.** Requiere la máquina con el árbol
`research-v2`; no se puede hacer desde acá. Original medido — la herramienta se comportó
bien; lo que falta es decidir la resolución.

Corrida real del paso 1 del programa, desde la máquina gobernada:

```
python tools/verify_tree.py --recut E:/EdgeLab/data/nt8_research_v2/recut_index.json \
                            --maxts --columns --no-source-hash
```

`15 ok | 1 falla | 2 avisos | 1 omitido` · 17.067.000.969 B re-hasheados ·
**`VEREDICTO: FAIL_FUENTE`**, por un único chequeo:

```
[FALLA] fuente.intacta   6E_09-26_ticks.parquet: ambiguo en el origen
```

**Causa raíz**: hay dos archivos con ese nombre bajo `E:/EdgeLab/data/nt8/`.

| Ruta | sha256 | Bytes |
| --- | --- | --- |
| `6E/6E_09-26_ticks.parquet` | `6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4` | 45.439.347 |
| `6E_prev_20260803_captura_rala/6E_09-26_ticks.parquet` | `654e006e483f62727dd2d52680e41b0c4c03531a3763471a1ba3532497883a06` | 37.559.162 |

El primero es el canónico: coincide con `source_sha256` del manifiesto **y** con uno de
los cinco parquets canónicos declarados. El segundo es una captura rala previa, y su
hash **`654e006e…` es uno de los dos exports Z1 que
`docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md` §1 prohíbe explícitamente
usar** («No usar los exports Z1 (`fd2e358…` / `654e006…`)»).

Así que la procedencia está intacta — el archivo correcto es el correcto — pero el
resolvedor **busca por nombre de archivo en el árbol** y encuentra dos candidatos, uno
de ellos en la lista negra del proyecto. Falla cerrado, que es lo correcto; el problema
es que el árbol de origen tiene una carpeta `*_prev_*` con un artefacto prohibido y
mismo nombre.

Antecedente relevante: el builder v1 de Kaggle tenía el filtro silencioso
`"all" not in f.name and "prev" not in f.name` (defecto D-4). Filtrarlas en silencio era
peor; **flaggearlas es mejor**, pero deja el veredicto global en rojo por un tema de
layout, no de integridad.

**Criterio de cierre** — elegir una, no las dos a medias:
1. `verify_tree.py` resuelve la fuente por la **carpeta declarada en el manifiesto** (o
   por coincidencia de `source_sha256`) en vez de por búsqueda de nombre; la ambigüedad
   pasa a aviso sólo si ningún candidato cierra por hash.
2. Las carpetas `*_prev_*` salen de `data/nt8/` a un árbol de cuarentena, y el acta de
   exports prohibidos se hace cumplir por ubicación además de por hash.

---

## P-34 · Las etiquetas de versión no se derivan del contenido

**Estado**: ABIERTA (2026-08-15) — medido. La cuarentena que disparó **se levantó con prueba**.

Al hacer el intake de los oráculos de `HFTZones2` y `aVolCellPOI2` aparecieron tres
etiquetas distintas para el mismo indicador. Se investigó en vez de asumir, y **las
tres describen el mismo comportamiento**:

| Artefacto | Etiqueta declarada | Comportamiento real |
| --- | --- | --- |
| `edgelab/bridge/indicators/hftzones2.py` (blob `8886d51c…`) | docstring «v2.1» | **v2.3** |
| `nt8/HFTZones2.cs` del repo (blob `64f1db87…`) | `engine=…v23_lifecycle_all_integer` | **v2.3** |
| `HFTZones2.cs` instalado en NT8 (blob `700ecdb4…`) | `engine=…v22_zone_edges` | **v2.3** |

**Prueba de equivalencia** (por lectura de código, no por analogía). Quitando las 53
líneas de `#region NinjaScript generated code` que NT8 autogenera, el diff entre el
`.cs` del repo y el instalado es **un solo bloque**: el repo saca
`long priceTick = PriceToTick(price);` **fuera** del `for` sobre zonas; el de NT8 lo
calcula **dentro**. `price` es un parámetro que no cambia en el loop y `PriceToTick`
es pura (`Math.Round(price / TickSize, AwayFromZero)`, sin estado): es un **hoist de
invariante de loop**. Mismo valor, mismas comparaciones enteras
(`priceTick >= z.LowerTick && priceTick <= z.UpperTick`), mismo resultado.

El kernel Python hace lo mismo que el repo: `px_t = snap_to_tick(price, tick_size)`
fuera del loop y `z["lower_t"] <= px_t <= z["upper_t"]` adentro
(`hftzones2.py:365-369`). Su docstring «v2.1» es etiqueta vieja, no código viejo.

`aVolCellPOI2`: el `.cs` del repo (`d43c686f…`) y el instalado (`91d186a6…`) **no
tienen ninguna diferencia real** — sólo el boilerplate autogenerado.

### Por qué queda abierta si todo dio bien

Porque el resultado favorable es accidental. **Ninguna de las tres etiquetas se deriva
del contenido**: son strings escritos a mano que se actualizan por disciplina. Esta vez
tres etiquetas distintas cubrían un mismo comportamiento; la falla simétrica —dos
artefactos con la **misma** etiqueta y comportamiento distinto— es P-08 otra vez, y no
hay nada en el sistema que la impida.

Consecuencia que importa: **cualquier paridad previa validada mirando sólo el string de
versión hereda esta duda.** El blob sí se deriva del contenido; la etiqueta no.

**Criterio de cierre**: la verificación de identidad de un oráculo compara **blobs**
(`.cs` del repo vs el que produjo el CSV), no strings de versión — y si el `.cs` que
corrió no está en el repo, el oráculo entra en cuarentena hasta que se commitee. Como
mínimo: subir el `version` del meta cuando cambia el engine, y sincronizar el docstring
del kernel Python.

**Residual inmediato**: los tres artefactos siguen mal etiquetados. Corregir las
etiquetas es barato; hacerlo **antes** de la próxima corrida formal evita que alguien
repita esta investigación desde cero.

---

## P-35 · Una paridad con `WARN` se registra como `parity_exact`

**Estado**: **DECIDIDA (2026-08-15)** — `WARN` **NO** es `parity_exact`; necesita estado
propio. Delegada por Nico. Fundamento: [`docs/research/DECISIONES_P35_P37_P10_2026-08-15.md`](research/DECISIONES_P35_P37_P10_2026-08-15.md).
**Implementacion PENDIENTE**: no se hizo en la maquina local porque
`test_coverage_propagation.py` esta en 12 fallas por falta de store — no se cambia
semantica de gates sin poder correr su test.

**Verificado** en `edgelab/bridge/store.py:268-276`:

```python
if gate == "FAIL":
    return "parity_failed"
if gate in ("PASS", "WARN"):
    return "parity_exact"
```

`WARN` y `PASS` colapsan al mismo estado: una paridad con advertencias queda sellada como
`parity_exact` e **indistinguible de una limpia**.

**Caso concreto del mismo día**: la paridad de HFTZones2 dio `WARN` sin frontera de
madurez (31 `STATE_ORDER_DIFF` + 4 `FEATURE_DIFF`) y `PASS` con ella — las dos corridas
están publicadas en `docs/research/paridad_hftzones2_12d_2026-08-15.json`. **Si se
hubiera publicado la primera al store, habría quedado marcada `parity_exact`.**

Es la misma familia que P-34: **la etiqueta no se deriva del contenido**. Acá el
colapso es de dos veredictos distintos en una sola etiqueta.

**Criterio de cierre**: o `WARN` tiene su propio estado, o se documenta por escrito por
qué un WARN es equivalente a un PASS para el consumo formal en G2+.

---

## P-36 · Dos semánticas de «covered» conviven en `coverage.py`

**Estado**: ABIERTA — mecánica, sin decisión de semántica.

**Verificado** en `edgelab/bridge/coverage.py`: el docstring y las matrices dicen que
`parity_covered` exige que **todas las ramas** estén cubiertas, vía `branches_of` (l. 24),
`config_branches` (l. 35) e `is_covered` (l. 50). Pero `propagate_coverage` (l. 131+) **no
usa ninguna de las tres**: decide con `coverage_blockers()` (l. 176-180), que compara
identidad dura + igualdad de params salvo los coverage-neutral.

`is_covered` sólo aparece referenciada **dentro de su propia definición** (l. 53): la
contabilidad de ramas es **código muerto respecto de la propagación**.

Riesgo: alguien lee el docstring, cree que las ramas se verifican, y no.

**Criterio de cierre**: o `propagate_coverage` usa la contabilidad de ramas, o el
docstring y las matrices dejan de prometerla.

**Evidencia completa (2026-08-15, maquina local).** La orden de trabajo pedia el grep
de repo entero para probar A2. Corrido sobre todos los `*.py`:

```
edgelab/bridge/coverage.py        4 ocurrencias
tests/bridge/test_coverage.py    10 ocurrencias
                                 --
total                            14, en 2 archivos
```

`is_covered`, `branches_of` y `config_branches` **no aparecen en ningun otro modulo del
repo**. No es solo que `is_covered` se referencie a si misma: los tres simbolos estan
aislados en su archivo y su propio test. **A2 queda probado a nivel repo**, no solo por
lectura local de `coverage.py`.

Lo que falta para cerrar sigue siendo la **decision de semantica**, que es de Nico.

---

## P-37 · `parity_covered` es inalcanzable para 4 de los 5 kernels

**Estado**: **DECIDIDA (2026-08-15)** — **NO se amplia** `COVERAGE_NEUTRAL`. D-6 queda
declarada NO EJECUTABLE para 4 de 5; cada kernel se gana su `parity_exact` con
oraculo propio. El camino real ya se demostro: HFTZones2 PASS 4821/4821 (`7596a78`).
Fundamento: [`docs/research/DECISIONES_P35_P37_P10_2026-08-15.md`](research/DECISIONES_P35_P37_P10_2026-08-15.md).

**Verificado** en `edgelab/bridge/coverage.py:64-71`: `COVERAGE_NEUTRAL` tiene **una sola
entrada**, `Gaps2`. Para los otros cuatro kernels `_neutral()` devuelve conjuntos vacíos,
así que **cualquier** diferencia de params bloquea la cobertura.

**Consecuencia dura**: la decisión **D-6** («paridad representativa» para el trío P-16)
**no tiene camino ejecutable** para 4 de 5. No por falta de cableado —`store.publish_run()`
sí llama a `propagate_coverage` (`store.py:393-400`)— sino por falta de entradas
justificadas en la lista blanca. El consumo formal en G2+ exige `parity_exact` o
`parity_covered`; hoy los «representativos» quedan fuera.

**Criterio de cierre**: cada entrada nueva en `COVERAGE_NEUTRAL` viene con justificación
escrita **por parámetro**, al nivel de la de `Gaps2` (que cita §8.3.1 campo por campo).
O se declara por escrito que D-6 no es ejecutable y se elige otro camino.

---

## P-38 · La allowlist de G2 sigue vacia: implementacion canonica no adjudicada

**LA CADENA QUE DESBLOQUEA ESTO** (rescatada de la entrada 005, que vivía sólo en
Notion — cero menciones en el repo hasta el 2026-08-18):

```
P-31 item 1  ->  diferencial A vs B  ->  merge de B  ->  P-38 (hashear)  ->  G2 promueve
(data_root)      (la medicion)          (un contrato)    (allowlist)
```

El capítulo 6 no podía cerrar **ni pasando G2**, y su primer eslabón —`data_root()`
fail-closed— era **lo más barato del proyecto** y se trabajaba último.

Estado al 2026-08-18: el eslabón 1 **está cerrado** (`data_root()` valida por contenido
y falla cerrado, con test). El diferencial **se corrió** (entrada 008: los dos contratos
dan resultados estadísticamente idénticos, A trae 17 tests más, adjudicación **NO
cerrada**). **P-38 sigue bloqueada por lo que la 005 nombró**: el paso 9 pide el sha256
«del archivo aprobado», y **no se puede hashear un contrato mientras existan dos
versiones rivales de él**.

Rescate completo: `docs/audits/ESPEJO_ENTRADAS_001_005_NOTION_2026-08-18.md`.

**Estado**: ABIERTA — **hallazgo, con causa raiz identificada**. Abierta 2026-08-15
desde la maquina local (Claude), leyendo codigo y las dos fuentes que la gobiernan.

**Medido**: `edgelab/research/promotion.py:38` -> `APPROVED_G2_CONTRACT_SHA256S =
frozenset()`. Confirmado en ejecucion. (No se contradice con CLAUDE.md: la que "ya
no esta vacia" es `AUTHORIZED_DSR_METHOD_SHA256S`, en `g2_decision.py:18`, que tiene
1 entrada. Son constantes distintas y las dos afirmaciones son correctas.)

**Lo que cambia el cuadro.** El vacio no es una prohibicion permanente: es una
**contencion condicional cuya condicion ya se cumplio**.

`docs/promotion_registry.md:48-53`:
> `APPROVED_G2_CONTRACT_SHA256S` esta vacio a proposito. Mientras **no exista una
> enmienda G2 corregida y hasheada**, ningun candidato puede materializar
> `statistically_supported`. **Cuando se apruebe la enmienda, su SHA-256 se
> agregara explicitamente.**

`docs/amendments/G2-2026-08-03_estimando_y_autoridad.md:324-326`, pasos 8 y 9:
> Nico aprueba el cambio semantico antes de una campana real; se calcula el
> SHA-256 exacto del archivo aprobado y **recien entonces se agrega**.

**La enmienda existe y fue aprobada**: `G2-A1`, commit `62ac28c`, con OK explicito
de Nico en sus 3 preguntas abiertas (CLAUDE.md). El paso 9 nunca se ejecuto.

**Consecuencia dura**: hoy **ningun candidato puede materializar
`statistically_supported`**, y el motivo no es una decision que alguien tomo — es
un paso que nadie dio. El capitulo 6 de la investigacion pide *"registrar el hash
de G2-A1 en la allowlist **o** documentar por que sigue vacia"*; la respuesta correcta es
**«implementacion canonica no adjudicada»**, no «por olvido». (Correccion del
auditor, `REVISION_ENTRADA_005_2026-08-16.md` §3, aceptada: Nico aprobo la
SEMANTICA de la enmienda, pero hay dos implementaciones rivales sin adjudicacion
medida, y eso basta para mantener la lista vacia fail-closed.)

**Pero no se ejecuta el paso 9 todavia, y por una razon nueva.** El paso 9 dice
«el SHA-256 **del archivo aprobado**». Hay **dos contratos canonicos rivales sin
adjudicar** (`fix/g2-a1-*`, ver P-10): conflictuan en `edge_validation_contract.md`,
`g2.py`, `g2_decision.py` y `promotion.py`. **No se puede hashear el contrato
mientras existan dos versiones rivales de el.**

**Criterio de cierre**: adjudicar P-10.3 primero y recien entonces hashear el
archivo ganador. **El diferencial YA SE CORRIO (2026-08-16) y NO los distingue**:
7 escenarios identicos al digito, A con 17 tests mas. Ver
`docs/research/g2a1_diferencial/RESULTADO_2026-08-16.md`. Sigue faltando la lista
estadistica del addendum §4. Hasta eso, la allowlist queda vacia **por este motivo escrito**, no por
INC-007 ni por olvido.

**Nota de alcance**: esto no autoriza agregar ningun hash. Lo unico que hace es
reemplazar una omision por una razon.

---

## P-39 · La identidad de NOMBRE contra CONTENIDO no se verifica en ningun lado

**Estado**: ABIERTA — **clase de defecto, no caso suelto**. Abierta 2026-08-16 desde
la maquina local tras verificar `features.py` y `reconstruct_daily_gex.py` contra
fuente.

**El patron.** El proyecto verifica identidad de ARCHIVOS con sha256 por todos
lados —manifiestos, oraculos, blobs, `code_identity`, `DeterminismError`— y **no
verifica en ningun lado que el NOMBRE de una salida corresponda a su CONTENIDO**.

| modulo | la etiqueta dice | el contenido es |
|---|---|---|
| `edgelab/gex/reconstruct_daily_gex.py` | columna `gex_dollar` | `OI x gamma x 100`, **sin spot**; no son dolares |
| `edgelab/bridge/features.py` | `zone_age` | **milisegundos**, unidad no declarada |
| `edgelab/bridge/features.py` | `distance_to_nearest_zone` | **unidades de precio**; `tick_size` se acepta y se descarta |

Precedentes ya asentados de la misma familia: **P-34** (etiquetas de version que no
se derivan del contenido), **P-35** (`WARN` sellado como `parity_exact`), y el gate
`mcpt` de `fix/g2-a1-statistical-semantics`, cuyo propio comentario admite que el
nombre miente.

**Por que importa mas que cada caso.** Un `sha256` prueba que el archivo es el
mismo; **no prueba que la columna `gex_dollar` tenga dolares adentro**. Todo el
aparato de identidad del proyecto es ciego a esta clase de error, y ya aparecio
seis veces.

**Agravante medido**: `F0.3_FEATURES_ESTADO_RESULTADO_2026-08-10.md:39` reporta
`zone_age` **«(barras)»** cuando el modulo lo emite en milisegundos. La conversion
—si la hubo— no esta declarada en ninguno de los dos lados. Un consumidor nuevo se
lleva un factor 60.000 sin que nada falle.

**Criterio de cierre**: o existe un chequeo ejecutable que valide nombre/unidad
contra contenido para las salidas declaradas —el `validity.py` que H-Z2A v3 propone
es el lugar natural, extendido con la dimension UNIDAD—, o se documenta por escrito
por que se acepta que los nombres no sean verificables.

**No parcheo nada**: `features.py` es la API que H-Z2A v4 va a consumir, y cambiarla
mientras se redacta su manifiesto es cambiar el instrumento durante la medicion.
Detalle en `docs/audits/VERIFICACION_FEATURES_PY_2026-08-16.md`.

---

## P-40 · El portador cientifico de H-Z2A no esta cableado al store

**Estado**: ABIERTA — **defecto de coherencia, NO bloqueante** (degradado 2026-08-16,
ver `docs/audits/ENTRADA_013_CORRIJO_P40_EL_CENSO_NO_ESTA_BLOQUEADO_2026-08-16.md`).
Abierta 2026-08-16
desde la maquina local, verificando el portador contra el codigo.

**Medido** (`edgelab/bridge/indicators/__init__.py`, confirmado por import):

```
REGISTRY = [AACloseOpenDiffs, BigTrap2, Gaps2, HFTZones2, VolTicksPOC2, aVolCellPOI2]
aVolClusterPOI en REGISTRY : False
aVolClusterPOI tiene run() : False
```

`avolclusterpoi.py` **existe** con `VERSION = "0.5"` —v4 §7 tiene razon contra v2,
la falta de kernel era de v0.4— pero es un **kernel de research**, no un indicador
del bridge. Su API publica son primitivas (`SessionProfile`, `detect_block`,
`classify_kind`, `cluster_hot_ticks`) y sus unicos consumidores son scripts de
`diag/tasa_senales/` que las importan directo.

**La cadena que se rompe.** El store se alimenta solo por `publish_run()`, cuyos
dos invocadores resuelven el kernel por `REGISTRY[n]`
(`run_nt8_bridge.py:266`, `run_campaign.py`). Sin entrada en `REGISTRY` no hay
publicacion; sin publicacion no hay `zone_id`; y `zone_panel.py` —primer modulo de
la arquitectura v4 §10— se define como «distancia por `zone_id`».

**La asimetria**: el paso 5 pide «censo en aVol v0.5 fijo + Gaps2 control».
**`Gaps2` esta cableado (REGISTRY si, run() si) y el portador no.** El censo tal
como esta escrito no puede correr.

**Toca a D-6**: asigna a `aVolClusterPOI` v0.5 «paridad exacta» PARA EL STORE, o
sea un estado de store a un indicador sin camino al store. No discute la paridad
medida (72/72 en 6E, Δscore=0); discute que el estado presupone una via inexistente.

**Riesgo de nombre — P-39 otra vez**: `aVolClusterPOI` (portador, no cableado) y
`aVolCellPOI2` (cableado, bar-driven, con `run()`) difieren en una palabra y D-6
los lista a los dos con estados distintos en la misma tabla. Cablear el equivocado
no daria error: daria un censo del objeto que no es.

**Criterio de cierre**: o (a) se promueve `aVolClusterPOI` a indicador del bridge
—`run()`, `REGISTRY`, `kernel_id`, camino de paridad formal—, o (b) se declara por
escrito que `zone_panel.py` lee el portador fuera del store, aceptando que quede
fuera de `config_id`, `DeterminismError` y `parity_state` que el control si tiene.

**CORREGIDO (2026-08-16)**: dije que «el censo no puede correr». **Es falso.**
`diag/tasa_senales/avolcluster_tick_formal.py` ya produce zonas del portador
desde los parquets canonicos, sin store y sin REGISTRY, y fija los hashes de
sus insumos: los tres 6E COINCIDEN con los de esta maquina. El camino real del
portador esta operativo. Lo que sigue en pie es que D-6 le asigna un estado DE
STORE sin camino al store, y que la premisa «zone_id del store» de
`zone_panel.py` no aplica al portador. Eso es coherencia, no bloqueo.

~~**Recomendacion de secuencia**: resolver esto ANTES de redactar el manifiesto~~
(v4 §10 lo pone en el paso 2 y el censo en el 5). Si no, el manifiesto se escribe
alrededor de un portador que no puede producir la poblacion que especifica.

Detalle en `docs/audits/ENTRADA_012_EL_PORTADOR_NO_ESTA_CABLEADO_2026-08-16.md`.

---

## P-41 · El firewall del portador corta por calendario CT, no por trade date

**Estado**: ABIERTA — **bloquea el censo H-Z2A**. Fix de una línea con un módulo que
ya existe.

Abierta por el auditor en
`docs/audits/ENTRADA_014_AUDITOR_GRILLA_PREDICADO_Y_FIREWALL_2026-08-16.md` §3. El
commit `f247e797a28ee441ceb50e9efb447709b04d0f02` se llama «board + indice: P-41
asentada» pero **sólo tocó `docs/audits/CANAL_AUDITOR.md`**: el board nunca la
recibió. Se asienta acá el 2026-08-17, **con la medición hecha**.

### El defecto

`diag/tasa_senales/avolcluster_tick_formal.py`:

```python
FIREWALL_CUTOFF = "2026-06-30"                              # l. 42
fw_mask = (ts_chi_full <= f"{FIREWALL_CUTOFF} 23:59:59")    # l. 428, America/Chicago
mask_p2 = (ts_chi >= "2026-04-09 17:00:00") & (ts_chi <= "2026-06-30 23:59:59")  # l. 318
```

El corte es por **fecha calendario de Chicago**. La sesión CME del trade date
2026-07-01 **abre a las 17:00 CT del 06-30**, así que todo lo operado entre esa
apertura y las 23:59:59 CT es holdout y el filtro lo deja pasar.

### Medido (no estimado)

| | |
| --- | --- |
| Apertura de la sesión 20260701 | `1782856800000000000` ns = 2026-06-30 22:00 UTC |
| Corte del runner (23:59:59 CT) | `1782881999000000000` ns = 2026-07-01 04:59 UTC |
| **Ventana de fuga** | **7,0 horas** |
| **Ticks de holdout admitidos en `6E_09-26`** | **5.319** |

El auditor estimó «> 871» razonando que P-17 midió 871 sólo en la franja 17:00→19:00
CT. La medición directa sobre el parquet canónico da **5.319** — **6,1× la estimación**.

Y el payload declara `"holdout_included": False` (l. 636) **escrito a mano**: una
etiqueta que no se deriva del contenido. Es P-39 dentro del artefacto que está por
producir la población de la línea activa, y P-35 otra vez en otra forma — **la
etiqueta no se deriva del contenido**, que es ya el patrón más repetido del board.

`mask_p2` tiene el mismo defecto en su borde de cierre; curiosamente el de arranque
sí usa el estilo correcto (17:00 CT).

**Criterio de cierre**: el corte usa `sessions_cme.session_bounds_utc_ns(20260701)[0]`
en vez de una fecha calendario; test del tick de las 17:30 CT del 06-30 (debe quedar
**fuera**); y `holdout_included` **computado** a partir de los datos, no escrito.

### RESUELTA (2026-08-17) — los tres criterios, con medición

Reasignada a esta máquina por Nico (la entrada 014 la ponía en la otra, que no tiene
los parquets y por lo tanto no podía verificar el fix).

1. **Corte por trade date**: `FIREWALL_CUTOFF_NS = session_bounds_utc_ns(20260701)[0]`.
   Aplicado en el firewall global (l. 443) **y** en el borde de cierre de `mask_p2`
   (l. 332), que tenía el mismo defecto — su borde de arranque ya era correcto.
2. **Test**: `tests/research/test_p41_firewall_trade_date.py`, 5 casos. El central fija
   que el tick de las 17:30 CT del 06-30 queda **afuera** con el corte nuevo y **entraba**
   con el viejo. Otro fija que la brecha regalada era de **7,0 horas**, no un borde de un
   segundo. Otro fija que el cutoff coincide con el del re-corte físico: un solo origen
   de verdad, porque si divergen un artefacto puede declararse limpio contra una frontera
   y sucio contra la otra.
3. **`holdout_included` computado**: `bool(ticks_formal.ts_ns.max() >= FIREWALL_CUTOFF_NS)`.
   Si un solo tick alcanza la apertura de la sesión de holdout, el artefacto **se
   autodelata** en vez de mentir. Se agregó además un bloque `firewall` al payload con
   criterio, cutoff, ticks conservados, ticks excluidos y `ts_max` conservado.

**Confirmación independiente que no estaba pedida**: sobre `6E_09-26` sin re-cortar
(2.784.986 ticks), el corte viejo conservaba 1.089.664 y el nuevo conserva **1.084.345**
— exactamente las filas del `6E_09-26_ticks.parquet` de `research-v2`. Dos caminos de
código que nunca se hablaron (`tools/recut_holdout.py` y este runner) coinciden **al
tick**. Los 5.319 de diferencia son los que P-41 denunciaba.

---

## P-42 · `aVolCellPOI2` no tiene paridad: 16 divergencias reales sobre 678 zonas

**Estado**: ABIERTA — **bloquea que el conjunto de P-32 quede canonizado**. Medido, no
inferido.

Primera paridad formal de `aVolCellPOI2` contra su oráculo
(`avolcellpoi2_v23_6E_0626_time1_100d.csv`, sha256 `5683d2e3…`), 6E 06-26, `time:1`,
30 días. Informes versionados, **re-corridos con `medicion_comprometida: false`**:
`docs/research/paridad_avolcellpoi2_30d_w1_2026-08-18.json` (warmup=1) y
`docs/research/paridad_avolcellpoi2_30d_w12_2026-08-18.json` (warmup=12) — las dos,
para que la separación entre warmup y divergencia real sea verificable por terceros.
(La cita original apuntaba a `runs/…`, **gitignoreado**: un path que no resuelve
fuera de esta máquina. Corregido tras la entrada 016 del auditor.)

```
kernel 671   vs   oraculo 678          gate: FAIL

MISSING_IN_PYTHON  9    el oraculo tiene zonas que el kernel no produce
MISSING_IN_NT8     2    y al reves
GEOMETRY_DIFF      2
FEATURE_DIFF       2    touches py=2/nt8=4 · py=3/nt8=9
TIMESTAMP_DIFF     1    created_ms diff = 60.000 ms = exactamente 1 barra
```

### Warmup descontado, no confundido con el defecto

Con 1 sesión de warmup los `MISSING_IN_PYTHON` eran 14; con **12** (por
`MinSessions=10`) bajan a **9**. O sea **5 eran warmup y 9 son reales**. El resto de
los códigos no se mueve entre las dos corridas: no son artefacto de ventana.

### La pista más rica

La zona 118/113 difiere en **geometría, timestamp y touches a la vez**:

```
py  = (46663, 46661)   ->  alto 2 medio-ticks = 1 tick
nt8 = (46665, 46661)   ->  alto 4 medio-ticks = 2 ticks
```

Mismo borde inferior, distinto superior: **NT8 fusionó dos celdas donde Python fusionó
una**, y la creó una barra antes.

**Descartado**: la lógica de fusión es idéntica en los dos lados — misma condición de
corte (`tick[i] - tick[i-1] > merge_gap + 1`, `.cs` l. 568 vs `.py` l. 346) y mismo
`min_zone_cells`. Con `MergeGapTicks=0` y `MinZoneCells=1` no hay margen de
interpretación ahí.

**Por lo tanto la causa está aguas arriba**: en qué celdas se marcan como anómalas, es
decir en el umbral del perfil (`is_anomaly`, `.py` l. 412 — cuantil / robust-z sobre el
perfil por bucket). Si el umbral difiere aunque sea marginalmente, una celda de borde
entra de un lado y no del otro, y eso explica los tres síntomas juntos: menos celdas →
zona más baja, creada más tarde, con menos toques.

**Criterio de cierre**: comparar el umbral por bucket y sesión entre kernel y oráculo
—el oráculo exporta `threshold`, `empirical_pct`, `robust_z`, `sample_count` y
`session_count` por evento `OBS`, así que la comparación es directa y no requiere
instrumentar nada nuevo— y localizar en qué punto del perfil divergen.

**No transportar a otros activos hasta cerrarla**: correr un kernel que ya se sabe
divergente sobre otro instrumento sólo agrega ruido.

---

## P-43 · Residual de `HFTZones2` en GC: 4 zonas de 3.630, localizadas

**Estado**: ABIERTA — residual chico y **acotado**, no bloqueante.

Primera paridad de un kernel fuera de 6E. `HFTZones2`, GC 06-26, `time:1`, oráculo
`0034a61da8d8e41b44edef707169fdc8cdc101b96d4685b1eb01a07f6de9201a`.

| ventana | kernel | oráculo | MATCHED | MISSING_IN_NT8 | FEATURE_DIFF |
| --- | --- | --- | --- | --- | --- |
| 12 días | 1.520 | 1.518 | 1.518 | 2 | — |
| 30 días | 3.630 | 3.628 | 3.626 | 2 | 2 |

**Lo importante es que no escala.** Con 2,4× más zonas las huérfanas siguen siendo
**exactamente 2** — las mismas. Si fuera un defecto sistemático del porteo crecerían
proporcionalmente. **99,89 % exacto.**

### Lo que esto establece

El kernel **transporta entre instrumentos y entre exchanges**. GC es COMEX (no CME),
`tick_size = 0.1` (decimal no representable en binario, el caso duro), y el porteo
sobrevive. Ningún kernel del bridge ramifica por instrumento — verificado — así que
esto era lo esperado, y ahora está **medido**.

### El residual

`Z001500` y `Z001501`, ambas `bucket=ABSORB`, `dir=-1`, creadas el **2026-04-02 16:34
UTC** (11:34 CT), contiguas en id, geometrías `4686.90/4686.80` y `4686.60/4686.50`.
Sus vecinas inmediatas **sí** emparejaron (`Z001499` ABSORB 16:22, `Z001502` PREDATOR
16:41): no es «todo ABSORB» ni «todo ese minuto».

**Hipótesis del feriado, NO establecida.** El 2026-04-03 es Viernes Santo y GC tiene
**cero ticks** el 03 y el 04; `sessions.py` no modela feriados y cree que se abrió una
sesión el 02 a las 17:00 CT que nunca existió. Pero **las zonas nacen a las 11:34 CT,
en mitad de sesión, no en un borde** — así que el vínculo es circunstancial y queda
como hipótesis, no como causa. Podría ser igual de bien un caso de borde de la lógica
de absorción (`DetectAbsorb`, `MinAbsorbPasos=6`).

**Criterio de cierre**: reproducir esas dos zonas aisladas y comparar `pasos`,
`valid_steps` y la traza de absorción contra las filas del oráculo — que exporta
`pasos`, `valid_steps`, `avg_ms`, `total_ms` y `max_retro_ticks` por evento, así que
la comparación es directa. Y decidir si `sessions.py` necesita calendario de feriados
por exchange, que es una pregunta más grande que estas dos zonas.

---

## P-44 · Dos catálogos de instrumentos, y los parámetros no transportan

**Estado**: ABIERTA. Dos hallazgos de la misma corrida, uno mecánico y uno de diseño.
Evidencia: `runs/kernels_activos.json` (7 kernels × 11 activos, ventana de 5 días).

### (a) El bridge conoce 6 instrumentos; el proyecto declara 11

| Fuente | Instrumentos |
| --- | --- |
| `edgelab/instruments.py::CME_UNIVERSE` | **11** — 6B, 6E, 6J, ES, GC, MBT, MES, MNQ, NQ, YM, ZB |
| `edgelab/bridge/ticks.py::instrument_spec` | **6** — 6E, ES, GC, NQ, YM, ZB |

`load_canonical_parquet` levanta `KeyError` en los otros cinco, así que **6B, 6J, MBT,
MES y MNQ no pueden correr ningún kernel**. No es que fallen: no cargan.

Es otra vez **dos fuentes de verdad para el mismo hecho** — la familia de P-34, P-35,
P-39 y P-41. Acá el costo es directo: el re-corte, el sello del holdout y el censo
tratan a los 11 como el universo, y el bridge sólo puede tocar 6.

**Criterio de cierre**: `instrument_spec` deriva de `CME_UNIVERSE` en vez de mantener
su propia lista, o se declara por escrito por qué el bridge cubre un subconjunto y
cuál es.

### (b) El código transporta entre activos; los PARÁMETROS no

Con **los mismos params y la misma ventana de 5 días**, las poblaciones difieren en
órdenes de magnitud:

| kernel | 6E | ES | GC | NQ | YM | ZB |
| --- | --- | --- | --- | --- | --- | --- |
| `gaps2` | 6.687 | 21.202 | 31.538 | **113.298** | 20.956 | **10** |
| `hftzones2` | 1.023 | 3.963 | 609 | 205 | **14** | 676 |
| `bigtrap2` | 251 | 236 | 255 | 178 | **14** | 338 |
| `voltickspoc2` | 25 | 9 | 15 | 10 | 15 | 26 |

`gaps2` va de **10 zonas en ZB a 113.298 en NQ**: cuatro órdenes de magnitud. La causa
es que los umbrales son **absolutos en ticks** (`min_gap_ticks`, `MinSweepTicks=4`,
`RetroFloorTicks=2`, `min_trap_volume=30`, `MinAbsoluteVolume=10`) y un tick significa
cosas distintas según el instrumento — `tick_size` va de `5e-07` (6J) a `5.0` (MBT).

**Esto NO contradice P-43.** Son cosas distintas y conviene no confundirlas:

- **El porteo transporta**: mismo código, mismo oráculo, 99,89 % en GC. Medido.
- **La configuración no transporta**: los mismos números producen poblaciones
  incomparables entre activos.

**Consecuencia para la línea activa**: correr H-Z2A multiactivo con params fijos no
compara el mismo fenómeno en seis mercados — compara seis poblaciones de tamaños
incomparables, y el brazo con 113.298 eventos domina cualquier agregado. Antes de
cualquier corrida multiactivo hay que decidir si los umbrales se normalizan (por
volatilidad, por rango de sesión, por percentil propio) o si cada activo se
pre-registra por separado con su propio presupuesto.

**Nota de método**: `avolcellpoi2` da 0 zonas en los seis. **No es un defecto**: con
`LookbackSessions=20` y `MinSessions=10`, una ventana de 5 días no alcanza para que el
perfil se forme. Esa columna es no informativa, no alarmante.

**Nota de herramienta**: `avolclusterpoi` figura como FALLA en los seis porque no
expone `run()` — se consume vía `SessionProfile`/`detect_block`/`RESEARCH_DEFAULTS`.
Es el supuesto de `tools/kernels_todos_los_activos.py` el que está mal, no el kernel;
y es otra cara de **P-40** (el portador no está cableado como los demás).

---

## P-45 — la segmentación del corredor depende de δ, y nadie lo decidió por escrito

**Abierta 2026-08-18** (entrada 025 del canal). **Bloquea el censo v2.**

El auditor pidió «declarar que las celdas ya no anidan en δ». Al computarlo en vez
de declararlo aparecieron **dos causas distintas**, y sólo una era un defecto.

**Causa 1 — bug, ya corregido.** El escaneo por ciclos tenía un `break` cuando un
mínimo no lograba separarse `R` ticks: abandonaba **el corredor entero**. Pero un
mínimo posterior más profundo tiene un umbral más bajo (`d_min' + R`) y puede
alcanzarlo. Misma familia que el `argmin`: un fracaso local borrando eventos válidos
posteriores. Sobre 400 series sintéticas con semilla fija, las violaciones de
anidación bajan de **135 a 21**.

**Causa 2 — decisión de estimand, SIN TOMAR.** La segmentación es **golosa**: con δ
grande un mínimo poco profundo califica primero, consume el corredor hasta su punto
de rechazo y **saltea** mínimos más profundos que un δ chico sí habría contado por
separado. El conjunto de **eventos** anida (un near-miss de `d_min=2` califica para
todo δ≥2); el **conteo** no. Caso mínimo fijado en
`tests/research/test_censo_hz2a_ceguera.py`.

**Las dos opciones**, para que sea una elección y no una herencia:

- **(a) segmentación dependiente de δ** (lo que hay hoy): «episodios de aproximación
  a escala δ». Coherente, pero el anillo marginal de la entrada 014 no se puede leer
  como anidado y `n_near_miss_marginal` puede ser negativo.
- **(b) segmentación independiente de δ**: enumerar los ciclos **una vez** por
  mínimos locales y recién después filtrar cada ciclo por (δ, R). Restituye la
  anidación exacta en δ. Sigue dependiendo de `R` para el punto de rechazo.

**Quién decide:** Nico, con el auditor. Es el estimand, no una tolerancia.

## P-46 — 17 de las 60 celdas de la grilla congelada son degeneradas por aritmética

**Abierta 2026-08-18** (entrada 025). **No bloquea; obliga a releer «8 de 60».**

La separación exige llegar a `d >= d_min + R`, pero el corredor **termina** en
`d >= D_far`. Si `δ + R >= D_far` la separación es **inobservable por construcción**,
sin mirar un solo tick. δ efectivo = `min(δ, D_far − R − 1)`.

| condición | celdas | comportamiento |
|---|---|---|
| `D_far − R − 1 < 1` | **15** | no pueden dar más que 0, nunca |
| `δ + R >= D_far` pero `D_far − R − 1 >= 1` | **2** | δ efectivo recortado (D=10, R=5, δ∈{5,8} → δ_ef = 4) |

Verificado contra el artefacto del 18-ago: las 15 dan exactamente 0.

**ENMIENDA 2026-08-18 (entrada 027 del auditor, aceptada).** La primera redacción de
esta consecuencia estaba mal por citar la ventana equivocada.

- **El denominador es 45, no 43.** Las 2 celdas recortadas **sí producen**: son
  `D=10 R=5 δ∈{5,8}`, con **1.505 near-miss cada una** sobre 228 sesiones, y son **2
  de las 8 vivas** — las más ricas de v1. Sacarlas del presupuesto era sacar
  justamente las más pobladas. Muertas son 15. `60 − 15 = 45`.
- **15/60 = 25 %**, no 28 %.
- **El «8 de 60» es «8 de 45»**.
- **134 y 28 no son el censo.** Salen de la ventana de 45 días **con el `break`
  todavía puesto**. En las 228 sesiones, `D=10 R=5 trade` da **268 · 579 · 977 ·
  1.505 · 1.505 y ANIDA** — verificado contra
  `docs/research/censo_hz2a_superficie_2026-08-18.json`. El marginal en δ=8 es
  **exactamente 0**, que es el recorte de δ_efectivo a 4 visible en los datos.
- **v1 con `argmin` sí anidaba.** La no-anidación la introdujo el escaneo por ciclos,
  mezclada con el `break`. El instinto de la 025 era correcto; el número que citaba
  estaba contaminado.

**Consecuencia vigente**: el presupuesto de multiplicidad del manifiesto se calcula
sobre **45 celdas**. Las 2 recortadas se conservan, declarando su δ efectivo = 4: no
son celdas independientes de δ=5 y δ=8, son la misma celda repetida.

Ahora cada celda publica `delta_efectivo`, `celda_degenerada`,
`separacion_observable` y `anillo_anida` — **computados**, no declarados.


---

## P-45 — DECIDIDA: **(c) episodio**. Asiento de la decisión de Nico

**Decidida 2026-08-18.** Fuente textual:
`docs/research/INTAKE_NICO_HZ2A_EXPLORATORIO_2026-08-18.md`.

> «Una vez que se cumplió el near miss, el 2do, si cumple las condiciones de
> excursión, distancia, tiempo, volumen, (o lo que esté descrito como
> umbral/parámetro para el análisis) se consideraría simplemente parte del retorno a
> la zona, y si luego se dieran las condiciones para considerarlo como otro near
> miss, entonces ahí sí se lo consideraría.» — Nico

**No es (a) ni (b). Es (c).** Un near-miss cumplido **abre un episodio**. El
acercamiento siguiente, si es el retorno, es **A2** — no un segundo near-miss. Otro
near-miss sólo si, **después** de cerrado ese episodio, se cumplen otra vez las
condiciones. **δ sigue siendo un parámetro de la grilla** (explorar cuál funciona
mejor), no un tipo de evento distinto.

**Implementada** en `censar_zona`, con tres tests en
`tests/research/test_censo_hz2a_ceguera.py`. Detalle que ya falló una vez y quedó
fijado: **no alcanza con reanudar un índice después del retorno** — si el escaneo se
reanuda dentro de la banda δ, vuelve a descender por la misma aproximación de vuelta
y la cuenta igual. El episodio se cierra consumiendo el retorno **entero**, o sea
recién cuando el precio sale de la banda.

**Consecuencia que (c) NO resuelve, medida y declarada.** El auditor prefería (b)
porque comparar celdas entre δ sólo tiene sentido si miden la misma población
filtrada. **(c) no restituye la anidación** — la aumenta:

| estimand | pares no monótonos sobre 19.200 |
|---|---|
| (a) golosa | 21 |
| **(c) episodio** | **49** |

La segmentación en episodios sigue dependiendo de δ: con δ grande el retorno se
absorbe antes y el corredor se consume distinto. **El anillo marginal de la entrada
014 no se lee como anidado** y `n_near_miss_marginal` puede ser negativo. No reabre
la decisión — el estimand lo eligió Nico — pero se declara, no se descubre leyendo
una tabla. La advertencia del auditor sobre **A2** vale igual: aunque NM anidara, A2
puede no hacerlo.

**Fuera de v2, por decisión explícita:** MAE/MFE y todo lo que mire qué pasó después
de llegar (es resultado — espera manifiesto + STOP) · HFTZones2 (después de v2, no en
la misma corrida) · «tendencia saludable» (empieza el escrito; F9 sigue en pausa) ·
zona no virgen (se revisa; **la primera v2 sigue virgen** — cambiarlo cambia qué se
cuenta) · la «firma» conjunta (después de tener N: primero la población, después qué
coincidió).


---

## P-47 — `vive_por_N` cuenta eventos; la 014 congeló el criterio sobre sesiones

**Abierta 2026-08-18** (entrada 030). **Bloquea leer «celdas vivas» como resultado.**

La entrada 014 §3 dice, textual: «`n` de sesiones con ≥ 1 evento por celda, no sólo
`n` de eventos. Una celda con 500 eventos en 3 sesiones no es 500 observaciones.»
Pero `vive_por_N` se computa `nm >= 403`, o sea **sobre eventos**.

En v2 no es teórico: las celdas de conteo más alto son **las más concentradas**.
`D=80 δ=8 R=20` tiene 2.181 eventos en **27 sesiones** (80,8 por sesión), contra
`D=10 δ=1 R=5` con 438 en **111**. Un criterio por eventos premia exactamente la celda
con menos información real.

**Qué NO se hizo, a propósito:** no se agregó un boolean de sesiones. El 403 se derivó
a nivel variante sobre eventos; su equivalente en sesiones no existe, y escribirlo
después de ver la tabla es **elegir el umbral mirando el resultado**. El artefacto
publica `criterio_N="eventos"` y `eventos_por_sesion` por celda, y nada más.

**Qué hace falta:** pre-registrar el piso de sesiones **antes** de volver a mirar la
tabla, con su derivación, como se hizo con el 403. Decide Nico con el auditor.


---

## P-47 — DECISIÓN: **opción A, sin boolean de sesiones**

**Decidida 2026-08-19.** Nico delegó explícitamente esta elección en Opus 5
(«con respecto a las opciones, quiero que elijas vos»). Marco:
`docs/research/P47_MARCO_PISO_SESIONES_2026-08-19.md`.

**Elijo A.** No hay «celda viva» por sesiones. Cada celda publica `n_sesiones`, y el
MDE se deriva del contrato que ya existe: `Δ ≈ 0,10 × √(403 / n_sesiones)`. La
configuración central se elige por **cobertura** y por si el Δ detectable **paga los
costos** (~3,9 ticks RT en 6E), no por un corte.

**Las cuatro razones, en orden de peso:**

1. **B exige inventar un Δ, y eso no me lo delegó nadie.** Nico delegó elegir entre A
   y B, no fijar el objetivo científico del proyecto. Escribir un Δ ahora sería el
   mismo pecado que P-47 existe para impedir, un nivel más arriba.
2. **Un boolean no agrega información; la destruye.** Con `Δ ≈ 0,10·√(403/n)`, ni el
   universo entero (228 sesiones → **~13 pp**) llega a los 10 pp del contrato. Un
   corte trazado en cualquier lado entre 20 y 228 no dice nada que `n_sesiones` no
   diga ya, y colapsa un continuo en pasa/no-pasa.
3. **Un boolean nuevo duplicaría el defecto que estamos arreglando.** `vive_por_N` ya
   es una etiqueta derivada que se lee **en vez de** la cantidad, y viaja sola. Sumar
   una segunda multiplica el problema en vez de resolverlo.
4. **La pregunta económica no es «vive la celda»**, es si el Δ detectable paga la
   fricción. Eso es una comparación contra un costo —un número— no un umbral sobre N.

**Consecuencia operativa.** `vive_por_N` queda como está (`eventos >= 403`) con su
`criterio_N="eventos"` al lado, y **no se lee como veredicto**. El MDE por celda es
función determinística de `n_sesiones`, que el artefacto ya publica: se puede derivar
sin re-correr. Bakear `mde_80` en el runner queda para la próxima corrida, no
justifica una hoy.

**Lo que esto NO decide:** el Δ objetivo del proyecto, el presupuesto de multiplicidad
(`N_eff = 71`, ya escrito) y la configuración central del manifiesto v2. Siguen siendo
de Nico.

---

## P-48 — abrir `HFTZones2` como segundo portador

**Estado:** DECIDIDA la apertura; **secuenciada después** del censo v2 en aVol 6E.

v4 lo dejó fuera del portador inicial (paridad fuerte, canon formal pendiente).
Nico: «abramos hftzones2». El criterio de cómputo impide hacerlo en la misma corrida
que v2. P-43 (residual GC) y P-32 (canon formal) siguen abiertas.

---

## P-49 — «firma»: near-miss + el resto, en conjunto

**Estado:** ABIERTA. Campaña **posterior** a tener población.

Primero capa 1 (geometría). Después se pregunta en qué zonas coinciden imbalance,
saldado, tendencia, no-virgen. **No se busca la firma eligiendo gráficos.**

---

## P-50 — tendencia «saludable»: spec ahora, no corrida

**Estado:** ABIERTA. F9 sigue **pausada** para correr detectores nuevos.

Nico: «que empiece ahora». Empieza el **spec** — definición falsable de escalón /
liquidación / fakeout — no un barrido sobre datos. Correrlo ahora compite con v2 y
reabre F9.

---

## P-51 — la zona no tiene que ser virgen (umbrales de invalidación)

**Estado:** ABIERTA. **No entra en la primera corrida de v2.**

*(Era el «P-47» de `docs/research/BOARD_P45_P50_2026-08-18.md`. Renumerada acá porque
P-47 ya es el piso de sesiones — dos cosas distintas no comparten número.)*

Nico: un atravesamiento corto en tiempo, distancia o volumen podría no invalidar. Hoy
v4 cond. 2 y el censo exigen **cero trades** en `[L,U]` antes del giro.

**La primera corrida de v2 sigue virgen.** Relajar el predicado **cambia la
población**, así que se revisa después, con alternativas escritas (tiempo / ticks /
volumen) antes de tocar nada.


---

## P-52 — DECISIÓN DE ALCANCE: de un indicador de NT8 se importa la **geometría**, no el **algoritmo**

**Asentada 2026-08-19.** Origen: pregunta de Nico —*«¿la complicamos mucho intentando
replicar indicadores de NT8 en lugar de crearlos de una manera útil y provechosa pero
no necesariamente copiándole a la lógica de otra plataforma?»*—. La respuesta corta es
**sí, en parte**, y esta entrada fija dónde exactamente, para que no haya que
re-litigarlo.

### La regla

> **El indicador de NT8 es un generador de hipótesis, no un instrumento de medición.**
>
> De él se importa **dónde está la zona**. El resto —cómo la calculó— se define
> nativo, en el repo, con su propia definición falsable.

**La interfaz son tres números por zona**: `lower_tick`, `upper_tick`, `creado_ns`.
Todo lo demás del `.cs` (estimadores, acumuladores, dibujo, colores, expiración,
series MTF) es implementación de un graficador, no del mercado.

### El test, para aplicarla sin discutir caso por caso

Ante cualquier pieza de un `.cs`, preguntar: **¿existiría esto si el indicador no
tuviera que dibujarse en tiempo real sobre una plataforma?**

- **No existiría** → es un accidente de plataforma. **No se replica.**
- **Sí existiría** → es parte de la definición del objeto. **Se importa o se
  reescribe explícitamente.**

### Qué compra la paridad (una sola cosa) y qué cuesta

**Compra:** la garantía de que el objeto que Nico señala en el chart es el objeto que
la máquina mide. Sin eso, un resultado negativo es ambiguo — «capaz mediste otra
zona». Es **el puente entre una intuición visual y una afirmación testeable**, y es
un puente real: la paridad de BigTrap2 (3.628/3.638 EXACT, abril+mayo 171/171) no
encontró ningún edge, pero **hizo que su muerte sirviera**. Matar una hipótesis sólo
vale si mataste la correcta.

**Cuesta:** cada rareza de NT8 se vuelve requisito nuestro. Dos ejemplos medidos, no
hipotéticos:

- **`sesionNoConfiable` no reseteaba** porque el bloque de frontera quedó detrás de un
  `return` (fix `f77a3be`). Semanas de silencio de TRAPs por un orden de sentencias
  en otro programa.
- **El estimador P² de `VolTicksDef`** (Jain–Chlamtac) aproxima un percentil sin
  guardar la muestra. Existe **porque NT8 no puede re-ordenar 200.000 barras en cada
  tick**. Nosotros tenemos la serie entera en memoria y podríamos calcular el cuantil
  **exacto**. La disyuntiva es nítida: cuantil exacto = más correcto y **sin
  paridad**; replicar P² = paridad y **copiar un error de aproximación que existe sólo
  por una restricción que no tenemos**. Eso no es medir el mercado: es medir
  NinjaTrader.

Se suman a la lista: orden de acumulación de un `double` que nunca se resetea,
calendarios de sesión, interleaving de `BarsInProgress` en MTF, y efectos laterales
(el LuxAlgo escribe SQLite a `D:\AlgoProject\`).

### El patrón correcto ya está en producción

`diag/tasa_senales/censo_hz2a_superficie.py` **no llama al runner del portador**. Trae
su propia distancia, en **ticks enteros y por `zone_id`** (porque `features.py` usa
`argmin` sin `zone_id` — P-39). Define corredor, `d_min`, separación `R` y episodio
**nativamente**: nada de eso viene de NT8. Del indicador usa exactamente los tres
números de la interfaz.

Se llegó ahí medio sin querer, empujado por la orden 019 (si el runner toca outcomes,
el artefacto no entra). Esta entrada lo convierte en política.

### Consecuencias — qué cambia y qué no

**Paridad se paga sólo donde un indicador (a) carga una hipótesis viva **y** (b) la
evidencia que la originó es visual.** Hoy eso es **`aVolClusterPOI`**, y nada más.
`HFTZones2` entra cuando P-48 lo abra.

**Deuda de paridad que queda DECLARADA y APARCADA, no perseguida** — ninguna hipótesis
depende hoy de estos:

| ítem | estado |
|---|---|
| **P-42** `aVolCellPOI2` sin paridad (671 vs 678) | aparcada — no hay hipótesis detrás |
| **P-43** residual de `HFTZones2` en GC (3.626/3.630) | aparcada hasta P-48 |
| **P-44** dos catálogos (11 vs 6) y params que no transportan | aparcada; sigue bloqueando multiactivo |
| **P-32** conjunto de indicadores | se reabre sólo si una hipótesis lo pide |

> **Esto no las cierra.** Aparcar ≠ resolver: siguen en el board con su estado real.
> **Reactivar cualquiera exige una hipótesis que la necesite**, escrita antes.

**Lo que NO cambia:** el contrato de paridad (`docs/nt8_indicator_parity_contract.md`)
sigue vigente **para lo que sí se mide**; no se relaja ningún gate; `aVolClusterPOI`
mantiene su paridad medida; y nada de esto toca el firewall del holdout ni el STOP.

### Cómo se aplica a un indicador nuevo

1. **¿Qué hipótesis lo necesita?** Si no hay una escrita, no se porta. (F9 sigue
   pausada por decisión sellada.)
2. **¿La evidencia que la originó es visual?** Si Nico lo vio en el chart, hay que
   importar **esa** geometría. Si la idea es analítica, se define nativa y **no se
   busca un `.cs` que copiar**.
3. **Importar sólo `lower_tick` / `upper_tick` / `creado_ns`** (o el equivalente).
4. **Todo lo demás se reescribe nativo**, y cada decisión de reescritura se documenta
   con su alternativa —como hace `edgelab/research/lux_imb.py`, que declara su
   divergencia de OG (wick-a-wick contra el body-a-body del `.cs`) en vez de esconderla.
5. **P-50 («tendencia saludable») es el caso testigo**: no hay `.cs` que copiar, y eso
   es una **ventaja** — la definición se escribe falsable desde el principio, sin
   heredar accidentes de nadie.

### El límite honesto de esta decisión

Es fácil decirlo hoy. Hace dos meses, sin saber si la intuición sobre BigTrap2 se
sostenía, la paridad era **la única forma de descartar «mediste otra cosa»** como
explicación de un resultado negativo. El error no fue empezar por ahí: fue **no parar
cuando quedó claro que la hipótesis se define sobre geometría de precio y no sobre el
interior del indicador**.

Corolario para el futuro: **la paridad tiene fecha de vencimiento por hipótesis.**
Cumple su función el día que la hipótesis queda escrita como afirmación medible sobre
el precio. Desde ahí, seguir persiguiéndola es deuda técnica disfrazada de rigor.

**Qué falta decidir (de Nico):** confirmar el aparcamiento de P-42 / P-43 / P-44 /
P-32. La regla la puedo asentar; **sacar ítems de la cola de trabajo es decisión
suya**, y por eso quedan marcados «aparcada» y no «cerrada».


---

## P-53 — lo que **sí** movería la aguja: sesiones, no modelos

**Asentada 2026-08-19.** Origen: Nico preguntó si se puede entrenar un algoritmo que
aprenda qué características tiene un movimiento tras el cual el precio se mueve X
ticks, y que aprenda regímenes. **Se puede, y es la parte fácil.** Esta entrada fija
por qué eso no es la restricción, y cuál es.

### La restricción real es N, y es una sola

| cantidad | valor |
|---|---|
| ticks tras firewall (6E) | 16.215.330 |
| barras M1 | 281.703 |
| **sesiones** | **228** |

Con etiquetas de ventana futura, las filas contiguas comparten casi toda su etiqueta:
**el N efectivo se parece a las sesiones, no a las barras.** Un modelo va a ver
281.703 filas y a reportar intervalos angostísimos que son mentira — el mismo error
que P-47 cazó en el censo (2.484 eventos en 39 sesiones no son 2.484 observaciones).

Con `Δ ≈ 0,10 · √(403 / n_sesiones)`:

| sesiones | MDE |
|---|---|
| 228 (universo entero) | ~13 pp |
| 76 (un régimen de tres) | ~23 pp |

Un edge real en futuros vive en **2–5 pp**. **No se detecta con 228 sesiones**, y
partirlas en regímenes empeora el problema. **Ningún modelo afloja esto.**

### Orden de inversión, de mayor a menor retorno

1. **Ganar sesiones.** `research-v2` tiene 56 contratos y 1.015.587.419 ticks. El
   cuello es **P-44**: los parámetros no transportan entre instrumentos (`gaps2` da
   10 zonas en un activo y 113.298 en otro). Resolver P-44 —normalizar por volatilidad
   / rango / percentil propio, o pre-registrar cada activo por separado— es lo que
   convierte 228 sesiones en miles. **Es la inversión de mayor retorno del proyecto.**
2. **Costos primero, no último.** 6E round-trip ≈ **3,9 ticks**. Con etiqueta «+10
   ticks», el edge bruto debe superar el **39 %** del objetivo sólo para empatar.
   Cap. 3 (ledger de costos) ya está abierto y va antes que F4 en el addendum 007.
3. **Etiqueta de barrera, no de retorno.** «Sube 10 ticks después» lo cumple un camino
   que primero bajó 30: se predice bien y se pierde plata. La etiqueta operable es
   **primer pasaje con dos barreras** (`+X` / `−Y`, horizonte máximo).
4. **Regímenes DECLARADOS, no aprendidos.** Tipo de sesión, bucket de volatilidad por
   cuantil de ventana expansiva, hora del día: computables en `t` sin mirar adelante,
   con N interpretable por bucket. Un HMM ajustado sobre toda la muestra **mete el
   futuro en el pasado** (la etiqueta de régimen en `t` usa datos posteriores a `t`),
   y a 228 sesiones agrega parámetros y fuga a cambio de nada.
5. **ML como estimador condicional sobre población pre-registrada**, no como buscador
   sobre todas las barras. La pregunta bien puesta es: *dado un episodio near-miss,
   ¿qué features medibles ANTES de que el evento se complete predicen el resultado de
   barrera?* Eso es **F4** en el addendum 007, y es la **«firma»** que Nico ya
   registró como **P-49**.

### Por qué el orden importa

Con ML la multiplicidad **deja de ser contable**. Una grilla de 60 celdas tiene un
`N_eff` que se escribe (el nuestro es 71). Un modelo con búsqueda de hiperparámetros y
selección de features tiene un número efectivo de hipótesis difícil hasta de acotar —
por eso existen DSR y SPA, y por eso acá se pre-registra.

### La frase que resume la entrada

> **Un modelo mediocre con 2.000 sesiones vence a un modelo excelente con 228.**

### Compuerta

Cualquier búsqueda sobre retornos o P&L cruza el **STOP**: manifiesto de campaña +
número efectivo de hipótesis + riesgos + datos faltantes, y OK explícito de Nico. Y el
addendum 007 pone **F4 después** de ledgers, costos y población — que es exactamente
donde está parado el proyecto hoy.


---

## P-54 — familia nueva registrada: **H-ASIA-1**, costo de pasaje por `asia_close`

**Registrada 2026-08-19.** Protocolo:
`docs/research/H-ASIA-1_COSTO_DE_PASAJE_PROTOCOLO.md`. Estado
`PROTOCOL_WRITTEN_NOT_RUN`.

Observación de Nico: *«cuanto más rompió el precio —por tiempo, por volumen, por
ticks—, el camino a través del último precio comerciado en la sesión asiática ofrece
menos resistencia»*.

**Familia nueva**: no hereda población, costos, oráculos ni presupuesto de
multiplicidad de BigTrap2, H-Z2A, LUX-IMB ni YM-PRERANGE.

**El confundidor, escrito antes de medir.** Las tres magnitudes de ruptura están
correlacionadas con **volatilidad**, y la volatilidad **reduce mecánicamente el dwell en
cualquier nivel**. «Rompió fuerte → cruzó rápido» es la predicción de un modelo **sin
ninguna hipótesis**. Por eso el estimando es el **contraste contra controles**
(espejo + placebo emparejado), nunca el valor absoluto — la lección de F2.7–F2.9, donde
el control sin zona dio casi lo mismo y el contraste cruzó cero.

**Línea target-free / STOP**: se miden `dwell_minutos`, `dwell_volumen`,
`n_reentradas`, `llega`. **No** se mide si atraviesa o rebota (eso es dirección: es la
pregunta de reversión con otro nombre), ni MFE/MAE/retornos.

**Instrumento**: el censo de Asia (`CENSO_RANGO_ASIA_2026-08-19.md`) mostró que sobre
índices americanos la población arranca **degenerada** (YM rompe el 100 %). **6J es
donde el objeto existe** (94,9 %, mediana 85 min).

**Potencia**: MDE 13,1–13,9 pp sin estratificar; con terciles de magnitud, ~23 pp. Es
P-53.

### RESULTADO (2026-08-19) — `HYPOTHESIS_NOT_SUPPORTED`

Acta: `docs/research/H-ASIA-1_RESULTADO_6J_2026-08-19.md`. 6J, **222 sesiones**.

- **La tendencia no existe.** Doce lecturas (3 magnitudes × 4 bandas), **ninguna
  monótona decreciente**; planas o en «V». Diferencias máximas ~9 pp contra un **MDE de
  23,3 pp** por tercil.
- **El confundidor de volatilidad quedó resuelto** por el control dentro de la sesión, y
  el chequeo construido para la posición **pasó** (corr magnitud↔posición = −0,01).
- **Hubo un efecto aparente fuerte y era geometría.** `asia_close` con percentil de
  dwell 0,667 y **z = 5,2** contra el nulo. Pero el espejo estaba **anti-emparejado**
  por distancia al extremo roto (reflejar invierte el lado): `asia_close` está más cerca
  del extremo roto en el **76,6 %** de las sesiones. Condicionando, el subconjunto donde
  está **lejos** (n = 52) da percentil **0,472** y contraste **−0,059** — cruza cero.
- **Control correcto para una v2**: condicionar por distancia al extremo roto, no
  reflejar sobre el punto medio.

**Nota de integridad**: la primera corrida midió la ventana posterior del **día
equivocado** (cinco horas *antes* de que Asia empezara). Ningún número de esa corrida se
publicó. Síntoma visible que no se leyó como alarma: 52 descartes `sin_post` de 243.


---

## P-55 — el contexto no es un control: es el objeto. Un nulo puede ser dos efectos opuestos cancelándose

**Asentada 2026-08-19.** Observación de Nico:

> «una zona funciona de maneras distintas según el contexto. EdgeLab tiene que aprender
> a reconocer distintos contextos, donde un mismo tipo de zona puede significar cosas
> distintas u opuestas. Quizás un objeto de un indicador arroja ruido porque funciona
> bien en dos contextos y justo por no medirlos, estos dos contextos se suprimen entre
> ellos y el resultado es ruido.»

### Por qué importa

Un resultado nulo tiene **dos lecturas incompatibles** que la media no distingue:

1. **No hay efecto.** El objeto no informa nada.
2. **Hay dos efectos de signo opuesto** en subpoblaciones que no se separaron, y la
   media los cancela **exactamente**.

Tratar (2) como (1) mata hipótesis buenas. Es la falla que este proyecto ya nombró en
sus reglas —«un efecto real bidireccional puede promediar exactamente cero si sólo se
mira el canal direccional»— pero estaba escrita como **control estadístico**, no como
**dirección de investigación**.

### La firma es medible, y NO exige adivinar el contexto

Si dos contextos opuestos se cancelan, la media da cero **pero la dispersión no**:

- distribución **bimodal**, o
- varianza / colas **por encima del nulo** con media en cero.

Eso se detecta **sin haber mirado** qué separa los grupos. Por eso todo resultado nulo
de este proyecto publica **los dos canales y la distribución completa**, no la media.

**Un nulo cuya dispersión también cae dentro del nulo es un nulo fuerte. Un nulo con
dispersión excedente es una señal de heterogeneidad no modelada, y se persigue.**

### La disciplina que lo separa del data snooping

**Los contextos candidatos se escriben ANTES de medir**, con su justificación, y pagan
su multiplicidad.

Si aparecen **después** de ver el ruido, cualquier partición encuentra algo: con
suficientes cortes siempre hay uno que separa. Es exactamente P-47 —elegir el umbral
mirando el resultado— aplicado a subpoblaciones en vez de a un número.

**El orden correcto:**

1. medir sin condicionar, publicando los dos canales y la distribución;
2. si la media es cero **y la dispersión también es normal** → nulo, se cierra;
3. si la media es cero **pero la dispersión excede** → hay heterogeneidad, y se abre
   una campaña **nueva** con contextos pre-registrados y su propio presupuesto;
4. nunca partir la población que ya se midió para rescatar un nulo.

### Consecuencia de diseño

«Reconocer contextos» pasa a ser un **objetivo de EdgeLab**, no un control de una
campaña. Implica que los objetos que se miden deben venir con **features de contexto
computadas y guardadas desde el principio** —régimen de volatilidad, hora, posición en
el rango de sesión, qué había antes— aunque no se usen en la primera medición. Sin eso,
volver a preguntar por contexto exige re-correr todo.

**Alcance:** aplica a H-Z2A, H-ASIA-1, HFTZonesESPureV2 y a lo que siga.

---

## P-56 — fuente L2 (ES 09-26, NRD→CSV) dentro del período de holdout — cuarentena estricta target-free

**Asentada 2026-08-21.** Intake: `docs/research/INTAKE_L2_ES_NRD_2026-08-21.md`. Manifiesto: `runs/intake_l2/manifest_es_sep26_l2.json` (`5a43f3a5c79f767e1bc08cf7a240ab50ad12de08f44de59fba5122e3414bcc63`).

**Origen y contexto:**
Once pares de archivos (.nrd de NinjaTrader Market Replay y .csv exportados) cubren del 2026-08-10 al 2026-08-21 (106.182.208 eventos, 5,13 GB CSV / 591 MB NRD). Todos caen íntegramente dentro de la ventana protegida de holdout (2026-07-01 → 2026-12-31).

**Regla de uso (Gobernanza):**
- **Permitido:** Auditoría forense de esquema, integridad de archivos, paridad de indicadores, verificación de relojes/timezone y cobertura macroscópica (actividad target-free).
- **Prohibido:** Cualquier cálculo de señales, outcomes, retornos hacia adelante, P&L, correlaciones o backtests sobre estos datos sin autorización explícita y escrita de Nico.
- **Estado de sesión 20260821:** Captura parcial de la sesión en curso (hasta 11:57:28 ART), contiene exclusivamente filas L1 (sin L2). Queda sellada tal como se encontró, sin reescribir ni completar.

---

## P-57 — conversor NRD→CSV (`NRDToCSV.cs`, NT8 AddOn v1.2.0) — código de procesamiento no versionado

**Asentada 2026-08-21.** Intake: `docs/research/INTAKE_L2_ES_NRD_2026-08-21.md`.

**Identidad del artefacto:**
- AddOn `NRDToCSV` v1.2.0 (`NRDToCSV.cs`, sha256 `d409e751c6b6ae104a36d28d62f588301e745131b56f807b7ebf4f1842c903e5`, 18.682 bytes).
- Paquete zip de instalación: `D:\Descargas\NRDToCSV-1.2.0.zip` (sha256 `f915fb379203e833a4d676f3b2a4b02275405167802284365003b8852afd7ae9`).
- Mecanismo interno: invoca `NinjaTrader.Data.MarketReplay.DumpMarketDepth(instrument, fromDate, toDate, csvPath)`.

**Riesgo de procedencia y deuda técnica:**
1. **Código no versionado en repo:** El AddOn reside en `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\AddOns\NRDToCSV.cs` fuera del control de versiones de git. Se prohíbe re-ejecutarlo arbitrariamente o alterar los archivos CSV existentes.
2. **Acoplamiento al reloj del sistema (ART = UTC-3):** Los timestamps generados por `DumpMarketDepth` adoptan la hora local de la máquina (ART = UTC-3), evidenciado por la coincidencia exacta de la pausa diaria de mantenimiento de CME (16:00–17:00 CDT = 18:00–19:00 ART). Cualquier conversor posterior a Parquet debe normalizar explícitamente el timezone a UTC teniendo en cuenta este offset.
3. **Ausencia de orden intra-microsegundo:** El CSV carece de columna de secuencia del exchange CME (`seq_num`), y entre el 77 % y el 94 % de las filas comparten microsegundos idénticos.

---

## P-58 — paridad `aVolClusterPOI` en 60 ticks (GC 04-26): 68,3%, causa del faltante sin identificar

**Asentada 2026-08-26.** Registro completo: `docs/research/AVOLCLUSTERPOI_60T_PARIDAD_INVESTIGACION_2026-08-26.md`.
Commits: `919ff35`, `bfddd16`.

**Estado:** `PARITY_PARTIAL_UNEXPLAINED`. NO es un PASS — no se declara paridad firmada
sobre `aVolClusterPOI` en 60 ticks estilo `HFTZones2`/`VolTicksPOC2`.

**Medido:** 123/180 zonas del oráculo NT8 coinciden exacto (precio, volumen, timestamp
al milisegundo) contra el kernel Python — las que coinciden, coinciden perfecto. El
30% restante no tiene causa identificada.

**Dos hipótesis plausibles, verificadas contra código, refutadas con evidencia empírica:**
1. Warmup insuficiente del `SessionProfile` — probado con 114 sesiones reales de
   calentamiento (cinta completa desde 2025-10-10): match rate **igual o peor** que sin
   warmup (68,3% vs 70,0% del intento original).
2. Ancla del bucket horario (`sessionBegin` = primer trade real vs
   `sessionIterator.ActualSessionBegin` de NT8) — corregido con
   `edgelab.bridge.sessions.session_begin_ns()` (ya validada 7/7): resultado **idéntico
   byte a byte** al anterior, ni un solo match cambió.

**Decisión de Nico (2026-08-26):** no seguir cavando por ahora — la meseta + placebo
target-free ya dan evidencia independiente de estructura real (55× sobre el placebo,
`AVOLCLUSTERPOI_RESOLUCION_RESULTADO_2026-08-26.md`), así que el 68% no bloquea seguir
explorando target-free. Sí bloquea declarar paridad firmada.

**Pendiente si se retoma:** diagnóstico quirúrgico de un bloque específico (valores
intermedios lado a lado NT8↔Python) — candidatos de causa listados en el documento:
interpolación de cuantil, desempate de mediana en punto flotante, diferencia real en
los datos de origen (feed NT8 vs `.Last.txt`), o criterio de "sesión completa" para el
FIFO de `lookback_sessions`.

---

## P-59 · Lotes de L1/L2 real de GC subidos a Notion — mismo riesgo que P-18, otra plataforma

**Asentada 2026-08-26. Confirmada por Nico: ya se subieron.** Decisión de Nico: seguir,
sin remediación por ahora ("no pasó nada").

Encontrados en `E:\DatosNT8\subir_a_notion_menor_200mb\`: múltiples zips (`gc_canonical_l2_lote*`,
`gc_jun26_l2_lote*`, `gc_aug26_l2_loteD*`) con parquets reales de `l1_quotes`/`l2_depth`
de GC (may-jun 2026), fraccionados a <200MB para el límite de adjuntos de Notion.
Verificado abriendo el contenido: son parquets reales, no sintéticos ni derivados.

Misma familia de riesgo que P-18 (ver `docs/research/CME_Market_Data_Policy_Cloud_Kaggle.html`):
la prohibición de subir ticks/L1/L2 reales a una nube de terceros no es específica de
Kaggle — depende de que la plataforma no sea "Service Facilitator" homologado por CME
y de la cláusula de licencia sobre contenido de usuario, algo estándar en casi cualquier
SaaS, Notion incluido. No verificado si la carpeta `Notion/` en disco refleja subida
completa o parcial.

**No se toma acción de remediación** por decisión explícita de Nico. Se registra para
trazabilidad, no como bloqueante activo.

## P-60 · Override explícito: corrida SL/TP/BE experimental GC+NQ (2026-09-01)

**Asentada 2026-09-01.** Nico pidió correr el análisis de TP/SL/BE sobre 1 contrato de
GC y 1 de NQ pese a dos gates que seguían cerrados: GC en
`DRAFT_DESIGN_ONLY_PREAUTHORIZATION` (`specs/bt2a_gc_exitlogic_sltp_breakeven_campaign_v1.draft.json`,
falta suite RW/MCS de validación) y NQ con Gate 1 en `NO_DIRECTIONAL_MECHANISM` (no
`SUPPORTED`, commit `755dc3c`). Confirmación explícita en chat: "Sí, dale, confirmado".

Alcance acotado, no confirmatorio: **1 contrato por activo, 5 celdas** (subconjunto de
las 372+24+16 de la campaña real), `status=EXPERIMENTAL_NON_CONFIRMATORY`,
`edge_declared=False`, `promotion_eligible=False`. No abre holdout. GC usa la economía
ya congelada en P2B (3.5t/5.5t); NQ se reporta solo en ticks brutos porque no existe
todavía un modelo de fricción validado para ese instrumento (prohibido transportarlo
desde GC).

Corrida localmente primero (`diag/tasa_senales/sltp_be_experimental_gc_nq.py`): falló
por `ModuleNotFoundError` (worktree sin el módulo), luego colgó 100+ minutos en el
cuello de botella ya diagnosticado de `BigTrap2Absorption.update_active_zones()`
(O(n_blocks × n_active_zones)) y se mató el proceso sin resultado. Ver P-61 para la
decisión de mover esta corrida a Kaggle.

## P-61 · Contradicción de gobierno: prohibición CME/Kaggle vs. política V1 de scatter-gather ya en uso

**Asentada 2026-09-01.** `docs/research/CME_Market_Data_Policy_Cloud_Kaggle.html`
(2026-08-14) prohíbe explícitamente subir ticks/L1/L2 reales de CME a cualquier nube de
terceros, nombrando Kaggle. Pero `docs/research/KAGGLE_SCATTER_GATHER_MULTI_KERNEL_POLICY_V1_2026-08-31.md`
(commit `981eb3c`, V1.1 `1b0ba85`, "adoptada por Nico") autoriza y de hecho ya viene
usándose desde 2026-08-28 para compute real sobre ticks de NQ (paridad, N_RAND,
TICKBAR-001, exports de coordenadas) — **sin ninguna referencia cruzada al memo de
2026-08-14** en ningún punto de la política V1 (verificado por grep). Son dos
documentos de gobierno del mismo repo que se contradicen y ninguno cita al otro.

Nico, al ver esto planteado explícitamente, aceptó el riesgo de nuevo para la corrida de
P-60: "Si lo acepto, segui en kaggle". Datasets ya existentes en Kaggle con ticks reales
de GC/NQ (`nicolasbuttaro/edgelab-ticks-gc-preholdout`, `-nq-preholdout`, entre otros)
confirman que la práctica real del proyecto ya asumía este riesgo desde antes de esta
sesión. **No se toma acción de remediación** — se registra para que quien lea
`CME_Market_Data_Policy_Cloud_Kaggle.html` no asuma que la prohibición sigue vigente sin
excepción; la excepción (V1) está aprobada y en uso activo.

## P-62 · Los scripts SL/TP/BE del 2026-09-01 no usaron la cadena de front-month real

**Asentada 2026-09-01.** Los dos scripts de Kaggle de P-60
(`sltp_be_experimental_gc_nq_runner.py` y `be_trigger_sweep_gc_nq_runner.py`) cargan UN
solo contrato (`GC_08-26_ticks.parquet`, `NQ_09-26_ticks.parquet`) directo del dataset
preholdout, sin pasar por `tools/bt2_absorption_frontmonth_chain.py` /
`docs/research/CADENA_FRONTMONTH_GC.json` — la construcción que el proyecto ya tiene para
identificar qué sesiones de qué contrato tienen volumen real (regla: mínimo 5.000 de
volumen/sesión, roll confirmado por 2 sesiones donde el sucesor supera al vigente).

Se detectó al correr el barrido de G (break-even) recortado a "las primeras 2 sesiones":
`GC_08-26` en sus dos primeras sesiones (2026-02-06/09, muy lejos de su vencimiento
ago-2026) tiene apenas 227 ticks totales — 0 señales. El fix inmediato fue tomar las
**últimas** 2 sesiones del archivo en vez de las primeras (más cerca del corte
pre-holdout, con más probabilidad de volumen real), pero eso es un parche puntual, no
lo mismo que filtrar por la cadena de front-month real.

Para la corrida de cinta completa (P-60, `sltp_be_experimental_gc_nq_2026-09-01_KAGGLE.json`,
1.422 señales GC / 3.485 NQ) el efecto es menor pero no nulo: `BigTrap2Absorption`
necesita `min_history_buckets=200` de historial de volumen para generar señales, así que
los tramos sin liquidez casi no aportan señales — pero igual se computó absorción/warmup
sobre ticks pre-front-month sin filtrar, mezclando algo de ruido en el historial usado por
el indicador.

Ambos scripts están rotulados `EXPERIMENTAL_NON_CONFIRMATORY` — no contaminan ningún
resultado confirmatorio del proyecto (esos ya usan la cadena de front-month, ej. la
población de 152 sesiones de aVolClusterPOI). **No se toma acción de remediación sobre
los resultados ya obtenidos** — se registra como limitación conocida de esta mirada
rápida. Si se quisiera repetir con la población correcta, el paso sería filtrar los
ticks de cada contrato por las sesiones que `CADENA_FRONTMONTH_GC.json` le asigna, en
vez de usar el archivo de un solo contrato completo.

**Adenda 2026-09-01, tarde**: el intento de barrer G (break-even trigger) sobre las
**últimas** 2 sesiones (para tener volumen real, ver arriba) se abandonó — quedó
trabado largo rato en Kaggle en v2 (`max_age_bars=50`) y v3 (`max_age_bars=200`) sin
completar, misma familia del cuello de botella O(n_blocks x n_active_zones) de
`update_active_zones`, ahora agravado porque una ventana de 2 sesiones de verdadera
liquidez concentra mucho más volumen/zonas activas que el promedio de la cinta completa
(que sí terminó, P-60). Decisión de Nico: cortar y quedarse con el único punto ya
medido (G=9, TP=18/SL=18, sobre la cinta completa: net USD medio −$49,26 en GC). El
script `notebooks/kaggle/be_sweep_kernel/be_trigger_sweep_gc_nq_runner.py` queda
commiteado en su último estado (max_age_bars=50, últimas N sesiones) como referencia
para un intento futuro, pero **nunca corrió hasta el final** — no interpretar su
presencia en el repo como que produjo un resultado.

## P-63 · Merge de `research/avolcluster-nq-parity-oracle-20260901` a `foundation` — el resumen del auditor no mencionaba el cambio de kernel

**Asentada 2026-09-01.** El auditor reportó infraestructura de embudo EF0/EF1 para
aVolClusterPOI (4 commits: `4b0e5b3`, `58496ad`, `142142b`, `d3d912c`) viviendo en
`origin/research/avolcluster-nq-parity-oracle-20260901`, no en `foundation` — violación
de la regla de una sola rama (mergear el mismo día). Nico pidió mergear.

Verificado antes de mergear: los 4 commits existen, el contenido coincide con lo
relatado (barreras duras `FORBIDDEN_FIELDS`, descomposición 658=414+244), y los 5 tests
del núcleo EF0 corren y pasan de verdad (no solo "se reportó que pasaron").

**Lo que el resumen NO mencionaba**: la rama también trae un refactor real de
`edgelab/bridge/indicators/avolclusterpoi.py::detect_block()` — nuevos estados de
decisión (`ABSTAIN_FEW_CELLS`, `ABSTAIN_NO_HISTORY`, `ABSTAIN_NO_CLUSTER`,
`ABSTAIN_BELOW_THRESHOLD`, `CREATE`), nuevos campos en el dict de retorno (`median`,
`hot_threshold`, `history_samples`, `decision`, `clusters`, `selected_cluster`), y un
caso nuevo (`len(cells)<3`) que antes no estaba especial-casado. Las 4 claves
históricas (`best_score`, `threshold`, `zones`, `abstain`) se preservan — confirmado
corriendo los 60 tests de aVolClusterPOI de este repo (incluye los que yo mismo escribí
esta sesión: paridad 60t, bar-type, plateau/placebo, event-store extract) — todos
pasan después del merge.

Merge limpio (sin conflictos, `f876aa2`), pusheado. Suite completa post-merge:
1.224 passed, 5 failed, 1 error — verificado uno por uno que **ninguna de esas 6 fallas
la causó el merge**: 3 son las mismas preexistentes del triaje de PR #15
(`test_store_v2`, 2x `test_ulp_sweep`); `test_current_md` falla porque
`docs/CURRENT.md` nunca declaró `**Fecha:**` (archivo no tocado por este merge);
`test_verify_tree` es un `PermissionError` de Windows sobre un temp file (ambiental);
`test_prerange_sweep_formal::test_placebos_and_gates` es un bug preexistente de fixture
(`null_out` nunca se declaró `@pytest.fixture`, archivo no tocado por este merge).

**No se toma acción de remediación sobre el cambio de kernel** — parece backward-compatible
por los tests, pero se registra para que quede constancia de que un merge trajo más de lo
que su propio resumen relataba, y de que verificar "el código compila y los tests que se
mencionaron pasan" no es lo mismo que verificar "esto es todo lo que trae el commit".

## P-64 · Capa de régimen contractual (`contract_regime.py`) mergeada; rama `audit/notion-ai-sltp-p2b-provenance-20260830` sigue divergente y NO se mergeó completa

**Asentada 2026-09-01.** El auditor publicó una capa transversal de régimen contractual
causal (`edgelab/data/contract_regime.py`, política `previous_complete_session_volume_leader_monotonic_v1`
— cruce si el sucesor lideró estrictamente el volumen de la sesión D-1, empate conserva
vigente, nunca retrocede, sesión faltante bloquea el avance) en `eb8857d`, con su nota de
auditoría en `fc02d7d`. Verificado antes de traerlo: las 7 pruebas declaradas (causalidad
D-1→D, no-rollover-mismo-día, no-retroceso, empate, dato faltante, bordes half-open,
manifiesto adulterado) corren y pasan de verdad.

Al ir a mergear encontré que `fc02d7d` (y el `d3d912c` huérfano de P-63) viven en
`origin/audit/notion-ai-sltp-p2b-provenance-20260830` — **una rama con cientos de commits**,
divergente de `foundation` desde muy atrás (todo el desarrollo histórico de Gate1/Gate2/AVol
NQ, infra Kaggle, etc.), incluyendo `ce31031` (la reconciliación de PENDIENTE.md que P-49/P-59
ya daban por resuelta) que **tampoco está en `foundation`**. Es la misma familia de falla que
`docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md` y el incidente del 2026-08-10 describen, en
escala mucho mayor que lo que P-63 había encontrado (4 commits sueltos).

**Decisión tomada**: NO mergear esa rama completa (alto riesgo de conflictos y de repetir
la colisión de numeración P-56..59 ya vivida). En cambio, cherry-pick quirúrgico de los dos
commits de auditoría aislados (`d3d912c`→`724bb43`, `fc02d7d`→`1797bff`, cada uno toca un
solo archivo nuevo en `docs/audits/`, sin dependencias). El resto de esa rama —incluida la
reconciliación `ce31031`— **sigue sin converger con `foundation`**. Esto requiere una
decisión de Nico: auditar qué de esa rama sigue vivo/vale la pena traer, o declararla
histórica y archivarla. No se toma esa decisión acá.

Suite completa post-merge: 1.231 passed (7 más que P-63, los nuevos tests de
`contract_regime`), mismas 6 fallas preexistentes/ambientales de siempre, ninguna nueva.
Pusheado (`1797bff`).

**Implicación para EF0/aVolClusterPOI**: el propio auditor señala que el trace actual
(`NQ_06-26` solo) no alcanza para determinar el período realmente operable de ese contrato
— hace falta el manifiesto de régimen sobre NQ 03-26/06-26/09-26 solapados, que todavía no
se generó. Hasta entonces, correr EF0 sobre el trace actual sigue siendo válido como estudio
provisional del archivo, pero no se puede presentar como el período continuo operable real.

**Decisión de Nico (2026-09-01, verificación independiente confirmada)**: no auditar la
rama divergente ahora — no bloquea el camino científico actual (los artefactos necesarios
ya están en `foundation`). Queda **`FROZEN_READ_ONLY` / `DO_NOT_MERGE` / `DO_NOT_DELETE`**.
Cuando se audite algún día: inventario de paths + merge-base + equivalencia de parches,
nunca un merge completo; `ce31031` en particular no se cherry-pickea a ciegas porque toca
la reconciliación histórica de PENDIENTE.md. Camino crítico ahora: cadena NQ multicontrato
→ volumen diario causal → `contract_regime_manifest_v1` → recorte del período operable →
trace estructural → EF0 → preguntas → plan EF1.

