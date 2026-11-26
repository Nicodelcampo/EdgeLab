# CARRIL2-EXTENSION: las 24 definiciones de Carril 2 hasta 2026-09 (DESC y REP de A5) (pre-registro, 2026-11-26)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de correr.
- **Pedido de Nico (2026-11-26):** «adelante con cada paso» (paso 2 de `docs/DECISIONES_20261126.md`: ampliar el pozo de estrategias
  decorrelacionadas).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2.** Extensión descriptiva de operaciones ya definidas, sin cambiar reglas. **Familia:** `CARRIL2_A5`.
- **Herramienta:** `tools/carril2_extension.py`. Reusa `tools/carril2.py::correr` sin cambios de regla, sólo con FIN = 2026-09-30, y llama
  a `exigir_contada`.

Cambio respecto a falla previa: no repite pruebas. Las 24 definiciones de los lotes 1 y 2 se congelaron el 2026-11-19 y acá sólo se
extienden 14 meses.

Antecedentes:
- `carril2_20261119/RESULTADO_LOTE1.md` y `RESULTADO_LOTE2.md`.
- `estabilidad_cartera_20261126/RESULTADO.md` §C: C2_VBBN NQ, C2_TOMN NQ/ES y C2_D7N ES quedaron cerca del criterio de estabilidad, con datos
  sólo hasta 2025-07 y sólo DESC/REP.
- **Declarado:** en ese tamiz los meses HOLDOUT de A5 de estas series quedaron en 0, no en «sin dato». Se corrige acá.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K33, K40 motor calibrado, K51, K53 definiciones sin disparos).

Potencia previa: no aplica a una prueba. Se agregan ≈ 14 meses, ≈ 9 de ellos DESC/REP, con ≈ 1–5 operaciones por mes por definición. Es
información para el tamiz de estabilidad, no una confirmación.

Diagnóstico de mecanismo: no aplica (reglas ya congeladas, sin grilla).

## Justificación económica
Son las estrategias swing de calendario y volatilidad del pozo. Son las más decorrelacionadas con la cartera intradía. Hay que saber si
siguen después de 2025-07.

## Qué se corre (fijo)
- **Corrida:** `carril2.correr` para los lotes 1 y 2 con FIN = 2026-09-30.
- **Meses:** sólo DESC y REP de A5; HOLDOUT y EMBARGO se descartan sin leerse.
- **Precios:** el lector corta en la frontera del terminal.
- **Salida:** `OPS_LOTE1.csv.gz` y `OPS_LOTE2.csv.gz` en esta carpeta. Las de 2026-11-19 no se pisan.
- **Se publica,** por definición e instrumento:
  - R medio, t y operaciones en 2025-08 → 2026-09 (DESC + REP);
  - la comparación con lo de antes de 2025-07;
  - una serie diaria en USD con 1 micro para el tamiz, con los meses HOLDOUT como «sin dato», no como 0.

## Cómo podría refutarse
Si las cercanas al criterio (C2_VBBN, C2_TOMN, C2_D7N) son negativas en el tramo nuevo, no se suman.
