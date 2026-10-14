# Informe de Auditoría Causal Formal — Hipótesis HP-007 (Corredores de Vacío)

**Fecha:** 2026-09-15  
**Campaña:** `HP007-CAMP-001`  
**Autor:** Auditor Cuantitativo Causal / EdgeLab  
**Rama:** `work/hp007-causal-campaign-v1-20260915`  
**Base Commit:** `20f2de397db7427893630bc626c4d4966b1122cf`  
**Contratos Certificados:** `6E 03-26` y `6E 06-26` (In-Sample; Holdout `>= 2026-07-01` estrictamente sellado)  
**Veredicto Formal:** `FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`

---

## 1. Resumen Ejecutivo

Se ejecutó la primera campaña formal, causal y determinista de medición de la hipótesis **HP-007 — Corredores de Vacío / Resistencia Microestructural**, bajo el protocolo gobernado por [HP007_MEASUREMENT_CONTRACT_V1.md](file:///d:/EdgeLab-hp007/docs/research/HP007_MEASUREMENT_CONTRACT_V1.md), el manifiesto de preregistro [HP007_CAMPAIGN_PREREGISTRATION_2026-09-15.json](file:///d:/EdgeLab-hp007/docs/research/HP007_CAMPAIGN_PREREGISTRATION_2026-09-15.json) y el libro de variantes [HP007_VARIANTS_LEDGER_2026-09-15.json](file:///d:/EdgeLab-hp007/docs/research/HP007_VARIANTS_LEDGER_2026-09-15.json).

### Principales Conclusiones Empíricas:
1. **Desmontaje Causal de la Variante Headline Histórica (`VAR_001`):**  
   Los parámetros heredados del script exploratorio no causal previo (`forward_density <= 0.28`, `backstop_density >= 0.70`, ancho 4–7 ticks, target 10t, stop 3t) produjeron **exactamente 0 candidatos cualificados** ($N_{\text{pairs}} = 0$) en ambos contratos (`6E 03-26` y `6E 06-26`). La auditoría demuestra de forma concluyente que las zonas microestructurales causales punto-en-el-tiempo no exhiben de manera simultánea un backstop superior al 70% y una forward density inferior al 28% en anchos angostos de 4 a 7 ticks. Las cifras históricas optimistas derivaban de sesgo retrospectivo (*lookahead*) y falta de causalidad estricta.

2. **Grilla Estructural Multivariante (54 Variantes, $N_{\text{eff}} = 29$):**  
   Al expandir el espacio paramétrico a anchos realistas (8–14 ticks) y calibraciones de densidad robustas:
   - 34 de las 54 variantes exhibieron una media aritmética no ajustada positiva frente a sus controles pareados ($\Delta_{\text{net\_R}} > 0$).
   - Variantes con alta densidad de backstop y anchura intermedia (p. ej., `VAR_039`, `VAR_041`, `VAR_023`) alcanzaron $\Delta_{\text{base}} \in [+0.205\text{R}, +0.343\text{R}]$ con $p$-values nominales no corregidos de $p \approx 0.0010$.
   - Sin embargo, tras aplicar el ajuste de control de tasa de error por familia (FWER) de **Holm-Bonferroni** sobre las 54 variantes ($N_{\text{eff}} = 29$), **ninguna variante sobrevivió al umbral $\alpha = 0.05$** (mínimo $p_{\text{Holm}} = 0.0540 > 0.05$).

3. **Colapso Fuera de Muestra en Walk-Forward por Contrato:**  
   En la partición Walk-Forward estricta (Entrenamiento: `6E 03-26` $\to$ Test OOS: `6E 06-26`):
   - La mejor variante seleccionada en Train fue `VAR_025` con $\Delta_{\text{train}} = +0.5032\text{R}$ ($p = 0.1678$, $N_{\text{pairs}} = 47$).
   - Al evaluarla estrictamente fuera de muestra sobre el contrato siguiente `6E 06-26`, su rendimiento colapsó a $\Delta_{\text{test}} = -0.0102\text{R}$ ($p = 0.5195$, $N_{\text{pairs}} = 104$).
   - El Ratio de Eficiencia Walk-Forward fue de **$-0.02$**, indicando una degradación total del contraste y ausencia de generalización temporal entre vencimientos de futuros.

4. **Veredicto:**  
   Conforme al contrato de auditoría, se emite el veredicto terminal:  
   **`FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`**.

---

## 2. Inventario de Datos y Cortafuegos de Holdout

- **Universo Temporal In-Sample:**
  - `6E 03-26`: 5,064,128 ticks canónicos (2026-01-02 a 2026-03-13).
  - `6E 06-26`: 5,554,201 ticks canónicos (2026-03-15 a 2026-06-12).
- **Holdout Firewall (`2026-07-01` en adelante):**  
  Estrictamente sellado por `edgelab.research.holdout_guard`. Cero señales evaluadas, cero ticks leídos, cero outcomes generados. `holdout_signals_opened = 0`.
- **Política de Roll y Contratos Continuos:**  
  Los contratos continuos sintéticos cross-asset carecen de una regla monótona certificada de volumen líder (`previous_complete_session_volume_leader_monotonic_v1`). Fueron clasificados formalmente como **`ABSTAIN`** para prevenir artefactos espurios de empalme o saltos de precios no ejecutables.

---

## 3. Metodología de Medición Causal

La campaña aplicó cuatro salvaguardas metodológicas estrictas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. ADAPTADOR CAUSAL LOCAL (edgelab/adapters/hp007_causal_adapter.py)        │
│    - Detección de zonas BigTrap2Absorption punto-en-el-tiempo.              │
│    - Creado_ns <= Disponible_ns <= Decision_ns. Cero peeking futuro.        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. SELECCIÓN SIN SOLAPAMIENTO (select_non_overlapping)                      │
│    - Cooldown determinista entre episodios antes de observar outcomes.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. MATCHING 1:1 DETERMINISTA (deterministic_matched_pairs)                 │
│    - Estratificación exacta: Contrato x Dirección x TimeBucket x Vol x Imp. │
│    - Caliper sobre Score de Forward Density (<= 0.25).                      │
│    - Asignación 1:1 sin reemplazo sobre covariables pre-tratamiento.        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. INFERENCIA A NIVEL SESIÓN (paired_session_inference)                     │
│    - Agrupación del estimand Delta_net_R por sesión bursátil.               │
│    - Bootstrap clusterizado (1000 resamples) + permutación de signos.       │
│    - Corrección FWER de Holm-Bonferroni (N_total = 54, N_eff = 29).         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Escenarios de Fricción Evaluados (`edgelab/research/costs.py`):
- **Ideal:** 0.0 ticks round-turn (fricción cero teórica).
- **Base:** 2.768 ticks round-turn ($12.50 slippage + $4.80 comisión para 6E).
- **Adverso:** 4.768 ticks round-turn ($25.00 slippage + $4.80 comisión).
- **Severo:** 6.768 ticks round-turn ($37.50 slippage + $4.80 comisión).

---

## 4. Resultados Detallados de la Grilla (54 Variantes)

### Tabla de Variantes Principales (Ordenadas por $\Delta_{\text{net\_R}}$ en Escenario Base)

| Variante | Ancho (t) | Fwd Max | Bck Min | Target / Stop | $N_{\text{pairs}}$ | $\Delta_{\text{base}}$ (R) | $p_{\text{raw}}$ | $p_{\text{Holm}}$ | Veredicto / Findings |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **VAR_013** | 4–7 | 0.28 | 0.50 | 10 / 3 | 13 | +1.6667 | 0.5095 | 1.0000 | `ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS` |
| **VAR_014** | 4–7 | 0.28 | 0.50 | 6 / 3 | 13 | +1.6154 | 0.5095 | 1.0000 | `ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS` |
| **VAR_031** | 4–7 | 0.35 | 0.50 | 10 / 3 | 57 | +0.8648 | 0.0849 | 1.0000 | `ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS` |
| **VAR_007** | 4–7 | 0.28 | 0.00 | 10 / 3 | 22 | +0.5778 | 0.4775 | 1.0000 | `ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS` |
| **VAR_008** | 4–7 | 0.28 | 0.00 | 6 / 3 | 22 | +0.5333 | 0.4775 | 1.0000 | `ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS` |
| **VAR_039** | 8–14 | 0.20 | 0.70 | 10 / 3 | 2,232 | +0.3434 | 0.0010 | 0.0540 | FWER no significativo ($p > 0.05$) |
| **VAR_041** | 4–14 | 0.20 | 0.70 | 10 / 3 | 2,232 | +0.3434 | 0.0010 | 0.0540 | FWER no significativo ($p > 0.05$) |
| **VAR_040** | 8–14 | 0.20 | 0.70 | 6 / 3 | 2,232 | +0.2480 | 0.0020 | 0.1000 | FWER no significativo ($p > 0.05$) |
| **VAR_042** | 4–14 | 0.20 | 0.70 | 6 / 3 | 2,232 | +0.2480 | 0.0020 | 0.1000 | FWER no significativo ($p > 0.05$) |
| **VAR_023** | 4–14 | 0.35 | 0.70 | 10 / 3 | 5,119 | +0.2054 | 0.0010 | 0.0540 | FWER no significativo ($p > 0.05$) |
| **VAR_021** | 8–14 | 0.35 | 0.70 | 10 / 3 | 5,098 | +0.2048 | 0.0010 | 0.0540 | FWER no significativo ($p > 0.05$) |
| **VAR_005** | 4–14 | 0.28 | 0.70 | 10 / 3 | 3,711 | +0.1888 | 0.0090 | 0.4315 | FWER no significativo ($p > 0.05$) |
| **VAR_010** | 8–14 | 0.28 | 0.00 | 6 / 3 | 35,404 | -0.0123 | 0.8072 | 1.0000 | Control empata/supera |
| **VAR_030** | 4–14 | 0.35 | 0.00 | 6 / 3 | 31,739 | -0.0174 | 0.8442 | 1.0000 | Control empata/supera |
| **VAR_001** | 4–7 | 0.28 | 0.70 | 10 / 3 | 0 | 0.0000 | 1.0000 | 1.0000 | `FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL` |

---

## 5. Auditoría de Robustez y Walk-Forward por Contrato

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ WALK-FORWARD CONTRACT FOLD 1: TRAIN (6E 03-26) -> TEST (6E 06-26)           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Variante Seleccionada en In-Sample: VAR_025                                 │
│   - Train IS: Delta_net_R = +0.5032 R (p = 0.1678, N_pairs = 47, 15 sess)   │
│   - Test OOS: Delta_net_R = -0.0102 R (p = 0.5195, N_pairs = 104, 21 sess)  │
│   - Walk-Forward Efficiency (WFE): -0.02                                    │
│                                                                             │
│ Veredicto WF: FALLA TOTAL DE GENERALIZACIÓN FUERA DE MUESTRA                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Análisis de Concentración y Robustez:
- **Concentración Top 1:** $0.0\%$ (no aplica debido a paridad o tamaño).
- **Concentración Top 5:** $0.0\%$ del delta total.
- **Sensibilidad a Fricción:** Cuando los costos aumentan al escenario adverso ($4.768\text{t}$) y severo ($6.768\text{t}$), las variantes con targets reducidos ($6\text{t}$) experimentan una degradación de retorno neto superior al $80\%$, dejando de cubrir costos transaccionales.

---

## 6. Dictamen de Auditoría y Próximos Pasos

1. **Rechazo de la Hipótesis HP-007 en su Formulación Actual:**  
   La hipótesis de que "la ausencia de resistencia microestructural inmediata genera una aceleración sistemática y explotable hacia la siguiente zona con expectativa positiva neta sobre un control emparejado" **no se sostiene causalmente**.
2. **Causa Raíz de la Ilusión Exploratoria:**  
   La investigación previa utilizaba señales retrospectivas donde la definición de zona dependía de datos posteriores a la decisión o carecía del cortafuegos de sesión y fricción transaccional real. Al exigir causalidad rigurosa y emparejamiento 1:1 por covariables, el supuesto edge se desvanece.
3. **Recomendación:**  
   Archivar HP-007 con clasificación `FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`. No autorizar apertura de holdout. Reorientar el esfuerzo investigativo hacia geometrías de absorción directa en balance institucional (BigTrap2Absorption primario) en lugar de corredores de vacío residuales.
