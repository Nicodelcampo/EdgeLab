# Intake Nico · H-Z2A exploratorio — 2026-08-18

- **Origen:** chat Notion, hilo del auditor, 18-ago-2026 23:37 y 23:49 ART.
- **Por qué existe este archivo:** Nico pidió que sus mensajes queden **textuales** en un lugar que sobreviva el recambio de agentes. El repo es el sistema de registro.
- **Esto no autoriza** F4, P&L, holdout ni un detector nuevo corriendo sobre datos.
- **Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

Si este archivo y el chat divergen, **manda este archivo** para la prosa de Nico. La adjudicación (qué entra a v2, qué no) manda desde la entrada 029 y `PENDIENTE.md` / el addendum del board.

---

## 1. Mensaje textual · 18-ago-2026 23:37 ART

> La máquina está libre. Respecto de P-45:
> Mi enfoque es el exploratorio. A pesar de tener una hipótesis, esta hipótesis surge de mi experiencia subjetiva en el mercado. Es decir: no he medido la distancia de la que proviene el precio cuando hace un near miss. Lo que si: 1- esta distancia tiende a ser lejana, lo que sugiere que desde que se creó la zona a la que el precio le ha realizado el near miss, el precio ya comerció lo que debía, y no se dará vuelta justo antes de la misma, por no tener otro objetivo más importante relativamente, considerando el esfuerzo y el consumo de ordenes que le requeriría evitar la zona near miss. 2- Tiende a revertir con imbalance, es decir, la reversión suele ser rápida, tener forma de vshape, imbalance, poco comercio, no muy escalonada ni trabajada. 3- A la vuelta, en las ocasiones en las que el precio SI llega o atravieza la zona, presenta más fuerza, empuje, y sobre todo, creación progresiva de valor, no parece un empuje institucional forzado que es “soltado” justo antes de la zona, parece más bien una aceptación progresiva la cual no va a permitir que el precio se derrumbe. 4- El precio, cuando si llega a la zona, proviene de haber realizado un relativamente alto nivel de comercio, saldado, balanceado, liquidado, además de provenir de una distancia relativamente alta. 5- Esto quizás lleve trabajo para que la máquina lo entienda, pero la tendencia tiene que ser lo que yo llamo “saludable” o “sólida”, esto quiere decir, que cuando el precio, en una tendencia, va dejando “escalones” o construcciones progresivas de liquidez, máximos o minimos progresivos o consecutivos, no los deja pendientes (ya que esto sugeriría que posiblemente va a revertir para tomarlos/alcanzarlos) sinó que se evidencia que tras crear estas construcciones, el precio, relativamente pronto, las liquida con un movimiento normalmente rápido, brusco, fuerte, y luego continua la tendencia, como si hubiera “patrocinadores de la tendencia” que no permiten que el precio rompa con fuerza, sinó que haga mas bien “fakeouts” para sumarse a mejores precio en la tendencia sin que esta se “derrumbe”. Se que esto ultimo que acabo de describir es semánticamente comprensible y debe estar estudiado y respaldado por teorías de estructuras y subastas, y que la parte compleja es que la máquina entienda este escenario. Considero probable que haya que realizar un trabajo riguroso y preciso para que la detección de esta situacion sea una posibilidad dentro de edgelab y que además sea explotable económicamente hablando. Enfocándome más en la respuesta concreta a la pregunta digo: muchas cosas cuentan como un near miss, si consideramos distintas distancias a las que reacciona, distintas distancias de las que proviene, distintas distancias a las que se tiene que alejar de la zona para considerar al evento un near miss, distintos tipos de zonas con más y menos densidad, más y menos volumen, más y menos imbalance/agresividad. Lo que quiero que se entienda es que near miss es un concepto amplio y el objetivo es explorarlo más que describirlo. A partir de esto realizá las preguntas que consideres necesarias para encauzar este mensaje hacia el proyecto y hacia P-45

---

## 2. Mensaje textual · 18-ago-2026 23:49 ART

> Otra cosa que estoy pensando. A que zonas el precio les realiza un near miss, y luego sucede lo que yo describo? Porque quizás, midiéndolo de esta manera, tenemos eventos específicos que cuando se presentan en conjunto son como una “firma” de un evento estadística y económicamente rentable. Y otra cosa: No necesariamente una zona tiene que ser virgen, quizás hay niveles de comercio o de atraviezamiento del precio que no la invalidan ya sea por pasar poco tiempo, poca distancia o poco volumen, por lo que eso seria algo a revisar. Con respecto a tus preguntas: 1- Debe haber un umbral (rango) y que posiblemente se comporte como un parámetro, dentro del cual considerar un near miss. Inicialmente no se debería diferenciar entre uno más cercano o más lejano, aunque sería bueno saber si uno funciona mejor que el otro. Una vez que se cumplió el near miss, el 2do, si cumple las condiciones de excursion, distancia, tiempo, volumen, (o lo que esté descrito como umbral/parámetro para el análisis) se consideraría simplemente parte del retorno a la zona, y si luego se dieran las condiciones para considerarlo como otro near miss, entonces ahí si se lo consideraría. 2- Si te parece que es mas conveniente, si, que mida solo capa, pero que lo haga de la manera debida, considerando la totalidad de la idea que se quiere probar/llevar a cabo. 3- Lo que consideres que no sea tanto nivel de cómputo y tenga buena relacion recurso/información/avance. 4- abramos hftzones2. 5- quiero que si se mire, probablemente brinde informacion importante, en relacion al comportamiento del precio luego de llegar, si se expande, detiene, revierte, adquiere fuerza, mae, mfe, etc. 6. que empiece ahora. Y estos ultimos mensajes, incluilos (a los míos) textuales en algun lugar que aguante fricciones de transicion entre agentes. y también los aportes metodológicos y de research (útiles como base) para esta parte del proyecto.

---

## 3. Base metodológica (no es la prosa de Nico; es el mapa)

Tres capas. Mezclarlas hace inmedible la hipótesis.

| Capa | Qué es, en su prosa | Dónde vive hoy | Qué se hace |
|---|---|---|---|
| **1 · geometría** | de dónde viene, qué tan cerca llega, cuánto se aleja | censo H-Z2A: `D_far`, `δ`, `R`, trade/quote | **v2 ahora**, con P-45 (c) |
| **2 · contexto / firma** | imbalance en V, saldado, tendencia saludable, tipo de zona, no-virgen | no está en el censo; v4 lo nombra como mecanismo o validez | spec y puntos de board; **no corre sobre datos en v2** |
| **3 · resultado** | si llega, fuerza, expansión, MAE/MFE, que no se derrumbe | H-A2ACCESS / H-PEN / H-ECON en v4 | **prohibido** hasta manifiesto + STOP |

La «firma» (near-miss + lo que describe, en conjunto) es una **campaña posterior**: primero hay población (capa 1), después se pregunta qué coincidió. No se busca la firma eligiendo el gráfico que se ve bien.

H-Z2A v4 ya partió la cadena: H-NM → H-REVISIT → H-A2ACCESS → H-PEN → H-ECON. El censo sólo responde «¿hay N para testear esta celda?». No responde «¿es rentable?».

Literatura de vocabulario (no de tasa): Auction Market Theory / poor high-low (v4: analogía, no identidad); Osler (interrupción en niveles, no la secuencia completa); Chung–Bellotti (rebote *después* de entrar, no el giro *antes*). El punto 5 (escalones, fakeouts, patrocinadores) es Wyckoff / subasta / liquidez pendiente: genera un detector futuro, no un prior numérico.

**P-45 (c), en una línea.** Un near-miss cumplido abre un episodio. El acercamiento siguiente, si es el retorno, es A2, no un segundo near-miss. Un near-miss nuevo sólo si, *después* de ese episodio, se cumplen otra vez las condiciones. δ sigue siendo un parámetro de la grilla (explorar cuál funciona mejor), no un tipo de evento distinto «al inicio».

**Virgen.** v4 cond. 2 hoy exige cero trades en `[L,U]` antes del giro. Nico pide revisar umbrales de tiempo / distancia / volumen. Eso es P-47: se revisa; **v2 primera corrida sigue virgen** (el predicado actual). Relajarlo cambia la población.

**HFTZones2.** v4 lo dejó fuera del portador inicial (paridad fuerte, canon formal pendiente). Nico lo abre. Secuencia: **después** del censo v2 en aVol 6E, no en la misma corrida (recurso/información).

**F9.** Sigue pausada para *correr* detectores nuevos. «Que empiece ahora» = escribir el spec de tendencia saludable, no barrer datos.
