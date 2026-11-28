# CRIPTO-OFI-PIT: Flujo Taker Buy/Sell No-OHLC en 226 Perpetuos PIT (resultado, 2026-11-27)

Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas en [TRIAL_REGISTRY_GLOBAL.jsonl](../TRIAL_REGISTRY_GLOBAL.jsonl)). **`HOLDOUT A5` (`18m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

| Mecanismo (`20 bps + funding`) | Rot. | `DESC (39m) Sh / t` | `REP (12m) Sh / t` | `DR (51m) Sh / t` | `corr_XSMOM` | `top5_D` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `OFI1_TakerFlow_21d_Stag5d` | `1.54x` | `0.96 / 1.72` | `0.77 / 0.77` | **`0.91 / 1.89`** | `+0.205` | `0.713` |
| `OFI2_FlowReturn_Div_14d_Stag5d` | `2.25x` | `-0.45 / -0.81` | `0.37 / 0.37` | **`-0.26 / -0.53`** | `-0.259` | `9.99` |
| `OFI3_WhaleFlow_14d_Stag5d` | `1.72x` | `0.2 / 0.37` | `-0.24 / -0.24` | **`0.1 / 0.21`** | `-0.188` | `2.647` |
| **`OFI_Canasta_InvVol`** (OFI1_TakerFlow_21d_Stag5d, OFI3_WhaleFlow_14d_Stag5d) | — | `0.68 / 1.22` | `0.34 / 0.34` | **`0.6 / 1.23`** | `0.014` | `beta=-0.030` |

Diagnóstico de grilla: sin grilla paramétrica (`3` reglas de flujo `taker` escalonadas a `5d`, patas `top-4/bot-4` + canasta causal `DESC`).
Episodios: `DESC` (`39m`, `Sh=0.68`), `REP` (`12m`, `Sh=0.34`), correlación mensual vs `XSMOM` `0.014` y vs `BAB` `-0.034`.

- **Aporte al referente**: mide de forma limpia y pre-registrada si el flujo agresor `taker buy/sell` no-OHLC aporta ventaja y ortogonalidad real frente a `XSMOM`.
