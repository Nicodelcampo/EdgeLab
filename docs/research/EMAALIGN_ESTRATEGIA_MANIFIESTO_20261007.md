# EMA-ALIGN — estrategia sobre EdgeLabEmaAlignment (EMA 200/500/2000) — MANIFIESTO (STOP: espera OK de Nico)

Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. **Búsqueda sobre P&L: no se corre
sin OK explícito.** Familia propia `EMAALIGN`: no hereda resultados de VTD-DIR (EMA 100 sobre otra señal).

## Indicador (fuente: `NinjaTrader 8/bin/Custom/Indicators/EdgeLabEmaAlignment.cs`)
EMA 200 / 500 / 2000 sobre el close. Señal al cierre de barra cuando entra una alineación estricta
(200>500>2000 = largo; 200<500<2000 = corto), alternada (no repite dirección sin una opuesta en el medio), tras
2.000 barras de calentamiento. Barras de **2 ticks** como en el chart de Nico.

## Estrategia
- **Entrada (3 modos):**
  - A: a mercado en la apertura de la barra siguiente a la flecha.
  - B: límite en la EMA naranja (200), esperando pullback.
  - C: límite en la EMA violeta (500).
  En B/C la orden se cancela si llega la señal opuesta o 2.000 barras sin fill.
- **Salida:** SL en ticks, TP = R × SL, BE opcional, cierre a fin de sesión, y cierre si aparece la señal opuesta.
- Simulación tick por tick: sin ambigüedad dentro de la barra. Los límites llenan sólo si el precio **atraviesa** el
  nivel por 1 tick (no basta con tocarlo).
- Sólo una posición a la vez. Señales en RTH; la posición puede seguir hasta el cierre de sesión.

## Grilla (número efectivo de hipótesis)
- SL ∈ {20, 40, 80} ticks × R ∈ {1, 2, 4} × BE ∈ {no, en +1R} = 18, × 3 modos de entrada = **54 celdas por instrumento**.
- 2 instrumentos (MNQ, MGC): **108 celdas** en descubrimiento, corregidas con **max-T**. El nulo usa la misma
  estrategia con la dirección de cada señal sorteada al azar (mismos tiempos, mismas EMAs para B/C), 2.000 sorteos.

## Descubrimiento / confirmación
- Por contratos y dentro de cada instrumento: los contratos más viejos son descubrimiento y los 2 más recientes antes
  del 2026-10-01 son confirmación.
- La confirmación corre **una vez**, con las celdas que pasaron y sin cambios. Pasa con Holm p ≤ 0,05 y expectativa
  neta > 0.
- Holdout (≥ 2026-10-01): no se abre.

## Costos (supuestos, no transportados)
MNQ: USD 1,90 ida y vuelta, más 1 tick de slippage por lado en stops y mercado. MGC: USD 1,90, más 1 tick por lado.
**Faltante:** fricción real medida.

## Justificación económica
La alineación de 3 EMAs marca una tendencia ya establecida. Si las tendencias intradía persisten, entrar a favor (mejor
aún en un pullback a la EMA) captura su continuación.

## Cómo podría refutarse
- Expectativa neta ≤ 0, o no mejor que dirección al azar (MDE publicado).
- Ganancia concentrada en una celda, un mes o 5 días.
- Antecedente en contra: REGIMEN-ESCALA (ES M1) no encontró persistencia de tendencia; VTD-DIR con EMA fue ruido.

## Riesgos
- Barras de 2t: el sesgo de la EMA 2000 cubre sólo unos minutos, así que es una señal de muy corto plazo y el costo
  pesa mucho.
- MNQ ya se usó mucho (no para esta señal). MGC tiene menos contratos.
- Muchas celdas pueden tener pocos trades en B/C.

## Decisión
Pasa a NT8 (estrategia compilable) y a prueba en simulación sólo si confirma. Si no, queda descartada para esta
definición.
