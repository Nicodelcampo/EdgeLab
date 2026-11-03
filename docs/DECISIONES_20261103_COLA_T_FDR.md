# Decisión 2026-11-03: cola t en el tamiz FDR

Estado: VIGENTE — decisión aprobada; implementación local pendiente de validación e integración. Referente: `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Nico aprobó en la conversación la opción 1 de `docs/research/relanzamiento_R_20261102/PROPUESTA_COLA_T_TAMIZ_FDR_20261103.md`: para el t por operación del tamiz, p unilateral con distribución t de Student y n−1 grados de libertad. No cambia el nivel q, ni LORD++, ni la regla de apertura de réplica o holdout. La t es exacta bajo sus supuestos, no corrige automáticamente dependencia entre operaciones ni la calibración del FDR en todas las grillas.

## Implementación y condición de salida

En trabajo local `edgelab/research/grilla_masiva.py` calcula la cola t con beta incompleta compilada y mantiene la cola normal sin grados de libertad para compatibilidad. La verificación numérica contra `escalera.t_cola_superior` y SciPy y la verificación n−1 pasan. La prueba existente de comparación BH/maxT pasa en HEAD original pero falla con la cola t: 198/1000 vs 110/1000 no supera la relación >2 exigida. Se conserva la aserción anterior: no se rebaja post hoc. Revisar y resolver el contrato de esa prueba con criterio independiente antes de integrar o lanzar. Los otros 22 tests del lote específico pasan.

El diagnóstico de nominaciones viejas es orientativo, no un recálculo integral: q por celda escalado por el cociente de p no reproduce necesariamente el ajuste conjunto ni Storey. No afirmar que sólo puede quitar nominaciones sin recalcular el procedimiento conjunto: la estimación de pi0 puede cambiar. No modificar resultados o actas históricas con esa aproximación.
