# Integridad Canónica de Carril 2 (`#7` de `PLAN_ESPIRAL_20261127.md`)

Estado: DESCRIPTIVO — auditoría sin pruebas nuevas que reconcilia `OPS_H3_PLACEBO` vs `OPS_LOTE{1,2}` y define `SERIE_CANONICA_CARRIL2.csv.gz`.

| Bloque | `H3 Canónica (sin censura) Sh (t)` | `Lote Censurada Sh (t)` | `Control N Sh (t)` | Ops `H3` vs `Lote` |
| :--- | :---: | :---: | :---: | :---: |
| `DESC` (`144m`) | **`1.068 (3.7)`** | `0.801 (2.77)` | `0.254 (0.88)` | `2249 / 2085` |
| `REP` (`42m`) | **`1.256 (2.35)`** | `1.073 (2.01)` | `1.453 (2.72)` | `589 / 536` |
| `HOLDOUT` (`63m`) | **`1.057 (2.42)`** | — | `0.373 (0.85)` | `902 / —` |
| `DESC_REP` (`186m`) | **`1.109 (4.37)`** | `0.857 (3.37)` | `0.508 (2.0)` | `3740 / —` |
| `TODO_2006_2026` (`249m`) | **`1.098 (5.0)`** | — | `0.473 (2.15)` | `3740 / —` |

Aporte al referente: elimina la discrepancia H3 vs `canasta_amplia` fijando la serie canónica completa de Carril 2 sin censura en bordes de mes.
