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

### Adenda 1 — cotas desde la Fase 0 (2026-10-23, antes de la Fase A)
- **Fase 0** (kernel `edgelab-u1b-fase0-nq`, `u1/fase0_operaciones.csv`): 69 operaciones, media +7,26, IC90 [1,19, 12,84]. Reproduce exacto la selección.
- **Extremos de la Fase 0:** peor −147,05 y mejor +51,95 pts.
- **Cotas:** 1,5 × cada uno. La cola izquierda es pesada (stop más allá del extremo), así que el e-proceso crece despacio. Es el costo honesto del stop amplio.

```json
{"piso": -220.575, "techo": 77.925, "mu_util": 3.65, "alfa": 0.003608, "alfa_futilidad": 0.10}
```

### Adenda 2 — resultado: LIMITE_VIOLADO en la Fase A; U1-B no se sostiene (2026-10-23)
- **Seguimiento** (`u1/SEGUIMIENTO_U1B.jsonl`, `u1/faseA_operaciones.csv`): se detuvo en la operación 42 de la Fase A con
  **LIMITE_VIOLADO**. Esa operación perdió −241,05 contra un piso declarado de −220,58. Al detenerse: n = 41, media −2,09,
  e_edge 0,82 (umbral 277) y e_futilidad 0,94 (umbral 10). Por la regla, las cotas no se mueven ni se recorta el valor.
- **Fase A completa, descriptiva** (`u1/faseA_resumen.json`): 91 operaciones en 46 sesiones, media **−0,18** pts/op, IC90
  [−10,1, +8,5], p = 0,53. Mediana +13,95, peor −241,05. Lo que en la exploración daba +7,3 no aparece en los seis meses
  siguientes; es la caída esperada por la selección.
- **Fase B (holdout): calculada localmente (85 disparos) pero NO inspeccionada.** El seguimiento se detuvo antes de llegar a ella.
  Los archivos derivados se borraron sin leerse y no forman parte de ninguna decisión. La apertura del holdout de U1-B queda
  sin uso efectivo: si Nico quiere, se puede considerar no consumida.
- **Veredicto: U1-B queda REFUTADA en NQ** (la media no supera 0 en datos nuevos).
  - **Lo que muere:** exactamente esta celda, en NQ, con esta ejecución.
  - **Lo que no muere:** la familia AREAS-EXP-1, ni lo aprendido por las marginales de USATECH (el alejamiento ordena el
    retorno, el VWAP, el volumen en la ida), que en NQ no se pudo medir con potencia.
- **Error de método:** las cotas salieron de 69 operaciones de una estrategia con cola izquierda pesada y sin pérdida máxima
  estructural. 1,5 × el peor caso visto no alcanzó. Regla nueva (guía): un seguimiento secuencial exige que la regla tenga
  pérdida máxima por operación por construcción (stop con tope), o cotas estructurales; nunca cotas sacadas del peor caso observado.
