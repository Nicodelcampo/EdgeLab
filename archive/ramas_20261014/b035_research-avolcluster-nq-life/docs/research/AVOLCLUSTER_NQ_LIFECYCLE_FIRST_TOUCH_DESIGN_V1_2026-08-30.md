# AVolClusterPOI NQ — Diseño Gate 3/4: lifecycle + interacción con la zona (V1.2, borrador)

- **Fecha:** 2026-08-30 (ART)
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`
- **Autor:** Notion AI — Auditor Cuantitativo.
- **Rama:** `research/avolcluster-nq-lifecycle-v1-20260830`
- **Base:** `research/bt2a-nq-gate1-v1-20260829` @ `c7a81dec3700eb162fc8e3ce8c00c8a8da44e3a1`
- **Spec draft:** `specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json` (v1.1.0, mismo commit)
- **NO autoriza:** ejecución, lectura de precios fuera de ventanas registradas, outcomes direccionales, P&L, ni holdout.
- **V1.2:** (a) las tres decisiones de freeze quedan **resueltas bajo delegación explícita de Nico** (2026-08-30, "dejo las 3 decisiones a tu criterio") — ver §6; (b) se integra la corrección conceptual de Nico: **la zona es una región, no un punto** — la medición es anatomía completa de la interacción, no clasificación de borde; (c) se adopta como principio estructural la regla de Nico: **la complejidad de cada corrida se resuelve con la información de corridas anteriores más simples (embudo)** — ver §4.

## 1. Por qué esto es lo próximo (y no otra cosa)

La cadena del candidato (regla permanente): **geometría/lifecycle → información → P&L bruto → edge neto**.

Estado verificado de la línea AVol NQ en la config elegida (`tick_120_W5_M20_C4_P950`):

```text
AVOL_NQ_TARGET_FREE_SELECTION  = COMPLETE  (5876 zonas OFF_PRICE, 234 sesiones, fitness 0,9987)
AVOL_NQ_ZONE_STORE_REAL_BUILD  = COMPLETE_5876_ROWS_234_SESSIONS  (Gate 1A, validado 1:1, PASS)
AVOL_NQ_FIRST_TOUCH            = NOT_IMPLEMENTED   ← el cuello real
AVOL_NQ_GATE1_OUTCOMES_OPENED  = false
```

El roadmap congelado del diseño conjunto (§19) ubica acá el **Gate 3 (diseñar/congelar lifecycle + episode collapse)** y **Gate 4 (ejecutar el store)**. Todo lo demás — expansión no direccional (H1), resolución direccional, confluencia BT2A, moderación L2 — cuelga de este reloj: **sin el registro de interacción no hay `t_touch`, y sin `t_touch` ninguna ventana temporal, hazard, supervivencia ni join causal existe**.

Es además la única capa que se puede avanzar **sin pedirle nada a nadie**: Gate 5 (BT2A NQ store) espera tokens del sweep V2; Gate L2 espera su contrato; los outcomes esperan tokens de Nico. Lifecycle sólo necesita lo que ya existe y está validado.

## 2. La corrección de Nico: la zona es una región, no un punto

> «el tema de first touch es complejo porque las zonas no son un punto, son zonas, y el precio interactúa con toda la zona, no con el borde» — Nico, 2026-08-30

Correcto, y cambia el objeto de medición. La versión inicial de este diseño clasificaba el toque por borde (superior/inferior/interior) — una lectura puntuada de un objeto extendido. La V1.1 del spec mide la **anatomía completa de la interacción**:

1. **Entrada:** primer tick dentro de [lower, upper]; borde de entrada derivado del lado de llegada (`LOWER`/`UPPER`), con `AMBIGUOUS` contado aparte cuando no hay tick anterior utilizable (P-28: no hay secuencia de exchange; no se inventa orden).
2. **Travesía sin contacto:** si dos ticks consecutivos abarcan la zona entera sin ningún tick dentro, la zona fue atravesada **sin detener el precio ni un tick** — estado propio (`TRAVERSED_NO_CONTACT`), jamás contado como toque. Es un hecho de primer orden sobre la zona: no frenó nada.
3. **Profundidad interior:** cuánto penetra en el primer episodio, en ticks desde el borde de entrada y en por-mil del ancho — comparable entre zonas de distinto ancho.
4. **Permanencia (dwell):** tiempo y ticks dentro de la zona en el primer episodio. La zona como región habitada, no como cerca tocada.
5. **Resolución:** sale por el lado de entrada (la zona lo devolvió), sale por el opuesto (travesía con contacto), o termina la sesión dentro. La primera travesía **consume** la zona para la familia primaria; reingresos previos se cuentan, secundarios.

Esto responde la complejidad que Nico nombra sin reducirla: la pregunta deja de ser "¿tocó el borde?" y pasa a ser "¿cómo fue la vida del precio dentro de la región?".

## 3. Qué mide (y qué explícitamente no)

**Mide, por cada una de las 5.876 zonas:** si hubo contacto, travesía sin contacto, o expiración; cuándo y a qué edad; por dónde entró; cuánto penetró; cuánto habitó; cómo resolvió; cuántas veces reingresó.

**No mide:** dirección favorable/adversa, MFE/MAE, primer pasaje con barreras, P&L, nada que requiera hipótesis de trade. La capa de contraste (zonas reales vs. matched-geometry / N_RAND / espejo) es Gate 8 del roadmap y NO está en este spec — la lección F2.7–F2.9 (el control sin zona dio casi lo mismo) exige contraste con presupuesto propio, no colado en el store.

**Declaración de acceso:** el lifecycle lee camino de precio posterior a la creación. No es outcome de P&L, pero `FUTURE_PRICE_PATH_ACCESSED` pasa a `true` cuando corre — por eso corre con token propio, post-freeze, en Kaggle, dentro de las ventanas CME registradas (máx. sesión 20260630; holdout intacto por construcción).

## 4. El embudo (principio de Nico, hecho estructura)

> «la complejidad de las corridas sea resuelta con la info que proveen corridas anteriores más simples» — Nico, 2026-08-30

Adoptado como propiedad del diseño, no como deseo. Este store es la corrida simple; sus salidas descriptivas (conteos y distribuciones, publicadas como manifiesto de cobertura — integridad, no inferencia) **congelan grados de libertad de las corridas complejas posteriores**, que las citan por hash y nunca las re-derivan distinto:

| Cantidad que produce este store | Libertad de diseño que congela aguas abajo |
|---|---|
| Tasa ENTERED / TRAVERSED_NO_CONTACT / EXPIRED | Si la familia "zona como barrera" vive o muere **barato**, antes de gastar presupuesto de Gate 8 |
| Distribución de profundidad interior (cuantiles) | Los thresholds de rechazo/aceptación de la capa direccional L4 se **bindean a esos cuantiles** en vez de elegirse a mano |
| Distribución de dwell | Recalibración **escrita** de las ventanas de confluencia BT2A (la grilla ±5s/30s/120s del diseño conjunto §7.1, hoy candidata) |
| Tasas de entry_edge y de travesía por gap | Si Gate 8 necesita reglas de gap/ambigüedad, y con qué presupuesto de exclusión |
| Hazard de contacto por edad de zona | La elección de horizontes H de las familias de outcomes posteriores |
| Tasa de EPISODE_COLLAPSED por sesión | Si la regla de colapso es asunto menor o exige análisis de sensibilidad propio |

El límite honesto, declarado: estas cantidades son **insumos de diseño**, no evidencia de efecto. Los contrastes con nulos y presupuesto viven en Gate 8.

## 5. Cómo podría refutarse (el store y la capa que habilita)

- Si la contabilidad 5.876 no cierra contra el store de creación → el runner midió otra población; no se publica nada.
- Si la tasa de interacción de zonas reales es indistinguible de geometrías matched (Gate 8, futuro) → "la zona atrae/interactúa" muere para este objeto, con alcance preciso (config primaria, NQ, pre-holdout).
- Si el dwell y la profundidad son idénticos a los de intervalos de precio aleatorios matched por ancho y distancia → la región no es especial; la anatomía es la de cualquier corredor de precio.
- Si `TRAVERSED_NO_CONTACT` domina la población → las zonas no detienen el precio ni un tick; cualquier narrativa de "liquidez institucional en la zona" muere gratis, antes de gastar un outcome.

## 6. Decisiones de freeze — RESUELTAS bajo delegación de Nico (2026-08-30)

Nico delegó las tres decisiones abiertas ("dejo las 3 decisiones a tu criterio"). Se asientan con sus razones, patrón P-47 (decisión delegada → razones escritas → no se reabre sin causa nueva):

- **D-L1 — Expiración: fin de sesión duro como censura (`EXPIRED_SESSION_END`).** Razones: (a) consistencia con la frontera dura CME de Gate 1 BT2A y con el store de creación, que es sesión-scoped; (b) la sesión es la unidad de cluster de toda la inferencia del proyecto — una zona multi-sesión mezclaría gap de mantenimiento e identidad de sesión; (c) la alternativa (zonas overnight) cambia el objeto: sería otra campaña, con otro store.
- **D-L2 — Alcance de Gate 4: sólo el store (medición pura).** Razones: (a) es el patrón que funcionó en el store de creación (build → finalize → validate, cero inferencia, auditoría limpia); (b) mezclar lectura descriptiva en la misma corrida acopla medición con interpretación y viola ATJ-14 (código primero, resultados después); (c) la lectura descriptiva posterior se hace **consultando el artefacto inmutable ya publicado** — gratis, sin re-correr ni abrir nada nuevo. La validación publica conteos de integridad (cuántas por estado), nunca estadísticos interpretativos.
- **D-L3 — Colapso por solapamiento: confirmado `FIRST_ELIGIBLE_EVENT_WINS`.** Razones: (a) ya estaba congelado en el `episode_policy` del spec conjunto — cambiarlo exigiría causa, no preferencia; (b) es determinista, causal (menor `availability_ts_utc_ns` gana, sin mirar la interacción) y auditable; (c) las alternativas ("la más ancha", "la más cercana al precio al tocar") condicionan el ancla a geometría o al outcome — la segunda es selección por resultado con otro nombre.

## 7. Lo que este documento NO decide ni autoriza

No ejecuta nada; no abre outcomes ni camino futuro; no toca el holdout; no modifica specs congelados (el store de creación queda intacto y se consume por hash); no implementa el runner (va con tests sintéticos de verdad conocida antes del freeze, incluyendo jugadas construidas a mano para depth y dwell exactos); no responde si las zonas "funcionan" — eso es Gate 8 en adelante.

## Aporte al referente

AVolClusterPOI NQ tiene el eslabón faltante escrito en su forma correcta: la zona como región habitada (entrada, profundidad, permanencia, resolución, travesía sin contacto) y no como punto tocado; las tres decisiones de freeze resueltas bajo delegación con razones asentadas; y el principio de embudo de Nico convertido en tabla explícita de qué congela esta corrida simple para las complejas que siguen. Sin gastar ni un outcome ni tocar el holdout.
