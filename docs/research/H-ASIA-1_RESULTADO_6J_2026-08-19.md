# H-ASIA-1 — resultado target-free sobre 6J

- **Fecha:** 2026-08-19 · **Instrumento:** 6J · **222 sesiones** · holdout excluido
- **Artefacto:** `docs/research/costo_pasaje_asia_6J_2026-08-19.json`
- **Protocolo:** `docs/research/H-ASIA-1_COSTO_DE_PASAJE_PROTOCOLO.md` (P-54)
- **Estado:** `HYPOTHESIS_NOT_SUPPORTED` · el efecto aparente **se explica por geometría**

---

## 1. La hipótesis: **no sostenida**

> «cuanto más rompió el precio —por tiempo, por volumen, por ticks— el camino a través
> del último precio de Asia ofrece menos resistencia»

Percentil de dwell de `asia_close` entre **todos** los niveles de su propio rango, por
tercil de magnitud de ruptura. La hipótesis predice una tendencia **decreciente**.

| magnitud | k=1 | k=2 | k=3 | k=5 |
|---|---|---|---|---|
| **M1 tiempo** | 0,675 → 0,700 → 0,658 | 0,667 → 0,667 → 0,671 | 0,658 → 0,692 → 0,671 | 0,684 → 0,706 → 0,686 |
| **M2 volumen** | 0,701 → 0,582 → 0,677 | 0,697 → 0,560 → 0,675 | 0,692 → 0,600 → 0,675 | 0,711 → 0,615 → 0,686 |
| **M3 ticks** | 0,656 → 0,749 → 0,644 | 0,655 → 0,745 → 0,659 | 0,659 → 0,739 → 0,653 | 0,676 → 0,752 → 0,686 |

**Doce lecturas independientes. Ninguna es monótona decreciente.** Son planas o en «V»,
que es la forma del ruido. Las diferencias máximas (~9 pp) están **muy por debajo del
MDE de 23,3 pp** con 74 sesiones por tercil.

El chequeo que se construyó para descartar el confundidor de posición **pasa**: la
correlación entre magnitud y posición en el rango es **−0,01 a −0,02**. La posición no
sesga la tendencia; simplemente no hay tendencia.

## 2. El hallazgo aparente — y por qué no lo es

El nivel absoluto sí llamaba la atención:

- percentil de `asia_close` **> 0,5 en 150 de 222 sesiones = 67,6 %** (nulo 50 %, **z = 5,2**)
- mediana del percentil: **0,667**
- contraste contra el espejo: **+0,24** consistente en todos los terciles y todas las bandas

Leído sin control, eso dice «`asia_close` retiene el precio más que un nivel cualquiera
de su rango». Con z = 5,2 parece sólido.

**No lo es.** El espejo estaba emparejado por distancia al **punto medio**, pero
**anti-emparejado** por distancia al **extremo roto** — reflejar invierte el lado, por
construcción.

Y esa es la dimensión que manda: el viaje de vuelta **entra al rango por el extremo
roto**, así que los niveles cercanos a ese extremo se pisan primero y más.

| | mediana de distancia normalizada al extremo roto |
|---|---|
| `asia_close` | **0,276** |
| espejo | **0,724** |

**`asia_close` está más cerca del extremo roto en el 76,6 % de las sesiones.** Tiene
sentido: el precio cierra Asia cerca de un lado y después rompe **ese** lado.

Al condicionar por esa distancia, el efecto desaparece:

| subconjunto | n | percentil | espejo | contraste |
|---|---|---|---|---|
| `asia_close` **cerca** del extremo roto | 170 | 0,709 | 0,414 | **+0,295** |
| `asia_close` **lejos** del extremo roto | **52** | **0,472** | 0,531 | **−0,059** |

Cuando `asia_close` no está del lado del rompimiento, su percentil es **0,472** —
indistinguible del nulo 0,5— y el contraste contra el espejo es **−0,059**, o sea
cruza cero.

**El +0,24 era la geometría del viaje de vuelta, no una propiedad del nivel.**

*Límite honesto:* el subconjunto «lejos» tiene n = 52 (MDE ≈ 27,8 pp). Que dé 0,472 es
**consistente con el nulo**, no una demostración de que no hay nada.

## 3. El error de diseño, y cuál era el control correcto

El control dentro de la sesión —percentil entre todos los niveles del mismo rango,
mismo viaje, mismos ticks— **sí resolvió** el confundidor de volatilidad que el
protocolo había declarado. Ése funcionó.

El que falló fue el **espejo**: se eligió por emparejar posición respecto del centro, y
resultó estar sistemáticamente del lado equivocado del rompimiento.

**El control correcto es condicionar por distancia al extremo roto**: comparar
`asia_close` contra niveles a distancia similar del extremo que se rompió, o
equivalentemente mirar el residuo de `dwell` tras regresar sobre esa distancia. Queda
escrito para la v2, si la hay.

Es la tercera vez que el proyecto tropieza con lo mismo (F2.9, y ahora acá): **un
control que parece emparejado no lo está en la dimensión que manda.**

## 4. Nota de integridad: la primera corrida fue inválida

La primera ejecución midió la ventana posterior del **día equivocado** — 03:00–17:00 del
día `d` en vez del `d+1`, o sea **cinco horas antes de que la ventana de Asia
empezara**. Detectaba «rupturas» sobre ticks anteriores al rango.

Verificado contra los datos (`6J_12-25`, 2025-10-05): ASIA `18:00 → 02:59` (51.405
ticks) · POST mal `13:40 → 15:50` (2 ticks) · POST bien `03:00 → 16:59` (66.415 ticks).

El síntoma estaba a la vista —**52 descartes por `sin_post` sobre 243 días**— y se leyó
como dato en vez de como alarma. Tras el fix: 222 sesiones censadas, 2 descartes.

**Ningún número de esa corrida se publicó como resultado.**

## 5. Lo que NO se midió

Si el precio atraviesa o rebota (eso es dirección). MFE / MAE / retornos / P&L.
Cualquier cosa posterior a que la banda se resuelva. Todo eso espera manifiesto + STOP.
