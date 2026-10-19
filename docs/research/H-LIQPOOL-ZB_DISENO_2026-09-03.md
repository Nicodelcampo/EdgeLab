# H-LIQPOOL-ZB — cómo hay que construir el detector de acumulación de máximos/mínimos

Fecha: 2026-09-03 · **Registro de familia nueva** (regla de CLAUDE.md: cada
familia se registra antes de estudiarse, con ledger propio; no se transportan
resultados, poblaciones, costos ni presupuesto de multiplicidad desde BigTrap2,
HFTZones, aVolCluster ni ninguna otra).

Instrumento: **ZB** (30-Year T-Bond). `tick_size = 1/32 = 0,03125`,
`tick_value = USD 31,25` (`edgelab/instruments.py`).

Propuesta de Nico: secuencias de máximos o mínimos consecutivos —lo que
informalmente se llama *acumulación de liquidez*— **atraen al precio** bajo cierto
contexto. Sub-tipos que él distingue: la **microzona** (picos creados muy cerca en
el tiempo) y la zona donde los picos están cerca en precio pero **lejos en tiempo
y con recorrido sustancial entre medio**.

Antes de escribir una línea de detector, tres cosas que cambian el diseño.

---

## 1. El proyecto ya probó una hipótesis de imán, y la refutó

`docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md`, estado
`BIGTRAP2_MAGNET_LINE_CLOSED`. Sobre 6E, 201 sesiones, 15.947 zonas:

- **F2.7** encontró una carrera real: Δ ≈ +0,048, IC [+0,031, +0,066]. La zona
  real le ganaba a su espejo, y las dos estaban a la **misma distancia** del
  close, así que «gana porque está más cerca» quedaba descartado.
- **F2.8 la mató**: un **control sin zona, con la misma geometría, dio casi lo
  mismo**. El contraste cruzó cero. Y el efecto no moría con la distancia, que es
  lo contrario de lo que hace un imán.
- **F2.9** remató: una vela extrema genérica (`S1`, +0,038) sellaba mejor que la
  creadora del indicador (`K0`, +0,021), y `K0 ≈ N0` (no-creadora emparejada).

**La lección operativa, y es la más importante de este documento:** medir que el
precio vuelve a un nivel marcado **no dice nada** hasta que se compara contra un
nivel de control con la misma geometría y sin la marca. El precio vuelve a niveles
cercanos porque el precio se mueve, no porque el nivel sea especial.

Ese control **no es un refinamiento posterior: es parte del diseño desde el día
cero**, o esta familia repite exactamente la misma muerte.

---

## 2. Las capturas son un generador de hipótesis, no evidencia

Las tres capturas muestran líneas trazadas sobre secuencias de picos, en lugares
donde el precio efectivamente volvió. Eso es **selección por resultado**: el ojo
elige los casos que funcionaron.

CLAUDE.md ya lo prohíbe como evidencia — *«lo que se ve reaccionar puede ser el
sesgo de supervivencia de la regla de dibujo, no el mercado»* — y exige censo
as-of que incluya **las zonas que no funcionaron**.

No es una objeción a la idea. Es la razón por la que hace falta un detector
mecánico: para enumerar **todas** las secuencias, incluidas las que el ojo
descarta sin registrarlas.

---

## 3. ZB tiene un problema propio que ningún otro instrumento del proyecto tiene

El tick de ZB es **1/32 de punto**, y el rango de una sesión de ZB se cuenta en
**decenas de ticks**, no en cientos como NQ o ES.

Si una sesión recorre, digamos, 40 ticks distintos, la probabilidad de que dos
máximos separados en el tiempo caigan **exactamente en el mismo precio** es alta
**por pura discretización**, sin que nadie haya dejado liquidez ahí.

**Consecuencia para el nulo:** el nulo correcto **no** es «niveles al azar
uniformes». Tiene que preservar la **granularidad de la grilla de precios y la
distribución de recorrido de la sesión**. Un nulo que ignore la discretización va
a decir que hay acumulación de liquidez donde sólo hay pocos precios posibles.

Esto es lo primero que hay que medir, y es barato: cuántos precios distintos toca
una sesión de ZB, y con qué frecuencia aparecen máximos repetidos **por azar**
dado ese grid.

---

## 4. El espacio de eventos, enumerado antes de congelar población

Regla de CLAUDE.md: ninguna población se congela sin enumerar por escrito el
espacio del que se extrae. Para esta familia:

| familia | qué sería | comentario |
|---|---|---|
| **creación** | el instante en que el k-ésimo pico completa la secuencia | evento; N chico |
| **aproximación** | el precio entra en un radio de la zona sin tocarla | estado |
| **primer toque** | el precio alcanza el nivel por primera vez | evento; es la que el ojo ve |
| **toque n-ésimo** | revisitas posteriores | evento |
| **invalidación** | el precio atraviesa y se aleja | evento |
| **expiración** | la zona muere por tiempo sin ser tocada | evento; **es la que el ojo nunca registra** |
| **confluencia** | coincide con otra zona | condición |
| **estado continuo** | en cada barra: ¿hay zona sin tocar arriba/abajo, y a qué distancia? | **estado** |

**Recomendación: la población primaria debe ser el ESTADO, no el evento.** La
hipótesis dice «atrae», que es una afirmación sobre la deriva del precio mientras
la zona existe — no sobre qué pasa cuando ya la tocó. Además el estado vale en
cada barra y tiene mucha más potencia, y la Fase 0 de la campaña anterior mostró
lo caro que sale trabajar con poblaciones de eventos agrupadas por sesión.

El primer toque como población es justamente la que introduce el sesgo del ojo:
condiciona a que la zona haya sido tocada.

---

## 5. El detector propuesto, con sus parámetros

Todo entero, en ticks, siguiendo el contrato de paridad
(`PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`): sin mediana, sin percentil
histórico, sin reloj entre ticks, empates deterministas.

### Paso 1 — pivotes

Un **pivote alto** en la barra `i` es un máximo que domina estrictamente a `K`
barras a cada lado. Análogo para el bajo.

| parámetro | qué controla |
|---|---|
| `PivotStrength` (K) | cuántas barras a cada lado; sube K → menos pivotes, más significativos |

### Paso 2 — agrupamiento de pivotes en zona

Se agrupan pivotes del mismo tipo cuya diferencia de precio no supere una
tolerancia.

| parámetro | qué controla |
|---|---|
| `LevelToleranceTicks` | cuánto pueden diferir dos picos y seguir siendo «el mismo nivel». **Con el tick de ZB, 0 y 1 son universos distintos** |
| `MinPivots` | cuántos picos hacen una zona (2 = par, 3+ = acumulación) |

### Paso 3 — los dos sub-tipos que Nico distingue

No son dos algoritmos: son **dos regiones del mismo espacio de parámetros**, y
por eso conviene medirlos con los mismos ejes en vez de con detectores separados.

| parámetro | microzona | zona separada |
|---|---|---|
| `SpanBars` (barras entre el primer y último pico) | bajo | alto |
| `ExcursionTicks` (recorrido máximo del precio entre picos) | bajo | alto |

Esos dos ejes son exactamente lo que él describió como *«el precio se movió varios
ticks y pasó bastante tiempo entre ellos»*. **Se registran siempre y se usan para
estratificar, no para filtrar** — filtrar de entrada congela una población sin
haber visto el landscape.

### Paso 4 — vida de la zona

| parámetro | qué controla |
|---|---|
| `ZoneHeightTicks` | grosor alrededor del nivel |
| `InvalidationTicks` | cuánto tiene que atravesar el precio para matarla |
| `MaxAgeBars` | expiración |

**La zona NO se borra al ser tocada.** Se marca como tocada y sigue en el censo.
Borrarla es lo que produce el sesgo de supervivencia que CLAUDE.md prohíbe.

---

## 6. El control, que es la parte que decide

Por cada zona detectada, se construyen controles **emparejados**:

1. **Espejo**: el nivel reflejado respecto del precio de referencia — misma
   distancia, lado opuesto. Es el control que usó F2.7.
2. **Sin marca, misma geometría**: un nivel a la misma distancia y con la misma
   antigüedad, pero donde **no** hay acumulación de pivotes. Es el control que
   **mató** la hipótesis anterior, así que va desde el principio.
3. **Nulo de grid**: niveles generados preservando la discretización y el
   recorrido de la sesión, para separar «acumulación real» de «pocos precios
   posibles» (punto 3).

Si la zona real no le gana a los tres, no hay hipótesis.

---

## 7. Orden de trabajo propuesto

1. **Censo target-free de la grilla de ZB.** Precios distintos por sesión, tasa de
   máximos repetidos observada contra la esperada por discretización. Decide si el
   objeto siquiera se distingue del azar. **Es el primer test y puede cerrar todo.**
2. **Detector + censo completo**, con las zonas muertas incluidas, y el landscape
   de `SpanBars` × `ExcursionTicks` × `MinPivots` publicado entero.
3. **Estado continuo con los tres controles**: ¿el precio deriva hacia la zona más
   que hacia sus controles emparejados?
4. Sólo si (3) sobrevive: P&L, con manifiesto y STOP.

## Cómo podría refutarse esta familia, en cada paso

- Si la tasa de niveles repetidos de ZB no supera al nulo de grid, la
  «acumulación de liquidez» es un artefacto de la discretización del tick.
- Si el estado continuo no le gana al control **sin marca con la misma
  geometría**, se repite exactamente F2.8 y la familia muere ahí.
- Si el efecto no decae con la distancia a la zona, no es atracción — es otra cosa
  que sucede en paralelo. Ese fue el diagnóstico de F2.8.

## Aporte al referente

Registra una familia nueva con su ledger propio, y le pone desde el inicio el
control que mató a la anterior — en vez de descubrir dentro de tres semanas que se
midió que el precio vuelve a niveles cercanos porque el precio se mueve.
