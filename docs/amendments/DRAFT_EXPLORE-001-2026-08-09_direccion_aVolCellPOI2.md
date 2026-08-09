# DRAFT — regla direccional de `aVolCellPOI2`

**Estado:** **BORRADOR. No adoptado. No sellado.** Requiere acto de Nico.
**Fecha:** 2026-08-09 · Outcome-free: **no se miró un solo resultado económico**.
**Origen:** aporte de Nico sobre la semántica del indicador, redactado por Claude.

> **Por qué es un borrador y no una propuesta cerrada.** La conclusión a la que
> llega este documento es que **no existe hoy una regla de signo único derivable
> de la semántica**. Lo que sí existe es una **orientación** target-free y un
> camino compatible con §5.3. Adoptar cualquiera de los dos es decisión de Nico.

---

## 1. Lo que aportó Nico

> *«Las zonas de ese indicador **no están pensadas para sugerir una dirección**.
> La dirección mayoritariamente se define según **la reacción que tenga el precio
> sobre estas zonas** o por **la dirección que presenta hacia ellas**.»*

Esa frase contiene tres cosas, y la spec las trata distinto.

## 2. Las tres, separadas

### 2.1 «No están pensadas para sugerir una dirección» — es el dato decisivo

§5.3 no pide *una regla direccional cualquiera*: pide una **«derivada de su
semántica»**. Si el indicador por diseño no sugiere dirección, un signo escrito
ahora **no se deriva de su semántica: se le impone desde afuera**. Eso es
precisamente lo que ese requisito existe para impedir.

### 2.2 «La reacción sobre estas zonas» — es posterior al toque

Es el **outcome**. §5.3 lo prohíbe sin ambigüedad: *«no se puede elegir fade o
break después de observar cuál gana»*. **No es utilizable para definir el signo.**

Puede ser una tesis válida si se declara **antes** de outcomes —y hoy todavía
estamos antes—, pero entonces es una **afirmación de mecanismo de Nico**, no algo
derivado del código.

### 2.3 «La dirección que presenta hacia ellas» — sí es utilizable

Es el lado de aproximación, y **ya existe en el kernel** como `ref_side`
(`avolcellpoi2.py:322-326`):

```python
s = 1 if close > z["upper"] else (-1 if close < z["lower"] else 0)
if s != 0:
    if z["ref_side"] == 0: z["ref_side"] = s          # se fija la 1ra vez
    elif s == -z["ref_side"]: reason = "close_through" # cambio de lado -> invalida
```

**Es target-free en la creación** (`ref_side=ref`, línea 364). La advertencia del
traspaso sigue vigente y es correcta: el valor **final** muta durante la vida de
la zona y exportarlo sería *lookahead*. **Sólo el de creación es admisible.**

## 3. El nudo: la orientación da el eje, no el signo

Saber que el precio se aproxima desde abajo dice **de qué lado estás parado**. No
dice qué es lo económicamente correcto. Y para una zona de concentración de
volumen, «reacción» admite **dos lecturas opuestas**:

| lectura | mecanismo | operación desde el mismo lado |
|---|---|---|
| la zona es **valor aceptado** | el precio tiende a **volver hacia ella** | seguir hacia la zona |
| la zona es **soporte/resistencia** | el precio tiende a **rebotar contra ella** | fade, alejarse de la zona |

Son **operaciones contrarias desde la misma aproximación**. La ambigüedad no la
resuelve `ref_side`.

Y no es una duda mía: la investigación del auditor ya la había registrado —

> *`aVolCellPOI2`. Una concentración de volumen puede representar aceptación,
> transferencia de inventario o simple actividad. **Puede sostener reversión
> alrededor de valor o continuación después de price discovery**; la dirección no
> surge del nombre y debe justificarse externamente.*

## 4. Lo que SÍ se puede declarar hoy

**Orientación target-free (`R-DIR-1`).** Cada evento de `aVolCellPOI2` lleva el
lado de aproximación `ref_side ∈ {−1, +1}` **tomado en la creación de la zona**,
nunca el final. Es derivable de la semántica, verificable en el código y no toca
outcomes.

Eso **no es todavía una regla direccional confirmatoria**: es el insumo que
cualquiera de ellas necesitaría.

## 5. Los dos caminos compatibles con §5.3

### A · Dos brazos como familia declarada

§5.3 lo autoriza explícitamente:

> *Probar fade y break como dos brazos es posible **sólo** si ambos quedan
> declarados como familia y **pagan su multiplicidad**.*

Con `R-DIR-1` fijando el eje, los dos brazos quedan bien definidos y ninguno se
elige mirando resultados. **Es el camino que no requiere inventar un mecanismo.**

Costo: duplica la multiplicidad de H2. Hay que recalcular `M_eff` y el MDE
resultante **antes** de sellar, y verificar que el margen medido de 1,60× lo
absorba.

### B · Tesis de mecanismo declarada por Nico

Si Nico afirma, **antes de cualquier outcome**, cuál de las dos lecturas del §3
sostiene el indicador, eso es un prior legítimo y §5.3 se cumple: la regla queda
congelada en E-R1 y no se eligió mirando resultados.

**Requisito:** la tesis debe enunciarse de forma **falsable y con mecanismo**, no
como preferencia. Por ejemplo, la forma —no el contenido, que lo pone Nico—:
*«la zona marca volumen aceptado; el precio que llega desde afuera tiende a X
porque Y»*.

**Yo no la escribo.** Cuál es la dirección económica de esas zonas es
conocimiento de mercado de Nico; si la redacto yo, estaría inventando un
mecanismo para llenar un casillero, que es el defecto que §5.3 persigue.

### C · No adoptar ninguna

§5.3 fija el default: `aVolCellPOI2` **sigue como fenómeno exploratorio, no como
hipótesis confirmatoria**. EXPLORE-001 corre con `BigTrap2` solo. Autorizado por
§6.4 —*«completar tres no justifica admitir una hipótesis mal definida»*— y ya
anticipado por el traspaso: *«menos hipótesis, no menos camino»*.

## 6. Control obligatorio antes de adoptar A o B

**Balance de `ref_side` en la creación**, outcome-free.

Si la distribución sale muy desbalanceada —del orden de 90/10— la regla
produciría casi siempre el mismo signo y **sería una apuesta direccional
encubierta, no una regla que discrimine**. Si sale razonablemente pareja, el eje
informa de verdad.

**No corrido todavía.** Requiere exponer `ref_side` en el dict de eventos —hoy no
se emite (`avolcellpoi2.py:227-233`)— y una pasada del kernel. Es el mismo tipo
de cambio que `1f0f62d`: toca sólo `events`, no la línea del CSV, así que **la
paridad no se ve afectada** (verificado de forma independiente: `parity.py`
consume `zones`, no `events`; `grep zone_id parity.py` → 0).

## 7. Recomendación — ~~A~~ **RETIRADA. Ver la decisión.**

> **Esta sección quedó obsoleta el mismo día.** Recomendaba **A**. Al ir a buscar
> el estimando de §5.1 para calcular la multiplicidad, resultó que los dos brazos
> **no son dos hipótesis**: con la fricción restada dentro de cada evento,
> `neto_fade + neto_break = −5,536` constante, así que como máximo uno puede ser
> positivo y alguno lo es **si y sólo si** `|E[r]| > 2,768`. Eso **es** la prueba
> bilateral que §5.3 prohíbe.
>
> Camino adoptado: **C**.
> → [`DECISION_2026-08-09_direccion_y_alcance_de_EXPLORE-001.md`](../research/DECISION_2026-08-09_direccion_y_alcance_de_EXPLORE-001.md)

El resto del documento —§1 a §6, la separación de las tres afirmaciones de Nico,
`R-DIR-1` y el control de balance— **sigue vigente**. Lo único retirado es esta
recomendación.

**B** sigue disponible si Nico enuncia una tesis de mecanismo genuina y previa.

**C** es lo adoptado, y con la lectura del chat externo dejó de ser una etiqueta
vacía: tiene programa (curva de respuesta, MFE/MAE, vida media, sin dirección).

## 8. Advertencia de momento

Ya se midieron y publicaron las tasas de los tres candidatos. **Redactar ahora una
regla direccional para el único que la necesita es hacerlo con esa curva a la
vista.** Es la misma razón por la que la spec dejó afuera a `AACloseOpenDiffs`.

Lo que protege el procedimiento es que **no se ha visto un solo outcome**: las
tasas son outcome-free por construcción y el holdout no se tocó. Por eso adoptar
A o B hoy sigue siendo pre-outcome y legítimo — pero exige **enmienda fechada,
congelada en E-R1 antes de la primera corrida económica**, y este documento no
la reemplaza.
