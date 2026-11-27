# Auditoría Integral (`PR #203` + Auto-Auditoría It. 1 y 2) y Próximos Frentes (2026-11-27)

> **Custodia estricta verificada**: `0` fechas `>= 2026-10-01` (`HOLDOUT-A4 / TERMINAL`) y `0` celdas leídas en `HOLDOUT A5` sellado (`CARRIL2_A5`, `CRIPTO_BINANCE`, `TENDENCIA_NO_EQUITY`). Todas las mediciones se registraron en [TRIAL_REGISTRY_GLOBAL.jsonl](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/docs/research/TRIAL_REGISTRY_GLOBAL.jsonl) vía [REGISTRO_POSTERIOR.md](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/docs/research/auditoria_claude_20261127/REGISTRO_POSTERIOR.md) (`773` campañas / `538,657,254` pruebas acumuladas).

---

## 1. Resumen transparente de las 2 iteraciones de auditoría propia (y errores corregidos)

| Qué auditamos | Fallo detectado en Iteraciones 1 y 2 | Corrección aplicada |
| :--- | :--- | :--- |
| **1. Ilusión de MDD por escala de volatilidad** (`marco_sin_forward.py` v1) | Al promediar frentes sin re-escalar al mismo riesgo final, `Super_3Core_HRP` tenía `daily_ann_sd = 2.32` (`40%` menos riesgo que `CME_Div10 = 3.86`), simulando un recorte ficticio del `MDD` (`mdd/OWN_ann_sd = 1.17` vs `0.90`). | Toda tabla histórica, estrés y **Bootstrap 20k semanal en Kaggle** compara ahora carteras escaladas a **exactamente `10%` de volatilidad anual propia**. |
| **2. Spike de lunes (`1.77x`) y descalce mensual** (`marco_sin_forward.py` v1) | Apilar retornos `7d` de cripto el lunes infló `sd(lunes)/sd(mar-vie) = 1.77` e hizo que `HRP` subponderara Cripto (`16.2%`) y sobrecargara `Carril 2` (`46.8%`). Además `a5_bloque(YYYYMM01)` recortaba `14` meses por `EMBARGO` del día 1. | Integración y pesos `HRP` pasados a **semanas `W-FRI` y meses `M`** con mapeo intra-mes (`_a5_mes_blq` sobre los `51m` / `186m` completos sin fuga A5). |
| **3. Contaminación `CME` en `CSCV` y `Bayes`** | `10` de las `20` columnas previas eran ganadores `CME/FundedSync` (muestra vista por el vendedor hasta `2026-08`). `CSCV` no detecta data-snooping upstream. | Separado en **3 bloques `CSCV` (`12,870` splits)**: `1_clean_carril2_16rules` (`176m`, `0` CME), `2_clean_non_cme_21rules` (`48m`, `0` CME) y `3_descriptive_with_cme` (etiquetado `DESCRIPTIVO_SESGO_VENDEDOR_CME`), con bandera `upstream_selection_caveat`. |
| **4. Sesgo de fase, TradFi y huecos en `CRIPTO-PIT v2`** | `UNIVERSO_PIT.csv` incluía perpetuos TradFi/acciones (`CLUSDT, XAUUSDT, MUUSDT, SOXLUSDT...`); `hysteresis_exit=35` era inoperante (`max rango = 25`); `Phase 0` de `iloc[::5]` dio suerte (`Sh=1.29` vs `Phase 1=0.48`); y el apagón de Binance `2022-02-26..28` causaba falsos `NaN` de delisting. | Excluidos `36` símbolos TradFi/stables + filtro causal `vol60 >= 25%`; `hysteresis_exit=25`; `_safe_close_returns` ante huecos internos (`delist_hits = 0` en `XSMOM`); y **5 tranches escalonadas** (`CR2_XSMOM_Stag5d`, `CR2_ResidMom_Stag5d`). |
| **5. Roll glitches en `FUTUROS-NO-EQUITY v2`** | Los continuos `Yahoo =F` no tienen back-adjustment: `NG=F` suma **`208` días `>8%`** (`31` días `>15%`, máx `47.5%`), `CL=F` **`78` días**, `RB=F` `67`, paridad `M1` de solo `0.76`. | Frente marcado explícitamente **`INVALIDADO_POR_ROLL_NO_AJUSTADO_YAHOO`** y excluido del núcleo (ni aprueba ni refuta futuros no-equity). |
| **6. Decaimiento secular de `Carril 2 Sellada 16`** | El Sharpe conjunto `2006–2026` (`0.86`) ocultaba caída post-2018 (`2021–2026 DESC Sh = 0.13`), reflejando `F-REVERSION-CORTA-APAGADA-2018`. | Desglosado por época (`06-12` `1.24`, `13-18` `1.00`, `19-26` `0.51`, `21-26` `0.51`) para impedir sobreponderarlo al `47%`. |
| **7. Gobernanza North Star** | Las corridas iniciales faltaban en `TRIAL_REGISTRY_GLOBAL.jsonl`. | Registradas las `3` campañas (`12 + 4 + 8 = 24` pruebas) en `TRIAL_REGISTRY_GLOBAL.jsonl` tras validar `REGISTRO_POSTERIOR.md` sin errores (`PREFLIGHT: []`). |

---

## 2. Auditoría a Claude (`PR #203` — `80164f3d`)

* **Trampa matemática de `K27` por familia aislada**: exigir `80%` de potencia en `18m / 22m / 63m` de holdout con shrinkage `0.5x` demanda un Sharpe de desarrollo de **`4.06 / 3.67 / 2.17`** (`2.90 / 2.62 / 1.55` a `0.7x`). En cambio, promediar **`M = 10-20` mecanismos con `rho = 0.05-0.10`** (`SR_ind = 0.70`) eleva la potencia teórica a `63m` (`0.7x`) a **`82.4% - 97.4%`**.
* **Falso negativo en `CRIPTO-PIT`**: la línea 177 (`w.sub(w.where(E1).mean(axis=1), axis=0)`) asignaba peso residual a `~21` monedas planas cada día, y `CR_Trend_4H_EMA` (`-\$165.9/m`) explicó `65.5%` de la pérdida `REP` de `CR_1N` (`-\$84.4/m`).
* **Motor `Carril 2`, `PRESET-DIVERSIFICADA` y `CANASTA-AMPLIA`**: `canasta_amplia.py verificar_motor` verificado **`IDENTICO`** (`dif_R = 0.0` hasta el 6.º decimal en `DESC/REP` de las 16 reglas selladas); `PRESET-DIVERSIFICADA` (`150k`, `2` micros `ResolveTz`) rinde `+\$217-234/m` neto con paridad `>=98.8%`; `CANASTA-AMPLIA` confirma que `DESC>0` (`HOLDOUT Sh=1.81`) supera a `DESC<=0` (`Sh=0.18`).

![Auditoria Claude K27 y Sesgos](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/docs/research/auditoria_claude_20261127/auditoria_claude_k27_y_sesgos.png)

---

## 3. `CRIPTO-PIT v2` Auditada (`226` monedas crypto PIT sin TradFi, `20 bps + funding`)

| Mecanismo / Canasta (`DESC+REP 51m`, `20 bps`) | Rot. | `DESC (39m)` `Sh / t` | `REP (12m)` `Sh / t` | `DESC+REP (51m)` `Sh / t` | `22–26` `Sh` | `beta_BTC` / `Top5d` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ABL_Claude_XSMOM_Bug` | `1.5x` | `t = 2.16` | `t = -0.23` | `0.79 / 1.63` | `0.58` | `0.483` Top5d |
| **`CR2_XSMOM_Stag5d` (`20 bps`)** | **`2.7x`** | **`1.05 / 1.89`** | **`1.14 / 1.14`** | **`1.08 / 2.23` (`+\$223.7/m`)** | **`0.98`** | **`+0.004` / `0.277`** |
| `CR2_XSMOM_Stag5d` (`10 / 30 / 40 bps`) | `2.7x` | `1.19 / 0.91 / 0.77` | `1.28 / 1.00 / 0.86` | **`1.22 / 0.94 / 0.80`** | — | `dh = 0` |
| `CR2_ResidMom_Stag5d` (`20 bps`) | `3.0x` | `0.20 / 0.36` | `0.51 / 0.51` | `0.27 / 0.56` | `0.50` | `-0.021` / `0.957` |
| `CR2_TSMOM_Blend_1D` (`20 bps`) | `1.7x` | `0.31 / 0.56` | `1.10 / 1.10` | `0.49 / 1.02` | `0.36` | `-0.058` / `0.833` |
| `CR2_Funding_Carry_Stag3d` (`20 bps`) | `4.6x` | `0.17 / 0.30` | `-1.31 / -1.31` | `-0.03 / -0.05` | `-0.06` | `-\$4,518` en 2025 |
| **`CR2_Core_XSMOM_ResidMom`** (`51.6% / 48.4%`) | — | `0.70 / 1.26` | `0.87 / 0.87` | **`0.75 / 1.55` (`p=0.061`)** | **`0.79`** | **`-0.008` / `0.396`** |
| `CR2_Canasta_InvVol` (`4` vivas `DESC`) | — | `0.64 / 1.15` | `0.84 / 0.84` | `0.69 / 1.41` | `0.61` | `-0.028` / `0.369` |

* **Descomposición crítica (`Top20_hyst 4L/4S`)**: `Long-Short_Alts` (`Sh=1.08`, `22-26=0.98`, `beta=+0.004`) > `LongAlts-ShortBTC` (`Sh=0.72`, `22-26=0.25`) y `Long-Only_Alts` (`Sh=0.90`, `22-26=0.52`, `beta=+0.575`); `Short-Only_Alts` pierde (`-0.25`) pero aporta cobertura `beta = -0.571` que estabiliza la canasta en mercados bajistas (`+1,826` USD en 2022). `5/5` fases (`Phase 0..4`) son positivas (`Sh = 0.48` a `1.29`).

![Frentes v2 Cripto PIT y Yahoo Roll Glitches](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/docs/research/auditoria_claude_20261127/frentes_v2_cripto_pit_y_futuros_no_equity.png)

---

## 4. Marco Sin Forward a Volatilidad Idéntica (`10%` anual) y CSCV Limpio (`Kaggle v3`)

Comparación honesta a **exactamente `10%` de volatilidad anual** (`2021-01..2026-09`, `51m DESC+REP`, `HOLDOUT` sellado) junto a Bootstrap semanal de **`20,000` rutas (`4` sem × `52` sem)** y escenario de **contracción `0.5x` en `CME`**:

| Cartera (`21–26 DESC+REP`) | Origen | `Sh` (`t`) | `MDD 10% vol` | `Calmar` | Boot 20k `Sh P50 / MDD P95` | Estrés `CME 0.5x` (`C2+CR 0.7x`) `Sh / MDD / Calmar` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Carril2_Sell16` | **LIMPIO** | `0.505` (`1.04`) | `-11.22%` | `0.45` | `0.519 / -19.76%` | — |
| `Cripto_Core_Stag` | **LIMPIO** | `0.745` (`1.54`) | `-10.47%` | `0.71` | `0.732 / -15.43%` | — |
| `CME_Div10` solo | Sesgo CME | `1.842` (`3.80`) | `-3.95%` | `4.67` | `1.716 / -8.74%` | `0.92 / -7.88% / 1.17` |
| `CME_TRZV` solo | Sesgo CME | `2.494` (`5.14`) | `-3.76%` | `6.63` | `2.456 / -6.84%` | `1.25 / -5.84% / 2.14` |
| `Super_3Core_EQ` (`1/3` `Div10+C2+CR`) | Mixto | `1.763` (`3.63`) | `-4.15%` | `4.24` | `1.559 / -11.75%` | **`1.03 / -5.99% / 1.72`** |
| `Super_3Core_HRP_Weekly` | Mixto | `1.769` (`3.65`) | `-4.20%` | `4.21` | `1.571 / -11.67%` | — |
| **`CME50_C2_25_Cripto25`** (`TRZV 50/25/25`) | Mixto | **`2.521` (`5.20`)** | `-5.23%` | `4.82` | `2.362 / -7.90%` | **`1.36 / -6.20% / 2.19`** (`0.5x/0.5x`: `1.26`) |

* **CSCV limpio SIN sobrevivientes `CME` (`12,870` splits `S=16`)**:
  - `1_clean_carril2_16rules` (`176m`): escoger la mejor regla IS cae `0.889 -> 0.322` OOS (`PBO = 55.38%`), mientras la **canasta `1/N`** logra **`OOS Sh = 0.851`** (`P10 = 0.605`, **`P(OOS > 0) = 100.0%`**, `P(OOS > 0.5) = 97.41%`).
  - `2_clean_non_cme_21rules` (`16 C2 + 5 Cripto`, `48m`): mejor regla `1.449 -> 0.146` (`PBO = 53.04%`), **`1/N`** logra **`OOS Sh = 0.654`** (`P(OOS > 0) = 86.51%`).
  - **Potencia teórica en holdouts sellados (sin abrirlos)**: `Carril 2 Sell16` (`63m`) = `0.253 / 0.393 / 0.625`; **pooling dinámico `Carril 2 + Cripto_Core_Stag` (`63m`)** sube a **`0.296 (0.5x) / 0.464 (0.7x) / 0.717 (1.0x)`**.

![Marco Sin Forward Igual Vol CSCV Limpio y Estres](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/docs/research/auditoria_claude_20261127/marco_sin_forward_cscv_bayes_y_supercanasta.png)

---

## 5. Separación operativa por vehículo y los 5 próximos frentes (según `NORTH_STAR.md`)

| Vehículo de ejecución | Qué opera hoy | Restricción / estado |
| :--- | :--- | :--- |
| **Prop intradía (`LucidFlex 150K`)** | `CME_Div10` / `Intradia8` (`2` micros, DLL intradía `ResolveTz` OK) | Prohibido mantener overnight; prioridad #1 = paridad NT8 de `N`, `Franklin` y `ES5N`. |
| **Cuenta personal / futuros overnight** | `Carril 2` (`C2_VZ`, `C2_EVRP`, `C2_TT`, `C2_TOM`, `C2_ROT`) | Requiere margen overnight; separar post-2018 antes de abrir `HOLDOUT A5` (`63m`). |
| **Cripto perpetuos (`Binance / Bybit`)** | `CR2_XSMOM_Stag5d` (+ `ResidMom`) `L/S` ex-TradFi | Corrida 24/7 independiente (`beta_BTC ~ 0`), holdout `18m` aún sellado. |

### Próximos frentes priorizados (libres de colisiones con `NO_REPETIR`)

1. **`CRIPTO-PIT v3` limpio y pre-registrado (`HOLDOUT A5 18m` intacto)**: conservar `CR2_XSMOM_Stag5d` (`Sh=1.08`, `beta=0.004`) y `ResidMom`, sumar **1–2 mecanismos verdaderamente ortogonales** con datos `Binance aggTrades / OpenInterest / Basis` y neutralización beta-ajustada antes de autorizar apertura conjunta del holdout `18m`.
2. **Índices globales + FX + Oro/WTI en `data/m1dk/` (`DEUIDXEUR`, `EUSIDXEUR`, `GBRIDXGBP`, `JPNIDXJPY`, `EURUSD`, `USDJPY`, `XAUUSD`, `LIGHTCMDUSD`)**: M1 continuos limpios (hasta `2026-09-29`, cero glitches `Yahoo =F`) en **horarios Asia/Europa**, descorrelacionados del bloque NY `09:30–11:30 ET` y sin colisionar con `F-LIT-MACRO-CFD` ni `F-MULTIACTIVO-MECANISMOS` (exige hipótesis económicas específicas por sesión y filtro de fricción `< 0.08 R`, nunca barridos crudos).
3. **`FundedSync O` a 1 micro fijo + paridad NT8 (`F-FS-O-N-A5`) y compresión de volatilidad `Carril 2` (`F-COMPRESION-VOL-CRECE`)**: `O` confirmó `REP p=0.025` (apagado en vendedor sólo por margen); resolver paridad de `N` (`950` vs `881`), `Franklin` y `ES5N` en NT8; y en `Carril 2` separar reglas de compresión/volatilidad vivas en `2019–2026` antes de una apertura conjunta pre-registrada de `HOLDOUT A5` (`Carril 2 63m + Cripto 18m`, potencia conjunta `0.30 / 0.46 / 0.72`).
4. **Información nueva no-OHLC (`liquid_tick_v1` y `F-TURTLES-ORO-MESETA`)**: aprobar para research los ticks de `liquid_tick_v1` para atacar `F-HFT-CLUSTER-GRANDE-NO-DEFIENDE` (`z=2.2` en `RTY+YM+6E+6B`) y revisar `F-TURTLES-ORO-MESETA` en oro M1 limpio.
5. **Futuros No-Equity únicamente con datos back-adjusted reales**: usar continuos back-adjusted verificados (Stooq / Databento / export back-adjusted de NT8) + primas `VIX/VIX3M` de [cboe_volatility_daily.parquet](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab-cartera/data/m1nt8/cboe_volatility_daily.parquet); **prohibido** re-evaluar sobre Yahoo `=F`.

Aporte al referente: quedan corregidos los 7 sesgos de medición e integrados `CRIPTO-PIT v2` escalonado ex-TradFi y el marco a volatilidad idéntica (`10%`) con `CSCV` no contaminado, fijando un roadmap de 5 frentes medidos únicamente por expectativa neta, OOS sellado y ejecutabilidad real por vehículo.
