# Confluencias MNQ: continuar con paridad aproximada aceptada

## Decisión del usuario y alcance

Nico indicó avanzar considerando que la paridad no será 100% pero estará muy cerca por el trabajo realizado. Esa estimación queda **aceptada para EXPLORACIÓN**, sin convertirla en un porcentaje medido, PASS nuevo o evidencia de edge. No se requiere otra auditoría exhaustiva NT8 para avanzar. Sí se mantienen identidad de implementación, causalidad, trazabilidad y comparación exacta del código optimizado contra su referencia.

No implica acceso al holdout desde 2026-10-01, otras particiones previamente reservadas, P&L, merge, autopromoción ni aprobación independiente. La preparación continúa sin esperar supervisor 24×7/writer/claves de producción. Los ticks y eventos privados permanecen en Kaggle.

## Implementado ahora (sólo pruebas inventadas)

### 1. Intersecciones as-of

`tools/research_ops/confluence/asof_intersections.py`:
- Snapshots inmutables, identidad de familia/config/build/zona y reloj `(ns, sequence)`; precios enteros en medios ticks.
- Índice de intervalos aumentado por familia (treap determinista). Busca candidatos que se intersectan, no cada par de todas las zonas activas. Balance esperado, no garantía adversarial O(log N).
- Lotes atómicos: aplicar removals/upserts y observar sólo el estado final del lote. No confluencias transitorias por orden de evaluación de indicadores.
- Intersección parcial, contención, contacto de bordes, geometría idéntica y orientación. No multiplicar zonas de la misma familia como «dos indicadores independientes».
- Revisiones ordenadas, reconocimiento no retroactivo, IDs inactivos que no resucitan. No reemitir cada coincidencia en cada tick sin cambio.
- Límites de activos, IDs históricos y pares; desbordamiento rechaza, no trunca. Error durante mutación envenena la instancia: reconstruir desde checkpoint verificado antes de reutilizar.

**Límites:** un scope de contrato/tape/sesión declarado por instancia. Los adapters deben verificar que cada input pertenece a ese scope; el módulo no demuestra la verdad de las declaraciones. No tiene loaders, quotes, anchors de llegada, triples, persistencia de episodios de coincidencia ni eventos de fin de par; no es el runner científico completo. La guardia de fecha tampoco certifica el calendario/split completo.

### 2. Racimos causales, sin modificar su regla

`tools/research_ops/confluence/racimo_asof.py`:
- `_racimo` copiado literalmente de aVolZonePOI2 en foundation `f397a318be8b0acf68789070fe8064d83e172f7d`; SHA256 de la función UTF-8 con newline final: `846aab2ee62074f91de17a64bf8b7ade3efbb5a842cf8ba36a9677ede6a33efe`.
- Emitir reconocimiento cuando el racimo se forma, no al nacimiento de su primer miembro; expansiones y cambios de miembros producen snapshots nuevos en el momento observable.
- Preservar orden original de zonas dentro de cada barra y coalescer observación final del lote. No ordenar nacimientos por precio porque cambia desempates del algoritmo.
- Indexar asignaciones de miembros y revisar sólo racimos tocados, sin reescanear todas las zonas/clusters después de cada lote. La regla detectora conserva su búsqueda original; emitir membresía completa sigue costando O(número de miembros).
- Preservar el carry legacy y etiquetar `spans_sessions`; el brazo primario excluye formaciones entre sesiones explícitamente. No rebautizar un detector modificado como equivalente.
- Bounded history: si se alcanza el límite, detenerse; no borrar estado viejo que podría afectar la geometría. El almacenamiento/checkpoint eficiente integral aún falta.

### 3. Piloto reproducible preparado, NO lanzado

`tools/research_ops/confluence/build_target_free_pilot.py` y `MNQ_CONFLUENCE_TARGET_FREE_PILOT_ROSTER.json`:
- 96 configuraciones completas: 32 AVZP2, 32 BigTrap2, 32 BigTrap2Absorption; referencias y probes densos incluidos.
- Cuatro variantes racimo para el piloto, separadas de la detección AVZ. Selección determinista por parámetros/semillas, sin consultar mercado, densidad observada o outcomes.
- Cobertura de todos los valores marginales del catálogo; **no** cobertura cartesiana de todas sus combinaciones. Densidad de los probes es propuesta, no ya medida.
- Hash por configuración completa y roster; aliases nominales detectados se conservan en metadata y se reemplazan determinísticamente para no duplicar cómputo.
- No reducir warm-up ni habilitar renderer retrospectivo.
- Source manifest, sesiones y presupuesto hardware siguen sin fijar. `launch_ready=false`; no existen nuevos resultados de mercado.

El piloto mide únicamente preparación/detección/racimos/intersecciones/cobertura/costo y escritura, sin etiquetas/outcomes. El roster es preparación, no permisos ni runner Kaggle ya conectado.

## Pruebas observadas y fallos corregidos

**43 pruebas específicas nuevas**, **555 Research Ops totales**, **18 navegación**, catálogo PASS.
- Intersecciones comparadas contra búsqueda exhaustiva independiente sobre 250 lotes sintéticos con altas/bajas/revisiones, más casos de ns compartido, medios ticks, bordes, límites y prefijos.
- Racimos incrementales comparados contra un adapter de recorrido completo, sobre dos sets de parámetros y 180 lotes cada uno. Ambos usan la misma regla legacy fijada: comprueban observación/registro incremental, NO constituyen paridad independiente contra NT8.
- Integración: no aparece confluencia de racimo antes de reconocimiento; invalidación simultánea no produce par transitorio; carry no se declara session-only.

Fallos de desarrollo conservados como aprendizaje:
1. El primer roster tenía aliases nominales repetidos y el test lo rechazó; se añadió deduplicación de cómputo con registro de aliases y reemplazo puro por parámetros.
2. Una primera optimización capturaba el clock antiguo de un miembro mediante closure. El test de tercer nacimiento detectó reconocimiento retrofechado. Se sustituyó por un callback de instancia que usa el clock del lote actual; el test y la referencia completa pasan.

No se abrió mercado ni outcomes durante esos fallos. No se afirma speedup real, paridad NT8 nueva, memoria pico en Kaggle o inferencia calibrada a partir de tests sintéticos.

## Próximo paso operativo (no otra auditoría de paridad)

1. Conectar creación/lifecycle observables de los tres detectores al stream de snapshots; no consumir sus objetos finales mutados ni el PIT v1 invalidado.
2. Bindear fuentes preholdout elegibles, contratos naturales, historia de formación/warmup y sesiones aprobadas. Declarar todos los gaps/splits; no fabricar certificados o usar el catálogo legacy como bypass.
3. Completar eventos triples, anchors de llegada y fin de episodios de confluencia. Las comparaciones de pares implementadas son sólo un subconjunto.
4. Empaquetar runner privado Kaggle, verificar mounts/builds y límites reales; ejecutar piloto target-free acotado con receipts agregados, sin sacar eventos/ticks.
5. Con esos costos/soportes fijar roster amplio, predicados, labels, modelos/ablaciones, controles, MDE/dependencia/multiplicidad y budget del estudio científico nuevo. Sin elección de ganadores en datos previamente inspeccionados ni declarar esa división holdout virgen.

**No queda un bloqueo de paridad 100%.** Lo pendiente es conectar y completar el experimento, no terminar infraestructura autónoma o repetir matrices/focales existentes.

## Reproducir sin datos reales

```sh
python -m unittest discover -s tests/research_ops -p 'test_confluence*.py' -v
python -m unittest discover -s tests/research_ops -v
python -m unittest discover -s tests/navigation -v
python tools/edgelab_catalog.py check --json
python tools/research_ops/confluence/build_target_free_pilot.py \
  --design docs/research/ops/MNQ_DENSE_CONFLUENCE_DESIGN.json \
  --out /ruta/nueva/pilot-roster.json
```

El output debe ser nuevo: no sobrescribir evidencia anterior. Los módulos de estas pruebas no consultan red ni datos privados.
