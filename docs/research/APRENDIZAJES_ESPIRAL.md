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
