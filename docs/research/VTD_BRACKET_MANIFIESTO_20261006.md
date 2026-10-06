# VTD-BRACKET — estrategia sin dirección sobre marcas VolTicksDef — MANIFIESTO DE CAMPAÑA (STOP: espera OK de Nico)

Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. **Búsqueda sobre P&L: no se corre
sin el OK explícito de Nico.**

## Hipótesis
Después de una marca VTD, el precio se mueve más que en un momento cualquiera (VTD-VOL-1, robusto a AVCL-PRE: 150t
+0,049), pero el lado no es predecible (VTD-DIR, VTD-VELA). Una entrada **bilateral** (la que se dispare primero) captura
el movimiento sin necesitar dirección. Pregunta: **¿la expectativa neta es > 0, y mayor que la de la misma estrategia
en barras al azar?**

## Justificación económica
Los lotes grandes (contratos por tick altos) anticipan actividad de precio inmediata. Si el movimiento siguiente es
mayor que el típico, un bracket de ruptura gana el tramo largo y corta el corto con el stop.

## Cómo podría refutarse
- Expectativa neta ≤ 0, o no mayor que la de barras al azar (MDE publicado).
- Una ganancia que dependa de una sola celda o de un instrumento.

## Estrategia (congelada salvo la grilla declarada)
- **Señal:** marca VTD (parámetros por defecto, barras de 150t), sólo RTH y sin posición abierta.
- **Entrada:** al cierre de la barra marcada se colocan un buy stop en close + k y un sell stop en close − k. El primero
  que se ejecuta abre la posición y cancela el otro. Si ninguno se ejecuta en 10 barras, se cancela.
- **Salida:**
  - stop-loss a SL = 1 ATR(14) desde la entrada;
  - take-profit a R × SL;
  - cierre por tiempo a las 50 barras o a fin de sesión.
- **Simulación a nivel tick:** se recorren los ticks reales, así que no hay ambigüedad dentro de la barra. Las stops se
  ejecutan en el primer tick que toca el nivel, más el slippage.

## Grilla (número efectivo de hipótesis)
- k ∈ {0,5; 1,0} ATR × R ∈ {2, 3} = **4 celdas**.
- Descubrimiento en 2 instrumentos (MNQ, ES): **8 celdas**, corregidas con **max-T** (nulo: las mismas reglas sobre
  barras al azar de la misma franja y el mismo régimen de amplitud, 2.000 sorteos de conjuntos de barras).
- Confirmación: la celda (o las celdas) que pasen, **una sola vez y sin cambios**, en YM, RTY y MGC.
- Contador global: +8 (descubrimiento) + n (confirmación).

## Métricas
- Expectativa neta por trade (ticks y USD), con IC por bootstrap de sesiones.
- Diferencia contra barras al azar.
- Win rate, payoff, MAE/MFE, drawdown, n de trades, concentración (sin el mejor mes y sin los 5 mejores días).

## Costos (no se transportan entre instrumentos)
| instrumento | comisión ida y vuelta | slippage supuesto |
|---|---|---|
| MNQ | USD 1,90 | 1 tick por lado en stops |
| ES | USD 4,50 | 1 tick por lado |
| YM | USD 4,50 | 1 tick por lado |
| RTY | USD 4,50 | 1 tick por lado |
| MGC | USD 1,90 | 1 tick por lado |

**Dato faltante:** no tenemos la fricción real medida por instrumento. Los costos de arriba son supuestos
conservadores. Si el resultado depende del slippage, hace falta una medición de ejecución real.

## Riesgos declarados
- **Datos ya usados:** MNQ (toda la campaña VTD) y ES/YM/RTY/MGC (VTD-VELA, sólo dirección, no P&L). No hay datos
  vírgenes salvo el holdout (≥ 2026-10-01), que **no se abre**. La confirmación en YM/RTY/MGC es OOS respecto del P&L,
  pero no respecto de VTD como tal.
- Tick por tick sobre ES es pesado: hay que cuidar la memoria (un contrato a la vez).
- La pausa de las 16:00 CT y los fines de sesión fuerzan cierres. Se cuentan como salida por tiempo.
- En barras de 150t el ATR varía mucho con la hora. El ATR se calcula sobre las 14 barras previas, sin mirar adelante.

## Decisión
- **Pasa al siguiente escalón** (más datos, ejecución real, holdout) sólo si:
  - pasa max-T en descubrimiento;
  - confirma con p ≤ 0,05 (Holm) y expectativa neta > 0 en la confirmación;
  - no depende de un mes ni de 5 días.
- Si no: VTD queda como sello informativo, sin estrategia bilateral rentable con estos parámetros.
