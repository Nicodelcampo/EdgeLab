# INFORME DE RESULTADOS: Diagnóstico de Heterogeneidad Horaria GC (BT2A P2-A V1)

**Fecha:** 2026-08-28  
**Autorización de Ejecución:** `AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1`  
**HEAD de Ejecución:** `6cb6d2ed7f968205aeb55ac214b527abedc0bef9`  
**Spec Congelada:** `specs/bt2a_p2a_gc_clock_heterogeneity_v1.json` (`0ff77118098667991b88737e91ad58b29d1eb5fee5406d2a278983edf9ae9cee`)  
**Payload del Resultado Consolidado (SHA-256):** `4a01978b98ccaa4342120493a295680820da44d0474b4d991b9f5bab94424a0d`  
**Estado:** `COMPLETE_AUTHORIZED_POST_SELECTION_CLOCK_DIAGNOSTIC`  

---

## 1. Veredicto y Dictamen Formal

```text
EXECUTION_COMPLETE                         = true
PREREGISTERED_FAMILY_COMPLETE              = true
CLOCK_HETEROGENEITY_SIGNAL                 = false
STATISTICAL_HOMOGENEITY_PROVEN             = false
NOMINAL_PATTERNS_PRESENT                   = true
NOMINAL_PATTERNS_FAMILYWISE_SUPPORTED      = false
WINNER_SELECTED                            = false
EDGE_DECLARED                              = false
PROMOTION_ELIGIBLE                         = false
HOLDOUT_TOUCHED                            = false
```

### Clasificación Contractual

```json
{
  "label": "P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL",
  "reason": "ZERO_HOLM_12_PHASE_VS_REST_CONTRASTS",
  "passing_contrasts": [],
  "post_selection": true,
  "winner_selected": false,
  "edge_declared": false,
  "promotion_eligible": false,
  "confirmatory_eligible": false
}
```

---

## 2. Precisión Epistemológica

En la familia post-selección preregistrada, con la cobertura y potencia disponibles, **no se detectó evidencia estadística de que el contraste K_ABS−N_RAND difiera entre las cuatro fases horarias después del ajuste de Holm-12**.

> [!IMPORTANT]
> **Ausencia de heterogeneidad no equivale a prueba de homogeneidad.**  
> No puede concluirse formalmente que el efecto sea invariante en todas las fases, que esté presente y positivo en cada ventana, ni que el horario sea irrelevante económicamente. Afirmar homogeneidad requeriría una prueba de equivalencia con margen $\delta$ congelado ex-ante.

---

## 3. Cobertura y Metodología

- **Universo de Sesiones:** **234 sesiones CME** (5 contratos de GC: 12-25, 02-26, 04-26, 06-26, 08-26).
- **Población Total:** **16.940 eventos `K_ABS`**.
- **Eventos Excluidos por Blackout Macroeconómico:** **71 eventos** (ventanas $[-15\text{m}, +15\text{m}]$ alrededor de CPI, NFP y FOMC).
- **Eventos Analizados:** **16.869 eventos `K_ABS`**.
- **Sesiones con Cobertura Multivariable Completa en las 4 Fases:** **215 sesiones**.
- **Inferencia:** Wild Bootstrap de Webb (10.000 replicaciones de cluster por sesión) y control familiar **Holm-12**.

---

## 4. Tabla Consolidada de los 12 Contrastes Fase vs Resto

Estimando: Diferencia en puntos porcentuales (pp) de la tasa de primer pasaje $\theta_{\text{FP}}(\text{K\_ABS}) - \text{median}(\theta_{\text{FP}}(\text{N\_RAND}))$ entre la fase específica y el promedio de las otras tres fases.

| Celda Padre $(B, H)$ | Fase de Mercado | Estimación ($\Delta$) | IC 95% Bootstrap | $p_{\text{unc}}$ (Two-sided) | $p_{\text{Holm-12}}$ | Sesiones | Señal Familiar |
|---|---|---|---|---|---|---|---|
| **(9t, 25t)** | `ASIA_ETH` | $+0{,}23\text{ pp}$ | $[-3{,}60;\, +4{,}11]$ | 0.9094 | **1.0000** | 215 | `false` |
| **(9t, 25t)** | `EUROPE_PRE_RTH` | $+2{,}20\text{ pp}$ | $[-1{,}57;\, +5{,}92]$ | 0.2527 | **1.0000** | 215 | `false` |
| **(9t, 25t)** | `GC_RTH` | $-0{,}89\text{ pp}$ | $[-3{,}48;\, +1{,}65]$ | 0.5037 | **1.0000** | 215 | `false` |
| **(9t, 25t)** | `POST_RTH` | $-1{,}54\text{ pp}$ | $[-6{,}34;\, +3{,}25]$ | 0.5317 | **1.0000** | 215 | `false` |
| **(30t, 100t)** | `ASIA_ETH` | $-0{,}93\text{ pp}$ | $[-3{,}61;\, +1{,}71]$ | 0.4987 | **1.0000** | 215 | `false` |
| **(30t, 100t)** | `EUROPE_PRE_RTH` | $+1{,}13\text{ pp}$ | $[-1{,}03;\, +3{,}23]$ | 0.3063 | **1.0000** | 215 | `false` |
| **(30t, 100t)** | `GC_RTH` | $-0{,}39\text{ pp}$ | $[-2{,}25;\, +1{,}45]$ | 0.6981 | **1.0000** | 215 | `false` |
| **(30t, 100t)** | `POST_RTH` | $+0{,}19\text{ pp}$ | $[-2{,}72;\, +3{,}17]$ | 0.9037 | **1.0000** | 215 | `false` |
| **(30t, 250t)** | `ASIA_ETH` | $+1{,}17\text{ pp}$ | $[-2{,}45;\, +4{,}80]$ | 0.5394 | **1.0000** | 215 | `false` |
| **(30t, 250t)** | `EUROPE_PRE_RTH` | $+3{,}64\text{ pp}$ | $[+0{,}74;\, +6{,}44]$ | 0.0151 | **0.1812** | 215 | `false` |
| **(30t, 250t)** | `GC_RTH` | $-3{,}06\text{ pp}$ | $[-5{,}80;\, -0{,}30]$ | 0.0311 | **0.3421** | 215 | `false` |
| **(30t, 250t)** | `POST_RTH` | $-1{,}75\text{ pp}$ | $[-5{,}84;\, +2{,}29]$ | 0.4063 | **1.0000** | 215 | `false` |

---

## 5. Tratamiento de Patrones Nominales en (30t, 250t)

En la celda $(B=30\text{ t},\, H=250\text{ t})$ se observaron dos desviaciones nominalmente llamativas:
- **Europe Pre-RTH:** $+3{,}64\text{ pp}$ ($p_{\text{unc}} = 0{,}0151$)
- **GC RTH:** $-3{,}06\text{ pp}$ ($p_{\text{unc}} = 0{,}0311$)

Sin embargo, tras el ajuste riguroso por multiplicidad familiar (Holm-12):
- Europe: **$p_{\text{Holm}} = 0{,}1812 > 0{,}05$**
- RTH: **$p_{\text{Holm}} = 0{,}3421 > 0{,}05$**

**Impacto Metodológico:**
- No constituyen señales formales.
- No justifican la creación de filtros horarios post-hoc (ni seleccionar Europa ni excluir RTH).
- No alteran el diseño de Puerta 2-B.
- Se reportan como patrones descriptivos nominales que no sobreviven el control familiar.

---

## 6. Firewalls y Estado Final

- `HOLDOUT_TOUCHED`: **`false`** (Holdout `2026-07-01` $\to$ `2026-12-31` intacto).
- `PNL_ACCESSED`: **`false`** (No se computó P&L ni equity).
- `P2B_RUN`: **`false`** (Puerta 2-B permanece implementada y cerrada).
- `L2_OUTCOMES_OPENED`: **`false`**.
- `WINNER_SELECTED`: **`false`**.
- `EDGE_DECLARED`: **`false`**.
- `PROMOTION_ELIGIBLE`: **`false`**.

---

## Aporte al referente

El diagnóstico de heterogeneidad horaria de BigTrap2Absorption sobre 234 sesiones de GC concluye con `P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL`. Se descarta formalmente introducir filtros horarios post-hoc no justificados, preservando la integridad de P2-B y todos los firewalls epistemológicos.
