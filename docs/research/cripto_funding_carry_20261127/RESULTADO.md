# CRIPTO-FUNDING-CARRY-PIT: Carry de Funding y Crowding en 226 Perpetuos PIT (`2021–2026-09`, resultado 2026-11-27)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`4` pruebas, `CRIPTO_FUNDING_CARRY_PIT`). **`HOLDOUT A5` (`18m`) y `>= 2026-10-01` SELLADOS (`NaN`).**

| Serie (20 bps RT + funding real) | Rot/mes | `DESC (39m) Sh` | `REP (12m) Sh` | `DR (51m) Sh / t` | `corr CR3` | `corr OFI` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CFC1_FundingCarry_14d_Stag5d` | `3.73x` | `-0.05` | `-0.64` | **`-0.2 / -0.41`** | `+0.391` | `-0.046` |
| `CFC2_FundingShock_Rev_Stag5d` | `3.95x` | `0.03` | `0.17` | **`0.06 / 0.12`** | `+0.178` | `+0.130` |
| `CFC3_CarryFilt_XSMOM_Stag5d` | `2.46x` | `1.24` | `-1.03` | **`0.68 / 1.4`** | `+0.441` | `+0.518` |
| **`CFC_Canasta_InvVol`** (1 patas) | — | `1.24` | `-1.03` | **`0.68 / 1.4`** | `+0.441` | `+0.518` |

- Costos 10/20/30/40 bps (`DR Sh`): `0.75` / `0.68` / `0.61` / `0.55`.

Diagnóstico de grilla: cero grilla paramétrica (`3` reglas causales escalonadas `5d` con `shift(1)`).
Episodios: detallado por bloques `DESC` (39m) y `REP` (12m) en `RESULTADO.json`; `HOLDOUT A5` permanece intacto.

Aporte al referente: mide si el diferencial de funding 8h y el momentum filtrado por crowding aportan un segundo/tercer pilar cripto limpio y descorrelacionado de `XSMOM` y `OFI`.
