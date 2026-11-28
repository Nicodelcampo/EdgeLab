# FX-MACRO-FIX-20Y: Reloj FX (K58), Oro Overnight vs NY, Treasury Fin de Mes y XS-Momentum Non-Equity (`2006–2026-09`)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `FX_MACRO_FIX_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).** Compuerta K58 superada (`corr` `2024-01=0.9255`, `DST Mar=0.9863`, `2024-07=0.8548` en desfase `0`).

| Mecanismo (`@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress` | `corr C2` | `corr MVC` | `corr MRV3` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `FXF1_FX_Clock_Session_EURJPY` | `1002.8x` | `-0.599` | `-2.214` | **`-0.938 / -3.69`** | `-1.904` | `-0.133` | `-0.003` | `-0.161` |
| `FXF2_Gold_AsianOvn_vs_NY` | `501.1x` | `0.017` | `1.459` | **`0.306 / 1.2`** | `-0.409` | `-0.038` | `-0.023` | `+0.084` |
| `FXF3_Treasury_MonthEnd_Rebal` | `24.2x` | `0.427` | `0.254` | **`0.394 / 1.55`** | `0.1` | `+0.102` | `-0.023` | `-0.141` |
| `FXF4_NonEq_XS_Mom_12ETFs` | `8.04x` | `0.37` | `-1.112` | **`-0.001 / -0.0`** | `-0.107` | `-0.097` | `+0.173` | `+0.129` |
| **`FXF_Canasta_InvVol`** (`2` patas) | — | `0.576` | `-0.737` | **`0.265 / 1.04`** | `-0.012` | `-0.003` | `+0.113` | `+0.003` |

- **Desglose `FXF2` Oro (`DR`):** pierna Overnight Asia/Londres `Sh=1.281` | pierna Corto COMEX RTH `Sh=0.068`.
Diagnóstico de grilla: cero grilla paramétrica (`4` mecanismos fijos sin optimización por Sharpe).
Episodios: evaluado en `DESC` (`144m`) + `REP` (`42m`) = `186m`; `HOLDOUT A5` (`63m`) sellado.

Aporte al referente: valida mecanismos macro/FX sin equity ni beta direccional de `20` años en `11.7s` con `63m` de holdout intactos.
