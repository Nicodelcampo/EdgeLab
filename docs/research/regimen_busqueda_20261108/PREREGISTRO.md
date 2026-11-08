# Pre-registro: búsqueda de régimen offline sobre los cubos (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr; pedido de Nico: «dale con todo» al plan del 08/11; variantes A–D pedidas por Nico el
07/11: «3 meses independientes… o pedir más días o más estabilidad entre los días»). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF3** (procedimiento de selección sobre grillas ya
corridas; la confirmación sería forward, ver abajo). Familia `REGIMEN_OFFLINE`, 4 pruebas en el contador global.

## Pregunta

Las familias mueren porque buscan un efecto FIJO para todo el período. ¿Elegir cada mes, con sólo el pasado, la celda más ESTABLE de
los últimos W meses (de entre las grillas ya corridas) da mejor R neto por operación en el mes siguiente que elegir al azar entre las
celdas elegibles y que elegir la mejor celda ESTÁTICA (todo el pasado)? Es la tesis de Nico: «lo que funciona ahora aunque antes no».

**Justificación económica:** los mercados cambian de régimen (volatilidad, participantes, tendencia). Una regla que funciona en un
régimen y no en otro promedia ≈ 0 en todo el período y muere en un barrido estático, pero se podría operar si su régimen persiste lo
suficiente como para detectarlo con el pasado reciente.

**Cómo podría refutarse:** ninguna variante le gana al azar más que el máximo del nulo de signo (p de familia > 0,05), o le gana al
azar pero no a la estática (entonces no es régimen, es calidad fija), o el R neto de lo elegido no es positivo.

## Universo y datos

- Cubos de `tools/cubos_regimen.py`: las campañas en R del atlas (106 lanzadas; entran las que tengan cubo con operaciones al correr;
  la lista exacta queda en el resultado). Período de cada cubo: inicio del DESC → 30/09/2026. **Nunca el holdout.**
- Cada cubo = las operaciones de toda su grilla, con el nivel de cada perilla, la sesión y el R neto (costos canónicos ya restados).
- Unidad: la sesión (las operaciones del mismo día están correlacionadas).

## Procedimiento (`edgelab/research/regimen_offline.py`, `buscar_streaming`, equivalente probado a `walk_forward`)

Para cada mes H (con W meses previos disponibles) y cada cubo: celdas con ≥ 30 operaciones en el cubo; puntaje = t del R diario en
los W meses previos (días activos), con pisos. Se elige UNA celda por cubo y se operan en H los k = 3 cubos de mejor puntaje
(R neto en H = suma de R / suma de operaciones).

| Variante | W (meses) | Pisos en W | Además |
|---|---|---|---|
| A_3M_CADA_MES | 3 | ≥ 30 ops, ≥ 20 días, ≥ 50 % días positivos | R > 0 y ≥ 4 días activos en CADA uno de los 3 meses |
| B_2M_ESTABLE | 2 | ≥ 30 ops, ≥ 20 días, ≥ 55 % días positivos | R > 0 y ≥ 6 días activos en cada mes |
| C_1M_MUY_ESTABLE | 1 | ≥ 25 ops, ≥ 12 días, ≥ 60 % días positivos | — |
| D_3M_SIN_CADA_MES | 3 | ≥ 30 ops, ≥ 20 días, ≥ 50 % días positivos | — (control de A) |

Controles con el mismo k: **AZAR** (k cubos y una celda elegible de cada uno, sorteados; 200 sorteos) y **ESTÁTICA** (mismo
puntaje y pisos con TODO el pasado antes de H).

**Nulo:** volteo de signo por sesión (el mismo para todas las celdas y cubos de ese día; conserva la correlación cruzada), B = 100
réplicas, repitiendo TODA la selección en las cuatro variantes. p de familia de cada variante = fracción de réplicas cuyo MÁXIMO
Δ contra azar entre las cuatro lo iguala o supera (corrige por haber probado cuatro).

## Decisión (fijada antes de correr)

Una variante **PASA** si: p de familia ≤ 0,05 **y** Δ contra estática > 0 **y** R neto medio de lo elegido > 0. Si pasa más de una,
se toma la de menor p (empate: la de más ventanas).

- **Si alguna pasa:** confirmación FORWARD en el holdout (sesiones desde el 01/10/2026), con el procedimiento congelado (variante,
  k = 3, pisos): al cierre de cada mes se elige con el pasado y se opera el mes siguiente. Por el protocolo de apertura
  (`edgelab/autopilot/holdout_apertura.py`), una sola apertura, con LORD++. Nada se elige mirando el holdout.
- **Si ninguna pasa:** la selección por régimen con estos pisos no agrega sobre el azar en este universo. Se publica el MDE: el q95 del
  máximo del nulo es el Δ mínimo que se habría detectado. Un nulo sin potencia no cierra la idea (ventanas ≈ 11–13: pocas).

## Riesgos y datos faltantes

- Pocas ventanas (14 meses de datos, W ≤ 3): la potencia es baja; se reporta.
- Cubos de la misma familia en varios instrumentos o de grillas emparentadas están correlacionados; el nulo por sesión lo conserva.
- Dos cubos (PRERANGE-BASE-NQ y -YM) estaban frenados por el tamaño del kernel al escribir esto; si no llegan, se corre sin ellos.
- Las celdas de estas grillas ya se miraron en DESC y réplica; el procedimiento sólo usa el pasado de cada mes, y el nulo repite la
  misma elección, así que la búsqueda dentro de las grillas queda corregida. La elección del universo no lo está: por eso la
  confirmación es forward.
