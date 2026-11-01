# Lectura de los documentos de @pablo.robotedge (RobotEdge): qué sirve para EdgeLab

Estado: VIGENTE. Fecha: 2026-11-01. Insumos (subidos por Nico):
- `EdgeLab_Pablo_RobotEdge_237_Deep_Dive_Completo.md`
- `EdgeLab_Pablo_RobotEdge_237_Todos_Listado.md`

Son resúmenes generados de 237 posts. Referente: `docs/NORTH_STAR.md`. Objetivo concreto de EdgeLab: ganar dinero en prop firms, Axi
Select y capital propio. Este perfil habla justamente de prop firms, así que se lee con ese foco.

## Conclusión corta
- **No trae edges de mercado.** Lo que propone como estrategia es:
  - "EMA200, sólo largos en NQ": es beta del Nasdaq con un filtro de tendencia;
  - SMA 300/1000;
  - RSI más estocástico.
  
  Nada de eso tiene una hipótesis de flujo ni una validación publicada.
- **Su tesis real es otra:** una evaluación de prop firm es una opción barata. Se pierde como máximo la cuota y se cobra si se llega al
  pago. Con reglas de consistencia y drawdown, la **forma** de la distribución del P&L cambia la probabilidad de cobrar aunque la
  ventaja sea cero. Esa tesis es correcta en principio, y EdgeLab ya tiene con qué medirla: `edgelab/propfirm/ev.py`, un Monte Carlo
  del ciclo completo con consistencia, límite de pérdida diaria, trailing, retiros y el **control de ventaja cero** (Hall 2026, §2.4).

## Sus números, contrastados con nuestro simulador (ventaja cero)
Reglas de `config/propfirms/catalogo_lucid_50k.json` (LucidFlex 50K: objetivo $3.000, pérdida máxima $2.000 con trailing al cierre,
consistencia 50 %). El catálogo está marcado **no verificado**. NQ mini con fricción canónica de $30,9 por viaje, 1 operación por día,
ventaja cero, 6.000–8.000 caminos.

| Bracket | Cuota | Pase | Cobra algún pago | EV por intento |
|---|---|---|---|---|
| RobotEdge 50K: TP $1.200 / SL $2.000 | $192 (catálogo) | 0,24 | 0,04 | −$69 ± 9 |
| ídem | **$80,50 (promo que cita)** | 0,24 | 0,04 | **+$41 ± 8** |
| 1:1, $500 / $500 | $80,50 | 0,17 | 0,08 | $0 ± 4 |
| "13:1 invertido", TP $150 / SL $2.000 | $192 | 0,15 | **0,00** | −$192 |
| 1:3, $1.500 / $500 | $192 | 0,22 | 0,04 | −$104 ± 7 |

Lectura:
1. **La forma sí importa.** A ventaja cero, el bracket de RobotEdge pasa más (24 %) que uno 1:1 (17 %). El EV sólo queda positivo con
   la cuota de promoción, y por poco: unos +$41 por intento antes del riesgo de baneo y de que las reglas reales difieran del
   catálogo.
2. **El "13:1 con 93 % de aciertos" no cobra en este modelo.** Gana a menudo, pero no llega al pago con estas reglas. El 93 % de
   aciertos es la fórmula de la ruina del jugador, P = SL/(SL+TP). A ventaja cero no suma EV: lo traslada a una cola de pérdidas
   grandes.
3. **Una ventaja real chica multiplica el valor de la opción.** Si la cartera viva consigue una estrategia con edge neto positivo
   aunque sea pequeño, elegir el bracket y el tamaño por cuenta con este simulador vale más que el bracket de un post.

## Lo que sí conviene tomar
1. **Optimizar el bracket por firma** con `edgelab/propfirm/ev.py`, nunca a ojo:
   - TP/SL y tamaño que maximizan el EV por intento dado el edge medido en papel de cada estrategia;
   - siempre comparado con su control de ventaja cero.
   
   Esto entra en la asignación de la cartera viva (`edgelab/cartera/asignacion.py`), cuando una persona habilite cuentas de evaluación.
   Requisito previo: **verificar las reglas del catálogo** (hoy `verified=False`) y las cuotas reales. Es tarea humana.
2. **Guardas de cumplimiento en la asignación** (riesgo de baneo, no de mercado). Los tres primeros puntos de la lista de abajo son
   verificables en código. Proponerlos en un PR de la cartera, con las reglas confirmadas por firma:
   - Nunca posiciones **opuestas** en el mismo instrumento, ni en instrumentos correlacionados (ES largo / NQ corto), entre cuentas de
     la misma firma.
   - Todo cerrado antes del cierre que exija la firma. Lucid: 16:45 ET.
   - Nada de microscalping: más del 50 % de la ganancia en operaciones de menos de 5 segundos. Ninguna familia actual lo hace.
   - No pasarse del máximo de contratos ni del límite de cuentas por hogar.
   - Evaluar si las entradas idénticas a la misma hora en varias cuentas de una firma se marcan como "coordinadas". Depende de cada
     firma.
3. **Riesgo de ruina del bankroll de evaluaciones.** Cuántas cuotas hay que tener para que una racha de evaluaciones fallidas no vacíe
   el presupuesto. Sale del mismo Monte Carlo (p_pase, cuota y pagos). Es útil como dato para quien decida comprar cuentas.

## Lo que no se toma
- **Rankings de indicadores** (S/A/B…) y "EMA200 sólo largos": opiniones sin validación. El sesgo alcista del Nasdaq es beta, no edge.
- **Testimonios de payouts y "$20k/mes"**: no verificables. Además, un pago no es rentabilidad neta de cuotas.
- **La lectura de Apex como "bote de exámenes"**: puede ser cierta, pero no cambia nada medible para EdgeLab más allá de verificar las
  reglas de cada firma antes de habilitarla.
