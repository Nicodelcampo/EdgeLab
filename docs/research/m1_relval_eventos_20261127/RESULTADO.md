# M1-RELVAL-EVENTOS-20Y: Dispersión Cross-Índice, Overnight/RTH, Pre-FOMC y VRP M1 (`2006–2026-09`, resultado 2026-11-27)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `M1_RELVAL_EVENTOS_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).**

| Mecanismo (costos canónicos CME, `@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress Sh` | `corr C2` | `corr RP4` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MRV1_CrossIdx_Disp_5d` | `33.77x` | `-0.139` | `-1.355` | **`-0.344 / -1.28`** | `-0.597` | `+0.082` | `+0.018` |
| `MRV2_OvnVsRTH_RelVal` | `24.58x` | `-0.213` | `-1.267` | **`-0.452 / -1.69`** | `-0.65` | `+0.005` | `+0.049` |
| `MRV3_PreFOMC_Drift_M1` | `8.43x` | `0.733` | `0.577` | **`0.685 / 2.56`** | `0.618` | `-0.038` | `-0.207` |
| `MRV4_TrueM1_VRP_ESNQGC` | `56.77x` | `0.654` | `0.92` | **`0.713 / 2.66`** | `0.671` | `+0.385` | `+0.244` |
| **`MRV_Canasta_InvVol`** (1 patas) | — | `0.733` | `0.577` | **`0.685 / 2.56`** | `0.618` | `-0.038` | `-0.207` |

- Exceso `MRV4_TrueM1_VRP_ESNQGC` sobre Buy&Hold equivalente (`DR`): `Sh=-0.205` (`t=-0.77`).
Diagnóstico de grilla: cero grilla paramétrica (`4` reglas fijas con costos canónicos de `edgelab/costos.py`).
Episodios: evaluado en `DESC` (`129m`) + `REP` (`38m`) = `167m` (`2008-01 → 2026-09`, `159` eventos FOMC); `HOLDOUT A5` (`63m`) sellado.

Aporte al referente: mide 4 mecanismos ortogonales sobre `20` años de barras `M1` reales CME (`ES, NQ, YM, RTY, GC`) con `63m` sellados.
