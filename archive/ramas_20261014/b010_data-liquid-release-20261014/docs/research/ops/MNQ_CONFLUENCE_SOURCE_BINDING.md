# Binding exploratorio de fuente para confluencias MNQ

## Fuente resuelta para continuar, no otra auditoría histórica

Fuente piloto fijada: MNQ_09-26, `nicolasbuttaro/edgelab-ticks-nt8-reexport-20261005` v2, bytes/rows/SHA256/max timestamp tomados de la autorización exploratoria histórica recuperada. No cambiar de versión por «latest». `MNQ_CONFLUENCE_SOURCE_PROBE_PLAN.json` conserva los pins y el hash de esa autorización. Original no disponible, calidad/calendario/liquidez no certificados; los flags históricos no se modifican ni se convierten en un certificado canónico.

Se completó un probe **Kaggle privado únicamente** que recupera esa fuente física y verifica bytes y footer Parquet: presencia/tipos de timestamp, precio, volumen, bid, ask y sequence; rows, rangos temporales y de sequence por row group, null-count declarado. El protocolo usa el mismo descriptor para hash/footer. No deserializa filas de precios, no ejecuta detectores/outcomes ni consume mercado fuera de Kaggle. Rango de tiempo/sequence en footer no demuestra orden dentro de los grupos, validez bid/ask, sesiones completas o calendario.

El chequeo terminó con PASS_PINNED_FOOTER_ONLY_NOT_MARKET_APPROVAL; no volver a ejecutarlo al retomar. El usuario indicó expresamente que los datasets deben darse por resueltos y que no quiere validaciones constantes. No reabrir calidad, selección o certificación histórica como prerrequisito del nuevo estudio. Los riesgos declarados se conservan sin inventar certificaciones. Un PASS del footer sigue `execution_allowed=false` y `source_quality_certified=false`; no selecciona sesiones ni firma aprobación de experimento. Revisión exploratoria y riesgos preservados, no exigir por este paso un original que el usuario ya declaró inexistente.

## Transporte y límites

El MCP devuelve una URL firmada del archivo exacto; se incluye **sólo en el request/notebook privado**. Ni URL ni ticks van al repo. El archivo queda en un directorio temporal de Kaggle, fuera de notebook outputs. El probe tiene Internet para el bootstrap de recuperación; no es el estudio científico offline. Hash antes de abrir footer, no reemplazo de una fuente fallida ni descompresión de fuentes arbitrarias.

Límite de archivo 2 GiB y exact bytes de pin, transferencia cooperativa 600 s con timeout de lectura 60 s, AS 4 GiB/CPU 420 s y timeout solicitado Kaggle 900 s. Scope single process, no cgroup ni protección de un árbol arbitrario. Exceso/retrieval/hash/schema falla, no se declara market-ready. Sólo boot receipt y footer receipt agregados son outputs.

## Pruebas y dependencia

`test_confluence_source_footer.py` y `test_confluence_source_package.py` cubren pins incorrectos, cuotas faltantes, holdout antes de acceso, paths/rows, URL exacta por host y file, privacidad y ejecución real del bootstrap sobre un Parquet **inventado**. PyArrow es la dependencia opcional `bridge` del proyecto; las pruebas Arrow se omiten si no está instalado, no se contabilizan como PASS en ese entorno. Las pruebas locales de este hito se ejecutaron con PyArrow 19.0.1, instalado en el venv de tests separado; no se cambiaron locks del proyecto ni jobs activos.

## Próximo procesamiento

El lector debe reutilizar las fuentes/sesiones exploratorias aprobadas; documentar targets/formation/otras reservas es configuración del experimento, no una nueva auditoría de dataset. Sólo se mantienen límites de acceso, holdout y comprobaciones mínimas de formato indispensables para procesar filas dentro de Kaggle. No leer y filtrar después un contrato entero para saltar reservas. Warmup AVZ mantiene lookback/min_samples; BT2A mantiene AbsorptionLookback/MinHistoryBuckets. Ventanas sin calibración son UNKNOWN, no negativos ni ausencia de zona.

Para escalar se debe conservar estado entre bloques: barras residuales y desempates NT8 del footprint TOTAL, historia por sesión/bucket AVZ, ventana/historia de BT2A, lifecycle e historia racimo. Cortar el array y reiniciar cada detector por shard cambia el indicador; no es una optimización equivalente. El piloto real y el estudio científico todavía no están lanzados por este preflight.
