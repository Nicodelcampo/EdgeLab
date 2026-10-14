# Coordinación de avances entre agentes: PR64, PR117 y PR118

## Snapshot externo revisado primero

Rama `claude/vibrant-clarke-s9z6e2`, PR64, commit fijado `972cb39bcade89f3505550f8176fb3ef7fdc9820` (Claude). Es una rama activa: este documento describe ese snapshot, no la punta futura. Nuestra rama PR117 seguía en `890319e96897b053d7a1a244fd49b59f8bd0fa8b`; main seguía en `4579f5512b150a440d0bd6ea3115a5032ec8d0f0`. Ninguno de estos avances externos fue mergeado automáticamente.

Leídos: commits a167948/eeb397a/747f6ce/972cb39, `deploy/debian/LEEME.md`, `edgelab/autopilot/{daemon,fdr,guard,spec,analyze}.py`, config/bitácora/heartbeat, resultado SLOT-1 y ledger hippocampus. También inspeccionado PR118 `a95227bb31963cef2f722e7948bed09fb8dad297`: despacho/checkpoint/status compuesto, no incorporado aquí.

## Qué agregó el otro agente

- Autopilot finito: seleccionar candidatos, verificar preregistros/protegidos, reservar alfa, lanzar en Kaggle, cerrar/analizar y actualizar evidencia/Brain.
- Installer/servicios/timers Debian, doctor, kill-switch, heartbeat/status, sync hacia rama de estado de escritor único y credenciales fuera del repo. **LEEME declara que todavía no se probó en Debian real**. No ejecutamos instalación, pedimos secretos ni activamos servicios.
- Config snapshot en execute, máximo dos corridas concurrentes/día, IDM-1 y SLOT-1 en bitácora. El heartbeat se escribe antes de cerrar corridas: **no usar ese JSON archivado como prueba de liveness actual**. Estado vivo de IDM-1 no consultado por este hito.
- SLOT-1 reportado sin hallazgo/0 rechazos: no generaliza la pista GC04:30 a otros activos; evidencia la degrada a FAILED_REPLICATION y consume esa muestra. Fuente: RESULTADO_SLOT1.md del snapshot. No recontamos sus resultados, no declaramos confirmación/edge ni cambiamos nuestro estudio MNQ por ese resultado.
- Dos nuevos registros de Brain para AUTOPILOT-slot-1. El archivo observado tiene 30 filas y tip `19798d86684073c7d9238985806640456dde1bd0d7ce1a1e5b4954bc0b745a59`; es una nueva versión de rama, **no nuestra autorización de writer ni un latest witness remoto**. No sobrescribir o concatenar nuestro ledger/anchors anteriores.

## Qué conserva/aporta PR117

96 configs AVZP2/BT2/BT2A, cuatro racimos y 32 tríadas alineadas; captura causal/streaming y control de source/planes/versiones privados. V1/V2 fallidos preservados; V2 target reportada completa pero sólo dos tríadas antes de error no clasificado. V3 diagnóstica sigue RUNNING según consulta actual, exact source/metadata contrastados. No relanzar, no modificar código activo ni reauditar datasets.

Journal durable finito con reserva previa de consultas; adquisición/review terminal de agregados; scope semántico explícito. Código V3 añade prefix receipts selladas y tiempos nested storage para conservar trabajo útil ante fallo. Sin daemon desplegado, custodian firmado, writer real aprobado o inferencia científica automática. Las afirmaciones de no despliegue/writer de PR117 **no niegan** que PR64 implementó otro prototipo y escribió su propio snapshot de rama.

## Decisión de integración: aprovechar, no duplicar ni auto-adoptar

No construir un segundo controlador de mercado que compita con el autopilot externo. Próximo hito compartido: interfaces entre RunSpec/selector externo y el seguimiento/adquisición/semántica de PR117, con un único escritor/owner operacional, presupuesto global de cuenta y contratos de custodia/ack claros. No crear ahora un daemon paralelo ni mergear ramas para aparentar integración.

Separar presupuestos: cuotas/tiempo/memoria de Kaggle, reservas de consultas, conteo de hipótesis y riqueza de alfa son cosas diferentes. Un piloto técnico de densidad/geometría o benchmark NO es una prueba de edge a liquidar por Holm. No alimentar conteos MNQ actuales al formato p-values del autopilot. Tener alpha-investing no certifica FDR global para escenarios dependientes/superpuestos; hay que preservar el protocolo propio de incertidumbre/multiplicidad.

La promoción de un borrador a candidato runnable del otro agente no se interpreta como promoción de estrategia/trading. Las nuevas muestras/negativos deben compartirse para no repetir una muestra consumida, pero requieren fuente/versión/protocolo y adjudicación; no basta con texto del selector.

## Límites concretos a resolver antes de adoptar código externo

Tres sondas sintéticas, stdlib-only, contra fdr/analyze **exactamente fijados por blob+SHA256** (sin red, mercado, archivos productivos o ejecución del daemon):

1. `decide` acepta p negativo como hit; p NaN marcado evaluable entra en n_evaluable. Hace falta gate explícito de tipos/rango/finitud y UNKNOWN, manteniendo denominador planeado. Esto no demuestra que SLOT-1 esté errado: sus datos no fueron reanalizados.
2. Dos objetos AlphaInvesting con estado inicial obsoleto, cada uno haciendo dos reservas, producen un costo combinado superior a riqueza inicial y un archivo que pierde reservas. Es una reproducción del primitivo aislado, **no incidente observado ni auditoría del lock del entrypoint**. Mantener escritor único; antes de conectar controladores, transacciones/locking/atomicidad/reservas compartidas verificadas.
3. En el daemon leído, launch precede a ledger.add y settle precede a finish; ERROR no liquida la reserva alfa en esa rama de código. Revisar crash/retry, handles/versiones y política de reservas fallidas con fault injection. Son puntos de revisión estática, no afirmación de corrupción productiva.

Además, la guarda de env comprueba aparición de valores como substring en el preregistro; no equivale a binding estructural key/value del spec completo. Datos/fechas y ejecuciones exigen scope efectivo verificado, no sólo declaraciones needs. Estas observaciones son locales al snapshot fijado; no parchear la rama activa del otro agente ni extrapolar a versiones futuras.

Las fuentes y observaciones cerradas están en `EXTERNAL_AGENT_ADVANCES_RECONCILIATION.json`. No se importó código externo al runtime PR117, no se ejecutó su suite completa, no se inventaron sus tests como propios. La última regresión propia sigue 731 ResearchOps +18 navegación PASS; este hito actualiza documentos/estado y agrega sondas específicas, no otro benchmark MNQ.

## Ideas de eficiencia útiles rescatadas

El Brain externo conserva propuestas LOW/UNRATED: perfil de análisis posterior (matching/permutaciones/bootstrap), índices numéricos por estrato y caches de derivados con paridad. Son ideas transferibles, no ratios de speedup automáticamente válidos para MNQ. M1 agregado NO sustituye ticks/footprints para confluencias; caches/primitivas del mismo scope pueden reutilizarse sólo con parámetros/clock/history/output exactos.

Usar sus manifests/versiones para transporte/identidad sin repetir QA de datasets ya resueltos. Toda prueba con ticks privados o derivados sigue dentro de Kaggle. No adoptar la sugerencia externa de probar ticks reales en local para este flujo KAGGLE_ONLY.

## Próximo orden de trabajo

1. Terminar V3 activa y revisar sólo outputs agregados contra paquete/plan diagnóstico V3, conservando prefix/failure.
2. Escoger una optimización por perfil real; evitar pérdidas de historia, máscaras o escenarios.
3. Preparar integración finita con autopilot externo y PR118, una responsabilidad por capa; probar idempotencia/capacidad/finitud antes de habilitar.
4. Mantener falsación, negativos, oportunidades propias, población común de anchors, densidad/ocupación/carry/dependencia antes de outcomes científicos; holdout cerrado y sin P&L.
