# AVZVOL: continuación confirmada frente a ruptura fallida

## Qué se hizo, sin volver a auditar datos

Se implementó un **clasificador causal de observaciones**, con pruebas inventadas: [módulo](../../edgelab/kaggle/avzvol_reactions.py), [pruebas](../../tests/test_avzvol_reactions.py) y [demo ejecutable](../../tools/avzvol_reaction_smoke.py). Distingue continuación tras retest de ruptura fallida tras retest y aplica exactamente la misma lógica a candidatos de zona y candidatos geométricos de control.

**Es código probado, no un backtest ni una ventaja de entrada demostrada.** No se ejecutó sobre mercado, no se reconstruyeron nuevas zonas, no se leyó ningún precio de mercado ni se calcularon respuestas futuras. Los controles del prototipo no adquieren certificación por pasar por el mismo código.

## La comparación concreta

| Etapa observada | Rama A: continuación | Rama B: ruptura fallida |
|---|---|---|
| Antes de salir | Banda congelada conocida y al menos un cierre observado dentro | Igual |
| Salida | Primer cierre observado fuera; allí se conoce el lado de salida | Igual |
| Retest | Una barra posterior intersecta el borde de salida | Igual |
| Confirmación propuesta | Cierre de una barra aún posterior afuera, del mismo lado | Cierre de una barra aún posterior dentro |
| Interpretación | Candidato a estudiar continuidad | Candidato a estudiar reversión/reentrada |

**No se llama salida a un precio que ya estaba afuera al empezar la observación.** Debe existir primero un cierre dentro conocido. El lado no se toma de una etiqueta futura.

La barra de salida no confirma su propio retest. La versión propuesta espera una barra posterior al retest. Es una política conservadora explícita del prototipo, no una regla científica aprobada ni prueba de que descartar la reacción inmediata sea óptimo. **El cierre de la propia barra del retest sí es observable cuando termina esa barra**; no se debe afirmar que siempre exige ticks para confirmarse. OHLC no reconstruye todos los cruces intrabar ni la trayectoria de una ejecución. Una variante que confirme al cierre de la barra del retest debe definir esa convención y su orden disponible de antemano; ticks serían necesarios para reglas intrabar o para resolver recorridos ambiguos, no por defecto para cualquier cierre.

Un cierre en el lado contrario fuera de la banda se conserva como estado separado, no como continuación ni reversión confirmada dentro. Los cierres exactamente sobre el borde tienen tratamiento explícito configurable. También son explícitos el buffer, los cierres consecutivos y la espera máxima en barras; los valores inventados de los tests **no son recomendaciones ni parámetros de mercado**.

## Qué medir para obtener una decisión útil

La próxima prueba de mercado debe responder dos preguntas, sin optimizar filtros por los efectos:

1. **¿El cierre posterior al retest distingue la respuesta futura?** Contrastar ambas ramas con el benchmark de retest sin confirmación, dejando claro que el benchmark decide antes. No atribuir a la confirmación movimientos que ocurrieron mientras se esperaba.
2. **¿La zona agrega información?** Comparar cada rama con la misma secuencia geométrica en un censo propio de controles sin zona, no con pseudos heredados elegidos después de ver zonas reales.

Para las ramas confirmadas, el origen de medición sería su cierre de decisión observable, no el borde ni el ancla antigua. Reportar respuesta orientada por el lado observado de salida, en ticks y anchura congelada de banda, y frecuencia de llegada a cada lado bajo horizontes explícitos. Distancias y horizontes siguen por fijar antes de ejecutar; no se trasladan las barreras O3 históricas como si fueran precios de entrada.

Los contrastes usan poblaciones de disparo distintas: una comparación condicional por reacción **no prueba un efecto causal de las zonas**. Deben acompañarla cobertura del censo inicial, casos sin salida, sin retest, sin confirmación, cruce al lado opuesto, espera vencida, historia incompleta y frontera de sesión. El tiempo de espera y los datos faltantes no se convierten en pérdidas ni se omiten para mejorar una tasa.

Controles: mismo contrato, sesión/regla temporal, geometría y contexto comparable conocidos en el instante relevante. La clasificación negativa debe ser as-of. No usar el racimo final ni convertir la ausencia de detección en prueba de ausencia de zona. Congelar selección, soporte, balance, endpoints, censura e inferencia conjunta, manteniendo dependencia por sesión y reutilización de controles.

## Regla de decisión, no búsqueda de un ganador

- Si una confirmación discrimina también sin zona, investigar **el patrón de precio**; no adjudicar la información a AVZVOL.
- Si agregar zona mejora de forma estable el patrón comparable, investigar **zona como contexto**, todavía sin afirmar rentabilidad.
- Si ambos se parecen o la diferencia es imprecisa, no promover una entrada ni rescatarla con filtros posteriores.
- Si hay poca cobertura o muchos casos desconocidos, el resultado es insuficiente; se conserva la falta de evidencia.

La materialidad y precisión mínimas no se fijan mirando el resultado. No se implementaron órdenes, fills, costes, stop/target ni P&L.

## Uso técnico y límites

```bash
python tools/avzvol_reaction_smoke.py
python tools/avzvol_reaction_smoke.py --purpose research
```

El primer comando usa sólo tres caminos inventados. El segundo devuelve STOP antes de abrir entradas. La API del clasificador también rechaza `purpose` distinto de synthetic. Esto es protección de alcance, no un sustituto de evidencia independiente.

El clasificador conserva identidad de snapshot/política, instante de disponibilidad y orden de fuente. Un snapshot tardío no se retroaplica. Historia incompleta o cambio de sesión terminan como UNKNOWN. Tras un disparo, anexar barras futuras no modifica la decisión del prefijo.

Los parámetros científicos y permisos existentes siguen sin modificación: P1 parcial, P2/P3 pendientes y P4 económico fuera de alcance. La instrucción de avanzar concreta el prototipo y el diseño; no certifica los requisitos previos para nuevos efectos de mercado.

Referencias: [hipótesis y resultados ya disponibles](AVZVOL_LOGICAS_DE_ENTRADA_20261011.md), [campos de captura necesarios](AVZVOL_CONFIRMACION_OBSERVABILIDAD_20261011.md), [requisitos de captura](../../config/research/avzvol_interaction_capture_v1.json).

Validación local: **24 pruebas del clasificador**, suite **785 + 25 subtests** y **18 pruebas de navegación**. [Casos sintéticos y alcance](avzvol_reaction_comparison_20261011/synthetic-evidence.json). Estos conteos no son observaciones de mercado.
