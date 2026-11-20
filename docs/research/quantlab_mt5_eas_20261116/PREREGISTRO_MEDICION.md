# QuantLab MT5 (SessionOpenMomentum y QLB): qué se mide y cómo (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de correr. Origen: traducción de Antigravity (commit 74e1cdb7) de dos EAs comerciales de QuantLab
reconstruidos por comportamiento (Strategy Tester + correlación con barras; el bytecode no se lee). La licencia de esos EAs es decisión de
Nico; EdgeLab sólo mide reglas. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF3** (regla
de fábrica, sin grilla). Corrida: `tools/quantlab_mt5_medir.py`.

## Triage
| EA | Decisión | Por qué |
|---|---|---|
| SessionOpenMomentum v2.2 | **Se mide** | Entrada (cierre de la vela M5 de las 09:30 NY vs EMA12), stop 8 × ATR14 M5 y trailing a la EMA120 desde +0,5 R verificados contra el Tester (14/14 y 8.917 modificaciones a 0,00 pips). Sólo el tamaño adaptativo es inferido, y en R no importa. |
| QLB_K_XAUUSD_3x | **No se mide** | Los gatillos de los slots 0 y 1 son **inferidos** (la traducción usa EMA10/50 + ATR5/ATR20 ≥ 0,85, que no salen del EA): medirlos sería medir una suposición. El slot 2 tiene verificada sólo la ventana de inicio de mes; el cambio de mes ya se midió y no supera al nulo (F-LIT-MACRO-CFD). En el Tester perdió en EURUSD (−4,1 %). |

## Regla (de fábrica, `SessionOpenMomentumConfig`)
NY abre 16:30 hora del servidor (= 09:30 NY; los CSV `*_M1_dukas` están en NY + 7); a las 16:35 (cierre de la primera vela M5) compra si el
cierre > EMA12 M5 y vende si <; stop inicial 8 × ATR14 M5 (1 R); sin objetivo; desde +0,5 R el stop sigue a la EMA120 M5 de la vela previa;
una posición a la vez. Celdas: `sin_eod` (de fábrica: puede quedar abierta días) y `eod` (`close_eod`, 22:55 servidor = 15:55 NY; la opción
del propio EA, coherente con «nada abierto el fin de semana»).

## Datos, costos y decisión
M1 Dukascopy USATECH → NQ, USA500 → ES, USA30 → YM; A = 2012-01-20 → 2019-12-31, B = 2020-01-01 → 2026-09-29; reciente 2025-08-05 →
2026-09-29 descriptivo. R = (pts − fricción canónica) / riesgo inicial (|entrada − stop inicial| = 8 × ATR14 M5). Pasa si R > 0 en A y en B, p de B
(bootstrap por sesión) sobrevive BH q 0,10 sobre 6 (2 celdas × 3 índices) y fricción mediana ≤ 0,08 R. Russell queda fuera (el CSV está en
UTC y la regla usa hora del servidor fija).

## Justificación económica / cómo podría refutarse
La dirección de los primeros 5 minutos de NY respecto de la media corta marca el flujo del día; el stop ancho y el trailing lento dejan correr
la tendencia. Antecedentes en contra: DOS_VELAS y ORB directo (momentum de apertura con objetivo fijo) sin ventaja; a favor: la salida que deja
correr (F-SALIDA-TECNICA-REGALA-LA-GANANCIA). Se refuta con R ≤ 0 en algún tramo o sin nominadas con MDE ≤ 0,10 R.

## Contador y linaje
Registro global `quantlab_mt5_20261116/SOM`: 6. Linaje SOM ← DOS_VELAS, ORB_EMA20.

## Enmienda 1 (2026-11-16, después de una primera corrida que se DESCARTA)
La primera corrida se miró y se descarta: el motor traducido llenaba el stop a su precio aunque la vela abriera más allá (gap; optimista,
sobre todo en `sin_eod`, que cruza noches y fines de semana) y no revisaba el stop en la vela de entrada. Se corrige el motor (llenado a la
apertura si hay gap; stop válido en la vela de entrada; los tests contra el Tester siguen pasando) y se relanza con la misma regla, celdas y
decisión. Cifras descartadas, para que consten: NQ sin_eod A +0,059 / B +0,093 R; eod +0,023 / +0,065; ES B +0,048 / +0,021; YM ≤ 0.

## Enmienda 2 (2026-11-16, regla de operación de Nico, antes de medirla): celda `sin_finde`
«Si se come el gap está bien siempre que no sea el del domingo»: se agrega la celda **`sin_finde`** = la de fábrica (mantiene la posición de
noche) pero **cierra el viernes a las 15:55 NY** (22:55 servidor). No sale de mirar resultados sino de la regla de no tener nada abierto el fin
de semana. Feriados de mitad de semana no se tratan. Se mide igual (NQ/ES/YM, A/B, R neto) y **es la celda que va al holdout** si NQ pasa con
la misma regla de decisión (R > 0 en A y B, p_B < 0,10 y fricción ≤ 0,08 R; prueba única, contador +3).
