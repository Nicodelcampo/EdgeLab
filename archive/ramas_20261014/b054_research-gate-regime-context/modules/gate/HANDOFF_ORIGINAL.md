# GATE → EdgeLab — Handoff para Claude Code

**Fecha:** 2026-08-23  
**Objetivo:** Continuar el complemento GATE (contexto PRE de micro-régimen) sobre el contrato EdgeLab, sin romper causalidad ni el gauntlet de research.

---

## 1. Qué es este módulo

GATE **no es una señal ni un edge**. Es un **productor de labels de contexto** en \(t_0\) del evento:

```
NT8 exporta evento (BigTrap2Absorption / HFTZones / TRAP)
    → GATE etiqueta régimen en t0 (as-of backward only)
    → trial pre-registrado CTX-3 (condiciona el estimando de la familia)
    → (opcional) valor incremental vs pct_rv
```

**model_id congelado:**  
`gate_tf_causal_bal_v2_feat10_sticky90_vpin055`  
(ver `schema/gate_model_id_frozen.json`)

---

## 2. Estructura del zip

```
GATE_MODULE_HANDOFF/
  HANDOFF.md                          ← este archivo
  docs/
    GATE_ROADMAP.md                   ← pasos 1–5
    GATE_INTEGRATION_CHECKLIST.md     ← definición de "aplicable"
  schema/
    gate_context_schema_v1.json       ← columnas + reglas join
    gate_model_id_frozen.json         ← hiperparámetros + sha256
  core/
    gate_adapter.py                   ← label_events_at_t0 (merge_asof)
    gate_target_free.py               ← persistencia, flip, corr(ancho)
    gate_incremental_vs_pctrv.py      ← nested partial-F vs pct_rv
    gate_recreate.py / generator / five_proposals  ← lab sintético previo
  integration/
    edgelab_gate_integration/
      column_map.py                   ← aliases NT8 → schema
      pipeline.py                     ← CLI end-to-end
      from_ticks.py                   ← ticks parquet → barras → labels
      paths.py, README.md
  research/
    H-ES-CTX-3_PREREGISTRO.md         ← DRAFT_READY_TO_FREEZE
  runs_examples/                      ← outputs de smoke (JSON/CSV chicos)
```

**No incluido (peso / licencia):** parquet Drive 6E (~45 MB).  
ID Drive: `15GW-D85ODGQbvvbGkGtqU1Vr09cjjAz0` (ticks 6E 09-26).

---

## 3. Roadmap (estado)

| Paso | Estado | Artefacto |
|------|--------|-----------|
| 1 Schema + adapter causal | HECHO (smoke) | `gate_adapter.py` |
| 2 Target-free | HECHO (demo) | `gate_target_free.py` |
| 3 Pre-registro CTX-3 | HECHO (plantilla) | `H-ES-CTX-3_PREREGISTRO.md` |
| 4 Incremental vs pct_rv | HECHO (demo) | `gate_incremental_vs_pctrv.py` |
| 5 model_id + checklist | HECHO | `gate_model_id_frozen.json` |
| Integración EdgeLab CLI | HECHO (fixture + 6E ticks) | `integration/` |

**Bloqueante real:** labels sobre **export de eventos ES/6E del lab** (no sintéticos) + Paso 2 con `OK_LOW_CORR` + congelar CTX-3 con estimando del acta viva.

---

## 4. Contrato EdgeLab (no negociable)

1. Indicador **exporta**; GATE **etiqueta offline**. **No** meter régimen en el `.cs`.
2. Join **as-of**: `feature_ts ≤ t0`. Fail-closed si no hay barra.
3. Sin outcomes en labels. Target-free **antes** de mirar AbsMagnitude / ticks_por_ancho.
4. Si `|corr(régimen, ancho_ticks)| ≥ 0.25` → **no congelar** CTX-3 (lección CTX-2 / fase sesión).
5. Holdout del lab **intacto**.
6. Proveniencia en cada corrida: `run_id`, `seed`, `model_id`, `commit`, `schema_version`.
7. Indicador de referencia con paridad Python: **BigTrap2Absorption v1.1.1** (`nt8/BigTrap2Absorption.cs`). HFTZones2 v2.3 alineado a `hftzones2.py`. Rama: `foundation/f0b-compatibility-probe`.

---

## 5. Cómo correr (sandbox / local)

```bash
# desde la raíz del unzip
export PYTHONPATH="$(pwd)/core:$(pwd)/integration:$PYTHONPATH"

# smoke fixture (aliases EdgeLab)
python -m edgelab_gate_integration.pipeline --fixture --out-dir runs_gate_labels

# con export real
python -m edgelab_gate_integration.pipeline \
  --events /path/to/TRAP_or_zones.csv \
  --bars /path/to/bars_1m.csv \
  --out-dir /path/to/EdgeLab/runs/gate_labels \
  --commit $(git -C /path/to/EdgeLab rev-parse --short HEAD)

# desde ticks (schema EdgeLab: ts_utc_ns, bid_ticks, ask_ticks, aggressor, ...)
python integration/edgelab_gate_integration/from_ticks.py
# (requiere edgelab_sample/sample.parquet o ajustar path)
```

Dependencias: `pandas`, `numpy`; para parquet: `pyarrow`.

---

## 6. Siguiente trabajo recomendado (Claude Code)

### Prioridad A — datos reales del lab
1. Ubicar export TRAP/zonas (BigTrap2Absorption) o sqlite oráculo en el worktree EdgeLab.
2. Barras 1m ES (o ticks → barras con `from_ticks.py` adaptado a ES).
3. Correr pipeline → `gate_labels_*.csv` + target-free JSON.
4. Verificar veredicto `OK_LOW_CORR` y cobertura ≥40 sesiones/celda si aplica.

### Prioridad B — CTX-3
1. Rellenar en `H-ES-CTX-3_PREREGISTRO.md` el **estimando primario** del acta viva.
2. Publicar MDE por celda (bootstrap de sesiones).
3. Pasar a `PREREGISTERED_READY_TO_RUN` solo con OK humano + Paso 2 limpio.
4. Ejecutar outcomes **una vez**; documentar cierre (no-edge aunque separe celdas).

### Prioridad C — incremental
1. Agregar `y_session` del estimando por sesión.
2. Correr `gate_incremental_vs_pctrv.py` con datos reales (no solo demo).
3. Reportar `INCREMENTAL_YES|NO` vs terciles `pct_rv`.

### No hacer
- Reabrir H-ES-CTX-2 a escondidas.
- Declarar edge desde GATE.
- Atención bi-dir en path de labels de producción.
- Fabricar oráculos de paridad NT8 (contrato `oracles/README.md`).

---

## 7. Alias de columnas export → GATE

| GATE | Alias aceptados |
|------|-----------------|
| event_id | zone_id, trap_id, EventId, id |
| t0 | t_start, bucket_start, StartTime, fill_time |
| session_id | trade_date, TradeDate, TradingDay, dia |
| ancho_ticks | width_ticks, WidthTicks, zone_width_ticks |
| symbol | Symbol, instrument |

---

## 8. Datos ya vistos en esta sesión

| Fuente | Contenido | Uso |
|--------|-----------|-----|
| Drive parquet `15GW-D85...` | Ticks **6E** 09-26 (~2.8M filas) | Pipeline validado; no ES |
| Yahoo ES=F | Rate-limited | No disponible en sesión |
| Databento / FirstRate | ES samples comerciales | Opción para ES 1m acotado |

---

## 9. Definición de “complemento aplicable”

GATE es aplicable en EdgeLab cuando:

1. Labels versionados sobre **eventos reales** del lab  
2. Target-free con corr(ancho) baja y cobertura reportada  
3. Entra a trial **pre-registrado** (CTX-3)  
4. (Opcional) Demuestra valor incremental vs `pct_rv`  

Hasta 1–3 en datos reales: especificación ejecutable, no aún research formal cerrado.

---

## 10. Contacto de diseño

Filosofía EdgeLab: causalidad estricta, anti-p-hacking, sesión como unidad de inferencia, costos primero, gauntlet (MCPT / PBO / DSR) solo si se gatean trades.

**Fin del handoff.**
