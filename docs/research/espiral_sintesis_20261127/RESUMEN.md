# Espiral Fase 1 — Síntesis Multi-Frente y Potencia K27 (DESC+REP; HOLDOUT A5 Sellado)

Estado: VIGENTE — análisis descriptivo exclusivamente sobre `DESC+REP` (`0` pruebas nuevas, `HOLDOUT A5` 100 % sellado).

## 1. Frentes y combinaciones en `20` años (`186m` DESC+REP; proyección K27 a `63m` sellados)
| Frente / Pool | `DESC Sh` | `REP Sh` | `DR Sh (t)` | `MDD@10%` | `Calmar` | `K27 @0.7x (63m)` | `K27 @1.0x (63m)` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Carril2_Sell16` | `0.721` | `1.41` | **`0.846 (3.16)`** | `-12.98%` | `0.65` | `0.387` | `0.615` |
| `Macro_RP4` | `0.288` | `0.585` | **`0.348 (1.3)`** | `-22.32%` | `0.16` | `0.139` | `0.198` |
| `MVC_CTA_VRP` | `0.615` | `0.977` | **`0.693 (2.59)`** | `-15.3%` | `0.45` | `0.297` | `0.477` |
| `MVC1_CTA_NonEq` | `0.376` | `0.205` | **`0.339 (1.26)`** | `-19.51%` | `0.17` | `0.135` | `0.193` |
| `MVC4_VolManaged` | `0.547` | `1.461` | **`0.715 (2.67)`** | `-17.23%` | `0.41` | `0.309` | `0.497` |
| `MRV_PreFOMC` | `0.733` | `0.577` | **`0.685 (2.56)`** | `-7.7%` | `0.89` | `0.292` | `0.47` |
| `Pool_Nuevo_Sellado_2F_EQ (MVC+MRV, 63m HO intacto)` | `0.937` | `1.15` | **`0.964 (3.59)`** | `-10.29%` | `0.94` | `0.461` | `0.714` |
| `Pool_Nuevo_Sellado_3M_EQ (CTA+MM+PreFOMC, 63m HO intacto)` | `0.901` | `1.112` | **`0.937 (3.5)`** | `-12.29%` | `0.76` | `0.444` | `0.692` |
| `Arquitectura_20y_4F_EQ (Carril2+RP4+MVC+MRV, solo DR)` | `1.151` | `1.411` | **`1.211 (4.52)`** | `-9.02%` | `1.34` | `0.617` | `0.871` |

- **Número efectivo de fuentes independientes (`N_eff` PCA sobre `Carril2, RP4, MVC, MRV` en 186m):** **`3.7` de `4,00`**.

## 2. Correlación mensual `DESC+REP` (`186m`, `2006–2026-09`)
| | Carril2_Sell16 | Macro_RP4 | MVC_CTA_VRP | MRV_PreFOMC |
| :--- | :---: | :---: | :---: | :---: |
| **Carril2_Sell16** | `+1.000` | `+0.058` | `+0.048` | `-0.038` |
| **Macro_RP4** | `+0.058` | `+1.000` | `+0.335` | `-0.207` |
| **MVC_CTA_VRP** | `+0.048` | `+0.335` | `+1.000` | `+0.021` |
| **MRV_PreFOMC** | `-0.038` | `-0.207` | `+0.021` | `+1.000` |

## Auditoría Claude (2026-11-28)
Ver `docs/research/auditoria_claude_20261128/REVISION_ESPIRAL_ANTIGRAVITY.md`.
