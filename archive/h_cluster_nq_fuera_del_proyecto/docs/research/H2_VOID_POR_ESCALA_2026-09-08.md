# H2 queda ANULADA por escala — el estimador no mide lo que la hipótesis dice

> Hallazgo del 2026-09-08, disparado por una observación de Nico sobre el chart:
> *«no sé cómo se midieron los rechazos a los bordes pero el gráfico está lleno de
> ejemplos como estos»*.
> Anula: `RECHAZO_CLUSTERS_NQ_2026-09-07.md` y `RECHAZO_CLUSTERS_NQ_65S_2026-09-08.md`.
> No toca el holdout. No hay P&L involucrado.

---

## Veredicto

Los dos resultados de H2 —el **+0,035** agregado y el **−0,011** del escalón 5b— **no
son evidencia de nada**. No son un nulo: son un estimador cuya escala de operación está
fuera de la escala del fenómeno. La etiqueta correcta es **VOID POR ESCALA**, no «sin
efecto detectado».

Nico tenía razón mirando el chart, y la razón es medible.

## Las cuatro medidas que lo demuestran

Todas target-free, sobre `NQ 06-26`, sesión 2026-04-06, barras de 25 ticks —la misma
configuración con la que se corrieron las 50 sesiones.

| lo que mide el estimador | escala del estimador | escala real del objeto |
| :-- | --: | --: |
| rechazo / cruce | **4 ticks** | rango **mediano de una barra: 12 ticks** (p90: 21) |
| volatilidad para aparear | 3 bins de σ | **99,2 % de la muestra cae en un solo bin** |
| «borde» del cluster | **±1 tick** | ancho **mediano del cluster: 60 ticks** (p90: 218) |
| horizonte de resolución | 20 barras | **98,9 % resuelve en la PRIMERA barra**; mediana = 1 |

### 1. El umbral es un tercio de una barra

Con el rechazo y la penetración fijados en 4 ticks y una barra que mediana 12, los dos
umbrales caen **dentro de la misma barra siguiente**. El desenlace no describe una
reacción: describe de qué lado de una banda de 4 ticks pasó el precio en el próximo
puñado de trades.

### 2. Un cuarto de los desenlaces los decide un desempate arbitrario

**El 25,0 % de los contactos resueltos** los resuelve una barra que **abarca los dos
umbrales a la vez**. El orden intrabarra no se conoce en la serie agregada, y el código
pregunta primero por el cruce:

```python
if b["hi"] >= nivel + pene:  return "cruza"     # se evalúa primero
if b["lo"] <= nivel - retro: return "rechaza"
```

Así que **siempre devuelve `cruza`**. Es un sesgo sistemático contra el rechazo, no
ruido. Si esos mismos casos se resolvieran al revés, la tasa de rechazo pasaría de
**0,323 a 0,573**. El estadístico central del canal direccional está decidido por un
desempate en un cuarto de la muestra.

Esto es un **defecto de corrección**, independiente de la escala, y tiene arreglo
limpio: el desenlace se resuelve **sobre los ticks**, no sobre la barra agregada. La
secuencia intrabarra existe en el parquet; se estaba tirando al agregar.

### 3. El «borde» es una astilla del objeto

Un cluster vivo mide 60 ticks de mediana. Con tolerancia de ±1 tick, **6 niveles de cada
60 cuentan como borde y 54 como interior**. Lo que Nico ve —el precio llegando a la
banda y dándose vuelta— cae casi todo en la categoría `dentro`, que quedó fuera de los
dos brazos del contraste: no es tratamiento ni control, es 690.284 de 1.026.840
observaciones (67 %) que no entran en ningún lado.

### 4. La estratificación por σ no estratifica

`bordes_sigma = (0, 2, 4, ∞)` con σ mediana de 9,3 ticks: el **99,2 %** de la muestra
cae en el último bin. La covariable que debía aparear el control es, en los hechos, una
constante.

## Por qué pasó, y de qué familia es la falla

Los umbrales (`retro_ticks=4`, `penetracion_ticks=4`, `tolerancia=1`, `bordes_sigma`) se
**congelaron en el pre-registro antes de conocer la escala del objeto**. Es exactamente
la misma falla que la banda de cobertura 15–60 % que corrigió la enmienda P-72: un
parámetro elegido a ciegas sobre un objeto cuya magnitud todavía no se había medido.

La diferencia es que la banda de cobertura fallaba **ruidosamente** —ninguna
configuración pasaba, y por eso se descubrió—. Ésta falló **en silencio**: produjo
tablas llenas, N de siete cifras, MDE de 0,0214 y un contraste con signo. Un resultado
mal escalado no se ve mal.

Y explica el patrón que quedó sin explicar en los dos informes: por qué la tasa base es
~0,34 en todas las celdas, por qué los `indefinidos` son **cero** con un horizonte de 20
barras, y por qué el contraste se mueve en centésimas.

## Lo que NO se puede concluir

- **No se puede decir que la hipótesis de Nico está refutada.** No fue puesta a prueba.
- **No se puede decir que está confirmada.** Los ejemplos del chart son observación
  visual y el propio proyecto los declara inadmisibles como evidencia mientras el render
  pueda esconder objetos muertos.
- **No se puede reusar el MDE de 0,0214.** Es la potencia de una pregunta distinta.

## Lo que sigue

1. **Arreglar el desenlace sobre ticks**, eliminando el desempate. Es corrección, no
   recalibración, y vale para cualquier escala que se elija después.
2. **Re-pre-registrar la escala**, con la justificación tomada de las medidas
   target-free de arriba —rango de barra, ancho de cluster, σ local— y **no** de ningún
   resultado. Barrer la escala y publicar el landscape completo; nunca elegir la celda
   de mayor contraste.
3. **Tratar `dentro` como un objeto con su propia hipótesis.** Es el 67 % de la muestra
   y hoy no es ni tratamiento ni control.
4. Recién después, volver a correr. La corrida de 50 sesiones que estaba por lanzarse
   **se frenó**: repetir un estimador roto con más sesiones sólo angosta el intervalo
   alrededor del número equivocado.

---

**Aporte al referente:** frena una rama que iba camino a promoverse o enterrarse por un
número que no medía la hipótesis, y deja escrita la escala real del objeto —barra, σ,
ancho de cluster— que cualquier estimador futuro tiene que respetar para ser admisible.
