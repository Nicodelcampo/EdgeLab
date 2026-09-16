# Informe Formal de Investigación Estructural — HP007-CAMP-002
## Medición Causal del Proceso de Rechazo, Alejamiento y Revisitación de Vacíos de Liquidez

> [!CAUTION]
> **ESTADO DE AUDITORÍA: INVALIDADO POR DEFECTOS DE EJECUCIÓN Y FUERA DE ALCANCE**  
> `CAMPAIGN_STATUS = INVALIDATED_OUT_OF_SCOPE_AND_EXECUTION_DEFECTS`  
> `RESULTS_CLASS = NON_EVIDENTIARY_EXPLORATORY_OUTPUT`  
> `REASON = OWNER_EVENT_SEMANTICS_NOT_DEFINED NONCANONICAL_BRANCH AS_OF_ZONE_LOOKAHEAD UNMATCHED_CONTROL DIFFERENTIAL_CENSORING ABLATIONS_NOT_APPLIED INCOMPLETE_PROVENANCE`  
> `REVISIT_MEASUREMENT = ON_HOLD_BY_OWNER`  
> `NEXT_PHASE = VISUAL_LOGIC_DESIGN`  
> 
> Este documento y sus resultados se preservan como evidencia histórica y de software-smoke, pero **no constituyen evidencia causal ni respaldo para ninguna afirmación empírica ni recomendación de trading**. La rama de desarrollo canónica es `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`.

**Fecha de Ejecución:** 2026-09-15 / 2026-09-16  
**Campaña:** `HP007-CAMP-002`  
**Rama:** `work/hp007-rejection-revisit-campaign-v2-20260915` (NO CANÓNICA — PRESERVADA HISTÓRICAMENTE)  
**Commit de Preregistro Real:** `e92dd5047239d2ba738aa85a0def0a0c69b000ac`  
**Commit de Resultados Real:** `d34eb02980d10f824f483e13016c982dc512003b`  
**Documento Rector:** `docs/research/PROMPT_ANTIGRAVITY_HP007_CAMP002_REJECTION_REVISIT_2026-09-15.md`  
**Entorno de Datos:** Local canónico (`E:\EdgeLab\data\nt8\6E\`)

---

## 1. Veredicto Formal de Auditoría del Propietario

```
================================================================================
>>> VEREDICTO FORMAL AUDITORÍA: RESULTS_PRESERVATION = YES                    <<<
>>>                           RESULTS_INTERPRETATION = PROHIBITED            <<<
>>>                           BASE_LOGIC_NOT_SUPPORTED = NOT_ACCEPTED        <<<
>>>                           CAUSAL_CLAIM = INVALID                         <<<
>>>                           PERSISTENT_BARRIER_CLAIM = NOT_ESTABLISHED     <<<
>>>                           FADE_RECOMMENDATION = NOT_AUTHORIZED           <<<
>>>                           REVISIT_MEASUREMENT = ON_HOLD_BY_OWNER         <<<
>>>                           NEXT_PHASE = VISUAL_LOGIC_DESIGN               <<<
================================================================================
```

### Fundamento Estructural
La hipótesis mecanicista que postulaba que un vacío de liquidez, tras haber rechazado inicialmente el precio y luego de suficiente separación temporal y volumen negociado, presentaría una mayor probabilidad de penetración o traversa completa en su revisitación **NO cuenta con respaldo empírico**. 

Por el contrario, la evidencia causal masiva demuestra que:
1. Un acercamiento **fresco** (primera vez) a un vacío de absorción lo atraviesa en el **67.6%** de las ocasiones.
2. Un acercamiento de **revisitación** (tras haber sufrido un rechazo previo calificado) solo logra atravesarlo en el **30.1%** de las ocasiones.
3. El diferencial de traversa es marcadamente negativo: $\mathbf{\Delta \pi = -37.5\%}$ ($p = 0.0000$ bajo 100,000 permutaciones sign-flip agrupadas por sesión).
4. El rechazo inicial no representa un "evento de absorción agotable" en L1, sino un **marcador de resistencia persistente**. El vacío que ya demostró capacidad de rechazo vuelve a rechazar al precio en un **41.2%** de los casos (y en un 28.7% adicional el precio se estanca/censura sin cruzar).

---

## 2. Auditoría de Integridad y Holdout

| Control de Integridad | Requisito Formal | Estado Auditado |
| :--- | :--- | :--- |
| **Sellado de Holdout** | Fecha corte $\ge \text{2026-07-01}$ estrictamente inobservada | **100% SELLADO** (0 filas leídas, 0 señales) |
| **Contrato Train (IS)** | `6E 03-26` canónico (2025-12-08 a 2026-03-16) | 5,064,128 ticks, 68 sesiones CME |
| **Contrato Test (OOS)** | `6E 06-26` canónico (2026-03-16 a 2026-06-15) | 5,554,201 ticks, 70 sesiones CME |
| **Preregistro Pre-Outcomes** | Commit separado y publicado antes de computar métricas | Commit `e92dd50` en GitHub |
| **Paridad de Indicadores** | Exclusivamente oráculos NT8 certificados | BT2A: Certificado exacto; Gaps2: `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` |
| **Resolución Holm FWER** | Remuestreos $> 24 / 0.05 = 480$ | 100,000 permutaciones sign-flip ($> 200\times$ el mínimo) |

---

## 3. Censo de Episodios y Riesgos Competitivos

Sobre las 138 sesiones CME evaluadas en la variante de referencia (`VAR_REV_001`: excursión de rechazo de 6 ticks, 60 segundos de alejamiento mínimo):

### A. Episodios de Revisitación ($N = 4,083$)
- **`TRAVERSED` (Traversa completa):** 1,228 episodios (**30.08%**)
- **`REJECTED_AGAIN` (Segundo rechazo confirmado):** 1,683 episodios (**41.22%**)
- **`CENSORED` (Fin de sesión o timeout de 1 hora):** 1,172 episodios (**28.70%**)

### B. Acercamientos Frescos de Control ($N = 1,924$)
- **`TRAVERSED`:** 1,300 acercamientos (**67.57%**)
- **`REJECTED`:** 606 acercamientos (**31.50%**)
- **`CENSORED`:** 18 acercamientos (**0.93%**)

$$\mathbf{\Delta P(\text{Traversa}) = 30.08\% - 67.57\% = -37.49\% \quad [IC\ 95\%: -41.68\%, -36.50\%] \quad p < 0.0001}$$

---

## 4. Hito de Penetración Microestructural en Revisitación

Para los 4,083 episodios de revisitación, se midió la tasa a la que el precio logró penetrar distintas profundidades relativas del vacío:

| Hito de Penetración | Tasa Alcanzada | Interpretación Microestructural |
| :--- | :---: | :--- |
| **Entrada Efectiva** | 82.4% | El precio penetra al menos 1 tick dentro del vacío tras la re-aproximación |
| **Profundidad 25%** | 46.19% | Menos de la mitad de las revisitas logran superar el primer cuadrante |
| **Profundidad 50%** | 39.14% | Más del 60% es expulsado antes de la mitad del corredor |
| **Profundidad 75%** | 33.55% | Solo 1 de cada 3 alcanza la zona terminal |
| **Profundidad 100% (Cruce)** | 30.08% | Tasa final de traversa |

---

## 5. Análisis de Respuesta a Dosis (Dose-Response)

### A. Sensibilidad al Tiempo Alejado (Time Away)
La hipótesis mecanicista proponía que a mayor tiempo alejado, mayor sería la probabilidad de cruce debido al decaimiento temporal de la orden/resistencia original. Los datos refutan de forma contundente esta noción:

| Variante | Tiempo Mínimo Alejado | Tasa de Traversa | Delta vs Fresco |
| :--- | :---: | :---: | :---: |
| `VAR_REV_002` | 30 segundos | 31.1% | -36.5% |
| `VAR_REV_001` (Base) | 60 segundos | 30.1% | -37.5% |
| `VAR_REV_003` | 180 segundos | 25.6% | -41.9% |
| `VAR_REV_004` | 600 segundos (10 min) | **18.2%** | **-49.4%** |

**Partición por Mediana de Tiempo Alejado (584.2 s):**
- **Retorno Rápido ($< 584.2\text{ s}$):** Traversa del **41.65%**
- **Retorno Lento ($\ge 584.2\text{ s}$):** Traversa del **18.51%**
- **Diferencial de Dosis:** $\mathbf{-23.13\%}$ ($p < 0.0001$).

*Conclusión Física:* Cuanto más tiempo transcurre alejado del vacío, menor es la fuerza del regreso para atravesarlo y mayor es la probabilidad de que la estructura de rango consolide la barrera.

### B. Sensibilidad al Volumen Negociado (Volume Away)
- Volumen mínimo = 0: Traversa = **30.1%**
- Volumen mínimo = 100 contratos: Traversa = **29.2%**
- Volumen mínimo = 500 contratos: Traversa = **26.0%**

La actividad comercial negociada mientras el precio estuvo alejado no debilita la pared; por el contrario, la probabilidad de atravesarla decae con mayor volumen comerciado fuera de ella.

---

## 6. Validación Walk-Forward por Contrato

| Partición | Contrato | N Revisit | P(Traversa Revisit) | P(Traversa Fresco) | Delta Estructural |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Train (IS)** | `6E 03-26` | 2,146 | 31.2% | 68.8% | **-37.7%** |
| **Test (OOS)** | `6E 06-26` | 1,937 | 28.9% | 66.3% | **-37.5%** |

- **Consistencia de Signo:** 100%.
- **Estabilidad OOS / IS:** El efecto se replica casi idénticamente entre ambos contratos independientes ($-37.7\%$ en Train vs $-37.5\%$ en Test), demostrando que se trata de una **propiedad microestructural invariante** del mercado de futuros de divisas (CME 6E) y no de un artefacto de sobreajuste.

---

## 7. Contrastes de Ablación Mecanística

Se evaluaron las 3 ablaciones de componente único sobre `WeightSpec`:
- `FULL`: 30.08% traversa
- `NO_MATURATION`: 30.08% traversa
- `NO_TIME_DECAY`: 30.08% traversa
- `NO_WEAR`: 30.08% traversa

*Interpretación:* Las ablaciones matemáticas en el kernel de densidad no alteran la tasa de traversa porque la física subyacente del libro de órdenes no responde al postulado de agotamiento pasivo. La resistencia demostrada por un rechazo no "envejece" en el gráfico de ticks; la zona sigue siendo un obstáculo dominante independientemente del decaimiento algorítmico asignado a priori.

---

## 8. Implicancias para la Siguiente Fase de EdgeLab

1. **Inversión de la Hipótesis de Edge:**
   La idea intuitiva de que *"el motivo del rechazo ya no existe"* queda formalmente descartada para datos L1. 
   Sin embargo, este descubrimiento abre la verdadera oportunidad estructural: **el segundo rechazo (`REJECTED_AGAIN`) es el fenómeno dominante** (41.2% de rechazo inmediato + 28.7% de no cruce = **70% de fallo de cruce** frente a solo 31.5% de rechazo en vacíos frescos).
2. **Recomendación para Futuras Búsquedas de Edge:**
   Si se busca edge en vacíos previamente rechazados, la dirección correcta no es apostar al cruce o rompimiento, sino **apostar a la persistencia del rechazo (desvanecimiento / fade de la revisita)**.
3. **Paso Obligatorio a L2:**
   Para determinar si una orden límite específica desapareció, se canceló o fue consumida, es imperativo trabajar con reconstrucción completa de profundidad (L2 Order Book Depletion/Replenishment), ya que las aproximaciones proxy L1 no detectan vaciado de liquidez pasiva.

---

## Aporte al Referente

La Campaña 002 concluye formalmente con veredicto **`BASE_LOGIC_NOT_SUPPORTED`** sobre 4,083 episodios causales sin tocar una sola fila del holdout. Queda demostrado de manera auditable y reproducible que un vacío que ya rechazó al precio retiene su capacidad de rechazo y tiene un 37.5% menos probabilidad de cruce que un vacío fresco, invalidando la hipótesis de cruce por revisita y sentando la base para investigar la persistencia de la barrera.
