# Decisión — condición de validez, orden de composición, y el margen

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado
**Autoriza:** Nico — *«no hay más Codex. Razoná vos sobre las 3 cosas y decidilas
por tu cuenta en base a la info que tenés y en base al referente del proyecto»*.

> **Decido contra una parte ausente.** Codex agotó su cuota antes de defender su
> posición. Escribo el argumento completo de cada decisión para que se pueda
> revertir leyéndolo, y **sus números quedan en el registro**, no borrados.

---

## 1. El hallazgo que resuelve las dos primeras juntas

Al razonarlas por separado parecían dos preferencias discutibles. **No lo son: se
traban entre sí por look-ahead.**

- **Mi condición:** vale si el **primer toque** de la zona es posterior a la
  excursión (`i_toque > k`).
- **La de Codex:** vale si existe **algún reingreso** posterior a la excursión
  (`j > k`), sea o no el primer toque.
- **Orden B:** filtrar por validez y **después** decongestionar.

Ahora combinemos.

**Bajo mi condición, en el instante del primer toque la excursión ya ocurrió** —
es literalmente lo que la condición exige. Así que al entrar ya sabés que el
evento es válido. **Orden B es realizable en tiempo real.**

**Bajo la de Codex, no.** Si el primer toque precede a la excursión, en ese
instante todavía no sabés si habrá un `j` válido más adelante. Filtrar por validez
antes de decongestionar exigiría **conocer el futuro**.

> **La condición de Codex combinada con el orden B es look-ahead.** No es una
> preferencia entre dos lecturas razonables: una de las dos combinaciones no es
> implementable.

## 2. Decisión 1 — la condición de validez: **la mía**

Además del look-ahead, hay un argumento de coherencia con la enmienda congelada.

La enmienda fija el ancla de `sep_min` en `first_touch_ms` y justifica: *«la
restricción representa **capacidad de exposición**, por lo que debe operar sobre
el instante de entrada»*.

| lectura | ancla de `sep_min` | entrada real | ¿coinciden? |
|---|---|---|---|
| **mía** | primer toque | primer toque | **sí** |
| Codex | primer toque | reingreso `j` | **no** |
| *(tercera)* | reingreso `j` | reingreso `j` | sí, pero **es otra población** |

Bajo la de Codex el ancla y la entrada son **instantes distintos**: se mediría la
capacidad de exposición en un momento en el que no se toma exposición. Eso rompe
la justificación misma de la enmienda.

La tercera lectura es coherente, pero redefine la población y **exigiría una
enmienda nueva**. No la tomo por mi cuenta.

Y §3.1 fija el orden temporal sin ambigüedad: *«el precio se aleja al menos `T`
ticks **y luego** produce el desenlace»*. La condición de Codex admite eventos
donde la entrada precede al setup.

**`f = 2,13 eventos/sesión`.**

> **Nota sobre el interés.** Mi condición da el número **más bajo** —2,13 contra
> 3,64— o sea peor potencia y una hipótesis más difícil de pasar. La decisión va
> en contra del resultado que me conviene.

## 3. Decisión 2 — el orden de composición: **B**

La misma frase de la enmienda lo resuelve. Su motivo para pasar de creaciones a
primeros toques fue que `sep_min` no debe operar *«sobre el instante en que nació
una zona **todavía no operable**»*.

**Un primer toque sin excursión válida no es una entrada**: no es un evento de la
hipótesis. Dejar que consuma la ventana de 120 minutos y **suprima una entrada
real** repite exactamente el defecto que la enmienda se escribió para corregir,
un escalón más arriba.

Y el §1 lo confirma: con la condición decidida, el orden B **no es look-ahead**.

El orden A es el que produce el absurdo operativo: 71 eventos en 201 sesiones
—0,35/ses— porque el greedy conserva el primero de cada ventana y ese primero casi
nunca es uno de los raros con excursión válida. **No está midiendo la hipótesis:
está midiendo con qué frecuencia la hipótesis coincide con el primer toque de cada
ventana de dos horas.**

## 4. Decisión 3 — el margen: uso la definición del spike-in, y registro la otra

Recordatorio de que este punto ya me hizo equivocar una vez hoy.

| fuente | dice | ¿verificable? |
|---|---|---|
| `docs/spike_in/MDE_EXPLORE-001.md` | margen = **fricción/MDE**; 7,0× a f=10 | **sí** — reproduce en sus 4 filas |
| `docs/ESPEC_TEST_EXPLORE-001.md:365` | *«el margen medido a f=10 es 1,60×»* | **no** — sin fuente ni derivación |

El `1,60×` no se reconcilia con nada: ni con el costo de multiplicidad declarado
en su propia línea —`MDE +11,8 %` daría 6,2×— ni con las tres hipótesis
preregistradas del spike-in —MDE 0,32 a f=10, o sea 8,45×—.

**Uso la definición del spike-in**, porque es la única aritméticamente verificada
contra su propia tabla. El `1,60×` queda **registrado como discrepancia sin
explicar**.

### 4.1 Y la decisión no depende de cuál gane

Con `f = 2,13` decidida:

```
MDE ~ 0,794                          margen = 2,768 / 0,794 = 3,49×
MDE ~ 0,888  (+11,8 % del barrido)   margen = 2,768 / 0,888 = 3,12×
```

**Pasa con y sin el costo de multiplicidad del barrido de resolución.** La celda
`BigTrap2 · T=34` **no es ciega**. La discrepancia del `1,60×` hay que resolverla,
pero no bloquea esto.

## 5. La cuarta, que NO decido: el sello

§7 Paso 5 exige *«adjudicar E-R1 mediante **acto humano**»*. No sello, y no es
formalismo: es la única barrera que queda entre esta cadena de decisiones —cuatro
de ellas mías, tomadas hoy, dos de ellas corrigiendo errores míos anteriores— y
una corrida con outcomes.

## 6. Y la que queda abierta de verdad: salida y censura

E-R1 §6 la dejó pendiente y **sigue pendiente**. Es el último parámetro libre.

No la invento. Lo que sí hago es acotar el espacio y recomendar:

**Recomendación — cero parámetros nuevos.** Salir por muerte de la zona
(`ended_ms` del `lifecycle`, que ya existe y está bajo `PARAM_SPEC`) o fin de
sesión CT, lo que ocurra primero, con la censura declarada y reportada. Cualquier
horizonte fijo —«N barras después de la entrada»— **introduce un parámetro nuevo
después de haber visto la tabla de frecuencias**, que es precisamente el tipo de
grado de libertad que la disciplina del proyecto persigue.

**Decisión de Nico o del referente.** Yo ya tomé cuatro hoy.

## 7. Resumen ejecutable

| # | qué | decisión | fundamento principal |
|---|---|---|---|
| 1 | condición de validez | **primer toque posterior a la excursión** | la alternativa + orden B es **look-ahead** |
| 2 | orden de composición | **B** | la enmienda: `sep_min` no debe operar sobre lo no operable |
| 3 | definición de margen | **fricción/MDE** (spike-in) | única verificada aritméticamente |
| — | **`f` de H1** | **2,13/sesión** | margen **3,49×**, no ciega |
| 4 | sello de E-R1 | **no lo tomo** | §7 Paso 5: acto humano |
| 5 | salida y censura | **abierta**, con recomendación | último parámetro libre |
