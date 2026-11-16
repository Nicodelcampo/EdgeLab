# FUNDEDSYNC — acta de apertura del holdout (2026-11-16)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar. Sigue a `PREREGISTRO_CADENA.md` (las PISTA pasan a una apertura única).
Familia `FUNDEDSYNC`, sin aperturas previas. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

- **Congeladas:** módulos **T** (FtmEngine), **Z** (ZetaTrendDay) y **R** (AtrPhase) de `edgelab/research/fundedsyncstack`, valores de fábrica,
  1 contrato, costos NQ 1,5455 pts. Nada se ajusta.
- **Datos:** M1 del Nasdaq de desarrollo (USATECH, 2012 → 2026-09-29) como historia/calentamiento + **USATECH sellado** (ticks de Dukascopy,
  medio bid/ask, volumen de ticks) del 2026-10-01 al **2026-11-13**, pasado a M1 en el kernel (misma fuente que el desarrollo: sin salto de
  base). Sólo cuentan las operaciones con entrada ≥ 2026-10-01.
- **Hipótesis (k = 3):** neto por operación > 0. p de desarrollo declarada: T 0,01 (t 4,37 contra un p95 del nulo de 1,92), Z 0,05, R 0,10.
  Combinación Fisher por módulo.
- **Potencia (declarada antes):** T ≈ 19 operaciones/mes → ≈ 28 en el holdout, desvío ≈ 45 pts → error estándar ≈ 8,5 pts contra un efecto
  de desarrollo de +13 a +23: potencia moderada (≈ 0,5–0,8). Z y R ≈ 2–3 por mes → 3–5 operaciones: sin potencia, sólo dato.
- **Lectura:** T CONFIRMADA si neto > 0 y Fisher < 0,05; EN_CONTRA si neto ≤ 0 con su error estándar; si no, NO_CONCLUYENTE. Una sola vez;
  después, forward con e-proceso. Contador global: 3 pruebas.

Justificación económica / cómo podría refutarse: las de `PREREGISTRO_CADENA.md`.

## Nota (2026-11-16 08:2x UTC): primer intento sin datos del holdout
El primer kernel devolvió **0 operaciones** en T, Z y R: `load_m1_data` del paquete corta por defecto en `end="2026-10-01"` (guarda anti-holdout
de la traducción), así que no entró ninguna vela sellada. No se vio ninguna operación del holdout. Se corrige pasando `FIN=2026-11-14` y se
relanza dentro de la MISMA apertura (sin registrar otra); regla, datos y lectura sin cambios.
