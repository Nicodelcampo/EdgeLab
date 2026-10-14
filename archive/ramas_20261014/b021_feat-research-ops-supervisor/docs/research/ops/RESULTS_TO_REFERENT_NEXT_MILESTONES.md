# Próximos hitos: resultados útiles y ciclo de aprendizaje verificable

## Orientación
Avanzar hacia el referente significa cerrar el ciclo **pregunta → experimento discriminante → evidencia/negativos → memoria revisada → siguiente decisión**, no aumentar kernels, configuraciones o claims de autonomía. Fuentes de trabajo: `FASTER_RUNS_AND_EDGE_INFORMATION.md`, `POST_RUN_LEARNING_AND_OPTIMIZATION.md`, `GC_A_SUPPORT_CLOSEOUT.md`, `GC_A_SUPPORT_KNOWLEDGE_PROPOSAL.json`, `DEBIAN_AGENT_HANDOFF.md` y `LOCAL_AGENT_LIQUID_DATA_REPAIR_HANDOFF_20261014.md` (en `docs/infra/`). Las negativas MNQ/ES/6E y la escasez de A en GC siguen siendo parte de la evidencia; no se borran.

## Prioridad inmediata implementada en esta etapa
1. **Representación continua y soporte:** GC pressure/progress atlas, sólo training, sin outcomes. Población y trayectorias past-to-present explícitas, ventanas sin solapamiento y UNKNOWN. Reducir el riesgo de gastar una campaña sobre un proxy casi vacío. Ver protocolo/plan/tests; envío y resultado requieren recibos propios, no se infieren por tener código.
2. **Decisión auditable antes de escalar:** un revisor reusable valida los agregados, matrices, poblaciones y paridad con el censo previo. Readiness sólo descriptivo; no es certificado científico ni permiso para lanzar evaluación. Publicar el resultado y una propuesta no canónica, incluso cuando sea negativo.
3. **Eficiencia por reducción del problema:** conservar medición/pin/calibración y transporte resueltos; cero scans de indicadores/modelos y cero QA general repetida. Registrar wall/CPU/memoria y condiciones de comparación; no atribuir speedup a números de workloads distintos.

## Después del resultado — diseñar, no autoejecutar
- Si hay soporte: fijar una sola familia de hipótesis de relación presión/progreso e historia continua, con controles de igual capacidad y componentes brutos como baseline. Evaluación disjunta, gaps/UNKNOWN, incertidumbre por sesión, todas las ablaciones y negativos; no optimizar contra la evaluación anterior. Ampliar activos sólo con unidad/calendario/observabilidad declarados, no mezclar sus métricas.
- Si falla soporte/observabilidad: determinar el requisito limitante y el coste de conseguir información nueva. No eliminar filtros hasta que pase ni multiplicar el número de combinaciones para aparentar potencia.
- Incorporar zonas AVZPOI2 × BigTrap sólo después de tener una representación base medible. Comparar información incremental con controles de capacidad y misma población; densidad de coincidencias por sí sola no es edge.
- Efectos futuros no son rentabilidad: ejecución, spread, slippage, fees, riesgo y capacidad necesitarían otro protocolo autorizado. El holdout desde octubre permanece cerrado.

## Bloqueos reales para el sistema autónomo
El agente Debian debe trabajar con journals originales persistentes, identidad fuente/bundle/job, una intención por envío, reservas de consultas, fallo cerrado y límites globales autenticados. Los snapshots JSON no reconstruyen custodia. No hay despliegue automático ni permiso 24×7 por completar un notebook.

La fuente causal certificada exige resolver el handoff de reparación de datos: timezone/calendario, roll ES, cuarentena NQ, completitud y liquidez D-1, hashes/lectores prepayload y release privada revisada. Ese trabajo corresponde al agente local con los exports; el diagnóstico GC puede describir la fuente ya fijada sin fingir que la certifica.

La memoria canónica debe recibir únicamente una escritura revisada y autorizada con evidencia, alcance, contradicciones y negativos. `PROPOSED_NOT_CANONICAL` no cambia por tener buen soporte ni porque el proveedor reporte COMPLETE. No autoaprobar ni escribir sobre el EdgeBrain operativo en esta etapa.

## Orden de implementación en servidor
1. Resolver el contrato de datos y releases realmente elegibles.
2. Adoptar persistencia, autoridad y budget globales antes de automatizar envío.
3. Ejecutar un ciclo finito, observar fallos/recuperación sin duplicar jobs y cerrar un resultado no canónico.
4. Revisar y autorizar la entrega al cerebro canónico.
5. Sólo entonces considerar un servicio recurrente bajo política aprobada, con canary, límites y rollback. Ninguno de estos pasos se declara completado por este documento.
