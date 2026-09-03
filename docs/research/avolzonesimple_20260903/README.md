# AVolZoneSimple v1.0 — zonas de volumen con una definición, estable y barrible

Fecha: 2026-09-03 · autorizado por Nico ("reestructuralo de forma más sencilla,
que siga contemplando zonas de volumen, que siga seleccionando las que se
destacan, que funcione en NT8 y en Python y sea fácil de barrer").

Archivos: `nt8/AVolZoneSimple.cs` · `edgelab/bridge/indicators/avolzonesimple.py`
· `tests/bridge/test_avolzonesimple.py` (12 tests).

## La definición, completa

> La zona es el **rango de precios más angosto que concentra S % del volumen del
> bloque**, y se publica sólo si su **concentración** supera un umbral.

Eso es todo. No hay mediana, ni multiplicador, ni clustering por gap, ni
percentil histórico.

```
necesario     = techo(volumen_bloque × SharePct / 100)
concentracion = volumen_zona × ancho_bloque × 1000 / (volumen_bloque × ancho_zona)
```

`concentracion == 1000` significa «tan concentrada como el reparto uniforme del
bloque»; 2000, el doble. Es adimensional, así que el parámetro significa lo mismo
en NQ, ES o GC. **Eso no autoriza a transportar costos ni resultados entre
instrumentos** — sólo hace comparable la escala del parámetro.

Todo entero, sin floats en la decisión. Empates: menor ancho, luego mayor
volumen, luego precio ascendente.

## Por qué se rediseñó — el defecto medido de la v0.5

Sobre los **22.507 bloques reales** de NQ 06-26 120t:

- el **89,60 %** de los bloques tenía al menos una celda a **un contrato** del
  umbral `mediana × 2`. Un contrato de diferencia entre NT8 y el parquet cambiaba
  el conjunto de celdas hot;
- el clustering por gap **amplificaba** eso: una celda de más o de menos fusiona
  o parte clusters, y la zona ganadora cambia entera;
- turnover de la geometría bajo ruido de ±1 contrato: **30,87 %**. Ninguna
  variante de la regla de selección bajó del 22 % (top-K, recortes, cuantización
  — la cuantización incluso empeora).

La causa es estructural: un umbral sobre celdas individuales tiene un borde que un
contrato cruza. Una **suma sobre muchas celdas** no lo tiene.

## Resultado

| | v0.5 (`mediana × 2`) | **AVolZoneSimple** |
|---|---:|---:|
| turnover bajo ruido de ±1 | 30,87 % | **4,97 %** |
| altura mediana de zona | 9 ticks | **9 ticks** |
| bloques con zona | 93,5 % forman cluster | 45,6 % publican zona |
| parámetros | 8 | **4** |
| estado entre bloques/sesiones | percentil histórico por franja | **ninguno** |

Cumple el criterio del `PARITY_FIRST_INDICATOR_CONTRACT_2026-09-02.md`
(turnover < 5 %), que ninguna variante de la regla vieja alcanzaba.

## Qué se eliminó, y qué se gana con cada cosa

- **La mediana y el multiplicador** → no hay umbral por celda, que era el borde.
- **El clustering por gap** → la zona es un intervalo contiguo por construcción:
  no puede fusionarse ni partirse por una celda marginal.
- **El percentil histórico por franja horaria y sesión** → era estado acumulado
  entre bloques y sesiones. Es la causa de lo que Nico observó en el chart: el
  indicador marcaba muchas zonas en un momento y ninguna en otro **sin que el
  mercado cambiara**, porque la calibración era por sesión y no por momento. Lo
  reemplaza un umbral **fijo y declarado**.
- **El filtro `Low[0]/High[0]`** → descartaba sin reasignar y perdía 0,41 % del
  volumen (medido, F5/F9). No aportaba nada; la suma del bloque es lo que decide.

Sin estado histórico, **cada bloque se decide solo**. Eso hace el indicador
reproducible barra a barra, y el barrido trivialmente paralelizable: no hay orden
ni warm-up que respetar.

## El barrido, que era el requisito

Cuatro parámetros enteros y monótonos. Landscape medido sobre los 22.507 bloques:

| share | maxW | minConc | zonas | % bloques | turnover | altura |
|---:|---:|---:|---:|---:|---:|---:|
| 15 % | 12 | 1500 | 21.244 | 94,4 % | 11,96 % | 5 t |
| 20 % | 12 | 2000 | 13.579 | 60,3 % | 7,87 % | 7 t |
| 25 % | 12 | 2000 | 9.979 | 44,3 % | 5,37 % | 8 t |
| **30 %** | **12** | **1500** | **10.254** | **45,6 %** | **4,97 %** | **9 t** |
| 30 % | 12 | 2000 | 6.852 | 30,4 % | 3,59 % | 9 t |
| 30 % | 20 | 1500 | 17.256 | 76,7 % | 11,82 % | 11 t |

Monótono en los tres ejes: subir `share` o `minConc` da menos zonas y más
estables; subir `maxW` da más zonas, más anchas y menos estables. Los defaults
son la fila marcada.

`sweep_grid()` devuelve el **landscape completo** —todas las celdas— nunca la
mejor. Es target-free: no mira retornos.

## Límites, dichos con precisión

La zona **no es invariante** ante un contrato, y el test lo fija explícitamente:

- sumar un contrato sube el volumen del bloque y con él `necesario`, que es un
  entero; cuando cruza, la ventana ganadora puede correrse;
- lo que está **acotado es cuánto**: un tick, porque la ventana es contigua y se
  ordena por ancho. El ancho no cambia;
- con una meseta **perfectamente plana** hay empates exactos entre ventanas
  vecinas y la indeterminación es real. Los bloques reales no son planos — por eso
  el turnover medido es 4,97 % y no 0 %.

`tests/bridge/test_avolzonesimple.py` fija las tres cosas, incluida la meseta
plana, para que nadie lo descubra como sorpresa en una campaña.

## Render: SharpDX, y la zona se extiende

El dibujo pasó de `Draw.Rectangle` a **`OnRender` con SharpDX**. `Draw.Rectangle`
crea un objeto de dibujo por zona y NT8 los mantiene vivos: con miles de bloques
el chart se degrada. Ahora las zonas son **datos** (`List<Zone>` con índices de
barra y ticks) y el pintado recorre sólo las visibles, culled contra
`ChartBars.FromIndex/ToIndex`.

Detalles que importan y son fáciles de arruinar:

- los brushes DX se crean en `OnRenderTargetChanged` y se **liberan siempre** ahí
  y en `Terminated`: el render target se recrea al redimensionar o cambiar de
  pantalla, y los brushes viejos quedan inválidos;
- `AntialiasMode.Aliased` durante el dibujo y restaurado en `finally` — en
  `PerPrimitive` los bordes de un rectángulo alineado a píxel salen borrosos;
- `SharpDX` no se importa con `using`: define `Brush` y haría ambiguo el `Brush`
  de `System.Windows.Media` de las propiedades de color. Se cualifica a mano.

Tres parámetros nuevos, **todos visuales** — no cambian la detección ni el CSV:

| parámetro | default | qué hace |
|---|---:|---|
| `Extend Bars` | 20 | barras que la zona se extiende a la derecha del bloque. 0 = sólo el bloque |
| `Extend To Last Bar` | false | extiende hasta el borde derecho del chart, ignora `Extend Bars` |
| `Max Zones Rendered` | 2000 | cota de memoria; descarta las más viejas. El CSV **no** se recorta nunca |

La extensión es visual por ahora. Si la vida de la zona pasa a ser parte de la
hipótesis —hasta que el precio la invalide, por ejemplo— eso es lifecycle y va
medido, no dibujado: hoy el CSV publica una fila por bloque y nada más.

## Paridad medida — capa 1 (algoritmo): EXACTA

Corrida de NT8 del 2026-09-03: **NQ SEP26, 120 ticks/barra, 10 días**, parámetros
por defecto (10 / 30 % / 12 t / 1500). Oráculo:
`data/nt8_oracles/avolzonesimple_NQ_20260903.csv`. Reporte:
`kernel_parity_v1.json`. Comando:

```
python tools/paridad_avolzonesimple.py data/nt8_oracles/avolzonesimple_NQ_20260903.csv
```

| | |
|---|---:|
| bloques | **3.086** |
| idénticos en los diez campos | **3.086 (100,0000 %)** |
| veredicto | **EXACT** |

Decisiones de NT8: `CREATE` 1.597 · `ABSTAIN_TOO_WIDE` 1.448 ·
`ABSTAIN_LOW_CONCENTRATION` 41. Las tres ramas quedaron ejercitadas.

### Un defecto propio, encontrado y corregido

La primera corrida dio **51,75 %**. No era desacuerdo del algoritmo: `decision`,
`lower_tick` y `upper_tick` coincidían en los 3.086 bloques, y **todas** las
diferencias eran `0` contra `null` en campos que no aplican — el `.cs` inicializa
sus variables en 0 y las emite siempre; el kernel Python devuelve `None`. Era una
**convención de vacío** no declarada, y el defecto estaba en el comparador.

Queda declarada en `tools/paridad_avolzonesimple.py` y normalizada sólo en los
campos numéricos.

### Verificación independiente, para no confiar en la normalización

Una normalización puede tapar una diferencia real, así que se comparó **aparte**
y **sin normalizar nada**: las 1.597 filas `CREATE`, campo por campo —
`lower_tick`, `upper_tick`, `zone_ticks`, `zone_volume`, `block_volume`,
`block_ticks`, `concentration`, `distance_ticks`, más `side` y `decision`.

**0 diferencias.** El 100 % no depende de la normalización.

### Qué queda fuera de este número

Esto es paridad **sobre input igual**: el kernel Python recibe las celdas que NT8
escribió. Prueba que las dos implementaciones son la misma función. **No** prueba
que Python reconstruya el mismo perfil desde los ticks del parquet — eso es la
capa 2, y su techo conocido es la partición de barras al 89,81 %.

Es la distinción que se le señaló a la certificación de aVolClusterPOI, así que
acá el estimand va escrito en el propio JSON.

**Capa 2 pendiente**: requiere una corrida sobre **NQ 06-26** (pre-holdout, con
parquet disponible). Ahí se mide lo que el rediseño promete: con 4,97 % de
turnover en vez de 30,87 %, las diferencias de ticks deberían impactar mucho menos.

## Paridad medida — capa 2 (end-to-end desde los ticks)

Corrida en Kaggle, commit pineado `2d2bc83e`, oráculo
`avolzonesimple_NQ0626_20260903.csv` (sha256 `5c0c8cf8…ada5`). El perfil se arma
**desde los ticks del parquet**, sin mirar las celdas de NT8. Reporte:
`layer2_report_v1.json`.

| | |
|---|---:|
| bloques emparejados | 5.371 de 5.778 |
| **acuerdo de decisión** | **99,27 %** (5.332) |
| zonas creadas por los dos lados | 2.133 |
| **geometría exacta entre ellas** | **92,92 %** (1.982) |
| jaccard mediano | **1,000** |
| jaccard ≥ 0,8 | 97,66 % |
| **perfil reconstruido exacto** | **0,24 %** (13 de 5.371) |

### El número que importa es el contraste entre los dos últimos

**Los perfiles casi nunca coinciden —0,24 %— y sin embargo las zonas coinciden
exacto el 92,92 % de las veces.** Eso es, medido, lo que significa robustez por
diseño: el indicador absorbe una diferencia de datos que sigue estando ahí entera.

La partición de barras no mejoró —sigue el 89,81 % de siempre, porque los dos
flujos de ticks no son idénticos transacción por transacción— y el perfil por
celda es distinto en 5.358 de 5.371 bloques. Lo que cambió es que la zona ya no
depende de celdas individuales.

Cuando difieren, difieren poco: de 2.133 zonas, **2.028 tienen el borde inferior
idéntico**, 65 se corren un tick, y sólo 9 se van más de 6.

### El corte de control

En los 13 bloques donde el perfil reconstruido sí coincide exacto con el de NT8,
hay 8 con `CREATE` en ambos lados y la geometría coincide en **8 de 8 (100 %)**.
Consistente con la capa 1: dado el mismo input, el resultado es el mismo. La
muestra es chica y no prueba nada por sí sola — es un control, no evidencia.

### Los desacuerdos, enumerados

`ABSTAIN_TOO_WIDE → CREATE` 18 · `CREATE → ABSTAIN_TOO_WIDE` 15 ·
`ABSTAIN_LOW_CONCENTRATION → CREATE` 3 · `ABSTAIN_TOO_WIDE → ABSTAIN_LOW_CONCENTRATION` 3.
Total 39 de 5.371. Todos son bloques al filo de `Max Zone Ticks` o de
`Min Concentration`, que es donde tiene que estar el desacuerdo si el resto
funciona.

### Lo que este número NO autoriza a decir

No es comparable de frente con el «201/203 zonas (99,01 %)» de aVolClusterPOI.
Aquel se midió sobre **203 zonas** salidas de 23.339 bloques (0,9 % de la
población); éste sobre **2.133 zonas** de 5.371 bloques (39,7 %). Poblaciones
distintas y tamaños distintos: el porcentaje más alto no es automáticamente el
mejor resultado. Lo que sí se puede afirmar es que **este acuerdo se sostiene
sobre una población cuarenta veces más grande en proporción**, y con el perfil
subyacente coincidiendo apenas el 0,24 % de las veces.

407 bloques quedaron sin emparejar (7 %): efecto del emparejamiento por
timestamp contra barras desfasadas, ya conocido y no atribuible al indicador.

## Justificación económica

Una zona de volumen es una hipótesis sobre dónde quedó inventario que puede
reaccionar. Si la zona se mueve porque un contrato cruzó un umbral, no se está
midiendo el mercado sino el ruido del feed, y ningún barrido sobre esa familia
produce un resultado promovible. Con 4,97 % de turnover, un barrido de parámetros
mide la hipótesis y no el feed.

## Cómo podría refutarse

- **Que la zona no informe**: si al barrer los tres ejes el landscape resulta
  plano —todas las celdas dan lo mismo— la definición no discrimina y la zona no
  dice nada sobre dónde está el precio.
- **Que no sea "el mismo indicador"**: si sobre el mismo chart las zonas no
  coinciden en absoluto con las de aVolClusterPOI, la premisa «misma
  funcionalidad, más simple y más estable» es falsa. Es medible directamente:
  las dos escriben CSV por bloque con el perfil crudo.

## Estado

Compilable, copiado a la carpeta de indicadores de NT8, 12 tests en verde, y los
3 candidatos que levantó el gate ULP quedaron sellados con veredicto `NO_ES_PRECIO`
(son comparaciones de string en el color y en el formateo del CSV, no umbrales).

**Falta**: correrlo en el chart junto a aVolClusterPOI y comparar. Nada de esto
sustituye a mirar las dos versiones sobre el mismo gráfico.
