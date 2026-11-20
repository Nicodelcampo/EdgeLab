# DELTASWEEP-PAT — patrones de disparos (pre-registro, 2026-11-14)

Estado: VIGENTE. Etapa EF2 (exploratorio). Familia DELTASWEEP_NQ (hereda las 8.527 pruebas del 13-nov y las de SEQ). North Star sha256
16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345. Módulo: `edgelab/research/deltasweep_pat.py`.

## Pedido
Más casos (potencia) con compuertas más densas, y filtrar bien: patrones de 2–5 disparos, tiempos entre disparos, distancia entre
disparos, puntos de entrada y SL/TP distintos.

## Espacio declarado
- Compuertas: PERM (todos los disparos permisivos), V4W, V3 (adaptativa), V5 (barre el swing y recupera); spread ≤ 2 ticks.
- n ∈ {2,3,4,5}; gap entre disparos ≤ {60, 300, 900} s; forma {sin condición, compacto ≤ 40 ticks, escalera (cada disparo mejor a
  favor)}; NY mañana o RTH. Control: el disparo suelto (n = 1) de la misma compuerta y régimen. 296 definiciones.
- Entradas y salidas (ideas del repo: palanca «stop grande frente a la fricción», ORB con stop en el extremo opuesto, brackets de las
  corridas del 13-nov): mercado con 80/160, 160/160, 160/320, 240/480 ticks; límite en retroceso de 40 u 80 ticks con 160/320; stop
  estructural detrás del extremo de los disparos del patrón con objetivo 2×. 7 ejecuciones × ~11 filtros comunes ≈ 22.800 celdas.

## Cómo se filtra (fijado antes)
Una celda es pista sólo si: (1) supera el p95 del máximo del nulo de la búsqueda en DESC **y** tiene el mismo signo en REP; (2) le gana a
su control (n = 1) en los dos períodos; (3) ≥ 4/5 sub-bloques positivos; (4) fricción ≤ 0,08 R. Además se lee la FORMA: un patrón
real debería mejorar de forma monótona con n o con la compacidad, no en una celda aislada. Nada se elige por P&L máximo aislado.

## Justificación económica
Disparos repetidos en el mismo sentido en poco tiempo = absorción insistente de agresores en un nivel; si el nivel aguanta varias veces,
el desequilibrio debería resolverse a favor del lado que absorbe.

## Cómo podría refutarse
Ninguna celda cumple (1)–(3); o el efecto no crece con n ni con la compacidad (sería azar de la grilla).

## Riesgos
REP ya fue mirado por la forma S2 (13-nov y SEQ): pesa DESC + nulo; lo que pase va a forward congelado. Entrada en la vela M1 siguiente.

## Enmienda v2 (2026-11-14, antes de ver resultados; pedido de Nico)
La v1 (gaps 60/300/900 s, forma «compacto ≤ 40 ticks») se relanzó sobre el mismo kernel ANTES de mirar nada y no se analiza. v2:
- gaps {10, 30, 60, 300} s (15 min es demasiado para la frecuencia de los disparos; 60 s como mínimo también);
- dispersión en precio (máx − mín) de los disparos del patrón como variable: `dpX` = de los disparos ANTERIORES al de la entrada,
  `dtX` = de TODOS incluido el de la entrada, X ∈ {8, 16, 32} ticks; se mantienen «any» y «escalera»; sale «compacto».
- 1.032 definiciones × 7 ejecuciones × ~11 filtros ≈ 79.000 celdas (se registran en el contador; la v1 también queda contada).
El filtro de pistas no cambia. Al traer, se verifica que la tabla venga del código v2 (`codigo`/`modulos` del JSON de la tabla).
