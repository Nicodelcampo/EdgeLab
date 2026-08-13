# ZAMR-1 — handoff reproducible (2026-08-12)

Documento canónico para retomar EdgeLab sin depender del chat. Autoridad: specs/contratos ejecutables > código/tests/commits/artefactos > Notion > PDFs > chat > supuestos.

## Rama y estados

- Rama: `research/zamr1-zone-atlas`; base F2.7 `1b8e168`; HEAD previo `a7121bf`.
- Corte exclusivo: `2026-06-30T22:00:00Z` (`1782856800000000000` ns).
- Estados: `F2.7_FORMAL_RUN_COMPLETE_REFLECTION_POSITIVE`, `ZAMR1_Z0_PASS_WITH_HARDENING`, `ZAMR1_Z1_INPUT_AUDIT_PASS`, `ZAMR1_Z1_SESSION_PLAN_READY_22_SESSIONS`.
- Prohibido: outcomes, retornos futuros, P&L, selección económica y lectura del holdout.

F2.7: `delta_reflection=0.0481526536`, IC95 `[0.0306759691,0.0656293381]`, 201 sesiones. Evidencia geométrica, no alpha. El touch binario está saturado; sucesores: primer pasaje, tiempo a revisita, hazard y competing risks.

Z0 Kaggle sintético: `passed=true`, 8/8 hashes, 13/13 checks, 20 sesiones, 120 eventos/zonas, seis frames, CPU/Internet off, sin outcomes/P&L/holdout. ZIP `98b7aec6180e345e4fc0ed584e2ad9962678f65a414e2467afcc7f21ab7cbe87`.

## Datos y muestra Z1

- 09-26: SHA `654e006e...`, 2,278,916 filas, 37 sesiones, 17 pre-holdout; export extendido no canónico.
- 06-26: SHA `fd2e358d...`, 5,550,120 filas, 71 sesiones, 0 post-holdout, 0 timestamps nulos; mismo schema F2; export extendido no canónico.
- No sustituir los hashes canónicos F2.7 (`6ffcdf...`/`124b375...`) con estas identidades.

Solapamiento 8–15 junio: 06-26 domina 8–11; 09-26 domina desde 12 (el 12: 10,862 vs 71,784 ticks). Roll: 06-26 hasta 11 inclusive, 09-26 desde 12. Muestra: 1–30 junio, 22 sesiones, 1,651,076 ticks, un contrato por sesión. Plan ejecutable: `specs/zamr1_z1_pilot_plan_2026-08-12.json`.

## Builder y gates

El siguiente commit agrega `edgelab/research/zamr1/z1_builder.py`: hashes/árbol limpio, 20–30 sesiones, defaults, seis frames, firewall físico, orden total, tick bars con reset, P1A, `events_long`/`zones_long`, validación estructural, manifests y recursos. Paridad debe quedar `NOT_ESTABLISHED`, no inventar PASS NT8. Licencia `NO_UPLOAD`; el override del usuario es campo separado y no permiso contractual.

Antes de Z2: suite PASS; corrida real y contrato PASS; determinismo; cero filas cutoff/columnas prohibidas/duplicados; P1A en 12 unidades; margen de recursos >=2x; resolver o excluir P-02 `max_age`; P-01 fail-closed; paridad independiente.

Secuencia congelada: Z1 piloto; Z2 17 resoluciones/defaults/201 sesiones y mesetas 3–5; Z3 familias BigTrap2 separadas; Z4 pares luego tríos; Z5 aVol independiente; Z6 interacción sólo si ambos sobreviven y gana OOF 4/5. Transferencia 6E→GC→ES→NQ.

## Instrucción mínima para otro LLM

> Trabajá sólo en `research/zamr1-zone-atlas`. Leé este handoff, el contrato estructural, el plan Z1, el builder y tests. No abras outcomes/P&L/holdout ni cambies hashes, roll, sesiones, frames o defaults para hacer pasar la corrida. Ejecutá tests y builder; fallá cerrado y documentá causa raíz. No autorices Z2 sin todos los gates.
