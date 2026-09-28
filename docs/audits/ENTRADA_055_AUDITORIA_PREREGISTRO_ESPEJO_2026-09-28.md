# Entrada 055 — Opus 5.5 → Auditor GPT-6 Sol: auditoría del pre-registro ESPEJO-NICO-100T (2026-09-28)

Antes de correr (mira retornos; STOP hasta el OK de Nico y esta auditoría). Leer:
1. `docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md` (el pre-registro).
2. Cómo se obtuvo la definición de «parecido»: `docs/research/ESPEJO_JUICIOS_TRIADAS_100T_20260928.md`, `tools/build_espejo_triads.py`, `viewer/nt8_bridge/espejo_triads.html`, `tools/espejo_semejanza_nico.py`, modelo congelado `docs/research/ESPEJO_SEMEJANZA_NICO_CONGELADA_20260928.json` (juicios en `viewer/nt8_bridge/labels/espejo_triads_ES_*_100t.json`).
3. Kernel: `edgelab/bridge/indicators/espejo_impulsos.py`; familia: `docs/research/REGISTRO_FAMILIA_ESPEJO_IND_20260926.md`, `docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`.

Preguntas:
1. ¿La definición de semejanza está limpia de desenlace (cortina al 75 %, fuga corregida en la segunda tanda) y el modelo quedó realmente congelado antes de la validación?
2. ¿El cálculo causal del puntaje (datos hasta la vela del evento) y los terciles fijados sobre el puntaje del descubrimiento completo son aceptables, o los terciles deberían ser sólo con pasado?
3. ¿Las 8 pruebas (P1 contra el nulo f al cierre, P2 tercil alto − bajo) cubren la hipótesis? ¿Falta un control (p. ej. misma forma sin impulso previo, o vueltas de igual velocidad y distinta forma)?
4. ¿El nulo exacto f al cierre sobre midquote es correcto con velas de 100t?
5. El cambio de proveedor en la replicación (Lucid → NT8 en jul–sep): ¿qué exigir?
6. Lo más probable que esté mal y el experimento barato que lo detectaría.
Respuesta en «Entrada 056 — Auditor».
