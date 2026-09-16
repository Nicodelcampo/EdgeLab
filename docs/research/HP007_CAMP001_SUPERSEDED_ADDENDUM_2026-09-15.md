# Addendum de Supersesión no destructiva: HP007-CAMP-001

**Fecha:** 2026-09-15  
**Campaña Original:** `HP007-CAMP-001`  
**Campaña Sucesora:** `HP007-CAMP-002` (Rejection Revisit / Structural Traversal)  
**Rama de Ejecución:** `work/hp007-rejection-revisit-campaign-v2-20260915`  
**Referencia Rector:** `docs/research/PROMPT_ANTIGRAVITY_HP007_CAMP002_REJECTION_REVISIT_2026-09-15.md`

---

## 1. Principio de Preservación de Evidencia Histórica
En estricto cumplimiento de las reglas de integridad de `AGENTS.md` y de la directiva de la Campaña 002:
1. Los artefactos, códigos, registros de variantes y métricas agregadas de `HP007-CAMP-001` (`commit 949f7c4`) se conservan íntegros e inalterados.
2. Ningún archivo histórico ha sido borrado, reescrito o trasladado.
3. El veredicto de la Campaña 001 (`FAIL_NO_INCREMENTAL_EDGE_OVER_MATCHED_CONTROL`) permanece registrado en su manifest canónico como hecho empírico sobre la formulación P&L/trading-rule original.

---

## 2. Limitaciones Metodológicas de la Campaña 001 Superadas en Campaña 002

| Eje Mecánico | Implementación Campaña 001 | Corrección Formal Campaña 002 |
| :--- | :--- | :--- |
| **Cap de Horizonte** | Truncado arbitrario a 1,000 ticks | Removido totalmente; corte causal por `np.searchsorted` sobre timestamps |
| **Etiquetado Incompleto** | Etiquetado como `TIMEOUT` | Diferenciado estrictamente: `DATA_EDGE` vs `CENSORED` |
| **Orden de Ticks** | Validación parcial de tiempo | Validación bidimensional obligatoria `(ts_utc_ns, sequence)` en cada fila |
| **Calendario / Trade Date** | Límite UTC rígido | `America/Chicago` (CME trade date) con soporte certificado para DST y ventana de mantenimiento |
| **Pregunta de Investigación** | Búsqueda económica de P&L, Sharpe, stops y targets fijos | Transiciones de estado microestructurales libres de P&L (primer rechazo → alejamiento → re-acercamiento → traversa vs segundo rechazo vs censura) |
| **Sesgo de Selección** | Comparación de corredores contra controles de mercado aleatorios sin aislar el evento de rechazo previo | Comparación contra acercamientos frescos comparables (matched fresh first approaches) y dose-response de alejamiento/desgaste |
| **Resolución Holm** | 1,000 permutaciones (insuficiente para 54 tests bajo FWER) | $\ge 100,000$ extracciones deterministas / sign-flips exactos garantizando resolución completa |
| **Ablaciones** | Solo switches globales en `WeightSpec` | Contrastes directos corregidos por Holm de 3 ablaciones de un componente (`NO_MATURATION`, `NO_TIME_DECAY`, `NO_WEAR`) contra `FULL` |

---

## 3. Estado de Holdout
El holdout `2026-07-01 -> 2026-12-31` se mantuvo 100% sellado durante la Campaña 001 y permanece 100% sellado e inobservado durante la Campaña 002. Cero filas, señales u outcomes en ventana de holdout.
