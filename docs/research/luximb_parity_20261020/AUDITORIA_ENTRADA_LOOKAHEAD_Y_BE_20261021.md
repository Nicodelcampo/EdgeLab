# Auditoria de entrada / look-ahead + variante con break even (regla del visor, NQ) — 2026-10-21

Estado: VIGENTE

Pedido de Nico: "probá agregarle break even a los 2,5 R y además revisá bien que la entrada sea exactamente donde está el
precio y que no haya look ahead".

## Auditoria (punto por punto, verificado contra el codigo)
| punto | estado |
|---|---|
| Deteccion del impulso (`detect_act`): activacion con ATR de la vela anterior y datos <= j | OK |
| **Impulso en curso al llegar un hueco > 30 min (cierre de sesion): se descartaba sin emitirse** | **SESGO DE SUPERVIVENCIA — corregido**: ahora se emite (why=3; fin de datos why=4). En NQ 09-26 aparecen 17 impulsos mas (6.372 -> 6.389) pero **ninguno cumplia los criterios**: 150/150 y 99/99 marcas identicas en 09-26 y 12-25. La copia sigue verificada contra el detector original para why 1-2. |
| Marca en la vela M1 kb: extremo, zonas cruzadas (`crossed` usa velas <= kb), velas 25t del tramo (<= minuto de kb) | OK |
| Umbrales causales: solo impulsos cerrados (jconf) **antes** de kb | OK |
| Zonas: existen desde el cierre de su vela creadora; cruce solo con velas posteriores | OK |
| **Entrada**: cierre de la vela M1 de marca = ultimo precio operado antes de tc; realista con 1 tick en contra | OK (el visor entraba en X hasta el 20/10 — ya corregido) |
| Simulacion: primera vela 25t con hora >= tc; misma vela SL y TP -> SL; BE se activa al cierre de la vela que lo toca | OK (conservador) |
| Limite conocido (no look-ahead, sesgo de omision): las operaciones de la vela 25t que empezo antes de tc y sigue despues no se usan (segundos). Afecta en ambos sentidos; la forma correcta es simular con ticks. | pendiente (bajo) |

## Variantes (entrada realista, $4,50 + 1 tick, tope 240 min) — pts NQ por operacion
| periodo | n | TP 1,0 / SL 0,20 | TP 1,25 / SL 0,15 | TP 1,25 / SL 0,15 / **BE 2,5 R** |
|---|---|---|---|---|
| 09-25 | 20 | -6,4 | -2,8 | -1,3 (BE 3) |
| 12-25 | 99 | +3,7 | +3,8 | +5,5 (BE 21) |
| 03-26 | 100 | +5,7 | +7,9 | +7,2 (BE 23) |
| 06-26 (abr-jun) | 130 | +6,2 | +8,0 | +3,5 (BE 26) |
| 09-26 (diseno) | 150 | +5,6 | +6,8 | +4,8 (BE 29) |
| **total 499** | | **+4,95** | **+6,34** | **+4,82** |
- El BE en 2,5 R no mejora en total: ayuda en 09-25/12-25 y empeora en 06-26/09-26 (corta operaciones que luego llegaban).
- TP 1,25 / SL 0,15 da algo mas, pero fue elegida mirando 09-26 (riesgo de sobreajuste; M11 mostro que el ranking de
  parametros no se sostiene). La comparacion honesta para el holdout es la regla original (TP 1,0 / SL 0,20) salvo decision.
- Visor con BE (sin costos, sin tope) en 09-26: TP 21 / SL 99 / BE 30, +76 R, +799 pts — coincide con la version realista
  (TP 21 / SL 100 / BE 29) salvo 1 operacion cerrada por tiempo.

## Variante pedida: SL +50 % y TP +10 % sobre TP 1,25 / SL 0,15 -> TP 1,375 / SL 0,225 (visor por defecto desde 21/10)
| periodo | n | con BE 2,5 R | sin BE |
|---|---|---|---|
| 09-25 | 20 | -11,6 | -13,2 |
| 12-25 | 99 | +1,5 | +1,0 |
| 03-26 | 100 | +5,9 | +4,6 |
| 06-26 | 130 | +8,3 | +10,4 |
| 09-26 (diseno) | 150 | +8,6 | +10,9 |
| total 499 | | +5,73 | +6,58 |
| solo descubrimiento (219) | | +2,29 | +1,37 |
Comparado con la regla original (TP 1,0 / SL 0,20: descubrimiento +3,73, total +4,95): la variante mejora los periodos
2026 (cerca del de diseno) y empeora el descubrimiento 2025 — firma tipica de ajuste al periodo mirado.
