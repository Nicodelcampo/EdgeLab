# HOLDOUT-A5-NOCME: Apertura Única Conjunta de `HOLDOUT A5` (`< 2026-10-01`) con Levantamiento de `K27` (4 Frentes Limpios No-CME) (pre-registro, 2026-11-27)

Estado: PREREGISTRO — campaña de confirmación **Etapa EF4** pre-registrada e inmutable antes de cualquier lectura de `HOLDOUT A5` (`< 2026-10-01`). **Compuerta K27 levantada por autorización escrita explícita de Nico (2026-11-27):** `«abrimos el holdout para k27» -> confirmación explícita: «Apertura conjunta No-CME (4 frentes: CARRIL2_A5 63m + MACRO_RISK_PREMIA 63m + CRIPTO_BINANCE 18m + CRIPTO_ORDERFLOW_PIT 18m) — máxima potencia (0.46 a 0.7x / 0.72 a 1.0x), confirma a la vez Carril 2 (ya pre-registrado) y toda la Super_v3_NoCME_HRP congelada; TERMINAL (>= 2026-10-01) sigue sellado»`. **`TERMINAL` (`>= 2026-10-01`) y las familias no autorizadas (`Global_VolComp_M1DK`, `CME_TRZV`) NO se leen.**

- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF4** (confirmación única sobre el bloque `HOLDOUT` intercalado de `HOLDOUT-A5`, `2006-01 -> 2026-09-30`, cero sesiones `>= 2026-10-01`).
- **Familias y pruebas contadas (`4` nuevas + `1` ya contada):**
  1. `CARRIL2_A5` (`63m` sellados, `1` prueba ya pre-registrada y contada en `docs/research/canasta_amplia_20261127/PREREGISTRO_HOLDOUT_CARRIL2.md` -> `CANASTA-AMPLIA-HOLDOUT-C2-20261127`).
  2. `MACRO_RISK_PREMIA` (`63m` sellados, `1` prueba nueva: `RP_Canasta_InvVol`).
  3. `CRIPTO_BINANCE` (`18m` sellados, `1` prueba nueva: `CR3_Canasta_InvVol`, dejando asentado con transparencia que su `REP` tuvo iteración previa entre `v1–v3`, mientras `HOLDOUT A5` está 100% virgen).
  4. `CRIPTO_ORDERFLOW_PIT` (`18m` sellados, `1` prueba nueva: `OFI_Canasta_InvVol`, `0` iteración previa de `REP`).
  5. `CANASTA_AMPLIA` (`63m` / `18m` sellados, `1` prueba nueva del pool conjunto No-CME: `Pool_NoCME_Dyn_4F_63m` junto a sus cortes congelados `Super_v3_Clean63m_EQ/HRP` y `Super_v3_NoCME_HRP`).

Cambio respecto a falla previa: en aperturas individuales anteriores (`SOM`, `Franklin`, `Turtles`, reglas aisladas de `Carril 2`), las pruebas sueltas carecían de potencia (`K27`); en `F-YAHOO-FUTUROS-ROLL-NO-AJUSTADO` los empalmes `=F` introdujeron saltos falsos por roll sin ajuste (reemplazados acá por `MACRO_RISK_PREMIA` sobre ETFs `adjclose` limpios + índices `^TNX`/`^IRX`); y `Global_VolComp_M1DK` (transferencia VIX con `corr = 0.48` vs `US_VZ_EVRP`) queda excluido del pool limpio. En esta apertura conjunta se combinan únicamente los `4` frentes No-CME ortogonales congelados en `DESC` antes de mirar un solo mes `HOLDOUT A5`, bajo autorización escrita explícita de Nico levantando `K27` y manteniendo `TERMINAL >= 2026-10-01` estrictamente sellado.

Antecedentes:
- `docs/research/canasta_amplia_20261127/PREREGISTRO_HOLDOUT_CARRIL2.md`
- `docs/research/macro_risk_premia_20261127/RESULTADO.md`
- `docs/research/cripto_pit_v3_20261127/RESULTADO.md`
- `docs/research/cripto_ofi_20261127/RESULTADO.md`
- `docs/research/supercartera_v3_20261127/RESULTADO.md`

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 levantado explícitamente por autorización escrita de Nico 2026-11-27; K36 causalidad estricta `shift(1)`; K49/K51 conteo global previo; paridad exacta verificada en `DESC+REP` antes de leer `HOLDOUT A5`; cero lectura de `TERMINAL >= 2026-10-01`).

Potencia previa: parámetros congelados en `DESC` / `DESC+REP` y potencias teóricas a una cola (`alpha = 0.05`) con `0.5x / 0.7x / 1.0x` del efecto observado (confirmando apertura única pese a `< 0.80` por autorización escrita de Nico):
- `CARRIL2_A5` (`Carril2_Sell16`, `63m` HOLDOUT): `SR_DR = 0.857`, potencias `0.253` (`0.5x`) / `0.393` (`0.7x`) / `0.625` (`1.0x`) (ver `PREREGISTRO_HOLDOUT_CARRIL2.md`).
- `MACRO_RISK_PREMIA` (`RP_Canasta_InvVol = {RP4_Rates_Curve_Credit: 1.0}`, `63m` HOLDOUT): `mean_DR = 0.001143`, `sd_DR = 0.010838` (`sd_DESC = 0.011246`), `SR_DR = 0.365`, potencias `0.110` (`0.5x`) / `0.145` (`0.7x`) / `0.210` (`1.0x`).
- `CRIPTO_BINANCE` (`CR3_Canasta_InvVol = {CR3_XSMOM_21d_Stag5d: 0.3858, CR3_XSMOM_BetaNeut_Stag5d: 0.3568, CR3_BAB_LowVol_Stag5d: 0.2574}`, `20 bps + funding`, `18m` HOLDOUT): `mean_DR = 211.8 USD/m`, `SR_DR = 1.29`, potencias `0.184` (`0.5x`) / `0.289` (`0.7x`) / `0.483` (`1.0x`). *(Nota: `REP` iterada entre `v1–v3`, `HOLDOUT A5` 100% sellado).*
- `CRIPTO_ORDERFLOW_PIT` (`OFI_Canasta_InvVol = {OFI1_TakerFlow_21d_Stag5d: 0.5317, OFI3_WhaleFlow_14d_Stag5d: 0.4683}`, `20 bps + funding`, `18m` HOLDOUT): `mean_DR = 167.5 USD/m`, `SR_DR = 0.60`, potencias `0.100` (`0.5x`) / `0.130` (`0.7x`) / `0.181` (`1.0x`). *(`0` iteración de `REP`).*
- **`Pool_NoCME_Dyn_4F_63m`** (`63m` HOLDOUT: `Carril2_Sell16 + Macro_RP_Canasta` normalizados por `sd_DESC` en `2006–2020`, y los `4` frentes normalizados por `sd_DESC` en `2021–2026`): `mean_DR = 0.183827`, `sd_DR = 0.647191`, `SR_DR = 0.984`, potencias **`0.302` (`0.5x`) / `0.474` (`0.7x`) / `0.729` (`1.0x`)**.
- **`Super_v3_Clean63m_EQ` / `HRP`** (`63m` HOLDOUT, `0` iteración `REP`, `Carril2_Sell16 + Macro_RP_Canasta` pesos `EQ = 0.50 / 0.50`, `HRP = 0.4822 / 0.5178`): `SR_DR = 0.847 / 0.835`, potencias `0.250` (`0.5x`) / `0.387` (`0.7x`) / `0.616` (`1.0x`).
- **`Super_v3_NoCME_HRP`** (`18m` HOLDOUT, `2021–2026`, pesos HRP `DESC` `0.2945 / 0.2681 / 0.2344 / 0.2031`): `mean_DR = 0.212437`, `sd_DR = 0.473676`, `SR_DR = 1.554`, potencias **`0.244` (`0.5x`) / `0.377` (`0.7x`) / `0.602` (`1.0x`)**.

Diagnóstico de mecanismo: no aplica — cero grilla; todas las reglas, universos, parámetros, pesos internos de canastas (`PESOS_CARRIL2_SELLADA.json`, `RP4 = 1.0`, `CR3_Canasta_InvVol`, `OFI_Canasta_InvVol`), escalados `sd_DESC` y pesos `HRP` (`Clean63m` y `NoCME 21–26`) están 100% congelados en `DESC` antes de leer ningún mes `HOLDOUT A5`.

## Criterio de Lectura Congelado (decidido antes de mirar `HOLDOUT A5`)
- **Primario (determina el veredicto de cada frente y del pool conjunto en `HOLDOUT A5`):**
  - **`CONFIRMA`**: `t` mensual de una cola `>= 1.645` (`p_una_cola <= 0.05`) en los meses `HOLDOUT A5` (`63` meses en `2006–2026-09` para `CARRIL2_A5`, `MACRO_RISK_PREMIA`, `Super_v3_Clean63m` y `Pool_NoCME_Dyn_4F_63m`; `18` meses en `2021–2026-09` para `CRIPTO_BINANCE`, `CRIPTO_ORDERFLOW_PIT` y `Super_v3_NoCME_EQ/HRP`).
  - **`NO_CONCLUYENTE`**: `media > 0` y `0 < t < 1.645`. Se reporta explícitamente junto a la potencia previa y la combinación exploratoria de Stouffer (`(t_REP + t_HOLDOUT) / sqrt(2)`) sin reemplazar el veredicto puro de `HOLDOUT`.
  - **`EN_CONTRA`**: `media <= 0` en los meses `HOLDOUT A5`.
- **Combinaciones informadas aparte:**
  - `Stouffer(REP, HOLDOUT)` por frente/cartera; y prueba combinada de **Fisher** sobre `p` de una cola en `HOLDOUT A5` (`fisher_clean_63m` sobre `Carril2 + Macro_RP`, `df = 4`; y `fisher_4_frentes`, `df = 8`).
- **Secundario (`DIAGNOSTICO`, NO decide veredicto primario):**
  - Reglas individuales (`16` de `Carril 2`, `RP1..RP5`, `Macro_RP_Diag_3Pos`, `CR3_*`, `Cripto_v3_XSMOM_BAB`, `OFI1..OFI3`), sensibilidad de costos (`2x` en `MACRO_RISK_PREMIA`; `10/20/30/40 bps` en Cripto), épocas (`06–12`, `13–18`, `19–26`, `21–26`), correlaciones empíricas dentro de `HOLDOUT A5`, retención empírica `b = SR_HOLDOUT / SR_DR` y cartera diagnosticada `Pool_NoCME_Poda_Diag` (`Carril2 + RP2/RP4 + XSMOM/BAB + OFI1`).

## Justificación económica
1. Combinar `4` mecanismos económicamente distintos en clases de activos descorrelacionadas (swing/calendario/volatilidad en futuros de índices y oro, régimen macro de pendiente de curva y crédito en ETFs líquidos sin `=F`, momentum transversal + Low-Vol `BAB` neutralizado a BTC en perpetuos crypto PIT, y flujo agresor no-OHLC `taker buy/sell` en Binance) reduce la varianza conjunta al promedio de covarianzas cercanas a cero.
2. Evaluar todos los meses `HOLDOUT A5` de una sola vez con pesos y parámetros congelados en `DESC`, tras verificar paridad matemática exacta en `DESC+REP` y dejando `TERMINAL >= 2026-10-01` intacto, entrega confirmación limpia out-of-sample inmediata sin esperar años de forward calendario.

## Cómo podría refutarse
1. Si cada frente individual o el pool conjunto (`Pool_NoCME_Dyn_4F_63m` / `Super_v3_Clean63m_EQ` / `Super_v3_NoCME_HRP`) arroja `media <= 0` (`EN_CONTRA`) o `0 < t < 1.645` (`NO_CONCLUYENTE`) en `HOLDOUT A5`, lo que se asentará literalmente en `FACTORES.jsonl` sin reajustar parámetros sobre `HOLDOUT`.
2. Si la correlación empírica entre frentes sube sustancialmente en `HOLDOUT A5` (destruyendo el beneficio de cartera), si `MACRO_RISK_PREMIA` o Cripto colapsan bajo estrés de costos en `HOLDOUT`, o si el pool falla en el periodo reciente `2021–2026`.
