# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `ORACLE_JUNIO_V2_LISTO_P2_NO_CORRIDO`  
**Fuente de verdad:** `nt8/aVolClusterPOI.cs` v0.5, blob `d512d91a…`  
**Runner:** `diag/tasa_senales/avolcluster_p2_replay_v01.py`  
**Spec:** `specs/avolcluster_p2_repair_v0_1.json`

No hay `P2_PASS`. No se corre formal.

## Oráculo junio v2 (commit `0483c4ae`)

Archivo: `data/nt8_oracles/avolcluster_v05_junio2026.csv`  
Origen: `6E 09-26` `DoNotMerge`, date picker NT8 **08/06/2026–30/06/2026** (día completo). Timestamps **ART (UTC-3)**.

171 eventos. 53 `ZONE_CREATED` OFF_PRICE. 19 `AT_PRICE_CREATED`.  
Primera zona: `2026-06-17T04:34` ART, `session_index=7`, `samples=21`, ticks `23295–23299`.  
Última invalidación: `2026-06-30T12:59` ART.

`samples=21` = 7 sesiones previas × 3 bloques. Coincide con min_samples=20 recién superado. El date picker del 8-jun ART 00:00 ≈ 7-jun 22:00 CT; el parquet canónico empieza 7-jun **22:03** CT. Residual: ~3 minutos de la sesión parcial inicial.

## Reloj

El runner (commit `994a20f6`) convierte ART → `America/Chicago` antes de matchear.  
`2026-06-17T04:34` ART = `2026-06-17T02:34` CDT. Test en `7e9dcdbc`.

Hash canónico completo:
`6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4`

## Comando (máquina con PyArrow + parquet canónico)

```bash
python diag/tasa_senales/avolcluster_p2_replay_v01.py \
  --parquet "RUTA_CANONICA/6E_09-26_ticks.parquet" \
  --oracle data/nt8_oracles/avolcluster_v05_junio2026.csv \
  --out diag/tasa_senales/AVOL_P2_replay_v01.json
```

`sha256sum` del parquet debe ser exactamente el hash de arriba. Formal, A/B, GC y concatenación: no.
