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
