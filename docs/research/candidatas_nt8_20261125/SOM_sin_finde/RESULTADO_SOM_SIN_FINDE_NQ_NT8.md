# `SOM_sin_finde` en NQ: control en NT8 contra Python y efecto del veto de noticias

Estado: RESULTADO (control de ejecución; no confirma ni refuta un edge nuevo)  
Fecha: 2026-11-25  
Corrida NT8 (`EdgeLabCandidataFS`, NQ, M1 ETH, 2019-01-02 → 2026-09-30, `Contratos fijos = 1`, veto ±2 / FOMC ±5): [`NT8_SOM_sin_finde_NQ_fijo1.csv`](NT8_SOM_sin_finde_NQ_fijo1.csv). Referencia: [`PY_SOM_sin_finde_NQ.csv`](PY_SOM_sin_finde_NQ.csv) (`tools/candidata_referencia.py`). Comparación: [`COMPARACION.json`](COMPARACION.json) (`tools/comparar_candidata.py`, calentamiento 12 meses).

1. **Paridad de entradas (2020-01-02 → 2026-09-29, sesiones DESC/REP de A5):**
   - **1.142 de 1.145 entradas de Python** coinciden al minuto de ejecución en NT8 (**99,74%** en `entradas_a_1_min`: Python marca `09:35:00 NY` — apertura de la barra de llenado — y NT8 marca `09:36:00 NY` — cierre de esa misma barra M1). Sólo 3 entradas de Python no coinciden exacto a ±1 min y 59 entradas extra aparecen en NT8 (`1.201` vs `1.145`).
   - **Puntos en sesiones DESC/REP (`2020–2026`):** NT8 **`+16.119,00 pts`** vs Python con veto **`+14.406,16 pts`** (`+11,9%`; frente a `SOMEOD` que sumó `+13.265,25 pts` en NT8 y `+12.754,53 pts` en Python con veto: dejar correr lunes–jueves suma `+2.853,75 pts` brutos en NT8).
2. **Veto de noticias (`NEWS_VETO`):**
   - Al mantener posiciones abiertas de lunes a jueves (`HardFlattenHHMM_ET = 0`), el calendario tier-1 (`08:30`, `10:00`, `14:00` FOMC) cierra **`357` de `1.660` operaciones en NT8 (`21,5%`)** (`274` de `1.316` = `20,82%` en Python).
   - En `2024`, el veto recorta de `+3.614 pts` (Python sin veto) a `+836 pts` (Python con veto) / `+543 pts` (NT8 DESC+REP).
3. **Lectura de época (`contratos fijos = 1` vs `R`):**
   - En `2020–2021` `SOM_sin_finde` ya fue muy rentable (`+12,38 R` y `+21,65 R` en NT8); en `2022–2024` atravesó su bache cíclico agravado por el veto de noticias (`-8,68 R`, `-9,49 R`, `-5,74 R` en NT8), y en `2025–2026` repuntó (`+32,58 R` y `+20,50 R`). Con 1 contrato fijo, además, la mediana del stop pasó de `103,75 pts` (`2020`, `~$2.075/NQ`) a `260,50 pts` (`2026`, `~$5.210/NQ`), exagerando visualmente la pendiente de `2025–2026` respecto a `2020–2021`.

4. **Desglose anual (NT8 completo vs `DESC/REP`):**

| Año | `n` (NT8) | `pts` (NT8) | `R_neto_mini` sum (NT8) | `riesgo_pts` med. | `NEWS_VETO` (NT8) | `DESC/REP` NT8 `pts` | `DESC/REP` PY con veto `pts` | `DESC/REP` PY sin veto `pts` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019 (calent.) | 249 | -443,50 | -13,50 R | 49,25 | 58 | -144,75 | -31,48 | -4,47 |
| 2020 | 249 | +2.112,50 | +12,38 R | 103,75 | 54 | +3.204,00 | +2.821,73 | +3.729,42 |
| 2021 | 246 | +2.103,25 | +21,65 R | 108,38 | 48 | +2.374,00 | +2.400,15 | +2.387,82 |
| 2022 | 252 | -489,25 | -8,68 R | 176,62 | 50 | -905,00 | +482,81 | -275,92 |
| 2023 | 241 | -199,50 | -9,49 R | 129,75 | 59 | -518,75 | +6,45 | -269,76 |
| 2024 | 246 | +885,50 | -5,74 R | 149,12 | 53 | +542,75 | +835,80 | +3.614,24 |
| 2025 | 241 | +7.750,25 | +32,58 R | 184,00 | 54 | +5.268,00 | +5.179,70 | +4.937,07 |
| 2026 (`≤sep`) | 185 | +3.956,25 | +20,50 R | 260,50 | 39 | +2.719,25 | +2.679,52 | +2.481,74 |
