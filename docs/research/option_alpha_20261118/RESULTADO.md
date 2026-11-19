# OPTION-ALPHA en M1 de futuros 2006–2025: ninguna regla pasa DESC (resultado, 2026-11-18)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (enmendado antes de correr: K49 y filtros fuera). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `DESC.json`, `CALIBRACION.json`, `CORRIDA.json`,
`OPS_DESC_REP.csv.gz`. Familia `OPTION_ALPHA_A5` (13 pruebas contadas), etapa EF3.

## 1. Veredicto: REFUTADA en DESC
- Ninguna de las 13 pruebas (8 reglas + 5 contrastes contra su control) pasa BH q 0,10 en DESC (ES + NQ + YM, meses DESC de A5 2006–2025).
- **R neto negativo en las 8 reglas** (−0,03 a −0,20 R por operación con costos canónicos). La fricción media en R va de 0,04 (OA7) a
  0,20 (OA2); sólo OA3 y OA7 quedan por debajo de 0,08 R, y esas dos tienen bruto ≈ 0.
- REP no se leyó: no hubo nominadas. El holdout A5 de la familia sigue sellado.

| Regla | n DESC | R bruto | p | años + | R neto | fricción R | bruto 2006–2011 |
|---|---|---|---|---|---|---|---|
| OA1 Taco 13:45 (vol calma) | 6.129 | +0,011 | 0,29 | 50 % | −0,108 | 0,12 | +0,021 |
| OA2 Sandwich 13:45 | 2.677 | +0,006 | 0,41 | 50 % | −0,199 | 0,20 | +0,011 |
| OA3 ORB 60 hold | 6.740 | +0,002 | 0,46 | 45 % | −0,075 | 0,08 | −0,007 |
| OA4 ORB 60 mié/vie | 3.067 | +0,014 | 0,19 | 65 % | −0,127 | 0,14 | +0,010 |
| OA5 ORB 60 + Daily Bias | 3.962 | +0,052 | 0,06 | 65 % | −0,093 | 0,15 | +0,053 (no calibra contra ticks) |
| OA6 HA + EMA + MACD 10 m | 7.311 | +0,055 | 0,04 | 55 % | −0,125 | 0,18 | +0,064 |
| OA7 compra del retroceso > SMA200 | 2.464 | +0,005 | 0,36 | 58 % | −0,031 | 0,04 | −0,032 |
| OA8 Theta Fly / fade de contención | 4.454 | −0,032 | 0,94 | 40 % | −0,198 | 0,17 | −0,041 |

Contrastes contra el control: OA1−OA1N +0,056 (p 0,08), OA5−OA5N +0,062 (p 0,09), los demás ≈ 0 o negativos: los filtros de
Option Alpha (calma, miércoles/viernes, contención) no agregan nada medible en el futuro.

## 2. Lectura
- Lo que paga en Option Alpha es la prima de opciones (VRP, theta), que un futuro lineal no cobra; sus disparadores de entrada, solos, no
  tienen dirección. Es lo que el pre-registro declaraba como refutación (§3).
- Lo más parecido a una señal (OA5 y OA6, ~+0,05 R bruto, igual en 2006–2011) no paga la fricción de sus stops (0,15–0,18 R) y OA5 además
  no calibra contra ticks. No se rescata ensanchando stops sin una curva bruto–stop (lección F-LUXIMB-EJECUCION-TIMING).
- Alcance de la muerte: estas 8 traducciones con su ejecución (obj/stop/cierre RTH) en ES, NQ y YM. No dice nada de vender opciones.
