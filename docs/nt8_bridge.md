# NT8 Bridge — kernels, visor de paridad y zone store

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md).

Pipeline: `parquet canónico F2 → selección contrato/rango → barras [inicio,fin)
(tiempo o tick) → footprint (gate P1A) → kernels Python 1:1 de NT8 → zonas/
eventos → matcher vs EventLog NT8 (gate P2) → visor + zones.parquet`.

**Regla no negociable:** un indicador NO entra a vectorbt/fuerza bruta hasta
pasar paridad real contra NT8 (mismo contrato, rango, timeframe, parámetros,
timezone declarada y tick data). El PASS sintético solo valida infraestructura.

## Suite de tests canónica

Comando único, reproducible, para toda verificación de regresión del bridge:

```powershell
.venv\Scripts\python -m pytest tests -m "not vectorbt" -q
```

Nota de alcance: el comando corre **todo el repo** (`tests/`), no solo
`tests/bridge/` — incluye `tests/foundation` (F0-F2) y `tests/research`
(firewall del holdout, FASE 3b); es la suite canónica del PROYECTO, documentada
acá por ser el punto de referencia histórico de esta reconciliación.

Al 2026-07-24 (commit `f316b23` + reconciliación de esta sección):
**152 passed, 3 deselected**. Los conteos "101 / 131 / 139" reportados en
turnos previos correspondían a alcances distintos, no a regresiones — evidencia
textual en los propios mensajes de commit:

| Conteo reportado | Commit / fase | Alcance real (evidencia) |
|---|---|---|
| 101 | `90fbe11` | **`tests/bridge` solamente** — el mensaje dice literalmente "Bridge suite 101 passed", un subconjunto (excluye `tests/foundation`, 30 tests). NO es la suite global. |
| 131 | `0555e5d` | Suite global (`tests -m "not vectorbt"`) en ese punto del historial, ANTES de que F8 agregara `test_features.py` (6 tests) y `test_vectorbt_demo.py` (2 tests no-vectorbt + 1 deselected). |
| 139 | `af48609` | Suite global tras F8. Verificación aritmética exacta: 131 + 6 + 2 = 139. |
| 141 | FASE 1 (`d0a894e`) | Suite global tras agregar 2 tests de regresión de frontera de madurez (`test_boundary_created_exactly_at_frontier_is_mature`, `test_real_gaps2_pass_run_has_zero_mature_lifecycle_diffs`). |
| **152** | FASE 3b (firewall del holdout) | Suite global tras agregar `tests/research/test_holdout_guard.py` (11 tests). Verificación aritmética: 141 + 11 = 152. |

Verificación de la partición: `tests/bridge` (109) + `tests/foundation` (30) =
**139** = conteo global de ese momento (antes de agregar los 2 tests de esta
reconciliación). Los "2 skipped" de `tests/foundation` son runtime-skips vía
`pytest.importorskip("vectorbt")` en `test_vectorbt_optional.py` (mecanismo
distinto de la deselección por marker `-m`: corren y se auto-saltan porque
vectorbt no está instalado).

## Uso

```bash
# demo sintética (sin datos reales)
.venv\Scripts\python tools\run_nt8_bridge.py --synthetic --indicator Gaps2 \
    --out runs\nt8_bridge\demo

# muestra real F2 con grid de parámetros (multi-run) y visor
.venv\Scripts\python tools\run_nt8_bridge.py \
    --data data\nt8\6E\6E_09-25_ticks.parquet --contract "6E 09-25" \
    --start-utc 2025-08-01T00:00:00 --end-utc 2025-08-02T00:00:00 \
    --bars time:1 --indicator Gaps2 \
    --param-grid "Gaps2=[{\"min_gap_ticks\":3},{\"min_gap_ticks\":6,\"bars\":\"tick:25\"}]" \
    --oracle Gaps2=oracles\Gaps2_events_nt8.csv \
    --out runs\nt8_bridge\6e_0925_gaps2
```

- `--bars time:N | tick:N` es el default; cada param set puede overridearlo con
  la clave reservada `"bars"` (p.ej. BigTrap2 sobre chart de 25 ticks).
- Cada run queda identificado por `param_set_id` (sha256 corto del JSON
  canónico de parámetros + bar spec): identidad estable para fuerza bruta.

## Salidas (`--out`)

| Artefacto | Contenido |
|---|---|
| `run_manifest.json` | fuente + sha256, filtros, rev de código, runs (params, gates) |
| `<run_id>_events_py.csv` | eventos en el MISMO formato que el EventLog NT8 (diffeable) |
| `zones.parquet` | **zone store**: coordenadas de todas las zonas de todas las configs (`indicator, param_set_id, bar_key, zone_id, top/bottom_ticks, created/ended_ms, state, ...`) |
| `p1a_report.json` | gate P1A por configuración de barras |
| `parity_report.json` | diagnósticos y gate P2 por run (solo con `--oracle`) |
| `viewer/` | visor offline (index.html + vendor local + data.js multi-run) |

## Store v2 (F6.2) — inmutable, content-addressed, tres niveles

Producto de primer nivel: EdgeLab consulta coordenadas de zonas por identidad
(dataset + kernel + config) con garantía auditada de que lo consultado es
exactamente lo que el kernel produjo, **sin re-correr indicadores**. Se activa
con `--zone-store <raíz>` (`edgelab/bridge/store.py`).

**Tres tablas por partición** (no solo zonas finales):
- `observations.parquet` — observaciones continuas (OBS/TRAP) para auditoría y
  re-filtrado offline de umbrales.
- `events.parquet` — la timeline inmutable completa (fuente de verdad).
- `zones.parquet` — proyección materializada para consulta rápida. **Regla:
  zones debe reconstruirse desde events y dar el mismo digest de núcleo**; si
  difiere, se localiza el evento donde nació la discrepancia (P3.1).

**Layout content-addressed** (una carpeta por run; la ruta NO es identidad, el
contenido sí):

```
<raíz>/catalog.duckdb
<raíz>/runs/instrument=<I>/contract=<C>/indicator=<K>/kernel_id=<KID>/
       bar_key=<BK>/config_id=<CID>/run_id=<RID>/
           manifest.json  observations.parquet  events.parquet  zones.parquet
           validation.json  parity.json
```

**Identidades** (`edgelab/bridge/identity.py`): `dataset_id` (contenido de ticks),
`kernel_id` (código + deps common/bars/sessions), `config_id` (params
materializados + bar_spec + chart_tz + kernel_id), `run_id`, `zone_key` (global).

**Manifest**: las 4 identidades, params canónicos, fuente (ruta+sha256+filas+
rango UTC), tz, conteos por estado, los **tres digests** (observation/event/zone
sobre filas ordenadas canónicamente), entorno (Python + hash del lockfile), y
los dos ejes de estado.

**Dos ejes de estado ortogonales** (reemplazan el booleano `trusted`):
- **integridad**: `computed → persisted → roundtrip_verified → recomputed_exact
  → api_verified` | `stale` | `failed`.
- **paridad**: `parity_pending | parity_exact | parity_covered | parity_failed`.

**Reglas duras**: escribir a temp → validar (P3.1) → round-trip (P3.2) → publicar
por rename atómico; partición publicada **inmutable**; reejecución idéntica con
digests iguales = idempotencia (no duplica), con digests distintos =
`DeterminismError` (no sobrescribe, frena); **cero zonas es un resultado válido**
(`n_zones=0`, partición presente).

**Consumo** (fuerza bruta): exploratoria exige `integrity_state=api_verified`;
formal exige además `parity_exact` o `parity_covered`; promover un edge a
`EDGES_DISCOVERED.md` exige `parity_exact` PROPIO de la config ganadora.

**API**: `store.catalog_df(root)` (una fila por partición), `store.publish_run(...)`,
`store.get_zones(root, indicator=..., config_id=..., integrity_state=..., state=...)`
(consulta pública que consume la fuerza bruta), `store.set_state(...)`.

## Gate P3 — auditor de materialización (F6.3)

**Guardar una zona y demostrar que coincide con NT8 son dos pruebas distintas.**
P3 valida la MATERIALIZACIÓN (que lo guardado es exactamente lo que el kernel
produjo); la paridad NT8 es el otro eje. Siete subgates (`edgelab/bridge/audit.py`):

- **P3.0** completitud de campaña — `expected == present + failed`, `missing=0`,
  `duplicated=0` contra un `campaign_manifest`.
- **P3.1** validación in-memory (inline al publicar): secuencias, unicidad,
  geometría, y **zones reconstruibles desde events** (mismo digest de núcleo).
- **P3.2** round-trip (inline + auditable): re-lee los 3 parquet, recalcula
  digests, exige igualdad con el manifest.
- **P3.3** determinismo por recomputación: reejecuta desde el manifest (fuente
  por sha256, kernel_id, params, entorno) y exige los 3 digests. Código ausente
  → `STALE`; entorno distinto → `ENV_DIFF` (≠ corrupción).
- **P3.4** accesibilidad por API: `digest(get_zones(...))` == `zone_digest`.
- **P3.5** integridad entre configs: una config jamás devuelve zonas de otra;
  `(dataset, config)` en >1 run = `DUPLICATE_CONFIG`.
- **P3.6** auditor adversarial: detecta las 9 corrupciones (zona borrada,
  tick/estado mutado, manifest alterado, config duplicada/eliminada, fila de
  otro contrato, parquet truncado, API con fila incorrecta) con exit != 0.
- **P3.7** `tools/store_audit.py --all` — EL gate previo a toda campaña:
  P3.2/P3.4/identidad al 100%, P3.3 por muestreo (`--recompute-sample`), reporte
  por partición, exit != 0 ante cualquier falla. `--promote` eleva a
  `api_verified` las particiones que pasan todo.

```bash
python tools/store_audit.py --store <root> --all --recompute-sample 1.0 --promote
```

## Runner de campañas (F6.4)

`tools/run_campaign.py` toma una campaña declarativa (`.toml` o `.json`; no se
usa YAML porque pyyaml no está en el lock), deriva la grilla (producto cartesiano
de la grilla × bar_specs), **declara el número de configs y el costo estimado
ANTES de correr** y aborta si supera `max_configs` (control de explosión). Valida
cada config contra PARAM_SPEC (no arranca a medias), genera el
`campaign_manifest` con los `config_id` esperados, ejecuta publicando al store
(P3.1/P3.2 inline) y **cierra con P3.0** (completitud: `expected == succeeded +
failed`, `missing=0`, `duplicated=0`). Grilla gruesa primero y refinamiento
local después = campañas pre-registradas sucesivas, nunca un barrido silencioso.

```toml
campaign_id = "gaps2_smoke"
store       = "runs/nt8_bridge/store"
max_configs = 40
[data]
  parquet = "data/nt8/6E/6E_09-25_ticks.parquet"
  contract = "6E 09-25"
  start_utc = "2025-08-01T00:00:00"
  end_utc   = "2025-08-02T00:00:00"
[[jobs]]
  indicator = "Gaps2"
  bars = ["time:1"]
  [jobs.grid]
    export_floor_ticks = [2, 3]
    min_gap_ticks = [5, 8, 12]
```

```bash
python tools/run_campaign.py --campaign campaign.toml --dry-run   # solo declara
python tools/run_campaign.py --campaign campaign.toml --audit     # corre + P3.0 + audit
```

## API de features para vectorbt (F8)

`edgelab/bridge/features.py` es la capa de consumo: la fuerza bruta lee zonas
**verificadas** del store por identidad y las materializa as-of a cualquier serie
de barras, **sin importar ningún módulo de kernel** (los kernels solo producen y
publican). Todo point-in-time: en la barra `t` solo se ven zonas con
`created_ms <= t` (cero look-ahead).

- `resolve_config_id(indicator, params, bar_key, chart_tz)` → config_id canónico.
- `get_zone_rows(root, …)` / `get_zones_df(root, …)` → zonas por identidad/estado
  (filtros: indicator, config_id | params, contract, instrument, bar_key, state,
  integrity_state, parity_state, rango). El digest de lo consultado ==
  `zone_digest` del manifest (garantía P3.4, verificada sobre las filas crudas).
- `materialize_features(zones_df, index_ms, price, features=[...])` → columnas
  alineadas: `inside_zone`, `distance_to_nearest_zone`, `active_zone_count`,
  `zone_age`, `nearest_zone_side`.

Demo end-to-end: `tools/demo_vectorbt_zones.py` combina zonas de **2 indicadores**
del store en una señal y corre una `vbt.Portfolio` — sin tocar ningún kernel
(test lo verifica inspeccionando los imports). vectorbt es el extra opcional
`research-vectorbt`; el test que lo ejecuta está detrás del marcador `vectorbt`.

```python
from edgelab.bridge import features
za = features.get_zones_df(root, indicator="Gaps2", contract="6E 09-26",
                           params={"min_gap_ticks": 2}, integrity_state="api_verified")
f = features.materialize_features(za, bar_ms, price=close,
                                  features=["inside_zone", "active_zone_count"])
```

## Visor v2 — tres modos sobre el store (F6.5)

`tools/build_viewer.py --store <root> --out <dir>` exporta el store publicado a
un bundle (`store_data.js`) que el visor v2 (`store_viewer.html`) consume. El
visor sigue **estrictamente pasivo**: renderiza lo que el exportador volcó del
store, jamás recalcula ni selecciona. Cambiar parámetros = correr otra campaña y
regenerar el bundle. Servir por HTTP (`python -m http.server`), no `file://`.

Tres modos sobre el mismo chart+overlay:
- **Parity Review**: zonas Python rellenas vs NT8 punteadas; con oráculo
  (`build_viewer --oracle Indicador=ruta.csv`) colorea huérfanas rojas,
  GEOMETRY_DIFF naranja, TIMESTAMP_DIFF amarillo, MATCHED neutro; navegación
  anterior/siguiente discrepancia que salta el chart a la zona con el detalle;
  filtro por código; export CSV; rótulo permanente de dataset/contrato/config_id/
  kernel_id/integridad/paridad; marca humana "investigada" con nota que **nunca**
  cambia el gate automático.
- **Parameter Atlas**: selector A/B de configs del mismo indicador; overlay de
  "solo agregadas / solo removidas / geometría modificada / comunes"; diff de
  parámetros resaltado y conteos comparados. La herramienta de "parámetros
  sólidos": ver cómo la variación paramétrica mueve las zonas.
- **Store Audit**: panel del catálogo (una fila por partición) con estados de
  integridad y paridad; click lleva a esa config en Parity Review.

```bash
python tools/build_viewer.py --store runs/nt8_bridge/store --out runs/nt8_bridge/viewer
python -m http.server -d runs/nt8_bridge/viewer 8770   # abrir http://127.0.0.1:8770
```

## Visor (offline, per-run legacy)

`viewer/index.html` — Lightweight Charts v4.2.0 **vendorizado** (sin CDN/
internet). Selector de run (indicador · param_set · barras) para cambiar de
configuración y ver el cambio de zonas; zonas Python rellenas, NT8 en contorno
punteado, huérfanas en rojo; filtros por fuente/estado, modo "solo huérfanas",
tabla navegable (click = zoom a la zona), panel P1A/paridad y parámetros del
run; tz rotulada en el header. El visor es estrictamente pasivo (jamás computa
señales): dibuja lo que el kernel produjo. Nota: `file://` puede fallar en
Chrome; servir con `python -m http.server` si hace falta.

## Estado del plan (reconciliado con artefactos, no con resúmenes de turno)

Reconciliación mecánica (evidencia = código/tests/artefactos, no el resumen de
un turno anterior):

- **F6.4 (runner de campañas)** — EXISTE: `tools/run_campaign.py` (244 líneas).
  Confirmado por inspección directa del código:
  - formato declarativo `.toml`/`.json` (NO `.yaml`: pyyaml no está en el lock,
    decisión de la fase original);
  - expansión de grillas: SÍ (`_expand_grid`, producto cartesiano vía `itertools`);
  - `max_configs` con abort si se excede (control de explosión) — es un TECHO
    duro, no el concepto de "presupuesto de investigación / N_eff" de
    `edge_validation_contract.md` (ese conteo de TODAS las hipótesis cobradas,
    incluidas las abandonadas, no existe como mecanismo automático todavía);
  - P3.0: SÍ (`campaign_manifest` con `expected_config_ids`, cierre vía
    `audit.check_campaign`);
  - reanudación idempotente: **NO existe optimización de reanudación**. El loop
    de ejecución SIEMPRE recomputa el kernel de cada config planificada, sin
    saltar las ya publicadas. Lo que SÍ es cierto: `store.publish_run` es
    idempotente (mismos digests → no duplica), así que re-correr la misma
    campaña completa es SEGURO (no corrompe el store), pero no es EFICIENTE
    (no hay skip-ahead de trabajo ya hecho).

- **F7 — separado en sub-fases** (no es una fase monolítica completa):
  - **F7a (pre-registro de oráculos, matrices de cobertura por rama)**: HECHO.
    `docs/parity_coverage/*.md` (5 archivos) + `docs/nt8_indicator_parity_contract.md`
    §6-§7 con contrato/rango/params/EventLogPath exactos por oráculo.
  - **F7b (oráculos NT8 recibidos)**: **PENDIENTE de Nico**, salvo uno. Único
    CSV real en `oracles/`: `Gaps2_6E_0926.csv` (ya procesado, gate PASS). Los
    9 oráculos de la tanda pre-registrada (Gaps2 25t, VolTicksPOC2 ×2, BigTrap2
    ×2, HFTZones2 ×2, aVolCellPOI2) **no han llegado**: todas las filas de las
    matrices de cobertura siguen marcadas `pendiente` (grep confirmado: 45
    ocurrencias de "pendiente" en `docs/parity_coverage/*.md`).
  - **F7c (gates y promoción automática por cobertura de ramas)**: **NO
    implementado**. `edgelab/bridge/coverage.py` (branch-accounting:
    `branches_of`, `config_branches`, `is_covered`) existe y tiene tests
    propios, pero **no se llama desde ningún otro módulo** (`store.py`,
    `audit.py`, `run_campaign.py`) — verificado por grep, cero referencias
    fuera del propio archivo. `store._parity_state()` solo asigna
    `parity_pending` / `parity_failed` / `parity_exact`; **nunca asigna
    `parity_covered`**, aunque ese estado está definido en `PARITY_STATES`.
    Es infraestructura declarada pero no conectada.

- **F8 (API de features)** — separado por nivel de evidencia:
  - API probada: SÍ (`test_features.py`, 6/6 tests, incluida la garantía de
    digest `get_zones == manifest.zone_digest`).
  - Contrato de dtypes y semántica as-of documentado: SÍ (`docs/nt8_bridge.md`
    § "API de features para vectorbt (F8)").
  - Demo vectorbt estructural (combina 2 indicadores sin importar kernels):
    SÍ, probado (`test_build_signals_combines_two_indicators`).
  - **Demo vectorbt EJECUTADA** (`vbt.Portfolio.from_signals` corriendo de
    verdad): **NO**. `vectorbt` no está instalado en este entorno
    (`ModuleNotFoundError`); `test_run_demo_portfolio` (marcado `@pytest.mark.vectorbt`)
    se salta (`SKIPPED`, confirmado corriendo el archivo directamente). Para
    ejecutarlo de verdad hace falta instalar el extra opcional
    `research-vectorbt` (`requirements/full-research.lock`).

## Estado de kernels

| Kernel | Integrado | Smoke sintético | P1A real | Paridad real NT8 |
|---|---|---|---|---|
| Gaps2 | ✅ | ✅ | ✅ (6E 09-25) | ✅ **PASS** (6E 09-26, 07-13→16, 1316/1316, ver `nt8_indicator_parity_contract.md` §1) |
| VolTicksPOC2 (F5A) | ✅ | ✅ | ✅ (6E 09-25, time:1) | pendiente (mismo protocolo) |
| BigTrap2 (F5B) | ✅ | ✅ | ✅ (6E 09-25, time:1 + tick:25) | pendiente (mismo protocolo) |
| HFTZones2 (F5C) | ✅ | ✅ | ✅ (6E 09-25, 3 sesiones) | pendiente (mismo protocolo) |
| aVolCellPOI2 (F5D) | ✅ | ✅ | ✅ (6E 09-25, 1 mes → 54 zonas) | pendiente (mismo protocolo) |

Los 5 kernels comparten el contrato común `run(ticks, bars[, footprints],
params, chart_tz)` y viven en `edgelab/bridge/indicators/`. Tick-driven: Gaps2,
HFTZones2. Bar-driven (consumen footprint reconstruido): VolTicksPOC2, BigTrap2,
aVolCellPOI2. El `oracle.py` ya parsea los 5 formatos (CSV coma + pipe BigTrap2).

## Límites conocidos (declarados)

- Sesiones CME sin feriados → diferencias en feriados = `CALIBRATION_DIFF`.
- Footprint reconstruido: ticks con ts == cierre de barra pueden caer en barras
  distintas que NT8 (corte canónico `[inicio, fin)`).
- Kernels en Python puro: correctitud primero; kernels Numba = fase posterior.

### Dibujo en el chart ≠ export (importante para paridad)

El **dibujo on-chart** es un filtro VISUAL, distinto del **export** que alimenta
la paridad. En Gaps2: se **exportan** al CSV todos los gaps `>= ExportFloorTicks`
(default 2); se **dibujan** solo los `>= MinGapTicks` (default 5, `Display`). La
paridad se confirma desde el CSV (`EventLogPath`), NO desde lo que se ve en el
chart. En 6E los saltos tick-a-tick son de 2-3 ticks (medido: sobre 2 días,
115 gaps de 2t + 2 de 3t + **0 de ≥5t**), así que con `MinGapTicks=5` el chart
queda **vacío aunque el CSV tenga cientos de zonas** — es correcto, no un bug.
`MinGapTicks=5` está calibrado para ES/NQ (tick 0.25 ≈ 1.25 pts); para 6E, bajar
`MinGapTicks` a 2 solo para VER las zonas (no afecta el export ni la paridad).
El mismo principio aplica a los otros kernels (piso de export vs corte de
display/detección).

### Desviaciones declaradas por kernel (F5)

- **VolTicksPOC2**: baseline recomputado `sum(win)/len` en vez del `baselineSum`
  incremental del .cs (misma media, solo orden de suma en float).
- **BigTrap2**: cada resolución de barra (time:1, tick:5, tick:25, …) es una
  configuración distinta; el `bar_key` entra al `param_set_id` y es columna del
  zone store, así que las zonas no colisionan aunque compartan `zone_id`
  `{bar}_{B|S}`. El POC es solo visual en el .cs y no entra al export analítico.
- **HFTZones2**: la paridad real exige que el rango arranque en borde de sesión
  con ≥1 sesión completa previa (calibración congelada); si no, la primera
  sesión emite `CALIBRATION_PENDING` y no crea zonas. Feriados no modelados →
  `CALIBRATION_DIFF`.
- **aVolCellPOI2**: con `min_sessions=15` y `lookback_sessions=20` el oráculo
  NT8 necesita **semanas** de historia cargada antes de que aparezcan zonas;
  sobre muestras cortas produce 0 zonas (historia insuficiente), nunca
  detecciones falsas. Celdas del footprint reconstruido ≡ barras Volumetric NT8
  (validar en P1B). Roll de sesión modela `IsFirstBarOfSession` con `b==0`.
