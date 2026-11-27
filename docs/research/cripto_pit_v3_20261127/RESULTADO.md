# CRIPTO-PIT v3: Microestructura Basis (`premiumIndex`) + Beta-Neutralización + 5 Mecanismos (resultado, 2026-11-27)

Estado: RESULTADO — campaña pre-registrada en [PREREGISTRO.md](PREREGISTRO.md) (`6` pruebas contadas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` (`18m`) y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

- Universo: `226` monedas crypto PIT reales (ex-TradFi, `vol60 >= 25%`, histéresis `<=20 / >25`) + `226` series `premiumIndexKlines/1d`.

| Mecanismo (`20 bps + funding`, `DESC+REP 51m`) | Rot. | `DESC (39m)` `Sh / t` | `REP (12m)` `Sh / t` | `DESC+REP (51m)` `Sh / t` | `22–26` `Sh` | `beta_BTC` / `Top5_D` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CR3_XSMOM_21d_Stag5d` | `2.67x` | `1.05 / 1.89` | `1.14 / 1.14` | **`1.08 / 2.23`** | `0.98` | `+0.004` / `0.299` |
| `CR3_XSMOM_BetaNeut_Stag5d` | `2.69x` | `0.73 / 1.31` | `0.98 / 0.98` | **`0.79 / 1.64`** | `0.55` | `-0.011` / `0.469` |
| `CR3_Basis_Carry_Stag5d` | `3.18x` | `0.2 / 0.37` | `0.72 / 0.72` | **`0.34 / 0.7`** | `-0.2` | `+0.001` / `1.486` |
| `CR3_BAB_LowVol_Stag5d` | `1.25x` | `0.68 / 1.22` | `1.04 / 1.04` | **`0.77 / 1.59`** | `0.81` | `+0.073` / `0.622` |
| `CR3_ResidMom_21d_2F_Stag5d` | `2.64x` | `0.1 / 0.17` | `0.4 / 0.4` | **`0.17 / 0.35`** | `0.36` | `-0.029` / `3.352` |
| **`CR3_Canasta_InvVol`** (CR3_XSMOM_21d_Stag5d, CR3_XSMOM_BetaNeut_Stag5d, CR3_BAB_LowVol_Stag5d) | — | `1.16 / 2.09` | `1.72 / 1.72` | **`1.29 / 2.66`** | `1.21` | `+0.016` / `0.228` |

- Pesos `1/sd` ajustados en `DESC`: `{'CR3_XSMOM_21d_Stag5d': 0.3858, 'CR3_XSMOM_BetaNeut_Stag5d': 0.3568, 'CR3_BAB_LowVol_Stag5d': 0.2574}`.
- **Aporte al referente**: evalúa 3 mecanismos ortogonales nuevos (`Basis_Carry`, `BAB_LowVol`, `ResidMom_2F`) + beta-neutralización explícita sobre universo PIT sin supervivencia ni fugas de holdout.
