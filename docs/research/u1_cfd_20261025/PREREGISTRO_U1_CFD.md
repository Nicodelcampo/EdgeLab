# Pre-registro — U1-CFD: la grilla completa de U1 sobre USA500, USA30 y EURUSD (millones de variantes, 27 meses)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Campañas `U1-ES-GRILLA`, `U1-YM-GRILLA`, `U1-6E-GRILLA` (familias `U1_ES_GRILLA`, `U1_YM_GRILLA`, `U1_6E_GRILLA`), por el embudo
automático (`config/autopilot/grillas/campanas/<cid>.json`). Etapa: **EF2/EF3** (DESC → … → OOS); confirmación en el holdout a N fijo.
Pedido de Nico (2026-10-25): «probar millones de variantes, cosa que antes no se hizo o no se hizo bien, y filtrar bien sin matar de más».

## 1. Por qué
U1 es lo más rentable medido en EdgeLab. U1-ORO-GRILLA (la misma grilla con la escala causal) nominó 125 celdas por FDR en el oro y sus
3 candidatas pasaron INTEGRIDAD; su OOS no confirmó (medias −1,98 / +1,60 / −0,19 USD/oz, dos sin potencia). Eso deja abierta la
pregunta de si U1 es general o propia del Nasdaq; la respuesta necesita más instrumentos y **más historia** que los 8 meses del oro.

## 2. Grilla (sin cambios respecto de U1-ORO-GRILLA: `edgelab/research/u1_cfd.py` reexporta `u1_oro`)
U1-INDAGA completa (N, x, A/H, volumen y velocidad por pierna, franjas, VWAP; 48 ejecuciones sin BE) × escala ∈ {0,5; 1; 2} sobre
W = 40 y G = 1 escalados por mes (rango M1 mediano del mes anterior del propio CFD / 6,25 de USATECH). **4.478.976 celdas por canal**,
canales total y reciente (los últimos meses del DESC que fija `grilla_generica`), por campaña.

## 3. Datos, ejecución y costos
- Sensor: USA500, USA30, EURUSD de Dukascopy (mid bid/ask), DESC **2024-01-02 → 2026-03-31**; OOS 2026-04-01 → 2026-09-30.
- Ejecución en DESC y OOS: **sobre el mismo CFD con la fricción canónica de su futuro** (`embudo_runners.friccion`: ES 0,8877 pts,
  YM 5,052 pts, 6E 0,000208), proxy declarado como en GAP-RTH. El futuro sólo cubre desde jul-2025: con él no habría 27 meses.
- Antes del holdout, la ejecución en el futuro (ES/YM/6E con señal en el CFD, como U1-CRUZADO) se verifica en la ventana común
  jul-2025 → sep-2026 con las candidatas congeladas; sin esa verificación no se abre el holdout.
- Nada desde la sesión del 2026-10-01.

## 4. Filtro (lo que hace que no se mate de más; todo en el embudo actual)
Tamiz FDR (Storey, q 0,10) sobre celdas **evaluables** (≥ 30 operaciones, D6); pistas a réplica en lote (un paso de LORD++ por lote,
Simes + BH) cuando el tamiz no nomina; la meseta ordena pero no veta; bootstrap con resolución adaptativa; el OOS mata sólo con
potencia y en contra significativo en el régimen actual (si no, NO_CONCLUYENTE); linaje como información, no como compuerta.

## 5. Multiplicidad y linaje
Las pruebas de DESC (4.478.976 × 2 por campaña) las registra el embudo en el contador global antes de lanzar, y las evaluables en
`EVALUABLES.jsonl` después. Linaje de cada familia ← `U1_ORO_GRILLA`, `AREAS_EXP_1_CRUZADO` (declarado en `LINAJES.jsonl` en este
commit).

## 6. Justificación económica
U1 cobra el regreso de un precio estirado ≥ 8–16 alturas a un racimo de huecos de cotización: la distancia de vuelta multiplica
la fricción, que es lo que mató a las familias de recorrido corto. Si es microestructura de feeds de 24 h, aparece en otros índices y
en el euro con la escala ajustada.

## 7. Cómo podría refutarse
Ninguna nominada ni pista confirmada en ninguno de los tres; nominadas que no pasan INTEGRIDAD (placebo ≈ regla); OOS en contra con
potencia; o candidatas que pierden la ventaja al ejecutarse en el futuro.

## 8. Riesgos
CFD ≠ futuro (horario, spread nocturno); 2024–2025 es otro régimen (por eso el canal reciente); el kernel de 27 meses puede acercarse
al límite de 12 h de Kaggle (el DESC del oro con 8 meses tardó 2,3 h).
