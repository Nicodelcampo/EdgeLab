# Tanda 5: resultado (2026-11-16)

Estado: RESULTADO — pre-registro `PREREGISTRO_TANDA5.md`. Cifras: `TANDA5_T5A.json`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## T5a. T+Z+R a 1 MNQ: no entra al forward
| versión | USD dev | t | DD | pasa / quema (media contraída) |
|---|---|---|---|---|
| v2 | 24.210 | 5,35 | −1.214 | 63 % / 3 % |
| v2 + TZR mín | 45.289 | 6,26 | −2.857 | 80 % / 16 % |
| v2 + T mín | 35.698 | 5,93 | −2.475 | 79 % / 13 % |
| v3 | 43.188 | 5,33 | −1.815 | 80 % / 14 % |
| v3 + TZR mín | 64.266 | 6,57 | −1.675 | 83 % / 16 % |
| v3 + T mín | 54.675 | 6,10 | −1.675 | 84 % / 15 % |

Ninguna combinación cumple la regla (quema ≤ 10 % y pasar ≥ la cartera sola). Sumar suba t y ganancia, pero la quema de la 50K pasa del 3 % a
más del 10 %. **La v2 sola sigue siendo la versión operable en una 50K**; con una cuenta de drawdown más holgado la cuenta cambia
(no medido acá).

## T5b y T5c: armados para el forward
PREAPERTURA-ES se baja en el forward diario (`cartera_v2_forward.SEGUIMIENTO`); el veto de noche y el filtro Franklin de T se calculan con
`tools/franklin_seguimiento.py traer_forward` sobre el kernel sellado de Franklin.
