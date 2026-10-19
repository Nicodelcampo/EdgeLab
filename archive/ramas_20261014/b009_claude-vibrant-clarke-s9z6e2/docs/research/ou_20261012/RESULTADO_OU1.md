# OU-1 — resultado (pre-registro `PREREGISTRO_OU1.md`, 42 pruebas, sin sesiones omitidas)

Kernel `edgelab-ou1-20261012` (catálogo v15), 1.135 s. Datos crudos: `OU1_RESULTADOS.json`. Sin holdout.

## Parte A (36 pruebas, Holm 36)
Solo **3 de 36** pasan Holm, todas en **ZB** y todas de **reversión**: 5 min/1 h (z = −14,1; Holm 0,007), 5 min/4 h (z = −7,7; 0,007) y 15 min/4 h (z = −3,3; 0,020). ZB 60 min no pasa (z = 0,06). Ningún otro futuro (ES, NQ, YM, GC, 6E, 6J) ni el oro spot pasa; el mínimo fuera de ZB es 6E 5 min/1 h con Holm 0,27 y ES spot 5 min/1 h con 0,67.
Exceso de reversión en ZB a 5 min: b = −0,164 contra −0,130 del nulo (vida media ≈ 19 min). Es una desviación pequeña en magnitud, muy significativa por las 71.677 barras.
ES, GC, ES spot y los demás: el signo suele ser reversión pero con z entre 0 y −2, compatible con azar. El oro spot (2022-25) tiene signo momentum en 3 de 4 celdas, sin significación.

## Parte B (6 pruebas, Holm 6)
Ninguna pasa. La franja **04:30 CT** de GC muestra correlación negativa en las dos muestras (reversión): futuro 2025-26 −0,32 (n = 281, p = 0,068, Holm 0,34) y spot 2022-25 −0,089 (n = 932, p = 0,019, **Holm 0,115**). 19:30 y 04:15 no muestran reversión (correlaciones +0,01 a +0,03 y −0,06 a +0,02).

## Regla de decisión (§6)
- Regla 2 («OU sirve para EdgeLab»): **no se cumple**. ZB pasa Holm pero no tiene hermano spot para comprobar el signo, y ES/GC (que sí lo tienen) no pasan.
- Cautela con ZB: la reversión a 5 y 15 min en un contrato de tick grueso es compatible con rebote bid-ask (el precio es el último trade, sin descontar costos). La familia de descubrimiento ya probó ZB con f1/f5 y no pasó nada. Esto no es evidencia de edge: habría que medirlo con precio medio y costos antes de nada.
- Parte B: coherente con los análisis previos. La reversión de 04:30 existe con el mismo signo en ambas muestras, pero sin potencia para pasar Holm; no cambia que H1/H2 no replicaron.

## Qué se concluye
1. En el resto de los activos y escalas **no hay evidencia** de reversión (ni de momentum) por encima de lo que da un nulo de martingala. Eso es consistente con que las familias de momentum y medias no hayan encontrado nada.
2. ZB es el único candidato, con la salvedad del rebote bid-ask.
3. 04:30 CT en GC es la única franja con señal consistente en dos muestras; seguiría siendo exploratoria (p nominal 0,019 en spot independiente, Holm 0,115).
4. Cualquier estrategia que salga de acá necesita su propio pre-registro.
