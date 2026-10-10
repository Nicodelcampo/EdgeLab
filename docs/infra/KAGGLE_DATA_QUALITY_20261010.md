# Auditoría Kaggle — estructura de barras no equivale a saneamiento/liquidez

## Dictamen

**BLOCKED_FOR_CAUSAL_RESEARCH_NOT_SANITIZED_LIQUID_CERTIFIED**.
No se certifica el dataset ni se habilita research. El agregado técnico puede conservarse
para QA/reconciliación, pero no sustituye certificación de ticks ni elegibilidad causal.

## Comprobado sobre el dataset publicado

Fuente privada fija: `nicolasbuttaro/edgelab-es-nq-aggregates-20261009/1`; sólo seis
primarios `store/`, nunca las copias `store/output/`. Manifest fijado externamente
`71862f0d2201cddc69db4ee7ba2cb45cb2b65a69980f99377500b54137e1e2c2`.
Catálogo `edgelab-data-catalog/15`: bytes de loader/resolver coinciden con pins históricos.

Auditoría acotada de **27.996.603 filas de barras**, 521 sesiones instrumento-fecha,
1s/30s/60s; checks de hashes, tipos/valores, OHLC, orden/duplicados, identidad,
tiempo/disponibilidad, descomposición de volumen, signo y totales entre frecuencias
y catálogo pasaron. Reducción independiente Arrow reprodujo trades/volumen.
Cero cotizaciones cruzadas, fraccionarias o no positivas en las últimas quotes de las barras.
Existen quotes locked (bid=ask): se reportan, no se corrigen ni se confunden con cruzadas.
No se interpretan retornos, fills, estrategias ni P&L. Los valores de precios no se
incluyen en el reporte público. Los archivos privados y totales de sesión quedan fuera del repo.

El profiler genérico no interpretó Parquet/JSON anidado: sus errores de formato se
registraron, y se usó explícitamente perfilado Arrow por schema/footer y batches
acotados. No se trataron esos errores como corrupción de mercado.

El inventario v15 también reporta cero desorden/libro cruzado/libro no positivo y
cero sesiones post-holdout en los 18 archivos primarios seleccionados. Es **evidencia
declarada del inventario**, no una nueva auditoría independiente de filas o hashes raw.

## Lo que impide llamarlos sanos y líquidos

- ES y NQ tienen veredicto **CON_SALVEDADES** en el resolver. 58 sesiones ES y 91 NQ
  aprobadas cargan `fuente_en_conflicto`: **149 en total**, sin adjudicación independiente.
- Las reglas de elegibilidad emplean medianas de toda la muestra y minutos de la
  sesión actual. Son filtro retrospectivo de disponibilidad, no permiso conocido en D-1.
- La selección declara volumen de la sesión anterior y los cinco rolls por instrumento
  son consistentes en fechas/volúmenes/avance de vencimiento. Esto NO reconstruye
  independientemente todo el calendario completo ni todos los challengers.
- No se encontraron certificados de saneamiento tick-level ni límites absolutos
  aprobados por instrumento para volumen y spread. Ser líder relativo no garantiza
  spread, tamaño/capacidad ni integridad de la fuente.
- Agregar a 1s/30s/60s puede ocultar ticks duplicados, secuencia errónea o quotes
  intrabar cruzadas. El PASS de barras no acredita esas propiedades de ticks.

## Contención implementada

`research_access` rechaza el resolver v15 para research causal. No hay flag de bypass.
Un artefacto futuro necesita política causal estructurada, revisión y hashes externos
fijados, contrato D-1 completo, límites de liquidez aprobados y resolución de salvedades.
El lector de research valida **todas las sesiones del archivo** antes de leer precios:
autorizar sólo una ventana no permite leer el resto (incluido D2) para filtrar después.

La autoridad de campaña y el auditor independiente siguen siendo externos; el API
valida consistencia, no autentica al autor de un JSON. Fuente inmutable, footer veraz
 y pins revisados son requisitos. No es un sandbox contra footers falsos o writers.
El holdout formal desde 2026-10-01 permaneció sin deserializar. Tampoco se generaron
certificados, umbrales arbitrarios, aprobaciones, trials o registros nuevos de éxito.

## Siguiente saneamiento, sin alterar historia

1. Auditar/adjudicar conflictos por identidad y procedencia; no elegir la fuente
   de mejor resultado ni deduplicar por igualdad económica.
2. Reconstruir selección D-1 de todos los contratos con calendario/completitud
   demostrados y máscara causal, nunca mediana futura.
3. Fijar límites de volumen/spread por instrumento antes de medir resultados;
   profundidad/tamaño y costos requieren evidencia adicional.
4. Emitir evidencia revisada y un nuevo catálogo/artefacto versionado; no relabelar
   los agregados v1 ni reescribir sus manifests/ledgers históricos.

[Evidencia técnica](KAGGLE_DATA_QUALITY_20261010.json) · [Contrato del componente](../COMPONENT_KAGGLE.md).

## Continuación: cobertura y QA parcial cruda

La auditoría posterior declara toda la ventana solicitada y comprueba dos de los
18 archivos primarios. No sustituye esta evidencia histórica ni certifica el resto.
Ver [cobertura y lote crudo](KAGGLE_COVERAGE_RAW_20261010.md).
