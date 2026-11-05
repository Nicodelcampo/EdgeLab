# RANGO-ASIA0100 y RANGO-PREAPERTURA — pre-registro (2026-10-31)

Estado: VIGENTE (pre-registrado antes de cualquier corrida sobre datos reales; aprobado por Nico en la sesión en la nube, 31-oct).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo: EF2 → embudo automático.
Núcleo `edgelab/research/rango_ruptura.py`; módulos `rango_asia0100.py` y `rango_preapertura.py`. Campañas: RANGO0100-NQ/ES/GC
y PREAPERTURA-NQ/ES/YM. **Dos familias por ventana e instrumento, independientes** (no comparten multiplicidad ni resultados, y no
heredan nada de ASIA-NQ: la ventana, la regla de reentrada y el filtro de cuerpo son nuevos; las pistas p2/p3 de ASIA-NQ, elegidas
mirando el OOS, NO se usan).

## Fuente
@theagent_trades (documento extenso del paquete, secc. 2.4, 3.3 y 4.1): ranking de ventanas (01:00–01:15 ET y 09:15–09:30 ET arriba;
09:30–09:45 saturada; 12:00–12:15 a evitar) y regla de una sola reentrada tras un falso quiebre. Se descarta su "streak sizing"
(subir tamaño tras pérdidas): sin autocorrelación negativa demostrada es la falacia del apostador.

## Justificación económica
Un rango corto acumula órdenes en sus bordes; la ruptura con cuerpo y volumen libera ese flujo. Tras un primer quiebre fallido que
barre la mitad del rango, los stops del lado atrapado ya salieron y el segundo quiebre es el limpio.

## Espacio de eventos y estados
Eventos: primer cierre fuera del rango, toque del borde sin cierre, reingreso al rango, barrido de la mitad, segundo quiebre,
expiración (hora límite). Estados: ancho del rango, distancia al borde, eficiencia previa. **Se mide**: primer quiebre por cierre y
el segundo quiebre tras barrer la mitad (perilla `intento`); el toque sin cierre y el reingreso quedan fuera (serían otras familias).

## Qué se mide
- Rango = máximo/mínimo de las velas que cierran en (INI, FIN]. Asia: 01:00–01:15 ET, entradas hasta 04:00, salida forzada 06:00.
  Pre-apertura: 09:15–09:30 ET, entradas hasta 11:30 (no se opera la zona muerta), salida forzada 15:55; el tope de 240 velas del
  simulador manda antes.
- Ejecuciones (6): stop en la MITAD o en el borde OPUESTO (± 1 tick) × objetivo 1R, 2R o SALIDA (hora fija).
- Perillas: cuerpo fuerte (≥ 55 % del rango de la vela; 0/1/cualquiera), volumen relativo ≥ 1,15 × media de 30 velas, ancho del
  rango/ATR14 (terciles, extremos), eficiencia de 60 velas de la sesión (cualquiera, ≥ 0,25, ≥ 0,42) e intento (1 o 2).
  **648 celdas por canal.**

## Períodos
DESC 2025-08-05..2026-03-31, OOS 2026-04-01..2026-09-30, holdout desde la sesión del 2026-10-01.

## Cómo se refuta
0 nominadas por FDR en DESC sin pistas que repliquen; media ≤ 0 en OOS u holdout. **Refutación específica de la reentrada**: si el
intento 2 no supera al 1 en las celdas nominadas, la regla de reentrada queda refutada para esa ventana.

## Controles
`tests/research/test_paquete_20261031.py`: causalidad, paridad lote/escalar, ruido sin efecto y efecto plantado (deriva tras el
primer quiebre: la ruptura gana más que sobre ruido).
