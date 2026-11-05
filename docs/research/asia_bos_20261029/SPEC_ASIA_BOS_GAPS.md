# Especificación Pre-Registrada: Familia `ASIA-BOS-GAPS` (`2026-10-29`)

- **Módulo experimental:** `edgelab/research/asia_bos_gaps.py`
- **Origen en la Biblioteca de Ideas:** Posts #18 y #23 (`@alefx_ar` — Rango Asia `18:00–20:00 ET` + modelo BOS), Post #159 (`@algo.jan` — *Asian Session Glitch*) y Posts #110/#140 (`@tomcampcoaching`), acoplados en espiral con `ZONAS-GAPS` y `EmaCorridorTrendVolW2`.
- **Mecanismo económico:** La baja liquidez del bloque asiático (`18:00–20:00`, `18:00–22:00` o `20:00–00:00 ET`) forma una caja compacta de órdenes acumuladas. Cuando la transición asiático-europea rompe esa caja con cuerpo fuerte (`>= 50%`) a favor del corredor EMA, se inicia expansión direccional (`BOS`); cuando barre el extremo, mitiga un gap previo y reingresa cerrando dentro de la caja (`IFVG`), atrapa a los operadores de ruptura tardía y revierte al extremo opuesto.
- **Cómo podría refutarse:** `0` celdas nominadas por FDR (`q <= 0,10`) en `DESC`, fallo ante placebo/latencia en `INTEGRIDAD`, o media neta `<= 0` en `OOS`/`HOLDOUT`.
