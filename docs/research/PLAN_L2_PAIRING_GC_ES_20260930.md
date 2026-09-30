# Siguiente fase GC C2 / ES PLANAS: preflight, no resultados

Decisión previa a esta ejecución: mantener GC C2 y ES PLANAS sin ajustar parámetros; preservar GC Junio15 ABSTAIN y los climas ES STOP. Revisar datasets accesibles, certificar custodia y tape antes de cualquier replay nuevo. No confundir features presentes con predictor validado.

Preflight instrument-neutral: instrumento/contrato/tick_size explícitos, hashes de ticks/L1/L2/manifiesto de conversión; tick_size y contrato comprobados contra manifiesto, no sólo config escrita por el usuario. Orden de source_row único por fuente, sin colisiones entre fuentes; clocks ordenados al entrelazar, tipos/códigos MBP-10 y grilla propios del instrumento. Igualdad del tape completo ordenado (UTC ns, precio en ticks, volumen) después de aplicar sólo el offset declarado con su procedencia. No inferir offset ES desde GC. No nearest, rounding, deduplicación, ajuste de cinco timestamps o permiso automático de replay.

El preflight PASS no valida reconstrucción del libro, publicación raw, staleness ni fill. Es una compuerta de entrada; las guardas de replay vigentes (bootstrap60s, atomicidad de timestamp, publicación en siguiente fila/timestamp observado, estricto antes de decisión, edad≤1s, ventana10s) siguen necesarias. Datos y configuraciones con rutas privadas fuera del repo.

Scope actual: repetir identidad GC May31/Junio15 sobre archivos intactos; preparar transferencia ES con tests instrument-neutral, abstenerse si faltan L1/L2. Ningún resultado futuro de señal. Para ES se requieren fuentes del mismo contrato/día que ticks y procedencia de reloj: labels calm/toxic NO reemplazan MBP-10.
