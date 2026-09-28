# Cómo partir las sesiones: exploración, confirmación y holdout (L2, 2026-09-24)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

Pregunta de Nico: ¿conviene partir mitad y mitad, o 3/4 para explorar y 1/4 para confirmar? La respuesta depende de cuatro cosas. No hay una fracción fija correcta.

## Los tres cajones de datos

| Cajón | Para qué | GC L2 | 6E L2 |
|---|---|---:|---:|
| Pre-holdout, **exploración** | Mirar libremente y generar sugerencias | 15 | — |
| Pre-holdout, **confirmación reservada** | Filtro intermedio: ¿la información es real? | 15 | — |
| **Holdout** (01/07–31/12/2026) | G4: **una** apertura por candidato de trading, después de G1–G3 (`edge_validation_contract.md`) | ~49 hoy; ~125 a fin de año si sigue la descarga mensual (P-80) | ~65 hoy |
| Futuro (2027+) | Confirmación natural: datos que nadie pudo mirar | 0 | 0 |

**El holdout no confirma información.** Confirma una regla de trading con P&L neto, una sola vez. Por eso la confirmación reservada pre-holdout es un **filtro para no gastar esa única apertura en ruido**, no la prueba final.

## Las cuatro fuerzas

1. **Necesidad de información de la exploración.** Explorar con pocas sesiones produce sugerencias ruidosas: con 12 celdas miradas, alguna dispara por azar. Más exploración da mejores sugerencias.
2. **Potencia de la confirmación.** La unidad es la **sesión**, no el evento: los eventos de un mismo día comparten régimen. El error de la confirmación es `SD_entre_sesiones / √n_conf`. La potencia se calcula con el efecto **encogido**: el que se ve en exploración está inflado por haber sido elegido (maldición del ganador).
3. **Tamaño del holdout.** Si el holdout va a ser grande (GC: ~125 sesiones), la confirmación intermedia puede ser más chica: su trabajo es filtrar, no decidir.
4. **Costo de un falso negativo.** Una confirmación con poca potencia mata efectos reales. Pasar ruido cuesta una apertura del holdout. Los dos errores cuestan.

## Regla propuesta (reemplaza la "mitad y mitad" fija)

1. **Antes de explorar**, estimar la variabilidad entre sesiones de la métrica. Target-free cuando se pueda; si no, con la primera tanda de exploración.
2. **Tamaño de la confirmación** = el mínimo `n_conf` que da **potencia ≥ 80 %** (α = 5 % a una cola) para el **efecto mínimo que importa**. En L2 ese efecto se define por la economía (costo del instrumento), no por lo que se vio. Todo lo demás va a exploración.
3. Si `n_conf` resulta mayor que la mitad, **no hay datos suficientes para explorar y confirmar en el mismo lote**. Entonces se explora ahora y se confirma en el futuro (datos 2027, rol `FUTURE`).
4. **Nunca partir dentro de la sesión** (mañana/tarde del mismo día): las dos mitades comparten régimen y la confirmación queda inflada.
5. La partición se declara en el Brain **antes** de mirar retornos, y no se mueve después. `record_partition` rechaza solapamientos.

**3/4 y 1/4** conviene cuando el efecto que importa es grande respecto de la variabilidad entre sesiones, o cuando la confirmación intermedia es solo un filtro y detrás hay un holdout grande. **Mitad y mitad** conviene cuando el efecto es chico y la confirmación tiene que valer por sí misma.

## Aplicado a GC y 6E

Variabilidad entre sesiones medida en la exploración de GC (15 sesiones):
- ruptura del nivel con el control correcto: 0,06–0,11;
- fade: 1,1 ticks a 10 s, 1,6 a 30 s, 2,6 a 60 s y 9,2 a 300 s (derivada del IC bootstrap, aproximada).

**Efecto mínimo detectable** (una cola, 5 %, potencia 80 %) según cuántas sesiones se usan para confirmar:

| Sesiones de confirmación | Fade 10 s | Fade 60 s | Fade 300 s | Ruptura 60 s |
|---:|---:|---:|---:|---:|
| 4 | 1,4 t | 3,3 t | 11,4 t | 0,12 |
| 8 (≈ 1/4 de 30) | 1,0 t | 2,3 t | 8,1 t | 0,08 |
| 15 (1/2 de 30) | 0,7 t | 1,7 t | 5,9 t | 0,06 |
| 30 | 0,5 t | 1,2 t | 4,2 t | 0,04 |
| 60 | 0,4 t | 0,8 t | 3,0 t | 0,03 |

**Qué efecto importa en GC.** El spread cotizado de este feed es de ~4 ticks (P-76), así que un movimiento que no supere ~4–5 ticks brutos no paga la ida y vuelta.

**Conclusión:**
- **Horizontes cortos (≤ 60 s): conviene 3/4 y 1/4.** Con 8 sesiones ya se detecta un efecto bastante menor que el costo. Lo que no se detecta con 8 sesiones tampoco pagaría el costo. Las sesiones de más rinden más explorando.
- **Horizontes largos (≥ 5 min): ninguna partición de 30 sesiones alcanza.** Confirmar un efecto del tamaño del costo necesita ~30 sesiones solo para confirmar. Se explora en pre-holdout y se confirma con datos futuros (2027).
- **6E (4 sesiones): no se parte.** Todo es descriptivo target-free (rol `FUTURE`).

**GC hoy:** la partición ya declarada (15/15) no se mueve. Mover sesiones de la reserva a exploración es seguro, pero hoy no hay para qué: después del chequeo de geometría, no hay ninguna sugerencia que valga gastar la reserva (ver el atlas). La próxima hipótesis de GC declara su propio tamaño de confirmación con esta tabla.
