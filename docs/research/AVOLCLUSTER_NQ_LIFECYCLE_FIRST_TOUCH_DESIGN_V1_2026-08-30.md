# AVolClusterPOI NQ — Diseño Gate 3/4: lifecycle + first-touch Event Store (V1, borrador)

- **Fecha:** 2026-08-30 (ART)
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`
- **Autor:** Notion AI — Auditor Cuantitativo, a pedido de Nico ("¿en qué podemos avanzar respecto de AVolClusterPOI? Quiero medirlo bien, en NQ, en la config elegida").
- **Rama:** `research/avolcluster-nq-lifecycle-v1-20260830`
- **Base:** `research/bt2a-nq-gate1-v1-20260829` @ `c7a81dec3700eb162fc8e3ce8c00c8a8da44e3a1`
- **Spec draft:** `specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json` (mismo commit)
- **NO autoriza:** ejecución, lectura de precios fuera de ventanas registradas, outcomes direccionales, P&L, ni holdout.

## 1. Por qué esto es lo próximo (y no otra cosa)

La cadena del candidato (regla permanente): **geometría/lifecycle → información → P&L bruto → edge neto**.

Estado verificado de la línea AVol NQ en la config elegida (`tick_120_W5_M20_C4_P950`):

```text
AVOL_NQ_TARGET_FREE_SELECTION  = COMPLETE  (5876 zonas OFF_PRICE, 234 sesiones, fitness 0,9987)
AVOL_NQ_ZONE_STORE_REAL_BUILD  = COMPLETE_5876_ROWS_234_SESSIONS  (Gate 1A, validado 1:1, PASS)
AVOL_NQ_FIRST_TOUCH            = NOT_IMPLEMENTED   ← el cuello real
AVOL_NQ_GATE1_OUTCOMES_OPENED  = false
```

El roadmap congelado del diseño conjunto (§19) pone acá el **Gate 3 (diseñar/congelar lifecycle + episode collapse)** y **Gate 4 (ejecutar el first-touch store)**. Todo lo demás que suena interesante — expansión no direccional (H1), resolución direccional, confluencia con BT2A, moderación L2 — cuelga de este reloj: **sin first touch no hay `t_touch`, y sin `t_touch` ninguna ventana temporal, hazard, supervivencia ni join causal existe**. Este documento escribe ese eslabón.

Es además la única capa que se puede avanzar **sin pedirle nada a nadie**: Gate 5 (BT2A NQ store) espera los tokens del sweep V2, Gate L2 espera su contrato, y los outcomes esperan tokens de Nico. Lifecycle sólo necesita lo que ya existe y está validado: el store de creación + los cinco parquets hash-bindeados.

## 2. Qué mide (y qué explícitamente no)

**Mide, por cada una de las 5.876 zonas:** si fue tocada; cuándo (ns, tick, barra 120t); a qué edad de la zona; por qué borde (inferior / superior / interior / penetración completa en el contacto / ambiguo); penetración máxima posterior; expiración sin toque al fin de sesión; reingresos (secundario declarado).

**No mide:** dirección favorable/adversa, MFE/MAE, primer pasaje con barreras, P&L, nada que requiera una hipótesis de trade. `approach_side` es geometría descriptiva del contacto, no una dirección operable. La capa de contraste (zonas reales vs. controles matched-geometry / N_RAND / espejo) es Gate 8 del roadmap y NO está en este spec — la lección F2.7–F2.9 (el control sin zona dio casi lo mismo) exige que el contraste se diseñe con su propio presupuesto, no colado dentro del store.

**Declaración de acceso:** el lifecycle lee camino de precio posterior a la creación. No es outcome de P&L, pero `FUTURE_PRICE_PATH_ACCESSED` pasa a `true` cuando corre — por eso corre con token propio, post-freeze, en Kaggle, dentro de las ventanas CME registradas (máx. sesión 20260630, holdout intacto por construcción).

## 3. Reglas causales y de colapso (el corazón del diseño)

1. **La barra de creación es inelegible para el toque.** El reloj arranca en `availability_ts_utc_ns`, no en `created_ts_utc_ns` (ATJ-03: creación no implica utilizabilidad).
2. **Empates de timestamp:** si un mismo tick toca ambos bordes, se clasifica `AMBIGUOUS_EDGE` y se cuenta aparte. No se inventa orden intrabar (disciplina HP-003; limitación P-28: `sequence` no es secuencia del exchange).
3. **Frontera de sesión dura:** ninguna zona vive entre sesiones; fin de sesión sin toque = `EXPIRED_SESSION_END` (censura por derecha declarada, no fracaso de la zona).
4. **Episode collapse:** zonas solapadas en precio dentro de la misma sesión → ancla `FIRST_ELIGIBLE_EVENT_WINS`; la segunda queda `EPISODE_COLLAPSED_WITH=<event_id>`, conservada pero fuera del análisis primario. Regla congelada **antes** de cualquier outcome (regla del diseño conjunto §7.4).
5. **Contabilidad exacta:** TOUCHED + EXPIRED + CENSORED = 5.876, en total y por sesión, reconciliado contra el store de creación por `identity_sha256`. Un gate de finalización lo exige; una zona que no cierra la cuenta es `FAIL`, no una nota al pie.

## 4. Inferencia posterior (declarada ahora, medida nunca acá)

El store habilita, para gates posteriores: probabilidad acumulada de toque y supervivencia sin toque (con censura por derecha), hazard por edad de zona, y los contrastes de Gate 8. Dos disciplinas ya escritas que aplican cuando eso llegue:

- **P-53:** el N efectivo son las **233 sesiones con zonas**, no los 5.876 eventos. Todo contraste publica su MDE con sesiones efectivas antes de leer el punto — con 233 sesiones el MDE será grande y eso se sabe antes de mirar.
- **P-55:** si un contraste da nulo, se publica la distribución completa y la dispersión, no sólo la media — un nulo con dispersión excedente es heterogeneidad no modelada y se persigue; un nulo con dispersión normal es nulo fuerte y se cierra.

## 5. Cómo podría refutarse (el store y la capa que habilita)

- Si la contabilidad 5.876 no cierra contra el store de creación → el runner está midiendo otra población; no se publica nada.
- Si la tasa de toque de zonas reales es indistinguible de la de geometrías matched (Gate 8, futuro) → "la zona atrae precio" muere para este objeto, con alcance preciso (config primaria, NQ, pre-holdout).
- Si los toques se concentran en los primeros ticks post-disponibilidad de forma idéntica a un control de timestamps aleatorios → el reloj de toque no informa nada sobre la zona; es microestructura de llegada genérica.

## 6. Puntos de decisión para Nico (bloquean el freeze)

- **DP-L1 — Expiración:** ¿fin de sesión duro como censura (recomendado; consistente con Gate 1 BT2A) o se permite supervivencia overnight entre sesiones del mismo contrato? (la segunda cambia el objeto: zonas multi-sesión).
- **DP-L2 — Alcance del Gate 4:** ¿sólo el store (recomendado — medición pura, validación 1:1, cero inferencia) o store + capa descriptiva de supervivencia en la misma corrida? (la segunda ahorra una corrida pero mezcla medición con lectura; el proyecto ya eligió separar esto en el store de creación).
- **DP-L3 — Colapso por solapamiento:** confirmar `FIRST_ELIGIBLE_EVENT_WINS` del diseño conjunto, o regla alternativa escrita antes del freeze (p.ej. zona más ancha gana, o más cercana al precio). No hay default libre: sin regla congelada no hay freeze.

## 7. Lo que este documento NO decide ni autoriza

No ejecuta nada; no abre outcomes ni camino futuro; no toca el holdout; no modifica specs congelados (el store de creación queda intacto y se consume por hash); no implementa el runner (va con tests sintéticos antes del freeze, regla de gates del proyecto); no responde si las zonas "funcionan" — eso es Gate 8 en adelante.

## Aporte al referente

AVolClusterPOI NQ deja de tener el cuello difuso: queda escrito el eslabón exacto que falta (lifecycle + first touch sobre las 5.876 zonas ya validadas), con reglas causales, colapso de episodios, contabilidad exacta y tokens separados — preparación completa sin gastar ni un outcome ni tocar el holdout.
