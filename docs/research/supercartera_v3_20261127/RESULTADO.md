# SUPERCARTERA v3: Pozo Limpio 63m Cero-Iteración + HRP Corregido + CSCV (resultado, 2026-11-27)

Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

## 1. Pozo Limpio 63m Cero-Iteración (`2006–2026-09 DESC 144m + REP 42m`, `@10% vol`)
| Cartera / Frente (`186m DR`, cero sesgo CME ni iteración REP) | `DESC Sh` | `REP Sh` | `DR Sh / t` | `MDD@10%` | `Calmar@10%` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Carril2_Sell16_06_26` | `0.801` | `1.073` | **`0.857 / 3.37`** | `-13.24%` | `0.65` |
| `Macro_RP_Canasta_06_26` | `0.298` | `0.642` | **`0.365 / 1.44`** | `-22.77%` | `0.16` |
| `Super_v3_Clean63m_EQ` | `0.786` | `1.048` | **`0.847 / 3.33`** | `-16.43%` | `0.52` |
| `Super_v3_Clean63m_HRP` | `0.772` | `1.038` | **`0.835 / 3.29`** | `-16.87%` | `0.49` |
| `Macro_RP_Diag_3Pos_06_26` | `0.32` | `0.816` | **`0.425 / 1.67`** | `-17.31%` | `0.25` |
| `Super_v3_Clean63m_Diag3Pos_EQ` | `0.839` | `1.155` | **`0.916 / 3.61`** | `-11.04%` | `0.83` |

- **Pesos HRP corregidos (`0.85*S + 0.15*diag(S)`, semanas `DESC`)**: `Clean63m = {'Carril2_Sell16': 0.4822, 'Macro_RP_Canasta': 0.5178}`, `NoCME 21-26 = {'Carril2_Sell16': 0.2945, 'Macro_RP_Canasta': 0.2681, 'Cripto_v3_Canasta': 0.2344, 'Cripto_OFI_Canasta': 0.2031}`, `Core_TRZV = {'CME_TRZV': 0.1736, 'Carril2_Sell16': 0.2178, 'Macro_RP_Canasta': 0.2292, 'Cripto_v3_Canasta': 0.2033, 'Cripto_OFI_Canasta': 0.1762}`.
- **Correlación mensual `Carril2_Sell16` vs `Macro_RP_Canasta` (`06–26`)**: `0.043` (`21–26`: `0.042`).

## 2. Frentes `2021–2026-09` (`51m DR`, `@10% vol`) y Estrés `CME 0.5x`
| Cartera / Frente | Sesgo CME | `DESC Sh` | `REP Sh` | `DR Sh / t` | `MDD@10%` | `Calmar@10%` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CME_TRZV` | Sí (`upstream`) | `2.693` | `1.887` | **`2.494 / 5.14`** | `-3.76%` | `6.63` |
| `Carril2_Sell16` | **NO (Limpio)** | `0.133` | `3.066` | **`0.505 / 1.04`** | `-11.22%` | `0.45` |
| `Macro_RP_Canasta` | **NO (Limpio)** | `0.708` | `1.244` | **`0.765 / 1.58`** | `-13.64%` | `0.56` |
| `Cripto_v3_Canasta` | **NO (Limpio)** | `1.161` | `1.628` | **`1.271 / 2.62`** | `-7.79%` | `1.63` |
| `Global_VolComp_M1DK` | **NO (Limpio)** | `0.762` | `2.188` | **`1.162 / 2.39`** | `-8.35%` | `1.39` |
| `Super_v3_Clean63m_EQ_21_26` | **NO (Limpio)** | `0.587` | `2.659` | **`0.878 / 1.81`** | `-8.3%` | `1.06` |
| `Super_v3_NoCME_EQ` | **NO (Limpio)** | `1.339` | `2.757` | **`1.594 / 3.29`** | `-8.12%` | `1.96` |
| `Super_v3_NoCME_HRP` | **NO (Limpio)** | `1.263` | `2.98` | **`1.554 / 3.2`** | `-7.57%` | `2.05` |
| `Super_v3_Core_TRZV_EQ` | Sí (`upstream`) | `2.299` | `3.147` | **`2.49 / 5.13`** | `-3.5%` | `7.12` |
| `Super_v3_Core_TRZV_HRP` | Sí (`upstream`) | `2.14` | `3.257` | **`2.368 / 4.88`** | `-3.73%` | `6.36` |

## 3. Potencia Teórica Conjunta sobre `HOLDOUT A5` Sellado (sin abrir holdouts)
| Bloque / Pool | Meses `DR` | `SR_DR` | `N_sellado` | Pot. `0.5x` | Pot. `0.7x` | Pot. `1.0x` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `1_Carril2_Sell16_06_26` | `186` | `0.857` | `63` | `0.253` | `0.393` | `0.625` |
| `2_Macro_RP_Canasta_06_26` | `186` | `0.365` | `63` | `0.11` | `0.145` | `0.21` |
| `3_Pool_Clean_63m_ZeroIter` | `186` | `0.847` | `63` | `0.25` | `0.387` | `0.616` |
| `4_Pool_Clean_63m_HRP` | `186` | `0.835` | `63` | `0.245` | `0.38` | `0.605` |
| `5_Pool_NoCME_Dyn_63m` | `186` | `0.968` | `63` | `0.296` | `0.463` | `0.717` |

## 4. Kaggle CSCV (`12,870` splits), Bootstrap 20k Semanal y Bayes
- **`1_clean_long_06_26`** (`LIMPIO_SIN_CME`, `T=176m`, `K=21`): `PBO=0.5239`, `best OOS=0.302`, **`1/N OOS Sh med=0.838` (`P>0=1.0`)**.
- **`2_clean_nocme_21_26`** (`LIMPIO_SIN_CME`, `T=48m`, `K=29`): `PBO=0.5512`, `best OOS=0.18`, **`1/N OOS Sh med=0.797` (`P>0=0.9284`)**.
- **`3_desc_all_21_26`** (`DESCRIPTIVO_SESGO_CME`, `T=48m`, `K=40`): `PBO=0.2327`, `best OOS=0.888`, **`1/N OOS Sh med=1.736` (`P>0=1.0`)**.

| Cartera (`Boot 20k @ 10% vol`) | `SR 1y p50` | `P(año>0)` | `MDD p50` | `MDD p95` | `Calmar p50` | `Bayes P(>0.5)` | `DSR(N=5000)` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Carril2_Sell16_06_26` | `0.868` | `78.4%` | `-7.22%` | `-18.18%` | `1.12` | `0.8479` | `0.386` |
| `Macro_RP_Canasta_06_26` | `0.309` | `62.4%` | `-7.85%` | `-17.21%` | `0.37` | `0.2195` | `0.0111` |
| `Super_v3_Clean63m_EQ` | `0.816` | `78.6%` | `-6.91%` | `-16.93%` | `1.11` | `0.8396` | `0.3694` |
| `Super_v3_Clean63m_HRP` | `0.78` | `77.8%` | `-6.92%` | `-16.8%` | `1.07` | `0.8281` | `0.3515` |
| `Super_v3_NoCME_EQ` | `1.456` | `92.9%` | `-6.04%` | `-12.28%` | `2.36` | `0.9112` | `0.3581` |
| `Super_v3_NoCME_HRP` | `1.462` | `92.7%` | `-6.17%` | `-12.76%` | `2.3` | `0.8999` | `0.3315` |
| `Super_v3_Core_TRZV_EQ` | `2.289` | `99.2%` | `-4.67%` | `-8.87%` | `4.77` | `0.9977` | `0.9178` |
| `Super_v3_Core_TRZV_HRP` | `2.219` | `98.7%` | `-4.89%` | `-9.37%` | `4.4` | `0.9957` | `0.8694` |
| `CME_TRZV` | `2.463` | `99.8%` | `-3.66%` | `-6.81%` | `6.56` | `0.9977` | `0.9412` |

Diagnóstico de grilla: sin grilla paramétrica (`CSCV` sobre `K` mecanismos ya fijados en `Clean Long`, `NoCME` y `CME`). `HRP` muestral regularizado (`0.85*S + 0.15*diag`) produce pesos distintos de `1/N` cuando difiere la covarianza entre frentes.
Episodios: en `2006–2026-09`, `Super_v3_Clean63m_EQ` (`Carril 2 + Macro_RP`) logra `DR Sh=0.847` (`DESC=0.786`, `REP=1.048`) y `Boot 20k P(año>0)=78.6%`.

- **Aporte al referente**: separa un pozo limpio `63m` verdaderamente libre de sesgo CME y de iteración de `REP` (`Carril 2 + MACRO_RISK_PREMIA`) y corrige `HRP` frente a `LedoitWolf = I`.
