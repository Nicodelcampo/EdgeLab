# SOM (SessionOpenMomentum) — acta de apertura del holdout (2026-11-16)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar. Familia `SOM`, sin aperturas previas. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Candidato que pasó su regla pre-registrada (`RESULTADO_SOM.md`).

- **Congelada:** `quantlab_mt5.correr_session_open_momentum` con la configuración de fábrica + `close_weekend=True` (celda `sin_finde`,
  enmienda 2: mantiene la posición de noche entre semana y cierra el viernes a las 15:55 NY). Sólo **NQ**. Costo 1,5455 pts. Nada se ajusta.
- **Datos:** M1 de desarrollo (USATECH, 2026-01 → 2026-09-29, hora del servidor) como historia + **USATECH sellado** (spot Dukascopy)
  2026-10-01 → **2026-11-13**, pasado a M1 y a hora del servidor en el kernel (`tools/kaggle_grilla/som_main.py`). Cuentan las entradas
  ≥ 2026-10-01; sesiones excluidas de `edgelab/holdout.py` fuera.
- **Hipótesis (k = 1):** R neto por operación > 0. **p de desarrollo declarada: 0,039** (la mayor de los dos tramos: A 0,039, B 0,001).
  Combinación Fisher (p del holdout por t con aproximación normal, unilateral).
- **Potencia:** ≈ 25–30 operaciones, desvío ≈ 0,9 R → error estándar ≈ 0,17 R contra +0,075 R: potencia baja (≈ 0,15). Puede refutar si
  sale muy en contra; casi no confirma solo. Decide el forward (`tools/som_seguimiento.py`, dentro de `tools/seguimiento_forward.py`).
- **Lectura:** CONFIRMADA si R > 0 y Fisher < 0,05; EN_CONTRA si R < −1 error estándar; si no, NO_CONCLUYENTE. Una sola vez.
- Correlación de desarrollo (ago-25 → sep-26, diaria): v2 0,03, Cartera B 0,30, Franklin 0,42 (comparten la apertura de NY); mensual ≤ 0,18.

Justificación económica / cómo podría refutarse: las de `PREREGISTRO_MEDICION.md`.
