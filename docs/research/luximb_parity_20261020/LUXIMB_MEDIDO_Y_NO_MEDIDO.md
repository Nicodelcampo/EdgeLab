# LUX-IMB (ImbalanceDetectorLuxAlgoMTF, OG+VI) — registro MEDIDO / NO MEDIDO

## MEDIDO
- 2026-10-20 Paridad NT8->Python NQ DEC26 M1: logica 1507/1507, velas 99,98 %, punta a punta limpia 1373/1373. `PARIDAD_LUXIMB_NQ1226_20261020.md`.
- 2026-10-20 Exploratorio sin desenlaces de impulsos v5 en NQ 09-26 (151) y variante vida 200 (51). `EXPLORATORIO_IMPULSOS_LUXIMB_NQ_20261020.md`.
- 2026-10-20 M1/M2/M3 (rebalanceo, control sin zonas, continuacion) en descubrimiento NQ: SIN EFECTO, MDE 8,4 pp. `RESULTADOS_M1_M2_M3_LUXIMB_NQ_20261020.md`.

- 2026-10-20 M4 penetracion 25/38,2/50/61,8/75 % hasta A vs X: SIN EFECTO a favor (signo opuesto, -4 a -6 pp, no significativo). `RESULTADOS_M4_PENETRACION_LUXIMB_NQ_20261020.md`.
- 2026-10-20 Exploratorio sin desenlaces, modo 'inicio cargado' con piso 60 (150 en NQ 09-26). `EXPLORATORIO_IMPULSOS_INICIO_LUXIMB_NQ_20261020.md`.
- 2026-10-20 M5 vuelta al inicio cargado: SIN EFECTO (H1 +2,2 pp IC [-3,9,+8,3], MDE 8,6; fade +3,4 pts IC [-3,1,+9,5], inestable por contrato). `RESULTADOS_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md`.
- 2026-10-20 Exploratorio sin desenlaces de escalonadas 150t sobre area cargada (182 en NQ 09-26). `EXPLORATORIO_ESCALONADAS150_LUXIMB_NQ_20261020.md`.
- 2026-10-20 M6 escalonadas 150t: SIN EFECTO a favor de ruptura; signo opuesto H1 -3,6 pp IC [-7,1,-0,2] (no preregistrado), menos recorrido a 60 min; P&L neto negativo en T y C. `RESULTADOS_M6_ESCALONADAS_LUXIMB_NQ_20261020.md`.
- 2026-10-20 M7 ES (pista de M6): recorrido 60 min -14 % con area cargada (H2 -3,3 pts IC [-4,9,-1,6], Holm 0,0008) PROVISIONAL; ruptura/rechazo y P&L sin efecto. `RESULTADOS_M7_ES_AREA_CARGADA_20261020.md`.
- 2026-10-20 M7b control por vol previa: H2b +0,23 pts IC [-0,93,+1,45] (MDE 1,71) -> el freno de M7 era volatilidad de regimen (T aparece con vol_pre mediana 13,5 vs 22,3); H2 no se promueve; replicacion ES intacta. `RESULTADOS_M7B_CONTROL_VOLATILIDAD_ES_20261020.md`.
- 2026-10-20 M8 franjas adelante/atras (desbalance, 4 vidas) + GBM vs contexto, NQ (5.421) y ES externo (6.469): SIN EFECTO (MDE ~6 pp; ML no mejora). `RESULTADOS_M8_FRANJAS_DESBALANCE_20261020.md`.
- 2026-10-20 M9 distancia/tiempo + zonas tomadas/restantes: NQ H_m d25 rapido +6,6 pp (Holm 0,045) NO confirma en ES (-0,7 pp); H_k nulo; celdas lentas vacias. `RESULTADOS_M9_DISTANCIA_TIEMPO_ZONAS_20261020.md`.
- 2026-10-20 M11 grilla SL/TP/BE del fade del visor (40 celdas, IS/OOS/ES, entrada realista + costos): ninguna sobrevive; corr IS-OOS -0,04; OOS positivo por periodo; entrada en X explicaba ~5-9 pts. `RESULTADOS_M11_GRILLA_SLTP_20261020.md`.
- 2026-10-20 M10 multiactivo (MYM, GC, 6E, 6B, 6J, MBT): H1/H2 no transportan; H3 -4,7 pp (signo opuesto a NQ) y M10b con control de precio ya visitado -> +0,2 pp [-3,4,+3,8]: era confusion. `RESULTADOS_M10_M10B_MULTIACTIVO_20261020.md`.
- 2026-10-20 Tablero por periodo + CORRECCION de M11: la regla del visor realista da +4,95 pts/op en NQ (499, IC [+0,55,+9,2], 4/5 periodos positivos); ES ~0. CANDIDATO A HOLDOUT (no edge). `DASHBOARD_VISOR_POR_PERIODO_NQ_20261020.md`, `CORRECCION_LECTURA_M11_20261020.md`.

## NO MEDIDO
- Holdout (>= 2026-10-01) de la regla del visor realista en NQ: una vez, regla congelada; faltan datos de oct en adelante.
- M5 en ES/YM (unico camino para mas potencia en descubrimiento).
- Continuacion tras penetracion (signo observado en M4; necesita preregistro propio).
- Velas 25t contra NT8 (sin paridad).
- Vida 200 con desenlaces; otras geometrias de salida (p. ej. objetivo A, horizonte fijo).
- Otros instrumentos (ES, YM); zonas LUX-IMB individuales como soporte/resistencia.
- Replicacion abr-sep: comprometida para esta familia (diseno mirando NQ 09-26).
