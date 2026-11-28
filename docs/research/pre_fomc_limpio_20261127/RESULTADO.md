# PRE-FOMC-LIMPIO-20Y: Calendario Programado Puro y Transferencia ATJ-28 (`2008–2026-09`, `DESC+REP`)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`5` pruebas, `PRE_FOMC_LIMPIO_20Y`). **`HOLDOUT A5` (`41` eventos en `63m`) y `TERMINAL` 100 % SELLADOS** (`exigir_sin_holdout_no_abierto` + `mascara_a5_limpia`).

## 1. Núcleo `ES + NQ + YM` (`DESC + REP`, `167m`, `122` eventos programados)
| Costo / Muestra | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `p (1-cola)` | `MDD@10%` | `Calmar` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Neto Mini** | `0.369` | `0.498` | **`0.387 (1.45)`** | `0.0736` | `-27.9%` | `0.14` |
| **Neto Micro** (`MES/MNQ/MYM`) | — | — | **`0.338 (1.26)`** | `0.1032` | `-29.68%` | `0.11` |
| **Estrés 2x Mini** | — | — | `0.244 (0.91)` | `0.1811` | `-39.56%` | `0.06` |
| **Bruto** | — | — | `0.529 (1.98)` | `0.0238` | `-25.87%` | `0.2` |

- **Placebo ATJ-28 (24h FOMC vs días sin FOMC en `DESC+REP`):** FOMC `+7.42 pb` vs No-FOMC `+0.76 pb` → **exceso `+6.66 pb/ev` (`t_Welch = 1.29`, `p = 0.09807`)**.
- **Post-publicación:** `2008–2011-06`: `Sh=0.912 (t=1.49)` | `2011-07–2015-02`: `Sh=-0.034 (t=-0.06)` | **`2015-03–2026-09`: `Sh=0.234 (t=0.68)`** | **`2022+`: `Sh=0.929 (t=1.74)`**.
- **Concentración sin eventos extremos:** `t` sin top-1 (`2008-10-29`) = **`1.11`** | sin top-5 = **`0.21`**.

## 2. Transferencia congelada ATJ-28 a otros mercados (`DESC+REP` limpio)
| Instrumento | `n` eventos | `Neto Mini (pb/ev)` | `t_ev` | `p` | `% ev +` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `ES` | `102` | `+7.01` | **`1.29`** | `0.09817` | `0.5` |
| `NQ` | `102` | `+7.97` | **`1.47`** | `0.07146` | `0.529` |
| `YM` | `102` | `+7.28` | **`1.34`** | `0.09052` | `0.608` |
| `EMD` | `102` | `+4.64` | **`0.8`** | `0.21168` | `0.49` |
| `RTY` | `47` | `+3.94` | **`0.56`** | `0.28746` | `0.511` |
| `GC` | `99` | `+2.70` | **`0.51`** | `0.30522` | `0.515` |
| `DAX` | `30` | `-3.32` | **`-0.21`** | `0.58405` | `0.5` |
| `EuroStoxx` | `25` | `-12.14` | **`-0.73`** | `0.7686` | `0.48` |
| `FTSE` | `31` | `-4.88` | **`-0.42`** | `0.66225` | `0.516` |
| `Nikkei` | `24` | `+5.61` | **`0.37`** | `0.35578` | `0.458` |

## 3. Plan formal de potencia K27 / K42 para una eventual apertura (`41` eventos en HOLDOUT A5, `alfa_LORD=0.010937`)
- `core_fomc_0.5x_alfa05`: potencia = **`0.118`** (`n_necesarias=1196`, `potencia 0.12 < 0.8 con N 41 (hacen falta 1196): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).
- `core_fomc_0.5x_lord`: potencia = **`0.033`** (`n_necesarias=1900`, `potencia 0.03 < 0.8 con N 41 (hacen falta 1900): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).
- `core_fomc_0.7x_alfa05`: potencia = **`0.159`** (`n_necesarias=610`, `potencia 0.16 < 0.8 con N 41 (hacen falta 610): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).
- `core_fomc_0.7x_lord`: potencia = **`0.05`** (`n_necesarias=970`, `potencia 0.05 < 0.8 con N 41 (hacen falta 970): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).
- `core_fomc_1.0x_alfa05`: potencia = **`0.235`** (`n_necesarias=299`, `potencia 0.23 < 0.8 con N 41 (hacen falta 299): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).
- `core_fomc_1.0x_lord`: potencia = **`0.085`** (`n_necesarias=475`, `potencia 0.09 < 0.8 con N 41 (hacen falta 475): no se gasta la única apertura (E8); esperar más datos o ir directo al forward secuencial`).

Diagnóstico de grilla: cero grilla paramétrica (`0` perillas ajustadas; calendario ex ante puro y salida `5` min pre-anuncio).
Episodios: reportados cuatro subperíodos (`2008–11`, `2011–15`, `2015–26`, `2022+`) y sensibilidad sin top-1 / top-5 eventos.

Aporte al referente: limpia el calendario FOMC real (`165` fechas programadas exactas), demuestra exceso genuino frente a días no-FOMC, confirma persistencia post-publicación y mide transferencia multi-mercado en `49.3s` sin tocar HOLDOUT.
