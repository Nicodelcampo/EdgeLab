# ACTIVE_PAIR_BUDGET: corrección de representación, no aumento ciego de cupo

## Causa y cambio acotado

V3 terminó en `EpisodeStream` al exceder50.000pares vivos. Ese motor conserva episodios/vecinos/triples para identidad y continuidad. El piloto actual, sin embargo, sólo consume conteos START/UPDATE/END por firma familiar: descarta objetos de episodios al actualizar counters. Mantener toda la gráfica viva durante la sesión es una representación innecesaria **para ese producto de conteos**, no prueba de que los pares sean científicamente irrelevantes.

No se elimina ningún cruce: se conservan las seis parejas entre familias y las dos clases de triples AVZP2/BT2/BT2A y RACIMO/BT2/BT2A. `geometry_counts.py` conserva snapshots/indexes/tombstones y calcula membresía afectada antes/después de cada mutación atómica. El componente cambiado mínimo es dueño único de cada intersección, evitando duplicados. Busca el tercer miembro en la banda común de los primeros dos, no en todos los pares de vecinos de una misma familia.

START=after−before, END=before−after, UPDATE=intersección(before,after), por identidad completa y cortes causales. No bajar densidad, excluir escenarios, recortar warm-up ni fabricar observaciones independientes. Sigue habiendo cotas por atomic clock, objetos/tombstones, private bytes, CPU/RSS y wall; overflow explícito, sin truncación.

## Alcance de paridad

Tests sintéticos comparan counters exactos con `EpisodeStream`: todas las familias, nacimientos/removals, geometría que pierde/recupera contacto, revisiones, empate de bordes, batches atómicos, racimos y default antiguo. Ocho seeds ×100batches aleatorios, más fixtures específicos. Un fixture tiene1.600pares vivos y un máximo de40afectados por clock, sin que el candidato retenga esa gráfica.

Benchmark reproducible `benchmarks/geometry_counts.py`: tape inventado de240zonas por dos familias; referencia ampliada a150kpares sólo para completar el oráculo. Candidato con cota50kpares afectados por clock;57.600creaciones lógicas idénticas. Cada variante en subprocess nuevo; un único par de mediciones, no ganancia de Kaggle demostrada. Recibo `GEOMETRY_COUNTS_SYNTHETIC_BENCHMARK.json`.

**No se afirma paridad de IDs/orígenes/revision histories:** el candidato no produce episodios individuales ni sirve directamente como store de arrivals/respuestas. Para un atlas científico que los requiera, mantener el motor con identidad o diseñar partición/spill exactos por separado. Esta corrección es del censo técnico agregado, no una eliminación silenciosa de detalles del estudio.

## Integración

`GeometryReplay(count_only=True)` usa el candidato sin cambiar la lógica upstream de racimos. Default sigue `False`. `market_pilot` permite seleccionar explícitamente `geometry_engine=AFFECTED_COUNTS` en un plan nuevo; default EPISODES para los planes antiguos. Un plan con nombre de engine desconocido falla. La allowlist del paquete incorpora el módulo; diagnóstico cerrado añade site GEOMETRY_COUNTS.

**No se lanzó V4 ni se reinterpretó V3 como completa.** Cambiar el engine exige nuevo source/bundle/plan y prueba acotada antes de una repetición grande. Los registros privados V3 estaban en directorio temporal del kernel: los agregados prueban avance, no acceso posterior garantizado al SQLite. No prometer resume/reuso sin verificar custodia del cache **dentro de Kaggle**. Para futuras corridas separar captura persistida privada de replay; no bajar SQLite al servidor.

## Próximo resultado nuevo independiente

Ahora que V3 es terminal, se prepara una única P0 de fenómenos, sin96detectores/26sesiones de warm-up ni geometría. Usa sólo la sesión2026-06-16 ya seleccionada y mide ventanas5/20/60s. Fuente/pin ya resueltos; ningún QA general nuevo ni búsqueda de edge/P&L. El host recién preparado tiene transporte≤600s, compute≤900s, CPU900s, RSS stop4GiB/address space6GiB, watchdog total1500s y notebook1800s. Features fuera de outputs; sólo boot/measurement receipts agregados.

Intención durable de P0 antes de envío usando `DispatchIntent`, sin auto-retry al perder respuesta. Es una ejecución manual finita en este host, **no integración ni presupuesto global de todos los controladores Debian**. Estado real de lanzamiento se guarda aparte; este documento no declara que ya corrió o terminó.
