# Selección ES del catálogo v15: roll prematuro

**Estado: selección no válida para research; no se reescribe v15 ni se certifica una alternativa.**

## Hallazgo y alcance

El `catalog.json` fijado en la auditoría declara ES_03-26 como líder desde
2025-10-06 hasta 2026-03-16. La evidencia del cambio usa `previous_session`
2025-10-05, una fecha dominical, y volumen viejo/nuevo 1/2. Los dos valores
concuerdan con los archivos crudos históricos v1: no es un error de suma del
agregado. Esa fecha con microvolumen no demuestra una sesión completa válida.
El calendario relevante y el origen de esos eventos siguen sin verificar.

La revisión adicional de las dos fuentes ya auditadas encuentra 52 fechas
compartidas entre 2025-10-06 y 2025-12-09; diciembre tiene mayor volumen que
marzo en 50 de ellas. En las sesiones del 6, 7 y 10 de octubre el contrato de
diciembre continúa presente con actividad sustancial y el de marzo es muy fino.
Esto descarta explicar toda la exclusión del período como simple ausencia del
contrato cercano en los archivos. **No demuestra completitud ni liquidez aprobada.**
Las 52 fechas son observaciones, no 52 sesiones de intercambio certificadas.

Un avance monotónico de la cadena iniciado por microvolumen puede mantener el
contrato lejano y provocar exclusiones posteriores aun existiendo ticks del
contrato cercano. El resolver v15 y el agregado derivado no se reparan pasando
un certificado PASS ni eliminando fines de semana por heurística.

## Reproducción y custodia

Inputs inmutables y SHA externos en `edgelab/kaggle/discovery.json`:

- `nicolasbuttaro/edgelab-data-catalog/15`: catalog.json y RESOLVER.json.
- `nicolasbuttaro/edgelab-nt8-historical-missing-20261001/1`:
  ES_12-25_ticks_ext.parquet y ES_03-26_ticks_ext.parquet.

Reproducir con `audit_canonical_tick_file(..., include_clock_diagnostics=True)`
por archivo, usando SHA/bytes/rows del inventario, y comparar `totals[date].volume`
privados. Consultar `catalog.instruments.ES.rolls` y `leader_segments`.
No publicar precios ni la tabla diaria privada. No hubo lectura de holdout,
reescritura, clipping, deduplicación ni outcomes económicos.

## Resolución necesaria

1. Verificar calendario, zona horaria upstream y completitud de cada sesión
   candidata, incluida la anomalía dominical; ausencia no equivale a cero.
2. Reconstruir la selección con todos los contratos elegibles de la **sesión
   previa completa**, límites ex-ante y fuentes explícitas. El builder causal
   existente exige `complete_session`; no inventar esa bandera desde row-counts.
3. Comparar el nuevo régimen con v15, mantener el inventario de fechas excluidas
   y resolver también máscaras retrospectivas/conflictos NQ.
4. Publicar nuevo resolver y agregados versionados, repetir QA y obtener evidencia
   revisada. Conservar v15/aggregate v1 como historia técnica, no como research listo.

## Rastreo adicional hasta el evento crudo

La inspección dirigida de los dos archivos fijados confirma **un evento por
contrato** en 2025-10-05, domingo al mediodía Chicago, anterior a 17:00. Los
volúmenes suman exactamente 1 y 2; el escaneo histórico del catálogo confirma
independientemente los mismos conteos y cantidades. Se leyeron únicamente
timestamps, volumen e identidad de origen en los row groups que intersectan la
ventana, tras verificar SHA, footer y ausencia de holdout en TODO el archivo.
No se calcularon precios ni outcomes. Identidades/horas exactas quedan privadas.

La referencia oficial cargada de CME para S&P 500/Nasdaq-100 dice 17:00–16:00 CT,
con pausa 16:00–17:00: https://www.cmegroup.com/markets/equities/sp-500-and-nasdaq-100-futures.html
Es evidencia de horario regular, **no el calendario histórico completo ni prueba
de eventos fabricados**. No se sustituye Globex por ClearPort, BrokerTec, trading
floor o settlement schedules. La extracción de la página de feriados no entregó
la tabla histórica específica de Equity Globex; ese vacío sigue declarado.

No se elimina ni desplaza ese evento para forzar el roll correcto. Primero se
necesitan los originales NT8, el conversor/exportador realmente usado, definición
de zona horaria, logs y trazabilidad de `source_row`. Las búsquedas dirigidas en
Box no encontraron originales relevantes; no se afirma que no existan.

[Pedido de reparación y evidencia faltante](KAGGLE_UPSTREAM_REPAIR_20261010.json).
El detalle privado permite ubicar los originales sin publicar ticks ni rutas
locales del usuario. Resolver/aggregate actuales permanecen históricos y BLOCKED.
