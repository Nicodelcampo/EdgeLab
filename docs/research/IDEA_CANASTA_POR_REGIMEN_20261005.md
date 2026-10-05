# IDEA — Canasta de estrategias por régimen (2026-10-05)

Estado: **IDEA REGISTRADA, NO EJECUTADA.** Es búsqueda sobre retornos: requiere manifiesto + OK de Nico (regla STOP)
antes de correr nada. Origen: propuesta de Nico en sesión del 2026-10-04/05.

## 1. La idea (en palabras de Nico, resumida)
1. Una canasta de estrategias que fue rentable en una ventana reciente (ej. 2 meses) y que en una confirmación corta
   (ej. 4 días en demo) se comporta igual se pondera por riesgo y se opera mientras dure el régimen.
2. Versión testeable: aplicar **la misma regla en el pasado** (ej. hace un año funcionó 2 meses, los 4 días siguientes
   confirmó) y medir qué pasó después con la canasta seleccionada → promover, ajustar o descartar **la regla**.
3. Extensión (Nico, 2026-10-05): **un régimen puede ser diario.** No sólo "las últimas 8 semanas", sino "qué tipo de
   día es hoy" (tendencia, rango, evento) y qué estrategias rinden en ese tipo de día.

## 2. Reformulación: el edge no es la estrategia, es la regla de asignación
Hipótesis H-REG-1 (persistencia): el rendimiento neto de una estrategia en la ventana W predice su rendimiento en la
ventana siguiente H, por encima de lo que da elegir al azar del mismo universo.
Hipótesis H-REG-2 (régimen diario condicional): existe un estado S del día, **observable antes de operar** (o en los
primeros minutos), tal que el rendimiento de las estrategias condicionado a S difiere del incondicional, y una
asignación que use S supera a la asignación fija.

**Justificación económica.** Los mercados alternan entornos (tendencia/reversión, volatilidad alta/baja, flujo
informado vs. ruido); una estrategia explota una ineficiencia que existe sólo en algunos entornos. Si los entornos
persisten (semanas) o son reconocibles temprano (un día), asignar capital según el entorno captura el edge cuando
existe y lo evita cuando no.

**Cómo podría refutarse.**
- H-REG-1: correlación de rangos ≤ 0 entre rendimiento en W y en H (o canasta top ≤ canasta aleatoria, neto, en
  walk-forward). Ojo con el sesgo esperable en universos salidos de búsqueda: las mejores recientes suelen ser las más
  sobreajustadas → reversión, no persistencia.
- H-REG-2: el estado S no se puede predecir con información ex-ante mejor que la frecuencia base, o el rendimiento
  condicional por estado no difiere del incondicional fuera de muestra, o la diferencia no cubre costos.

## 3. Qué dice la práctica y la evidencia (investigación 2026-10-05)
- **Momentum de factores / estrategias: existe, pero concentrado.** AQR (Gupta y Kelly, *Factor Momentum Everywhere*):
  65 factores, los que rindieron recientemente siguen rindiendo; la cartera de *timing* sobre todos tiene Sharpe ~0,84.
  Reexamen (Fan et al. 2021): el efecto lo explican pocas estrategias (6 de 20); el resto casi no persiste. Implicancia:
  la persistencia es real en estrategias **económicamente fundadas y simples**, no garantizada en cualquier canasta.
- **Asignación a CTAs por rendimiento reciente: poca evidencia.** Amundi: comprar el momentum de los CTAs o tomar
  ganancia tras rachas casi no agrega valor de forma sostenida; los allocators que sí lo hacen definen el régimen con el
  **entorno de mercado** (calidad de tendencia, correlación entre tendencias), no con la curva de P&L.
- **Persistencia en hedge funds: corta y asimétrica.** Agarwal y Naik (JFQA 2000): máxima a horizonte trimestral,
  casi nula anual, y se explica más porque **los perdedores siguen perdiendo** que porque los ganadores sigan ganando.
  Implicancia práctica: la regla sirve más para **apagar** lo que dejó de funcionar que para elegir ganadores.
- **Filtro sobre la curva de capital (equity curve trading):** práctica común (operar una estrategia sólo si su
  equity está sobre su media). Reduce drawdowns, cuesta rendimiento por el retraso de reentrada, y sólo ayuda si los
  resultados de la estrategia son rachosos (autocorrelacionados). Es un caso particular de H-REG-1.
- **Degradación fuera de muestra:** las estrategias seleccionadas por buen rendimiento reciente suelen degradarse
  (sobreajuste + cambio de mercado). Lo que se elige con el período de evaluación nunca puede ser también la prueba.

Cómo se aplica de verdad (síntesis): (a) universo chico de estrategias con lógica económica distinta y baja
correlación; (b) régimen definido por **variables de mercado observables ex-ante** (volatilidad, tendencia,
correlación, calendario/eventos), no sólo por P&L; (c) ponderación por riesgo (inversa a la volatilidad, tope por
estrategia, riesgo total fijo), cambios graduales y no todo-o-nada; (d) reglas de **salida** del régimen declaradas de
antemano (lo que más plata cuesta es salir tarde); (e) la confirmación corta en demo valida **ejecución**, no edge.

## 4. Régimen diario (extensión de Nico)
Espacio de estados candidatos (enumerar antes de congelar cualquiera, regla de población):
- **Pre-apertura (ex-ante puro):** rango y dirección overnight, gap vs. cierre previo, volatilidad realizada previa,
  calendario (datos macro, vencimientos, FOMC), régimen de volatilidad de varios días.
- **Apertura temprana (primeros N minutos, decisión después de N):** rango inicial vs. su media, impulso de apertura,
  volumen relativo, ruptura o no del rango overnight.
- **Etiqueta ex-post del día (sólo para entrenar/evaluar, nunca como entrada):** día de tendencia, rango, reversión,
  evento.
Pregunta 1 (información): ¿los estados ex-ante predicen la etiqueta ex-post mejor que la frecuencia base? Si no, el
régimen diario no es operable. Pregunta 2 (P&L): ¿el rendimiento de cada estrategia condicionado al estado predicho
difiere, neto de costos? Sigue la cadena del proyecto: información → P&L bruto → neto.
Trampa principal: usar información del día completo para definir el régimen del mismo día (mirar adelante).

## 4b. Variante intradía a nivel trade (Nico, 2026-10-05) — H-REG-3
Estrategias generadas que hacen ~10 trades/día. Si ayer fue rentable y hoy los primeros 7 trades también, ¿la canasta
de esas estrategias es rentable en los trades restantes? Es persistencia **dentro del día** del P&L por trade.
- Test directo: P(trades k+1…n rentables | trades 1…k rentables, y día previo rentable) vs. la tasa incondicional,
  por estrategia y para la canasta. Equivale a medir autocorrelación de resultados de trades (rachas).
- Se puede probar entero en el pasado, sin tocar el holdout: el condicionante usa sólo trades ya cerrados.
- Trampas: (a) las estrategias de la canasta comparten el mismo movimiento de mercado ese día → los trades no son
  independientes; la unidad de inferencia es la **sesión**, no el trade (N efectivo = días, no trades); (b) "ganó los
  primeros 7" puede ser sólo "el mercado fue en tendencia en la mañana": comparar contra un condicionante de mercado
  puro (ej. retorno/rango de la mañana) para ver si la curva de P&L agrega algo; (c) las estrategias generadas
  arrastran sesgo de selección: el universo y su fecha de generación tienen que ser anteriores al tramo evaluado;
  (d) costos por trade, que en 10 trades/día pesan mucho.
- Refutación: tasa condicional ≈ incondicional (IC por sesión cruza la diferencia cero), o la ventaja desaparece al
  controlar por el condicionante de mercado puro, o no cubre costos.

## 5. Diseño del test (cuando haya OK)
- Universo de estrategias fijado antes de mirar resultados (point-in-time; ninguna agregada después).
- Walk-forward sobre 2023→2026-09 (holdout desde 2026-10-01 intacto): en cada fecha, ventana W hacia atrás,
  confirmación C, canasta top-k ponderada por riesgo, mantenida H, salida por regla.
- Medidas: correlación de rangos W→H; canasta top vs. aleatoria del mismo universo vs. canasta fija; asimetría
  (¿sirve más para apagar perdedoras?); para H-REG-2, tasa de acierto del estado y rendimiento condicional.
- Nulo: mezclar el orden temporal de los bloques de rendimiento por estrategia (rompe la persistencia, conserva la
  distribución). Grilla chica y declarada (ej. W ∈ {1,2,3} meses, C ∈ {0,4,10} días, H ∈ {5,20} días, k fijo),
  registrada en `TRIAL_REGISTRY_GLOBAL.jsonl`; corrección por multiplicidad sobre la grilla.
- Costos por instrumento (no transportar), MDE publicado, canal direccional y no direccional.
- Expectativa previa: baja para universos salidos de búsqueda grande (reversión esperable), moderada para estrategias
  simples con lógica económica. El resultado negativo también se registra.

## Fuentes
- AQR / Gupta y Kelly, Factor Momentum Everywhere — https://alphaarchitect.com/is-factor-momentum-really-everywhere/
- Institutional Investor, Factor Momentum Is Real — https://institutionalinvestor.com/article/b1cmczbjjl4qgs/Factor-Momentum-Is-Real-Researchers-Argue
- Quantpedia, A Deeper Look into Factor Momentum (Fan et al.) — https://quantpedia.com/a-deeper-look-into-factor-momentum/
- Amundi, Core allocation CTAs: might be wise going tactical — https://research-center.amundi.com/article/core-allocation-ctas-might-be-wise-going-tactical
- Agarwal y Naik (2000), JFQA — https://ideas.repec.org/a/cup/jfinqa/v35y2000i03p327-342_00.html
- Equity-curve-based throttling — https://www.luxalgo.com/library/concept/equity-curve-based-throttling/
- Harbourfront Quant, When trading systems break down — https://harbourfrontquant.substack.com/p/when-trading-systems-break-down-causes
