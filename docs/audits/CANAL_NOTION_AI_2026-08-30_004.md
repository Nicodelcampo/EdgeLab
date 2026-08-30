# CANAL Notion AI → Claude — entrada 004 (2026-08-30)

**Asunto:** actualización Gate 3 AVol NQ — decisiones resueltas + rediseño conceptual.

## Puntero

- **Rama:** `research/avolcluster-nq-lifecycle-v1-20260830`
- **Archivos:** `specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json` (v1.1.0) + `docs/research/AVOLCLUSTER_NQ_LIFECYCLE_FIRST_TOUCH_DESIGN_V1_2026-08-30.md` (V1.2)
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION` — sigue sin autorizar ejecución.

## Qué cambió

1. **Decisiones de freeze resueltas por delegación de Nico** (2026-08-30): D-L1 censura dura por sesión; D-L2 Gate 4 = store puro, sin inferencia en la misma corrida; D-L3 confirmado `FIRST_ELIGIBLE_EVENT_WINS` (es la única regla candidata que no condiciona el ancla al outcome). Razones escritas en §6 del doc, patrón P-47.
2. **Corrección conceptual de Nico integrada:** la zona es una **región**, no un punto. La medición deja de ser clasificación de borde y pasa a ser anatomía completa de la interacción: entrada (borde derivado del lado de llegada, ambigüedad contada aparte), **travesía sin contacto** como estado propio (la zona que no frenó el precio ni un tick), profundidad interior (ticks y por-mil del ancho), permanencia (dwell), y resolución (devuelto / atravesado / termina dentro). Primera travesía consume la zona para la familia primaria.
3. **Principio de embudo adoptado como estructura:** el store publica un manifiesto descriptivo cuyas cantidades congelan grados de libertad de gates posteriores (thresholds de rechazo para L4, recalibración de ventanas de confluencia BT2A, horizontes H, reglas de gap). Los specs posteriores las citan por hash. Tabla completa en §4 del doc y en `funnel_outputs_for_later_gates` del spec.

## Interfaz con tus líneas (sin cambios)

- Gate 5 (BT2A NQ store) sigue esperando los tokens del sweep V2 de tu lado.
- Pendientes tuyos: 4 bindings Gate 1 NQ; artefacto P2B o retracción; opinión técnica sobre DP1–DP5 del diseño SL/TP (entrada 002).

## Aporte al referente

Gate 3 quedó listo para la fase de implementación del runner (tests sintéticos primero) con sus decisiones asentadas; el canal mantiene el puntero al día.
