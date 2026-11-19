# A20-REGIMEN: A20 (FundedSync) con el procedimiento exacto de T-REGIMEN, ventana desde su quiebre (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de calcular la decisión.
- **Pedido de Nico:** «También A20 … son grandes ganadoras desde 2020» y «no olvides ninguno de los frentes … riguroso … sin falsos
  positivos». NETO-PISTAS midió A20 sólo en la ventana completa (SOBREAJUSTE_PROBABLE) y dejó como descriptivo que desde su quiebre es una
  meseta; acá se pre-registra esa ventana como en T.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3. Familia:** `FUNDEDSYNC`. **Herramienta:** `tools/neto_pistas.py a20_regimen` (misma grilla de 81 y mismo R con el stop duro
  propio, `RZ_OPS.csv.gz` ya calculado; `g2.pbo_cscv`, `parameter_sensitivity`).

Antecedentes: T-REGIMEN (quiebre medido con la fábrica, grilla evaluada desde ese quiebre), NETO-PISTAS §A2 (quiebre de A20 2017-11-10, p 0,003;
descriptivo 81/81 positivas desde ahí) — **la ventana se eligió después de ver ese descriptivo**: este pre-registro no la vuelve limpia; por eso
la decisión exige además el control por instrumento y por subperíodo de abajo.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K38, K48, K49, K51).

Potencia previa: NQ desde 2017-11 ≈ 1.800 operaciones de la fábrica (≈ 20 por mes); sd ≈ 1,2 R → error estándar del R medio ≈ 0,03.

## Justificación económica
- A20 vende absorción en velas de 20 minutos (cortos contra compradores agresivos que no mueven el precio). Si desde 2017 el mercado de NQ
  cambió (más fricción relativa baja, más flujo de opciones de corto plazo), la ventaja aparecería desde ese quiebre en todo el vecindario.

## Decisión (en la ventana 2017-11-10 → 2026-09-29, NQ)
- Mismos umbrales que T: `REGIMEN_ROBUSTO` si ≥ 70 % de las 81 variantes con R neto > 0, mediana ≥ 50 % de la fábrica, vecinos > 0 y PBO < 0,3;
  `SOBREAJUSTE_PROBABLE` si PBO > 0,5 o < 50 % positivas; si no, `INTERMEDIO`.
- **Controles extra por haber elegido la ventana mirando:** (1) las dos mitades de la ventana (2017-11 → 2021-12 y 2022-01 → 2026-09) deben
  tener cada una ≥ 70 % de variantes positivas; (2) en ES, la fábrica en la misma ventana debe tener R neto > 0. Si falla alguno, el veredicto
  máximo es `INTERMEDIO`.
- **Cómo podría refutarse:** PBO > 0,5, < 50 % positivas, una mitad sin meseta o ES negativo.
- **Contador:** 1 prueba en `FUNDEDSYNC`.
