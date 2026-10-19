# PRED-007 — **S1 REFUTADA.** La saturación no era un artefacto de la población

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado
**Artefacto:** `diag/tasa_senales/censo_primeros_toques.json`
**Preregistro:** `docs/predictions/PRED-007_D3_sobre_primeros_toques.json`

---

## 1. Resultado

201 sesiones · 4 contratos · población **autoritativa** (primeros toques) ·
`sep_min = 120`

| indicador | cru/ses *(creac.)* | post/ses *(creac.)* | superv. | **cru/ses** | **post/ses** | **superv.** |
|---|---:|---:|---:|---:|---:|---:|
| BigTrap2 | 79,37 | 8,84 | 11,1 % | **77,54** | **9,08** | **11,7 %** |
| aVolCellPOI2 | 42,34 | 6,50 | 15,4 % | **41,73** | **6,71** | **16,1 %** |
| VolTicksPOC2 | 7,31 | 3,41 | 46,6 % | **7,13** | **3,47** | **48,6 %** |

*(las tres primeras columnas son el censo de CREACIONES, diagnóstico; las tres
últimas el de PRIMEROS TOQUES, autoritativo)*

**Dispersión post-`sep_min`: 2,59 → 2,62.** Prácticamente idéntica.

## 2. Las cinco predicciones

| # | esperado | medido | estado |
|---|---|---|---|
| **S1** | dispersión **mayor** que 3,2 | **2,62** | **REFUTADA** |
| **S2** | supervivencias más dispersas | 11,7 / 16,1 / 48,6 contra 11,1 / 15,4 / 46,6 | **REFUTADA** |
| **S3** | 5 indicadores admitidos | **3** | **REFUTADA** |
| **S4** | `AACloseOpenDiffs` sin población, no censo de cero | clasificado aparte | **CONFIRMADA** |
| **S5** | reportar `MIN_STUDENTIZED_SESSIONS = 160` | 201 · 199 · 177 — **los tres pasan** | **CONFIRMADA** |

## 3. Qué significa

**La saturación de `sep_min` es real y no depende de la población.** Medir sobre
la población correcta —primeros toques, la que la enmienda declara autoritativa—
da los mismos números que medir sobre creaciones, con diferencias de 2-3 %.

Eso **refuerza** el mecanismo que D3 describía: `sep_min = 120` no filtra señales
malas, satura. Lo que queda después del filtro está gobernado por cuántas
ventanas de 2 h entran en una sesión, no por el indicador.

Dato colateral: las tasas **crudas** también son casi idénticas entre poblaciones
(77,54 contra 79,37; 41,73 contra 42,34; 7,13 contra 7,31). Para estos tres
indicadores **casi toda zona creada llega a tener su primer toque**, así que las
dos poblaciones tienen tamaño parecido. Es coherente con que sus zonas nacen
cerca del precio —14,3 %, 22,2 % y 18,3 % ya lo contienen al quedar disponibles—
sin llegar al 75 % de `Gaps2`.

## 4. Y sin embargo D3 no bloquea §3.3

El reencuadre de `docs/research/D3_REENCUADRE_2026-08-09.md` se sostiene, y ahora
con la medición hecha: **la spec no selecciona por tasa.** v0.3 Paso 3 dice
*«No se selecciona un argmax»*. La tasa entra como una columna de la tabla de
diseño, con función de **factibilidad y potencia**.

Y en esa función el resultado es favorable: **los tres superan
`MIN_STUDENTIZED_SESSIONS = 160`** — 201, 199 y 177 sesiones con al menos una
señal. Que la tasa no discrimine no impide congelar H1–H3; sólo impide usarla
para ordenarlos, que es algo que la spec nunca pidió.

## 5. Estado de H1–H3

| | indicador | población autoritativa | sesiones c/señal |
|---|---|---|---|
| **H1** | `BigTrap2` | **9,08/ses** | 201 |
| **H2** | `aVolCellPOI2` | **6,71/ses** | 177 |
| **H3** | `Gaps2` | **RECHAZADO** (invariante) | — |

**La alerta de H2 se cierra.** `aVolCellPOI2` produce 8.387 primeros toques sobre
177 sesiones. El `raw_count = 0` del piloto era de la ventana de 6 sesiones, no un
defecto. **H2 se sostiene.**

Para H3, §6.4 fija la alternativa outcome-free entre `HFTZones2` y
`VolTicksPOC2`; `HFTZones2` cae por el mismo invariante, así que el único tercero
posible es **`VolTicksPOC2`** (3,47/ses, 199 sesiones). No lo propongo como
decisión: la regla exige documentarlo con la tabla del Paso 2 delante.

## 6. Alcance de esta corrida — declarado

Se corrió **sólo con los tres admisibles**. `Gaps2` y `HFTZones2` no figuran en
`rechazados` porque no se ejecutaron: su rechazo está documentado en el piloto de
6 sesiones y en `ff59472`, reproducido dos veces, y es determinista —el invariante
falla en la primera zona—. Correrlos sobre 201 sesiones para obtener el mismo
rechazo era gasto puro.

**Y no es una hipótesis: es lo que costó.** La primera corrida, con los seis,
estuvo **10,3 h** sin terminar el primer contrato, paginando —CPU al 55 % del
reloj, 1,96 GB paginados contra 173 MB residentes—. Con los tres admisibles el
trabajo real fueron **3 minutos**. Las diez horas eran enteramente los dos
indicadores que se descartan.

## 7. Errores de operación de esta corrida

**Lancé los seis sabiendo que dos serían rechazados.** El piloto los había
rechazado horas antes. Debí acotar desde el principio.

**Mi propio encadenador disparó `recuento_kT` en paralelo.** Para frenarlo escribí
`EXIT=CANCELADO_POR_PAGINACION` en el log, pero su condición era
`grep -q "^EXIT="` — esa línea la **cumple**, así que en vez de detenerlo lo
lancé. Verifiqué 3 segundos después y concluí «no arrancó», cuando el vigilante
consulta cada 60. Resultado: dos trabajos pesados compitiendo con 153 MB libres.
Detenido antes de que levantara sus cuatro workers.

Ninguno de los dos afecta el resultado —el censo corrió solo y cerró con
`EXIT=0`— pero los dos costaron tiempo de máquina y quedan registrados.

## 8. Qué sigue

`recuento_kT.py` sigue **sin correr**. Es el Paso 1 de §7 y produce la
**frecuencia corregida** con `k_T > 0`, que es la columna que falta de la tabla
del Paso 2. Su predicción está registrada en el módulo desde antes: *«la
frecuencia corregida no se mueve más de ~0,2 % en las celdas candidatas»*, con la
regla de lectura correcta —si sale muy distinto, buscar un defecto en ese código
antes que anunciar un hallazgo—.

Conviene correrlo **solo**, y evaluar `--workers` contra la memoria libre real:
con 8 GB y este censo pidiendo 1,7 GB, cuatro workers son un riesgo de paginación.
