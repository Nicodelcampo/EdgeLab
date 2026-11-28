# Roadmap de Frentes de Continuación (Handoff Técnico para Claude y Nico — 2026-11-26)

Estado: PROPUESTA (Antigravity, 2026-11-26). Orden y reparos de Claude: `REVISION_CLAUDE.md` §3.

**Rama:** `audit/cartera-opt-20261126` (base `709ef588`, sin modificar archivos previos del repo)  
**Principios rectores (North Star + `docs/DECISIONES_20261126.md`):**
- **Objetivo:** ↑ rentabilidad neta, ↑ estabilidad (`t` mensual, `%` años/meses `+`, Sortino/Calmar), ↑ `n` muestral y cantidad de estrategias activas, ↓ drawdown intradía y colas `P95/P99`, ↑ diversificación efectiva (`N_eff`) y ↑ decorrelación real entre motores, activos y horarios.
- **Guardas innegociables:** No apagar estrategias por rendimiento reciente (`DECISIONES_20261126.md`), **0 lecturas `>= 2026-10-01`** (`HOLDOUT-A4`), familias nuevas estrictamente en `A5 DESC -> REP` manteniendo `HOLDOUT/EMBARGO/TERMINAL` sellados, respetar los `68` descartes `NO_REPETIR` (`docs/research/FACTORES.jsonl`), y costos canónicos en `edgelab/costos.py`.

---

## Frentes Priorizados (de Mayor Impacto Inmediato a Mayor Expansión Estructural)

### Frente 1 — Producción Inmediata en `NT8` (`EdgeLabCartera.cs` + Futuros Prop `LucidFlex` / `Tradeify`)
- **Diagnóstico resuelto hoy:** La selección exacta de `REGLA-CARTERA` (`Claude_Regla`) depende de `FS_F_NQ` (`FabioOrb`) y `FS_C_NQ` (`CapstoneGap`), que **no existen en C# (`NT8`)**, fallan A5 (`FS-NFCO-A5`) y tienen `Sharpe < 0.25` en `2012-2026`. Además `FS_O_NQ` quedó congelada en `0` ops desde `2025-10-14` por un tope de margen/cierre.
- **Acción concreta:**
  1. Implementar en `nt8/strategies/EdgeLabCartera.cs` un nuevo preset **`ReglaV2Clean`** con los `8` motores `100%` intradía EOD que sí tienen respaldo causal largo: `T_NQ`, `FR_NQ`, `RQ5_ES`, `R_ATR50_NQ` (`R` con stop catastrófico `0.50*ATR20`), `Z_ATR50_NQ`, `V_nm30_tp1400_NQ`, `N_ATR25_NQ` (`NDayLong` ya existe en `Core.cs`) y `SOM_eod_NQ` (`SOMEOD` ya existe en `Core.cs`).
  2. Resultado ya probado en `WF 2021-07 -> 2026-09` (`OOS`): Sharpe **`1.94`**, Sortino **`7.17`**, Calmar intradía **`2.34`**, tramo `May-Sep 2026` **`+\$14,449`** (a igual volatilidad que `Actual_Base` `-\$4,806`). En `LucidFlex 150K` con política **Grossman-Zhou**, logra `EV +\$798.6` (`50%` media) / **`+\$2,841.7`** (`100%` media, `60.3%` de pase) sin `F/C`.
  3. Añadir soporte `O_qty1_ATR50` (sin tope de `25k`) **exclusivamente** al preset `Interdia / Futuros Broker` (nunca en cuentas Lucid intradía ni CFD con swap).
  4. Completar paridad M1/NT8 de `N_ATR25` y `W_eod_ATR25` antes de pasar a papel/forward.

### Frente 2 — Escalado del Nuevo Frente Cripto (`Binance Futures USDT-M`) — Mayor Salto en `DR` y Reducción de `DD`
- **Por qué es prioridad #1 en investigación:** Con sólo `8` perpetuos y `5` reglas simples (`2020-09 -> 2026-09`, net `10 bps` RT + funding `8H` real), `3/5` sobrevivieron `DESC` **y** `REP` (`CR_Donchian_1D`, `CR_Trend_4H_EMA`, `CR_XSMOM_Neutral`). La cartera `HRP` dio OOS `REP Sharpe 1.443` / Calmar `3.72` y **correlación mensual de apenas `+0.024` vs `CME_MIXTO`**, reduciendo el drawdown intradía conjunto de `-\$16,256` a `-\$7,873` (`50/50` vol-matched) y la cola `DD P95` anual del Broker Multi-Frente en **`-33%`**. El `HOLDOUT A5` cripto sigue **100% sellado**.
- **Acciones concretas (manteniendo `HOLDOUT A5` y `TERMINAL` sellados):**
  1. Ampliar universo de `8` a **`20–30` perpetuos USDT-M** de alta liquidez en `data.binance.vision` (`< 2026-10-01`: `ADA, SUI, TON, ARB, OP, NEAR, APT, INJ, LTC, BCH, DOT, UNI, AAVE, ATOM, FIL, TIA, SEI, FET, RENDER`, verificando historial mínimo o entrada dinámica sin sesgo de supervivencia).
  2. Probar `4` familias ortogonales adicionales (`DESC -> REP`):
     - **Stat-Arb Residual Market-Neutral:** reversión de retornos residuales ortogonalizados contra factor `BTC+ETH` (`1D` / `4H`).
     - **Open Interest / Basis / Long-Short Ratio (`data.binance.vision/data/futures/um/daily/metrics`):** carry y desapalancamiento extremo combinados con régimen de tendencia.
     - **Trend Multi-Horizonte (`15m/1H/4H/1D` blend):** suavizado de señal para bajar rotación de `509` ops/mes (`CR_Trend_4H_EMA`) y capturar más netos tras comisiones maker/taker.
     - **Microestructura real en ticks (`aggTrades` con `is_buyer_maker`):** desequilibrio agresor (`OFI`) y cascadas de liquidación/absorción, usando ticks gratuitos reales de `Binance Vision` y `Bybit`.
  3. Validar ejecución real (`maker` limit offset vs `taker` `10 bps` RT + deslizamiento en volatilidad alta) antes de abrir `HOLDOUT A5` cripto con plan de potencia.

### Frente 3 — Expansión en Activos Globales NO-Equities (Energía, Metales, Tasas/Bonos, Índices Asia/Europa)
- **Lección empírica del barrido Kaggle (`15` mercados x `6` mecanismos = `99` candidatos):** El filtro estricto `A5 DESC > 0` **y** `REP > 0` eliminó `91/99` heurísticas genéricas (todo `FADE`, `PRECLOSE`, `FTSE`, `EURUSD`). No conviene insistir en más variantes de renta variable EE. UU. intradía (`F-CARTERAS-LOCALES-INTRADIA-REDUNDANTES`, `F-MULTIACTIVO-INDICES-ORO-NO-DIVERSIFICA`).
- **Activos y mecanismos a profundizar (`DESC -> REP`, cuidando no duplicar `NO_REPETIR`):**
  1. **Energía (`CL/MCL`, `LIGHTCMDUSD`, `BRENT`, `GAS`):** `DK_WTI_DON` (`55/20`) fue el único sobreviviente `vivo=True` estricto (`DESC Sh=0.563`, **`REP Sh=0.880`**, `yr+=80%`). Probar canasta multi-horizonte Trend Following (`20/10`, `55/20`, `120/60`) + ajuste de volatilidad en Crudo, Brent y Gas Natural (futuros `CL/MCL` sin swap).
  2. **Bonos y Tasas (`ZB`, `ZN`, `USTBONDTRUSD`, `BUNDTREUR`, `UKGILT`):** Clase de activo hoy **ausente** en la cartera (descorrelación macro estructural en caídas de renta variable). Bajar ticks faltantes de Dukascopy/Databento y probar tendencia multi-día + efecto fin de mes (`Q/TOM` en bonos) en A5.
  3. **Metales (`GC/MGC`, `SI/SIL` Plata, `HG/MHG` Cobre):** Aprovechar **`DK_XAU_DON`** (`REP Sh=0.573`) y descargar **`SI` (Plata)** desde Hugging Face `syncster-data` (`2.09M` ticks/archivo) + `XAGUSD`/`COPPERCMDUSD` de Dukascopy para armar bloque Trend de Metales.
  4. **Índices fuera de EE. UU. sobrevivientes:** Profundizar **`DK_DAX_ORB`** (`n=2,640`, `DESC 0.370`, `REP 0.223`) con calibración a ticks Exness/Dukascopy y **`DK_NKD_OVN_RAW`** (`19-26 Sh=0.447`, `yr+=66.7%`) / **`CME_RTY_OVN_RAW`** (`DESC 0.745`, `REP 0.384`) en cuentas sin swap.

### Frente 4 — Cosechar Pistas Vivas de `docs/research/FACTORES_CON_VENTAJA.md` en `CME`
- **`Z-banda` (`F-Z-SEVERIDAD-DOSIS-RESPUESTA`):** Promedio de las `9` configuraciones equivalentes de `Z` (correlación diaria `~0` con `T` y `R`; ya mostró `T+R+Z -> Sharpe 2.38` vs `2.11`). Integrarla como serie separada al pool limpio y compararla contra `Z_ATR50_NQ`.
- **`A20` con peso acotado (`F-A20-SOLO-CORTA-HOLDOUT-TERMINAL`):** `A20` tiene beta **`-0.51` con NQ** (`+1.10 R/op` en el holdout terminal de oct-nov 2026). Nunca como estrategia dominante (`DD -90 R` si entra al `100%`), pero sí evaluarla en `MaxDiv / HRP` con tope estricto (`w <= 0.08–0.10`) como seguro explícito contra meses bajistas de índices.
- **`Franklin` en días volátiles (`F-FRANKLIN-DIAS-VOLATILES`):** Confirmar el contraste pre-registrable en **`YM + EMD + RTY + GC`** (tercio superior de `ATR20` o `VIX` previo; jamás medido aún en esos instrumentos).
- **Reversión multi-día con filtro de régimen/crash (`F-REVERSION-CORTA-APAGADA-2018`, `F-COMPRESION-VOL-CRECE`):** Sólo para cuenta **Broker / FTMO**, probar `IBS / Double Seven` con filtro de crash ex-ante definido en `REP`, más compresión de volatilidad implícita (`VIX/VXN`).

### Frente 5 — Expansión Real de Muestra de Ticks (`< 2026-10-01`) y Cierre de Costos Estimados
- **Ingesta verificada fuera de tus datasets Kaggle (`PROBE_NEW_TICKS_DEEP.json`):**
  1. **`Exness` (`ticks.ex2archive.com`, `2020-2026`):** `USTEC_Raw_Spread` (`~44.5k` ticks/día), `USOIL_Raw_Spread` (`~32.3k`/día), `US500`, `US30`, `XAUUSD`, `EURUSD` -> permite recalibrar spreads reales por año y validar réplica M1->ticks fuera de Dukascopy.
  2. **Hugging Face `syncster-data/historical-market-data`:** Extraer **`SI` (Plata)** completo + ticks `ES/NQ/GC` `2025-2026` (con guarda estricta `< 2026-10-01`) y `VIX`.
  3. **`Dukascopy` (`tools/dukascopy_descarga.py`, `PAUSA_S >= 0.6`):** Completar los símbolos faltantes en Kaggle (`LIGHTCMDUSD`, `XAGUSD`, `DEUIDXEUR`, `JPNIDXJPY`, `USSC2000IDXUSD`, `USTBONDTRUSD`, `BUNDTREUR`).
  4. **`Databento` (`\$125` crédito gratis):** Descargar ventanas puntuales L1/MBO oficiales de `RTY/M2K`, `CL/MCL`, `NKD`, `SI/SIL`, `ZB/ZN`, `EMD` y `6J` para reemplazar todos los `spread_estimado: true` de `config/costos/costos_canonicos.json` por mediciones reales.

### Frente 6 — Ingeniería de Tamaño Dinámico y Asignación Específica por Tipo de Cuenta
- **Futuros Prop (`LucidFlex 50K/150K`, `Tradeify SelectFlex 150K`):** En nuestro MC `20,000` rutas quedó demostrado que `HRP/ERC/MaxDiv/Discrete` a escala completa (`13-16` micros) sufren **exceso de riesgo bruto** frente a un MLL de `\$2,000–\$4,500`. Siguiente paso: optimizar en Walk-Forward el **multiplicador escalar de cartera `k_vol`** (objetivo `sd_mes ~ \$1,100–\$1,600` en `50K`, `\$2,200–\$2,800` en `150K`) sobre los pesos relativos de `HRP / MaxDiv / Regla_V2_Clean` + freno dinámico **Grossman-Zhou / LockStep** en fase fondeada.
- **CFDs (`FTMO 100K`):** Explotar el tamaño **fraccionario continuo** de `MIXTO_MaxDiv` / `Discrete_Micro_Opt` (`EV +\$2,946` al `50%`, `+\$7,234` al `100%`), incorporando `DK_WTI_DON` y `DK_DAX_ORB` (sin swap intradía en `ORB` y con bajo swap en tendencias acotadas).
- **Broker Personal Multi-Frente:** Implementar rebalanceo trimestral `HRP` o `MaxDiv` con **Vol-Targeting agregado de cartera** (evitar concentración de riesgo en tramos de volatilidad extrema sin apagar estrategias individualmente).

---

## Índice de Archivos Entregados para Claude

- **Informe maestro:** `docs/research/auditoria_cartera_20261126/RESULTADO.md`
- **Roadmap / Handoff:** `docs/research/auditoria_cartera_20261126/ROADMAP_FRENTES_CONTINUACION.md`
- **Auditoría forense:** `tools/audit_regla_cartera.py` → `AUDITORIA_RESUMEN.json`, `SERIES_AUDITORIA_DIARIAS.csv.gz`, `SERIES_AUDITORIA_MIN_INTRADIA.csv.gz`, `cache_O_qty1_nq.pkl`
- **`ADAPTAR-PRESENTE 2`:** `tools/adaptar_presente_v2.py` → `ADAPTAR_PRESENTE_V2.json`
- **Expansión CME + M1DK:** `tools/expansion_cartera_multiactivo.py` → `EXPANSION_MULTIACTIVO.json`, `SERIES_EXPANDIDAS_DIARIAS.csv.gz`, `SERIES_EXPANDIDAS_MIN_INTRADIA.csv.gz`
- **Kernel Kaggle 1 (`15` mercados x `6` mecanismos):** `docs/research/auditoria_cartera_20261126/kaggle_m1_expansion/kaggle_m1_expansion.py` → `kaggle_m1_out/{KAGGLE_M1_EXPANSION.json, KAGGLE_M1_DAILY_DR.csv.gz, KAGGLE_M1_MIN_DR.csv.gz}` (slug: `nicolasbuttaro/edgelab-multiactivo-m1-expansion-20261126`)
- **Frente Cripto Binance Futures:** `tools/cartera_cripto_binance.py` → `CARTERA_CRIPTO_RESUMEN.json`, `SERIES_CRIPTO_DESC_REP.csv.gz`, `SERIES_CRIPTO_MIN_DESC_REP.csv.gz`
- **Optimización OOS `7` asignadores + MC `20k`:** `tools/optimizar_cartera_v2.py` + `kaggle_mc20k/kaggle_mc20k.py` → `OPTIMIZACION_CARTERAS.json`, `OOS_{INTRADIA,MIXTO,MULTIFRENTE}_7M.csv.gz`, `kaggle_mc20k_out/KAGGLE_MC20K_RESUMEN.json` (slug: `nicolasbuttaro/edgelab-cartera-mc20k-20261126`)
- **Sondeo de nuevas fuentes de ticks:** `tools/probe_tick_sources.py`, `tools/probe_new_ticks_deep.py` → `probe_tick_sources.json`, `PROBE_NEW_TICKS_DEEP.json`
- **Gráficos comparativos (`4`):** `tools/generar_graficos_cartera.py` → `auditoria_claude_regla_vs_fixes.png`, `expansion_multiactivo_y_decorrelacion.png`, `cartera_cripto_y_supercartera_multifrente.png`, `optimizacion_carteras_oos_y_props.png`
