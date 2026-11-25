# RQ5-REGIMEN: apertura del holdout A5 autorizada por Nico, sólo hasta el 2026-09-30 (adenda, 2026-11-20)

Estado: PRE-REGISTRO — adenda del `PREREGISTRO.md`. Se commitea y se registra la apertura ANTES de calcular cualquier desenlace del holdout.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Decisión humana (Nico, 2026-11-20):** «Abrí solo el holdout que corresponda a fechas anteriores al 30 sep 2026». Responde a
  `RESULTADO.md` §Holdout. La compuerta K27 (potencia ≥ 0,8 para gastar la única apertura) es una regla de validación y la levanta Nico
  **para esta apertura**; el registro guarda la potencia real y la autorización.

Antecedentes: RESULTADO.md de esta carpeta (REGIMEN_ROBUSTO en DESC 2018–2025: +0,050 R, p 0,045; 3 de 4 índices).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27/K42 potencia y alfa de la apertura, K49, K51, K56 episodios).

Potencia previa:
- **N:** 1.871 operaciones de la fábrica en los meses HOLDOUT de A5, 2018-01-01 → 2026-09-30, cinco índices. Se contaron sin desenlaces:
  NQ 367, ES 373, YM 368, RTY 389, EMD 374.
- **Potencia** (α 0,05, una cola, sd 1,0): **0,69** con el efecto de desarrollo (+0,050) y **0,28** con la mitad.
- **Lectura:** un resultado no significativo no mata (K49); se publica su MDE.

Diagnóstico de mecanismo: no aplica a la grilla. Se lee una sola regla congelada. Se publican los episodios por mes del holdout (K56) y el
resultado por índice.

## Qué se abre (fijo)
- **Ventana:** meses con bloque HOLDOUT de A5 (`edgelab/holdout.py::a5_bloque`) entre 2018-01-01 y **2026-09-30**. Los meses de 2025-08 →
  2026-09 entran porque A5 los asigna así.
- **Nada desde la sesión del 2026-10-01** (terminal sellado, HOLDOUT-A4): queda cerrado.
- **Regla congelada:** la fábrica `L60_m1_c689|P_obj_s0.45_tp2_stop_s0.45_tp2_fin`, idéntica a la RQ5 original. P3 no se adoptó. Sin
  cambios.
- **Instrumentos:** NQ, ES, YM, RTY y EMD (EMD con spread estimado declarado, K33).
- **Medida:** R neto = r bruto − fricción canónica / riesgo, con el motor único `ejecucion.py` calibrado.
- **Prueba primaria:** media de R neto > 0 en las 1.871 operaciones, bootstrap por sesión, p de una cola.
- **Combinación:** Fisher con la p de desarrollo (0,0445).
- **Lectura:**
  - **CONFIRMA:** p del holdout < 0,05;
  - **APOYA:** p de Fisher < 0,05 pero p del holdout ≥ 0,05;
  - **NO_CONCLUYENTE:** media > 0 sin significancia;
  - **EN_CONTRA:** media ≤ 0, con su MDE.
- **Se informa además:** el resultado por índice, los cuatro que votan juntos, los episodios por mes y el tramo 2025-09 → 2026-09 aparte.
- **Una sola apertura,** que consume también la de la familia padre `ROBOQUANT_A5` para RQ5. El resultado no se usa para elegir, ajustar
  ni reintentar.

## Cómo podría refutarse
Media ≤ 0 en el holdout, o positiva sólo por un índice o por pocos meses.
