# Incidente: Event Store all5 — cinco defectos de integridad

**Fecha de registro:** 2026-08-27  
**Autor:** Antigravity (auditoría automatizada)  
**Clase:** integridad de pipeline / procedencia de datos  
**Estado:** RESUELTO (builder v2 + auditor creados)  
**Rama de trabajo:** `work/bt2a-gate2-p2a-freeze-20260826`  

---

## Resumen

El Event Store de 4 indicadores (`E:\DatosNT8\event_store_gc_all5`, 117.156 filas)
generado por `build_event_store_all5.py` (commit `ced33dd`) tiene cinco defectos
que lo descalifican como input para downstream (Gate 2, sweep, contexto):

| # | Defecto | Severidad | Verificado |
|---|---------|-----------|------------|
| 1 | Holdout no recortado | CRÍTICO | 4.731 filas (41,3% de GC 08-26) post 2026-07-01 |
| 2 | Procedencia desconocida | CRÍTICO | 0 manifests con git commit / hash de inputs |
| 3 | Discrepancia contra Puerta 1 | ALTO | 71/234 sesiones difieren (+78 BT2A, +15 BT2) |
| 4 | `metadata_json` placeholder | ALTO | 100% de 117.156 filas con valores en cero |
| 5 | Duplicados HFTZones2 | MEDIO | 866 filas duplicadas (433 pares, zone_width=0) |

## Causa raíz por defecto

### 1. Holdout no recortado

**Código culpable:** `build_event_store_all5.py` (commit `ced33dd`) itera sobre
el parquet completo de cada contrato sin filtrar por el registro de sesiones de
Gate 1 (`bt2_absorption_gate1_all5_sessions_2026-08-26.json`), que congela la
ventana de GC 08-26 al rango `20260528–20260630`.

**Agravante:** al agregar HFTZones2 y VolTicksPOC2, el defecto se multiplicó
de 1.286 filas (solo BT2/BT2A) a 4.731 (HFTZones2: 3.059, VolTicksPOC2: 386).

### 2. Procedencia desconocida

**Código culpable:** el script no registra `git rev-parse HEAD`, dirty state,
hashes de inputs ni parámetros usados. El manifest sólo tiene `schema`,
`generated_utc` y conteos — insuficiente para reproducir.

**Agravante:** el commit `ced33dd` vive solo en la rama remota
`origin/work/futures-l2-context-foundation-20260825`, sin merge a `foundation`.
Los parciales del sweep registran `ced33dd` como `code_commit`, pero HEAD de
foundation es `7e8526e` — son hermanos divergentes.

### 3. Discrepancia contra Puerta 1

**Causas concurrentes:**

1. El script usa `edgelab.bridge.indicators.bigtrap2absorption` (runtime del
   bridge) en vez del runtime congelado de Gate 1
   (`edgelab.research.all5_runtime`).
2. No aplica la elegibilidad de horizonte de Gate 1 (`build_path_cache` con
   descarte por tick_cap/clock_cap).
3. Usa `min(idx + 1, n_ticks - 1)` como fill sin rechazar el último tick.
4. Procesa el contrato entero, no la registry de 234 sesiones.

### 4. `metadata_json` placeholder

**Mapa de claves incorrectas:**

| Indicador | Script buscó | Kernel emite |
|-----------|-------------|-------------|
| BigTrap2Absorption | `z.get("score")` | `z["a_score"]` |
| BigTrap2Absorption | `z.get("absorbed_vol")` | `z["vol"]` |
| HFTZones2 | `z.get("zone_width")` | `z["height_ticks"]` |
| VolTicksPOC2 | `z.get("poc_vol")` | zona no tiene esa clave |

Todas las claves inexistentes caen al default `0.0` del `.get()`.

### 5. Duplicados HFTZones2

**Causa:** `z.get("sig_idx", z.get("bar_idx", 0))` resuelve a `0` porque los
dicts de `zones` de HFTZones2 no contienen ni `sig_idx` ni `bar_idx`.
Múltiples zonas colapsan al tick 0, generando pares duplicados ficticios.

## Resolución

### Scripts creados

1. **`tools/build_event_store_all5_v2.py`** — builder corregido que:
   - Filtra por session registry (corrige #1)
   - Registra git state, hashes, parámetros (corrige #2)
   - Usa `session_ids` + filtro de sesiones válidas (alinea con #3)
   - Mapea las claves reales de cada kernel (corrige #4)
   - Resuelve tick indices correctamente: `sig_idx`/`fill_idx` para BT2A,
     `bar_close_indices` para BT2/VolTicksPOC2, `created_ms` → searchsorted
     para HFTZones2 (corrige #5)

2. **`tools/audit_event_store.py`** — auditor con 6 checks:
   - `1_holdout_trimming`: filas con session >= 20260701
   - `2_provenance`: manifest con git commit y hashes
   - `3_gate1_reconciliation`: cruce contra session registry
   - `4_metadata_placeholders`: detección de campos all-zero
   - `5_duplicates`: duplicados exactos y por clave compuesta
   - `6_fill_causality`: fill estrictamente posterior a señal

### Resultado de auditoría sobre el store existente

```
1_holdout_trimming:      FAIL  (4.731 violations)
2_provenance:            FAIL  (no manifest with git state)
3_gate1_reconciliation:  FAIL  (rows outside window)
4_metadata_placeholders: FAIL  (100.0% all-zero)
5_duplicates:            FAIL  (duplicate rows present)
6_fill_causality:        PASS  (0 violations)
OVERALL: FAIL
```

### Uso del builder corregido

```powershell
python tools/build_event_store_all5_v2.py `
    --data-dir "E:\DatosNT8\gc_gate1_parquets_20260825" `
    --output-dir "E:\DatosNT8\event_store_gc_all5_v2" `
    --session-registry specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json `
    --input-registry specs/bt2_absorption_gate1_all5_input_registry_2026-08-26.json
```

### Uso del auditor

```powershell
python tools/audit_event_store.py `
    --store-dir "E:\DatosNT8\event_store_gc_all5_v2" `
    --session-registry specs/bt2_absorption_gate1_all5_sessions_2026-08-26.json `
    --output-json audit_result.json
```

## Nota sobre el store existente

El store original (`event_store_gc_all5/`) NO se borró ni modificó.
Queda como evidencia forense con el `AUDIT_RESULT_2026-08-27.json` junto a él.

## Aporte al referente

El Event Store de 4 indicadores queda formalmente descalificado y documentado.
El builder v2 y el auditor están creados y verificados para la regeneración
cuando Nico lo autorice.
