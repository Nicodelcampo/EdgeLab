# Resultado DESC — estrategias de reels (Kemet, Italian Founder, AlphaZone; FlexingJoe pendiente)

Estado: RESULTADO (2026-11-08). Pre-registros: `PREREGISTRO.md` y `../gap_continuacion_20261108/PREREGISTRO.md`. Medido en R neto
con costos canónicos; CFD Dukascopy 2023-01 → 2026-03 (total y reciente ≥ 2025-07) y futuros jul-2025 → mar-2026 (descriptivo).

| Familia | Pruebas | Nominadas FDR | Media R (total) | Mejor celda total | MDE mediano | IC90 inf > 0 |
|---|---|---|---|---|---|---|
| GAP_CONTINUACION (Kemet) | 240 | 0 | −0,149 | +0,005 | 0,13 | 0 / 296 |
| EMA_VWAP (AlphaZone) | 36 | 0 | −0,193 | −0,026 | 0,06 | 0 / 54 |
| ORO_RANGO (Italian Founder) | 8 | 0 | −0,050 | −0,013 | 0,11 | 0 / 12 |
| MARTES_DEBIL (Italian Founder) | 4 | — | — | — | — | 25 ops en 3 años: no evaluable |
| ORB_EMA20 (FlexingJoe, v3 corregida) | 24 | 0 | −0,021 | +0,023 (NQ, stop opuesto, 1R) | 0,09 | 0 / 36 |

Lectura:
- **Kemet, continuación del gap grande no rellenado: REFUTADA** con potencia en el canal total (1 de 120 celdas positiva, MDE 0,13 R).
  En reciente y futuros también negativa. El «2 de 3 no vuelve» puede ser cierto y aun así no pagar operarlo a favor desde las 10:00/10:30.
- **EMA9 + VWAP: REFUTADA** (miles de operaciones, MDE 0,06 R, todas las celdas negativas en total). La única positiva es NQ reciente
  primeras 2 h, stop en la mecha (+0,136, IC90 [−0,07, +0,38], q 1): no es pista (IC inferior < 0) y el total es negativo.
- **Oro, rango de Londres: SIN EFECTO** (todas ≈ 0 a −0,08 R; el PF 1,19 del reel no sobrevive costos ni R). En futuros GC jul–mar
  levemente positiva (+0,04 a +0,09, IC cruza cero): descriptivo, no rescata.
- **Martes débil: NO EVALUABLE** (la regla dispara ~8 veces por año). Sin potencia no se mata ni se promueve.
- Ninguna celda va a réplica (ni nominadas ni pistas con IC90 inferior > 0). Holdout intacto.
- **ORB + EMA20: SIN EFECTO DETECTADO** (v3, con la enmienda de EMA continua y vela de entrada sólo con stop; módulo sha256
  `e97deb2ddf60…`). Lo único coherente: **NQ con stop en el extremo opuesto del rango** es positivo en los tres canales (total +0,013 a
  +0,023 R, reciente +0,02 a +0,07, futuros jul–mar +0,04 a +0,075; IC90 inferior −0,02 a −0,07). ES no. Es chico (≈ fricción por
  ganar) y ninguna cota inferior pasa cero: no va a réplica por las reglas (ni nominada ni pista). Queda anotado como observación de NQ,
  sin potencia para efectos < 0,07 R; no se rescata con variantes elegidas mirando esto.
