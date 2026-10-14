# Qué datasets adjuntar, por instrumento (generado por `tools/data_resolver.py`)

Solo el resolver decide la fuente de cada sesión (`edgelab_data.py`). Para un kernel, adjuntá los datasets de la fila del instrumento; `python docs/data_catalog/edgelab_data.py INST DESDE HASTA` da la lista exacta para un rango. Además siempre: `edgelab-data-catalog` (código y resolver).

| Instrumento | Veredicto | Sesiones aprobadas | Datasets primarios (sesiones) | Spot/CFD hermano (solo potencia) |
|---|---|---:|---|---|
| 6B | APROBADO | 285 | `edgelab-nt8-historical-missing-20261001` (285) | edgelab-dukascopy-6b-gbpusd |
| 6E | CON_SALVEDADES | 289 | `edgelab-nt8-historical-missing-20261001` (222); `edgelab-ticks-nt8-reexport-20261005` (62); `edgelab-ticks-6e-preholdout` (5) | edgelab-dukascopy-6e-eurusd |
| 6J | APROBADO | 267 | `edgelab-nt8-historical-missing-20261001` (267) | edgelab-dukascopy-6j-usdjpy |
| ES | CON_SALVEDADES | 243 | `edgelab-nt8-historical-missing-20261001` (186); `edgelab-ticks-nt8-reexport-20261005` (50); `edgelab-ticks-es-nq-2026q3-ext` (7) | edgelab-dukascopy-es-usa500 |
| GC | CON_SALVEDADES | 281 | `edgelab-ticks-gc-preholdout` (201); `edgelab-ticks-nt8-reexport-20261005` (80) | edgelab-dukascopy-xauusd-ticks-m1 |
| MBT | CON_SALVEDADES | 121 | `edgelab-ticks-nt8-reexport-20261005` (89); `edgelab-ticks-mbt-preholdout` (32) | - |
| MES | APROBADO | 277 | `edgelab-ticks-nt8-canonical` (219); `edgelab-ticks-nt8-reexport-20261005` (58) | edgelab-dukascopy-es-usa500 |
| MGC | CON_SALVEDADES | 219 | `edgelab-mgc-nt8-raw-parquet-20261002` (160); `edgelab-ticks-nt8-reexport-20261005` (59) | edgelab-dukascopy-xauusd-ticks-m1 |
| MNQ | CON_SALVEDADES | 261 | `edgelab-ticks-nt8-canonical` (148); `edgelab-ticks-nt8-reexport-20261005` (113) | edgelab-dukascopy-nq-usatech |
| MYM | CON_SALVEDADES | 136 | `edgelab-ticks-nt8-canonical` (83); `edgelab-ticks-nt8-reexport-20261005` (53) | edgelab-dukascopy-ym-usa30 |
| NQ | CON_SALVEDADES | 278 | `edgelab-nt8-historical-missing-20261001` (119); `edgelab-ticks-nt8-reexport-20261005` (67); `edgelab-ticks-es-nq-2026q3-ext` (58); `edgelab-ticks-nq-preholdout` (34) | edgelab-dukascopy-nq-usatech |
| RTY | CON_SALVEDADES | 143 | `edgelab-ticks-nt8-canonical` (142); `edgelab-ticks-nt8-reexport-20261005` (1) | - |
| YM | CON_SALVEDADES | 266 | `edgelab-ticks-nt8-canonical` (198); `edgelab-ticks-nt8-reexport-20261005` (68) | edgelab-dukascopy-ym-usa30 |
| ZB | APROBADO | 264 | `edgelab-ticks-zb-preholdout` (121); `edgelab-ticks-nt8-reexport-20261005` (77); `edgelab-nt8-historical-missing-20261001` (66) | - |
