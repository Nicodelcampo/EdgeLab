# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `ABSTAIN_P2`  
**Runs:** `e7602fe6` (50/53) y `6f05e947` (50/53 tras clock-trim).  
Sello nuevo: `1c829eeb22d3548e4a2ed946496c5c4d34c9a82e5b4f450cd9044b81362fd1f3`

Hash canónico OK. P1A PASS. Formal no ejecutada. Gate 100% intacto.

## Clock-trim: no sirvió

`first_session_clock_trim`: applied, `bars_dropped=10`, `aligned_minute=320`.  
Se esperaba ~7 barras hasta el minuto 310 (22:10 CT). Se recortó de más (22:20).  
Sesión 0: 934 → 924 barras. Las 3+3 zonas no se movieron: mismos ticks, mismas horas.

No hay más parches de grilla. El desfase de historial no se adivina desde Python.

## Las 6 siguen iguales

NT8 sola (Chicago): 17-jun 13:26 `[23184,23185]` 1107/750 n=20; 20:03 `[23107,23110]` 1437/434 n=21; 23:39 `[23125,23127]` 478/164 n=20.

Python sola: 18-jun 12:01 `[23005,23008]` 1093/740 n=24; 25-jun 09:08 `[22827,22837]` 3584/3232 n=39; 30-jun 21:35 `[22880,22882]` 220/174 n=41.

## Qué queda

Un solo insumo, si se quiere otro intento de P2: reexport NT8 `DoNotMerge` desde **2026-06-08 00:03 ART** (22:03 CT del 7-jun, primer tick del parquet) hasta 30-jun. Sin eso, este par oráculo/parquet queda en `ABSTAIN_P2`. No formal. No A/B.
