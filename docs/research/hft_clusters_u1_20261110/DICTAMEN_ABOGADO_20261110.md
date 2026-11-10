# Dictamen del abogado del diablo: `U1-HFT-CLUSTERS-GRILLA` y `U1-HFT-CRUZADO`

Estado: VIGENTE (2026-11-10). Audita `PROPUESTA_AUDITORIA_U1_HFT_CLUSTERS.md` y `edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py`
(commit `640d5d7e`). **Veredicto: la grilla de 20.736 celdas NO se corre.** Se reemplaza por `PREREGISTRO_E0_E_INFORMACION.md`.

## Por qué no
1. **Repite `F-SELECCION-EN-GRILLAS-GRANDES`:** miles de celdas sobre ~9 meses de un activo, eligiendo la mejor. Antecedente directo:
   U1-RACIMOS-GRILLA-NQ-R, 0 de 20 pistas confirmadas y canasta −0,004 R.
2. **La fricción la mata por diseño (`F-STOP-GRANDE-FRENTE-A-FRICCION`):** con 1R = ancho del cluster (2 a 12 puntos de NQ) y fricción de
   1,55 puntos, cada operación paga 0,13 a 0,77 R; con el piso de 4 puntos propuesto, 0,39 R.
3. **El lado U1 no existía:** la alineación a 1 minuto, la regla de 1R y los controles estaban sólo en el documento.

## Vector 1 — fugas
- `inmutable_en_detect=True` (opción B) es correcta y suficiente.
- La sección 3.3 habilitaba el cluster «a partir de la barra cuyo cierre es ≥ t_ns»: esa barra contiene precios anteriores a la
  detección. Regla correcta: sólo ticks (o barras cuya APERTURA sea) posteriores a `t_ns`.
- `escala_vol_arr` del almacén usa el rango completo de la barra de detección (hasta 4 ticks posteriores): usar la barra anterior.
- Sin `session_ids` el almacén corta por día UTC, no por sesión CME.
- La familia H (percentil causal) depende de dónde empieza el dato (la historia se reinicia por trimestre).
- Faltaba el test de causalidad por prefijo; los umbrales visuales se ajustaron mirando gráficos del 8-nov (período de holdout).

## Vector 2 — vigencia
En segundos de reloj y fija. En barras de 5 ticks la definición cambia con la actividad (300 barras son del orden de 1 a 3 minutos
en horario activo de NQ, no 15 a 45: a verificar en el E0). Invalidación como regla, no como eje.

## Vector 3 — 1R
Stop = max(ancho + 2 ticks por lado, fricción / 0,08) → 19,5 puntos en NQ. Todo en bruto y en neto. Ancla POC afuera (achica el stop).

## Vector 4 — grilla
E0 sin retornos obligatorio, para quedarse con UNA definición por activo por regla mecánica. Sin barrido de ejecución.

## Qué se corre en su lugar
`PREREGISTRO_E0_E_INFORMACION.md`: E0 en NQ, ES, YM y GC; después una sola hipótesis (rebote en el borde real contra placebo
desplazado, en bruto); P&L sólo si pasa. `U1-HFT-CRUZADO` y las expansiones quedan afuera de esta vuelta.
