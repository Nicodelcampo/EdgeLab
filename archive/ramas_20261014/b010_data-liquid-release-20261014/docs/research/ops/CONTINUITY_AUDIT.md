# MNQ y Research Ops — auditoría de continuidad del entorno

## Resultado

**La campaña recuperada no está activa en el entorno accesible y sus checkpoints privados no están disponibles. El código, protocolos, selección y evidencia ya publicada siguen recuperables.** No se conoce la causa del cambio de entorno por estos indicios; no atribuirlo a corrupción de ticks ni a un fallo científico del motor.

Esta revisión no lanzó jobs de mercado, no descargó los ticks ni abrió holdout. Los archivos de auditoría se conservan aparte; no se reescriben recibos históricos para aparentar continuidad.

## Qué se comprobó

- Campaña: rama `research/avzvol-longevity-full-grid`, head `9125197dc6098100459f36a3d90a5c7b7aa4f9c0`. El último commit publica el reinicio y su preflight, no un cierre posterior de los cinco contratos pendientes. Snapshot publicado `RUNNING` en longevidad de MNQ12-25: evidencia histórica, no liveness actual.
- Última observación en esta sesión, anterior a perder acceso: MNQ12-25 terminó18familias de longevidad y pasó a análisis primario. Ahora faltan su estado/logs/outputs privados; no puede promoverse esa observación a checkpoint verificado de finalización del contrato.
- No se encontraron controlador/watchdog/jobs de la campaña ni sus áreas runtime. Los outputs antiguos `avzp2racgrid` disponibles localmente NO sustituyen los raw ticks ni los resultados nuevos.
- La selección recuperada de PR111 conserva exactamente261filas únicas fecha-contrato y el SHA256 congelado `764ec7cdd2cd432b3442fd22f96eb3d4543ba5e5d579780957a188bd1d6ba5ee`.
- El banco de34recetas conserva exactamente el SHA256 `59184949160128b524c7a47290889d4bdf55c6c0ff214c8a7fc4eac411e0ee06`. No se reseleccionó.
- Las seis fuentes requeridas suman4.879.714.232bytes y485.596.960registros en sus manifests. Kaggle lista sus nombres y tamaños en canonicalv1 y reexportv2 correctos. Son recuperables como inputs candidatos fijados; listar no verifica sus bytes actuales. No sustituir06-26/09-26/12-26 con variantes de canonicalv1.
- Se recuperaron las implementaciones del motor y helpers desde las rutas canónicas `research/` y `tools/research/`. No son un runner portable: rutas absolutas, imports y dependencias deben reconstruirse y verificarse antes de ejecutar. El entorno Python312 antiguo apunta a un binario ausente; un entorno313 aislado permitió pruebas sintéticas.

## Qué evidencia científica sobrevive

El piloto publicado MNQ12-26 conserva cobertura de1.935.360pares de configuración/regla y su exploración focal separada. Hay cero recetas congeladas que pasan conjuntamente los checks absolutos y relativos al control; la intersección con la revisión de robustez también tiene cero celdas. Esto NO demuestra ausencia universal de edge. Fuentes originales no certificadas, universo previamente inspeccionado, controles observacionales, censura y muestras efectivas por sesión siguen siendo límites.

Los1.935.360pares originales por contrato, las3.207.600definiciones focales y las34recetas de replicación son universos distintos. Sus aplicaciones repetidas no son muestras/estrategias independientes. Conservar todos los intentos, invalidaciones y versiones; no reiniciar el historial de multiplicidad por haber perdido runtime.

## Research Ops: integridad comprobada, no autonomía desplegada

Head `d59113cc3d253cb9fbe92375ce8cd564c47698a9`, PR117 abierto/draft, no integrado en main. Los11archivos registrados en `PHASE4_TEST_EVIDENCE.json` coinciden con sus hashes en el árbol remoto recuperado. Esta comprobación cierra la revisión de esos hashes, no una firma/autenticación de productor.

Se repitieron160tests Research Ops,18de navegación y19del hipocampo canónico en Python313: PASS. CI remoto observado: synthetic3.12, synthetic3.13, navigation-only y cpu-base SUCCESS. No se afirma que se ejecutó toda la suite local del repo.

Las vinculaciones de ledger real y corpus siguen vacías; dispatcher de research y budget durable externos pendientes. La cola SQLite es durable dentro de su almacenamiento, NO garantiza continuidad ante rollback/pérdida del host. Un watchdog en el mismo entorno tampoco es almacenamiento externo ni prueba de completitud.

## Antes de reanudar

1. Registrar este intento interrumpido y su última observación separadamente; no inventar checkpoints.
2. Recuperar archivos de las versiones exactas, verificar SHA256/bytes/footer/cutoff y selección/banco, sin modificar fuentes ni permisos.
3. Reconstruir imports/runtime aislado y volver a ejecutar tests de motor/cache/schema/matriz/focal antes de labels.
4. Usar job IDs nuevos enlazados al intento previo. Sólo saltar unidades con recibos y outputs verificados; aquí no hay checkpoints privados verificables del nuevo contrato.
5. Antes de otra corrida larga, vincular host y almacenamiento externo persistentes, checkpoints verificables por unidades, heartbeat externo y recibos terminales. Un nombre `RUNNING` o una línea `FAMILY` no basta para saltar trabajo.
6. Continuar protocolo congelado, secuencial para jobs pesados, con holdout/P&L/promoción cerrados. Nuevo diseño/optimización no autoriza retuning de esta campaña.

No se relanzó la campaña durante esta auditoría. Evidencia técnica resumida: `CONTINUITY_AUDIT_EVIDENCE.json`.
