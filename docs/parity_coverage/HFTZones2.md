# Cobertura de paridad — HFTZones2

## ✅ PARIDAD AFIRMADA — v2.3, 2026-07-27

| | |
|---|---|
| oráculo | `oracles/HFTZones2_adaptive_6E_0926_v23.csv` |
| `.cs` | v2.3, sha256 `9bdbcc8108d8dc32…` |
| resultado | **PASS — 1599 / 1599, 0 diffs** |
| preflight de calendario | **OK — 11 sesiones NT8 = 11 Python** |
| tolerancias | **intactas** |

El `.cs` había quedado en v2.2 (con `inside` comparando `double`) mientras el
kernel Python ya era v2.3 en enteros: los dos lados estaban desalineados **por
construcción**. Corregido y validado.

Requirió **warmup real**: con la ventana de datos recortada a la de comparación
el kernel daba 947 de 1599 zonas, porque su calibración adaptativa se congela
por sesión y necesita la sesión anterior completa. Ver la regla "ventana de datos
≠ ventana de comparación" en el contrato.

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

## RESULTADO del primer oráculo (2026-07-25) — **WARN**

Oráculo: `oracles/HFTZones2_adaptive_6E_0926.csv`, `.cs` **v2.1**
(`engine=…_integer_grid`), defaults, `adaptive_mode=true`.

### Primer intento: FAIL por error MÍO de ventana, no del kernel

Corrí la ventana estándar 07-13T22:00 → 07-16T21:00 UTC y dio **FAIL** con 652
`MISSING_IN_PYTHON`. Causa raíz inmediata: **violé el requisito pre-declarado en
§5** ("el rango DEBE arrancar en borde de sesión con **≥1 sesión completa
previa**"). Python emitió `CALIBRATION_PENDING` el 13/07 19:00 y **no creó
ninguna zona en toda su primera sesión**, mientras NT8 venía calibrado desde el
12/07 porque el chart cargaba desde el 09/07.

Lo delataba el propio reporte: `MISSING_IN_NT8 = 0` y `GEOMETRY_DIFF = 0` — todo
lo que Python produjo, matcheó. No era un desacuerdo, era muestra faltante.

### Segundo intento: warmup correcto ⇒ WARN

Dándole a Python el mismo arranque que tuvo NT8 (`--start-utc
2026-07-09T22:00:00`):

```
py_zones 2111 | nt8_zones 2111 | matched 2111
MATCHED 2029 · FEATURE_DIFF 82 · MATURITY_TAIL 74
MISSING_IN_PYTHON 0 · MISSING_IN_NT8 0 · GEOMETRY_DIFF 0
gate: WARN
```

**Geometría y ciclo de vida exactos**, conteo de zonas idéntico. Es un resultado
fuerte para un primer oráculo, y valida el fix simétrico v2.1 (grilla entera en
retroceso y altura) aplicado en el `.cs` y el kernel a la vez.

### Causa raíz PENDIENTE — los 82 `FEATURE_DIFF` de `touches`

Caracterización hecha (no es todavía la causa):

| medición | valor |
|---|---|
| zonas afectadas | 82 de 2111 (**3,9 %**) |
| dirección | **simétrica**: Python cuenta más en 37, NT8 en 45 |
| ¿truncamiento por `max_logged_touches=20`? | **NO** — 0 casos con `nt8 == 20` |
| \|delta\| | mediana 3, máximo 30 |
| delta de exactamente 1 toque | 24 de 82 |

La simetría descarta un sesgo sistemático, y la ausencia de casos en el tope de
20 descarta la hipótesis del truncamiento del export. Queda una diferencia
semántica real en **cuándo se cuenta una época de toque** en un indicador
tick-driven.

### CAUSA RAÍZ ENCONTRADA (2026-07-25) — no es el conteo de toques

La evidencia directa la dio comparar los timestamps de `ZONE_TOUCHED` de una zona
afectada:

```
Z000127   NT8 = 32 toques      Python = 6
  los 6 primeros coinciden AL MICROSEGUNDO; Python simplemente deja de contar.
```

Misma geometría, misma creación. **Python no cuenta distinto: deja de contar
antes, porque invalida la zona antes.**

| | |
|---|---|
| zonas cerradas en ambos lados | 2.078 |
| con el **mismo** timestamp de cierre | 1.890 (**91,0 %**) |
| con timestamp distinto | **188 (9,0 %)**, todas `close_through` |
| dirección | **Python cierra primero, siempre** |

La condición es **idéntica carácter por carácter** en los dos lados
(`price <= z.Lower - PenetrationTicks * TickSize`). El problema es la
**aritmética**: es la **tercera aparición de la familia de AUDIT-001**.

- NT8 construye `z.Lower` desde `_swL`, que es el `double` **del feed**.
- Python lo construye desde `st["swl"] = pticks × tick_size`, **reconstruido**.
- Los dos difieren en 1 ULP en el **24,3 %** de los niveles del 6E, y —medido—
  **el del feed está SIEMPRE por debajo** (1.215 casos por debajo, **0** por
  encima).

Como el umbral es `borde − penetration × tick`, el de Python queda 1 ULP **más
arriba**, así que su condición `price <= umbral` se cumple **antes**. Predicción
direccional: Python invalida primero y NT8 nunca. Verificado: 24,3 % de los
niveles con Python más arriba, **0 %** al revés — y en el oráculo, las 188
diferencias van todas en esa dirección.

**Corrección a AUDIT-001:** esa auditoría marcó las comparaciones de borde de
zona como riesgo **NULO** razonando que "ambos operandos son precios de grilla
construidos igual en los dos lados". **Era falso** para HFTZones2: un lado usa el
feed y el otro el reconstruido. La auditoría cubrió el retroceso y la altura pero
**no** el borde de zona ni el umbral de penetración.

**No se aplica ningún fix**: es un cambio de semántica en ambos lados y requiere
OK de Nico, igual que los dos anteriores de esta familia. Hasta entonces
HFTZones2 **no** pasa a `parity_exact` y no puede sembrar cobertura.
