# BigTrap2 — nulo local por reflexión de geometría

**Estado:** `PREREGISTERED_NOT_RUN`
**Fecha de sellado:** 2026-08-12
**Rama:** `research/bigtrap2-local-displacement-null`
**Spec congelada:** `specs/bigtrap2_local_reflection_null_v2.json`
**SHA-256 de spec (LF):** `7868ff327b240a9e3a8c5a2dc2412f8605f3bd91b371dc828a677755a5e0993b`
**NORTH_STAR (cuerpo):** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Enmienda:** Enmendado por F2.7 (`docs/research/F2.7_ENMIENDA_V2_REFLEXION_2026-08-12.md`) antes de cualquier corrida; v1 superada por defectos D1 (endpoint binario saturado) y D2 (espejo muerto en B+1).
**Alcance de datos:** research interno local; M0 sigue abierto. No se versionan ni redistribuyen parquets, filas ni artefactos derivados hasta una decisión de licencia explícita.

## 1. Pregunta y motivación

F1.1 halló más toques de zonas BigTrap2 que de ubicaciones aleatorias. La campaña de matching posterior quedó bloqueada porque `bar_volume` forma parte de la propia definición de una zona: las barras sin creación no tienen soporte común suficiente para ser sus controles.

Esta campaña cambia el contrafactual, no el indicador: para cada zona creada se evalúa la **misma geometría** reflejada alrededor del cierre de su barra de creación. Volumen, hora, sesión, régimen observable, anchura, edad disponible, lado semántico y distancia absoluta quedan constantes por construcción; sólo cambia la ubicación firmada respecto del precio de creación.

> ¿La zona real recibe más primer toque antes de su remoción que su reflejo local, disponible en el mismo instante y con igual distancia absoluta?

Esto adjudica una asimetría de ubicación local. No identifica una estrategia, causalidad de mercado, dirección futura ni rentabilidad.

## 2. Event-space y población congelados

Se enumeran antes de elegir la población: creación, zona activa, primer toque, toque n-ésimo, invalidación, expiración y censura administrativa. La población fuente son **todas** las zonas BigTrap2 creadas en 6E/time:1 hasta 2026-06-30, sin condicionar por toque, volumen observado posterior ni outcome.

El filtro de creación es por fecha de sesión (America/Chicago) ≤ 2026-06-30, nunca por rango del archivo: el archivo de smoke contiene sesiones de holdout (medido 2026-08-12).

Una zona es elegible para el par reflejado sólo si, al cierre de su barra creadora, su reflexión es distinta y disjunta de la geometría real. Las exclusiones se contabilizan por motivo y no se sustituyen post hoc. Si la cobertura elegible es menor que 95 % de todas las creaciones, la campaña termina `ABSTAIN_REFLECTION_COVERAGE`.

## 3. Construcción causal y exacta del reflejo

Sea `a_i = close_t[B_i]` el cierre entero en ticks de la barra creadora. Para la zona real `[lo_i, hi_i]`, el único control es:

```text
mirror_lo_i = 2 * a_i - hi_i
mirror_hi_i = 2 * a_i - lo_i
```

La construcción se efectúa sólo con datos disponibles al cierre de `B_i`. Preserva exactamente ancho, distancia absoluta al ancla y grilla de ticks. El campo `is_bull` se conserva como etiqueta semántica del par; las **reglas de lifecycle** del espejo son la reflexión geométrica de las de la zona: la invalidación del espejo es por cierre a través del espejo en la dirección que se aleja del ancla (equivale a invertir `is_bull` SÓLO para el lifecycle). Sin esto, con CloseThrough, el espejo bull ubicado bajo el precio muere en B+1 casi siempre y E[r] > 0 bajo el nulo por construcción (defecto D2 de v1, medido por Monte Carlo — ver F2.7). La zona y su reflejo están disponibles desde `B_i + 1`; la barra creadora nunca cuenta como toque.

No hay pool, K, caliper, matching, selección de vecinos ni parámetro de desplazamiento. La reflexión es la única transformación primaria.

## 4. Lifecycle y frontera temporal

Real y reflejo corren con la función pura que replica la precedencia de `bigtrap2.py`:

1. expiración si `age > max_age_bars` y `continue`;
2. toque por intersección;
3. invalidación con el cierre de esa misma barra.

*Nota editorial pre-corrida*: La ventana de exposición donde cuentan los toques es min(max_age_bars, disponibles); la barra created+max_age_bars+1 sólo chequea expiración y su toque no cuenta (precedencia del kernel). La lectura de datos termina mecánicamente en 2026-06-30; jamás se carga julio ni el holdout. Una zona truncada por esa frontera se reporta censurada, no se elimina ni se le imputa un toque.

## 5. Estimand e inferencia

Para cada par elegible, la carrera de primer pasaje dentro del par: r_i = +1 si la zona real toca antes que el espejo (dentro de H_i, antes de remoción/censura), −1 si el espejo toca primero, 0 en empate técnico o doble censura. R_s = mean(r_i) en la sesión creadora; Delta_reflection = mean_s(R_s). Toques en la misma barra se resuelven por timestamp de tick. Las categorías de cero se publican por separado con sus denominadores (frac_resueltos, frac_doble_censura, frac_empate_tecnico). El espejo corre el lifecycle geométricamente reflejado (§3). Bajo el nulo de ubicaciones intercambiables dadas geometría y horizonte, P(real primero) = P(espejo primero) exactamente, sin estimar σ. Inferencia: HAC Bartlett sobre la serie cronológica de R_s, lag ceil(sqrt(n_sessions)), IC bilateral 95 %, MDE fijado en 0,05. Etiquetas pre-registradas: REFLECTION_POSITIVE / COMPATIBLE_WITH_ZERO / REFLECTION_NEGATIVE / ABSTAIN_*. El binario de v1 queda como secundario declarado y descriptivo.

## 6. Gates, auditoría y pruebas obligatorias

Gates adicionales (v2): `frac_resueltos < 0,30` → `ABSTAIN_RESOLUTION` (un IC ancho se leería como ausencia de efecto cuando sería ausencia de resolución); `frac_empate_tecnico > 0,01` → `ABSTAIN_TIE_RULE` y revisar granularidad de timestamps. El gate de cobertura ≥ 95 % se mantiene como trampa de seguridad aunque la evidencia dice que pasa por construcción.

Antes de datos reales deben existir tests truth-known para: reflexión exacta; ancho/distancia conservados; no-overlap; disponibilidad desde `B+1`; precedencia touch/invalidation/expiration; cutoff pre-holdout; side preservado; determinismo; igualdad del horizonte; exclusiones y cobertura; ponderación igual por sesión; HAC con serie sintética; nulo sintético; señal sintética conocida; rechazo de árbol dirty o cambio de HEAD; **regresión de D2** (espejo NO muere en B+1 en path ascendente); y **empates a nivel barra resueltos por tick**.

El artefacto debe registrar hashes de spec, NORTH_STAR, kernel, script y dataset; `head_start/end`, `dirty_start/end`; todos los denominadores; exclusiones; lifecycle de ambos lados; resultados por sesión; y `outcomes_accessed=false`. Una auditoría read-only debe recalcular pares, denominadores, estimador y HAC antes de cualquier interpretación.

## 7. Prohibiciones y refutación

Prohibido: tocar `bigtrap2.py`/defaults, tick:25, holdout, P&L, retornos, dirección de trading, stops, targets, parámetros, despliegues alternativos o el protocolo F1.1 sellado. No se modifica el reflejo después de mirar datos.

La hipótesis de una asimetría local queda refutada si el IC contiene cero. Aun un resultado positivo no demuestra que BigTrap2 cause el movimiento ni que sea operable: el espejo prueba sólo esta comparación geométrica local.

## Aporte al referente

Este nulo elimina la dependencia del soporte común de volumen sin acercarse a P&L ni al holdout. Una adjudicación limpia decide si la ubicación detectada por BigTrap2 merece una hipótesis posterior, no una promoción.
