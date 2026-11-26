# Campaña Post-IL `FUNDEDSYNCSTACK` en Unidad R y Variantes Estructurales (HOLDOUT-A4 / HOLDOUT-A5)

Estado: PRE-REGISTRO — se commitea antes de contar pruebas y antes de correr.
Fecha: 2026-11-22
Familia / módulo: `FUNDEDSYNC`
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
- **Etapa del embudo:** EF2 (re-medición diagnóstica en M1 real de futuros tras arreglos IL) y EF3 (descubrimiento/mejora en `DESC` A5 + transferencia multi-índice + confirmación congelada en `REP` A5).
- **Herramienta:** `tools/fundedsync_post_il_cadena.py` (ejecuta `edgelab.research.fundedsyncstack` perfil `il_fabrica`, fricción canónica `edgelab/costos.py`, partición `edgelab/holdout.py`, diagnóstico K55/K56 `edgelab/research/diagnostico_grilla.py`, compuerta K51 `registro_global.exigir_contada` y puerta 4 capas `edgelab/research/puerta_corrida.py`).
- **Presupuesto global (K51):** **`85` pruebas** (`14` Bloque A + `14` B1 + `12` B2 + `21` B3 + `24` B4 transferencia/REP).

Antecedentes: RESULTADO_CADENA.md (CFD 2026-11-16, T/Z/R pistas y S/W/A1/Q/V refutadas pre-IL), RESULTADO_MECANISMOS.md (salidas técnicas regalan ganancia; T+Z+R descorrelacionada), RESULTADO_TANDA2.md (L1 confirma EOD sobre S y W en ES/YM/RTY pero fricción limita W; L2 T+Z+R c/ stop ATR), transfer_rty_emd_20261119/RESULTADO.md (Z RTY+EMD +0,146 R p=0,085), AUDITORIA_PARIDAD_IL_20261120.md (6 bugs IL corregidos en V, Q, E, A1/A20/S, N, T y verificación 1:1 CT en NT8), PARIDAD_VENDEDOR_SWEEP_20261121.md (perfil separado `vendedor_calibrado` en O/S/W/C; vendedor cerró imagen ~2026-09-01). Factores en `FACTORES.jsonl`: `F-FUNDEDSYNC-SIN-VENTAJA`, `F-SALIDA-TECNICA-REGALA-LA-GANANCIA`, `F-AUDITORIA-UNIDADES-Y-VIEJAS`, `F-FRICCION-RELATIVA-REGIMEN`, `F-LUCID-SIN-OVERNIGHT`, `F-FRECUENCIA-POR-SELECCION`, `F-FRECUENCIA-PROP-R-POR-MES`, `F-Z-TRANSFER-RTY`, `F-R-ATRPHASE-EN-R`.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27, K32, K33, K40, K48, K51, K55, K56, HOLDOUT-A4/A5).

Cambio respecto a falla previa: respecto de `F-FUNDEDSYNC-SIN-VENTAJA` (medición 2026-11-16 sobre CFD Dukascopy en puntos planos con código IL incompleto), esta campaña introduce cuatro cambios estructurales explícitos: (1) usa los 6 arreglos forenses IL del commit `7965e7fb`, incluyendo `V_BlockedEntryHour` en CT en `V` (que cambió `V` de ~+1.900 a +4.942 pts netos en NQ 2021–2026) y `point_value` MNQ `2.0` en `Q`; (2) evalúa todos los módulos sobre datos reales M1 de futuros NT8 (`NQ, ES, YM, RTY, EMD`) y en unidad `R` sobre riesgo inicial o stop de catástrofe en `ATR20` con costos canónicos mini y micro (`edgelab/costos.py`), evitando comparar épocas en puntos fijos; (3) incorpora el corte real de desarrollo del vendedor al **2026-09-01** leyendo descriptivamente la ventana `2026-09-01 → 2026-09-30` (`POST_1SEP`, pre-holdout A4) por separado; y (4) en el Bloque B somete variantes estructurales (salida EOD + stop duro amplio sin salidas técnicas rápidas en S/W/A20/N y escalado ATR20/RR en Q/F/C/E/V) bajo partición estricta **HOLDOUT-A5** (`DESC` -> `REP`), nunca `vendedor_calibrado`.

Potencia previa: sobre `NQ` M1 real (`2008-01-01 → 2026-09-30`, ~18,7 años / 225 meses), los módulos operan entre `~2` y `~110` ops/mes (`n ≈ 400–8.000` en total; en partición `DESC` A5 de 7/12 meses `n ≈ 230–4.500`), lo que da MDE al 80% (`α=0,05`) entre **`0,04 R` y `0,18 R`** según frecuencia; excepciones de baja frecuencia (`Z`, `R`, `C`: `2–5 ops/mes`) quedan declaradas explícitamente para evaluación conjunta en frecuencia multi-instrumento (`F-FRECUENCIA-MINIMA`, `F-FRECUENCIA-PROP-R-POR-MES`). La subventana `POST_1SEP` (`2026-09-01 → 2026-09-30`, ~21 sesiones) acumula ~`2–90` ops según módulo y **se declara solo descriptiva** (sin potencia inferencial ni decisión aislada; en A5 además `2026-09` es mes `HOLDOUT`, por lo que Bloque B jamás toca `2026-09`).

Diagnóstico de mecanismo: toda grilla de Bloque B (`B1_V`, `B2_EOD`, `B3_Q`, `B3_F`, `B3_C`, `B3_E`) pasará obligatoriamente por `edgelab.research.diagnostico_grilla.diagnostico()` (operaciones por celda, degeneradas `< max(30, 15% mediana)`, `numero_efectivo` por autovalores de correlación mensual, `perillas_inertes` y `Spearman(ops, R)`) y `episodios()` (media neta excluyendo los 3 peores y los 3 mejores meses) en `DESC` antes de elegir finalistas para `REP` o transferencia, pegando sus líneas verbatim en `RESULTADO.md` (K55/K56).

Costos estimados declarados (K33): `NQ`, `MNQ`, `ES`, `MES`, `YM`, `MYM` y `RTY` usan exclusivamente spreads y comisiones medidos en `config/costos/costos_canonicos.json`; `EMD` utiliza spread ESTIMADO (2 ticks = `0,20` pts, fricción base `$43,78` / `0,4378` pts) únicamente dentro de `costos.estimados_permitidos("docs/research/fundedsync_post_il_20261122/PREREGISTRO.md")`, reportado por separado de los activos con spread medido.

## Justificación económica
1. **Bloque A (auditoría real post-IL y corte 2026-09-01):** Los arreglos IL modificaron sustancialmente el comportamiento de `V` (`V_BlockedEntryHour` CT), `Q` (escala MNQ real), `S/A20/E/N` (`EnforceDailyFuturesClose` `15:44–17:01 CT`) y `T` (`same_et_date`). Re-medir la cartera completa de fábrica en `R` (bruto y neto mini/micro) sobre 18 años de futuros reales permite separar: (a) qué módulos murieron por diseño (`fric_R > 0,15`), (b) cuáles tienen señal estable desde `2008` frente a régimen post-2020, y (c) cómo se comportaron en `2026-09` tras la fecha declarada por el vendedor (`2026-09-01`, última ventana pública sin tocar el holdout terminal `2026-10-01`).
2. **Bloque B (variantes estructurales):** La literatura interna (`RESULTADO_MECANISMOS.md` §2.2, `F-SALIDA-TECNICA-REGALA-LA-GANANCIA`, `F-AUDITORIA-UNIDADES-Y-VIEJAS`) mostró que las salidas técnicas rápidas cortan tendencia positiva antes del cierre y que los parámetros en puntos/USD fijos pierden escala entre regímenes de volatilidad. Reemplazar salidas técnicas por stop estructural amplio + EOD y escalar umbrales a `ATR20` / `R:R` puede rescatar frecuencia rentable y descorrelacionada para combinar con `T + Z + R` en prop firms (`R neto / mes`).

## Diseño fijo del experimento (Bloque A + Bloque B)

### Bloque A — Evaluación de fábrica `il_fabrica` post-IL en `NQ` (`14` pruebas + `O` descriptivo)
- **Datos:** `NQ_M1_nonadj_utc.parquet` cargado vía `m1_intradia.leer_m1nt8` (`ts < HOLDOUT_APERTURA_UTC_NS`, `>= 2008-01-01`), perfil **`il_fabrica`**.
- **Riesgo `R`:** módulos con stop duro nativo (`A1, A20, F, P, C, V, E, Q`) usan `|entry - stop|` (`T`: `clip(orb15 * 1.25, 2.0, 100.0)`); módulos sin stop o con salida técnica usan stop de catástrofe vía MAE (`0,25 × ATR20` en `R, Z`; `0,50 × ATR20` en `S, W, N, O`).
- **Particiones temporales A4 (solo lectura informativa pre-holdout):**
  - `PRE_2020`: `2008-01-01 → 2019-12-31`
  - `VEND_A`: `2020-01-01 → 2024-12-31`
  - `VEND_B_HASTA_1SEP`: `2025-01-01 → 2026-08-31`
  - `POST_1SEP`: `2026-09-01 → 2026-09-30` (post corte vendedor, estrictamente `< 2026-10-01`; descriptivo).
- `O` (`Overnight`) se reporta como **solo descriptivo** por `F-LUCID-SIN-OVERNIGHT` (no elegible para cuenta intradía).

### Bloque B — Mejora estructural bajo partición estricta **HOLDOUT-A5** (`71` pruebas)
- **Firewall A5:** en descubrimiento/grillas (**B1–B3**) solo entran sesiones con `a5_bloque(dia) == "DESC"`. En **B4** solo finalistas de `DESC` pueden leerse en índices externos (`DESC`) y una sola vez en `a5_bloque(dia) == "REP"`. **Prohibido tocar `HOLDOUT`, `EMBARGO` o `TERMINAL`.**
- **B1 — Re-indagación estructural de `V` (`VaultBreak`) (`14` pruebas en `NQ DESC`):**
  - Grilla 12 variantes nativas: `noise_multiplier ∈ {0.30, 0.40, 0.55}` × `vwap_exit_bars ∈ {2, 999}` × `profit_target_usd_per_contract ∈ {1400.0, 99999.0}`.
  - +2 overlays MAE ATR20 (`k ∈ {0.40, 0.60}`) sobre `V_fabrica`.
- **B2 — Salida EOD + stop duro amplio en `R` (`12` pruebas en `NQ DESC`):**
  - `S`: `exit_on_st_flip=False, use_hard_stop=True, hard_stop_atr_mult ∈ {2.0, 3.0, 4.5}` (`3`).
  - `W`: `exit_on_vwap_cross=False, allow_reentries=False`, MAE stop `k_atr ∈ {0.25, 0.50, 0.75}` (`3`).
  - `A20`: `exit_on_st_flip=False, use_hard_stop=True, hard_stop_atr_mult ∈ {1.5, 2.5, 3.5}` (`3`).
  - `N`: `(use_failed_breakout_exit=False, maximum_loss_prior_range_fraction ∈ {0.5, 1.0})` + `(use_failed_breakout_exit=False, use_daily_efficiency_filter=True)` (`3`).
- **B3 — Escalado a volatilidad (`ATR20`) y R:R (`21` pruebas en `NQ DESC`):**
  - `Q`: `risk_reward ∈ {0.30, 0.75, 1.50, 2.50}` × `break_margin_ticks ∈ {6, 12}` (`8`).
  - `F`: `tp_rr ∈ {1.0, 1.5, 2.5}` × `max_initial_risk_atr ∈ {0.0, 0.50}` (`6`).
  - `C`: `(stop_loss_amount, profit_target_amount, minimum_gap_points) ∈ {(1500,2500,2), (1500,4000,2), (2500,5000,2), (1500,2500,8)}` (`4`).
  - `E`: `(stop_points, target_points) ∈ {(30,45), (40,80), (60,120)}` (`3`).
- **Criterio de selección de finalistas en `DESC`:** `n_desc >= 30`, no degenerada en `diagnostico_grilla`, `R_neto_desc > 0`, `p_boot_desc < 0.05` (bootstrap por sesión), `mediana_fric_R <= 0.12`. Hasta 6 finalistas (siempre evaluando `V_fabrica` si pasa en `NQ DESC`).
- **B4 — Transferencia (`ES, YM, RTY, EMD` en `DESC`) + Confirmación congelada (`REP`) (`24` pruebas):** confirma si el efecto existe en activos no usados y en sesiones congeladas (`REP`), más correlación diaria y **R neto por mes** respecto a `T + Z + R`.

## Cómo podría refutarse
- Cada módulo/variante queda **refutado** si en `NQ DESC` su `R_neto <= 0`, `p_boot >= 0,05` o su mediana de fricción relativa supera `0,12 R`, si el diagnóstico de grilla revela `numero_efectivo < 2` / meseta ilusoria o dependencia de `< 3` episodios extremos (`episodios`), o si en `REP` y transferencia a `ES/YM/RTY` colapsa el signo neto. Ningún resultado de `POST_1SEP` aislado promueve ni refuta por baja potencia.
