# Cobertura solicitada y QA parcial de ticks — 2026-10-10

**BLOCKED para research causal.** No se emite certificado de saneamiento, liquidez,
continuidad upstream ni ausencia de sesgo. Continuación de la QA de barras #72;
no modifica datasets, máscaras, ledger ni resultados congelados anteriores.

## Alcance real

Catálogo v15 y agregados v1 ya fijados; manifest/resolver SHA externos anteriores
conservados. Se proyectaron exclusivamente identidad y timestamp de los dos
archivos 1s: 25.843.175 filas, sin deserializar columnas de precio para cobertura.
Inventario completo de 457 fechas por instrumento, 914 registros, desde
2025-07-01 hasta 2026-09-30. Holdout desde trade-date 2026-10-01 intacto.

| Diagnóstico | ES | NQ |
|---|---:|---:|
| Materializadas, no certificadas | 243 | 278 |
| Excluidas por catálogo, ausentes del resolver | 91 | 55 |
| Rechazadas explícitamente por resolver | 5 | 0 |
| No observadas, calendario sin revisar | 118 | 124 |
| De ellas, lunes–viernes | 19 | 27 |
| Fuera del span observado del catálogo, todas las clases | 22 | 36 |
| Sesiones materializadas con salvedad de fuente | 58 | 91 |
| Minutos nominales sin observación, actividad UNKNOWN | 15.442 | 16.390 |
| Intervalos nominales sin observación | 285 | 283 |
| Máximo intervalo nominal sin observación, minutos | 300 | 244 |
| Minutos observados en banda de reloj 16:00–17:00 Chicago | 7 | 547 |
| Sesiones con observación en esa banda | 4 | 16 |

Primera/última sesión materializada: ES 2025-07-18..2026-09-25;
NQ 2025-08-04..2026-09-25. Los números de exclusiones/no observación son
**fechas**, no una estimación de sesiones de mercado que deberían haber abierto.
Los días lunes–viernes pueden incluir feriados: NO son 46 pérdidas demostradas.

Los bins 17:00→17:00 Chicago son una convención de etiqueta, NO calendario de
trading: incluyen mantenimiento/feriados. Ausencia de barra nunca prueba cero
trades ni pérdida de ticks. La banda 16:00→17:00 requiere reconciliar horario
histórico de la bolsa, DST, timestamps y fuente; no se corrigió desplazando relojes
ni se concluyó corrupción. No usar anuncios de 2012 o horarios BrokerTec como
calendario ES/NQ de 2025/26. Inventario diario e intervalos completos quedan
privados/locales; el reporte público sólo contiene conteos, procedencia y hashes.

## QA cruda independiente, parcial

Dos fuentes canonical_tick_v1 de `edgelab-nt8-historical-missing-20261001/1`:
ES_09-26_ticks_ext.parquet (12.986.371 filas) y
NQ_09-26_ticks_ext.parquet (5.773.916 filas). SHA/bytes/rows reconciliados con
AUDIT_MANIFEST, files.sha256 y catálogo. Los checksums publicados demuestran
consistencia de procedencia, NO autenticación ni autoridad independiente.

**18.760.287 ticks comprobados, PASS_RAW_STRUCTURE_ONLY en ambos.** Sin nulos
requeridos, retrocesos de timestamp, secuencias locales no crecientes, duplicados
exactos de identidad source_file+source_row, precios/cotizaciones no positivos,
book cruzado o volumen de trade no positivo. Reconciliados trades/volumen de
8 sesiones primarias ES y 1 NQ contra el resolver. El lote incluye días/contratos
no líderes: su auditoría estructural no los habilita para análisis.

- Timestamp repetido legítimo: ES 9.565.330, NQ 2.735.827. No se deduplicó.
- Book locked: ES 37, NQ 29. Declarado como warning, no borrado.
- Agresor no clasificado: ES 5, NQ 2. No imputado.
- ts_utc_ns y ts_local_ns iguales en ambas fuentes: observable, **no demuestra**
  que la zona original sea correcta. Verificación independiente pendiente.
- La secuencia local continua NO prueba continuidad del exchange/proveedor.
- La columna integer price_ticks NO recupera ni prueba la precisión del texto
  original ni la procedencia del agresor/book, que siguen pendientes.

**2 de 18 archivos primarios auditados; faltan 16.** No se extrapola este PASS
al dataset completo. Calendario, resolución de fuentes en conflicto, máscara
causal, todos los challengers D-1 y límites de liquidez revisados siguen pendientes.

## Integración y validación

APIs y CLIs documentados en [Componente Kaggle](../COMPONENT_KAGGLE.md).
`load_research_bars` exige ahora una declaración revisada para **cada fecha** de
la ventana, dentro del certificado externo fijado; desconocidos, sesiones abiertas
sin materializar y cierres contradichos bloquean antes de hash/lectura de precios.
El guard comprueba consistencia de declaraciones, no autentica al aprobador ni
carga/verifica por sí mismo el calendario referenciado. Diagnósticos no son certificados.

368 tests CPU + 8 subtests, cero fallos/skips; wheel y core-only probados fuera del
checkout, smoke funcional con datos inventados y agregado al CI CPU. El verificador
de navegación pasa. No se generaron trials, outcomes, fills/P&L ni promociones.
No se implementó ccbus ni el agente autónomo; loaders legacy siguen opt-in/no global.

[Evidencia estructurada](KAGGLE_COVERAGE_RAW_20261010.json) ·
[QA previa de barras](KAGGLE_DATA_QUALITY_20261010.md).
