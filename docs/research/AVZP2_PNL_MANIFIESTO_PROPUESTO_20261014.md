# AVZP2-PNL-ES — manifiesto PROPUESTO (no ejecutado) — 2026-10-14

**STOP: no se corre nada sobre retornos hasta el OK de Nico.** NORTH_STAR `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Cadena del candidato: geometría/lifecycle ✔ → información ✔ (MNQ + réplica en ES) → **P&L bruto** → edge neto/replicado.

## Justificación económica
Un racimo largo (≥1.000 velas de 25t, franja 30–45 ticks) es inventario acumulado; al salir, la dirección de la tendencia previa se impone ≈ +5–7 pp más que en
una consolidación comparable, pero **con compresión del recorrido** (mediana de MFE ≈ 3 ticks en ES). Pregunta económica única: ¿ese sesgo, con ese recorrido, supera la
fricción de ES?

## Cómo podría refutarse (declarado antes)
Expectativa neta por operación con límite inferior del IC (bootstrap estacionario clusterizado por sesión, `PrimaryCI` de G2-A1) ≤ 0 en la muestra sellada de confirmación.
**Prior: más probable negativa que positiva** (MFE mediana 3 ticks vs fricción ≈ 1,5–2,5 ticks).

## Hipótesis y espacio efectivo
- Instrumento: **ES** (potencia comprobada). NQ no entra (potencia insuficiente en la réplica).
- Evento: primer cierre de vela fuera de la franja del racimo con dirección = signo de tendencia 500 velas; una entrada por racimo.
- Celdas de racimo: **6/1000/30 y 6/1000/45** (2).
- Salida: bracket TP ∈ {3, 5, 8} ticks, SL ∈ {4, 8} ticks, salida por tiempo a 200 velas o fin de sesión (3×2 = 6).
- **Número efectivo de hipótesis ≤ 12** (celdas × brackets; correlacionadas, se reporta N bruto = 12 para DSR/Holm).
- Entrada: a mercado en el primer tick posterior al cierre (fill al ask/bid del tick); variante pasiva (límite en el borde del racimo con fill sólo si el precio lo atraviesa) como
  **análisis separado declarado**, no como celda adicional libre.

## Costos (propios de ES, sin transportar de otros instrumentos)
- Spread: medido en la release por tick (bid/ask) en el momento del fill.
- Comisión + fees por lado: **DATO FALTANTE — lo debe dar Nico** (broker/plan reales). Mientras tanto se reporta con $2,50 y $4,50 round-turn como sensibilidad.
- Slippage: 0 ticks en límites favorables, 1 tick adicional en stops.

## Partición de datos
- Descubrimiento de brackets: ES 09-25, 12-25, 03-26. **Confirmación sellada, una sola apertura:** ES 06-26 y 09-26. Holdout (≥ 2026-10-01) fuera de la release; no se abre.
- Las celdas de racimo y el criterio ya fueron observados en información (MNQ/ES); lo que se juega ahora es P&L.

## Criterios de decisión
1. Bruto > 0 y neto > 0 en descubrimiento con los costos centrales.
2. En confirmación: neto/operación > 0 con `PrimaryCI.lower > 0`, DSR con N = 12, y sensibilidad a +1 tick de slippage sin cambio de signo.
3. Si falla (2): se archiva como `SIN EDGE NETO` con el MDE de la expectativa por operación; no se rescata con otros brackets.

## Datos faltantes antes de ejecutar
- Comisiones reales de ES (Nico). Confirmar si se opera ES o MES (misma señal, otra fricción por contrato).
- Aprobación de la política de liquidez de la release (hoy propuesta).

## Aporte esperado al referente
Cierra con evidencia el ítem 1 de la jerarquía (expectativa neta) para la única línea con información replicada en dos instrumentos, o la mata a bajo costo.
