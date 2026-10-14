# Rendimiento, unidades de trabajo y reanudación verificable

Estado: **PLANNING_ONLY + SYNTHETIC_CONTEXT_PARITY_ONLY**. No servicio24/7 ni ejecutor exploratorio habilitado. La corrida MNQ activa no se modifica, pausa, relanza ni adopta.

## Avance del sistema

- `work_plan.py`: inventario determinista de las18familias actuales por contrato, sin ampliar o alterar parámetros. Identidad por fuente, selección, código, protocolo, autorización y revisión de riesgos. IDs y fingerprints por familia, plan sellado, verificación por reconstrucción, presupuesto explícito de intentos/segundos y máximo un worker pesado. Cambiar un pin invalida la identidad del checkpoint. Cambiar presupuesto no cambia la definición científica de una familia.
- Todos los fragmentos nacen `PLANNED_UNAUTHORIZED`, no terminados. Una línea `FAMILY` no es checkpoint. Un recibo con fingerprint y digest de output sólo acredita identidad: no acredita contenido, existencia, finalización, adjudicación ni permiso de omitir trabajo. `skip_allowed` y `execution_allowed` permanecen False. Hashes locales no autentican una autoridad ni protegen contra un administrador que reescriba todo.
- `admission.py`: evaluación conservadora de memoria/carga previa a una futura admisión; solicita un pico máximo y headroom, no descuenta automáticamente page-cache. Bloquea la recomendación de otro trabajo pesado cuando hay uno activo. Incluso si hay capacidad, no autoriza ni reserva/lanza nada. El snapshot puede quedar viejo y no es un lease; debe conectarse a un supervisor confiable y reserva atómica antes del payload.
- `context_memo.py`: memo LRU acotado para consultas causales repetidas, con identidad fija e instancia nueva por input/selección/código. Dos caches independientes: rango por barra cerrada y hora por timestamp exacto del trigger. **No usar la barra como clave de hora**: una barra puede cruzar una hora o transición DST. No hay nuevo código generado o acción de cola.

Los readers del memo son funciones del runner confiable, ligadas a datos inmutables. La librería no autentica las funciones ni garantiza su causalidad por sí sola; las pruebas verifican las expresiones existentes, no cualquier callback. No se reutiliza el cache al modificar arrays, cambiar fuente o límites de sesión. Es secuencial, no un cache distribuido/thread-safe. Capacidad por cada cache:1–65.536entradas, default8.192. Contadores de hits/misses y evacuación LRU se mantienen acotados.

## Qué se midió

### Expresiones actuales con inputs sintéticos

`context_benchmark.py` reproduce las expresiones NumPy/Pandas actuales del runner: rango de256barras previas limitado al comienzo de sesión y hora Chicago del timestamp exacto. Inputs enteros/timestamps inventados, no archivos de mercado; no ejecuta scripts de la campaña. Dos workloads de8.192consultas y tres repeticiones por método, con cache fresco y orden alternado. Las repeticiones incluyen construcción del memo y colección de los outputs; importaciones y readers se calientan antes. Registra tiempos individuales, versiones, mediana, identidad de inputs/outputs y hits/misses.

- Paridad exacta de todos los outputs contra las expresiones vigentes.
- Chequeo adicional por slicing Python y datetime/ZoneInfo en seis posiciones predefinidas, incluido inicio de sesión. No se afirma verificación independiente de cada celda por este segundo método.
- Caso repetido:512claves,16consultas consecutivas por clave.
- Caso único:8.192claves sin repetición.

**El cache sólo ayuda si hay reutilización suficiente.** El benchmark demuestra el caso favorable y el contraejemplo: también hay overhead cuando no hay hits. Los tiempos son un microbenchmark sintético en host compartido, no el factor de aceleración de MNQ. La medición no establece la distribución de hits de eventos reales ni el costo de preparar tick tapes, prefix caches, scans, controles o serialización.

Evidencia exacta y todos los tiempos: `CONTEXT_BENCHMARK_EVIDENCE.json`. El CLI opcional requiere NumPy/Pandas ya instalados:

```bash
python -m tools.research_ops.cli benchmark-context-synthetic
python -m unittest discover -s tests/research_ops -v
```

### Perfilado breve de MNQ en curso

Se usó py-spy en entorno separado,12segundos a49Hz, modo no bloqueante sin pausas solicitadas y sin capturar valores de mercado. El SHA del archivo activo coincide con el manifest de la campaña. Se obtuvieron453muestras y134errores de lectura. El muestreo identifica stacks visibles, **no permite repartir con fiabilidad el tiempo total**: ventana breve, lectura no bloqueante potencialmente inconsistente, líneas Python con varias operaciones y sin resolución nativa del interior de NumPy/Numba. No extrapolar porcentajes de este muestreo a toda la campaña ni presentar una línea como una función independiente.

No se cambió el worker, su entorno Python, los datos, pins o parámetros. La herramienta de perfilado se instaló aparte. El monitor de recursos sigue separado y un aviso de memoria alta no prueba una caída.

## Cómo acelerar la campaña completa sin recortar la investigación

### Prioridad1 — reutilización exacta y menos trabajo Python

- Medir hit-rate real por familia/barra/trigger antes de activar el memo. Mantener fallback sin memo si no compensa. Congelar la política operacional antes de medir outcomes; no seleccionar familias por rendimiento económico.
- Reutilizar preparación y matrices/outcomes ya existentes en vez de repetir cargas o recalcular por cada variante. El motor YA utiliza NumPy/Numba y prefix caches; esto no se presenta como implementación nueva.
- Considerar lote compilado de reglas por anchor y compartir detección de trigger entre endpoints compatibles. El pretrigger puede ser común, pero los targets/opposite y censuras requieren comprobación independiente; no asumir que todos los outcomes se comparten. Es candidato, no optimización aplicada.
- Evitar construir grandes prefix caches en casos sin señales aprovechables, sólo si se demuestra que el nuevo orden no usa labels futuros para seleccionar y conserva el censo completo de censuras/ausencias. Cambiar el orden de observación exige revisar equivalencia, no sólo medir velocidad.

### Prioridad2 — salida y checkpoints por fragmento

- Medir costo de dicts/CSV/gzip por señal. Probar batches tipados/columnar, manteniendo schema, orden, nulos/NaN, conteos y trazabilidad de eventos exactamente compatibles con los consumidores. No reemplazar una salida en uso con una incompleta.
- Fragmentos por familia y luego sesión si lo permite la semántica original. Checkpoint durable externo y recibo ligado al input/código/protocolo. Hash y verificación del output antes de omitir un fragmento; no adoptar logs como evidencia.
- Comparar tiempo completo con preparación, JIT, memoria y serialization incluidos; conservar también un kernel-only benchmark para diagnosticar, sin confundirlos.

### Prioridad3 — paralelismo acotado, no a ciegas

- Bajo el límite actual de memoria, no lanzar simultáneamente otras campañas pesadas. Un core ocupado no significa que RAM/disco permitan muchos workers.
- Compartir readonly memmaps/cache de datos y medir buffers privados por tarea antes de aprobar concurrencia. Un supervisor confiable debe mantener admisión y reserva atómicas, parada por presión/timeout y alertas externas.
- Evaluar máquina con más cores/RAM sólo con perfil y benchmark completo. GPU después de paridad y evidencia de que ayuda a estos recorridos; no asumir que scans ramificados/causales se aceleran sólo por disponer de GPU.

## Criterio de aceptación

No instalar candidatos en la corrida actual. Para una versión futura: mismos pins, sesiones/particiones, configuración, decisiones de trigger, targets/opposite, último observado, censuras, rows y features. Tests adversariales y referencia independiente. Si el uso de flotantes cambia orden de acumulación, revisar tolerancia fija y demostrar que no cambia decisiones, no aceptar una tolerancia post-hoc. Registrar todos los intentos fallidos del benchmark y los costos; una mejora técnica no es edge.

Próximo hito: adaptador exploratorio aprobado y prueba de un fragmento fijo ya autorizado, sin modificar la campaña en marcha. Deben verificarse source/selection/code realmente, no sólo recibirse sus hashes; el planner aquí no lo hace. Siguen pendientes autorización de executor, aislamiento, persistencia externa, LLM con límites API, revisión científica independiente y despliegue24/7.
