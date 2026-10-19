# FASE 0 — población de señales de racha sobre NQ 06-26 (target-free)

Fecha: 2026-09-03 · Oráculo `data/nt8_oracles/hftimpulse_NQ0626_20260903.csv`
(1,1 GB, NQ JUN26, 5 ticks/barra, defaults 12/16/6000/3/40/48). Pre-holdout.
**sha256 `856d235f96298b8154cba6af65b2cce17a08158c18e7addc721aa54c0a94702b`** — el archivo queda fuera del árbol por tamaño, así que
el hash es su única procedencia: sin él, este acta no es reproducible.
**No se miraron retornos.** Manifiesto:
`MANIFIESTO_CAMPANA_HFTIMPULSE_SIGNALS_2026-09-03.md`.

## La población

| | |
|---|---:|
| ventanas evaluadas | 3.035.927 |
| **señales** | **6.043** |
| sesiones | 29 |
| señales por sesión (mediana) | 195 |
| alcistas / bajistas | 2.981 / 3.062 |
| desplazamiento acumulado (ticks) | mediana 69 · p10 54 · p90 98 · máx 327 |

## Tres cosas que sí sabemos ahora

### 1. No es un seguidor de tendencia diaria disfrazado

El desvío del balance direccional **dentro de cada sesión** tiene mediana 0,023 y
máximo 0,120. Si la señal fuera simplemente «el día iba para arriba», habría
sesiones con desvíos cerca de 0,5. No las hay: cada sesión tiene señales de los
dos lados en proporción pareja.

Es un descarte real y barato de la explicación alternativa más obvia.

### 2. Las señales no se pisan

Separación mínima entre señales consecutivas: **36 barras**, con `WindowBars = 12`.
Ninguna solapada. La mediana es 293 barras. Cada señal es un evento distinto, no
la misma cosa contada varias veces.

### 3. Pero están fuertemente agrupadas por sesión — y esto cambia el cálculo

**Índice de dispersión (varianza/media) de señales por sesión: 45,9.** Un proceso
de Poisson daría 1. Las sesiones van de 59 a 470 señales. El coeficiente de
variación de los intervalos es 1,78, también por encima del 1 exponencial.

Las 6.043 señales **no son 6.043 observaciones independientes**. El régimen del
día domina, y eso hay que pagarlo en la inferencia — la enmienda G2-A1 del
proyecto ya exige bootstrap clusterizado por sesión, y este número dice por qué.

## Potencia real, con el agrupamiento pagado

Efecto de diseño `deff = 1 + (m−1)·ICC` con `m = 208` señales por sesión.
El ICC no se puede estimar sin outcomes; el rango 0,01–0,05 es el habitual en
intradiario, donde el régimen del día manda.

| ICC | deff | N efectivo | MDE Fase 2 (25 celdas) | MDE pedido completo (21.000) |
|---:|---:|---:|---:|---:|
| 0,000 | 1,00 | 6.043 | 0,051 | 0,238 |
| 0,005 | 2,04 | 2.967 | 0,072 | 0,340 |
| **0,010** | **3,07** | **1.966** | **0,089** | 0,418 |
| 0,020 | 5,15 | 1.174 | 0,115 | 0,541 |
| 0,050 | 11,37 | 532 | 0,171 | 0,804 |

Techo realista de un sistema intradiario neto de costos: **0,02–0,10**.

**Veredicto de potencia:**

- **Fase 2 (sólo SL × TP, 25 celdas): viable pero justa.** Con ICC 0,01 el MDE es
  0,089, apenas por debajo del techo. Con ICC 0,02 queda al límite y con 0,05 es
  inviable.
- **El pedido completo (21.000 celdas): inviable en todos los escenarios**, incluso
  suponiendo independencia perfecta. No es una cuestión de correrlo mejor.

## Qué sigue

La condición de corte del manifiesto era «MDE < 0,10 con el espacio podado». Se
cumple **sólo para la Fase 2**, y sólo si el ICC resulta bajo. Por eso el orden no
cambia: primero la Fase 1 (alcanzabilidad geométrica, target-free), que poda SL,
TP y retroceso sin gastar presupuesto, y recién después una Fase 2 pre-registrada
sobre lo que quede.

**Y hay que estimar el ICC en la primera corrida con outcomes**, antes de
interpretar nada: es el parámetro que decide si esta campaña puede concluir algo.

## Lo que falta y sigue abierto

1. **`burst_count` sigue siendo 3 en las 6.043 señales.** El eje «más acumulación»
   no existe en el dato. El proxy usable es `burst_displacement_ticks`, que sí
   varía (54–98 entre p10 y p90, máximo 327).
2. **Nulo de tasa**: queda pendiente comparar contra un nulo que preserve tasa y
   agrupamiento. El índice de dispersión de 45,9 ya adelanta que un nulo de
   Poisson homogéneo sería el nulo equivocado.
3. Costos propios de NQ, sin transportar de otros instrumentos.

## Cómo podría refutarse esta fase

Si el balance direccional por sesión hubiera dado desvíos grandes, la señal sería
un seguidor de tendencia y no haría falta seguir. No ocurrió. Si el agrupamiento
hubiera dado dispersión ~1, la inferencia sería mucho más simple y el MDE de la
tabla valdría tal cual. Tampoco ocurrió: hay que pagar el clustering.

## Aporte al referente

Establece, antes de gastar un solo grado de libertad, cuánto se puede detectar con
esta población: la Fase 2 es viable y el pedido completo no lo es. Y descarta con
evidencia propia la explicación alternativa más barata —que la señal siga la
tendencia del día—, que de ser cierta habría cerrado la campaña entera.
