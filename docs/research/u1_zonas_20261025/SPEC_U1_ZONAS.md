# U1-ZONAS — la gramática de U1 sobre las zonas de los otros indicadores

Estado: PROPUESTA (diseño; cada corrida con desenlaces lleva su pre-registro propio antes de lanzarse)
Fecha: 2026-10-25. Pedido de Nico: «no relanzar los análisis viejos con la misma lógica: reutilizar los indicadores y quizás alguna
parte buena de la lógica, y el resto armarlo con lo que mejor funcionó en EdgeLab».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Qué funcionó mejor (lo que se reutiliza entero)
U1 (`docs/research/DESCUBRIMIENTO_U1_CRUZADO_REGISTRO.md`, `edgelab/research/u1_indaga.py`) es lo más rentable medido: +17 a +28 pts/op
de desarrollo en USATECH → NQ, y en el oro 125 celdas nominadas por FDR con INTEGRIDAD pasada. Su gramática no depende de LUX-IMB:
1. **Racimo**: ≥ N zonas vivas dentro de una banda de alto ≤ W (`areas_expansion.eventos`).
2. **Estiramiento**: el precio se aleja ≥ A/H veces la altura del área (`areas_expansion.disparos`).
3. **Vuelta confirmada**: recorre de vuelta una fracción x del camino.
4. **Ejecución hacia el área**, stop estructural detrás del extremo (S3) o 1× la distancia al objetivo (S2), objetivos T1/T2/T3, y
   las esperas y la anatomía de U1-INDAGA (volumen por pierna, velocidad, VWAP).
5. **Escala causal mensual** de W y G (rango M1 mediano del mes anterior), que es lo que destapó la señal en el oro.
6. **Embudo automático** (DESC → PISTAS → INDAGA → INTEGRIDAD → OOS → TOPES → ACTA → holdout a N fijo), costos canónicos, D6, LORD++.

## 2. Qué aporta cada indicador (lo único que cambia)
La fuente de zonas. Cada indicador PASS (`config/autopilot/indicadores.json`) da zonas con hora de creación (cierre de la barra que la
crea) y banda de precio; se guardan en un **almacén de zonas** (target-free) y U1 las usa en lugar de las de LUX-IMB.

| indicador | estado | qué es su zona | por qué podría servirle a U1 | orden |
|---|---|---|---|---|
| aVolZonePOI2 | PASS (MNQ 25t) | cluster de niveles con volumen ≥ 2× la mediana del bloque, score ≥ p95 de su franja horaria | volumen real concentrado: inventario; su racimo ya replicó en ES (compresión 7/7) | 1.º |
| aVolClusterPOI | PASS (MNQ 50t/200t) | cluster de ticks calientes por bloque | misma familia, otra definición del calor | 2.º |
| VolTicksPOC2 | PASS (muestra chica) | POC de volumen por barra | nivel de aceptación, más fino | 3.º |
| BigTrap2 | PASS_CON_CAVEAT | vela extrema con absorción (caja) | la «vela extrema» sí marcó una carrera asimétrica (F2.9) | 4.º |
| HFTZonesNQ / HFTZones2 | PASS | racha HFT (barrido) | barrido + estiramiento es la «SweepGate» de k36 | 5.º (costo cuadrático en ticks) |

Las partes buenas de la lógica vieja que se conservan como perillas (no como reglas fijas): el estado de orderblock de aVolZonePOI2
(sólo cuando ya está decidido, `t_decidida_ns` ≤ decisión: causal) y el score como filtro de calidad del racimo.

## 3. Datos e instrumentos
Estos indicadores necesitan ticks de **operaciones** con volumen (footprint): corren sobre los futuros del release (`liquid_tick_v1`),
no sobre los CFD de Dukascopy (sólo cotizaciones). Sensor = ejecución = el mismo futuro (ES y NQ primero). Descubrimiento
2025-07-01 → 2026-03-31; OOS abr → sep 2026 (partición A3, una vez por familia); holdout desde 2026-10-01 a N fijo.

## 4. Almacén de zonas (paso 1, target-free)
`tools/kaggle_grilla/almacen_zonas_main.py`: por trimestre (con 45 días de calentamiento) barras de 25 ticks → footprint total NT8 →
`avolzonepoi2.run` con los parámetros de la réplica AVZP2 (`ob_away_heights` 6, `ob_max_inside_pct` 4, `racimo_bars` 500,
`racimo_altura_ticks` 30). Guarda `t_ns, lo, hi, niveles, score, estado, t_decidida_ns`. Sin desenlaces. Publica el censo (zonas por
sesión, alto mediano) antes de cualquier corrida con P&L.

## 5. Experimento (paso 2)
`edgelab/research/u1_zonas.py`: U1-INDAGA con `zonas()` reemplazado por el lector del almacén (vida 500 min como U1), la escala causal
de U1-ORO-GRILLA (R de referencia = rango M1 mediano del propio futuro en el descubrimiento), y la perilla `indicador`. Pre-registro
propio, registro global y linaje (`U1_ZONAS` ← `AREAS_EXP_1_CRUZADO`, `U1_ORO_GRILLA` y la familia de cada indicador) antes del DESC.

## 6. Justificación económica
U1 cobra el regreso de un precio estirado a un área donde se concentró actividad. Si lo que importa es la concentración (inventario)
y no la forma de la vela, zonas de volumen real deberían marcar mejores áreas que los huecos de cotización de LUX-IMB, y en el futuro
mismo (donde U1-B con LUX-IMB murió por los huecos tapados del libro).

## 7. Cómo podría refutarse
Ninguna celda nominada por FDR ni pista confirmada en réplica con ninguna fuente; o nominadas que no pasan INTEGRIDAD (placebo ≈ regla);
o media neta ≤ 0 en el OOS con potencia. Una fuente que no dispara (censo vacío) se descarta antes del P&L.
