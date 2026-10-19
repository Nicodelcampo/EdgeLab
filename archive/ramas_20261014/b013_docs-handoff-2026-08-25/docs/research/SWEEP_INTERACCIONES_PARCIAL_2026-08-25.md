# Interacciones — resultado **PARCIAL**, 13 de 48 · GC 02-26

- **Fecha:** 2026-08-25 · **Corrida:** `sweep_7fbab53_GC02-26`, parciales bajo `7fbab53`
- **Estado:** 64 de 99 configs (51 OAT + **13 interacciones**) · **corrida interrumpida por apagado**
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · `promotion_eligible=false` · **nada declara edge**

> Los parciales pesan 176 MB y no se commitean. Acá va **la información que contienen**.

---

## 1. El resultado: los efectos **no se componen**

Para cada configuración de interacción se predijo el conteo de zonas suponiendo que los
ejes son independientes —multiplicando los ratios medidos en el barrido de un eje por
vez— y se comparó contra lo medido.

| config | real | predicho | real / predicho |
|---|---:|---:|---:|
| `bt2a_b1025cb1aad5c` | 147 | 0,1 | **1.537×** |
| `bt2a_ceb4b5b39b6fe` | 361 | 0,3 | **1.155×** |
| `bt2a_c55d0aad62909` | 8 | 0,0 | **617×** |
| `bt2a_c748fe7fe9c6c` | **18.422** | 60,8 | **303×** |
| `bt2a_c766d781132eb` | 7 | 0,7 | 10,6× |
| `bt2a_1db76d2785831` | 35 | 0,0 | **∞** |
| `bt2a_d61b11c99601a` | 259 | 0,0 | **∞** |
| `bt2a_5cf50855f25ef` | **0** | 3,6 | **0×** |

La independencia falla en **las dos direcciones**: hay combinaciones que producen
**cientos de veces más** zonas de lo predicho, y una que produce **cero** cuando se
esperaban casi cuatro.

> **El barrido de un eje por vez no predice combinaciones.** Toda afirmación de la forma
> «el parámetro X tiene efecto Y» derivada del OAT es válida **sólo en el punto del
> headline**, no como propiedad del parámetro.

---

## 2. El mecanismo, aislado

El efecto más fuerte del OAT era: **`MinDeltaFilter ≥ 50` deja CERO zonas.** Parecía un
interruptor absoluto. En combinación, no lo es:

| config | `MinDeltaFilter` | `TicksPerRow` | `TapeWindowTicks` | **`MinStackedRows`** | zonas |
|---|---:|---:|---:|---:|---:|
| `531b88973b16a` | 50 | 1 | 25 | **2** | **0** |
| `1dbe91bafa9d9` | 100 | 1 | 25 | **2** | **0** |
| `c200ba2306729` | 50 | 2 | 5 | **2** | **0** |
| `b604c78600c21` | 100 | 1 | 100 | **2** | **0** |
| `7fcfb6e5982be` | 50 | 2 | 50 | **3** | **0** |
| `7737605e75a22` | 50 | 4 | 15 | **4** | **0** |
| `1db76d2785831` | 100 | 4 | 10 | **1** | **35** |
| `d61b11c99601a` | 50 | 1 | 50 | **1** | **259** |

**Separación perfecta por `MinStackedRows`.** Con 1 sobrevive; con 2 o más, muere. Los
otros ejes no discriminan: hay muertos con `TicksPerRow=4` y vivos con `TicksPerRow=1`.

### Por qué

`MinDeltaFilter` descarta filas cuyo desbalance `|ask − bid|` es chico. Eso deja el
libro de filas **ralo y salpicado**. `MinStackedRows` exige una **corrida contigua** de
filas sobrevivientes: con el umbral en 2, casi nunca hay dos filas vecinas que pasen; con
1, una sola alcanza.

**No es un efecto estadístico: es geométrico.** Un filtro rompe la contigüidad que el otro
exige.

> Corrección de método: mi primera hipótesis fue que `TicksPerRow` rescataba, agrupando
> ticks en filas más gruesas. Los datos la descartaron en el mismo comando —hay un muerto
> con `TicksPerRow=4` y un vivo con `TicksPerRow=1`—. La separación por `MinStackedRows`
> es exacta en los ocho casos.

---

## 3. La combinación que explota

`bt2a_c748fe7fe9c6c` produce **18.422 zonas** contra las 3.878 del headline: **4,75×**,
más del doble que el máximo de cualquier eje individual (`MinStackedRows=1`, +124 %).

Predicho por independencia: **60,8**. Error de **303×**.

Es el mismo mecanismo al revés: aflojar varios filtros a la vez no suma sus efectos, los
**multiplica de forma no lineal** porque cada uno deja de recortar el material del que
depende el siguiente.

---

## 4. Consecuencia para la campaña

**Lo que sigue en pie del barrido OAT:**

- La clasificación en tres familias —creación, ciclo de vida, no-op— **no cambia**: es
  sobre qué *tipo* de efecto tiene cada eje, no sobre su magnitud.
- Los tres no-op reales siguen siendo no-op.
- El defecto de `MinExportVolume` sigue siendo un defecto.

**Lo que hay que leer con cuidado:**

- Las **magnitudes** del OAT valen en el punto del headline. `MinDeltaFilter` no es «un
  interruptor»: es un interruptor **cuando `MinStackedRows ≥ 2`**.
- Cualquier futuro descarte de un eje por «bajo efecto» necesita al menos una interacción
  que lo confirme. `AbsorptionLookback` da ±1,1 % en OAT; **nadie midió qué hace
  combinado**.

---

## 5. Lo que NO se puede leer de acá

- **13 de 48 interacciones.** El diseño no está completo.
- **Un solo contrato**, GC 02-26, 39 sesiones reportables.
- **Ningún ganador.** No se miraron outcomes y no se pueden mirar. Que una combinación dé
  18.422 zonas **no dice que sea mejor** — podría ser el punto de máximo ruido.
- La corrida se **interrumpió por apagado**, no por completarse.

---

## Aporte al referente

El censo se diseñó para mapear qué parámetros mueven la población, y la etapa de un eje
por vez ya había dado ese mapa. Las primeras 13 interacciones muestran que **ese mapa no
se puede extrapolar**: predecir combinaciones desde efectos individuales falla por
factores de hasta 1.537×, en las dos direcciones. Queda además aislado un mecanismo
concreto y verificable —un filtro que rompe la contigüidad que otro exige— que explica el
caso más extremo sin recurrir a estadística.

## Nota de método

La predicción por independencia no se hizo esperando que funcionara: se hizo **para tener
contra qué contrastar**. Sin ese predicho, los conteos reales serían una lista de números
sin interpretación, y la no-separabilidad del espacio —que es el hallazgo— habría quedado
invisible.
