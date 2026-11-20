# SQX lote 1 — par 1: LIT-TSMOM S&P D1 (real vs nulo), 2026-11-15
Estado: RESULTADO (EF2). Pre-registro: `PREREGISTRO.md` (enmiendas 1–4). Datos: `sqx/corridas/LIT-TSMOM_SP_M1_dukas_D1_202611142222/comparacion_nulo.json`.
Herramienta: `edgelab/sqx_puente.py` (t por estrategia desde las columnas del databank, igual para real y nulo).
- Generadas: real 132.973, nulo 134.315 (2 h cada uno). Aceptadas por SQX: real 4.507, nulo 12.100.
- Con ≥ 200 operaciones (2012–2019): real 1.468, nulo 3.886.
| t por estrategia | p50 | p90 | p99 | máximo |
|---|---|---|---|---|
| Real (S&P D1) | 0,16 | 1,39 | 2,88 | 4,13 |
| Nulo (serie sintética) | 0,83 | 2,12 | 3,20 | 5,54 |
**Veredicto: 0 candidatas.** La mejor real (t 4,13) queda debajo del máximo del nulo (5,54), y en TODOS los cuantiles el nulo está
por encima del real: el Builder de tendencia sobre el S&P diario no encuentra nada que no encuentre sobre ruido con la misma
volatilidad. Para el SQX solo, una estrategia así habría pasado sus filtros (aceptó 4.507).
Limitación: un solo nulo (sin p95 del máximo); el t se aproxima desde las columnas (ver `edgelab/sqx_puente.py`). Con el nulo por
encima en todos los cuantiles, ninguna de las dos cambia la conclusión.
