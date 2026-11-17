# SessionOpenMomentum (QuantLab MT5): resultado (2026-11-16)

Estado: RESULTADO — pre-registro `PREREGISTRO_MEDICION.md` (+ enmienda 1: la primera corrida se descartó por llenado optimista del motor en
gaps; motor corregido). Cifras: `RESULTADO_SOM.json`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Nada miró el holdout.

## Resultado: **pasa en NQ (las dos celdas)**; ES sólo régimen reciente; YM no
| Prueba | A 2012–2019: n / R (p) | B 2020 → 2026-09: n / R (p) | Reciente (ago-25 →) | Fricción mediana |
|---|---|---|---|---|
| NQ sin_eod (de fábrica) | 1.559 / +0,043 (0,068) | 1.517 / **+0,089** (< 0,001) | 254 / +0,167 | 0,011 R |
| NQ eod (cierre 15:55 NY) | 1.937 / +0,022 (0,148) | 1.735 / **+0,064** (0,001) | 297 / +0,148 | 0,011 R |
| ES sin_eod | 1.397 / −0,023 | 1.505 / +0,044 (0,044) | +0,127 | 0,029 R |
| ES eod | 1.664 / −0,024 | 1.733 / +0,020 (0,17) | +0,094 | 0,029 R |
| YM (las dos) | ≈ 0 | −0,02 / −0,04 | −0,08 / −0,09 | 0,02 R |

- Nominadas por BH q 0,10 sobre 6 y positivas en los dos tramos: **NQ sin_eod y NQ eod**. ES es régimen reciente (B > 0 sólo), YM no.
- NQ año por año: 11 de 15 años positivos en las dos celdas. Con cierre diario ganan los dos lados (largos +0,056, cortos +0,027 R); sin cierre
  diario el lado largo carga más (+0,111 vs +0,017): parte es la deriva del Nasdaq al quedar abierta varios días.
- Acierto ≈ 50 %; ganadora mediana +0,47 R, perdedora −0,73 (eod) / −1,0 R. El stop de 8 × ATR M5 es grande frente a la fricción (0,011 R):
  es la palanca F-STOP-GRANDE-FRENTE-A-FRICCION, y el trailing lento deja correr (F-SALIDA-TECNICA-REGALA-LA-GANANCIA). Frente a DOS_VELAS
  (misma idea de apertura, objetivo 1:1, ≈ 0) lo que cambia es la salida.

## QLB_K_XAUUSD_3x: no se mide (motivo en el pre-registro: gatillos inferidos; cambio de mes ya refutado).

## Integridad: dos arreglos en la traducción
1. `quantlab_mt5/indicators.load_ohlc_data` cortaba en 2026-10-01 00:00 UTC; el holdout abre 2026-09-30 22:00 UTC → 2 h de fuga. Ahora usa
   `edgelab.holdout.HOLDOUT_APERTURA_UTC_ISO`.
2. `session_open_momentum`: llenado del stop a la apertura si hay gap y stop válido en la vela de entrada (antes, optimista).

## Siguiente (propuesto)
Holdout de la familia SOM (una apertura): NQ, celda `eod` (no queda abierta el fin de semana, apta para prop), regla congelada, spot USATECH
sellado 2026-10-01 → 2026-11-13; luego forward con el comando bajo demanda. Potencia baja en 31 sesiones (≈ 31 operaciones, MDE ≈ 0,3 R):
decide más el forward. Antes: correlación con la v2, la Cartera B y Franklin (comparten la apertura de NY).

## Celda `sin_finde` (enmienda 2: mantiene de noche, cierra el viernes 15:55 NY) — pasa en NQ, va al holdout
| | A 2012–2019 | B 2020 → 2026-09 | Reciente |
|---|---|---|---|
| NQ | 1.680 / +0,046 (p 0,039) | 1.602 / **+0,075** (p 0,001) | 268 / +0,162 |
| ES | −0,031 | +0,030 (p 0,10) | +0,097 |
| YM | −0,007 | −0,021 | −0,089 |

Correlación diaria (ago-25 → sep-26) de SOM sin_finde NQ con: v2 0,03 · Cartera B 0,30 · Franklin 0,42 (misma dirección el 63 % de los días
en que operan los dos). Mensual: −0,09 a 0,18. Diversifica a la v2; con la B y Franklin comparte la apertura de NY.

## Holdout (apertura única, `ACTA_HOLDOUT_SOM.md`, 2026-10-01 → 2026-11-13): NO_CONCLUYENTE, a favor
29 operaciones NQ, **R +0,16 por operación**, acierto 66 % (18 por trailing, 6 en el stop inicial, 5 cierres de viernes); t 0,70, p 0,24.
Fisher con el desarrollo (0,039): **0,053** — queda justo arriba de 0,05: NO_CONCLUYENTE por la regla del acta, con el signo a favor y el
doble del efecto de desarrollo. Decide el forward (`tools/seguimiento_forward.py`). Cifras: `seguimiento/RESULTADO_HOLDOUT.json`.

## Revisión de Antigravity contra el MT5 Tester (2026-11-17, `REVISION_ANTIGRAVITY_20261117.md`) y correcciones
- Fidelidad: USATECH M5 2024-01 → 2026-09, 616/623 operaciones comunes con 100 % de lado, entrada, SL inicial y motivo de salida.
- **Corregido**: el EA bloquea el día si a las 16:30:00 hay posición abierta, aunque cierre por SL dentro de esa vela; la traducción cerraba y
  entraba igual (7 casos). Con la corrección: **617/617 operaciones del Tester presentes** (la única extra es el 29-sep, fuera de la corrida del
  Tester). Re-medido: `sin_finde` NQ A +0,046 (p 0,04) / B **+0,079** (antes +0,075) / reciente +0,169; sigue pasando. Holdout re-ejecutado en la
  misma apertura: idéntico (29 ops, +0,16 R, Fisher 0,053, NO_CONCLUYENTE).
- Se mantiene a propósito: llenado del stop a la apertura cuando hay gap. El Tester llena al SL exacto (simula CFD); para futuros la orden
  stop se ejecuta al primer precio → regla conservadora y realista para lo que operamos. Diferencias menores no corregidas: trailing activado
  dentro de la vela de entrada en 30/617 operaciones (M5 no tiene el orden intravela).
- Confirmado: 11 símbolos más de SQX en UTC (agregados a `EN_UTC`/`M1_EN_UTC`); `stop_price` de T es el stop activo (consistente con H2).
