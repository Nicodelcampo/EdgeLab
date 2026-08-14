# PENDIENTE — decisiones abiertas

Registro de decisiones que el código señala explícitamente como "pendientes de
Nico/auditor". Ninguna de estas se toma unilateralmente en una implementación.
Cada entrada nombra el punto exacto del código que la referencia.

**Punto de entrada para continuidad**: `docs/research/HANDOFF_AUDITORIA_2026-08-14.md`.

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

---

## P-06 · El gate `MAX_ABS_SMD ≤ 0.10` no tiene panel de calibración sintético

**Estado**: ABIERTA — anotada, no construida (instrucción explícita: no construir el panel ahora).

El umbral 0.10 es convención de la literatura; no existe panel propio que mida error tipo I ni potencia para este matcher concreto. Queda registrado para decidir con pre-registro propio si se construye antes o después de la corrida formal de 201 sesiones.

---

## P-07 · M0 — decisión de licencia de los datos locales

**Estado**: ABIERTA — bloqueo legal/operativo, no técnico.

Falta `DATA_LICENSE_DECISION.md` (proveedor, términos, alcance, responsable). Insumos del 2026-08-14: docs de política CME/Kaggle commiteados en `bda944a`.

**Criterio de cierre**: Nico aporta la fuente de los términos y aprueba el documento.

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

**Estado**: ABIERTA — decisión de Nico, nadie más.

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
