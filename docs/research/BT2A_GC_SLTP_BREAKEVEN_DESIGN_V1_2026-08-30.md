# BT2A GC — Diseño de medición de lógicas de salida SL/TP asimétricas y breakeven (V1, borrador)

- **Fecha:** 2026-08-30 (ART)
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`
- **Autor:** Notion AI — Auditor Cuantitativo, a pedido explícito de Nico ("quiero medir BigTrap2Absorption incorporando distintas lógicas de SL/TP y break even; prepará eso mientras Claude trabaja").
- **Rama:** `research/bt2a-gc-sltp-breakeven-design-v1-20260830`
- **Base:** `research/bt2a-nq-gate1-v1-20260829` @ `c7a81dec3700eb162fc8e3ce8c00c8a8da44e3a1`
- **Referente rector:** `docs/NORTH_STAR.md` (sha256 del cuerpo `d85364e21951980c…`, citado de `CLAUDE.md` @ `c7a81de`, blob `215ec70fe8901b2e5f424379aa2d294a2093b654`).
- **Auditoría previa relacionada:** `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` (verificó que ninguna lógica asimétrica ni breakeven fue medida jamás en el proyecto).
- **NO autoriza:** ejecución, acceso a outcomes nuevos, freeze, ni selección de ganador. La ejecución exige spec JSON congelado + token de ejecución separado + Kaggle (política `KAGGLE_ONLY_EXECUTION_POLICY_V1`).

## 1. La hipótesis, en las palabras de Nico

> «tras una burbuja el precio: o hace una pequeña excursión a favor y se va al stop (escenario ideal de break even) o se va en favor de la entrada sin regresar al punto de entrada (escenario ideal de tp)»

Formalización en dos arquetipos de trayectoria post-entrada (evento K_ABS, dirección de la señal BT2A):

- **Arquetipo BE (breakeven ideal):** excursión favorable acotada — MFE alcanza un gatillo chico G — seguida de reversión al punto de entrada. Con stop fijo en −SL el trade pierde −SL; con stop movido a entrada al tocar +G, el trade raspa (~0 antes de costos). El valor de la lógica es **pérdida evitada**.
- **Arquetipo TP (TP ideal):** movimiento favorable sostenido **sin regreso** al punto de entrada. El stop de breakeven nunca se activa; el TP se captura íntegro.
- **Costo de la lógica BE, declarado de entrada:** los trades intermedios — alcanzan +G, regresan a entrada (scrape a 0) y **después** habrían llegado a TP — son confiscados por el breakeven. La pregunta económica no es "¿el BE salva trades?" sino **si la tasa de rescate supera a la tasa de confiscación** en expectativa neta.

**Pregunta económica del diseño:** ¿alguna regla de salida (asimétrica fija y/o breakeven) mejora la expectativa neta por señal contra la base simétrica congelada, después del modelo de costos de GC, con inferencia clusterizada por sesión CME?

## 2. Posición en la cadena del candidato y en el firewall

- Cadena permanente: geometría/lifecycle → información → P&L bruto → edge neto. Gate 1 GC midió asimetría de recorrido (d_hat = mediana(MFE) − mediana(MAE), **sin barreras**); P2A soportó el mecanismo direccional como diagnóstico post-selección (`P2_DIAGNOSTIC_MECHANISM_SUPPORTED`, `confirmatory_eligible=false`); **este diseño es el eslabón P&L bruto/neto** — el que P2B debía medir y nunca midió (`P2B = IMPLEMENTED_NOT_RUN`; ver §7).
- Guardrail vigente (`docs/CURRENT.md`): «Gate 1 no se reabre para elegir SL/TP». Este diseño **no reabre Gate 1**: es una capa de outcomes nueva, downstream, con preregistro propio.
- Etiquetas epistémicas (ATJ-16): la observación motivante es `USER_REPORTED`; toda medición de esta campaña será `MEASURED_COMMITTED` o no existirá. GC es **desarrollo exploratorio gastado** (outcomes P2A abiertos): nada de lo medido acá puede ser confirmatorio. La confirmación sólo puede venir del holdout (una apertura por candidato, post-G3) o de transferencia a NQ **después** de Gate 1 NQ.

## 3. Población y espacio de eventos (enumeración obligatoria)

**Población propuesta:** eventos del Event Store canónico BT2A GC — `canonical_event_store_payload_sha256: 602f8f18467f6be081f36e8fc08f5d7e703f510a088afeb480d0b27b5e678e1d` — 22.202 eventos, 234 sesiones CME, 5 contratos (GC 12-25, 02-26, 04-26, 06-26, 08-26), sesión máxima 2026-06-30 (pre-holdout).

- **Brazos:** K_ABS (primario, 16.940 eventos), K_BT2 (5.262), N_RAND (control congelado, 10.000 réplicas), K_ABS_SHUFFLE (control secundario).
- **Espacio del que se extrae:** todas las emisiones del headline BigTrap2Absorption congelado (`tape_window_ticks=25`, `absorption_pct=90`, `absorption_lookback=500`, `min_history_buckets=200`, `min_stacked_rows=2`, `min_trap_frac=0,2`, `require_flow_side_match=true`) sobre el universo de oro GC, más sus controles matched. Enumeración escrita en `specs/bt2_absorption_gate1_v1.json` y enmiendas all5.
- **Alternativas escritas y descartadas:** (i) re-medir señales con otros parámetros headline — sería campaña de señal nueva, no de lógica de salida; (ii) eventos NQ — Gate 1 NQ aún no midió el mecanismo direccional; la cadena prohíbe P&L antes que información; queda como transferencia condicionada (§11); (iii) subpoblación por fase horaria como población primaria — P2A clock-heterogeneity = `COMPLETE_NO_CLOCK_HETEROGENEITY_SIGNAL`; queda como desagregación descriptiva rotulada.
- **Condición de refutación de la población:** si la auditoría de admisión (`docs/research/BT2_ABSORPTION_GATE1_ALL5_ADMISSION_AUDIT_2026-08-26.json`) dejara de reproducirse sobre el store `602f8f18…`, la población no es la declarada y la campaña no corre.

## 4. Familias de reglas de salida (definiciones target-free)

**Entrada común** (idéntica al P2B congelado): señal disponible al cierre de barra; entrada agresiva a mercado en el primer tick canónico estrictamente posterior a la señal; ancla de fill sin slippage; frontera de sesión CME dura; empate en la misma observación → adverso; cierre de sesión fuerza salida a mercado; una ejecución por señal por celda (`FIRST_EXECUTABLE_SIGNAL_WINS_PER_CELL`).

### Familia REF — referencia simétrica (16 celdas)
SL = TP = B, con [5,9,18,30] × [25,50,100,250] — idénticas al kernel P2B. **Política de reutilización (DP3):** si existe artefacto P2B válido, se consume y NO se re-mide; si no existe, estas 16 celdas se cobran al presupuesto de esta campaña.

### Familia ASIM — asimétrica fija (24 celdas primarias)
SL ∈ {5,9,18,30}, TP ∈ {5,9,18,30}, SL ≠ TP → 12 combinaciones × horizontes {25, 250} = **24 celdas primarias**. Los horizontes {25, 250} son los extremos del conjunto congelado: acotan la escala temporal sin elegir por outcome. Horizontes intermedios {50, 100}: desagregación descriptiva rotulada, fuera de Holm.

### Familia BE — breakeven (24 celdas primarias)
Stop inicial en −SL0. Al primer toque de +G, el stop se mueve al precio de entrada (scrape = 0 de trayectoria, antes de costos). Salida por TP, por stop (−SL0 antes del gatillo, 0 después) o por timeout a mercado en H observaciones.
Grilla: SL0 ∈ {18, 30} × (G, TP) ∈ {(5,9), (5,18), (5,30), (9,18), (9,30), (18,30)} × H ∈ {25, 250} → 2 × 6 × 2 = **24 celdas primarias**.
Restricción estructural declarada: G < TP siempre (un gatillo ≥ TP es una regla distinta y no es la hipótesis de Nico).

### Capa 0 — censo de arquetipos (descriptiva, declarada)
Distribución conjunta por celda de: MFE/MAE, tiempo al primer paso, y el estadístico BE clave — **P(regreso a entrada | MFE ≥ G)** — junto a P(TP después de scrape | MFE ≥ G y regreso) (tasa de confiscación). Motiva e interpreta; no alimenta selección. Sigue siendo acceso a outcomes: se mide post-freeze junto al resto, no antes.

## 5. Presupuesto de multiplicidad

- **Primarias: 48 celdas** (24 ASIM + 24 BE); Holm sobre 48, por separado por escenario de costo (base/adverso) — misma estructura que P2B (Holm-16 → aquí Holm-48).
- REF: cobradas sólo si se miden en esta campaña (DP3) → presupuesto total en ese caso: 64.
- Secundarias rotuladas (fuera de Holm, nunca activan etiqueta positiva por sí solas): horizontes intermedios, fase horaria, contrato, Capa 0.
- `N_eff` del manifiesto = 48 (o 64). Agregar variantes después de correr = campaña nueva que hereda el presupuesto acumulado (regla anti-gaming, `edge_validation_contract.md`).

## 6. Economía (GC, sin transportar)

Modelo de costos congelado de P2B (`USER_SUPPLIED_FROZEN_ASSUMPTION_2026-08-27`): base = 3,5 ticks all-in (USD 35); adverso = 5,5 ticks (USD 55). Tick GC = 0,10 puntos = USD 10. Prohibido transportar a otro instrumento.

Estimandos: `NET_USD_PER_TRADE_EQUAL_SESSION`, `NET_TICKS_PER_TRADE_EQUAL_SESSION`, `NETO_POR_SEÑAL_ELEGIBLE`, desglose RTH/sesión completa, turnover y tasa de rechazo por concurrencia.

**Nota de magnitud target-free (aritmética sobre costos congelados, sin outcomes):** con fricción base de 3,5t, cualquier celda cuyo payoff bruto mediano sea chico parte en desventaja estructural — en particular las celdas BE con G=5, donde el valor por trade rescata como mucho unos pocos ticks de pérdida evitada contra 3,5t de fricción por trade. Se declara ahora para que una matriz negativa no se lea como falla de ejecución sino como lo que sería: el costo fijo comiéndose la lógica.

## 7. Relación con P2B y con el reclamo sin artefacto

P2B (16 celdas simétricas, USD netos) está congelado y **nunca ejecutado**. El reclamo del canal («todas supported: false, todas negativas») está clasificado **NO EVIDENCIA** hasta artefacto o retracción (`docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §3). Consecuencias de diseño:

1. Este documento NO puede apoyarse en ese reclamo para podar REF ni para justificar la asimetría.
2. Si aparece un artefacto P2B válido → REF se reutiliza (ATJ-08), no se re-mide.
3. Si la retracción confirma que nunca corrió → REF se mide aquí y P2B queda históricamente superado por esta campaña, **sin modificar su spec congelado**.

## 8. Inferencia

Unidad: `CME_SESSION`; pesos iguales por sesión; Webb six-point wild cluster bootstrap, 10.000 réplicas, IC95 bilateral; semillas declaradas en el spec. Análisis de potencia (MDE por celda) **antes** de la ejecución — misma disciplina que Gate 1 NQ. Para GC exploratorio es admisible planificar con la SD pareada por sesión derivada de los outcomes P2A ya abiertos; se declarará como tal. Celdas sin potencia → etiqueta `INCONCLUSIVE_POWER`, no silencio.

## 9. Reglas de decisión y etiquetas

- **Permitidas:** `BT2A_GC_EXITLOGIC_EXPLORATORY_ROBUST_CELL_EXISTS`, `BT2A_GC_EXITLOGIC_EXPLORATORY_BASE_ONLY`, `BT2A_GC_EXITLOGIC_EXPLORATORY_EXECUTION_NEGATIVE`, `BT2A_GC_EXITLOGIC_INCONCLUSIVE`.
- **Prohibidas:** `EDGE_DECLARED`, `CONFIRMATORY_PASS`, `PROMOTED`, `WINNER_SELECTED`, `BEST_EXIT_RULE`.
- `winner_selection_allowed=false`, `promotion_allowed=false`, `edge_declaration_allowed=false`.
- Cualquier candidato posterior exige la cadena completa: G2 (PrimaryCI, PBO ≤ 0,50, DSR ≥ 0,95 con N_eff de manifiesto, walk-forward, sensibilidad ±1 paso), G3 (cuatro escenarios de costo), G4 (holdout, una sola apertura). Este diseño no otorga nada de eso.

## 10. Cómo podría refutarse

- Ninguna celda ASIM/BE supera a su REF pareada en expectativa neta base → la forma de la salida no agrega nada: la asimetría de recorrido de Gate 1 no se monetiza con reglas estáticas.
- BE mejora en base pero colapsa en adverso (caída > 0,5× de la expectancy base) → la lógica es frágil al costo, no al mercado.
- Capa 0 muestra que los dos arquetipos no existen como tipos separados (P(regreso | MFE ≥ G) plana en G) → la intuición motivante no tiene soporte de trayectoria y ASIM/BE eran el instrumento equivocado.
- El efecto aparece sólo en H=250 o sólo en SL0=30 → sensibilidad estructural; se reporta, no se elige.
- La tasa de confiscación (§4, Capa 0) supera a la tasa de rescate → el breakeven destruye valor aunque "se vea" bien en el chart.

## 11. Transferencia NQ (condicionada, no activa)

Sólo si Gate 1 NQ se ejecuta y soporta el mecanismo direccional: mismo esqueleto de diseño, con economía NQ estimada propia (prohibido transportar la de GC) y población del Event Store NQ correspondiente. Redactar esa sección como enmienda es trabajo posterior al freeze de Gate 1 NQ.

## 12. Datos faltantes / precondiciones antes de freeze

1. Verificar contra el Event Store `602f8f18…` qué capas de trayectoria ya existen (`mfe_mae`, `first_passage` simétrico) y qué hay que medir de nuevo (primer paso asimétrico; regreso-a-entrada condicional a MFE ≥ G). Reuso antes que recómputo (ATJ-08).
2. Política `KAGGLE_ONLY_EXECUTION_POLICY_V1`: la medición corre en Kaggle con tokens de runtime; el freeze local no toca precios.
3. Respuestas de Nico a DP1–DP5 (§13).
4. Estado del artefacto P2B (§7).

## 13. Puntos de decisión para Nico (bloquean la redacción del spec de freeze)

- **DP1 — Alcance:** ¿GC exploratorio solo, con transferencia NQ condicionada? (recomendado: sí)
- **DP2 — Grilla:** ¿48 primarias (24 ASIM + 24 BE), o recorte estructural a H fija en 250 → 24 primarias, Holm-24? (la segunda reduce presupuesto y aumenta potencia por celda; la primera mapea mejor la escala temporal)
- **DP3 — REF:** ¿la política de reutilización de P2B de §7? (recomendado: sí)
- **DP4 — Mecánica BE:** ¿scrape exactamente a entrada, o a entrada − 1 tick (cubre parte de la fricción)? ¿Sin re-entrada tras scrape (una ejecución por señal, como P2B)? (recomendado: scrape a entrada exacta, sin re-entrada — más limpio de auditar)
- **DP5 — Capa 0:** ¿censo de arquetipos como familia descriptiva declarada dentro de esta campaña (recomendado) o como campaña aparte?

## 14. Lo que este documento NO decide ni autoriza

No ejecuta nada; no abre outcomes; no toca el holdout; no modifica specs congelados (Gate 1, P2A, P2B intactos); no registra la hipótesis en `docs/HIPOTESIS_PENDIENTES.md` (pendiente: entrada HP-005 apuntando a este documento); no es el spec de freeze — el spec JSON se redacta DESPUÉS de las respuestas a DP1–DP5.

## Aporte al referente

La intuición SL/TP + breakeven de Nico queda formalizada como diseño preregistrable: dos arquetipos de trayectoria operacionalizados con su intercambio rescate/confiscación declarado, 48 celdas primarias con presupuesto Holm explícito, economía GC congelada reutilizada, condiciones de refutación escritas y los cinco puntos de decisión que bloquean el freeze. Distancia reducida hacia un edge neto: la pregunta de salida pasa de observación de chart a campaña diseñada **sin gastar ni un outcome**.
