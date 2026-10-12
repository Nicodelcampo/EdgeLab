# Corridas en Kaggle: qué faltaba y cómo se resolvió (2026-10-09)

**Estado:** `GAPS_IDENTIFIED` → se actualiza al final (sección 4) con lo que se implementó.
**Alcance:** diseñar corridas fácil, que devuelvan exactamente lo esperado, duren lo menos posible y se carguen
solas en el hipocampo del Edge Brain. Reglas que no cambian: KAGGLE_ONLY (los datos de mercado no salen de Kaggle),
holdout HOLDOUT-A1 (sesiones desde 2026-10-01) intocable, EXPLORAR ≠ CONFIRMAR, sin auto-aprobación.

## 1. Lo que ya había

| Pieza | Dónde | Sirve | Límite |
|---|---|---|---|
| `edgelab_data.py` + `RESOLVER.json` | dataset `edgelab-data-catalog` | una fuente por sesión, serie líder, sesiones aprobadas, guarda de holdout, `check_inputs`, `required_files` | `load_ticks` reabre y re-escanea todos los row groups en cada llamada; no hay caché de barras salvo M1 |
| Protocolo de ejecución congelada V1 | rama `infra/kaggle-frozen-execution-v1-20260828` | freeze A/B, attestation, `output.zip` + sha | desactualizado (holdout 2026-07-01, clona con internet, nunca usado por las corridas de octubre) |
| Corridas de octubre (avzgrid, racimo, hftret, brk, vela…) | kernels `edgelab-*` | funcionan; reparto k1…kN por contrato | scripts sueltos: copian funciones, salidas y evidencia distintas en cada una, sin carga al hipocampo |

## 2. Faltantes (iterados)

Primera lista → revisión → lista final. Lo descartado queda anotado con el motivo.

| # | Faltante | Evidencia | Qué hace falta |
|---|---|---|---|
| F1 | **Adjuntar datasets no es confiable** | 2026-10-09: 3 kernels mínimos (`edgelab-probe-mount-a/b/c`) creados con la herramienta MCP `save_notebook` usando `datasetDataSources`, `datasetDataSourcesSetter` y `kernelDataSourcesSetter`: `/kaggle/input` vacío en los tres; `get_notebook_info` no muestra fuentes. La corrida LITCHECK falló 3 veces a los 2-3 s por esto. | Un modo de datos que no dependa del montaje: si no hay montaje, bajar cada archivo dentro de Kaggle desde un plan de descarga (URLs firmadas que da la API, válidas 72 h), verificar bytes contra el catálogo, registrar sha256, guardar en `/tmp` (nunca en outputs). Si el montaje funciona, se usa el montaje. |
| F2 | **No hay armazón único** spec → kernel → salidas | cada corrida reescribe carga, bucle por sesión, bootstrap, attestation | `edgelab/kaggle_harness`: una spec JSON + un módulo de job con dos funciones (`per_session`, `summarize`); el armazón genera un kernel autocontenido y siempre emite las mismas salidas. |
| F3 | **Errores tarde** | los 3 fallos se vieron después de lanzar | preflight: validar la spec localmente (holdout, rango, datasets requeridos vía resolver), test del job con ticks sintéticos, y fallar en segundos en Kaggle con un mensaje que diga qué falta. |
| F4 | **Se releen gigas de ticks en cada corrida** | ES ≈ 720 k trades por sesión; los contrastes de papers casi nunca necesitan cada tick | caché de barras por sesión (30 s y 1 min: volumen, trades, volumen firmado, OHLC, bid/ask de cierre) que se escribe como output de un kernel la primera vez y las corridas siguientes leen en segundos. *Descartado:* barras de 1 s (≈ 80 M filas por instrumento-año: más lento de leer que los ticks) y subir la caché como dataset desde el sandbox (sacaría datos derivados de CME fuera de Kaggle). |
| F5 | **Lectura ineficiente** | un `load_ticks` por mes re-escanea los metadatos de todo el archivo | leer cada archivo una vez, por row group, solo las columnas necesarias, filtrando por las sesiones que el resolver le asigna, y entregar sesión por sesión (memoria acotada). |
| F6 | **Paralelismo a mano** | k1…kN con contratos en variables de entorno | `shards` en la spec: reparto determinista por contrato, un kernel por shard con salidas por sesión, y un merge ordenado que produce el mismo resultado que una corrida única. |
| F7 | **El código corrido no es verificable contra el repo** | el commit se inyectaba editando el script | el kernel generado embebe el código del armazón + job + spec y su sha256; la attestation guarda commit, sha de cada pieza y sha de la spec; `tools/kaggle_harness.py verify` recompone el kernel desde el commit y compara byte a byte. |
| F8 | **Salidas no estándar** | cada corrida elige nombres | siempre `results.json`, `per_session.jsonl`, `execution_attestation.json`, `artifact_manifest.json`, `output.zip` (determinista) y `output.zip.sha256`. |
| F9 | **El resultado no vuelve al cerebro** | carga manual o nula | `tools/kaggle_harness.py ingest`: verifica zip/manifest/attestation y registra partición, observaciones DESCRIPTIVE y contrastes `PROPOSED` en el ledger del brain; la adjudicación sigue siendo humana. |
| F10 | **Pruebas múltiples entre corridas** | el N de pruebas vive en cada script | la spec declara cada hipótesis; el ingest las cuenta en el ledger (observaciones/contrastes) para Bonferroni/DSR. |

*Descartado en la iteración:* reescribir `edgelab_data.py` (es la puerta única y lo mantiene el catálogo: el armazón lo usa tal cual para resolver sesiones y fuentes); exigir internet siempre (solo hace falta en el modo descarga, F1).

## 3. Criterios de "resuelto"

1. Una corrida nueva = una spec + un job de ~50 líneas; el resto lo pone el armazón.
2. La corrida LITCHECK-SSRN-20261009 termina en Kaggle con las salidas estándar y queda cargada en el hipocampo.
3. La segunda corrida sobre las mismas sesiones lee la caché de barras y tarda una fracción de la primera.
4. Tests locales (sintéticos) del armazón, del caché, del merge de shards y del ingest.

## 4. Cambios realizados

*(pendiente: se completa al terminar)*
