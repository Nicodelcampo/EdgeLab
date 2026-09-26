# Enmienda HOLDOUT-A1 — holdout a futuro desde la sesión del 1-oct-2026 (2026-09-26)

**Decisión de Nico (chat, 26/09):** «Escribila» sobre la propuesta de Claude, y «canonizá los datos nuevos». Esta enmienda cambia la semántica de validación, así que queda **firmada por Nico** con esas dos instrucciones.

## Qué cambia
| | Antes | Ahora |
|---|---|---|
| Exploración | ≤ 2026-03-31 | ≤ 2026-03-31 **y** sesiones CME del 1-jul al 30-sep-2026 |
| Reserva | abr–jun 2026 (1–3 configuraciones, una vez) | sin cambios |
| Holdout | 2026-07-01 → 2026-12-31 | **desde la sesión CME del 1-oct-2026** (apertura 2026-09-30 17:00 CT) → 2026-12-31, datos a futuro |

## Por qué
- La potencia es el límite de varias familias (IPC macro: 28/28 SIN_POTENCIA con 181 sesiones). La fuente (NT8, Provider31) **no tiene historia anterior** a la ya descargada (confirmado por Nico), así que la única muestra nueva es jul–sep.
- El holdout estaba **intacto**: nada de jul–sep se usó para diseñar o elegir antes de esta enmienda. Por eso el cambio se puede hacer limpio hoy.
- Un holdout a futuro es el más limpio posible: no existía cuando se diseñó ningún candidato.

## Costo
- El holdout se acumula de a poco (oct–dic): confirmar un candidato requiere esperar sesiones a futuro.
- jul–sep deja de ser fuera de muestra para todo lo diseñado desde ahora.

## Datos
- Canonizados con `tools/build_es_ext_2026q3.py` en `E:\EdgeLab\data\nt8_ext_2026q3\ES_parquet\` (esquema canonical_tick_v1, igual que research-v2, que **no se toca**). Ventana `[2026-06-30 17:00 CT, 2026-09-30 17:00 CT)`.
- Catálogo: `docs/research/contract_regimes/ES_ext_2026q3_sessions_catalog.json` — **52 sesiones completas**, 10 excluidas: 3-jul y 7-sep (feriados), 14, 20, 21, 26 y 28-ago, 16, 17 y 18-sep (huecos del proveedor: `NO_DATA` o pocos ticks en el AddOn). Roll a ES 12-26 el 15-sep por la regla canónica.
- Corrección durante la canonización: un día sin datos del contrato vigente (21-ago) hacía «rollear» al 12-26 un mes antes (671 ticks > 0). Ahora el líder tiene que tener una sesión completa el día anterior.
- Por instrumento: esto cubre **sólo ES**. NQ, YM, MYM y el resto siguen con el holdout viejo hasta que se descarguen y canonicen.

## Publicación
No se sube a Kaggle: los ticks de CME vía el proveedor de NT8 siguen bajo `ABSTAIN_LICENSE` (P-18), y la V1 del dataset ya tiene ese problema abierto.
