# Manifiesto: costo de ejecución condicionado al libro (QI), NQ · ES · GC · 6E L2, 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Mide el precio después de un fill (selección adversa): **STOP, necesita el OK de Nico.**
**Ledger:** `artifacts/hippocampus/exec_qi_20260924.jsonl`. Familia nueva, **EXEC-QI**. No es una estrategia: es un **modelo de costo**.

## 1. Por qué esta tarea y no otra (priorización 24/09)

| Candidata | Prob. de éxito | Valor si sale bien | Originalidad | Buenas prácticas | Potencia con los datos de hoy |
|---|---|---|---|---|---|
| **EXEC-QI: costo de entrar pasivo vs agresivo según QI** | **Alta**: el efecto de QI ya está medido (+39 pp, estable) y la literatura es sólida | **Transversal**: baja el costo de *toda* estrategia futura. En NQ el spread es de 4,6 ticks, así que ahorrar medio spread por lado mueve la esperanza neta de cualquier candidato | Media-alta: con libro NT8 validado 20/20 y cuatro instrumentos | Alta: el gate de costos realistas es obligatorio en el contrato | **Muy alta**: millones de instantes |
| V-RND, confirmación en NQ | Baja: no se replicó y probablemente está inflado | Alto si sale | Alta | Media | Baja hasta fin de octubre |
| Volatilidad por disputa de nivel (V-VIRGEN y V-GASTADA) | Media | Medio: sirve para tamaño y stops | Alta | Alta | Media |
| Momentum intradía (Gao et al. 2018; Baltussen et al. 2021) | Media-alta en la literatura | Alto | Baja | Alta | **Baja**: ~250 sesiones pre-holdout, un dato por día |
| Re-auditar la familia A y el atlas de GC con controles limpios | Alta como higiene | Bajo: nada apunta a un edge | Baja | Alta | Alta |

**Conclusión:** EXEC-QI tiene la mejor combinación de probabilidad, valor transversal y potencia. Además es la pieza que falta para medir **neto** (prioridad 1 del referente) cualquier candidato que venga: es acumulativa en el sentido de la bola de nieve.

## 2. Pregunta

Para entrar en una dirección (compra o venta), ¿cuánto cuesta en ticks, incluyendo la selección adversa:
- **(A)** cruzar el spread ya (orden a mercado), o
- **(P)** dejar una orden límite en el mejor precio propio y esperar hasta T segundos, cruzando si no se llena?

¿Y cómo cambia eso según el QI del instante?

**Justificación económica:** el QI predice el próximo movimiento del precio medio (Cont, Kukanov y Stoikov; Gould y Bonart; medido acá: +39 pp). Una orden pasiva del lado "bueno" del QI se llena poco y sufre selección adversa. Del lado "malo" se llena seguido pero justo antes de que el precio vaya en contra. El costo óptimo depende del QI. Si el ahorro es de medio tick o más por lado, cambia el signo neto de estrategias marginales.

**Cómo podría refutarse:** que el costo de P, sumando la selección adversa y los no-llenados que terminan cruzando más caro, no sea menor que el de A en ningún tercil de QI. En ese caso, pasivo no conviene y el costo de A es el que se usa en todo backtest.

## 3. Población y espacio enumerado

Qué instantes de decisión se muestrean:
- **Elegido:** grilla de 1 s en todas las sesiones de exploración, fuera de la pausa diaria. Es la decisión "quiero entrar ahora" con probabilidad uniforme.
- **Alternativas no elegidas:** sólo instantes de señal (depende de cada estrategia, no es transversal); sólo RTH (se reporta por bloque horario); instantes después de un trade (sesgo de actividad).

Las dos direcciones, compra y venta, se miden por separado y juntas.

## 4. Simulación de fills (conservadora, escrita antes de mirar)

- **Cola:** al poner la orden en t, queda **detrás de todo el tamaño visible** en el mejor nivel propio. Se llena sólo cuando el volumen negociado a ese precio, del lado contrario, **supera la cola inicial + 1**. Las cancelaciones delante **no** adelantan la orden (supuesto pesimista).
- **Si el precio se aleja** (el mejor nivel propio mejora sin llenar): la orden **no** persigue. Al vencer T, se cruza al precio contrario de ese momento.
- **Resultado por decisión** (ticks, positivo = costo): precio pagado − precio medio en t (el costo de implementación, *implementation shortfall*), más la selección adversa: −(precio medio en t + h − precio de fill) × dirección, con h = 60 s.
- **A:** paga el precio contrario en t + latencia de 250 ms.
- **T** ∈ {5, 30, 120} s: tres variantes declaradas, sin barrido.

## 5. Datos, particiones y potencia

| Instrumento | Partición | Sesiones |
|---|---|---|
| NQ | `P-NQL2-EXP` (01/07–21/08) | 41 |
| ES | `P-VRND-ES` (la misma ventana) | 41 |
| GC | `P-VRND-GC` | 31 |
| 6E | `P-VRND-6E` | 38 |

**Nota:** se reusan particiones de EXPLORACIÓN ya declaradas, y ninguna reserva se toca.
- `P-NQL2-CONF` y el holdout L2 (nov–dic) quedan intactos.
- Reusar esas sesiones para otra pregunta es legítimo en exploración. Como se miran más veces, **nada de EXEC-QI se confirma ahí**: la confirmación va en `P-NQL2-CONF` y en el holdout L2.

**Potencia:** unas 50.000 decisiones por sesión. El IC por sesión del ahorro medio va a ser del orden de ±0,1 tick. La limitación no es N sino **el supuesto de cola**. Por eso se reporta también una variante optimista (cola a la mitad), como banda de sensibilidad.

## 6. Número de miradas

4 instrumentos × 3 terciles de QI × 3 valores de T × 2 direcciones = 72 celdas descriptivas. No se elige "la mejor celda": se publica la tabla completa. Una sugerencia sale sólo si el ahorro de P frente a A es ≥ 0,5 tick con el IC por encima de 0, en los dos supuestos de cola.

## 7. Riesgos

- **Supuesto de cola:** es el riesgo principal. Se mitiga con la banda pesimista-optimista y, más adelante, con la validación en paper/sim de NT8 (fills reales), que es donde sale el costo definitivo.
- **Libro NT8:** validado 20/20 contra Tradovate en NQ y GC (P-76 y P-87), pero los relojes de P-84 excluyen días.
- **Latencia real** de la cuenta: desconocida, se asumen 250 ms.
- No se transportan costos entre instrumentos: cada uno tiene su tabla (regla del proyecto).

## 8. Guardia de controles

No hay diseño evento-contra-control: se compara A contra P en el **mismo instante**. Se registra `design="OTHER"`. La guardia `CTRL_TIMING_V1` no aplica y queda anotado.
