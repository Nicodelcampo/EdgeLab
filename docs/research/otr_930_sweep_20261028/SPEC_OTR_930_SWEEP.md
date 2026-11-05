# Especificación Pre-Registrada — Familia `OTR-930-SWEEP` (`9:30 Cheat Code / OTR Range Breakout Return`)

## 1. Motivación e Hipótesis Microestructural
Esta familia traduce y expande al marco de grilla masiva de EdgeLab (`grilla_generica.py`, **1.119.744 celdas por canal**) la lógica operativa conocida como **`9:30 Cheat Code` / `OTR Range Breakout Return`** (evaluada originalmente en `MNQ` en el dashboard de RoboQuant), cruzándola con las primitivas microestructurales verificadas en el repositorio (`U1`, `SweepGate k36`, `ZONAS-GAPS` y `EmaCorridorTrendVolW2`).

### Hipótesis Física
1. **Acumulación Pre-Market (`08:12–09:12 ET` / `08:00–09:15 ET` / `08:30–09:29 ET`)**:
   Durante la hora previa a la apertura de contado de Nueva York (`09:30 ET`), los participantes institucionales y algoritmos de arbitraje fijan un rango de referencia `[lo_rng, hi_rng]` de altura `H_rng = hi_rng - lo_rng` alrededor de los anuncios macroeconómicos de las `08:30 ET`.
2. **Barrido de Liquidez en Apertura (`>= 09:30 ET`)**:
   Al abrir el mercado de contado (`09:30 ET`), la inyección de órdenes a mercado barre uno de los extremos del rango pre-market (`High > hi_rng` $\to$ `lado_barrido = +1`; `Low < lo_rng` $\to$ `lado_barrido = -1`), ejecutando stops acumulados fuera de la caja.
3. **Absorción y Retorno al Extremo Opuesto (`RETORNO` vs `CONTINUACION`)**:
   Si el barrido exterior se agota (confirmado por reingreso al rango, retroceso del 25% de la excursión estilo `U1`, o mecha de rechazo `SweepGate k36`, especialmente tras mitigar gaps previos de `ZONAS-GAPS`), el precio atraviesa el rango en sentido inverso hacia el punto de control (`POC_65`), el punto medio (`MID_50`) o el extremo opuesto (`OPUESTO_100`).

## 2. Espacio de Parámetros (`VARIABLES` — 9 Perillas + `EJECUCIONES` = 1.119.744 Celdas por Canal)

| # | Perilla (`Variable`) | Columna | Modo | Niveles | Definición Exacta |
|---|---|---|---|---|---|
| 0 | `ventana_rango` | `v_rng` | `grupo` | 3 | `0`: `08:12–09:12 ET` (literal video) · `1`: `08:00–09:15 ET` · `2`: `08:30–09:29 ET` (con ajuste DST `America/New_York` exacto). |
| 1 | `gatillo_retorno` | `gat` | `grupo` | 3 | `0`: `REINGRESO_CIERRE` (cierre M1 de vuelta dentro del rango) · `1`: `EXCURSION_U1_25` (excursión $\ge 0.12 H$ y regreso $\ge 25\%$ estilo `U1`) · `2`: `RECHAZO_MECHA_SWEEP` (mecha de rechazo $\ge 30\%$). |
| 2 | `excursion_rel` | `exc_rel` | `ge` | 3 | Excursión máxima fuera del rango `A_exc / H_rng`: `0`: $\ge 0$ · `1`: $\ge 0.08 H_{rng}$ · `2`: $\ge 0.20 H_{rng}$. |
| 3 | `sweep_gate_k36` | `sw_gate` | `eq_any` | 2 (+1) | `0`: sin `SweepGate` · `1`: con `SweepGate k36` (mecha $\ge 35\%$ y volumen M1 $\ge 1.15\times$ media previa) · `2`: cualquiera. |
| 4 | `gap_barrido` | `g_tom` | `eq_any` | 3 (+1) | Puntaje continuo `ZONAS-GAPS` de gaps previos barridos durante la excursión (`cortes = (0.05, 1.00)`). |
| 5 | `gap_iman_rango` | `g_cam` | `eq_any` | 3 (+1) | Puntaje continuo `ZONAS-GAPS` de gaps vivos dentro de `[lo_rng, hi_rng]` que actúan como imán hacia el objetivo (`cortes = (0.05, 1.00)`). |
| 6 | `corredor_ema` | `ema_al` | `eq_any` | 3 (+1) | Estado del corredor `EMA(20)/EMA(60)`: `0`: contra el retorno · `1`: comprimido ($\le 0.35\,\text{ATR}$) · `2`: a favor del retorno · `3`: cualquiera. |
| 7 | `tamano_rango` | `tam_rng` | `extremos` | 3 | Terciles causales de `H_rng / ATR14` (`0`: estrecho T1 · `1`: amplio T3 · `2`: cualquiera). |
| 8 | `vwap_al` | `vwap_al` | `eq_any` | 2 (+1) | `0`: objetivo alejándose del `VWAP` · `1`: objetivo hacia el `VWAP` de la sesión · `2`: cualquiera. |
| 9 | `ejecución` | — | `grupo` | 24 | `2` modos (`RETORNO`, `CONTINUACION`) $\times$ `2` entradas (`CIERRE`, `SIG`) $\times$ `3` objetivos (`OPUESTO_100`, `POC_65`, `MID_50`) $\times$ `2` stops (`S_SWEEP`, `S_RANGO55`). |

## 3. Campañas y División por Cuentas de Kaggle
- **`OTR930-NQ`** (`sensor: NQ`, `ejecucion: NQ`, `cuenta_kaggle: nicolasbuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
- **`OTR930-ES`** (`sensor: ES`, `ejecucion: ES`, `cuenta_kaggle: nicolasbuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
- **`OTR930-CFD-NQ`** (`sensor: DK:USATECHIDXUSD`, `ejecucion: NQ`, `cuenta_kaggle: nicobuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
- **`OTR930-CFD-ES`** (`sensor: DK:USA500IDXUSD`, `ejecucion: ES`, `cuenta_kaggle: nicobuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
