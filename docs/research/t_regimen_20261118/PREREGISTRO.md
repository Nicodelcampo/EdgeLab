# T-REGIMEN: ¿el T de FundedSync desde 2021 es un régimen o un sobreajuste? Meseta de parámetros y PBO (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr. Propuesta y contexto: `PROPUESTA.md` (P-97).
- **Pedido de Nico:** «continuá con lo que habíamos dejado pendiente» (P-97: distinguir régimen real de sobreajuste desde 2020).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (diagnóstico sobre desarrollo ya mirado; no abre REP ni holdout). **Familia:** `FUNDEDSYNC` (linaje existente).
- **Herramienta:** `tools/t_regimen.py` (reusa `fundedsyncstack.correr_modulo("T", …, **cfg)`, el kernel de `m1_largo`, la fricción
  canónica de `embudo_runners.friccion`, `g2.pbo_cscv` y `g2.parameter_sensitivity`).

Antecedentes: «FundedSync T FtmEngine ORB KNN regimen sobreajuste» — familias parecidas: EL_DIA_TENDENCIA, FUNDEDSYNC, M1LARGO_EXTERNAS_20261117; NO_REPETIR: F-REELS-20261108, F-GEX-DIA-TENDENCIA, F-ORB-EMA20-NQ-STOP-OPUESTO, F-FUNDEDSYNC-SIN-VENTAJA; código: tools/fundedsync_tanda2.py:263, edgelab/research/fundedsyncstack/modulos_w_n_t.py:157, edgelab/research/fundedsyncstack/modulos_w_n_t.py:1131

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36 unidad R con el riesgo inicial de T, K38 ajuste del diseñador, K48, K49, K50).

Potencia previa: T en NQ 2021-02-10 → 2026-09-29 ≈ 1.300 operaciones en ≈ 1.300 días (una por día), sd ≈ 1,16 R/op; un efecto neto de
+0,08 R/op tiene error estándar ≈ 0,032 y potencia ≈ 0,80 a α 0,05 por variante. La decisión no es una prueba de media sino la forma de la
grilla (meseta contra pico) y la PBO, que usan las 81 variantes y 68 meses.

## 1. Justificación económica y qué se prueba
- T = ruptura del rango de apertura de 15 min en NQ con un KNN trimestral que invierte la dirección. Si su ventaja 2021+ es un régimen
  real (flujo de cobertura de gamma y 0DTE, Baltussen et al. 2021), debería sobrevivir a mover sus parámetros un paso a cada lado. Si es
  un sobreajuste del vendedor a 2020+, la configuración de fábrica debería ser un pico aislado y la selección por desempeño debería
  fallar fuera de la mitad elegida (PBO alta).

## 2. Población y grilla (cerrada antes de correr)
- NQ, M1 real de futuros NT8, 2008-01-02 → 2026-09-29 (desarrollo; nada del holdout). Ventana de decisión: desde el quiebre medido
  2021-02-10 (PROPUESTA §2) hasta 2026-09-29. Antes del quiebre se reporta igual (descriptivo).
- 81 variantes = `orb_bars` {10, 15, 20} (con `orb_end_minute_et = 570 + orb_bars`) × `knn_k` {10, 15, 25} ×
  `knn_flip_probability_threshold` {0,60, 0,65, 0,70} × `admission_min_close_location` {0,50, 0,60, 0,70}. Fábrica: (15, 15, 0,65, 0,60).
- R neto por operación = (pnl en puntos − fricción canónica de NQ) / riesgo inicial; riesgo inicial = clip(rango de los primeros
  `orb_bars` minutos × 1,25, 2, 100) (la misma regla que `_orb_t` para la fábrica).

## 3. Decisión (fijada antes de mirar)
- **Meseta:** ≥ 70 % de las 81 variantes con R neto > 0 en la ventana de decisión, y mediana de la grilla ≥ 50 % del R de fábrica, y
  mediana de los vecinos ±1 paso de la fábrica > 0 (`parameter_sensitivity`).
- **PBO** (`g2.pbo_cscv`, S = 16 bloques sobre la matriz meses × variantes de R neto sumado por mes, ventana de decisión).
- **Veredicto:** `REGIMEN_ROBUSTO` si hay meseta y PBO < 0,3; `SOBREAJUSTE_PROBABLE` si PBO > 0,5 o < 50 % de variantes positivas;
  `INTERMEDIO` en otro caso.
- **Cómo podría refutarse:** la fábrica es un pico (vecinos ≤ 0) o PBO > 0,5.
- **Descriptivo, sin decisión:** (a) la misma grilla 2008-01 → 2021-02-09 (¿todas negativas antes del quiebre? → régimen y no
  parámetro); (b) el mecanismo de gamma ya se midió con la canasta que incluye T (`F-GEX-DIA-TENDENCIA`, NO_REPETIR): no se vuelve a
  probar acá.
- **Contador:** 1 prueba (el veredicto) en `FUNDEDSYNC`. Se elige NADA por desempeño: la fábrica sigue siendo la regla; la grilla sólo
  mide su vecindario.

## 4. Pendiente fuera de esta corrida
- Prueba 2 de la propuesta (datos que el vendedor no vio): falta la fecha de compra o de la versión de FundedSync (Nico).
- Prueba 4 (vigilancia secuencial en papel): se diseña si el veredicto no es `SOBREAJUSTE_PROBABLE`.
