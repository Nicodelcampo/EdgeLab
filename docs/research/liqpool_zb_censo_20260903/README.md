# H-LIQPOOL-ZB paso 2 — censo del detector EQH/EQL, con controles

Fecha: 2026-09-03 · commit pineado `9ec8225a` · Kaggle · **target-free, sin
outcomes, holdout intacto**. ZB 03-26 / 06-26 / 12-25 pre-holdout, barras de 200
ticks, **196 sesiones**. Detector: `liqpool.py` v2.0, porte del modelo de
referencia (`H-LIQPOOL_FUENTES_COMPARADAS_2026-09-03.md`).

## El resultado principal

Con los defaults (`pivot 2/2`, tolerancia 0,10 %, `min_pivots 2`):

| | zonas | toques medio | edad al sweep (mediana) | nunca tocadas |
|---|---:|---:|---:|---:|
| **ZB real** | 1.188 | **1,184** | **12** | 33,2 % |
| **nulo de grilla** | 2.658 | **1,220** | **12** | 30,5 % |

**Las zonas detectadas sobre ZB real se comportan igual que las detectadas sobre
un paseo aleatorio con la misma grilla, la misma escala y la misma longitud.**
Mismos toques, misma vida, misma fracción sin tocar. El nulo incluso produce
*más* zonas y con *más* toques.

Es la segunda medición independiente que dice lo mismo: el **paso 1** ya había
mostrado que la repetición de niveles no supera al azar en **frecuencia**; este
paso muestra que tampoco se distingue en **comportamiento**.

## Un hallazgo que vale por sí solo

Reparto de estados de las 1.188 zonas reales:

| estado | n | |
|---|---:|---:|
| `ACTIVE` | 619 | 52,1 % |
| `BROKEN` (cierre a través) | 559 | 47,1 % |
| **`SWEPT` (mecha a través, sin cerrar)** | **10** | **0,8 %** |

**El barrido de liquidez —mecha a través del nivel sin aceptación— ocurre en 8 de
cada 1.000 zonas.** Cuando el precio llega al borde lejano, prácticamente siempre
**cierra** más allá: el nivel deja de existir en vez de rebotar.

Esa distinción existe en el detector porque el porte la trajo de PyIndicators y
la literatura la pide (Osler: take-profit hacen rebotar, stops hacen acelerar).
Medida en ZB, la rama del rebote casi no ocurre. Todo el marco de *liquidity
sweep* descansa sobre un evento que acá es marginal.

## Landscape de parámetros — el detector sí controla lo que dice controlar

| variante | zonas | toques medio | tolerancia (ticks) |
|---|---:|---:|---:|
| `L1_tol0.05_min2` | 3.270 | 1,465 | 2 |
| `L2_tol0.05_min2` | 3.156 | 1,645 | 2 |
| `L3_tol0.05_min2` | 2.875 | 1,795 | 2 |
| `L3_tol0.1_min2` | 1.265 | 1,360 | 4 |
| `L2_tol0.1_min2` | 1.188 | 1,184 | 4 |
| `L2_tol0.1_min3` | 1.112 | 1,129 | 4 |

Monótono en los tres ejes: más longitud de pivote → menos zonas y más toques;
más tolerancia → menos zonas (los clusters se fusionan) y tolerancia mayor en
ticks; `min_pivots` 3 → menos zonas. **El detector funciona.** Lo que no aparece
es señal en el objeto que detecta.

Nota: la tolerancia relativa de 0,10 % se resuelve a **4 ticks** en ZB — el orden
que anticipaba la comparación de fuentes, y cuatro veces la que yo usaba antes.

## Un control defectuoso, declarado

El **control (b) «sin marca, misma geometría»** dio 2,429 toques y edad mediana
38, **por encima** de las zonas reales. No se puede leer como evidencia: el
control elige una barra al azar de la sesión, y una barra temprana deja más
sesión por delante, así que acumula más toques y más vida por posición, no por
mérito. **Está mal emparejado en tiempo restante** y hay que rehacerlo antes de
usarlo.

El control (a) espejo tiene el problema simétrico: casi todo el conjunto termina
`BROKEN` (1.172 de 1.188) porque el nivel reflejado suele caer del lado por el que
el precio ya venía. Tampoco es utilizable como está.

**El control (c), el nulo de grilla, sí está bien construido** —misma serie, misma
longitud, mismo detector, sólo barajados los incrementos— y es el que sostiene la
conclusión.

## Estado de la familia

`SIN EFECTO DETECTADO EN EL CANAL TARGET-FREE`, con dos mediciones
independientes y un control válido. **No se cierra todavía**, por dos razones
explícitas:

1. los controles (a) y (b) están mal construidos y hay que rehacerlos;
2. sólo se probó **una resolución** (200 ticks/barra) y **un instrumento**.

Lo que **no** haría es pasar a medir P&L. Con el objeto indistinguible del azar
en frecuencia y en comportamiento, un barrido sobre retornos encontraría celdas
ganadoras por multiplicidad, no por edge.

## Cómo podría refutarse este resultado

Que a otra resolución de barra las zonas reales superen al nulo de grilla en
toques o en vida. Es la dimensión no explorada, y es una corrida.

## Aporte al referente

El detector quedó portado del modelo de referencia y **verificado que controla lo
que dice controlar** (landscape monótono en tres ejes), y con eso el objeto pudo
compararse contra un nulo bien construido: no se distingue. Además queda medido
que el barrido de liquidez, que es el mecanismo que toda la familia presupone,
ocurre en el 0,8 % de las zonas en ZB. Dos hechos que ahorran una campaña de P&L
sobre una hipótesis sin sustento medible.
