# Iteración 3 — Kimi — linaje, contabilidad y cadena de custodia

**Fecha:** 2026-08-05
**Rama auditada:** `fix/capture-probe-v2-contract`
**Tip de entrada de esta iteración:** `176f7fcdcd808c6bae37a8caf6aa1967a60dbc41`
**Tip de código productivo bajo análisis:** `a0087b9429eb2ec741a5d4a1c3d4ba6d3b783a58`
**Iteraciones previas leídas:** `ITERATION_1_GPT_2026-08-05.md`, `ITERATION_2_GROK_2026-08-05.md`
**Naturaleza:** análisis estático de linaje y contabilidad; **no implementación**
**Outcomes consultados:** no · **Holdout abierto:** no · **NT8 ejecutado:** no

> Tercera y última capa antes de que Claude implemente. No se asume que las
> iteraciones 1 y 2 sean correctas. Cada ítem se clasifica como `confirmación`,
> `refutación parcial`, `extensión` o `hallazgo independiente`.

## 0. Lente de esta iteración

Las iteraciones 1 y 2 auditaron **el instrumento** (ramas alcanzables, emisor
fiel, gate de compilación). Esta capa audita **los libros**:

1. ¿Cada número publicado tiene numerador y denominador de la misma población?
2. ¿Se puede reconstruir el linaje de un número desde el artefacto crudo?
3. ¿Los registros de custodia prueban lo que ocurrió, o sólo lo que se declaró?
4. ¿El material que P5 necesita es **admisible**, no sólo idéntico?

La tesis: el proyecto ya tuvo dos veces el mismo defecto —un denominador que no
existía (H2) y un parámetro inerte dentro de un hash (B1)—. Esta capa busca la
tercera instancia de esa familia **fuera** de `pred004_analyze.py`.

## 1. Veredicto ejecutivo

```text
Confirmo el veredicto de las capas 1 y 2: no capturar todavía.

Agrego un bloqueante que ninguna de las dos capas anteriores levantó:

  El artefacto de referencia de P5 (BigTrap2_time1_6E_0926_v2.csv) aparece
  NOMBRADO en el código que define la cuarentena INC-005 como una de las
  extracciones que QUEMARON los días 2026-07-01 -> 07-24.

  Si eso se confirma, P5 no es sólo "abrir el holdout": es usar como patrón
  de oro un artefacto que el propio repo clasifica como contaminante.
  Eso se adjudica ANTES de correr P5, no después de ver el resultado.

Segundo eje: la contabilidad publicada por el analizador y por la puerta
única de estudios no cierra por identidad. Nadie puede verificar que no se
cayó material en el camino, porque el denominador de entrada no se publica.
```

## 2. Evidencia adicional inspeccionada

Además de lo citado por las capas 1 y 2:

| Artefacto | Para qué |
|---|---|
| `edgelab/research/universo_estudio.py` | puerta única; contabilidad de holdout y cuarentena |
| `edgelab/research/holdout_guard.py` | qué prueba y qué no prueba el log de accesos |
| `docs/holdout_access_log.md` | filas reales, incluida la brecha del atlas nulo |
| `docs/predictions/CLAUSULAS_INFERENCIA_EXPLORE-001.md` | 200 / 197 / N_eff y hueco de preregistro |
| `docs/predictions/PRED-004_tickbar_attribution_v23.json` | estimando y orden preregistrado |

## 3. Matriz sobre las capas 1 y 2

| ID previo | Clasificación | Lectura Kimi |
|---|---|---|
| H-GPT-1 `verif` | **confirmación** | El `NameError` es real. Coincido con Grok: el fixture es adversarial. Agrego criterio contable: la rama debe publicar los mismos campos que la salida normal, o el consumidor no puede distinguir ABSTAIN de salida truncada. |
| H-GPT-2 `--resolucion` | **confirmación** | Adhiero a la variante de Grok (`required=True`). Motivo contable: un ABSTAIN opcional crea dos estados con la misma etiqueta y distinto significado. |
| H-GPT-3 / H-GROK-5 T6 | **confirmación** | Nada que agregar salvo que el artefacto de compilación debe entrar al mismo bundle de hashes que el `.cs` y el contrato. Un PASS de compilación sin hash del binario/salida no es trazable. |
| H-GPT-4 preflight | **confirmación** | Extensión en H-KIMI-6: el preflight debe incluir inventario de `oracles/` como **artefacto**, no como paso narrado. |
| H-GPT-5 / H-GROK N1 `seq` | **confirmación + dependencia nueva** | N1 bloquea mi propuesta H-KIMI-5 (resumen final del emisor). No es sólo deuda de P5: es deuda que impide instrumentar la reconciliación. |
| H-GPT-6 completitud OHLCV | **confirmación** | De acuerdo con la prioridad baja de Grok. |
| H-GROK-1 `denom==0` inalcanzable bajo emisor fiel | **confirmación** | El razonamiento se sostiene con `TAIL_BARRAS=0` y warmup por `BARRA_PROCESADA`. Refuerzo: al ser inalcanzable hoy, la rama es **defensa**, y una defensa debe ser barata y correcta, no rica en contadores derivados. |
| H-GROK-2 mismatch cuenta en denominador | **confirmación fuerte** | Es correcto para el estimando, y es exactamente el punto donde se rompe la contabilidad publicada. Ver H-KIMI-3. |
| H-GROK-4 meta 2.3 vs 2.4 | **confirmación** | Es un defecto de procedencia, que es el tema de esta capa. Ver H-KIMI-7. |
| H-GROK-6 T3 en dos capas | **extensión sustantiva** | T3a y T3b son necesarias pero **insuficientes**: falta T3c, admisibilidad. Ver H-KIMI-1. |
| H-GROK-8 firewall por string | **confirmación + extensión** | Ver H-KIMI-4: el log no puede probar ausencia de acceso, y ya falló exactamente así. |

## 4. Hallazgos independientes

### H-KIMI-1 — El artefacto de referencia de P5 puede ser el que causó la cuarentena (BLOQUEANTE)

**Hecho (código).** `edgelab/research/universo_estudio.py` documenta la
cuarentena permanente INC-005 así:

> `2026-07-01 a 2026-07-24 fueron quemados por contaminación cruzada manual.`
> `El censo con min()/max() REALES ... confirma que la extracción de oráculos`
> `alcanza 2026-07-24T17:59:20 (BigTrap2_diag_tick25, BigTrap2_time1_v2, Gaps2).`

**Hecho (preflight).** La referencia que P5 exige es
`oracles/BigTrap2_time1_6E_0926_v2.csv`, con ventana medida
`2026-07-07T19:04 -> 2026-07-24T17:59`.

**Inferencia (a verificar, no concedida).** `BigTrap2_time1_v2` del comentario y
`BigTrap2_time1_6E_0926_v2.csv` del preflight parecen el mismo artefacto. La
coincidencia del extremo superior —`17:59:20` contra `17:59`— es fuerte.

**Por qué importa, y por qué no es lo mismo que N5.** N5 dice "P5 abre el
holdout". Eso es una cuestión de **metodología** y se resuelve registrando la
apertura. Esto es distinto y peor: la cuarentena es de **procedencia**, y el
propio código dice que ni una apertura sancionada entrega días quemados —
`holdout_servible` los excluye explícitamente. O sea: el repo tiene una regla
que dice que ese material no sirve para nada, y P5 lo quiere como patrón de oro.

**Las dos salidas posibles, y las dos son legítimas:**

1. **Admisible.** La cuarentena aplica al **material de días** usado como muestra
   inferencial (ticks, excursiones, zonas). P5 no usa esos días como muestra:
   compara **bytes de un EventLog contra bytes de otro EventLog**. La
   contaminación cruzada no afecta una prueba de bit-identidad, porque el
   defecto que P5 busca es una regresión del `.cs`, no una propiedad del mercado.
2. **Circular.** Si el oráculo histórico fue producido por una corrida que el
   propio censo clasifica como contaminante, entonces "bit-idéntico al oráculo"
   puede significar "reproduce fielmente una captura defectuosa".

**Mi lectura preliminar:** la salida 1 es probablemente correcta, porque P5 es
target-free por construcción. Pero **no está escrito en ningún lado**, y la
diferencia entre las dos salidas cambia qué significa un PASS de P5.

**Qué debe hacer Claude (T3c, admisibilidad):**

1. Verificar si `BigTrap2_time1_v2` del comentario de cuarentena **es** el
   archivo del preflight. Comparar nombre, ventana e instrumento, sin abrir el
   contenido de días para nada inferencial.
2. Localizar el código o el reporte de censo que produjo esa lista de tres
   oráculos y citar la línea.
3. Redactar la cláusula de admisibilidad y **elevarla a Nico**, con esta forma:

```text
P5 usa el oráculo histórico como REFERENCIA DE REGRESIÓN, no como muestra.
La cuarentena INC-005 no lo inhabilita para ese uso porque <razón>.
Un PASS de P5 significa: el camino de tiempo no cambió entre 2.1 y 2.4.
Un PASS de P5 NO significa: la captura histórica era correcta.
```

4. Si no puede acreditarse la equivalencia del artefacto, P5 queda `ABSTAIN`
   por procedencia, no por formato.

**Prohibido:** resolver esto abriendo el CSV para "ver si se parece".

### H-KIMI-2 — La puerta única no publica su denominador de entrada

**Hecho.** `cargar_dias_de_estudio` devuelve `validos` y un dict con
`descartados_holdout`, `fechas_holdout`, `descartados_cuarentena`,
`fechas_cuarentena`. **No devuelve cuántos días entraron.**

**Consecuencia.** Ninguna identidad contable cierra desde afuera:

```text
¿n_entrada == len(validos) + descartados_holdout + descartados_cuarentena ?
NO, y no se puede saber:
  - los quemados están HOY íntegramente dentro del sello, así que
    en_cuarentena es un SUBCONJUNTO de en_holdout -> doble conteo;
  - un día quemado y pre-holdout no entra a `validos` ni a `en_holdout`,
    sólo a `en_cuarentena`;
  - el filtro por `tipos_de_dia` ya descartó días antes, sin reportar cuántos.
```

Hoy el sistema funciona por una coincidencia: la cuarentena empieza exactamente
en el sello. Si INC-005 se ampliara hacia atrás —cosa que ya pasó una vez, el
docstring dice "ampliada"— aparecerían días que **desaparecen de la
contabilidad** sin que ningún consumidor pueda detectarlo.

**Es la misma familia que H2.** En H2 el denominador de P1/P2 no existía en el
log y el veredicto salía por construcción. Acá el denominador de entrada del
universo no se publica y la exclusión no es auditable desde afuera.

**Reparación propuesta (barata, sin cambiar semántica):** devolver también
`n_entrada`, `n_descartados_por_tipo`, y `n_solapamiento_cuarentena_holdout`, y
agregar un test que exija una identidad explícita:

```text
n_entrada == n_descartados_por_tipo
           + len(validos)
           + |en_holdout ∪ en_cuarentena|
```

**Alcance:** esto es T4/T5, **no** entra en el microparche de PRED-004. Se anota
acá porque es el mismo modo de falla y conviene que Claude lo vea junto.

### H-KIMI-3 — `footprint_mismatch_total` y `tasa_mismatch_total` no comparten población

**Hecho (código, `modo_p1p2`).**

```python
footprint_mismatch_total = len(mism_todas)
tasa_mismatch_total      = len(mism_todas & procesadas) / len(procesadas)
```

El contador publica **todas** las barras con mismatch. La tasa publica sólo las
que además fueron procesadas. Son dos poblaciones distintas con nombres
hermanos.

**Consecuencia.** Cualquiera que intente reconciliar el reporte haciendo
`tasa_mismatch_total × barras_procesadas_total` y comparar contra
`footprint_mismatch_total` obtendrá números distintos en cuanto exista **una**
barra con mismatch que no haya sido procesada. Y ese caso existe: la propia
batería lo fabrica en `test_B4_P3_no_cuenta_mismatch_de_barras_no_procesadas`.

Esto es exactamente el "menor 3" que el contrato v3 dice haber corregido. La
tasa se corrigió; **el contador que la acompaña no**.

**Segundo caso, misma familia:**

```python
excluidos_por_warmup_barras = len({b for b in mism_todas if b < lo_int})
```

El nombre dice `barras` y el sufijo distingue de `_eventos`, pero lo que cuenta
son **barras con mismatch** excluidas, no barras excluidas. Un lector razonable
leerá "cuántas barras quedaron fuera del interior". El "menor 2" separó unidades
(barras vs eventos) pero no separó **poblaciones** (todas las barras vs barras
con mismatch).

**Reparación propuesta:** renombrar a
`mismatch_excluidos_por_warmup_barras` y `mismatch_total_todas_las_barras`, o
publicar además `barras_en_warmup` y `barras_totales_en_log`. Y una nota
explícita en el JSON de salida:

```text
footprint_mismatch_total NO es el numerador de tasa_mismatch_total.
```

**Prioridad:** media. No cambia ningún veredicto, pero es precisamente el tipo
de ambigüedad que produce una reconciliación errónea en la adjudicación.

### H-KIMI-4 — El log de holdout registra declaraciones, no accesos

**Hecho.** `check_holdout` escribe una fila cuando el propósito es
`target_free_validation` o cuando deniega. Un acceso que **no pasa por el
guard** no deja rastro. Y eso no es hipotético: la brecha del atlas nulo
(10 días, 2026-07-27) tuvo que agregarse **a mano** después de detectarla, y hay
tres filas más marcadas `manual/retroactive`.

**Consecuencia contable.** El log puede probar que **hubo** un acceso. **No**
puede probar que no hubo otros. Para un firewall, esa asimetría es el punto
entero.

**Segundo hecho.** El log es un `.md` en el repo. "Append-only" está declarado
en el encabezado y sostenido por convención de escritura (`"a"`), no por una
capacidad: cualquier commit puede reescribir una fila y el diff lo mostraría
sólo si alguien lo mira.

**Relación con PRED-004.** Si P5 se corre, la apertura debe quedar registrada
**antes** de leer el archivo. Con el mecanismo actual eso depende de que quien
corra P5 se acuerde. Propuesta mínima, sin construir T5 completa:

```text
pred004_analyze.py p5-time llama a check_holdout(purpose="target_free_validation",
caller="pred004_analyze:p5-time") ANTES de abrir el histórico,
y aborta si el guard levanta.
```

Eso convierte el registro en un efecto del código y no en una promesa del
operador. Es tres líneas y cierra la deuda que el propio log declara dos veces
("cablear `check_holdout` dentro del matcher", "el arnés no verifica la ventana
del oráculo antes de consumirlo").

**Ojo:** esto **cambia el comportamiento** de un modo que Nico debe aprobar,
porque hace que P5 escriba en un log versionado durante su ejecución.

### H-KIMI-5 — El emisor tiene contadores internos que nunca se publican

**Hecho.** `BigTrap2.cs` mantiene `nPares`, `nMismatch`, `nAbstenciones`,
`nResiduales`, `nSuprimidas`. Sólo dos salen, y sólo dentro de
`SESION_RESINCRONIZADA`.

**Oportunidad.** Un evento único al final de la corrida con esos cinco números
daría **doble contabilidad**: el analizador reconstruye desde las filas, el
emisor declara su propio conteo, y los dos deben coincidir.

```text
analizador: len(procesadas)   vs   emisor: nPares
analizador: len(mism_todas)   vs   emisor: nMismatch
analizador: len(amb)          vs   emisor: nAbstenciones
```

Una discrepancia probaría lo que hoy **ningún gate detecta**: log truncado por
flush incompleto, captura cortada a mitad, o filas perdidas. Es justo el riesgo
que `TAIL_BARRAS = 0` deja abierto, y que P6 tampoco cubre (P6 detecta append,
no truncamiento).

**Pero está bloqueado por N1, y por eso lo dejo como propuesta y no como tarea.**
Agregar un evento nuevo corre `eventSeq` y, si cae en el camino de tiempo, toca
P5 directamente. Secuencia obligatoria:

```text
1. adjudicar N1 (inventario de tipos que incrementan seq, por camino y versión)
2. recién ahí decidir si v2.5 emite RESUMEN_FINAL, y sólo en camino de tick
3. nunca en la misma captura que mide PRED-004
```

**No es para esta ronda.** Es la mejora estructural que hace que la próxima
captura sea autoverificable.

### H-KIMI-6 — N2 (overwrite) puede dejar de ser procedimental

**Hecho.** El contrato declara que P6 no detecta overwrite y que se verifica
"por procedimiento": inventario de `oracles/` antes y después.

**Problema contable.** Un procedimiento narrado en un `.md` no es evidencia.
Si mañana alguien pregunta "¿se pisó un archivo?", la respuesta es la memoria
del operador.

**Reparación (barata y mecánica):**

```text
tools/inventario_oracles.py --dir oracles --out runs/pred004/inv_antes.json
<capturas>
tools/inventario_oracles.py --dir oracles --out runs/pred004/inv_despues.json
tools/inventario_oracles.py --diff inv_antes.json inv_despues.json

Exige: exactamente N archivos nuevos, 0 modificados, 0 desaparecidos.
Cada entrada: nombre, bytes, mtime, sha256.
Salida content-addressed, igual que el analizador.
```

Con eso N2 pasa de promesa a artefacto, y el reporte de captura puede citar dos
hashes en vez de una afirmación.

### H-KIMI-7 — La procedencia declarada no se verifica contra el paquete congelado

**Confirmación y formalización de H-GROK-4.** El analizador lee `# meta` para
decidir si abstiene, pero nunca compara la versión declarada contra la versión
que el paquete congelado dice haber instalado.

**Escenario que hoy pasa silencioso:** se captura con el `.cs` v2.2 todavía
instalado —que es **exactamente el estado que el preflight encontró**—, el log
sale con `version=2.2`, no trae `BARRA_PROCESADA`, y el analizador abstiene. Eso
está bien. Pero si alguien captura con una v2.4 mal instalada o con un binario
viejo cacheado por NT8, el log podría traer `BARRA_PROCESADA` y una versión que
no corresponde, y se mediría igual.

**Reparación:** flag `--exigir-version 2.4` que, en modo captura, convierta la
discrepancia en `ABSTAIN` de procedencia. Y en la batería, dejar de usar
`META_23` como meta por defecto para fixtures que fabrican eventos de v2.4:
fabricar un emisor con la versión que corresponde al evento que emite.

### H-KIMI-8 — EXPLORE-001 tiene cuatro números de universo y un hueco de preregistro

**Hechos.** Circulan al menos cuatro cifras para el mismo universo:

| Cifra | Origen | Significado declarado |
|---|---|---|
| 256 | handoff | días aptos brutos |
| 200 | cláusulas §3 | entradas de contratos APTO en alcance |
| 197 | cláusulas §3 | bloques de día tras deduplicar 3 viernes de roll |
| 193 | cierre de campaña | N efectivo reportado |
| 191 | cláusulas §3 (refutado) | conteo previo, explícitamente corregido |

Las cláusulas explican 200 -> 197 (deduplicación por fecha en los tres viernes
de roll trimestral). **No hay documento que explique 256 -> 200 ni 197 -> 193.**

**Además, hueco abierto y declarado en el propio preregistro:**

> `PENDIENTE DE PREREGISTRO. Cómo se trata n_eventos(d) en las fechas con doble`
> `contrato: si se suman ambos contratos o si se usa el contrato vigente al`
> `cierre. Esa decisión cambia el denominador del estimando diario.`

Otra vez: **un denominador sin definir**, esta vez en el estimando diario de
EXPLORE-001, y esta vez el propio documento lo admite.

**Consecuencia.** El umbral `N >= 200` que cerró EXPLORE-001 se evaluó contra un
número cuya derivación no está escrita. No estoy afirmando que el cierre esté
mal; estoy afirmando que **no es reproducible desde los documentos**.

**T4, formalizada:** producir `docs/LINAJE_UNIVERSO_EXPLORE-001.md` con una sola
tabla de reconciliación, una fila por transición, cada una con la regla que la
produce y el archivo/línea que la implementa. Y cerrar el `PENDIENTE DE
PREREGISTRO` **antes** de abrir outcomes, porque después deja de ser preregistro.

## 5. Paquetes para Claude, desde la lente de linaje

No reemplazan a G0–G5 de la capa 2. Se **insertan** en ese grafo.

### K1 — T3c: admisibilidad del oráculo de P5 *(bloqueante de P5, no del parche)*

- Verificar identidad entre `BigTrap2_time1_v2` (cuarentena) y la referencia del preflight.
- Citar la línea del censo que produjo esa lista.
- Redactar cláusula de admisibilidad y elevarla.
- Sin abrir contenido para nada inferencial.

**Salida:** párrafo en el preflight + una línea en el contrato. Si no se puede
acreditar: P5 = `ABSTAIN` por procedencia.

### K2 — Consistencia de poblaciones en la salida del analizador *(entra en G1)*

- Renombrar o desambiguar `footprint_mismatch_total` y `excluidos_por_warmup_barras`.
- Publicar `barras_totales_en_log` y `barras_en_warmup`.
- Nota explícita de no-reconciliación en el JSON.
- Test que verifique que cada tasa publicada declara su población.

### K3 — Registro automático de apertura en P5 *(requiere OK de Nico)*

- `check_holdout` invocado desde `p5-time` antes de abrir el histórico.
- Aborta si el guard levanta.
- Cierra dos deudas ya declaradas en el propio log.

### K4 — Inventario de `oracles/` como artefacto *(entra en G4)*

- Herramienta de inventario y diff con sha256.
- Convierte N2 de procedimiento en evidencia.

### K5 — Exigencia de versión en modo captura *(entra en G1 o G4)*

- `--exigir-version`.
- Fixtures con meta coherente con los eventos que fabrican.

### K6 — Linaje del universo EXPLORE-001 *(T4, fuera de PRED-004)*

- Tabla de reconciliación 256 -> 200 -> 197 -> 193.
- Cerrar el `PENDIENTE DE PREREGISTRO` de `n_eventos(d)`.

### K7 — Identidad contable en la puerta única *(T4/T5, fuera de PRED-004)*

- Publicar `n_entrada` y el solapamiento cuarentena/holdout.
- Test de identidad que falle si algo desaparece.

## 6. Backlog consolidado de las tres capas

Esta es la tabla que conviene que Claude use como índice. `Bloq` = bloquea la
captura.

| # | Tema | Origen | Bloq | Paquete |
|---|---|---|---|---|
| 1 | `verif` / rama `denom==0` | GPT-1, GROK-1 | sí | G1 |
| 2 | `--resolucion` opcional en P5 | GPT-2, GROK | sí | G1 |
| 3 | Mensajes de warmup con semántica vieja | GROK-3 | no | G1 |
| 4 | Poblaciones inconsistentes en la salida | KIMI-3 | no | G1 + K2 |
| 5 | Meta 2.3 vs `.cs` 2.4 | GROK-4, KIMI-7 | sí* | G1 + K5 |
| 6 | Inventario N1 (`seq`) | GPT-5, GROK, KIMI-5 | sí | G2 |
| 7 | Gate real de compilación | GPT-3, GROK-5 | sí | G3 |
| 8 | Preflight obsoleto | GPT-4, GROK | sí | G4 |
| 9 | Inventario de `oracles/` | KIMI-6 | sí | G4 + K4 |
| 10 | T3a hash del oráculo | GROK-6 | sí | T3 |
| 11 | T3b bytes de los ticks de input | GROK-6 | no | T3 |
| 12 | **T3c admisibilidad INC-005** | **KIMI-1** | **sí** | **K1** |
| 13 | Registro automático de apertura P5 | KIMI-4 | no | K3 |
| 14 | Completitud OHLCV en P3 | GPT-6, GROK | no | G1 |
| 15 | Firewall por capacidad | GROK-8, KIMI-4 | no | T5 |
| 16 | Linaje 256/200/197/193 | KIMI-8 | no** | K6 |
| 17 | Identidad contable puerta única | KIMI-2 | no** | K7 |
| 18 | `RESUMEN_FINAL` del emisor | KIMI-5 | no | post-N1 |
| 19 | T0' medición alternativa | GPT, GROK-7 | no | paralelo |

\* bloqueante sólo para la captura real, no para el parche.
\*\* no bloquea PRED-004; **sí** bloquea abrir outcomes de EXPLORE-001.

## 7. Desacuerdos explícitos

1. **Prioridad de N1.** GPT lo mete en el parche; Grok lo saca a inventario; yo
   agrego que además **bloquea** la instrumentación de reconciliación (H-KIMI-5).
   Los tres coincidimos en que no se resuelve eligiendo la opción cómoda.
2. **Alcance de T3.** Grok propone dos capas; yo sostengo que sin la tercera
   (admisibilidad) las otras dos pueden dar verde sobre material inadmisible.
3. **Gravedad de la contabilidad.** Las capas 1 y 2 la tratan como cosmética.
   Yo sostengo que es la misma familia de defecto que ya produjo H2 y B1, y que
   por eso merece test, no sólo renombre.
4. **P5 y la cuarentena.** Mi lectura preliminar es que P5 **es** admisible por
   ser target-free. No lo doy por cerrado: lo que objeto es que hoy no está
   escrito en ningún lado y que la ausencia se está tratando como permiso.

## 8. Prompt de arranque para Claude

```text
Rama y tip los indica Nico. Leé CLAUDE.md, NORTH_STAR.md, el JSON de PRED-004,
CONTRATO_ANALIZADOR_PRED-004.md, check_nt8_cs.py y las TRES iteraciones en
docs/research/ITERATION_{1,2,3}_*.

Ninguna de las tres es autoridad. Empezá por la tabla consolidada de la
iteración 3 (sección 6) como índice, y para cada fila producí:
  confirmado / refutado / no reproducible, con archivo y línea.

Orden: G0 reproducción -> G1 parche mecánico -> G2 inventario N1 ->
G3 compilación -> G4 preflight. K1 (admisibilidad del oráculo P5) corre en
paralelo y bloquea P5, no el parche.

Reglas duras: no abras NT8, holdout ni outcomes. No muevas el pin. No uses
run_nt8_bridge para PRED-004. Todo test sintético declara emisor_fiel o
emisor_adversarial y cita la línea del .cs que emite el evento que fabrica.
Toda tasa publicada declara su población. Commits chicos y adjudicables.
El que implementa no aprueba su propia reparación. Si algo cambia la semántica
congelada, frená y consultá a Nico.
```

## 9. Resultado de esta iteración

Esta capa no implementa nada. Aporta un bloqueante que las dos anteriores no
vieron —la admisibilidad del oráculo de P5 frente a la cuarentena INC-005—,
formaliza tres defectos de contabilidad de la misma familia que H2 y B1, propone
la doble contabilidad emisor/analizador como mejora estructural post-N1, y deja
un backlog consolidado de 19 ítems con dependencias y bloqueos explícitos.

**Aporte al referente:** evita que PRED-004 se adjudique contra un patrón de oro
cuya admisibilidad nunca se declaró, y ataca la familia de defecto que ya
produjo dos veredictos vacíos en este proyecto: números publicados cuyo
denominador nadie puede reconstruir.
