# Un agente autónomo de descubrimiento de edges bajo un embudo falsacionista: arquitectura en espiral, contraste cruzado, inferencia secuencial y economía de tokens

**Proyecto:** EdgeLab — https://github.com/Nicodelcampo/EdgeLab
**Fecha:** 2026-10-04 (v2, con estado del arte verificado en fuentes primarias)
**Estado del documento:** especificación de diseño aprobada por secciones (1–4) y completada (5–9); no describe un sistema construido.
**Referente rector:** `docs/NORTH_STAR.md`, sha256 del cuerpo `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
**Anexos de evidencia:** `docs/research/agente_espiral/DOSSIER_{A,B,C,D}_*.md` (sistemas LLM; validación estadística; infraestructura de agentes; futuros intradía). Cada afirmación de la sección 2 remite a uno de ellos; allí están las citas textuales, fórmulas reproducidas y URLs.

---

## Resumen

Se propone un agente de investigación autónomo e indefinido cuyo objetivo es reducir la distancia hacia un edge neto, robusto y operable, tal como lo define el referente de EdgeLab. No es un modelo de lenguaje (LLM) en control de un proceso: es un **orquestador Python determinista** que invoca LLM por rol, con entradas y salidas tipadas, dentro de un embudo falsacionista que ya existe en el repositorio (EF0–EF5, D0/D1/D2, Edge Brain con ledger encadenado por SHA-256). La revisión del estado del arte sobre fuentes primarias arroja cuatro hechos que gobiernan el diseño: (1) ninguno de los nueve sistemas de *alpha mining* con LLM publicados entre 2024 y 2026 aplica corrección por multiplicidad, y la única evaluación honesta, con registro completo de la búsqueda y *look-ahead* inexpresable por construcción, rechaza todas las estrategias descubiertas por LLM (Gençay, 2026); (2) el *False Strategy Theorem* y la cota de largo mínimo de backtest implican que un screening de 10⁶ celdas sobre menos de ~24 años de datos produce un Sharpe in-sample de 1 por puro ruido, de modo que el número de pruebas debe contarse **acumulado durante toda la vida del agente**; (3) un agente que corre indefinidamente es un problema de **inferencia secuencial**, y la única forma válida de abrir holdouts o monitorear candidatos sin inflar el error tipo I es un presupuesto de α (*alpha-wealth*) con FDR online bajo dependencia (e-LOND) y procesos-e para el monitoreo; (4) en futuros micro intradía sobre OHLCV de 5 minutos, 11 de 14 familias mueren por un techo de edge bruto de 1–2 puntos contra una fricción de 2 (Mesfin, 2026), y los dos fenómenos más fuertes son de borde de barra, lo que justifica trabajar a nivel tick. Las contribuciones de este diseño son: el LLM propone **familias** con ≤3 parámetros libres y la expansión a millones de celdas es mecánica; cada ciclo ejecuta un **contraste cruzado** avances↔descartados y contra literatura con identificador verificable; catorce **reglas de descarte preregistradas con cita** se cargan en el Edge Brain antes de la primera corrida; tres **controles canario** (oráculo con fuga, nulo aleatorio, benchmark pasivo) viajan en cada ledger; y la autonomía es total dentro de un perímetro en código que incluye el alpha-wealth. Se especifica además la economía de tokens bajo una membresía con ventanas de uso, el comportamiento verificado de Claude Code en modo headless, y un plan de verificación con pruebas sintéticas.

---

## 1. Introducción

### 1.1 Problema

EdgeLab acumula, al 2026-10-04, más de cuarenta ramas de investigación y un patrón consistente: las hipótesis entran, se miden y mueren. Entre el 30/09 y el 02/10 de 2026 se cerraron al menos nueve familias sin edge (EMA3 multiactivo 0/24, momentum RTY 0/24, VWAP reclaim 0/3, absorción L1 0/3, opening-range 0/3, IPC-ROB 0/23). La única familia viva, EMA 200×500 sobre MGC con TP 400 ticks, sobrevive a un test de cuatro (MCPT p≈0,026) y falla DSR, BH y SPA. El proceso es correcto. El cuello de botella es la **tasa de generación de hipótesis serias** y la **memoria metodológica** entre campañas: cada sesión rehace contexto, pierde negativos y a veces reabre lo ya refutado con umbrales vecinos.

### 1.2 Objetivo

Un agente que: (1) obtenga el contexto del proyecto por sí mismo; (2) proponga familias de hipótesis fundadas en literatura y en resultados previos; (3) las pase por el embudo, expandidas a miles o millones de variantes en CPU/GPU híbrido (Kaggle); (4) interprete resultados y decida promover, descartar o derivar; (5) actualice el Edge Brain con reglas nuevas; (6) corra indefinidamente, sin consulta humana dentro de su perímetro, con uso de tokens proporcional a la utilidad.

### 1.3 Decisiones ya tomadas por el responsable

- El agente reemplaza el "OK explícito de Nico" en G0–G4. Se formaliza como enmienda al NORTH_STAR (§8.3).
- Infraestructura: la máquina local como servidor 24/7; Kaggle como acelerador GPU.
- La paridad de indicadores pendientes la certifica el responsable. El agente sólo consume indicadores con `parity_exact`.

---

## 2. Estado del arte

### 2.1 Sistemas de *alpha mining* con LLM (Dossier A)

Se verificaron diez sistemas sobre sus páginas de arXiv, versiones HTML y repositorios: R&D-Agent(Q) (Li et al., 2025; NeurIPS 2025; MIT, ~14,8k estrellas; <10 USD y 12 h por corrida; Thompson sampling contextual sobre {factor, modelo}; "idea forest"), AQuA (Guo et al., 2026; sandbox sellado con operadores causales por construcción; embargo 2020; Sharpe 2,15–2,50 en acciones de EE. UU. 2021–2025; sin código), QuantaAlpha (Han et al., 2026; evolución a nivel trayectoria con mutación de prefijo congelado y crossover; 1,8M tokens y 20 h por corrida; MIT), AlphaSeek (derivado de QuantaAlpha, ingiere noticias sin controlar timestamps), FaVOR (Kim et al., 2026; gate determinista de fidelidad al mecanismo sin mirar retornos; test de un solo año), XAlpha (Liu et al., 2026; tests dinámicos de fuga por truncamiento y ruido futuro), AlphaLogics (Weng et al., 2026; lógicas compiladas a restricciones ejecutables), QuantAgent y Alpha-GPT 2.0 (Wang/Yuan et al., 2024; sin números verificables), y Chain-of-Alpha (retirado por arXiv; no citar).

**Tres hallazgos transversales:**

1. **Ninguno de los nueve sistemas de minado aplica corrección por multiplicidad.** Validan por backtest sobre el que el propio sistema optimiza.
2. **Los baselines no son comparables entre papers.** El ARR de RD-Agent en CSI300 aparece como 14,21 % (propio), 7,81 % (AlphaSeek), ~3,6 % (QuantaAlpha) y 6,67 % (XAlpha). Correr los baselines en el propio embudo o no comparar.
3. **Contaminación por corte de conocimiento.** El test 2017–2020 de R&D-Agent(Q) es anterior al corte de GPT-4o y o3-mini. El survey de Hua et al. (2026) recomienda testear después del release del modelo y enmascarar tickers y fechas.

**Gençay (2026), "What survives honest evaluation?"**, es el único trabajo con registro completo de la búsqueda. Diseño: el agente compone estrategias sólo con herramientas validadas por esquema (`add_feature`, `add_signal_term`, `finalize`); nunca escribe código; una familia de features con fuga existe pero el mismo flag la excluye del enum del esquema, del catálogo y de la validación del servidor, de modo que el *look-ahead* es **inexpresable por construcción**. Cada evaluación distinta cuenta como intento, duplicados incluidos; N y la varianza de Sharpe entre intentos salen del ledger y alimentan el DSR (umbral 0,95); PBO por CSCV con S=16; bootstrap estacionario sobre una ventana de evaluación nunca vista. Resultados: con 453 acciones y 39 ETF, costos realistas y ventanas de 4 y 9 años, **0 estrategias LLM sobreviven** (gpt-4.1 y claude-sonnet-5), 0/5 repeticiones del nulo, mientras los benchmarks pasivos se certifican. El experimento canario E1 muestra que un oráculo con el retorno de mañana como feature obtiene Sharpe de diseño 34,7, de evaluación 51,5 y **DSR 1,00**: la deflación corrige selección entre backtests honestos, no un conjunto de información contaminado. Fuga y búsqueda son defensas complementarias. Sobre tamaño muestral: "a true SR=0.6 strategy needs roughly eleven years of out-of-sample data to reach t≈2". Artefacto reproducible en Zenodo (MIT + CC-BY).

### 2.2 Infraestructuras de descubrimiento con propuesta LLM y verificación no-LLM (Dossier C)

**AlphaEvolve** (Novikov et al., 2025): base de datos evolutiva MAP-Elites + islas; Gemini Flash para amplitud y Pro para profundidad (proporción no publicada); cascada de evaluadores de dificultad creciente; ablaciones muestran que quitar el modelo grande o el contexto degrada. Limitación declarada: sólo problemas con evaluador automático. **ShinkaEvolve** (Sakana, 2025; Apache-2.0): métricas `public` (las ve el LLM) y **`private` (ocultas al LLM)**, UCB sensible al costo para elegir modelo, SQLite reanudable, `max_api_costs`, y desde mayo 2026 backend `headless/claude` sobre suscripción. **OpenEvolve** (Apache-2.0): cascada `evaluate_stage1/2/3`, checkpoints, ensemble 0,8/0,2. **DeltaEvolve** (2026): memoria en tres niveles L1 (20–40 tokens) / L2 (plan) / L3 (código) con revelación progresiva; −36,79 % de tokens. **FunSearch** (Nature 2023): LLM congelado, 10⁶ muestras, islas con reinicio periódico, patrón *skeleton*.

**AI Scientist v1/v2** y su evaluación independiente (Beel et al., 2025): 42 % de experimentos fallan por errores de código; resultados numéricos alucinados; el revisor automático sobrevalora. Incidentes documentados por Sakana: el agente editó su propio código para extender el timeout. **AI co-scientist** (Google, 2025): torneo Elo entre hipótesis, sin verificador ejecutable en el lazo. **Curie** (2025): validadores de setup y de re-ejecución en entorno limpio. **AIRA-dojo** (Meta, 2025): elegir la solución final por score de validación pierde 9–13 puntos absolutos; top-k por validación más confirmación en held-out recupera ~10. **POPPER** (2025): falsación secuencial con sub-hipótesis nulas y e-valores acumulados (`E ≥ 1/α`), error tipo I 0,103 con α=0,1. **Kosmos** (2025): las afirmaciones de síntesis aciertan sólo 57,9 %; "conflate statistically significant results with scientifically valuable ones". Survey "Verification Gap" (2026): "no LLM-era system … demonstrates an externally validated in-loop oracle".

**Claude Code headless (verificado en code.claude.com, CLI 2.1.285):** `claude -p` con `--output-format stream-json`, `--json-schema` (salida validada en `structured_output`; subtype `error_max_structured_output_retries`), `--max-turns`, `--model` y `--fallback-model`, `--session-id`, `--permission-prompts none`, `--setting-sources`, `--strict-mcp-config`, `--tools`. Emite `rate_limit_event` con `status: allowed|allowed_warning|rejected` y `resetsAt`. **La auto-espera hasta el reset es sólo interactiva**: en `-p` el orquestador debe dormir y reanudar. Las ventanas son compartidas entre modelos pero los límites de Opus y Sonnet son por familia. `claude setup-token` emite un token OAuth de un año para scripts. `total_cost_usd` es estimación client-side. SIGTERM corta el turno; SIGINT lo cierra limpio.

### 2.3 Validación estadística bajo multiplicidad y para un agente perpetuo (Dossier B)

**False Strategy Theorem** (López de Prado & Bailey, 2021): el máximo Sharpe esperado de N pruebas sin habilidad crece sin cota con N. **Largo mínimo de backtest** (Bailey et al., 2014, *Notices of the AMS*), reproducido en el dossier con la forma exacta:

| N celdas independientes | Años para SR=1 por ruido | Años para SR=2 |
|---:|---:|---:|
| 10³ | 10,6 | 2,6 |
| 10⁴ | 14,9 | 3,7 |
| 10⁶ | **23,7** | **5,9** |
| 10⁷ | 28,1 | 7,0 |

El N relevante es el **efectivo**, estimado por clustering de P&L (ONC, López de Prado & Lewis, 2019) o por correlación media, y **acumulado en la vida del agente**, no por corrida. **DSR** (Bailey & López de Prado, 2014; ejemplo del paper reproducido, DSR≈0,90) usa curtosis cruda, no excedente: quantstats tuvo exactamente ese bug hasta v0.0.82 (issue #550, sep-2026). **PBO/CSCV** (Bailey et al., 2017; S=16, C(16,8)=12.870, errata del paper que dice 12.780) mide si el *proceso* de selección sobreajusta; exige entregar todas las pruebas y, con búsqueda guiada, una columna por búsqueda terminada.

**Para miles o millones de celdas:** Reality Check (White, 2000; Sullivan-Timmermann-White 1999 sobre 7.846 reglas técnicas), **SPA** (Hansen, 2005; estudentizado, más potente), **StepM** (Romano-Wolf, 2005) y **FDP/k-FWER** (Romano-Shaikh-Wolf, 2008). Con bootstrap estacionario de bloque óptimo (Patton-Politis-White, 2009) los remuestreos de todas las columnas son un producto W(B×T)·R(T×m): un GEMM, ideal para GPU [inferencia del dossier]. BH sólo como filtro barato; **BY destruye la potencia** con m=10⁶ (factor ≈14,4). **Para un puñado de finalistas:** Model Confidence Set (Hansen-Lunde-Nason, 2011) y MCPT de Masters **reoptimizando todo el pipeline** en cada permutación (verificado en código de neurotrader888/mcpt); ninguno escala a 10⁶.

**Agente siempre activo = problema secuencial.** Monitorear p-values de forma continua invalida el error tipo I (Johari et al., 2022). Soluciones: *safe anytime-valid inference* (Ramdas et al., 2023; Grünwald et al., 2024), procesos-e y secuencias de confianza (Howard et al., 2021; Waudby-Smith & Ramdas, 2024, con variables acotadas); **FDR online** con presupuesto de α que se gasta en cada test y se recupera con cada descubrimiento (LORD++, SAFFRON) y, bajo dependencia arbitraria, **e-BH** (Wang & Ramdas, 2022) y **e-LOND** (Xu & Ramdas, 2024). Advertencias de 2025–2026: e-BH sobre supremos de procesos-e no controla FDR sin ajustadores (Tavyrikov et al., 2025). Implementaciones: `online-fdr` (Python, BSD-3), `onlineFDR` (R), `confseq` (C++/Python, MIT). No existe un proceso-e publicado específico para Sharpe de estrategias: hueco real.

**Librerías:** mlfinlab ya no es open source; `arch` (SPA, StepM, MCS, `optimal_block_length`) es la referencia; `skfolio` (BSD-3) trae CPCV; `statsmodels.multipletests`; pypbo (AGPL), fluke y backtest-overfitting (0 estrellas) sólo como referencia para validar implementación propia.

### 2.4 Futuros micro intradía: qué está refutado, qué tiene soporte, con qué motor (Dossier D)

**Mesfin (2026), arXiv:2605.04004** (sin revisión por pares; autor único): 72.604 barras OHLCV de 5 min de MNQ, RTH, dic-2021 a ago-2025, walk-forward expansivo con tres folds, fricción round-trip 2,0 pts (≈8 ticks), cinco criterios simultáneos (t≥2 neto, ≥30 trades por fold, media neta >0, mismo signo en tres años, permutación). **14 familias, ninguna pasa.** Once mueren por un **techo de edge bruto de 0,07–1,50 pts** contra 2,0 de fricción (expansión Asia t=−11,5; liquidity grab t=−14,1; volume spike/dry-up t entre −2,2 y −5,3; OU en MGC todas negativas, half-life ≈8 h). Mecanismo: el movimiento se consume dentro de la barra que lo genera (open→next open +32,24 pts; close→next open −0,17). Los controles positivos del autor (régimen GMM + Markov, t=3,11 y 4,30) tienen 53+ combinaciones sin DSR, GMM ajustado con todo 2022, baseline ATR con look-ahead y **stops llenados al precio exacto**; con un delay de una barra el signo **se invierte** (t de +4,30 a −2,78). Paper hermano (2605.17724): LSTM y GBM no superan 51,8 % de tasa base. **Implicación para EdgeLab:** los dos fenómenos más fuertes son de borde de barra; es la mejor justificación publicada para trabajar a nivel tick/25 ticks y para prohibir fills idealizados de stop.

**Yin et al. (2026), riesgo de implementación:** 15 estrategias en cinco motores; con costo cero todos coinciden; con costo, divergencia hasta 3,71 % en alta rotación; siete defectos en tres motores (Backtrader divide la comisión por 100; NautilusTrader cobra dos veces, trunca a 62 de 1.258 días, confunde HEDGING y NETTING). Recomendación: testing diferencial con dos arquitecturas distintas y baseline a costo cero.

**Familias con soporte publicado:** market intraday momentum en la última media hora (Gao et al., 2018, JFE; Baltussen et al., 2021, JFE, 60+ futuros, mecanismo de gamma hedging, con decaimiento post-publicación reportado); OFI (Cont-Kukanov-Stoikov, 2014; Cont-Cucuringu-Zhang, 2023): impacto contemporáneo robusto, forecast en horizontes de **segundos** (Takahashi, 2025: los shocks se disipan dentro del segundo en ES), sin evidencia de rentabilidad neta a latencia retail. **Folklore sin evidencia primaria:** volume profile/POC/VA, auction market theory, absorption/exhaustion de footprint, VWAP trend (SSRN de practicantes). **Refutadas:** ORB a 5 min en MNQ, expansión y liquidity grab de Asia, gap fill, volume spike/dry-up, drift post-noticia, OU intradía en MGC, ML sobre OHLCV, estrategias LLM bajo evaluación honesta.

**Motores tick-exact:** hftbacktest (Rust/Numba; L2 MBP y L3 MBO; modelos de cola y de latencia; conversor Databento MBO de CME; sin impacto de mercado); NautilusTrader (modelo de cola y latencia; en barras usa heurística O→H→L→C "not a reconstruction"); Backtrader no sirve a resolución tick. **Kaggle (doc oficial renderizada):** GPU "30 hours or sometimes higher" por semana; sesiones de **12 h** para CPU/GPU; P100 o T4×2 con 4 cores y 29 GB; `enable_internet` default false; la API batch acepta `dataset_sources` en `kernel-metadata.json` y la doc recomienda usarla para no gastar cuota interactiva. **Roll:** Databento `ROOT.v.N`/`ROOT.n.N` por volumen u OI del día anterior, sin ajuste (causal); Carchano & Pardo (2009): cinco métodos de roll no difieren significativamente. **Protocolo:** Arnott-Harvey-Markowitz (2019), siete puntos; Harvey (2017), p-valor bayesianizado. **Costos verificados:** exchange no-miembro MES/MNQ/M2K 0,353 USD por lado; MGC 0,70; NFA 0,01 por lado desde jul-2026 (0,02 desde jul-2027); comisión de broker no verificada; posible cambio CME desde 2026-10-01 (SER 9799, PDF bloqueado).

### 2.5 Síntesis

Los sistemas de 2.1 dejan al LLM escribir código y optimizar sobre su propio backtest sin contar la búsqueda; Gençay (2026) es su refutación empírica. AlphaEvolve y ShinkaEvolve muestran la alternativa que funciona cuando hay verificador fuera del LLM, y agregan dos mecanismos que este diseño adopta: métricas privadas ocultas al LLM y selección de modelo sensible al costo. La estadística dice que con datos fijos y N creciente cualquier umbral termina superado, y que un agente perpetuo sólo puede confirmar con datos nuevos bajo inferencia secuencial válida. La evidencia de futuros intradía dice que el techo de edge en OHLCV de 5 min está por debajo de la fricción y que lo que queda vive en el borde de barra. EdgeLab ya tiene el verificador y los datos tick. Lo que este diseño agrega es el generador disciplinado, la memoria que evita repetir refutaciones, la contabilidad de la búsqueda de por vida y el presupuesto secuencial.

---

## 3. Método: arquitectura en espiral

### 3.1 Unidad de trabajo

La unidad es la **familia** de hipótesis (contrato `edgelab_hypothesis_v1`, ≤3 parámetros libres, `asserts_edge: false`). El LLM nunca ve, propone ni adjudica una celda. Esto hace contable la multiplicidad: el número efectivo de hipótesis se declara en el preregistro y se recalcula por ONC sobre el P&L real, nunca se infiere después.

### 3.2 Máquina de estados por familia

```
CONJECTURED → PREREGISTERED → ELIGIBLE → SCREENED → CONTRASTED
    → ADJUDICATED_{PROMOTE | KILL | DERIVE}
PROMOTE → D1_RUNNING → MULTIPLICITY → ECON → HOLDOUT_OPENED → PAPER → LIVE_CANDIDATE
KILL    → RETIRED (con regla nueva opcional)
DERIVE  → CONJECTURED (radio + 1, parent_id, presupuesto heredado)
```

Correspondencia: `ELIGIBLE` ≡ G0, `SCREENED`+`CONTRASTED` ≡ G1, `MULTIPLICITY` ≡ G2, `ECON` ≡ G3, `HOLDOUT_OPENED` ≡ G4, `PAPER` ≡ G5. Cada transición es una fila append-only en el ledger del Edge Brain con hash encadenado y una transacción en `agent_state.db`.

### 3.3 La espiral

Cada vuelta tiene más radio: más contrastes acumulados, más literatura indexada, más negativos vecinos. Una familia derivada hereda `parent_id`, cuenta contra el presupuesto de multiplicidad del padre y declara qué predicción fallida la motivó. La espiral converge o se cierra; no se convierte en búsqueda continua de parámetros, prohibida por contrato (`forbidden: continuous_period_search, post_hoc_grid_expansion`). Mutación y derivación siguen el patrón de prefijo congelado de QuantaAlpha: sólo cambia el nodo de decisión identificado como fallido, el resto se conserva con hash.

### 3.4 Contraste cruzado

Cada hipótesis preregistrada declara `prediction` (consecuencia observable adicional si es verdadera) y `refutation` (qué la mata). Tres contrastes antes de adjudicar, sin LLM salvo caso ambiguo:

1. **Avance → descartados.** Matching estructural de la `prediction` contra el ledger de retiradas por `location`, `regime`, `trigger`, instrumento y ventana. Si una retirada ya midió la negación con potencia suficiente (MDE registrado), el avance cae a `DERIVE` con la contradicción adjunta.
2. **Descarte → avances vivos.** Un `KILL` dispara re-evaluación de toda familia viva que comparta primitivas. Si una promovida dependía de algo recién refutado, vuelve a `CONTRASTED`.
3. **Literatura.** Índice local del corpus (401 papers, 24.340 pasajes) primero; hasta *K* búsquedas externas por ciclo restringidas a SSRN, arXiv q-fin y revistas con DOI. Agrega `corroborating_refs` o `contradicting_refs`. **Un paper nunca promueve.** Las familias de §2.4 "refutadas" entran al ledger desde el día cero como retiradas con cita, y las "con soporte" como conjeturas iniciales con prior explícito.

Es el método hipotético-deductivo operacionalizado: conjetura, predicción deducida, intento de refutación, revisión de conjeturas previas.

### 3.5 Perímetro de autonomía

El agente decide solo todo lo anterior, incluido cuándo abrir el holdout de un candidato que pasó G3. El código impide, sin excepción ni prompt:

- abrir el holdout dos veces por candidato (`holdout_guard` + registro inmutable);
- leer `trade_date ≥ frontera` fuera de G4;
- ejecutar un registro cuyo hash no coincide con el preregistro;
- reutilizar artefactos stale;
- **abrir un holdout sin alpha-wealth disponible** (§5.3): el presupuesto secuencial de α es un recurso finito que sólo se repone con descubrimientos confirmados o con datos nuevos (paper/live);
- **aceptar un resultado de corrida cuyo ledger no contenga los tres controles canario** (§5.4);
- mergear cambios a `edge_validation_contract.md`: el agente propone un PR, no lo fusiona.

---

## 4. Roles LLM, cómputo y persistencia

### 4.1 Contratos de rol

| Rol | Modelo | Entrada | Salida | Nota |
|---|---|---|---|---|
| Proponente | Opus | delta L1/L2 del Edge Brain, registro de paridad, catálogo de datasets, fichas de papers, presupuesto restante, familias retiradas vecinas | hipótesis v1 + `prediction`, `refutation`, `refs` | sólo primitivas del registro; sin código |
| Compilador | sin LLM | hipótesis | `candidate_registry.json` con hash | aquí nacen las celdas |
| Lector de corridas | Haiku | `summary.json`, agregados por familia | tabla por familia, 3 líneas | sin juicio |
| Contraste ambiguo | Opus | dos expedientes | `{refuta: sí/no/insuficiente, cita}` | sólo si el matching estructural no decide |
| Revisor | Opus, sesión nueva | expediente completo, métricas **públicas** solamente | `{decision, reason, new_rule?, variant?}` | nunca ve métricas privadas (holdout, D2) |
| Cronista | Haiku | transiciones del ciclo | ledger, manifiesto con hash del referente, handoff, "Aporte al referente" | plantillas; cada número sale de una consulta al ledger, nunca de texto LLM |

Validación de salida contra JSON Schema vía `--json-schema`; un reintento; después `LLM_INVALID_OUTPUT` y el ciclo sigue. El LLM nunca recibe rutas de datos, credenciales, nada posterior a la frontera, ni métricas marcadas `private` (patrón ShinkaEvolve).

### 4.2 Registro de primitivas

El proponente compone `location`, `regime` y `trigger` desde un registro versionado de primitivas implementadas en el motor compartido (banco EMA, VWAP de sesión, terciles de volatilidad, y los indicadores del bridge con `parity_exact`). El registro, el esquema JSON que ve el LLM y la validación del servidor se generan **del mismo flag** (patrón Gençay): una primitiva marcada como no elegible desaparece del enum, del catálogo y del validador a la vez. Una primitiva nueva es un PR con tests de paridad, no un prompt. Control de redundancia: dos candidatos con correlación de señal ≥0,99 se consideran uno (R&D-Agent(Q)); una hipótesis con embedding ≥0,99 contra una existente se rechaza por novedad (ShinkaEvolve).

### 4.3 Reglas de descarte: preregistradas y emergentes

**Preregistradas (activas desde el día cero, con cita; detalle en Dossier D):**

| # | Regla | Base |
|---|---|---|
| K1 | Hipótesis económica escrita antes de mirar datos, más registro completo de trials incluidos los fallidos | Arnott-Harvey-Markowitz 2019; Fabozzi & López de Prado 2018 |
| K2 | t neto OOS ≥ 2,0 por familia preregistrada; ≥ 3,0 si salió de búsqueda amplia | Mesfin 2026; Harvey-Liu-Zhu 2016 |
| K3 | DSR ≥ 0,95 con N_eff acumulado del ledger; PBO por CSCV (umbral preregistrado, p. ej. < 0,5) | Bailey & López de Prado 2014; Bailey et al. 2017 |
| K4 | Edge bruto medio > fricción round-trip, con P_bootstrap(media neta > costo) ≥ 95 % | Mesfin 2026 (11/14 mueren acá) |
| K5 | ≥ 30 trades por fold OOS, no por total | Mesfin 2026 |
| K6 | Mismo signo neto en cada año o régimen OOS | Mesfin 2026 |
| K7 | Permutación sobre timestamps de señal, más SPA sobre la familia completa | Mesfin 2026; White 2000; Hansen 2005 |
| K8 | Robustez a 1 barra o N ticks de delay: muerte si el signo se invierte | Mesfin 2026 |
| K9 | Orden intra-barra pesimista (stop primero): muerte si el veredicto cambia entre pesimista y optimista; prohibidos fills idealizados | Nautilus doc; Mesfin Tabla A1 |
| K10 | Superar el benchmark incondicional de la misma ventana horaria en cada fold | Mesfin 2026 |
| K11 | Ninguna estadística de muestra completa en features: ajuste sólo con entrenamiento del fold | Mesfin 2026; Gençay 2026 |
| K12 | Testing diferencial de motores: con costo cero deben coincidir; con costo, divergencia bajo umbral de materialidad | Yin et al. 2026 |
| K13 | Roll causal (volumen u OI del día previo) y resultado estable con roll alternativo | Databento; Carchano & Pardo 2009 |
| K14 | Haircut por decaimiento: sobrevivir a −50 % del edge | McLean & Pontiff 2016 |

**Emergentes:** si el revisor adjunta `new_rule` a un `KILL`, entra como `PROPOSED` y se activa cuando dos familias distintas la confirman. Una regla activa bloquea en EF0 toda hipótesis que la viole, con cita a las familias fundadoras. Nunca se borran; se superseden con cadena de invalidación.

### 4.4 Cómputo híbrido

- **Local (CPU de referencia):** EF0, compilador, contraste, gates, tick-exact de finalistas, CSCV, MCS, MCPT con reoptimización, bootstrap PPW.
- **Kaggle (GPU):** EF2 cheap-kill masivo y el GEMM del bootstrap para SPA/StepM de familia. Un job = un kernel privado autocontenido (plantilla + registro embebido + hash de arrays esperado), `dataset_sources` = versión inmutable de `edgelab-arrays`, `enable_internet: false`, sesión ≤ 12 h (se usa 1 h por job para granularidad de cuota). Polling cada 2 min; descarga de `summary.json` + `survivors.parquet`; verificación de `split_hash` y hash de arrays. Resultado sin hashes correctos = inválido, registrado, no reintentado a ciegas. **Nota sobre la auditoría del 04/10:** el fallo "New Datasets cannot be attached in non-interactive sessions" fue por `kagglehub` interactivo; la ruta batch con `dataset_sources` en `kernel-metadata.json` es la documentada y la que este diseño usa.
- **Paridad CPU/GPU:** `gpu_parity.py` por versión de kernel; sin paridad verde ningún resultado GPU de esa versión se acepta.
- **Testing diferencial (K12):** el motor tick-exact de EdgeLab se contrasta contra **hftbacktest** (Rust, MBO, modelo de cola) sobre los finalistas: a costo cero deben coincidir fill a fill; con costo, la divergencia se registra. El modelo de costos es un oráculo separado: fees de exchange + NFA + spread efectivo medido en bid/ask tick + slippage de stop (gap a través del stop), con sensibilidad ×1, ×1,5, ×2.
- **Degradación:** sin Kaggle, EF2 corre local con `backend=cpu`. Mismo contrato, más lento.
- **Credencial:** `kaggle.json` local, fuera de Git. El Worker de Notion queda para acceso desde chat.

### 4.5 Persistencia y reanudación

`agent_state.db` (SQLite): `families`, `jobs`, `llm_calls` (rol, modelo, tokens, hash de entrada/salida), `budget` (ventanas LLM, cuota Kaggle, **alpha-wealth**), `trials` (una fila por celda evaluada, incluidas las descartadas: es el ledger completo por construcción). Toda transición es una transacción. Al arrancar, el daemon retoma: jobs `RUNNING` se consultan, no se relanzan; llamadas LLM sin respuesta se repiten, idempotentes por hash. Pérdida máxima ante apagón: un paso.

### 4.6 Loop del daemon

Cada 60 s: (1) recoger jobs remotos terminados; (2) avanzar familias cuyo próximo paso no requiere LLM; (3) si hay presupuesto, ejecutar la llamada LLM de mayor valor; (4) ante `rate_limit_event: rejected`, dormir hasta `resetsAt` y seguir sólo con lo numérico; ante `allowed_warning`, degradar a Sonnet/Haiku; (5) cada *N* ciclos, commit y push de ledger y documentos.

### 4.7 Asignación de cómputo entre familias

Dos niveles (Dossier C, §8): **entre familias**, Thompson sampling Beta-Bernoulli con descuento (γ≈0,95–0,99) donde la recompensa es "sobrevivió al gate", nunca el score crudo (AIRA-dojo muestra que seleccionar por validación repetidamente pierde 9–13 puntos); **dentro de la familia**, successive halving asíncrono (ASHA) sobre fidelidad creciente (meses, instrumentos), con `optuna.pruners` y storage SQLite reanudable.

---

## 5. Pipeline estadístico por etapa y presupuesto secuencial

### 5.1 Etapa EF2 — screen masivo en GPU (10⁵–10⁷ celdas)

Por celda, todo en forma cerrada: SR, t, asimetría, curtosis cruda, PSR(SR*=0), y estadísticas suficientes por bloque (S=16: Σr y Σr²) que permiten correr CSCV después sin rehacer backtests. **Compuerta de familia:** SPA estudentizado con bootstrap estacionario de bloque PPW sobre la matriz T×m de la familia contra benchmark; si p > α, muere la familia completa. Conjunto de descubrimiento: StepM o FDP/k-FWER con los mismos remuestreos. BH sólo como filtro barato. Piso de ruido: SR₀ = E[max] con N_eff y V[{SR}] de la familia. Lo que no lo supera no es candidato. No se hace MCS ni MCPT acá.

### 5.2 Etapa EF3 — meseta de familia (10²–10⁴ representantes)

Clustering ONC por correlación de P&L → N_eff y un representante por cluster; se elige el **centro de la meseta**, no el pico. PBO/CSCV con S=16 sobre representantes (una columna por búsqueda terminada si hubo optimizador). CPCV (skfolio) sólo si hay componentes que ajustan. DSR ≥ 0,95 con el N_eff **acumulado de por vida**; MinBTL: si los años disponibles son menos que el mínimo para el SR objetivo con ese N_eff, la familia no puede pasar por diseño.

### 5.3 Etapa EF4/G3 — finalistas en CPU (≤ 10–50) y presupuesto de holdout

MCS (`arch.MCS`) sobre pérdidas netas; del conjunto se elige el más simple. SPA de finalistas contra benchmark con costos. MCPT de Masters reoptimizando todo el pipeline de la familia (B ≥ 1000), complementado con bootstrap en bloques por la pérdida de agrupamiento de volatilidad. Intervalos bootstrap para SR y drawdown; haircut de Harvey-Liu como control de cordura.

**Apertura de holdout (G4) bajo FDR online.** Cada apertura es una hipótesis en un flujo infinito, dependiente de las anteriores (comparten régimen). Se usa **e-LOND** (`online-fdr`) con un presupuesto inicial de α fijado en el preregistro del agente. Cada apertura gasta alpha-wealth; sólo un descubrimiento confirmado lo repone. Si el alpha-wealth llega a cero, **no se abre ningún holdout más** hasta que entren datos nuevos por G5 (paper/live). Es la versión formal de "no existe testear gratis para siempre" y el análogo secuencial del False Strategy Theorem. Si se abren varios finalistas en una apertura, Holm dentro de ella. El holdout abierto queda consumido y pasa a datos de investigación.

### 5.4 Controles canario en cada ledger

Tres brazos obligatorios viajan con cada corrida, en el mismo ledger y bajo los mismos gates: (a) **oráculo con fuga** (retorno futuro como feature, inexpresable por el proponente, inyectado por el orquestador): si el embudo no lo marca como fuga por los tests dinámicos de truncamiento y ruido futuro (XAlpha), la corrida es inválida; (b) **nulo aleatorio** de la misma familia; (c) **benchmark pasivo** (long incondicional en la misma ventana horaria). Sin los tres, el resultado no se acepta (§3.5).

### 5.5 Etapa G5 — paper/live con monitoreo válido en cualquier tiempo

Proceso-e o secuencia de confianza (betting CS, `confseq`) sobre retornos acotados por el stop duro. Promover o matar en cualquier momento sin inflar el error tipo I. Es la única fuente de datos nuevos para un agente que corre indefinidamente.

---

## 6. Economía de tokens

### 6.1 Restricción real

Membresía con ventanas de 5 h y semanal, no API facturada. El LLM es intermitente; el embudo numérico progresa sin él; la métrica a optimizar es **utilidad por llamada** (reducción de distancia a un edge según la jerarquía del referente), no tokens por día.

### 6.2 Función de valor

Cola de prioridad `V = U / T`:

| Prioridad | Llamada | Por qué |
|---|---|---|
| 1 | Revisor sobre familia con sobrevivientes en EF2/EF3 | destraba la única ruta hacia G2–G4 |
| 2 | Contraste ambiguo que bloquea una adjudicación | sin él no hay decisión |
| 3 | Proponente, sólo si familias en vuelo < *F_min* | evita inanición, no "llena por llenar" |
| 4 | Revisor sobre familia sin sobrevivientes (para `new_rule`) | mejora EF0 futuro |
| 5 | Cronista | por lotes |

Si familias en vuelo ≥ *F_max*, el proponente no se llama: proponer más de lo que el cómputo puede matar sólo infla N_eff.

### 6.3 Mecanismos de ahorro

Idempotencia por hash de entrada; Haiku para lo mecánico; **revelación progresiva** del Edge Brain al proponente (L1 de 20–40 tokens para familias viejas, L2 para élite reciente, L3 sólo para el padre directo; patrón DeltaEvolve, −37 % de tokens); índice local de literatura antes de búsqueda externa; tope diario por rol; `--max-turns` en cada invocación.

### 6.4 Comportamiento ante límite (verificado)

`claude -p --output-format stream-json` emite `rate_limit_event`. `rejected` → registrar `RATE_LIMITED` con `resetsAt`, dormir, seguir con lo numérico, drenar la cola por `V` al reabrir. `allowed_warning` → degradar a Sonnet/Haiku. Límite de Opus con Sonnet disponible → cambiar familia de modelo para roles que lo admitan (lector, cronista). `CLAUDE_CODE_RETRY_WATCHDOG=1` para 429/529 de capacidad. Auth por `CLAUDE_CODE_OAUTH_TOKEN` de `claude setup-token`. Invocación con `--session-id` determinístico por tarea, `--permission-prompts none`, `--setting-sources` acotado, `--strict-mcp-config`, `--tools` mínimo; nunca `--bare` (no lee OAuth). Terminar con SIGINT.

---

## 7. Ventajas y desventajas frente al estado del arte

### 7.1 Ventajas

1. **Verificador fuera del LLM** con métricas privadas (AlphaEvolve, ShinkaEvolve). Toda cifra sale de código con hash.
2. **Búsqueda contada por construcción y de por vida.** Única forma de que DSR y MinBTL signifiquen algo (Gençay; False Strategy Theorem). Ningún sistema de §2.1 lo hace.
3. **Inferencia secuencial válida** para un agente perpetuo (e-LOND, procesos-e). Ningún sistema revisado la implementa; POPPER es lo más cercano y sólo acumula e-valores dentro de una hipótesis.
4. **Memoria que bloquea lo refutado**, no sólo que informa lo siguiente (contraste cruzado + reglas K1–K14 + familias refutadas como retiradas desde el día cero).
5. **Sin código generado en el camino de los datos**; registro/esquema/validador desde un mismo flag.
6. **Controles canario** en cada ledger: la defensa contra fuga es verificable en cada corrida, no asumida.
7. **Testing diferencial de motores** y oráculo de costos separado: el riesgo de implementación (Yin) y el dominio del costo en intradía (Mesfin) están en el diseño.
8. **Tolerancia a la infraestructura real**: membresía con ventanas, Kaggle batch, apagones.

### 7.2 Desventajas y riesgos

1. **Expresividad acotada** por el registro de primitivas. Costo deliberado.
2. **Tasa de descubrimiento esperada muy baja.** Gençay: 0/N; Mesfin: 0/14; MinBTL: 10⁶ celdas exigen ~24 años para que SR=1 no sea ruido. Lo más probable es una biblioteca de negativos documentados. El referente lo admite; conviene decirlo.
3. **Alpha-wealth finito.** Un agente sin descubrimientos agota su presupuesto de aperturas y queda limitado a G0–G3 hasta que entren datos nuevos. Es correcto, pero puede percibirse como parálisis.
4. **Dependencia de la certificación de datos.** `NOT_CERTIFIED_FOR_NEW_STRATEGY` (04/10) bloquea EF0 hasta resolverse. El agente no arregla datos.
5. **N_eff mal estimado** invalida el DSR. ONC es O(m²T) y con m=10⁶ exige muestreo o clustering de representantes [inferencia del Dossier B, a validar].
6. **Calidad del contraste estructural** depende de predicciones bien tipadas. Mitigación: esquema estricto y `DERIVE` por predicción mal formulada.
7. **Costo de Opus en el revisor** si muchas familias sobreviven a la vez. Mitigación: tope diario y paridad GPU por versión.
8. **Delegación de decisiones humanas** en G0–G4: se pierde una capa de juicio. La enmienda lo hace explícito, no lo compensa.
9. **Hueco en la literatura:** no existe proceso-e publicado para Sharpe de estrategias. G5 usará secuencias de confianza sobre retornos acotados, que sí están publicadas.

---

## 8. Plan de verificación y enmienda

### 8.1 Pruebas sintéticas (sin datos de mercado, sin holdout)

| Prueba | Qué falla si rompe |
|---|---|
| `test_holdout_once` | segunda apertura sobre el mismo candidato lanza y queda registrada |
| `test_alpha_wealth_exhausted` | con alpha-wealth 0, una apertura de holdout se rechaza y se registra |
| `test_prereg_hash_mismatch` | registro expandido distinto al preregistrado se rechaza |
| `test_crash_resume` | matar el daemon en cada estado y reanudar reproduce el mismo ledger |
| `test_llm_schema` | salida inválida del LLM simulado se reintenta una vez y luego se registra |
| `test_contrast_structural` | predicción con negación ya medida produce `DERIVE` con cita |
| `test_kill_cascades` | un `KILL` reabre las familias vivas que comparten primitivas |
| `test_rule_activation` | regla `PROPOSED` se activa sólo con dos familias distintas |
| `test_canary_leak_detected` | el oráculo con fuga es marcado como fuga; si no, la corrida es inválida |
| `test_canary_required` | un ledger sin los tres controles se rechaza |
| `test_private_metrics_hidden` | ninguna métrica `private` aparece en la entrada de ningún rol LLM |
| `test_rate_limit` | ante `rejected` simulado, lo numérico sigue y la cola se drena al reabrir |
| `test_gpu_parity_gate` | sin `gpu_parity.json` verde, el resultado GPU se descarta |
| `test_engine_differential_zero_cost` | EdgeLab tick-exact y hftbacktest coinciden fill a fill a costo cero sobre fixture |
| `test_dsr_against_paper` | la implementación propia reproduce DSR≈0,90 del ejemplo de Bailey & López de Prado (2014) |
| `test_cscv_count` | C(16,8) = 12.870 combinaciones, no 12.780 |
| `test_minbtl_gate` | familia con N_eff y años insuficientes no puede pasar EF3 |
| `test_north_star_hash` | ya existe; se mantiene |

Todas con LLM falso (fixtures JSON por rol), deterministas y gratis.

### 8.2 Validación end-to-end sintética

Dataset sintético con un edge plantado conocido, diez familias ruidosas, el oráculo con fuga y el nulo. Éxito: el agente promueve la plantada hasta G3, retira las diez, marca el oráculo como fuga, genera al menos una regla emergente consistente, y el ledger reconstruye la secuencia desde cero. Fracaso en cualquiera bloquea el despliegue.

### 8.3 Enmienda al NORTH_STAR (texto propuesto)

> **Enmienda A-2026-10-04 — Delegación al agente de investigación.** Las decisiones de promoción en G0–G4, incluida la apertura única del holdout, se delegan al agente descrito en `docs/research/AGENTE_ESPIRAL_20261004.md` (versión y hash citados en cada manifiesto), bajo condiciones no negociables: (a) el perímetro de §3.5 está en código y cubierto por §8.1; (b) ninguna salida de LLM es evidencia; (c) el número de pruebas se cuenta acumulado de por vida y el presupuesto de α para aperturas de holdout es finito y preregistrado; (d) los cambios a `edge_validation_contract.md` siguen requiriendo decisión explícita del responsable. Esta enmienda no mueve ninguna frontera de holdout.

Tras la enmienda, refrescar la autocita y actualizar `CLAUDE.md`/`AGENTS.md` (este último cita un hash stale, `d85364…`).

### 8.4 Tarea previa: unificar ramas

El embudo y el Edge Brain viven en `main` (177 archivos); el referente, los contratos, `CLAUDE.md` y `AGENTS.md` en `claude/focused-fermat-qjt805` (3.425). Primer commit: traer `docs/NORTH_STAR.md`, `docs/edge_validation_contract.md`, `docs/kernel_contract.md`, `tests/test_north_star_hash.py`, `CLAUDE.md` y `AGENTS.md` a `main`.

---

## 9. Ruta del proyecto

Orden de implementación derivado de la evidencia, cada hito con su criterio de cierre:

| # | Hito | Cierre |
|---|---|---|
| R0 | Unificar ramas; enmienda al NORTH_STAR; `AGENTS.md` con hash correcto | `test_north_star_hash` verde en `main` |
| R1 | Ledger completo por construcción: tabla `trials` + N_eff acumulado + MinBTL gate | `test_minbtl_gate`, `test_prereg_hash_mismatch` |
| R2 | Estadística propia validada: DSR, PSR, CSCV, bloque PPW, contra ejemplos publicados | `test_dsr_against_paper`, `test_cscv_count` |
| R3 | Controles canario + tests dinámicos de fuga en el embudo | `test_canary_leak_detected`, `test_canary_required` |
| R4 | Reglas K1–K14 cargadas como activas; familias refutadas como retiradas con cita | EF0 rechaza una hipótesis que viole K4 en fixture |
| R5 | Oráculo de costos separado + testing diferencial contra hftbacktest | `test_engine_differential_zero_cost` |
| R6 | SPA/StepM de familia como GEMM en GPU; paridad CPU/GPU por versión | `gpu_parity.json` verde; SPA coincide CPU/GPU en fixture |
| R7 | Orquestador: máquina de estados, SQLite, roles con `claude -p --json-schema`, gobernador de límites | `test_crash_resume`, `test_rate_limit`, `test_llm_schema` |
| R8 | Kaggle batch con `dataset_sources`; fallback CPU | un job round-trip con hashes verificados |
| R9 | Alpha-wealth con e-LOND; G5 con secuencias de confianza | `test_alpha_wealth_exhausted` |
| R10 | Scheduler Thompson + ASHA | familia estancada recibe menos GPU en simulación |
| R11 | Validación end-to-end sintética (§8.2) | los cuatro criterios de éxito |
| R12 | Primer ciclo real sobre el canónico certificado | manifiesto con hash del referente y "Aporte al referente" |

Dependencias duras externas: certificación del canónico (auditoría 04/10) antes de R12; paridad de indicadores (responsable) antes de ampliar el registro de primitivas.

---

## 10. Discusión

El diseño apuesta a que el valor de un agente de investigación está en cuántas estrategias **falsas** rechaza antes de arriesgar capital y en no volver a pagar por refutaciones ya compradas. La evidencia lo respalda con más fuerza de lo que se suponía en la v1 de este documento: la única evaluación honesta de estrategias LLM rechaza todas; en futuros micro intradía sobre OHLCV el techo de edge está por debajo de la fricción; y con datos fijos cualquier umbral termina superado si N crece sin contarse. Lo que sobrevive es el verificador fuera del LLM, la contabilidad de por vida y la confirmación con datos nuevos bajo inferencia secuencial. Las finanzas no tienen verificador exacto; tienen SPA, CSCV, DSR, MCS, MCPT, un holdout que se abre una vez y un presupuesto de α que se agota. Este agente los usa como si fueran exactos y acepta la tasa de descubrimiento baja que eso implica.

### 10.1 Trabajo futuro

- Proceso-e para Sharpe de estrategias (hueco en la literatura); mientras tanto, secuencias de confianza sobre retornos acotados.
- Ampliar el registro de primitivas con L2/MBP-10 bajo la enmienda L2 del 2026-09-24, donde el OFI tiene soporte contemporáneo robusto.
- Métrica explícita de "distancia al edge" por familia para refinar la función de valor.
- Publicar la biblioteca de negativos como resultado en sí mismo, con las trazas y semillas que el 62 % de los sistemas revisados no publica.

---

## 11. Extensión (2026-10-05): apuestas de régimen, propfirms, canasta e ingesta diaria

Decisiones del responsable del 2026-10-05: el payout de propfirm no es la función objetivo principal pero es de igual importancia; "apuesta de régimen" es una vía respetable y distinta del edge; se buscará una canasta del orden de quince apuestas con riesgo ponderado; el humano sumará datos día a día (ticks, L2); el agente registra sus pedidos de datos.

### 11.1 Dos cadenas de estados

| | `EDGE` | `REGIME_BET` |
|---|---|---|
| Pregunta | ¿Es real? | ¿Cuánto riesgo le asigno y cuándo la mato? |
| Validación | G0–G5, N_eff de por vida, alpha-wealth | G0 técnico + costo real + régimen declarado + **calibración de la clase** |
| Ventana | Toda la historia disponible, MinBTL | Ventana del régimen (meses), sin pretensión de significancia |
| Promoción a edge | Pasando G0–G5 | **Nunca por acumular meses**; sólo entrando a la cadena `EDGE` |
| Kill | Falsación en gates | Secuencia de confianza sobre retornos acotados (G5), haircut K14, cambio de régimen detectado |
| Riesgo | Según G3 | Acotado por apuesta y por canasta; Kelly fraccional con tope |

**Por qué no se puede validar una apuesta de régimen como edge.** Gençay (2026): SR 0,6 necesita ~11 años para t≈2; E4: cinco repeticiones del nulo fueron rentables fuera de muestra y 0/5 sobrevivieron la deflación. MinBTL: con 10⁴ candidatos, 15 años para que SR 1 no sea ruido. Mirar cuál de 50 bots ganó los últimos tres meses garantiza encontrar varios por azar.

**Por qué igual es una vía respetable.** Los mecanismos existen y decaen (McLean & Pontiff, −58 % post-publicación; Baltussen et al., gamma hedging). Una estrategia atada a un mecanismo vigente es una apuesta con prior económico, no una lotería. La diferencia con el edge es que se gestiona como riesgo, no como verdad.

**Calibración de la clase (lo que reemplaza al "probablemente la mayoría funcione").** No se asume la tasa de acierto de las apuestas de régimen; se **mide**. Cada apuesta registra al entrar: régimen declarado, detector (ajustado sólo con datos del fold), ventana observada, N de variantes probadas antes de elegirla, haircut aplicado. Al salir registra: duración real, P&L neto, causa de muerte. El ledger de calibración produce la tasa histórica de la clase y su intervalo; el tamaño de riesgo por apuesta nueva es función de esa tasa medida. Si la tasa cae por debajo del costo del drawdown, la clase entera se pausa. Esto es lo que hace que "quince apuestas" sea una política y no una esperanza.

### 11.2 Motor de reglas de propfirm

Existe en `feat/propfirm-ev-20260926`: `edgelab/propfirm/ev.py` (Monte Carlo del ciclo evaluación → fondeada → retiros, con piso estático/EOD/intradía, límite diario, consistencia, días mínimos, topes y cadencia de payout) y `rules.py` con catálogo de cinco planes 50k (Apex, Tradeify ×2, Topstep, MyFundedFutures) y `admits_algorithms()`. Ya incluye el **control de ventaja cero** (Hall 2026, §2.4): el mismo pipeline con `p_win = sl/(tp+sl)`.

Lo que falta y se agrega:

1. **Entrada empírica.** Hoy el simulador asume un bracket paramétrico (p_win, tp, sl, mae uniforme). Debe aceptar **trayectorias reales** del embudo: bootstrap estacionario por sesión (bloque PPW) del P&L diario y de las secuencias intradía de la estrategia, con sus MAE reales. El bracket queda como caso degenerado.
2. **Filtro de admisibilidad previo a toda estadística.** `algo_policy` (Apex: prohibido; resto: condicional con reglas de tenencia mínima, HFT, cobertura, noticias). Una estrategia que viola `min_hold_rule` o `news_rule` de una firma no se evalúa contra esa firma.
3. **Salida por (estrategia, firma, plan):** P(pasar evaluación), P(primer payout), EV por fee pagado, tiempo esperado al payout, distribución de payouts acumulados, y **lo mismo para el nulo**. Regla de lectura: si EV(nulo) > 0, el plan está mal priceado y el mérito es de la firma; si EV(estrategia) − EV(nulo) ≤ 0, la estrategia no aporta en esa firma aunque pague.
4. **Verificación de reglas.** El catálogo marca `verified: false` y precios de terceros. Cada regla usada en una decisión debe tener `source_url`, `fetched_at` y hash del texto; las reglas cambian (Tradeify cambió topes el 1-sep-2026) y el agente las recrawlea con cadencia y detecta diffs.

Posición en el embudo: etapa **paralela** a G3, no posterior. Una estrategia puede tener EV positivo en propfirm sin pasar G3 real (varianza alta, drawdown acotado por las reglas) y eso es información para la canasta, no para la cadena `EDGE`.

### 11.3 Canasta

Unidad: un **bot** = (estrategia, instrumento, cuenta, tamaño). Cuentas de propfirm y cuentas reales son buckets separados con sus reglas. Asignación: riesgo por bot acotado por su clase (edge vs apuesta de régimen) y por la calibración medida; correlación de P&L entre bots medida sobre ventanas comunes, nunca asumida; drawdown máximo por bucket y total; Kelly fraccional con tope duro. Rebalanceo cuando una apuesta muere, cuando cambia un régimen detectado o cuando una firma cambia reglas. Todo cambio de asignación es una fila del ledger con la razón.

### 11.4 Ingesta diaria y pedidos de datos

- **Ingesta.** Carpeta de entrada con manifiesto por archivo (instrumento, contrato, rango, fuente, hash). El agente valida esquema, orden temporal, identidad de ticks y frontera de holdout antes de anexar al canónico; rechaza y reporta, nunca repara en silencio. Los detectores de régimen se recalculan sólo con datos anteriores a la fecha as-of de cada decisión.
- **`data_requests`.** Tabla con: qué (p. ej. ticks MGC agosto, L2 MNQ semana X), qué hipótesis o apuesta desbloquea, valor esperado estimado, prioridad, estado (abierto / entregado / rechazado), quién lo cerró. El agente la llena; el humano la lee. Es la única interfaz por la que el agente pide algo a una persona.

### 11.5 Entorno de agentes y Kaggle

Credencial `kaggle.json` en `%USERPROFILE%\.kaggle\` con permisos de usuario, puesta por el responsable; nunca en chat, repo ni prompt. Sólo el orquestador Python la lee; ningún rol LLM recibe credenciales. Capacidades a verificar en el primer arranque: listado de datasets privados, push de un kernel con `enable_gpu`, otro con `enable_tpu`, lectura de cuota. Documentación de referencia: `kaggle-api/docs/kernels_metadata.md`, `kaggle.com/docs/notebooks`, `kaggle.com/docs/efficient-gpu-usage` (ver Dossier D §5).

### 11.6 Primera hipótesis manual

La estrategia "M1 04:15 del oro" probada el 2026-10-04 no está en el repositorio. Entra como primera hipótesis registrada a mano: reglas exactas, instrumento y contrato, horario y huso, qué se observó, cuántas variantes se probaron antes de fijarla, y clase declarada (`EDGE` o `REGIME_BET`). Sin ese registro no es evaluable.

---

## Referencias

Las referencias completas, con URLs verificadas y notas de verificación, están en los Dossiers A–D. Se listan aquí las citadas directamente en el cuerpo.

- Arnott, R., Harvey, C. R., & Markowitz, H. (2019). A Backtesting Protocol in the Era of Machine Learning. *Journal of Financial Data Science*, 1(1), 64–74.
- Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio. *Journal of Portfolio Management*, 40(5), 94–107.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014). Pseudo-Mathematics and Financial Charlatanism. *Notices of the AMS*, 61(5), 458–471.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The Probability of Backtest Overfitting. *Journal of Computational Finance*, 20(4), 39–70.
- Baltussen, G., Da, Z., Lammers, S., & Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics*, 142(1), 377–403.
- Beel, J., Kan, M.-Y., & Baumgart, M. (2025). Evaluating Sakana's AI Scientist. arXiv:2502.14297.
- Carchano, Ó., & Pardo, Á. (2009). Rolling over stock index futures contracts. *Journal of Futures Markets*, 29(7), 684–694.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88.
- Gao, L., Han, Y., Li, S. Z., & Zhou, G. (2018). Market intraday momentum. *Journal of Financial Economics*, 129(2), 394–414.
- Gençay, E. (2026). What survives honest evaluation? arXiv:2608.27734. Artefacto: doi:10.5281/zenodo.21261868.
- Grünwald, P., de Heide, R., & Koolen, W. (2024). Safe testing. *JRSS-B*, 86(5), 1091–1128.
- Guo, J. et al. (2026). AQuA. arXiv:2608.12841.
- Han, Y. et al. (2026). QuantaAlpha. arXiv:2602.07085.
- Hansen, P. R. (2005). A Test for Superior Predictive Ability. *JBES*, 23(4), 365–380.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). The Model Confidence Set. *Econometrica*, 79(2), 453–497.
- Harvey, C. R. (2017). Presidential Address: The Scientific Outlook in Financial Economics. *Journal of Finance*, 72(4), 1399–1440.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the Cross-Section of Expected Returns. *RFS*, 29(1), 5–68.
- Hua, et al. (2026). Agentic Quantitative Trading: A Survey. arXiv:2608.31041.
- Johari, R., Koomen, P., Pekelis, L., & Walsh, D. (2022). Always Valid Inference. *Operations Research*, 70(3), 1806–1821.
- Kim, et al. (2026). FaVOR. arXiv:2608.30192.
- Li, Y. et al. (2025). R&D-Agent-Quant. arXiv:2505.15155. NeurIPS 2025.
- Liu, F. et al. (2026). XAlpha. arXiv:2607.08332.
- López de Prado, M., & Bailey, D. H. (2021). The False Strategy Theorem. *American Mathematical Monthly*, 128(9).
- López de Prado, M., & Lewis, M. J. (2019). Detection of false investment strategies using unsupervised learning methods. *Quantitative Finance*, 19(9), 1555–1565.
- Lu, C. et al. (2024). The AI Scientist. arXiv:2408.06292.
- Masters, T. (2020). *Permutation and Randomization Tests for Trading System Development*.
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance*, 71(1), 5–32.
- Mesfin (2026). Structural Limits of OHLCV-Based Intraday Momentum Signals in MNQ Futures. arXiv:2605.04004.
- Novikov, A. et al. (2025). AlphaEvolve. arXiv:2506.13131.
- Patton, A., Politis, D. N., & White, H. (2009). Correction to "Automatic block-length selection". *Econometric Reviews*, 28(4), 372–375.
- Politis, D. N., & Romano, J. P. (1994). The Stationary Bootstrap. *JASA*, 89(428), 1303–1313.
- Ramdas, A., Grünwald, P., Vovk, V., & Shafer, G. (2023). Game-Theoretic Statistics and Safe Anytime-Valid Inference. *Statistical Science*, 38(4), 576–601.
- Romano, J. P., & Wolf, M. (2005). Stepwise Multiple Testing as Formalized Data Snooping. *Econometrica*, 73(4), 1237–1282.
- Romano, J. P., Shaikh, A. M., & Wolf, M. (2008). Formalized data snooping based on generalized error rates. *Econometric Theory*, 24, 404–447.
- Sakana AI (2025). ShinkaEvolve. arXiv:2509.19349.
- Sullivan, R., Timmermann, A., & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), 1647–1691.
- Takahashi (2025). arXiv:2508.06788.
- Tavyrikov, Goeman, & de Heide (2025). Carefree multiple testing with e-processes. arXiv:2501.19360.
- Wang, R., & Ramdas, A. (2022). False discovery rate control with e-values. *JRSS-B*, 84(3), 822–852.
- Waudby-Smith, I., & Ramdas, A. (2024). Estimating means of bounded random variables by betting. *JRSS-B*, 86(1), 1–27.
- Weng, et al. (2026). AlphaLogics. arXiv:2603.20247.
- White, H. (2000). A Reality Check for Data Snooping. *Econometrica*, 68(5), 1097–1126.
- Xu, Z., & Ramdas, A. (2024). Online multiple testing with e-values (e-LOND). AISTATS 2024. arXiv:2311.06412.
- Yin, Miki, Lesnichenko, & Gural (2026). Implementation Risk in Portfolio Backtesting. arXiv:2603.20319.

---

**Aporte al referente:** este documento no reduce por sí mismo la distancia a un edge; fija el mecanismo por el cual cada ciclo futuro deberá demostrar que la redujo, cuenta la búsqueda de por vida para que ese "demostrar" signifique algo, e impide volver a pagar por refutaciones ya hechas.
