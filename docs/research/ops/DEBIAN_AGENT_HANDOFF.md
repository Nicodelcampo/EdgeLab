# Handoff al agente del servidor Debian — EdgeLab Research Ops

**Objetivo:** operar un único host de investigación que proponga, supervise Kaggle, recupere cierres y prepare aprendizaje trazable. Este handoff NO declara producción lista ni habilita trading, holdout o P&L. No instalar un segundo controlador que compita con el existente.

## 0. Leer primero y fijar releases

- PR117, rama `feat/research-ops-supervisor-mvp`: componentes ResearchOps y este handoff. Último código de fenómenos previo a este hito: `d1eda03ea76812384c622a066d94230adb986138`. Resolver una vez el commit que contiene este handoff y registrarlo como release exacta; no seguir automáticamente una rama móvil.
- PR64, rama `claude/vibrant-clarke-s9z6e2`: autopilot y despliegue Debian. **Snapshot recién revisado:** `d19629fd5df4317aaef2ac2cecbd51198f86a127`. Leer `deploy/debian/LEEME.md`, instalador/units y `edgelab/autopilot/{daemon,executor,ledger,guard,spec,fdr,analyze,brain}.py`. `DEBIAN_AGENT_HANDOFF_SOURCE_REVIEW.json` fija los archivos leídos.
- PR118 fue inspeccionado previamente en `a95227bb31963cef2f722e7948bed09fb8dad297`, no integrado ni revalidado en este hito.
- Memoria/artículos canónicos y conocimiento primero: `KNOWLEDGE_FIRST_RESEARCH.md`, `EXTERNAL_AGENT_ADVANCES_RECONCILIATION.md`, `MNQ_DENSE_CONFLUENCE_BRAIN_RECALL.json`, corpus PR67 fijado en `5c10da451b164c54133bdb9a4674de43d6fa2d22`.
- Fenómenos: `ABSORPTION_EXHAUSTION_EMPIRICAL_DESIGN.md`, `MNQ_PHENOMENA_IMPLEMENTATION_CHECKPOINT.md`, `MNQ_PHENOMENA_P0_PLAN.json`.

Las secciones antiguas de `CLAUDE_HANDOFF.md` son snapshots. No restaurar estado antiguo como si fuera latest; ni concatenar ledgers/anchors del Brain de ramas diferentes. Este host no reemplaza el EdgeBrain por otra memoria.

## 1. Estado y límites científicos que no se negocian por instalación

- Cuenta Kaggle `nicolasbuttaro`; repo `Nicodelcampo/EdgeLab`. Cómputo pesado y toda cinta/feature row/SQLite privado quedan **en Kaggle**, no en Debian/GitHub. Sólo recuperar agregados, conteos, hashes y progreso explícitamente permitidos. No descargar ZIPs completos ni prefijos privados para facilitar debug.
- Trade dates desde **2026-10-01** cerrados; frontera UTC `1790805600000000000`. El guard del spec no sustituye el lector/gate antes de payload ni autoriza fuentes.
- No P&L, órdenes, credenciales de broker o autopromoción. El mandato externo de utilidad/challenges no amplía este alcance. Sus valores de ejemplo no se consideran aprobados por Nico.
- Datasets ya resueltos: reusar manifests/pins/selecciones. No otra QA general, campaña MNQ congelada o auditoría NT8 exhaustiva. Paridad aproximada aceptada para explorar, no porcentaje medido. Tests de un cambio optimizado contra referencia siguen siendo necesarios.
- EXPLORAR ≠ CONFIRMAR. Configuraciones, zonas y filas correlacionadas no equivalen a muestras independientes. Preservar censuras, UNKNOWN, negativos y todos los intentos; no reiniciar multiplicidad/historial.

### Corridas cerradas: no relanzar en recovery

Confluencias `nicolasbuttaro/edgelab-mnq-dense-confluence-engineering-pilot`, id138386707/v3, source97cc93d40d531627381fe71ee4b9e70ca496512b: ERROR ACTIVE_PAIR_BUDGET. Recibos/version y prefijo preservados; no censo completo ni negativo científico. Leer `MNQ_CONFLUENCE_MARKET_KAGGLE_V3_TERMINAL_DIAGNOSIS.json`. NoV4. Nuevo `GeometryCountStream` permite censo de conteos exactos sin conservar gráfica viva, ver `CONFLUENCE_ACTIVE_PAIR_CAPACITY_FIX.md`; no sustituye episodios/llegadas.

P0 fenómenos `nicolasbuttaro/edgelab-mnq-phenomena-p0`, id138410298/v1, source3419122f0c571bc17b0cd96e539ff23dd068c7ef: COMPLETE, recibos de medición vinculados PASS. Leer `MNQ_PHENOMENA_P0_CLOSEOUT.md/.json`. Sesión2026-06-16, ventanas5/20/60s, anclas5s; presión/progreso/decaimiento, NO clasificador A/E/respuestas/edge. Intent durable antes del send y terminal registrados por host manual finito, no integración del daemon. Los snapshots no reemplazan SQLite local completo/witness externo ni prueban globalbudget/custodia.

Atlas target-free multisesión enviado manualmente: `nicolasbuttaro/edgelab-mnq-target-free-phenomena-atlas`, id138412105/v1, source `5a8d74c2b31526aafb30d6618e7012097116e194`; terminal COMPLETE; recibos agregados vinculados PASS. Fuente exacta privadaCPU verificada. Leer `MNQ_PHENOMENA_ATLAS_CLOSEOUT.md` (análisis está en `MNQ_PHENOMENA_ATLAS_ANALYSIS.json`), launch, plan y diseño. No relanzar en recovery. Sesiones June12/15/16, gates P0 intactos, causas UNKNOWN y distribuciones; protocolo de clasificación/respuestas aún pendiente antes de inferencia. Features privadas fueron temporales fuera de outputs; no asumir reuso tras cierre VM. Sólo ese nuevo atlas enviado; no writer canónico activado. Tests772ResearchOps +18navegación PASS en source previo al lanzamiento. Las secciones posteriores de blockers siguen vigentes.

### Siguiente protocolo implementado, todavía no enviado en este snapshot

`MNQ_PHENOMENA_SCIENTIFIC_PROTOCOL.md` y plan fijan calibraciónJune12 / evaluaciónJune15-16 de desarrollo: A/E/coexistencia sin zonas, respuestas observadas60s en midpoint, censura, gates sin relajar por éxito. NO M2−M1 ni inferencia todavía. Tests812ResearchOps+18nav PASS. No usar ejemplos de este piloto como órdenes de producción.

En recovery actual, los journals del sandbox estaban anteriores a snapshots publicados; conservarlos como históricos, no rearmar eventos inventados/resetear lifetime. Se recuperó source exactof3d9f26 para seguir. Un nuevo batch manual tendrá intención1/watch4 y ancla al snapshot latest; **no integra ni demuestra presupuesto/lock global**. Debian necesita recuperación durable aprobada/latest witness antes de adoptar ejecución automática.

## 2. Bloqueos de la implementación externa actual

Estos puntos se observaron en el snapshot nuevo; no se afirma un incidente productivo ni que todo el repo haya sido auditado.

1. `daemon.tick`: launch antes de `ledger.add`. Una caída puede dejar envío remoto sin handle local. Reservar intención durable antes del proveedor; timeout desconocido no es fallo seguro para reenviar.
2. Liquidación alfa, cierre de ledger, evidencia y Brain son pasos no atómicos. Caída entre pasos puede duplicar/liquidar mal o dejar aprendizaje incompleto. ERROR cierra run sin resolver la reserva alfa en esa rama. Revisión de semántica de fallos y recuperación requerida.
3. `AlphaInvesting` mantiene JSON cargado en memoria y `_save` no es transacción compartida/atomic replace. No usar varios procesos con estado obsoleto; presupuesto de cuenta y FDR son contabilidades distintas.
4. `analyze.decide`/Holm no validan finitud/rango/tipos de p: negativos/NaN requieren rechazo o UNKNOWN explícito, manteniendo denominador planeado. No interpretar conteos de P0/confluencia como p-values.
5. `guard.check_env_in_prereg` compara **valores por substring**, no claves/valores ni spec completo. Vincular estructuralmente fuente/selección/build/params/endpoint/protocolo, sin “reparar” manifiestos protegidos automáticamente.
6. `propose` **no es read-only**: el ciclo cierra corridas existentes, analiza/liquida y puede escribir Brain antes de proponer. `--status` también instancia el ledger; no llamarlo una lectura forense inmutable. No probar propose contra estado productivo sin backup/lock y política de cierres.
7. Unit hace `git pull --ff-only` en cada ciclo: podría cambiar build activo. Pin de release y cambio explícito, no auto-update durante ejecución. Units no resuelven procesos manuales paralelos; un lock global debe cubrir CLI/timer/generador/escritores.
8. `sync_state.sh` hace `git add -A autopilot_runs`; SQLite principal está ignorado y no respalda allí recovery completo. Allowlist de export limpio y backup consistente independiente son necesarios; no publicar logs arbitrarios/secrets o archivos crudos.
9. LEEME aún declara **sin prueba en Debian real**. Instalador usa Python por defecto de Debian, pero PR117 `pyproject.toml` pide **Python>=3.12,<3.13**. Debian12 trae normalmente3.11: preparar3.12 aprobado, no asumir compatibilidad por doctor>=3.10.
10. Doctor llama un endpoint de lista; HTTP200 y `.netrc` presente no prueban acceso privado ni validez del token. Verificar cuenta/permiso en operación mínima autorizada, sin exportar contenido privado. `brain_ledger` de ejemplo no es un destino canónico aprobado por sí mismo.

No activar `execute` sólo porque doctor imprime LISTO. No refresh del protected manifest para tapar cualquiera de estos puntos. Resolver en una rama de integración revisable y probar; no modificar/mergear ramas de otros agentes automáticamente.

## 3. Pieza nueva para integrar, no segundo controlador

`tools/research_ops/dispatch_intent.py::DispatchIntent` es un journal SQLite finito, stdlib, sin red/selector/runner/credenciales/writer. Resuelve el **primitivo de intención local**, no toda la integración:

```
PREPARED -> SEND_UNCERTAIN -> ACKNOWLEDGED -> COMPLETE | ERROR | CANCELLED
PREPARED -> ABANDONED_PRE_SEND
```

- `initialize(account,max_pending=1,max_intents=8)` crea política inmutable. No reset al reiniciar ni refund automático; abandonar antes de send libera slot, no gasto histórico.
- `prepare(request,expected_tip=...)` persiste identidad cerrada: account/spec SHA/source commit/bundle SHA/plan SHA. Misma identidad es idempotente, incluso terminal: no produce otro intento.
- `begin_send(key,expected_tip=...)` **se guarda ANTES** de llamar al proveedor. Desde aquí una caída/timeout es ambiguo y consume el slot; no `begin_send` otra vez ni abandonar para liberar capacidad.
- Host obtiene aprobación y hace un único envío mediante el executor existente; recoge coordenadas exactas y las verifica externamente. `acknowledge` enlaza kernel/version/pins a request y es idempotente. Si la respuesta se perdió, reconciliar por recibo/metadata/source exactos; cero/múltiples candidatos o pins discrepantes = QUARANTINE, no resend.
- `terminal` exige job exacto reconocido. COMPLETE técnico no adjudica ciencia ni escribe memoria. Snapshot no acredita latestness/remote truth; un archivo viejo válido aún requiere witness externo y fencing.

El componente **no está llamado por PR64 hoy**. No afirmar exactamente-una-vez de Kaggle, presupuesto global de cuenta o crash recovery integral por pasar sus tests. Unificarlo con run ledger/presupuestos/ack del host existente, no tener dos schedulers y dos cupos independientes. Mantener caps de cuenta incluidas corridas manuales/agentes ajenos; mientras no haya esa visibilidad, no nuevos lanzamientos automáticos.

## 4. Implementación Debian por etapas

### A. Preparación sin habilitar servicios

1. Identificar si ya hay controlador activo, propietario y timers. No crear otra instancia ni borrar su estado. En host nuevo mantener PAUSE; en host existente coordinar parada del host sin cancelar jobs remotos.
2. Usuario de servicio `edgelab` sin root/shell interactiva; estado bajo`/var/lib/edgelab-autopilot`, configuración bajo`/etc/edgelab`, código en releases versionadas bajo`/opt/edgelab`. Código/protected config fuera del permiso ordinario de escritura del agente. Directorios de estado0700, secretos0600.
3. Descargar/checkoutear PR64 y PR117 en worktrees/repos **separados y fijados a SHA** para revisión. No mezclar APIs de ramas vía PYTHONPATH ni copiar sólo un módulo con dependencias faltantes. Preparar release de integración revisada con la única interfaz de host adoptada; no mergear main.
4. Instalar Python3.12 de una fuente aprobada por el administrador y venv separado. Conservar lock/`pip freeze` y recibo de entorno. Referencia de pruebas ResearchOps: `requirements/research-ops-authority.txt`; para fenómenos NumPy/Pandas/PyArrow y dependencias bridge. El instalador externo instala paquetes flotantes: fijarlos en la release antes de declarar reproducibilidad.
5. Leer `deploy/debian/install.sh` antes de ejecutarlo. No correr a ciegas contra un clon de estado existente; su lógica de orphan/remoción no es migración segura. Usar paths/configs aprobados y comprobados, no inventar defaults de branch/estado.

Comandos de verificación en **el checkout PR117 fijado**, no en producción:

```bash
python3.12 --version
python3.12 -m venv .venv-handoff
.venv-handoff/bin/python -m pip install -r requirements/research-ops-authority.txt
# Instalar las dependencias del fixture de fenómenos en el venv; guardar versiones.
.venv-handoff/bin/python -m unittest tests.research_ops.test_dispatch_intent -v
.venv-handoff/bin/python -m unittest tests.research_ops.test_phenomena -v
.venv-handoff/bin/python -m unittest discover -s tests/research_ops -v
.venv-handoff/bin/python -m unittest discover -s tests/navigation -v
.venv-handoff/bin/python tools/edgelab_catalog.py check --json
```

No hay garantía de que PR64 tenga esos paths/tests. Ejecutar también sus tests en su release/entorno, no atribuirle los de PR117. No se ha corrido todavía ningún comando en Debian real desde este chat.

### B. Autenticación y red

- El host Debian no hereda MCP, login, `.netrc` o credenciales de este chat. Usar credenciales del usuario/servicio aprobadas; pedirlas por canal seguro, no chat/repo/argumentos de proceso/historial.
- Si se elige la ruta CLI externa, `.netrc`0600 sólo para`www.kaggle.com`; no enviar auth a URLs firmadas de GCS ni otros dominios. Verificar permisos de cuenta con operación mínima permitida. Si se usa MCP/Worker, vincular identidad/acceso y presupuesto del host: no asumir que basta copiar un nombre de herramienta.
- Deploy key para **estado sanitizado** con alcance mínimo; ni secretos ni runtime privado en GitHub. GitHub deploy keys escribibles no restringen por sí solas a una rama: guard de destino/permisos de plataforma y política de un único escritor siguen siendo necesarios.
- URLs firmadas en kernels privados expiran (las usadas antes duraban72h). Renovarlas desde el proveedor si falta, no versionarlas en config. Egress mínimo Kaggle/GitHub/GCS según operación; DIX/propfirm research sólo si se aprueba esa función, no requisito del piloto MNQ.

### C. Observación controlada

Primero scratch state y lectura de metadata/estado exactos. `--status` del externo no lanza, pero puede crear DB/schema: usar root conocido y lock, no réplica forense. `propose` sobre root con runs pendientes puede cerrar/escribir: usar fixture vacío y `brain_ledger=null`/registry deshabilitado para humo, sin importar estado vivo. PAUSE evita que tick trabaje; no fingir éxito porque sólo devolvió paused.

Adoptar `RemoteWatch`: reservar consulta antes de red y registrar respuesta/hash/identidad, incluso UNAVAILABLE. No reembolso de consulta tras caída. Reservas pendientes requieren reconciliación manual/host, no loop infinito. Status desconocido no es ERROR ni permiso de relanzar.

### D. Envío de humo y luego P0

Antes del primer envío: release/config exactos, singleton/fencing, global budget y dispatch-intent conectados, autoridad de scope, datos/selección/build atados y host limits activos. Ejecutar un humo sintético inocuo, privado, con token de intento durable; simular pérdida de respuesta/reinicio y comprobar que no manda dos veces.

Después recuperar V3 existente (sin repetir auditorías generales) y empaquetar P0 fenómenos de **una sesión**. Reusar pin aprobado, fuente sólo Kaggle, límites900s/4GiB/5M ticks/250kanchors y512MiB privados; parent/CPU/RSS/spill y transferencia deben quedar fijados antes de send. Runner P0 por sí solo no impone el límite RSS global: el host está pendiente. Features temporales privadas fuera de`/kaggle/working`; allí sólo recibos allowlist. No convertir este P0 en apuesta alfa/edge.

### E. Activación acotada

Sólo tras los criterios abajo y decisión explícita de activación: timer oneshot con lock compartido, release inmutable, cuenta/caps finitos, kill switch y avisos de fallos. No `--loop` y timer simultáneos. Sugerencia inicial conservadora: un slot global, una corrida nueva/día y pocas consultas por intento, acordadas y persistidas; no copiar automáticamente los2slots/2corridas del ejemplo.

Deshabilitar auto-pull de unit en release aprobada. `TimeoutStartSec` del host no debe matar/reencolar una corrida Kaggle: kill/timeout del host marca envío incierto o deja remoto activo. Restart no repite send; requiere reconciliation. MemoryMax del host es distinto del límite del notebook. Mantener generador/propfirm timers apagados hasta aprobar sus funciones/costo. Si se eligen decisiones científicas automáticas posteriores, requieren sus protocolos/roles y endpoints específicos, no el permiso genérico de instalar un timer.

## 5. Cierres y aprendizaje al EdgeBrain

Un estado COMPLETE no basta: recuperar outputs de **versión exacta** mediante allowlist de filenames/bytes/hosts, verificar sellos/source/bundle/plan y estado semántico, sin bajar datos privados. Archivar fallos/prefix/timings aun sin éxito. Identidad equivocada, artefacto ausente o sello roto = cuarentena.

Producer→envelope→outbox→review→canonical ack son capas distintas. `authenticated_closeout.py` cubre un cierre semántico MNQ completo con custodia firmada y RSS real de proceso aislado; no aceptar un prefix de confluencia ni P0 como si satisfacieran ese esquema. V3 sampled child RSS NO es su medida estricta. Extender tipos con tests explícitos o guardar el agregado como evidencia técnica, nunca inventar memoria/RSS/units para pasar el gate.

`canonical_delivery.py` implementa entrega **técnica revisada** con firma de rol distinto, destino/anchors frescos, payload idéntico y ack durable. Falta vincular claves reales, custodio, revisor, destino y witness de latestness. No generar llaves y autoaprobar con dos nombres del mismo agente. Resultados científicos necesitan revisión/esquema propios: ni `brain_sink` directo del externo ni cambiar status del outbox sustituyen esa autorización. No crear otro ledger para eludir un bloqueo.

Consistencia del cierre: registrar terminal recibido → outputs verificados → decisión/alfa aplicada idempotente → cierre operacional durable → outbox pendiente → ack de destino. Cada paso debe poder reanudarse sin reejecutar compute, reliquidar alfa o perder una escritura parcialmente hecha. DONE científico y DELIVERED son estados diferentes.

## 6. Backup, fallos y criterios de aceptación

Backup bajo lock: SQLite online backup/snapshot consistente, no copiar DB viva sin WAL/journal; coordinar run ledger, dispatch journal, remote watch, alpha, outbox y hashes de configuración. Restaurar conserva incertidumbre/RUNNING y presupuestos. Destino independiente, cifrado/permisos y último witness externo; `git push` de logs no equivale a backup integral ni latestness. Verificar restauración en sandbox sin enviar jobs.

Pruebas obligatorias del host integrado (todavía pendientes):
- Caída antes/después de send y antes/después de ack; timeout/5xx/pérdida de red; job duplicado/versión distinta; **cero reenvíos automáticos ambiguos**.
- Dos procesos/CLI+timer: sólo un lock/reserva válida; contador de cuenta comparte todos los lanzadores, cuotas/reservas sobreviven reinicio.
- p negativo/NaN/Inf/bool/fuera de[0,1], resultados duplicados/no evaluables, denominador planeado; política de alfa para ERROR/inconclusos sin recompensas falsas.
- Caída entre settle/finish/evidence/Brain/ack; tail rasgado, conflicto mismo ID, ancla vieja/restauración incompleta → bloquear, no sobreescribir historia.
- Fuente/build/env/prereg estructuralmente distintos; need malformado/fecha invertida/holdout; archivo fuera de allowlist/byte cap/URLhost equivocada → bloquear antes de payload/acción.
- PAUSE/kill switch real; fallo de sync/credenciales; logs sin tokens/URLs firmadas; restauración con fencing y liveness verificados.
- Benchmark exacto y perfil por etapa; no adoptar variantes más lentas ni extrapolar ratios sintéticos a mercado. Sin nueva QA general de datasets.

**Estado aceptable inicialmente:** observación y propuestas finitas con cero lanzamientos no autorizados, sin writer científico automático. **Execute listo** requiere pruebas del host real y bindings anteriores. No hay claim de servicio24/7 por ver heartbeat JSON, instalar systemd o pasar tests locales.

## 7. Entrega que debe hacer el agente Debian

Dejar en repo/estado sanitizado: commits de release revisados, changelog de integración, config sin secretos, versiones Python/deps, units/drop-ins, identidad de host y singleton, políticas/budgets, resultados de tests/fault-injection/restore, primer humo y P0 con IDs/versiones, estado de V3 y evidencia allowlist, backup/witness, destino/roles del Brain y procedimiento de parada/recuperación. Separar evidencia real de tests simulados; no aprobarse a sí mismo.

**Prioridad:** terminar el host mínimo seguro, recuperar la corrida activa y obtener mediciones nuevas útiles. No abrir otra ronda interminable de auditoría histórica ni construir una infraestructura de trading que Nico no pidió en este alcance.
