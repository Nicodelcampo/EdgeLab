# Contrato de kernel del bridge NT8 → EdgeLab

Este documento define TODO lo necesario para escribir un kernel válido sin leer
otro archivo. Un kernel traduce un indicador NT8 a Python 1:1 y produce
observaciones, eventos y zonas verificables contra el oráculo NT8 (paridad P2).

> Regla rectora: **guardar correctamente una zona y demostrar que coincide con
> NT8 son dos pruebas diferentes.** El kernel produce; el store persiste con
> integridad auditada (gate P3); la paridad NT8 es un eje de evidencia aparte.

## 1. Firma y registro

Un kernel es un módulo en `edgelab/bridge/indicators/<name>.py` con:

```python
NAME = "MiIndicador"          # == nombre de clase NT8 y clave del REGISTRY
DEFAULTS = dict(...)          # todos los parámetros con su valor por defecto
PARAM_SPEC = {...}            # espacio paramétrico declarado (ver §3)
HEADER = "col1,col2,..."      # header del CSV de eventos (o None si formato pipe)

def run(ticks, bars, params=None, chart_tz="UTC"):            # TICK_DRIVEN
def run(ticks, bars, footprints, params=None, chart_tz="UTC"): # BAR_DRIVEN
    ...
    return dict(indicator=NAME, params=p, header=HEADER, csv_lines=lines,
                events=rows, zones=zones, params_line=<meta>)
```

Registro en `edgelab/bridge/indicators/__init__.py`:
- agregar `from . import <name>` y `REGISTRY["MiIndicador"] = <name>`;
- clasificar en `TICK_DRIVEN` (recorre ticks + barras) o `BAR_DRIVEN` (consume
  el footprint reconstruido `bars.build_footprints`).

`run` recibe:
- `ticks`: `TickSeries` (`ts_ns` int64 UTC monótono, `price_ticks` int64,
  `volume` float64, `bid_ticks`/`ask_ticks` int64|None, `sequence`, `tick_size`,
  `instrument`, `contract`). Precios en ticks enteros; precio real = `p*tick_size`.
- `bars`: `BarSeries` (`start_ns`, `end_ns`=cierre, `open/high/low/close_t` en
  ticks, `volume`, `kind` time|tick, `param`, `tick_bar_idx`).
- `footprints` (solo BAR_DRIVEN): `.ask[b]`, `.bid[b]`, `.total[b]` dicts
  `{price_tick: vol}`, `.n_quote`, `.n_rule`, `.has_quotes`.

## 2. Invariantes NO negociables

1. **Cuantiles/percentiles EXACTOS sin interpolación** (`common.quantile_exact`,
   `common.empirical_pct`). Prohibidos estimadores streaming aproximados
   (P², reservoir, sketches).
2. **El baseline / perfil EXCLUYE la observación actual** (anti auto-amortiguación):
   la ventana/perfil se actualiza DESPUÉS de comparar la barra/tick actual.
3. **Cero look-ahead**: nada depende de barras futuras ni de `len(bars)` total.
   La barra/tick creador de una zona nunca toca ni invalida su propia zona.
4. **Lifecycle nombrado y explícito**: `ZONE_CREATED`, `ZONE_TOUCHED`,
   `ZONE_PARTIAL` (si aplica), `ZONE_INVALIDATED` (con `reason`), `ZONE_EXPIRED`,
   `SESSION_END`. Estados finales: INVALIDATED | EXPIRED | ACTIVE.
5. **Footprint reconstruido, un solo motor**: siempre desde la subserie 1-tick
   (clasificación quote-then-tickrule de `bars.build_footprints`), jamás un
   dual-path Volumetric. `total = ask + bid` por nivel.
6. **Errores nunca silenciosos**: sin quotes / sin tick data → evento `ERROR` y
   cero detecciones, nunca fallback a un precio inventado.
7. **Formatos de evento estables** (mismas columnas y orden que el EventLog NT8;
   `InvariantCulture` vía `common.fnum/gnum/plain`). Determinismo bit a bit:
   sin `Date`/`random`/orden de dict no determinista.
8. **Desviaciones declaradas**: cualquier diferencia con el .cs (aunque sea solo
   de campo de export) se documenta en el docstring del kernel.

## 3. PARAM_SPEC

Cada parámetro de `DEFAULTS` declara su metadato (más los visual/forbidden que
no están en DEFAULTS pero deben rechazarse):

```python
PARAM_SPEC = {
  "imbalance_ratio": {"type": "float", "default": 3.0, "min": 1.0,
                      "class": "recompute", "branches": ["imbalance_detection"],
                      "suggested_grid": [1.5, 2.0, 3.0, 4.0]},
  "detection_percentile": {"type": "float", "default": 99.5, "class": "offline",
                      "branches": ["cut"], "requires_covered_by": "export_floor_percentile"},
  "max_age_bars": {"type": "int", "default": 2000, "class": "lifecycle",
                   "branches": ["expiration"]},
  "TopPercentFilter": {"class": "forbidden", "optimizable": False,
                       "reason": "renderer selecciona por percentil (look-ahead)"},
}
```

- `type`: `int|float|bool|str`. `default` debe ser idéntico a `DEFAULTS[key]`.
- `class`:
  - **recompute** — cambia el estado histórico; reejecuta el kernel.
  - **lifecycle** — invalidación / edad / touches; re-simulable desde eventos+ticks.
  - **offline** — corte re-filtrable desde el export continuo (OBS) SOLO si el
    piso de export lo cubre → declarar `requires_covered_by: <param_del_piso>`.
  - **instrument** — propio del instrumento (tick_size, etc.).
  - **visual** — solo dibujo; `optimizable: False`; nunca en identidad ni grilla.
  - **forbidden** — look-ahead / renderer analítico; se rechaza siempre.
- `branches`: ramas de código que activa el parámetro → alimenta la matriz de
  cobertura de paridad (F7).
- `min`/`max`/`choices`/`suggested_grid`: opcionales.

Solo las clases **recompute, lifecycle, offline, instrument** entran a
`config_id`. visual/forbidden jamás. La CLI (`identity.validate_params`) rechaza:
(1) parámetro inexistente, (2) tipo incorrecto, (3) fuera de rango/choice,
(4) visual/forbidden en grilla analítica, (5) filtro offline con piso de export
no cubierto.

## 4. Schemas de salida

`run` devuelve un dict con:
- `csv_lines`: líneas del EventLog en el MISMO formato que NT8 (diffeable).
- `header` / `params_line`: header y línea `# meta`/`# params` del CSV.
- `events`: lista de dicts (timeline completa) — al menos `seq` (monótono),
  `type`, `ts_ns`, `unix_ms`; `zone_id` cuando aplique, `reason`.
- `zones`: lista de dicts con el esquema común mínimo:
  `id, indicator, top, bottom, created_ms, ended_ms, state, kind, touches,
  end_reason` + campos propios del kernel (`size_ticks`, `dir`, `bucket`,
  `calib_id`, …) que van a `features` en el store. `timeline` opcional (visor).
- **Observaciones continuas** (`OBS`): exportar el score continuo (percentil
  empírico, robust-z, ratio, poc, etc.) desde un piso de export, no solo las
  zonas que superan el corte → permite barrer umbrales offline sin recomputar.

## 5. Identidades (ver `identity.py`)

`dataset_id` (contenido de ticks) · `kernel_id` (código del kernel + deps
common/bars/sessions + versión de schema) · `config_id` (params materializados +
bar_spec + chart_tz + kernel_id) · `run_id` (dataset+config+rango+engine) ·
`zone_key` (global, incluye run_id). Cambiar el bar builder o el calendario
cambia el `kernel_id` de todos los kernels que dependen de ellos.

## 6. Definition of done (ver F9)

contrato → tests (determinismo, anti-lookahead, invariante propio, smoke) →
determinismo bit a bit → anti-lookahead verificado → P1A real sobre muestra
chica → gate P3 completo (integridad + round-trip + recomputación) → visor →
(si hay NT8) parser de oráculo + P2 → campaña chica → **consulta desde EdgeLab
sin ejecutar el kernel**. Recién ahí el kernel está "terminado".
