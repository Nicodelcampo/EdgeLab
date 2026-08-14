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
la suite sin fallos; registrar el enlace/commit verificado.

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
brutos o derivados que los términos no permitan.

---

## P-08 · Identidad del `BigTrap2.cs` local (v2.5.2) vs blobs del repo

**Referenciada desde**: verificación git-blob del 2026-08-14 (auditoría externa,
`docs/research/AUDITORIA_EXTERNA_2026-08-14.md` §1).

**Estado**: ABIERTA — bloquea la exportación de oráculos CSV con identidad sellada.

El `.cs` que corre en la máquina local (62.401 bytes, CRLF puro, marcadores
v2.5.2: meta `version=2.5.2`, `LogEventAt` en los 7 sitios, drenaje en
`Terminated`) tiene sha1 git-blob `ee984f6ef4d92827101eaf56a8a60d0a43ab53f6`,
que no coincide con ningún blob del repo: `fix/bigtrap2-v252-tick-export` tiene
`dbf226138af813bb035e08e339ba5dadc4b3a910` (v2.5.2 completa) y las ramas
research/audit tienen `78f6909dcb75f8aa78dafb354ca4cf851eaa2093` (era v2.5.1,
con el helper `LogEventAt` presente pero los sitios de export sin cambiar).
Hay una diferencia de contenido real, de localización desconocida desde afuera.

**Criterio de cierre**: `git status` + `git diff` local contra
`fix/bigtrap2-v252-tick-export`; decidir cuál copia es la canónica; commitear
la que genere oráculos y registrar su blob en `nt8/README.md` (cuyo inventario
además quedó desactualizado: lista BigTrap2 como v2.1). Ningún CSV exportado
antes de esto tiene procedencia completa.

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
