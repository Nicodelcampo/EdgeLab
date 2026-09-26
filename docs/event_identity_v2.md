# EventIdentity v2 — contrato de identidad y procedencia de captura

> Estado: **implementado en Python; probe NT8 pendiente de compilación y medición real**.
> Este contrato no certifica semánticas del feed que NT8 no exponga.

## 1. Problema que resuelve

El schema F2 v1 conserva `ts_utc_ns` y un `sequence` que es el orden de fila del
archivo. Eso es suficiente para reproducir el archivo, pero no para contestar:

- si dos filas idénticas son duplicados o dos trades reales;
- si una pérdida ocurrió antes de NT8;
- si el orden proviene del exchange, proveedor, callback o escritor;
- cuánto del timestamp pertenece a la fuente y cuánto a la máquina de captura;
- si el agresor vino del proveedor o fue reconstruido.

La respuesta anterior implícita —usar timestamp + precio + volumen como
identidad— es inválida: mercados reales pueden producir eventos distintos con la
misma terna, incluso en el mismo timestamp.

## 2. Campos obligatorios

| campo | semántica |
|---|---|
| `capture_id` | identifica una ejecución de captura; no se reutiliza |
| `process_instance_id` | instancia concreta de NT8/proceso |
| `instrument`, `contract` | identidad del mercado observado |
| `event_kind` | tipo de callback/evento |
| `callback_seq` | contador local asignado al entrar al callback |
| `capture_seq` | contador local asignado al persistir la fila |
| `capture_utc_ns` | reloj UTC de la máquina capturadora |
| `monotonic_ns` | reloj monotónico local |
| `timestamp_provenance` | procedencia declarada del tiempo fuente |
| `quote_provenance` | procedencia declarada de bid/ask |
| `aggressor`, `aggressor_provenance` | valor y método que lo produjo |

`source_time_ns` puede ser nulo porque no todos los callbacks garantizan un
timestamp de fuente. Ausencia declarada es preferible a fabricar precisión.

## 3. Tres órdenes que no se pueden confundir

1. **Orden upstream:** exchange o proveedor. Sólo existe si el feed entrega una
   secuencia externa y su contrato define el alcance.
2. **Orden de callback:** `callback_seq`. Prueba el orden observado por esta
   instancia de NT8; no detecta pérdidas previas.
3. **Orden de persistencia:** `capture_seq`. Prueba que el escritor no omitió ni
   duplicó filas después del callback.

Una captura sin `source_sequence` puede auditar su proceso local, pero su estado
respecto de pérdidas upstream es **NO OBSERVABLE**, no PASS.

## 4. Identidad

`event_id = sha256(JSON_canónico(todos_los_campos))`.

La unicidad operacional descansa en `(capture_id, capture_seq)`. El contenido
entra al digest para hacer detectable cualquier alteración. Dos callbacks con
igual tiempo, precio, volumen y quotes tienen IDs distintos si su secuencia local
es distinta. **No se deduplican.**

## 5. Precisión temporal

La captura conserva nanosegundos como unidad canónica aun cuando la fuente tenga
menor resolución. Reducir a `unix_ms` para matching o identidad puede colapsar
eventos distintos. El auditor cuenta esos alias explícitamente.

Conservar más dígitos que la resolución real no crea precisión: la resolución
efectiva se mide y se declara por separado.

## 6. Agresor

Valores permitidos: `buy`, `sell`, `unclassified`, `unknown`.

Procedencias permitidas:

- `native_provider`
- `quote_rule`
- `tick_rule`
- `first_tick_default`
- `not_applicable`
- `unknown`

`native_provider` sólo se usa si el proveedor entrega el dato y su semántica fue
documentada. La regla quote/tick de BigTrap2 sigue siendo reproducible, pero pasa
a estar etiquetada como **inferencia**, no verdad nativa.

## 7. Gates iniciales

Una captura v2 falla si:

- mezcla más de un `capture_id`;
- `capture_seq` no empieza en cero o no es contiguo;
- `callback_seq` no es estrictamente creciente;
- retrocede el reloj monotónico;
- retrocede `capture_utc_ns`;
- aparece una secuencia externa sin declarar su alcance;
- bid supera ask.

Timestamps fuente repetidos no son fallo: se cuentan. Alias producidos al truncar
a milisegundos tampoco se corrigen: se reportan como pérdida semántica potencial.

## 8. Migración

- F2 v1 permanece inmutable.
- F2 v2 será una construcción nueva desde capturas nuevas.
- No se rellenarán campos v2 inventando datos desde archivos v1.
- Un archivo v1 puede envolverse como evidencia legacy, pero los campos no
  observables quedarán `None`/`unknown`.
- Ningún resultado histórico gana retrospectivamente certificación v2.

## 9. Próxima prueba con NT8

El probe será un indicador diagnóstico separado. Debe registrar cada callback
sin deduplicar, usar archivo exclusivo por ejecución y emitir metadatos de chart,
conexión, modo Historical/Playback/live, timezone, instrumento y contrato.

La primera captura real medirá antes de decidir:

1. resolución efectiva de `MarketDataEventArgs.Time`;
2. relación entre tiempo de fuente, UTC de captura y reloj monotónico;
3. frecuencia de timestamps repetidos;
4. orden de callbacks entre Last/Bid/Ask;
5. disponibilidad real de bid/ask y agresor por modo;
6. qué secuencia externa, si alguna, expone la conexión usada.
