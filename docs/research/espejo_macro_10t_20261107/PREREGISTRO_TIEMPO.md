# Pre-registro: ESPEJO-MACRO-10T-TIEMPO (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2**.
Pedido de Nico: «ajustá los parámetros para que sí aparezcan operaciones donde no alcanzan».

## Por qué

En el barrido original (`PREREGISTRO_BARRIDO.md`) la ida tenía un tope de **400 velas** de 10 ticks:
- en NQ son unos 11 minutos de media;
- en ES (muchas más operaciones por minuto) son pocos minutos, y casi nunca entra un movimiento del ancho mínimo.

Resultado del DESC: **ES quedó con 0 celdas evaluables e YM con 504.** El tope era una escala en velas que sólo calzaba en NQ.

## Cambio único (`edgelab/research/espejo_macro_tiempo.py`)

- **Topes en tiempo:** ida ≤ 60 min desde A; ida + vuelta ≤ 120 min.
- **Duración de la ida como perilla en minutos:** ≤ 10, ≤ 30 o ≤ 60. La celda «≤ 10» queda cerca de la regla original.
- **Igual que el padre:** ancho mínimo en viajes de fricción severa (≥ 10 / 20 / 40), mínimos de velas de ida (8) y de vuelta (4),
  retrocesos (≤ 0,20 / 0,30 / 0,40), fracción de entrada (25 / 50 / 75 %), ritmo, RTH, ejecuciones (stop en B o 10 % más allá × A,
  75 % o 2R), salidas, noticias y costos.
- **Tamaño:** 31.104 celdas por canal.

## Advertencia de selección

Este cambio se hizo después de ver el DESC del padre: que ES no tuviera eventos. No se miró el P&L de ninguna celda de ES ni de YM,
porque no había. Igual cuenta como prueba nueva: familias hijas con linaje que heredan la multiplicidad bruta del padre en cada activo.

## Campañas

ESPEJO10TT-{NQ,ES,YM,GC}, señal y ejecución en el futuro, `ticks_por_barra: 10`. DESC del 2025-08-05 al 2026-03-31, réplica
abr–sep 2026, holdout desde 2026-10-01.

## Cómo podría refutarse

Ninguna celda nominada por FDR q 0,10 y ninguna pista que replique. Un nulo sin potencia no cierra la familia.
