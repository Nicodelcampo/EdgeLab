# EXTERNAS-28 (114 variantes del catálogo externo) en M1 de futuros: 110 descartadas por fricción, 4 Dual Thrust con bruto real y neto ≈ 0 (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (114 pruebas contadas en `EXTERNAS_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `FASE0.json` (y `FASE0_{NQ,ES,YM,GC}.json`). Etapa EF2 → EF3.
Holdout A5 y terminal sellados; REP no se leyó.

## 1. Fase 0 (EF2, sin retornos): fricción en R
- Regla fijada antes: mediana de fricción canónica / riesgo inicial ≤ 0,08 R y ≥ 30 sesiones en DESC.
- **Pasan 4 de 114**, todas `EXT-DUAL-THRUST` (X036 k 0,35 obj 1,0; X037 k 0,35 obj 1,5; X038 k 0,5 obj 1,0; X039 k 0,5 obj 1,5): fricción
  mediana 0,038–0,041 R (NQ 0,033–0,037; ES 0,046–0,052; YM 0,031–0,034; GC 0,041–0,045). Las otras 110 quedan `DESCARTADA_FRICCION` (fricción
  mediana ≥ 0,08 R, casi todas ≥ 1 R: stops de pocos ticks en M1) sin mirar ningún desenlace.
- Nota de procedencia: GC se terminó con un segundo proceso en orden inverso (`EXTERNAS_REVERSO=1`); sólo cambia el orden de cálculo.

## 2. Fase 1 (DESC): ya medida por la auditoría de Gemini/Antigravity
- `../externas_estructurales_a5_20261118/AUDITORIA_DUAL_THRUST_EXTERNAS28.json` corrió exactamente X036–X039 en DESC (ES+NQ+YM+GC, 2006–2025):
  R bruto +0,033 / +0,036 / +0,053 / +0,054 (p 0,005 / 0,003 / 0,0005 / 0,0007; 75–80 % de años positivos) → pasarían BH q 0,10 entre las 4;
  **R neto −0,010 / −0,007 / +0,005 / +0,006** (fricción media 0,044–0,048 R); subconjunto operable (fricción ≤ 0,08 R) +0,006 a +0,027.
- No se repite esa medición (sería mirar dos veces lo mismo) ni se gasta Kaggle en calibrarla: aun nominadas, la lectura de REP exige potencia
  ≥ 0,8 con la mitad del efecto de DESC al nivel LORD++ (K49), y con un neto de −0,01 a +0,006 R la potencia es **0,01** (calculada con su ee).
- **Veredicto:** `SIN_POTENCIA_PREVIA` con bruto real y neto ≈ 0 — el mismo grupo que RQ5, SOM y FM1/FM2 (ruptura intradía con ventaja en
  puntos que la fricción se come). El bruto era más grande en 2006–2011 (+0,06 a +0,10, «limpios»): no es una pista que crezca.

## 3. Cierre del frente
- 110 `DESCARTADA_FRICCION` (alcance: esa implementación con stops de M1; no la idea en otra escala), 4 `SIN_POTENCIA_PREVIA` (neto ≈ 0).
- Lo reutilizable: la regla de fase 0 (fricción en R antes de mirar retornos) descartó el 96 % del catálogo sin gastar un solo desenlace.
