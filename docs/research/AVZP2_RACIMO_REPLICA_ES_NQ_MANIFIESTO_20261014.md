# AVZP2-RACIMO-REPLICA — replicación de compresión (O5) y salida a favor de tendencia (O1) en ES y NQ — manifiesto — 2026-10-14

Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
**Información, no P&L** (no requiere STOP). Escrito **antes de abrir un solo dato de ES o NQ con este indicador**.
Datos: release canónica `liquid_tick_v1` (`nicolasbuttaro/edgelab-liquid-ticks-20261014`, CANDIDATE_NOT_RESEARCH_APPROVED, SHA verificado);
holdout (trade date ≥ 2026-10-01) ausente de la release.

## Justificación económica
Un racimo es inventario de volumen acumulado en una franja angosta. Si la compresión posterior (O5) y la continuación a favor
de la tendencia previa (O1) son propiedades de la mecánica de absorción y no de MNQ, deben aparecer en otros índices de la
misma bolsa y la misma sesión. Es el paso previo obligatorio antes de gastar presupuesto de P&L (handoff §6).

## Hipótesis congeladas (copiadas de AVZP2-RACIMO-GRILLA, sin tocar)
Zonas: parámetros de la configuración de Nico (barras 25t, OB 100/6/8/4 %, detección por defecto). Racimo = (mín. zonas / ventana velas / altura ticks).
- **H-O5** (compresión, desenlace primario): β(real − pseudo apareado) < 0 en las celdas **6/500/30** (config de Nico) y **{4,5,6}/1000/{30,45}**.
- **H-O1** (continuación a favor de tendencia, con FE por decil de magnitud de tendencia 500 velas y momentum 100 velas): β > 0 en **{4,5,6}/1000/{30,45}**.
- Mismos desenlaces, mismo nulo (5 pseudo por racimo apareados por ocupación previa ±0,05, mismo reloj de 30 min, misma altura/posición), mismos FE y SE clusterizado por sesión que `tools/avzp2_racimo_grid_stage2.py`.
- **7 celdas × 2 desenlaces (O5 en las 7, O1 en 6) = 13 pruebas por instrumento.** Holm por instrumento. ES y NQ son réplicas separadas; no se mezclan.

## Criterio de replicación (fijado antes)
- Un instrumento **replica O5** si ≥ 5 de 7 celdas tienen β < 0 con p_Holm ≤ 0,05. **Replica O1** si ≥ 4 de 6 celdas tienen β > 0 con p_Holm ≤ 0,05 (con control).
- **Refutación:** que O1 sea ≈ 0 o negativo en ambos instrumentos refuta la lectura "pausa con inventario" como propiedad general: queda como rareza de MNQ.
- **Potencia:** una celda se evalúa solo con ≥ 150 racimos por instrumento (el piso de la grilla fue 300 con 4 contratos de descubrimiento; aquí hay ~1 año). Las que no lleguen se publican con su MDE y **no** cuentan como refutación.
- Todo nulo publica MDE. Se publica el paisaje completo (13 pruebas × 2 instrumentos), sin elegir.

## Diferencias declaradas respecto de MNQ (no se pueden quitar, se declaran)
1. **La release sólo tiene sesiones del contrato líder.** Cada contrato empieza con la historia que la release le da (sin sesiones previas a ser líder): el umbral de zonas necesita 20 sesiones de historia, así que **las primeras 20 sesiones de cada contrato no generan zonas** y se excluyen también del pool de pseudo (pseudos sólo de sesiones con ≥ 20 sesiones previas del mismo contrato en la release).
2. Altura en **ticks** (mismo valor en ticks que en MNQ): ES/NQ tienen otro precio y otra volatilidad en ticks que MNQ. No se reescala por volatilidad (eso sería otra hipótesis, NO MEDIDA).
3. Sin separar descubrimiento/confirmación: **todo el período es réplica fuera de muestra** (otro instrumento). No hay selección de celdas posterior.
4. `sequence` de la release es índice de fila (P-28), no secuencia del exchange: el footprint usa bid/ask del tick, como en NT8.

## NO MEDIDO / no se hará acá
P&L, costos, otras celdas, escalado por volatilidad, otros instrumentos (YM, RTY), interacción O1 × compresión.

## Enmienda 1 (escrita antes de correr; resultados de ES y NQ ya conocidos) — MNQ y MES sobre la release canónica
Se agregan dos corridas **con las mismas 7 celdas y el mismo criterio** (≥5/7 para O5, ≥4/6 para O1, mínimo 150 racimos):
- **MNQ canónico:** los resultados originales de MNQ salieron de exports sin sanear (descubrimiento 09-25…06-26, confirmación 09-26/12-26). Esto verifica si **sobreviven a los datos saneados de la release** (control de integridad de datos, no evidencia nueva de mecanismo). Refutación: que O1 caiga a ≈ 0 o cambie de signo en ≥ 3 de las 6 celdas largas.
- **MES:** réplica del mismo subyacente que ES con otro tamaño de contrato y otros participantes; **no cuenta como instrumento independiente de ES** en el criterio de réplica (se publica aparte).
- Holm por instrumento, paisaje completo publicado. Ninguna decisión posterior depende de elegir entre estas corridas.
