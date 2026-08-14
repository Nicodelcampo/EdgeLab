# aVolClusterPOI — handoff 2026-08-14

Rama: `research/bigtrap2-local-displacement-null`  
Este archivo es el estado para retomar en otro chat. **No hay ticks en Git.**

## Decisión vigente

Mejorar el indicador **no exige P2_PASS**. El 50/53 de 6E prueba que el objeto es el mismo.  
Universo de medición: **todas las OFF_PRICE de Python**, no las 50 matcheadas.  
Primer pasaje vs espejo cierra **una** pregunta (imán). No cierra “nivel de un setup”.  
“Cuando la zona funciona” es circular. Ruido = forma en t, no resultado.  
Riesgo asimétrico = otro endpoint, hay que declararlo antes.  
**Kaggle con ticks: no.** Dataset privado sigue siendo tercero / CQG.

No concatenar contratos. No QualityScore. No P&L. No GEX/L2/Asia en este pack.

## 6E — cerrado hasta nuevo n

P2: `ABSTAIN_P2` 50/53. Runs `e7602fe6` y `6f05e947`. Clock-trim no movió nada.  
Parquet canónico SHA-256:
`6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4`

Baseline Python v0.5 (`3eb47785`):

- 53 OFF, 27 zona / 20 espejo / 6 empates, p=0.574, binomial ≈0.38
- SHORT 13–13. LONG 14–7 (n=21, no interpretar)
- Lag zona p50 = 2 barras
- Doc: `docs/research/AVOL_BASELINE_FP_PYTHON_V05_2026-08-14.md`

## ES — recibido, baseline no corrido

Oráculo NT8: `avolcluster_v05_ES_0926.csv`  
SHA-256 `aacb7adb46e84b1bb8b1d9d782fbe47bb2689249ed0d2a6b5b5eeaf1637f29ca`  
Meta: `ES 09-26`, tick 0.25, v0.5. 1061 eventos. **306 OFF** (154 LONG / 152 SHORT), 159 AT.  
Primera zona `2026-05-01T11:01` `session_index=15`. Última `2026-06-30T09:10` sess 57.  
TARGET/STOP del CSV no se usan para adjudicar.

Parquet `ES_09-26_ticks.parquet` extraído (no en Git):

- 453 601 432 bytes, PAR1, **30 509 257** ticks, 31 row groups
- SHA-256 `add9bfcd46b3e8a14b26e6fe90295509dc9444309836f186661850af214146ef`
- Rango footer: **2026-06-08 03:00 UTC → 2026-07-28 00:51 UTC**
- Schema F2 (ts_utc_ns, price_ticks, bid/ask, volume, instrument, contract)

**P2 ES = `ABSTAIN_ALIGNMENT`.** El CSV arranca 1-may; el parquet 8-jun. Mayo no existe en este archivo. No comparar las 306 zonas NT8 contra este parquet.

Otros 7z ES (completos, no extraídos para baseline):

| Contrato | Parquet interno |
|---|---|
| 03-26 | ~991 MB, 2 vols |
| 06-26 | ~1.07 GB, 2 vols |
| 12-25 | ~1.02 GB, 2 vols |
| 09-25 | ~473 MB, 1 vol |
| 09-26 | extraído, hash arriba |

Catálogo: ES tick 0.25, USD 12.50 (`edgelab/data/nt8_contract.py`).

## Bloqueo técnico del baseline ES

Decoder local Snappy (sin PyArrow) leyó RG0–RG9 (10M ticks) y falló en RG10 página 18: hybrid RLE bitwidth 17 devolvió **19984/20000** índices (faltan 16).  
No padear en silencio. Arreglar hybrid o usar máquina con PyArrow.  
Script local sandbox: `/data/analysis/avol_es_baseline_fp.py`.

## Qué hacer al retomar

1. Baseline Python v0.5 en ES 09-26, ventana = cobertura del parquet (8-jun → 28-jul CT), mismo protocolo que 6E (espejo, 2000 barras, ceros adentro, empate same-bar).
2. Un contrato a la vez. Si hay n, recién entonces 06-26 / 12-25 / 03-26 por separado.
3. P2 ES solo si aparece un parquet que cubra mayo o se recorta el oráculo al 8-jun+ con warmup del mismo archivo.
4. Una mejora preregistrada (absorción **o** mecha) solo después del baseline ES, con definición de ruido de **forma** (AT_PRICE, same-bar touch, ancho > p90, cluster_share chico).

Asia / GEX / L2: líneas aparte. No abrirlas en este pack.
