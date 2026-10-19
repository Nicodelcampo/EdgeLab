# GC exact4 — código, control reportado y cinco perfiles efectivos

**Preparado y probado en nube · no edge, no censo de febrero ni integración visual terminada.** Nico aportó configuración actual después del primer traspaso077. No es preciso que Claude rediseñe el detector: está listo en tools.

## Control C0

Capa `GC_04-26_202602_25T_HFT__nq__n4__precio`, febrero2026, 1.459zonas **reportadas por Claude/Nico, no recontadas aquí**. Comando: `--asset GC_04-26_202602_25T_HFT --conf precio --escala 3.51 --familia nq --nmin 4`.

Fuente `tools/escalonadas_det.py`, blob `bcf4fce0476c0570712f1b08b5a081b93c80685c`: parámetros de familiaNQ y escala3,51 reproducen exactamente escalón49, pull25, confirmación28. w1, gap30, nmin4, total_min0/step_min0. Duración usa sentinel1000000 en código, descrito por local como sin tope práctico; se conserva sentinel en todas las variantes, no se multiplica silenciosamente. C0 NO es cuatro exactos: mínimo +backfill +crecimiento.

Bundle privado/candles febrero no disponibles acá. Su hash y paridad/censo siguen pendientes. `source_sha256` del registro es hash del REPORTE DE PARÁMETROS, explícitamente NO hash del bundle. No se presenta como captura independiente. Bar25T_HFT reportado; comprobar grano/origen real antes de aplicar sobre otro feed.

## Parámetros efectivos fijados para QA target-free

Todos: w1, confirmación por precio28ticks, total_min0/step_min0, sin pendiente mínima. No sweep de w/disparo/grano; mismas fechas/barras verificadas del control.

|Perfil|Gap máximo velas|Escalón máximo ticks|Retroceso mínimo ticks|Conteo/lifecycle|
|---|---:|---:|---:|---|
|C0 actual|30|49|25|Mínimo4 original, no sustituido|
|C1 exact4|30|49|25|Cuatro exactos, bloques disjuntos|
|C2 exact4 densas|23|49|19|Cuatro exactos|
|C3 exact4 separadas|45|49|38|Cuatro exactos|
|C4 exact4 planas|30|25|25|Cuatro exactos|

Redondeo de propuestas half-up ya declarado077. Cinco hashes diferentes, ningún alias. Baseline igual salvo lifecycle exact4. C4 puede perder señales por geometría estricta; C2 no garantiza más detecciones. Se comparan frecuencia/cobertura/juicios ciegos, no P&L.

## Implementación disponible

- `tools/escalonadas_exact4.py`: núcleo puro Python, ticks enteros, OHLC cerradas. Emite sólo al confirmar4º conocido; nunca con3. Congela exactamente4 miembros/bordes, sin backfill/crecimiento/veto por5º futuro. Rechazo de bloque4 no se rescata al5º; bloques disjuntos, sin ventana2–5. H/L simétricos; reset gap/sesión; EOF no confirma.
- `tools/gc_exact4_variants.py`: resuelve cinco perfiles, no inventa defaults ni hash privado, deduplica antes del censo. C0 debe usar detector original: ABSTAIN en vez de simularlo con nuevo núcleo. Resto permite censo lógico de cerrado, publicaciones raw sólo checks de metadata, nunca certificación financiera.
- `tools/gc_exact4_prepare.py`: captura metadata del layer/serie seleccionado explícitamente y corre censo target-free sobre barras en ticks. JSONL de eventos queda privado; evidencia/configs agregadas aparte. Output nuevo vacío; no sobrescribir baseline.
- `tests/research/test_gc_exact4.py`:26tests, PASAN también desde estructura tools/tests repo. Incluyen4/5/8picos, sin rescate, prefijos, reflexión H/L, EOF/gap/session, cantidad de confirmaciones, velas vs precio, caller no muta eventos, perfilGC49/25/28, resolver/redondeos/sentinel, capturador y no fake publicación.

## Prueba real limitada, sin cambiar parámetros para obtener señales

Con perfil FIJO DE SMOKE MECÁNICO (w1,gap15,step2,pull5,confirm2), dos archivos GC propios20260531/20260615:92/616velas150LAST,0/0zonas exact4. Inputs rehasheados y agregación source-first V2 usada sólo para construir velas/snapshots.

NO es el C0/C1 reportado, ni grano25T, ni febrero, ni dos sesiones CME completas certificadas. Al no emitir zonas, igualdad de prefijos de listas vacías NO ejercita emisión real positiva; los tests sintéticos sí. No se cambiaron thresholds después para obtener verde. No concluye escasez ni edge de configuraciónGC actual. Falta run sobre su bundle/período o barras propias compatibles y paridad.

## Próximo trabajo local mínimo

Fetch HEAD en worktree propia; correr tests. Confirmar hash del bundle/capa seleccionada y grano/meta. No rehacer research ni implementar núcleo exact4 de nuevo. Para integración del visor, usar capas privadas opt-in namespaced y su adaptador existente; no bifurcar visor ni sobrescribir C0. Está PENDIENTE, no hecha.

Censo de perfiles sobre la MISMA población original; C0 con detector original, C1–C4 con nuevo. Adjuntar filas raw de publicación cuando existan; si sólo bundle gráfico, declarar lógico/no disponible, nunca backdating/fill. Para L2 usar sesiones con propio feed/clock/bars auditados; no unir febrero a ejemplos mayo/junio por proximidad de timestamp. Raw/precios/Lucid fuera repo. Muestra útil/clusters antes de economía; manifiesto +OK antes de outcomes.

## Aporte al referente

Exact4 ya tiene implementación y QA; GC conserva control declarado y cuatro alternativas concretas. Falta verificar bundle/paridad y frecuencia útil, no diseño de detector desde cero.
