# LUXIMB-HVN — MEDIDO / NO MEDIDO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cada resultado). Pre-registro: `PREREGISTRO.md`.

## MEDIDO
| fecha | qué | datos | resultado |
|---|---|---|---|
| 2026-11-11 | Tablas de desarrollo (4 kernels) + exploración (`EXPLORACION.md`, 4.767 celdas por corte) | NQ y USATECH, 2025-08 → 2026-09; 32.180 eventos únicos; visor 925 | **Nada sobre el nulo de la búsqueda**: mejor t 1,5–1,9 contra un mejor-por-azar de mediana 2,7 (p95 3,5) en todos los cortes. |
| 2026-11-11 | H-ZONAS (previa): visor − control, E0 stop 0,5·D objetivo 1,0·D | ídem | R neto +0,04 / +0,17 / +0,09 / +0,005 (NQ DESC, NQ REP, USATECH DESC, USATECH REP): 4/4 ≥ 0; visor ≈ 0 absoluto, control < 0. PISTA_VIVA (`F-LUXIMB-ZONAS-VS-CONTROL`). |
| 2026-11-11 | H-HVN-1 y H-HVN-2 (previas) | ídem | **SIN POTENCIA**: hvn_1440 ≥ 2 en 3 de 925 eventos del visor (p99 1,59). La definición no sirve para probar el mecanismo; en el control, hvn alto toca A menos (0,46 vs 0,54). `F-LUXIMB-HVN-DEFINICION`. |
| 2026-11-11 | Regla del visor tal cual (stop 0,2·D, objetivo A) | ídem | R neto +0,10 / +0,23 / +0,10 / −0,21 con fricción 0,10 R (no elegible por la guarda de 0,08). |
| 2026-11-11 | Confirmación H-ZONAS (USATECH 2023–2025, una vez) | 625 visor / 5.181 control | +0,056 / +0,048 R, 4/5, p 0,27 / 0,40, MDE 0,15: NO_CONFIRMADA (sin potencia). |
| 2026-11-11 | LUXIMB-HVN2 (nodo relativo + VWAP) exploración | NQ y USATECH | Nada sobre el nulo (mejor t 2,4–2,7 vs p95 3,4–3,6). `hvn2/EXPLORACION.md`. |

## NO MEDIDO
- Confirmación en USATECH 2023-01 → 2025-07 (se genera después de congelar hipótesis).
- Señal en USATECH con ejecución en NQ (cruzado, como U1-CRUZADO): iteración posible.
- Veto por clusters HFT grandes más allá de B (`F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-D`): iteración posible.
- Gestión (parcial/BE) en la entrada EXT; entradas límite en la franja del HVN.
