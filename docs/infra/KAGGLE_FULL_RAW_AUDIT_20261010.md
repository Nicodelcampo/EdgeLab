# Auditoría estructural completa de fuentes primarias ES/NQ

**BLOCKED: discrepancia horaria/fuentes, calendario y liquidez causal sin resolver.**
Continuación de #73. Se completa la inspección estructural de los 18 archivos
primarios que materializaron el agregado v1; no de todo Kaggle, todos los contratos
alternativos ni la verdad/continuidad del exchange.

## Alcance verificado

- **18/18 archivos, 546.709.478 ticks**, versiones originales del plan conservadas:
  histórico missing v1, extensión Q3 v1, NQ preholdout v6 y reexport v2.
- SHA/bytes/rows contra documentos de checksums publicados y catálogo. Conteo
  independiente con footers reales y hashes recomprobados tras la ejecución.
- **521 sesiones primarias**: trades/volumen raw coinciden con el resolver, cero
  discrepancias. Minutos observados en la banda 16:00–17:00 CT coinciden con las
  barras agregadas en las 521 sesiones. Esto demuestra **consistencia**, no que
  el catálogo o la fuente sean correctos.
- Todos pasan `PASS_RAW_STRUCTURE_ONLY`: cero nulos requeridos, retrocesos de
  tiempo, secuencias locales no crecientes, duplicados exactos source_file+source_row,
  book cruzado, precios/cotizaciones no positivos, volumen trade no positivo,
  identidades/tipos inválidos o precisión temporal fuera de 100 ns.
- 10 rolls declarados: valores old/new D-1 coinciden con al menos una fuente cruda
  auditada; **2 tienen volumen del challenger ambiguo entre fuentes**. No es
  revisión de todos los challengers/calendario completo ni certificación causal.

Warnings preservados: 4.660 books locked y 1.328 agresores sin clasificar.
369.273.599 repeticiones de timestamp se conservaron: igualdad de timestamp no
es criterio de duplicación. Identidad local distinta NO demuestra que sean eventos
upstream distintos. No se deduplicó, interpoló ni reescribió ningún input.
En los 18 archivos, ts_local_ns coincide con ts_utc_ns: no recupera ni acredita
la zona horaria original, y no es una verificación independiente de UTC/DST.

## Discrepancia concreta de NQ septiembre 2026

`nicolasbuttaro/edgelab-ticks-nq-preholdout/6`, archivo
`NQ_09-26_ticks.parquet`, tiene **363.601 trades en la banda 16:00–17:00 Chicago**
en las nueve sesiones primarias seleccionadas de junio, 540 minutos observados.
La alternativa histórica missing v1 NQ_09-26_ticks_ext.parquet no tiene trades en
esa banda en esas nueve sesiones. No se asume por ello que la alternativa sea completa.

Se compararon en orden exacto timestamp UTC, price_ticks, bid_ticks, ask_ticks,
volume y aggressor. Para esa comparación solamente se apartó la banda de reloj
16:00–17:00 de la primaria; los archivos originales y agregados **no cambiaron**:

- **5/9 sesiones**: el resto del contenido ordenado coincide exactamente con la
  alternativa, incluidos timestamps. Un desplazamiento global de una hora no
  explica esa coincidencia y las filas extra posteriores.
- **4/9**: persisten diferencias de cantidad de filas fuera de esa banda.
  Quitar la hora sospechosa o cambiar automáticamente de fuente **no es reparación**.
- Ejemplo 2026-06-17: primaria 574.565 filas, alternativa 488.223; la diferencia
  son 86.342 filas de la banda de reloj. Fuera de ella, los seis campos coinciden
  exactamente en orden. El join por source_file+source_row no tiene identidades
  compartidas: sus namespaces no autentican la misma identidad upstream.

La especificación CME consultada en búsqueda indica mantenimiento regular NQ
16:00–17:00 CT. La carga del sitio no devolvió esa tabla dinámica, ni se obtuvo
calendario histórico completo 2025/26: se registra como referencia a investigar,
**no** como certificado automático del horario de cada fecha. No se aplican
horarios BrokerTec/ClearPort u opciones Micro a estos futuros.
Referencia: [CME NQ contract specs](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html?videoId=6376085766112).

La discrepancia y su causa deben resolverse con procedencia/export original,
calendario aplicable y evidencia reproducible. No se afirmó que esos trades sean
falsos, ni se corrigieron timestamps ciegamente. Se mantiene **cuarentena para
research** de esa combinación exacta de versión y archivo.

## Protección e integración

`research_access.KNOWN_UNRESOLVED_SOURCES` incluye la combinación congelada
anterior. El consumidor protegido comprueba el plan ya fijado y la rechaza **antes
de precios**, aun si un certificado del caller dice PASS. Cambiar la lista requiere
revisión explícita sustentada; no se levanta por relabel automático. Una versión
nueva no recibe autorización sólo por no aparecer en la lista: conserva todas las
guardas de causalidad, fuente, calendario, liquidez y cobertura diaria.

`audit_canonical_tick_file(..., include_clock_diagnostics=True)` y
`tools/audit_kaggle_raw_ticks.py --include-clock-diagnostics` cuentan la banda de
reloj y guardan detalle por fecha **privado**. No la clasifican como cierre verificado.
La reducción diaria usa enteros y límites DST de Chicago; un bitmap exacto por
páginas conserva memoria acotada sin imponer un límite arbitrario de 50M al ID
source_row. No cambia la definición de identidad ni relaja los controles.

375 tests CPU + 8 subtests, sin fallos/skips; wheel/core-only y smoke funcional
sintético fuera del checkout. Pruebas nuevas de DST, suma >int32 sin floats,
IDs dispersos grandes y cuarentena no sustituible por certificados. Evidencia de
validación final en la descripción del PR. Checksums publicados son procedencia,
no autenticación ni autoridad independiente.

## Pendiente, sin cerrar por este PASS

1. Resolver la fuente NQ v6 y las otras salvedades de fuentes del catálogo;
   revisar campañas dependientes sin borrar automáticamente resultados/hipótesis.
2. Calendario histórico ES/NQ por fecha: apertura, mantenimiento, festivos/cierres
   tempranos, DST. Diferenciar ausencia, cero actividad demostrada y falta upstream.
3. Revisar challengers completos D-1, fuente primaria inequívoca, política causal
   de rolls/selección y límites de liquidez aprobados antes del análisis.
4. Evidencia original de timezone, grid y procedencia de quotes/agresor;
   secuencia/identidad upstream cuando exista. Columnas tipadas no restituyen texto
   original o event IDs que no se capturaron.

Los 18 primarios quedan auditados **estructuralmente**, no saneados/certificados.
No quedan pendientes esos 16 archivos primarios del reporte anterior; sí otras
fuentes y las revisiones indicadas. No se abrieron filas holdout, calcularon
outcomes/fills/P&L ni emitieron permisos/trials/promociones. Lectores legacy siguen
sin gate global; trabajo ccbus/agente autónomo fuera de alcance.

[Evidencia resumida sin precios](KAGGLE_FULL_RAW_AUDIT_20261010.json) ·
[Inventario de cobertura previo](KAGGLE_COVERAGE_RAW_20261010.md) ·
[Componente Kaggle](../COMPONENT_KAGGLE.md).
