# Paridad NT8 -> Python: ImbalanceDetectorLuxAlgoMTF (OG + VI) sobre NQ DEC26, M1

Estado: MEDIDO (target-free; geometria de zonas y velas, sin desenlaces ni retornos)
Fecha: 2026-10-20
Export: `E:\EdgeLab\data\nt8_oracles\luximb\luximb_NQ_DEC26_1_Minute_20261020_134014_{zones,m1bars}.csv`
(1.507 zonas, 43.464 velas M1, 2026-08-02 19:01 a 2026-09-17 17:01 hora NT8). Parametros en el encabezado del CSV:
OG y VI activos, FVG apagado, sin filtro de ancho, Extend 500 min.
Codigo: `tools/luximb_parity/parity_luximb.py` (detector Python = replica de `OnBarUpdate`).

## Resultado
| capa | que mide | resultado |
|---|---|---|
| A | detector Python sobre las velas M1 que exporto NT8 | **1.507 / 1.507 (100 %)**, misma geometria |
| B | velas M1 construidas desde ticks vs velas de NT8 | **OHLC igual 99,98 %** en 39.795 velas comunes; volumen 99,97 % |
| C | detector sobre velas desde ticks vs zonas de NT8 (todo) | 91,2 % (1.374 / 1.507) |
| C limpia | igual, solo zonas cuya vela y vela previa coinciden en ambas series | **1.373 / 1.373 (100 %)** |

Las 134 zonas fuera de la capa C limpia estan en velas que faltan en la fuente de ticks local
(sobre todo 2026-09-14 a 09-17: 121 zonas), no en diferencias de logica.

## Hallazgos que importan para research
1. **El grafico DEC26 de NT8 esta back-adjusted antes del roll.** Hasta la sesion del 2026-09-13 22:00 UTC
   NT8 muestra datos de **NQ 09-26 + 299,25 puntos**; despues muestra NQ 12-26 real. Los precios de las
   zonas de ese tramo estan corridos 299,25 puntos respecto del contrato que realmente opero.
   Para el visor y para medir: o se exporta por contrato sin merge, o se resta el offset por tramo.
2. **Convencion de velas:** marca de CIERRE; un tick en HH:MM:00.000 abre la vela nueva.
3. **El export quedo sin cerrar:** cada CSV termina con una linea truncada (se descarta al leer).
   Para exports futuros: quitar el indicador o cerrar el grafico antes de leer (dispara `State.Terminated`).
4. **2026-08-27:** 83 % de igualdad de velas ese dia (unico dia < 99 %); sin zonas afectadas en la capa limpia.
   Causa no investigada (probable diferencia de ticks entre fuentes).

## Como podria refutarse
Una corrida sobre otro tramo/contrato sin merge donde la capa C limpia baje de ~100 %, o zonas NT8 que
aparezcan en velas iguales y Python no reproduzca.

Aporte al referente: el detector LUX-IMB queda con paridad exacta medida (logica 100 %, punta a punta 100 % donde hay datos),
y se detecta el corrimiento de 299,25 puntos del back-adjust antes de usar sus zonas en el visor o en una medicion.
