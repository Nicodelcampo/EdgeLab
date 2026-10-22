# Catálogo de datos de EdgeLab (empezar acá)

Todo lo que hay en Kaggle (cuenta `nicolasbuttaro`), inventariado: qué datasets existen, qué contiene cada archivo, qué contratos y fechas cubre, cuándo hay rolls, qué sesiones tienen liquidez, qué días faltan y dónde dos fuentes se contradicen. **Antes de bajar o usar un dato, consultá acá.**

## Qué usar (tres archivos, en este orden)
1. `DATASETS_POR_INSTRUMENTO.md`: qué datasets adjuntar a un kernel para cada instrumento.
2. `edgelab_data.py` + `RESOLVER.json`: **la única puerta de entrada** (una fuente por sesión, sin holdout, con fuente alternativa consistente si falta un primario; `python edgelab_data.py INST DESDE HASTA` lista lo que hay que adjuntar).
3. `RESOLVER_STATUS.md`: lo que el resolver referencia y **todavía no existe en Kaggle** (qué hay que subir).

## Regla de oro
**Antes de analizar, usá solo lo aprobado en `CURATED.md`.** Si necesitás algo que no figura, mirá `REEXPORT.md`. Las reglas son las mismas para todos los instrumentos y están en `tools/data_curate.py`.

## Cómo encontrar un dato (30 segundos)
```bash
python tools/data_find.py --list                                   # qué instrumentos hay y su cobertura
python tools/data_find.py --instrument GC --from 2026-01-01 --to 2026-03-31   # contratos, archivos, comandos de descarga, líder, huecos
python tools/kaggle_data.py get nicolasbuttaro/<dataset> <archivo> --out /data/raw/<ACTIVO>   # bajar un archivo (reintenta ante 429)
```
Archivos de este catálogo (todos generados por `tools/data_catalog_build.py`; **no editar a mano**, regenerar):

| Archivo | Para qué |
|---|---|
| `catalog.json` | Fuente de verdad legible por máquina (datasets, archivos de ticks, instrumentos, rolls, huecos, conflictos) |
| `INSTRUMENTS.md` | Por instrumento: contratos y fuentes, serie líder y rolls, liquidez, calendario, conflictos entre fuentes |
| `TICK_FILES.md` | Una fila por archivo de ticks (rango, trades, libro, agresor, anomalías) |
| `DATASETS.md` | Los datasets de Kaggle, su tipo, tamaño, privacidad y README |
| `CURATED.md` / `curated.json` | **Qué datos usar:** veredicto por instrumento, rangos aprobados, fuente primaria por contrato y rol de cada dataset (reglas fijas en `tools/data_curate.py`) |
| `REEXPORT.md` | **Qué hay que re-exportar o re-subir** (contratos faltantes, sesiones faltantes, archivos vacíos, fuentes en conflicto, cobertura corta) |
| `sessions.json` | Una fila por sesión elegible (fuente elegida, volumen, minutos, banderas) |
| `ISSUES.md` | Problemas conocidos y reglas de uso (léelo antes de elegir una fuente) |

## Convenciones de los ticks (comunes a los archivos canónicos)
- Columnas: `ts_utc_ns` (UTC en ns), `price_ticks`, `bid_ticks`, `ask_ticks` (enteros en ticks: precio = valor × tamaño de tick), `volume`, `aggressor` (`buy`/`sell`/`unclassified`), `tick_type` (`trade` y otros), `contract` (p. ej. `GC 08-26`), `sequence`, `source_row`. Solo se usan filas `trade`.
- **Fecha de trading CME:** la sesión va de 17:00 a 16:00 CT; el tick pertenece a la fecha en que cierra la sesión (se corre 7 h hacia adelante en hora de Chicago). Una barra se etiqueta con su instante de **cierre** (convención NinjaTrader).
- **Contrato líder:** el de mayor volumen en la sesión completa **anterior**; avanza y no retrocede; sin ajuste de precios (la diferencia entre contratos en el roll es el diferencial de calendario). Una sesión es **elegible** si su volumen ≥ 50 % de la mediana de ese contrato como líder.
- Los archivos `*-preholdout` están cortados en `2026-06-30T22:00Z` y suelen ser «rebanadas parciales» de cada contrato (no cubren toda su vida).

## Custodia
- **Holdout (HOLDOUT-A4, único para todos los activos y L2): sesiones de trading desde 2026-10-01 (`edgelab/holdout.py`). No leer.** Todo lo anterior es desarrollo. Desde el 2026-10-22 el RESOLVER sale del release canónico `edgelab-liquid-ticks-20261014` (ver `RESOLVER_STATUS.md`).
- Los ticks de NinjaTrader/CME se mantienen **privados**. `ABSTAIN_LICENSE` se levantó el 2026-10-05 sólo para compartir con gonzaloescobar (ver `docs/decisions/DECISION_20261005_RESEARCH_V2_LICENCIA.md`). `mnq-parquet` verificado privado el 2026-10-05; `mnq-tick-data` no existe en la cuenta.

## Regenerar el catálogo
```bash
python tools/data_inventory.py --out /data/catalog        # lista y escanea cada parquet de ticks (reanuda; usa copias locales si existen)
python tools/data_catalog_build.py --scan-root /data/catalog --out docs/data_catalog
python tools/data_curate.py                                  # veredictos, rangos aprobados, roles y lista de re-exportación
```
El escaneo por sesión (`scan/…json`) queda además en el dataset privado `nicolasbuttaro/edgelab-data-catalog` (minutos por sesión, trades, volumen).

## Lanzamientos con manifiesto (2026-10-12)
`tools/kaggle_launch.py` registra, en `docs/data_catalog/launches/<kernel>.json`, la versión de cada dataset adjuntado y los bytes de cada archivo que el resolver eligió (primarios o alternativas), y copia el script inyectando `EDGELAB_LAUNCH_MANIFEST`. `edgelab_data.check_inputs` (llamado por `load_m1`/`load_ticks`) llama a `verify_launch_manifest`: si un archivo montado no existe o tiene otro tamaño, el kernel falla en segundos con la lista exacta. `_path` falla ante dos archivos con el mismo nombre en un dataset (no elige por nombre). Corridas locales (sin manifiesto) no cambian.
Límites: el manifiesto fija tamaños, no SHA256 (la API de listado no los da); Kaggle adjunta la versión vigente al lanzar, por eso se guardan las versiones para auditar.
