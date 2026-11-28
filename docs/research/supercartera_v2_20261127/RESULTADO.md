# SUPERCARTERA v2: Integración Multi-Frente Ortogonal a Volatilidad Idéntica (`10%`) y CSCV/Bootstrap (resultado, 2026-11-27)

Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

## 1. Desempeño a Volatilidad Idéntica (`10%` anual propia, `2021–2026-09 DESC+REP 51m`, `W-FRI`/`M`)
| Cartera / Frente | Sesgo CME | `DESC (39m) Sh` | `REP (12m) Sh` | `DR (51m) Sh / t` | `Ret@10%` | `MDD@10%` | `Calmar@10%` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `CME_TRZV` | Sí (`upstream`) | `2.693` | `1.887` | **`2.494 / 5.14`** | `+24.94%` | `-3.76%` | `6.63` |
| `CME_Div10` | Sí (`upstream`) | `1.902` | `1.749` | **`1.842 / 3.8`** | `+18.42%` | `-3.95%` | `4.67` |
| `FundedSync_O_1MNQ` | Sí (`upstream`) | `0.443` | `-0.008` | **`0.263 / 0.54`** | `+2.63%` | `-16.86%` | `0.16` |
| `CME_TRZV_plus_O` | Sí (`upstream`) | `1.237` | `0.359` | **`0.899 / 1.85`** | `+8.99%` | `-12.75%` | `0.7` |
| `Carril2_Sell16` | **NO (Limpio)** | `0.133` | `3.066` | **`0.505 / 1.04`** | `+5.05%` | `-11.22%` | `0.45` |
| `Global_VolComp_M1DK` | **NO (Limpio)** | `0.762` | `2.188` | **`1.162 / 2.39`** | `+11.62%` | `-8.35%` | `1.39` |
| `Cripto_v3_Canasta` | **NO (Limpio)** | `1.161` | `1.628` | **`1.271 / 2.62`** | `+12.71%` | `-7.79%` | `1.63` |
| `Cripto_v3_XSMOM_BAB` | **NO (Limpio)** | `1.333` | `1.925` | **`1.467 / 3.02`** | `+14.67%` | `-6.78%` | `2.16` |
| `Super_v2_NoCME_EQ` | **NO (Limpio)** | `1.08` | `3.375` | **`1.563 / 3.22`** | `+15.63%` | `-5.97%` | `2.62` |
| `Super_v2_NoCME_HRP_Weekly` | **NO (Limpio)** | `1.08` | `3.375` | **`1.563 / 3.22`** | `+15.63%` | `-5.97%` | `2.62` |
| `Super_v2_EQ` | Sí (`upstream`) | `2.077` | `3.893` | **`2.464 / 5.08`** | `+24.64%` | `-4.97%` | `4.95` |
| `Super_v2_HRP_Weekly` | Sí (`upstream`) | `2.077` | `3.893` | **`2.464 / 5.08`** | `+24.64%` | `-4.97%` | `4.95` |
| `Super_v2_Core_TRZV_EQ` | Sí (`upstream`) | `2.387` | `4.93` | **`2.859 / 5.89`** | `+28.59%` | `-4.56%` | `6.27` |
| `Super_v2_5F_with_O` | Sí (`upstream`) | `1.85` | `2.195` | **`1.942 / 4.0`** | `+19.42%` | `-6.3%` | `3.08` |

- **Pesos HRP semanal (`DESC`) 4 frentes**: `{'CME_Div10': 0.25, 'Carril2_Sell16': 0.25, 'Global_VolComp_M1DK': 0.25, 'Cripto_v3_Canasta': 0.25}`; **3 frentes limpios (`NoCME`)**: `{'Carril2_Sell16': 0.3333, 'Global_VolComp_M1DK': 0.3333, 'Cripto_v3_Canasta': 0.3333}`.
- **Correlación mensual `Global_VolComp_M1DK` vs `Carril2_Sell16` (`21–26`)**: `0.13` (semanal: `0.106`).

## 2. Estrés de Contracción (`CME 0.5x` vs `Otros 0.5x/0.7x`) a Igual `10%` Volatilidad
| Escenario | `CME_TRZV Sh (Calmar)` | `Super_v2_NoCME_EQ Sh (Calmar)` | `Super_v2_EQ Sh (Calmar)` | `Super_v2_Core_TRZV_EQ Sh (Calmar)` |
| :--- | :---: | :---: | :---: | :---: |
| `CME_1.0x__Oth_1.0x` | `2.494 (6.63)` | `1.563 (2.62)` | `2.464 (4.95)` | `2.859 (6.27)` |
| `CME_0.5x__Oth_0.7x` | `1.247 (2.14)` | `1.094 (1.48)` | `1.548 (2.21)` | `1.738 (2.73)` |
| `CME_0.5x__Oth_0.5x` | `1.247 (2.14)` | `0.782 (0.93)` | `1.232 (1.43)` | `1.43 (1.93)` |

## 3. Potencia Teórica Conjunta sobre `HOLDOUT A5` Sellado (sin abrir holdouts)
| Bloque / Pool | Meses `DR` | `SR_DR` | `N_sellado` | Pot. `0.5x` | Pot. `0.7x` | Pot. `1.0x` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `1_Carril2_Sell16_06_26` | `186` | `0.857` | `63` | `0.253` | `0.393` | `0.625` |
| `2_Global_VolComp_M1DK_14_26` | `109` | `0.454` | `38` | `0.107` | `0.14` | `0.201` |
| `3_Cripto_v3_Canasta_21_26` | `51` | `1.271` | `18` | `0.193` | `0.289` | `0.465` |
| `4_Pooled_C2_plus_Cripto_v3_21_26` | `51` | `1.184` | `18` | `0.179` | `0.265` | `0.423` |
| `5_Pooled_NoCME_3F_21_26` | `51` | `1.563` | `18` | `0.246` | `0.38` | `0.606` |
| `6_Pooled_NoCME_3F_Dyn_06_26` | `186` | `1.087` | `63` | `0.345` | `0.539` | `0.801` |

## 4. Resultados Kaggle: CSCV (`12,870` splits), DSR (`N=5000`), Bayes & Bootstrap 20k Semanal
- **`1_clean_carril2_16rules`** (`LIMPIO_SIN_CME`, `T=176m`, `K=16`): `PBO=0.5538`, `1/N OOS Sh med=0.851` (`P>0=1.0`).
- **`2_clean_non_cme_28rules`** (`LIMPIO_SIN_CME`, `T=48m`, `K=28`): `PBO=0.687`, `1/N OOS Sh med=1.146` (`P>0=0.9908`).
- **`3_descriptive_with_cme`** (`DESCRIPTIVO_SESGO_VENDEDOR_CME`, `T=48m`, `K=39`): `PBO=0.3536`, `1/N OOS Sh med=2.151` (`P>0=1.0`).

| Cartera (`Boot 20k semanal @ 10% vol`) | `SR 1y p50` | `P(año>0)` | `MDD p50` | `MDD p95` | `Calmar p50` | `Bayes P(>0.5)` | `DSR(N=5000)` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `CME_TRZV` | `2.461` | `99.8%` | `-3.66%` | `-6.89%` | `6.53` | `0.9977` | `0.9412` |
| `Carril2_Sell16` | `0.519` | `67.4%` | `-8.25%` | `-19.8%` | `0.59` | `0.3259` | `0.0062` |
| `Global_VolComp_M1DK` | `1.201` | `89.2%` | `-6.04%` | `-12.73%` | `1.93` | `0.7366` | `0.0971` |
| `Cripto_v3_Canasta` | `1.344` | `90.5%` | `-5.8%` | `-11.88%` | `2.22` | `0.7922` | `0.1262` |
| `Super_v2_NoCME_EQ` | `1.686` | `93.8%` | `-6.24%` | `-12.84%` | `2.65` | `0.9026` | `0.3345` |
| `Super_v2_NoCME_HRP_Weekly` | `1.683` | `93.9%` | `-6.24%` | `-13.05%` | `2.65` | `0.9026` | `0.3345` |
| `Super_v2_EQ` | `2.255` | `98.6%` | `-4.99%` | `-9.59%` | `4.42` | `0.9973` | `0.8815` |
| `Super_v2_HRP_Weekly` | `2.253` | `98.7%` | `-5.03%` | `-9.65%` | `4.38` | `0.9973` | `0.8815` |
| `Super_v2_Core_TRZV_EQ` | `2.631` | `99.6%` | `-4.36%` | `-8.66%` | `5.93` | `0.9997` | `0.9624` |

- **Aporte al referente**: integra 3 frentes limpios (`Carril 2 + CRIPTO-PIT v3 + Global_VolComp_M1DK`) junto con CME descriptivo a volatilidad idéntica `10%`, reporta CSCV limpio sobre 28 reglas no-CME y cuantifica la ganancia estadística de sumar frentes ortogonales.

Diagnóstico de grilla: sin grilla paramétrica. El PBO del CSCV es sobre K reglas ya fijadas (16, 28 y 39); las 4 carteras declaradas son variantes de ponderación, y «HRP_Weekly» dio pesos 0,25 exactos y cifras idénticas a EQ: es la misma cartera, no una variante distinta (causa no verificada; sin `sklearn` la función cae a 1/sd) (ver `auditoria_claude_20261127/REVISION_CLAUDE.md`).
