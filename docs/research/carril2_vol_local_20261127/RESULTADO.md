# CARRIL2-VOL-LOCAL: Corrección K61 de Volatilidad Implícita Local (`2006–2026-09`)

Estado: RESULTADO — EF3 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (`3` contrastes, `CARRIL2_VOL_LOCAL`). Cobertura verificada K62: `ASX200/^AXVI`, `Dow/^VXD`, `Russell2000/^RVX`, `GC/^GVZ` (`^V2TX/^VHSI/^JNIV/^VDAX` no disponibles vía Yahoo/TLS en este entorno).

## Resumen agregado por regla (`LOCAL` vs `VIX_EEUU`)
| Regla | `LOCAL Regla Sh (t)` | `LOCAL Diff vs N Sh (t)` | `VIX Regla Sh (t)` | `VIX Diff vs N Sh (t)` |
| :--- | :---: | :---: | :---: | :---: |
| `C2_VBB` | `0.427 (1.73)` | **`0.589 (2.32)`** | `-0.075 (-0.26)` | `0.84 (2.47)` |
| `C2_VZ_1F` | `0.357 (1.63)` | **`0.045 (0.21)`** | `1.093 (4.96)` | `1.314 (5.94)` |
| `C2_EVRP_1F` | `0.614 (2.8)` | **`0.584 (2.49)`** | `0.576 (2.62)` | `0.383 (1.71)` |

## Detalle por par activo × volatilidad implícita
| Par | Regla | `LOCAL Sh (t)` | `LOCAL diff N (t)` | `VIX Sh (t)` | `VIX diff N (t)` |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `ASX200_AXVI` | `C2_VBB` | `0.385 (1.67)` | `0.147 (0.64)` | `-0.896 (-3.88)` | `-1.234 (-5.34)` |
| `ASX200_AXVI` | `C2_VZ_1F` | `0.163 (0.71)` | `-0.015 (-0.07)` | `2.797 (12.11)` | `4.078 (17.66)` |
| `ASX200_AXVI` | `C2_EVRP_1F` | `0.099 (0.43)` | `-0.053 (-0.23)` | `0.083 (0.36)` | `-0.119 (-0.52)` |
| `Dow_VXD` | `C2_VBB` | `0.207 (0.94)` | `-0.053 (-0.24)` | `0.338 (1.54)` | `0.089 (0.41)` |
| `Dow_VXD` | `C2_VZ_1F` | `0.292 (1.33)` | `0.177 (0.8)` | `0.142 (0.65)` | `-0.042 (-0.19)` |
| `Dow_VXD` | `C2_EVRP_1F` | `0.707 (3.22)` | `0.749 (3.41)` | `0.698 (3.18)` | `0.734 (3.35)` |
| `Russell2000_RVX` | `C2_VBB` | `0.279 (1.27)` | `-0.063 (-0.29)` | `0.217 (0.99)` | `-0.085 (-0.39)` |
| `Russell2000_RVX` | `C2_VZ_1F` | `0.279 (1.27)` | `-0.003 (-0.02)` | `0.026 (0.12)` | `-0.086 (-0.39)` |
| `Russell2000_RVX` | `C2_EVRP_1F` | `0.317 (1.45)` | `0.142 (0.65)` | `0.067 (0.3)` | `-0.214 (-0.98)` |
| `GC_GVZ` | `C2_VBB` | `0.107 (0.46)` | `-0.173 (-0.74)` | `0.211 (0.9)` | `0.011 (0.05)` |
| `GC_GVZ` | `C2_VZ_1F` | `0.191 (0.82)` | `-0.064 (-0.27)` | `0.084 (0.36)` | `-0.063 (-0.27)` |
| `GC_GVZ` | `C2_EVRP_1F` | `0.493 (2.11)` | `0.371 (1.58)` | `0.605 (2.58)` | `0.535 (2.28)` |

Diagnóstico de grilla: cero grilla paramétrica (`3` reglas congeladas comparando insumo local vs `^VIX`).
Episodios: cubre `2006/2008–2026-09` completo sobre los `4` activos con volatilidad implícita local verificada.

- **Hallazgo de alineación horaria K58/K61 en `ASX200`:** `ASX200` cierra a las `16:00 AEST` (`02:00 NY`), `14` horas **antes** del cierre `16:15 NY` de CBOE `^VIX` en la misma fecha calendario; usar `^VIX` sin desfasar generó look-ahead intradía artificial en `ASX200 C2_VZ_1F` (`Sh=2.797, t=12.11`), que desaparece por completo bajo `^AXVI` simultáneo (`Sh=0.163, t=0.71`), mientras `C2_VBB` pasa de `-0.896` con `^VIX` a `+0.385 (t=1.67)` con `^AXVI`.

Aporte al referente: corrige el error K61 donde se usó `^VIX` de EE. UU. como proxy universal en reglas de volatilidad implícita y detecta el desfase de huso horario Sydney vs CBOE.
