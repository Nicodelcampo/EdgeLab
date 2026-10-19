# Iteración 4 — Grok 4.5 — adjudicación adversarial de la relajación de `seq` en P5

**Fecha:** 2026-08-06 · **Autoría:** Grok 4.5, sin editar.
**Alcance pedido:** una sola pregunta — si una regresión real puede quedar en
PASS por haber sacado `seq` del criterio de FAIL.
**Por qué existe:** la enmienda N1 es la única **relajación de gate** del día, y
la regla *"el que implementa no aprueba su propia reparación"* estaba incumplida.

> Devuelto en markdown por Grok y commiteado por Claude sin modificar el
> contenido. Las reparaciones que provocó están en el commit que acompaña.

---

## 1. ¿Puede una regresión REAL pasar como PASS?

**Confirmación (parcial).** En el camino de tiempo (`fpTicksPerBar <= 0`) el
único `FOOTPRINT_MISMATCH` relevante es `VerificarOHLC` (~601). Tras el mismatch
el drenaje hace `continue` y no llama `EmitirBarra`. Por tanto: si el predicado
cambia y cambia el conjunto de barras emitidas → cambian `TRAP`/`ZONE_*` →
`len(ea)!=len(eb)` o tipo/ts/campos → **FAIL**. Si el stream económico es el
mismo con otro conteo de diagnósticos → sólo corre `seq` → PASS con
`seq_corrido=true`, que es el caso que justificó la relajación.

**Refutación — la relajación no es "sólo seq": P5 nunca miró la regresión de
atribución no económica.** `P5_TIPOS_ECONOMICOS` excluye `FOOTPRINT_MISMATCH`,
`ANCLAJE_*`, `BARRA_PROCESADA`, `SESION_RESINCRONIZADA`, `ERROR`. Cualquier
regresión que altere sólo diagnósticos, o que cambie el orden/conteo de
no-económicos sin mutar la subsecuencia económica filtrada, **ya daba PASS antes
de tocar `seq`**. El agujero es el predicado de P5, no el contador. Eso no
invalida la relajación; sí impide vender P5 como "bit-identidad del EventLog".

| Escenario | ¿FAIL sin `seq`? | ¿FAIL con `seq`? |
|---|---|---|
| Mismo stream económico, más/menos no-económicos | PASS | FAIL (`seq`) |
| Mismo stream económico, reorden sólo de no-económicos | PASS | FAIL (`seq`) |
| Cambia un `TRAP`/`ZONE_*` (tipo/ts/campos/cantidad) | FAIL | FAIL |
| Atribución rota pero mismas zonas/traps emitidos | PASS | PASS |

**No encontré un camino en el que cambie un campo económico o desaparezca un
evento económico y P5 quede PASS.**

**Veredicto G1:** no refuto la relajación como puerta para regresiones
económicas; sí refuto la lectura de que P5 "sigue gritando toda regresión real
del camino de tiempo".

## 2. ¿Basta publicar el corrimiento, o es trampa silenciosa?

**Confirmación.** Se publican `seq_corrido`, `delta_seq_min/max`,
`delta_seq_distintos`, `footprint_mismatch_por_lado`. No es borrar evidencia: el
FAIL por `seq` se sustituye por telemetría.

**Refutación / hueco de proceso.** Nada exige que un wrapper trate
`seq_corrido=true` como bloqueo de promoción o de pin. Si el ritual de captura
sólo mira PASS/FAIL, **el corrimiento es invisible en la práctica**. Es el modo
de falla recurrente —número publicado, nadie lo consume—: no un bug del `if seq`,
sino del **contrato de lectura del resultado**.

**Hallazgo.** `footprint_mismatch_por_lado` es conteo global de tipo, **no
emparejado con el zip económico**. Sirve como alarma gruesa, no como prueba de
que el corrimiento se explica sólo por FM. Falta algo del estilo
`n_no_economicos` por lado.

**Veredicto G2:** alcanza para no ser trampa **de código** si el preflight obliga
a leer `seq_corrido`. Si no, es trampa **de proceso**.

## 3. ¿`delta_seq_distintos` truncado a 20 oculta no-uniformidad?

**Confirmación.** La no-uniformidad (`min != max`) siempre es visible: `min` y
`max` se calculan sobre la lista entera, sin truncar.

**Hallazgo (sexta instancia del modo "listado incompleto").**
`sorted(set(delta))[:20]` muestra sólo los 20 valores distintos **menores**. Con
más de 20, la cola alta no aparece, y **no hay `n_delta_seq_distintos`**: se
pierde la cardinalidad y la forma del conjunto — la diferencia entre 2 modos de
corrimiento y 200.

**Veredicto G3:** no refuto "siempre se ve un delta no uniforme"; sí hay pérdida
de catálogo si `len(set(delta)) > 20`.

## 4. Sexta instancia del modo de falla habitual

El test se vende como detector de regresión del camino de tiempo, pero el FAIL
sólo mira la proyección económica, el corrimiento pasa a telemetría **sin gate**,
y no hay aserción de que `seq_corrido ⇒ explicación FM`. **El nombre del gate
promete más de lo que su predicado alcanza.** Misma familia que las ramas con
fixture que no llega al FAIL.

## Resumen

| # | Clase | Conclusión |
|---|---|---|
| 1 | Confirmación acotada | No vi camino en que cambie la subsecuencia económica y P5 quede PASS por sacar `seq` |
| 1b | **Refutación de overclaim** | P5 no cubre regresiones sólo-diagnóstico; era cierto antes y sigue |
| 2 | Confirmación condicional | La telemetría evita la trampa **si el proceso prohíbe ignorarla** |
| 3 | **Hallazgo** | `distintos[:20]` trunca el catálogo con >20 deltas |
| 4 | **Hallazgo** | Sexta forma del patrón: PASS con evidencia lateral no enforceable |

**Sobre la decisión de Nico:** no la refuto como "abre un hueco para zonas/traps
distintos con PASS". Sí dejo constancia de que es segura **sólo** como "P5 =
igualdad de subsecuencia económica ordenada", no como igualdad de EventLog, y de
que el corrimiento debe ser condición de revisión humana o de ABSTAIN/FAIL de
política, **no un campo decorativo**.

**Desacuerdo registrado (no votado):** si `seq_corrido=true` con económicos
idénticos debe ser **PASS, ABSTAIN o FAIL de política** — eso es contrato, no se
deduce del código.
