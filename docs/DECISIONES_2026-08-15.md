# Decisiones tomadas — 2026-08-15

Ocho puntos que estaban abiertos y quedaron cerrados o acotados en una sola vuelta.
Cada uno con quién decidió y contra qué evidencia. Las entradas del board apuntan acá.

---

## D-1 · Kaggle sale del programa (cierra P-07 y acota P-18)

**Decidió**: Nico, con la medición de abajo a la vista.

La pregunta era si había análisis que **sólo** se pueden hacer en Kaggle. Medido sobre
la máquina real (Ryzen 5 3600, 6c/12t, 16 GB):

| Recurso | Kaggle | Local | ¿Es cuello? |
| --- | --- | --- | --- |
| CPU | ~4 vCPU | 6c/12t | **No** — el árbol entero a `tick:1` con un kernel son ~4,1 h en 1 core; paralelizado por contrato (56 archivos independientes) es una fracción de eso. |
| RAM | ~30 GB | 16 GB | **Sí, sin podar.** `MNQ_03-26` pide **9,67 GiB** sólo para los datos crudos; podado baja a **5,80 GiB**. |
| GPU | sí | no | **No** para este programa. Nada acá lo usa. |

Podar las columnas duplicadas (D-2) elimina el único cuello real. **El programa entero
—store, EDA de rangos, cruzado multiactivo, herramientas de Kaggle corridas en local—
entra en esta máquina.**

Consecuencias, que son el verdadero premio:

- **P-07 (licencia M0) se cierra por reducción de alcance, no por dictamen legal.** Si
  no se sube nada, no hay distribución y el gate deja de bloquear. El gate de código
  (`ABSTAIN_LICENSE`) queda igual, como red de seguridad contra publicar por accidente.
- **P-18** deja de ser bloqueante para el pipeline. El residual —la V1 ya subida con
  ticks crudos y holdout físicamente presente— **no se disuelve solo**: la
  recomendación es **borrar el dataset V1 de Kaggle**, que cierra la exposición de una
  vez. Es acción de Nico; ninguna herramienta la hace.
- `research-v2` sigue teniendo todo su valor: es el firewall del holdout hecho físico,
  verificado en disco (56/56, `max(ts) <` apertura de sesión). Lo que se cae es
  publicarlo, no tenerlo.

**Lo que se pierde**: si en algún momento hace falta GPU (p. ej. la línea
`research/bigtrap2-multiframe-ml`), habrá que reabrir la discusión. Hoy F9 está pausada
y no hay ML autorizado, así que no aplica.

---

## D-2 · Podar las columnas duplicadas — verificado en el árbol completo

**Decidió**: Nico. **Evidencia**: `docs/research/verif_columnas_duplicadas_2026-08-15.json`.

Se verificó columna a columna, **fila por fila, en los 56 parquets** (no en los 11 del
manifiesto): `sequence == source_row` y `ts_local_ns == ts_utc_ns`.

```
archivos verificados : 56
filas totales        : 1.015.587.419
diferencias          : 0
VEREDICTO: PODABLE
```

Peso de lo redundante, medido en `MNQ_03-26` (el mayor, 103.825.550 filas):

| Columna | % del archivo comprimido | |
| --- | --- | --- |
| `sequence` | 24,23 % | duplicado exacto de `source_row` |
| `ts_local_ns` | 17,47 % | duplicado exacto de `ts_utc_ns` |
| `instrument` + `contract` + `source_file` | 0,07 % | constantes por archivo, ya en ruta y nombre |

**41,78 % del dataset son bytes duplicados.** En disco: 15,895 → **9,255 GiB**. En RAM
por contrato: 9,67 → **5,80 GiB**, que es lo que lo vuelve procesable acá.

Podar **no cuesta nada científicamente**: son idénticos byte a byte, no una
aproximación. Lo que sí hay que preservar es la advertencia de P-28 — `sequence` no es
secuencia del exchange, es índice de fila, y ningún análisis de microestructura que
asuma orden intra-timestamp está soportado por estos datos. Podar la columna no cambia
eso; sólo deja de pagar dos veces por el mismo dato.

---

## D-3 · P-28 sube de categoría

Ya no es «indistinguibilidad bajo la función de digesto del manifiesto» ni «probado en
11 de 56». Es **igualdad byte a byte en 1.015.587.419 filas, 56/56 archivos**, más las
22 comparaciones con pyarrow de `verify_tree.py --columns`. La limitación de
microestructura pasa a ser un hecho medido y se pre-registra como tal.

---

## D-4 · P-31 ítem 6: el evento nunca se quitó, el test caducó

**Resuelto por evidencia, no era decisión.**

`BARRA_PROCESADA` está en `nt8/BigTrap2.cs:549`, dentro de `DrenarPorOHLCV()`
(líneas 434–568), o sea en el camino de tick. Lo que cambió fue la emisora:

```
antes:  LogEvent("BARRA_PROCESADA", ...)
ahora:  LogEventAt(s.Time, "BARRA_PROCESADA", ...)
```

`LogEventAt` con timestamp explícito es coherente con el fix de frontera de sesión
(`f77a3be`, P-13): estampa el evento con la hora de la barra en vez de «ahora». **El
denominador existe y el invariante se cumple.**

El test se corrigió para verificar el invariante que su propio docstring declara —que
el evento se emita desde dentro de `DrenarPorOHLCV`— en vez de un nombre de función
incidental. **Queda más estricto, no más laxo**: sigue exigiendo posición, y ahora
además exige que sea una llamada de la familia `LogEvent*`. Verificado en negativo:
falla si la llamada se borra y falla si queda sólo como comentario.

Esto **no** es relajar un gate. El gate medía un literal; ahora mide la propiedad.

---

## D-5 · P-33: se resuelve por (a), no por (b)

**Decidió**: Nico.

(b) —sacar `*_prev_*` de `data/nt8/`— mueve datos y no arregla la causa: el resolvedor
seguiría buscando por nombre y volvería a fallar con el próximo par de homónimos.

(a) —resolver la fuente por carpeta declarada o por `source_sha256`— arregla la clase
entera y es **más estricto**: hoy acepta cualquier archivo que se llame igual; con (a)
sólo acepta el que cierra por hash contra el manifiesto, y la ambigüedad degrada a
aviso únicamente si ningún candidato cierra. (b) queda como higiene opcional posterior.

Recordatorio de por qué importa: el segundo candidato era
`654e006e483f62727dd2d52680e41b0c4c03531a3763471a1ba3532497883a06`, **uno de los dos
exports Z1 que el acta de cierre F2.7–F2.10 §1 prohíbe usar**.

---

## D-6 · P-32: el conjunto que entra al store

**Decidió**: Nico. Acepta declarar **paridad representativa** para el trío P-16.

Entran, cada uno con su estado declarado en el store (`integrity_state` / `parity_state`
por partición, así que nunca se confunde uno representativo con uno exacto):

| Indicador | Estado con el que entra |
| --- | --- |
| `BigTrap2` | paridad exacta |
| `aVolClusterPOI` v0.5 | paridad exacta |
| `Gaps2` v2.0 | **paridad representativa** |
| `AACloseOpenDiffs` v1.2 | **paridad representativa** |
| `VolTicksPOC2` v2.1 | **paridad representativa**, con la limitación de D-3 anotada |
| `HFTZones2` v2.3 | pendiente de paridad NT8 formal |
| `aVolCellPOI2` v2.0 | pendiente de paridad NT8 formal |

`YMPreRangeSweep` **no entra**: bloqueado por P-19…P-22 y ya se sabe que no es edge
(nulo browniano 54–76 %).

**Advertencia registrada sobre `VolTicksPOC2`**: su secuenciador causal no está portado
a `tick:N`, y con D-3 probado, las configs `tick:N` dependen de un orden intra-timestamp
que **estos datos no soportan**. Entra al store como feature fijada —eso es target-free—
pero sus configs de tick quedan marcadas con la limitación, y **no se promueve nada
desde ellas** sin resolver el secuenciador. Lo mismo aplica a `aVolCellPOI2`.

---

## D-7 · P-10: uno mergeado, dos siguen siendo de Nico

**Decidió**: Nico («mergeá lo que consideres»), con el criterio de abajo.

Los tres estaban agrupados bajo «semántica de validación» y no son equivalentes:

| Rama | Tamaño | Qué toca | Decisión |
| --- | --- | --- | --- |
| `docs/lux-imb-source-correction` | +771 | módulo nuevo + tests + docs de una familia bloqueada | **MERGEADA** |
| `research/ym-prerange-session-window` | +767/−340 | `edgelab/sessions.py`, infraestructura compartida | sigue abierta |
| `fix/g2-a1-*` | +2267/−1006 | `g2.py`, `g2_decision.py`, `promotion.py` y 500 líneas del contrato de validación | sigue abierta |

Se mergeó la primera porque **no toca gates ni promoción**, y porque no mergearla tenía
un costo activo: `CLAUDE.md` y el protocolo H-COND-1 seguían describiendo el bloqueo de
LUX-IMB como «el render borra zonas mitigadas», premisa que Nico retractó el
2026-08-11. Mantener una afirmación falsa en el documento rector no es prudencia.

Las otras dos no corren prisa —ninguna campaña las necesita hoy— y sí cambian semántica
compartida. Siguen requiriendo decisión explícita, una por rama.

---

## D-8 · Orden de trabajo que queda

1. Podar columnas → `research-v3` (árbol nuevo; los parquets son inmutables, no se
   parchean). Re-verificar con `verify_tree.py` contra su propio manifiesto.
2. Aplicar D-5 a `verify_tree.py` para que `FAIL_FUENTE` deje de disparar por layout.
3. Paridad NT8 formal de `HFTZones2` y `aVolCellPOI2` (exportar oráculos + correr).
4. Campaña declarativa al store por indicador × contrato × `bar_spec`, declarando N y
   costo antes de correr. `store_audit.py --all` (P3.7) antes de cualquier EDA.
5. EDA de rangos **como régimen ex-ante**, no como target de sweep.

Sin tocar: holdout, P&L, F4, y las dos ramas de P-10.
