# H-SWEEP-1 — Familia YM-PRERANGE: doble barrido del rango pre-apertura

> **Fecha de registro:** 2026-08-10
> **Estado:** protocolo escrito. Nada ejecutado.
> **Gate:** bloqueada por el incidente P0 de procedencia y por la ausencia de calendario de research y oráculos para YM.

**Familia registrada:** `YM-PRERANGE`. Rango de la ventana **08:12–09:12** sobre YM, y comportamiento del precio **después** de esa ventana.

Es una familia nueva. No es BigTrap2 y no es LUX-IMB. No es una zona derivada de un indicador: es una **ventana temporal fija**. No hereda resultados, poblaciones, costos, oráculos ni presupuesto de multiplicidad de ninguna familia previa.

## Afirmación del operador

> El precio toma un extremo del rango y luego toma el otro.

Observado en 6 días consecutivos sobre YM, con 5 casos a favor.

---

## 1. Resultado principal

**Con 5 de 6 solo se podría rechazar una tasa base por debajo de 41,8%, y la tasa base estimada del doble toque está entre 54% y 76%. El intervalo de confianza de la observación contiene por completo al baseline.**

Traducción: 5 de 6 no es sorprendente, es aproximadamente lo esperado. Eso no es un argumento para no medir. Es un argumento para no operar todavía.

### 1.1 Por qué medir igual es la decisión correcta

Hay dos preguntas distintas y solo una está cerrada:

- **¿Es evidencia?** No. Y ningún análisis adicional sobre estos seis días lo va a cambiar.
- **¿Justifica gastar presupuesto de medición?** Sí.

La segunda es una decisión de asignación de recursos, no una inferencia, y se sostiene por tres razones:

1. **El test decisivo es barato.** El emparejamiento cruzado de días no requiere infraestructura nueva y puede cerrar la hipótesis en una sola corrida.
2. **Los datos ya están.** YM tiene 23,2 millones de ticks ingeridos. La muestra necesaria, de 50 a 120 días, probablemente ya existe en disco.
3. **Hay un mecanismo documentado detrás.** El agrupamiento de stops apenas más allá de niveles visibles predice exactamente este comportamiento.

La regla no es esperar significancia antes de investigar. Es **no confundir una razón para mirar con una razón para operar**.

### 1.2 El día que falló es la observación más informativa

De los seis, uno no cumplió el patrón. Esa única observación vale más que las cinco que sí, porque es el primer candidato a moderador. Si el día que falló fue la observación 6 —la del rango de 188 puntos que no es un rango sino una tendencia— la hipótesis se afina sola: el doble barrido ocurriría en ventanas de consolidación y no en ventanas de tendencia. Eso convierte una corazonada en una predicción con signo, registrable antes de medir.

---

## 2. Datos observados

| Obs. | Rango (puntos) | Punto medio | Nota |
| --- | --- | --- | --- |
| 1 | 104 | 54.073 | — |
| 2 | 153 | 54.122 | 07 ago 2026 visible en el eje |
| 3 | 79 | 54.600 | Rango limpio, lateral |
| 4 | 94 | 54.500 | Rango limpio, lateral |
| 5 | 121 | 53.974 | — |
| 6 | 188 | 53.247 | **No es un rango: es una tendencia alcista continua** |

Media 123,2 puntos. Mediana 112,5. El rango más grande es 2,4 veces el más chico. En YM, 1 punto es 1 tick y vale 5 dólares, así que la muestra va de 395 a 940 dólares de amplitud por contrato.

Las capturas originales están adjuntas en la página de Notion correspondiente.

---

## 3. Por qué "toma ambos extremos" es casi gratis

Un movimiento browniano sin deriva que arranca dentro de un intervalo **toca ambos bordes con probabilidad 1** si se lo deja correr. La pregunta solo tiene contenido con un horizonte finito declarado.

### 3.1 Estimación de la volatilidad desde los propios datos

El rango esperado de un movimiento browniano en `[0,T]` es `E[rango] = sigma * sqrt(8T/pi) ≈ 1,596 * sigma * sqrt(T)`.

Con rango medio observado de 123,2 puntos y `T = 60` minutos:

```
sigma_hat = 123,2 / (1,596 * sqrt(60)) ≈ 9,97 puntos por minuto
```

### 3.2 Probabilidad del segundo toque

Una vez tocado el primer extremo, el precio está a distancia `R` del otro. Por el principio de reflexión:

```
P_2 = 2 * Phi(-R / (sigma * sqrt(t)))
```

De 09:12 al cierre de la sesión regular hay unos 408 minutos. Con `sigma = 10` y `R = 123`:

```
P_2 = 2 * Phi(-0,610) ≈ 0,54
```

**Esta cifra subestima el baseline.** La volatilidad se estimó en la ventana previa a la apertura, que es la parte más tranquila del día. Si la volatilidad efectiva post-apertura duplica a la del pre-mercado, `P_2 = 2 * Phi(-0,305) ≈ 0,76`.

> **Baseline del doble toque: entre 54% y 76%.** No es 50%. Cualquier test que use 50% como nulo está mal planteado y va a "encontrar" el patrón aunque no exista.

---

## 4. Poder estadístico con el registro real de 5 de 6

La probabilidad exacta de observar 5 aciertos o más en 6 intentos bajo una tasa base `p0` es `P(X >= 5) = 6*p0^5 - 5*p0^6`.

| Tasa base supuesta | p-valor con 5 de 6 | ¿Rechaza a 5%? |
| --- | --- | --- |
| 0,50 — una moneda | 0,109 | No |
| 0,54 — extremo bajo del baseline | 0,152 | No |
| 0,70 | 0,420 | No |
| 0,76 — extremo alto del baseline | 0,558 | No |

Resolviendo `6*p0^5 - 5*p0^6 = 0,05` se obtiene `p0_max ≈ 0,418`. **Con 5 de 6 solo se podría rechazar un baseline por debajo de 41,8%**, y el baseline estimado es 54% a 76%. No se rechaza ni siquiera una moneda.

### 4.1 Intervalo de confianza

El intervalo de Wilson al 95% para 5 de 6 es aproximadamente `[0,437 ; 0,970]`. Ese intervalo **contiene por completo** el rango de baseline estimado. Los datos son compatibles con que no exista ningún efecto y también con que exista uno grande. Eso es precisamente lo que significa no tener poder.

### 4.2 MDE declarado

Usando `n ≈ [z_alfa*sqrt(p0*q0) + z_beta*sqrt(p1*q1)]^2 / (p1-p0)^2` con alfa 0,05 a una cola y 80% de poder:

- Exceso de 15 puntos porcentuales sobre un baseline de 0,70: **unos 50 días.**
- Exceso de 10 puntos porcentuales: **unos 119 días.**

---

## 5. El nulo correcto para la versión operable

La versión negociable no es "se tocan los dos extremos", es: **después del primer barrido, operar en contra**. Eso es una carrera entre objetivo y stop, y tiene nulo exacto.

Después de tocar el extremo superior `U`, con objetivo en `L = U - R` y stop en `U + s`, la ruina del jugador da `p0 = s / (R + s)`.

### 5.1 La consecuencia incómoda

```
EV = [s/(R+s)] * R - [R/(R+s)] * s = 0
```

**Exactamente cero.** Ninguna combinación de objetivo y stop genera valor sobre un paseo sin deriva. La pregunta entera se reduce a si la tasa observada supera `s/(R+s)`.

### 5.2 El umbral de costos

Con costo de ida y vuelta `c`, la tasa necesaria es `(s+c)/(R+s)` y el exceso requerido es `delta_p = c/(R+s)`.

Con `R = 123`, `s = 30` y `c = 3` puntos: nulo 19,6%, necesario 21,6%, exceso requerido **1,96 puntos porcentuales**.

### 5.3 Cuántos días hacen falta

| Escenario | Tasa real | Días para 80% de poder |
| --- | --- | --- |
| Edge marginal, apenas paga costos | 0,216 | ≈ 2.500 |
| Edge grande | 0,300 | ≈ 100 |

> Un edge que apenas cubre costos requiere unos diez años de datos para verificarse. Solo un efecto grande es verificable en un plazo razonable. Si al medirlo la tasa queda cerca de `s/(R+s)`, la respuesta correcta es cerrar, no aumentar la muestra.

---

## 6. Confusores identificados

### C1 — La apertura del efectivo a las 09:30

La ventana termina 18 minutos antes de la apertura de la sesión regular. La literatura sobre rangos de apertura documenta que volumen y fluctuación de retornos alcanzan su pico exactamente en la apertura y el cierre del mercado subyacente. Es probable que ambos extremos se tomen por la explosión de volatilidad de la apertura y no por los niveles. Eso sería un efecto de régimen de volatilidad, no de nivel.

### C2 — Los datos macro de las 08:30

La ventana **contiene** el horario estándar de publicación de datos en Estados Unidos. El ancho del rango es entonces endógeno al calendario económico: probablemente por eso hay un rango de 79 y otro de 188 en la misma muestra. Obliga a estratificar por calendario.

### C3 — Zona horaria y etiqueta del indicador

- En agosto rige horario de verano. "08:12 EST" y "08:12 EDT" difieren en una hora.
- El recuadro del gráfico dice "Tokyo". O el indicador conserva el nombre de un preajuste reconfigurado, o la ventana real no es la declarada. Hay que resolverlo antes de definir la población.

### C4 — La observación 6 no es un rango

La sexta captura muestra una tendencia alcista sostenida dentro de la ventana. Tomar ambos extremos de un tramo de tendencia significa algo distinto que tomarlos de un lateral. La población mezcla dos estructuras incompatibles y hay que estratificar por eficiencia interna del recorrido.

### C5 — Seis días consecutivos

Es la muestra con más autocorrelación posible: un solo régimen de volatilidad, una sola semana de calendario macro. El tamaño efectivo es menor que 6.

### C6 — Selección posterior de la ventana

08:12 es un horario inusual. Si salió de mirar el gráfico, la multiplicidad implícita es enorme. Con 50 combinaciones exploradas informalmente, la probabilidad de al menos un falso positivo es `1 - 0,95^50 ≈ 0,92`.

---

## 7. Controles

### Control decisivo — emparejamiento cruzado de días

Aplicar el rango del día `d` al recorrido posterior del día `d' != d`. Preserva ambas distribuciones marginales y destruye únicamente el vínculo causal.

> Si la tasa de doble toque **no cambia** al cruzar días, los niveles no contienen información: lo único que importa es el ancho del rango y la volatilidad posterior. Ese solo test puede cerrar la hipótesis entera.

### Controles adicionales

- **Ventanas placebo:** misma duración a las 06:12, 07:12, 10:12, 11:12.
- **Bootstrap de bloques:** preservando la estacionalidad intradiaria de la volatilidad.
- **Barrido de ventana:** inicios de 07:30 a 09:00 y duraciones de 30 a 90 minutos. Un efecto real es una región suave, no un pico aislado en 08:12.

---

## 8. Descomposición en hipótesis separadas

1. **H-SWEEP-1a — doble toque.** ¿La tasa de tocar ambos extremos dentro del horizonte `H` supera al nulo emparejado?
2. **H-SWEEP-1b — secuencia.** Dado el primer toque, ¿el segundo llega antes que una extensión adicional?
3. **H-SWEEP-1c — asimetría temporal.** ¿El primer toque se concentra en un horario, por ejemplo la apertura?
4. **H-SWEEP-1d — falso quiebre.** ¿El primer toque es rechazo más seguido que continuación?

Solo 1b y 1d son directamente operables. 1a y 1c son descriptivas.

**Tensión con la literatura:** los estudios de ruptura del rango de apertura reportan rentabilidad de la **continuación**, mientras que este patrón implica que el primer quiebre es falso. Son afirmaciones opuestas y no pueden ser ambas ciertas en la misma población. Esa contradicción define un test discriminante.

---

## 9. Mecanismo candidato

Osler mostró, con datos de órdenes reales, que las órdenes de toma de ganancia se agrupan en números redondos mientras que los stops se agrupan apenas más allá de ellos, lo que produce reversiones en niveles predecibles y aceleraciones al cruzarlos.

Si los stops se acumulan justo fuera de los extremos del rango pre-apertura, el barrido de un extremo libera liquidez y el precio puede viajar hacia el otro. Es un mecanismo plausible y falsable: predice que el efecto debe ser más fuerte cuando los extremos coinciden con números redondos, y ese es un moderador pre-registrable.

---

## 10. Regla de toque — la definición ausente

Hasta acá, "tomar el extremo" se adjudicó mirando el gráfico. Esa es la fuente de falsos positivos más barata que existe, porque la regla se mueve sin que nadie lo note. Antes de medir hay que fijar por escrito cinco cosas:

1. **Nivel exacto.** ¿El extremo es el máximo y mínimo de mecha dentro de la ventana, o de cuerpo? Hay que exportar cuál dibuja el indicador.
2. **Criterio de contacto.** ¿Alcanza con negociar al precio exacto, o hace falta superarlo por al menos un tick? Con tick de 1 punto en YM la diferencia es material y no es simétrica entre los dos lados.
3. **Fuente del dato.** ¿La mecha del gráfico o el tick real? El máximo de una vela de un minuto puede provenir de una sola operación de un lote, que no es liquidez tomable.
4. **Horizonte `H`.** Hasta el cierre de la sesión regular, hasta el mediodía, hasta la apertura del día siguiente. Sin `H` declarado la afirmación es trivialmente verdadera.
5. **Orden estricto.** ¿El segundo toque debe ocurrir después del primero, o cuenta si una misma vela barre ambos extremos? Una vela de expansión que atraviesa el rango entero no es el patrón que se quiere explotar, es lo contrario.

> Cada una de estas cinco elecciones puede mover el conteo de 6 sobre 6 a 3 sobre 6 sobre los mismos seis días. Ninguna se decide mirando las capturas: se declaran antes, se aplican por código, y el conteo resultante es el que sea.

**Corolario:** el conteo observado de 5 sobre 6 no es un dato de entrada del estudio. Es una motivación. El primer entregable de la medición será recontar esos mismos seis días con la regla escrita, y es esperable que el número cambie.

---

## 11. Ledger de sesión

Por día: fecha, contrato, `bar_spec`, huso horario declarado y verificado, límites `L` y `U`, ancho, punto medio, precio al cierre de la ventana, eficiencia del recorrido interno, volumen de la ventana, indicador de publicación macro y su hora, primer extremo tocado con marca temporal, segundo extremo tocado o no con marca temporal, excursión máxima más allá de cada extremo, distancia de los extremos al número redondo más cercano, y volatilidad realizada antes y después de la apertura.

---

## 12. Presupuesto de multiplicidad

- **Primario: 1.** H-SWEEP-1b contra el nulo de ruina del jugador, en el horizonte y con el stop declarados de antemano.
- **Secundarios: 6** bajo Romano–Wolf: ancho normalizado, día con publicación macro, eficiencia interna, proximidad a número redondo, dirección del primer barrido, régimen de volatilidad.
- Barridos de ventana y horizonte: exploratorios, publicados como superficie completa, sin capacidad de adjudicar.

---

## 13. Criterios de muerte

- El emparejamiento cruzado de días reproduce la tasa observada: los niveles no informan.
- La tasa de doble toque no supera `2*Phi(-R/(sigma*sqrt(t)))` con volatilidad emparejada.
- La tasa de la carrera no supera `s/(R+s)` más el umbral de costos.
- El efecto existe solo en 08:12 y desaparece en ventanas vecinas.
- El efecto desaparece al excluir los días con publicación macro.
- El efecto se explica enteramente por la volatilidad de la apertura de las 09:30.

---

## 14. Qué hace falta antes de medir

- [ ] Confirmar huso horario: EST o EDT, y en qué referencia está el gráfico
- [ ] Resolver la etiqueta "Tokyo" del recuadro y exportar la configuración real del indicador
- [ ] Recuperar las seis fechas exactas y su orden
- [ ] Declarar el horizonte `H` antes de mirar los datos
- [ ] Declarar el stop `s` antes de mirar los datos
- [ ] Medir el costo real de ida y vuelta en YM en ese horario, con su liquidez propia
- [ ] Construir el calendario de sesiones de YM, que todavía no existe

---

## 15. Gate de ejecución

YM tiene 23,2 millones de ticks ingeridos y `InstrumentSpec` cargado, pero **no tiene calendario de research ni oráculos propios**. Además sigue vigente el gate del incidente P0 de procedencia. Nada de esto se ejecuta hasta cerrar ambos.

Orden: cerrar P0, resolver huso horario y etiqueta, construir el calendario de YM, contar los días disponibles, y recién entonces correr el emparejamiento cruzado, que es el test más barato y el que más rápido puede matar la hipótesis.

---

## 16. Referencias externas

- Osler, C. (2003). Currency orders and exchange rate dynamics: an explanation for the predictive success of technical analysis. *Journal of Finance*. <https://onlinelibrary.wiley.com/doi/full/10.1111/1540-6261.00588>
- Osler, C. Stop-loss orders and price cascades in currency markets. Federal Reserve Bank of New York Staff Report 150. <https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf>
- Holmberg, Lönnbark y Lundström. Assessing the profitability of intraday opening range breakout strategies. <https://www.sciencedirect.com/science/article/pii/S1544612312000438>
- Timely opening range breakout sobre futuros de índices con datos de un minuto. <https://ieeexplore.ieee.org/document/8641124/>
- Zarattini y Aziz. Can day trading really be profitable? Estudio práctico, tratar con escepticismo alto. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622>
