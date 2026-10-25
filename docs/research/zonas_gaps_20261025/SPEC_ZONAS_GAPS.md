# SPEC PRE-REGISTRADA: `ZONAS-GAPS` (`ZGAP-NQ` y `ZGAP-CFD`) — 2026-10-25

## 1. Origen y Propósito
Traducción íntegra y generalización experimental del indicador NinjaTrader 8 `ZonasDeGaps.cs` (probado por Nico en `NQ 50T`) al motor de grilla masiva y embudo de EdgeLab (`edgelab/research/zonas_gaps.py`), corrigiendo tres defectos algorítmicos del código C# original y cruzando su física de vacíos de liquidez y clusters compactos con la mecánica de excursión y regreso de `U1`.

## 2. Hipótesis Económica y Mecanismo Físico
1. **Vacío puro de órdenes límite (`GapZone` en `50T` y `M1`):**
   Un salto de precio entre el cierre de una barra y la apertura de la siguiente (`|Open[b] - Close[b-1]| >= MinGapTicks * tick`) o un salto tick-a-tick no rellenado al cierre de una barra de `50 ticks` (`50T`) o `1 minuto` (`M1`) indica que un barrido agresivo consumió la liquidez disponible sin encontrar contrapartida en los niveles intermedios.
2. **Muro continuo de vacíos (`ClusterZone` con `MaxGapFreeSpaceTicksInCluster`):**
   Cuando $\ge 3$ gaps activos se apilan dentro de una banda de hasta `160 ticks` (`40 pts` en `NQ`) con un espacio libre interno entre gaps consecutivos $\le 32\text{ ticks}$ (`8 pts`), conforman un vacío compuesto continuo.
3. **Dos lecturas contrapuestas medidas simultáneamente en la grilla (`FAVOR` vs `CONTRA` en 3 mecánicas):**
   - **Mecánica `0` (`TOQUE_RETEST` — regla nativa de `ZonasDeGaps.cs`):** tras alejarse al menos `AwayDistanceTicks = 10 ticks` (`2,50 pts`), el precio regresa y toca la zona/cluster. Si quedaron órdenes límite institucionales defendiendo el nivel del barrido, el precio rebota hacia el extremo previo (`FAVOR`); si el hueco actúa como vacío de liquidez sin defensa, el precio lo atraviesa (`CONTRA`).
   - **Mecánica `1` (`GIRO_IMAN` — giro temprano desde el extremo):** tras una excursión amplia $A \ge 4 \cdot H_{\text{eff}}$, el precio gira desde el extremo recorriendo el primer $35\%$ de vuelta hacia la zona ($D \le 0,65 \cdot A$). `FAVOR` opera la atracción magnética hacia la zona; `CONTRA` opera la reanudación de la tendencia hacia el extremo.
   - **Mecánica `2` (`IMAN_U1` — aproximación del $75\%$ estilo `U1`):** tras una excursión $A \ge 4 \cdot H_{\text{eff}}$, el precio completa el $75\%$ del regreso hacia la zona ($D \le 0,25 \cdot A$). `FAVOR` opera el tramo final de absorción hacia el borde opuesto de la zona; `CONTRA` opera el rechazo antes de ingresar.

## 3. Corrección de los 3 Bugs de `ZonasDeGaps.cs` e Incorporación como Perillas Empíricas
1. **Bug 1 (Ceguera de cluster único en `RebuildClusters()`):**
   En `ZonasDeGaps.cs` (líneas 353–392), el doble bucle guardaba únicamente un escalar `bestStart..bestEnd` global en todo el historial y llamaba a `activeClusters.Clear()`, borrando todos los clusters cercanos al precio actual si existía un cluster viejo con un gap más a `500 puntos` de distancia. En `edgelab/research/zonas_gaps.py` (`_extraer_objetos_nb`), se mantienen **todos** los clusters compactos disjuntos activos simultáneamente.
2. **Bug 2 (Falta de verificación de no-relleno al cierre de la barra creadora):**
   En `ZonasDeGaps.cs`, el gap se registraba midiendo sólo `|Open[0] - Close[1]|`, aun cuando los 49 ticks restantes de la propia barra `0` hubieran rellenado el hueco por completo. En `zonas_gaps.py`, la perilla `confirmado` mide explícitamente ambas variantes:
   - `confirmado = 0`: gap bruto de `ZonasDeGaps.cs`.
   - `confirmado = 1`: vacío confirmado que permanece abierto al cierre de la barra creadora (`50T` o `M1`).
3. **Bug 3 (Auto-disparo de `IsPriceAway` en la propia barra creadora):**
   En `ZonasDeGaps.cs`, `UpdateExistingGaps()` corría en el mismo `OnBarUpdate` inmediatamente después de `DetectNewGap()`, permitiendo que la mecha de la vela creadora activara `IsPriceAway = true` en su nacimiento. En `zonas_gaps.py` (`_ciclos_zonas_nb` / `_ciclos_zonas_vec`), el seguimiento de alejamiento y regreso comienza estrictamente en `j >= m_nac + 1`.

## 4. Espacio Completo de la Grilla (`933.120` celdas por canal)
- **Variables de Evento y Filtro (`38.880` combinaciones):**
  1. `escala` (`grupo`, 2 niveles): `0 = 50T` (reconstruido causalmente desde `tpx`), `1 = M1`.
  2. `confirmado` (`grupo`, 2 niveles): `0 = Bruto C#`, `1 = Vacío confirmado sin relleno en creación`.
  3. `objeto` (`grupo`, 2 niveles): `0 = Gap individual`, `1 = Cluster compacto multi-zona (>= 3 gaps)`.
  4. `mecanica` (`grupo`, 3 niveles): `0 = TOQUE_RETEST`, `1 = GIRO_IMAN (D <= 0,65·A)`, `2 = IMAN_U1 (D <= 0,25·A)`.
  5. `virginidad` (`eq_any`, 4 niveles): `0 = Virgen (0 toques previos)`, `1 = 1 toque previo (opacidad 0,55)`, `2 = 2+ toques previos o zona cruzada`, `3 = cualquiera`.
  6. `alejamiento` (`extremos`, 3 niveles): terciles causales en `E0` de $A / H_{\text{eff}}$ (`bajo, alto, cualquiera`).
  7. `tamano` (`extremos`, 3 niveles): terciles causales en `E0` de $H / \text{ATR}_{14}$ (`bajo, alto, cualquiera`).
  8. `actividad` (`extremos`, 3 niveles): terciles causales en `E0` del volumen relativo del ciclo (`bajo, alto, cualquiera`).
  9. `vwap` (`eq_any`, 3 niveles): `0 = en contra del VWAP de la sesión`, `1 = a favor del VWAP`, `2 = cualquiera`.
  10. `reg_hora` (`eq_any`, 5 niveles): `0 = Asia (22:00-07:00 UTC)`, `1 = Europa (07:00-13:30 UTC)`, `2 = NY (13:30-20:00 UTC)`, `3 = Cierre (20:00-22:00 UTC)`, `4 = cualquiera`.
- **Matriz de Ejecuciones (`24` combinaciones = `2 lados × 3 entradas × 4 perfiles de salida`):**
  - Lados: `FAVOR` y `CONTRA`.
  - Entradas: `CIERRE` (`limite = 0`), `SIG` (`limite = 2`, primer tick de la vela siguiente), `LIM15` (`limite = 1`, retroceso límite del $15\%$ de $D_0$).
  - Perfiles `(TP, SL, BE)` en múltiplos de la distancia estructural $D_0$: `(0.5, 0.25, 0)`, `(1.0, 0.25, 0)`, `(1.0, 0.25, 1)`, `(1.5, 0.50, 0)`.
- **Total de celdas por canal:** $38.880 \times 24 = 933.120$ celdas.

## 5. Ventanas, Linaje y Criterio de Refutación
- **Campañas registradas:**
  - `ZGAP-NQ`: sensor `NQ`, ejecución `NQ`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-25`.
  - `ZGAP-CFD`: sensor `DK:USATECHIDXUSD`, ejecución `NQ`, `DESC = 2025-08-05..2026-03-31`, `OOS = 2026-04-01..2026-09-30`.
- **Holdout reservado (`HOLDOUT-A3` / `HOLDOUT-A4`):** desde `2026-10-23`, a $N = 150$ operaciones fijas, una única apertura para toda la familia `ZONAS_GAPS`.
- **Refutación:** La familia queda refutada si ninguna celda supera la compuerta dura de FDR ($q \le 0,10$ cobrando el linaje de celdas evaluables `D6`) y Romano-Wolf en `DESC`, si no replica con media neta $> 0$ bajo fricción canónica (`1,02 pts/op` base y `1,52 pts/op` adversa en `NQ`) en `OOS`, o si la media neta en el holdout a $N$ fijo resulta $\le 0$.
