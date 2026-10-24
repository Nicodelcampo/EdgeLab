# Tablero del visor por periodo de NQ (simulacion "fin de caja en X -> TP en A, SL 1/5") + version realista

Estado: MEDIDO (exploratorio, pedido de Nico). Codigo `luximb_dash_periodos.py`; salida `DASHBOARD_VISOR_POR_PERIODO_NQ.json`.
Impulsos con la config del visor (`--modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60`).
Visor = entrada en X, sin costos, sin tope. Realista = cierre de la vela de marca -1 tick, $4,50, tope 240 min (M11).

| contrato (fechas) | particion | n | visor: acierto / R / pts | realista: acierto / pts por op [IC 95 % por dia] |
|---|---|---|---|---|
| 09-25 (ago-sep 2025) | descubrimiento | 20 | 25 % / +10 R / +184 | 10 % / -6,4 [-19,5, +14,7] |
| 12-25 (sep-dic 2025) | descubrimiento | 99 | 21,2 % / +27 R / +600 | 19,2 % / +3,7 [-5,3, +13,5] |
| 03-26 (dic 2025-mar 2026) | descubrimiento | 100 | 27,0 % / +62 R / +1.137 | 22,0 % / +5,7 [-3,2, +14,3] |
| 06-26 (mar-jun 2026) | replicacion (no usada para disenar) | 130 | 30,8 % / +110 R / +2.673 | 19,2 % / +6,2 [-2,7, +16,0] |
| 09-26 (jun-sep 2026) | replicacion (periodo de diseno) | 150 | 30,0 % / +120 R / +1.781 | 24,0 % / +5,6 [-2,5, +14,0] |
| 12-26 (18-25 sep 2026) | replicacion | 1 | 0 % / -1 R / -13 | -12,1 |
| **descubrimiento junto** | | 219 | | **+3,7 [-2,3, +9,7]** |
| **todo (499)** | | 499 | | **+4,95 [+0,55, +9,2]** |

Lectura:
- Realista positivo en 4 de 5 periodos con n >= 99 (~+4 a +6 pts NQ por operacion neto, ~$80-120); ningun periodo
  aislado excluye 0. El total excluye 0 solo sumando el periodo de diseno (09-26) y abr-jun.
- En ES (mismo periodo de descubrimiento, M11) da ~0: no transporta.
- abr-jun 2026 (06-26) no se uso para disenar y da +6,2: consistente, pero la replicacion de esta familia ya estaba
  declarada comprometida y esta mirada la consume. **La unica prueba limpia que queda es el holdout (>= 2026-10-01)**,
  una vez, con la regla exacta congelada aca (requiere datos de oct en adelante, hoy no descargados).

## Correccion del visor (2026-10-20)
El visor entraba en X (extremo), no en la confirmacion (error senalado por Nico). Ahora entra al **cierre de la vela M1 de confirmacion**; TP en A; SL = 1/5 de la distancia entrada-A. Con eso el tablero de NQ 09-26 da 150 op, TP 36 / SL 114, +66 R, +911,7 pts sin costos: coincide en TP/SL con la columna "realista" (que ademas descuenta 1 tick y comision y aplica tope de 240 min). La columna "visor" de la tabla de arriba corresponde a la entrada vieja en X.
