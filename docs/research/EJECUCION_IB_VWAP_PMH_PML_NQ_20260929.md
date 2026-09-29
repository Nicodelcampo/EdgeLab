# IB→VWAP y PMH/PML — ejecución autorizada, 2026-09-29

Nico: «Retoma y correas». Se ejecutan las dos reglas del manifiesto `MANIFIESTO_IB_VWAP_Y_PMH_PML_NQ_20260929.md`, sin filtros L2 ni optimización. Entorno sandbox, no Kaggle kernel; el conector permite descargar el dataset privado v1.

HEAD de lectura: `3fc19fc9479742faa7520ca00b98d43b4d592db1`. Se registran runner, fixtures, hashes y cobertura antes de abrir outcomes.

## Precisiones operativas previas a resultados

- Datos: ticks canónicos NQ 09-26/12-26, catálogo v1. Contrato fijado por el catálogo, nunca elegido por resultado. No concatenar contratos para llenar huecos.
- Sólo sesiones listadas en el catálogo. Una sesión RTH debe tener ticks en las 78 barras de 5 minutos 09:30–16:00 ET. PMH/PML exige además las 66 barras de 04:00–09:30. Esta evidencia de presencia no certifica completitud absoluta; se publica máximo gap.
- Barras izquierda cerrada/derecha abierta. El cierre 10:30 pertenece al IB, no a un breakout posterior; la primera barra post-IB cierra 10:35. Primer breakout fija dirección IB; el retroceso debe ocurrir en una barra posterior. Toque VWAP: low ≤ VWAP al cierre ≤ high; cierre del lado de la ruptura y fuera del IB.
- VWAP usa todos los ticks de RTH anteriores al cierre, ponderados por volumen; no promedio de barras.
- Sweep PM se observa desde 09:45. Dos cierres de barras consecutivas, con el primero posterior al sweep. Stop = extremo desde el primer sweep de ese lado hasta el cierre de confirmación, más 1 tick adverso. Ambos lados confirmados en la misma barra → sesión sin operación. Objetivo ya cruzado en el tick de entrada o stop del lado incorrecto → señal no ejecutable, contada; no buscar un segundo trade de rescate.
- Entrada = precio negociado del primer tick con timestamp **estrictamente posterior** al cierre confirmatorio. Es proxy de ejecución market del manifiesto, no prueba de fill al ask/bid. Coste primario fijo = 2 ticks totales descontados al resultado, sin comisión; no sumar spread también.
- Stop: primera operación que cruza el nivel, precio de ese tick (incluye salto adverso). TP: precio objetivo teórico; para punto medio PM se redondea hacia el objetivo al tick válido (ceil largo / floor corto, como precisión operativa máxima 0,5 tick). No afirmar fills de límite/cola reales.
- Exit temporal: primer tick ≥15:55; TP/SL sólo en ticks anteriores. No abrir entrada ≥15:55. Reset total por sesión.
- Dos medias R por operación, bootstrap **común de sesiones completas**, B=10000, seed=20260929; máximo del |t| bootstrap centrado, IC95 simultáneo. Se publica n y falta de potencia (<30 operaciones o <20 sesiones). Celdas sin potencia no se promueven aunque el punto/IC aparente sea positivo.
- Comisión de equilibrio = media de P&L después de 2 ticks × USD5/tick por contrato; si negativa, no existe comisión no negativa que conserve esperanza positiva.

## Exclusiones y límites

El preflight enumera catálogo y filas, cobertura por estrategia, fecha/contrato, causas y hashes antes del run. Duplicados de timestamp se ordenan por `sequence` de fuente; no se deduplican trades. Inversiones de reloj/sequence abortan. `ts_utc_ns` es la autoridad; no usar `ts_local_ns`.

Octubre y cualquier reserva distinta de Q3 desarrollo quedan fuera. No modifica NQ-CRUCE25-CLIMA ni utiliza sus resultados.