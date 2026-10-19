# BT2A GC — Diseño de medición de lógicas de salida SL/TP asimétricas y breakeven (V1.1, borrador)

- **Fecha:** 2026-08-30 (ART) · **V1.1:** grilla densa de gatillo BE + Romano-Wolf + MCS + regla de meseta, a pedido de Nico ("la excursión para poner break even no puede ser arbitraria; quiero que se pruebe todo, o al menos muchas combinaciones; quizás ninguna funciona pero que sugiera cuál es mejor y más sólida").
- **Corrigendum V1.1 (mismo día):** en §13, la alternativa DP2 con H fija son **186** primarias (29×3×2 BE + 12 ASIM, con 1 H), no 232 como decía la primera versión de este archivo. Registrado también en `docs/audits/CANAL_NOTION_AI_2026-08-30_002.md` §3.
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`
- **Autor:** Notion AI — Auditor Cuantitativo.
- **Rama:** `research/bt2a-gc-sltp-breakeven-design-v1-20260830`
- **Base:** `research/bt2a-nq-gate1-v1-20260829` @ `c7a81dec3700eb162fc8e3ce8c00c8a8da44e3a1`
- **Referente rector:** `docs/NORTH_STAR.md` (sha256 del cuerpo `d85364e21951980c…`, citado de `CLAUDE.md` @ `c7a81de`, blob `215ec70fe8901b2e5f424379aa2d294a2093b654`).
- **Auditoría previa relacionada:** `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` (verificó que ninguna lógica asimétrica ni breakeven fue medida jamás en el proyecto).
- **NO autoriza:** ejecución, acceso a outcomes nuevos, freeze, ni selección de ganador. La ejecución exige spec JSON congelado + token de ejecución separado + Kaggle (política `KAGGLE_ONLY_EXECUTION_POLICY_V1`).

## 1. La hipótesis, en las palabras de Nico

> «tras una burbuja el precio: o hace una pequeña excursión a favor y se va al stop (escenario ideal de break even) o se va en favor de la entrada sin regresar al punto de entrada (escenario ideal de tp)»

Y la corrección de fondo de Nico (2026-08-30): **el gatillo de breakeven no puede ser un valor arbitrario** — hay que barrer el espacio de reglas y que el resultado diga, con honestidad estadística, si alguna región funciona y cuál es la más sólida.

Formalización en dos arquetipos de trayectoria post-entrada (evento K_ABS, dirección de la señal BT2A):

- **Arquetipo BE (breakeven ideal):** excursión favorable acotada — MFE alcanza un gatillo chico G — seguida de reversión al punto de entrada. Con stop fijo en −SL el trade pierde −SL; con stop movido a entrada al tocar +G, el trade raspa (~0 antes de costos). El valor de la lógica es **pérdida evitada**.
- **Arquetipo TP (TP ideal):** movimiento favorable sostenido **sin regreso** al punto de entrada. El stop de breakeven nunca se activa; el TP se captura íntegro.
- **Costo de la lógica BE, declarado de entrada:** los trades intermedios — alcanzan +G, regresan a entrada (scrape a 0) y **después** habrían llegado a TP — son confiscados por el breakeven. La pregunta económica no es "¿el BE salva trades?" sino **si la tasa de rescate supera a la tasa de confiscación** en expectativa neta. Este costo está documentado en la literatura de practitioners como el modo de falla central del breakeven stop (tradeciety, "Why you lose money with break-even stops").

**Pregunta económica del diseño:** ¿existe alguna **región** del espacio de reglas de salida (asimétrica fija y/o breakeven) que mejore la expectativa neta por señal contra la base simétrica congelada, después del modelo de costos de GC, con inferencia clusterizada por sesión CME — y si no existe, cuál es la región menos mala y qué tan informativo es el dato para decirlo?

## 2. Posición en la cadena del candidato y en el firewall

- Cadena permanente: geometría/lifecycle → información → P&L bruto → edge neto. Gate 1 GC midió asimetría de recorrido (d_hat = mediana(MFE) − mediana(MAE), **sin barreras**); P2A soportó el mecanismo direccional como diagnóstico post-selección (`P2_DIAGNOSTIC_MECHANISM_SUPPORTED`, `confirmatory_eligible=false`); **este diseño es el eslabón P&L bruto/neto** — el que P2B debía medir y nunca midió (`P2B = IMPLEMENTED_NOT_RUN`; ver §7).
- **Nota de literatura que refuerza la cadena:** Kaminski & Lo ("When do stop-loss rules stop losses?", SSRN 968338) demuestran que bajo random walk los stops siempre restan expectativa y sólo agregan valor en presencia de momentum/serial correlation real. Traducción a EdgeLab: una lógica BE/SL-TP sólo puede sumar si el mecanismo direccional de P2A es real. Si esta campaña diera positivo sin mecanismo, sospechar del artefacto antes que celebrar.
- Guardrail vigente (`docs/CURRENT.md`): «Gate 1 no se reabre para elegir SL/TP». Este diseño **no reabre Gate 1**: es una capa de outcomes nueva, downstream, con preregistro propio.
- Etiquetas epistémicas (ATJ-16): la observación motivante es `USER_REPORTED`; toda medición de esta campaña será `MEASURED_COMMITTED` o no existirá. GC es **desarrollo exploratorio gastado** (outcomes P2A abiertos): nada de lo medido acá puede ser confirmatorio. La confirmación sólo puede venir del holdout (una apertura por candidato, post-G3) o de transferencia a NQ **después** de Gate 1 NQ.

## 3. Población y espacio de eventos (enumeración obligatoria)

**Población propuesta:** eventos del Event Store canónico BT2A GC — `canonical_event_store_payload_sha256: 602f8f18467f6be081f36e8fc08f5d7e703f510a088afeb480d0b27b5e678e1d` — 22.202 eventos, 234 sesiones CME, 5 contratos (GC 12-25, 02-26, 04-26, 06-26, 08-26), sesión máxima 2026-06-30 (pre-holdout).

- **Brazos:** K_ABS (primario, 16.940 eventos), K_BT2 (5.262), N_RAND (control congelado, 10.000 réplicas), K_ABS_SHUFFLE (control secundario).
- **Espacio del que se extrae:** todas las emisiones del headline BigTrap2Absorption congelado (`tape_window_ticks=25`, `absorption_pct=90`, `absorption_lookback=500`, `min_history_buckets=200`, `min_stacked_rows=2`, `min_trap_frac=0,2`, `require_flow_side_match=true`) sobre el universo de oro GC, más sus controles matched. Enumeración escrita en `specs/bt2_absorption_gate1_v1.json` y enmiendas all5.
- **Alternativas escritas y descartadas:** (i) re-medir señales con otros parámetros headline — sería campaña de señal nueva, no de lógica de salida; (ii) eventos NQ — Gate 1 NQ aún no midió el mecanismo direccional; la cadena prohíbe P&L antes que información; queda como transferencia condicionada (§11); (iii) subpoblación por fase horaria como población primaria — P2A clock-heterogeneity = `COMPLETE_NO_CLOCK_HETEROGENEITY_SIGNAL`; queda como desagregación descriptiva rotulada.
- **Condición de refutación de la población:** si la auditoría de admisión (`docs/research/BT2_ABSORPTION_GATE1_ALL5_ADMISSION_AUDIT_2026-08-26.json`) dejara de reproducirse sobre el store `602f8f18…`, la población no es la declarada y la campaña no corre.

## 4. Familias de reglas de salida (definiciones target-free) — V1.1: G densa, no arbitraria

**Entrada común** (idéntica al P2B congelado): señal disponible al cierre de barra; entrada agresiva a mercado en el primer tick canónico estrictamente posterior a la señal; ancla de fill sin slippage; frontera de sesión CME dura; empate en la misma observación → adverso; cierre de sesión fuerza salida a mercado; una ejecución por señal por celda (`FIRST_EXECUTABLE_SIGNAL_WINS_PER_CELL`).

### Familia REF — referencia simétrica (16 celdas)
SL = TP = B, con [5,9,18,30] × [25,50,100,250] — idénticas al kernel P2B. **Política de reutilización (DP3):** si existe artefacto P2B válido, se consume y NO se re-mide; si no existe, estas 16 celdas se cobran al presupuesto de esta campaña.

### Familia ASIM — asimétrica fija (24 celdas primarias)
SL ∈ {5,9,18,30}, TP ∈ {5,9,18,30}, SL ≠ TP → 12 combinaciones × horizontes {25, 250} = **24 celdas primarias**. Horizontes intermedios {50, 100}: desagregación descriptiva rotulada, fuera de la corrección primaria.

### Familia BE — breakeven con gatillo DENSO (348 celdas primarias)

**El cambio V1.1:** el gatillo G deja de ser {5,9,18} elegido a mano y pasa a ser una **grilla densa**:

- **G ∈ {2,3,4,…,30} ticks** (29 valores) — toda la escala relevante entre el ruido de spread y la barrera máxima congelada.
- **Anclaje estructural anti-arbitrariedad (target-free):** además de ticks crudos, cada G se reporta re-expresado en unidades estructurales congeladas: múltiplos del spread round-trip (1,0 tick, asunción congelada P2B) y de la mediana de rango de barra del instrumento (estadístico de contexto, no outcome — misma clase que las b9_metrics del spec Gate 1). Así, si la región sólida aparece en "G ≈ 2×spread" en vez de "G = 7", la lectura es estructural y portable, no un número mágico.
- Parámetros restantes: TP ∈ {9, 18, 30}, SL0 ∈ {18, 30}, H ∈ {25, 250} → 29 × 3 × 2 × 2 = **348 celdas primarias**.
- Restricciones estructurales declaradas: G < TP siempre (un gatillo ≥ TP es otra regla, no la hipótesis de Nico); si G es inalcanzable dentro de H, la celda es mecánicamente TIMEOUT-dominada — no se descarta en silencio: se reporta la **tasa de activación del gatillo por celda** (ATJ-15, lineage de denominadores) y la celda entra al paisaje con esa tasa visible.
- **Regla de lectura:** la unidad de análisis es la **curva de respuesta** expectativa neta vs. G (superficie G × TP × SL0 × H), no las 348 celdas como tests aislados (ATJ-09: preservar continuas las variables mientras alcance la cobertura).

### Capa 0 — censo de arquetipos, ahora en función de g (descriptiva, declarada)

Distribución conjunta por celda de: MFE/MAE, tiempo al primer paso, y los estadísticos BE clave **como función del gatillo**: **P(regreso a entrada | MFE ≥ g)** (tasa de rescate potencial) y **P(TP después de scrape | MFE ≥ g y regreso)** (tasa de confiscación), para g recorriendo la misma grilla densa. El cruce de ambas curvas es la respuesta estructural a "dónde deja de ser arbitrario": si existe un g donde rescate ≫ confiscación de forma estable por sesión, ahí vive la lógica; si las curvas son planas o cruzan en cualquier punto según la sesión, la premisa de los dos arquetipos no tiene soporte. Motiva e interpreta; no alimenta selección. Sigue siendo acceso a outcomes: se mide post-freeze junto al resto, no antes.

## 5. Presupuesto de multiplicidad — V1.1

- **Primarias: 372 celdas** (24 ASIM + 348 BE); corrección family-wise sobre las 372, por separado por escenario de costo (base/adverso).
- **Método primario: Romano-Wolf stepdown** (Romano & Wolf, Econometrica 2005; JASA 2005) sobre el mismo bootstrap clusterizado por sesión — controla FWER y explota la dependencia entre celdas (las G vecinas son casi colineales: exactamente el caso donde Holm regala potencia). **Holm-372 se publica como cota conservadora de referencia.** SPA (White) disponible en el repo (`validation/spa.py`) como sensibilidad.
- REF: cobradas sólo si se miden en esta campaña (DP3) → presupuesto total en ese caso: 388.
- Secundarias rotuladas (fuera de la corrección primaria, nunca activan etiqueta positiva por sí solas): horizontes intermedios, fase horaria, contrato, Capa 0, unidades estructurales de G.
- `N_eff` del manifiesto = 372 (o 388), declarado para DSR. Agregar variantes después de correr = campaña nueva que hereda el presupuesto acumulado (regla anti-gaming, `edge_validation_contract.md`).
- **Ledger completo:** las 372 celdas se publican, sobrevivan o no — el paisaje completo es el entregable (regla de publicación total del proyecto; ATJ-12).

## 6. Economía (GC, sin transportar)

Modelo de costos congelado de P2B (`USER_SUPPLIED_FROZEN_ASSUMPTION_2026-08-27`): base = 3,5 ticks all-in (USD 35); adverso = 5,5 ticks (USD 55). Tick GC = 0,10 puntos = USD 10. Prohibido transportar a otro instrumento.

Estimandos: `NET_USD_PER_TRADE_EQUAL_SESSION`, `NET_TICKS_PER_TRADE_EQUAL_SESSION`, `NETO_POR_SEÑAL_ELEGIBLE`, desglose RTH/sesión completa, turnover y tasa de rechazo por concurrencia. Pérdida por trade en loss-series para MCS: −net_ticks por sesión-celda.

**Nota de magnitud target-free (aritmética sobre costos congelados, sin outcomes):** con fricción base de 3,5t, cualquier celda cuyo payoff bruto mediano sea chico parte en desventaja estructural — en particular las celdas BE con G chico, donde el valor por trade rescata como mucho unos pocos ticks de pérdida evitada contra 3,5t de fricción por trade. Se declara ahora para que una matriz negativa no se lea como falla de ejecución sino como lo que sería: el costo fijo comiéndose la lógica. Corolario: si alguna región sobrevive, casi con certeza no estará en G muy chico — y eso también es información.

## 7. Relación con P2B y con el reclamo sin artefacto

P2B (16 celdas simétricas, USD netos) está congelado y **nunca ejecutado**. El reclamo del canal («todas supported: false, todas negativas») está clasificado **NO EVIDENCIA** hasta artefacto o retracción (`docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §3). Consecuencias de diseño:

1. Este documento NO puede apoyarse en ese reclamo para podar REF ni para justificar la asimetría.
2. Si aparece un artefacto P2B válido → REF se reutiliza (ATJ-08), no se re-mide.
3. Si la retracción confirma que nunca corrió → REF se mide aquí y P2B queda históricamente superado por esta campaña, **sin modificar su spec congelado**.

## 8. Inferencia y selección robusta — V1.1

Unidad: `CME_SESSION`; pesos iguales por sesión; Webb six-point wild cluster bootstrap, 10.000 réplicas, IC95 bilateral; semillas declaradas en el spec. Análisis de potencia (MDE por celda) **antes** de la ejecución — misma disciplina que Gate 1 NQ. Para GC exploratorio es admisible planificar con la SD pareada por sesión derivada de los outcomes P2A ya abiertos; se declarará como tal. Celdas sin potencia → etiqueta `INCONCLUSIVE_POWER`, no silencio.

**Cómo se responde "cuál es mejor y más sólida" sin trampa (entregable en tres capas, todo predeclarado):**

1. **Model Confidence Set (Hansen, Lunde & Nason, Econometrica 2011)** al 95% y 90% sobre las loss-series por sesión: el conjunto de reglas estadísticamente indistinguibles de la mejor. Es el análogo a un IC para "qué regla es la mejor": si el dato es poco informativo, el MCS es grande y esa ES la respuesta honesta; si es informativo, el MCS acota la región ganadora. Nunca un ganador puntual.
2. **Regla de meseta (plateau) predeclarada:** región robusta = máximo conjunto contiguo de G (dentro de cada slice TP × SL0 × H) con lower95 de expectativa neta > 0 y con *parameter stability* ≥ 70% de la vecindad ±20% rentable en base (umbral de la literatura de plateau; LuxAlgo/NTUT-PSO). Pico aislado sin meseta = frágil por definición, aunque sobreviva a RW.
3. **Estabilidad temporal:** walk-forward por contrato (fold = contrato; re-selección de la región usando sólo contratos anteriores; el agregado WF-OOS debe ser > 0) + PBO/CSCV (S = 8) sobre la matriz completa celdas × tiempo + DSR con N_eff = 372/388. Todo ya existe en el repo (`validation/pbo.py`, `edgelab/research/g2*.py`); se reusa, no se reinventa.

## 9. Reglas de decisión y etiquetas

- **Permitidas:** `BT2A_GC_EXITLOGIC_EXPLORATORY_ROBUST_REGION_EXISTS`, `BT2A_GC_EXITLOGIC_EXPLORATORY_BASE_ONLY`, `BT2A_GC_EXITLOGIC_EXPLORATORY_EXECUTION_NEGATIVE`, `BT2A_GC_EXITLOGIC_INCONCLUSIVE`.
- **Prohibidas:** `EDGE_DECLARED`, `CONFIRMATORY_PASS`, `PROMOTED`, `WINNER_SELECTED`, `BEST_EXIT_RULE`, `BEST_G`.
- `winner_selection_allowed=false`, `promotion_allowed=false`, `edge_declaration_allowed=false`. El MCS y la meseta identifican **regiones**, nunca un punto elegido.
- Si ninguna celda sobrevive Romano-Wolf y el MCS es no-informativo → etiqueta `EXECUTION_NEGATIVE` o `INCONCLUSIVE`, y la región descriptiva menos mala se reporta como **NO ACCIONABLE** para confirmación sin datos independientes (transferencia NQ post-Gate 1 NQ, o holdout vía G4 con su única apertura). "Quizás ninguna funciona pero sugiere cuál es mejor" se implementa así: la sugerencia existe, pero nace con su etiqueta de evidencia y su camino de confirmación separado (ATJ-13: EF2 genera hipótesis, nunca confirma).
- Cualquier candidato posterior exige la cadena completa: G2 (PrimaryCI, PBO ≤ 0,50, DSR ≥ 0,95 con N_eff de manifiesto, walk-forward, sensibilidad ±1 paso), G3 (cuatro escenarios de costo), G4 (holdout, una sola apertura). Este diseño no otorga nada de eso.

## 10. Cómo podría refutarse

- Ninguna celda ASIM/BE supera a su REF pareada en expectativa neta base → la forma de la salida no agrega nada: la asimetría de recorrido de Gate 1 no se monetiza con reglas estáticas.
- BE mejora en base pero colapsa en adverso (caída > 0,5× de la expectancy base) → la lógica es frágil al costo, no al mercado.
- Capa 0 muestra que los dos arquetipos no existen como tipos separados (P(regreso | MFE ≥ g) plana en g) → la intuición motivante no tiene soporte de trayectoria y ASIM/BE eran el instrumento equivocado.
- La curva de respuesta en G es ruido sin meseta (ninguna región contigua estable) → no hay gatillo no arbitrario que elegir: la pregunta misma muere, con evidencia.
- La tasa de confiscación (§4, Capa 0) supera a la tasa de rescate en toda la grilla → el breakeven destruye valor aunque "se vea" bien en el chart.
- El MCS contiene a la mayoría de las celdas → el dato no distingue reglas; respuesta honesta: muestra insuficiente para la pregunta, no selección encubierta.
- Kaminski & Lo como prior: si el mecanismo direccional de P2A fuera artefacto, toda regla de salida resta — un resultado positivo aquí obliga a re-verificar P2A antes de creérselo.

## 11. Transferencia NQ (condicionada, no activa)

Sólo si Gate 1 NQ se ejecuta y soporta el mecanismo direccional: mismo esqueleto de diseño, con economía NQ estimada propia (prohibido transportar la de GC) y población del Event Store NQ correspondiente. Redactar esa sección como enmienda es trabajo posterior al freeze de Gate 1 NQ.

## 12. Datos faltantes / precondiciones antes de freeze

1. Verificar contra el Event Store `602f8f18…` qué capas de trayectoria ya existen (`mfe_mae`, `first_passage` simétrico) y qué hay que medir de nuevo (primer paso asimétrico; regreso-a-entrada condicional a MFE ≥ g sobre grilla densa). Reuso antes que recómputo (ATJ-08).
2. Implementación de Romano-Wolf stepdown y MCS **verificada contra datos sintéticos con verdad conocida** (regla del proyecto: un gate que sólo sabe decir "no" no sirve — ver `edge_validation_contract.md` §G2). No existe aún en el repo; entra como código nuevo con tests (ruido ⇒ FWER controlado; efecto plantado ⇒ detección; meseta plantada ⇒ región detectada; pico aislado ⇒ rechazado por la regla de meseta).
3. Política `KAGGLE_ONLY_EXECUTION_POLICY_V1`: la medición corre en Kaggle con tokens de runtime; el freeze local no toca precios. Factibilidad de cómputo: 372 celdas × 22.202 eventos es vectorizable y barato; el cuello es el bootstrap clusterizado (10.000 réplicas × sesiones), declarado y presupuestado en el spec.
4. Respuestas de Nico a DP1–DP5 (§13).
5. Estado del artefacto P2B (§7).

## 13. Puntos de decisión para Nico (bloquean la redacción del spec de freeze)

- **DP1 — Alcance:** ¿GC exploratorio solo, con transferencia NQ condicionada? (recomendado: sí)
- **DP2 — Grilla V1.1:** ¿G densa {2..30} con curva de respuesta y H ∈ {25, 250} (372 primarias — recomendado, es tu pedido de no arbitrariedad), o recorte a H fija en 250 para ganar potencia por celda (**186 primarias**: 29×3×2 BE + 12 ASIM con una sola H)?
- **DP3 — REF:** ¿la política de reutilización de P2B de §7? (recomendado: sí)
- **DP4 — Mecánica BE:** ¿scrape exactamente a entrada, o a entrada − 1 tick (cubre parte de la fricción)? ¿Sin re-entrada tras scrape (una ejecución por señal, como P2B)? (recomendado: scrape a entrada exacta, sin re-entrada — más limpio de auditar)
- **DP5 — Capa 0:** ¿censo de arquetipos en función de g como familia descriptiva declarada dentro de esta campaña (recomendado) o como campaña aparte?

## 14. Lo que este documento NO decide ni autoriza

No ejecuta nada; no abre outcomes; no toca el holdout; no modifica specs congelados (Gate 1, P2A, P2B intactos); no registra la hipótesis en `docs/HIPOTESIS_PENDIENTES.md` (pendiente: entrada HP-005 apuntando a este documento); no es el spec de freeze — el spec JSON se redacta DESPUÉS de las respuestas a DP1–DP5.

## 15. Fundamentación metodológica (research 2026-08-30)

Fuentes consultadas para el rediseño V1.1 (búsqueda web, 2026-08-30):

- **Hansen, Lunde & Nason (2011), "The Model Confidence Set", Econometrica 79(2), 453–497** — el MCS contiene al mejor modelo con confianza dada; datos poco informativos ⇒ MCS grande. Base del entregable "conjunto de reglas mejores" (§8.1). https://www.econometricsociety.org/publications/econometrica/2011/03/01/model-confidence-set
- **Romano & Wolf (2005), "Stepwise Multiple Testing as Formalized Data Snooping", Econometrica 73(4)** y **(2005) JASA 100(469)** — stepdown bootstrap que controla FWER explotando dependencia; motivado literalmente por "un trader que backtesta varias ideas y quiere saber cuántas valen". Base de la corrección primaria (§5). https://www.econometricsociety.org/publications/econometrica/2005/07/01/stepwise-multiple-testing-formalized-data-snooping
- **Kaminski & Lo (2007/2014), "When do stop-loss rules stop losses?"** — bajo random walk los stops siempre restan expectativa; sólo suman con momentum real. Prior estructural de la campaña y refutación cruzada con P2A (§2, §10). https://ssrn.com/abstract=968338
- **Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting"** y **Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", JPM 40(5)** — PBO/CSCV y DSR con N_eff; ya implementados en el repo, se aplican a la matriz completa (§8.3). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- **Literatura de meseta de parámetros:** LuxAlgo, "Stress-Test Your Algorithmic Trading Strategy" (meseta vs. aguja; sensibilidad paramétrica); NTUT, "On the design of searching algorithm for parameter plateau in quantitative trading strategies" (plateau score; los picos aislados fallan OOS y las mesetas sobreviven); umbral de estabilidad de vecindad 70–80% (PickMyTrade validation guide). Base de la regla de meseta (§8.2). https://www.luxalgo.com/blog/stress-test-your-algorithmic-trading-strategy-guide-to-avoiding-overfitting/ · https://www.sciencedirect.com/science/article/pii/S095070512400265X
- **Evidencia practitioner sobre breakeven stops:** tradeciety, "Why You Lose Money With Break-Even Stops" — el modo de falla documentado es la confiscación de ganadores por retracement; ya declarado como costo estructural en §1. https://tradeciety.com/why-you-lose-money-with-break-even-stops

**Lo que NO se encontró:** ninguna fuente que valide elegir un gatillo BE puntual por observación visual — consistente con el pedido de Nico de grilla densa. Tampoco evidencia académica específica de breakeven stops en futuros intradía tick-level: esta campaña mediría algo que la literatura no resolvió, lo cual sube el valor del resultado en cualquiera de los dos signos.

## Aporte al referente

La intuición SL/TP + breakeven de Nico queda formalizada como diseño preregistrable V1.1: gatillo BE denso y estructuralmente anclado (nada arbitrario), 372 celdas primarias con Romano-Wolf como corrección primaria y MCS + regla de meseta + walk-forward como respuesta honesta a "cuál es mejor y más sólida", economía GC congelada reutilizada, prior de Kaminski-Lo integrado como refutación cruzada, y los cinco puntos de decisión que bloquean el freeze. Distancia reducida hacia un edge neto: la pregunta de salida pasa de observación de chart a campaña diseñada con metodología publicada — **sin gastar ni un outcome**.
