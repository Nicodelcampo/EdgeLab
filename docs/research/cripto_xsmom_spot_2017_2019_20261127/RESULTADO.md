# CRIPTO-XSMOM-SPOT-PRE: `CR3_XSMOM` Congelado en Binance Spot (`2017-10 → 2019-08`)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`2` pruebas, `CRIPTO_XSMOM_SPOT_PRE`). `64` pares Spot USDT PiT cargados (`20 pb RT`, `0` funding). Muestra primaria K60 sin recortes post hoc: `2017-10-01 → 2019-08-31`.

| Regla (`20 pb`, `live60, n>=10`) | `Todo (23m) Sh (t)` | `Solo 2017 (3m)` | `2018–2019 (20m) Sh (t)` | `p (1-cola)` | `Long leg Sh` | `Short leg Sh` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CR3_XSMOM_21d_Stag5d` | **`0.44 (0.61)`** | `0.0 (0.0)` | **`0.47 (0.61)`** | `0.2698` | `-0.06` | `0.34` |
| `CR3_XSMOM_BetaNeut_Stag5d` | **`0.45 (0.62)`** | `0.0 (0.0)` | **`0.48 (0.62)`** | `0.2683` | `-0.09` | `0.32` |

- **Sensibilidad (`live30, n>=6`):** `CR3_XSMOM_21d_Stag5d` `todo=0.56 (t=0.78)`, `2018-19=0.6`; `BetaNeut` `todo=0.35 (t=0.48)`.

Diagnóstico de grilla: cero grilla paramétrica (`2` reglas congeladas de `cripto_pit_v3.py`, sin optimizar perillas).
Episodios: detallado `2017` vs `2018–2019` (ex-burbuja) en la tabla superior y mes a mes en `RESULTADO.json`.

Aporte al referente: prueba las reglas XSMOM congeladas de `cripto_pit_v3` sobre casi `2` años vírgenes de Spot (`2017–2019`) sin tocar el holdout 2021–2026.
