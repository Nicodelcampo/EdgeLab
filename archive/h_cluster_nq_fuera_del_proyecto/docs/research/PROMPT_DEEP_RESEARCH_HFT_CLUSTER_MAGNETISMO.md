# Prompt de deep research — magnetismo de aglomeraciones de zonas HFT

> Para pegar en una sesión de deep research. Es autocontenido: el agente no tiene
> acceso al repo. Todo lo que necesita saber del indicador está descrito adentro.

---

Sos un metodólogo cuantitativo. Tu tarea **no** es decirme si mi hipótesis es
cierta, ni proponerme una estrategia. Es entregarme un **plan de medición con
estructura de embudo**: qué medir primero, qué decide cada medición sobre la
siguiente, y bajo qué resultado exacto se abandona la línea.

## 1. El objeto, con precisión

Trabajo con futuros del Nasdaq (NQ, CME) en barras de N ticks. Un indicador
propietario detecta **zonas HFT**: ráfagas de ticks consecutivos en una misma
dirección que cumplen umbrales de velocidad (milisegundos promedio entre ticks),
duración total, tasa de volumen, volumen total y retroceso máximo. Cada zona nace
en una barra concreta y ocupa un rango de precio (`Upper`, `Lower`). Se clasifican
en cuatro cubos (predator / ultra / direccional / absorción) según velocidad.

Sobre esas zonas, el indicador construye **clusters**, que son el objeto de mi
hipótesis:

1. Cada vez que **nace una zona nueva**, se toman las zonas previas (hasta 150
   hacia atrás en la lista) que siguen "vigentes".
2. Se arma un histograma de densidad **por tick de precio**: cada zona suma 1 en
   cada tick que cubre.
3. Los ticks con densidad ≥ 4 zonas se agrupan en segmentos contiguos (tolerancia
   de 1 tick de hueco). Cada segmento es un cluster.
4. El cluster tiene un **POC**: el tick con más zonas superpuestas, desempatado por
   volumen acumulado.
5. Si el cluster nuevo se solapa en precio con uno activo, se **fusiona**:
   `Lower = min`, `Upper = max`, `ZoneCount = max(anterior, nuevo)`, y se extiende
   el fin.

## 2. Mi hipótesis

**Las aglomeraciones de zonas con actividad HFT atraen al precio.**

## 3. Tres defectos del instrumento que el plan debe neutralizar

Los descubrí leyendo el código y son la razón principal por la que pido esto.

1. **La vigencia de una zona es un parámetro de dibujo.** Una zona participa del
   histograma mientras no expiró su extensión visual, que es un parámetro
   cosmético (600 barras por defecto). Es decir: el ancho, la membresía y la vida
   del cluster dependen de una decisión de presentación, no de un criterio de
   mercado. Necesito saber cómo se define la vigencia de un nivel de liquidez en
   la literatura, y qué hacer cuando la definición es arbitraria: ¿barrido de
   sensibilidad?, ¿vida media estimada de los datos?, ¿vigencia definida por
   invalidación de precio?

2. **El cluster no decae y se reescribe hacia atrás.** `ZoneCount` es una marca de
   agua que nunca baja, y la geometría fusionada es la unión histórica. El objeto
   que existe al final del gráfico **no es** el que existía cuando el precio se
   acercó. Cualquier medición necesita un **censo as-of**: reconstruir el estado
   del cluster tal como era en el instante t, incluyendo los clusters que después
   se fusionaron o murieron.

3. **El cluster se dibuja 600 barras hacia el futuro.** Visualmente siempre parece
   que el precio "va hacia" algo que ya estaba ahí. Necesito que el plan diga
   explícitamente qué parte de mi impresión visual es un artefacto de esto.

## 4. Un antecedente que no quiero repetir

En este mismo proyecto, una hipótesis muy parecida —zonas de otro indicador como
**imán** de precio, sobre el euro— fue **refutada y cerrada**. La cadena que la
mató, y que quiero heredar como estándar mínimo:

- El efecto contra un **espejo geométrico** (la zona reflejada respecto del precio)
  era real y positivo... pero
- un **control sin zona**, con la misma geometría y la misma distancia, daba casi
  lo mismo: el contraste cruzaba cero. **No era la zona: era la geometría.**
- Y una **vela extrema genérica** sellaba el efecto igual de bien que la zona del
  indicador: el detector no aportaba nada por encima de un marcador barato.

Quiero que el plan incorpore controles de esta clase desde el primer escalón, no al
final.

## 5. Lo que te pido, concretamente

### A. Estado del arte, con fuentes verificables

Buscá y sintetizá, citando papers, working papers o libros con autor, año y venue:

1. **Magnetismo / atracción de precio hacia niveles**: pinning en vencimientos de
   opciones, atracción hacia strikes, números redondos, POC y HVN del perfil de
   volumen, niveles de alta liquidez en el libro. Qué efectos están documentados,
   con qué tamaño, en qué activos, y **cuáles fueron desmentidos**.
2. **Clustering de órdenes y cascadas de stops**: qué dice la microestructura sobre
   la acumulación de órdenes en niveles y su efecto sobre el recorrido del precio.
3. **Crítica metodológica**: por qué las afirmaciones de "atracción" son
   típicamente artefactos. Me interesan especialmente el sesgo de proximidad (el
   precio golpea más lo que tiene cerca), la reversión a la media como línea base,
   la selección por supervivencia del objeto dibujado, y el problema de que el
   nivel se define a partir del mismo precio que después se mide.

### B. El nulo correcto

Esta es la parte que más me importa. Para "el precio es atraído por un cluster",
decime **cuál es la línea base contra la que hay que comparar** y cómo se
construye:

- ¿Cuál es la probabilidad de tocar un nivel a distancia *d* bajo un caminante sin
  deriva? Dame la forma exacta y sus supuestos, y qué pasa cuando la volatilidad no
  es constante.
- ¿Cómo se construye un **control sin cluster** con la misma geometría, la misma
  distancia, el mismo instante y el mismo contexto de volatilidad? Dame la receta,
  y también las formas conocidas en que ese control sale mal.
- ¿Qué controles adicionales exige un objeto cuya **existencia depende de actividad
  reciente**? El cluster nace de ráfagas, las ráfagas ocurren donde hay volumen, y
  el volumen ocurre donde el precio ya estuvo. Quiero el tratamiento formal de esa
  endogeneidad.

### C. El embudo

Entregame una **secuencia de mediciones**, de la más barata y target-free a la más
cara, donde cada escalón tenga:

- **Nombre y pregunta** que responde, en una línea.
- **Estimand**: qué cantidad exacta se estima, escrita sin ambigüedad.
- **Población**: enumerada explícitamente. Distinguí entre medir **eventos**
  (nacimiento de cluster, primer toque, fusión, invalidación) y medir **estado**
  (cluster activo en cada barra, distancia del precio al POC en cada barra). Decí
  cuál corresponde a cada escalón y por qué, y qué potencia estadística gana o
  pierde cada elección.
- **Nulo y control** concretos.
- **Condición de refutación**: el resultado numérico exacto que mata el escalón.
- **Regla de decisión**: qué escalón sigue si pasa, y cuál si falla.
- **MDE**: cómo calcular el efecto mínimo detectable *antes* de correr, para que un
  resultado nulo se distinga de falta de potencia.

Los primeros escalones tienen que ser **target-free**: geometría, ciclo de vida,
dinámica de la distancia precio-cluster. Nada de P&L hasta que la información
condicional esté demostrada.

Para cada escalón, además: **qué canal se mide**. Un efecto que empuja al precio en
las dos direcciones puede promediar exactamente cero si sólo se mira el canal
direccional, así que quiero direccional **y** no direccional (magnitud absoluta,
distribución completa), no uno solo.

### D. Estimadores

Nombrá las herramientas estadísticas apropiadas y **decí cuándo cada una es la
equivocada**. Me interesan al menos: análisis de supervivencia con riesgos
competitivos (tocar el cluster vs. invalidarse vs. censura por fin de sesión),
tiempos de primer paso contra referencia browniana, procesos puntuales marcados y
condicionamiento por intensidad, funciones de segundo orden tipo Ripley para
clustering en el eje de precio, y bootstrap por bloques o clusterizado por sesión
para inferencia con dependencia serial. Si alguna es inapropiada acá, decilo y por
qué.

### E. Instrumentación

Decime **qué hay que registrar en el momento en que ocurre** —no reconstruido
después— para que todo lo anterior sea medible: campos por zona, por cluster, por
barra, y el censo as-of que hace falta para que un cluster fusionado o muerto no
desaparezca del registro. Incluí qué hace falta para detectar **repintado**: cómo
verificar que el objeto que el indicador muestra en la barra t es el mismo que
mostraba en tiempo real en la barra t.

## 6. Restricciones de la respuesta

- Nada de recomendaciones de trading, ni parámetros sugeridos, ni promesas de
  rentabilidad.
- Si la evidencia de la literatura contradice mi hipótesis, decilo primero y con
  claridad.
- Cada afirmación empírica va con su fuente. Si no encontrás fuente, marcala
  explícitamente como conjetura tuya.
- Preferí decir "esto no se puede medir con lo que tenés" antes que ofrecer un
  sustituto débil.
- Formato: un documento estructurado, con el embudo como tabla o lista numerada
  donde cada escalón se pueda leer y ejecutar por separado.
