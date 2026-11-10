# Pre-registro Formal: Campaña `HFT-GC-P10-R` y Almacén Target-Free `ZONAS_HFTGCP10_GC` (2026-11-05)

- **Estado:** VIGENTE (congelado antes de lanzar en Kaggle sobre `GC`).
- **Indicador NT8 de referencia:** `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTZonesGCClusterP10.cs` (`version=1.0.0`).
- **Motor causal Python/Numba:** [`edgelab/bridge/indicators/hft_gc_cluster_p10.py`](file:///e:/EdgeLab-port/edgelab/bridge/indicators/hft_gc_cluster_p10.py) (paridad 100% certificada contra SQLite NT8 `hft_logger_gc_cluster_p10.sqlite`: `0` discrepancias en `1.224` zonas, `124` eventos de `Cluster P10`, `POC` y `1.223` resoluciones de alejamiento).
- **Experimento del embudo:** [`edgelab/research/hft_gc_cluster_p10.py`](file:///e:/EdgeLab-port/edgelab/research/hft_gc_cluster_p10.py).
- **Campaña:** [`config/autopilot/grillas/campanas/HFT-GC-P10-R.json`](file:///e:/EdgeLab-port/config/autopilot/grillas/campanas/HFT-GC-P10-R.json) (`n_celdas_por_canal = 9.720`, `"estadistico": "R"`).
- **Almacén Target-Free en Kaggle:** `almacen-zonas-hftgcp10-gc` (`INDICADOR=HFTGCP10`, `INSTS=GC`, `2025-07-01..2026-09-30`, generando `ZONAS_HFTGCP10_GC.parquet` y `ZONAS_HFTGCP10_CLUST_GC.parquet`, listo también para el filtro posterior de barreras HFT).

---

## 1. Justificación Económica y Microestructural

En el futuro de Oro COMEX (`GC`), las ráfagas agresivas sub-segundo (`MaxAvgMs <= 21,8 ms`, `MaxTotalMs <= 212 ms`, `VolRate >= 197 cts/s`) dejan dos huellas microestructurales observables sin mirar retornos futuros:
1. **Zonas con Borde Gris + Flecha (`AlejamientoTicks = 20`):** cuando el precio se aleja `20 ticks ($2,00)` desde una zona HFT sin haber comerciado ambos bordes ni haber revertido en `V` (`>= 50%`), revela desequilibrio neto no mitigado. Se contrastan dos hipótesis opuestas:
   - `B2_RETEST_GRIS`: la zona actúa como Order Block institucional en su primera mitigación (`Limit` en el borde cercano).
   - `B1_FLECHA_CONT`: el quiebre de `20 ticks` arrastra impulso inmediato desde el `Open` de la vela siguiente (`AwayConfirmedBar + 1`).
2. **Clusters por Compresión Vertical Relativa (`P10` de los 100 grupos previos de 4 zonas HFT vigentes):** cuando `>= 4` zonas HFT activas (en una ventana práctica de `360 min` de reloj de mercado activo, descontando pausas `> 5 min`) se apilan en una altura inferior al `P10` de los `100` grupos mínimos previos de 4 zonas, marcan un nodo denso de liquidez y absorción institucional:
   - `A1_CLUSTER_FADE`: al primer cierre M1 fuera de la envolvente `[lo, hi]` sin escape desbocado (`<= 4 * max(H, 10 ticks)`), reversión hacia el equilibrio (`POC` gravitacional).
   - `A2_CLUSTER_PULLBACK`: tras confirmar un escape limpio de `20 ticks` fuera del cluster, orden `Limit` en el borde cercano operando al cluster como soporte/resistencia.

---

## 2. Partición Temporal, Costos y Embudo Completo

- **Dataset:** `nicolasbuttaro/edgelab-liquid-ticks-20261014` (`data/GC_ticks.parquet`, `273` sesiones aprobadas `2025-08-05..2026-09-30`).
- **Descubrimiento (`DESC`):** `2025-08-05 .. 2026-03-31` (con `45` días de calentamiento previo de ticks para el historial `P10` y vigencia de zonas).
- **Réplica / `PISTAS` / `OOS`:** `2026-04-01 .. 2026-09-30` (controlado por `LORD++` en el libro canónico).
- **Holdout sellado (`ACTA -> CONTEO -> HOLDOUT`):** `>= 2026-10-01` (`N_fijo = 150` operaciones, `nicolasbuttaro/edgelab-holdout-sellado`).
- **Fricción canónica de `GC` (`edgelab.costos`):** `0,605 puntos` (`6,05 ticks = $60,50` ida y vuelta base) y `0,805 puntos` (`8,05 ticks` escenario adverso).
- **Exclusión de eventos macro Tier-1:** sin entradas en `±5 min` y salida forzada previa a datos Tier-1 (`lineas_salida`).

---

## 3. Grilla Compacta en `R` (`9.720` celdas por canal)

Siguiendo [`PROGRAMA_R.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/PROGRAMA_R.md) y [`RESULTADO_CONTEXTO_Y_VETOS_R_20261104.md`](file:///e:/EdgeLab-port/docs/research/programa_r_20261103/RESULTADO_CONTEXTO_Y_VETOS_R_20261104.md):
- `mecanismo` (`4`, `grupo`): `B2_RETEST_GRIS`, `B1_FLECHA_CONT`, `A1_CLUSTER_FADE`, `A2_CLUSTER_PULLBACK`.
- `tipo_zona` (`2`, `eq_any` → `3` niveles): `Predator/Fast`, `Absorb/Ultra`, `Cualquiera`.
- `estructura` (`2`, `eq_any` → `3` niveles): zona aislada (`4z`) vs en `Cluster P10` (`>= 5z`), `Cualquiera`.
- `franja_ny` (`4`, `eq_any` → `5` niveles): `Asia (18:00–03:00 ET)`, `Londres (03:00–08:20 ET)`, `COMEX Mañana (08:20–12:00 ET)`, `NY Tarde (12:00–16:30 ET)`, `Cualquiera`.
- `fuerza_vol` (`3` cuantiles E0, `ge` → `3` niveles): volumen HFT relativo al volumen M1 reciente de la sesión.
- `compresion` (`3` cuantiles E0, `le` → `3` niveles): altura de zona/cluster normalizada por `ATR14` de sesión.
- `ejecución` (`6` niveles): stops `S1_ZONA` (`+6 ticks`, piso `15 ticks`) y `S3_ATR` (`+max(16 ticks, 0,50·ATR14)`, piso `24 ticks`) × objetivos `1,5R`, `2,0R`, `3,0R`.

---

## 4. Criterio de Refutación

La campaña queda refutada si:
1. Ninguna celda sobrevive al `FDR q <= 0,10` en `DESC` ni confirma en `PISTAS` (`LORD++`) sobre `2026-04-01..2026-09-30`;
2. Las candidatas nominadas fallan `INTEGRIDAD` (placebo o latencia de `+1` vela M1) o `TOPES`;
3. `OOS` o el `HOLDOUT` sellado (`>= 2026-10-01`, `N = 150`) arrojan media neta en `R <= 0` con potencia declarada.

