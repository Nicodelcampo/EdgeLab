# H2 — ¿el precio rechaza los extremos de un cluster? Primer resultado

> **Target-free.** Sin P&L, sin entrada ni salida ni costo: sólo la geometría del
> recorrido posterior a un contacto.
> Reproducción: `tools/rechazo_clusters_nq.py --sesiones 15`.
> Estimador: `edgelab/research/cluster_rejection.py` (14 tests).
> **Alcance: 15 sesiones de `NQ 06-26`, abril 2026, pre-holdout.** Holdout intacto.

---

## Veredicto

**SIN EFECTO DETECTADO** — pero con un residuo **positivo y consistente** por debajo de
la potencia disponible. Es un resultado distinto del de H1, y el más prometedor de los
dos.

| | |
| :-- | --: |
| contactos enumerados | 160.759 |
| resueltos sobre un borde de cluster | 11.318 |
| **MDE** (8 celdas, Bonferroni, deff = 5) | **0,053** |
| contraste agregado | **+0,038** |

## Cómo se midió

Se enumeran **todos** los contactos de primera vez con un nivel de precio en la sesión
—haya cluster o no—, viniendo desde al menos 4 ticks. El desenlace se resuelve por lo
que ocurre **primero** en las 20 barras siguientes: *rechaza* (vuelve 4 ticks por donde
vino) o *cruza* (sigue 4 ticks de largo). Los que no hacen ninguna quedan **indefinidos
y fuera del denominador** — meterlos adentro haría que la tasa dependa del horizonte,
que es un parámetro nuestro y no del mercado.

El control no es "nada": es **un nivel libre al que el precio llegó igual**, estratificado
por distancia de aproximación y volatilidad local.

## Resultados, con el control limpio

| dist | σ | n borde | n libre | n dentro | rechazo borde | rechazo libre | contraste |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 1 | 2 | 332 | 405 | 1.966 | 0,572 | 0,570 | +0,002 |
| **1** | **3** | **5.814** | **14.868** | 58.880 | 0,423 | 0,399 | **+0,024** |
| 2 | 2 | 50 | 57 | 288 | 0,580 | 0,632 | −0,052 |
| **2** | **3** | **4.149** | **12.894** | 43.712 | 0,397 | 0,365 | **+0,032** |
| 3 | 3 | 861 | 3.709 | 9.958 | 0,297 | 0,301 | −0,004 |
| 4 | 3 | 112 | 1.224 | 1.466 | 0,188 | 0,074 | +0,113 |

En los **dos estratos bien poblados** —los únicos con miles de observaciones en las tres
categorías— el contraste es **+0,024 y +0,032**. Ambos por debajo del MDE agregado de
0,053, y bastante por debajo del MDE por estrato (≈0,07 con n ≈ 5.800).

## Lectura

**1. No alcanza para afirmar nada.** Un borde de cluster rechaza el precio unos 2,5–3
puntos porcentuales más que un nivel libre a la misma distancia y volatilidad. El MDE es
5,3 puntos. Formalmente: no detectado.

**2. Pero es un residuo distinto del de H1.** En el módulo de decaimiento el contraste
era ~0 y de signo mezclado; acá es positivo en los dos estratos grandes y en el
agregado, en la dirección que predice la hipótesis. No es evidencia — es la diferencia
entre "no hay nada" y "puede haber algo chico que no vemos".

**3. Un defecto del control, encontrado y corregido antes de reportar.** La primera
corrida comparaba el borde contra *todo lo que no es borde*, lo que incluye el
**interior** de los clusters. Con el control limpio —sólo niveles **libres**— los mismos
dos estratos pasan de +0,030 y +0,037 a **+0,024 y +0,032**. La contaminación estaba
inflando el efecto un 20 %.

**4. El dato incómodo: el cluster está donde está el precio.** De los 79.562 contactos
del estrato principal, **58.880 caen dentro de un cluster vivo** — el 74 %. Aunque los
clusters cubren sólo el 4–9 % del rango de precio de la sesión, el precio pasa la mayor
parte del tiempo adentro de alguno.

Es exactamente la endogeneidad que el deep research advertía: el cluster nace donde hubo
actividad, la actividad ocurre donde estuvo el precio. Cualquier efecto medido acá está
condicionado sobre una variable co-determinada por el precio, y por eso el escalón 5
—condicionar por la intensidad previa— no es opcional.

## Qué haría falta para cerrar

1. **Más sesiones.** El MDE cae con √n: para llevarlo de 0,053 a 0,025 hacen falta unas
   **65 sesiones**. Es la única forma de decidir si el +0,03 es real.
2. **Bootstrap clusterizado por sesión** en vez del `deff = 5` supuesto. El proyecto ya
   tiene `edgelab/stats/bootstrap_estacionario.py` con largo de bloque óptimo.
3. **Escalón 5**: condicionar por intensidad. Con el 74 % de los contactos dentro de un
   cluster, sin ese paso no se puede separar el efecto del objeto del efecto de estar
   donde el precio ya estaba.

---

**Aporte al referente:** entrega el canal direccional que faltaba con su control
depurado, y lo deja dimensionado — el residuo va en la dirección de la hipótesis pero es
la mitad del mínimo detectable, así que dice cuántas sesiones cuesta decidirlo en vez de
afirmarlo.
