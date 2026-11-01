# MODELO-ASIA — pre-registro (2026-11-01)

Estado: VIGENTE (pre-registrado antes de correr). Pedido de Nico: «¿probaste esta estrategia (Modelo Asia NQ 100–300 pts con EMA) y
variantes estilo EdgeLab?». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo: EF2 → embudo automático. Módulo:
`edgelab/research/modelo_asia.py`. Tests: `tests/research/test_modelo_asia.py`.

## Fuente y regla literal
"Modelo Asia" de @alphatraders_latam (post De2e_Mns9UG). La versión recibida es la que pegó Nico en la sesión. El creador declara 14
TP seguidos en vivo; eso no es evidencia, es selección.

| Elemento | Regla literal |
|---|---|
| Instrumento | NQ, 5 minutos |
| Rango | Alto y bajo de 18:00–20:00 NY (velas que cierran en (18:00, 20:00]) |
| Filtro | Se opera sólo si 100 ≤ alto − bajo ≤ 300 puntos |
| Sesgo | Al cierre de la vela de 15 min de las 20:15: precio sobre la EMA20 de 5 min = sólo compras; debajo = sólo ventas |
| Entrada | Ruptura del borde del lado del sesgo |
| Stop | Borde opuesto del rango |
| Objetivo | Abierto ("dejan correr", ejemplos de +500 pts); en el backtest, hasta la sesión de NY |

**Lo que el texto no fija y se decide acá, antes de mirar:**
- La ruptura es un **cierre** fuera del rango, de una vela de 1 min o de 5 min. Las dos son una perilla. La entrada es en el primer
  tick de la vela siguiente, nunca en el extremo.
- Las entradas valen hasta las 09:30 ET.
- "Hasta la sesión de NY" se toma como **16:00 ET** en la celda literal. Las 09:30 y las 12:00 son variantes.
- 300 incluye a 300: el corte es 300,25.

**Celda literal**: gatillo M1 · ancho [100, 300] · sesgo a favor · stop OPUESTO, objetivo ABIERTO, cierre a las 16:00. Se publica
aparte con costos, por período y por mes, además de entrar en la grilla.

## Grilla (240 celdas por canal)
| Perilla | Niveles |
|---|---|
| Gatillo | cierre M1 / cierre M5 |
| Ancho en puntos | < 100 / 100–300 / > 300 / cualquiera |
| Sesgo EMA20 M5 a las 20:15 | contra / a favor / cualquiera |
| Ejecución | 10 combinaciones (abajo) |

Ejecuciones: stop {OPUESTO, MID} × {1R o 2R (con cierre a las 16:00), ABIERTO con cierre a las 09:30, 12:00 o 16:00}. El +500 del
post es un ejemplo, no una regla. Casi nunca se alcanza en una noche, así que como ejecución quedaba idéntica a ABIERTO-16:00: el
preflight la marcó como perilla muerta y se sacó antes de correr.

El nivel "cualquiera" de cada perilla es el control: si la celda literal no supera a "cualquier ancho" o a "cualquier sesgo", el filtro
no aporta.

## Espacio de eventos (regla de población)
La población es el **primer cierre fuera del rango 18–20 después de las 20:15, por lado y por gatillo**. Familias de entrada
consideradas y descartadas:
- **Creación del rango** (entrar a las 20:00): no es la regla.
- **Barrido con reingreso** y **pullback al borde**: ya medidos en ASIA_BOS_GAPS (gatillos 1 y 2).
- **Toque n-ésimo del borde**: la regla opera una ruptura por lado.
- **Estado continuo**, como "precio fuera del rango a la hora X": queda para después si la ruptura muestra algo.

Se elige la ruptura porque **es la regla literal** y porque la misma ruptura sin el filtro de ancho en puntos ni la EMA de las 20:15
ya existe en ASIA_BOS_GAPS (gatillo 0 BOS). Así, el aporte de cada filtro se mide contra su control.

## Justificación económica
Asia acumula órdenes (stops y entradas) en los bordes de un rango de 2 horas, y NY trae el volumen que las ejecuta. El filtro de 100–300
puntos busca un rango "institucional": ni el chop chico ni una expansión ya hecha. La EMA20 de 5 min alinea con el flujo de la
tarde-noche.

Riesgo conocido: NQ es más caro en 2025–26 que en 2023, así que el mismo ancho en puntos no es el mismo régimen. Por eso se corre
también en el CFD 2023–25 y se mantiene el nivel "cualquiera" como control.

## Cómo se refuta
- 0 nominadas por la criba maxT (α 0,05 por canal) en DESC.
- Y canasta de pistas en contra con potencia en la réplica.
- O media ≤ 0 en la réplica / holdout.
- La celda literal se informa siempre, con su IC y su MDE. Un nulo sin potencia NO la mata (`SIN_POTENCIA`).

## Datos, costos y multiplicidad
| Campaña | Datos | DESC | Réplica | Costos |
|---|---|---|---|---|
| `MODELO-ASIA-NQ` | Futuros NQ | 2025-08-05 → 2026-03-31 | 2026-04-01 → 2026-09-30 | Canónicos de NQ (`edgelab/costos.py`) |
| `MODELO-ASIA-CFD-NQ` | DK:USATECHIDXUSD | 2023-01-03 → 2024-06-28 | 2024-07-01 → 2025-07-31 | Canónicos del CFD |

- Holdout: desde la sesión del 2026-10-01 (HOLDOUT-A4), sin tocar.
- Linaje (`docs/research/LINAJES.jsonl`): hijas de `ASIA_BOS_GAPS_NQ` y `ASIA_BOS_GAPS_CFD_NQ` (misma caja 18–20, otra regla). Heredan
  su multiplicidad en bruto.
- Conteo en `TRIAL_REGISTRY_GLOBAL.jsonl` vía el embudo (preflight).

## Cambio de motor que habilita esta familia
`areas_expansion.simular_cierre_linea` cortaba toda operación a las 240 velas (4 h). Ahora acepta `tope_barras` y cada experimento
puede declarar `TOPE_BARRAS`; esta familia usa 1300. El valor por defecto sigue siendo 240, así que ninguna familia existente cambia
(`tests/research/test_salida_linea.py`). Sin esto, "dejar correr hasta NY" era imposible de medir: una entrada de las 21:00 salía
sola a la 01:00.

## Controles
`tests/research/test_modelo_asia.py`:
- preflight y tamaño;
- causalidad;
- la EMA20 M5 es la de pandas sobre los cierres de 5 min;
- paridad lote/escalar;
- una sesión armada a mano: la regla literal compra a las 21:00, sigue abierta más de 240 velas y sale a las 16:00;
- un rango de 60 puntos cae en el nivel "< 100".

## Preflight alineado a la sesión CME
El sintético del preflight armaba bloques de 23 h desde las 03:54 ET, y las tres horas de cierre (09:30, 12:00 y 16:00) quedaban
fuera de la sesión. Eso hacía idénticas las ejecuciones por hora: un artefacto de los datos de control, no de la grilla. El módulo
declara `PREFLIGHT_T0_S` (bloques desde las 18:00 ET) y `preflight.dinamico` lo usa sólo si el experimento lo declara. Ninguna
verificación se relaja, y el resto de los experimentos corre con el sintético de siempre.

## v2 (2026-11-01, antes de mirar resultados): tres lecturas de "puntos"
Nico preguntó si "100–300 puntos" podía referirse a otra unidad. Con el CFD del S&P en M1 (`/data/spot_new`, como escala), el
rango 18:00–20:00 ET de NQ tiene una mediana de ~25–55 puntos según el año y un p90 de ~45–125. Entonces 100–300 **puntos del índice**
pasa sólo en ~5–15 % de los días (más en 2025–26), y hay otras dos lecturas plausibles:
- **ticks de NQ** (0,25): 100–300 ticks = 25–75 puntos, la zona media de la distribución. Encaja con "+500 pts" (= 125 puntos) como
  objetivo de una noche;
- **points de MT5** con paso 0,1, típico del NAS100 en CFD: 10–30 puntos.
La variable `ancho_pts` pasa a 6 tramos más "cualquiera": <10 | 10–25 | 25–75 | 75–100 | 100–300 | >300. Son 2 × 7 × 3 × 10 = **420
celdas por canal**. La celda de cada lectura está en `modelo_asia.LECTURAS`; la de MT5 se aproxima con el tramo 10–25.

**Corridas v1 descartadas sin mirar** (regla de la guía de grilla masiva):
- `MODELO-ASIA-NQ` y `MODELO-ASIA-CFD-NQ`: frenadas en DESC/CORRIENDO, con estados en `embudo_v1_descartada/`.
- Los dos kernels de la regla literal v1: `literal_v1_descartada/`.
- Sus 480 + 480 pruebas ya están en el registro global y **siguen contando** para la familia.
Las campañas nuevas son `MODELO-ASIA-V2-NQ` y `MODELO-ASIA-V2-CFD-NQ`, con las mismas familias, linaje y ventanas.
