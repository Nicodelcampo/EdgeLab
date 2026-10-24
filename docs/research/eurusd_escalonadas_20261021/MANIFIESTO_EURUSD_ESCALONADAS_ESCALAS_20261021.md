# Manifiesto EURUSD-ESCALONADAS-ESCALAS — misma grilla que MNQ (648 celdas), descubrimiento + replica unica

Estado: PRE-REGISTRADO antes de correr. Pedido de Nico 2026-10-21: "revisa el historial de analisis que se le habia hecho al
nq y mnq sobre estos picos, y aplicales los mismos o similares al eurusd". Familia NUEVA (EURUSD), no transporta resultados.
Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Antecedente: MNQ-ESCALONADAS-ESCALAS (`RESULTADO_MNQ_ESCALONADAS_ESCALAS_20260930.md`): 0/648 sobreviven max-T.

## Calibracion (target-free, solo tamanos de vela)
Rango medio de vela en ticks propios: ES 1,08 / 3,39 / 6,57; NQ 9,25 / 25,71 / 48,49; **EURUSD (tick 0,00001) 9,19 / 26,26 /
50,21** (25t / 150t / 500t). EURUSD en ticks de 0,00001 coincide con NQ/MNQ -> se usan **exactamente los parametros de MNQ**:
familia PLANAS escalada x4,5 / x12,42 / x23,49 desde ES, SL base 5 / 14 / 26 ticks, confirmacion por precio escalada igual.

## Grilla (identica a MNQ): 6 entradas (velas_w2, velas_w1, precio_stop, precio_lim50, precio_lim25, anticipada_2p) x
3 escalas (25t/150t/500t) x SL (x1, x2, x4 del base) x TP (1,2,3,5,10R) x BE (0/1/2R, BE < TP) = **648 celdas, max-T sobre 648**.
Mecanica, horizonte (1.500 velas o fin de sesion), control (3 por evento, otras sesiones, franja +/-30 min, tercil de
volatilidad, misma mecanica) y bootstrap por sesion: identicos a `tools/mnq_escalonadas_grid.py`.

## Datos y costos
Dukascopy EURUSD (`E:/EdgeLab/data/eurusd_ticks.parquet`: mid `last`, bid, ask; velas 25t = 25 cotizaciones). Sesion FX
desde 17:00 ET. **Descubrimiento: ago-2025 .. ene-2026** (mismos 6 meses que MNQ). **Replica unica: abr-jun 2026**, solo
celdas que sobrevivan con R neto > 0. Holdout (>= 2026-07-01): no hay datos ni se toca.
Costos: spread real via bid/ask; comision RT **3,5 ticks (0,35 pip = $35 por millon)**.
## Justificacion y refutacion
Igual que MNQ: absorcion escalonada que cede; con velas grandes el costo fijo pesa menos. Refuta: ninguna celda supera al
control tras max-T, o las que lo superan tienen R neto <= 0.
