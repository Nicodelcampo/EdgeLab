# AREAS-EXP-1 — Áreas de zonas OG/VI, expansión y regreso: especificación exacta (v1)

Estado: PROPUESTA v1.1 (diseño; nada corrido sobre desenlaces). Pedido de Nico, 2026-10-22.

> **Cambios v1.1, todos decididos sin mirar desenlaces** (por conteos E0, controles sintéticos y pedidos de Nico):
> 1. **Área = banda de altura ≤ W con ≥ N zonas vivas.** W es perilla: 5, 15, 40 y 100 puntos. La v1 unía zonas pegadas y daba 0,35 áreas por día.
> 2. **Una misma área se evalúa en varios ciclos.** Atravesarla no la invalida; se ponen hasta 10 ciclos y vive mientras viva su última zona. Si el precio vuelve antes de alejarse 1·H, el ciclo se reinicia y el área no se descarta.
> 3. **A/H va de ≥1 a ≥8**, con espaciado geométrico: variantes bien distintas y distancias muy variadas.
> 4. **Ambigüedad M1:** si una vela toca el stop y el objetivo, o en la vela del llenado de una límite, decide el ORDEN REAL DE LOS TICKS. Un stop saltado se llena en el tick real. Se informa cuántos casos se resolvieron así.
> 5. **Grilla:** 12 (N×W) × 3 x × 108 ejecuciones × 4 A/H × 4 comercio × 4 p_vol × 3 v_rel = **746.496 celdas por fuente**.
> 6. **Núcleo genérico reutilizable** (`edgelab/research/grilla_masiva.py`): tensor con perillas ordinales, criba FDR, máscara de celda y meseta. El kernel se empaqueta con `tools/kaggle_areas/construir_kernel.py`.
> 7. **Controles sin mercado:**
>    - con ruido puro, 0 nominadas sobre 746.496 celdas;
>    - con una reversión plantada, gana HACIA el área, como corresponde;
>    - la búsqueda compilada de áreas coincide exactamente con un oráculo en Python, incluidos los empates casi exactos.


**Pregunta.** ¿Hay un grupo de zonas que, combinado con cierto alejamiento, cierto acercamiento y cierta ubicación del volumen, con cierto tipo de entrada, SL, TP y BE, dé una estrategia rentable neta que replique fuera de muestra? Se corre para las zonas del **futuro (NQ)** y para las del **índice (USATECH, Dukascopy)**, por separado.

**Justificación económica.**
- Un área con muchas zonas de desbalance (OG/VI) marca un precio donde hubo urgencia de un lado.
- Tras alejarse, el regreso del precio puede encontrar órdenes remanentes (rebote) o vacío (atraviesa el área).
- El volumen negociado durante la expansión dice dónde quedó posicionado el mercado. Por eso puede servir para decidir si entrar y en qué precio.

**Cómo podría refutarse.** El experimento falla si ninguna celda pasa a la vez estos cuatro filtros:
- el tamiz FDR en descubrimiento;
- la meseta (las celdas vecinas también positivas);
- la réplica pre-registrada, con nivel LORD++;
- el económico con costos canónicos.

Si ninguna pasa, la familia queda refutada con este alcance exacto.

## 1. Datos (sólo pre-holdout; `edgelab/holdout.py`)
| Fuente | Precio | Volumen | Tick |
|---|---|---|---|
| NQ futuro | `price_ticks` del release `liquid_tick_v1` (contrato líquido por sesión; `outside_regular == False`) | `volume` de cada operación (real) | 0,25 |
| USATECH índice (CFD) | mid = (bid + ask)/2 de los ticks de Dukascopy | `bid_vol + ask_vol` del tick (**liquidez cotizada, no operaciones**: proxy) | 0,01 |

- Velas M1 desde ticks.
- Zonas LUX-IMB (OG + VI) con `parity_luximb.detect`: paridad NT8 exacta en NQ; en USATECH no está medida (`PARITY_ABSTAIN`).
- Cada zona nace al cierre de su vela y vive 500 min.

## 2. Objetos y variables (cada una es una perilla)

**Zona viva en t:** creada antes de t y con t < t1.

**Comercio de una zona** (desgaste):
- `visitas_i(t)` = cantidad de veces que el precio ENTRA a la zona desde afuera, entre su creación y t.
- Se cuenta en M1: una vela cuyo rango corta la zona, con la vela anterior fuera de ella.

**Área** (la marca). En cada cierre M1:
- se ordenan las zonas vivas por precio;
- se unen las que se superponen o están a ≤ `G` ticks (G = 4 en NQ; en USATECH, G = 1 pt);
- un grupo con **≥ N zonas** es un área: [`lo`, `hi`], altura `H = hi − lo`;
- **el área se marca en el primer cierre en que el grupo alcanza N** (`t_m`).

**Regla de no repetición (pedido de Nico: «si hay dos pegadas cuenta una sola»):**
- un área nueva se descarta si se superpone, o queda a ≤ G, de un área marcada en los 500 min anteriores (misma N);
- el grupo que sigue creciendo no se vuelve a marcar.

**Lado y alejamiento.** Desde `t_m`:
- el **lado** es por dónde sale el precio, por cierre: arriba de `hi` o abajo de `lo`;
- si vuelve a entrar al área antes de alejarse 1·H, el evento se descarta: no hubo expansión;
- **alejamiento** `A(t)` = distancia máxima desde el borde cercano hasta el extremo (`E`, máximo o mínimo) entre `t_m` y t. Se mide en ticks y normalizado como `A/H`.

**Acercamiento y disparo.**
- Una vez que el precio dejó de hacer extremo, se evalúa la entrada.
- **Acercamiento** `D(t)` = distancia del cierre al borde cercano.
- El **disparo** es el primer cierre en que `D/A ≤ x`, es decir, el precio ya recorrió `(1−x)` del camino de vuelta.
- Hay un solo disparo por (evento, x), con tope de 500 min desde `t_m`.

**Variables medidas en el disparo (sin mirar nada posterior):**
- `N`: cantidad de zonas del área (al marcar).
- `H`: altura del área (ticks).
- `comercio` = media de `visitas_i` sobre las zonas del área, al disparo. Es el índice global de desgaste.
- `A/H`: alejamiento normalizado.
- **Ubicación del volumen** `p_vol`:
  - se toma el perfil de volumen negociado entre `t_m` y el disparo, sólo en precios entre el borde cercano y `E`;
  - se divide en 10 tramos iguales;
  - `p_vol` es la posición (0 = borde del área, 1 = extremo) del tramo de máximo volumen.
- **Cantidad de volumen** `v_rel` = volumen en ese tramo ± 1 / volumen medio por minuto de la sesión anterior × minutos transcurridos.
- `hora` de disparo (UTC) y `dir` del lado: quedan registradas como diagnóstico, no como perilla.

## 3. Entradas, dirección y salidas (perillas de ejecución)

**Dirección:**
- `HACIA`: a favor del regreso, hacia el área. Si el precio está arriba, venta.
- `REBOTE`: en contra del regreso, se espera que el área rechace.

**Entrada:**
- `E1`: mercado al cierre M1 del disparo, con 1 tick peor.
- `E2`: límite en el precio del tramo de máximo volumen (`p_vol`). Se llena sólo si el precio lo atraviesa por 1 tick, dentro de los 120 min siguientes al disparo; si no, no hay operación.
- `E3`: límite en el borde cercano del área, con la misma regla de llenado.

**Objetivos:**
- `HACIA`: TP en el borde cercano (`T1`), el 50 % del área (`T2`) o el borde lejano (`T3`).
- `REBOTE`: TP en 1R o 2R, o en el extremo `E`.

**Stop:**
- `S1` = entrada ± 0,5·(distancia al TP);
- `S2` = entrada ± 1,0·(distancia al TP);
- `S3` = más allá del extremo `E` (HACIA) o del borde lejano del área (REBOTE), con 1 tick.

**BE:** ninguno, o mover el stop a la entrada al recorrer 1R.

**Salida forzada:** 240 min o fin de sesión, a mercado.

**Fills:**
- stop a mercado con hueco: se llena al open peor (G0.4);
- si en la misma vela se tocan SL y TP, cuenta el SL;
- NQ se simula con ticks;
- USATECH con M1, conservador.

**Costos** (`edgelab/costos.py`):
- NQ: escenario base y adverso;
- USATECH: no tiene costo canónico (es un CFD), así que se informa en bruto y con el costo de NQ como referencia. **Es sólo información: no es operable tal cual.**

## 4. Grilla y número de pruebas
| Perilla | Valores | n |
|---|---|---|
| N (zonas por área) | ≥ 3, ≥ 5, ≥ 8 | 3 |
| A/H mínimo | ≥ 1, ≥ 2, ≥ 4 | 3 |
| x (acercamiento) | 0,75, 0,50, 0,25 | 3 |
| comercio máximo | 0, ≤ 1, ≤ 3, cualquiera | 4 |
| p_vol | < 1/3, 1/3–2/3, > 2/3, cualquiera | 4 |
| v_rel | tercio bajo, alto, cualquiera (cortes fijados en descubrimiento, sin desenlaces) | 3 |
| dirección × objetivos | HACIA × 3 + REBOTE × 3 | 6 |
| entrada | E1, E2, E3 | 3 |
| stop | S1, S2, S3 | 3 |
| BE | no, 1R | 2 |

Son **139.968 celdas por fuente y por instrumento**, unas 280 mil en total. Con N_eff (Li-Ji sobre las celdas candidatas) el número efectivo es mucho menor, porque las celdas están anidadas.

## 5. Embudo (`edgelab/funnel/escalera.py`)
1. **E0 (sin desenlaces, ya permitido):** conteos de eventos y distribución de variables por fuente. Los cortes de `v_rel` y la verificación de que cada celda puede tener ≥ 30 operaciones se fijan acá.
2. **E1 tamiz (descubrimiento):** por celda, media neta por operación y t con error agrupado por sesión (aproximación por tensor). FDR BH-Storey a q = 0,10.
3. **E2 en sobrevivientes:**
   - bootstrap por sesiones;
   - meseta (≥ 2/3 de vecinos ±1 paso positivos);
   - recorte Harvey-Liu con N_eff;
   - económico (sin las 5 mejores, ningún mes > 80 %, adverso).
   - Hasta 3 celdas por fuente pasan a réplica, elegidas por estadístico de candidato pre-declarado, no por P&L máximo.
4. **E3 réplica (corrida aparte, pre-registrada, celdas congeladas):** nivel LORD++.
5. **Holdout:** sólo con `LISTA_PARA_HOLDOUT` y el monitor secuencial.

## 6. Particiones (A DECIDIR POR NICO antes de correr)
- **Descubrimiento:** NQ 2025-08-05 → 2026-03-31; USATECH, mismo período.
- **Réplica, opciones:**
  - (a) USATECH 2023-01 → 2025-07: nunca mirado, alta potencia, pero sólo para la fuente índice;
  - (b) NQ abr–sep 2026: una sola apertura por familia; los meses de NQ se vieron en el visor para otras preguntas LUX-IMB;
  - (c) ES como réplica entre activos.

## 7. Implementación (optimizada)
- Los ticks se leen por row group.
- El volumen por precio se guarda disperso, ordenado por minuto.
- Las variables se calculan una vez por (evento, x).
- Los desenlaces se calculan una vez por (evento, x, entrada, dirección, objetivo, stop, BE): unos 324 por evento.
- Las perillas de filtro se discretizan. Para cada combinación de ejecución se arma un tensor (N × A/H × comercio × p_vol × v_rel) con suma, suma de cuadrados y conteo; con **sumas acumuladas** salen las 140 mil celdas sin recorrer eventos.
- La inferencia cara (bootstrap por sesiones) se hace sólo sobre sobrevivientes.
- Todo corre en un kernel de Kaggle por fuente. No hay código del repo en el kernel: el script se empaqueta con el detector y el motor incluidos, con sus SHA.

## 8. Riesgos
- **Multiplicidad enorme:** se controla con FDR más réplica, y no con exigir error familiar en descubrimiento.
- **Celdas con pocas operaciones:** mínimo 30 operaciones y 20 sesiones por celda.
- **Volumen del índice:** es cotizado, no negociado.
- **Las combinaciones anidadas comparten operaciones:** por eso se usan N_eff y meseta, no conteo bruto.
- **La definición de «área» es una elección:** G y la regla de no repetición son perillas fijas en v1. Si nada pasa, puede ser un nulo del estimador (ATJ-18): se informa el MDE.
