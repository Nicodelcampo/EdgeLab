# FASE 1 — alcanzabilidad geométrica de las señales de racha (target-free)

Fecha: 2026-09-03 · Oráculo `hftimpulse_NQ0626_20260903.csv`
sha256 `856d235f96298b8154cba6af65b2cce17a08158c18e7addc721aa54c0a94702b`
(NQ 06-26, 5 ticks/barra, pre-holdout, 3.035.927 barras, **6.043 señales**,
29 sesiones). Manifiesto: `MANIFIESTO_CAMPANA_HFTIMPULSE_SIGNALS_2026-09-03.md`.

**No se calculó P&L, ni tasa de acierto, ni expectativa.** Se midió hasta dónde
llega el precio después de cada señal, a favor y en contra.

## Veredicto

> **SIN EFECTO DIRECCIONAL DETECTADO.** La excursión a favor de la señal y la
> excursión en contra son estadísticamente indistinguibles — y lo poco que se
> separan, se separa **en contra**.

## La medición

Por cada señal, con referencia en el cierre de la barra que la disparó:
excursión **favorable** (cuánto avanza el precio en la dirección de la señal) y
**adversa** (cuánto avanza contra ella), dentro de un horizonte, cortado en la
frontera de sesión.

### Curvas de alcanzabilidad — a favor y en contra son la misma curva

Fracción de señales que alcanza cada nivel, horizonte de 300 barras:

| nivel (ticks) | a favor | en contra |
|---:|---:|---:|
| 8 | 90,7 % | 90,9 % |
| 16 | 81,8 % | 81,9 % |
| 24 | 72,9 % | 72,8 % |
| 32 | 65,1 % | 65,1 % |
| 48 | 49,9 % | 50,0 % |
| 64 | 36,0 % | 38,2 % |
| 100 | 16,4 % | 18,4 % |

Medianas: favorable 47 t, adversa 47 t. p90: 119 t contra 123 t.

### Diferencia media, con IC bootstrap clusterizado por sesión

29 sesiones como clusters, 4.000 remuestreos (método que exige la enmienda G2-A1
del proyecto, justificado por la dispersión 45,9 medida en la Fase 0):

| horizonte | media fav−adv | IC 95 % | efecto | fav>adv |
|---:|---:|---|---:|---:|
| 10 | −0,52 t | [−0,95, −0,11] * | −0,036 | 49,5 % |
| 20 | −0,75 t | [−1,33, −0,17] * | −0,036 | 49,0 % |
| 50 | −1,28 t | [−2,25, −0,33] * | −0,038 | 49,6 % |
| 100 | −1,70 t | [−2,87, −0,60] * | −0,036 | 49,7 % |
| 300 | −2,03 t | [−3,91, −0,24] * | −0,024 | 49,9 % |
| 600 | −2,44 t | [−5,14, +0,26] | −0,020 | 49,5 % |
| 1200 | −1,78 t | [−5,26, +1,77] | −0,010 | 50,2 % |

`*` = el IC no cruza cero.

**MDE de esta medición**: semiancho del IC a 300 barras = 1,8 ticks = **0,022
desvíos**. La medición tenía precisión de sobra; el efecto que encontró es real y
es chico, y va en contra.

### No mejora con la intensidad

Partiendo por cuartil de `burst_displacement_ticks` (el único proxy de intensidad
que varía, porque `burst_count` es 3 en las 6.043), horizonte 300:

| cuartil | n | fav mediana | adv mediana | diferencia |
|---|---:|---:|---:|---:|
| Q1 más débil | 1.597 | 38 t | 41 t | −3 |
| Q2 | 1.512 | 46 t | 44 t | +2 |
| Q3 | 1.442 | 52 t | 50 t | +2 |
| Q4 más fuerte | 1.492 | 60 t | 62 t | −2 |

Sin patrón. Las rachas más fuertes no extienden más a favor.

## Lectura, con sus límites

Lo que **sí** quedó establecido: la dirección de la señal no informa sobre qué
lado del precio se extiende más, en ningún horizonte entre 10 y 1.200 barras, con
un MDE de 0,022 desvíos. La consistencia del signo negativo desde la barra 1 es
lo que hace creíble el resultado: si fuera ruido, el signo se daría vuelta.

Lo que **no** queda refutado, y hay que decirlo: la excursión máxima **no es una
regla de trading**. Una estrategia sale antes, y podría vivir del *orden* en que
se tocan los niveles aunque las excursiones máximas sean simétricas. Eso es la
carrera de primer paso, y es Fase 2.

**Una explicación mecánica plausible del signo negativo**: la señal dispara
después de un movimiento acumulado de 69 ticks de mediana, o sea en un extremo
local. Medir desde el cierre de esa barra incorpora el rebote bid-ask. Parte de
los −0,52 ticks del horizonte 10 puede ser exactamente eso, y no una propiedad
del mercado.

## Recomendación

**No correr la Fase 2 como barrido direccional.** La premisa de la campaña —que
la racha marca una dirección— tiene evidencia en contra, medida con buena
precisión y con el clustering pagado. Sumado al MDE de la Fase 0, un barrido de
21.000 celdas sobre esta población sería data snooping con el resultado ya
conocido.

Tres caminos, y el orden de preferencia es ese:

1. **Cerrar la línea** como `SIN_EFECTO_DIRECCIONAL_DETECTADO`, con su MDE
   publicado. Es el resultado honesto de hoy.
2. **Probar sólo la carrera de primer paso** (qué nivel se toca antes), una
   pregunta única pre-registrada, con la multiplicidad declarada y prior bajo.
   Requiere aprobación del STOP.
3. **Reformular la hipótesis al revés** (la señal marca agotamiento, no
   continuación). Es una hipótesis nueva: probarla sobre los mismos datos que
   acaban de sugerirla es exactamente el snooping que las reglas prohíben sin
   contabilizarlo. Si se hace, se hace con presupuesto propio y holdout aparte.

## Lo que esta fase NO midió

- **Canal no direccional.** El proyecto exige medir el efecto en los dos canales.
  Acá está el direccional; falta comparar la *magnitud* de excursión contra un
  nulo que preserve tasa y agrupamiento. Un efecto bidireccional real puede
  promediar cero en el canal direccional — aunque las curvas de alcanzabilidad
  casi idénticas hacen poco probable que se esconda algo grande ahí.
- **Retroceso de entrada.** No se midió porque el eje sólo tiene sentido si hay
  dirección que capturar.
- **Costos.** Ninguno. La medición es de geometría pura.

## Cómo podría refutarse este resultado

Si la carrera de primer paso mostrara asimetría fuerte pese a excursiones máximas
simétricas —es decir, si lo favorable llegara sistemáticamente *antes*—, este
resultado sería insuficiente y no refutaría la campaña. Es una posibilidad real y
por eso el camino 2 queda abierto en vez de cerrado.

## Aporte al referente

Una campaña de 21.000 combinaciones sobre P&L quedó detenida antes de gastar un
solo grado de libertad, por una medición geométrica que costó minutos y mostró
que la premisa direccional no se sostiene. El progreso es negativo pero real:
se descartó un candidato con evidencia, en vez de dejarlo abierto o de encontrarle
una celda ganadora por azar.
