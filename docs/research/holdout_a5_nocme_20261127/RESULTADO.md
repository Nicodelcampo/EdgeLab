# HOLDOUT-A5-NOCME: Veredicto de Apertura Única Conjunta (4 Frentes Limpios, `< 2026-10-01`)

Estado: RESULTADO — confirmación **Etapa EF4** pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`TRIAL_REGISTRY_GLOBAL.jsonl` + [HOLDOUT_VENTANAS.jsonl](../HOLDOUT_VENTANAS.jsonl)) con compuerta K27 levantada por autorización escrita de Nico (`2026-11-27`). **`TERMINAL` (`>= 2026-10-01`) permanece 100% sellado.**

## 1. Veredicto Primario en `HOLDOUT A5` (`< 2026-10-01`)
| Frente / Cartera | `N_H` | `DESC Sh` | `REP Sh` | `DR Sh` | **`HOLDOUT Sh / t`** | `p` (1-cola) | `MDD@10%` | `Stouffer(R,H)` | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Carril2_Sell16` | `63` | `0.801` | `1.073` | `0.857` | **`1.057 / 2.42`** | `0.0077` | `-9.3%` | `3.13` (`p=0.0009`) | **`CONFIRMA`** |
| `Macro_RP_Canasta` | `63` | `0.298` | `0.642` | `0.365` | **`0.38 / 0.87`** | `0.192` | `-12.73%` | `1.46` (`p=0.0721`) | **`NO_CONCLUYENTE`** |
| `Cripto_v3_Canasta` | `18` | `1.161` | `1.721` | `1.289` | **`0.493 / 0.6`** | `0.2732` | `-7.27%` | `1.64` (`p=0.0505`) | **`NO_CONCLUYENTE`** |
| `Cripto_OFI_Canasta` | `18` | `0.678` | `0.337` | `0.596` | **`1.133 / 1.39`** | `0.0826` | `-3.97%` | `1.22` (`p=0.1112`) | **`NO_CONCLUYENTE`** |
| `Super_v3_Clean63m_EQ` | `63` | `0.786` | `1.048` | `0.847` | **`0.829 / 1.9`** | `0.0287` | `-11.32%` | `2.73` (`p=0.0032`) | **`CONFIRMA`** |
| `Super_v3_Clean63m_HRP` | `63` | `0.772` | `1.038` | `0.835` | **`0.814 / 1.86`** | `0.0311` | `-11.45%` | `2.69` (`p=0.0036`) | **`CONFIRMA`** |
| `Pool_NoCME_Dyn_4F_63m` | `63` | `0.973` | `1.01` | `0.984` | **`0.923 / 2.12`** | `0.0172` | `-12.62%` | `2.84` (`p=0.0023`) | **`CONFIRMA`** |
| `Super_v3_NoCME_EQ` | `18` | `1.339` | `2.767` | `1.597` | **`1.583 / 1.94`** | `0.0262` | `-4.97%` | `3.33` (`p=0.0004`) | **`CONFIRMA`** |
| `Super_v3_NoCME_HRP` | `18` | `1.263` | `2.996` | `1.556` | **`1.538 / 1.88`** | `0.0298` | `-5.75%` | `3.45` (`p=0.0003`) | **`CONFIRMA`** |

- **Fisher combinado limpio (`63m`, `Carril2 + Macro_RP`):** `chi2 = 13.034` (`df=4`), **`p = 0.011113`**.
- **Fisher combinado `4` frentes (`Carril2 + Macro_RP + Cripto_v3 + Cripto_OFI`):** `chi2 = 20.616` (`df=8`), **`p = 0.00824`**.
- **Correlación mensual en `HOLDOUT A5` (`18m`):** `{'Carril2_Sell16': {'Carril2_Sell16': 1.0, 'Macro_RP_Canasta': 0.548, 'Cripto_v3_Canasta': -0.27, 'Cripto_OFI_Canasta': 0.046}, 'Macro_RP_Canasta': {'Carril2_Sell16': 0.548, 'Macro_RP_Canasta': 1.0, 'Cripto_v3_Canasta': -0.367, 'Cripto_OFI_Canasta': -0.015}, 'Cripto_v3_Canasta': {'Carril2_Sell16': -0.27, 'Macro_RP_Canasta': -0.367, 'Cripto_v3_Canasta': 1.0, 'Cripto_OFI_Canasta': 0.026}, 'Cripto_OFI_Canasta': {'Carril2_Sell16': 0.046, 'Macro_RP_Canasta': -0.015, 'Cripto_v3_Canasta': 0.026, 'Cripto_OFI_Canasta': 1.0}}`.

## 2. Diagnósticos Secundarios y Sensibilidad (`NO deciden veredicto primario`)
| Diagnóstico / Regla | `N_H` | `DR Sh` | **`HOLDOUT Sh / t`** | `p` | `MDD@10%` | Lectura |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `Macro_RP_Diag_3Pos` | `63` | `0.425` | **`0.593 / 1.36`** | `0.0869` | `-11.75%` | `NO_CONCLUYENTE` |
| `Super_v3_Clean63m_Diag3Pos_EQ` | `63` | `0.916` | **`1.106 / 2.53`** | `0.0056` | `-6.76%` | `CONFIRMA` |
| `Cripto_v3_XSMOM_BAB` | `18` | `1.479` | **`0.438 / 0.54`** | `0.2957` | `-7.98%` | `NO_CONCLUYENTE` |
| `OFI1_TakerFlow_21d_Stag5d` | `18` | `0.915` | **`1.02 / 1.25`** | `0.1058` | `-3.87%` | `NO_CONCLUYENTE` |
| `Pool_NoCME_Poda_Diag_18m` | `18` | `1.613` | **`1.667 / 2.04`** | `0.0206` | `-6.54%` | `CONFIRMA` |

Diagnóstico de grilla: sin grilla paramétrica — todas las reglas, ponderaciones `1/sd_DESC` y pesos `HRP` se congelaron antes de leer `HOLDOUT A5` tras verificar paridad exacta en `DESC+REP` (`diff_mrp=1.0e-16`, `diff_cr3=2.3e-13`, `diff_ofi=4.5e-13`).
Episodios: en `HOLDOUT A5` (`63m` / `18m`), `Pool_NoCME_Dyn_4F_63m` registra `Sh=0.923` (`t=2.12`, `61.9%` años+) y `Super_v3_NoCME_HRP` `Sh=1.538` (`t=1.88`).

Aporte al referente: entrega el veredicto limpio y definitivo en `HOLDOUT A5` sellado de los `4` frentes No-CME y sus carteras integradas, preservando intacta la barrera `TERMINAL >= 2026-10-01`.
