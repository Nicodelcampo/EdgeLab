# CARRIL2-CIERRE: IBS, Double Seven, Turnaround Tuesday y cambio de mes entrando al cierre de las 15:55 en lugar de las 18:00 (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Pedido de Nico:** «entrada al cierre en Carril 2: primero habría que ver si ese desvío mató el efecto». El lote 1 entró a las 18:00 (desvío
  declarado); la literatura (QS, Connors) define estas reglas con entrada en el cierre RTH. Sólo cuenta de broker (varios días; Lucid no admite
  overnight).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** en DESC de A5 (REP sólo si se nomina, con potencia K49). **Familia:** `CARRIL2_A5` (8 pruebas más).
- **Herramienta:** `tools/carril2_cierre.py correr|desc`: mismo motor calibrado (`sqx_catalogo.simular`, K28) y mismas señales
  (`carril2._senales`), con dos cambios de datos, no de lógica: (1) las señales se calculan con la barra RTH del día (09:30–15:55: IBS, máximo y
  cierre previos, SMA200, ATR20, mínimos/máximos de 7); (2) la barra de ejecución va de 15:56 a 15:55 del día siguiente (el viernes 15:56 se une
  al lunes), así que la entrada a mercado de la barra siguiente se llena a las 15:56 y las salidas por regla salen al cierre de las 15:55.
  Partición: entrada en DESC y salida fuera de HOLDOUT/EMBARGO (assert), igual que el lote 1.

Antecedentes: CARRIL2-LOTE1 (entrada 18:00: IBS +0,017, D7 +0,079, TT +0,059, TOM +0,034 en DESC; 0/8 BH), RE_INDAGACION y MIRADA_HUMANA
(IBS y D7 pierden concentrado en meses de crisis desde 2018), QS (IBS: entrar más tarde baja el retorno 0,41 → 0,31 %).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36, K40, K48, K49, K51, K53, K55/K56).

Diagnóstico de mecanismo: no hay grilla (reglas fijas del lote 1); la única diferencia es la hora de entrada/salida. Se publica la descomposición
por meses (Episodios) de cada regla y del contraste.

Potencia previa: el lote 1 tuvo 353–650 operaciones por regla en DESC (ee 0,05–0,08 R); con entrada al cierre el número es similar: MDE ≈ 0,15–0,2 R
por regla; el contraste es pareado por fecha de señal (misma señal, distinta hora), con ee menor.

## Justificación económica
- La presión vendedora que crea un cierre débil (IBS bajo, mínimo de 7 días, lunes flojo) se descarga en la subasta de cierre y en la noche;
  entrando a las 18:00 se pierde la primera hora de la reversión (16:00–17:00, sesión extendida). Si el efecto vive ahí, la versión al cierre
  debería rendir más que la de las 18:00.

## Pruebas (8, BH q 0,10 entre ellas)
- Por regla (IBS+VIX, Double Seven, Turnaround Tuesday, cambio de mes; ES+NQ+YM+RTY, D7 también GC): (a) R neto de la versión 15:56 > 0;
  (b) contraste 15:56 − 18:00 sobre las mismas señales (pareado por fecha e instrumento) > 0. Bootstrap por sesión, p unilateral.
- **Cómo podría refutarse:** el contraste ≤ 0 (el desvío no mató nada) o el neto al cierre ≤ 0.
- **Contador:** 8 pruebas en `CARRIL2_A5`.
