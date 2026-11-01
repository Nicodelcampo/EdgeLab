# SPEC PRE-REGISTRADA: `CORREDOR-VOL-GAPS` (`CVGAP-NQ`, `CVGAP-ES`, `CVGAP-CFD-NQ`, `CVGAP-CFD-ES`) — 2026-10-28

- **Familia en linaje y LORD++:** `CORREDOR_VOL_GAPS_NQ` (para `CVGAP-NQ` y `CVGAP-CFD-NQ`) y `CORREDOR_VOL_GAPS_ES` (para `CVGAP-ES` y `CVGAP-CFD-ES`), descendientes declarados en `docs/research/LINAJES.jsonl` con herencia `"bruto"` de `ZONAS_GAPS`, `U1_ZONAS_ES` y `AREAS_EXP_1_CRUZADO` (evitando colisión con la ventana única de holdout ya consumida por `ZGAP-NQ-CANASTA` en `ZONAS_GAPS`).
- **Módulo ejecutable:** `edgelab/research/corredor_vol_gaps.py` (`NOMBRE = "CORREDOR-VOL-GAPS"`).
- **Indicadores registrados (`NATIVO_AGENTE`):** `EmaCorridorTrendVolW2` y `ZONAS-GAPS` (`config/autopilot/grillas/indicadores_agente.json`), verificados por `tests/research/test_corredor_vol_gaps.py::test_causal`.

## 1. Justificación Económica y Microestructural

1. **Corredor de Impulso Estable y Rectángulo Amarillo (`EmaCorridorTrendVolW2.cs`):**
   - Un corredor de tendencia sostenido por los 4 pilares de `EmaCorridorTrendVolW2.cs` (`FastPeriod = 20`, `SlowPeriod = 60`, `StabilityWindow = 15`, `MaxNarrowingPct = 15%`, `SlopeLookback = 5`, `MaxInsideBars = 3`) define el impulso estructural `[OriginBar..EndBar]` con caja `[BoxLo, BoxHi]` y altura $H_{\text{imp}} = \text{BoxHi} - \text{BoxLo}$.
   - Al romperse el corredor (`ConfirmBreakBars = 2` cierres fuera de `EMA(60)` o cruce de EMAs), se proyecta el sector adelantado `[SectorLo, SectorHi]` (`TailPct = 25%` hacia adentro del extremo del impulso + `BeyondPct = 25%` más allá del extremo, altura $H_{\text{am}} = 0.50 \cdot H_{\text{imp}}$) durante `ForwardBars = round(impWidth * W)` barras (`W1 = 100%`, `W2 = 200%`).
   - Cuando el volumen operado dentro de `[SectorLo, SectorHi]` supera el percentil histórico causal (`P80` o `P90` de las zonas previas), el sector se marca como **Rectángulo Amarillo** (absorción institucional en el extremo del impulso) con anclajes `AnchorPOC` (precio modal de volumen) y `AnchorVAEdge` (`VAL` en tendencia alcista, `VAH` en tendencia bajista).

2. **Ruptura en la Dirección del Impulso + Excursión + Regreso (`Hipótesis de Nico`):**
   - Si el precio **NO** rompe hacia el lado del origen del impulso, sino que **rompe el Rectángulo Amarillo en la misma dirección del impulso inicial**, se aleja una excursión $A \ge \{1.0, 2.0, 4.0\} \times H_{\text{am}}$ y **regresa**, la ruptura alcista/bajista tardía sobre una zona de absorción alta (`P80`/`P90`) representa una trampa de agotamiento (barrido de stops tardíos).
   - Al regresar en uno de los 3 puntos estructurales (`0 = ANTES_CAJA` al retroceder $40\%$ de la excursión $A$; `1 = EN_CAJA_AMARILLA` al retocar el borde externo / `AnchorPOC`; `2 = DESPUES_CAJA_VA` al cruzar `AnchorVAEdge` / borde interno de la caja amarilla), se apuesta a que el precio invierte/rellena el impulso inicial hacia:
     - `MID50`: el $50\%$ del impulso inicial (`0.5 * (BoxLo + BoxHi)`),
     - `MID25`: el $25\%$ medido desde el origen del impulso inicial (`BoxLo + 0.25 * H_imp` en tendencia alcista, `BoxHi - 0.25 * H_imp` en bajista, equivalente al $75\%$ de retroceso del impulso),
     - `ORIG100`: el $100\%$ de inversión completa hasta el origen del impulso (`BoxLo` en alcista, `BoxHi` en bajista).

3. **Acoplamiento con `ZONAS-GAPS` (Puntaje Continuo de Gaps Tomados e Imán de Camino):**
   - Guiados por la descomposición empírica de las 20 pistas de `ZGAP-NQ` (donde `confirmado = 1` ocupó 20/20 pistas y `1_toque` previo ocupó 16/20 pistas), cada gap activo $g$ recibe un puntaje continuo causal:
     $$\text{score}(g) = w_{\text{conf}}(g) \cdot \exp\left(-\frac{\text{edad}_{\min}(g)}{180}\right) \cdot w_{\text{comercio}}(g)$$
     con $w_{\text{conf}} \in \{1.0, 0.5\}$ y $w_{\text{comercio}} = 1.35$ (`1_toque`), $1.00$ (`0_toques` virgen), $0.60$ (`2+ toques`).
   - Se miden dos perillas ortogonales:
     - `gap_score_tomados` (`g_tom`): puntaje acumulado de gaps barridos/mitigados durante la excursión $A$ más allá de la caja amarilla.
     - `gap_iman_camino` (`g_cam`): puntaje acumulado de gaps confirmados aún abiertos entre el precio de entrada y `ORIG100` (vacíos que actúan como imán hacia el origen del impulso).

## 2. Grilla Pre-Registrada (`933.120` celdas por canal)

- `escala` (`2`, `grupo`): `0 = 50T`, `1 = M1`.
- `variante_w` (`2`, `grupo`): `0 = W1 (100% ForwardWidthPct)`, `1 = W2 (200% ForwardWidthPct)`.
- `pct_vol` (`2`, `ge`): `0 = >= P80`, `1 = >= P90`.
- `exc_amarilla` (`3`, `ge`, `cortes=(1.0, 2.0, 4.0)`, `piso=True`): `A / H_am >= 1.0, 2.0, 4.0`.
- `punto_regreso` (`3`, `grupo`): `0 = ANTES_CAJA`, `1 = EN_CAJA_AMARILLA`, `2 = DESPUES_CAJA_VA`.
- `gap_score_tomados` (`4`, `eq_any`, `cortes=(0.05, 1.15)`): `0 = sin gaps`, `1 = moderado`, `2 = alto`, `3 = cualquiera`.
- `gap_iman_camino` (`4`, `eq_any`, `cortes=(0.05, 1.15)`): `0 = sin imán`, `1 = 1 gap imán`, `2 = multi-imán`, `3 = cualquiera`.
- `tamano_impulso` (`3`, `extremos`, `cuantiles=3`): terciles causales de `H_imp / ATR14`.
- `vwap` (`3`, `eq_any`, `categoria=2`): contra VWAP (`0`), a favor de VWAP (`1`), cualquiera (`2`).
- `reg_hora` (`5`, `eq_any`, `categoria=4`): Asia (`0`), Europa (`1`), NY (`2`), Cierre (`3`), cualquiera (`4`).
- `ejecución` (`18`, `grupo`): `3 entradas (CIERRE, SIG, ANCLA_LIM) × 3 targets (MID50, MID25, ORIG100) × 2 stops (S_EXT, S_CAJA)`.

## 3. Reparto Multi-Cuenta en Kaggle y Ventanas

- **Cuenta 1 (`nicolasbuttaro` — Futuros CME directos):**
  - `CVGAP-NQ`: sensor `NQ`, ejecución `NQ`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-25`.
  - `CVGAP-ES`: sensor `ES`, ejecución `ES`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-25`.
- **Cuenta 2 (`nicobuttaro` — Señal CFD Dukascopy $\to$ Ejecución Futuro CME):**
  - `CVGAP-CFD-NQ`: sensor `DK:USATECHIDXUSD`, ejecución `NQ`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-25`.
  - `CVGAP-CFD-ES`: sensor `DK:USA500IDXUSD`, ejecución `ES`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-25`.

## 4. Mejoras de Paridad Causal y Microestructura (Auditoría v2 — 2026-10-28)

1. **Integración Exacta de Volumen por Tick y Percentil Causal (`_acumular_perfil_sector_nb` / `_evaluar_percentil_causal_nb`):**
   - Integra directamente los precios de cada tick (`tpx[b_t0[b]:b_t1[b]]`) dentro de `[SectorLo, SectorHi]` durante `b = EndBar + 1 .. ForwardEndBar` (paridad exacta con `BuildVolumeAtPrice` de `EmaCorridorTrendVolW2.cs`), desempata `AnchorPOC` por cercanía al centro del sector `0.5 * (SectorLo + SectorHi)` (línea 880 C#) y evalúa `P80`/`P90` reales sobre ventana rodante `LookbackZones = 50`.
2. **Confirmación Causal Temprana de Rupturas Intra-Sector (`_extraer_cajas_amarillas_nb`):**
   - Dado que el volumen acumulado en `[EndBar + 1 .. i]` es monótonamente no decreciente, si en `i < ForwardEndBar` dicho volumen ya supera `P80` y el precio rompe la Caja Amarilla en la dirección del impulso, la zona se confirma causalmente en `b_k[i]` sin usar información futura del resto de `ForwardBars`, actualizando siempre `hist_vols` al cierre completo en `ForwardEndBar`.
3. **Acoplamiento con el Detector y Ciclo de Vida de `ZonasDeGaps.cs` (`_gaps_barras_nb` / `_contar_toques_epoca_nb`):**
   - Unifica saltos apertura-cierre, saltos tick a tick intrabarra en `50T` y huecos de 3 barras (`FVG`) con piso adaptativo `max(min_gap_ticks * tick, 0.12 * ATR14_M1)`.
   - Exige separación de épocas de toque por `AwayDistanceTicks = 10` (`<= 1` época previa = vivo; al 2do toque previo el gap muere, evitando la saturación de `g_tom` en NQ) e incorpora bono `1.25x` por racimo compacto (`>= 3` gaps activos en `12` ticks).
4. **Excursión Genuina Post-Caja y Exclusión Mutua de `punto_regreso` por Barra:**
   - Exige excursión más allá del borde externo `ext_beyond >= max(0.25 * H_am, 2 * tick)`, mide el retroceso de `ANTES_CAJA` sobre `ext_beyond` (`dist_rem <= 0.60 * ext_beyond`) y garantiza exclusión mutua (`break` tras el primer `pt` activado en la barra `m`) para no duplicar órdenes `"CIERRE"`/`"SIG"` en un mismo minuto.
