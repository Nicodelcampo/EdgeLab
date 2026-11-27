# MACRO-RISK-PREMIA: 5 Primas Estructurales sobre ETFs Ajustados (`2006–2026-09`, resultado 2026-11-27)

Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`6` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` (`63m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

- Datos: `41` series Yahoo `adjclose` + índices `^TNX`/`^IRX` (`2006-01-03 -> 2026-09-30`, cero empalmes `=F`, `PROCEDENCIA.json` con SHA-256).

| Mecanismo (`10 bps RT + borrow`, `@10% vol`) | Rot/año | `DESC (143m) Sh` | `REP (42m) Sh` | `DR (185m) Sh / t` | `2x Stress Sh` | `corr_SPY` (`beta`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `RP1_Sector_XSMOM_Neut` | `6.5x` | `-0.009` | `-0.271` | **`-0.073 / -0.29`** | `-0.259` | `+0.025` (`+0.025`) |
| `RP2_Sector_BAB_LowBeta` | `1.87x` | `0.209` | `0.666` | **`0.306 / 1.21`** | `0.224` | `-0.030` (`-0.030`) |
| `RP3_Country_XSMOM_Neut` | `8.02x` | `-0.284` | `-0.163` | **`-0.258 / -1.01`** | `-0.459` | `+0.115` (`-0.006`) |
| `RP4_Rates_Curve_Credit` | `7.68x` | `0.298` | `0.642` | **`0.365 / 1.44`** | `0.109` | `+0.096` (`+0.006`) |
| `RP5_NonEq_MultiSpeed_Trend` | `9.91x` | `0.106` | `0.302` | **`0.148 / 0.58`** | `-0.076` | `-0.286` (`-0.066`) |
| **`RP_Canasta_InvVol`** (1 activas) | — | `0.298` | `0.642` | **`0.365 / 1.44`** | `0.109` | `+0.096` |

- Regla causal `DESC` (`DESC Sh > 0.25` y `|corr_SPY| < 0.35`): incluidas `['RP4_Rates_Curve_Credit']`, pesos `{'RP4_Rates_Curve_Credit': 1.0}`.
- Por época (`RP_Canasta_InvVol`): `06–12 Sh=0.434`, `13–18 Sh=-0.563`, `19–26 Sh=0.904`, `21–26 Sh=0.765`.

Diagnóstico de grilla: sin grilla paramétrica (`5` mecanismos institucionales fijos con rebalanceo escalonado `5d`, ventanas estándar `21/63/126/252` y selección causal en `DESC`).
Episodios: épocas de la canasta `06–12 Sh=0.434`, `13–18 Sh=-0.563`, `19–26 Sh=0.904`, `21–26 Sh=0.765`; años positivos `DR`: `71.4%`.

- **Aporte al referente**: abre un frente macro multi-clase limpio de `20+` años con `0` iteración de `REP`, `0` empalmes `=F` y `63` meses de `HOLDOUT A5` sellado.
