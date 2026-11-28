# REMEDICION-FS-IL: con la traducción corregida, T, R y Z no cambian, A20 mejora apenas y V pasa a ser candidata (resultado, 2026-11-21)

Estado: RESULTADO — re-medición pre-registrada (`PREREGISTRO.md`), 1 prueba contada. Descriptivo.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `FS_OPS_NQ_IL.csv.gz` (nuevas) y `COMPARACION.csv` (vieja contra nueva).
- **Medida:** neto en puntos de NQ, fricción canónica, t mensual.

Episodios: el t mensual por ventana de la tabla.

| Módulo | t 2010–21 (viejo → nuevo) | t 2022–26 (viejo → nuevo) | Neto 2022–26 pts (viejo → nuevo) | t desde 2025-09 (viejo → nuevo) |
|---|---|---|---|---|
| T | 1,51 → 1,49 | 5,81 → 5,81 | 18.990 → 18.990 | 1,90 → 1,90 |
| R | 2,35 → 2,35 | 4,54 → 4,54 | 9.985 → 9.985 | 3,57 → 3,57 |
| Z | 1,76 → 1,76 | 2,79 → 2,79 | 4.564 → 4.564 | 1,23 → 1,23 |
| A20 | −2,96 → −2,85 | 2,57 → **2,77** | 10.757 → 11.547 | 1,11 → 1,40 |
| **V** | 1,41 → 1,28 | 1,09 → **2,87** | 1.894 → **5.115** | 0,86 → 1,53 |
| S | −3,66 → −3,64 | 1,76 → 1,86 | 9.449 → 10.095 | 0,98 → 1,18 |
| N | 0,89 → 0,84 | 1,80 → 1,95 | 3.723 → 3.894 | 1,79 → 1,84 |
| E | −2,58 → −2,79 | 0,34 → 0,11 | 395 → 125 | −0,45 → −0,51 |
| A1 | −16,0 → −16,1 | 1,35 → 1,29 | 2.884 → 2.702 | 1,71 → 1,71 |
| C, F, O, P, Q, W | sin cambio | sin cambio | sin cambio | sin cambio |

El cambio de Q es sólo de USD (valor del punto de MNQ); en puntos queda igual.

## Lectura
- **T, R y Z son idénticas.** Las conclusiones que las usan siguen valiendo: canasta, correlación, Lucid, filtros.
- **A20 cambia poco:** t 2,57 → 2,77. Las conclusiones sobre A20 siguen valiendo en lo cualitativo (sólo corta, no cubre).
  - Los números exactos de A20-REGIMEN, FILTROS-CONTEXTO, el holdout terminal y CANASTA-CORRELACION se hicieron con la versión vieja.
  - La diferencia está dentro del ruido (≈ 7 % más de neto), pero se re-hacen si A20 entra a una decisión.
- **V es el cambio grande:** t 1,09 → 2,87 desde 2022, positiva también en 2010–21 (t 1,28) y desde la venta del producto (t 1,53).
  - Pasa a la misma categoría que A20, y con mejor historia previa a 2022.
  - Opera ≈ 17 veces por mes.
  - Siguiente paso: su correlación con la canasta y si suma.
- **S y N** suben un poco (t 1,9) pero siguen siendo pistas, no candidatas.
