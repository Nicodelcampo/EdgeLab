# Registro de Limitaciones, Abstenciones y Supuestos — Hipótesis HP-007

**Fecha:** 2026-09-15  
**Campaña:** `HP007-CAMP-001`  
**Autoridad de Gobernanza:** `docs/research/HP007_MEASUREMENT_CONTRACT_V1.md`  
**Worktree:** `D:\EdgeLab-hp007`  
**Rama:** `work/hp007-causal-campaign-v1-20260915`

---

## 1. Declaración Formal de Abstenciones Metodológicas

En estricta observancia de los rituales permanentes de EdgeLab, la integridad del proceso de investigación y la política de prevención de falsos positivos, se establecieron las siguientes **abstenciones formales vinculantes**:

### 1.1. Abstención sobre Contratos Continuos Cross-Asset
- **Condición Encontrada:** Los datasets de contratos continuos sintéticos (`6E_CONT` u otros activos cross-asset) carecen de una especificación certificada de política de rolado monótona por volumen líder en la sesión previa completa (`previous_complete_session_volume_leader_monotonic_v1`).
- **Riesgo:** El uso de empalmes ad-hoc o basados en fechas de expiración arbitrarias introduce saltos artificiales de precios (gaps de rolado) y volumen sintético distorsionado, generando señales espurias de "vacío de liquidez".
- **Dictamen:** **`ABSTAIN_UNREGISTERED_ROLL_POLICY`**. La campaña formal se abstuvo de procesar contratos continuos y restringió su ejecución exclusivamente a los contratos trimestrales individuales con procedencia verificada.

### 1.2. Abstención por Insuficiencia de Sesiones Independientes
- **Condición Encontrada:** En variantes con anchos angostos (4–7 ticks) y filtros de densidad estrictos (p. ej., `VAR_007`, `VAR_008`, `VAR_013`, `VAR_014`, `VAR_031`, `VAR_032`), el número de sesiones bursátiles que contenían al menos un par emparejado fue inferior a 30 ($N_{\text{sessions}} < 30$).
- **Riesgo:** La inferencia bootstrap a nivel sesión pierde potencia y estabilidad asintótica con muestras pequeñas, lo que infla artificialmente el retorno aparente por eventos atípicos aislados.
- **Dictamen:** **`ABSTAIN_TOO_FEW_INDEPENDENT_SESSIONS`**. Dichas variantes quedan formalmente invalidadas para cualquier reclamo de significancia estadística, con independencia del valor nominal de su media.

---

## 2. Cortafuegos Institucional del Holdout

- **Período de Holdout:** `2026-07-01` a `2026-12-31`.
- **Estado de Sellado:** **100% INTACTO**.
- **Garantías Técnicas Implementadas:**
  - `edgelab.research.holdout_guard.assert_no_holdout_access`: validación en tiempo de ejecución que aborta cualquier lectura de ticks o señales con fecha $\ge \text{2026-07-01}$.
  - El conjunto consolidado de señales (`136,190` observaciones) contiene **0 observaciones** pertenecientes al holdout.
  - Ningún parámetro de la grilla, de matching o de costos fue optimizado o ajustado sobre datos posteriores al `2026-06-12` (cierre de `6E 06-26`).

---

## 3. Alcance de los Datos y Validez Externa

### 3.1. Concentración en un Único Subyacente (Euro FX — 6E)
- La campaña se ejecutó sobre futuros de Euro FX (`6E 03-26` y `6E 06-26`) negociados en CME Globex.
- **Limitación:** Los resultados no pueden extrapolarse de manera directa a activos con diferente microestructura de libro de órdenes, tales como futuros de índices (ES, NQ) o commodities (GC, CL), sin un preregistro específico que calibre el tamaño del tick, la profundidad media y la dinámica de absorción institucional.

### 3.2. Dependencia del Calibrador de Zonas BigTrap2Absorption
- El cálculo de las densidades forward y backstop depende directamente del detector causal `BigTrap2Absorption`.
- Si bien la paridad del kernel ha sido auditada rigurosamente (`KERNEL_PARITY_ON_EQUAL_INPUT = ~EXACT`), el indicador opera bajo parámetros fijos de absorción y trap. La campaña midió la respuesta del mercado a las zonas tal como fueron delimitadas por este algoritmo, no a cualquier definición arbitraria o discrecional de soporte/resistencia.

---

## 4. Modelado de Costos y Supuestos de Ejecución

### 4.1. Supuesto de Ejecución a la Primera Transacción Disponible
- La resolución de primer pasaje asume que el trade se ejecuta en el primer tick estrictamente posterior a `decision_ns`.
- Se aplicó una penalización fija de slippage y comisiones (`2.768t` en el escenario base) conforme a `edgelab/research/costs.py`.
- **Limitación:** No se modeló el impacto de mercado adverso inducido por órdenes de gran tamaño (supuesto de tomador de liquidez pasivo/pequeño lote). Para órdenes de tamaño institucional, el slippage efectivo degradaría aún más el retorno neto.

### 4.2. Tratamiento de Barreras Simultáneas
- Cuando en un único tick o secuencia rápida se alcanzaron simultáneamente el target y el stop, el algoritmo clasificó el evento como ambiguo y no le asignó resultado favorable, garantizando una postura conservadora (cero optimismo).

---

## 5. Dictamen Final de Gobernanza

El fallo de la hipótesis HP-007 (`FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`) constituye un resultado positivo para la gobernanza de EdgeLab: demuestra que el sistema de auditoría causal previene con éxito el despliegue de estrategias basadas en espejismos exploratorios, protegiendo el capital de investigación y manteniendo la integridad del referente empírico.
