# HFT-CONTEXTO — resultado

Estado: RESULTADO (2026-11-10). Pre-registro: `PREREGISTRO_CONTEXTO.md`. Datos: `HFTC_contexto.json` / `.csv` (DESC jul-2025 → mar-2026,
NQ y ES, clusters del E0-b, definición de rebote D0_BASE elegida por regla). Recomendaciones: `RECOMENDACIONES_contexto.md`.
Procedencia: el kernel se construyó antes de que `hft_clusters_info.py` sumara la columna `net_dir` (diff `7ac35e7f..74a26458`);
contexto no lee esa columna, el cambio quedó aceptado con justificación escrita en el JSON (`cambios_aceptados`).

## Qué salió
- 3.197 toques reales (NQ y ES). **0 de 3 variables probadas nominadas** (BH q 0,10).
- **Tres variables sin muestra en un estrato** (compuerta ≥ 150, fijada antes): `respaldo` (≥ 2 clusters detrás: 0 eventos; 1: 78),
  `confluencia` (otro cluster solapado: 0 eventos) y `densidad` (≥ 3 en ±2X: 33). Los clusters grandes del E0-b (10–20 por sesión,
  vida 1.800 s) casi nunca coexisten cerca: con estos clusters esas preguntas no tienen población.
- Probadas, ninguna con efecto:

| Variable (A vs B, signo esperado) | Diferencia | IC90 | p declarada | Control (dif) | Dif-en-dif | Por activo |
|---|---|---|---|---|---|---|
| obstáculo cerca vs ninguno (−) | +0,043 | [−0,027, +0,115] | 0,84 | +0,204 (n 964) | −0,161 | NQ +0,028; ES +0,417 (se 0,25) |
| el tocado es el más nuevo (+) | −0,039 | [−0,140, +0,064] | 0,73 | +0,103 (n 237) | −0,142 | NQ −0,033; ES −0,150 |
| huella 0 vs ≥ 1 (sin dirección) | −0,057 | [−0,150, +0,034] | 0,31 | +0,084 (n 1.021) | −0,141 | NQ −0,045; ES −0,434 (se 0,30) |

MDE (80 %): 0,11–0,16. Un efecto de contexto menor que ≈ 0,1 sigue posible; uno mayor no aparece.

## Lectura
El rebote en un cluster grande no cambia con el obstáculo adelante, con que el tocado sea el más nuevo ni con clusters nacidos
mientras el precio estaba afuera. Las preguntas de respaldo, confluencia y densidad no se pudieron hacer con clusters tan escasos.
Ninguna recomendación pasa a INDAGAR; las tres probadas quedan NO_CONCLUYENTE y las otras tres SIN_MUESTRA.

## Qué no repetir / qué haría falta
No repetir el contexto con los clusters del E0-b en DESC. Respaldo y confluencia sólo tienen sentido con una definición más densa
de cluster (las de 4 zonas del E0, ya descartadas como rebote) o midiendo la distancia continua al cluster vecino más cercano.
