# CARRIL2-CIERRE: entrar al cierre de las 15:55 no recupera nada frente a las 18:00 (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO_CIERRE.md` (8 pruebas en `CARRIL2_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS_CIERRE.csv.gz`, `DESC_CIERRE.json`. DESC de A5, mismo motor
calibrado (K28); salida fuera de HOLDOUT/EMBARGO (assert). 0/8 en BH; REP no se leyó.

| Regla | n DESC (15:56) | R neto 15:56 | p | R bruto | R neto 18:00 (lote 1) | Contraste 15:56 − 18:00 (ee, p) |
|---|---|---|---|---|---|---|
| IBS + VIX | 536 | +0,040 | 0,26 | +0,057 | +0,017 | +0,022 (0,053; 0,34) |
| Double Seven | 639 | +0,064 | 0,11 | +0,083 | +0,079 | −0,015 (0,034; 0,67) |
| Turnaround Tuesday | 584 | +0,003 | 0,48 | +0,024 | +0,059 | −0,056 (0,033; 0,96) |
| Cambio de mes | 363 | +0,016 | 0,43 | +0,031 | +0,034 | −0,018 (0,022; 0,80) |

| R neto por época | 2006–11 | 2012–17 | 2018–25 | 2018–25 sin meses de crisis* |
|---|---|---|---|---|
| IBS 15:56 / 18:00 | +0,064 / +0,066 | +0,235 / +0,135 | −0,077 / −0,098 | +0,002 / +0,034 |
| D7 15:56 / 18:00 | +0,081 / +0,171 | +0,148 / +0,130 | −0,004 / +0,001 | +0,057 / +0,065 |
| TT 15:56 / 18:00 | +0,045 / +0,137 | +0,078 / +0,092 | −0,082 / −0,019 | −0,046 / +0,017 |
| TOM 15:56 / 18:00 | +0,026 / +0,070 | +0,044 / +0,059 | −0,007 / −0,001 | +0,001 / −0,019 |
(*) meses elegidos mirando la historia: feb, oct y dic de 2018; feb y mar de 2020; ene, abr y sep de 2022.

Episodios (versión 15:56):
- IBS: Episodios: media +0.040 (n 536); sin los 3 peores meses +0.096; sin los 3 mejores +0.004; peores {'201812': -11.69, '200810': -7.99, '202201': -6.36}; mejores {'202105': 6.13, '201212': 6.37, '202503': 6.8}.
- D7: Episodios: media +0.064 (n 639); sin los 3 peores meses +0.110; sin los 3 mejores +0.030; peores {'201810': -10.14, '202201': -8.32, '202109': -7.45}; mejores {'202307': 7.02, '202411': 7.58, '202402': 7.6}.
- TT: Episodios: media +0.003 (n 584); sin los 3 peores meses +0.035; sin los 3 mejores -0.036; peores {'201410': -6.13, '200811': -6.07, '202305': -5.59}; mejores {'202203': 6.53, '202411': 7.16, '200903': 8.13}.
- TOM: Episodios: media +0.016 (n 363); sin los 3 peores meses +0.051; sin los 3 mejores -0.040; peores {'201801': -4.06, '201911': -4.06, '201907': -4.06}; mejores {'202506': 5.74, '202001': 7.07, '201106': 7.13}.

Diagnóstico de mecanismo: no hay grilla; misma señal y mismo motor, sólo cambia la hora de entrada/salida (barras de ejecución 15:56 → 15:55,
verificadas en una semana de ES: apertura 15:56, cierre igual al RTH, viernes unido al lunes).
