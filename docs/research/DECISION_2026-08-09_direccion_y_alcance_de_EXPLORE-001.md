# Decisión — el camino C, y por qué A estaba mal

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado · Sin NT8
**Autoriza:** Nico — *«avancemos por el camino que consideres mejor considerando
el referente del proyecto»*.
**Corrige:** `DRAFT_EXPLORE-001-2026-08-09_direccion_aVolCellPOI2.md` §7.

---

## 1. Corrección

Ayer recomendé el **camino A** —*fade* y *break* como dos brazos declarados—.
**Estaba mal.** Al ir a buscar el estimando exacto para calcular la multiplicidad,
resultó que esos dos brazos **no son dos hipótesis**: son una prueba bilateral.

Es lo que §5.3 prohíbe. Recomendé el camino prohibido creyendo que era el
autorizado.

## 2. El argumento, con el estimando en la mano

§5.1 fija el estimando primario:

```
expectativa neta por evento elegible, en ticks
fricción round turn = 2,768 ticks, restada DENTRO del resultado de cada evento
umbral económico del estimando neto = 0 ticks
```

Los dos brazos entrarían en **el mismo punto** —al completarse la excursión, en
`k_T`— sobre **los mismos eventos**, en direcciones opuestas. Si `r` es el retorno
con signo de esa ventana:

```
neto_fade   =  r − 2,768
neto_break  = −r − 2,768
────────────────────────
suma        =    −5,536      ← constante, negativa, siempre
```

De ahí salen dos cosas mecánicas, no empíricas:

1. **Como máximo un brazo puede ser positivo.** Nunca los dos.
2. **Alguno es positivo si y sólo si `|E[r]| > 2,768`.**

Entonces «correr los dos brazos» **es** contrastar `|E[r]| > 2,768`. Una prueba
bilateral con banda de fricción. Y §5.3 dice, sobre esto exactamente:

> *una prueba bilateral **no concede gratuitamente** la dirección de trading.*

Un resultado VIVE en uno de los brazos no diría *«el mecanismo es fade»*: diría
*«la media condicionada no es cero»*, y el signo lo habría elegido el dato. Que es
la definición de lo que §5.3 impide.

### 2.1 Por qué el permiso de §5.3 no rescata a A

§5.3 sí contempla los dos brazos:

> *Probar fade y break como dos brazos es posible **sólo si** ambos quedan
> declarados como familia y pagan su multiplicidad.*

**«Sólo si» es condición necesaria, no suficiente.** Declarar la familia y pagar
multiplicidad es un requisito adicional; no deroga la prohibición bilateral, que
está en el mismo párrafo y sigue vigente. Pagar la multiplicidad no compra el
permiso.

> **Marcado para el referente.** Esta lectura de «sólo si» es **mía** y es
> portante: si el auditor la lee como condición suficiente, A vuelve a estar
> disponible y la decisión de este documento cae. **Queda señalado, no resuelto
> por mí.**

### 2.2 Y la propia spec ya lo condenaba, en otras palabras

`ESPEC_TEST_EXPLORE-001.md` §3.3, regla de selección de candidatos:

> *Preferir **mecánicamente distintas** — no tres variantes de zonas de volumen,
> que **inflan `M_eff` sin diversificar**.*

Dos brazos exactamente anticorrelados son el **caso extremo** de eso: correlación
−1, diversificación cero, y aun así consumen presupuesto. La regla ya existía; yo
no la había cruzado con §5.3.

## 3. Decisión: camino C

`aVolCellPOI2` **no entra como hipótesis confirmatoria de edge.** Sigue como
fenómeno exploratorio, que es el default que §5.3 fija cuando no hay regla
direccional defendible.

**No es un descarte del indicador.** Es un descarte de su rol en E-R1.

## 4. El alcance que se sigue, y no es cómodo

§5.3 cubre *«`aVolCellPOI2`, `Gaps2`, `HFTZones2` y **cualquier zona sin dirección
intrínseca**»*. `VolTicksPOC2` es una zona sin dirección intrínseca: **queda
cubierto por la misma cláusula.**

Y §6.4 fijaba el tercer candidato entre `HFTZones2` y `VolTicksPOC2` — los dos
caen, uno por el invariante y el otro por la dirección.

| | indicador | censo | invariante | dirección | rol en E-R1 |
|---|---|---|---|---|---|
| H1 | `BigTrap2` | 9,08/ses · 201 ses | ok | **nativa** | **confirmatoria** |
| — | `aVolCellPOI2` | 6,71/ses · 177 ses | ok | no | exploratorio |
| — | `VolTicksPOC2` | 3,47/ses · 199 ses | ok | no | exploratorio |
| — | `Gaps2` | — | **falla** | no | fuera |
| — | `HFTZones2` | — | **falla** | no | fuera |
| — | `AACloseOpenDiffs` | — | — | — | fuera por §4.1 |

> **De los seis candidatos, `BigTrap2` es el único con dirección nativa.**
> EXPLORE-001 corre con **una** hipótesis confirmatoria.

Está autorizado —§6.4: *«completar "tres" no justifica admitir una hipótesis mal
definida»*— y anticipado por el traspaso: *«menos hipótesis, no menos camino»*.
Pero conviene decirlo sin suavizar: **se pierde la diversificación mecánica que
§3.3 buscaba.** El resultado, sea cual sea, hablará de `BigTrap2`, no de una clase
de fenómeno.

## 5. Multiplicidad — declarada, no aprovechada

Presupuesto declarado y pagado por el barrido de resolución:

```
M_eff 21,2 → ~106    z 3,041 → 3,50    MDE +11,8%    margen medido 1,60×
```

Correr **una** hipótesis en vez de tres es **conservador** respecto de eso. La
tentación es recalcular un `M_eff` menor y quedarse con un MDE mejor.

**No se hace.** Es el mismo principio que la spec ya aplicó a Bonferroni:

> *el costo real es menor — **anotado, no aprovechado**.*

El presupuesto declarado se mantiene. La holgura se registra y no se gasta.

## 6. Qué hace `aVolCellPOI2` ahora

El camino C dejaba de ser una etiqueta vacía tras leer el chat externo. Su
programa, **outcome-free hasta que Nico y el auditor autoricen outcomes**:

- curva de respuesta `E[R(τ)]` por horizonte, sin dirección;
- MFE / MAE y sus cuantiles;
- vida media de la respuesta;
- `ref_side` de creación como **estratificador**, no como signo.

Eso caracteriza el fenómeno sin afirmar un edge, que es exactamente lo que §5.3
permite a un candidato sin dirección. **No está autorizado todavía** — requiere el
mismo acto que cualquier outcome.

## 7. `R-DIR-1` queda igual, y sirve

Exportar `ref_side` **de creación** en el dict de eventos sigue siendo correcto y
barato: es target-free, no toca la paridad (`parity.py` consume `zones`, no
`events`) y es el insumo del §6. **Ya no es para elegir un signo.** No lo
implemento hoy: no bloquea nada.

## 8. Qué decido y qué no

**Decido** el camino C y el alcance del §4, bajo la autorización explícita de
Nico.

**No decido** —y marco para el referente— la lectura de «sólo si» del §2.1, de la
que depende todo lo anterior.

**No aprovecho** la holgura de multiplicidad del §5.

**No toco** outcomes, holdout ni NT8.
