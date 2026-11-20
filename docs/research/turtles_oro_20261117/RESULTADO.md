# Turtles en oro con cierre del viernes: réplica y mejora (resultado, 2026-11-17)

Estado: CERRADO — pre-registro `PREREGISTRO.md`. Datos `RESULTADO.json`, operaciones `ops/`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Cuánto opera
**5,3 operaciones por año** (83 en 2011 → 2026-09; 117 desde 2004). Dos tercios largos. Casi todas salen el viernes (mediana 3 velas); el stop
de 2 ATR20 casi no se toca. Fricción 0,016 R. Peor caída de la serie de R: −1,7 R (2011–2026).

## 1. Réplica en 2004–2010 (nunca mirada)
| | n | R/op | p | MDE |
|---|---|---|---|---|
| Base 2004–2010 | 34 | **+0,03** | 0,36 | 0,24 |
| Base 2011–2026 (desarrollo) | 83 | +0,22 | 0,0006 | 0,17 |
| Base 2004–2026 | 117 | +0,17 | 0,002 | 0,14 |
**No replica** por la regla pre-registrada (hacía falta p < 0,10). Signo positivo pero chico y **sin potencia**: el MDE (0,24) es del tamaño del
efecto de desarrollo. No mata la pista, pero la debilita: la ventaja se concentra en 2011–2026 (y más en 2020–2026).

## 2. Mejora (pares 2012…2026 para elegir, impares 2011…2025 para confirmar)
| Variante | ops/año | R/op dev | t mensual pares | t impares | años+ pares | 2004–2010 R/op | Elegible |
|---|---|---|---|---|---|---|---|
| **base** | 5,3 | +0,22 | 1,88 | 1,86 | 6/8 | +0,03 | — |
| entrada_stop | 7,4 | +0,21 | **2,45** | 1,60 | 7/8 | +0,13 (t 2,0) | sí → finalista |
| sin_filtro_tend | 7,6 | +0,15 | 1,72 | 1,41 | 6/8 | −0,00 | sí → finalista |
| sin_filtro_vol | 8,5 | +0,17 | 1,77 | 2,08 | 5/8 | +0,06 | no (años) |
| canal_20 | 8,4 | +0,16 | 1,78 | 1,66 | 5/8 | +0,11 | no (años) |
| solo_largos | 3,5 | +0,35 | 2,11 | 2,14 | 4/6 | +0,03 | no (años) |
| reentrada_lunes | 18,7 | +0,08 | 0,67 | 1,66 | 5/8 | +0,09 | no |
| h4 | 20,1 | +0,11 | 0,98 | 0,96 | 5/8 | +0,10 | no (fricción 0,04 ok; años) |
| metales (GC+SI) | 9,7 | +0,07 | 1,28 | 0,37 | 5/8 | +0,03 | no |
Confirmación en impares: entrada_stop − base = +0,011 R/mes (p 0,38); sin_filtro_tend −0,015 (p 0,74). **Ninguna confirma: no hay ganadora.**

## Lectura
1. **Meseta (L1 otra vez):** todas las vecinas son positivas en las dos mitades. La regla de fábrica no es un pico, y moverle una perilla no
   le gana fuera de la muestra de elección.
2. **Potencia sin pagar rentabilidad no apareció:** lo que multiplica las operaciones (H4, re-entrada del lunes, canal 20) baja el R por
   operación más de lo que suma N; el t mensual cae o queda igual. La plata no acompaña (impares +0,03): **el efecto es del oro**, no de los metales.
3. `entrada_stop` es la única que mejora algo en las tres lecturas (pares, 2004–2010 y ops/año), pero no en impares. Queda como observación,
   no se elige.
4. Para el forward, la base sola necesita ≈ 34 operaciones (≈ 6 años) para t = 2. Su valor realista hoy es **diversificación** (oro, semanal,
   correlación ≈ 0 esperable con la apertura de NQ), no una decisión rápida.

## Qué sigue
Holdout (apertura única) y forward de la **base congelada**: `ACTA_HOLDOUT.md`, `tools/turtles_oro_seguimiento.py`, incluida en
`tools/seguimiento_forward.py`.

## 3. Holdout (apertura única, 2026-10-01 → 2026-11-13; acta `ACTA_HOLDOUT.md`, regla de `1f5e3e79`)
**0 operaciones** (el kernel leyó el XAUUSD sellado hasta la barra del 13-nov; se esperaban ≈ 0,6). Lectura: **NO_CONCLUYENTE** (Fisher con
p de desarrollo 0,32 = 0,68). No hubo señal en seis semanas; no se usa para nada más. Sigue el **forward** desde el 2026-11-14, incluido en
`tools/seguimiento_forward.py` (`edgelab-turtles-oro-seg-fw<HASTA>`). Operaciones: `seguimiento/holdout/`.

## 4. Fuera del forward (2026-11-17, K27)
Nico: «opera demasiado poco». Con la compuerta nueva (`tools/potencia_previa.py`, `holdout_ventanas.plan_potencia`): 0,4 operaciones por
mes y 196 meses para decidir → no pasa (máximo 60 meses: junta 4 veces menos información por mes que SOM). Sale de `tools/seguimiento_forward.py`; el holdout de arriba
se abrió sin potencia (K27, registrado como error). Sigue como pista sólo dentro de una canasta que junte frecuencia.
