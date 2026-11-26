# CARRIL2-EXTENSION: en 2025-08 → 2026-09 (sólo DESC/REP) C2_VZ sigue positiva; las demás cercanas al criterio no (resultado, 2026-11-26)

Estado: RESULTADO — descriptivo, pre-registrado (`PREREGISTRO.md`).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `OPS_LOTE1.csv.gz`, `OPS_LOTE2.csv.gz` y `RESULTADO.json`. Herramienta `tools/carril2_extension.py`.

Episodios: R por definición antes y después de 2025-08, en `RESULTADO.json`.

| Definición | Hasta 2025-07: n, R, t | 2025-08 → 2026-09: n, R, t |
|---|---|---|
| C2_VZ NQ | 298, +0,147, 3,57 | 16, **+0,104**, 0,58 |
| C2_VZ ES | 306, +0,104, 2,68 | 17, **+0,179**, 0,82 |
| C2_VBBN NQ | 346, +0,118, 4,02 | 7, −0,294, −0,97 |
| C2_TOMN NQ | 177, +0,191, 2,86 | 8, −0,216, −0,89 |
| C2_TOMN ES | 177, +0,122, 1,81 | 8, −0,187, −0,80 |
| C2_D7 NQ / ES | 196 / 199, +0,15 / +0,17 | 14 / 14, +0,10 / +0,07 |
| C2_TT NQ | 228, +0,151, 2,89 | 13, −0,026 |
| Lote 1 entero (operaciones nuevas) | | 283, −0,033, t −0,67 |
| Lote 2 entero (operaciones nuevas) | | 251, +0,023, t 0,44 |

## Lectura
- **Potencia:** el tramo nuevo tiene 7–17 operaciones por definición, sin potencia; ningún signo es significativo.
- **C2_VZ** sigue a favor en NQ y en ES, igual que en las corridas NT8. Es la única de Carril 2 que entra a la regla de cartera.
- **C2_VBBN NQ y C2_TOMN** tienen signo en contra en el tramo nuevo. No se suman hasta tener forward o una apertura del holdout A5 de
  `CARRIL2_A5` (no abierto), con plan de potencia.
