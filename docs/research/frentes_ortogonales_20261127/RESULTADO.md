# FRENTES-ORTOGONALES-20261127: FundedSync O (1 MNQ fijo) y Compresión de Volatilidad Global en M1DK (resultado, 2026-11-27)

Estado: RESULTADO — pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`11` pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl`). **`HOLDOUT A5` y sesiones `>= 2026-10-01` SELLADOS (`NaN`).**

## A. FundedSync O (`qty=1` MNQ fijo, `2018–2026-09`)
- Con tamaño por defecto (`capital=100k`), `O` dejó `0` operaciones desde `2025-10`; fijando `qty=1` MNQ opera **`36`** veces en `2025-10..2026-09` (`DESC+REP`) sumando **`\$-3041.4`** netos.
- `DESC (18–26)`: `Sh=0.777` (`t=1.74`, `+\$80.28/m`); `REP (18–26)`: `Sh=0.034` (`t=0.04`, `+\$6.53/m`); `21–26 DR`: `Sh=0.263` (`t=0.54`).
- Correlaciones: `{'corr_monthly_vs_CME_TRZV': -0.301, 'corr_daily_vs_CME_TRZV': 0.021, 'corr_monthly_vs_CME_Div10': -0.068, 'corr_daily_vs_CME_Div10': -0.008, 'corr_monthly_vs_Carril2_Sell16': 0.238, 'corr_daily_vs_Carril2_Sell16': 0.085, 'corr_monthly_vs_Cripto_Core_Stag': 0.126, 'corr_daily_vs_Cripto_Core_Stag': 0.047}`.

## B. Transferencia global `F-COMPRESION-VOL-CRECE` (`C2_VZ` y `C2_EVRP` en `data/m1dk/`, `8 bps RT`)
| Regla / Activo | `ops DR` | `mean R` (`fric R`) | `DESC Sh` | `REP Sh` | `DR Sh` | `19–26 Sh` | `16 bps Sh` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `C2_VZ_DAX` | `258` | `+0.069R` (`0.045R`) | `0.447` | `0.721` | `0.521` | `0.968` | `0.176` |
| `C2_EVRP_DAX` | `163` | `+0.040R` (`0.030R`) | `0.022` | `0.667` | `0.2` | `0.349` | `0.052` |
| `C2_VZ_EuroStoxx` | `251` | `+0.028R` (`0.047R`) | `0.056` | `0.659` | `0.215` | `0.731` | `-0.147` |
| `C2_EVRP_EuroStoxx` | `150` | `-0.024R` (`0.030R`) | `-0.244` | `0.228` | `-0.123` | `0.3` | `-0.273` |
| `C2_VZ_FTSE` | `297` | `+0.034R` (`0.056R`) | `0.186` | `0.481` | `0.26` | `0.463` | `-0.162` |
| `C2_EVRP_FTSE` | `215` | `-0.041R` (`0.035R`) | `-0.613` | `0.776` | `-0.226` | `0.006` | `-0.416` |
| `C2_VZ_Nikkei` | `295` | `+0.070R` (`0.040R`) | `0.478` | `0.539` | `0.488` | `0.615` | `0.21` |
| `C2_EVRP_Nikkei` | `171` | `+0.034R` (`0.028R`) | `0.365` | `-0.609` | `0.166` | `0.491` | `0.029` |
| `C2_VZ_Oro` | `264` | `+0.012R` (`0.049R`) | `-0.113` | `0.635` | `0.047` | `0.195` | `-0.241` |
| `C2_EVRP_Oro` | `256` | `+0.054R` (`0.031R`) | `0.119` | `0.844` | `0.279` | `0.841` | `0.12` |
| **`Global_VolComp_M1DK`** (7 activas) | — | — | `0.415` | `0.562` | **`0.454` (`t=1.37`)** | `1.132` | `21–26=1.162` |

- Incluidas por regla causal (`DESC > 0` y `fricR < 0.08`): `['C2_VZ_DAX', 'C2_EVRP_DAX', 'C2_VZ_EuroStoxx', 'C2_VZ_FTSE', 'C2_VZ_Nikkei', 'C2_EVRP_Nikkei', 'C2_EVRP_Oro']` (pesos: `{'C2_VZ_DAX': 0.1567, 'C2_EVRP_DAX': 0.1656, 'C2_VZ_EuroStoxx': 0.1586, 'C2_VZ_FTSE': 0.1392, 'C2_VZ_Nikkei': 0.1186, 'C2_EVRP_Nikkei': 0.149, 'C2_EVRP_Oro': 0.1123}`).
- **Aporte al referente**: recupera un mecanismo overnight de `FundedSync O` con `corr ~ 0` frente a `TRZV` mediante tamaño fijo `1 MNQ`, y mide limpiamente si `F-COMPRESION-VOL-CRECE` transfiere a índices globales y oro sin glitches de roll.
