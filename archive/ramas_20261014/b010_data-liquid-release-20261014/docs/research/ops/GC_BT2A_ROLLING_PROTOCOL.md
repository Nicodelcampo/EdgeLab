# Percentil BT2A incremental exacto — candidato experimental

Plan congelado `GC_BT2A_ROLLING_PLAN.json`, SHA `c91b12d689ceeaa62ee0cb130e563814f15d40edb13855dd5c2e15475f4471ba`. No outcomes, modelos, P&L ni holdout; no cambio del default de producción ni promoción automática.

## Cambio único
Mantener lista ordenada estable del mismo lookback nativo, en vez de ordenar desde cero en cada llamada al percentil. Interpolación y valores originales intactos. FIFO nativa `abs_ring` permanece sin cambios: hook AST fuente-pinned añade actualización de cache tras cada append nativo no residual y sustituye sólo `_percentile(abs_ring,abs_pct)`. Guardias de censo:1 umbral y2 append. Sin compartir historias entre configuraciones, acortar lookback, mover nacimiento o cambiar score/threshold/calendario.

BT2AStream acepta `rolling_percentile=False` por defecto. Sólo el nuevo benchmark opta explícitamente porTrue; los runners científicos existentes no lo activan. Tests sintéticos comparan umbrales en logs diagnósticos, capturas, residuos, estado tras sesiones yEOF para cuatro tamaños de tick y tres perfiles; no certifican NT8.

## Medición cerrada
GC, los mismos470.027 ticks/cuatro sesiones3–6 de agosto del perfil anterior. Misma lectura/bounds/pines. Tres perfiles originales, estado persistente. Scheduler PROFILE_SEQUENTIAL en ambos brazos para aislar percentil: no combinar intercalado y cache de percentiles en una comparación confusa.

ABBA producción: ORIGINAL,ROLLING,ROLLING,ORIGINAL. Medianas de push+finish; hash/fingerprint fuera de ese temporizador. Dos pases adicionales diagnósticos(original,rolling) comprueban también umbrales y logs completos. No incluir estos pases en la aceleración de producción. Fingerprints incluyen historial, zonas activas, relojes, buffer, prefijo, secuencia de barras yEOF. Verificar FIFO y orden estable de cache contra historia nativa tras cada sesión. Ante discrepancia falla todo sin declarar speedup exitoso.

Exportar únicamente agregados, tiempos y hashes; código/log/estados de mercado permanecen enKaggle. Total≤64KiB de recibo. Un intento nuevo, max1 pending, seis polls; journals originales conservados. Antes de envío guardar SEND_STARTED; ACK sólo tras fuente remota exacta,CPU privado,versión yDocker. Ante envío ambiguo no reenviar ni refund. No tocar jobs terminales previos.

## Salida esperada y límites
Si la paridad pasa, reportar velocidad del subpaso de tres perfiles enGC, NO de todo EdgeLab ni de otros instrumentos. No convertirlo en edge científico. Integración futura en runners requiere opt-in explícito y considerar evidencia suficiente; esta corrida no despliega enDebian ni habilita autonomía24x7. Mantener todo resultado negativo/inconcluso y el contexto de selección previo.
