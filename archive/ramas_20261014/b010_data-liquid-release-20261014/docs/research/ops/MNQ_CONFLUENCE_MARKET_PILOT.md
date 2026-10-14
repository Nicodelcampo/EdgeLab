# Piloto real MNQ: densidad y geometría antes del cartesiano grande

## Alcance fijado antes de la corrida

96 configuraciones completas del roster (32 AVZP2, 32 BT2, 32 BT2A), cuatro racimos del mismo roster, y 32 triadas alineadas por índice. No son 32³ combinaciones ni las 24 familias de escenarios futuras. No elegir parámetros por densidad ganadora u outcomes; la selección existente es sólo paramétrica.

Fuente aprobada MNQ_09-26 reexport v2. Target: 2026-06-16, primera sesión ya seleccionada del universo exploratorio histórico, no una muestra virgen. Warmup: las observaciones existentes desde el inicio de la ventana histórica de 45 días (2026-05-02 05:00 UTC) hasta el target. Conservar íntegros parámetros/lookback/min_samples; historia insuficiente sigue sin señal, no se reduce el warmup para fabricar soporte. Fuente y riesgos previos reutilizados, sin otro footer probe, QA ni auditoría de matrices/focales.

El target termina a 17h Chicago/22h UTC del 16 de junio. Formación observada puede ser fragmentaria según fuente histórica; no se certifica una sesión completa ni calendario/liquidez. El corte de presupuesto no se presenta como censo exitoso: abortar, no devolver un prefijo silencioso. Archivo físico y datos derivados permanecen dentro de Kaggle, fuera de notebook outputs.

## Qué responde este piloto

- Cuántos nacimientos/lifecycle produce cada config dentro del target y cuánto cuesta cada etapa.
- Qué pares y triples se reconocen causalmente entre configs alineadas, incluidos racimos; carry intersesión queda separado/excluido del brazo primario.
- Si las implementaciones estatales y el almacenamiento por lotes tienen costo/memoria viable para expandir el experimento.

No responde todavía si hay ventaja predictiva: no analiza P&L, barreras/labels, precio de llegada, visitas/revisitas, nulls de ocupación, controles densidad/geometría, inferencia, estabilidad entre contratos o multiplicidad. Los conteos de coincidencias son oportunidades geométricas, no edge ni muestras independientes. Geometría se evalúa en clocks de mutación reales, sin inventar ticks o arrivals para acelerar.

## Arquitectura y equivalencia

`kaggle_session_reader.py` filtra la ventana fijada, usa batches Arrow de 100000 y materializa como máximo una sesión natural para construir OHLC exacto. No carga 110M filas juntas, no ordena ni imputa. Los row groups se eligen por rango antes de payload; el último grupo puede incluir filas preholdout adyacentes, que se filtran antes de detectores. Un grupo que alcance holdout se rechaza antes de payload; esta fuente fijada termina antes de él.

`session_primitives.py` comparte clasificación agresora una vez por sesión y ambas primitivas una vez por bar spec entre todas las configuraciones. Preserva tickrule global, reinicio de conteo nativo por sesión, disponibilidad con lookahead real y **carry de los miembros del timestamp final asignados al siguiente bar por TOTAL NT8**. No sustituye TOTAL por aggressive ni elimina ese carry. El ensamblaje entero de una sesión es la unidad acotada de memoria; no se afirma streaming tick-a-tick de todos los builders.

El origen absoluto consumido y la disponibilidad permanecen separados. SQLite guarda receipts privados con índice por config/clock y hashes ordenados. Un heap une tres streams por triada, y `geometry_replay.py` conserva la semántica de scope/racimos del replay de referencia. No hay cubo config×tick ni arrivals falsificados. Las triadas se procesan de a una para no mantener 32 grafos densos en RAM simultáneamente.

El runner completo reproduce hashes/conteos de captura de las 96 configs contra referencia sobre el fixture inventado del piloto; pruebas de primitivas verifican cohortes multi-close, residuales/carry y tickrule entre sesiones. No equivalen a paridad NT8 100% del mercado ni son una nueva auditoría de dataset.

## Límites y transporte

8M ticks en ventana total, 5M por sesión, 3M captures privadas, 1.5 GiB de SQLite; guards por etapa. AS child 6 GiB, parada RSS 4 GiB, CPU 6300 s, deadline cooperativa 5400 s, watcher 6600 s, timeout notebook solicitado 7200 s. Protege el grupo del único child conocido, no cgroup ni procesos arbitrarios.

El bootstrap sólo descarga el archivo exacto a tmp privado y comprueba su pin **durante transferencia**, no repite QA/lectura de footer. Internet del notebook se habilita por ese transporte; el runner no realiza llamadas de red. URL firmada sólo en notebook privado, expira 72h; nunca en repo o receipts. Outputs: boot/pilot receipts agregados y progreso sanitizado. Ticks, SQLite y log privado quedan fuera del directorio outputs.

## Después del piloto

Interpretar soporte real junto con costo/ocupación, no premiar configs por más zones. Optimizar subpasos costosos medidos con equivalencia por entradas idénticas. Incorporar las preguntas científicas ya diseñadas (M3 vs M2, interacción incremental/orden/llegada/flow, controles de densidad y oportunidad, carry, dependencia/multiplicidad/estabilidad) al protocolo de outcomes antes del estudio grande. No escribir al EdgeBrain canónico ni promover candidatos automáticamente.
