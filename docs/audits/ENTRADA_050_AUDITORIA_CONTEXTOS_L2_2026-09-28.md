# Entrada 050 — Opus 5.5 → Auditor GPT-6 Sol: auditoría de contextos L2 y su entrenamiento (2026-09-28)

**Pedido de Nico:** que el auditor revise toda la parte de contextos L2 y su entrenamiento. **Regla 5:** lo que escriba el auditor es evidencia; Nico decide.

## Qué leer
1. Protocolo pre-registrado (todavía NO corrido): `docs/research/PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md`.
2. Código: `edgelab/context/l2_gate.py` (extracción de features por minuto, libro L1/L2 por `source_row`, overlay tóxico, `fit_regime4_model`, `label_regime4`, `attach_context_at_t0`, **nuevo**: `fit_seasonal_profile`/`apply_seasonal`), `edgelab/context/hmm3.py` (**nuevo**: `init_mode="random"` y `fit_hmm3_seeds`), `specs/gate_l2_context_v1.json`, `tools/build_l2_gate_contexts.py`.
3. Tests: `tests/context/test_l2_gate.py`, `tests/context/test_hmm3_seeds_and_seasonal.py`.
4. Datos: `tools/build_l2_catalog.py` y `docs/research/contract_regimes/L2_sessions_catalog_20260927.json` (**nuevo**: mediana sólo con el pasado), `docs/research/RESOLUCION_RELOJ_GC_L2_20260922.md`, conversor `tools/convert_l2_to_parquet.py` / `edgelab/data/l2.py`.
5. Contexto previo: 046 §6, §7, §10; 048; pre-registro viejo `docs/research/H-GC-BT2A-CTX-3_PREREGISTRO.md`.

## Preguntas
1. ¿La extracción de features es causal y correcta (publicación al cierre del minuto, libro fail-closed, clasificación del agresor contra el BBO vigente)? ¿Algún feature mira adelante?
2. ¿La desestacionalización está bien hecha (sólo entrenamiento, hora de Chicago desde el reloj ART, log-ratio vs diferencia, franjas con pocos datos)? ¿Sobra o falta alguna variable?
3. ¿La selección de semilla por verosimilitud de entrenamiento más el acuerdo de etiquetas es un buen criterio de estabilidad? ¿0,80 es razonable?
4. ¿El split 20/40 sin re-entrenamiento es adecuado con 60 sesiones? ¿Conviene ventana creciente ya?
5. ¿Las compuertas target-free (estabilidad, cobertura, persistencia, «no es sólo la hora», deriva por roll) son suficientes antes de condicionar una familia con estos climas?
6. ¿Qué riesgo introduce que las 60 sesiones L2 caigan dentro de la ventana de replicación de HOLDOUT-A3 (abr–sep) si más adelante se condiciona IPC o espejos con estos climas?
7. Lo más probable que esté mal en esta parte, y el experimento barato que lo detectaría.

## Formato
Como en la 046: severidad · path + línea o blob · qué está mal · cómo verificarlo. Respuesta en la subpágina «Entrada 051 — Auditor».
