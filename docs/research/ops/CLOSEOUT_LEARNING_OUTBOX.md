# Cierres verificables y bandeja durable de aprendizaje

Estado: **importación local + planificación + outbox transaccional probados**. No polling remoto, autenticación Kaggle, descarga automática, escritor Brain, adjudicación científica ni activación de optimizaciones. No se modifica el motor de la campaña activa. Continúa [el ciclo poscorrida](POST_RUN_LEARNING_AND_OPTIMIZATION.md).

## Qué quedó conectado

`Envelope técnico sellado → verificación de bytes/schema/job/versión → plan_post_run → outbox REVIEW_PENDING → lectura pendiente revisada`

- `closeout.py` captura una lectura local no-follow, regular y acotada a64KiB; valida SHA externo, JSON sin claves duplicadas/NaN, contrato cerrado, proveedor/job/versión fijados por el host y terminal COMPLETE/FAILED/CANCELLED.
- Sólo admite la proyección técnica tipada de `RunObservation`. Rechaza campos económicos, free-text instructions y estados RUNNING. Identidades/hashes de fuente/build son declaraciones hasta verificar custodia; no certifica datos ni autoridad por comparar hashes.
- `learning_outbox.py` prepara el plan existente y lo persiste en una transacción SQLite `BEGIN IMMEDIATE`/`synchronous=FULL`. Cierra con un evento encadenado y verifica la proyección exacta por replay. No duplica la memoria de EdgeBrain: es una bandeja operacional de entregas **aún no efectuadas**.
- Identidad lógica única por **proveedor + job + versión**. El binding del proveedor debe identificar la ejecución/sesión inmutable; un slug reutilizable solo no basta para distinguir reruns. Mismos bytes del cierre: noop incluso tras reiniciar. Otra evidencia/recibo bajo la misma identidad: conflicto, sin overwrite ni segunda lección silenciosa. Una revisión/corrección necesita invalidación y diseño de un sucesor explícito, no reutilización del registro invalidado.
- La capacidad se congela al inicializar (default32, máximo128). No ejecuta subprocess, red o LLM; no consume presupuesto científico ni concede otro intento. Incluye fallos/incompletos con un plan de reparación.
- Las mutaciones de ingest requieren el tip esperado; dos clientes con un tip viejo no pueden registrar simultáneamente. Es CAS local, no lease/fencing de dos máquinas ni autorización del proponente. Tip y SHA deben custodiarse fuera de ese mismo host para detectar rollback real.
- Invalidación preserva evidencia y bloquea reutilización. No borra drafts ni los transforma en DELIVERED/ADOPTED. Esa transición no existe sin writer/revisión auténticos.

## Esquema de entrada

Objeto JSON exacto con `schema=research_ops_technical_closeout_v1`, `provider` (`synthetic` o `kaggle`) y `observation`. La observación sigue el dataclass existente de `post_run.py`: run/job/version, terminal, source/selection/protocol/build/manifest/receipt hashes, wall, RSS máximo medido, unidades esperadas/terminadas, spans seriales, integridad y failure code cerrado.

El sobre no admite resultados científicos ni texto libre. Un productor aprobado debe:

1. Consultar el job remoto y fijar su versión inmutable.
2. Completar la paginación de outputs; evitar considerar una primera página como inventario completo.
3. Descargar a almacenamiento privado, verificar bytes/SHA y cierre semántico.
4. Ejecutar auditorías independientes de cobertura/recuentos y conservar TODOS los fallos.
5. Proyectar únicamente metadata operacional; mantener resultados/outcomes en sus contratos científicos y acceso aprobado.
6. Medir RSS/costos/tiempos completos; si una medida falta, detener la importación y registrar el diagnóstico fuera del sobre. **Nunca imputar cero, inventar RSS ni presentar tiempos declarados como autenticados.**
7. Sellar el sobre y custodiar su SHA y binding job/version en el host confiable.

El importer valida la frontera LOCAL, no hace estos siete pasos ni autentica que ocurrieron. `integrity=PASS` es una declaración tipada, no un certificado de auditoría. No aceptar sobres creados por un LLM como si provinieran del productor. El host aún debe ligar autorización, evidencia original, reloj, unidad de censo y build/environment antes de usar una propuesta.

## Recuperación sin doble aprendizaje

El outbox tiene un archivo SQLite separado de la cola sintética existente. Inicializarlo encima de la cola u otra base se rechaza. El snapshot anterior `snapshot-queue` **no lo incluye**: respaldar ambos artefactos por separado hasta implementar un checkpoint coordinado del supervisor.

- `export_outbox`: snapshot local exclusivo, acotado a4MiB, pin SHA y tip; no sobreescribe.
- `restore_outbox`: comprueba el SHA/tip externos y contrato cerrado, materializa/replay-verifica en un temporal y sólo después restaura en un directorio nuevo. Conserva REVIEW_PENDING/INVALIDATED, capacidad y eventos.
- No envía drafts, no escribe Brain ni repite trabajos de Kaggle al restaurar. Un restore válido con ancla vieja no prueba que sea el estado más reciente: witness/latest/fencing remoto siguen pendientes.
- Hashes locales no protegen contra un administrador que reescriba coherentemente DB y anclas. Se requiere directorio privado confiable; no se afirma resistencia a carreras de un adversario que controle el filesystem padre.

Antes de añadir el writer: definir idempotencia en destino canónico y protocolo de recibo/ack para el caso «Brain escribió, el proceso cayó antes del ack local». No llamar a esto exactly-once end-to-end. Este hito sólo demuestra registro local idempotente y restauración fiel.

## CLI

Los nuevos comandos son explícitos y no activan el worker ni un daemon:

```bash
python -m tools.research_ops.cli outbox-init --outbox artifacts/research_ops_learning/outbox.sqlite --max-items 32
python -m tools.research_ops.cli outbox-verify --outbox artifacts/research_ops_learning/outbox.sqlite --expected-tip TIP_EXTERNO
python -m tools.research_ops.cli ingest-closeout envelope.json --outbox artifacts/research_ops_learning/outbox.sqlite --expected-sha256 SHA_EXTERNO --expected-tip TIP_EXTERNO --provider synthetic --job-id job_1 --version 1
python -m tools.research_ops.cli snapshot-outbox outbox-snapshot.json --outbox artifacts/research_ops_learning/outbox.sqlite --expected-tip TIP_EXTERNO
python -m tools.research_ops.cli restore-outbox outbox-snapshot.json restored-learning --expected-sha256 SHA_SNAPSHOT_EXTERNO --expected-tip TIP_EXTERNO
```

SHA/TIP son placeholders de pins verificados/custodiados, no credenciales. Los comandos no almacenan ni requieren tokens. Validar y renovar el tip tras cada transición; una excepción por tip viejo exige verificar el estado, no reintentar ciegamente.

## Evidencia y límites

46 pruebas nuevas sintéticas: duplicados/restart, cierre conflictivo, versiones/proveedores, capacidad, CAS concurrente, corrupción de proyección/cadena, interrupción entre insert/event y caída de proceso con transacción sin commit, invalidación, snapshots, restore sin dispatch, binding de importer, NaN, symlinks, archivos grandes, métricas ausentes y CLI. Suites y hashes en `CLOSEOUT_OUTBOX_TEST_EVIDENCE.json`. Demo local synthetic closure→ingest→repeat→reopen→snapshot→restore en `CLOSEOUT_OUTBOX_DEMO_EVIDENCE.json`.

No se importaron datos privados o outcomes de MNQ en una memoria operacional. Los tiempos recuperados de MNQ siguen siendo contexto técnico; todavía no hay un productor aprobado que complete ese sobre con RSS y todas las pruebas de custodia. No alegar ciclo Kaggle→Brain activo por haber completado una demo local.

Próximo hito mínimo: productor read-only de cierre y telemetría confiables; después writer canónico operacional con revisión y deduplicación en destino. Activación de benchmarks/parches requiere presupuesto durable, ejecutor aislado y gates separados. La campaña científica permanece congelada.


## Local MNQ receipt bridge

See [MNQ_CLOSEOUT_PRODUCER.md](MNQ_CLOSEOUT_PRODUCER.md) and `MNQ_PRODUCER_TEST_EVIDENCE.json`. The technical-only producer now validates pinned, independently reviewed real receipt bundles, but blocks envelope output without measured RSS and verified execution/input/build binding. This is not live Kaggle ingestion, canonical-memory delivery or optimization activation.
