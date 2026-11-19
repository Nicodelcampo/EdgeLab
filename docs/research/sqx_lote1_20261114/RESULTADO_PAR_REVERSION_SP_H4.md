# SQX lote 1 — par reversión S&P H4: resultado (2026-11-15)
Estado: RESULTADO. Pre-registro: `PREREGISTRO.md`. Real `SQX-PLANTILLA-REVERSION_SP_M1_dukas_H4_202611142223` (15.561 generadas, 1.762 aceptadas)
contra su nulo de semanas re-encadenadas `SQX-PLANTILLA-REVERSION_NULO_SP_M1_dukas_H1_s1_H4_202611142223` (16.124 generadas, 1.523 aceptadas).
Comparación con `edgelab/sqx_puente.py` (t por estrategia, n ≥ 200): `sqx/corridas/SQX-PLANTILLA-REVERSION_SP_M1_dukas_H4_202611142223/comparacion_nulo.json`.

| | n | t p50 | t p90 | t p99 | t máx |
|---|---|---|---|---|---|
| Real | 1.258 | 0,41 | 1,46 | 2,26 | 3,77 |
| Nulo | 989 | 0,36 | 1,57 | 2,65 | **4,44** |

**Ninguna candidata**: el mejor real (3,77) no llega al máximo del nulo (4,44) y la cola del real es igual o más flaca que la del nulo. Con
la plantilla de reversión en S&P H4, el Builder no encuentra nada que no encuentre también en una serie sin estructura de régimen
(las semanas re-encadenadas). Alcance: esta plantilla, este instrumento y este marco temporal; no se transporta a otras.
