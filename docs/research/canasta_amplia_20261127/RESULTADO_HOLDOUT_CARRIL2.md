# CANASTA-AMPLIA: Resultado del HOLDOUT A5 de la canasta Carril 2 sellada (`63` meses, 2026-11-27)

Estado: RESULTADO — apertura única pre-registrada en [PREREGISTRO_HOLDOUT_CARRIL2.md](PREREGISTRO_HOLDOUT_CARRIL2.md) con autorización escrita K27 de Nico (`2026-11-27`), verificada contra [HOLDOUT_CARRIL2.json](HOLDOUT_CARRIL2.json). `TERMINAL >= 2026-10-01` sellado.

- **Motor diario (`HOLDOUT_CARRIL2.json`, operaciones=`ver json`):** Sharpe `1.06`, `t = 2.42`, meses `63`, meses+ `0.59`.
- **Serie mensual normalizada (`63` meses completos, `@10% vol`):** `DESC Sh = 0.801`, `REP Sh = 1.073`, **`HOLDOUT Sh = 1.057 (t = 2.42, p = 0.0077)`**, `MDD@10% = -9.3%`, `Stouffer(REP,H) = 3.13`, veredicto **`CONFIRMA`**.

## Por época en `HOLDOUT A5` (`63` meses completos)
| Época | `N_H` | `HOLDOUT Sh` | `t` | `% años+` | `MDD@10%` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `06_12` | `21` | `0.678` | `0.9` | `71.4%` | `-7.37%` |
| `13_18` | `18` | `1.417` | `1.74` | `66.7%` | `-5.57%` |
| `19_26` | `24` | `1.121` | `1.59` | `75.0%` | `-7.95%` |
| `21_26` | `18` | `1.451` | `1.78` | `83.3%` | `-7.08%` |

Diagnóstico de grilla: sin grilla — 16 reglas-instrumento y pesos `1/sd_DESC` congelados en `PESOS_CARRIL2_SELLADA.json`.
Episodios: en `63` meses de `HOLDOUT A5` de `CARRIL2_A5`, la canasta logra `Sh=1.057` (`t=2.42`, `71.4%` años+).

Aporte al referente: cierra el veredicto limpio de `63` meses sellados de la canasta `Carril 2 Sellada 16` e integra su resultado en [holdout_a5_nocme_20261127/RESULTADO.md](../holdout_a5_nocme_20261127/RESULTADO.md).
