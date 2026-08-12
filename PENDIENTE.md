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

**Estado**: ABIERTA — mecánica.

`research/bigtrap2-distance-matched-null` arrastra su propia copia de
`CLAUDE.md`, `docs/NORTH_STAR.md` y `tests/test_north_star_hash.py` (commit
`9474bc6`) de lo que en `audit/p0-bigtrap2-drift` es `1916ffa`. Se resuelve con
rebase sobre `1916ffa` y drop de ese commit.

---

## P-05 · No hay CI

**Estado**: ABIERTA.

La suite de 826 tests corre sólo localmente. No hay ninguna garantía mecánica de
que un commit pusheado esté verde. Todo el reporte de estado depende de que quien
corre la suite reporte fielmente.

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
