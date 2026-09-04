# H-LIQPOOL — las implementaciones existentes, comparadas contra la nuestra

Fecha: 2026-09-03 · pedido de Nico tras cuatro iteraciones fallidas del detector:
buscar las fuentes de su captura y determinar cuál sirve más.

## Las cuatro que valen, y qué hace cada una

### PyIndicators — `internal_external_liquidity_zones`, modo `equal_hl`
[coding-kitties/PyIndicators](https://github.com/coding-kitties/PyIndicators)

- **Puntos**: pivotes, con dos longitudes — `internal_pivot_length` y
  `external_pivot_length`. Las zonas internas viven dentro del rango externo.
- **Igualdad**: `eq_tolerance_atr` — tolerancia **basada en ATR**, no en ticks.
  Sólo pivotes **consecutivos** dentro de esa tolerancia forman zona.
- **Estados**: `0 = active`, `1 = swept` (el precio tocó pero no cerró a través),
  `2 = broken` (cerró a través). **Tres estados, no dos.**
- Python puro, sin dependencias, pandas/polars.

### LuxAlgo EQH/EQL Liquidity Zones
[luxalgo.com](https://www.luxalgo.com/library/indicator/eqh-eql-liquidity-zones/)

- **Puntos**: pivotes con `Pivot Left/Right Length` **separados**.
- **Igualdad**: `Equality Threshold (%)` — porcentaje **del precio**, no ATR ni ticks.
- **Clustering**: zonas vecinas **se fusionan** («2x EQH») sumando el volumen de
  los pivotes.
- **Sweep, definido con precisión**: *«se registra sólo cuando el precio atraviesa
  el borde LEJANO de la zona — por encima del punto más alto de una EQH o por
  debajo del más bajo de una EQL»*.

### SMC-Liquidity-Hunter — `ICT_IMPLEMENTATION.md`
[GdotAiM](https://github.com/GdotAiM/SMC-Liquidity-Hunter)

- **Umbral**: `equalLevelThreshold = 0.001` — 0,1 % del precio.
- **Score por pool**: toques + peso de sesión (solape Londres/NY ×1,5) + **decaimiento
  por antigüedad**; los barridos salen del conjunto activo.
- **Mitigación**: *«un pool se neutraliza cuando el precio CIERRA más allá de su
  nivel distal»*.

### smart-money-concepts (TypeScript)
[gabrielkoerich](https://github.com/gabrielkoerich/smart-money-concepts) — EQH/EQL
con umbral y longitud configurables. Misma familia, más simple.

---

## El consenso, y en qué contradice lo que construí

| dimensión | las cuatro fuentes | lo que hice yo |
|---|---|---|
| **puntos** | pivotes con longitud izq/der configurable | **la mecha de cada vela** |
| **tolerancia** | **relativa**: % del precio o ATR | **fija: 1 tick** |
| **fusión** | zonas vecinas se fusionan | cadena única, sin fusión |
| **sweep** | atravesar el **borde lejano**; *broken* = **cierre** más allá | `invalidation_ticks` desde el nivel |
| **estados** | 3 (active / swept / broken) | 2 (touched / swept) |
| **score** | toques + recencia + sesión | sólo cuento `n_pivots` |
| **forma** | **horizontal** (EQH/EQL) | escalera con deriva |

Tres de esas diferencias son errores míos, y una es información nueva sobre tu idea.

### 1. La tolerancia fija en ticks es el error de fondo

Todas usan tolerancia **relativa**. Con ZB a 108 y 0,1 % de LuxAlgo/GdotAiM, la
tolerancia es **≈ 3,5 ticks**, no 1. Mi `touch_tolerance_ticks = 1` es entre tres
y cuatro veces más estricto que cualquier implementación de referencia — y eso
solo explica buena parte de que el detector no una lo que vos unís a ojo.

### 2. El sweep está mal definido de mi lado

«Atravesar el borde **lejano**» y «**cerrar** más allá del nivel distal» son
criterios precisos, y distinguen **mecha** de **cierre**. Yo uso un único
`invalidation_ticks` desde el nivel, que mezcla las dos cosas. Los tres estados de
PyIndicators —activa / barrida por mecha / rota por cierre— son la distinción
correcta, y encima es **justo la que la literatura pide**: mecha a través = cascada
de stops sin aceptación; cierre a través = el nivel dejó de existir.

### 3. Volver a pivotes, pero cortos

Las cuatro usan pivotes. Tu corrección —«un punto es la mecha de una vela»— y esto
se reconcilian con **longitud de pivote 1 o 2**, que captura casi todos los
extremos locales sin quedarse con un puñado disperso como pasaba con 3.

### 4. Y algo que confirma tu idea

**El score por toques + recencia de GdotAiM coincide con lo que mide el paper
académico** que ya teníamos (arXiv 2101.07410): más toques previos ⇒ más
probabilidad de rebote, y el efecto decae con el tiempo. Práctica y literatura
llegaron a lo mismo por caminos distintos. Eso es lo más sólido de todo el
conjunto y hay que registrarlo por zona.

### 5. La escalera es tuya, no de la literatura

**Ninguna de las cuatro detecta una escalera con pendiente.** Todas hacen EQH/EQL
**horizontal**. Dos lecturas posibles, y no las voy a decidir por vos otra vez:

- **(a)** lo que marcás es EQH/EQL horizontal, y los «escalones» que yo veía caen
  todos dentro de una tolerancia de ~3,5 ticks. Es lo más probable viendo tu
  último ejemplo, que es una línea **plana** uniendo dos grupos;
- **(b)** la escalera con pendiente suave es un objeto **tuyo**, distinto del
  estándar. Si es así, vale la pena — pero es una extensión, no el objeto base.

## Cuál sirve más

**Para EdgeLab: PyIndicators.** Es Python puro sin dependencias, tiene el modo
`equal_hl` explícito, tolerancia por ATR, los tres estados y la separación
interna/externa. Es lo más cercano a un módulo reutilizable en el pipeline, y se
puede espejar en el `.cs` sin ambigüedad.

**Para el `.cs`: la especificación de LuxAlgo.** Su definición de sweep —borde
lejano— y la fusión de zonas vecinas son las dos piezas que mi implementación no
tiene y que están descritas con precisión suficiente para portarlas.

**Para el registro por zona: el score de GdotAiM**, porque coincide con la
evidencia académica.

## Qué haría, concreto

1. **Tolerancia relativa** (`eq_tolerance_pct` ≈ 0,1 %, o ATR) en vez de ticks fijos.
2. **Pivotes con longitud izq/der configurable**, default 1–2, no la mecha de cada vela.
3. **Tres estados** con la definición correcta: mecha a través = `SWEPT`, cierre a
   través del borde lejano = `BROKEN`.
4. **Fusión de zonas vecinas**, con conteo de pivotes acumulado.
5. **Score por zona**: toques + antigüedad, para poder estratificar después.
6. **La escalera queda como modo opcional**, no como el objeto base — salvo que
   confirmes que (b) es lo que buscás.

## Aporte al referente

Cuatro iteraciones fallidas se explican por tres decisiones concretas y
verificables contra implementaciones de referencia —tolerancia fija, sweep mal
definido, puntos equivocados— en vez de por una diferencia de criterio
inasible. Y queda separado qué parte de la idea es estándar y qué parte es propia,
que es lo que decide si esto se porta o se inventa.
