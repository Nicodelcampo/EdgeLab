# aVolClusterPOI — FASE 8: el corte por grupo de timestamp queda REFUTADO

Fecha: 2026-09-02 · commit pineado `706c4fe2` · CSV NT8 sha256 `81f32a97…f9da`
Kernel: `notebooks/kaggle/avolcluster_tsgroup/tsgroup_entry.py` (Kaggle)
Estado: `DIAGNOSTIC_NO_CODE_CHANGED`.

## Hipótesis probada

El 51,05 % de los ticks de NQ comparte timestamp con el anterior (medido acá).
La hipótesis era que NT8 no corta una barra en el medio de un grupo de ticks
simultáneos, mientras el parquet, contado como 120 filas consecutivas, sí.

Variantes del corte: `crudo` (120 exactos), `extiende` (cierra al terminar el
grupo), `trunca` (cierra antes de que empiece), cruzadas con lag 0/−1 y filtro
on/off.

## Resultado — refutada, y sin ambigüedad

| variante | barras | emparejados | exactos | vol NT8/py |
|---|---:|---:|---:|---:|
| **`crudo_L-1_filtro`** (F6) | 239.539 | 22.507 | **3.436 (15,27 %)** | 0,9964 |
| `extiende_L0` | 234.584 | 9.532 | 2 | 0,9684 |
| `trunca_L0` | 56.510 | 1.681 | 5 | 0,5572 |

Ninguna variante ajustada mejora nada: **destruyen** el emparejamiento. Con
`trunca` sólo sobreviven 1.681 de 22.507 bloques y el volumen cae al 55,7 %.
NT8 sí parte grupos de ticks simultáneos, igual que el kernel Python.

El mejor mecanismo conocido sigue siendo el de la FASE 6, sin cambios.

## Estado de la paridad: NO VALIDADA

Se probaron y descartaron, con evidencia propia y reproducible:

| # | hipótesis | veredicto |
|---|---|---|
| F2 | desalineación de barras | refutada (offset 0 al 99,98 %, Δt 0 ns) |
| F3 | filtro `Low/High` aislado | refutada como causa aislada (descarta 0 ticks) |
| F4 | fase global de partición | real pero parcial (`k=−1`, 9,01 %) |
| F5 | conjuntos de ticks distintos | refutada — es una *pérdida* sistemática de 0,41 % |
| F6 | lag −1 + filtro `Low/High` | **confirmado**, 15,27 %, reproduce el déficit |
| F7 | residuo estructurado | chico, en el medio, plano — no es filtro ni deriva |
| F8 | corte por grupo de timestamp | refutada |

De 0,07 % a 15,27 % de bloques idénticos, con un mecanismo nombrado y verificado
por dos vías independientes. **Pero 15,27 % no es paridad**, y el residuo ya no
tiene ninguna hipótesis viva que pueda medirse desde el parquet: es un
desajuste de frontera de barra por pocos ticks, variable, que se autocorrige, y
el parquet no contiene la información que diría dónde puso NT8 esa frontera.

## Qué desbloquea esto — un pedido concreto, no otra hipótesis

`aVolClusterPOI.cs` ya escribe un log por bloque. Alcanza con agregarle, **por
barra**, tres campos que hoy no exporta:

- `bar_first_tick_time` y `bar_last_tick_time` (timestamp del primer y último
  tick que NT8 metió en esa barra),
- `bar_tick_count` (cuántos ticks contó realmente),
- opcionalmente el perfil crudo de la barra, no del bloque.

Con eso, la frontera de NT8 deja de ser una hipótesis y pasa a ser un dato: se
alinea barra a barra y la paridad se cierra o se explica en una sola corrida.
Es un cambio **aditivo de logging**, no toca la lógica del indicador — pero
igual requiere OK de Nico, porque toda modificación del `.cs` se consulta.

## Cómo podría refutarse esta conclusión

Si un barrido de lag variable (no constante) sobre el parquet alcanzara paridad
alta, la instrumentación sería innecesaria. No se probó lag variable porque el
espacio es enorme y no hay señal que lo acote: la FASE 7 mostró error plano y
sin estructura, que es justamente la ausencia de esa señal.

## Justificación económica

Con 15,27 % de paridad, un barrido de parámetros sobre aVolClusterPOI mide un
indicador que no es el que corre en el chart. La familia sigue **fuera del
embudo** hasta cerrar esto. Lo que cambió hoy es que el bloqueo dejó de ser
difuso: tiene un mecanismo medido y un pedido de una línea de logging.
