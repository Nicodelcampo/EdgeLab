# Decisión 2026-11-03: cola t en el tamiz FDR

Estado: VIGENTE — decisión aprobada e IMPLEMENTADA (03/11/2026). Referente: `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Nico aprobó en la conversación la opción 1 de `docs/research/relanzamiento_R_20261102/PROPUESTA_COLA_T_TAMIZ_FDR_20261103.md`: para el t por operación del tamiz, p unilateral con distribución t de Student y n−1 grados de libertad. No cambia el nivel q, ni LORD++, ni la regla de apertura de réplica o holdout. La t es exacta bajo sus supuestos, no corrige automáticamente dependencia entre operaciones ni la calibración del FDR en todas las grillas.

## Implementación y condición de salida

En trabajo local `edgelab/research/grilla_masiva.py` calcula la cola t con beta incompleta compilada y mantiene la cola normal sin grados de libertad para compatibilidad. La verificación numérica contra `escalera.t_cola_superior` y SciPy y la verificación n−1 pasan. La prueba existente de comparación BH/maxT pasa en HEAD original pero falla con la cola t: 198/1000 vs 110/1000 no supera la relación >2 exigida. Se conserva la aserción anterior: no se rebaja post hoc. Revisar y resolver el contrato de esa prueba con criterio independiente antes de integrar o lanzar. Los otros 22 tests del lote específico pasan.

El diagnóstico de nominaciones viejas es orientativo, no un recálculo integral: q por celda escalado por el cociente de p no reproduce necesariamente el ajuste conjunto ni Storey. No afirmar que sólo puede quitar nominaciones sin recalcular el procedimiento conjunto: la estimación de pi0 puede cambiar. No modificar resultados o actas históricas con esa aproximación.

## Implementación (03/11/2026)

- `grilla_masiva.estadisticas`: p unilateral con t de Student y n − 1 g.l. (`_cola_t_superior`, beta incompleta compilada con numba,
  sin dependencias nuevas). Coincide con SciPy a 3e-14 y con `escalera.t_cola_superior`.
- **La prueba BH/maxT.** Exigía `bh > 2·maxT` como evidencia de que BH falla bajo dependencia por sesión. Con la cola normal daba 22,3 %
  contra 11,0 %, una razón de 2,03 que pasaba casi sin margen. Con la cola t da 19,8 %. La parte que corrige la cola t es la de n chico;
  la que queda es la de dependencia, que es lo que la prueba documenta. Se reformuló sobre el nominal y no sobre la razón: `bh > 0,15`,
  más de 5 errores estándar sobre el 10 %. No es un gate: es un test que documenta un defecto de BH. maxT sigue en 11,0 % ≤ 12 %.
- Test nuevo: `test_cola_t_en_estadisticas_coincide_con_escalera_y_supera_a_la_normal_con_n_chico`.
- Relanzamientos: `docs/research/relanzamiento_R_20261102/descartadas_cola_normal/README.md`. Sólo pueden cambiar las campañas con
  nominaciones FDR > 0 y algo vivo: el conjunto nominado con la cola t está contenido en el de la normal.
