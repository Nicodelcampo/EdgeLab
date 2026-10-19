# BigTrap2Absorption — Provenance y Semántica Temporal M5/tick_25

**Fecha:** `2026-09-20T22:20 UTC-3`
**Documento:** Auditoría de provenance solicitada en sesión 2026-09-20
**Estado:** REPARADO Y VERIFICADO — cadena causal canónica con soporte dual de alias y orígenes trazables

---

## 1. Tres versiones identificadas y linaje canónico

### Versión A — Remoto publicado (`84eea97` / `b651d6e`)

| Campo | Valor |
|---|---|
| Commit base | `84eea9758ca50fd07e07076dd346e0947bffcf3f` / `b651d6ef9c35e55d57738ecd1517e4fa6f97edd0` |
| Rama | `feat/edge-discovery-brain-foundation-20260919` / `feat/unified-nt8-viewer-20260920` |
| SHA-256 (git blob, LF) | `7b13f198896b1fe4a89cb154f07c7c95d0a24bc74b6692590e6c47ff4cee56ea` |
| Tamaño | 19.643 bytes, 497 líneas |

Contiene: `meta_line()`, `header`, `csv_lines`, `params_line`, y campos `indicator`, `top`, `bottom`, `kind`, `timeline`, `lo`, `hi`, `side`, `dir` en `z_entry`.

### Versión B — Rama local divergente (`work/bt2a-gate2-p2a-freeze-20260826`, commit `e50bbf3`)

| Campo | Valor |
|---|---|
| Commit | `e50bbf3` (HEAD local) |
| SHA-256 (git blob, LF) | `b36670a140ccf918d6166f3739f33f242ff97d8fab19c9cd31281dc0189069fc` |
| Tamaño | 19.022 bytes, 479 líneas |

Divergencia vs A:
- Omitía: `meta_line()`, `header`, `csv_lines`, `params_line` en `return dict()`.
- Omitía: campos `indicator`, `top`, `bottom`, `kind`, `timeline` de `z_entry` (solo dejaba `hi/lo/side`).
- Causa de regresión en `f9dbb9b`: importada inadvertidamente desde worktree local B.

### Versión C — Canónica reparada (Base A íntegra + semántica causal completa)

| Campo | Valor |
|---|---|
| Base | `b651d6e` (Versión A completa y preservada) |
| SHA-256 (git blob, LF) | `fae5b57755751b036a38f55d44d619971cdae80603fbc50ce07f5d6d1a22eaa9` |
| Tamaño | 19.802 bytes, 501 líneas |

Campos agregados en `z_entry` sobre la Versión A:
- `formation_start_ns = int(blk_ts[0])`: apertura exacta del bloque en nanosegundos.
- `formation_end_ns = int(blk_ts[-1])`: cierre exacto del bloque en nanosegundos.
- `available_at_ns = int(blk_ts[-1])`: disponibilidad causal idéntica al cierre del bloque.

Preserva 100% de la API remota: `meta_line`, `indicator`, `top`, `bottom`, `kind`, `timeline`, `header`, `csv_lines`, `params_line`.

---

## 2. Semántica causal y exportador `viewer_export.py`

### Mapeo y compatibilidad de alias

`viewer_export._zone_json` implementa resolución dual para compatibilidad total productor/consumidor:
- `top`: `z["top"]` si existe, fallback a `z["hi"]`.
- `bottom`: `z["bottom"]` si existe, fallback a `z["lo"]`.
- `kind`: `z["kind"]` si existe, fallback a `z["side"]`.

### Timestamps exportados

- `t0`: exportado preferentemente desde `formation_start_ns` (`int(f_start_ns // 1e9)`). Si falta, fallback a `created_ms // 1000`.
- `formation_start_ts`: `formation_start_ns // 1e9` (segundos enteros).
- `formation_end_ts`: `formation_end_ns // 1e9` (segundos enteros).
- `available_ts`: segundo exacto en que la señal es ejecutable sin look-ahead.

### Clasificación de procedencia (`available_origin`)

| Etiqueta | Condición | Comportamiento |
|---|---|---|
| `KERNEL_AVAILABLE_AT_NS` | `available_at_ns` presente en zona | `available_ts = available_at_ns // 1e9` |
| `EXPLICIT_AVAILABLE_TS` | `available_ts` explícito precalculado | `available_ts = int(available_ts)` |
| `DERIVED_COMPATIBILITY_FALLBACK` | Sin timestamp y `source_barspec` es `time_*` | `available_ts = t0 + bar_duration_s` |
| `UNAVAILABLE` | Sin timestamp y barra no temporal (tick/vol) | `available_ts = None` (omitida en visor) |

### Invariante de causalidad

Para cualquier bloque o barra con duración mayor a cero ticks:
$$\text{formation\_start\_ts} \le \text{formation\_end\_ts} \le \text{available\_ts}$$

---

## 3. Estado de pruebas y cobertura

La suite focal `tests/bridge/test_bigtrap2_available_ts.py` cuenta con 22 pruebas automatizadas (PASS):
1. **`TestBarDurationS`** (9 tests): resolución exacta de duraciones para `time_5m`, `time_1m`, etc., y rechazo para `tick_25`, `vol_1000`, etc.
2. **`TestZoneCompatibilityAliases`** (3 tests): compatibilidad bidireccional Form A (`top/bottom/kind`), Form B (`hi/lo/side`) y canónica kernel (ambas formas simultáneas).
3. **`TestCausalOriginAndTimestamps`** (6 tests): etiquetado `KERNEL_AVAILABLE_AT_NS`, `EXPLICIT_AVAILABLE_TS`, `DERIVED_COMPATIBILITY_FALLBACK`, `UNAVAILABLE`, prioridad de kernel, e invariante de desigualdad temporal.
4. **`TestProducerToExporterIntegration`** (2 tests): verificación de APIs del productor (`meta_line`, `pipe_v1`) y roundtrip completo productor→exportador sin `KeyError`.
5. **`TestHoldoutIntegrity`** (2 tests): validación de que todos los fixtures sintéticos son estrictamente pre-holdout ($< 1.782.856.800.000.000.000\text{ ns}$).