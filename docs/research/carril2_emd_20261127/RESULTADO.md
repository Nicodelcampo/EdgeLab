# CARRIL2-EMD: Transferencia Congelada a MidCap 400 (`EMD`, `2006–2026-09`)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` pruebas, `CARRIL2_EMD`). Costo K33 estimado base `0.4378` pts (`fricR=0.0123`), adverso `0.2` pts. `TERMINAL >= 2026-10-01` sellado.

| Grupo (`R_base`) | Ventana | `Regla Sh (t)` | `Control N Sh (t)` | `Regla − Control Sh (t)` | `p (1-cola diff)` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `todo_2006_2026` (`249m`) | `0.611 (2.78)` | `0.095 (0.43)` | **`0.443 (2.02)`** | `0.0218` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `antes_2009` (`36m`) | `1.036 (1.79)` | `-0.831 (-1.44)` | **`1.445 (2.5)`** | `0.0062` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `desde_2009` (`213m`) | `0.523 (2.2)` | `0.262 (1.1)` | **`0.22 (0.93)`** | `0.1772` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `desde_2019` (`93m`) | `0.055 (0.15)` | `0.258 (0.72)` | **`-0.217 (-0.6)`** | `0.7271` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `DESC` (`144m`) | `0.559 (1.94)` | `-0.135 (-0.47)` | **`0.596 (2.06)`** | `0.0195` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `REP` (`42m`) | `1.165 (2.18)` | `0.911 (1.71)` | **`0.245 (0.46)`** | `0.3236` |
| `Nucleo 5 (IBS,D7,TT,TOM,VBB)` | `HOLDOUT` (`63m`) | `0.364 (0.83)` | `0.146 (0.33)` | **`0.169 (0.39)`** | `0.3492` |
| `Todas 9 Carril 2` | `todo_2006_2026` (`249m`) | `0.311 (1.41)` | `0.018 (0.08)` | **`0.301 (1.37)`** | `0.0853` |
| `Todas 9 Carril 2` | `antes_2009` (`36m`) | `0.545 (0.94)` | `-1.328 (-2.3)` | **`1.419 (2.46)`** | `0.007` |
| `Todas 9 Carril 2` | `desde_2009` (`213m`) | `0.277 (1.17)` | `0.173 (0.73)` | **`0.097 (0.41)`** | `0.3417` |
| `Todas 9 Carril 2` | `desde_2019` (`93m`) | `0.228 (0.64)` | `0.234 (0.65)` | **`-0.058 (-0.16)`** | `0.5638` |
| `Todas 9 Carril 2` | `DESC` (`144m`) | `0.049 (0.17)` | `-0.438 (-1.52)` | **`0.501 (1.74)`** | `0.0413` |
| `Todas 9 Carril 2` | `REP` (`42m`) | `1.728 (3.23)` | `1.222 (2.29)` | **`0.316 (0.59)`** | `0.2773` |
| `Todas 9 Carril 2` | `HOLDOUT` (`63m`) | `0.066 (0.15)` | `0.278 (0.64)` | **`-0.278 (-0.64)`** | `0.7377` |

## Por regla individual en `EMD` (`R_base`)
| Regla | Ops (R/N) | `todo Sh (t)` | `2009+ Sh (t)` | `diff todo (t)` | `diff 2009+ (t)` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `C2_IBS` | `292/490` | `0.435 (1.98)` | `0.268 (1.13)` | `0.426 (1.94)` | `0.243 (1.03)` |
| `C2_D7` | `275/148` | `0.374 (1.7)` | `0.335 (1.41)` | `0.27 (1.23)` | `0.14 (0.59)` |
| `C2_TT` | `381/286` | `0.471 (2.15)` | `0.39 (1.64)` | `0.335 (1.52)` | `0.245 (1.03)` |
| `C2_TOM` | `248/248` | `0.169 (0.77)` | `0.139 (0.59)` | `-0.114 (-0.52)` | `-0.204 (-0.86)` |
| `C2_VBB` | `206/495` | `0.294 (1.34)` | `0.324 (1.37)` | `0.142 (0.65)` | `0.078 (0.33)` |
| `C2_P80` | `212/162` | `0.154 (0.7)` | `0.291 (1.22)` | `0.033 (0.15)` | `0.12 (0.51)` |
| `C2_EVRP` | `352/272` | `-0.023 (-0.11)` | `-0.025 (-0.11)` | `-0.249 (-1.13)` | `-0.269 (-1.13)` |
| `C2_VZ` | `449/495` | `0.214 (0.98)` | `0.232 (0.98)` | `-0.003 (-0.01)` | `-0.003 (-0.01)` |
| `C2_DBO` | `155/188` | `-0.605 (-2.76)` | `-0.546 (-2.3)` | `0.054 (0.24)` | `-0.035 (-0.15)` |

Veredicto primario (`nucleo_5` diff `2009+`): **`NO_CONCLUYENTE`** (`Sh=0.22`, `t=0.93`).

Diagnóstico de grilla: cero grilla paramétrica (reglas congeladas de Carril 2 en instrumento nuevo EMD).
Episodios: desglose explícito pre-2009, 2009–2026-09, 2019–2026-09 y bloques DESC/REP/HOLDOUT en la tabla superior.

Aporte al referente: mide fuera de muestra instrumental si el mecanismo de Carril 2 sobrevive sobre su placebo exacto `N` en EE. UU. post-2009 sobre MidCap (`EMD`).
