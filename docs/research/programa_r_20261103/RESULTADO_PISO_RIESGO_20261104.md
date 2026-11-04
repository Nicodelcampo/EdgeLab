# Resultado: piso de riesgo frente a la fricción en las 11 reglas (04/11/2026)

Estado: VIGENTE — **REFUTADO según el pre-registro** (`PREREGISTRO_PISO_RIESGO_20261104.md`). Datos: `RESULTADO_PISO_RIESGO_20261104.json`.
11 reglas: 606 operaciones en DESC y 555 en réplica. Octubre no se usó.

| Tramo | Umbral (no operar si fricción/riesgo > u) | Descartadas | R medio (Δ vs base) | Bruto medio | R total (base) | Reglas mejor o igual |
|---|---|---|---|---|---|---|
| DESC | base | — | +0,185 | +0,236 | 112,2 | — |
| DESC | 0,10 | 10,4 % | +0,212 (+0,027) | +0,248 | 115,3 | 8/11 |
| DESC | 0,075 | 15,8 % | +0,221 (+0,036) | +0,253 | 112,7 | 8/11 |
| DESC | **0,05 (elegido)** | 27,6 % | **+0,232 (+0,047)** | +0,260 | 101,9 | 9/11 |
| Réplica | base | — | +0,107 | +0,155 | 59,4 | — |
| Réplica | 0,10 | 8,6 % | +0,131 (+0,023) | +0,165 | 66,1 | 9/11 |
| Réplica | 0,075 | 15,0 % | +0,120 (+0,013) | +0,151 | 56,8 | 7/11 |
| Réplica | **0,05 (elegido)** | 26,7 % | **+0,096 (−0,012)** | +0,122 | 38,9 | **4/11** |

## Lectura

1. **La regla pre-registrada falla.** Con DESC se elige u = 0,05. En la réplica baja el R medio (−0,012) y sólo 4 de 11 reglas quedan
   mejor o igual. Queda refutada.
2. **Subir el R por operación no es ganar más.** Con u = 0,05 el R medio de DESC sube, pero el R total cae de 112 a 102: se tiran
   operaciones ganadoras. Un filtro se juzga también por el R total (o por el R por día), no sólo por la media por operación.
3. **u = 0,10 mejora en los dos tramos.** En la media sube +0,027 y +0,023; en el total, +3 y +7R; en las reglas, 8/11 y 9/11. **No se
   adopta**: no fue la elegida y verla ahora es mirar la réplica. Queda como **hipótesis nueva a medir desde noviembre de 2026**: descartar
   sólo las operaciones donde la fricción supera el 10 % del riesgo (unas 9 de cada 100).
4. **La lección de la revisión del atlas se mantiene** (la fricción explica parte de los efectos «ATR bajo» y «stop ancho»). Pero en estas
   reglas, cortar fuerte por el tamaño del stop no paga: los stops chicos también traen ganadoras.

Aporte al referente: descarta un filtro de costo que parecía obvio antes de aplicarlo, y deja para validar hacia adelante una versión
suave (u = 0,10) que sí sumó en los dos tramos.
