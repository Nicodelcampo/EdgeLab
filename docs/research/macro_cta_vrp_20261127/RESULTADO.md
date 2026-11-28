# MACRO-CTA-VRP-20Y: CTA No-Equity, Term Structure VIX/VIX3M y Vol-Managed (`2006–2026-09`, resultado 2026-11-27)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `MACRO_CTA_VRP_20Y`). **`HOLDOUT A5` (`63m`) y `>= 2026-10-01` SELLADOS (`NaN`).**

| Mecanismo (`5 bps RT`, `@10% vol`) | Rot/año | `DESC Sh` | `REP Sh` | `DR Sh / t` | `2x Stress Sh` | `corr C2` | `corr RP4` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MVC1_CTA_NonEq_MultiHorizon` | `9.01x` | `0.425` | `0.422` | **`0.426 / 1.68`** | `0.301` | `-0.036` | `+0.046` |
| `MVC2_VIX_TermStruct_FTQ` | `4.8x` | `0.229` | `-0.588` | **`0.07 / 0.27`** | `0.01` | `+0.069` | `-0.018` |
| `MVC3_Rates_RealYield_Carry` | `4.41x` | `-0.131` | `-0.842` | **`-0.299 / -1.18`** | `-0.379` | `+0.054` | `-0.067` |
| `MVC4_MoreiraMuir_VolManaged` | `4.66x` | `0.578` | `1.495` | **`0.766 / 3.02`** | `0.731` | `+0.101` | `+0.475` |
| **`MVC_Canasta_InvVol`** (2 patas) | — | `0.663` | `1.138` | **`0.773 / 3.04`** | `0.667` | `+0.042` | `+0.336` |

- Referencia estática `1/vol` en `MM_5` (`DR`): `Sh=0.838` vs vol-managed `0.766`.
Diagnóstico de grilla: cero grilla paramétrica (`4` reglas estándar escalonadas `5d` con `shift(1)`).
Episodios: evaluado en `DESC` (`144m`) + `REP` (`42m`); `HOLDOUT A5` sellado.

Aporte al referente: suma mecanismos macro no-equity y de estructura temporal de volatilidad con `20+` años de historia y `63m` de holdout intactos.

## Auditoría Claude (2026-11-28)
Ver `docs/research/auditoria_claude_20261128/REVISION_ESPIRAL_ANTIGRAVITY.md`.
