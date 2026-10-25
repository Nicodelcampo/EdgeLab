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
- 2026-10-21 MIRADA EXPLORATORIA del holdout NQ 12-26 (1-20 oct, n=14): 14 SL / 0 TP, -20,15 pts/op. Apertura limpia de estas sesiones consumida (decision de Nico). `CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`.
- 2026-10-22 ESCALERA DEL EMBUDO con costos CANONICOS (NQ 1,545 pts/viaje; la campana habia usado 0,725): regla del visor realista +4,05 pts/op (+0,20 R), IC90 [+0,01, +0,38] R, p = 0,036, t = 1,8 sobre 212 sesiones; con 46 pruebas en su familia el efecto esperado tras seleccion es ~0 (DSR 0,33) -> **SIN_POTENCIA** (viva, ~950 op. para distinguirla del cero). Economico canonico: pasa los 4 duros (sin top-5 > 0, ningun periodo > 80 %, adverso +0,17 R; 4/6 periodos > 0). Los 6 periodos pre-holdout se miraron antes de congelar: no hay replica limpia previa al holdout. Holdout ya consumido (14 op.) con monitor secuencial: **SIN_DECIDIR** (e-edge 0,38; e-futilidad 2,2 de 10). `docs/research/auditoria_embudo_20261022/ESCALERA_CANDIDATOS_REALES.json`.

- 2026-10-22 FUTURO vs INDICE (NQ 09-26 vs USATECH Dukascopy, 1-jul..14-sep, target-free): 12 % de los OG y 17 % de los VI del futuro nacen tambien en el indice (mismo minuto y precio tras la base; por azar ~0). Comportamiento del precio del futuro, coincidentes vs no (registro `luximb_20261022/coincidentes_fut_vs_cfd`, 6 pruebas, Holm): ninguna diferencia significativa. La mayor, VI reaccion a 30 min: +5,2 vs +1,1 pts (dif +4,0, IC [-0,6, +8,7], p Holm 0,42); OG relleno 91 % vs 97 % (p Holm 0,27). MDE ~6 pts en VI y ~10 pp en relleno OG: sin potencia para efectos chicos. `COMPORTAMIENTO_COINCIDENTES_NQ_USATECH.json`, `ZONAS_NQ_VS_USATECH_tol*.json`.

- 2026-10-22 PRUEBA PRE-REGISTRADA VI coincidentes futuro/indice, reaccion a 30 min (ago-2025..mar-2026, 5.414 VI, 1.261 coincidentes, 155 dias; 1 prueba): coeficiente controlado por tamano/hora/direccion -0,20 pts, IC90 [-1,79, +1,29], p 0,60 -> **REFUTA** (la cota optimista no llega a la friccion de 1,55 pts; MDE 2,3 pts). La pista de jul-sep 2026 (+4,0) era seleccion: mejor de 6 pruebas. Diferencia cruda +0,11 pts; por contrato -0,83 / +0,02 / +1,04. Alcance: solo VI, reaccion a 30 min, NQ vs USATECH. `PREREGISTRO_VI_COINCIDENTES_REACCION_20261022.md`, `RESULTADO_VI_COINCIDENTES_REACCION_20261022.json`.

- 2026-10-24 RECÁLCULO del candidato sobre el **release de Kaggle** (`edgelab-liquid-ticks-20261014`, NQ sha256 `cccc7c80…`) con **costos canónicos** (`edgelab/costos.py`, base 1,5455 / adverso 2,0455 pts), 1 prueba registrada: reproduce exacto los 6 períodos (500 op., 212 sesiones). Neto **+4,05 pts/op** (IC90 [+0,36, +7,56]), adverso +3,55; en R +0,198 [+0,013, +0,375], 47 pruebas en la familia, DSR 0,33 -> **SIN_POTENCIA** (igual que el 22/10, ahora sin depender de bundles locales). PROVISIONAL (release candidato). `RESULTADOS_RECALCULO_CANONICO_RELEASE_20261024.md`, `RECALCULO_CANONICO_RELEASE_20261024.json`.

## NO MEDIDO
- Holdout (>= 2026-10-01) de la regla del visor original en NQ: **CONGELADA** 2026-10-21 (`CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`); faltan datos de oct en adelante y alta en el protocolo del autopilot.
- M5 en ES/YM (unico camino para mas potencia en descubrimiento).
- Continuacion tras penetracion (signo observado en M4; necesita preregistro propio).
- Velas 25t contra NT8 (sin paridad).
- Vida 200 con desenlaces; otras geometrias de salida (p. ej. objetivo A, horizonte fijo).
- Otros instrumentos (ES, YM); zonas LUX-IMB individuales como soporte/resistencia.
- Replicacion abr-sep: comprometida para esta familia (diseno mirando NQ 09-26).
- 2026-10-24 Grilla masiva LUXIMB-GRILLA (907.200 celdas por canal, la regla del visor es una celda): **preparada, no lanzada** (ni E0 ni DESC). Spec `docs/research/luximb_grilla_20261024/SPEC.md`; campañas `LUXG-NQ` / `LUXG-CFD` apagadas.

## Agregado de la revisión del 2026-10-24 (`docs/research/revision_20261024/REVISION_20261024.md`)
- **Candidato de la regla del visor:** el +4,95 pts/op es **dentro de muestra**. La regla salió de ajustes exploratorios (TP, SL, BE y entrada) y de la relectura de M11. Solo genera la hipótesis.
- **Costos:** `tools/luximb_parity/luximb_holdout_regla_visor.py` cobra 0,225 pts más 1 tick, no la fricción canónica de NQ (1,5455 pts). ~~No medido: el candidato con costos canónicos.~~ Medido el 2026-10-24 (ver abajo).
- **Multiplicidad:** se registró después de los resultados (`d98876a2`). La familia suma unas 46 pruebas en LUXIMB_FADE_VISOR y unas 105 en total.
- **Holdout:** la mirada exploratoria (n=14, 14 SL y 0 TP) se hizo fuera del protocolo de aperturas. Quedó registrada retroactivamente como ventana consumida del 10-01 al 10-21 en `docs/research/HOLDOUT_VENTANAS.jsonl`. Una confirmación arranca el 2026-10-22 o después; las familias derivadas (EXPANSION_ZONAS) arrancan el 2026-10-23.
- 2026-10-24 NULO GEOMÉTRICO (ruina del jugador) sobre los conteos del recálculo canónico: tasa de TP 104/495 = 0,210 contra p0 = 1/6 → z 2,59, p 0,007 (información). Contra el umbral económico (≈ 0,179 con D medio ≈ 108 pts) da z ≈ 1,8, igual que el P&L: el límite es el margen, no el método. Se calculó antes de registrarla (1 prueba, registrada después). `docs/research/potencia_20261024/POTENCIA_CON_LOS_MISMOS_DATOS.md`.
- 2026-10-25 Ventanas de noticia (target-free, sólo tiempos): 208 de 42.743 decisiones de M8/M10 (0,49 %) caen en ±1 min de una noticia USD tier1; 552 (1,29 %) con ±5. No medido: operaciones de la regla del visor (no hay CSV con entrada y salida). `docs/research/noticias_20261025/IMPACTO_FILTRO_NOTICIAS.md`.
