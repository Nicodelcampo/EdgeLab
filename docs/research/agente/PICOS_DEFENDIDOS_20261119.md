# Pre-registro: PICOS-DEFENDIDOS (2026-11-19)

Estado: PROPUESTA. Pre-registro committeado antes de correr; lo lanza otro agente (§10).
Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa **EF2 exploratorio** (grilla masiva, `docs/research/GUIA_GRILLA_MASIVA.md`).

| Pieza | Ruta |
|---|---|
| Código | `edgelab/research/agente/picos_defendidos.py` |
| Tests | `tests/agente/test_picos_defendidos.py` |
| Campañas | `config/autopilot/grillas/campanas/PICOS-DEFENDIDOS-{NQ,ES}.json` |

## 1. La idea (Nico, captura de NQ del 18-nov y nota)

Es una estrategia tendencial, o sin filtro de tendencia. Son dos variantes.

**Secuencia:**
1. Se forman picos.
2. El precio se aleja considerablemente.
3. Vuelve a acercarse considerablemente al último pico, pero no lo toma.
4. Se vuelve a alejar: «están defendiendo el nivel».

**Hipótesis:** en la próxima ocasión, o cuando aparezca un disparador, el precio **sí** toma los picos y puede ir más allá. El tamaño
del objetivo mide cuánto más allá.

**Ejemplo de la captura (10 min, bajista):**
- dos mínimos al final del impulso;
- reversión a la media;
- un impulso nuevo que se acerca a los mínimos sin tomarlos;
- un nuevo alejamiento.

Ahí se abren las entradas en corto.

**Disparadores propuestos por Nico:**
- tocar la EMA;
- cruzar la EMA en contra y volver a cruzarla;
- cruce de dos EMAs;
- espejo de un impulso contrario, laxo para que no filtre todo;
- cruzar el POC reciente en contra y a favor;
- entrar apenas se alejó;
- entrar cuando, después de alejarse, volvió x hacia el nivel.

También pidió distintas definiciones de tendencia (una o dos EMAs, varios períodos), configuraciones de picos, temporalidades y
distancias de SL y TP.

## 2. Antecedentes y linaje (fuente antes que recuerdo; verificados el 2026-11-19)

| Antecedente | Qué midió | Qué dice para esta familia |
|---|---|---|
| **IPC-NIVEL-MES** (`RESULTADO_IPC_NIVEL_MES_DESCUBRIMIENTO_20260928.md`) | MES 25t; techos con ≥ 3 visitas | El nivel se barre **6,2 pp menos** que un pivote suelto. Va **en contra** de la hipótesis: un nivel defendido resiste más. |
| **DOBLE-RETROCESO** (`doble_retroceso_20261104/RESULTADO_DOBLE_RETROCESO.md`) | 10 activos; continuación alejándose del nivel tras «retroceso 2 cerca de P2 sin tomarlo» | 0 celdas FDR. Canastas ≤ 0, en contra en ES. Holdout forzado: −0,30R agregado. |

Sobre IPC-NIVEL:
- La población es distinta: sin tendencia, sin disparador, y el desenlace fue la carrera simétrica.
- Su propia acta deja abierto que «resiste» sea la suma de barridos fuertes y rebotes. Separarlo por contexto, por ejemplo por
  tendencia, quedó **pendiente**: esta familia lo mide.

Sobre DOBLE-RETROCESO:
- Comparte la población «acercamiento al nivel sin tomarlo».
- La lectura es la **opuesta**: allá se opera alejándose del nivel; acá, hacia el nivel y a través de él.

**Linaje:** padre `DOBLE_RETROCESO_<activo>`, hereda la multiplicidad `bruto`, `linaje_como: "informacion"`. IPC-NIVEL no tiene
familia en el contador global y no se puede declarar como padre. Se cita acá como evidencia previa en contra.

Coordenadas en la gramática (`edgelab/research/agente/gramatica.py`):

| Eje | Valor |
|---|---|
| objeto | picos de swing (primitiva de precio, como `expansion`) |
| evento | `toque_n` fallido y su siguiente aproximación |
| lectura | `ruptura` |
| régimen | `tendencia` (perilla) |
| entrada | varias |
| salida | `estructural` / `multiplo_R` |
| horizonte | `intradia` |

## 3. Justificación económica

Un nivel que se defendió dos veces, con un acercamiento que no lo tomó y un nuevo alejamiento, acumula detrás:
- stops de quienes operan el rebote, ubicados justo más allá del nivel;
- órdenes de ruptura en reposo.

Si la tendencia de fondo empuja hacia el nivel, la defensa se agota. La próxima llegada ejecuta esa liquidez y el movimiento se
acelera más allá. **Del otro lado pierde** quien vende o compra el rebote del nivel defendido con el stop pegado a él.

## 4. Cómo podría refutarse

- **DESC:** 0 celdas nominadas por la criba de la campaña (FDR q 0,10 o maxT, según congele el embudo) y una canasta de pistas en
  réplica ≤ 0 con potencia.
- **Variante tendencial sin ventaja:** las celdas con `tendencia = a favor` no superan a las de `en contra`. La mitad tendencial de
  la idea no aporta.
- **Antecedente confirmado:** el signo de IPC-NIVEL se reproduce acá, con el nivel defendido tomado menos de lo necesario para pagar
  la fricción.
- **Integridad:** falla de alineación, placebo o latencia en INTEGRIDAD.
- **OOS u holdout:** refutación con potencia.
- **Nulo sin potencia:** no mata la familia. Publica su MDE y queda `SIN_POTENCIA` o `PISTAS_VIVAS`.

## 5. Población: espacio de eventos enumerado antes de congelar

| Familia de evento | ¿Se mide? | Por qué |
|---|---|---|
| creación (nace el pico) | no | Es el punto de partida; operar la creación es otra hipótesis (imán o rebote). |
| aproximación | sí | Es la segunda llegada, la que según la hipótesis toma el nivel. |
| primer toque | no | El pedido exige que el primer acercamiento NO tome el nivel. Es la condición, no el desenlace. |
| toque n-ésimo | **sí** | Acercamiento fallido + alejamiento + disparador = el evento congelado. |
| invalidación (se toma antes del disparo) | no | Mata el candidato. Medirla sería otra familia (ruptura sin defensa). |
| expiración (60 velas sin disparo) | no | Mata el candidato. |
| confluencia (varios niveles) | parcial | El nivel PAR es la confluencia de dos picos. Confluencias con otros objetos: no. |
| estado continuo (distancia al nivel en cada vela) | no | Tendría más potencia, pero la idea es de secuencia. Queda escrito como alternativa. |

**Evento contra estado:** se mide un evento (una fila por disparo). La alternativa de estado se descarta porque la hipótesis exige
la secuencia completa.

## 6. Definiciones exactas (código: `picos_defendidos.py`)

- **Velas:** 1, 3, 5, 10 y 15 min, armadas desde las M1 del contexto (t = cierre).
  - Una vela de N minutos se conoce en la M1 que cierra su bloque. Si falta esa M1, en la primera M1 del bloque siguiente.
  - La última vela abierta nunca cuenta; tampoco una vela cortada por el fin de sesión sin cerrar.
- **A:** ATR(14) causal de la temporalidad (`zonas_gaps._atr_causal`).
- **EMAs:** `estrategias._indicadores_ext.ema`, sobre los cierres de la temporalidad.
- **Niveles (perilla `pico`)** con `picos_robustos.zigzag_alterno` en espacio techo; los pisos se espejan con x = −precio:
  - `Z15`: cada pico del zigzag de 1,5 A;
  - `Z3`: zigzag de 3 A;
  - `PAR`: dos picos consecutivos del zigzag de 1,5 A con |P1 − P2| ≤ 0,25 · excursión central. El nivel es el más extremo y se
    conoce en la confirmación del segundo.
  - Un nivel ya tomado entre su pico y su confirmación no entra.
- **Secuencia** (mínimos del detector; lo demás es variable):
  1. Alejamiento 1 ≥ **2 A**.
  2. Acercamiento a ≤ **1 A** del nivel sin tomarlo («tomar» = un máximo ≥ P + 1 tick).
  3. Armado cuando un **cierre** queda ≥ **1 A** debajo del máximo del acercamiento.
  - El candidato muere si se toma el nivel, a las **60 velas** del armado o al fin de la sesión. Cada disparador dispara a lo sumo
    una vez por candidato.
- **Disparadores (perilla `disparador`)**, en espacio techo, operando hacia el nivel:

  | Disparador | Regla |
  |---|---|
  | `ALEJA` | En la vela del armado. |
  | `REACERCA_33` / `_50` | Cierre a 1/3 o 1/2 del camino desde el extremo del alejamiento 2 hasta el nivel. |
  | `EMA_TOQUE` | El rango de la vela contiene la EMA. |
  | `EMA_DOBLE_CRUCE` | Cierre 0,25 A del lado contrario de la EMA y después 0,25 A del lado a favor. |
  | `CRUCE_EMAS` | Cruce nuevo de la rápida sobre la lenta a favor. |
  | `ESPEJO_75` / `_100` | Espejo laxo, sin exigir imbalance para no filtrar todo. Impulso contrario = del máximo del acercamiento al extremo del alejamiento 2. Vuelta ≥ 75 % / 100 % de su tamaño en ≤ max(2 × su duración, 2) velas. |
  | `POC` | POC de las 60 M1 previas al armado (perfil del contexto). Cierre 0,25 A en contra y después 0,25 A a favor. |

- **Tendencia (perillas `def_tend` × `tendencia`):** cada disparo se repite por cada definición.

  | Definición | Estado de tendencia | EMA de los disparadores | Par de `CRUCE_EMAS` |
  |---|---|---|---|
  | `E20` | cierre del lado de la EMA 20 con su pendiente de 5 velas | 20 | 9/20 |
  | `E50` | ídem con la EMA 50 | 50 | 20/50 |
  | `X9_21` | EMA 9 contra EMA 21 | 21 | 9/21 |
  | `X20_50` | EMA 20 contra EMA 50 | 50 | 20/50 |

  - Estados: 0 a favor de la operación, 1 en contra, 2 neutra.
  - `eq_any` agrega «cualquiera»: es la variante **sin filtro**. La «tendencial» es `tendencia = 0`.
  - **Aviso de multiplicidad:** con `tendencia = cualquiera`, las 4 definiciones dan el mismo conjunto de operaciones para los
    disparadores sin EMA (celdas duplicadas). Queda contado en bruto: es conservador.
- **Variables medidas** (en A, cortes = mediana del E0 de cada fuente, modo ≥/≤):
  - `alej1`;
  - `cerca` (distancia del máximo del acercamiento al nivel);
  - `alej2` (máximo del acercamiento menos el extremo del alejamiento 2, en la decisión).
- **Deduplicación:** si varios niveles disparan lo mismo en la misma decisión (temporalidad, pico, definición, lado), queda el de
  mayor `alej1`.
- **Ejecución:** a mercado en el **primer tick después de k** (límite 2).

  | Pieza | Valores |
  |---|---|
  | Stop | `S_ESTR` (1 tick más allá del extremo del alejamiento 2), `S_1A`, `S_2A` |
  | Riesgo | Nunca menor a **0,5 A**: si es menor, el stop se ensancha. El R queda acotado. |
  | Objetivo | Más allá del nivel: `T_2TK` (P + 2 ticks), `T_05` (P + 0,5 A), `T_1`, `T_2` |

  12 ejecuciones. Sin BE. Nada cruza la sesión (simulador `areas_expansion.simular_cierre`, ambigüedad M1 resuelta con ticks).

## 7. Perillas, celdas y potencia

`tf` 5 × `pico` 3 × `alej1` 2 × `cerca` 2 × `alej2` 2 × `def_tend` 4 × `tendencia` 4 × `disparador` 9 × ejecución 12 =
**207.360 celdas por canal** (`grilla_generica.n_celdas`).

En datos sintéticos (60 días de ruido, para dimensionar), sobre 149.527 filas con las 4 definiciones:
- unas 620 filas por día;
- el 76 % en 1 min;
- 15 a 34 mil por disparador.

La etapa E0 del embudo da los conteos reales antes del DESC. Si más del 90 % de las celdas no llega a 30 operaciones (`EVALUABLES`),
el agente que lanza **no** agrega perillas: informa y propone podar en un pre-registro nuevo.

## 8. Datos, períodos, costos y estadístico

| Pieza | Valor |
|---|---|
| Sensor = ejecución | NQ y ES (futuros del release) |
| DESC | 2025-08-05 → 2026-03-31 |
| OOS / réplica | 2026-04-01 → 2026-09-30 (HOLDOUT-A3/A4) |
| Holdout | desde 2026-10-01, N fijo 150, sólo por protocolo |
| Estadístico | **R** |
| Costos | `edgelab/costos.py`; fricción canónica NQ 4,6 pts, ES 2,7 pts por viaje |
| Relevancia | mediana del objetivo ≥ 3 × fricción (`RATIO_MOV_FRICCION`) |

Por la regla de relevancia, es esperable que muchas celdas de 1 min no la cumplan. Es correcto: no se promueven.

## 9. Régimen

La tendencia es la perilla de régimen, declarada antes de correr. No hay régimen de calendario: `regimen.actual_desde = 20250805`
(todo el DESC).

## 10. Para el agente que lo lanza

1. `python tools/estado.py`, árbol limpio y al día.
2. `python -m pytest tests/agente/test_picos_defendidos.py -q` y `python -m edgelab.research.preflight edgelab.research.agente.picos_defendidos`,
   los dos en verde. El preflight tarda ~6 min.
3. En la campaña: `"activa": true` y una línea en `decisiones` con «se lanza» y la fecha. La conduce el `conductor` declarado. **2026-11-19: lanzada con conductor `local`** (el Debian está en PAUSE); estado en `docs/research/picos_defendidos_20261119/embudo/`.
4. El embudo registra las pruebas en el contador global antes del DESC.
   - No mirar una corrida lanzada con código que después se corrigió.
   - La regla de selección y las compuertas son las del embudo; no se cambian.
5. Al cerrar:
   - MEDIDO/NO MEDIDO en el mismo commit que el resultado;
   - la línea en `MEDIDO` de `gramatica.py`;
   - el MDE de todo nulo.

## 11. No medido (escrito antes de correr)

- **Paridad con NT8:** no hay indicador NT8 todavía. Paso obligatorio antes de operar en vivo.
- **Espejo estricto con imbalance (eficiencia mínima):** se eligió el laxo, como pidió Nico.
- **Nota de Nico «en x punto volumen ema»:** se interpretó como toque o cruce de EMA. La entrada condicionada a volumen no se mide.
- **Fuera de alcance:**
  - velas de ticks;
  - otros activos y CFD;
  - BE, trailing y salida por tiempo;
  - confluencia con zonas de otros indicadores;
  - la versión de estado continuo.
- **Historia M1 2006–2025** del dataset `edgelab-nt8-m1-futuros`: no se usa. El embudo lee ticks del release. Ampliar el DESC con esa
  historia es una decisión aparte (fuente nueva y partición nueva).
