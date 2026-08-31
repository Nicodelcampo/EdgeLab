# BT2A NQ — Diseño de medición de lógicas de salida SL/TP asimétricas y breakeven (V1, borrador)

- **Fecha:** 2026-08-31 (ART) · **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`
- **Autor:** Notion AI — Auditor Cuantitativo.
- **Rama:** `research/bt2a-nq-gate1-runner-impl-v1-20260831`
- **Padre metodológico:** `docs/research/BT2A_GC_SLTP_BREAKEVEN_DESIGN_V1_2026-08-30.md` (V1.1) — este documento ES la transferencia NQ que su §11 dejó condicionada: *"Sólo si Gate 1 NQ se ejecuta y soporta el mecanismo direccional: mismo esqueleto de diseño, con economía NQ estimada propia (prohibido transportar la de GC) y población del Event Store NQ correspondiente."* Todo lo metodológico (Romano-Wolf, MCS, regla de meseta, walk-forward, PBO/CSCV, DSR, prior de Kaminski-Lo) se hereda de ahí y no se duplica acá.
- **Pedido de Nico (chat, 2026-08-31 ~14:07 ART):** "prepará la corrida de sl tp y be para el nq si sale bien gate1".
- **NO autoriza:** ejecución, acceso a outcomes nuevos, freeze, ni selección de ganador. La ejecución exige: (i) resultado de Gate 1 NQ con etiqueta `BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED`, (ii) spec JSON de esta campaña congelado con su propio token de freeze, (iii) token de ejecución separado, (iv) sobre Kaggle con preflight físico (mismo patrón que el runner de Gate 1).

## 1. Condición de apertura (el gatillo es una etiqueta, no una impresión)

Esta campaña **sólo se abre** si la corrida de Gate 1 NQ (spec `b9e75c25...`, rebind de hoy incluido) devuelve `BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED` con sus celdas positivas enumeradas (`positive_supported_cells`).

- Si Gate 1 da `NO_DIRECTIONAL_MECHANISM`: el prior de Kaminski & Lo manda — sin mecanismo direccional real, toda regla de salida resta expectativa bajo fricción, y **esta campaña no se abre**. No hay SL/TP que rescatar si no hay excursión direccional que cosechar.
- Si da `INCONCLUSIVE_POWER` o `ABSTAIN_*`: tampoco se abre; primero se resuelve la potencia o la cobertura.
- Las celdas soportadas de Gate 1 (barrera × horizonte) son las **candidatas estructurales** de esta campaña: la REF y las grillas se anclan a esas barreras/horizontes, no a un espacio nuevo elegido a posteriori.

## 2. La hipótesis (heredada, en las palabras de Nico)

> «tras una burbuja el precio: o hace una pequeña excursión a favor y se va al stop (escenario ideal de break even) o se va en favor de la entrada sin regresar al punto de entrada (escenario ideal de tp)»

Los dos arquetipos de trayectoria (BE = rescate de pérdida; TP = captura íntegra), el costo estructural declarado (los trades intermedios confiscados por el breakeven), y la pregunta económica —**si la tasa de rescate supera a la de confiscación en expectativa neta**— son los del documento GC, §1. Lo que cambia es el instrumento, la población y la economía.

## 3. Población y espacio de eventos (enumeración obligatoria)

**Población propuesta:** eventos del Event Store BT2A NQ congelado — manifest `1e45c43fa60327b67aeb618d00b4137b82cc6c44ad43f348fc5bca8250ef90ea` (rebind de hoy, `docs/research/DECISION_NICO_REBIND_EVENT_STORE_MANIFEST_2026-08-31.md`) — **152.695 eventos K_ABS, 234 sesiones CME, 5 contratos** (NQ 09-25, 12-25, 03-26, 06-26, 09-26), sesión máxima 2026-06-30, holdout afuera (`1782856800000000000`).

- **Brazos:** K_ABS (primario), K_BT2 (benchmark, coords `tick_25_IMB30_VOL10`, dataset ya stageado), N_RAND (control congelado con apareamiento por estrato y exclusión del propio anchor — versión post-auditoría del runner), K_ABS_SHUFFLE (control secundario). **Los mismos brazos de Gate 1: cero acceso a datos nuevo para preparar esta campaña.**
- **Espacio del que se extrae:** las emisiones del config seleccionado `bt2a_nq_7e84981882b0b380` (INFORMAL_EARLY_STOP — la confirmación viene de Gate 1, no de la selección) sobre el universo NQ pre-holdout, más sus controles.
- **Condición de refutación de la población:** si la verificación de hashes del event store deja de reproducirse contra el manifest rebindeado, la población no es la declarada y la campaña no corre.

## 4. Familias de reglas de salida (definiciones target-free)

**Entrada común** (idéntica al patrón P2B/GC): señal disponible al cierre de la observación; entrada a mercado en el primer tick canónico estrictamente posterior; fill sin slippage de ancla (el slippage entra por el modelo de costos, §6); frontera de sesión CME dura; empate en la misma observación → adverso; cierre de sesión fuerza salida; una ejecución por señal por celda (`FIRST_EXECUTABLE_SIGNAL_WINS_PER_CELL`).

### Familia REF — referencia simétrica (16 celdas)
SL = TP = B sobre las 16 celdas de Gate 1: [5, 9, 18, 30] × [25, 50, 100, 250]. **Reuso antes que recómputo (ATJ-08):** la corrida de Gate 1 ya produce por evento `min(MFE,B) − min(MAE,B)` y las trayectorias completas están computadas por celda — lo que sea reutilizable se consume, no se re-mide.

### Familia ASIM — asimétrica fija (24 celdas primarias)
SL ∈ {5,9,18,30}, TP ∈ {5,9,18,30}, SL ≠ TP → 12 combinaciones × horizontes {25, 250} = **24 primarias**. Horizontes intermedios {50, 100}: desagregación descriptiva rotulada.

### Familia BE — breakeven con gatillo DENSO (348 celdas primarias)
Idéntica a la V1.1 de GC: **G ∈ {2..30} ticks** (29 valores, nada arbitrario), TP ∈ {9,18,30}, SL0 ∈ {18,30}, H ∈ {25,250} → 348 primarias. Restricciones: G < TP siempre; tasa de activación del gatillo reportada por celda (lineage de denominadores); G además re-expresado en unidades estructurales (múltiplos del spread y de la mediana de rango de barra de NQ — contexto, no outcome).

### Capa 0 — censo de arquetipos en función de g (descriptiva, declarada)
P(regreso a entrada | MFE ≥ g) y P(TP después de scrape | MFE ≥ g y regreso) sobre la grilla densa. El cruce de las curvas responde estructuralmente "dónde deja de ser arbitrario". Motiva e interpreta; no alimenta selección. Se mide post-freeze, no antes.

## 5. Presupuesto de multiplicidad

**372 primarias** (24 ASIM + 348 BE) + REF sólo si no se reutilizan de Gate 1/P2B-equivalente (→ 388). Corrección primaria: **Romano-Wolf stepdown** sobre bootstrap clusterizado por sesión; Holm-372 como cota conservadora publicada. Secundarias rotuladas: horizontes intermedios, fase horaria, contrato, Capa 0, unidades estructurales. `N_eff = 372/388` declarado para DSR. **Ledger completo: las 372 celdas se publican, sobrevivan o no.** Regla anti-gaming: agregar variantes después de correr = campaña nueva que hereda el presupuesto acumulado.

## 6. Economía NQ (NO congelada — input pendiente de Nico)

**Prohibido transportar la de GC** (3,5t/5,5t). Estructura heredada, números no:

- NQ: tick = 0,25 puntos = **USD 5,00**. El modelo de costos es `base` y `adverso` en ticks all-in (comisiones + spread + slippage), a aportar por Nico como `USER_SUPPLIED_FROZEN_ASSUMPTION` (mismo formato que GC, `2026-08-27`). **Dato que NO tengo y no invento: la comisión real por lado y el slippage típico de NQ en la cuenta de Nico.**
- Nota de magnitud target-free (aritmética de estructura, sin outcomes): la fricción fija por round-trip se cobra igual en cada celda; las celdas BE con G chico rescatan pocos ticks de pérdida evitada por trade — si la fricción NQ es comparable en ticks a la de GC, la lectura estructural del documento GC se traslada: si alguna región sobrevive, casi con certeza no estará en G muy chico.
- Estimandos: `NET_USD_PER_TRADE_EQUAL_SESSION`, `NET_TICKS_PER_TRADE_EQUAL_SESSION`, `NETO_POR_SEÑAL_ELEGIBLE`, desglose RTH/sesión, turnover y tasa de rechazo por concurrencia. Loss-series por sesión-celda para MCS: −net_ticks.

## 7. Relación con Gate 1 NQ y con el pipeline ya verificado

- Gate 1 NQ todavía **no corrió** (kernel pendiente: dataset del event store por subir + lanzamiento; token 4 sin gastar). Este documento no la apura ni la modifica.
- El runner post-auditoría (`8fabfa29`) ya computa por evento las excursiones MFE/MAE capeadas en las 16 celdas y respeta la mecánica de sesión. La capa nueva que esta campaña necesita es: **primer pasaje con barreras asimétricas** (SL≠TP), **regreso-a-entrada condicional a MFE ≥ g** sobre grilla densa, y la conversión a PnL neto por sesión. Reuso de primitivas `edgelab/research/bt2_gate1_outcomes.py` (PathCache, directional_excursions) como hizo el runner de Gate 1.
- Si Gate 1 se corre con checkpointing atómico por contrato-sesión (lo hace), los stats por celda son reutilizables para la Capa 0 sin re-cómputo de trayectorias.

## 8. Inferencia y selección robusta (heredada de GC §8, sin cambios)

Unidad `CME_SESSION`; pesos iguales; Webb six-point wild cluster bootstrap, 10.000 réplicas, IC95 bilateral; semillas declaradas en el spec. Análisis de potencia (MDE por celda) **antes** de la ejecución — misma disciplina que Gate 1 (MDE 2,9t, SD pareada 11,528529, 228 requeridas: el precedente está). Entregable en tres capas predeclaradas: **MCS** al 95/90% sobre loss-series (regiones, nunca un ganador puntual), **regla de meseta** (máximo conjunto contiguo de G con lower95 > 0 y estabilidad de vecindad ≥ 70%), **estabilidad temporal** (walk-forward por contrato + PBO/CSCV S=8 + DSR con N_eff del manifiesto).

## 9. Reglas de decisión y etiquetas

- **Permitidas:** `BT2A_NQ_EXITLOGIC_EXPLORATORY_ROBUST_REGION_EXISTS`, `BT2A_NQ_EXITLOGIC_EXPLORATORY_BASE_ONLY`, `BT2A_NQ_EXITLOGIC_EXPLORATORY_EXECUTION_NEGATIVE`, `BT2A_NQ_EXITLOGIC_INCONCLUSIVE`.
- **Prohibidas:** `EDGE_DECLARED`, `CONFIRMATORY_PASS`, `PROMOTED`, `WINNER_SELECTED`, `BEST_EXIT_RULE`, `BEST_G`. El MCS y la meseta identifican regiones, nunca un punto.
- Si ninguna celda sobrevive Romano-Wolf y el MCS es no-informativo → `EXECUTION_NEGATIVE` o `INCONCLUSIVE`, y la región descriptiva menos mala se reporta como **NO ACCIONABLE** para confirmación sin datos independientes (holdout, vía G4, una sola apertura por candidato).
- Cualquier candidato posterior exige la cadena G2/G3/G4 completa. Este diseño no otorga nada de eso.

## 10. Cómo podría refutarse

Heredadas de GC §10, adaptadas: ninguna ASIM/BE supera a su REF pareada en expectativa neta base (la asimetría de recorrido no se monetiza con reglas estáticas); BE mejora en base y colapsa en adverso (frágil al costo, no al mercado); Capa 0 muestra que los arquetipos no existen como tipos separados en NQ; la curva de respuesta en G es ruido sin meseta; la tasa de confiscación supera a la de rescate en toda la grilla; el MCS contiene a la mayoría de las celdas (dato insuficiente para la pregunta). Y la refutación cruzada: un positivo acá con un Gate 1 débil obliga a re-verificar Gate 1 antes que celebrar.

## 11. Qué cambia respecto a GC (la transferencia, explícita)

1. **Instrumento y economía:** NQ con costos propios pendientes (§6) — nada de GC se transporta.
2. **Población:** event store NQ congelado y rebindeado (§3) — 152.695 eventos contra 22.202 de GC; la potencia por celda se re-computa con la SD pareada que mida Gate 1 NQ, no con la de GC.
3. **Gate antecesor:** Gate 1 NQ (16 celdas, Holm, spec `b9e75c25`) en vez de la cadena GC Gate1/P2A/P2B. La condición de apertura es su etiqueta (§1).
4. **Estado del padre metodológico:** la campaña GC es un borrador no ejecutado; Romano-Wolf stepdown y MCS **todavía no existen en el repo** (el documento GC los lista como código nuevo con tests sintéticos de verdad conocida). Si esta campaña NQ se concreta antes que la de GC, esa implementación entra acá con los mismos tests (ruido ⇒ FWER controlado; efecto plantado ⇒ detección; meseta plantada ⇒ región detectada; pico aislado ⇒ rechazado).

## 12. Datos faltantes / precondiciones antes de freeze

1. **Resultado de Gate 1 NQ** con etiqueta y celdas soportadas (bloquea todo lo demás).
2. **Modelo de costos NQ de Nico** (§6) — sin él no hay expectativa neta.
3. Respuestas de Nico a DP1–DP5 (§13).
4. Implementación verificada de Romano-Wolf + MCS (§11.4) y la capa de primer pasaje asimétrico + regreso-a-entrada (§7).
5. Política KAGGLE_ONLY: medición en Kaggle con el sobre de ejecución congelada y preflight físico; el freeze local no toca precios.

## 13. Puntos de decisión para Nico (bloquean la redacción del spec de freeze)

- **DP1 — Alcance:** ¿NQ condicionado a Gate 1 SUPPORTED, como está escrito? (recomendado: sí)
- **DP2 — Grilla:** ¿G densa {2..30} con H ∈ {25, 250} (372 primarias), o H fija en 250 para potencia por celda (**186 primarias**: 29×3×2 BE + 12 ASIM)?
- **DP3 — REF:** ¿reuso de trayectorias de Gate 1 donde aplique (recomendado: sí, ATJ-08)?
- **DP4 — Mecánica BE:** ¿scrape exactamente a entrada, o entrada − 1 tick? ¿Sin re-entrada tras scrape? (recomendado: entrada exacta, sin re-entrada — más auditable)
- **DP5 — Capa 0:** ¿censo de arquetipos dentro de esta campaña (recomendado) o aparte?
- **DP6 (nuevo, NQ):** ¿los costos base/adverso en ticks que mando a congelar? (sin esto no hay spec)

## 14. Lo que este documento NO decide ni autoriza

No ejecuta nada; no abre outcomes; no toca el holdout; no modifica specs congelados (Gate 1 NQ intacto con su rebind); no es el spec de freeze — el spec JSON se redacta DESPUÉS de las respuestas a DP1–DP6; no registra HP ni abre rama de trabajo nueva. Si Gate 1 no corre o no soporta, este documento queda como diseño listo, sin efecto.

## Aporte al referente

La capa económica de NQ (SL/TP asimétrico + breakeven denso) queda pre-diseñada con la metodología del padre GC, la población y los hashes del event store ya congelados, la condición de apertura convertida en etiqueta verificable, y los seis puntos de decisión que bloquean el freeze — **sin gastar un outcome, sin tocar la campaña en curso, y con los costos NQ marcados como lo que son: el único número que falta y que no se inventa**.
