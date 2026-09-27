# Manifiesto ESPEJO-MÁS-ALLÁ — ¿qué pasa después del espejo? (BORRADOR, 2026-09-27)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pedido de Nico (2026-09-27):** mirar qué hay más allá del movimiento espejado. Quizás, cuando hay un imán, el precio
no sólo espeja el impulso sino que va más lejos. Las razones posibles son muchas: la dirección, el agotamiento, la
presencia de imanes del precio, etc.
**Estado: BORRADOR, NO EJECUTABLE.**
- **§4.3 (qué cuenta como imán) queda vacío a propósito**, hasta que Nico lo defina.
- Además aplica el STOP: esto es búsqueda sobre retornos, así que hace falta el OK de Nico sobre el manifiesto
  completo.
- No se miró ningún dato para escribirlo.

**Familia:** ESPEJO, subfamilia ESPEJO-MÁS-ALLÁ, con ledger y multiplicidad propios. Hereda **sólo** el detector y el
evento de ESPEJO-MACRO, no sus resultados.

## 1. Notación

- Impulso de A a B, de tamaño W. La vuelta va de B hacia A.
- La **extensión o** es cuánto pasa de A, medida en W. El objetivo está en A + o·W, del otro lado de A.
- o ∈ {0,25; 0,5; 1,0}, fijado ahora.

## 2. Poblaciones (dos, declaradas por separado)

**P1 — condicional al espejo.** El primer toque de A, en eventos que ya completaron el espejo.
- Pregunta: ya espejado, ¿sigue?
- **Barrera en contra:** la mitad del impulso (A + 0,5·W de vuelta hacia B). Es la principal.
- **Nulo exacto** (precio sin memoria): P(llegar a A + o·W antes que a la barrera) = 0,5 / (0,5 + o).
- Como variante se reporta también la barrera en B, con nulo 1 / (1 + o).

**P2 — desde la entrada.** El evento de ESPEJO-MACRO: primer cruce de x, con x ∈ {0,5; 0,75}.
- Pregunta: ¿se puede predecir desde temprano el tramo completo, incluida la extensión?
- **Nulo exacto:** P(llegar a A + o·W antes que a B) = f / (1 + o), con f medido al cierre de la vela.

**Espacio de eventos considerado y descartado:**
- toque n-ésimo de A;
- estado continuo cerca de A;
- ruptura de A por cierre, en lugar de por toque.

Por qué se eligió así:
- P1 aísla la pregunta de Nico («más allá del espejo»).
- P2 es la operable desde temprano.

**Cómo podría refutarse la población:** si el efecto sólo aparece por cierre más allá de A y no por toque, o sólo en
el estado continuo.

## 3. Detector, datos y horizonte

- **Detector:** TBZX de ESPEJO-MACRO (5 y 15 min, k ∈ {3, 4, 6}), sin cambios. Los impulsos ineficientes quedan para
  ESPEJO-INEF.
- **Horizonte:** hasta el cierre de la sesión del día siguiente. Con la sesión RTH sola, las extensiones grandes
  quedarían censuradas. Los censurados se reportan aparte.
- **Descubrimiento:** SPY 2008–2021.
- **Replicación:** ES, NQ e YM, de jul-25 a mar-26. Los cortes quedan congelados en el descubrimiento.
- Holdout y abr–jun intactos.

## 4. Condicionantes (cada uno se prueba solo; los cruces, después y con pre-registro propio)

### 4.1 Dirección
- Alcista o bajista.
- A favor o en contra de la tendencia de fondo: pendiente de la media de 60 minutos al momento del evento.

### 4.2 Agotamiento
Medido en el evento, sólo con información pasada.
- **Aceleración de la vuelta al llegar a A:** velocidad del último cuarto contra el promedio de la vuelta.
- **Volumen por vela** del último cuarto de la vuelta, contra el del impulso.
- Hipótesis: si la vuelta llega a A acelerando y sin agotarse, sigue. Si llega frenando, se queda en el espejo.

### 4.3 Imanes — **PENDIENTE: lo define Nico**
Requisitos que la definición tendrá que cumplir, fijados ahora:
1. Se puede calcular *as-of*, con información disponible en el evento, y no se repinta.
2. Tiene **control sin imán con la misma geometría**, a la misma distancia de A y con el mismo W.
   - Motivo: en F2.8 (BigTrap2, 6E) el «imán» murió justamente porque ese control daba casi lo mismo.
   - Aquella muerte no se transporta acá, pero la lección de diseño sí.
3. La distancia al imán se mide en W y se declaran de antemano las franjas: el imán dentro de la extensión o, justo
   después, o lejos.
4. Si el indicador del imán borra niveles al mitigarlos, hace falta un censo as-of que incluya los muertos.

## 5. Medidas y pruebas

**Resultado:**
- La tasa de llegada a cada o, con su exceso sobre el nulo.
- **Además, la distribución completa de la extensión máxima** antes de tocar la barrera. Es el canal no direccional:
  una cola más larga puede existir aunque la tasa en un o fijo no se mueva.

**Pruebas:**
- **Base:** exceso sin condicionar, por población, x y o.
- **Condicionales:**
  - tercil alto contra tercil bajo en cada condicionante continuo;
  - comparación entre categorías en los discretos.
- **Estadística:** bootstrap por sesión (1.000), BH-FDR con q = 0,10 sobre toda la grilla.
- **Potencia:**
  - se publica el MDE de cada prueba;
  - no se interpreta ninguna celda con n < 30.
- **Sostenido:**
  1. pasa FDR en SPY;
  2. mismo signo en ES, NQ e YM;
  3. IC > 0 en la combinada de futuros.
- **Número efectivo de hipótesis:** se calcula y se presenta con el OK, una vez definido §4.3.

## 6. Justificación económica y cómo podría refutarse

**Mecanismo candidato:**
- El espejo deja atrapados a los que entraron a favor del impulso. Si más allá de A hay liquidez que atrae (el imán) o
  la vuelta no muestra agotamiento, los stops de esos atrapados empujan el precio más allá.
- Económicamente, la extensión agranda el recorrido con el mismo costo, así que baja costo/recorrido.

**Refutación:**
- el exceso sobre 0,5 / (0,5 + o) no sostiene en P1; o
- los condicionantes no separan (tercil alto ≈ tercil bajo); o
- el imán no le gana a su control sin imán.

**Un NO acá** invalida sólo la extensión más allá de A con este detector, estas barreras y estos condicionantes.
No invalida el espejo.

## Fase 0 — ¿hay a simple vista casos que van más allá y casos que no? (pedido de Nico, 2026-09-27)

Escrita y commiteada **antes** de medir. **No usa imanes ni condicionantes**: sólo pregunta si la extensión más allá
de A se reparte distinto de lo que produce el azar. Nico lo pidió explícitamente.
- Descriptiva, sin entradas ni costos.
- Es un chequeo de heterogeneidad, no una búsqueda de reglas.

**Población:** P1 de §2.
- El primer toque de A en impulsos TBZX cuyo espejo se completó dentro de la sesión.
- Velas de 5 minutos, configuraciones `5m_12_3`, `5m_12_4` y `5m_24_4`: las tres que sostuvieron en ESPEJO-MACRO,
  fijadas de antemano.

**Medida:** M es la extensión máxima más allá de A, en unidades de W.
- Se corta cuando el precio vuelve hasta la barrera A ± 0,5·W (hacia B), o al terminar la sesión. Si termina la
  sesión, el evento queda censurado y se reporta aparte.
- La vela del toque cuenta: para pasar de A, el precio tuvo que tocar A primero.
- En las velas siguientes, si la barrera y una extensión nueva caen en la misma vela, se toma primero la barrera. Es
  la opción pesimista, y se aplica igual al real y al placebo.

**Nulos:**
- **Principal: placebo empírico.** Por cada evento real se toma una vela al azar de la misma sesión (semilla fija).
  - El nivel es la apertura de esa vela.
  - Mismo W, misma dirección de continuación, mismo algoritmo.
  - Controla la discretización, la volatilidad del día y el censurado por fin de sesión.
- **Referencia teórica:** P(M ≥ o) = 0,5 / (0,5 + o).

**Pruebas:** 18 en total.
- **Supervivencia:** en o ∈ {0,25; 0,5; 1; 2}, la diferencia entre P(M ≥ o) del real y del placebo. Son 4 × 3 = 12
  pruebas.
- **Heterogeneidad** («casos que sí y casos que no»):
  - la parte que muere en A (M < 0,1), real menos placebo;
  - la parte que se va lejos (M ≥ 1), real menos placebo;
  - 2 × 3 = 6 pruebas.
  - Si las **dos** son positivas, hay más casos de los dos extremos que en el azar: dos clases de casos.
- **Estadística:** bootstrap por sesión (1.000) y BH-FDR con q = 0,10 sobre las 18 pruebas en SPY (descubrimiento).
- **Replicación:** ES, NQ e YM RTH combinados, con el mismo signo e IC > 0. ES sesión completa se reporta como
  descriptivo.
- Se publica el MDE de cada prueba y **la distribución completa de M**.
- Holdout y abr–jun intactos.

**Justificación económica:** si hay una clase de espejos que siguen de largo, P1 tiene una cola aprovechable que
después se puede buscar con condicionantes (dirección, agotamiento, imanes).

**Cómo podría refutarse:** la distribución de M real es indistinguible de la del placebo. En ese caso, «a simple
vista» no hay dos clases, y cualquier diferencia que se vea en un chart es la que produce el azar.
