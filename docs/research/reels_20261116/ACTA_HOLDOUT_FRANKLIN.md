# FRANKLIN — acta de apertura del holdout (2026-11-16, modo exploratorio)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar. Familia `FRANKLIN`, sin aperturas previas. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Modo exploratorio (decisión de Nico 2026-11-08): no hay candidato
confirmado por BH; se declara antes la probabilidad de azar de desarrollo y la combinación.

- **Congelada:** `estrategias_scrapeadas.franklin_variantes` con la celda `("1000", "rango", "ninguno")` = la regla base (a las 10:00 NY,
  cierre de la vela 09:59 arriba del máximo de Londres 03:00–09:30 y del VWAP de sesión → compra; abajo de los dos → venta; stop en el
  extremo opuesto de 09:30–10:00; salida al cierre 16:00). La búsqueda de mejoras no encontró nada mejor (`PREREGISTRO_FRANKLIN_MEJORAS.md`).
  Costos: NQ 1,5455 pts, ES 0,8877 pts. Nada se ajusta.
- **Datos:** M1 de desarrollo (USATECH, USA500; 2024 → 2026-09-29) como historia + **spot sellado** de Dukascopy (USATECHIDXUSD,
  USA500IDXUSD) del 2026-10-01 al **2026-11-13**, pasado a M1 en el kernel (`tools/kaggle_grilla/franklin_main.py`). Sólo cuentan las sesiones
  ≥ 2026-10-01; las excluidas de `edgelab/holdout.py` se descartan en el lector.
- **Hipótesis (k = 1):** R neto por sesión (NQ + ES sumados) > 0. **p de desarrollo declarada: 0,093** (base en 2023 → 2026-09, NQ+ES
  juntos; es la más conservadora de las que hay: 2020–26 daba 0,018 en NQ y 0,037 en ES). Combinación: **Fisher** (p del holdout por t de
  las sesiones con aproximación normal, unilateral).
- **Potencia (declarada antes):** ≈ 31 sesiones × 2 índices, con sesgo alineado ≈ la mitad de los días → ≈ 30 operaciones; desvío ≈ 1 R →
  error estándar ≈ 0,2 R contra un efecto de desarrollo de +0,1 R. **Potencia baja (≈ 0,15–0,25)**: el holdout puede refutar si sale muy en
  contra, pero casi no puede confirmar solo. Lo que no se resuelva lo decide el forward (e-proceso) desde el 2026-11-14.
- **Lectura:** CONFIRMADA si R > 0 y Fisher < 0,05; EN_CONTRA si R < −1 error estándar; si no, NO_CONCLUYENTE. Russell y YM no replicaron
  en desarrollo y no entran.
- **Filtro de T (descriptivo):** con el sesgo por minuto del kernel se marcan las operaciones T del holdout ya abierto de FUNDEDSYNC (26 ops):
  a favor vs resto. Con n tan chico no decide nada; decide el forward.
- Una sola vez. Contador global: ya contado (FRANKLIN 7 + FRANKLIN_MEJORAS 67).

Justificación económica / cómo podría refutarse: las de `PREREGISTRO.md` §4–5 (la aceptación de NY por encima/debajo de Londres y del precio
medio ponderado marca la dirección del día; se refuta con R ≤ 0 fuera de muestra).
