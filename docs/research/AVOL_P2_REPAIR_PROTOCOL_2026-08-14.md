# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `IMPLEMENTED_NOT_RUN_ON_CANONICAL`  
**Fuente de verdad:** `nt8/aVolClusterPOI.cs` v0.5, blob `d512d91a…`  
**Runner:** `diag/tasa_senales/avolcluster_p2_replay_v01.py`  
**Spec:** `specs/avolcluster_p2_repair_v0_1.json`

## Qué resolvió el C# entregado

El archivo adjunto es exactamente el mismo contenido lógico que la copia del
repo: al normalizar a LF, su Git blob SHA-1 es `d512d91a606d41609b21ef244c896ead1dc52a10`.
El adjunto tenía terminadores mezclados; para instalar en NT8 se usa el checkout
CRLF del repo, nunca el byte-stream adjunto.

El C# retira una sospecha y demuestra cinco divergencias:

1. **H4 queda retirado:** son bloques **disjuntos** de 10 barras, no sliding.
2. **FIFO por sesión:** NT8 retiene 20 sesiones completas; Python retenía solo
   20 scores (~6–7 sesiones porque hay tres bloques por bucket/sesión).
3. **Primera sesión:** NT8 conserva la primera sesión completa; Python la
   descartaba mediante `first_roll_done`.
4. **Bucket:** NT8 usa `(bar close − 1 segundo)`; Python mandaba los cierres
   exactos de :30/:00 al bucket siguiente.
5. **Warmup:** el oráculo exporta su primera zona en `session_index=7`, coherente
   con ~21 muestras acumuladas (3 por sesión). El runner original cortó los
   ticks antes del warmup.
6. **Sesión de barra:** `[start,end)` se asigna con `end−1s`, no con `end`.

## Por qué el P2 original no adjudica

Además de las divergencias anteriores, el matching original permitía que una
misma zona Python satisficiera varias filas del oráculo, no rechazaba zonas
Python sobrantes, relajó la regla preregistrada de 100% a 99%, y siguió
calculando la formal pese a P2 FAIL. La etiqueta `ABSTAIN_P2` sí fue correcta;
los números posteriores no deben usarse.

## Gate nuevo

1. Hash exacto del `6E_09-26_ticks.parquet` preregistrado. Mismatch →
   `ABSTAIN_INPUT` antes de leer el oráculo, abrir Parquet, importar PyArrow,
   ejecutar P1A o calcular cualquier resultado.
2. Meta del oráculo = `6E 09-26`.
3. Cargar el contrato completo para conservar historia anterior.
4. Barras M1, P1A, bloques y buckets espejo del C#.
5. Comparar dentro de 2026-04-10 a 2026-06-30 CT.
6. Matching uno-a-uno `(lower_tick, upper_tick)` exacto y `|Δt|≤60s`.
7. `P2_PASS` exige P1A PASS, cero filas NT8 faltantes **y cero zonas Python
   sobrantes**. Cualquier otra cosa → `ABSTAIN_P2` con diff completo.
8. La formal **no se ejecuta** en este runner.

## Datos recibidos

Los nueve parquets tienen magic `PAR1`, pero los cuatro 6E de la formal son
**4/4 hash mismatch** contra la spec. El replay los rechaza; no se cambian los
hashes del preregistro para hacerlos pasar. El quinto 6E (`09-25`) y cuatro GC
quedan como candidatos no adjudicados en
`specs/avol_market_data_upload_manifest_2026-08-14.json`.

GC ya tiene geometría contractual en el bridge: tick 0.1, multiplicador 100 oz,
USD 10/tick. Falta verificar con PyArrow: schema F2, instrument/contract internos,
monotonía, rango temporal, quote coverage y P1A; luego declarar firewall/holdout.

## Orden después de P2_PASS

1. Baseline v0.5 por contrato separado. Prohibido concatenar ticks de contratos
   solapados en las mismas barras; carreras censuradas en el final de cada
   contrato. Agregación por sesión-calendario.
2. Mejora A — absorción bid/ask, predicción y threshold preregistrados.
3. Mejora B — rechazo/mecha, aislada de A.
4. Recién después, A+B con regla predeclarada.
5. GC como replicación con spec propia; nunca como rescate post-hoc.

## Comando en la máquina con PyArrow

```bash
python diag/tasa_senales/avolcluster_p2_replay_v01.py \
  --parquet "RUTA_CANONICA/6E_09-26_ticks.parquet" \
  --oracle data/nt8_oracles/avolcluster_v05_20260813.csv \
  --out diag/tasa_senales/AVOL_P2_replay_v01.json
```

Antes de ejecutarlo, `sha256sum` debe dar exactamente
`6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4`.
