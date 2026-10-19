# AVZVOL: medir desde la confirmación, sin inventar resultados

## Avance concreto

A la clasificación de continuación y ruptura fallida se añade un **módulo de medición no económica**, probado sólo con caminos inventados. [Código](../../edgelab/kaggle/avzvol_reaction_response.py), [pruebas](../../tests/test_avzvol_reaction_response.py), [demo](../../tools/avzvol_response_smoke.py).

No es un resultado de mercado ni un backtest. No se abrieron datos de mercado, no se eligieron filtros por sus efectos, no se calcularon P&L/fills ni se habilitó el holdout. Los parámetros científicos existentes siguen pendientes. Este avance implementa el cálculo y su tratamiento de faltantes; no demuestra qué entrada conviene operar.

## Qué produce para cada confirmación

- Origen: **cierre de la barra de decisión observada**, disponible en su instante de publicación; nunca el borde, el ancla ni el extremo anterior al disparo.
- Respuesta firmada por el lado de salida observado, en ticks y dividida por un normalizador explícito. No se cambia el signo después de ver el recorrido. La rama de ruptura fallida conserva la misma orientación de medición: no se la transforma automáticamente en un supuesto trade ganador.
- Excursión hacia cada lado desde ese cierre, **solamente en las barras completas posteriores y disponibles**. Se conserva como medida del prefijo observado, no como máximo de un recorrido continuo de ticks.
- Primera observación de distancia bajo una política explícita: lado de salida, lado contrario o **ambos dentro de una misma barra, con orden desconocido**. No es tasa de acierto ni una simulación de stop/target.
- Estado de cada horizonte: ventana completa, censura por final de datos, frontera de sesión, historia desconocida, barra parcial posterior al disparo o ausencia de nueva barra completa.

Distancias, normalizador y horizontes son inputs obligatorios, sin defaults de mercado. Los números diminutos de las pruebas son inventados y no proponen una calibración. Si se usa altura de banda, debe congelarse previamente su definición y unidad; no se adopta silenciosamente la altura histórica O3.

## Convención temporal explícita

Los horizontes son de **reloj**, no cantidades de barras. El deadline parte de la disponibilidad de la decisión. La respuesta usa el último cierre completo disponible al deadline y publica su antigüedad real. Es una observación escalonada de cierres, **no el precio exacto a ese segundo**.

Una barra que aún no terminó/publicó al deadline no aporta su high/low ni su cierre. Si el deadline cae dentro de ella, no se inventan observaciones intrabar. Un `NO_COMPLETED_BAR_HIT_OBSERVED` sólo afirma que no hubo ese hit en las barras completas usadas; no prueba ausencia de hit en un recorrido de ticks o una barra todavía abierta.

Una barra que contiene datos previos a la disponibilidad del disparo no se usa para inflar excursiones: se conserva como `UNKNOWN_PARTIAL_POSTDECISION_BAR`. La API exige inicio y final con orden de fuente y watermark de observación explícitos; estos metadatos inventados no certifican una fuente real.

Si la ventana está incompleta, la respuesta del horizonte es **null, no cero**. El prefijo observable y cualquier observación de distancia ya ocurrida se conservan aparte. La ausencia de datos no se convierte en pérdida, éxito o no-hit.

## Qué permitirá decidir, cuando sea ejecutable con datos reales

Aplicar la misma convención a las dos ramas y a sus propios controles comparables sin zona:

1. Contrastar las distribuciones desde el disparo, no sólo una media o una tasa.
2. Comparar cobertura del censo inicial y censura por rama; reportar falta de soporte, sin seleccionar sólo casos resueltos.
3. Separar discriminación del patrón de precio de información incremental de zona.
4. Mantener contrato/sesión/dependencia y reutilización de controles en la inferencia congelada. Una comparación condicional no demuestra causalidad.

Si el patrón funciona igual sin zona, priorizar el patrón. Si zona añade información material y estable bajo el protocolo, investigarla como contexto. Si no hay precisión/soporte suficiente, no promover entradas ni buscar un ganador mediante filtros posteriores.

El módulo **no implementa todavía** censo as-of, certificación de controles, replay de detector, matching, inferencia estadística ni extracción de nuevas respuestas de mercado. No elimina esos requisitos por pasar pruebas de software.

## Ejecución técnica

```bash
python tools/avzvol_response_smoke.py
python tools/avzvol_response_smoke.py --purpose research
```

Demo sintética en el primer comando; STOP sin abrir inputs en el segundo. La API también rechaza propósito no sintético. No hay loader de mercado.

Referencias: [comparación de reacciones](AVZVOL_COMPARACION_REACCIONES_20261011.md), [hipótesis originales](AVZVOL_LOGICAS_DE_ENTRADA_20261011.md), [requisitos pendientes](../../specs/research/avzvol_incremental_design_v1.json).

Validación local: **28 pruebas específicas**, suite **813 + 25 subtests** y **18 pruebas de navegación**. [Ejemplos inventados y evidencia técnica](avzvol_reaction_response_20261011/synthetic-evidence.json). No son tamaños de muestra de mercado.
