# Contextos L2 (4 climas) en NQ — resultado del entrenamiento (2026-09-28)

Protocolo `PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md`; runner `tools/build_l2_contexts_nq.py` (plan sha `b1958936…`); commit
`a8be2b70`, **árbol limpio**; target-free (`outcomes_accessed` false). Entrenamiento 20 sesiones (26/06–28/07),
evaluación 40 (29/07–23/09). Artefactos `artifacts/l2_contexts/NQ/{gate_report,model}.json` (+ `labels.parquet` local).

**Veredicto de la compuerta: PASS, sin STOPs.**

| Métrica | Valor |
|---|---|
| Cobertura | 53.872 / 53.872 minutos elegibles etiquetados (100 %) |
| Estabilidad entre semillas (eval) | acuerdo mínimo 0,970 (calm 0,971, normal 0,958, volatile 0,967) |
| Minutos por clima (eval) | calm 35.656 · normal 8.430 · toxic 5.245 · volatile 4.541 |
| Racha mediana | calm 18 min · volatile 15 · normal 11 · toxic 7 |
| Cambios de clima por hora | 2,3 |
| Concentración horaria (máx. 2 h) | calm 0,11 · normal 0,15 · volatile 0,19 · toxic 0,25 (todas pasan) |
| Sólo-hora predice el clima | 0,30 contra 0,66 de la clase mayoritaria: los climas no son un reloj |

## Reconstrucción del libro (tres arreglos del 28/09)
Cruce intra-lote (ask nuevo antes de borrar el bid viejo), cruce real en preapertura sin vaciar el libro, y foto de
9 niveles en un MBP10 (hueco de cola). Resultado: 45 de 60 sesiones con 1.371 minutos elegibles; la peor, 1.108.

## A vigilar (no es STOP)
- **Deriva en el roll (15/09):** antes calm 62 % / normal 18 % / toxic 10 % / volatile 10 %; después calm 84 % / normal 5 %
  / toxic 7 % / volatile 3 %. Sólo 6 sesiones post-roll y septiembre fue tranquilo, pero puede ser el contrato nuevo
  (dic-26) con otra profundidad. Revisar con más sesiones de dic-26 antes de usar los climas como filtro allí.
- El `model_id` conserva el prefijo `gate_gc_…` heredado del runner de GC: es nombre, no contenido (el plan y los
  datos son NQ).

## Qué habilita
Los climas se pueden usar como **filtro/estratificación** en julio–septiembre (desarrollo, adenda A3), con confirmación
sólo de octubre en adelante. Primeros usos candidatos: separar por clima la continuación/reversión del espejo y el
cruce del 25 %.
