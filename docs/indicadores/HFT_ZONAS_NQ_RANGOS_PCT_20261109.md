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

## Versión liviana (2026-11-09, segunda entrega)
Nico no lo podía cargar. Cambios sólo de dibujo (el detector no cambia):
- Antes cada tick recorría TODAS las zonas para ver cuáles faltaba dibujar (cuadrático en el histórico): ahora un puntero a la primera
  pendiente, y en el histórico se dibuja en la serie primaria, no por tick. En vivo la zona aparece en el tick en que se cierra.
- En el histórico sólo se crean objetos para las zonas de las últimas `VelasDibujoHistorico` (1.500) velas; las más viejas siguen
  contando para los rangos pero no se dibujan.
- Los rangos por percentil se calculan una sola vez al terminar el histórico (antes cada 5 velas, borrando y redibujando todo); en vivo,
  cada `PctRecomputeBars`.
- Texto por zona apagado por defecto (`MostrarTexto`).
Lo que sigue pesando es la carga de la serie de 1 tick (es el detector): cargar pocos días (2–3) en el gráfico.

## Correcciones tras verlo en el gráfico (2026-11-09, tercera entrega)
- Las zonas terminaban todas en la misma vela: el rectángulo se extendía `ExtensionDibujo` velas desde la vela en que se DIBUJABA (en el
  histórico se dibujaban juntas). Ahora la extensión cuenta desde el fin de cada zona.
- Zonas que dejaban de dibujarse: el corte histórico de 1.500 velas era corto para 50 ticks; ahora 20.000 (`VelasDibujoHistorico`).
- Se quitaron los clusters viejos del V4_V2 («★ CLUSTER 4x (POC…)»), que se mezclaban con los nuevos.
- **Expansiones** (antes «vacíos» por huecos de precio de toda la ventana): ahora son regiones velas × precio por donde el precio pasó
  sin ninguna zona que lo cubriera en ese momento (la regla de vacíos del V4_V2), dibujadas sólo en las velas donde ocurrieron, sin
  extensión. Se marca el `PctAmplio` (10 %) de mayor amplitud de precio. Ventana por defecto 3.000 velas (`PctLookbackBars`).
