# Acta — seguimiento secuencial de U1-B y apertura del holdout (2026-10-23)

Estado: VIGENTE. La regla de decisión quedó **registrada antes de mirar** cualquier dato de confirmación. OK de Nico en el chat del
2026-10-23, que aprobó la opción recomendada: seguimiento secuencial desde NQ abril 2026 y hacia adelante desde el 2026-10-01,
con apertura del holdout por protocolo.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia: AREAS-EXP-1. Candidato: **U1-B** (`SPEC_U1_INDAGA.md` §Resultado). Una sola apertura del holdout para este candidato.

## Regla congelada
- **Celda:** `[0, 2, 1, 2, 2, 2, 3, 3, 3, 0]` del experimento `edgelab.research.u1_indaga`:
  - N ≥ 3, x = 0,15 y A/H ≥ 8;
  - volumen, velocidad, franjas y VWAP «cualquiera»;
  - ejecución `E1A, T1, S3, sin BE`: tick siguiente, objetivo en el borde cercano, stop más allá del extremo.
- **Cortes:** los del E0 de NQ en `u1/ELEGIBLES_USATECH.json::cortes_nq`. Esta celda no usa ninguno, pero quedan fijos.
- **Fricción:** canónica de NQ, 1,5455 pts (`edgelab/costos.py`).
- **Código:** el commit de esta acta. La serie por operación sale de `grilla_generica.operaciones_de`.

## Datos, en orden
- **Fase 0:** exploración de NQ, 2025-08-05 → 2026-03-31. Ya usada; sirve sólo para fijar las cotas del e-proceso.
- **Fase A:** NQ 2026-04-01 → 2026-09-30 (release de Kaggle, última sesión 2026-09-25). Nunca miradas para esta familia.
- **Fase B (holdout):** NQ 12-26 desde la sesión del 2026-10-01 (`E:\DatosNT8\tick_history_HOLDOUT_SELLADO\NQ_12-26_ticks.parquet`).
  - Se leen sólo sesiones completas, con `fuentes_ticks.bloques_nq_sellado`, que exige esta acta.
  - Hueco documentado: 7–8 de octubre.
  - Sigue con cada sesión nueva.
- **Advertencia:** las mismas sesiones del holdout se usaron para la mirada exploratoria de otro candidato de LUX-IMB, el de la familia
  IMPULSOS. Son familias independientes según la regla de familias, pero el indicador de zonas es el mismo.

## Decisión (e-proceso, `edgelab/funnel/secuencial.MonitorCandidato`)
- **Serie:** P&L neto por operación, en orden de tiempo. Se acumula de la Fase A a la Fase B y se puede mirar en cualquier momento (Ville).
- **Confirmación de edge:** H0 es E[x] ≤ 0; confirma si e ≥ 1/α.
  - α = **0,003608**: paso 2 de LORD++ de la familia. El paso 1 fue el lote de 80 réplicas de v1.4, sin rechazo y contado como un solo paso.
  - Umbral: **e ≥ 277,2**.
- **Futilidad:** H0 es E[x] ≥ 3,65 pts/op (la mitad de lo observado en la exploración de NQ, como G4), con α = 0,10. Se descarta si e ≥ 10.
- **Sin decidir:** si no cruza ninguno, el estado es SIN_DECIDIR y el seguimiento sigue con datos nuevos.
- **Cotas (piso, techo):** se fijan en la Fase 0 como 1,5 × la peor pérdida y 1,5 × la mejor ganancia de U1-B en la exploración de NQ.
  Se escriben en este acta (adenda) y se committean ANTES de la Fase A. Una operación fuera de las cotas detiene el seguimiento con
  LIMITE_VIOLADO, sin recortar.
- **Lo que no se hace:** no se cambia la regla, ni las cotas, ni α al ver resultados. No se prueba otra celda con estos datos.

## Adendas (append-only)
