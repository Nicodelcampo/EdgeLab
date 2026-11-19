# REGIMEN-SOM-FRANKLIN: los procedimientos de T-REGIMEN aplicados a SOM y Franklin (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «Iterá una vez más en confirmar SOM y Franklin como régimen real. Realizá los procedimientos que hiciste sobre T».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (desarrollo ya mirado, 2006 → 2026-09-29; ni REP de A5 ni holdout). **Familias:** `SOM` y `FRANKLIN`.
- **Herramienta:** `tools/regimen_som_franklin.py` (reusa los motores de `tools/m1_largo.py` — `quantlab_mt5_medir.ops_som` con
  `SessionOpenMomentumConfig` y `estrategias_scrapeadas.franklin_variantes` con `FRV_CELDAS` —, la fricción canónica, `g2.pbo_cscv`,
  `g2.parameter_sensitivity` y el sup-F de `tools/neto_pistas.py`). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: «SOM Franklin régimen meseta PBO quiebre» — T-REGIMEN (REGIMEN_ROBUSTO), F-SENALES-ESTABLES-SOM-FRANKLIN, NETO-PISTAS parte B
(S3 mejora SOM en NQ+ES+YM y no confirma en EMD+RTY), AUDITORIA_ANTIGRAVITY_20261119 (K52: no sumar puntos crudos entre épocas; se mide en R).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36, K38: la celda de Franklin se eligió dentro de esta misma grilla de 32; K48, K49,
K50, K51, K52).

Potencia previa: SOM NQ+ES+YM ≈ 14.500 operaciones y Franklin NQ+ES ≈ 3.950 en 20 años (sd ≈ 1,1–1,3 R): error estándar del R medio por
variante ≈ 0,01 (SOM) y ≈ 0,02 (Franklin) en la ventana completa; la mitad si la ventana posterior a un quiebre cubre ~5 años. Alcanza para
la forma de la grilla y la PBO.

## 0. Justificación económica
- SOM (impulso de la apertura de sesión con trailing por EMA) y Franklin (sesgo del día a las 10:00 NY contra el rango de Londres y el VWAP)
  tienen bruto positivo y estable 20 años: momentum de apertura y continuación del sesgo europeo. Si la ventaja es estructural, debería ser
  una meseta sobre su vecindario de parámetros (no un pico) y, si su neto depende de un régimen de fricción relativa baja (como T), debería
  mostrar un quiebre fechable a partir del cual el neto es una meseta.

## 1. Grillas (cerradas)
- **SOM** (celda `sin_finde`, cierre de viernes; NQ + ES + YM agrupados): `fast_ema` {8, 12, 16} × `trail_ema` {80, 120, 160} ×
  `trail_start_r` {0,25; 0,5; 0,75} × `sl_atr_mult` {6, 8, 10} = 81. Fábrica 12 / 120 / 0,5 / 8.
- **Franklin** (NQ + ES agrupados): las 32 celdas de `FRV_CELDAS` (hora de decisión {09:45, 10:00, 10:30, primera} × stop {rango, 0,5·ATR20}
  × filtro {ninguno, vwap_ny, sin_gap, vwap_ny+sin_gap}). Fábrica 10:00 / rango / ninguno. Vecinos: las celdas que difieren en un solo eje.
- R por operación = (bruto − fricción canónica) / riesgo inicial (igual que en las operaciones versionadas).

## 2. Decisión (por estrategia)
- **(a) Señal bruta, ventana completa 2006 → 2026-09:** `SENAL_ROBUSTA` si ≥ 70 % de las variantes tienen R bruto > 0, vecinos de la fábrica
  con mediana > 0 y PBO (bruto, meses × variantes, S = 16) < 0,3; `SENAL_FRAGIL` si PBO > 0,5 o < 50 % positivas; si no, `INTERMEDIA`.
- **(b) Régimen neto:** quiebre de la fábrica en R neto con sup-F (recorte 15 %, 300 permutaciones de meses). Si p ≤ 0,05, la ventana de
  decisión es desde el quiebre; si no, la ventana completa. En esa ventana, sobre el R neto: `REGIMEN_ROBUSTO` (≥ 70 % positivas, mediana ≥ 50 %
  de la fábrica, vecinos > 0, PBO < 0,3), `SOBREAJUSTE_PROBABLE` (PBO > 0,5 o < 50 % positivas), `INTERMEDIO` en otro caso.
- **Descriptivo:** años positivos de la fábrica antes y después del quiebre; R neto por instrumento; prueba de causalidad por prefijo de la
  fábrica (corte 2015-06-30: las operaciones hasta esa fecha coinciden con datos cortados).
- **Cómo podría refutarse:** (a) bruto que es un pico (vecinos ≤ 0) o PBO > 0,5 → la «señal estable» es selección; (b) sin quiebre y neto
  ≤ 0 en la mayoría de la grilla → no hay régimen neto; la prueba de prefijo con diferencias → hay look-ahead.
- **Contador:** 2 pruebas en `SOM` y 2 en `FRANKLIN` (a y b).
