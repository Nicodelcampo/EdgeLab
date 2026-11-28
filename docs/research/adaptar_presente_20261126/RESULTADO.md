# ADAPTAR-PRESENTE 1: escalar por precio el tope de T y el de F no mejora; los topes en puntos fijos no eran un desajuste dañino (resultado, 2026-11-26)

Estado: RESULTADO — lectura pre-registrada (`PREREGISTRO.md`), 2 pruebas contadas. **No se adopta ninguna variante.**
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `OPS_T_F.csv.gz` y `RESULTADO.json`. Herramienta `tools/adaptar_presente.py`.

Episodios: operaciones por año en `RESULTADO.json`.

| 2012 → 2026-09, USD con 1 MNQ | T vendedor | T escalado | F vendedor | F escalado |
|---|---|---|---|---|
| USD/mes | +229 | +207 | +16 | +14 |
| Sharpe mensual anual | **1,26** | 1,09 | 0,22 | 0,17 |
| % años positivos | 53 % | 53 % | 47 % | 40 % |
| Sharpe 2022 → 2026-09 | **2,60** | 2,22 | 0,70 | 0,57 |
| Operaciones en 2026 | 164 | 164 | **18** | **77** |

## Lectura
- **T:** con el tope de stop proporcional al precio, el Sharpe baja 0,17 (umbral 0,1). **No se adopta.**
  - El tope fijo de 100 puntos achica el stop relativo en el NQ de hoy, y en 2022–2026 esa versión rinde más (2,60 contra 2,22).
  - El desajuste existe, pero no le resta: es parte de cómo gana T hoy.
- **F:** la escala recupera la frecuencia (77 operaciones en 2026 contra 18), pero baja el Sharpe y los años positivos. **No se adopta.**
  F es débil en las dos versiones.
- **Lección para «adaptar al presente»:** que un parámetro en puntos se haya vuelto activo no prueba que dañe. Cada adaptación se mide antes
  de usarla, como acá.
- **Pendientes de la auditoría:**
  - O dejó de operar por su techo de margen, que es tamaño, no regla: se resuelve con tamaño fijo de 1 micro.
  - E tiene stop y objetivo fijos en puntos.

## Error de medición encontrado (no cambia la decisión)
- El kernel de `fundedsync_main.operaciones` calcula el riesgo de T con el tope fijo (`_orb_t`: clip a [2, 100]) en lugar del stop real.
- En la variante escalada, la columna `riesgo` y el R por operación de T están mal: no se usan.
- La comparación se hizo en USD (neto), que no depende de esa columna, y es la que decide según el pre-registro.
- La fracción de operaciones en el tope de la variante no se pudo medir por la misma razón: queda como NO MEDIDO.
