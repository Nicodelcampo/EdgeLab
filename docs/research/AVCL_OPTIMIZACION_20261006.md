# Optimización del cálculo de aVolClusterPOI — 2026-10-06

Pedido de Nico: es la base para probar muchas variantes y, más adelante, recalcular por régimen. Condición: **resultado
idéntico y paridad NT8 intacta**, o no se usa.

## Resultado
Referencia: MNQ 12-26 completo (re-export, 21,4 M ticks, Jul–Sep 2026), máquina local.

| etapa | antes | después |
|---|---|---|
| sesión por tick (`session_ids`) | 6,6 s | 0,8 s |
| barras 50t (`build_tick_bars`) | 10,4 s | 1,9 s |
| indicador 50t, base (p95, None, MaxAge 500) | 26,4 s | **4,0 s** |
| indicador 50t, defectos (p98, CloseThrough) | 16,2 s | 4,6 s |
| indicador 50t, p90 · W5 · top-K · FirstTouch | 99,5 s | **9,9 s** |
| indicador 200t, base | 2,1 s | 1,1 s |

Pipeline completo por contrato en 50t: unos 68 s → unos **15 s** (carga 3 + barras 2 + footprint 5 + indicador 4). El
footprint (5 s) pasa a ser la etapa más cara. En una grilla, barras y footprint se calculan **una vez por bar_spec** y
sólo el indicador se repite por celda: unos 4–10 s por celda y contrato.

## Qué se cambió (todo sin efecto en el resultado)
1. **Zonas AT fuera de la lista de vivas** (`avolclusterpoi_fast.py`). Era el cuello real: las AT nunca se invalidan,
   así que se acumulaban en `live` y el ciclo de vida las recorría (y salteaba) en cada barra, con costo O(zonas ×
   barras). `live` sólo se usa para ese recorrido.
2. **Footprint del bloque** agregado con numpy desde el CSR al cerrar el bloque (`np.unique` + `bincount` sobre un tramo
   contiguo), en lugar de un dict actualizado tick por tick en cada barra.
3. **Historia del umbral** ordenada una vez por sesión (sólo cambia en el commit de sesión), no en cada bloque.
4. **Celdas calientes, clusters y scores** vectorizados. Se respeta el desempate del original: primer cluster de score
   máximo en orden de tick, y top-K por (−vol, tick).
5. **Fin de sesión** precalculado por minuto único.
6. `bars.py`: **`session_ids` por minuto único** (la frontera 17:00:00 CT cae en borde de minuto) y **`_ohlc`
   vectorizado** con `reduceat`.

La versión original `avolclusterpoi_full.run_full` queda **intacta** como referencia.

## Verificación
- `run_full_fast` contra `run_full`, MNQ 12-26 completo: **igualdad exacta** de zonas, eventos, bloques y dashboard
  en 6 configuraciones (50t y 200t × base / defectos / p90-W5-topK-FirstTouch).
- `bars.py` antes/después: `session_ids` y las barras de 50t y 200t **idénticas** en todos los campos.
- **Paridad NT8 con las barras optimizadas: 50t PASS 934/934, 200t PASS 338/338.**
- `tests/test_avolclusterpoi_fast.py`: 9 tests (fast == full con ticks sintéticos en 4 configuraciones × 2 bar_spec,
  y OHLC vectorizado == bucle).
- Suite completa: 2.019 passed; 11 failed **preexistentes** (fallan igual en HEAD sin el cambio: visor, edge_brain, CURRENT.md, triaje de .cs, nulo BigTrap2).

## Pendiente para usarla en Kaggle
El dataset de código `edgelab-code-avcl-vol1` tiene el commit `c1763699`. Hay que publicar una versión nueva con
`bars.py` y `avolclusterpoi_fast.py` antes de lanzar grillas. `tools/avcl_cache_stage1.py` ya importa la versión rápida.

## Siguiente nivel, si hace falta
Una vez que la grilla esté definida: footprint CSR con numba (≈5 s → <1 s), y el ciclo de vida en numba. Hoy no se
justifica: el indicador ya no domina el tiempo.
