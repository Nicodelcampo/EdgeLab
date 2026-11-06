Dossier A — anexo de docs/research/AGENTE_ESPIRAL_20261004.md — verificado 2026-10-04

# Dossier verificado: sistemas LLM para descubrimiento de alfa/estrategias (al 2026-10-04)

**Cómo lo verifiqué.** Leí las páginas `arxiv.org/abs` y las versiones HTML de cada paper (método, experimentos, limitaciones) y los README de GitHub. En 2608.27734 hice además una segunda pasada pidiendo citas textuales.

**Límites de la verificación:**
- Las lecturas pasaron por un extractor automático, no por lectura humana línea a línea.
- Cuando algo no cierra o no aparece en el paper, lo marco como **[no verificado]** o **[inconsistencia]**.
- Salvo R&D-Agent(Q), que fue aceptado en NeurIPS 2025, todo lo demás son preprints sin revisión por pares.

---

## 1. R&D-Agent(Q): "R&D-Agent-Quant: A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization"

**(a) Cita.** Li, Yang, Yang, Xu, Wang, Liu, Bian (Microsoft). arXiv:2505.15155 [q-fin.CP]. v1 del 21-05-2025, v2 del 25-09-2025. Aceptado en NeurIPS 2025. 42 páginas.

**(b) Arquitectura.** Es un loop de cinco unidades:
- **Specification:** define el contexto como una tupla S=(B,D,F,M).
- **Synthesis:** genera hipótesis a partir del historial y de las mejores soluciones hasta el momento (SOTA). Lo que se acumula de hipótesis se llama **"idea forest"**. Ojo: el término es **"idea forest", no "knowledge forest"**. "Knowledge forest" no aparece ni en este paper ni en los otros que revisé.
- **Implementation (Co-STEER):** usa un scheduler sobre un DAG, cadena de razonamiento y una base de conocimiento que crece con tríos (tarea, código, feedback). Hace como máximo 10 iteraciones internas por tarea.
- **Validation:** descarta factores redundantes (si la correlación de IC con uno existente es ≥ 0.99, se excluye) y corre el backtest en Qlib.
- **Analysis:** un **bandit multi-brazo con Thompson sampling lineal y contextual**. Los brazos son {factor, model}, cada uno con su modelo lineal bayesiano. El contexto es un vector de 8 métricas: [IC, ICIR, RankIC, RankICIR, ARR, IR, −MDD, SR]. La recompensa estimada es r̂=θ̃ᵀx_t.

**(c) Validación.**
- Splits en CSI300: train 2008–2014, validación 2015–2016, test 2017-01-01 a 2020-08-01.
- Split extendido: train 2008–2021, validación 2022–2023, test 2024 a junio 2025 (también en CSI500 y NASDAQ100).
- Estrategia long-short diaria por ranking en Qlib, con walk-forward y costos.
- Los baselines se corren con 5 semillas y se reporta el ARR mediano.
- Control de fuga declarado: el LLM "never exposed to raw market data", solo ve el esquema de los datos.
- **No aplica ninguna corrección por multiplicidad.**
- **Riesgo propio:** el test 2017–2020 cae antes del corte de conocimiento de GPT-4o y o3-mini, así que el modelo pudo haber memorizado ese período.

**(d) Resultados en CSI300 con o3-mini:**

| Métrica | R&D-Agent(Q) | Alpha158 | TRA |
|---|---|---|---|
| IC | 0.0532 | 0.0341 | 0.0404 |
| ICIR | 0.4278 | — | — |
| ARR | 14.21% | 5.70% | 6.49% |
| IR | 1.7382 | 0.8459 | 1.0091 |
| MDD | −7.42% | — | — |

- R&D-Factor con GPT-4o: ARR 14.61% e IC 0.0489, usando el 22% de los factores de Alpha158.
- Afirmación central: "2× ARR … 70% fewer factors".
- 2024–2025: CSI500 IC 0.0288 e IR 2.1721; NASDAQ100 IC 0.0162 e IR 1.7737.

**(e) Limitaciones declaradas.** Depende solo del conocimiento financiero interno del LLM. No detecta régimen en tiempo real. No usa noticias ni microestructura.

**(f) Código.** https://github.com/microsoft/RD-Agent, licencia MIT, alrededor de 14.8k estrellas. Se corre con `rdagent fin_quant`, `fin_factor` o `fin_model`. Usa LiteLLM como backend, requiere Docker y solo corre en Linux. El disclaimer dice que no está listo para inversión real.

**(g) Costo.** "under $10" por corrida, unas 12 horas alternando factor y modelo (6 horas por componente). Hardware: 112 hilos de CPU y 4 RTX A6000.

---

## 2. AQuA: "Recursively Self-Improving Quantitative Trading Research Agents"

**(a) Cita.** Guo, Huang, Gao, Li, Ge, Liang, Kuang, Wang (autor de correspondencia: Mengdi Wang). arXiv:2608.12841 [cs.CL]. v1 del 13-08-2026, v3 del 28-09-2026.

**(b) Arquitectura.** Son dos sistemas independientes:
- **Parte I (factores):** un AI Manager media entre seis especialistas: Data Steward → Visual Analyst → Idea Miner → Factor Evaluator → Backtest Engineer → Research Librarian. Hay tres loops anidados: calibración de dirección, actualización de creencias guiada por falsación, y memoria más política entre corridas.
- Una **creencia** es una confianza asignada a un mecanismo dentro de un contexto de mercado.
- **Parte II (modelo):** es un DSL de configuración (split, sampler, arch, loss, optim) sobre un modelo híbrido de series temporales.
- La formalización es R_{t+1}=U(R_t,H_t,C_t,E_t), con la siguiente hipótesis muestreada de P(·|R_{t+1}).

**(c) Validación.**
- Usa un **sandbox sellado**: los splits D, las features F, los labels L y el evaluador V los escriben humanos y el modelo nunca los edita.
- En la Parte I hay un registro de operadores causales. Los operadores de serie temporal solo leen su ventana pasada y los cross-seccionales solo el timestamp actual, así que cualquier composición es causal por construcción.
- Parte II: train 2010–2019, **2020 como embargo**, test 2021–2025 que nunca vuelve al agente. La selección del modelo usa una validación interna tomada del final del train.
- **La Parte I no tiene test held-out**: solo reporta IC de validación a lo largo de las iteraciones.
- **No aplica DSR, PBO ni ninguna corrección por multiplicidad.**
- El Apéndice B documenta un caso real de fuga: código de features escrito por el agente usaba normalización de volumen del día completo y pasó el chequeo del agente revisor.

**(d) Resultados.**
- Parte I (cripto, 5 minutos): IC combinado de validación ≈0.190; factores individuales entre 0.026 y 0.037.
- Parte II (acciones de EE.UU., 30 minutos, test 2021–2025):
  - IC por acción +0.0843, contra GRU 0.0613, LSTM 0.0535, LightGBM 0.0397 y ridge 0.0251.
  - Sharpe long/short neutral por sector +2.15; +2.50 con targeting de volatilidad; ≈+2.0 en walk-forward completamente causal.
  - Sharpe por año: 2021 +1.7, 2022 +3.5, 2023 +1.9, 2024 +1.8, 2025 +2.7.
- No especifica los activos cripto ni el universo de acciones de EE.UU.
- **[inconsistencia]** El texto habla de un costo de rotación de dos patas de 22 bps, pero una tabla aparece rotulada "Sharpe@2bp". Hay que revisarlo en el PDF.

**(e) Limitaciones declaradas.**
- Un solo mercado y horizonte por sistema.
- Hay un operador humano supervisando.
- Los resultados son simulados, sin validación en vivo.
- El aislamiento del test es "a governance property … not a cryptographic guarantee".
- Falta la ablación con la memoria apagada.

**(f) Código.** No hay repositorio, y las expresiones de factores están ocultadas ("withheld").

**(g) Costo.** No informa ni el LLM usado ni el costo.

---

## 3. QuantaAlpha: "An Evolutionary Framework for LLM-Driven Alpha Mining"

**(a) Cita.** Han, Zhang, Li, … , Wang (17 autores). arXiv:2602.07085 [q-fin.ST]. v1 del 06-02-2026, v3 del 18-05-2026.

**(b) Arquitectura.**
- Una corrida completa es una **trayectoria** τ=(s₀,a₀,…,s_n), y su recompensa es R(τ)=L(f(X),y)−λR(f).
- **Mutación:** la autorreflexión localiza el nodo de decisión subóptimo, congela el prefijo y reescribe solo esa acción.
- **Crossover:** combina segmentos de alta recompensa de k trayectorias padre.
- **Inicialización diversificada:** busca complementariedad entre fuentes de señal (precio o volumen), horizonte y mecanismo (momentum o reversión).
- Un verificador LLM chequea la coherencia hipótesis↔descripción↔expresión y la fidelidad expresión↔código.
- Complejidad: C(f)=α₁·SL+α₂·PC+α₃·log(1+|F_f|).
- Redundancia: subárbol común más grande en el AST, más un filtro por correlación de las salidas.

**(c) Validación.**
- CSI300: train 2016–2020, validación 2021, test 2022-01-01 a 2025-12-26.
- Costo de compra 0.05% y de venta 0.15%. Top 50 con 5 rotados por día, ejecución al open del día siguiente.
- El gate de admisión por RankIC usa solo 2021; "the 2022–2025 test window is never accessed during evolution".
- Transfiere sin reoptimizar a CSI500 y S&P500.
- **No aplica ninguna corrección por multiplicidad.**

**(d) Resultados con GPT-5.2.**
- IC 0.0472, ICIR 0.2691, RankIC 0.0459, ARR 4.68%, IR 0.6453, MDD 11.8%.
- Frente a RD-Agent con el mismo LLM: +0.0186 de IC, +1.10% de ARR y −4.96% de MDD.
- Frente a AlphaAgent: +0.0125 de IC y +3.57% de ARR.
- Transferencia a 4 años: +40.28% de exceso acumulado en CSI500 y +19.1% en S&P500.
- Ablaciones con DeepSeek-V3.2:

| Configuración | IC | ARR |
|---|---|---|
| Completo | 0.0461 | 4.53% |
| Sin mutación | 0.0382 | 3.27% |
| Sin crossover | 0.0401 | 4.02% |
| Sin planificación | 0.0448 | 3.81% |

**(e) Limitaciones declaradas.** Para producción faltan modelado de costos, control de riesgo y trading en vivo. Hay decaimiento del alfa después de 2023.

**(f) Código.** https://github.com/QuantaAlpha/QuantaAlpha, licencia MIT, alrededor de 1.6k estrellas. Está construido sobre Qlib, RD-Agent y AlphaAgent.

**(g) Costo.** Alrededor de 1.8M tokens por corrida (AlphaAgent 1.5M, RD-Agent 2.3M) y unas 20 horas sin GPU. Usa 10 direcciones en paralelo y 5 iteraciones evolutivas. LLMs probados: Qwen3-235B, DeepSeek-V3.2, Gemini-3-Pro-Preview, Claude-4.5-Sonnet y GPT-5.2.

---

## 4. Chain-of-Alpha

**(a) Cita.** "Chain-of-Alpha: Unleashing the Power of LLMs for Alpha Mining in Quantitative Trading". arXiv:2508.06312, del 08-08-2025. **RETIRADO por los administradores de arXiv**: v1 y v2 fueron removidas porque el remitente no tenía derechos sobre la licencia, y no hay PDF.
- arXiv lista como autor solo a Lang Cao. Una fuente secundaria (Lacuna) lista a Cao, Xi, Liao, Yang y Cao.

**(b) Arquitectura.** Doble cadena:
- **Factor Generation Chain:** busca diversidad usando un pool de candidatos y un pool de descartados.
- **Factor Optimization Chain:** refina con el feedback del backtest.

**(c, d) Validación y resultados.** Solo por fuente secundaria, **[no verificado contra el paper]**:
- CSI500 AR 0.1324 e IR 1.4178; CSI1000 AR 0.1471 e IR 1.4043.
- Período 2010 a junio de 2025.
- LLMs: GPT-4o, DeepSeek-V3 y Qwen3-32B.
- Baselines: LLM+CoT, ToT y MCTS.

**(e) Limitaciones.** No disponibles.

**(f) Código.** No hay.

**(g) Costo.** No informado.

**Recomendación: no citarlo como evidencia.**

---

## 5. AlphaSeek: "Trajectory-Level Self-Iterative Factor Mining Framework for Multi-Source Financial Data"

**(a) Cita.** Zhu, Lu, Zhu, Chen, Yin, Fong. arXiv:2608.13913 [cs.CE], del 14-08-2026.

**(b) Arquitectura.** Tres etapas:
1. Descubre direcciones de minado a partir de noticias y papers académicos recientes.
2. Hace evolución a nivel trayectoria: mutación con prefijo congelado, crossover entre direcciones paralelas y expansión paralela. La regularización es R(f)=α₁SL+α₂PC+α₃log(1+|F|)+α₄ER(f,h), y la consistencia semántica es C(h,d,f).
3. Optimiza el portafolio iterativamente con el historial D_{n−1}.

**[Observación]** Los splits, la fórmula de complejidad y los operadores son prácticamente idénticos a los de QuantaAlpha. Es un trabajo derivado.

**(c) Validación.**
- CSI300 con los mismos splits que QuantaAlpha: 2016–2020, 2021 y 2022–2025.
- **No discute el corte de conocimiento del LLM ni la sincronización de timestamps de noticias y papers**, que es un vector de fuga obvio cuando se ingieren noticias.
- No aplica ninguna corrección por multiplicidad.

**(d) Resultados.**

| Método | IC | ICIR | RankIC | IR | ARR | MDD |
|---|---|---|---|---|---|---|
| AlphaSeek | 0.0454 | 0.2561 | 0.0431 | 1.29 | 8.28% | 6.28% |
| RD-Agent | 0.0401 | — | 0.0522 | 0.8202 | 7.81% | 18.03% |
| Alpha158 | 0.0131 | — | — | — | 2.66% | — |

- En la ablación, sacar el control de redundancia es lo que más pega: −6.91% de ARR y +12.10% de MDD.
- La transferencia zero-shot a CSI500 es solo cualitativa.

**(e) Limitaciones.** No tiene sección de limitaciones.

**(f) Código.** No hay.

**(g) Costo.** No informa ni el LLM ni el costo.

---

## 6. FaVOR: "LLM-Based Agentic Framework for Factor Mining via Empirical Validation"

**(a) Cita.** Kim, Kim, Jung, Pyo, Jang, Lee. arXiv:2608.30192, del 31-08-2026.

**(b) Arquitectura.**
- Agentes: Hypothesis → Observation (descompone la hipótesis en condiciones observables) → Factor → Validation.
- **La Etapa 2 no mira retornos.** Para cada factor arma quintiles en el train y perfiles distribucionales sobre C−O, H−L, (C−L)/(H−L) y V. Después aplica cuatro chequeos y exige que pasen todos:
  - corrimiento de la tendencia central;
  - comportamiento de colas (diferencia Q90−Q10);
  - consistencia en al menos 2 estadísticos;
  - consistencia semántica juzgada por el LLM.
- Los tres primeros son deterministas.
- Etapa 3: integración con chequeo de selectividad direccional. Etapa 4: umbrales optimizados con Optuna sobre validación.
- La memoria guarda solo IDs de hipótesis y un escalar de IR promedio, sin retornos crudos.

**(c) Validación.**
- CSI500 (Baostock) y S&P500 (Yahoo), solo OHLCV diario.
- Train 2022–2023, validación 2024, test 2025. **El test es de un solo año.**
- Declara que el corte de conocimiento de GPT-4o es anterior al test 2025.
- No aplica ninguna corrección por multiplicidad.

**(d) Resultados en 2025.**

| Mercado | Método | AR | IR | MDD |
|---|---|---|---|---|
| CSI500 | FaVOR | 0.2067 | 1.5295 | −0.0853 |
| CSI500 | RD-Agent-Q | 0.1382 | 1.3360 | — |
| CSI500 | AlphaAgent | −0.0192 | — | — |
| S&P500 | FaVOR | 0.1062 | 1.1315 | — |
| S&P500 | RD-Agent-Q | 0.0604 | 0.8028 | — |

- Ablación en CSI500: sin la Etapa 2, AR 0.0492; sin la Etapa 3, AR −0.3902.
- No reporta IC.

**(e) Limitaciones declaradas.** No cubre factores de reversión cuya dirección cambia. Supone impacto de mercado despreciable.

**(f) Código.** https://github.com/damilab/FaVOR. **La licencia está pendiente** (solo hay un `LICENSE-DECISION.md`). Es una liberación "paper-focused" sin datos ni la bóveda de experimentos.

**(g) Modelos.** GPT-4o por defecto. Sensibilidad probada con GPT-5.4-mini, Gemini-2.5-Flash, Claude-Sonnet-4.6, Llama-3.3-70B y Qwen3-235B. No reporta costo en dólares.

---

## 7. XAlpha: "A Memory-Driven AI Quant Researcher for Hypothesis-to-Code Alpha Discovery"

**(a) Cita.** F. Liu, Fu, Wang, Q. Liu. arXiv:2607.08332 [cs.CL]. v1 del 09-07-2026, v2 del 13-07-2026.

**(b) Arquitectura.**
- **Macro Brain:** planifica temas y elige "Research Archetypes": una capa B primaria más 3 o 4 de soporte.
- **Micro Brain:** pasa de hipótesis a código Python, con un gate sobre el AST, un juez de tri-alineación, validación numérica y mutación/crossover/refinamiento.
- **Cross Brain:** atribuye cada factor a un arquetipo (FAA) y construye feedback GOOD/BAD por arquetipo, generación y ciclo.
- Memoria "Report-to-Memory Absorption" con taxonomía A/B/C:
  - A = factibilidad con OHLCV;
  - B = familia de mecanismo;
  - C = arquetipo con caminos respaldados por reportes.

**(c) Validación.**
- CSI300 con objetivo de retorno open-to-open a 10 días.
- Train 2011–2020, validación 2021, test 2022–2025.
- **Control de fuga dinámico:** tests unitarios de truncamiento y de perturbación con ruido futuro. El AST rechaza shifts negativos. Descarta factores con más de 30% de valores inválidos o extremos.
- Gates: normal RankIC≥0.005 con ratio positivo ≥0.50; élite RankIC≥0.01 con ≥0.55.
- No aplica ninguna corrección por multiplicidad.

**(d) Resultados en el test.**

| Método | IC | RankIC | AR | IR |
|---|---|---|---|---|
| XAlpha | 0.0619 | 0.0748 | 0.1795 | 1.5368 |
| AlphaAgent | 0.0243 | — | — | 0.9516 |
| CogAlpha | 0.0366 | — | — | 0.5747 |
| R&D-Agent(Q) | 0.0209 | — | — | 0.4062 |

- XAlpha además reporta ICIR 0.3703 y AER 0.1443.
- Correlación mediana entre factores: 0.181 dentro de un tema y 0.099 entre temas.

**(e) Limitaciones.** No tiene sección formal. Es un solo mercado y un solo horizonte.

**(f) Código.** No hay.

**(g) Costo.** gpt-oss-120b local en 2×H100. Unos 15 segundos por factor, 16 minutos por generación y 3 horas por ciclo. 64 semillas, pool de 80 factores y 10 generaciones por ciclo.

---

## 8. AlphaLogics: "A Market Logic-Driven Multi-Agent System for Scalable and Interpretable Alpha Factor Generation"

**(a) Cita.** Weng, Zhang, Wang, Xia. arXiv:2603.20247 [q-fin.CP], del 10-03-2026.

**(b) Arquitectura.**
- Extrae "lógicas de mercado" de Alpha101, Alpha191, Alpha158 y Alpha360 siguiendo fórmula → significado → lógica.
- Una lógica es H=⟨C,B⟩: C son predicados (v, op, θ, w) y B es (objetivo, dirección, horizonte). Se compila de forma determinista a restricciones ejecutables Γ.
- Loop interno: genera factores bajo Γ, con early stopping a 3.
- Loop externo: genera y refina lógicas según el desempeño agregado de sus factores.

**(c) Validación.**
- CSI500 y S&P500. Train 2015–2019, validación 2020, test 2021–2024.
- Combina los factores con LightGBM.
- No aplica ninguna corrección por multiplicidad.

**(d) Resultados en el test 2021–2024.**

| Mercado | Método | IC | AR (exceso) | IR | MDD |
|---|---|---|---|---|---|
| CSI500 | AlphaLogics | 0.0251 | 16.72% | 1.5266 | −5.31% |
| CSI500 | AlphaAgent | — | 12.46% | 1.2230 | — |
| S&P500 | AlphaLogics | 0.0093 | 13.75% | 1.2658 | −9.06% |

- Ablación de persistencia: si la lógica es transitoria, el IC cae de 0.0182 a 0.0165; si persiste, sube de 0.0199 a 0.0232.

**(e) Limitaciones declaradas.** Solo lógica técnica (OHLCV). Advierte sobre el posible impacto en el mercado si se adopta masivamente.

**(f) Código.** No hay.

**(g) Presupuesto.** GPT-3.5-turbo como modelo principal. 20 intentos × 5 rondas, con el mismo tope de llamadas para los baselines.

---

## 9. QuantAgent: "Seeking Holy Grail in Trading by Self-Improving Large Language Model"

**(a) Cita.** S. Wang, H. Yuan, L. M. Ni, J. Guo. arXiv:2402.03755, del 06-02-2024.

**(b) Arquitectura.**
- Loop interno writer/judge con recuperación desde una base de conocimiento; itera hasta score ≥β o t≥T.
- Loop externo: evaluación "real-world" que actualiza la base de conocimiento.
- Teorema 4.6: el regret bayesiano es sublineal en KT. Supone que el LLM hace inferencia bayesiana y una condición de pesimismo, y ninguna de las dos se valida.

**(c) Validación.** 500 acciones chinas, "year 2023" solamente. Sin splits explícitos, sin control de fuga y sin corrección por multiplicidad.

**(d) Resultados.** **No hay números en el texto**, solo curvas de MSE y heatmaps de win-rate. Tampoco hay baselines.

**(e) Limitaciones declaradas.** Depende de la calidad de la base de conocimiento y del costo computacional.

**(f) Código.** No hay; es un framework propietario llamado "idea-factor".

**(g) Costo.** gpt-4-0125-preview. Costo de tokens O(KT²H), sin dólares.

---

## 10. Alpha-GPT 2.0: "Human-in-the-Loop AI for Quantitative Investment"

**(a) Cita.** H. Yuan, S. Wang, J. Guo. arXiv:2402.09746 [q-fin.CP], del 15-02-2024. Marcado como "Draft. Work in progress".

**(b) Arquitectura.** Tres capas:
- Alpha Mining: de lenguaje natural a expresiones, más programación genética.
- Alpha Modeling: entrenamiento, búsqueda de arquitectura y de hiperparámetros.
- Alpha Analysis: riesgo con "Think-on-Graph" sobre un grafo de conocimiento financiero.
- El humano interviene en cada etapa. La memoria incluye bases de alfas, literatura, logs y el grafo de conocimiento.

**(c, d) Validación y resultados.** **No hay protocolo de validación ni números.**

**(e) Limitaciones.** Alto costo de cómputo y rendimientos decrecientes.

**(f) Código.** No hay.

**(g) Costo.** No especifica el LLM.

---

## 11. "What survives honest evaluation? Leakage-safe, search-aware assessment of LLM-driven trading strategy discovery" (el central)

**(a) Cita.** Eray Gençay. arXiv:2608.27734 [q-fin.ST], del 27-08-2026, CC BY 4.0.

### (b) Arquitectura
- El agente solo compone estrategias con herramientas validadas por esquema: `add_feature`, `add_node`, `add_signal_term`, `select_strategy`, `set_combo`, `finalize`. "The agent never writes code".
- **El look-ahead es inexpresable por construcción.** Existe una familia de features con fuga, pero el mismo flag del registro la excluye del enum del esquema, del catálogo que ve el modelo y de la validación del servidor.
- Una capa de auditoría determinista verifica el timing de los eventos (retraso de publicación de señales externas) y **rechaza planes en vez de repararlos**.
- La ejecución tiene un lag de 1 día. Costos: 1 bp de comisión, 2 bp de spread, impacto de raíz cuadrada contra el volumen en dólares de los últimos 21 días, y 50 bp anuales de préstamo para cortos.
- El universo se reselecciona point-in-time por liquidez: top 200 por volumen en dólares de 63 días, cada 21 días.

### (c) Cómo registra cada evaluación (el ledger de intentos)
- "Every candidate the agent composes flows through the same evaluation entry point", así que el ledger queda **completo por construcción**.
- Se cuenta como intento **cada evaluación distinta de estrategia**: cada iteración de refinamiento que produce un backtest en la ventana de diseño y cada brazo experimental.
- **Los duplicados se cuentan tal cual** ("duplicated candidates are counted at face value"), lo que es conservador.
- La ventana de evaluación nunca entra en la búsqueda.
- El manifiesto guarda: proveedor, modelo, revisión del código, versiones de paquetes, **hashes del contenido de los datos**, la traza completa de refinamiento y el bloque de estadísticos.

### Correcciones que tienen en cuenta la búsqueda
**1. Deflated Sharpe Ratio** (Bailey y López de Prado).
- DSR = PSR(SR₀*).
- PSR(SR*) = Φ[(ŜR−SR*)√(T−1) / √(1−γ₃ŜR+((γ₄−1)/4)ŜR²)].
- SR₀* = √V·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))], con γ la constante de Euler-Mascheroni.
- **N y V salen del ledger**, no de una estimación del autor. V es la varianza de los Sharpe de los intentos.
- **No hay corrección por intentos correlacionados ni "N efectivo".**
- Umbral: DSR ≥ 0.95.

**2. PBO por CSCV.** S=16 bloques sobre la ventana de diseño, todas las combinaciones C(16,8), λ=ln(ω/(1−ω)) y PBO=P(λ≤0).

**3. Sobre la ventana de evaluación:**
- Intervalos de confianza por stationary bootstrap (Politis-Romano 1994) para el Sharpe y el retorno.
- Block-bootstrap pareado de las diferencias diarias contra buy-and-hold.
- "Certified" significa que el IC del Sharpe en la evaluación excluye el cero.

**4. Curva de evaporación.** Para k=1…N toma el mejor Sharpe de diseño entre los primeros k intentos y lo deflacta con k y con la dispersión de esos k.

**No usa White's Reality Check, Hansen SPA, Romano-Wolf, Bonferroni, Holm ni el haircut de Harvey-Liu** (lo verifiqué con búsqueda textual). Benjamini-Hochberg solo aparece mencionado como alternativa: "false-discovery-rate control … over every hypothesis the search actually scored".

### Pre-registro
"At N=1 the threshold collapses to the benchmark and DSR equals PSR". Una tesis pre-especificada enfrenta un umbral más bajo que "a machine that tried a thousand variants, unless the machine pays for the thousand".

### (d) Resultados
**Datos.**
- 453 acciones grandes de EE.UU. (Tiingo, 2015–2026): diseño 2017–2021 (unos 1,261 días), evaluación 2022–2025.
- 39 ETFs multi-activo (países, sectores, Treasuries, crédito, oro, commodities, monedas, bitcoin): diseño 2007–2016, evaluación 2017–2025.

**E1, oráculo con fuga ("deflation does not catch leakage").**
- Se pone a mano el retorno de mañana como feature, en un brazo de configuración literal que el agente no puede expresar.
- Resultado textual: "design Sharpe ratio of 34.7, an evaluation Sharpe of 51.5, and a DSR of 1.00".
- **La deflación no detecta la contaminación**: corrige la selección entre backtests honestos, no un conjunto de información contaminado, y la fuga sobrevive fuera de muestra. Fuga y búsqueda son defensas **complementarias**.

**E2, paisaje base (N=9, PBO=0.83).** Solo el equal-weight buy-and-hold pasa: DSR 0.97, Sharpe de diseño 1.15 y de evaluación 0.60. SPY queda en DSR 0.94. Momentum, reversión y baja volatilidad L/S fallan.

**E3, descubrimiento autónomo (gpt-4.1, 100 candidatos de los que 99 son válidos, N=102).**
- El ganador es RSI×volumen: Sharpe de diseño 1.69 → evaluación 0.18 (+4.7%), DSR 0.86 contra un umbral deflactado de 1.21.
- Mientras tanto SPY hace 0.67 en evaluación (+51.5%).
- **PBO=0.01**: el ganador conserva su ranking pero pierde el edge absoluto.

**E4, robustez del nulo.** 5 repeticiones con N=18 cada una. Las 5 convergen en la familia volatility-breakout, con Sharpe de evaluación entre 0.59 y 0.70 (+26 a +33%) y DSR entre 0.15 y 0.29. **0/5 sobreviven.** Los costos ×0.5 y ×2 no cambian nada.

**Replicación con claude-sonnet-5.** 80/100 válidos. El mejor Sharpe de diseño 0.44 cae a −0.33 en evaluación, con DSR 0.18.

**Crítico JSON sin validación en el loop.** "60 of 60 proposals were rejected".

**E5, ETFs (N=20, PBO=0.80).**

| Brazo | Sharpe eval | Retorno eval | IC del Sharpe | Certificado |
|---|---|---|---|---|
| SPY | 0.85 | +249% | [0.24, 1.53] | sí |
| B&H 39 ETFs | 0.71 | +108% | [0.07, 1.46] | sí |
| Momentum de series de tiempo (TSM) | 0.49 | +55% | [−0.13, 1.24] | no |
| Divergencia pre-registrada | −0.15 | — | — | no |
| Agente | −0.23 | −21% | — | no |
| **Nulo aleatorio** | **0.55** | **+23%** | — | **no** |

**E6b, sistema humano en producción sobre GLD (N=1).** Sharpe de evaluación −0.12 (−13%) contra GLD buy-and-hold 1.04 (+257%), con p<0.001 en el bootstrap pareado.

**Tamaño de muestra.**
- "a true SR=0.6 strategy needs roughly eleven years of out-of-sample data to reach t≈2". La deflación sube la vara todavía más.
- Momentum de series de tiempo: "+55% over nine held-out years, and is still under-powered" (t≈1.5).
- Cuatro años no alcanzan para certificar edges moderados.

### (e) Limitaciones declaradas
- Supervivencia: constituyentes fijos, lo que sesga **a favor** de las estrategias activas.
- Solo features de precio.
- Solo dos modelos.
- La ventana contiene un bull market histórico de oro y acciones.
- La traducción de E6b no es exacta a nivel de microestructura.
- "DSR assumes trials are exchangeable draws; our hypothesis-rotation makes candidates heterogeneous".
- PBO con N≈20 es grueso.

### (f) Código
Artefacto en Zenodo: https://doi.org/10.5281/zenodo.21261868, v1.0.0 del 08-07-2026.
- Código con licencia MIT; manifiestos y configuraciones con CC-BY-4.0.
- Contiene DSR, PSR, PBO por CSCV, bootstrap, tests pareados, el ledger, las configuraciones E1–E6b y las trazas completas.
- La plataforma de descubrimiento completa se entrega solo a pedido.
- Los experimentos deterministas se reproducen exactos.

### (g) Costo
100 candidatos por corrida, 20 pistas rotativas de hipótesis por corrida. **No informa costo de API.**

---

## 12. Survey "Agentic Quantitative Trading: A Survey of Workflows, Systems, and Evaluation"

**Cita.** Hua, Yang, Hao, Zhang, Cao, Qi, Li, Guo. arXiv:2608.31041 [q-fin.CP], del 31-08-2026. 9 páginas.

**Taxonomía:**
- **Por etapa del pipeline:** minado de factores; descubrimiento de señales (razonamiento del agente, modelo de factores, estrategia ejecutable); construcción de portafolio; ejecución; riesgo (control previo a la ejecución y adaptación posterior).
- **Por estructura:** secuencial, iterativa, jerárquica, orquestada, o con colaboración humana. RD-Agent(Q) entra como orquestado.
- **Por coordinación:** flujo directo (A2A/MCP) o por agregación. Los desacuerdos se resuelven por debate, por selección o por **gating determinista**.
- **Por adaptación:** memoria por capas, reflexión, feedback de desempeño, detección de régimen.

**Hallazgos sobre 20 sistemas:**
- 20/20 hacen descubrimiento de señales; solo 4/20 tienen minado de factores como núcleo.
- Solo 2 cubren las 5 etapas como núcleo.
- En 15 de 17 sistemas multiagente la coordinación es por agregación; solo 5 usan selección, 3 debate y **2 gating**.

**Recomendaciones de evaluación:**
- Controlar el corte de conocimiento del LLM y testear después de su release (FinLake-Bench: las ganancias del backtest caen después del corte).
- Hacer contrafactuales y enmascarar memorias de ticker y fecha.
- Atribuir los retornos a mercado, estilo y selección (KTD-FIN: los retornos son mayormente exposición, no selección).
- Incluir costos, slippage y liquidez (PolyBench: cambian los rankings).
- Hacer paper trading en vivo antes de afirmar capacidades (LiveTradeBench: "strong static benchmark scores do not predict live trading performance"; DeepFund: la mayoría de los LLMs perdió plata).
- Inyectar desinformación de forma adversaria.
- **Ajustar la evaluación a lo que se afirma**: ejecutable no implica rentable, y backtest no implica vivo.

**Problemas abiertos:** coordinación más allá de la agregación, registrar por qué se rechaza cada decisión, y feedback de etapas posteriores hacia las anteriores.

**[Observación]** Para multiplicidad el survey solo recomienda OOS, prueba entre mercados y validación por régimen. **No menciona DSR, PBO ni SPA.**

---

## Tabla comparativa

| Sistema | Loop / memoria | Holdout | Control de fuga | Corrección por multiplicidad | Resultado principal | Código | Costo |
|---|---|---|---|---|---|---|---|
| R&D-Agent(Q) 2505.15155 | 5 unidades, Thompson sampling sobre {factor, model}, "idea forest", base de Co-STEER | Test 2017–2020 y 2024–2025 | Solo ve el esquema | No | CSI300 ARR 14.21%, IR 1.74 | MIT | <$10, 12 h |
| AQuA 2608.12841 | Manager + 6 agentes, creencias con confianza, memoria entre corridas | Parte II 2021–2025 con embargo 2020; Parte I solo validación | Sandbox sellado, operadores causales | No | IC 0.0843, Sharpe 2.50 | No | No informa |
| QuantaAlpha 2602.07085 | Trayectorias con mutación y crossover | Test 2022–2025 | Splits | No | IC 0.0472, ARR 4.68% | MIT | 1.8M tokens, 20 h |
| Chain-of-Alpha 2508.06312 | Doble cadena | ? | ? | ? | Retirado | — | — |
| AlphaSeek 2608.13913 | Trayectorias + noticias y papers | 2022–2025 | No trata noticias ni corte del LLM | No | ARR 8.28%, IR 1.29 | No | No informa |
| FaVOR 2608.30192 | Hipótesis → condiciones → 4 chequeos deterministas | **Solo 2025** | Corte de GPT-4o anterior al test | No | CSI500 AR 20.7%, IR 1.53 | Licencia pendiente | No informa |
| XAlpha 2607.08332 | 3 "cerebros", memoria A/B/C, GOOD/BAD | 2022–2025 | AST + tests de truncamiento y ruido futuro | No | IC 0.0619, IR 1.54 | No | gpt-oss local, 3 h/ciclo |
| AlphaLogics 2603.20247 | Biblioteca persistente de lógicas compiladas a Γ | 2021–2024 | Splits | No | CSI500 16.7%, IR 1.53 | No | 20×5 intentos |
| QuantAgent 2402.03755 | Writer/judge + base de conocimiento | Solo 2023 | No | No | Sin números | No | O(KT²H) |
| Alpha-GPT 2.0 2402.09746 | 3 capas con humano en el loop | — | — | — | Sin números | No | — |
| **Honest eval 2608.27734** | Herramientas por registro + auditoría determinista | 4 y 9 años | **Look-ahead inexpresable** + oráculo con fuga como control | **DSR con N del ledger, PBO-CSCV, bootstrap** | 0 estrategias LLM sobreviven | MIT + CC-BY | No informa |

**Patrón transversal:** **ninguno de los 9 sistemas de minado aplica corrección por multiplicidad**.

**Además, el mismo baseline da resultados incompatibles entre papers.** El ARR de RD-Agent en CSI300 aparece como:
- 14.21% en su propio paper;
- 7.81% en AlphaSeek;
- alrededor de 3.6% implícito en QuantaAlpha;
- AR 6.67% en XAlpha.

Las comparaciones entre papers no son confiables.

---

## Lecciones para un sistema que separa la conjetura del LLM de un embudo determinista de falsación

### Técnicas que vale la pena tomar
1. **Look-ahead inexpresable por construcción.** El agente compone solo con herramientas de un registro, y la lista que ve, el esquema y la validación salen del mismo flag. Si un plan falla, se rechaza, no se repara. [2608.27734; AQuA 2608.12841 con el registro de operadores causales]
2. **Un ledger completo por construcción, como único punto de entrada a la evaluación.** Cada backtest de la ventana de diseño cuenta, incluidos los refinamientos, y los duplicados se cuentan tal cual. El manifiesto lleva hashes de datos, versiones y modelo. N y V del DSR salen del ledger. [2608.27734]
3. **Doble puerta.** DSR≥0.95 sobre el diseño con N del ledger, PBO por CSCV con S=16, y además un IC por bootstrap estacionario sobre una evaluación nunca vista, que tiene que excluir el cero. También test pareado contra buy-and-hold. [2608.27734]
4. **Controles positivos y negativos dentro del mismo ledger.** Un oráculo con fuga como prueba canario (si el embudo no lo marca como fuga, falla la defensa de fuga), un nulo aleatorio y benchmarks pasivos. [2608.27734 E1, E5]
5. **Separar lo pre-registrado (N=1) de lo generado por búsqueda.** Que una conjetura del LLM declarada antes de mirar los datos pague menos deflación. [2608.27734]
6. **Curva de evaporación** como diagnóstico de cuándo frenar la búsqueda. [2608.27734]
7. **Embargo entre train y test, y selección de modelo solo con validación interna.** [AQuA, que embarga 2020]
8. **Tests dinámicos de fuga:** truncar la serie y perturbar con ruido futuro. Si la señal pasada cambia, hay fuga. Se suman al gate del AST. [XAlpha 2607.08332]
9. **Gate de fidelidad al mecanismo, independiente de los retornos.** Chequeos deterministas por quintiles sobre perfiles distribucionales. Sirve para falsar "el factor no mide lo que la hipótesis dice". [FaVOR 2608.30192; su ablación muestra AR de 0.2067 a 0.0492 sin esa etapa]
10. **Scheduler bandit** (Thompson sampling lineal sobre un vector de métricas) para repartir el presupuesto entre tipos de experimento. [R&D-Agent(Q) 2505.15155] Sugerencia propia, no viene del paper: usar como recompensa **métricas post-embudo** (por ejemplo, si sobrevivió), no el IC crudo, para no premiar el overfitting.
11. **Memoria a nivel trayectoria con mutación localizada (prefijo congelado) y crossover.** [QuantaAlpha 2602.07085, con ablaciones; AlphaSeek 2608.13913]
12. **"Idea forest"** (no "knowledge forest", que no lo encontré) como estructura de hipótesis. [R&D-Agent(Q)] También memoria jerárquica A/B/C con feedback GOOD/BAD por arquetipo [XAlpha], **creencias con confianza actualizadas por falsación** [AQuA], y una biblioteca persistente de lógicas compiladas a restricciones [AlphaLogics 2603.20247, donde persistir rinde más que lo transitorio].
13. **Control de redundancia:** subárbol común en el AST más correlación de salidas [QuantaAlpha], dedup por IC≥0.99 [R&D-Agent(Q)]. Es la ablación de mayor impacto en AlphaSeek (−6.91% de ARR).

### Modos de falla a evitar
1. **Pensar que la deflación atrapa la fuga.** El oráculo con Sharpe 34.7 da DSR 1.00. [2608.27734 E1]
2. **Dejar que el agente escriba código libre de features.** La normalización de volumen del día completo pasó el revisor LLM [AQuA, Apéndice B]. El crítico JSON sin validación tuvo 0/60 válidos [2608.27734].
3. **Reportar el mejor de N sin deflactar.** Sharpe de diseño 1.69 → 0.18 en evaluación; 0/5 repeticiones sobreviven aunque todas fueron rentables fuera de muestra. [2608.27734 E3, E4]
4. **Confundir persistencia del ranking con edge.** PBO=0.01 con el retorno absoluto colapsado. [2608.27734]
5. **Ventanas de test cortas.** Hacen falta unos 11 años para t≈2 con SR 0.6. Por eso FaVOR (un año) y QuantAgent (2023) no tienen poder estadístico. [2608.27734; 2608.30192; 2402.03755]
6. **Contaminación por el corte de conocimiento del LLM.** El test 2017–2020 de R&D-Agent(Q) es anterior al corte de sus LLMs. AlphaSeek ingiere noticias sin controlar timestamps. [Survey 2608.31041 citando FinLake-Bench; 2505.15155; 2608.13913]
7. **No contar la búsqueda de la Parte I ni reservar un held-out.** [AQuA]
8. **Suponer que los intentos son intercambiables cuando las hipótesis rotan.** Hay que estimar un N efectivo por clusters o reportar sensibilidad. [Limitación declarada en 2608.27734]
9. **Comparar contra baselines reportados por otros papers.** RD-Agent da entre 3.6% y 14.2% de ARR según quién lo corra. Hay que correr los baselines en el propio embudo. [2505.15155 vs 2608.13913 vs 2602.07085 vs 2607.08332]
10. **Afirmar capacidad sin atribución ni prueba en vivo.** Los retornos suelen ser exposición a mercado o estilo. [Survey 2608.31041: KTD-FIN, LiveTradeBench, DeepFund]
11. **Coordinar solo por agregación, sin gates deterministas ni registro de rechazos.** [Survey 2608.31041: solo 2/17 sistemas usan gating]
12. **Universo con sesgo de supervivencia**, que favorece a las estrategias activas. [Limitación de 2608.27734]

---

## URLs usadas
- https://arxiv.org/abs/2608.27734 · https://arxiv.org/html/2608.27734 · https://doi.org/10.5281/zenodo.21261868 · https://zenodo.org/doi/10.5281/zenodo.21261868
- https://arxiv.org/abs/2608.31041 · https://arxiv.org/html/2608.31041
- https://arxiv.org/abs/2505.15155 · https://arxiv.org/html/2505.15155 · https://github.com/microsoft/RD-Agent
- https://arxiv.org/abs/2608.12841 · https://arxiv.org/html/2608.12841
- https://arxiv.org/abs/2602.07085 · https://arxiv.org/html/2602.07085 · https://github.com/QuantaAlpha/QuantaAlpha
- https://arxiv.org/abs/2508.06312 · https://arxiv.org/abs/2508.06312v1 · https://lacuna.tiptreesystems.com/work/chain-of-alpha-unleashing-the-power-of-large-language-models-for-alpha-mining-in/wrk_de71a5f1d75161fcc9fec81634df6ca0 (secundaria) · https://www.semanticscholar.org/paper/Chain-of-Alpha:-Unleashing-the-Power-of-Large-for-Cao-Xi/d392598fbffaae986b15695b24611205be2e6ec3 (devolvió 403)
- https://arxiv.org/abs/2608.13913 · https://arxiv.org/html/2608.13913
- https://arxiv.org/abs/2608.30192 · https://arxiv.org/html/2608.30192 · https://github.com/damilab/FaVOR
- https://arxiv.org/abs/2607.08332 · https://arxiv.org/html/2607.08332
- https://arxiv.org/abs/2603.20247 · https://arxiv.org/html/2603.20247
- https://arxiv.org/abs/2402.03755 · https://arxiv.org/html/2402.03755
- https://arxiv.org/abs/2402.09746 · https://arxiv.org/html/2402.09746 · https://www.alphaxiv.org/abs/2402.09746

## Pendientes antes de citar
- La inconsistencia de costos en AQuA (22 bps contra "Sharpe@2bp").
- Si AlphaSeek compara contra QuantaAlpha en su tabla.
- Los números de Chain-of-Alpha, que solo tienen fuente secundaria.
- La frase "nine years suffices to certify SR≈0.7" de 2608.27734 no la pude confirmar textual. Las frases confirmadas son la de "eleven years" y la de momentum de series de tiempo "under-powered" a 9 años.
