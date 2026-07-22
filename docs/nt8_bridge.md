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
| HFTZones2 / VolTicksPOC2 / aVolCellPOI2 / BigTrap2 | pendiente (F5+, mismo protocolo) | — | — | — |

## Límites conocidos (declarados)

- Sesiones CME sin feriados → diferencias en feriados = `CALIBRATION_DIFF`.
- Footprint reconstruido: ticks con ts == cierre de barra pueden caer en barras
  distintas que NT8 (corte canónico `[inicio, fin)`).
- Kernels en Python puro: correctitud primero; kernels Numba = fase posterior.
