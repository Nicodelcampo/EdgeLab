# AVZP2-REBOTE — ¿el precio rebota en las zonas de aVolZonePOI2 más que en zonas al azar? — manifiesto — 2026-10-07

Pedido de Nico: "veo que el precio rebota más en esos clusters" y "fijate si es mejor o peor que aVolClusterPOI".
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. **Información, no P&L.**
Escrito antes de calcular nada con estos datos.

## Familias (independientes, ledger propio)
- `AVZP2` (nueva): aVolZonePOI2 con parámetros por defecto, réplica con paridad exacta (45.916 bloques, 2.723 zonas,
  641/641 OB). No hereda nada de AVCL ni de HFTV4.
- `AVCL`: aVolClusterPOI v0.5 (paridad 200t 338/338), parámetros de la paridad (p95, invalidación None, MaxAge 500).
  Se usa como comparador con la misma regla de evento.

## Datos
- MNQ, barras de 200 ticks, **cada contrato con sus propios ticks** (sin merge, sesiones del RESOLVER).
- **Descubrimiento:** 09-25, 12-25, 03-26, 06-26. **Confirmación (una sola vez):** 09-26, 12-26.
- Holdout ≥ 2026-10-01: no se lee.

## Espacio de eventos (regla de población)
| familia de evento | ¿se mide? | por qué |
|---|---|---|
| creación | no | la pregunta de Nico es el rebote al volver |
| alejamiento sin volver | no (ya fue HFTV4-RETORNO, otra familia) | |
| **primer regreso (primer toque después de salir de la zona)** | **sí** | es lo que Nico ve: el precio vuelve y rebota |
| toque n-ésimo | no | se deja para después, si el primero muestra algo |
| invalidación / expiración | no | aVolZonePOI2 no tiene ciclo de vida |
| estado continuo (distancia a la zona más cercana) | no | ver "No medido" |

## Evento (causal)
1. La zona está disponible desde la barra siguiente a su creación.
2. **Salida:** primera barra completa fuera de la zona. El lado (arriba o abajo) es el lado de la salida.
3. **Regreso:** primera barra posterior que toca la zona (low ≤ alto y high ≥ bajo), en la misma sesión y dentro de
   2.000 barras.
4. Borde de referencia: el borde del lado de la salida. `D = max(2 × altura, 8 ticks)`.

## Resultados (desde la barra siguiente al toque, misma sesión, hasta 200 barras)
- **Canal direccional — rebote:** el precio llega a `borde ± D` del lado de la salida antes de llegar a `borde ∓ D`
  del lado opuesto. Si los dos ocurren en la misma barra, el caso es ambiguo y se excluye. Si no se llega a ninguno,
  queda NaN.
- **Canal no direccional:** llega a cualquiera de los dos niveles dentro de 50 barras (el nivel es "activo").
- Descriptivos: el tiempo hasta el resultado y la distribución del rebote por altura.

## Nulo: pseudo-zonas
- 3 por zona real, en barras al azar del mismo contrato y la misma franja de 30 min CT.
- Misma altura y misma posición relativa al close que la zona real en su creación.
- Misma regla de salida, regreso y resultado.

## Estimador
β (real − pseudo) en un modelo lineal de probabilidad con FE (contrato × franja, tercil de amplitud de 50 barras al
toque, decil de D en ticks) y SE clusterizado por sesión. Bilateral. Se publica el MDE (2,8 × SE).

## Pruebas formales (4, Holm), canal direccional
1. AVZP2, todas las zonas.
2. AVZP2, azules (no OB).
3. AVZP2, rojas (OB).
4. AVCL.

Pasa en descubrimiento con Holm p ≤ 0,05 y β > 0. La confirmación replica sólo las que pasan.

**Mejor o peor que aVolClusterPOI:** se compara el exceso sobre su propio nulo (β_AVZP2 − β_AVCL), de forma
**descriptiva**, con IC por bootstrap de sesiones. No es una prueba formal.

## Justificación económica
Un cluster de volumen anómalo marca inventario (participantes con posición en ese precio). Al volver, defienden o
cierran posiciones y el precio reacciona en el lado del que vino. Si es así, el rebote es mayor que en un nivel
cualquiera a la misma distancia.

## Cómo podría refutarse
- β ≈ 0 con el MDE publicado: el rebote que se ve sería la tasa base de cualquier nivel (como pasó con HFTV4-RETORNO).
- Un efecto sólo en el canal no direccional: el nivel "atrae movimiento" pero sin lado.

## NO MEDIDO (explícito, para no confundirlo con "medido y no dio")
1. **P&L, costos, entradas, stops.** Esto es información. Un rebote más probable no implica un trade rentable.
2. **El toque n-ésimo**, zonas ya tocadas, ni la "fuerza" que pierde una zona con los toques.
3. **Otros horizontes y distancias:** sólo `D = 2 alturas` (piso de 8 ticks) y 200 barras. Un rebote más chico (por
   ejemplo, 1 altura) o más lento no queda medido.
4. **Parámetros del indicador distintos de los por defecto:** score por densidad, otro percentil, otra franja, otros
   umbrales de OB. Sólo los valores por defecto.
5. **Otras escalas de barra** (sólo 200t) y **otros instrumentos** (sólo MNQ). Nada sobre ES, NQ, MGC u otros.
6. **El chart fusionado (merge back-adjusted)** que usa Nico: se mide cada contrato con sus ticks. Antes del roll, las
   zonas del chart salen del contrato anterior; esa serie no es la que se mide acá.
7. **Confluencia:** zonas superpuestas, racimos, cercanía a otras zonas o a otros indicadores.
8. **La interacción con el régimen** (tendencia o rango, volatilidad), más allá de usar la amplitud como control.
9. **El primer toque antes de salir de la zona** (cuando el precio nunca la abandonó). Por definición del evento,
   esas zonas no entran.
10. **La comparación con aVolClusterPOI como prueba formal:** queda descriptiva. Además, la comparación es con la
    v0.5 y los parámetros de la paridad, no con otra configuración de AVCL.
11. **Si el color rojo (OB) mejora o empeora el rebote respecto del azul**, como contraste directo entre las dos:
    sólo cada una contra su nulo.
12. **Las sesiones con datos parciales** (contrato no líder): quedan afuera por el RESOLVER.

## Enmienda 1 (2026-10-08, después de ver los resultados; OK de Nico: "dale") — nulo apareado por la regla OB
Motivo: el nulo original no copia la condición que define a una roja, así que el efecto rojo podía ser del
"alejamiento limpio" y no de la zona (punto A del acta de resultados).
- **Población:** sólo zonas rojas (AVZP2, regla OB por defecto: 100 barras, 3 alturas, 8 ticks, 2 %).
- **Nulo apareado:** pseudo-zonas con la misma geometría y franja que las rojas (10 candidatas por zona). Se les
  aplica **la misma regla OB que al indicador**: desde la barra siguiente a la colocación, el precio llega a
  max(3 × altura, 8 ticks) antes de 100 barras, con ≤ 2 % del volumen operado dentro hasta ese momento. Sólo las
  que la cumplen entran al nulo.
- Mismo evento (salida → primer regreso), mismo resultado (rebote de 2 alturas), mismo estimador.
- **Prueba única en descubrimiento** (09-25 → 06-26). Pasa si p ≤ 0,05 y β > 0. Si pasa, se corre una única
  confirmación en 09-26 y 12-26; los datos de confirmación ya se miraron una vez para las rojas (contra el nulo
  simple), y eso queda declarado.
- Descriptivo: también se mide el canal no direccional.
- **Cómo podría refutarse:** β ≈ 0 contra el nulo apareado, con el MDE publicado. En ese caso, el rebote de las rojas
  es del alejamiento limpio y no del cluster de volumen.
