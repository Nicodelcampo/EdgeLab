# TBZ, etapa E2: parametrización holística de la expansión como "área de patinaje" (2026-09-24)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Familia:** TBZ (`FAMILIA_TBZ_FRANJAS_BAJA_PERMANENCIA_20260924.md`), variante **TBZ-EXP**. Ledger: `artifacts/hippocampus/tbz_20260924.jsonl`.
**Registro de parámetros (máquina):** `docs/specs/TBZ_E2_PARAM_REGISTRY.json`. Todo lo de abajo está ahí con su rol, sus datos, su grilla y su instante de disponibilidad.
**Estado:**
- **E2a** (censo target-free): se puede correr sin OK.
- **E2b** (resultados): **STOP**, espera el OK de Nico sobre este documento.

## 1. El fenómeno, en palabras de Nico

Una expansión rápida A → B deja una franja que se negoció poco. Cuando el precio vuelve a entrar ("pegando la vuelta"), la franja puede funcionar como **área de patinaje**: el precio la cruza rápido hacia A porque no hay nada negociado que lo frene. La pregunta: **¿existe alguna configuración que le gane al azar cuando el precio está dentro de la franja?**

**Justificación económica:** poco volumen negociado en un rango significa poco inventario de participantes con posición en esos precios. Nadie defiende su precio promedio ahí, y el precio viaja sin fricción entre nodos de volumen: es la lógica de los perfiles de volumen (HVN y LVN), la misma del mecanismo M3 del research de TBZ.

**Cómo podría refutarse:** la tasa de cruce hasta A, o el resultado neto, no supera a los tres nulos (§4) en ninguna configuración del presupuesto, después de corregir por miradas múltiples. O la supera sólo en exploración y no en `P-TBZ-CONF`.

## 2. Los ocho grupos de parámetros

| Grupo | Qué captura | Ejemplos | Rol |
|---|---|---|---|
| **G0 Barras** | resolución de detección | 25t, 50t, 100t, 1m | cambia qué franjas existen |
| **G1 Detección** | qué cuenta como expansión | ventana W, k·σ, eficiencia, fin por retroceso, neto mínimo, **velocidad mínima**, **volumen relativo mínimo**, duración máxima | cambia cantidad y tipo de franjas |
| **G2 Descriptores de la expansión** | cómo fue | ancho (ticks y σ), duración, velocidad, eficiencia, volumen total y relativo, **delta** (agresor por regla de cotización), mayor retroceso interno, **perfil de volumen interno** (LVN dentro), fase de sesión, dirección vs tendencia | describe, no filtra |
| **G3 Post-expansión** | qué pasó antes de volver | **recorrido más allá de B**, tiempo hasta el reingreso, **volumen negociado entre medio**, delta, toques previos a B, edad | describe |
| **G4 Reingreso** (el evento) | el precio dentro de la franja | **4 poblaciones de entrada**: primer toque de B, penetración del 25 %, cierre de vela adentro, segundo toque. Además: velocidad, volumen y delta de la aproximación, **absorción en B**, longitud de patinaje, **filtros EMA20, EMA50, SMA200 y VWAP** | entrada y filtros |
| **G5 Perfil izquierdo** | nodos de volumen desde la expansión hacia la izquierda | ventana hacia atrás (1 h, 4 h, sesión, sesión previa), tamaño de bin, suavizado, prominencia de HVN, profundidad de LVN, **HVN/POC y LVN dentro de [A, B]**, **TP en HVN o POC**, **entrada sólo en LVN** | descriptor, TP y entrada |
| **G6 Salidas** | la operación | stop (más allá de B, más allá del extremo post, 1σ), tiempo máximo, **entrada agresiva**, costo | salida |
| **G7 L2** (registrado, no se mide en E2) | libro en B | QI, reposición (iceberg), cancelaciones cerca del precio (spoofing aparente), absorción L2 | para después, con menos sesiones |

**Por qué la entrada es agresiva por defecto.** MM-QI y EXEC-QI mostraron que la orden pasiva se llena justo cuando uno se equivoca y se pierde los movimientos que se escapan. En una operación de patinaje, la que se escapa es la ganadora.

## 3. Cómo se explora sin fabricar un edge

Con un espacio así (miles de combinaciones), **se exploran las combinaciones, no se prueban**:
1. **E2a, censo target-free** (sin precio posterior):
   - franjas por día y por configuración de G0/G1;
   - distribución de cada descriptor;
   - **correlaciones entre parámetros**, para agrupar los redundantes y bajar la dimensión;
   - frecuencia de cada población de reingreso;
   - superposición con HVN/LVN.

   El visor muestra las franjas con sus descriptores.
2. **E2b, exploración de resultados** (STOP):
   - **Grilla primaria chica**, que es la que decide:

     | Parámetro | Valores |
     |---|---|
     | Detección | 4 (W20/W60 × k2,5/k4, la grilla de E1) |
     | Entrada | 4 poblaciones |
     | TP | 2: borde A y HVN más cercano |
     | Stop | 1: más allá de B + 0,25W |
     | Tiempo máximo | 1: 1.800 s |

     Son **32 celdas por instrumento**, 64 en MES + ES, que se cuentan como 32 por fecha porque MES y ES son el mismo subyacente.
   - **Descriptores (G2 a G5, filtros de G4):** entran **sólo por el árbol honesto**, igual que en la sinergia de NQ. Una mitad de sesiones arma los cortes y la otra estima. Sirve para sugerir, no para probar.
   - **Corrección:** BH-FDR q = 0,10 sobre las 32 celdas primarias.
3. **Confirmación:** a lo sumo 3 sugerencias pasan a `P-TBZ-CONF` (01/04–30/06/2026), con una spec en revisión ciega y una campaña aprobada.

## 4. Qué es "ganarle al azar": tres nulos, todos obligatorios

- **N1, ruina del jugador (analítico).** Con camino sin deriva, P(tocar A antes del stop) = s / (d_A + s), donde d_A es la distancia a A y s la distancia al stop. Es la vara mínima: patinar hasta A tiene que ser **más probable que lo que da la geometría sola**. Es la misma lección de YM-PRERANGE: el nulo correcto no es el 50 %.
- **N2, franja falsa.** La misma regla sobre franjas del mismo ancho y edad puestas al azar en el rango negociado **sin** expansión, emparejadas por hora y volatilidad. Es la construcción de E1b. Aísla si importa que haya sido una expansión.
- **N3, otra sesión.** La misma geometría en otra sesión a la misma hora. Controla la estacionalidad intradía y cumple la guardia `CTRL_TIMING_V1`.

Una celda le gana al azar si supera a **los tres**, en tasa de toque de A **y** en resultado neto, con el IC por sesión fuera del nulo.

## 5. Datos y alcance

- **Ticks de `research-v2`** de MES y ES, pre-holdout (jul-2025 a jun-2026). Traen bid/ask, así que **el agresor sale por regla de cotización** y la absorción corre sin L2.
- **Particiones ya declaradas:**
  - `P-TBZ-EXP`: hasta el 31/03/2026, unas 417 sesiones.
  - `P-TBZ-CONF`: 01/04–30/06/2026.
- **Holdout de ticks** (jul–dic): no se toca. El **24/09** queda excluido de TBZ.
- **G7 (L2):** ES y MES de jul–sep son desarrollo por la enmienda L2, pero son pocas sesiones. Se abre como E3 cuando E2 deje algo.
- **Costos:** los de ES y MES (spread observado + comisión), no los de NQ.

## 6. Lo que se construye

1. `tools/tbz_e2_census.py` (E2a): lee el registro JSON, calcula G0 a G5 por franja y por evento, y escribe `artifacts/tbz_e2/`. Todo es causal y cada campo lleva su `available_at`.
2. `tools/tbz_e2_explore.py` (E2b, después del OK): la grilla primaria, los tres nulos y el árbol honesto.
3. Visor: una capa de reingresos con sus descriptores, que Nico recorre a ojo antes de E2b, en la línea de la revisión ciega.

## 7. Iteración 1 (24/09, antes de medir; manda sobre §2–§6 donde choquen)

Verificado contra `edgelab/research/tbz_bands.py::expansion_bands`, contra los datos de `research-v2` y contra los manifiestos de los bundles.

**I1. Las poblaciones de entrada estaban mal definidas.**
- La expansión termina cuando una vela retrocede ≥ max(2 t, r·W) desde B. **En t_avail el precio ya está dentro de la franja por construcción**, a una profundidad ≥ r·W.
- Por eso "primer toque de B desde afuera" y "penetración 25 %" no tienen sentido tal como estaban (con r = 0,3, la penetración del 25 % se cumple siempre).
- Las cuatro poblaciones correctas, que reemplazan a las de G4:

  | Evento | Definición | Ventana |
  |---|---|---|
  | **E0 confirmación** | en t_avail (cierre de la vela que confirma): el precio pegó la vuelta | — |
  | **E1 profundización** | primera vez después de t_avail que el precio llega a una profundidad ≥ 0,5W, sin haber hecho antes un extremo nuevo más allá de B | ≤ 240 min |
  | **E2 reingreso tras extensión** | después de t_avail el precio supera B por ≥ 2 t y después vuelve a una profundidad ≥ r·W | ≤ 240 min |
  | **E3 retesteo de B desde adentro** | después de t_avail el precio vuelve a ≤ 1 t de B sin superarlo y después baja otra vez a una profundidad ≥ r·W | ≤ 240 min |

**I2. Dirección.**
- **Primaria: patinar hacia A** (contra la expansión, lo que describió Nico).
- **Secundaria, con su propia corrección FDR: hacia B** (continuación). No se mezclan en la misma familia de pruebas.

**I3. Ejecución y salida por evento.**
- Entrada **agresiva** en el primer trade posterior a evento + 250 ms, al precio contrario (ask para comprar, bid para vender).
- **Stop:** B + 0,25W más allá de B. Se ejecuta a mercado en el primer trade posterior a tocarlo.
- **Target:** A, o el HVN del perfil izquierdo entre la entrada y A (si no hay, A). Se ejecuta como límite y se llena **sólo si el precio lo atraviesa por 1 tick** (conservador).
- **Tiempo máximo:** 1.800 s, a mercado.
- **Comisión por lado:** ES USD 2,50 (0,2 t) y MES USD 0,85 (0,68 t).
- **Unidad primaria:** el **evento**, con solapamientos permitidos y bootstrap por sesión. Se agrega como descriptiva una versión "una posición a la vez".

**I4. Nulos redefinidos para que respondan la pregunta.**
- **N1:** ruina del jugador con las distancias reales de cada evento: s/(d_A + s).
- **N2, "recorrido lento del mismo tamaño":** el mismo detector con ventana W×6 (movimientos del mismo ancho pero lentos), sin superposición con franjas rápidas, emparejado por ancho en σ y con las mismas reglas E0–E3. Contesta si **importa que haya sido rápido** (la baja permanencia), que es la hipótesis.
- **N3, otra sesión a la misma hora:** mismas distancias de stop y target en ticks y misma dirección, desde un instante al azar de otra sesión a ±5 min de la misma hora. Controla la deriva y la estacionalidad. Cumple `CTRL_TIMING_V1`.

**I5. Instrumento primario:** ES. MES es el mismo subyacente con otro reloj de 25 ticks: se reporta como apoyo y **no decide**.

**I6. Datos.**
- Ticks de `research-v2`. Las velas de 25 ticks se rearman con `build_tick_bars(..., reiniciar_por_sesion=True)`, igual que los bundles.
- Las sesiones y el contrato del día salen de los manifiestos de los bundles: ES tiene 313 sesiones entre el 18/07/2025 y el 30/06/2026; ante un solapamiento de contratos, se toma el de más ticks.
- **El agresor viene en la columna `aggressor` de `research-v2`.** Antes de usar delta o absorción se valida contra el agresor del L2 en el único solapamiento pre-holdout: ES del 29 y 30/06 y NQ del 25 al 30/06 (target-free). Si el acuerdo es < 90 %, esos descriptores quedan afuera.

**I7. Presupuesto.** Primaria: 4 detecciones × 4 eventos × 2 TP = **32 celdas** (hacia A). Secundaria: 32 (hacia B), con su propio FDR.

**I8. Regla de sugerencia.** Una celda es SUGERENCIA si cumple todo esto:
- pasa FDR q = 0,10 dentro de su familia;
- esperanza neta por evento con IC > 0;
- tasa de "A antes del stop" por encima de N1, N2 y N3 con IC;
- positiva en ≥ 55 % de los meses.

**I9. Recursos** (hubo dos cuelgues de la PC): se procesa sesión por sesión, leyendo los parquet por row group filtrado a la ventana. Como máximo 2 procesos.

**I4b (24/09, construyendo el censo, antes de cualquier resultado).** El N2 "detector con ventana ×6" no sirve: en ES del 02/03/2026 da 11 franjas en una configuración y 0 en las otras tres. El umbral k·σ crece con la ventana, y la eficiencia ≥ 0,6 casi nunca se cumple en ventanas largas.

**Nuevo N2 = "tramo que no es expansión":**
- Tramos de un zigzag con **la misma regla de fin** (retroceso ≥ max(2 t, 0,3·tramo)) que **no terminan donde termina una franja TBZ** (mismo B a ≤ 1 t y t_avail a ≤ 3 velas).
- Llevan las mismas reglas E0–E3.
- En el reporte se **emparejan por ancho**: pesos por bin de ancho de las franjas TBZ (4–8, 8–16, 16–32 y ≥ 32 t).
- La pregunta pasa a ser: ¿importa que haya sido una **expansión TBZ**, o cualquier tramo del mismo ancho con la misma vuelta da lo mismo?

**Hallazgo del censo que cambia la lectura del fenómeno.** En esa sesión las franjas TBZ **no son los movimientos más rápidos**:
- en 8–16 ticks, las franjas TBZ van a una mediana de **1,2 ticks/s** y los tramos que no son TBZ a **5,9 ticks/s**;
- el detector TBZ captura desplazamientos **sostenidos** (k·σ en W velas con eficiencia), no veloces.

La "expansión rápida" de Nico no es lo mismo que la franja TBZ. La velocidad queda como descriptor (G2 `speed_tps`) y como candidata a detector (G1 `speed_min`). Se cuantifica en el censo completo.

**I1c (24/09, probando la simulación en una sesión, antes de la corrida).** El N1 original (s/(d + s) con distancias desde el precio de entrada) no usaba las convenciones de la simulación:
- el stop se ejecuta con sólo tocarlo, y el target hay que atravesarlo por 1 tick;
- la entrada paga el spread.

Con distancias chicas (franjas de 13 ticks), eso inflaba el nulo: en ES del 31/07/2025 daba 0,544 contra un acierto de 0,468.

**N1 corregido:** el camino es el de los precios de trade desde el último trade al entrar, con el stop a distancia `tdir·(x0 − stop)` y el target efectivo a `tdir·(target + tdir − x0)`. En esa sesión: acierto 0,468 contra N1 0,463. **El nulo queda calibrado**: un camino sin memoria con estas convenciones reproduce la tasa observada.

## 8. Resultado E2b en ES (25/09, madrugada): el patinaje no aparece

Reporte `artifacts/tbz_e2/report_E2b_ES.json` (sha `117d1037e192…`). Censo `artifacts/tbz_e2/census_summary_ES.json`. Ledger `artifacts/hippocampus/tbz_20260924.jsonl`. 181 sesiones de `P-TBZ-EXP`; 48 celdas (32 primarias hacia A, 16 secundarias hacia B). Guardia de controles N3: PASS.

**Veredicto: 0 sugerencias.** Las 48 celdas pierden (−0,8 a −2,1 ticks netos por operación) y pasan el FDR por ser negativas.

**Lo que decide la hipótesis (acierto de llegar a A antes del stop):**
- **Contra N1** (la geometría sola, con las mismas convenciones): el acierto queda **0,4 a 2,9 pts por debajo** en todas las celdas. En W20 k2,5 E0: 0,419 contra 0,426, IC del exceso [−1,0; −0,4]. **La franja no se cruza más rápido que un camino aleatorio**, sino apenas más lento.
- **Contra N2** (tramos del mismo ancho que no son TBZ): igual o **peor**. En E1 (profundización) da −4 a −6 pts: las franjas TBZ se revierten **menos** que un tramo cualquiera.
- **Contra N3** (otra sesión a la misma hora, mismas distancias): +1,5 a +7 pts. **Esto no es evidencia a favor**: los eventos ocurren en momentos activos y un instante al azar tiene menos volatilidad, así que en 30 min llega menos seguido a cualquier target. N1 compara sobre el mismo camino y es el nulo que manda.
- **Árbol honesto:** todas las hojas son negativas. La menos mala son las franjas anchas (W > 22 t, −0,08 R), donde los costos pesan menos, no donde hay ventaja.
- **Hacia B (continuación):** tampoco; en E0 queda por debajo de N1 (−1,8 pts).

**Censo (target-free), ES:**
- W20 k2,5 da ~625 franjas por sesión y W60 k4 ~13 por sesión.
- Velocidad mediana de las franjas TBZ: 0,85 t/s; de los tramos N2: 0,60 t/s (más angostos: mediana 5 t contra 10 t).

**Alcance de la muerte:**
- **Muere:** "la expansión TBZ-EXP funciona como área de patinaje hacia A" (y la continuación hacia B), con E0–E3, las 4 detecciones de la grilla, target A o HVN, stop B + 0,25W, 30 min, en ES, jul-2025 a mar-2026.
- **No se midieron:** los descriptores G2–G5 como filtros primarios (sólo entraron por el árbol, sin nada positivo); los detectores por velocidad (`speed_min`) y volumen relativo (`vol_rel_min`) de G1; el L2 (G7).

MES (apoyo, no decide) se agrega cuando termine su corrida.
