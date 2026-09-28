# Entrada 053 — Opus 5.5 → Auditor: pasos de la 052 cerrados + dos proveedores de datos (2026-09-28)

## Pasos de la 052 (todos target-free; commit de referencia en la página de Notion)
1. **Runner NQ** `tools/build_l2_contexts_nq.py` con preflight que aborta: 60 sesiones, contrato por sesión, archivos y tamaños contra manifiesto, `subsecond_unit == 100ns_ticks`, plan congelado (hash `f88ccbfc…`). Preflight con datos reales: **0 errores**.
2. **Extractor** (`l2_gate.extract_minute_features`): inversión de reloj intercalada, BBO > 60 s y libro invalidado → minuto no elegible; trades sin BBO fresca (≤ 5 s) por tick rule y contados; ventanas por tiempo transcurrido. Tests `tests/context/test_l2_extractor_causal.py`.
3. **Overlay toxic desestacionalizado** en `fit_regime4_model`/`label_regime4`.
4–5. **Reporte** `context_gate_report` con PASS/STOP automático sólo sobre evaluación (cobertura, persistencia, concentración horaria con STOP por estado, clasificador de sólo-hora, deriva por roll, estabilidad por semilla y estado). Tests `tests/context/test_context_gate_report.py`.
- Adenda de A3 (Nico): preguntas condicionadas por climas L2 → abr–sep es desarrollo; confirmación sólo oct+.

## Hecho nuevo (Nico): dos proveedores
- **Ticks canónicos jul-2025 → jun-2026 (research-v2): cuenta Lucid.** **Ticks jul–sep 2026 (extensión A1) y todo el L2: NinjaTrader (Provider31).**
- Consecuencias que veo:
  1. En ES/NQ el cambio de proveedor **coincide con la frontera abr–jun / jul–sep** dentro de la replicación: una diferencia de feed (agregación de trades, timestamps, bid/ask) puede confundirse con un efecto.
  2. Un evento detectado en ticks de Lucid **no puede unirse** a contextos L2 de NT8 por timestamp (misma regla que prohíbe L2 ↔ `.Last.txt`): para preguntas condicionadas por clima, los eventos se detectan sobre el **L1 del mismo stream** L2.
  3. Nico puede bajar ticks de NT8 desde ~ago/sep-2025: da un **solapamiento** Lucid ↔ NT8 de ~10 meses para una prueba de paridad de proveedor target-free (conteo de ticks por sesión, volumen, precios, bid/ask, agresor, velas de 25t idénticas o no).
- Pregunta al auditor: ¿qué criterio de paridad exigirías antes de mezclar proveedores dentro de una familia, y qué hacer con la extensión jul–sep ya canonizada?
