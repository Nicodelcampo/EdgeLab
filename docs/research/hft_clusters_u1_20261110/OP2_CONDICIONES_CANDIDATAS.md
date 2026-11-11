# OP-2 — condiciones candidatas para concentrar el efecto (antes del resultado)

Estado: PLAN (2026-11-11, pedido de Nico: «antes del resultado de la corrida, investigá qué filtros o condiciones podrían aumentar
el efecto»). Escrito ANTES de ver `HFTC_op2.csv`: nada de esto sale de esa tabla. Fuentes: registro de factores de EdgeLab,
`edgelab/research/contexto_comun.py`, y literatura de microestructura (abajo, resumida con palabras propias).

## El punto de partida
«No defiende» es real − control ≈ +0,09, pero la ruptura absoluta del cluster es ≈ 0 en NQ (la mayoría de los eventos) y +0,13/+0,14
en YM. Para que la continuación pague hay que encontrar DÓNDE el cruce del cluster sigue de largo: una condición que lleve la ruptura
bruta a ≳ +0,15 (fricción 0,08 + margen).

## Candidatas, por prioridad (mecanismo → rasgo causal → estado en EdgeLab)
| # | Condición | Mecanismo (fuente) | Rasgo causal propuesto | Estado |
|---|---|---|---|---|
| C1 | **Stops del otro lado:** un pico de 1 min vivo (sin tomar) a ≤ X/2 MÁS ALLÁ del borde lejano del cluster | Las órdenes stop se acumulan justo detrás de niveles visibles; al cruzarlos se disparan en cascada y el movimiento se acelera, mientras que las órdenes de toma de ganancia en el nivel lo frenan (Osler, J. Finance 2003, sobre órdenes de clientes en divisas) | `pico_mas_alla_x`: distancia al pico vivo más cercano del lado de la continuación; estrato «≤ X/2» | **Nunca medido** (`picos_sin_tomar` mide el lado de atrás, y ahí dio rebote: coherente con este mecanismo) |
| C2 | **Veto de huida** (no continuar justo después de un impulso fuerte en contra) | Pista viva propia: lo único del atlas de contexto que no era fricción (−0,05 R DESC / −0,11 R réplica al entrar igual) | `contexto_comun.veto_huida` (ya existe) | Su réplica dirigida pide justamente «una familia de continuación no usada»: OP-2 lo es |
| C3 | **El flujo del cluster a favor de la llegada y cluster joven** | La ejecución de una orden grande (metaorden) empuja mientras dura y después revierte en parte; si el precio vuelve en el sentido del ejecutor y la ejecución sigue, continúa (Bacry et al. 2014; Zarinelli et al. 2014, sobre impacto y su decaimiento) | `net_dir` del cluster × dirección de llegada; edad < 10 min | Medido en DESC para ruptura sin efecto claro (`flujo_alineado` degenerado: casi nunca neutro; edad media +0,048): prioridad baja |
| C4 | **Hueco de liquidez del otro lado** | Los saltos grandes de precio salen de huecos en el libro más que del tamaño de las órdenes (Farmer et al. 2004) | proxy con ticks: pocos trades por tick de precio en el tramo más allá del cluster durante su formación; con L2 (GC/ES), profundidad del otro lado | Nuevo. Con L2 sería la prueba directa del mecanismo (indagación I3 del plan) |
| C5 | **Confirmación cruzada:** NQ y ES (o NQ y RTY) cruzando un cluster en la misma ventana de 2 min | Flujo direccional amplio y no ruido de un contrato; en EdgeLab las señales cruzadas son lo único que pasó canastas (U1-CRUZADO) | `cruce_simultaneo_otro_indice` | Nuevo |
| C6 | **Geometría de salida** que use el recorrido grande (en NQ el avance máximo en 15 min es ≈ 2 X) | Operativa, no de mecanismo | breakeven a X/2 y objetivo 2X; salida por tiempo 30 min | Fijar 2–3 variantes ANTES, nunca buscar la mejor |
| C7 | **YM** | Dato propio en dos períodos (+0,13/+0,14) con pocos eventos | — | Candidata declarada en `PREREGISTRO_OP2.md` |

Descartadas por medición previa (no repetir): tendencia de la sesión y retroceso contra la sesión, volumen del cluster, pendiente de
EMAs, expansión limpia, velocidad de aproximación, desequilibrio de 30 s (`RESULTADO_RUPTURA_INDAGA.md`).

## Cómo probarlas sin contaminar
DESC y abr–sep de NQ/ES/RTY/YM ya están mirados para esta línea. Por eso:
1. Agregar al generador de OP-2 los rasgos C1, C2, C4 y C5 (contrato de rasgos propios: test de prefijo, sin retornos).
2. **No elegir con los datos mirados.** C1, C2 y C7 quedan declaradas desde YA como hipótesis previas (por mecanismo y por la
   pista viva, no por la tabla de OP-2), con signo, estrato y geometría primaria fijos.
3. Probarlas sólo en datos nuevos: el holdout desde el 1-oct-2026 (modo exploratorio, una apertura de la familia, probabilidades
   de azar de desarrollo declaradas) o el forward. Con ≈ 6 semanas de holdout la potencia es baja (MDE ≈ 0,15): las tres previas
   se combinan con BH y se mira estabilidad, no un único p.
4. C3, C4, C5 y C6 se exploran sobre las tablas ya miradas sólo para ordenar prioridades (exploratorio), nunca como evidencia.
