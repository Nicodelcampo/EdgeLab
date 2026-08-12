# PENDIENTE — decisiones abiertas

Registro de decisiones que el código señala explícitamente como "pendientes de
Nico/auditor". Ninguna de estas se toma unilateralmente en una implementación.
Cada entrada nombra el punto exacto del código que la referencia.

---

## P-01 · Tratamiento de `SIN_ZONAS` en el gate de balance

**Referenciada desde**: `diag/tasa_senales/F1.1_nulo_condicional_distancia.py`,
`agregar_balance_global()`, motivo de invalidez
`"archivo sin ninguna zona BigTrap2 (SIN_ZONAS)"`.

**Estado**: ABIERTA.

Un archivo de contrato con `n_total_zonas == 0` se marca `SIN_ZONAS` (distinto
de `ABSTAIN`, que significa datos rotos) y **hoy cuenta como inválido**, lo que
hace fallar el gate de esa covariable.

- **Opción A (actual, bloqueante)**: un contrato sin ningún evento BigTrap2
  invalida la corrida. Conservador: obliga a mirar por qué no hay eventos.
- **Opción B (neutral)**: se excluye del pooling sin fallar el gate, y se
  reporta en `archivos_excluidos`. Riesgo: un bug que suprima eventos pasaría
  silencioso.

**Criterio para decidir**: sólo con la pasada estructural de 201 sesiones a la
vista, viendo cuántos archivos caen en `SIN_ZONAS` y por qué. Decidir antes de
ver ningún endpoint.

---

## P-02 · `removed_reason="max_age"` es inalcanzable

**Referenciada desde**: `zone_lifecycle()` y `horizonte_zona()`.

**Estado**: ABIERTA.

`horizonte_zona()` devuelve `min(MAX_AGE_BARS, disponibles)` y `zone_lifecycle`
recorta `b1 = min(b1, created_bar + horizon_cap)`. Con `horizon_cap = H_i <=
MAX_AGE_BARS`, la condición `ages > max_age_bars` **nunca** se cumple dentro del
slice.

Consecuencias:

- `removed_reason = "max_age"` es código muerto.
- Toda zona que no se invalida se reporta `censored=True`.
- Los **riesgos competidores** declarados en `secondary_descriptive` están
  invalidados: uno de los cuatro no puede ocurrir.

El **endpoint primario no está sesgado**: con el `continue` del kernel, el toque
de la barra de expiración tampoco contaría.

**Opciones**: (A) reconocer que el horizonte efectivo es `H_i` y sacar `max_age`
de la lista de riesgos competidores; (B) permitir `b1 = created_bar +
MAX_AGE_BARS + 1` cuando hay barras disponibles, separando el tope de ventana
del tope de edad.

---

## P-03 · Falta de soporte común entre zonas y controles

**Referenciada desde**: PR #11, sección de defectos abiertos.

**Estado**: ABIERTA — bloquea la corrida formal.

El pool típico es de 9–11 candidatos y se eligen K=8: es casi un censo del
minuto, no un matching selectivo. Las zonas BigTrap2 tienen volumen extremo por
diseño del indicador, y los controles excluyen exactamente esas barras.

**Ramas pre-registradas** (elegir UNA, con los números estructurales a la vista
y sin haber abierto ningún endpoint):

- **A — Recorte al soporte común.** El estimand pasa a ser la región de
  solapamiento. La cobertura cae por debajo de 95% y eso requiere enmienda
  explícita del gate, no relajación silenciosa.
- **B — Pesos de solapamiento o entropy balancing** en lugar de K-NN.
- **C — Controles de casi-evento**: barras que casi disparan BigTrap2. Separan
  el efecto de la geometría del efecto del volumen.

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
