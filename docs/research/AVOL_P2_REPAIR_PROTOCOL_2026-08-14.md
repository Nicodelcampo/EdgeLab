# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `ORACLE_JUNIO_RECIBIDO_NO_ALINEADO`  
**Fuente de verdad:** `nt8/aVolClusterPOI.cs` v0.5, blob `d512d91a…`  
**Runner:** `diag/tasa_senales/avolcluster_p2_replay_v01.py`  
**Spec:** `specs/avolcluster_p2_repair_v0_1.json`

No hay `P2_PASS`. No se corre formal.

## Oráculo junio (commit `4c74b148`)

Archivo: `data/nt8_oracles/avolcluster_v05_junio2026.csv`  
Origen declarado: `6E 09-26` `DoNotMerge`, 30 días hasta 2026-06-30, timestamps **ART (UTC-3)**.  
309 eventos. Primera zona `2026-06-10T11:32` `session_index=7` `samples=20`. Última invalidación `2026-06-30T12:59`. `zone_id` 1–135.

El contrato único sin merge es el camino correcto. **No alcanza para P2.**

## Por qué esta pareja todavía no adjudica

1. **Reloj.** El runner compara el oráculo como datetime naive contra barras convertidas a `America/Chicago`. En junio ART−CDT = 2 h. La tolerancia es 60 s. Correr P2 ahora produce un falso `ABSTAIN_P2` por huso, no por el kernel.
2. **Warmup.** `LookbackSessions=20` es FIFO de sesiones completas. `session_index=7` el 10-jun implica historia NT8 desde ~31-may / 1-jun. El parquet canónico `6ffcdf04…` empieza **7-jun 22:03 CT**. Faltan ~5 sesiones que el umbral del oráculo sí usó. Eso contamina **toda** la ventana 10–30 jun, no solo el arranque.
3. El bucket 33 a las 11:32 ART es coherente con sesión CME 17:00 CT. El C# está bien; el matching del runner no.

## Re-export que falta

Mismo chart `6E 09-26` `DoNotMerge`. Cargar **solo** historia que el parquet tiene:

- desde **2026-06-08 17:00 CT** (19:00 ART) — primera sesión completa compartida;
- hasta **2026-06-30 16:00 CT** (18:00 ART).

No cargar 30 días atrás. No empezar el domingo 7-jun 17:00 CT: el parquet no tiene 17:00–22:03.

Después: timestamps del CSV en ART se convierten a CT **antes** de matchear. El runner hay que parchearlo; hoy asume Chicago naive.

## Qué no hacer

No concatenar `12-25`/`03-26`/`06-26`. No cambiar el hash canónico. No formal. No mejora A/B. No GC.
