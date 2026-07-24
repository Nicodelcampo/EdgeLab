# Contrato de paridad NT8 ↔ Python — primer oráculo real: Gaps2

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md).

> Objetivo: producir el `EventLogPath` de **Gaps2** en NT8 sobre un rango
> idéntico al que corre el kernel Python, y pasar el gate **P2**:
> PASS = cero zonas huérfanas y cero discrepancias geométricas (en ticks).

## 1. Selección pre-registrada

| Ítem | Valor |
|---|---|
| Indicador | Gaps2 v2.0 (el MISMO .cs que exporta EventLogPath) |
| Instrumento/contrato | **6E 06-26** (contrato más denso: 5.56M ticks) |
| Dataset Python | `data/nt8/6E/6E_06-26_ticks.parquet` (F2, UTC verificado) |
| Rango UTC (2 sesiones CME completas consecutivas) | **2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z** (sesiones del mié 6 y jue 7 de mayo; CDT: abren 17:00 CT, cierran 16:00 CT) |
| Timeframe primario | **1 minuto** |
| Parámetros | defaults del kernel (tabla abajo) — NO cambiar ninguno sin re-registrar |
| Timezone del chart NT8 | la que tenga tu UI (ART); se pasa a la CLI como `--chart-tz America/Argentina/Buenos_Aires`. El matching de Gaps2 usa `unix_ms` (absoluto), así que la tz del chart solo afecta la columna legible `ts` |

Parámetros default (deben coincidir 1:1 con la UI del indicador en NT8):
`min_gap_ticks=5 · export_floor_ticks=2 · reopen_pause_minutes=60 ·
reopen_warmup_minutes=30 · atr_period=14 · vol_baseline_ticks=2000 ·
min_vol_baseline_samples=500 · partial_fill_pct=50 · reversal_confirm_ticks=2 ·
max_age_bars=2000 · max_logged_touches=20`

### Desviación del pre-registro — primer oráculo real ✅ PASS

El primer oráculo real NO fue el 06-26 de mayo de arriba, sino **6E 09-26**
(el contrato que estaba cargado con tick data completa en la instalación):

| Ítem | Valor |
|---|---|
| Oráculo | `oracles/Gaps2_6E_0926.csv` (export real, 1776 zonas) |
| Contrato · barras | **6E 09-26** · **1 minuto** |
| Ventana comparada (UTC) | **2026-07-13T22:00:00 → 2026-07-16T21:00:00** (borde de sesión CME) |
| Params | defaults salvo **`min_gap_ticks=2`** (declarados por la línea `# params` del CSV) |
| Dataset Python | `data/nt8/6E/6E_09-26_ticks.parquet` (cubre 2026-06-08 → 2026-07-21) |
| **Gate P2** | **PASS** — 1316/1316 zonas, 0 `MISSING_*`, 0 `GEOMETRY_DIFF`; 15 `MATURITY_TAIL` (cola de ventana, lifecycle no comparable) |

Motivo de la desviación: 6E 06-26 no tenía tick data cargada en esta
instalación; 6E 09-26 sí (mismo feed). `min_gap_ticks=2` en vez de 5 es solo el
umbral de **display** (para ver zonas en el chart); no afecta el export ni la
paridad (ver `nt8_bridge.md` "Dibujo ≠ export"). Evidencia completa (oracle
sha256, config_id, ventana, regla) en el `parity.json` de la partición del store.

## 2. Pasos en NT8 (tu parte)

1. Chart nuevo: **6E 06-26** (contrato individual, NO continuo ni rollover),
   **1 minuto**, con datos históricos de tick completos para el rango
   (el mismo feed del que salieron los `.Last.txt`).
2. Rango del chart: que cubra **desde antes del 2026-05-05 17:00 CT hasta
   después del 2026-05-07 16:00 CT** (dejá margen de 1 día a cada lado; el
   kernel Python recorta exacto por UTC, NT8 puede tener warmup extra — los
   eventos fuera de rango se excluyen del diff).
3. Aplicar **Gaps2 v2.0** con TODOS los parámetros en default (tabla arriba) y
   `EventLogPath = C:\ProyectosQuant\EdgeLab\oracles\Gaps2_6E_06-26_may.csv`
   (crear la carpeta `oracles\` si no existe).
4. Dejar que el indicador procese todo el histórico del chart (recalcular si
   hace falta: F5). Cerrar el chart o refrescar para que el log se flushee.
5. Verificar que el CSV tiene el header `event_seq,event_type,ts,unix_ms,...`
   y me avisás.

## 3. Corrida Python (mi parte, cuando exista el CSV)

```bash
.venv\Scripts\python tools\run_nt8_bridge.py ^
  --data data\nt8\6E\6E_06-26_ticks.parquet --contract "6E 06-26" ^
  --start-utc 2026-05-05T22:00:00 --end-utc 2026-05-07T21:00:00 ^
  --bars time:1 --indicator Gaps2 ^
  --chart-tz America/Argentina/Buenos_Aires ^
  --oracle Gaps2=oracles\Gaps2_6E_06-26_may.csv ^
  --out runs\nt8_bridge\parity_gaps2_0626_may
```

## 4. Gate P2 (pre-registrado)

- **PASS**: 0 `MISSING_IN_*`, 0 `GEOMETRY_DIFF` (geometría exacta en ticks).
- **WARN**: solo `TIMESTAMP_DIFF` ≤ 60 s, `STATE_ORDER_DIFF`, `FEATURE_DIFF`
  (touches) o `CALIBRATION_DIFF` declarado → se revisan una por una en el visor
  antes de promover.
- **FAIL**: zonas faltantes o geometría distinta → el kernel NO entra a
  vectorbt; se depura con el visor (modo "solo huérfanas") y se re-corre.

Exclusiones declaradas del diff (documentadas en `nt8_bridge.md`):
`SESSION_END` si el chart NT8 sigue vivo (no hubo OnTermination), y eventos
NT8 anteriores al inicio del rango Python (warmup del chart).

### Regla de frontera de madurez (pre-declarada)

NT8 exporta más rango que la ventana Python (warmup a ambos lados). Las zonas
creadas a **menos de `max_age_bars` del cierre de la ventana** no pueden
completar su ciclo de vida dentro de la ventana común Python∩NT8: Python las
corta (SESSION_END) y NT8, que sigue procesando, las expira/invalida/toca más.
Regla del matcher (`parity.match_zones(maturity_frontier_ms=...)`):

- **Geometría (top/bottom en ticks) + timestamp de creación**: se comparan para
  el **100%** de las zonas, maduras e inmaduras.
- **Estado final + touches (lifecycle)**: se comparan **solo para zonas maduras**
  (`created_ms <= cierre_barra[n-1-max_age]`). Para las inmaduras se registra
  `MATURITY_TAIL` (informativo, no WARN/FAIL) con lo que se suprimió.

**No es ampliar tolerancia**: es una regla de ventana con principio (la simétrica
del warmup inicial). Una zona **madura** con `STATE_ORDER_DIFF`/`FEATURE_DIFF`
sigue siendo WARN/FAIL — hay un test adversarial que lo fija.

**Prohibido:** generar un CSV NT8 ficticio o editado. El oráculo es el export
real del indicador corriendo en NT8. Sin ese archivo, ningún kernel se declara
"paridad real confirmada".

**Versión de los `.cs`:** los oráculos válidos deben generarse con la versión
**190ed59 o posterior** de los `.cs` (en particular `aVolCellPOI2.cs` reescrito a
subserie 1-tick, sin barras Volumetric nativas de OrderFlow — un solo motor de
footprint, idéntico al port Python). Cualquier export de aVolCellPOI2 generado
con la versión Volumetric anterior **NO es válido** como oráculo y debe
regenerarse. Registrar en cada oráculo la rev de los `.cs` usada.

## 5. Protocolo para los kernels siguientes (F5+ — integrados)

El mismo contrato aplica a VolTicksPOC2, BigTrap2, HFTZones2 y aVolCellPOI2 (los
4 ya integrados: kernel + smoke + P1A real + soporte CLI/visor + parser de
oráculo). Un oráculo por indicador y por configuración paramétrica que se quiera
promover. Requisitos específicos de rango/historia por kernel:

| Kernel | Barras | Requisito de rango / historia para el oráculo NT8 |
|---|---|---|
| **VolTicksPOC2** | time:N | ≥ `avg_period` barras para baseline y ≥ `min_ratio_samples` ratios antes de detectar; export continuo `OBS` desde `export_floor_percentile`. |
| **BigTrap2** | **tick:N** (o time) | el `--bars tick:N` debe coincidir con la resolución del chart NT8; export **pipe** (`seq|iso|type|payload`). Cada resolución es un oráculo distinto. Barra 0 descartada. |
| **HFTZones2** | time:N (tick-driven) | el rango DEBE arrancar en **borde de sesión** con **≥1 sesión completa previa** para tener calibración congelada; si no, la 1ª sesión sale `CALIBRATION_PENDING` y no crea zonas. Feriados → `CALIBRATION_DIFF` (WARN). |
| **aVolCellPOI2** | time:N | pre-registrar que el chart NT8 tenga **≥ `lookback_sessions` + `min_sessions` sesiones** cargadas (con defaults: ≥ 35 sesiones ≈ 7 semanas) antes del rango a comparar; sobre historia pobre el kernel produce 0 zonas (correcto). |

**Regla común:** el rango Python (`--start-utc/--end-utc`), los parámetros, la
timezone del chart (`--chart-tz`) y la resolución de barras deben coincidir 1:1
con el indicador corriendo en NT8. Sin el CSV real, ningún kernel se declara
"paridad real confirmada" (§4).

## 6. Pre-registro de oráculos — campaña mínima (F7)

Generar en una sola sesión de NT8 (rev `.cs` **190ed59+**; registrar la rev en
cada CSV). Contrato base **6E 06-26** (5.56M ticks). Timezone del chart: la de tu
UI; pasarla a la CLI como `--chart-tz`. Matrices de ramas en
`docs/parity_coverage/`. Todos con defaults salvo lo indicado.

### Rango corto (2 sesiones CME) — reutiliza el de Gaps2
`2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z`, `--bars time:1` (salvo BigTrap2 O2).

| Oráculo | Params NT8 (no-default) | Bars | EventLogPath sugerido |
|---|---|---|---|
| **Gaps2 O1** (ya en §1) | defaults | time:1 | `oracles\Gaps2_6E_06-26_may.csv` |
| **Gaps2 O2** min_gap denso | MinGapTicks=3, ExportFloorTicks=2 | time:1 | `oracles\Gaps2_dense_6E_0626.csv` |
| **VolTicksPOC2 O1** | defaults | time:1 | `oracles\VolTicksPOC2_6E_0626.csv` |
| **VolTicksPOC2 O2** FirstTouch | InvalidationMode=FirstTouch | time:1 | `oracles\VolTicksPOC2_firsttouch_6E_0626.csv` |
| **BigTrap2 O1** Diagonal | defaults | time:1 | `oracles\BigTrap2_diag_time1_6E_0626.csv` |
| **BigTrap2 O2** SameLevel | ImbalanceMode=SameLevel | **tick:25** | `oracles\BigTrap2_samelevel_tick25_6E_0626.csv` |
| **BigTrap2 O3** wick off | UseWickFilter=false | time:1 | `oracles\BigTrap2_nowick_time1_6E_0626.csv` |
| **HFTZones2 O1** adaptativo | defaults (arrancar en borde de sesión) | time:1 | `oracles\HFTZones2_adaptive_6E_0626.csv` |
| **HFTZones2 O2** manual | AdaptiveMode=false (params manuales default) | time:1 | `oracles\HFTZones2_manual_6E_0626.csv` |

> Para HFTZones2 el chart debe cubrir ≥1 sesión CME completa ANTES del
> 2026-05-05 17:00 CT (para calibrar) — dejar margen de 2 días a la izquierda.

### Rango largo (≥ 7 semanas) — aVolCellPOI2
El chart NT8 debe tener **≥ 35 sesiones** cargadas antes del rango a comparar.
Rango de comparación sugerido: `2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z`
(las mismas 2 sesiones), con historia cargada desde **2026-03-09** (inicio del
contrato). `--bars time:1`.

| Oráculo | Params NT8 (no-default) | EventLogPath sugerido |
|---|---|---|
| **aVolCellPOI2 O1** | defaults (SessionRelative/TotalVolume/Quantile) | `oracles\aVolCellPOI2_default_6E_0626.csv` |
| **aVolCellPOI2 O2** WallClock/AbsDelta | BucketAnchor=WallClock, DetectionSource=AbsDelta | `oracles\aVolCellPOI2_wallclock_absdelta_6E_0626.csv` |

Corrida Python (mismo patrón que §3, ajustando indicador/params/bars/oráculo).
`parity_covered` de una config se asigna solo cuando TODAS las ramas que activa
(ver `docs/parity_coverage/<kernel>.md`) tienen un oráculo PASS.

## 7. Próxima tanda de oráculos — 6E 09-26 (contrato ya cargado, tick data OK)

Preferido sobre §6 (06-26 no tenía tick data en esta instalación). Todos sobre
**6E 09-26**, dataset `data/nt8/6E/6E_09-26_ticks.parquet` (cubre 2026-06-08 →
2026-07-21). Rev `.cs` **190ed59+**. Ventana corta reutilizable (borde de sesión
CME): **2026-07-13T22:00:00 → 2026-07-16T21:00:00 UTC**.

Pasos NT8 comunes: chart 6E 09-26, Days to load ≥ 10 (para aVolCellPOI2 ≥ 40),
setear el `EventLogPath` del indicador, F5 para recalcular, cerrar/refrescar para
flushear. Dejar los CSV en `E:\EdgeLab\oracles\`.

| Oráculo | Bars | Params no-default | EventLogPath | Ventana Python |
|---|---|---|---|---|
| **Gaps2 25t** | **25 Tick** | `min_gap_ticks=2` | `Gaps2_6E_0926_tick25.csv` | 07-13→07-16 |
| **VolTicksPOC2** | 1 Minute | defaults | `VolTicksPOC2_6E_0926.csv` | 07-13→07-16 |
| **VolTicksPOC2 FirstTouch** | 1 Minute | `InvalidationMode=FirstTouch` | `VolTicksPOC2_ft_6E_0926.csv` | 07-13→07-16 |
| **BigTrap2 Diagonal** | 1 Minute | defaults | `BigTrap2_diag_time1_6E_0926.csv` | 07-13→07-16 |
| **BigTrap2 SameLevel** | **25 Tick** | `ImbalanceMode=SameLevel` | `BigTrap2_same_tick25_6E_0926.csv` | 07-13→07-16 |
| **HFTZones2 adaptativo** | 1 Minute | defaults (arranca en borde de sesión) | `HFTZones2_adaptive_6E_0926.csv` | 07-13→07-16 |
| **HFTZones2 manual** | 1 Minute | `AdaptiveMode=false` | `HFTZones2_manual_6E_0926.csv` | 07-13→07-16 |
| **aVolCellPOI2** | 1 Minute | defaults (Days to load ≥ 40) | `aVolCellPOI2_6E_0926.csv` | **07-19→07-21** |

- **Gaps2 25t**: el `--bars tick:25` de la corrida Python debe coincidir; es un
  `config_id` distinto al de 1 minuto (el `bar_key` entra a la identidad).
- **HFTZones2**: la ventana arranca en 07-13T22:00 (apertura CME) y trae ≥1
  sesión previa cargada → calibración congelada antes de las detecciones.
- **aVolCellPOI2**: necesita ~7 semanas de historia; cargá desde el inicio del
  contrato (06-08) y comparamos las 2 últimas sesiones del parquet (07-19→07-21).
  Requiere el `.cs` reescrito a subserie 1-tick (rev 190ed59+).

Cada uno: me pasás el CSV y corro `run_nt8_bridge.py … --oracle <ind>=<csv>
--zone-store runs/nt8_bridge/store` (con la frontera de madurez automática) →
`parity_report.json` + gate + evidencia en el store. La ventana corta 07-13→07-16
ya validó Gaps2 (PASS); el resto usa la misma para comparabilidad.
