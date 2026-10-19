# Entrada 077 — Auditor/nube → Claude local: MNQ L2 y variantes GC escalonadas

**Pedido directo de Nico, 30/09/2026.** Nico entrega el ZIP a Claude local. Preparar y probar varias configuraciones GC; incluir una con **exactamente cuatro picos por zona y disparo SIEMPRE en el cuarto**. Se conserva su requisito de suficiente muestra para potencia. Esta orden cubre preparación/QA/censo target-free; NO nuevos retornos, costos, MFE/MAE ni búsqueda de mejor P&L.

## Referencias byte-identificadas (no copiar código del mensaje)

HEAD de referencia `e9fa30275e72760cb6f02376566d3ac774959bed`, rama de integración `foundation/f0b-compatibility-probe`; resolver HEAD remoto actual antes de escribir.

- `tools/mnq_l2_prepare_v2.py` · blob `5ad9fcf548fe8df5746c7fa50032e11c4ac4d546`.
- `docs/research/HANDOFF_MNQ_L2_V2_DIAGNOSTICO_UNA_SESION_20260930.md` · blob `559a6e3fafd608bff934fbcbefd0a618b532a15e`.
- `tools/escalonadas_det.py` · blob `bcf4fce0476c0570712f1b08b5a081b93c80685c`.
- `tools/peaks_rule.py` · blob `20897247948dfac541dc98a6b91171fdaf734f19`.
- Acta primera sesión MNQ: `docs/research/RESULTADO_MNQ_ESCALONADAS_L2_PRIMERA_SESION_TARGETFREE_20260930.md`.
- Muestra/potencia: `docs/research/PLAN_MNQ_GC_ESCALONADAS_MUESTRA_Y_POTENCIA_20260930.md`.

## Prioridad 1 — MNQ: una sola ejecución, el resto lo hace nube

1. Recibir ZIP `MNQ_L2_V2_DIAGNOSTICO_Y_PLAN_GC.zip` de Nico; preferir blobs ya publicados para evitar divergencia de copia. Worktree propia, un escritor, root/HEAD/status, venv/lock del repo, un solo proceso pesado (PC16GB). Sin cambiar raw, detector, climas ni visor.
2. V1 quedó congelado y NO es GO para52. En 20260629 se reproducen31 señales, pero26 fuera top10 +1 sin libro:27 máscaras desconocidas. Disponibilidad V1 no certificada: reconocer fin de grupo exige la fila siguiente observada. No tratar null como false.
3. Ejecutar tests V2 y luego UNA sesión20260629 con nuevo output vacío y flag explícito `--ack-diagnostic-v2`, según handoff byte-referenciado arriba. No necesita diseño ni research de Claude. Nico pidió transmitir estos requisitos; la fase financiera sigue sin autorización.
4. Pasar `MNQ_targetfree_para_nube.zip` generado, evidence y tiempo real de ejecución a Nico/nube; si falla, traceback completo y evidence existente. No cambiar semántica/tolerancias para verde. No arrancar52 automáticamente.
5. Nube revisará snapshot vs publicación, gates, edad, cobertura antes/en pico/al confirmar, identidad de señales y densidad. `pico_pre_observation` es conocido antes/al extremo; `pico_observation` después de cerrar su grupo; la ASOCIACIÓN a la zona se conoce al detectar, no en el pico. No retrotraer fills ni señal. No rescatar climas STOP.

## Prioridad 2 — GC: recuperar la CONFIGURACIÓN ACTUAL real antes de cambiarla

**Límite de acceso:** no hay configuración específica GC escalonadas versionada ni bundle `peaks_det` privado disponible en nube. El repo ofrece defaults PLANAS/EMPINADAS y familia `nq`, pero eso NO prueba qué eligió Nico en su PC. NO inventar que el default es su configuración actual.

Local debe leer la URL/variante actualmente usada (`?det=...`), bundle seleccionado en `viewer/nt8_bridge/bundles/peaks_det/<GC asset>...json`, `parametros`, `variante`, confirmación/disparo, familia, asset/bar_series/tick_size y comando real de generación si existe. Capturar parámetros efectivos ya redondeados, no sólo factor de escala. Revisar `--w`, `--nmin`, `--familia nq`, `--escala` y `--conf` del código referenciado. La escala multiplica también distancia de confirmación. No generar una corrida a partir de campos que no estén resueltos.

Publicar manifest de metadatos/hash (sin velas/precios ni bundles privados) con `asset`, contrato/período, tipo y tamaño de barra, tick_size, familia, w,max_gap,max_step,min_pull,nmin,dmax,total_min,step_min, modo y ticks de confirmación, fuente/blob/hash. **C0 = ESA configuración sin cambios.** Si no se puede identificar qué bundle vio Nico, abstenerse para C0 y pedirle URL/nombre; las otras siguen propuestas, no atribuirlas a su configuración.

## Prioridad 3 — cinco configuraciones, censo común sin retornos

Todas parten de C0 identificado. Misma barra, fechas, reloj y población LAST propios; ambos lados H/L separados. No producto cartesiano ni probar configuraciones a demanda según resultados. Parámetros numéricos efectivos de cada variante se escriben y hashean ANTES del censo. Regla de redondeo de propuesta: `round_half_up(x)=floor(x+0.5)` para magnitudes no negativas; mínimo1 para gap/pull; máximo de escalón puede ser0. Si baseline no tiene duración máxima, conservar ese modo, no fabricar límite con un sentinel.

| ID | Configuración | Cambios respecto de C0 |
|---|---|---|
| C0_ACTUAL | Actual de Nico, control geométrico | Ninguno; conserva su regla de conteo/lifecycle. Identidad con bundle original. |
| C1_EXACT4 | EXACTAMENTE4, propuesta principal | Geometría de C0; membresía/lifecycle exact4; primera confirmación causal del4º. Sin crecimiento ni backfill extra. |
| C2_EXACT4_DENSAS | Cuatro picos más cercanos, retrocesos menores | C1; max_gap=round(0,75×C0), min_pull=round(0,75×C0). Resto igual. Es propuesta, no garantía de más señales. |
| C3_EXACT4_SEPARADAS | Cuatro picos más separados, retrocesos mayores | C1; max_gap=round(1,5×C0), min_pull=round(1,5×C0); si C0 tiene duración máxima finita, dmax=round(1,5×C0). Resto igual. |
| C4_EXACT4_PLANAS | Cuatro picos con menor escalón | C1; max_step=round(0,5×C0), total_min=0,step_min=0. Pull/gap/disparo de C0. Rotular familia plana nueva si C0 era empinada. |

w y distancia de confirmación no se barren en este lote; se conservan valores efectivos C0. Si los redondeos producen perfiles idénticos, deduplicar ANTES del censo y registrar alias, no contar como evidencia adicional. Son configuraciones GC nuevas sobre su baseline; no usar ES×12,42/MNQ por comodidad.

## Contrato EXACT4 — no basta con `--nmin 4`

**Problema del código existente:** nmin es mínimo; `R.backfill` puede añadir miembros y `full` reconstruye toda la serie futura. `--nmin 4` por sí solo NO garantiza cuatro miembros ni zona que deje de crecer. El nuevo modo se implementa aislado, con tests, sin cambiar defaults existentes.

- Cuatro picos distintos DEL MISMO LADO, elegibles por las reglas de C0, en orden causal y una secuencia activa; no contar repetidas confirmaciones del mismo pico. Todos los miembros de la zona deben ser esos cuatro: sin picos retrospectivamente añadidos ni quinto miembro visual.
- Nada dispara con1,2,3. Al quedar conocido/confirmado el4º, evaluar el prefijo de CUATRO contra filtros; si pasa, emitir UNA señal y congelar sus cuatro miembros, bordes geométricos y punto de detección. El evento se asocia al4º, no al5º.
- Disparo significa **primera confirmación causal del cuarto con el modo/distancia declarados**. No afirmar conocimiento en el trade exacto del extremo usando su futura reversión. Guardar `pico4_row`, `pico4_known_row`, `signal_available_row` y precio de disparo teórico, sin inferir fill.
- Si los cuatro no pasan filtros al quedar confirmado el cuarto, ese bloque no se rescata disparando al quinto. Registrar rechazo; continuar con un bloque nuevo de cuatro, sin ventana deslizante2–5 que reutilice los mismos picos. Reset de bloque tras emisión/rechazo; no pérdida silenciosa de candidatos.
- Un quinto pico posterior NO modifica ni elimina la zona emitida; puede iniciar el siguiente bloque, pero no crear instantáneamente otra zona2–5. No usar futuro para exigir que la serie jamás llegue a5; la regla es **cuatro miembros por zona emitida**, no «toda serie futura tiene longitud4».
- Ruptura/gap/session/roll y candidatos incompletos se cierran con causas declaradas. La familia actual puede tener backfill y lifecycle diferentes: C0 se conserva, exact4 es una hipótesis nueva, no falsa paridad.
- En modo velas, confirmar el4º exige esperar w velas; en precio, esperar distancia declarada y publicación observable. Si Nico quiere otro modo para ese lote, requiere registrar cambio antes, no anticiparlo.

## Tests mínimos EXACT4 y entrega

1. Tres picos:0señales; cuatro válidos:1señal, len(members)=4 y índice de disparo4.
2. Añadir5º,6º,7º: zona1 byte-invariante, sin redisparo2–5; ocho válidos pueden producir segundo bloque independiente.
3. Cuarto inválido: no rescate al5º. Mismos picos confirmados dos veces no cuentan doble.
4. Invariancia por prefijos; backfill tentador no añade5º ni cambia miembros; H/L simétricos.
5. Múltiples velas en mismo timestamp y EOF: publicación observada, no backdating ni fill inventado. Reset por gap/sesión/roll.
6. Detector↔visor: exactamente4 marcadores y disparo ligado al4º, sin dibujar5º como parte de zona. No bifurcar visor canónico; nuevas capas privadas namespaced y opt-in.

Entrega mínima target-free: JSON de configs efectivos+hashes, tests, conteos por sesión/hora/lado, rechazos, clusters/solapamientos y soporte L2 de pico/confirmación. Comparar perfiles sólo por frecuencia, cobertura y juicio geométrico ciego; NO elegir mejor retorno. Reportar fracción de señales observables y balance de estados (true/false/unknown), no convertir ausencia top10 en no-defensa. Si sólo existe ejemplo corto GC, llamarlo smoke y pedir varias sesiones; no proclamar potencia.

La nube continúa lectura/análisis. Antes de medir utilidad financiera: congelar población/configs, mínima mejora económicamente útil, costos propios GC y MNQ, clusters y MDE/potencia80%/error familiar5% acordados; manifiesto + OK de Nico. Holdout forward oct+ intacto. No raw/precios/Lucid al repo; evidencia y MEDIDO/NO MEDIDO en mismo commit.

## Respuesta al canal

Responder con commit completo, path+blob de config actual recuperada, estado de MNQ V2 y tablas target-free. Si bloqueado por config/datos: declarar exactamente el faltante, no usar defaults como sustituto. Un solo proceso pesado; no gastar créditos en rehacer el research ya escrito.

## Aporte al referente

Nico agrega GC y una regla exact4 causal; se prepara una comparación pequeña con muestra observable, sin confundir marcas abundantes con potencia ni con edge neto.


## Actualización posterior — Entrada078

MNQV2 primera sesión recibida/auditada; controlGCreportado e identificado; núcleo exact4 y26tests ya listos en nube. Las tareas de reimplementar exact4/replicar primera sesión quedan SUPERADAS por `ENTRADA_078_GC_EXACT4_LISTO_MNQ_V2_AUDITADO_20260930.md` y su handoff. BundleGC/hash/censo/paridad/visor todavía pendientes; nada financiero aprobado.
