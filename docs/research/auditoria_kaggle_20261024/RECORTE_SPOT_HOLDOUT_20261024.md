# Recorte de los datasets SPOT de Dukascopy en la frontera del holdout

Estado: VIGENTE. Recorte preparado y verificado; la subida de las versiones nuevas a Kaggle está PENDIENTE.
Fecha: 2026-10-24
Familia / módulo: datos SPOT (`edgelab-dukascopy-*`), frontera `edgelab/holdout.py` (HOLDOUT-A4)
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Procedencia: metadatos y archivos leídos por la API de Kaggle el 2026-10-24 entre las 06:38 y las 06:55 UTC. Herramienta
`tools/recortar_spot_holdout.py` con tests en `tests/test_recortar_spot_holdout.py`.
Decisión: P-96 P4 de `AUDITORIA_CORRIDAS_KAGGLE_Y_EMBUDO_20261024.md`, con OK de Nico el 2026-10-24 («OK a todo»).

## Qué se encontró
La auditoría vio el problema en `edgelab-dukascopy-nq-usatech`. Al medirlo resultó que son **los seis** datasets SPOT: todos
se subieron con corte en la fecha UTC 2026-09-30 y todos traen las 120 velas M1 de 22:00 a 23:59 UTC de ese día. Ese tramo ya
es holdout, porque la sesión CME del 2026-10-01 abre a las 22:00 UTC del 30-sep.

| dataset | velas M1 | velas M1 del holdout | última vela |
|---|---:|---:|---|
| `edgelab-dukascopy-nq-usatech` (USATECHIDXUSD) | 1.681.920 | 120 | 2026-09-30 23:59 UTC |
| `edgelab-dukascopy-es-usa500` (USA500IDXUSD) | 3.900.960 | 120 | 2026-09-30 23:59 UTC |
| `edgelab-dukascopy-ym-usa30` (USA30IDXUSD) | 1.681.920 | 120 | 2026-09-30 23:59 UTC |
| `edgelab-dukascopy-xauusd-ticks-m1` (XAUUSD) | 1.905.120 | 120 | 2026-09-30 23:59 UTC |
| `edgelab-dukascopy-6e-eurusd` (EURUSD) | 1.689.120 | 120 | 2026-09-30 23:59 UTC |
| `edgelab-dukascopy-6j-usdjpy` (USDJPY) | 1.689.120 | 120 | 2026-09-30 23:59 UTC |

Los lectores de código ya cortan en la frontera, así que ninguna corrida auditada usó esas filas. El problema es de custodia:
los datos del holdout están físicamente en Kaggle.

## El recorte
`tools/recortar_spot_holdout.py` sólo quita filas. Reescribe cada parquet con `time_utc_ns < HOLDOUT_APERTURA_UTC_NS` (la
constante de `edgelab/holdout.py`, sin literal propio), row group por row group. Falla si el archivo no es ascendente.
Después vuelve a leer la salida y verifica los conteos y que ninguna fila quede en la frontera o después.
`calidad.json` pierde lo que describe al holdout: los huecos que terminan dentro de él y los ticks del 30-sep posteriores a las
22:00. El README declara el recorte. `RECORTE_HOLDOUT.json` va dentro de la versión, con conteos y sha256 de entrada y salida.

Prueba completa sobre `edgelab-dukascopy-nq-usatech` v1:

| archivo | filas v1 | filas recortado | quitadas | sha256 v1 | sha256 recortado |
|---|---:|---:|---:|---|---|
| USATECHIDXUSD_m1.parquet | 1.681.920 | 1.681.800 | 120 | `b9e12a95…5b25f62b` | `9ef53726…fb05c64d` |
| USATECHIDXUSD_ticks.parquet | 261.588.257 | 261.569.036 | 19.221 | `b2091ea4…e8f33d0a` | `c59697f6…21594fe3` |

El último tick que queda es de las 20:14:59 UTC. Entre las 20:15 y las 22:00 hay un hueco de 105 minutos que `calidad.json` ya
registraba (el cierre diario del CFD).

## Lo que falta
1. ~~Subir las seis versiones nuevas.~~ **Hecho el 2026-10-24** desde la sesión en la nube (`tools/recortar_spot_holdout.py --subir`).
   Cada versión nueva parte de la **última** versión publicada del dataset: ES estaba en v2 y XAU en v3, y el primer intento
   comparó contra la v1 y falló por tamaño (por eso la herramienta tiene ahora `--version`). Los recibos completos, con sha256
   de entrada y de salida, están en `recorte_spot/recorte_<dataset>.json`.

| dataset | versión de origen | archivo | filas antes → después | quitadas | sha256 de la salida |
|---|---:|---|---|---:|---|
| `edgelab-dukascopy-6e-eurusd` | v1 | EURUSD_m1.parquet | 1.689.120 → 1.689.000 | 120 | `52986e72…9d513dc4` |
| `edgelab-dukascopy-6e-eurusd` | v1 | EURUSD_ticks.parquet | 85.803.967 → 85.802.544 | 1.423 | `59bad4c5…34abd622` |
| `edgelab-dukascopy-6j-usdjpy` | v1 | USDJPY_m1.parquet | 1.689.120 → 1.689.000 | 120 | `fba83fd6…588c9510` |
| `edgelab-dukascopy-6j-usdjpy` | v1 | USDJPY_ticks.parquet | 137.907.862 → 137.903.464 | 4.398 | `f9b2d5b8…22d36cdd` |
| `edgelab-dukascopy-es-usa500` | v2 | USA500IDXUSD_m1.parquet | 3.900.960 → 3.900.840 | 120 | `90e2e418…ede4c4dd` |
| `edgelab-dukascopy-es-usa500` | v2 | USA500IDXUSD_ticks.parquet | 147.279.620 → 147.277.198 | 2.422 | `6948f864…23ab67eb` |
| `edgelab-dukascopy-nq-usatech` | v1 | USATECHIDXUSD_m1.parquet | 1.681.920 → 1.681.800 | 120 | `81819615…8fb8bed0` |
| `edgelab-dukascopy-nq-usatech` | v1 | USATECHIDXUSD_ticks.parquet | 261.588.257 → 261.569.036 | 19.221 | `7037b34d…dd332011` |
| `edgelab-dukascopy-xauusd-ticks-m1` | v3 | XAUUSD_m1.parquet | 1.905.120 → 1.905.000 | 120 | `4c907627…e42f5a77` |
| `edgelab-dukascopy-xauusd-ticks-m1` | v3 | XAUUSD_ticks.parquet | 258.524.416 → 258.520.378 | 4.038 | `8a27e0de…f7fde83d` |
| `edgelab-dukascopy-ym-usa30` | v1 | USA30IDXUSD_m1.parquet | 1.681.920 → 1.681.800 | 120 | `6b263557…3d5ae369` |
| `edgelab-dukascopy-ym-usa30` | v1 | USA30IDXUSD_ticks.parquet | 124.282.962 → 124.278.565 | 4.397 | `9d6775d4…4e2543a4` |

   El sha256 de USATECH no coincide con el de la prueba de arriba, aunque las filas son las mismas (261.569.036). La diferencia
   está en los bytes del parquet (metadatos del escritor), no en el contenido: los conteos y el último tick coinciden.
2. **La versión 1 sigue en el historial de Kaggle.** Una versión nueva no la borra. Si se quiere que esas dos horas no estén
   en Kaggle de ningún modo, hay que borrar la versión vieja o el dataset entero y volver a crearlo. Las dos cosas son
   irreversibles y rompen los kernels que la fijan, así que las decide Nico aparte.
