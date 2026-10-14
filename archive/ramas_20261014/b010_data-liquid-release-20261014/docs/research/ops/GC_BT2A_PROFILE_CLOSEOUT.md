# Perfil BT2A: percentiles como próximo candidato, no cache más grande

Job técnico `138566248/v1`, `edgelab-gc-bt2a-multisession-profile-v1`, COMPLETE. Source commit `7fbbe4e80f2531ed0f9986a2528b731de327006b`; plan `269f62b9991e6c9985a23fe8b1d62a9e7cf936f5c495971868a17b1f7ca29596`. Una intención cerrada, dos polls, sin reenvíos. Sin etiquetas, modelos, P&L, exportación privada, holdout o escritura canónica. Wrapper ya informa outcomes_requested/computed=false correctamente.

## Medición nueva
470.027 ticks GC de4 sesiones consecutivas,3–6 de agosto. Tres configuraciones BT2Absorption originales; historial, zonas y residuos persisten entre sesiones. Modo diagnóstico de producciónfalse. ABBA no instrumentado y un pase cProfile separado, excluido de aceleración.

- Medianas nativas push+finish: secuencial19,82145s vs intercalado19,58172s, **1,01224×** (~1,21% menor duración). Los tiempos individuales se superponen; no demuestra aceleración estable ni pipeline más rápido.
- Fingerprints de **todos los valores de estado semántico no callable del cierre nativo**, buffer pendiente, relojes, secuencia de barras y prefijo coinciden tras cada sesión y enEOF. También capturas, conteos, tamaños y logs. Código callable fuente-pinned, no serializado. Mayor evidencia que comparar sólo tamaños; no certifica NT8 ni todo escenario posible.
- Host119,96s incluye todos los pases, descarga y profiling; RSS muestreado~181MiB. No usar ese total como duración de una corrida científica.

## Cuello de botella
Pase instrumentado28,39252s. Tiempo propio: ordenamientos6,29986s, cuerpo nativo de cubeta6,17078s, preparar footprint/cache5,66201s. Juntos63,86% del pase. El resto incluye otros costos e instrumentación. El perfil exporta sólo18 funciones estáticas permitidas, sin paths ni datos.

`_percentile`:46.409 llamadas, tiempo **acumulado6,61472s (~23,30%)**. Los tiempos acumulados se solapan: NO sumarlos con sorted o flush. `sorted` también ordena niveles de zonas; no atribuir sus6,30s íntegros a percentiles. La cache y la vida de zonas no son una explicación única del costo.

## Candidato de optimización preparado
`rolling_native_percentile.py`: deque cronológica +lista ordenada por inserción estable. Misma interpolación nativa; elimina el valor más antiguo entre empates y conserva orden de ceros con signo. Tests comparan representación hex de floats frente a `_percentile` nativo, varias ventanas, percentiles, duplicados y evicciones. Valores no finitos fallan; no se propone transformar scores ni acortar lookback.

**No está conectado a BT2AStream ni desplegado.** Dos tests candidatos PASS; todavía no hay aceleración real medida de este cambio ni equivalencia del detector con ese algoritmo. Próximo paso: hook AST fuente-pinned de actualización de ventana; verificar estado/capturas/umbrales multis sesión completos y medir ABBA en job con plan/budget nuevo. No usar budget ya consumido ni modificar este kernel.

## Frente científico
`NEXT_MECHANISM_AFTER_GC_NEGATIVE.md` conserva el negativo GC y propone transiciones A→E/E→A, con historia continua equivalente y densidad como comparador obligatorio antes de volver a interacciones espaciales. El diseño reutiliza fuentes/papers ya revisados; no declara nueva lectura íntegra del corpus.

`phenomena_transitions.py` es prototipo causal puro: duración hasta el presente, transición ya observada, expiración120s, ruptura porUNKNOWN/gap/sesión y orden(timestamp,sequence). Tres tests PASS de prefijo, same-ns, reset, expiración y rewind. Primer fixture usó ns0 rechazado por Clock y se corrigió; no hubo error de mercado ni rerun remoto. Es sólo ingeniería: faltan base con historia retardada equivalente, controles de capacidad, margen práctico y congelación del protocolo científico. **No se lanzó nueva corrida de resultados de mercado ni se rescató la pista anterior.**

Pruebas nuevas:3 perfil +3 transiciones +2 percentil PASS. No se presenta la regresión anterior922 como cobertura de estos cambios posteriores. Productores y canonicalBrainwriter siguen desconectados; sin autonomía/24x7 o deployment Debian. Se exportaron sólo agregados y hashes de estado.
