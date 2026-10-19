# Revisión del clon — qué estaba resuelto, qué no, y una afirmación falsa

**Fecha:** 2026-08-05 · **Motivo:** dos resúmenes de LLM sobre avances del clon.
**Nada abierto:** sin outcomes, sin holdout, sin NT8.

> Los dos resúmenes se verificaron contra el repo. **Uno es correcto y aporta
> algo que yo no había considerado. El otro es falso en su punto decisivo.**

---

## 1. FALSO — «la paridad de ticks está resuelta, el error cayó a 0,00 %»

El resumen dice que `BigTrap2.cs` v2.2 llevó el error de **89,12 % a 0,00 %** y
concluye que *"BigTrap2 ya está desbloqueado para operar en barras de ticks"*.

**Es falso.** La cronología, con cita:

| fecha | qué pasó | fuente |
|---|---|---|
| 2026-07-24 | gate P2 **FAIL**, footprint corrupto en charts de tick, **89,12 %** | `holdout_access_log.md:12` |
| 2026-07-27 | v2.2 implementado, suite verde, **«sin gastar un solo oráculo»** | `REPORTE_NOCHE_2026-07-27.md:9` |
| 2026-08-04 | se gastó el oráculo. **K=25 → 3,91 %. K=10 → 81,78 %** | `REPORTE_LOCAL_2026-08-04g.md:17-18` |

El reporte del 27 dice literalmente **«sin gastar un solo oráculo»** y titula su
tabla **«Condiciones para gastar oráculo»**. O sea: v2.2 estaba implementado y
verde en tests sintéticos, y **la captura real no se había corrido todavía**.

Cuando se corrió, el resultado fue:

> **P1** — «0 % sobre barras interiores» → **3,91 %. REFUTADA.**
> **P2** — «si funciona en `tick:25` pero no en `tick:10`, era un parche atado a
> N=25 y se rechaza» → **81,78 % en K=10. REFUTADA.**

El **0,00 % no aparece en ningún documento**. El 89,12 % es la medición
**anterior** al fix. El resumen tomó un reporte que dice explícitamente que no
midió, y reportó el resultado esperado como logrado.

**Y hay un detalle que lo confirma:** las corridas 2 y 3 con K=10 son idénticas
fila por fila — el defecto es **determinista**, no ruido. Con K=10 se crearon
**cero zonas**.

Dos correcciones más del mismo resumen:

- *«el warm-up descarta la primera sesión»* — esa regla **se retiró**. Medida
  contra el defecto real dejaba el veredicto a 0,05 puntos del umbral y borraba
  hasta el 80 % de la evidencia (bloqueante B2). Hoy el warm-up es por
  `BARRA_PROCESADA`.
- v2.2 fue **superada por v2.3**, cuyo propio comentario dice que el enfoque de
  v2.2 *era* el defecto: *«NO se pre-corta a K por orden de llegada. Ese corte
  era el defecto: bastaba un evento de desfase para que TODOS los bloques
  siguientes quedaran mal, y el conteo no lo delataba porque seguía dando K.»*

**Conclusión: PRED-004 sigue bloqueando a BigTrap2 en barras de tick.** El fix
v2.3/v2.4 está implementado y **nunca compilado ni capturado**.

---

## 2. CORRECTO, y desbloquea mi recomendación — 7 de 8 oráculos en PASS

Verificado en `REPORTE_NOCHE_2026-07-27.md:49-60`:

| oráculo | estado | zonas |
|---|---|---|
| Gaps2 | ✅ PASS | 1316 / 1316 |
| BigTrap2 `time:1` (O1) | ✅ PASS | 225 / 225 |
| BigTrap2 `wick off` (O3) | ✅ PASS | 393 / 393 |
| BigTrap2 `SameLevel` (O2′) | ✅ PASS | 425 / 425 |
| HFTZones2 v2.3 | ✅ PASS | 1599 / 1599 |
| AACloseOpenDiffs v1.2 | ✅ PASS | 1803 / 1803 |
| VolTicksPOC2 (warmup) | ✅ PASS | 23 / 23 |
| **aVolCellPOI2 v2.1** | ⛔ **DATA_INTEGRITY_FAIL** | 140 / 144 / 117 |

Esto es lo que yo **no había considerado** y es justo lo que hacía falta para
resolver la cautela que había dejado abierta.

### La cautela se disuelve: normalizar los contratos NO puede romper la paridad

Yo había advertido que tocar lo que emite un kernel podría invalidar su oráculo,
y que había que verificarlo por indicador. **Verificado, y la respuesta es
general:**

`edgelab/bridge/parity.py::match_zones(py_zones, nt8_zones, ...)` consume
**`zones`**, no `events`. Y en las 160+ líneas del módulo:

```text
grep -c zone_id      edgelab/bridge/parity.py  ->  0
grep -c touch_count  edgelab/bridge/parity.py  ->  0
```

El emparejamiento es por `created_ms` y geometría. **La paridad nunca lee
`zone_id` ni `touch_count`.**

Además, en `avolcellpoi2.py:225-230` la línea del CSV ya hace `str(zone_id)`; el
valor crudo entero está **sólo** en el dict de `events`. O sea que el arreglo
—`str()` en el dict— toca exclusivamente la estructura que consume el censo.

> **La salida A es segura para los cuatro indicadores con falla de tipo, y está
> verificado, no supuesto.** `VolTicksPOC2` y `aVolCellPOI2` son un `str()`;
> `Gaps2` y `HFTZones2` son exponer como campo tipado el ordinal que ya calculan
> y hoy entierran en `"epoch=" + str(...)`.

`AACloseOpenDiffs` sigue aparte: no tiene concepto de toque, y eso es diseño.

### Salvedad sobre `aVolCellPOI2`

Su oráculo está en **`DATA_INTEGRITY_FAIL`**, no en PASS, y por una causa
declarada: *el bloque duplicado de 06-22 → 07-02 cae justo donde iría el
warm-up*. El reporte es explícito: **`DATA_INTEGRITY_FAIL`, no `KERNEL_FAIL`**, y
**«no se toca el parquet para conseguir un PASS»**. Arreglar su `zone_id` no
resuelve eso — son dos bloqueos independientes.

---

## 3. Otros avances reales que tampoco estaban considerados

**Censo de integridad — el detector tenía un falso negativo.** Se reescribió con
hash rodante vectorizado y aparecieron duplicaciones **nuevas** en `6E_09-26` y
`6E_06-26` que antes pasaban desapercibidas (`REPORTE_NOCHE:93-120`).

**Atlas de excursiones nulas — construido.** Es el placebo contra el que se mide
si un indicador supera al azar (`REPORTE_NOCHE:125-213`), con intervalos por
bootstrap de bloques diarios y estratos de franja horaria × volatilidad rezagada
en `runs/atlas/atlas_null.json`. Su validación interna es elegante: **un 50/50
tiene que dar 0,5, y lo da.**

**Esto cambia mi respuesta anterior sobre la distancia al edge.** Yo no lo había
contado, y es una de las piezas que hacía falta: sin el nulo, un acierto del 45 %
no se puede interpretar.

**Kronos** corrió y no fue eliminado por el filtro de redundancia. Pide OK de
Nico para el paso con P&L, que las reglas prohíben sin autorización.

---

## 4. Coordinación — una discrepancia que se resolvió mientras escribía esto

Al verificar (tip `efe0397`) los archivos que la otra máquina pedía traer **no
estaban como los describía**: `post_sepmin.json` tenía 20 sesiones y 2 contratos
—último commit `6838f9b`— y `post_sepmin.run_manifest.json` **no existía**. El
dato de 201 vivía sólo en `post_sepmin_rapidos.json`, con cuatro indicadores.

**Se resolvió solo:** la otra máquina pusheó `2f8fb9b` (*"CENSO COMPLETO — 6
indicadores × 201 sesiones"*) y `bd75e37` mientras yo escribía. Verificado
después del rebase:

```text
post_sepmin.json  ->  201 sesiones, 4 contratos, 6 indicadores   ✅
post_sepmin.run_manifest.json  ->  existe                        ✅
```

Se deja registrado porque **el aviso de la otra máquina llegó antes que los
archivos**, y quien hubiera hecho `pull` en esa ventana se habría llevado el
piloto de 20 días creyendo tener el censo completo. No es un error de nadie: es
una carrera entre el aviso y el push.

Y un detalle a favor: el manifiesto ya traía
`population_note: "cuenta creaciones; no equivale automaticamente a first_touch"`
— alguien de ese lado ya había visto lo mismo que encontré por separado.
