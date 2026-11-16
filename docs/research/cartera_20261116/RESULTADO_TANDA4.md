# Tanda 4: resultado (2026-11-16)

Estado: RESULTADO — pre-registro `PREREGISTRO_TANDA4.md` (commit eb24d539). Herramienta `tools/cartera_tanda4.py` (c1, c2c5, c4, operativa_v3).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Nada miró el holdout; noviembre no se usa para decidir
la v3 (se decide en forward desde 2026-11-14).

## C1. Re-elegibilidad con el filtro de fricción → cartera v3 (cambia)
Repetir la regla §5 con M1 aplicado antes de elegir cambia 3 de las 8 reglas (`v3/SELECCION.json`, `CARTERA_V3_OPERATIVA.json`):

| sale (v2) | entra (v3) |
|---|---|
| U1-ZONAS-BT2-ES, U1-ZONAS-BT2-NQ, U1-ORO-GRILLA | DRC-NQ-R, U1-ZONAS-AVCL-ES-C, U1-ZONAS-AVCL-NQ |

Quedan CVGAP-ES-C, U1-RACIMOS-GRILLA-NQ, PREAPERTURA-NQ, CONF-CVR-CFD-NQ-R y CVGAP-CFD-ES-C. **No** entran TORI-NQ-R ni PREAPERTURA-ES, que eran las
dos reglas que la propuesta esperaba recuperar. Aviso: DRC-NQ-R saltea el 70 % de sus operaciones de desarrollo por M1 y sus micros fijos (7 MNQ) salen
del riesgo mediano de **todas** sus operaciones (14,25 pts). Por eso, en las que sí opera (stop ≥ 19,3 pts) arriesga ≥ 270 USD, por encima de los 200 de
referencia. Es la definición M3 de la v2, aplicada igual que en la v2; no se corrige después de ver el resultado.

## C2 + C5. Cartera conjunta y freno diario (desarrollo 2025-08-05 → 2026-09-29, 301 sesiones; prop 50K)

| versión | USD dev | t diario | DD máx | pasa / quema (media contraída) | pasa / quema (media 0) |
|---|---|---|---|---|---|
| v2 | 24.210 | 5,35 | −1.214 | **63 % / 3 %** | 14 % / 50 % |
| v2 + freno | 24.169 | 5,33 | −1.214 | 63 % / 3 % | 14 % / 49 % |
| v3 | 43.188 | 5,33 | −1.815 | **80 % / 14 %** | 24 % / 73 % |
| v3 + freno | 40.025 | 5,01 | −2.062 | 77 % / 17 % | 25 % / 73 % |
| v2 + TZR | 70.456 | 5,35 | −5.506 | 66 % / 34 % | 30 % / 70 % |
| v3 + TZR | 89.434 | 6,15 | −4.036 | 69 % / 31 % | 26 % / 74 % |
| TZR sola | 46.246 | 3,85 | −4.874 | 56 % / 44 % | 30 % / 70 % |

- **Correlación diaria v2 ↔ T+Z+R: 0,08.** Están descorrelacionadas, pero T+Z+R a ≈ 200 USD de riesgo por regla tiene una varianza diaria que
  no entra en el drawdown de 2.000 de la 50K: sumarla sube la quema de 3 % a 34 %. **C2: la combinación a este tamaño no mejora la quema → refutada
  como está.** Lo que sí queda es que la ganancia y el t suben (v3 + TZR: t 6,15).
- **v3 vs v2:** casi duplica la ganancia de desarrollo con igual t, y la probabilidad de pasar sube de 63 % a 80 %, pero la quema sube de 3 % a 14 %
  (más riesgo efectivo, sobre todo DRC-NQ-R). Las dos son selecciones sobre el mismo desarrollo; la diferencia se decide en el forward.
- **C5 (freno de −500 USD por día): refutado.** No baja la quema en ninguna versión; donde cambia algo, la sube (v3: 14 → 17 %; v2 + TZR: 34 → 38 %),
  porque corta días que después se recuperan.

## C4. Noche movida como contexto (H: noche ALTA > resto; A → B, BH sobre 4)

| regla | A: alta / resto (n alta) | p A | B: alta / resto (n alta) | p B | pasa |
|---|---|---|---|---|---|
| T (pts) | 6,4 / 16,7 (314) | 0,92 | 22,8 / 17,3 (242) | 0,26 | no |
| Z (pts) | 50,9 / 16,5 (31) | 0,04 | 86,0 / 23,7 (18) | 0,07 | no (BH) |
| PREAPERTURA-NQ (R) | 0,32 / 0,37 (34) | 0,55 | 0,50 / 0,32 (28) | 0,43 | no |
| PREAPERTURA-ES (R) | −0,47 / 0,76 (20) | 1,00 | −0,08 / 0,63 (19) | 0,88 | no |

Ninguna pasa. Hay dos lecturas descriptivas, que no son evidencia:
- **Z rinde más con noche movida** en las dos mitades. Con n = 18 en B no alcanza la corrección BH (haría falta p ≤ 0,025).
- **PREAPERTURA-ES pierde con noche movida en las dos mitades**: es la dirección **opuesta** a la hipótesis (t −2,96 en A). Probarlo como filtro exige un
  pre-registro nuevo y una réplica no mirada.

## Qué pasa al forward
- La **v3 entra al forward como versión paralela**, con el mismo e-proceso, las mismas cotas (operación −6/+30 y sesión −15/+40 R de cartera) y el mismo
  umbral (e ≥ 10) que la v2 (`PREREGISTRO_FORWARD_V2.md`). Lo declaro antes de que exista ninguna sesión forward. El tramo diario lanza la unión
  de reglas (11) y escribe `FORWARD.json` (v2) y `FORWARD_V3.json` (v3).
- La **v2 sigue siendo la versión operable** por su quema del 3 %. T+Z+R sigue en su propio forward (`fundedsync_cadena.py forward`) y **no se suma a la
  cuenta de la cartera a este tamaño**. Si se quiere combinar, hace falta un tamaño menor declarado antes (por ejemplo ≈ 50 USD de riesgo por regla). Eso es
  una hipótesis nueva, no se ajustó acá.
- El freno diario de −500 no se usa.

## Contador
`cartera_20261116/tanda4_c1` (1) y `cartera_20261116/tanda4_c4_noche` (4), registrados antes de correr. C2/C5 son descriptivos. C3 (cluster HFT ×
PREAPERTURA) queda para la próxima vuelta.
