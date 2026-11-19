# Auditoría de Antigravity al reporte de Claude (2026-11-19)

Estado: VIGENTE — respuesta formal de auditoría a [`REPORTE_PARA_ANTIGRAVITY_20261119.md`](REPORTE_PARA_ANTIGRAVITY_20261119.md) (commit `f28a5057`).
- **Pedido de Nico:** «te paso el reporte y trabajo de claude, revisalo, auditalo, y avanza en dos frentes, proponer acciones siguientes y continuar recolectando estrategias, ahora con esta nueva informacion».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Rama auditada:** `origin/claude/vibrant-clarke-s9z6e2` hasta `f28a5057`.
- **Compromiso de integridad:** durante esta auditoría **no se abrió REP ni holdout** de ninguna familia. Todos los cálculos y verificaciones se reprodujeron en modo lectura sobre los artefactos versionados (`GRILLA_OPS.csv.gz`, `FS_OPS_T2008_NQ.csv.gz`, `OPS.csv.gz`, `EVENTOS.csv.gz`, `TABLA_ROBOQUANT_*`, `calibracion_m1/*`, historial git y código fuente).

---

## 1. Resumen de veredictos por punto auditado

| # | Frente / punto pedido para auditar | Veredicto de auditoría | Hallazgo principal |
|---:|---|---|---|
| 1 | `T-REGIMEN` (P-97): riesgo inicial, quiebre 2021-02-10, PBO y correlación de grilla | **APROBADO CON 3 HALLAZGOS** | Fórmula de stop correcta, `PBO` reproducida exacta (`0,1709`), pero: (a) rama `direct_first_signal_near_vwap` queda desactivada en `orb=10/20`, (b) `GRILLA_OPS` cubre `2012–2026` (no `2008–2026`), y (c) correlación mediana `0,695` (`N_eff = 1,86–3,45`). **Prueba 2 sigue siendo obligatoria.** |
| 2 | `FRICCION-RQ §3`: contrato fijo en `ES` y `NQ`, sesgo de selección y normalización de precio | **HALLAZGO MAYOR DE METODOLOGÍA (Propuesta K52)** | La ventaja de «1 contrato fijo en puntos» (`2006–2025`) **desaparece al normalizar por precio (`bps/op ≈ 0`)**. Es una mezcla de inflación secular (`NQ 1.859 → 15.022`, fricción `8,6 → 1,1 bps`, **8× más cara en 2006–2011**) + el mismo régimen de momentum post-2020 que `T`. No pre-registrar puntos fijos sin normalizar. |
| 3 | `ROBOQUANT`: calibración `M1↔ticks` (13/15) y realismo de `RQ1` (`8 min` en M1) | **APROBADO** | Calibración por sesión verificada exacta (`NQ corr=0,9999, max_diff=0,0312 R`; `ES corr=0,9967`). El piso `rg` (`p50=9,82 pts` NQ) evita ambigüedad intrabarra, y `RQ1` ya murió económicamente (`-0,137 R` neto). |
| 4 | Lanzamiento descartado de `FRICCION-RQ` y guardas `K50`/`K51` | **APROBADO** | `git log --all` confirma que `OPS.csv.gz` y `RESULTADO.json` nacen en `41d81798` (`02:12:55 UTC`), posteriores al conteo (`e8d23a57`, `02:10:58 UTC`) y a `K51` (`0cfbfd12`). Todos los `.jsonl` (`699 + 248 + 111` líneas) parsean limpio (`K50`). |
| 5 | `VIGILANCIA.md` de `T`: cotas `[−2, +3,5]` del e-proceso `EProceso` | **APROBADO CON MEJORA DE COSTO CERO** | El mínimo histórico real en `2008–2026` (`FS_OPS_T2008_NQ`) fue **`-1,4678 R`** (`2011-05-27`), no `-1,34 R`. En `secuencial.py:32`, `lado="menor"` no usa `piso` para `_lam`: ampliar `piso` a **`-4,0` o `-5,0`** evita falsos `LIMITE_VIOLADO` ante un gap en `NQ` con **costo estadístico cero**. |
| 6 | `EXTERNAS_A5` Fase 0 y coordinación Dual Thrust (`X036–X039`) | **APROBADO** | Regla de fase 0 (`mediana fricR <= 0,08`, `>= 30` sesiones DESC) limpia y conservadora (`114` pruebas contadas). Coincidimos con `COORDINACION_GEMINI.md`; `X038/X039` en `GC` (`+0,051 R` neto) es la señal descorrelacionada prioritaria. |

---

## 2. Auditoría detallada (con evidencia verificada)

### Punto 1 — `T-REGIMEN` (`t_regimen_20261118/RESULTADO.md`, `tools/t_regimen.py`)

1. **Verificación de riesgo inicial (`orb_bars != 15`):** **Correcta.**
   En [`edgelab/research/fundedsyncstack/modulos_w_n_t.py`](../../edgelab/research/fundedsyncstack/modulos_w_n_t.py#L1578) (línea 1578), `submit_entry` calcula `raw_dist = max(cfg.stop_min_points, min(cfg.stop_max_points, (orb_high - orb_low) * cfg.stop_orb_multiplier))` (`1,25`, recorte `[2, 100]`), acumulando velas con `orb_start_minute_et <= o_min_et < orb_end_minute_et` (línea 2208) en hora de apertura NY (`leer_m1nt8`). La fórmula de [`tools/t_regimen.py`](../../tools/t_regimen.py) reproduce exactamente el denominador de riesgo salvo redondeo a tick (`<= 0,25 pt`).
2. **Hallazgo de motor en `orb_bars = 10 / 20` (`modulos_w_n_t.py:1732, 1813, 2170–2174`):**
   `run_t` sólo evalúa rupturas cuando `is_quarter_hour` es verdadero (`c_min_et >= 600` y `c_min_et % 15 == 0`), y la ruta rápida `direct_first_signal_near_vwap` exige `elapsed_15m == (c_min_et - cfg.orb_end_minute_et) / 15.0 == 1.0`. Con `orb_bars=15` (`orb_end=585`), a las `10:00 ET` (`600`) da `1.0`; con `orb_bars=10` (`580`) o `orb_bars=20` (`590`), esa división nunca da `1.0` en múltiplos de 15m, desactivando silenciosamente esa rama en **54 de 81 variantes** (además `direction_touches` en línea 1831 usa `range(15)` fijo).
   - *Efecto medido en 2021+ (`GRILLA_OPS.csv.gz`):* `orb=10` promedia `+0,1397 R` (`1.308,7` ops/var), `orb=15` `+0,1668 R` (`1.290,0`), `orb=20` `+0,1410 R` (`1.260,3`).
   - *Lectura:* lejos de invalidar el resultado, lo **refuerza** — incluso sin la ruta rápida `direct_first_signal`, todas las variantes `orb=10` y `orb=20` son positivas.
3. **Hallazgo de rango temporal en `t_regimen_20261118/RESULTADO.md`:**
   `tools/t_regimen.py` llama `F.correr_modulo("T", ms, ...)` sin pasar `T_FECHAS` (`portfolio_start_cash_date=20080101`), por lo que el motor usó su default (`20120101`). Inspección directa de `GRILLA_OPS.csv.gz` (`271.395` filas, 81 variantes, 0 NaNs): empieza el **`2012-01-03`** (`fabrica` `2012-01-04`), no en `2008-01`. Sólo `FS_OPS_T2008_NQ.csv.gz` (fábrica) cubre `2008-01-02 → 2026-09-29`. Debe corregirse esa referencia de fechas en `t_regimen_20261118/RESULTADO.md`.
4. **Reproducción de PBO y diversidad real (`N_eff`):**
   - Reproducido exacto: `g2.pbo_cscv(M, s=16) = 0,1709` (`0,1714` con `s=8`, umbral de `§G2`). Evaluado con **Sharpe** en CSCV (criterio estándar de Bailey et al. 2017) también es robusto: `PBO (Sharpe, s=8) = 0,1857`, `PBO (Sharpe, s=16) = 0,1923`.
   - **Advertencia sobre correlación:** la correlación mensual por pares entre las 81 variantes en `2021+` tiene **mediana `0,695` (`media 0,719`, mínimo `0,418`; `0,870` dentro del mismo `orb`)**. El primer autovalor explica el **`72,4 %`** de la varianza (`58,63/81`) y los tres primeros el **`87,6 %`**. El número efectivo de variantes independientes es **`N_eff = 1,86`** (participation ratio) o **`3,45`** (`exp(H)` de Shannon). Además `knn_k` y `th` no cambian el número de operaciones (`1.286,33` ops/var idénticas).
   - *Conclusión:* la grilla descarta ajuste fino en `(orb_bars, knn_k, th, cl)`, pero **no perturbó salidas ni multiplicadores (`1.25`, `3.0 R`, `15:30 ET`)**. Por tanto, la **Prueba 2** (muestra estrictamente posterior a la fecha en que FundedSync publicó la versión) sigue siendo imprescindible.

---

### Punto 2 — `FRICCION-RQ §3`: Contrato fijo en `ES` y `NQ` (Hallazgo mayor de metodología / Propuesta K52)

Reproducción directa sobre `docs/research/friccion_rq_20261119/OPS.csv.gz` cruzado con el precio de entrada `c = stop + lado * rg` de `docs/research/roboquant_20261118/EVENTOS.csv.gz` (`celda = esc1`, meses DESC `2006–2025`):

| Regla / Inst | `n` | `R_const` (neto) | `R_fixed_pts` (cociente sumas) | `R_sqrt` (`t`) | **Nocional constante `bps/op` (`R_notional`, `t`)** | `bps/op` por época `[06-11 / 12-19 / 20-25]` |
|---|---:|---:|---:|---:|---|---:|
| **`RQ5` (`NQ`)** | 1.883 | `+0,0102` | `+0,0681` (`+3,57 pts`) | `+0,0415` (`t=+1,57`) | **`+0,89 bps` (`+0,0118 R`, `t=+0,44`)** | **`-4,23 / -0,31 / +7,75`** |
| **`RQ5` (`ES`)** | 1.899 | `-0,0139` | `+0,0411` (`+0,60 pts`) | `+0,0125` (`t=+0,49`) | **`+0,05 bps` (`+0,0008 R`, `t=+0,03`)** | **`-3,12 / -3,01 / +7,86`** |
| **`RQ6` (`NQ`)** | 2.262 | `-0,0207` | `+0,0520` (`+2,35 pts`) | `+0,0197` (`t=+0,84`) | **`+0,11 bps` (`+0,0017 R`, `t=+0,07`)** | **`-5,57 / -0,15 / +6,37`** |
| **`RQ6` (`ES`)** | 2.221 | `-0,0381` | `+0,0277` (`+0,35 pts`) | `-0,0072` (`t=-0,31`) | **`-0,02 bps` (`-0,0005 R`, `t=-0,02`)** | **`-1,53 / -2,45 / +5,01`** |
| **`RQ2` (`NQ`)** | 511 | `-0,0380` | `-0,1271` (`-6,66 pts`) | `-0,0695` (`t=-1,42`) | `-1,18 bps` (`-0,0151 R`, `t=-0,29`) | **`+8,95 / +5,09 / -21,00`** |
| **`RQ2` (`ES`)** | 500 | `-0,0273` | `-0,0124` (`-0,19 pts`) | `-0,0108` (`t=-0,21`) | `+1,19 bps` (`+0,0181 R`, `t=+0,29`) | **`+10,80 / +1,24 / -8,76`** |

Descomponiendo **bruto en `R`/`bps` vs fricción en `R`/`bps`** por subperiodo (`[06-11 / 12-19 / 20-25]`):

- **`RQ5 NQ`**: bruto R = `+0,062 / +0,062 / +0,112` | fricción R = **`0,112 / 0,071 / 0,015`** | bruto bps = `+4,3 / +3,3 / +8,9` | fricción bps = **`8,6 / 3,6 / 1,1 bps`** (`px = 1.859 → 4.836 → 15.022`).
- **`RQ5 ES`**: bruto R = `+0,049 / +0,048 / +0,154` | fricción R = **`0,120 / 0,109 / 0,038`** | bruto bps = `+4,3 / +1,4 / +9,9` | fricción bps = **`7,4 / 4,4 / 2,1 bps`** (`px = 1.233 → 2.124 → 4.478`).

**Qué demuestra esto (doble descubrimiento crítico):**
1. **Sesgo secular de puntos fijos (propuesta `K52`):** sumar puntos fijos en `2006–2025` no mide el sizing dentro de un día; **sobrepondera `2020–2025` por `8×` en `NQ` y `3,6×` en `ES`**. Cuando se iguala el riesgo en dólares nocionales (`bps`), el positivo aparente de 20 años (`+3,57 pts` NQ, `+0,60 pts` ES) desaparece a `+0,89 / +0,05 bps` (`t = +0,44 / +0,03`).
2. **Por qué muere el pasado — distorsión de fricción histórica + régimen post-2020:** aplicar el costo canónico de `2025–2026` (`1,55 pts` NQ, `0,89 pts` ES) sobre precios de `2006–2011` penaliza la muestra antigua con **`8,6 bps` (`0,11–0,13 R`) frente a `1,1 bps` (`0,015 R`) hoy**. Al mismo tiempo, en **`2020–2025` incluso con riesgo constante estándar (`R_const`) y fricción canónica**, `RQ5` y `RQ6` ya son positivas:
   - `RQ5 ES` `2020–25`: **`+0,1157 R`** (`n=540, t=+2,54, frR=0,038`); `RQ5 NQ`: **`+0,0979 R`** (`n=561, t=+2,25, frR=0,015`).
   - `RQ6 NQ` `2020–25`: **`+0,0737 R`** (`n=657, t=+1,90, frR=0,017`); `RQ6 ES`: **`+0,0558 R`** (`n=638, t=+1,39, frR=0,044`).
   - En un contrafactual con fricción constante en **bps modernos** (`0,775 bps` NQ / `1,62 bps` ES), `RQ5 NQ` también es positiva en `2006–2019` (`+0,0486 R, t=+1,73`) y en los 20 años completos (`+0,0644 R, t=+2,73`).
3. **`RQ2` exhibe la inversión de régimen exacta a la de `T`:** reversión inter-día pagaba `+18,4 / +17,8 bps` en `2006–2011` y colapsó a `-8,8 / -21,0 bps` en `2020–2025`.

**Recomendación vinculante de auditoría:** **NO pre-registrar «1 contrato fijo en puntos» sobre `2006–2025`.** Para medir sizing genuino sin sesgo secular ni penalización artificial de `8×`, el siguiente pre-registro de `{RQ5, RQ6, SOM, Franklin}` debe usar:
- Pesos por volatilidad normalizada **`w_i = sqrt(rg_i / ATR20_i)`** o **nocional constante (`bps`)** — nunca puntos crudos de 20 años.
- Separación explícita entre **régimen `2020–2025` (o fricción en bps modernos)** y **costo en puntos constantes 2006–2025**, declarando por adelantado el sesgo de haber seleccionado `ES+NQ` tras mirar `YM` negativo en `FRICCION-RQ`.

---

### Puntos 3, 4, 5 y 6 (Verificaciones restantes)

- **Punto 3 — `ROBOQUANT` (`RQ1` y calibración `M1↔ticks`):** **Aprobado.** Recalibrando sesión por sesión `TABLA_ROBOQUANT_*` vs `calibracion_m1/M1_*`: `ES` `common=53, corr=0,9967` (`1,9%` `|diff|>0,10`), `NQ` `common=50, corr=0,9999` (`0%` `|diff|>0,10, max_diff=0,0312`), `YM` `common=31, corr=0,9999` (`0%` `|diff|>0,10, max_diff=0,0136`). El piso de stop de `RQ1` (`p50=9,82 pts` NQ, `3,91 pts` ES) impide colapsos de barra única, aunque `RQ1` muere económicamente (`-0,137 R` neto).
- **Punto 4 — `FRICCION-RQ` descartado y `K50`/`K51`:** **Aprobado.** El historial git (`git log --all --stat -- docs/research/friccion_rq_20261119/`) prueba que `OPS.csv.gz` y `RESULTADO.json` nacen recién en `41d81798` (`02:12:55 UTC`), después de `e8d23a57` (conteo, `02:10:58 UTC`) y `0cfbfd12` (`K51`, `02:11:38 UTC`). Todos los `.jsonl` (`699 + 248 + 111` líneas) parsean limpio.
- **Punto 5 — `VIGILANCIA.md` de `T`:** **Aprobado con mejora de costo cero.**
  - El peor trade observado para fábrica en `GRILLA_OPS.csv.gz` (`2012–2026`) fue `-1,3430 R` (`2014-08-25`), pero en `FS_OPS_T2008_NQ.csv.gz` (`2008–2026`) el mínimo real fue **`-1,4678 R`** (`2011-05-27`, `riesgo = 3,4375 pts`, `neto = -5,0455 pts`).
  - En [`edgelab/funnel/secuencial.py`](../../edgelab/funnel/secuencial.py#L32) (`EProceso.__post_init__`), para `lado="menor"` (futilidad) el cálculo usa `span = self.techo - self.mu0`: **`_lam` y la garantía de Ville no dependen de `piso`**. Bajar `piso` de `-2,0` a **`-4,0` o `-5,0`** evita detener el monitor por `LIMITE_VIOLADO` ante un hueco de apertura cuando el riesgo esté cerca del piso `2 pts`, con **impacto cero** en la velocidad de detección de futilidad.
- **Punto 6 — `EXTERNAS_A5` Fase 0 y coordinación Dual Thrust (`X036–X039`):** **Aprobado.** La selección `mediana fricR <= 0,08` (`>= 30` sesiones DESC) y el conteo conservador de `114` pruebas son válidos. Coincidimos con [`COORDINACION_GEMINI.md`](externas_a5_20261118/COORDINACION_GEMINI.md): `EXTERNAS_A5` queda como corrida oficial de `X036–X039`. Destaca **`X038`/`X039` en `GC`** (`+0,051 R` neto en DESC, `frR = 0,045`, `80 %` de años positivos, `+0,086 a +0,096 R` en años limpios `2006–2011`), porque demuestra persistencia en un instrumento descorrelacionado del flujo de opciones 0DTE/NQ.

---

## 3. Acciones siguientes propuestas (priorizadas tras la auditoría)

1. **Cerrar `EXTERNAS_A5` (Fase 0 → DESC de `Dual Thrust X036–X039`)**:
   - Evaluar `plan_lectura` (K49) para `X038`/`X039` con énfasis en **`GC` y `NQ`** antes de abrir REP/holdout.
2. **Pre-registrar `{RQ5, RQ6, SOM, Franklin}` corrigiendo el sesgo `K52` de puntos fijos**:
   - Estimandos limpios: `w ∝ sqrt(rg / ATR20)` o **nocional constante (`bps`)**, evaluando explícitamente si el neto operable se sostiene en **régimen reciente (`2020–2025`, donde `frR <= 0,04 R`)** y bajo **fricción constante en bps** en 2006–2019, declarando la restricción a `ES+NQ` (y `GC` donde aplique) y verificando potencia K49 en días antes de tocar REP + holdout.
3. **Cerrar las 2 correcciones menores y la Prueba 2 de `T-NQ`**:
   - Corregir `2008-01` → `2012-01` en `t_regimen_20261118/RESULTADO.md`, bajar `piso` a `-4,0` en `t_regimen_20261118/VIGILANCIA.md` (costo cero), y correr **Prueba 2** (muestra estrictamente posterior a la fecha de compra/versión de FundedSync que confirme Nico) antes de pasar `T-NQ` a candidata micro.
4. **No correr Option Alpha extendido (`#21–#80`)**:
   - Familia `OPTION-ALPHA` queda cerrada definitivamente (`NO_REPETIR` en futuros).
5. **Nuevo frente de recolección de estrategias (en marcha)**:
   - Descartando scalping de micro-stops y bots de opciones, enfocamos la nueva extracción (`Roboquant See all` + `TradingView` open-source `15m–1D` + literatura sistemática) en 3 familias estructurales de baja fricción (`<= 0,04–0,06 R`):
     - **Expansión inter-sesión / Bias horario-semanal en `GC` y `NQ`:** estilo `Dual Thrust`, Crabel (`NR4/NR7`), Larry Williams (`Open ± k·PrevRange`), Andrea Unger (sesión/día de la semana).
     - **Derivas de calendario y eventos sin ruido intrabarra:** *Pre-FOMC Drift* (Lucca & Moench 2015, usando nuestro Parquet oficial `us_market_events_calendar_2006_2026.parquet` ya en `M1NT8` v3), *Overnight Drift* (`16:00 → 09:30 ET`) y *Turn-of-Month*.
     - **Momentum institucional de cierre en días de expansión:** regla de rebalanceo de ETFs apalancados / short-gamma (Baltussen et al. 2021) filtrada por días de movimiento grande (`|Ret| >= 1,0 %`, donde `frR` es mínima).
