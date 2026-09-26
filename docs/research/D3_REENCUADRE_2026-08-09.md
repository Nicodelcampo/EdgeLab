# D3 reencuadrada — la tasa nunca fue el criterio de selección

**Fecha:** 2026-08-09 · Outcome-free. Sin holdout. Sin NT8.
**Origen:** Nico pidió avanzar con D3 «revisando detenidamente». La revisión
encontró tres cosas que cambian el problema antes de medir nada.

---

## 1. Lo que decía D3

> *«La tasa post-`sep_min` no discrimina entre indicadores. Crudas en factor 83,
> post-filtro colapsando a 3,2. Consecuencia: no sirve como criterio de selección
> de indicador.»*

La conclusión operativa que se arrastró desde ahí fue que **§3.3 estaba bloqueada
por una decisión de criterio**.

## 2. Hallazgo 1 — el documento de D3 está desactualizado

`docs/D3_CENSO_AUTORITATIVO_PRIMEROS_TOQUES.md` (2026-08-05) concluye
*«sólo `BigTrap2` produce la población autoritativa»* y propone un **camino A**:
normalizar el contrato de eventos.

**Ese camino ya estaba recorrido.** El commit `1f0f62d`, de esa misma noche,
normalizó `zone_id` a string en `voltickspoc2` y `avolcellpoi2`, y expuso
`touch_count` tipado en `gaps2` y `hftzones2` —el ordinal que ya calculaban,
enterrado en texto libre `"epoch=N"`—. Verificado en fuente: cinco de seis
cumplen el contrato hoy.

Estuve a punto de implementar algo hecho hace cuatro días. Lo frenó el pedido de
revisar con cuidado, no mi propia lectura.

## 3. Hallazgo 2 — el criterio de selección de la spec **no es la tasa**

`ESPEC_TEST_EXPLORE-001_v0.3.md`, Paso 3:

> `H1` `BigTrap2` ≈ `T=34`; `H2` `aVolCellPOI2` ≈ `T=21`; `H3` `Gaps2` ≈ `T=34`,
> condicional a sus gates. Los valores exactos se fijan con la tabla corregida,
> sin outcomes. **No se selecciona un argmax.**

Dos consecuencias:

1. **Las hipótesis ya están propuestas.** No hay una selección pendiente entre
   seis candidatos; hay tres nombrados y una tabla que los valida o los baja.
2. **La tasa no ordena nada.** Entra como **una columna** de la tabla de diseño
   del Paso 2 —junto a `k_T == 0`, cobertura, MDE, gate direccional y estado de
   paridad— y su función es **factibilidad y potencia**, no ranking.

> **D3 preguntaba si la tasa discrimina lo suficiente para elegir. La spec no
> elige por tasa. La pregunta es inaplicable.**

Lo que la tasa sí decide es si una celda tiene **potencia suficiente**:
`MIN_STUDENTIZED_SESSIONS = 160` y el MDE. Para eso no hace falta que discrimine
entre indicadores — hace falta que cada uno supere su umbral por separado.

## 4. Hallazgo 3 — el rechazo de `Gaps2` y `HFTZones2` no es un umbral estricto

El censo autoritativo los rechaza por el invariante `touch_bar > created_bar`:
registran un «toque» en la misma barra que crea la zona. Ya estaba diagnosticado
en `ff59472` y deliberadamente sin parchear; mi piloto lo reprodujo de forma
independiente.

**Relajar el criterio no los rescataría**, y la razón está medida en las sondas
de hoy — fracción de zonas que **ya contienen al precio** cuando quedan
disponibles:

| indicador | 8 sesiones | 40 sesiones |
|---|---:|---:|
| **Gaps2** | **75,1 %** | **74,7 %** |
| **HFTZones2** | **67,1 %** | **64,4 %** |
| aVolCellPOI2 | 22,2 % | 32,7 % |
| VolTicksPOC2 | 18,3 % | 21,2 % |
| BigTrap2 | 14,3 % | 10,6 % |

En tres de cada cuatro zonas de `Gaps2`, el precio **ya está adentro** cuando la
zona nace. Para esas, «primer toque posterior a la creación» no es un evento raro
que el gate esté filtrando de más: **es un evento que no significa lo mismo**. El
precio no llega a la zona — la zona nace donde el precio ya está.

Es el mismo hallazgo que disparó la sonda de alejamiento: *«una reentrada sin
salida previa no es una reentrada»*.

Si se relajara el invariante, `Gaps2` entraría con ~260 señales/sesión que en su
mayoría serían toques instantáneos y vacuos. **No sería más señal que `BigTrap2`:
sería otro evento.** El gate no los castiga — los distingue.

## 5. Estado real de H1–H3

| | indicador | estado en el censo autoritativo |
|---|---|---|
| **H1** | `BigTrap2` | **admitido** |
| **H2** | `aVolCellPOI2` | **admitido** *(ver §6)* |
| **H3** | `Gaps2` | **RECHAZADO** por el invariante |

§6.4 de la spec anticipa exactamente esto:

> *«También es válido ejecutar sólo dos hipótesis si ningún tercer mecanismo
> cumple los gates. Completar "tres" no justifica admitir una hipótesis mal
> definida.»*

Y fija la alternativa **outcome-free**: si `Gaps2` falla, el tercero se decide
con la misma regla entre `HFTZones2` y `VolTicksPOC2`. `HFTZones2` está rechazado
por el mismo invariante, así que **el único tercero posible es `VolTicksPOC2`**
—admitido, y el único cuya tasa post-filtro decía algo del indicador (46,6 % de
supervivencia contra 1,8 % de `AACloseOpenDiffs` sobre creaciones)—.

**No lo propongo como decisión tomada.** La regla exige documentar por qué, y esa
documentación se escribe con la tabla del Paso 2 delante.

## 6. Lo que falta, y una alerta

El censo autoritativo sobre las 201 sesiones está corriendo. Produce la **tabla
del Paso 2**, que es lo que la spec pide y lo que nunca se midió sobre la
población correcta.

> **Alerta abierta.** En el piloto de 6 sesiones, `aVolCellPOI2` salió
> `status=COMPLETE, raw_count=0, zero_raw_sessions=6` — el kernel produjo **cero
> eventos**. Sobre creaciones producía 42/día. Un cero con formato de dato es
> exactamente el patrón que `efe0397` corrigió para `AACloseOpenDiffs`. Si sobre
> las 201 sesiones sigue en cero, **no es baja frecuencia: es otro defecto**, y
> deja a H2 sin población. Hay que mirarlo antes de leer cualquier tasa suya.

## 7. Qué decido y qué no

**Decido** registrar que D3, tal como está formulada, es **inaplicable**: la spec
no selecciona por tasa. Lo que bloqueaba §3.3 no era un criterio pendiente sino
una tabla que no se había producido sobre la población autoritativa.

**No decido** cuál es el tercer candidato, ni si se corre con dos. Eso exige la
tabla completa y es de Nico y del auditor.

**No toco** `Gaps2` ni `HFTZones2`. Cambiar cuándo cuenta un toque altera su
serie `lifecycle`, que está en `PARAM_SPEC` y por contrato nunca puede quedar
cubierta por paridad ajena: habría que rehacer sus oráculos. Y no resolvería el
75 %.

**Advertencia de método.** Definir ahora un evento a medida para los rechazados
—por ejemplo reentrada tras salida, que sí tiene sentido económico para zonas que
nacen sobre el precio— sería elegir el criterio **con la curva de los demás a la
vista**. Es la misma razón por la que la spec dejó a `AACloseOpenDiffs` afuera. Si
se hace, con enmienda fechada y antes de mirar un solo outcome.
