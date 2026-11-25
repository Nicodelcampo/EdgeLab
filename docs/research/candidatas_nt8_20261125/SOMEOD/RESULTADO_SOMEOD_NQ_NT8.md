# SOMEOD (`SOMEOD_ext_NQ`) en NQ: control en NT8 contra Python y lectura de régimen

Estado: RESULTADO (control de ejecución; no confirma ni refuta un edge nuevo)  
Fecha: 2026-11-25  
Corrida NT8 (`EdgeLabCandidataFS`, NQ, M1 ETH, 2019-01-02 → 2026-09-30, `Contratos fijos = 1`, veto ±2 / FOMC ±5): [`NT8_SOMEOD_NQ_fijo1.csv`](NT8_SOMEOD_NQ_fijo1.csv). Referencia: [`PY_SOMEOD_ext_NQ_NQ.csv`](PY_SOMEOD_ext_NQ_NQ.csv) (`tools/candidata_referencia.py`). Comparación: [`COMPARACION.json`](COMPARACION.json) (`tools/comparar_candidata.py`, calentamiento 12 meses).

1. **Paridad de entradas (2020-01-02 → 2026-09-30, sesiones DESC/REP de A5):**
   - **1.256 de 1.256 entradas de Python** aparecen exactamente al minuto de ejecución en NT8 (**100,0%** en `entradas_a_1_min`: Python registra `09:35:00 NY` — apertura de la vela de llenado — y NT8 registra `09:36:00 NY` — cierre de esa misma barra M1). Sólo 6 señales extra en NT8 (`1.262` vs `1.256`).
   - **Puntos en sesiones DESC/REP:** NT8 **`13.265,25 pts`** vs Python con veto **`12.754,53 pts`** (`+4,0%`; sin veto eran `17.699,77 pts`).
2. **Veto de noticias (`NEWS_VETO`):**
   - Como `SOMEOD` entra a las `09:35/09:36 NY`, el calendario de las `10:00 NY` le cierra **`310` de `1.740` operaciones en NT8 (`17,8%`)** a las `09:58 NY` (`244` de `1.444` = `16,9%` en `DESC/REP` Python).
   - En `DESC/REP`, ese recorte cuesta **`-4.945 pts`** brutos en Python (`2020`: `+4.830 → +3.220 pts`; `2024`: `+2.971 → +1.049 pts`).
3. **¿Es un régimen desde 2024 o está sobreajustada?**
   - **No está sobreajustada ni arranca en 2024:** en el estudio formal de 20 años ([`docs/research/regimen_som_franklin_20261119/RESULTADO.md`](../../regimen_som_franklin_20261119/RESULTADO.md), 81 variantes en `NQ+ES+YM`), la señal bruta dio **`SENAL_ROBUSTA`** (`81/81` positivas, `PBO = 0,082`, vecinos `8/8`), con quiebre `sup-F` real el **`2017-11-13` (`p = 0,02`)**.
   - **Por qué en NT8 parece plana/negativa antes de 2025:** (a) en `2020–2021` sí ganó (`+22,8 R` y `+18,2 R` en DESC/REP; `+9,9 R` y `+18,5 R` completo en NT8), (b) sufrió un **bache real en `2022–2023`** (`-1,1 R` y `-14,9 R`) + `2024` plano en R (`+0,6 R` total / `-0,12 R` DESC+REP), y (c) con `1` contrato fijo el `NQ` subió de `103 pts` de stop mediano (`2020`, `$2.068/NQ`) a `258 pts` (`2026`, `$5.155/NQ`), ampliando visualmente en dólares la subida de `2025–2026`.
   - **Veredicto neto EdgeLab:** desde nov-2017 las 81 variantes tienen R neto positivo, pero chico (`+0,030 R` global, `+0,054 R` en NQ) con `PBO neto = 0,839` → **sirve como módulo complementario en canasta (`Core5`), no como régimen neto fuerte aislable como `T` o `R`**.

4. **Desglose anual (NT8 completo vs `DESC/REP`):**

| Año | `n` (NT8) | `pts` (NT8) | `R_neto_mini` sum (NT8) | `riesgo_pts` med. | `DESC/REP` NT8 `pts` | `DESC/REP` PY con veto `pts` |
|---|---:|---:|---:|---:|---:|---:|
| 2020 | 258 | +2.056,75 | +9,85 R | 103,38 | +3.094,25 | +3.220,14 |
| 2021 | 258 | +2.107,50 | +18,46 R | 108,38 | +2.085,25 | +2.233,24 |
| 2022 | 258 | +584,50 | -1,06 R | 175,62 | +313,50 | +234,58 |
| 2023 | 257 | -1.252,75 | -14,89 R | 127,50 | -659,50 | -629,61 |
| 2024 | 259 | +1.336,25 | +0,59 R | 147,75 | +1.214,75 | +1.049,46 |
| 2025 | 257 | +6.956,50 | +28,03 R | 181,50 | +4.762,00 | +4.503,37 |
| 2026 (`≤sep`) | 193 | +4.348,50 | +22,12 R | 257,75 | +2.455,00 | +2.143,35 |
