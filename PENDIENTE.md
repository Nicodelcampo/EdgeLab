# PENDIENTE — decisiones abiertas

Registro de decisiones que el código señala explícitamente como "pendientes de
Nico/auditor". Ninguna de estas se toma unilateralmente en una implementación.
Cada entrada nombra el punto exacto del código que la referencia.

---

## P-01 · Tratamiento de `SIN_ZONAS` en el gate de balance

**Referenciada desde**: `diag/tasa_senales/F1.1_nulo_condicional_distancia.py`,
`agregar_balance_global()`, motivo de invalidez
`"archivo sin ninguna zona BigTrap2 (SIN_ZONAS)"`.

**Estado**: RESUELTA (2026-08-13).

Cerrada por la transición hacia el nulo reflectivo F2.7 / F2.8 y la simplificación de micro-régimen F2.9 / F2.10. En el pipeline de matching heredado, la opción neutral (Opción B: exclusión explícita reportada en `archivos_excluidos` sin corromper el balance global de covariables continuas) es la norma adoptada.

---

## P-02 · `removed_reason="max_age"` es inalcanzable

**Referenciada desde**: `zone_lifecycle()` y `horizonte_zona()`.

**Estado**: RESUELTA (2026-08-13).

Cerrada por diseño en F2.7 / F2.8: el estimand primario de primer pasaje adopta un horizonte explícito simétrico e idéntico para la zona real y el espejo ($H_i$), eliminando el código muerto de riesgos competidores no identificables y censura asimétrica.

---

## P-03 · Falta de soporte común entre zonas y controles

**Referenciada desde**: PR #11, sección de defectos abiertos.

**Estado**: RESUELTA (2026-08-12).

Cerrada por decisión de la enmienda F2.7. La curva F2.5 demostró que el estimand `v3-local` de matching condicional por distancia no posee soporte común medible bajo K-NN sin deflactar la varianza de referencia. Se declara dicho estimand como no medible según lo pre-registrado. Su campaña sucesora es la enmienda F2.7 (Nulo Local por Reflexión de Geometría, spec v2), que elimina el matching selectivo y los controles K-NN en favor de una transformación reflectiva exacta de la geometría sobre el ancla.

---

## P-04 · Duplicado de gobernanza en la rama

**Estado**: RESUELTA (2026-08-12).

`research/bigtrap2-distance-matched-null` arrastra su propia copia de
`CLAUDE.md`, `docs/NORTH_STAR.md` y `tests/test_north_star_hash.py` (commit
`9474bc6`) de lo que en `audit/p0-bigtrap2-drift` es `1916ffa`.

La rama sucesora `research/bigtrap2-soporte-balance-curve` fue rehecha sobre
`audit/p0-bigtrap2-drift@1916ffa`, omitiendo sólo `9474bc6`. La rebase de
prueba y la aplicada produjeron un árbol idéntico al previo; el primer commit
publicado de la historia corregida es `9fcdd9c` y el ancestro de auditoría es
verificable mecánicamente.

---

## P-05 · CI declarada, verificación remota pendiente

**Estado**: ABIERTA — parcialmente resuelta en código.

La rama incorpora `.github/workflows/ci.yml`: instala
`requirements/core-bridge-dev.lock` y ejecuta `pytest -q` en `push` y
`pull_request`. Eso elimina la ausencia de automatización en el árbol.

Todavía falta confirmar desde GitHub que el workflow ejecutó correctamente con
el lock exacto (en particular, que los pins resuelven en el runner). No se deben
relajar los pins para forzar un verde: un fallo de instalación sería evidencia
sobre el lock, no sobre la semántica del workflow.

**Criterio de cierre**: un run remoto visible de CI que instale el lock y termine
la suite sin fallos; registrar el enlace/commit verificado. (Nota 2026-08-14:
los pushes `03d1104`, `84dcfcd` y `2ad04ec` ya dispararon el workflow tres
veces; falta la confirmación en la pestaña Actions.)

---

## P-06 · El gate `MAX_ABS_SMD ≤ 0.10` no tiene panel de calibración sintético

**Referenciada desde**: `docs/research/F2.6_NOTA_ESTIMAND_SUCESOR_2026-08-12.md`
§3; `MAX_ABS_SMD` en `diag/tasa_senales/F1.1_nulo_condicional_distancia.py` y
`diag/tasa_senales/F2.5_curva_soporte_balance.py`.

**Estado**: ABIERTA — anotada, no construida (instrucción explícita: no
construir el panel ahora).

El umbral `0.10` sobre SMD balanceado es un valor convencional de la literatura
de matching observacional. No existe en este repo un panel de calibración
sintético (datos simulados con desbalance conocido) que mida, para este
matcher concreto (K-NN MAD-estandarizado, caliper, `k_efectivo`, tamaños de
pool reales del archivo), la tasa de error tipo I (¿con cuánta frecuencia el
gate declara "balanceado" un desbalance real?) ni la potencia (¿con cuánta
frecuencia detecta un desbalance que sí existe?) en función de `n`, tamaño de
pool y magnitud del desbalance inyectado.

Sin ese panel, `celda_pasa_gates=True` en la curva de F2.5 (o en el resultado
formal de F1.1) es una afirmación calibrada por convención de la literatura,
no por evidencia propia de que el umbral discrimina correctamente para este
diseño específico.

**Criterio para decidir**: no aplica todavía — este ítem queda registrado para
que se decida, en un turno futuro y con pre-registro propio, si vale la pena
construir el panel antes o después de la corrida formal de 201 sesiones.

---

## P-07 · M0 — decisión de licencia de los datos locales

**Referenciada desde**: gate M0 del estado operativo y la ausencia de
`DATA_LICENSE_DECISION.md` en el árbol versionado.

**Estado**: ABIERTA — bloqueo legal/operativo, no técnico.

No hay una decisión versionada que identifique el proveedor, los términos
aplicables, el alcance permitido (research interno, publicación de artefactos,
redistribución de datos derivados) y el responsable que acepta ese riesgo.
El repositorio puede verificar hashes y procedencia, pero no puede inferir una
licencia a partir de parquets locales ni crearla unilateralmente.

**Criterio de cierre**: Nico o el responsable autorizado aporta la fuente de los
términos y aprueba una `DATA_LICENSE_DECISION.md` con alcance, restricciones y
fecha. Hasta entonces no se declara este gate satisfecho ni se publican datos
brutos o derivados que los términos no permitan. (Insumo nuevo 2026-08-14: los
docs de política CME/Kaggle commiteados en `bda944a`.)

---

## P-08 · Identidad del `BigTrap2.cs` local (v2.5.2) vs blobs del repo

**Referenciada desde**: verificación git-blob del 2026-08-14 (auditoría externa,
`docs/research/AUDITORIA_EXTERNA_2026-08-14.md` §1).

**Estado**: RESUELTA (2026-08-14, commit `2ad04ec`).

La copia local quedó commiteada como canónica: `nt8/BigTrap2.cs` en HEAD
`2ad04ec` tiene blob `ee984f6ef4d92827101eaf56a8a60d0a43ab53f6` (62.401 bytes),
byte-idéntico al archivo que corre en NT8 (verificado por el auditor externo
contra el archivo subido por chat: mismo sha1 git-blob en crudo CRLF).

Residuales no bloqueantes que quedan registrados: (a) el delta semántico contra
`dbf22613` (la v2.5.2 de `fix/bigtrap2-v252-tick-export`) no quedó documentado —
la canónica es ahora la del repo por definición, pero conviene leer el diff una
vez; (b) `nt8/README.md` sigue listando BigTrap2 como v2.1 — actualizar el
inventario con el blob nuevo. (Nota 2026-08-14 tarde: el `.cs` canónico pasó a
ser el blob `62b0c951` tras el fix de frontera de P-13 — actualizar el README
con ESE blob.)

---

## P-09 · El JSON formal AVOLT no cierra contra su propio sello

**Referenciada desde**: `docs/research/AVOLT_AUDITORIA_DICTAMEN_2026-08-14.md`,
hallazgo H1.

**Estado**: ABIERTA — mecánica.

`diag/tasa_senales/AVOLT_formal_d5c41684e162.json`: el sha256 declarado no
cierra sobre una recomputación independiente, y `zones.session_means` trae 176
valores contra `n_sessions=188` declarado (media/SE recomputados difieren de
los declarados). El archivo commiteado no es el payload que produjo la corrida.

**Criterio de cierre**: regenerar el JSON desde el runner y recommitear;
verificación de una línea en el dictamen H1.

---

## P-10 · Merges que cambian semántica de validación, pendientes de decisión

**Referenciada desde**: `CLAUDE.md` (estado vigente 2026-08-10) y commit
`70d2ed4` de `audit/p0-bigtrap2-drift`.

**Estado**: ABIERTA — decisión de Nico, nadie más.

Tres líneas remotas sin mergear tocan semántica o premisas vigentes:

1. `fix/g2-a1-statistical-semantics` + `fix/g2-a1-calibration-hardening`:
   reescriben `g2_decision.py`/`promotion.py` con calendario obligatorio,
   `MIN_DSR_SESSIONS` y DSR V1/V2 — más riguroso que la enmienda G2-A1
   mergeada. Cambio de semántica de validación: requiere decisión explícita.
2. `research/ym-prerange-session-window`: `minute_window_matrices` con
   calendario explícito y cruce de medianoche — más completo que
   `build_session_matrices`. Revisar antes de tocar `edgelab/sessions.py`.
3. `docs/lux-imb-source-correction`: retracta la premisa de H-COND-1 (el
   indicador LUX-IMB no borra zonas mitigadas). La versión vigente en el repo
   sigue describiendo el bloqueo por la razón vieja.

**Criterio de cierre**: una decisión merge/no-merge por rama, registrada acá.

---

## P-11 · El oráculo aVol de ES 09-26 no existe (archivo duplicado del 06-26)

**Referenciada desde**: verificación del auditor externo 2026-08-14
(`docs/research/W1_PARIDAD_SANDBOX_2026-08-14.md` §5).

**Estado**: RESUELTA (2026-08-14, commit `78de4d6`) — verificada.

El archivo re-exportado tiene blob `bd8b72652dbf5e6d73686f4014d5cad108353b0d`
(150.734 bytes), meta `instrument=ES 09-26` correcta, 1.066 eventos,
ventana 01-may→30-jun y `session_index` arrancando en 22 (instancia cargada
~01-abr: 21 sesiones completas antes del primer evento → perfil caliente, sin
el defecto H3 del dictamen). El duplicado viejo quedó atrás.

Bloqueo residual (no es esta P): para el replay de ES falta el parquet ES 09-26
en el sandbox — 453 MB no entra como adjunto; ventanear abr→jun + warmup o
partir por mes. Ver `docs/research/W1_PARIDAD_SANDBOX_R2_2026-08-14.md` §2.

---

## P-12 · Falta el parquet 6E 09-26 de 90 días (abril incluido)

**Referenciada desde**: verificación del auditor externo 2026-08-14
(`docs/research/W1_PARIDAD_SANDBOX_2026-08-14.md` §5; veredicto medido en
`W1_PARIDAD_SANDBOX_R2_2026-08-14.md` §3).

**Estado**: ABIERTA — paquete de datos.

El paquete W1 pedía 90 días (04-01→06-30); el parquet entregado cubre solo
junio (manifiesto ya regenerado y coincidente ✓). El paquete posterior trajo el
parquet 06-26 (`becc5625…`, verificado OK) "para validar los 9 TRAPs de abril",
pero **no puede**: los TRAPs son del contrato 09-26 (back-month en abril) y el
06-26 operaba 40–48 ticks abajo (01-abr: rango [1,1643; 1,1666] vs zona
[1,170025; 1,170075] del TRAP#0 — sin solape); el control negativo del kernel
sobre abril del 06-26 (2.985 TRAPs) no reproduce ninguno de los 9. Mismo
contrato + misma ventana (H2 del dictamen AVOLT) no admite sustitución por
"front-month natural".

**Criterio de cierre**: empaquetar el parquet **09-26 de 90 días** — el primer
manifiesto recibido declaraba 3.182.270 filas / hash `2377b076…`: casi seguro
ese build completo ya existe local; partirlo por mes si hace falta, con el
manifiesto regenerado desde el archivo final.

---

## P-13 · BigTrap2 time:1 — silencio de TRAPs del oráculo después del 16-abr

**Referenciada desde**: verificación del auditor externo 2026-08-14
(`W1_PARIDAD_SANDBOX_2026-08-14.md` §3; cierre medido en
`W1_PARIDAD_SANDBOX_R2_2026-08-14.md` §1).

**Estado**: RESUELTA (2026-08-14, commits `f77a3be` + `c899970`) — con la
etiqueta formal pendiente de la corrida local gobernada.

Raíz medida: en `AccumulateTick()` el `return` del camino de tiempo dejaba
inalcanzable el bloque de frontera de sesión → `sesionNoConfiable` nunca se
reseteaba en time:1 → supresión permanente tras el primer mismatch (17-abr).
Fix verificado sobre el patch: reubicación exacta de la frontera antes del
return. Oráculo nuevo con identidad verificada (blob `0837ef7e`, sha256
`4c76a0f2…`): 3.807 TRAPs, 9 `SESION_RESINCRONIZADA` con contadores (uno por
cada sesión marcada del oráculo viejo — cierra la cadena causal).
Comparación 1:1 junio (sandbox, diagnóstica): **3.628/3.638 EXACT (99,73 %)**;
resto atribuido con causa medida: 128 colas suprimidas documentadas, 1 barra de
borde de ventana, 2 field_diff de 1 tick entre las dos rutas de datos, 8 del
lado Python (7 = defecto del parquet 25-jun → P-14; 1 = anomalía de barra
idéntica a investigar local).

Decisiones y residuales registrados: (a) Nico decidió que en futuras versiones
`sesionNoConfiable` marque los eventos en el log en vez de suprimirlos (un
oráculo suprimido es indistinguible de uno sin detecciones); (b) el meta sigue
declarando `version=2.5.2` con el código ya cambiado (blob `62b0c951`) — subir
el string en la próxima edición; (c) borrar la copia vieja
`BigTrap2_v252_6E_0926_time1_90d_completo__Minute1.csv` (blob `fb41f33a`, la
filtrada) para que el nombre no mienta; (d) divergencia semántica medida a
decidir en la campaña: la supresión por sesión hace que el universo de traps de
junio del oráculo sea 3,4 % menor que el del kernel (que no puede desincronizar
por construcción).

---

## P-14 · Defecto del 25-jun en el parquet de junio de 6E 09-26 (`46413432…`)

**Referenciada desde**: comparación 1:1 del auditor externo 2026-08-14
(`W1_PARIDAD_SANDBOX_R2_2026-08-14.md` §4).

**Estado**: ABIERTA — defecto de datos.

Al parquet W1 le faltan los minutos 11:02–11:10 ART del 25-jun (el nativo NT8
tiene barras activas de 314 a 1.893 de volumen ahí) y la barra 12:48 ART
aparece inflada (vol 227 vs 37). Escapó a la batería estructural (que miraba
duplicados en mantenimiento, no minutos faltantes intra-sesión). Es la causa de
7 de los 8 MISSING_IN_PYTHON de la comparación de junio.

**Criterio de cierre**: regenerar el parquet desde el `.Last.txt` exigiendo
cobertura por minuto contra la serie nativa (extender el chequeo barras-propias
vs `6E_1min.csv` a "0 minutos faltantes en horario activo"), o auditar la fuente.
