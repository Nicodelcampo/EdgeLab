# BigTrap2 — nulo local por reflexión de geometría

**Estado:** `PREREGISTERED_NOT_RUN`
**Fecha:** 2026-08-12
**Rama:** `research/bigtrap2-local-displacement-null`
**Spec congelada:** `specs/bigtrap2_local_reflection_null_v1.json`
**SHA-256 de spec:** `301be316dc2e3fe3c8d7272b479aae56fe54eaa815374fca27c3fee15c699ae5`
**NORTH_STAR (cuerpo):** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Alcance de datos:** research interno local; M0 sigue abierto. No se versionan ni redistribuyen parquets, filas ni artefactos derivados hasta una decisión de licencia explícita.

## 1. Pregunta y motivación

F1.1 halló más toques de zonas BigTrap2 que de ubicaciones aleatorias. La campaña de matching posterior quedó bloqueada porque `bar_volume` forma parte de la propia definición de una zona: las barras sin creación no tienen soporte común suficiente para ser sus controles.

Esta campaña cambia el contrafactual, no el indicador: para cada zona creada se evalúa la **misma geometría** reflejada alrededor del cierre de su barra de creación. Volumen, hora, sesión, régimen observable, anchura, edad disponible, lado semántico y distancia absoluta quedan constantes por construcción; sólo cambia la ubicación firmada respecto del precio de creación.

> ¿La zona real recibe más primer toque antes de su remoción que su reflejo local, disponible en el mismo instante y con igual distancia absoluta?

Esto adjudica una asimetría de ubicación local. No identifica una estrategia, causalidad de mercado, dirección futura ni rentabilidad.

## 2. Event-space y población congelados

Se enumeran antes de elegir la población: creación, zona activa, primer toque, toque n-ésimo, invalidación, expiración y censura administrativa. La población fuente son **todas** las zonas BigTrap2 creadas en 6E/time:1 hasta 2026-06-30, sin condicionar por toque, volumen observado posterior ni outcome.

Una zona es elegible para el par reflejado sólo si, al cierre de su barra creadora, su reflexión es distinta y disjunta de la geometría real. Las exclusiones se contabilizan por motivo y no se sustituyen post hoc. Si la cobertura elegible es menor que 95 % de todas las creaciones, la campaña termina `ABSTAIN_REFLECTION_COVERAGE`.

## 3. Construcción causal y exacta del reflejo

Sea `a_i = close_t[B_i]` el cierre entero en ticks de la barra creadora. Para la zona real `[lo_i, hi_i]`, el único control es:

```text
mirror_lo_i = 2 * a_i - hi_i
mirror_hi_i = 2 * a_i - lo_i
```

La construcción se efectúa sólo con datos disponibles al cierre de `B_i`. Preserva exactamente ancho, distancia absoluta al ancla y grilla de ticks. El campo `is_bull` se conserva: el pseudo-objeto difiere únicamente en ubicación; no se le asigna una nueva semántica de detector. La zona y su reflejo están disponibles desde `B_i + 1`; la barra creadora nunca cuenta como toque.

No hay pool, K, caliper, matching, selección de vecinos ni parámetro de desplazamiento. La reflexión es la única transformación primaria.

## 4. Lifecycle y frontera temporal

Real y reflejo corren con la función pura que replica la precedencia de `bigtrap2.py`:

1. expiración si `age > max_age_bars` y `continue`;
2. toque por intersección;
3. invalidación con el cierre de esa misma barra.

Con defaults, el horizonte natural permite la barra de expiración: `H_i = min(max_age_bars + 1, barras_preholdout_disponibles)`. La lectura de datos termina mecánicamente en 2026-06-30; jamás se carga julio ni el holdout. Una zona truncada por esa frontera se reporta censurada, no se elimina ni se le imputa un toque.

## 5. Estimand e inferencia

Para cada par elegible:

```text
y_real_i   = 1 si la zona real toca antes de remoción/censura dentro de H_i
y_mirror_i = 1 si el reflejo toca antes de remoción/censura dentro de H_i
r_i        = y_real_i - y_mirror_i
R_s        = mean(r_i) en la sesión creadora s
Delta_reflection = mean_s(R_s)
```

Cada sesión pesa una vez. La inferencia primaria usa HAC Bartlett sobre la serie cronológica de `R_s`, con lag `ceil(sqrt(n_sessions))`, IC bilateral 95 % y MDE con potencia 0,80. No se inspecciona ni selecciona por resultados secundarios.

Etiquetas pre-registradas: `REFLECTION_POSITIVE` si el límite inferior del IC es mayor que cero; `COMPATIBLE_WITH_ZERO` si contiene cero; `REFLECTION_NEGATIVE` si el límite superior es menor que cero; `ABSTAIN_PROVENANCE`, `ABSTAIN_REFLECTION_COVERAGE` o `ABSTAIN_INFERENCE` si falla el gate correspondiente.

## 6. Gates, auditoría y pruebas obligatorias

Antes de datos reales deben existir tests truth-known para: reflexión exacta; ancho/distancia conservados; no-overlap; disponibilidad desde `B+1`; precedencia touch/invalidation/expiration; cutoff pre-holdout; side preservado; determinismo; igualdad del horizonte; exclusiones y cobertura; ponderación igual por sesión; HAC con serie sintética; nulo sintético; señal sintética conocida; y rechazo de árbol dirty o cambio de HEAD.

El artefacto debe registrar hashes de spec, NORTH_STAR, kernel, script y dataset; `head_start/end`, `dirty_start/end`; todos los denominadores; exclusiones; lifecycle de ambos lados; resultados por sesión; y `outcomes_accessed=false`. Una auditoría read-only debe recalcular pares, denominadores, estimador y HAC antes de cualquier interpretación.

## 7. Prohibiciones y refutación

Prohibido: tocar `bigtrap2.py`/defaults, tick:25, holdout, P&L, retornos, dirección de trading, stops, targets, parámetros, despliegues alternativos o el protocolo F1.1 sellado. No se modifica el reflejo después de mirar datos.

La hipótesis de una asimetría local queda refutada si el IC contiene cero. Aun un resultado positivo no demuestra que BigTrap2 cause el movimiento ni que sea operable: el espejo prueba sólo esta comparación geométrica local.

## Aporte al referente

Este nulo elimina la dependencia del soporte común de volumen sin acercarse a P&L ni al holdout. Una adjudicación limpia decide si la ubicación detectada por BigTrap2 merece una hipótesis posterior, no una promoción.
