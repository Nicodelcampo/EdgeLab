# NT8 Bridge — kernels, visor de paridad y zone store

Pipeline: `parquet canónico F2 → selección contrato/rango → barras [inicio,fin)
(tiempo o tick) → footprint (gate P1A) → kernels Python 1:1 de NT8 → zonas/
eventos → matcher vs EventLog NT8 (gate P2) → visor + zones.parquet`.

**Regla no negociable:** un indicador NO entra a vectorbt/fuerza bruta hasta
pasar paridad real contra NT8 (mismo contrato, rango, timeframe, parámetros,
timezone declarada y tick data). El PASS sintético solo valida infraestructura.

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

## Visor (offline)

`viewer/index.html` — Lightweight Charts v4.2.0 **vendorizado** (sin CDN/
internet). Selector de run (indicador · param_set · barras) para cambiar de
configuración y ver el cambio de zonas; zonas Python rellenas, NT8 en contorno
punteado, huérfanas en rojo; filtros por fuente/estado, modo "solo huérfanas",
tabla navegable (click = zoom a la zona), panel P1A/paridad y parámetros del
run; tz rotulada en el header. El visor es estrictamente pasivo (jamás computa
señales): dibuja lo que el kernel produjo. Nota: `file://` puede fallar en
Chrome; servir con `python -m http.server` si hace falta.

## Estado de kernels

| Kernel | Integrado | Smoke sintético | P1A real | Paridad real NT8 |
|---|---|---|---|---|
| Gaps2 | ✅ | ✅ | ✅ (6E 09-25) | **pendiente** (ver `nt8_indicator_parity_contract.md`) |
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
