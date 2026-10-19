# Research: transición en el borde de una zona de expansión (TBZ), 2026-09-24

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Estado:** INVESTIGACIÓN + PROPUESTA DE FAMILIA. **No registrada, no medida.** Registrarla la decide Nico (P-86).
**Origen:** observación de Nico sobre dos capturas de MES DEC26 (10 ticks) del **24/09/2026, que es holdout**. Ver §10.
**Nombre neutral:** TBZ, "transición de borde de zona". Se evitan nombres que ya afirman un mecanismo ("inventario balanceado", "zona institucional").

---

## 1. El fenómeno, en términos observables

Nico lo describe así: una **expansión rápida** de A a B deja una zona [A, B]. Después el precio negocia **fuera** de la zona, se aleja, negocia volumen y **rechaza varias veces el borde exacto**, negándose a entrar. En algún momento "cambia la intención": el precio empieza a **penetrar levemente** en lugar de rechazar, y después **atraviesa la zona sin dificultad** hasta el otro borde.

### Lectura de las dos capturas (solo visual; no se saca ningún parámetro de acá)

| | Captura 1 (8:10–8:43) | Captura 2 (8:26–8:59) |
|---|---|---|
| Expansión | Sube de ~7726,25 (A) a ~7731,25 (B), 8:12–8:14 | Sube de ~7727,25 (A) a ~7729,5 (B), 8:35–8:36 |
| Dónde queda el precio | **Del lado de B** (arriba, lado de continuación) | **Del lado de A** (abajo): la expansión se revierte entera enseguida |
| Borde que rechaza | B, desde arriba (8:18, 8:22, 8:27–8:29) | A, desde abajo (8:39, 8:40, 8:55) |
| Travesía | De B hacia A, **en contra** de la expansión (8:33–8:40) | De A hacia B, **a favor** de la expansión (8:56–8:58) |
| Después del borde lejano | Sigue de largo hasta 7722 | Sigue de largo hasta 7733,5 |

**Consecuencia de diseño:** los dos casos **no son espejos**. El fenómeno es "**borde cercano**, cualquiera sea": el precio puede estar del lado del final de la expansión (CONT) o del lado del origen (ORIG). Una definición que suponga que el precio siempre queda del lado de B pierde la mitad de los casos, incluido el segundo ejemplo.

**Otras cosas que se ven:**
- **B no es el extremo de la expansión.** Es el final del primer empuje rápido: el precio siguió hasta 7736,5. Definir "fin de la expansión" es el parámetro más delicado.
- **Las zonas se solapan.** La región de la segunda zona queda cerca del borde A de la primera. La confluencia es una población en sí misma.
- **El borde lejano no es un techo ni un piso:** en los dos casos el precio siguió de largo.

---

## 2. Descomposición en fases

| Fase | Qué pasa | Pregunta que abre |
|---|---|---|
| **F0 Formación** | Desplazamiento rápido de A a B, con poco tiempo y poco volumen por nivel de precio | ¿Qué es "rápido"? ¿Dónde termina? |
| **F1 Exterior** | El precio negocia fuera, del lado cercano, se aleja y acumula volumen | ¿Cuánto volumen y cuánta distancia? ¿Quién opera? |
| **F2 Contactos** | Vuelve al borde cercano y rechaza, una o varias veces | **¿Por qué rechaza justo ahí?** |
| **F3 Transición** | Los contactos empiezan a penetrar | ¿Qué cambió? ¿Se puede ver **antes** de que cruce? |
| **F4 Travesía** | Cruza la zona rápido hasta el borde lejano | ¿Por qué rápido? |
| **F5 Después** | Sigue, frena o vuelve | Abierta: en las capturas siguió |

---

## 3. Mecanismos candidatos, con la literatura que los respalda

Cada mecanismo es una **hipótesis**, con una predicción que se puede medir. Ninguno está probado para MES.

### M1: Memoria del nivel (profecía autocumplida) → F2
- Garzarelli, Cristelli, Zaccaria y Pietronero (2014, *Scientific Reports* 4:4487; [arXiv:1110.5197](https://arxiv.org/abs/1110.5197)): en acciones de Londres, a escala de 45–90 s, el precio **rebota más de lo que cruza** en niveles de soporte/resistencia. La probabilidad de rebote **sube con la cantidad de rebotes previos**, contra un nulo de retornos barajados que da ~0,5.
- Chung y Bellotti (2021, [arXiv:2101.07410](https://arxiv.org/abs/2101.07410)): lo replica en EURUSD, acciones y Brent (datos de 1 min). Además, el efecto **decae con el tiempo**: con 1 rebote previo vuelve a 0,5 en ~350 min, con 4 rebotes en ~900 min (EURUSD). **No se explica con procesos AR(1).**
- **Dato metodológico clave:** en los dos trabajos, el ancho de la franja que define "estar en el nivel" es la variación media del precio a esa escala. Chung y Bellotti muestran que **una franja más ancha infla la probabilidad de rebote aun en una caminata aleatoria, y una más angosta la desinfla.** La tolerancia no se elige a ojo: se calibra para que el nulo dé 0,5.
- **Tensión con el fenómeno:** M1 dice que cuantos más rebotes, más fuerte el borde. Lo que describe Nico es que después de varios rebotes el borde **cede**. Las dos cosas pueden ser ciertas si el borde se fortalece al principio y se debilita con el tiempo o con otra variable. **Esa es la pregunta central** (§5.4).

### M2: Liquidez concentrada en el borde → F2 y F3
- Kavajecz y Odders-White (2004, *Review of Financial Studies* 17(4):1043–1071, [enlace](https://academic.oup.com/rfs/article-abstract/17/4/1043/1570736)): los niveles de soporte y resistencia **coinciden con picos de profundidad** en el libro de órdenes límite.
- Cont, Kukanov y Stoikov ([arXiv:1011.6402](https://arxiv.org/abs/1011.6402)): en intervalos cortos, el cambio de precio es **lineal en el desequilibrio de flujo de órdenes (OFI)**, con pendiente **inversamente proporcional a la profundidad**.
- **Predicción:** mientras hay rechazos, la agresión hacia la zona se come la fila del borde, pero la fila se **repone**: mucho volumen, poco avance. La transición llega cuando la reposición cae o la fila se retira: el mismo volumen agresor consigue más avance.
- **Dato necesario: L2.** Con ticks solo se ve el avance por unidad de volumen agresor, no la reposición.
- Bechler y Ludkovski ([arXiv:1708.02715](https://arxiv.org/abs/1708.02715)): en activos de tick grande, a escala de minutos, **los flujos de órdenes límite (altas y cancelaciones) son los que más predicen**, más que el desequilibrio del libro. Justamente lo que M2 necesita medir.

### M3: Impacto de una orden grande y su relajación → F1, F3 y F4
- Una expansión rápida puede ser la ejecución de una **orden grande partida** (metaorden). La literatura de impacto muestra, con datos propietarios, que:
  - mientras la orden se ejecuta, el precio se sostiene;
  - **cuando termina, el precio revierte en seguida** (Bacry, Iuga, Lasnier y Lehalle, [arXiv:1412.0217](https://arxiv.org/abs/1412.0217): decaimiento intradiario en dos regímenes);
  - en promedio, el impacto se relaja a **~2/3 del máximo** (Zarinelli, Treccani, Farmer y Lillo, [arXiv:1412.2152](https://arxiv.org/abs/1412.2152); "Market Impact: A Systematic Study of Limit Orders", [arXiv:1802.08502](https://arxiv.org/abs/1802.08502); "Slow decay of impact in equity markets", [arXiv:1901.05332](https://arxiv.org/abs/1901.05332): ~2/3 al cierre del mismo día).
- Farmer, Gerig, Lillo y Waelbroeck ([arXiv:1102.5457](https://arxiv.org/abs/1102.5457)) lo derivan como **"fair pricing"**: el precio después de la ejecución es igual al precio promedio de ejecución.
- **Esto es lo más cercano, en la literatura, a "cuando el precio ya niveló inventarios".** En M3:
  - "negarse a entrar" es la orden grande todavía activa, que compra cada retroceso;
  - la "transición" es que la orden termina;
  - la "travesía" es la relajación del impacto.
- **Predicción cuantitativa que lo distingue:** si todo fuera M3, el precio devolvería **~1/3 del impacto máximo** (medido desde A hasta el extremo que alcanzó el precio), **no volvería hasta A**. En la captura 1, eso sería desde 7736,5 hacia ~7733, y el precio fue mucho más allá de A. Una travesía completa exige algo más (M4 o M5). Es medible: ¿dónde termina la vuelta, como fracción del impacto máximo?
- **Se puede medir con ticks:** "Generating realistic metaorders from public data" ([arXiv:2503.18199](https://arxiv.org/abs/2503.18199)) reconstruye metaórdenes sintéticas con solo la cinta pública (signo del trade y orden cronológico), incluido un futuro (EuroStoxx), y recupera la relajación posterior. Un proxy más simple: **el flujo firmado de agresión desde la formación debería aplanarse antes de la transición**.

### M4: Órdenes stop y cascadas → F4
- Osler (2003, *Journal of Finance* 58:1791–1819, [enlace](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588)), con órdenes reales de un banco de FX:
  - las órdenes **take-profit** se agrupan en niveles visibles y **frenan** tendencias;
  - las órdenes **stop-loss** se agrupan **justo del otro lado** y las **aceleran** cuando se cruza el nivel.
- Osler (2005, *J. Int. Money and Finance* 24:219–241, [enlace](https://ideas.repec.org/a/eee/jimfin/v24y2005i2p219-241.html)): los stops generan **cascadas de precio** que se refuerzan solas.
- **Predicción:** un borde muy defendido (muchos rechazos) acumula stops justo adentro de la zona. Cuando cede, aparece un **estallido de agresión** en la dirección de la travesía, y la travesía es más rápida cuantos más contactos hubo. **Se mide con ticks**: volumen agresor en los primeros ticks adentro de la zona, contra el mismo recorrido en controles.

### M5: Hueco de liquidez adentro de la zona → F4
- Tóth, Lemperiere, Deremble, de Lataillade, Kockelkoren y Bouchaud ([arXiv:1105.1694](https://arxiv.org/abs/1105.1694)): la liquidez latente tiene forma de V y se forma alrededor de donde el precio **estuvo**. Una zona recorrida rápido casi no tuvo precio "estacionado", así que tiene poca liquidez acumulada.
- "Studies of the limit order book around large price changes" ([arXiv:0901.0495](https://arxiv.org/abs/0901.0495)): después de un movimiento grande, el libro se **recupera lento** (ley de potencia, exponente ~0,4).
- "Endogenous Liquidity Crises" ([arXiv:1912.00359](https://arxiv.org/abs/1912.00359)): la liquidez **cae después de volatilidad y tendencia**.
- **Evidencia interna: HP-007.** El precio viaja **~3 veces más rápido** en corredores de baja densidad. Ojo: medido con otro modelo de densidad, no con el objeto de esta familia.
- **Predicción:** la travesía es más rápida y con menos volumen por tick que un recorrido de la misma distancia fuera de zonas.

### M6: Teoría de subasta (Market Profile; práctica, no evidencia)
Es el marco de los traders: Steidlmayer y Koy, *Markets and Market Logic* (1986); Dalton et al., *Mind Over Markets*.
- La expansión deja un **nodo de bajo volumen** (single prints).
- Afuera se construye "valor" (nodo de alto volumen), y el borde de la zona es el límite de ese valor.
- Cuando el valor se desplaza, el precio "rota" rápido por el nodo de bajo volumen.

Su contenido medible coincide con M5 más "equilibrio completado" (M3): no se lo trata como hipótesis aparte, sino como vocabulario.

### M7 (nulo): caminata aleatoria y ojo selectivo → todo
- Una caminata aleatoria **vuelve muchas veces** a un nivel cercano.
- Con una tolerancia del tamaño del ruido de una barra, "rechazos exactos" aparecen por azar.
- El ojo elige las zonas que terminaron en travesía y descarta las que no.
- Cualquier resultado se mide **contra este nulo**: retornos barajados dentro de la sesión (Garzarelli), niveles placebo (§7) y la **población completa** de zonas.

---

## 4. Qué predice cada mecanismo (lo que permite distinguirlos)

| Observable | M1 memoria | M2 liquidez en el borde | M3 orden grande | M4 stops | M5 hueco | M7 nulo |
|---|---|---|---|---|---|---|
| Rebote en el borde contra placebo | > placebo | > placebo | > placebo mientras la orden está activa | ≈ | ≈ | = placebo |
| Rebote a medida que suman contactos | **sube** | baja si la reposición cae | cae cuando la orden termina | ≈ | ≈ | constante |
| Avance por unidad de agresión en contactos sucesivos | ≈ | **sube antes del cruce** | sube cuando termina la orden | ≈ | ≈ | constante |
| Flujo firmado desde la formación | ≈ | ≈ | **se aplana antes del cruce** | ≈ | ≈ | ≈ 0 |
| Estallido agresor al cruzar | ≈ | ≈ | ≈ | **sí, mayor cuantos más contactos** | ≈ | no |
| Velocidad y volumen por tick en la travesía | ≈ | ≈ | ≈ | más rápida | **más rápida, menos volumen** | igual al control |
| Dónde termina la vuelta | — | — | **~1/3 de la zona** | pasa A | llega a A | sin preferencia |
| Profundidad en el borde (L2) | ≈ | **pico, y después cae** | ≈ | ≈ | baja adentro | sin pico |

Los mecanismos **no son excluyentes**. El objetivo no es elegir uno, sino **medir cuánto explica cada uno**, en qué fase y en qué instrumento.

---

## 5. Definición operativa (causal, sin mirar el futuro)

### 5.1 Detector de expansión (F0)
Una expansión es un tramo en el que, en una ventana W, se cumplen tres cosas:
- el desplazamiento neto es ≥ k · σ_W (volatilidad de esa ventana, en ese instrumento y a esa hora, calculada solo con el pasado);
- la **eficiencia** (movimiento neto ÷ recorrido total) es ≥ e;
- la velocidad está por encima de un percentil causal.

**Fin de la expansión (B):** el primer instante en que la velocidad cae por debajo del umbral, o hay un retroceso ≥ r ticks. Es el "fin del primer empuje" que marca el ojo, no el extremo.

**A** es el precio al inicio. A y B quedan **congelados** en `available_at` = fin + latencia.

La escala es **múltiple por construcción**: el ojo de Nico marca empujes de ~20 ticks en ~2 min, en MES de 10 ticks, pero eso es una escala entre varias. Se censan **todas** las escalas (paisaje target-free) antes de elegir. Ninguna se elige por resultado.

### 5.2 Coordenadas relativas (sirven para los dos lados)
- **Borde cercano** E_c = el borde del lado donde está el precio. **Borde lejano** E_l = el otro.
- **Ancho** w = |B − A| en ticks.
- **x** = distancia firmada al borde cercano, positiva hacia afuera. La zona es −w ≤ x < 0; el otro lado, x < −w.
- **Lado:** CONT (el precio está del lado de B) u ORIG (del lado de A). Cada captura es un caso distinto.

### 5.3 Eventos
Todos se definen con una tolerancia τ **calibrada contra el nulo**: la franja con la que una caminata con los retornos barajados da rebote ≈ 0,5 (Chung y Bellotti). τ se reporta en ticks **y** como fracción de w y del rango típico de la barra (ATJ-18).

| Evento | Definición |
|---|---|
| Aproximación | x ≤ a |
| Contacto | x ≤ τ |
| Rechazo | Después de un contacto, x vuelve a ≥ r_fuera sin haber bajado de −p_dentro |
| Penetración | x < −p_dentro |
| Aceptación adentro | Tiempo o volumen dentro de la zona ≥ umbral, sin salir |
| Travesía | x ≤ −w (llegó al borde lejano) |
| Retorno | Después de penetrar, vuelve afuera sin cruzar |
| Vencimiento | Edad > T_max o fin de sesión (censura) |
| Invalidación inmediata | Cruza sin ningún contacto previo |

- **Contactos independientes:** entre dos contactos tiene que haber una salida mínima δ y una separación mínima de tiempo. Diez trades seguidos en el borde son un contacto, no diez.
- **Zonas solapadas:** se registran las dos, con una marca de confluencia. No se fusionan en silencio.

### 5.4 Variables de estado (valen en cada barra; son la parte con más potencia)
- Edad de la zona.
- Distancia al borde cercano.
- Contactos y rechazos hasta ahora.
- **Volumen negociado afuera desde la formación ÷ volumen de la formación.**
- Excursión máxima afuera y tiempo afuera.
- **Penetración máxima y su tendencia a lo largo de los contactos.**
- Tiempo adentro por contacto.
- **Avance por unidad de volumen agresor en cada contacto** ("absorción").
- **Flujo firmado desde la formación** (proxy de M3).
- Volatilidad reciente, hora del día, cercanía a números redondos (Osler) y otras zonas cerca.

**La pregunta central, medible:** en cada instante, ¿cuál es el riesgo de cruce de la zona en función de (contactos previos, edad, tendencia de penetración, volumen afuera, flujo firmado)? Es un modelo de **riesgos competitivos**: cada estado puede terminar en rechazo, penetración, travesía o vencimiento. Así se reconcilian M1 ("más contactos, más fuerte") y la observación de Nico ("después de varios, cede"): ¿el riesgo de cruce baja con los contactos y sube con otra variable, como el volumen acumulado o la penetración creciente?

---

## 6. Población: el espacio enumerado antes de elegir (regla del proyecto)

| Familia de eventos | Qué pregunta responde | Etapa |
|---|---|---|
| Creación | ¿Cuántas zonas, de qué tamaño, cuándo? | E1, censo |
| Aproximación | ¿Cuántas vuelven? | E1 |
| Primer contacto | ¿Rebota más que un placebo? | E1b / E2 |
| Contacto n-ésimo | ¿Cómo cambia el rebote con los contactos? | E2 |
| Penetración | ¿Qué fracción termina en travesía y cuál vuelve? | E2 |
| Aceptación adentro | ¿Aceptar adentro precede a la travesía? | E2 |
| Travesía | ¿Es más rápida que un control? | E1b / E3 |
| Vencimiento | Tasa de censura (sin esto, la muestra queda sesgada) | E1 |
| Confluencia | ¿Las zonas solapadas se comportan distinto? | E2, población aparte |
| **Estado continuo** | Riesgo de cruce en cada barra (§5.4) | **E2, principal** |

**Cómo podría refutarse la población:** si el detector de expansión no separa estas zonas de zonas del mismo ancho formadas despacio (control del §7), el objeto no es "la expansión" sino cualquier rango de precio, y la familia se redefine.

---

## 7. Nulos y controles (cada uno ataca un mecanismo o un sesgo)

| Control | Para qué |
|---|---|
| **Retornos barajados dentro de la sesión** | Calibra τ y da el rebote base (M7) |
| **Niveles placebo a la misma distancia del precio**, la misma edad y la misma hora, sin expansión | ¿El borde es especial o es cualquier nivel? |
| **Control de geometría: misma distancia al toque en t0** | Lección del 24/09 (la "barrera" de absorción era distancia) |
| **Zonas del mismo ancho formadas despacio** | Aísla el efecto "formación rápida" (M5) |
| **Recorridos de la misma distancia fuera de zonas** | Velocidad de travesía (M5) |
| **Espejo por lado (CONT/ORIG)** | Se miden por separado y juntos |

Además, en todos los casos:
- se publica el **MDE**;
- se miden **dos canales** (con dirección y sin dirección);
- se publican las distribuciones completas;
- y se publica la **tabla de escalas** (ATJ-18): rango típico de la unidad de análisis, ancho de la zona, τ, tiempo hasta resolver. Si τ queda por debajo del ruido de una barra, el nulo es del estimador.

---

## 8. Datos y etapas del embudo

| Etapa | Qué | Datos | Mecanismos | Necesita OK de Nico |
|---|---|---|---|---|
| **E0** | Esta investigación y la definición | — | todos | — |
| **E1** | Censo target-free: zonas por escala e instrumento, anchos, frecuencias, censura, confluencias | Ticks pre-holdout de `research-v2`: **MES, ES, NQ y MNQ**, ago-2025 a jun-2026 (MES: 167 M trades; ES: 263 M) | — | No (target-free) |
| **E1b** | Ciclo de vida descriptivo contra placebo (rebote, penetración, travesía, velocidad), **solo en partición de exploración** declarada antes | Ídem | M1, M5, M7 | Sí (mira el precio después: reglas del atlas) |
| **E2** | La transición: riesgo de cruce según el estado (§5.4) | Ídem | M1, M2 (proxy), M3, M4 | **Sí: manifiesto + STOP** |
| **E3** | Mecanismo en el libro: profundidad y reposición en el borde, hueco adentro | **L2**: GC 30 sesiones pre-holdout (tick chico, no se transporta a MES). MES/ES L2 pre-holdout: **no existe** | M2, M4, M5 | Sí |
| **E4** | P&L | Solo si E2 da información incremental robusta | — | Sí, cadena completa G0–G5 |

**Límite honesto:** M2 (defensa y reposición en el borde) **no se puede identificar en MES/ES** hasta tener L2 pre-holdout: 2027, o datos comprados. Con ticks solo se ve su sombra (avance por unidad de agresión). Además, el L2 tiene 5 archivos con el reloj corrido (P-84).

---

## 9. Parámetros a estandarizar (se eligen por el paisaje target-free, nunca por P&L)

| Parámetro | Qué es | Cómo se fija |
|---|---|---|
| W, k, e | Ventana, tamaño mínimo (en σ) y eficiencia de la expansión | Barrido de escalas; se publica el censo completo |
| r | Retroceso que marca el fin del empuje (define B) | Barrido; sensibilidad reportada |
| τ | Tolerancia de contacto | **Calibrada contra el nulo barajado** (rebote ≈ 0,5) |
| δ, t_min | Separación entre contactos | Relativa a τ y a la escala de la zona |
| p_dentro, r_fuera | Penetración y rechazo | Múltiplos de τ; se reporta todo el barrido |
| T_max | Vencimiento | Según la decadencia observada en el censo (Chung y Bellotti: horas) |

**Normalización entre instrumentos:** todo en ticks del instrumento **y** en unidades de σ a esa escala y hora. Un número absoluto de contratos o segundos no se compara entre MES, ES y NQ.

---

## 10. Holdout: lo que implica que la idea salga del 24/09

- Las capturas son del **24/09/2026, holdout**. Sirven para **plantear** el fenómeno, no para medirlo.
- **No se saca ningún umbral de las capturas.** Todos los parámetros salen del censo pre-holdout.
- **El 24/09 queda excluido** de cualquier confirmación de esta familia, en MES y ES. Si Nico reporta más observaciones de días del holdout, se agregan a la lista.
- **Decisión de Nico:** ¿el resto del holdout sirve como confirmación ciega de una hipótesis que nació mirando el mercado en vivo durante el holdout? La exposición no es de parámetros sino de la idea. La alternativa conservadora es confirmar con datos de 2027.

---

## 11. Relación con lo que ya existe (no se transporta nada)

| Familia / resultado | Relación |
|---|---|
| BigTrap2 como soporte/resistencia: **refutado** (~96 % de ruptura) | Otro objeto: zonas de absorción de 1–3 ticks. Lección: las zonas terminan rompiéndose. Acá la pregunta es **cuándo** y **qué lo anticipa** |
| HP-007, corredores de vacío | Evidencia interna a favor de M5, con otro modelo de densidad |
| H-CLUSTER-NQ / H2 (08/09) | **Lección de escala (ATJ-18):** un borde de ±1 tick sobre un objeto de 60 dio un nulo falso |
| Atlas de absorción (24/09) | **Lección de geometría:** un control mal puesto fabricó una "barrera" |
| LUX-IMB (FVG/OG/VI, bloqueada) | Objeto parecido (hueco de 3 velas) pero distinto: acá es un empuje de varias barras. Hay que medir el solapamiento antes de declarar familias independientes |
| HFTZones | Zonas de otro detector. Sin cruce hasta registrar la familia |

---

## 12. Propuesta (decide Nico, P-86)

1. **Registrar la familia TBZ** con esta definición: los dos lados (CONT/ORIG), coordenadas relativas y ledger propio.
2. **Arrancar por E1**, el censo target-free en MES y ES pre-holdout: cuántas zonas hay por escala, cuánto duran, cuántas se censuran. Sin OK adicional.
3. **Después, E1b en exploración y E2 con manifiesto.** La primera pregunta es la del §5.4: ¿el riesgo de cruce baja con los contactos (M1) y sube con la penetración creciente o el volumen acumulado afuera (la observación de Nico)?
4. **Contrastar casos concretos con hora** (ATJ-18): cuando el detector esté, se corre sobre los casos que Nico marque en días **pre-holdout**, para verificar que el detector ve lo mismo que el ojo antes de medir agregados.

---

## 13. Addendum (24/09, tarde): corredores entre zonas HFT = el mismo objeto

Nico mostró dos capturas más de MES del **24/09 (holdout: el día ya está en la lista de exclusión)**:
- `HFTZonesNQPureV4` aplicado a MES: zonas densas con **huecos**;
- `HFTZonesESPureV2`: pocas zonas y fuertes.

**Lectura:**
- El hueco de ~7738–7740 (10:16–10:25) es una franja por donde el precio pasó **rápido**, no una franja que nunca visitó. Es una expansión vista como "ausencia de zona".
- Hay rechazos en el borde del hueco y la travesía llega después: el mismo fenómeno que §1.
- La zona fuerte del indicador de ES (7754–7755) actuó como **pared** dos veces: es el complemento del corredor.

**Consecuencia de diseño:**
1. **Unificar** corredor (HP-006/HP-007), zona de expansión y campo de densidad en **una sola familia**, con un solo objeto: franja de **baja permanencia** (tiempo y volumen negociado por nivel de precio en una ventana causal).
2. Para definir corredores sirve un detector **denso** (Nico tiene razón en preferir el de NQ antes que el de ES). Pero la densidad de `HFTZonesNQPureV4` en MES depende de parámetros calibrados para NQ, y su paridad NT8 es solo NQ (MES: `PARITY_ABSTAIN`). Por eso, **la medición usa la permanencia por precio calculada desde ticks** (sin parámetros de otro instrumento y comparable entre MES, ES y NQ). El indicador queda como representación visual.
3. **Chequeo target-free previo:** el solapamiento entre los huecos del indicador de NQ (y del perfil multiactivo `SCALED_FUNNEL_V1`) y las franjas de baja permanencia. Si coinciden, se valida la representación; si no, la diferencia es un hallazgo.
4. La pregunta central (§5.4) no cambia: el riesgo de pasar de rechazar a atravesar, según el estado.
