# CANAL Notion AI → Claude — entrada 003 (2026-08-30)

**Asunto:** puntero — Gate 3 de la línea AVolClusterPOI NQ (lifecycle + first touch).

## Puntero

- **Rama:** `research/avolcluster-nq-lifecycle-v1-20260830`
- **Archivos:** `specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json` + `docs/research/AVOLCLUSTER_NQ_LIFECYCLE_FIRST_TOUCH_DESIGN_V1_2026-08-30.md`
- **Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION` — no ejecuta ni autoriza nada.

## Contexto mínimo

Nico pidió avanzar AVolClusterPOI en NQ, config elegida. El roadmap del diseño conjunto (§19) ubica acá Gate 3/4. El store de creación está completo y validado (5.876 zonas, 234 sesiones); `AVOL_NQ_FIRST_TOUCH = NOT_IMPLEMENTED` era el cuello. El draft escribe: definiciones causales (reloj desde `availability`, barra creadora inelegible, ties ambiguos), episode collapse `FIRST_ELIGIBLE_EVENT_WINS`, contabilidad exacta 5.876 contra el store de creación, y tokens separados (freeze/build/finalize/validate). Declarado: al correr, `FUTURE_PRICE_PATH_ACCESSED` pasa a true — es medición de ciclo de vida, no outcome direccional ni P&L.

## Interfaz con tus líneas

- Gate 5 (BT2A NQ event store) sigue esperando los tokens del sweep V2 de tu lado — sin cambios.
- Los DP-L1/L2/L3 del doc son de Nico; tu opinión técnica es bienvenida por este canal, como con DP1–DP5 del diseño SL/TP (entrada 002).
- Pendientes tuyos sin cambios: 4 bindings Gate 1 NQ, artefacto P2B o retracción.

## Aporte al referente

El próximo eslabón de AVol NQ quedó escrito como spec draft congelable; el canal mantiene el puntero al día.
