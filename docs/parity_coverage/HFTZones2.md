# Cobertura de paridad — HFTZones2

Oráculos pre-registrados: **O1 adaptativo** (default), **O2 manual**
(`adaptive_mode=false`). Especificación en
`../nt8_indicator_parity_contract.md` §6. El rango DEBE arrancar en borde de
sesión con ≥1 sesión completa previa (calibración congelada); feriados →
`CALIBRATION_DIFF` (WARN).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `calibration_mode` | adaptive_mode | O1 (adaptive), O2 (manual) | pendiente |
| `calibration_adaptive` | q_predator, q_ultra, q_max_avg, pause_mult, total_ms_mult, vol_mult_median_tick, pause_exclude_ms, min_calib_samples, calib_sample_cap | O1 | pendiente |
| `calibration_manual` | manual_predator_ms … manual_min_total_vol | O2 | pendiente |
| `streak_structure` | min_pasos, min_absorb_pasos, detect_absorb, fallos_tolerados | O1 | pendiente |
| `sweep_vs_absorb` | min_sweep_ticks | O1 | pendiente |
| `retro` | use_relative_retro, retro_floor_ticks, retro_pct_height | O1 | pendiente |
| `geometry` | zone_height_ticks | O1 | pendiente |
| `export_floor` | min_export_valid_steps | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode, penetration_ticks | O1 | pendiente |
| `lifecycle_max_touches` | max_touches | O1 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |
| `touch_logging` | max_logged_touches | O1 | pendiente |

O1 cubre la calibración adaptativa; O2 cubre el camino manual (que O1 nunca
ejercita, `adaptive_mode` distinto).

## Pre-registro del PRIMER oráculo (2026-07-25) — exige `.cs` v2.1

**Sin oráculo previo.** El store tiene **0 particiones de HFTZones2**, así que no
hay nada que quede no comparable por el fix v2.1 (verificado).

**Requisito bloqueante:** el `.cs` debe ser **v2.1** (grilla entera de ticks en
retroceso y altura) y el kernel debe llevar el **fix espejo** ya aplicado. Un
oráculo generado con el `.cs` v2.0 se compararía contra un Python distinto y
divergiría por construcción — en el 5,0 % de los niveles de precio en la rama del
piso y el 22 % en la porcentual (medido, ver `../audits/AUDIT-001_…md`).

| Campo | Valor pre-registrado |
|---|---|
| Indicador | **HFTZones2 v2.1** — verificar `version=2.1` en la línea `# meta` del CSV |
| `.cs` canónico | `nt8/HFTZones2.cs`, sha256 `b8c8214cb1bbd203876886efd325e23617ec99202576dbb590091e80c77a5c6e` (sin la región generada) |
| Chart | 6E **09-26**, **1 Minute** (`--bars time:1`) |
| Params | **defaults** (`adaptive_mode=true`) ⇒ este export es **O1** |
| Requisito de rango | arrancar en **borde de sesión** con **≥1 sesión completa previa**; sin eso la 1ª sesión sale `CALIBRATION_PENDING` y no crea zonas (§5 del contrato) |
| `EventLogPath` | archivo **nuevo** (el `.cs` abre en modo append; nunca reutilizar uno existente) |
| Gate exigido | P2 según §4, **sin relajar tolerancias** |

Orden respecto de los otros exports: **BigTrap2 v2 va primero** (valida la
predicción `PRED-001` bit a bit); HFTZones2 v2.1 va después. `VolTicksPOC2` y
`aVolCellPOI2` no cambiaron de código y pueden salir en la misma sesión.
**`Gaps2` no se toca**: es la referencia que ya dio 1316/1316.
