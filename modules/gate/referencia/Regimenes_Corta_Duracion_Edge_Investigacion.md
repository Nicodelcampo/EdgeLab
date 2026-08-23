# Regímenes de mercado de corta duración y edge económicamente rentable

**Documento de investigación consolidado (3 iteraciones)**  
**Alcance:** detección, generación de hipótesis, motores de prueba, datasets, prácticas y recursos (Kaggle, GitHub, papers, software).  
**Horizonte de régimen:** segundos → minutos → horas de sesión (no solo bull/bear diario o semanal).  
**Objetivo:** base tangible para un apartado *build* (módulos, contratos, embudo de validación).

---

## 1. Tesis

Los regímenes **más explotables** para un edge táctico operable suelen ser **locales en el tiempo**:

| Escala | Ejemplos de estado | Drivers típicos |
|--------|--------------------|-----------------|
| Segundos–minutos | Quiet / toxic / burst de flujo | HFT, toxicidad del order flow, shocks de liquidez, news |
| Minutos–horas | Trend vs chop; opening / midday / close | Estacionalidad intradía, absorción, inventario, auctions |
| Fase de reloj | Bursts en :00 / :15 / :30 (según mercado) | Algos sincronizados, rebalanceos, fijaciones |

**El régimen no es el edge.** Es el **contexto (gate)** que habilita o apaga una hipótesis con mecanismo económico, evaluada con **costos de ejecución reales**.

---

## 2. Mapa de métodos

| Método | Rol | Escala típica | Herramienta / referencia |
|--------|-----|---------------|---------------------------|
| HMM / Markov-switching | Estado latente persistente | 1m–horario; también HF con features | `hmmlearn`; papers intradía |
| Change-point (PELT, BinSeg, KernelCPD) | Detectar que el régimen **cambió** | Barras intradía / diario | Librería `ruptures` |
| Clustering temporal | Estados de sesión intradía | Intradía | Hendricks et al. (Quantitative Finance) |
| Features de microestructura | Input del detector | Evento → minuto | OFI, VPIN, Kyle λ, depth, ER |
| Histéresis / sticky transitions | Evitar flip-flop y churn de costos | Todas las escalas | Umbrales de probabilidad / N barras |
| Early-warning multi-canal | Build-up latente antes del estrés | LOB / HF | LOB latent regimes (arXiv) |

---

## 3. Plantilla de features

### 3.1 Familias

1. **Flujo firmado** — trade imbalance; **OFI de libro** (eventos de BBO).
2. **Toxicidad** — VPIN (buckets de volumen).
3. **Impacto** — Kyle λ (regresión Δprecio ~ net flow).
4. **Liquidez** — spread, profundidad top-of-book, Amihud.
5. **Actividad** — trade intensity, inter-trade duration, volume bursts.
6. **Path / memoria** — realized volatility, Hurst, Efficiency Ratio, autocorrelación.
7. **Incertidumbre de estado** — entropía de posteriors HMM.

**Distinción crítica:**

- *Trade imbalance* usa solo el tape (agresores).
- *OFI (Cont–Kukanov–Stoikov)* usa altas, cancelaciones y cambios de tamaño en el **mejor bid/ask**.

No son intercambiables.

### 3.2 OFI (definición operativa)

Según Cont, Kukanov y Stoikov (2014), el impacto de corto plazo se relaciona de forma aproximadamente lineal con el *order flow imbalance* construido a partir de eventos del libro en el BBO. La contribución de cada evento depende de si el mejor bid/ask sube, baja o se mantiene y de cómo cambia el tamaño en ese nivel; el OFI del intervalo es la suma de esas contribuciones. Empíricamente:

\[\Delta P_k \approx \beta \cdot \mathrm{OFI}_k\]

con \(\beta\) ligado a la profundidad.

### 3.3 Plantillas mínimas

| Datos disponibles | Features mínimas |
|-------------------|------------------|
| Solo trades / L1 | Signed volume (z-score rolling) + realized vol + proxy de spread + Efficiency Ratio (ventanas 1–5 min) |
| L2 / BBO | OFI + VPIN + Kyle λ + depth imbalance + (opcional) entropía de posteriors HMM |

**Causalidad:** normalización solo con pasado (rolling o expanding). Prohibido z-score con media/desvío de toda la muestra en backtest.

---

## 4. Detección de regímenes

### 4.1 HMM

- Varios random restarts; selección de número de estados por BIC cuando aplique.
- Reordenar estados por varianza tras cada entrenamiento (etiquetas estables).
- Inferencia **causal** (filtro forward) en evaluación online; no usar smoothed Viterbi sobre el futuro del sample.
- Walk-forward: re-fit por ventanas; features ya laggeadas.

### 4.2 Change-point

- Librería de referencia: **`ruptures`** (PELT, binary segmentation, kernel CPD).
- Ajustar `min_size` a la escala temporal (evitar “regímenes” de pocos ticks).
- Offline para etiquetar historia; métodos online (CUSUM, BOCPD) para transiciones en streaming.

### 4.3 Métricas de calidad del detector (antes de buscar edge)

- Persistencia media del estado.
- Tasa de cambios (flip-flop).
- Estabilidad semántica OOS (¿el estado “Volatile” sigue siendo el de alta varianza?).
- Lead-time respecto a estrés observable (si el objetivo es early warning).
- Distribución de retornos, spread y volumen **por** estado (pureza).

---

## 5. Generación de hipótesis condicionada al régimen

Patrón operativo:

```
1. Fijar 2–4 regímenes (ej. Quiet / Normal / Volatile / Toxic)
2. Congelar o re-entrenar el detector solo en esquema walk-forward
3. Para cada régimen R, proponer reglas SOLO sobre barras con label R
4. Evaluar expectancy, nº de trades, concentración temporal
5. Promover solo reglas con tesis económica y números netos de costos
```

Acoplamientos típicos **a falsar** (no verdades):

| Régimen | Hipótesis de trabajo |
|---------|----------------------|
| Quiet | Mean-reversion de muy corto plazo |
| Normal | Continuidad moderada con filtro de liquidez |
| Volatile | Momentum / ruptura de rango reciente |
| Toxic | No operar o tamaño mínimo |

La búsqueda masiva (genéticos, grillas) debe vivir **dentro de cada R**, no sobre el día completo sin etiqueta.

---

## 6. Embudo de prueba (cómputo controlado)

| Etapa | Acción | Compresión |
|-------|--------|------------|
| 0 | Features + labels de régimen (1 pasada) | Guardar parquet |
| 1 | Hipótesis solo en `regime == R` | Menos barras |
| 2 | Filtros baratos (#trades, expectancy bruta) | Descarte temprano |
| 3 | Walk-forward del par detector + regla | Re-fit acotado |
| 4 | Costos (spread + fees + slippage) | Incluir cambios de régimen |
| 5 | Multiplicidad (conteo de trials; MCPT/DSR/PBO) | Anti p-hacking |
| 6 | Superviviente → motor tick/event-driven | Ejecución creíble |

Sin costos en las **transiciones de régimen**, el filtro infla curvas de forma artificial.

---

## 7. Inventario de recursos

### 7.1 Repositorios y código

| Recurso | Enfoque |
|---------|---------|
| [Market-Regime-Detection-HFT](https://github.com/anshumansinha3301/Market-Regime-Detection-HFT) | L2, features O(1), Gaussian HMM, Quiet/Normal/Volatile |
| [lob-regime-scanner](https://github.com/CameronScarpati/lob-regime-scanner) | LOB crypto, 30+ features, HMM, dashboard |
| [LOB-Latent-Regimes](https://github.com/prakulhiremath/LOB-Latent-Regimes) | Detección temprana de estados latentes en LOB |
| [VolatilityEdge](https://github.com/sege2023/VolatilityEdge) | HMM de vol + momentum/reversion + filtros de microestructura |
| [HMM-regime-terminal](https://github.com/az9713/HMM-regime-terminal) | BIC, gating, walk-forward, costos, bootstrap |
| [market-regime-detection-hmm](https://github.com/isaacnicas/market-regime-detection-hmm) | Overlay de riesgo por probabilidades + vol targeting |
| [ruptures](https://github.com/deepcharles/ruptures) | Change-point detection (PELT, etc.) |
| NautilusTrader ejemplo **Hurst/VPIN directional** | Régimen de persistencia (Hurst) + VPIN + gate por quotes |
| [stefan-jansen/machine-learning-for-trading](https://github.com/stefan-jansen/machine-learning-for-trading) | Pipeline intradía (order flow / LOB), costos, point-in-time |

### 7.2 Papers y literatura (conceptos ancla)

- Cont, R., Kukanov, A., & Stoikov, S. — *The price impact of order book events* (OFI y relación lineal con ΔP).
- Easley, D., López de Prado, M., & O’Hara, M. — VPIN / toxicidad de flujo sincronizada por volumen.
- Hendricks, D. et al. — *Detecting intraday financial market states using temporal clustering* (Quantitative Finance): estados intradía y *state signature vectors*.
- Modelos de regime-switching en durations / inter-trade (regímenes cortos vs largos; vínculo con actividad HFT).
- MS-ACI / price durations — regímenes de volatilidad intradía y shocks de liquidez.
- HMM aplicados a momentum intradía con *side information* (ratios de vol, estacionalidad).
- *Early Detection of Latent Microstructure Regimes in Limit Order Books* (arXiv) — build-up latente y lead-time.
- RADIANT (SSRN) — arquitectura con histéresis para detección HF de regímenes.
- Documentación y tutoriales NautilusTrader (estrategias, datos, regímenes vía ejemplos Hurst/VPIN).

### 7.3 Kaggle, datasets y competencias

- Competencias útiles como **gimnasio de features**, no como definición de régimen etiquetado: Optiver (Trading at the Close), Jane Street forecasting, DRW crypto, históricas tipo Caltech HFT LOB.
- Datasets: LOB crypto públicos; LOB sintéticos con regímenes; datos CME institucionales (MBO/MBP, vendors tipo Databento/AlgoSeek) para trabajo serio en futuros.
- **No** hay un estándar Kaggle de “ground truth de regímenes de 30 segundos en ES/NQ”.

### 7.4 Software de generación masiva de estrategias

| Software | Rol |
|----------|-----|
| StrategyQuant X | Generación genética/aleatoria + robustez (MC, WF) |
| Build Alpha / Adaptrade Builder | Fábrica de sistemas no-code |
| QuantConnect | Optimización y muchos backtests en cloud |
| Python vectorizado (polars, vectorbt, Ray) | Grillas masivas si el backtest es por barras |
| NautilusTrader | Validación de alta fidelidad y camino a live (no fábrica de millones) |

Generar millones **sin** embudo por régimen, costos y corrección por multiplicidad produce sobreajuste, no edge.

---

## 8. Diseño sugerido para *build*

```
build/
  data/            # ingest, sesiones, sello de holdout
  features/        # ofi, vpin, kyle_lambda, path, activity
  regimes/         # hmm_detector, pelt_transitions, hysteresis
  hypotheses/      # registro de reglas por régimen + tesis económica
  backtest/        # costos, walk-forward, métricas por régimen
  validation/      # contador de trials, MCPT/DSR hooks
  exec_bridge/     # exportación a Nautilus u otro motor
  docs/            # este documento + decisiones congeladas
```

**Contrato recomendado de señal:**  
solo información pasada → índices y dirección (o posición); el motor aplica fills y costos. El régimen entra como **gate/feature causal**, nunca como label futuro.

---

## 9. Checklist de aceptación de un candidato a edge

1. Tesis económica explícita (quién pierde y por qué).
2. Labels de régimen causales y semánticamente estables fuera de muestra.
3. Expectancy **neta** de costos > 0 **dentro** del régimen.
4. Número de trades suficiente; no concentrado en un solo mes.
5. Walk-forward con re-entrenamiento del detector.
6. Trials contabilizados (multiplicidad).
7. Política clara en regímenes tóxicos o de transición (flat / size↓).
8. Misma lógica portable a simulación tick / event-driven.

---

## 10. Anti-patrones

| Anti-patrón | Efecto |
|-------------|--------|
| HMM fit full-sample + decode suavizado en todo el sample | Look-ahead |
| Z-score con estadísticas de toda la historia | Look-ahead |
| Cambio de régimen sin histéresis | Churn y costos |
| Optimizar una regla global ignorando el régimen | Edge fantasma de un subperíodo |
| No cobrar costos en flips de régimen | Métricas infladas |
| Confundir OFI de libro con imbalance de tape | Features no replicables |
| Millones de estrategias sin corrección por multiplicidad | P-hacking |

---

## 11. Conclusiones de las tres iteraciones

1. El objeto correcto de investigación táctica son **micro-regímenes temporales**, no solo regímenes macro diarios.
2. El stack open-source existe: features de microestructura + `hmmlearn` + `ruptures` + repos LOB/HMM + ejemplos Nautilus (Hurst/VPIN).
3. Kaggle aporta ideas y datos parciales; no sustituye un lab con datos de calidad y costos.
4. Las hipótesis deben generarse y evaluarse **condicionadas al régimen**.
5. Sin costos, walk-forward causal y control de multiplicidad no hay edge “de mercado real”.
6. Un *build* tangible es: feature store → detector → registry de hipótesis por régimen → embudo → puente a ejecución.

---

## 12. Orden de implementación sugerido

1. Elegir activo y resolución (p. ej. futuros índice 1s–1m o BBO).
2. Feature store mínimo (flujo firmado + vol + ER; OFI si hay L2).
3. Detector HMM 2–3 estados + histéresis; reportar persistencia y estabilidad.
4. Una hipótesis por estado, con costos.
5. Walk-forward; descartar o promover.
6. Si sobrevive, portar gate + señal a NautilusTrader (o motor tick equivalente).

---

## 13. Fuentes

### 13.1 Papers y literatura

- Cont, R., Kukanov, A., & Stoikov, S. — *The Price Impact of Order Book Events* (OFI; relación lineal con cambios de precio de corto plazo).
- Easley, D., López de Prado, M., & O’Hara, M. — VPIN y medidas de toxicidad de order flow sincronizadas por volumen.
- Hendricks, D. et al. — *Detecting intraday financial market states using temporal clustering*, *Quantitative Finance* (estados intradía; state signature vectors).
- Literature on multifactor regime-switching duration models / inter-trade duration regimes in limit order markets.
- High-frequency volatility modeling / MS-ACI style papers on price durations and intraday regimes.
- Christensen, H., Godsill, S., & Turner, R. E. — *Hidden Markov Models Applied To Intraday Momentum Trading With Side Information* (arXiv:2006.08307).
- Hiremath et al. — *Early Detection of Latent Microstructure Regimes in Limit Order Books* (arXiv).
- Saraf, I. — RADIANT: Regime-Adaptive Dynamic Inference & Allocation Network with Temporal-Hysteresis (SSRN).
- Trabajos sobre efectos de fase de reloj / periodic algorithmic trading en futuros (incl. crypto).

### 13.2 Software y documentación

- [ruptures](https://github.com/deepcharles/ruptures) — change point detection (PELT, BinSeg, KernelCPD).
- hmmlearn — Gaussian Hidden Markov Models.
- [NautilusTrader](https://nautilustrader.io/) — plataforma event-driven; ejemplo de estrategia Hurst/VPIN directional.
- StrategyQuant X, Build Alpha, Adaptrade Builder — generación automática de estrategias.
- QuantConnect / LEAN — research, optimización y ejecución en cloud.
- QuantConnect Research — *Intraday Application of Hidden Markov Models*.

### 13.3 Repositorios GitHub

- https://github.com/anshumansinha3301/Market-Regime-Detection-HFT
- https://github.com/CameronScarpati/lob-regime-scanner
- https://github.com/prakulhiremath/LOB-Latent-Regimes
- https://github.com/sege2023/VolatilityEdge
- https://github.com/az9713/HMM-regime-terminal
- https://github.com/isaacnicas/market-regime-detection-hmm
- https://github.com/deepcharles/ruptures
- https://github.com/stefan-jansen/machine-learning-for-trading
- https://github.com/nautechsystems/nautilus_trader (ejemplo `hurst_vpin_directional`)

### 13.4 Competencias y datos

- Kaggle: Optiver – Trading at the Close; Jane Street Real-Time Market Data Forecasting; DRW – Crypto Market Prediction; competiciones HFT/LOB históricas (p. ej. Caltech CS155).
- Datasets LOB crypto y sintéticos en Kaggle.
- Datos CME de vendors institucionales (MBO/MBP; p. ej. Databento, AlgoSeek) para producción en futuros.

### 13.5 Práctica complementaria

- Guías de regime filters y backtests filtrados por régimen (costos en transiciones, Efficiency Ratio intradía).
- Material aplicado sobre Kyle λ, OFI y VPIN en market microstructure.
- Tutoriales de change-point con PELT sobre retornos financieros (`ruptures` + ejemplos públicos).

---

## Anexo A — Resumen de las tres iteraciones

| Iteración | Contenido principal |
|-----------|---------------------|
| **1 — Mapa** | Escalas de régimen; métodos (HMM, CP, clustering, microestructura); repos y papers de entrada; escasez en Kaggle; régimen como gate. |
| **2 — Profundización** | Plantilla de features; HMM + `ruptures`; hipótesis por régimen; embudo de cómputo; métricas de calidad del detector. |
| **3 — Cierre build** | Checklist operativo; pipeline mínimo; prioridades de recursos; anti-patrones; diseño de módulos; puente a Nautilus. |

---

## Anexo B — Checklist rápido de implementación

- [ ] Activo y resolución definidos
- [ ] Holdout / sello temporal definido
- [ ] Feature store causal (sin look-ahead)
- [ ] Detector HMM y/o PELT con histéresis
- [ ] Métricas de persistencia y estabilidad OOS del régimen
- [ ] Al menos una hipótesis económica por régimen
- [ ] Backtest con costos (incl. flips de régimen)
- [ ] Walk-forward del par detector + regla
- [ ] Contador de trials / corrección por multiplicidad
- [ ] Puente a motor de ejecución tick o event-driven

---

*Documento consolidado a partir de investigación web (GitHub, papers, documentación Nautilus, literatura de microestructura) en tres iteraciones. Destinado a servir como especificación de trabajo para implementar detección de regímenes cortos, hipótesis condicionadas y validación con costos en mercado real.*
