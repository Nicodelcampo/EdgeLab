# HFTZonesNQRangosPct — clusters densos y rangos vacíos por percentil (NT8)

Estado: VIGENTE (indicador visual, target-free; sin paridad Python todavía). Fecha: 2026-11-09. Pedido de Nico.

Archivo: `nt8/HFTZonesNQRangosPct.cs`. Detector HFT idéntico a `nt8/HFTZonesNQPureV4_V2.cs` (mismo motor de rachas y mismos
parámetros por defecto); sólo se agrega una capa de dibujo. Logging a SQLite apagado por defecto (no toca los oráculos).

Capa nueva (grupo «P. Rangos por percentil»), recalculada cada `PctRecomputeBars` velas con las zonas ya terminadas dentro de
`PctLookbackBars` velas (causal: una zona entra cuando el detector la cierra):
- **Clusters densos:** zonas ordenadas por precio; cada grupo de `MinZonasCluster` (4) zonas consecutivas define un rango (del
  mínimo al máximo de esas zonas). Se marca el `PctAngosto` (10 %) de rangos más angostos; los que se solapan se fusionan. Etiqueta:
  zonas contenidas y ancho en ticks.
- **Rangos vacíos:** huecos de precio sin ninguna zona entre la unión de zonas, más los extremos hasta el máximo/mínimo del precio
  en la ventana. Se marca el `PctAmplio` (10 %) de huecos más amplios. Etiqueta: ancho en ticks.
- Con pocos candidatos se marca al menos uno de cada tipo (techo del porcentaje).

Linaje: el indicador de clusters anterior (`HFTClusterZonesNQ.cs`) salió del proyecto el 2026-09-21 y está en
`archive/h_cluster_nq_fuera_del_proyecto/`; éste es una definición nueva (por percentil) a pedido de Nico. Antes de usarlo en
research: paridad Python, censo as-of y familia registrada (regla de CLAUDE.md). No compilado en este entorno (sin compilador C#):
compilar en NinjaTrader y avisar errores.
