# Prompt de extracción — CerebroSSRN (v1)

Instrucciones canónicas para extraer el destilado conceptual de un paper del
corpus SSRN de trading cuantitativo. Este prompt es el análogo del
PROMPT_EXTRACCION del CerebroJLP, adaptado al dominio quant. La extracción es
LA única lectura completa del corpus: lo que no se capture acá no existirá
para el Cerebro.

## Contexto y propósito

El destilado alimenta un grafo de conocimiento cuyo fin es **mejorar un
ecosistema real de backtesting** (quantlab + VectorBT sobre futuros del ES:
zonas de liquidez HFT, order flow, excursiones intradía, minería con Optuna,
validación IS/OOS). Extraé pensando en un trader-quant que pregunta: *"¿qué
de este paper me sirve para diseñar, testear o auditar una estrategia?"*

## Salida requerida

Un único JSON válido (UTF-8, sin comentarios) con EXACTAMENTE este schema:

```json
{
  "doc_id": <int>,
  "titulo": "<título del paper>",
  "resumen_operativo": "<2-4 frases: qué aporta este paper a un trader cuantitativo. En castellano.>",
  "calidad_paper": "alta|media|baja",
  "conceptos": [
    {
      "nombre": "<nombre canónico en inglés, singular, sin siglas salvo universales>",
      "tipo": "concepto|estrategia|metodo|metrica|fenomeno|riesgo_metodologico|dato",
      "definicion_en_contexto": "<1-3 frases en castellano, fiel al uso del paper>",
      "relaciones": [
        {"tipo": "<ver tipos cerrados>", "objeto": "<nombre canónico del otro concepto>"}
      ],
      "cita_textual": "<frase EXACTA del paper (inglés), máx ~40 palabras, que ancla el concepto>"
    }
  ],
  "hallazgos": [
    {
      "afirmacion": "<el resultado empírico en castellano, específico y falsable>",
      "mercado": "<activo/mercado: ES futures, US equities, BTC, FX EURUSD, ...>",
      "periodo": "<ventana temporal del dato, ej. 2010-2020, o 'no especificado'>",
      "magnitud": "<números clave: Sharpe, retorno, bps, win rate, t-stat, ...>",
      "condiciones": "<bajo qué supuestos vale: costos incluidos?, OOS?, frecuencia, ...>",
      "robustez": "alta|media|baja",
      "cita_textual": "<frase exacta del paper con el resultado>"
    }
  ],
  "aplicabilidad_es_intradia": {
    "nivel": "alta|media|baja|nula",
    "nota": "<1 frase: por qué / qué se podría testear en el ecosistema ES>"
  }
}
```

## Tipos de relación (CERRADOS — no inventar otros)

| Tipo | Semántica | Ejemplo |
|---|---|---|
| `EQUIVALE_A` | sinónimos / mismo objeto con otro nombre | microprice EQUIVALE_A weighted mid-price |
| `PARTE_DE` | composición o taxonomía | queue position PARTE_DE limit order book |
| `USA` | A se implementa/apoya con B | pairs trading USA cointegration |
| `MIDE` | métrica que cuantifica algo | Sharpe ratio MIDE risk-adjusted return |
| `PREDICE` | señal→objetivo predictivo | order flow imbalance PREDICE short-term returns |
| `CAUSA` | mecanismo causal afirmado | adverse selection CAUSA bid-ask spread |
| `SE_OPONE_A` | enfoques/efectos contrarios | momentum SE_OPONE_A mean reversion |
| `MEJORA_A` | A supera/refina a B | deflated Sharpe ratio MEJORA_A Sharpe ratio |
| `CONTRADICE_A` | hallazgo que refuta otro | (usar cuando el paper refuta resultados previos) |
| `MITIGA` | A reduce el riesgo B | walk-forward validation MITIGA backtest overfitting |
| `APLICA_A` | dominio de aplicación | Avellaneda-Stoikov APLICA_A market making |
| `REQUIERE` | precondición dura | queue position modeling REQUIERE L3 data |

## Reglas de extracción

1. **10-25 conceptos por paper** (menos si el paper es corto o pobre). Solo
   conceptos TRANSFERIBLES: lo que otro quant podría reutilizar. NO extraer
   notación propia del paper (su "modelo M2"), nombres de secciones, ni
   papers citados de pasada sin contenido propio.
2. **Vocabulario preferente** (ontología semilla): usá estos nombres canónicos
   cuando el paper hable de lo mismo, aunque con otras palabras — pero quedás
   ABIERTO a conceptos nuevos no listados:
   order flow imbalance, limit order book, market making, adverse selection,
   inventory risk, bid-ask spread, microprice, queue position, tick size,
   market impact, square-root law, optimal execution, VWAP, TWAP,
   implementation shortfall, Almgren-Chriss framework, Avellaneda-Stoikov model,
   Hawkes process, price discovery, informed trading, PIN, VPIN,
   bid-ask bounce, Roll model, Kyle lambda, Amihud illiquidity,
   effective spread, realized spread, midpoint reversion,
   momentum, mean reversion, statistical arbitrage, pairs trading,
   cointegration, Ornstein-Uhlenbeck process, Kalman filter, regime switching,
   hidden Markov model, GARCH, realized volatility, volatility clustering,
   jump detection, intraday seasonality, overnight return, opening auction,
   closing auction, futures roll, contango, backwardation, carry, basis,
   lead-lag effect, cross-sectional momentum, time-series momentum,
   transaction costs, slippage, backtest overfitting, data snooping,
   look-ahead bias, survivorship bias, walk-forward validation,
   purged cross-validation, combinatorial purged cross-validation,
   deflated Sharpe ratio, probabilistic Sharpe ratio, false discovery rate,
   multiple testing, Sharpe ratio, Sortino ratio, maximum drawdown,
   profit factor, expectancy, Kelly criterion, position sizing, risk parity,
   hierarchical risk parity, triple-barrier labeling, meta-labeling,
   feature importance, random forest, gradient boosting, LSTM,
   reinforcement learning, Q-learning, high-frequency trading, latency,
   iceberg order, spoofing, quote stuffing, liquidity provision,
   liquidity taking, market microstructure noise, tick data, trade sign,
   Lee-Ready algorithm, order book depth, resting limit order, stop hunting,
   liquidity sweep, support and resistance, technical analysis.
3. **`tipo` con criterio**: `riesgo_metodologico` es para trampas de
   investigación (sesgos, overfitting); `fenomeno` para regularidades
   empíricas del mercado; `metodo` para técnicas estadísticas/computacionales;
   `estrategia` para familias operables con entrada/salida.
4. **Relaciones solo si el paper las AFIRMA** (no conocimiento general tuyo).
   2-5 relaciones por concepto importante; 0 está bien para conceptos
   secundarios. El `objeto` debe ser el nombre canónico de otro concepto
   (idealmente uno que también extraés, o uno de la ontología semilla).
5. **`cita_textual` es OBLIGATORIA por concepto y por hallazgo** — es el
   antídoto contra la alucinación. Copiá la frase EXACTA del texto (con sus
   errores de OCR si los hay). Si no encontrás una cita que lo ancle, ese
   concepto NO va.
6. **`hallazgos` = solo resultados con evidencia empírica del propio paper**
   (backtest, regresión, experimento). Con números en `magnitud`. Un survey
   sin experimentos propios → `hallazgos: []` y listo. Calibración de
   `robustez`: alta = OOS real + costos + varios mercados/períodos;
   media = backtest decente con alguna validación; baja = in-sample,
   sin costos, período corto o sospecha de cherry-picking.
7. **`calidad_paper`**: baja = predatorio/promocional/sin rigor (los hay en
   SSRN); media = correcto pero limitado; alta = riguroso. Sé duro: un paper
   con backtest sin costos, sin OOS y Sharpe 5 es calidad "baja" aunque
   presuma.
8. **Ignorá** bibliografía, agradecimientos, disclaimers legales y apéndices
   de código repetitivo.
9. Los campos en castellano van en castellano (definiciones, resumen,
   hallazgos); `nombre` y `cita_textual` quedan en inglés.

## Ejemplo de concepto bien extraído

```json
{
  "nombre": "order flow imbalance",
  "tipo": "concepto",
  "definicion_en_contexto": "Diferencia neta entre presión compradora y vendedora en el libro; el paper la construye con cambios de tamaño en el mejor bid/ask y muestra que explica los movimientos de precio de corto plazo mejor que el volumen.",
  "relaciones": [
    {"tipo": "PREDICE", "objeto": "short-term returns"},
    {"tipo": "USA", "objeto": "limit order book"},
    {"tipo": "MEJORA_A", "objeto": "trade volume"}
  ],
  "cita_textual": "we show that order flow imbalance explains price changes better than trade volume at short horizons"
}
```
