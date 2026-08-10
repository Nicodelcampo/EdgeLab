# SESGO DE DISEÑO — el toque como única entrada concebida

**Fecha** 2026-08-10 · **Detectado por** Nico, por objeción directa
**Alcance** toda la evidencia acumulada sobre BigTrap2 hasta `8106351`
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Severidad** estructural — no invalida ninguna medición, invalida el **alcance
de lo que las mediciones permiten concluir**

---

## 0. La objeción, textual

> *«Lo que a mí no me parece bien es buscar edges o hacer análisis solo
> basándose en los toques del precio a las zonas, porque quizás hay edges que no
> nacen de tocarlas, sino de otro tipo de entradas que a pesar de tener al
> indicador como condición, no necesariamente se tienen que hacer sobre la zona
> cuando el precio la toca.»*

Es correcta. Y lo que sigue documenta que **no es una intuición: es verificable
en el repositorio, con fecha y commit.**

---

## 1. Enunciado del sesgo

Toda la evidencia producida sobre BigTrap2 —el censo, la curva de excursión, el
sello E-R1, H1 y su acta de muerte— está condicionada a **un único tipo de
evento: el primer toque del precio a la zona.**

Ese condicionamiento **nunca se declaró como una decisión**. Entró como premisa
de otra decisión, se volvió el camino por defecto, y todas las mediciones
posteriores lo heredaron sin volver a mencionarlo.

**Lo que el sesgo NO hace:** ninguna medición está mal. El censo de 15.577
primeros toques es correcto. La curva de excursión es correcta. H1 se ejecutó
según su sello y murió por regla. Nada de eso se retracta.

**Lo que el sesgo SÍ hace:** convierte «BigTrap2 no produjo un edge» en una
afirmación **mucho más chica de lo que parecía** — a saber, «una regla de
entrada al toque, sobre BigTrap2 con parámetros por defecto, no produjo un edge».

---

## 2. La cadena de propagación, con commits

| fecha | commit | qué pasó |
|---|---|---|
| **2026-07-24** | `af48609` | **Se construye la API de features de zona**: `get_zones` / `materialize_features`. Trata la zona como **estado continuo** alineado a barras, as-of, sin look-ahead. |
| pre-08-05 | — | El censo vigente (`post_sepmin.py:170`) opera sobre **creaciones de zona** (`z["created_ms"]`). Marco de **evento en la creación**. |
| **2026-08-04** | — | Enmienda `EXPLORE-001-2026-08-04_first_touch_decongestion.md`. Declara la entrada primaria en el primer toque y **degrada** el censo de creaciones. |
| **2026-08-05** | `fc92a41` | Censo de primeros toques. D3 lo declara **autoritativo**. |
| 2026-08-06 → 08-09 | `368c171`, `3d0981f`, `90ab6cf` | Curva de excursión, PRED-007, `f` con ambos filtros — **todo sobre primeros toques**. |
| 2026-08-09 | sello E-R1 v0.3.1 | Congela una población de primeros toques. |
| 2026-08-09 | `889c048`, `5f1b65d` | H1 medida y muerta, sobre primeros toques. |

**El marco alternativo existía trece días antes que el marco que se adoptó.**

---

## 3. El instante exacto en que el alcance se filtró

La enmienda del 2026-08-04, citada por D3 §1:

> *«EXPLORE-001 define la entrada primaria en el primer toque posterior. La
> restricción representa capacidad de exposición, por lo que debe operar sobre el
> instante de entrada y no sobre el instante en que nació una zona todavía no
> operable.»*

> *«Las tasas de creaciones siguen siendo **diagnósticas**. H1–H3 sólo pueden
> congelarse con tasas producidas por **esta** población y **esta** política.»*

### El razonamiento de la enmienda es correcto — y condicional

Lo que la enmienda decide es la **semántica de `sep_min`**, y decide bien: *si la
entrada es el toque, entonces la descongestión —que representa capacidad de
exposición— tiene que aplicarse en el instante de entrada, no en el nacimiento
de la zona.* Impecable dentro de su alcance.

**El defecto es que el antecedente del condicional se perdió.**

```
lo que la enmienda establece:   SI la entrada es el toque, ENTONCES descongestionar en el toque
lo que quedó operando:          la entrada es el toque
```

Una premisa dentro de un condicional pasó a ser **axioma de todo el programa**.
Y la segunda cita selló la puerta: el marco alternativo —creaciones de zona—
quedó reclasificado como «diagnóstico», con lenguaje de autoridad («sólo pueden
congelarse con **esta** población»). A partir de ahí, medir cualquier otra cosa
parecía salirse del protocolo.

Nadie decidió que las otras entradas no sirvieran. **Nadie las evaluó.**

---

## 4. La evidencia dura: la infraestructura correcta existe y research nunca la usó

`edgelab/bridge/features.py:21`:

```python
DEFAULT_FEATURES = ("inside_zone", "distance_to_nearest_zone",
                    "active_zone_count", "zone_age", "nearest_zone_side")
```

`materialize_features()` alinea zonas a la serie de barras **as-of, sin
look-ahead**. Es el marco **zona-como-estado**: en cada barra hay un valor, sin
que el precio tenga que tocar nada.

Búsqueda de sus consumidores en todo el repositorio
(`materialize_features|get_zones_df|active_zone_count|distance_to_nearest_zone`):

```
tests/bridge/test_features.py      <- su propio test
tools/demo_vectorbt_zones.py       <- un demo
edgelab/bridge/features.py         <- el propio archivo
```

**Cero archivos de research.** Toda la línea H1 se construyó por un camino
paralelo hecho a mano —censo de toques → curva → `f_ambos_filtros` → runner—
con la API de estado sin usar al lado.

---

## 5. Por qué el aparato de auditoría no lo detectó — y esto es lo importante

Este proyecto audita con severidad poco común: hashes de parquets, manifiestos
con guardia de angostamiento, conjuntos de dependencias congelados, sellos
preregistrados, gates con causa raíz obligatoria, incidentes en cuarentena en
vez de borrados. En esta sesión sola se cazaron una quincena de defectos, varios
encontrados por auditoría adversaria.

**Nada de eso podía cazar esto.**

> **Todo lo que se declaró fue auditado sin piedad. Lo único que nadie auditó es
> lo que nadie escribió como decisión.**

Un gate compara lo declarado contra lo observado. Si la elección de la población
nunca se escribió como *elección* —con alternativas, con justificación, con
condición de refutación— no hay nada contra qué comparar. El sesgo fue invisible
**por construcción del aparato**, no por descuido en su aplicación.

### Cuarto miembro de la familia de fallas de esta sesión

Las tres ya catalogadas:

1. *un gate que no puede detectar aquello para lo que existe*
2. *una afirmación en el texto que el código no tiene*
3. *dos notaciones que se leen igual*

Y ahora:

4. **un supuesto que nunca se escribió como decisión, y que por lo tanto nunca
   se pudo revisar**

Es el más peligroso de los cuatro, porque los tres primeros fallan ruidosamente
cuando se los ejercita. Éste **no falla nunca**: produce mediciones correctas
sobre la pregunta equivocada, con toda la trazabilidad en orden.

---

## 6. Qué queda en pie y qué hay que releer con el alcance corregido

### Queda en pie, sin cambios

- El acta de muerte de H1 y su veredicto. **H1 no se reabre.**
- El hallazgo estructural: primer toque ≈ muerte de zona en el 92,9 %; 0 de 394
  close-throughs ganan; la invalidación sólo se dispara en contra.
- Las cifras de potencia: `SE(HAC)` 1,0903, *design effect* 1,14, MDE 6,58 ticks
  brutos.
- El firewall del holdout, intacto.

### Hay que releer con el alcance corregido

| lo que se dijo | lo que corresponde decir |
|---|---|
| «H1 murió» | correcto, sin cambios |
| «BigTrap2 no produjo edge» | **una regla al toque** sobre BigTrap2 por defecto no produjo edge |
| «el filtro T=34 define la población» | define la población **de toques**; no dice nada de la población de zonas |
| «la fuerza bruta debe barrer los 12 parámetros» | insuficiente: barrer parámetros **dentro de una sola familia de eventos** sigue siendo una búsqueda angosta |

### El dato que hoy no existe y debería

Se midieron **15.577 primeros toques**. **Nunca se contó cuántas zonas nacen.**
No se sabe qué fracción de las zonas se toca alguna vez, ni cuántas mueren por
edad sin haber sido tocadas nunca. Es decir: **se midió un numerador sin
denominador durante todo el programa.** Si la mayoría de las zonas nunca se
toca, la población de H1 era una minoría no representativa del objeto que el
indicador produce.

> **MEDIDO EL MISMO DÍA (F0.2) — la hipótesis de este párrafo es FALSA.**
> Hay **15.947 zonas** y **el 97,9 % se toca**. No había ninguna mayoría
> intocada. La población de H1 sí era una minoría (2,7 % de las zonas), pero por
> el filtro de excursión `T=34`, no por falta de toques.
>
> Lo que el censo sí encontró es otra cosa, y más grande: de **48.768 eventos de
> toque** totales, H1 midió sólo los primeros — **32 %**. Los **33.160**
> restantes (68 %) nunca se midieron. Y la altura mediana de zona es **1 tick**,
> lo que explica la muerte de H1 mecánicamente.
>
> Ver `F0.2_CENSO_ZONAS_RESULTADO_2026-08-10.md`. El párrafo se conserva sin
> editar: una hipótesis equivocada que la medición corrigió es evidencia de que
> el método funciona, no algo que haya que tapar.

---

## 7. Corrección permanente de método

Se adopta como regla, para toda población futura:

> **Antes de congelar una población hay que enumerar por escrito el espacio de
> eventos y estados del que se la extrae, y justificar la elección con una
> condición de refutación.** Una población elegida sin alternativas escritas no
> es una elección: es una herencia.

Esto extiende el campo obligatorio «cómo podría refutarse» de las plantillas
generadoras: hasta hoy se aplicaba a la hipótesis; a partir de acá se aplica
también **a la población sobre la que la hipótesis se define**.

---

## Aporte al referente

El sesgo no reduce la distancia al edge por sí mismo, pero corrige una
subestimación grave del espacio de búsqueda: durante todo el programa se creyó
estar evaluando un indicador cuando se estaba evaluando **una regla de entrada**
entre varias posibles, y el marco alternativo —la zona como estado continuo, con
potencia estadística mucho mayor— estaba construido y sin usar desde el
2026-07-24. Reconocerlo evita gastar el presupuesto de multiplicidad barriendo
parámetros dentro de la familia de eventos equivocada, que era exactamente el
próximo paso planificado.
