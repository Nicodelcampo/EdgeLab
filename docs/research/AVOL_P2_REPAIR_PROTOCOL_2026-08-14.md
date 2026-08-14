# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `ABSTAIN_P2`  
**Run:** `diag/tasa_senales/AVOL_P2_replay_v01.json` (`e7602fe6`)  
**Sello:** `feaa9cc9361019c867531ea50e177235436b85528bacf487e37d6caa84eea43c`

Hash canónico OK. P1A PASS (2 784 986 ticks, 54 112 barras, quote 100%). Formal no ejecutada.

## Resultado

53 vs 53 OFF_PRICE. **50 matcheadas.** 3 NT8 solas + 3 Python solas.  
`ABSTAIN_P2` es la etiqueta correcta. **No se baja el 100% a 94%.** 50/53 prueba que el reloj ART→CT y el objeto son los mismos; no autoriza formal ni A/B.

No es un desfase global de bloques: si la grilla de 10 barras estuviera corrida, caerían casi todas.

## Las 6 zonas no son gemelas

NT8 sola (hora Chicago del runner = ART−2h):

1. `2026-06-17T13:26` `[23184,23185]` SHORT — CSV 15:26 ART, score 1107 / umbral 750, 2 ticks, `cluster_share` 0.17, tercer bloque del bucket 40.
2. `2026-06-17T20:03` `[23107,23110]` LONG — CSV 22:03 ART, score 1437 / 434. No es un flip de umbral.
3. `2026-06-17T23:39` `[23125,23127]` LONG — CSV 18-jun 01:39 ART.

Las tres caen el primer día de detección (sesiones 7–8). Sospecha: residual de ~3 min al inicio del parquet + `one_cluster_per_block`.

Python sola (no son las mismas zonas corridas en el tiempo):

1. `2026-06-18T12:01` `[23005,23008]` LONG — el oráculo tiene `[23005,23007]` a las 08:31 ART; otro objeto.
2. `2026-06-25T09:08` `[22827,22837]` SHORT
3. `2026-06-30T21:35` `[22880,22882]` SHORT

## Siguiente paso

Autopsia de esas 6 barras: celdas, mediana, clusters, umbral, `close_tick`, kind. No relajar matching. No formal.
