# Relanzamiento de análisis viejos con el EdgeLab actual — inventario y prioridad

Estado: VIGENTE
Fecha: 2026-10-25. Pedido de Nico: «revisá profundamente todos los historiales; muy probablemente casi todos estuvieron mal hechos,
así que se pueden relanzar con la versión actualizada y los resultados serán sustancialmente distintos».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Qué cambió desde entonces (los defectos que hacen que valga la pena relanzar)

| código | defecto de las corridas viejas | qué lo corrige hoy |
|---|---|---|
| **N** | poca muestra: 5 días, 6–16–25 sesiones, «4 meses» de un contrato. Un nulo así no distingue ausencia de falta de potencia | Dukascopy 2023-01 → 2026-09 (≈ 3,7 años, 6 activos, recortado antes del holdout) + `liquid_tick_v1` jul-2025 → sep-2026 |
| **F** | corrección FWER sobre toda la grilla (max-T, Holm, Bonferroni, `p_max`): mata una celda real si la grilla es grande | tamiz FDR (Storey, q 0,10) sobre celdas evaluables + pistas en lote a réplica (Simes, un paso de LORD++) |
| **M** | MCPT de G2 original, que medía concentración temporal y castigaba al edge estable (enmienda G2-A1) | inferencia primaria por bootstrap de sesiones (`escalera.resumen_sesiones`) |
| **V** | denominador del FDR con celdas vacías (< 30 ops) | `m` = evaluables (D6, `EVALUABLES.jsonl`) |
| **C** | costos del feed NT8, comisión supuesta, tablas locales, o costos transportados entre instrumentos | `edgelab/costos.py` (spread medido + comisión máxima de firmas con algoritmos + slippage G3) |
| **E** | escala nominal fija (pts o ticks) aplicada a años con volatilidad distinta | escala causal (rango del período anterior), como U1-ORO-GRILLA |
| **R** | sin canal «reciente» declarado: el pasado mataba lo que funciona ahora | ventana reciente declarada antes de mirar (ATJ-24) |

Una corrida vieja con el defecto **N** o **F** sobre una celda que estaba cerca es la que más puede cambiar. Una con muestra grande,
potencia alta y nulo medido contra un control bien construido (por ejemplo AVCL D1/D2, BigTrap2 imán) **no** cambia por relanzarla:
ahí el defecto no era de inferencia.

Custodia (sin cambio): todo relanzamiento es desarrollo (EF2/EF3) sobre las sesiones ya vistas; los años de Dukascopy que esa
familia **no** usó sí son datos nuevos para ella, y eso es lo que hace valioso relanzar. La confirmación sigue siendo réplica no mirada
(abr–sep 2026 en CME, una vez por familia) y después holdout a N fijo.

## 2. Inventario (familias que midieron P&L o dirección)

| familia (doc) | qué murió y cómo | defectos | relanzar | por qué |
|---|---|---|---|---|
| **C-TICKS F4 cierre de gap** (`CAMPANA_TICKS_MULTI_RESULTADOS_20260923.md`) | MCPT p 0,001 (ES), 0,001 (NQ), 0,019 (YM); «sin potencia: 25–56 trades en 4 meses»; 6E F4 v3 +18,9 t IC [6; 32] tumbada por MCPT p 0,074 | N, M, C, F | **1.º** | la señal de timing ya estaba; faltaba muestra. Con 3,7 años de USATECH/USA500/USA30 la potencia sube ×10 |
| **GC espejo P1/P2** (`RESULTADO_GC_P1_P2_20260929.md`) | +0,080 W, IC [+0,035; +0,123], t 2,93 < 3,09 de max-T sobre 30 celdas | F, N | baja (revisado) | además de max-T murió por economía: la degradación tick a tick (−0,034 W) deja el neto en ≈ −0,01 W; la ventaja es relativa al control, no absoluta |
| **AVZP2 racimo, salida a favor de tendencia** (`AVZP2_RACIMO_REPLICA_ES_NQ_RESULTADOS_20261014.md`) | no murió: replicó 6/6 y 7/7 en ES; el manifiesto de P&L quedó **propuesto y nunca corrido** | — | baja (revisado) | su propio prior es negativo: MFE mediana 3 ticks contra fricción canónica de ES 0,8877 pts = 3,55 ticks |
| **EdgeReplica USATECH** (`edgereplica_usatech/RESULTADO.md`) | sobrevive (+4,08 pts, IC [+2,94; +5,27]), creciente hacia el presente; post-publicación negativo con n 14 | R | baja (revisado) | las mismas reglas ya abrieron su holdout en MNQ (`ghost_edgeexperiment_re_20261003`): −4,4 ticks, `EDGE_NO_CONFIRMADO` |
| **Escalonadas MNQ / EURUSD 500t** (`RESULTADO_MNQ_ESCALONADAS_ESCALAS_20260930.md`, `eurusd_escalonadas_20261021/`) | 0/648 max-T; 500t positivas (+0,15 R; mejor +0,45 R, n 39) «sin potencia» | F, N | 5.º | sólo la escala grande; Dukascopy da años |
| **Discovery f1–f5** (`discovery_20261004/RESULTADO_FAMILIAS.md`) | GC `p_max` 0,0074 (f1), Holm sobre 15 → 0,112; D0 ≈ 110 sesiones | F, N, V | 6.º | XAU/USATECH multi-año; ojo: la celda 04:30 no replicó en D1 (señal ya débil) |
| **ORB0100** (`orb0100_20261021/`) | IS −1,35, OOS +2,27, ES −0,44; n 62–178 | N | **hecho 2026-10-25: EN CONTRA** | celda congelada sobre USATECH 2023-01 → 2025-08: −1,01 pts/op, IC90 [−3,25; +1,22], MDE 3,36 |
| **R3 dirección 15–60 min** (`R3_DIRECCION_15_60M_RESULTADOS_20261014.md`) | H 30–60 «sin potencia» (MDE 5–8 pp contra 2–3 pp) | N, F | 8.º | idem |
| **OU-1 GC 04:30** (`ou_20261012/RESULTADO_OU1.md`) | reversión en spot 2022-25 p 0,019, Holm 0,115 | F | 9.º | vecina de la 04:15 (ya analizada por Nico): baja prioridad |
| **IVC** (`IVC_RESULTADOS_20260926.md`) | 38 FDR, 0 «prometedoras» (exigía IC inferior > costo en descubrimiento) | C | 10.º | revisar el criterio, no la inferencia |
| **EMASEP-MGC150**, **MGC EMA** | p_max 0,0998 sobre 21 celdas; spot 2022-25 ya probado (p_max 0,19) | N, F | baja | ya tuvo su réplica en spot y no apareció |
| **VTD, espejo REV/CONT, GEX** | 5 días, 6 contratos, 16–20 sesiones | N | baja | dependen de L2/feed NT8: Dukascopy no los reproduce |
| **Corredor EMA k28–k36** | mejor neto −1,28 t: la fricción se come el bruto | — | no | murió por economía, no por inferencia; la variante con estiramiento A/H es familia nueva |
| **AVCL dirección, BigTrap2 imán, LUX M10 H3, PRED-*** | potencia alta o controles que explican el efecto | — | no | el defecto no era de inferencia |

## 3. Orden de trabajo

1. Lo que ya está andando: U1-ORO-GRILLA por el embudo (INTEGRIDAD); U1-CRUZADO espera datos forward (8 de ≈ 95–150 operaciones).
2. **GAP-RTH** (F4 relanzada): pre-registro `docs/research/gap_rth_20261025/PREREGISTRO_GAP_RTH.md`.
3. Escalonadas 500t en años de Dukascopy; discovery f1–f5 multi-año; ORB0100 y R3 en USATECH (los de defecto N/F).
4. El resto según la tabla, de a uno, cada uno con su pre-registro y su registro global antes de correr.
Revisado al leer cada acta a fondo (2026-10-25): GC espejo, AVZP2 P&L y EdgeReplica bajan; los tres tienen una muerte que no es de
inferencia (economía, prior propio negativo, holdout ya abierto).

Cada resultado se agrega a esta tabla (columna «relanzar» → resultado) en el mismo commit que el resultado.
