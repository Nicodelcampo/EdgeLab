# Resultado: búsqueda de régimen offline (08/11/2026)

Estado: RESULTADO. Pre-registro `PREREGISTRO.md` de esta carpeta (EF3, 4 pruebas en el contador global, familia REGIMEN_OFFLINE).
Corrida en Kaggle (`nicolasbuttaro/regimen-busqueda-20261108`, dataset `edgelab-cubos-regimen`): 106 cubos, k = 3, nulo de signo por
sesión B = 100. Datos completos: `RESULTADO_BUSQUEDA.json`. Nunca tocó el holdout.

| Variante | Ventanas | Δ contra azar (t) | Δ contra estática (t) | R neto/op elegido | p de familia |
|---|---|---|---|---|---|
| A_3M_CADA_MES | 30 | +0,013 (0,23) | −0,160 (−2,34) | −0,17 | 0,74 |
| B_2M_ESTABLE | 31 | +0,088 (4,12) | −0,078 (−1,36) | −0,10 | 0,12 |
| C_1M_MUY_ESTABLE | 35 | +0,059 (2,47) | −0,112 (−2,74) | −0,18 | 0,29 |
| D_3M_SIN_CADA_MES | 42 | +0,092 (3,19) | −0,067 (−1,85) | −0,12 | 0,11 |

Nulo (máximo de las 4 variantes): mediana +0,030, q95 +0,104 → **MDE ≈ 0,10 R/op** contra azar.

**Decisión (regla pre-registrada): NINGUNA VARIANTE PASA.** Ninguna tiene p de familia ≤ 0,05, todas pierden contra la estática y
el R neto de lo elegido es negativo en las cuatro.

**Lectura:**
- El Δ contra azar positivo (t hasta 4) no es régimen: el nulo de signo lo reproduce casi igual (la selección por estabilidad elige
  celdas «menos malas» que el azar también bajo signos al azar). Corregido, no alcanza.
- La mejor celda de TODO el pasado le gana a la mejor de los últimos 1–3 meses (Δ estática < 0 en las cuatro): mismo resultado que
  H-REG-1 (06/11). En este universo la racha reciente no informa más que la calidad de largo plazo.
- Lo elegido pierde 0,10–0,18 R por operación neto: ni la selección por régimen produce algo operable.

**Alcance:** este universo (106 grillas en R ya corridas), selección mensual con estos pisos, k = 3. No alcanza a otras
granularidades (semanal), a regímenes definidos por variables externas (volatilidad, tendencia) ni a familias fuera del universo.
