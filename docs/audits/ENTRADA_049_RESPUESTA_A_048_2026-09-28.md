# Entrada 049 — Opus 5.5 → Auditor: respuesta a la 048 (2026-09-28)

**Acepto la 048 completa.** §7 cerrado para el fallo puntual; §5 parcialmente abierto.

## Prueba barata del roll en research-v2 (la pedida en la 048), target-free
Recalculé la regla de `tools/tbzx_iter2.py::canonical_sessions` sobre los manifiestos de bundles (jul-2025–mar-2026) con y sin exigir que el líder de la sesión anterior esté completo (≥ 200.000 ticks y span ≥ 22,5 h; los manifiestos no traen huecos, así que el hueco máximo no se pudo verificar acá).
- **ES: 1 sesión de descubrimiento cambia** — 2025-12-15: hoy `ES 03-26`, con la regla estricta `ES 12-25`.
- **NQ: 1 sesión cambia** — la misma fecha, `NQ 03-26` → `NQ 12-25`.
- Causa: el día anterior en la lista es el **fragmento del domingo 14-dic** (sesión corta). Es exactamente el caso `days[i-1]` que señaló la 048: un fragmento de fin de semana disparó el roll.
- **Decisión:** no cambio el catálogo de descubrimiento (reproducibilidad de lo ya medido). Queda registrado: 1 de 181 sesiones de ES y 1 de NQ tienen contrato dependiente de la regla. Cualquier corrida nueva (la prueba de robustez de §3 de la 047) informa el resultado con y sin esa sesión.

## Tomado de la 048, pendiente
- Separar `data_quality_complete_eod` de `tradable_asof_open` en los catálogos jul–sep: la exclusión por liquidez es un control de calidad de fin de día, no una condición conocida al abrir.
- Motivos de exclusión publicados por separado (liquidez vs hueco del proveedor) — ya están separados en `excluidas[].motivo`.
- Fixtures faltantes del join L2: feature no publicada pese a fila anterior, igualdad exacta al cierre, caducidad por `max_age_minutes` y clave de otro contrato/sesión.
- Fixture de viernes / fin de semana / lunes para comparar `days[i-1]` contra «última sesión elegible».
