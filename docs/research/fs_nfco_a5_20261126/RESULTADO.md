# FS-NFCO-A5: O confirma en REP y N queda no concluyente; F y C no se nominan (resultado, 2026-11-26)

Estado: RESULTADO — lectura pre-registrada con enmienda declarada antes de leer N y O (`PREREGISTRO.md`), 8 pruebas contadas.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `RESULTADO.json`. Herramienta `tools/fs_nfco_a5.py`.
- **Holdout A5:** no está limpio para FundedSync (declarado). La confirmación limpia es el forward.

Episodios: R por año, en `RESULTADO.json`.

| 2018 → 2026-09 | Unidad de R | DESC: n, R, q BH | REP: n, R, p | Desenlace |
|---|---|---|---|---|
| **O** | ATR20 (sin stop) | 476, +0,028, q 0,088 | 131, **+0,055, p 0,025** | **CONFIRMA_REP** |
| **N** | ATR20 (sin stop) | 585, +0,021, q 0,088 | 176, +0,008, p 0,35 (MDE 0,048) | NO_CONCLUYENTE |
| F | riesgo propio | 594, +0,014, q 0,35 | — | SIN_NOMINAR (MDE 0,079) |
| C | riesgo propio | 311, +0,019, q 0,35 | — | SIN_NOMINAR (MDE 0,121) |

## Lectura
- **O:** confirma en REP, pero no opera desde 2025-10. Su techo de margen da 0 contratos con NQ > 25.000 (auditoría de Antigravity). Para
  sumarla hay que operarla con tamaño fijo (1 micro), que es tamaño, no regla. Su ventaja por operación es chica (≈ 0,03–0,05 ATR20).
- **N:** se nomina, pero en REP no se distingue de cero, sin potencia para un efecto de 0,02. Sigue como pista.
- **F y C:** no se nominan; sus nulos tienen MDE 0,08 y 0,12 y no cierran nada.
- **Error encontrado y corregido antes de leer:** la primera corrida trató a N y O (sin stop) como grupos vacíos y los marcó nominados. Se
  descartó y se enmendó la unidad (ATR20).
