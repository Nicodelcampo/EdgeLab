# Revisión ciega de especificaciones antes de correr una prueba (2026-09-24)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Para qué

Que Nico **vea** lo que se va a probar antes de probarlo: eventos, entradas, stop, target, break-even y tiempo máximo, recorriendo la grilla con una barra deslizante. Así se atrapan errores de construcción antes de gastar datos y presupuesto de pruebas. Casos que lo motivaron:
- HP-008: "no se midió lo que quería medir".
- 2026-09-23: F3/F4 tomaban la barra de las 18:00 ET de la noche previa como apertura.

Tiene antecedentes en otras disciplinas: la "revisión ciega de datos" de los ensayos clínicos (ICH E9), "mirar los datos antes de entrenar" en ML y la especificación por ejemplos en software.

## La regla central: ciega de verdad

- La vista previa muestra **todo lo que define la prueba y nada de lo que la resuelve**.
- `tools/build_spec_preview.py` **no escribe ningún precio posterior a la entrada**: la ceguera es de datos, no de CSS. Lo verifica `tests/data/test_spec_preview.py`, con un fixture que tiene una subida enorme después de la entrada.
- Como es target-free, puede usar días del holdout solo como geometría (NORTH_STAR: el holdout se permite para el visor).
- Nunca se muestran resultados, ni por operación ni agregados. Lo que sí se muestra, derivado solo de la grilla y los costos:
  - el **acierto necesario** para cubrir el costo, (stop + costo) / (stop + target);
  - la fracción de eventos que se perderían por la regla de una posición a la vez;
  - alertas geométricas: target menor a 1,5 × costo, o stop menor al rango típico de 60 s.

## Flujo

1. Se escribe la spec en `docs/specs/SPEC_*.json`. Tiene que incluir hipótesis, justificación económica, cómo se refuta, población con las alternativas enumeradas, entrada, grilla, salidas, costos y muestra.
2. `python tools/build_spec_preview.py --spec docs/specs/SPEC_X.json` genera `viewer/nt8_bridge/bundles/spec_<id>.json`.
3. Nico abre `spec_review.html?spec=<id>` (también desde el botón **Revisión de spec** del visor) y la recorre:
   - ↑/↓ cambia de ejemplo;
   - ←/→ o la barra cambia de combinación;
   - los chips saltan por dimensión.
4. Si es lo que quiere probar, responde **"confirmo <spec_id> <hash12>"**. Se registra con `DurableHippocampus.record_spec_confirmation(..., confirmed_by="human:Nico")`.
5. **El Brain no acepta una campaña sin una spec confirmada:** `record_campaign(..., spec_sha256=...)` levanta `CampaignBudgetError` si falta. Las campañas anteriores a esta regla siguen reproduciéndose en el replay.

## Primer caso: absorción L2 en 6E

- **Spec:** `docs/specs/SPEC_6E_L2_ABSORPTION_20260924.json`.
- **Muestra:** 12 sesiones, 814 eventos (~68 por día) y 24 ejemplos.
- **Qué muestra el panel, sin resultados:**
  - con stop 2t y target 2t haría falta acertar el **94 %**, y el target no llega a 1,5 × costo;
  - con stop 6t, target 8t, BE +2t y 5 min hace falta el **58 %**, pero se pierde el **43 %** de los eventos por superposición.
- **Límite:** en el 6E hay solo 4–5 sesiones L2 pre-holdout. La herramienta sirve; el test real necesita más historia.

## Cambio de base: detector de absorción causal

`AbsorptionTracker` pasa a ser **causal por defecto**. El umbral p99 sale solo de ventanas ya cerradas: se recalcula cada 30 ventanas y exige 200 celdas de historia. El modo viejo (percentil de la sesión completa, que usaba información futura) queda como `causal=False`, solo para comparar.

**Consecuencia:** el nulo de absorción de la Fase 0 (§6: 1,41×) y los bundles L2 ya generados usaron el umbral viejo. El nulo tiene que re-medirse con el causal antes de citarlo como evidencia de entradas.
