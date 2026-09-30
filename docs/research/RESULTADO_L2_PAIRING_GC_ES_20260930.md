# GC / ES: continuación del puente L2 — target-free

## Qué se completó
Preflight nuevo instrument-neutral `tools/l2_pairing_preflight.py`, sin usar el tick0.1 de GC para validar ES0.25. Custodia con hashes externos, manifiesto de sesión/contrato/conversión, grilla y tipos enteros, orden mixto, metadata que identifica LAST=2, tape completo ordenado sin nearest/deduplicación/rounding.14 tests PASS; fixture ES sintética end-to-end PASS: no es una corrida con L2 ES real.

Durante QA se verificó la semántica NT8: L1 contiene DAILY_VOLUME=5 y otros registros no trade, preservados para orden/reloj pero NO sumados al tape; metadata identifica LAST=2. El nivel10 de cola desplazada no es un nivel visible extra ni automáticamente un error: la reconstrucción posterior debe aplicar y contar la política canónica P-75/EDGE_RESYNC. No se modificó ningún raw para que pasara.

## Ejecución real, archivos intactos
- GC May31: PASS de identidad/custodia;13.913 prints coinciden en orden, timestamp UTC, precio_tick y volumen.
- GC Junio15: ABSTAIN_ORDERED_TAPE_IDENTITY;92.515 prints en ambas fuentes,5 timestamps distintos,0 diferencias de precio y0 de volumen. Sigue bloqueado; no se reparan timestamps en el auditor.
- PASS de preflight NO es PASS de replay/book/frescura/fills/predicción. Guardas anteriores permanecen y replay en esta fase=NOT_RUN.

## Disponibilidad de fuentes
Se consultó listado My de datasets Kaggle accesibles y archivos del paqueteGC v2. RawL2 GC expuesto: sólo May31 y Junio15. No se encontró rawL2 ES en ese listado; hay ticks ES y el diagnóstico de climas, pero no sustituyen el libro. No afirmar que no exista en la PC o en fuentes no accesibles.

Se preparó `ENTREGA_LOCAL_L2_GC_ES_20260930.md` para enviar primero una sesión ES cronológica del catálogo ya extraído conL1/L2/manifiesto/ticks y referencias, luego3 sesiones para QA (no potencia). El protocolo de contextos ES documenta48 sesiones ES09-26; también documenta solapamientos y grabación incompleta11/08: los archivos no se mezclan ingenuamente. Ese protocolo no autoriza por sí mismo nuevas búsquedas de retornos.

## Futuro de investigación
`BORRADOR_MANIFIESTO_L2_PREDICCION_GC_ES_20260930.md`: propuesta de prueba incremental L2 vs baseline precio en primer cruce prospectivo50% del segundo impulso, conservando todos los intentos. Endpoint/horizonte/censura/split/potencia/costos deben sellarse y recibir OK separado. Zonas C2/ES PLANAS mantienen calibración y requieren su definición operativa aprobada; no trasladar un resultado de espejo a ellas.

**NO MEDIDO:** nuevos efectos económicos/predictivos, parámetros nuevos de zonas, book ES real, sesionesGC adicionales, P&L/fills/costos/potencia. Sin modelos ni labels futuros, sin climas rescatados, C0/visores/holdout intactos. Código,14tests,acta y MEDIDO/NO MEDIDO en mismo commit; rutas/raw/precios fuera repo.
