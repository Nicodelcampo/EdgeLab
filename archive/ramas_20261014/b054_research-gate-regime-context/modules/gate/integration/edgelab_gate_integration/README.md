# EdgeLab ↔ GATE integration

Cableado del complemento GATE al contrato EdgeLab:

**indicador exporta → GATE etiqueta en t0 → trial pre-registrado (CTX-3)**

## Instalación / path

Desde `artifacts/`:

```bash
python -m edgelab_gate_integration.pipeline --fixture
```

Con datos reales:

```bash
python -m edgelab_gate_integration.pipeline \
  --events /path/to/EdgeLab/export_zonas.csv \
  --bars /path/to/bars_with_features.csv \
  --out-dir /path/to/EdgeLab/runs/gate_labels \
  --commit $(git rev-parse --short HEAD)
```

## Alias de columnas (export NT8 / research)

| GATE | Alias aceptados |
|------|-----------------|
| event_id | zone_id, trap_id, EventId, id |
| t0 | t_start, bucket_start, StartTime, fill_time |
| session_id | trade_date, TradeDate, TradingDay, dia |
| ancho_ticks | width_ticks, WidthTicks, zone_width_ticks |
| symbol | Symbol, instrument |

## Salidas

- `gate_labels_{run_id}.csv` — schema v1
- `gate_integration_{run_id}.json` — proveniencia + target-free (sin outcomes)

## Formal vs fixture

- `--fixture`: alias EdgeLab sintéticos (smoke de integración).
- Producción: pasar barras con **régimen ya detectado** por el motor GATE causal (`model_id` congelado); si no hay `regime`, el pipeline usa proxy por cuantiles solo para cableado.

## Relación con el roadmap

| Paso | Uso aquí |
|------|----------|
| 1 | `normalize_events` + `label_events_at_t0` |
| 2 | `target_free_report` embebido en el artefacto |
| 3 | Labels listos para poblar CTX-3 |
| 4 | CSV de labels + y_session del lab → `gate_incremental_vs_pctrv` |
| 5 | `--model-id` default = frozen id |
