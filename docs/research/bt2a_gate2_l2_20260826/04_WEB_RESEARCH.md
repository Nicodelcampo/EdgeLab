# 04 — Research externo y consecuencias de diseño

## 1. First-passage y barreras

### Fuente

- *First passage times in portfolio optimization: A novel nonparametric approach*.
  European Journal of Operational Research.
  https://www.sciencedirect.com/science/article/pii/S0377221723006033

### Consecuencia

Una estrategia con take-profit y stop-loss se define por el primer cruce de dos
fronteras y por el tiempo hasta el cruce. MFE/MAE no preserva ese orden. Puerta 2 debe
persistir `TP_FIRST`, `SL_FIRST` y censura/timeout, no inferirlos desde extremos.

## 2. Triple-barrier labeling

### Fuente

- Trabajo reciente sobre etiquetado triple-barrier y secuencia temporal:
  https://link.springer.com/article/10.1186/s40854-025-00866-w

### Consecuencia

La tercera barrera temporal es parte del outcome, no un filtro posterior. En EdgeLab
el timeout debe permanecer en la población; la capa económica lo liquida a mercado.

## 3. Order-flow imbalance

### Fuente primaria

- Cont, Kukanov y Stoikov, *The Price Impact of Order Book Events*.
  arXiv: https://arxiv.org/abs/1011.6402
  DOI: https://doi.org/10.1093/jjfinec/nbt003

### Consecuencia

El flujo formado por órdenes límite, market orders y cancelaciones explica movimientos
de corto plazo, y su impacto depende de la profundidad. Gate L2 debe conservar OFI,
profundidad y depleción/reposición; no basta con volumen negociado.

## 4. Queue imbalance

### Fuente primaria

- Gould y Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit
  Order Book*.
  https://arxiv.org/abs/1512.03492
  DOI: https://doi.org/10.1142/S2382626616500064

### Consecuencia

Agregar `queue_imbalance_l1` y profundidad multilevel es coherente con la hipótesis de
contexto. Estas variables describen estado pre-evento; no deben optimizarse contra P2.

## 5. Imbalance y adverse selection

### Fuente primaria

- Cartea, Donnelly y Jaimungal, *Enhancing Trading Strategies with Order Book Signals*.
  SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2668277
  DOI: https://doi.org/10.1080/1350486X.2018.1434009

### Consecuencia

La imbalancia de volumen ayuda a predecir el signo de la próxima market order y el
cambio inmediato de precio. El uso correcto en este proyecto es como modificador de
adverse selection/contexto, no como prueba independiente de edge de K_ABS.

## 6. Microprice

### Fuente primaria

- Stoikov, *The Micro-Price: A High Frequency Estimator of Future Prices*.
  SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694
  DOI: https://doi.org/10.1080/14697688.2018.1489139

### Consecuencia

Se propone `microprice_minus_mid_ticks`, calculado causalmente desde BBO/imbalance.
También refuerza que la ejecución se evalúe contra bid/ask y no sólo contra last trade.

## 7. Regímenes y filtrado causal

### Fuente primaria

- Hamilton, *A New Approach to the Economic Analysis of Nonstationary Time Series and
  the Business Cycle* (1989).
  https://www.jstor.org/stable/1912559

### Consecuencia

Las probabilidades filtradas permiten inferencia en tiempo real. El smoothing usa
información futura y queda prohibido. El HMM es una compresión del estado observable,
no evidencia económica por sí mismo.

## 8. Cautela con VPIN

### Fuente primaria

- Andersen y Bondarenko, *Assessing Measures of Order Flow Toxicity and Early Warning
  Signals for Market Turbulence*.
  SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2292602
  DOI: https://doi.org/10.1093/rof/rfu041

### Consecuencia

VPIN puede quedar dominado por errores del clasificador y por volumen/volatilidad. El
overlay actual debe seguir llamándose `not_vpin`; promoverlo a VPIN requeriría un
contrato distinto, buckets de volumen y validación incremental propia.

## 9. Backtest overfitting

### Fuentes primarias

- Bailey et al., *The Probability of Backtest Overfitting*:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Bailey y López de Prado, *The Deflated Sharpe Ratio*:
  https://ssrn.com/abstract=2460551

### Consecuencia

PBO y DSR son apropiados después de construir una familia de P&L, pero no reparan una
mala definición del outcome. Primero first-passage y ejecución; después G2. El sweep de
99 configuraciones más 16 barreras no puede tratarse como una sola prueba.

## 10. Síntesis para EdgeLab

```text
Gate 1  = amplitud/asimetría del camino
Gate 2  = orden first-passage + ejecutabilidad
Gate L2 = heterogeneidad del efecto por estado pre-evento
G2      = robustez estadística de la familia de P&L resultante
```

La literatura respalda cada capa, pero ninguna autoriza seleccionar barreras, features
o estados después de observar el resultado all5.
