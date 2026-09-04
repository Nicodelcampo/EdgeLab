# Manifiesto de campaña — señales de racha de HFTImpulseZones_P

**Estado: PROPUESTA. No ejecutada. Requiere aprobación explícita de Nico** (STOP
del proyecto: ninguna búsqueda sobre P&L/retornos se corre sin manifiesto
aprobado).

Referente: `docs/NORTH_STAR.md`, sha256 del cuerpo
`d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

## Lo que se pidió

Barrer, después de cada señal, combinaciones de: nivel de retroceso para entrar,
SL, break-even, TP, filtro horario, y EMA de distintos períodos filtrando por
dirección.

## Por qué la grilla completa NO se puede correr

| eje | valores |
|---|---:|
| retroceso de entrada | 5 |
| SL | 5 |
| break-even (incl. sin BE) | 4 |
| TP | 5 |
| filtro horario | 6 |
| EMA (períodos + apagada) | 7 |
| **total de celdas** | **21.000** |

Efecto mínimo detectable, en desvíos estándar por trade (potencia 80 %, α 0,05,
Bonferroni):

| N por celda | 1 hipótesis | 21.000 hipótesis |
|---:|---:|---:|
| 566 | 0,118 | **0,234** |
| 1.200 | 0,081 | 0,160 |
| 5.900 | 0,036 | 0,072 |
| 20.000 | 0,020 | 0,039 |

Un sistema intradiario real de futuros rinde típicamente **0,02–0,10 desvíos por
trade después de costos**. Con 566 señales y 21.000 celdas el umbral de detección
es 0,234: **más de dos veces el techo de lo que existe**.

Y es peor de lo que muestra la tabla, porque **los filtros no sólo multiplican
hipótesis: reducen N**. Una ventana horaria de 2 h conserva ~25 % de las señales y
la EMA ~50 %: el N efectivo por celda es ~1/8 del total. Con la población entera
pre-holdout estimada (~5.900 señales) eso deja ~740 por celda → MDE ≈ 0,20.

**Conclusión: la grilla tal como está pedida no puede distinguir un edge real de
ruido. No es cuestión de correrla con más cuidado; es que no tiene potencia.**

## Tres hallazgos de la población que cambian el diseño

Medidos sobre `hftimpulse_NQ_20260903.csv` (NQ SEP26 5t, 5 sesiones):

1. **566 señales, 264 alcistas y 302 bajistas.** Balanceada — no hay sesgo
   direccional incorporado. Bien.
2. **Las señales están separadas: mediana 340 barras, ninguna a menos de 12.**
   No se pisan, así que se pueden tratar como eventos casi independientes. Bien.
3. **Las 566 tienen `burst_count == 3`.** Y esto es un problema: el pedido habla
   de *"los clusters de MÁS acumulación"*, pero la señal se emite en el momento
   exacto en que la racha llega a 3 y nunca después, así que **la intensidad no
   varía**. El eje "más acumulación" hoy no existe en el dato.
   - Lo que sí varía es `burst_displacement_ticks`: mediana 69, p10 54, p90 100.
     Ese es el proxy de intensidad utilizable hoy.
   - Si la intensidad tiene que ser el conteo de ráfagas, hay que cambiar el
     indicador para que registre hasta dónde llegó la racha. Es un cambio chico,
     pero es una decisión, no un detalle.

## Orden propuesto, y por qué ese orden

El principio: **todo lo que se pueda decidir sin mirar retornos, se decide sin
mirar retornos**. Eso no gasta presupuesto de multiplicidad. Cada eje que entra
al barrido de P&L multiplica el umbral de detección para todos los demás.

### Fase 0 — población y nulo (target-free, no gasta presupuesto)

- Correr el indicador sobre **todo el pre-holdout de NQ 06-26**, no sobre SEP26.
  La corrida actual es de 3 días y **cae dentro del holdout**; sirvió para validar
  paridad (uso permitido) pero no para definir población.
- Publicar el N real y el **MDE antes de gastar nada**.
- Nulo de tasa: ¿el ritmo de señales se distingue de un nulo con la misma tasa y
  el mismo agrupamiento temporal? Si no, la racha está contando volatilidad y
  todo lo demás sobra.

**Condición de corte**: si el N pre-holdout no alcanza para un MDE < 0,10 con el
espacio ya podado, la campaña no se corre. Se dice y se para.

### Fase 1 — alcanzabilidad geométrica (target-free, no gasta presupuesto)

Después de cada señal, medir **pura geometría de primer paso**: con qué frecuencia
el precio retrocede X ticks antes de avanzar Y. No es P&L: es la distribución de
qué niveles son siquiera alcanzables.

Esto **poda dos ejes enteros sin tocar retornos**:
- niveles de retroceso que casi nunca se alcanzan → no hay entradas que medir;
- niveles de retroceso que se alcanzan casi siempre → no filtran nada;
- SL y TP fuera del rango de excursión típico → decididos de antemano.

Es la fase con mejor relación entre lo que informa y lo que cuesta.

### Fase 2 — primer contacto con outcomes, mínimo posible

**Una sola pregunta pre-registrada**: entrada en la apertura de la barra
siguiente (sin retroceso), grilla chica de SL/TP sobrevivientes de la Fase 1, sin
BE, sin filtro horario, sin EMA. Neta de costos.

Si acá no hay nada, el resto es decoración: los filtros no crean edge, sólo
seleccionan sobre uno existente.

### Fase 3 — un eje por vez, cada uno con su presupuesto

Orden sugerido, de mayor a menor prior y de menor a mayor riesgo de snooping:

1. **Retroceso de entrada** — cambia *qué señales se llenan*, o sea cambia la
   población. Va primero porque interactúa con todo lo demás.
2. **Break-even** — modifica la distribución de salidas de forma acotada.
3. **EMA direccional** — es un condicionante con mecanismo declarado
   (alineación con la tendencia). Se puede pre-registrar la dirección esperada.
4. **Filtro horario, último y con la corrección más fuerte.** Cortar el día en
   ventanas es el eje con más riesgo de encontrar algo espurio: hay muchas formas
   de partir seis horas y media, y siempre alguna "funciona". Además interactúa
   con el calendario de sesión, que en este proyecto ya dio problemas.

## Riesgos declarados

- **Ambigüedad SL/TP en la misma barra.** Con barras de 5 ticks, SL y TP pueden
  tocarse dentro de la misma barra y el orden real es desconocido. Hay que
  resolverlo con datos de tick o declarar una política conservadora — el proyecto
  ya tiene `diag/ejecucion/ambiguedad_stop.py`. Sin eso, los resultados son
  optimistas por construcción.
- **Costos.** La fricción de NQ se estima para NQ. No se transporta de 6E ni de
  GC. Con un desplazamiento acumulado mediano de 69 ticks (~17 puntos NQ), los
  costos no son un ajuste menor: son parte central del resultado.
- **Resolución de barra.** Todo lo medido es sobre 5 ticks/barra. `bar_spec` y los
  parámetros del indicador son ejes distintos y no se pueden confundir.
- **La población de validación es holdout.** Hay que rehacerla sobre 06-26 antes
  de definir nada.

## Datos que faltan

1. Corrida de `HFTImpulseZones_P` sobre **NQ 06-26** pre-holdout, con
   `EventLogPath`, misma configuración.
2. Estimación de costos propia de NQ (comisión + spread + slippage realista).
3. Decisión sobre la intensidad: `burst_displacement_ticks` como proxy, o cambiar
   el indicador para que la racha registre su tamaño final.

## Cómo podría refutarse la campaña entera

Si la Fase 0 muestra que la tasa de señales es indistinguible de un nulo con la
misma tasa y agrupamiento, la racha no informa nada sobre el estado del mercado y
ninguna combinación de entrada y salida puede rescatarla. Ese es el primer test, y
puede cerrar todo antes de gastar un solo grado de libertad.

## Aporte al referente

Convierte un pedido de 21.000 combinaciones —que con la muestra disponible no
puede distinguir edge de ruido— en una secuencia donde cada fase o poda el espacio
sin costo estadístico o responde una pregunta que la anterior dejó en pie. El
progreso no es haber corrido el barrido: es haber reducido la distancia hasta un
edge neto sin quemar la capacidad de detectarlo.
