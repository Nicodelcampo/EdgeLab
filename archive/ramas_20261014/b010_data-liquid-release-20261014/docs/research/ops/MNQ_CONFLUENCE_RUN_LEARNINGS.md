# Aprendizajes de los intentos de confluencia MNQ

Registro técnico revisable, **no adjudicación científica ni memoria canónica nueva**. Evidencia estructurada: `MNQ_CONFLUENCE_RUN_LEARNINGS.json`. El Brain canónico no se modifica; el circuito existente de custodia/revisión y destino aprobado sigue obligatorio.

## Observado

V1 falló después de completar 25 sesiones de formación: 2899645 capturas, frente a presupuesto de 3000000. Wall 1294.832117357 s; máximo RSS child muestreado 910565376 bytes. El watchdog no declaró parada por tiempo/RSS. No completó target ni replay geométrico; no hay resultados científicos nuevos ni estimación de speedup global. Preservar fallo, pins y progreso, no sólo intentos exitosos.

El límite de capturas es la hipótesis principal, **no causa confirmada**. V2 aumenta capacidad y añade categorías sanitizadas; mantiene fuente, warmup, target y parámetros. Última consulta: RUNNING, no éxito inferido. Un reintento del mismo universo no es réplica independiente.

## Lecciones operativas y científicas

- La carga de almacenamiento escala con capturas, no sólo ticks o RAM. No truncar silenciosamente al tocar el límite.
- El costo de fallo incluye volver a formar historia: no existe restore privado del estado actual. Un checkpoint futuro debe conservar todos los estados/carries e identidad, quedarse dentro de Kaggle y exigir revisión antes de resume.
- RSS muestreado de un child no es peak medido del job completo. **No crear una RunObservation elegible para el outbox existente inventando esa medición.** Tampoco sustituir por cgroup raíz compartido.
- Geometría cerrada half-tick puede incluir contactos sin print entero. Coincidencia ≠ llegada ≠ respuesta favorable.
- Mayor densidad aumenta ocupación; el análisis debe comparar censos propios de oportunidades, mismas poblaciones de anchors y aporte incremental, no contar coincidencias como edge.
- Racimos derivan de AVZ; no son votos independientes. Origen consumido y disponibilidad de la captura no son el mismo clock; carry va separado.
- Aproximación aceptada NT8 no autoriza afirmar un porcentaje medido ni eliminar tests de equivalencia interna.
- El holdout permanece cerrado; sin P&L, auto-promoción, QA repetida o nueva selección por outcomes.

## Cómo acelerar la fase siguiente

Ya implementado: primitivas/barras compartidas por spec, motores con historia continua, CSV diagnóstico desactivado, joins incrementales, triadas secuenciales, racimo sweep/Fenwick; llegadas lazy y first-passage heaps preparados para fase posterior. Equivalencia demostrada con fixtures inventados, no speedup de mercado medido.

Prioridad propuesta tras recibir perfil V2:
1. Medir serialización/captura/commit/creación de índice por separado: actualmente su costo queda mezclado con detectores o wall sin asignar. No confundir timings mezclados con CPU puro del indicador.
2. Si almacenamiento domina, evaluar columnas tipadas/batches privados conservando hash lógico ordenado y todos los records/props/reasons. Comparar contra baseline idéntico dentro de Kaggle.
3. Si BT2A domina, compartir primitivas de TapeWindow idénticas entre configs; no compartir thresholds/estado activo diferentes ni cambiar cierre residual.
4. Si racimos dominan, perfilar snapshots/membresías además de la búsqueda ya optimizada; no eliminar miembros para acelerar.
5. Sólo después diseñar checkpoint privado reutilizable para evitar formación repetida. No afirmar que ya existe ni extraer datos de mercado.

Elegir una mejora por cuello medido; benchmark finito sobre mismas entradas y ordered-output parity, incluyendo cold/warm y memoria. No modificar kernel activo. No prometer GPU, aceleración global o campaña cartesiana ilimitada.


## Actualización V2 terminal

V2 ERROR después de target reportada completa y tríadas 0/1. Capturas acumuladas 6296969; no censo final ni perfil por etapa/per-config disponible. UNCLASSIFIED_ENGINE_ERROR sigue sin causa específica. El supervisor preservó/revisó el cierre agregado, sin custodia autenticada o inferencia de edge. Ver CONFLUENCE_TERMINAL_ACQUISITION.md y MNQ_CONFLUENCE_V2_SUPERVISOR_CLOSEOUT.json. Se preparó perfil nested y checkpoints agregados parciales para no perder trabajo útil tras un fallo. Candidato clustered conserva paridad sintética, pero no se adoptó.
