# EXPLORE-001 — Decisiones y especificación consolidada del gate

**Versión:** DRAFT v0.3
**Fecha:** 2026-08-07
**Estado:** **no sellada; no ejecutable sobre outcomes**
**Referente:** `docs/NORTH_STAR.md`
**Ámbito:** diseño outcome-free del primer gate real de EdgeLab
**Autoría de las decisiones:** el auditor. Registrado por Claude sin alterar el
contenido normativo; ver §11 para lo único que se agrega.

Esta especificación consolida las decisiones vigentes de EXPLORE-001 después de
completar la curva de diseño sobre ticks, auditar su procedencia y detectar
eventos cuyo supuesto alejamiento ya estaba cumplido cuando comenzaba la ventana.

**No constituye evidencia de edge, no autoriza outcomes, no abre el holdout y no
adjudica ninguna hipótesis confirmatoria.**

## 0. Documento canónico y procedencia

### 0.1 Decisión

Ninguna de las dos especificaciones anteriores seguirá gobernando directamente.
Se crea como documento canónico:

```
docs/predictions/ESPEC_TEST_EXPLORE-001_v0.3.md
```

Esta versión toma como **base sustantiva** `docs/ESPEC_TEST_EXPLORE-001.md`,
porque es la más reciente e incorpora: MDE y factibilidad económica; fricción
real de 2,768 ticks; régimen de frecuencia; tres hipótesis; reglas
VIVE/MUERE/GRIS; multiplicidad; replicación; régimen de signo.

Aquella versión quedó desactualizada después de la curva de 201 sesiones y
todavía declara pendiente una tasa de señales que **ya fue medida**.

También **recupera** de `docs/predictions/ESPEC_TEST_EXPLORE-001.md` las reglas
que siguen siendo válidas: un evento por zona; primer evento posterior a la
disponibilidad; prohibición de pseudo-replicar toques; separación entre medición
inferencial y análisis descriptivo; resguardo de la dependencia por sesión;
prohibición de rescatar un global negativo mediante estratos.

### 0.2 Estado de los documentos anteriores

Los dos documentos anteriores se conservan como **registros históricos** y
reciben un encabezado que indica que están SUPERSEDED para trabajo futuro por
esta versión. **No se borran ni se reescribe retroactivamente su contenido.**

### 0.3 Regla de gobierno

A partir de la creación de v0.3: toda decisión futura de EXPLORE-001 parte de
v0.3; una modificación material exige una **enmienda fechada**; ningún borrador
anterior puede invocarse para reemplazar una regla de v0.3; v0.3 seguirá siendo
DRAFT hasta cerrar E-R1; **sólo una decisión humana explícita** puede cambiarla
a SEALED.

## 1. Objeto de EXPLORE-001

EXPLORE-001 busca determinar si alguno de los mecanismos candidatos produce una
expectativa **económicamente operable, neta de fricción y distinguible del
ruido**, sin utilizar el holdout para diseñar la hipótesis.

El proceso se divide en cuatro etapas que **no pueden mezclarse**:

1. **Diseño outcome-free** — frecuencia, cobertura, descarte, disponibilidad y
   contaminación de eventos.
2. **Pre-registro E-R1** — candidatos, umbrales, dirección, estadístico,
   multiplicidad y reglas de muerte.
3. **Research outcomes** — ejecución conjunta de las hipótesis selladas.
4. **Replicación y holdout** — únicamente para hipótesis que sobrevivan el
   research bajo las reglas predefinidas.

**La curva de diseño pertenece exclusivamente a la primera etapa.**

## 2. Adjudicación de la curva de diseño

### 2.1 Identidad

```
diag/tasa_senales/curva_excursion_ticks.json
sha256: 76e1c8767553ff7f74a80dec33c5adfc38293e76effe640c6a6ab8f18af07e66
commit de emisión: dfff4fd
```

Condiciones: 201 sesiones de research; cuatro contratos de 6E; cinco indicadores
elegibles; medición sobre ticks; firewall en 2026-06-30 22:00 UTC;
`outcomes_accessed=false`; sin lectura del holdout; orden reproducible por
`(ts_ns, sequence_de_archivo)`.

### 2.2 Alcance exacto de la adjudicación

```
ACEPTADA COMO MAPA DE DISEÑO OUTCOME-FREE
NO ADJUDICADA COMO EVIDENCIA DE EDGE
```

**Permite:** usar la frecuencia por indicador y umbral; identificar regiones
ciegas o excesivamente frecuentes; diseñar una grilla confirmatoria por
indicador; calcular el MDE correspondiente al `f` real; seleccionar mecanismos
candidatos sin mirar outcomes; producir un censo corregido de eventos elegibles.

**No permite:** afirmar rentabilidad; elegir dirección mirando resultados;
elegir el umbral con mejor P&L; abrir outcomes; sellar E-R1 automáticamente;
abrir el holdout; declarar VIVE o MUERE ninguna hipótesis.

### 2.3 Condiciones y reservas aceptadas

#### A. No existe un umbral global

La curva demostró que un único `T` no coloca a todos los indicadores en un
régimen comparable. Por lo tanto: **`T` se define por indicador**, y queda
prohibido imponer un `T` global por conveniencia.

#### B. Los umbrales bajos mezclan dos eventos

La curva publicada cuenta conjuntamente (i) una excursión que ocurre **después**
de que la zona está disponible y (ii) un estado que **ya estaba** fuera del
umbral en el primer tick disponible. La segunda situación no demuestra una
ruptura posterior a la existencia de la zona.

Por eso la curva completa se acepta como **mapa descriptivo**, pero antes de
sellar candidatos se debe **recalcular la frecuencia de las celdas
seleccionadas** bajo la definición de evento de §3. No hace falta repetir toda
la curva: alcanza un recuento outcome-free de las celdas candidatas, con la
misma población y el mismo firewall.

#### C. El split por clase de kernel se mantiene

```
bar_close:    available_ns = bar_end[created_bar]
tick_create:  available_ns = (created_ms + 1) * 1_000_000
```

La medición original **documentó su muestra y definición**: diez días de
`6E 03-26`, contando **cualquier** caso con `created_ms > bar_end[created_bar]`.
Dio **99 %** para `Gaps2` y **97 %** para `HFTZones2`, con medianas de **21,5** y
**27,5** segundos.

Una **réplica** sobre ocho sesiones de `6E 09-26`, bajo la misma definición,
obtuvo **100 %** y **96,4 %**, con medianas de **27,7** y **28,2** segundos. Las
fracciones y el orden de magnitud replican en otro contrato y trimestre.

Con un umbral material mayor a un segundo, los valores son **96,7 %** y
**92,9 %**, mientras los tres controles `bar_close` caen a **0,0 %**.

**El split por clase queda aceptado.** La diferencia de aproximadamente seis
segundos en el p50 de `Gaps2` se registra como variación entre períodos y **no se
explica sin evidencia adicional**.

#### D. Equivalencia de workers

Aceptada: 12 campos de resultado, seis unidades (contrato, indicador), igualdad
exacta, artefactos y verificador versionados. La memoria se expresa sin
ambigüedad:

```
1 worker:  1925 MiB ≈ 1,88 GiB
2 workers: 2734 MiB ≈ 2,67 GiB
```

Son las mismas mediciones en unidades binarias distintas. Es operativo y **no
cambia ninguna frecuencia**.

#### E. El artefacto emitido es inmutable

El JSON original no se reescribe porque modificarlo invalidaría su hash. Todas
las correcciones de interpretación se agregan mediante: esta especificación;
actas fechadas; verificadores versionados; artefactos derivados con nueva
identidad.

## 3. Definición del evento y tratamiento de `k_T == 0`

### 3.1 Pregunta causal mínima

La hipótesis de excursión pregunta si, **después de que la zona existe y puede
ser conocida**, el precio se aleja al menos `T` ticks y luego produce el
desenlace definido. Esto exige orden temporal:

```
zona disponible
 → precio todavía no cumplió la excursión T
 → cruce posterior del umbral T
 → desenlace posterior
```

Si el primer tick de la ventana ya está a `T` ticks o más del borde, el cruce
**no fue observado después de la disponibilidad**: es una condición inicial
preexistente.

### 3.2 Definición formal

Sea `i0` el primer tick estrictamente posterior a `available_ns`. Sea `k_T` el
índice relativo del primer tick que alcanza un alejamiento de al menos `T` ticks
desde la banda.

```
k_T > 0    →  excursión válida para la hipótesis primaria

k_T == 0   →  estado inicial ya externo
              NO es ruptura primaria
              NO habilita un retorno primario
```

Para un retorno válido debe cumplirse **`k_T > 0` y `j_retorno > k_T`**. No
alcanza con que el precio vuelva a la banda desde una posición que ya estaba
fuera al comenzar la ventana.

### 3.3 Motivo de la decisión

Contar `k_T == 0` como ruptura presenta tres problemas: atribuye a la zona un
movimiento ocurrido **antes** de que estuviera disponible; convierte una
condición inicial en un evento; permite declarar «retorno» sin haber observado
una excursión posterior.

En los indicadores `bar_close`, el precio tuvo parte o toda la barra creadora
para alejarse antes de que la zona pudiera utilizarse. A `T=1`, esto afecta
aproximadamente entre **40 % y 60 %** de las zonas medidas.

**La exclusión no se adopta porque perjudique o favorezca un resultado:** se
adopta **antes de mirar outcomes** y por la semántica temporal del evento.

### 3.4 Destino de los casos excluidos

Los casos `k_T == 0` **no se borran ni se ocultan**. Se reportan como arquetipo
descriptivo separado: **`ya_fuera_al_quedar_disponible`**.

Para cada indicador, contrato, sesión y `T` deben publicarse: zonas elegibles;
excursiones válidas con `k_T > 0`; estados iniciales `k_T == 0`; retornos válidos
posteriores; descartes por falta de tramo; descartes por reloj o clase; tasa
corregida por sesión.

### 3.5 Hipótesis distinta, no rescate

La posibilidad de que una zona nazca detrás del precio y luego lo vea volver
puede ser económicamente interesante, **pero no es la misma hipótesis**. Nombre
provisional: **`reentrada_desde_estado_inicial_externo`**.

No entra en EXPLORE-001 v1. Si se estudia después: cuenta como hipótesis nueva;
requiere definición y dirección propias; consume multiplicidad; debe
pre-registrarse antes de outcomes; **no puede rescatar retroactivamente una
hipótesis primaria muerta**.

## 4. AACloseOpenDiffs

### 4.1 Decisión

**`AACloseOpenDiffs` queda fuera de EXPLORE-001 v1.**

### 4.2 Fundamento

El indicador **sí** posee identidad de barra creadora mediante `m1_bar`,
exportable como `created_bar`. Por lo tanto, **la ausencia de barra creadora ya
no es un motivo válido de exclusión**.

El motivo vigente es: no emite `ZONE_TOUCHED`; no existe una definición canónica
de primer toque; no existe un censo comparable bajo esa semántica; introducirla
ahora agregaría una definición nueva **después de ver la curva de los demás
indicadores**; ampliaría la superficie de error y la multiplicidad del primer
gate.

### 4.3 Condición para una futura entrada

Sólo mediante una enmienda futura que defina, **antes de outcomes**: qué
constituye un toque; desde qué reloj está disponible; cómo se evita el toque en
la propia barra creadora; cuál es el primer evento elegible; qué dirección
económica tiene; qué oráculo o golden acredita la implementación; cuál es su
tasa outcome-free; cuál es el costo adicional de multiplicidad.

Hasta entonces, cualquier ausencia de clase o semántica debe **fallar cerrado**.

## 5. Estadístico y unidad inferencial

### 5.1 Estimando primario

```
expectativa neta por evento elegible, en ticks
fricción round turn = 2,768 ticks, restada DENTRO del resultado de cada evento
umbral económico del estimando neto = 0 ticks
```

**Queda prohibido volver a restar 2,768 del lado derecho de la comparación.**

### 5.2 Dependencia por sesión

La estrategia operaría eventos, por lo que el estimando económico principal
conserva peso por evento. Pero los eventos de una misma sesión **no son
observaciones independientes**. Por eso: la estimación puntual se calcula sobre
eventos elegibles; **la inferencia remuestrea o agrupa por sesión**; el bloque
mínimo de dependencia es el **día de sesión CT**; se reporta como sensibilidad la
media equal-weight de las expectativas diarias; una diferencia material entre
pooling por evento y equal-weight diario **debe declararse, no promediarse**.

Los estratos horarios o de volatilidad son **descriptivos**. No pueden rescatar
un global muerto.

### 5.3 Dirección

**`BigTrap2`** posee dirección nativa (`trapped_sellers` / `trapped_buyers`).
Puede utilizar un estadístico con signo siempre que la traducción concreta quede
**congelada en E-R1 antes de outcomes**.

**Indicadores sin dirección nativa** (`aVolCellPOI2`, `Gaps2`, `HFTZones2` y
cualquier zona sin dirección intrínseca): no se puede elegir *fade* o *break*
después de observar cuál gana; no se puede usar valor absoluto para afirmar un
edge operable; **una prueba bilateral no concede gratuitamente la dirección de
trading**.

Antes de entrar a E-R1, cada candidato debe tener una **regla direccional
target-free derivada de su semántica**. Si no existe una regla direccional
defendible antes de outcomes:

```
el candidato puede seguir como fenómeno exploratorio,
pero NO como hipótesis confirmatoria de edge.
```

Probar *fade* y *break* como dos brazos es posible **sólo** si ambos quedan
declarados como familia y **pagan su multiplicidad**.

### 5.4 Regla de decisión

```
VIVE:   cota inferior del IC ajustado > 0
MUERE:  cota superior del IC ajustado < 0
GRIS:   el IC contiene 0  →  MUERE POR DEFECTO
```

Una hipótesis gris sólo puede sobrevivir **una vez** si la excepción y el dato
que la resolvería quedaron escritos **antes** de outcomes. Sin esa excepción
previa, gris significa muerta.

Una hipótesis muerta **no vuelve con parámetros retocados**. Su regreso
constituye una hipótesis nueva.

## 6. Selección de candidatos y grilla confirmatoria

### 6.1 La frecuencia es una salida, no una perilla

No se fuerza a todos los indicadores a `f = 7-12`. La banda fue útil para
planificar, pero la curva demostró que **no es un régimen común**. Cada candidato
debe usar su frecuencia corregida real, su MDE correspondiente, su DEFF
correspondiente y su operabilidad económica correspondiente.

**Queda prohibido mover `T` hasta que la frecuencia «quede linda».**

### 6.2 Regla de selección, en orden

Antes de outcomes: excluir celdas con evento semánticamente inválido;
**recalcular las tasas seleccionadas excluyendo `k_T == 0`**; descartar
geometrías ciegas al MDE de su frecuencia real; exigir una dirección
target-free; preferir mecanismos distintos; preferir candidatos con paridad,
oráculo y gate ya montados; congelar un `T` o una banda estrecha por indicador;
**pagar toda multiplicidad antes de ejecutar**.

### 6.3 Mapa inicial de candidatos

| indicador | rol | `T` de diseño | `f` publicada | dirección | `k_T==0` en esa celda |
|---|---|---:|---:|---|---|
| `BigTrap2` | **candidato principal** | ≈ 34 | ≈ 8,3 | **nativa** | prácticamente nula |
| `aVolCellPOI2` | **candidato principal** | ≈ 21 | ≈ 8,1 | requiere regla target-free | prácticamente nula |
| `Gaps2` | tercer mecanismo, condicional | ≈ 34 | ≈ 13,1 | requiere regla y gate explícitos | — |
| `HFTZones2` | reserva de diseño | — | alta incluso en `T=34` | — | no entra por defecto si `Gaps2` pasa |
| `VolTicksPOC2` | reserva de baja frecuencia | — | no alcanza el régimen buscado | — | no entra al primer trío salvo justificación previa |

**Son candidatos, no hipótesis selladas.** La selección final requiere el
recuento corregido y la regla direccional.

### 6.4 Regla del tercer candidato

El tercer candidato preferido será `Gaps2` si, **antes de outcomes**: pasa el
recuento corregido; dispone de dirección target-free; pasa paridad/gate; su
frecuencia permite una geometría no ciega; no requiere decisiones post hoc.

Si falla cualquiera de esos puntos, **no se lo reemplaza mirando outcomes**. La
alternativa se decide con la misma regla outcome-free entre `HFTZones2` y
`VolTicksPOC2`, documentando por qué.

**También es válido ejecutar sólo dos hipótesis** si ningún tercer mecanismo
cumple los gates. Completar «tres» no justifica admitir una hipótesis mal
definida.

## 7. Secuencia autorizada desde este punto

**Paso 1 — corregir la semántica outcome-free.** Implementar o derivar el
recuento `k_T > 0` (excursión válida) / `k_T == 0` (`ya_fuera_al_disponible`).
**No leer outcomes.**

**Paso 2 — producir la tabla final de diseño.** Para las celdas candidatas:
indicador; clase de kernel; `T`; sesiones; zonas elegibles; `k_T == 0`;
excursiones válidas; retornos válidos; frecuencia corregida por sesión; días sin
eventos; cobertura; descartes; MDE aplicable; gate direccional; estado de
paridad/oráculo.

**Paso 3 — congelar H1-H3.** Propuesta inicial: `H1` `BigTrap2` ≈ `T=34`; `H2`
`aVolCellPOI2` ≈ `T=21`; `H3` `Gaps2` ≈ `T=34`, condicional a sus gates. Los
valores exactos se fijan con la tabla corregida, sin outcomes. **No se selecciona
un argmax.** Si se usa una banda de resoluciones, se entrega la curva completa y
se exige **estabilidad entre puntos adyacentes**.

**Paso 4 — redactar E-R1 v0.3**, cerrando: población de eventos; disponibilidad;
regla `k_T > 0`; dirección por hipótesis; horizonte; salida y censura; fricción;
estimando; dependencia por sesión; bootstrap/IC; multiplicidad; regla
VIVE/MUERE/GRIS; criterio de futilidad; replicación; regla de una sola mirada al
holdout; artefactos y hashes esperados.

**Paso 5 — auditoría y sello.** Verificar rutas y hashes; ejecutar tests de
paridad; verificar que no haya acceso al holdout; confirmar que no quedan
parámetros libres; **adjudicar E-R1 mediante acto humano**; cambiar DRAFT a
SEALED sólo después de ese acto.

**Paso 6 — outcomes research.** Ejecutar las hipótesis **juntas**; no correr una,
mirar y ajustar la siguiente; aplicar fricción 2,768 dentro del resultado;
publicar todos los descartes; emitir VIVE/MUERE/GRIS según contrato; no rescatar
globales mediante estratos.

**Paso 7 — replicación y holdout.** Sólo una hipótesis VIVE puede avanzar:

```
research VIVE → replicación ES/NQ con fricción propia → una sola mirada al holdout
```

ES y NQ **no aumentan artificialmente `n`**: son gates de transportabilidad.

## 8. Prohibiciones vigentes

Hasta sellar E-R1 queda prohibido: leer outcomes para elegir candidatos; elegir
dirección después de ver resultados; elegir el mejor `T` por P&L; reintroducir
`k_T == 0` en la hipótesis primaria; incorporar `AACloseOpenDiffs`; abrir el
holdout; adjudicar automáticamente la curva desde código; modificar el artefacto
original; tratar un resultado descriptivo como confirmatorio; sustituir un
candidato fallido después de outcomes; ejecutar menos o más hipótesis que las
selladas; ampliar la grilla después de ver resultados.

## 9. Decisiones adoptadas

1. Se crea `ESPEC_TEST_EXPLORE-001_v0.3.md` como única especificación canónica futura.
2. Las dos especificaciones anteriores quedan SUPERSEDED, sin ser borradas.
3. La curva de 201 sesiones se acepta como **mapa de diseño outcome-free**.
4. La curva **no** constituye evidencia de edge ni autoriza outcomes.
5. No existe un `T` global; la grilla será **por indicador**.
6. `k_T == 0` **no** es ruptura ni retorno de la hipótesis primaria.
7. `k_T == 0` se reporta como `ya_fuera_al_quedar_disponible`.
8. La posible reentrada desde estado inicial externo queda para una hipótesis futura.
9. `AACloseOpenDiffs` queda fuera de EXPLORE-001 v1.
10. `BigTrap2` y `aVolCellPOI2` son los dos candidatos principales.
11. `Gaps2` es el tercer candidato condicional.
12. Toda dirección debe definirse target-free **antes** de outcomes.
13. El estimando primario será expectativa neta por evento con fricción dentro del resultado.
14. La dependencia se tratará **por sesión**.
15. GRIS **muere por defecto**.
16. E-R1 v0.3 debe sellarse antes de cualquier outcome.
17. Sólo una hipótesis VIVE y replicada puede abrir el holdout.

## 10. Próxima acción autorizada

```
1. Crear la especificación consolidada v0.3.
2. Marcar las dos anteriores como SUPERSEDED.
3. Producir el recuento outcome-free corregido para las celdas candidatas.
4. Preparar la tabla final de diseño.
5. Proponer H1–H3 y E-R1 v0.3.
```

**No se autorizan outcomes, P&L ni acceso nuevo al holdout.**

## 11. Nota de registro — lo único que agrega Claude

El contenido normativo de §0-§10 es del auditor y se registró **sin
modificarlo**, incorporando su propia corrección al párrafo de §2.3.C
(«definición reproducible y resultado replicado», no «reproducida»).

Lo único que se agrega es este apartado, con dos observaciones de implementación
que **no cambian ninguna decisión**:

1. **§2.3.C, cifra de `bar_close`.** El `0,0 %` de los tres controles vale **con
   umbral material > 1 s**, y así está escrito. Conviene que el implementador
   sepa por qué: **sin** umbral esos tres dan **100 %**, porque para un kernel
   que crea al cierre el `created_ms + 1` deja 1 ms de diferencia **por la propia
   convención**. Un recuento futuro que omita el umbral verá 100 % en el grupo de
   control y concluirá que el split no discrimina.

2. **§7 paso 1, alcance del recuento.** El recuento corregido necesita, por
   celda candidata, distinguir `k_T == 0` de `k_T > 0` **y además** el retorno
   con `j > k_T`. La sonda actual (`sonda_alejamiento_cero.py`) mide la
   **fracción con `k_T == 0`** pero **no** emite el conteo de retornos válidos:
   ese recuento es trabajo nuevo sobre `eventos_de_zona`, no una lectura del
   artefacto existente. Se declara acá para que no se lo confunda con algo ya
   medido.

**Aporte al referente:** fija, antes de ver un solo outcome, qué cuenta como
evento y de dónde sale su dirección. Las dos son las puertas por donde entra el
sesgo de selección que convierte un artefacto de medición en un edge aparente.
