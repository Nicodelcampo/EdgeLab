# Handoff Antigravity -> Claude / Nico (2026-11-27, rama `claude/vibrant-clarke-s9z6e2`)

Estado: VIGENTE — índice del trabajo de Antigravity del 2026-11-27; la revisión de Claude está en `auditoria_claude_20261127/REVISION_CLAUDE.md`.

Este documento indexa todo el trabajo ejecutado y auditado por Antigravity sobre `EdgeLab` hasta el cierre de hoy (`2026-11-27`), para que Claude pueda auditarlo y continuar en la misma rama sin depender de la conversación original.

**Invariante de custodia cumplido:** todas las campañas operaron estrictamente en `DESC + REP` (`< 2026-10-01`). **`HOLDOUT A5` (`CARRIL2_A5`, `CRIPTO_BINANCE`, `GLOBAL_VOLCOMP_M1DK`) y `TERMINAL` (`>= 2026-10-01`) NO fueron leídos en ningún cálculo.** Las series diarias publicadas llevan `NaN` explícito en todo bloque fuera de `DESC`/`REP`.

---

## 1. Orden de lectura recomendado

1. `docs/research/auditoria_claude_20261127/RESULTADO.md` — Auditoría forense del PR `#203` (imposibilidad matemática de K27 a `1` familia, decaimiento secular de `Carril 2`, invalidación de Yahoo `=F` sin back-adjustment, fix crypto `ex-TradFi` + `5-tranche` + `Marco Sin Forward` a `10%` vol).
2. `docs/research/cripto_pit_v3_20261127/PREREGISTRO.md` y `RESULTADO.md` — `CRIPTO-PIT v3` (`226` monedas ex-TradFi + `premiumIndexKlines/1d`, `BetaNeut`, `BAB_LowVol`, `Basis_Carry`, `ResidMom_2F`).
3. `docs/research/frentes_ortogonales_20261127/PREREGISTRO.md` y `RESULTADO.md` — Diagnóstico `FundedSync O (qty=1 MNQ)` y transferencia global `F-COMPRESION-VOL-CRECE` sobre `data/m1dk/` (`DAX, EuroStoxx, FTSE, Nikkei, Oro`).
4. `docs/research/supercartera_v2_20261127/PREREGISTRO.md` y `RESULTADO.md` — Integración multi-frente (`Super-Canasta v2`) a volatilidad idéntica `10%` anual (`W-FRI`/`M`), `CSCV` (`12,870` splits), `DSR`, `Bayes`, `Bootstrap 20k semanal` en Kaggle y potencia conjunta de holdouts sellados.

---

## 2. Pruebas contadas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`

| `campaign_id` | Familia | `n_trials` | Nota / Registro | Hash cadena |
| :--- | :--- | :---: | :--- | :--- |
| `AUDITORIA-CRIPTO-PIT-V2-20261127` | `CRIPTO_BINANCE` | `12` | `docs/research/auditoria_claude_20261127/REGISTRO_POSTERIOR.md` | `8e9a2044` |
| `AUDITORIA-FUTNOEQ-V2-20261127` | `TENDENCIA_NO_EQUITY` | `4` | `docs/research/auditoria_claude_20261127/REGISTRO_POSTERIOR.md` | `d5e83660` |
| `AUDITORIA-MARCO-SIN-FORWARD-20261127` | `CANASTA_AMPLIA` | `8` | `docs/research/auditoria_claude_20261127/REGISTRO_POSTERIOR.md` | `28a9edbf` |
| `CRIPTO-PIT-V3-20261127` | `CRIPTO_BINANCE` | `6` | `docs/research/cripto_pit_v3_20261127/PREREGISTRO.md` | `a54817fa` |
| `FRENTES-ORTOGONALES-20261127` | `CANASTA_AMPLIA` | `11` | `docs/research/frentes_ortogonales_20261127/PREREGISTRO.md` | `357c3008` |
| `SUPERCARTERA-V2-20261127` | `CANASTA_AMPLIA` | `4` | `docs/research/supercartera_v2_20261127/PREREGISTRO.md` | `c6c5d022` |

---

## 3. Hallazgos principales y reproducción exacta

### A. `CRIPTO-PIT v3` (`tools/cripto_pit_v3.py`)
- **Datos públicos requeridos (gitignored):** `data/crypto_binance_pit/` y descarga automática en `data/crypto_binance_pit_basis_1d/` desde `data.binance.vision/data/futures/um/monthly/premiumIndexKlines/{sym}/1d/` (`< 2026-10-01`).
- **Comando:** `python -u tools/cripto_pit_v3.py`
- **Resultado (`20 bps RT + funding`, `DESC+REP 51m`):**
  - `CR3_XSMOM_21d_Stag5d`: `Sh = 1.08` (`t = 2.23`, `beta_BTC = +0.004`, `top5_D = 0.299`, `dh = 0`).
  - `CR3_BAB_LowVol_Stag5d`: **`Sh = 0.77`** (`DESC = 0.68`, `REP = 1.04`, `rot = 1.25x/m`, `top5_D = 0.622 < 0.65`, **`corr_m vs XSMOM = -0.217`**).
  - `CR3_XSMOM_BetaNeut_Stag5d`: `Sh = 0.79` (`corr_m vs XSMOM = 0.947`).
  - `CR3_Basis_Carry_Stag5d` (`Sh = 0.34`, `top5_D = 1.486`) y `CR3_ResidMom_21d_2F_Stag5d` (`Sh = 0.17`) quedan fuera de la canasta por la regla fija de `PREREGISTRO`.
  - **`CR3_Canasta_InvVol`** (`XSMOM + BetaNeut + BAB`, pesos `DESC` `0.386 / 0.357 / 0.257`): **`Sh = 1.29` (`t = 2.66`, `p = 0.0039`, `+\$211.8/m`, `69%` meses+, `REP 12m Sh = 1.72`, `beta_BTC = +0.016`, `top5 = 0.228`)**.
  - **Diagnóstico limpio (`Cripto_v3_XSMOM_BAB`, eliminando `BetaNeut` redundante de `0.947` corr):** **`Sh = 1.467` (`t = 3.02`, `REP = 1.925`, `MDD@10% = -6.78%`, `Calmar = 2.16`)**.

### B. `FRENTES-ORTOGONALES-20261127` (`tools/frentes_ortogonales_20261127.py`)
- **Datos requeridos (`data/`):** `NQ_M1_nonadj_utc.parquet` (filtrado `< 2026-09-30 22:00 UTC`), `data/m1dk/{DAX,EuroStoxx,FTSE,Nikkei,Oro}_M1.parquet` (`< 2026-09-30 18:00 NY`), y `cboe_volatility_daily.parquet` (`< 2026-10-01`).
- **Comando:** `python -u tools/frentes_ortogonales_20261127.py`
- **Resultado Bloque A (`FundedSync O qty=1 MNQ`):**
  - Fijar `qty=1` destrabó `36` operaciones en `2025-10..2026-09` (donde el tamaño por defecto congeló en `0`), pero esas `36` operaciones **perdieron `\$-3,041.4`**. Aunque mantiene `corr_m = -0.301` vs `CME_TRZV`, su rendimiento `21–26 DR` baja a `Sh = 0.263` (`REP = -0.008`), y al integrarlo degrada `CME_TRZV` (`2.494 -> 0.899`) y `Super_v2_EQ` (`2.464 -> 1.942`). Se reporta honestamente y **no entra al núcleo recomendado**.
- **Resultado Bloque B (`Global_VolComp_M1DK`, `C2_VZ` y `C2_EVRP` en `data/m1dk/`):**
  - Canasta causal de `7` reglas (`C2_VZ_DAX`, `C2_EVRP_DAX`, `C2_VZ_EuroStoxx`, `C2_VZ_FTSE`, `C2_VZ_Nikkei`, `C2_EVRP_Nikkei`, `C2_EVRP_Oro`, todas `fricR <= 0.056R < 0.08R` a `8 bps RT`): `DESC Sh = 0.415`, `REP (24m) Sh = 0.562`, `109m DR Sh = 0.454`, **`19–26 Sh = 1.132`**, **`21–26 DR Sh = 1.162` (`t = 2.39`, `p = 0.0083`)**.
  - **Cautela explícita de fricción:** a `16 bps RT`, `DAX`, `Nikkei` y `Oro (EVRP)` siguen positivos (`Sh = 0.12–0.21`), mientras que `C2_VZ_EuroStoxx (-0.147)` y `C2_VZ_FTSE (-0.162)` pasan a negativo.
  - **Ortogonalidad confirmada:** correlación mensual `21–26` con `Carril2_Sell16` de apenas **`+0.130`** (semanal `+0.106`), **`-0.327`** vs `CME_TRZV`, y **`+0.051`** vs `Cripto_v3_Canasta`.

### C. `SUPERCARTERA-V2-20261127` (`tools/supercartera_v2_20261127.py` + Kaggle)
- **Kernel Kaggle privado ejecutado:** `nicolasbuttaro/edgelab-supercartera-v2-20261127` (`13.1s`, `hasError=false`).
- **Comandos:**
  - `python -u tools/supercartera_v2_20261127.py --prepare`
  - `python tools/kaggle_kernel.py output --slug nicolasbuttaro/edgelab-supercartera-v2-20261127 --file KAGGLE_SUPER_V2_RESUMEN.json --out docs/research/supercartera_v2_20261127/KAGGLE_SUPER_V2_RESUMEN.json`
  - `python -u tools/supercartera_v2_20261127.py --finalize`
  - `python -u tools/generar_graficos_frentes_20261127.py`
- **Desempeño comparado a `10%` de volatilidad anual propia (`21–26 DR 51m`, `W-FRI`/`M`):**
  - `Carril2_Sell16` [Limpio]: `Sh = 0.505`, `MDD@10% = -11.22%`, `Calmar = 0.45`, `Boot 20k Calmar = 0.59`.
  - `Global_VolComp_M1DK` [Limpio]: `Sh = 1.162`, `MDD@10% = -8.35%`, `Calmar = 1.39`, `Boot 20k Calmar = 1.93`.
  - `Cripto_v3_Canasta` [Limpio]: `Sh = 1.271`, `MDD@10% = -7.79%`, `Calmar = 1.63`, `Boot 20k Calmar = 2.22`.
  - **`Super_v2_NoCME_EQ` (`3` frentes limpios, `0` sesgo CME):** **`Sh = 1.563` (`t = 3.22`, `REP = 3.375`), `MDD@10% = -5.97%`, `Calmar = 2.62` (`Boot 20k SR 1y p50 = 1.686`, `P(año>0) = 93.8%`, `Calmar = 2.65`, `Bayes P(>0.5) = 0.9026`)**.
  - **`Super_v2_Core_TRZV_EQ` (descriptivo con `CME_TRZV`):** **`Sh = 2.859` (`t = 5.89`, `REP = 4.930`), `MDD@10% = -4.56%`, `Calmar = 6.27` (`Boot 20k P(año>0) = 99.6%`, `DSR N=5000 = 0.9624`, estrés `CME 0.5x / Oth 0.7x Sh = 1.738`)**.
- **CSCV limpio en Kaggle (`12,870` splits):**
  - `1_clean_carril2_16rules` (`176m`): `PBO = 0.5538`, `1/N OOS Sh med = 0.851` (`P>0 = 1.000`).
  - `2_clean_non_cme_28rules` (`48m`, `16 Carril2 + 5 Cripto v3 + 7 Global VolComp`): `PBO = 0.687` (esperable con `28` reglas en `48m` por la mejor individual `0.059`), pero **`1/N OOS Sh med = 1.146` (`P>0 = 0.9908`, `P>0.5 = 0.8913`)** — confirma directamente que **promediar mecanismos ortogonales funciona incluso donde elegir la mejor regla sola falla (`1.146` vs `0.059`)**.
  - `3_descriptive_with_cme` (`39` reglas, caveat CME): `PBO = 0.3536`, `1/N OOS Sh med = 2.151`.

---

## 4. Cautelas y decisiones abiertas para Nico / Claude

1. **Sesgo de selección CME:** toda cartera que incluya `CME_TRZV` / `CME_Div10` hereda selección previa del vendedor en `2019–2025` (`upstream_selection_caveat = True`). El desempeño limpio libre de ese sesgo está en `Super_v2_NoCME_EQ` (`Sh = 1.563`, `Boot Calmar = 2.65`).
2. **Potencia conjunta sobre `HOLDOUT A5` sellado (`K27`):** el pool `NoCME 3F` (`Carril2 + Global_VolComp + Cripto v3`) sigue teniendo potencia de `0.38` en `18m` (`21–26`) y `0.539` en `63m` dinámicos bajo contracción `0.7x` (`0.801` a `1.0x`). **Ningún holdout fue abierto.** Nico decide si mantiene `K27` cerrado o autoriza una apertura única del pool completo, o si sumamos antes un `4º` frente limpio no-equity back-adjusted (Databento / Stooq continuo limpio / NT8 futuros reales de tasas-energía-metales) para llevar la potencia conjunta a `0.7x` por encima de `0.70–0.80`.
3. **Poda operativa sugerida en los nuevos frentes (pre-registrar antes si se adopta):**
   - En `CRIPTO-PIT v3`: usar solo `XSMOM_21d_Stag5d + BAB_LowVol_Stag5d` (`Sh = 1.467`, elimina `0.947` de solapamiento con `BetaNeut`).
   - En `Global_VolComp_M1DK`: priorizar `DAX`, `Nikkei` y `Oro (EVRP)` que sobreviven a `16 bps RT`.
