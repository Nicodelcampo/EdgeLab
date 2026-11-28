# T-MECANISMO-ETF-APALANCADOS (`PLAN_ESPIRAL_20261127 #2`, `2010–2026-09`, `DESC+REP`)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` pruebas, `T_MECANISMO_ETF_APALANCADOS`). **`HOLDOUT A5` y `TERMINAL` excluidos (`mascara_a5_limpia`).**

## 1. Orden cross-seccional `DollarVol ETFs 3x / DollarVol Futuro` (`DESC+REP`)
| Índice | `2010–2020 (%)` | `2021–2026 (%)` | Salto | Vol ETF 3x `2021+ (M USD/d)` | Resultado conocido de `T` |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `NQ` | `2.04%` | **`4.05%`** | `1.99x` | `7224.9` | Fuerte desde 2021 (+0,13/+0,22 R) |
| `ES` | `0.4%` | **`0.51%`** | `1.27x` | `1841.5` | Positivo menor que NQ |
| `YM` | `0.65%` | **`1.57%`** | `2.42x` | `403.4` | Positivo |
| `RTY` | `7.4%` | **`5.09%`** | `0.69x` | `990.0` | Débil / nulo |
| `EMD` | `0.0%` | **`0.0%`** | `0.0x` | `0.0` | Nulo (sin ETF 3x relevantes) |

## 2. Serie temporal y presión causal `t-1 → t` (`DESC+REP`)
| Índice | `Spearman mens R vs ratio60` | `R/día pre-2021` | `R/día 2021+` | `R(presión alta) vs R(baja)` | `t_Welch` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `NQ` (`65m`) | **`-0.068`** | `6.017` | `20.345` | `27.6666 vs 13.5586` | **`1.29`** |
| `ES` (`65m`) | **`0.057`** | `4.7946` | `1.8296` | `3.9155 vs 2.3807` | **`0.25`** |
- **`NQ` ops (`FUNDEDSYNC_OPS`) lado `T` vs signo retorno previo `t-1`:** mismo signo `R=544.9477` (`n=932`) vs opuesto `R=356.7704` (`n=1047`, `t=0.86`).

Diagnóstico de grilla: cero grilla paramétrica (`3` pruebas de mecanismo sin optimizar perillas).
Episodios: comparado `2010–2020` vs `2021–2026-09` en `DESC+REP`.

Aporte al referente: mide con datos reales `DESC+REP` si la huella temporal y cross-seccional del volumen en ETFs apalancados `3x` explica el patrón geográfico/temporal de `T`.
