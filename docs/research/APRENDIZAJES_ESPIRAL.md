# Aprendizajes de la Espiral Cuantitativa (`APRENDIZAJES_ESPIRAL.md`)

Bitácora viva y acumulativa del ciclo en espiral (`Medir -> Aprender -> Investigar -> Proponer -> Correr -> Mejorarse`). Cada entrada resume qué se midió con rigor estadístico en el embudo, qué ejes separan señal de ruido, qué hipótesis quedaron refutadas y qué primitivas pasan al catálogo reutilizable.

## Ciclo 2026-10-28 — Acoplamiento `CORREDOR-VOL-GAPS` v2 y Avance Multi-Mercado (`U1` + `CVGAP`)

### 1. Qué funcionó (Señal Confirmada en Descubrimiento, Integridad, OOS y Topes)
- **`CVGAP-NQ` (`edgelab.research.corredor_vol_gaps`, futuros NQ `2025-08-05..2026-09-25`)**:
  - **Descubrimiento (`83.052` celdas evaluables de `933.120`)**: `297` celdas nominadas por FDR (`q <= 0,10`), umbral Romano-Wolf `t = 4,21`.
  - **Integridad (`3/3` candidatas aprobadas)**: La celda `[0, 0, 1, 2, 2, 2, 3, 2, 0, 2, 11]` (`50T`, `W2_200`, `P80`, excursión `>= 2,0x H_amarilla`, regreso `R_CAJA`, target `T50`, stop `S_CAJA`, `G_TOM >= 1`, `G_CAM >= 0`, ventana `SIG`, franja `ORIG100`) obtuvo `+$14,64/op` (placebo `-$3,13/op`, latencia 1 vela `+$15,47/op`).
  - **Réplica OOS (`2026-04-01..2026-09-25`)**: `n = 88` operaciones en `58` sesiones, **`media_neta = +$19,13/op`**, `IC90 = [+$4,51, +$33,21]`, `p_sesiones = 0,0153`, `meseta = True`, `4/4` criterios económicos en verde (`conservado = 86,58%`, `drawdown_max = -$399,98`, `total = +$1.683,75`).
  - **Topes y Acta Pre-Holdout**: Elegido tope `['mult', 4.0]` (`puntaje = 2,8248`, `peor = -$221,80`) y **ACTA registrada antes de mirar** (`n_fijo = 150` desde `2026-10-23`, `alfa = 0,00361`).
- **`CVGAP-CFD-NQ` (`USATECH->NQ` cruzado, familia `CORREDOR_VOL_GAPS_CFD_NQ`)**:
  - **Descubrimiento (`71.792` evaluables)**: `80` nominadas por FDR (`q <= 0,10`), RW `4,31`.
  - **Integridad (`3/3` aprobadas)**: Las tres candidatas (`[0, 1, 0, 0, 2, 3, 2, 1, 2, 0, 10]`, `[0, 1, 0, 0, 2, 2, 2, 1, 2, 0, 4]` y `[0, 1, 1, 0, 2, 2, 3, 1, 2, 0, 2]`) superaron placebo (`-$2,16` a `-$1,57/op`) y conservaron `+92%` a `+95%` de la media bajo latencia de 1 vela (`+$16,45/op`, `+$16,39/op`, `+$12,25/op`).
  - **Réplica OOS (`2026-04-01..2026-09-25`)**: `3/3` medias positivas (`+$10,50/op` en `c0` y `c1` con `n = 110`, `69` sesiones, `meseta = True`, `4/4` económico y `69,56%` conservado; `+$7,41/op` en `c2`).
  - **Topes y Acta Pre-Holdout**: Elegida `c0` `[0, 1, 0, 0, 2, 3, 2, 1, 2, 0, 10]` con `tope = ['pts', 50.0]` (`puntaje = 11,3214`, `peor = -$74,80`, `media con tope = +$17,84/op`, `IC90 [+$10,45, +$25,34]`, `p = 0,0010`, `1ª mitad +$8,17/op p=0,0445`, `2ª mitad +$27,33/op p=0,0015`) y **ACTA registrada antes de mirar** (`n_fijo = 150` desde `2026-10-23`, `α = 0,00361`).
- **`U1-RACIMOS-GRILLA-NQ` (`edgelab.research.u1_racimos_grilla`, NQ)**:
  - **Integridad (`3/3` aprobadas)**: Medias de `+$25,67/op`, `+$24,24/op` y `+$23,72/op` con placebos negativos (`-$3,74` a `-$14,21/op`) y latencia 1 vela intacta (`+$27,85/op`, `+$22,19/op`, `+$23,43/op`).
  - **OOS (`2026-04-01..2026-09-30`)**: Las 3 candidatas mantuvieron media neta positiva en OOS (`+$32,83/op` con `IC90 = [+$15,93, +$52,34]` y `p = 0,0044`; `+$19,78/op`; `+$5,74/op`) y avanzaron a `TOPES`.
- **`U1-ZONAS-GRILLA-YM` (`edgelab.research.u1_zonas_grilla`, YM)**:
  - **Integridad aprobada** (`+$12,78/op`, placebo `-$5,90/op`, latencia 1 vela `+$17,10/op`, latencia 2 velas `+$19,81/op`) y OOS positivo (`+$3,65/op`, `meseta = True`), avanzando a `TOPES`.

### 2. Qué aprendimos sobre Microestructura y Asimetría entre Instrumentos
- **Paridad estricta del sector adelantado (`BuildVolumeAtPrice` + `LookbackZones=50`)**: Reemplazar la fracción lineal OHLC por la acumulación exacta en `b = z.EndBar + 1 .. z.ForwardEndBar` con desempate de `AnchorPOC` al centro del sector y bloqueo de re-apertura del mismo impulso (`last_closed_origin`) eliminó la duplicación de zonas y elevó las nominadas FDR en NQ de `0` (en v1) a `297` (en v2).
- **Invarianza de escala en filtros de gaps (`G_TOM` y `G_CAM`)**: En NQ (`tick_size = 0,25`, alta fragmentación de precio), los umbrales `[0, 1, 2, 4]` operan en el rango intercuartil real; en ES (`tick_size = 0,25`, libro denso) y CFDs, un filtro rígido `>= 4` vacía la muestra. Los umbrales de gaps deben parametrizarse por cuantiles empíricos del instrumento o normalizarse por la tasa de gaps por sesión.
- **Canastas `PISTAS_VIVAS` en ES (`CVGAP-ES` y `CVGAP-CFD-ES`)**: En `CVGAP-ES` (`20` pistas en OOS), la canasta combinada dio `+$5,99/op` (`p = 0,180`, veredicto `SIN_POTENCIA` / `PISTAS_VIVAS`), con la pista `p3` alcanzando `+$24,47/op` (`p = 0,0049`, `n = 60`). En ES la reversión requiere franjas horarias específicas (`ORIG100` / `RTH`) y stops más holgados (`S_CAJA` / `S_IMP`).

### 3. Primitivas Promovidas al Catálogo Reutilizable (`L1`/`L2`)
1. `_extraer_cajas_amarillas_nb` (`edgelab/research/corredor_vol_gaps.py`): Detector causal del corredor EMA 20/60 + caja amarilla `W1=100% / W2=200%` con ventana rodante de 50 zonas y soporte de ruptura intra-sector.
2. `_precomputar_eventos_nb` (`edgelab/research/corredor_vol_gaps.py`): Tensor de eventos en 2 pasadas (`O(N_eventos)` en vez de `O(N_barras)` por celda) con contabilidad causal de gaps tomados (`g_tom`), puntaje ponderado por antigüedad/volumen (`g_pts`) y gaps abiertos en el camino (`g_cam`).

## Ciclo 2026-10-28 (Olas 6–9) — Cosecha Completa de Zonas/Racimos (3 nuevas ACTAs), Barridos `OTR-930-SWEEP` y `ORO-ALMUERZO-RUPTURA`, y Biblioteca de Ideas

### 1. Tres Nuevas Campañas en `CONTEO / PENDIENTE` (`ACTA_HOLDOUT.json` emitidas antes de mirar)
- **`U1-ZONAS-BT2-ES` (`edgelab.research.u1_zonas_bt2`, futuros ES `2025-08-01..2026-09-30`)**:
  - **Descubrimiento (`15.960` evaluables)**: `3` nominadas por FDR (`q <= 0,10`), RW `4,24`.
  - **Integridad (`3/3` aprobadas)**: `[0, 0, 2, 2, 2, 2, 3, 3, 3, 0, 0, 9]` (`+11,45 pts/op`, placebo `-1,24`, latencia 1 vela `+12,71`); `[0, 2, 0, 2, 2, 2, 1, 3, 1, 0, 0, 6]` (`+3,29 pts/op`, placebo `-1,08`, latencia 1 vela `+3,82`); `[0, 2, 0, 2, 2, 2, 0, 0, 3, 0, 0, 4]` (`+2,81 pts/op`, placebo `-1,38`, latencia 1 vela `+4,44`).
  - **OOS (`2026-04-01..2026-09-30`) y Topes**: La celda `[0, 2, 0, 2, 2, 2, 1, 3, 1, 0, 0, 6]` obtuvo **`+2,47 pts/op`** en OOS y fue seleccionada en `TOPES` con `tope = ['pts', 50.0]` (`puntaje = 12,6946`, `peor = -9,34 pts`). **ACTA registrada antes de mirar** (`n_fijo = 150` desde `2026-10-01`, `α = 0,00361`).
- **`U1-ZONAS-BT2-NQ` (`edgelab.research.u1_zonas_bt2`, futuros NQ `2025-08-01..2026-09-30`)**:
  - **Integridad (`3/3` aprobadas)**: `[0, 1, 0, 2, 2, 1, 3, 2, 3, 0, 0, 10]` (`+13,64 pts/op`, placebo `+2,16`, latencia 1 vela `+7,28`); `[0, 2, 0, 1, 2, 2, 3, 2, 3, 0, 0, 4]` (`+15,02 pts/op`, placebo `+0,14`, latencia 1 vela `+16,15`); `[0, 1, 0, 1, 2, 2, 3, 2, 3, 0, 0, 2]` (`+6,90 pts/op`, placebo `-6,07`, latencia 1 vela `+7,92`).
  - **Topes y Acta Pre-Holdout**: Seleccionada `[0, 2, 0, 1, 2, 2, 3, 2, 3, 0, 0, 4]` con `tope = ['pts', 50.0]` (`puntaje = 2,6914`, `peor = -52,05 pts`) y **ACTA registrada antes de mirar** (`n_fijo = 150` desde `2026-10-01`, `α = 0,00361`).
- **`U1-RACIMOS-GRILLA-ES` (`edgelab.research.u1_racimos_grilla`, futuros ES `2025-08-01..2026-09-30`)**:
  - **Integridad (`2/2` aprobadas tras propagar `escala_seg` en `u1_indaga.py`)**: `[0, 0, 0, 16, 2, 2]` (`+5,95 pts/op`, placebo `-0,75`, latencia 1 vela `+5,72`) y `[0, 1, 0, 16, 2, 3]` (`+4,78 pts/op`, placebo `+0,81`, latencia 1 vela `+4,38`).
  - **Topes y Acta Pre-Holdout**: Seleccionada `[0, 0, 0, 16, 2, 2]` con `tope = ['pts', 50.0]` (`puntaje = 4,1269`, `peor = -37,51 pts`) y **ACTA registrada antes de mirar** (`n_fijo = 150` desde `2026-10-01`, `α = 0,00361`).
- **`U1-6E-GRILLA` (`DK:EURUSD -> 6E`)**: Cosechada etapa `PISTAS / REP` y cerrada en `FIN / PISTAS_VIVAS` (`SIN_RECHAZO`).

### 2. Seis Campañas de Nuevas Familias (`OTR-930-SWEEP` y `ORO-ALMUERZO-RUPTURA`) en `FIN / PISTAS_VIVAS`
- **`OTR-930-SWEEP` (`edgelab/research/otr_930_sweep.py`, `194.400` celdas/canal)**:
  - **`OTR930-NQ` (`NQ -> NQ`)**: `49.080` celdas evaluables (`1.778` disparos). En OOS (`[2026-04-01, 2026-09-30]`), la canasta de 20 pistas logró **`+5,12 pts/op`** (`p = 0,1075`, `94` sesiones, `potencia = 0,966`, `SIN_RECHAZO` / `PISTAS_VIVAS`), destacando la pista `[0, 1, 1, 0, 3, 3, 0, 1, 1, 10]` con **`+29,97 pts/op`** (`n = 26`, `p = 0,1654`).
  - **`OTR930-CFD-NQ` (`DK:USATECHIDXUSD -> NQ`)**: `50.640` celdas evaluables (`1.814` disparos). En OOS, la canasta promedió **`+3,03 pts/op`** (`102` sesiones, `PISTAS_VIVAS`), con la pista `[1, 1, 2, 2, 0, 0, 3, 2, 2, 2]` alcanzando **`+17,59 pts/op`** (`n = 58`, `p = 0,1224`).
  - **`OTR930-ES` (`ES -> ES`)**: `53.184` celdas evaluables (`1.796` disparos). En OOS, la canasta promedió **`+0,45 pts/op`** (`52` sesiones, `potencia = 0,869`, `SIN_RECHAZO` / `PISTAS_VIVAS`), mejor pista `[2, 0, 0, 0, 3, 3, 0, 1, 2, 8]` con `+2,14 pts/op`.
  - **`OTR930-CFD-ES` (`DK:USA500IDXUSD -> ES`)**: `42.000` celdas evaluables (`1.829` disparos). En OOS, la canasta promedió **`+0,38 pts/op`** (`86` sesiones, `potencia = 1,000`, `SIN_RECHAZO` / `PISTAS_VIVAS`), destacando la pista `[1, 2, 0, 1, 0, 0, 3, 2, 2, 9]` con **`+7,71 pts/op`** (`n = 22`, `p = 0,0595`).
- **`ORO-ALMUERZO-RUPTURA` (`edgelab/research/oro_almuerzo_ruptura.py`, `194.400` celdas/canal)**:
  - **`ORO-ALM-GC` (`GC -> GC`)**: `45.828` celdas evaluables (`1.313` disparos). En OOS, la canasta promedió **`+0,21 pts/op`** (`37` sesiones, `potencia = 0,780`, `SIN_POTENCIA` / `PISTAS_VIVAS`), destacando la pista `[1, 2, 3, 2, 1, 0, 0, 2, 1, 11]` con **`+14,00 pts/op`** (`n = 20`, `p = 0,0538`).
  - **`ORO-ALM-CFD` (`DK:XAUUSD -> GC`)**: `47.556` celdas evaluables (`1.448` disparos). En OOS, la canasta promedió **`+0,42 pts/op`** (`52` sesiones, `potencia = 1,000`, `SIN_RECHAZO` / `PISTAS_VIVAS`), destacando la pista `[0, 2, 1, 2, 0, 3, 0, 2, 2, 2]` con **`+13,62 pts/op`** (`n = 21`, `p = 0,0386`).

### 3. Biblioteca de Ideas (`docs/research/biblioteca_ideas_20261028/`)
- Se incorporaron y preclasificaron las `248` estrategias de trading extraídas de los guardados de Instagram (`estrategias_guardadas_trading.md`) y el paper formal de líneas de tendencia por tiempos de parada de Tori Trades (`TORI_TRADES_STOPPING_TIME_TRENDLINES_20261026.md` + `.docx`), organizadas en el ranking ejecutable `CATALOGO_Y_PRECLASIFICACION_EDGELAB_20261028.md` (Top 12 Tier-1 testeables en M1/ticks hoy + Tier-2 L2/opciones).

## Ola 10 — Síntesis en Espiral (`CONFLUENCIA-CVGAP-RACIMOS`) y Nuevas Familias del Scrap (`ASIA-BOS-GAPS` y `TORI-TREND-TOQUE3`) (2026-10-29)

1. **Resolución del Cuello de Botella de Escala en ES mediante Cortes por Cuantiles (`CONFLUENCIA-CVGAP-RACIMOS`)**:
   - En `CVGAP-ES` (Ola 5), los umbrales absolutos producían sólo `5.832` celdas evaluables de `933.120`. Al migrar los filtros de puntaje de gaps y de densidad de racimos a cortes empíricos por cuantiles (`extremos`, `cuantiles=3`, invariantes de escala entre NQ y ES), `CONF-CVR-ES` alcanzó **`46.968` celdas evaluables** (`8,05x` más densidad) y `CONF-CVR-NQ` alcanzó **`45.456` celdas evaluables** sobre `314.928` celdas/canal.
   - En la réplica OOS (`20260401–20260925`), `CONF-CVR-NQ` quedó en **`PISTAS_VIVAS`** (`SIN_RECHAZO`, potencia `0,870`, mejor pista `p9 = [1, 1, 0, 1, 0, 2, 0, 1, 2, 3]` con `+$6,73 pts/op`, `n=79`, `59` sesiones), mientras que `CONF-CVR-ES` fue refutada con potencia (`0,993`, `IC90 [-1,52, -0,16]`), confirmando que en ES la confluencia de absorción requiere el anclaje estructural directo de `U1-RACIMOS-GRILLA-ES` o `U1-ZONAS-BT2-ES` sin exigir simultáneamente caja amarilla adelantada.
2. **Compresión Asiática + BOS / Sweep Reclaim + `ZONAS-GAPS` (`ASIA-BOS-GAPS`, `ASIA-NQ`)**:
   - En `DESC` (`20250805–20260331`), `ASIA-NQ` produjo `28.344` celdas evaluables con pistas top de `+$26,82 pts/op` (`IC90 [+9,77, +43,72]`).
   - En la réplica OOS (`20260401–20260925`), la canasta igual-ponderada de 20 pistas alcanzó **`+$4,38 pts/pista/sesión`** (`IC90 [-0,33, +8,82]`, **`p = 0,0530`**, `102` sesiones, potencia `0,991`), y el lote de 20 pistas registró **`p_simes = 0,0388`** (`LORD++ t=2`). Las pistas individuales `p2 = [1, 0, 0, 2, 1, 3, 3, 2, 2, 3]` (**`+$55,47 pts/op`**, `IC90 [+19,31, +89,66]`, **`p = 0,0039`**, `18` sesiones) y `p3 = [1, 0, 0, 2, 1, 3, 3, 2, 0, 9]` (**`+$54,83 pts/op`**, `IC90 [+19,39, +88,07]`, **`p = 0,0031`**, `18` sesiones) replicaron con IC90 entero positivo en OOS.
3. **Línea de Tendencia Causal de Tiempo de Parada + 3er Toque (`TORI-TREND-TOQUE3`, `TORI-NQ`)**:
   - En `DESC` (`20250805–20260331`), `TORI-NQ` evaluó `16.944` celdas con top `+$13,03 pts/op` (`IC90 [+3,95, +22,45]`).
   - En la réplica OOS (`20260401–20260925`), quedó en **`PISTAS_VIVAS`** (`SIN_RECHAZO`, potencia `0,999`), destacándose la pista `p19 = [1, 0, 1, 0, 3, 2, 3, 2, 1, 15]` con **`+$15,03 pts/op`** (`IC90 [+1,58, +30,08]`, **`p = 0,0505`**, `14` sesiones).
