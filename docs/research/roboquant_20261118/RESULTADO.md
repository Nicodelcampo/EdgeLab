# ROBOQUANT en M1 de futuros 2006–2025: señal bruta real en 4 reglas, sin neto y sin potencia para la réplica (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (enmendado por Claude antes de correr: K49, filtros fuera, hija de ORB_A5). North Star
sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `DESC.json`, `CALIBRACION.json`, `CORRIDA.json`,
`OPS_DESC_REP.csv.gz`. Familia `ROBOQUANT_A5` (15 pruebas contadas), etapa EF3. Módulo de Gemini/Antigravity (`roboquant_a5.py`).

## 1. DESC (ES + NQ + YM, meses DESC de A5)
- **5 nominadas** (BH q 0,10 y calibran contra ticks): RQ1, RQ2, RQ5, RQ6 y el contraste RQ2 − RQ2N.
- **REP no se leyó: K49** (`a5_campana rep`) — potencia en días al nivel LORD++ de 0,04 a 0,07 para las cinco. REP y holdout A5 intactos.

| Regla | n | R bruto | p | años + | bruto 2006–11 | fricción R | R neto | neto operable (≤ 0,08 R) |
|---|---|---|---|---|---|---|---|---|
| RQ1 NQ Precision 10:00, salida a 8 min | 1.677 | +0,039 | 0,001 | 70 % | +0,036 | 0,18 | −0,137 | −0,008 |
| RQ2 «Friday Range Revisit» (corto a mínimo previo) | 1.529 | +0,073 | 0,03 | 75 % | +0,135 | 0,09 | −0,017 | +0,017 |
| RQ5 banda de ruido (Zarattini) temprana | 5.683 | +0,062 | 0,001 | 70 % | +0,061 | 0,07 | −0,011 | +0,035 |
| RQ6 retroceso al VWAP en día de tendencia | 6.668 | +0,054 | 0,001 | 70 % | +0,052 | 0,08 | −0,029 | +0,036 |
| RQ2 − RQ2N (máximo previo no superado vs sí) | — | +0,136 | 0,002 | — | — | — | — | — |
| RQ3, RQ4, RQ7, RQ8 | — | +0,003 a +0,059 | ≥ 0,08 | — | — | — | negativo | — |
- El bruto es parejo en los tres índices (RQ5: ES +0,078, NQ +0,077, YM +0,031; RQ6: +0,067, +0,055, +0,041).

## 2. Lectura
- Mismo patrón que SOM y Franklin: **señal bruta estable de 20 años, sin neto** con su ejecución actual (stops de 0,45–2,2 × ATR que dejan
  la fricción en 0,07–0,18 R). Ninguna es operable tal como está.
- RQ5 y RQ6 son momentum intradía (continuación a favor del día), coherente con Baltussen et al. (2021) y con la ventaja de T. RQ2 es
  una reversión inter-día con un contraste fuerte (+0,136 R cuando el máximo previo no superó al de dos sesiones antes).
- El límite es la potencia de la réplica, no N: un efecto bruto de ~0,05 R/op con varias operaciones por día no se confirma en 39
  meses de REP. Por K49 no se gasta REP; la única vía honesta es mejorar el neto en DESC (stops más grandes con curva bruto–stop, como
  pide F-LUXIMB-EJECUCION-TIMING) y pre-registrar esa forma antes de tocar REP + holdout juntos con potencia.
