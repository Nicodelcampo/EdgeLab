# Paridad de junio sobre GC 08-26 — precondición **SATISFECHA**, y dos defectos del instrumento

- **Fecha:** 2026-08-23 · **Base:** `fe43523`
- **Firewall:** outcomes `false` · junio **no abierto como outcomes** — esto es paridad de
  implementación, target-free
- **Cierra:** `specs/bt2_absorption_gate1_v1.json` → `parity_precondition`, que estaba en
  `BLOCKED_PENDING_ORACLE`
- **Artefacto:** `docs/research/PARIDAD_BT2_ABSORPTION_JUNIO_GC0826.json`

---

## 1. Resultado sobre la ventana **exacta** del pre-registro

`parity_precondition.window = [2026-06-18, 2026-06-30]`, `required_layers = [a_score, a_thr,
a_pass, zones, fills]`.

| capa | junio · GC 08-26 | agosto · GC 12-26 (firmado) |
|---|---|---|
| cubetas comparables | **35.928 / 35.928** | 27.328 / 28.042 |
| excluidas pre-ancla | **0** | 714 |
| **cobertura del export** | **100 %** | 97,45 % |
| `signed_flow` · `d_ticks` · `a_score` · `n_ticks` · `residual` | **35.928/35.928** cada uno | 27.328/27.328 |
| **`a_pass` · `n_hist` · `a_thr`** | **35.420 / 35.420** | 26.824 / 26.824 |
| capa residual D-2 (8 cortes) | **8 / 8** en los 4 campos | 4 / 4 |
| **zonas** | **488 / 488** | 365 / 365 |
| **fills** | **488 / 488** | 365 / 365 |
| `only_nt8` / `only_python` | **0 / 0** en todas | 0 / 0 |
| veredicto | **`PASSED_PUERTA_0`** | `PASSED_PUERTA_0` |

**Las cinco capas requeridas dan `EXACT`.** Es además la medición más grande hecha hasta hoy:
35.928 cubetas contra 27.328, y sobre el **100 %** del export en vez del 97,45 %.

⇒ `parity_precondition`: **SATISFECHA**. La paridad deja de ser un hecho de un contrato y pasa
a ser un hecho del kernel — dos contratos, dos meses, dos longitudes de sesión.

### 1.1 Insumos

| | |
|---|---|
| export completo | `bt2_absorption__AbsMagnitude__GC0826jun2__TW25.csv` · `ca178fa1e486924a…` · 44.919.109 B · 15 sesiones (`20260610`–`20260630`) |
| export recortado a la ventana | `5eee744f30b73aaa…` — línea `# meta` + todos los eventos desde la primera `BARRA_PROCESADA` con `td>=20260618` |
| cinta | `GC 08-26.Last.txt` · `f75dba6d32c4911b…` · 213.951.580 B · **4.525.912 ticks** |
| `.cs` / kernel | `18d16312…` / `0d162a60…` — sin cambios respecto de la firma |
| D-3 | pares zona↔fill validados, **0 violaciones** · D-4 procedencia `.cs` OK |

---

## 2. Defecto A — el loader truncaba en 700.000 ticks. **CORREGIDO**

`tools/sweep_bigtrap2_tickframes.py:25` tenía

```python
def load_canonical_ticks(filepath, tick_size=0.10, max_ticks: int = 700000):
```

y `verify_layer_parity.py` lo llamaba **sin pasar `max_ticks`**.

> **La cinta de la firma tiene 683.188 ticks. Quedó 16.812 por debajo del tope: un margen del
> 2,4 %.** Puerta 0 se firmó sin tocar el corte por casualidad.

Con `GC 08-26` (4.525.912 ticks) la corrida se rompía — pero **falló cerrado por accidente, no
por diseño**. Si la ventana del oráculo hubiera caído dentro de los primeros 700.000 ticks, el
ancla habría enganchado, la comparación habría corrido sobre una cinta truncada y el veredicto
habría salido `EXACT` sin que nada avisara.

### 2.1 El fix

```python
def load_canonical_ticks(filepath, tick_size=0.10, max_ticks=None, allow_truncation=False):
```

- **`max_ticks=None` por default**: no trunca.
- Si se pasa un tope y quedan líneas sin leer, **`ValueError`** salvo `allow_truncation=True`
  explícito. Verificado que dispara:
  `TRUNCAMIENTO en GC 08-26.Last.txt. max_ticks=700000 alcanzado con 3825912 lineas sin leer.`
- Las **líneas malformadas** también se descartaban en silencio; ahora se cuentan y se
  reportan.

Y en `verify_layer_parity.py`: **`--tape`** por CLI (la cinta ya no está hardcodeada a
`GC 12-26.Last.txt`) y `max_ticks=None` explícito.

### 2.2 Los otros dos caminos de pérdida: **medidos, limpios**

Antes de tocar nada medí los tres sobre los 4.525.912 ticks de `GC 08-26`:

| camino | medido |
|---|---|
| líneas malformadas descartadas | **0** |
| líneas con 7º dígito ≠ 0 (los `[16:22]` tiran 100 ns) | **0** |
| `int(dt.timestamp()*1e9)` ≠ aritmética entera exacta | **0** (0,0000 %) |

Los dos últimos son **frágiles, no seguros**: el ULP del `double` en este epoch es 238 ns y la
única razón de que no muerda es que este feed no usa el séptimo dígito. Misma familia que D-1
del auditor. **No los toqué** — están medidos en 0 y arreglarlos sin necesidad sería cambiar el
instrumento por gusto.

### 2.3 Prueba de no-regresión: **125 campos, 0 diferencias**

Cambié un instrumento firmado, así que re-corrí la paridad de agosto con el harness parchado y
comparé el JSON campo por campo contra `PARIDAD_BT2_ABSORPTION_PUERTA0_ABSMAGNITUDE.json`:

```
campos comparados : 125     (excluyendo timestamp y los tape_* nuevos)
DIFERENCIAS       : 0
```

27.328/27.328 · 26.824/26.824 · 4/4 · 365/365 · `PASSED_PUERTA_0`. **La firma de agosto se
reproduce exacta.**

⇒ El artefacto de junio **ya es reproducible desde el repo**, que era la deuda anotada en la
versión anterior de este documento.

---

## 3. Defecto B — **las primeras cubetas de una carga larga traen un batch de warmup**

Este apareció al usar el oráculo de 20 días, y es el hallazgo nuevo.

Con la carga de **12 días** (7 sesiones, `06-22`→`06-30`) la paridad daba **29.033/29.033,
100 %, anclando en `bar=1`**. Con la carga de **20 días** (15 sesiones, `06-10`→`06-30`),
anclando también en `bar=1`, el resultado se desmorona:

```
NT8 66.683 cubetas | Python 66.683 cubetas | comunes 967  (only_nt8 65.716, only_py 65.716)
```

### 3.1 No es pérdida de datos: los streams son idénticos

Ticks por sesión, NT8 contra cinta:

```
20260610  NT8 173.331  cinta 173.356   -25   <- borde: primera cubeta descartada
20260611 .. 20260629    13 sesiones      +0   <- identicas al tick
20260630  NT8  99.350  cinta  99.368   -18   <- borde: residual sin flushear
```

**13 de 15 sesiones coinciden exactamente.** Los dos desvíos son los bordes del export.

### 3.2 La causa, localizada al tick

La primera divergencia está en la **cubeta 2**:

```
[0] NT8 bar=1 t=22:00:00.752 n=25 | PY bar=1 t=22:00:00.752 n=25      <- coincide
[1] NT8 bar=2 t=22:00:01.400 n=25 | PY bar=2 t=22:00:01.528 n=25      <- diverge
```

Y la cinta desempata. Desde el ancla (índice absoluto `1.147.949`):

```
offset 12  ->  22:00:01.400   <- donde NT8 dice que arranca la cubeta 2
offset 25  ->  22:00:01.528   <- donde la cinta dice que esta el tick 25
```

> **La cubeta 1 de NT8 declara `n_ticks=25` pero consume sólo 12 ticks de la cinta. Vio 13
> ticks que la cinta no tiene.**

Re-anclar en el offset +12 tampoco cierra (90,54 % de `t_start`), así que el batch no está
confinado a la primera cubeta: contamina un tramo del arranque.

Es la familia **TICKBAR-001** — el mismo `AddDataSeries(Tick,1)` entregando ticks en lote en el
borde de la carga, documentado en `docs/parity_coverage/BigTrap2.md`.

### 3.3 La demostración controlada

Mismo oráculo, misma cinta, mismo harness. Lo único que cambia es dónde cae el ancla:

| ancla | cubetas comparadas | resultado |
|---|---:|---|
| `bar=1` (arranque de la carga) | 66.683 | **967 comunes** — desastre |
| primera cubeta de `20260618` | **35.928** | **35.928 / 35.928, `EXACT` en todo** |

**El kernel no tiene nada malo. El arranque de la carga sí.**

### 3.4 Regla operativa que se desprende

> **Un oráculo se exporta con una carga que empieza bastante antes de la ventana que se va a
> comparar, y el ancla nunca es `bar=1`.**

Es exactamente lo que pasó **por casualidad** en agosto: la cinta arrancaba 5 h después de la
apertura, el ancla cayó en `bar=715` y las 714 cubetas de warmup quedaron afuera solas. Lo que
allí fue suerte, acá queda como procedimiento.

**Corolario incómodo:** el resultado de 7 sesiones que reporté antes (29.033/29.033 anclando en
`bar=1`) fue correcto **por suerte**, no por método. Con esa carga el batch no apareció. No lo
uso como evidencia; la evidencia es la corrida de §1.

---

## 4. Inventario del censo: 133 sesiones

| contrato | sesiones | desde → hasta |
|---|---:|---|
| GC 04-26 | **55** | 2026-01-20 → 2026-03-26 |
| GC 06-26 | **49** | 2026-03-27 → 2026-05-26 |
| GC 08-26 | **29** | 2026-05-27 → 2026-06-30 |
| **TOTAL** | **133** | 2026-01-20 → 2026-06-30 |

Contra `power_planning.sessions_for_80pct_2_5_ticks = 133`. **Alcanza, sin margen.**

### 4.1 La regla de roll congelada no se puede aplicar

`universe.continuous_rule.confirmation` pide
`successor_volume_gt_current_for_2_consecutive_overlap_sessions`. Contrastada:

```
solape 04-26 -> 06-26                      solape 06-26 -> 08-26
  20260326  04-26=162.423  06-26= 62.855     20260526  06-26=101.634  08-26= 35.324
  20260327  04-26=  2.422  06-26=145.068     20260527  06-26=  1.603  08-26=145.701
            ^ ultima fecha de 04-26                    ^ ultima fecha de 06-26
```

**El sucesor gana una sola vez, y esa vez es el último día del predecesor en la cinta.** No hay
segundo día para confirmar.

No cambia el resultado —el cruce va de 2,6× a **60×** en un día, y de 2,9× a **91×** en el
segundo; no hay oscilación que filtrar— pero la regla necesita enmienda, y el solape no se
puede alargar: son los rangos completos de la db de NT8.

**Enmienda mínima propuesta:**

> …o, si la serie del predecesor termina antes de acumular las dos confirmaciones, el roll es
> efectivo en la primera sesión en que el sucesor supera al predecesor, **siempre que la razón
> de volúmenes sea ≥ 10×**. Ambos rolls la cumplen con holgura.

---

## 5. Estado

```
PUERTA_0                = FINAL_PUERTA0_SIGNED   (GC 12-26, agosto)
PARITY_PRECONDITION     = SATISFIED              (GC 08-26, 2026-06-18..06-30, 100%)
                          35.928/35.928 · 35.420/35.420 · 8/8 · zonas 488/488 · fills 488/488
LOADER_700K             = CORREGIDO, fail-closed, sin regresion (125 campos, 0 diffs)
HARNESS_TAPE            = --tape agregado; junio ya es reproducible desde el repo
WARMUP_DE_CARGA         = DEFECTO NUEVO documentado -> el ancla nunca es bar=1
CINTAS_CENSO            = 133 sesiones, 2026-01-20 -> 2026-06-30
ROLL_RULE               = INAPLICABLE tal como esta escrita -> enmienda propuesta en 4.1
B-9                     = PENDIENTE (a_thr por sesion y por bin de 30 min)
N_RAND                  = PREREGISTERED_NOT_RUN
OUTCOMES                = NOT_OPENED
```

---

## Aporte al referente

La precondición de Puerta 1 queda satisfecha sobre la ventana literal del pre-registro, con la
medición más grande del programa hasta hoy. Y el instrumento queda mejor que antes: el tope de
700 k pasa de truncar en silencio a fallar cerrado, con no-regresión probada campo por campo
sobre la firma existente.

Lo que más vale no es el `EXACT`: es la **demostración controlada** de §3.3. Mismo oráculo,
misma cinta, mismo harness, y el veredicto se da vuelta según dónde caiga el ancla. Eso
convierte «el arranque de la carga es sospechoso» de intuición en procedimiento.

## Nota de método

Tres defectos en dos días, todos de la misma forma: **un dato correcto, impreso, y nadie
preguntando por él.** El `a_score` del fill `11537_B`. El `dir` de los 377 eventos. Y ahora un
`max_ticks=700000` que sólo era inocuo por 16.812 ticks — un margen del 2,4 % entre una firma
válida y una firma sobre datos truncados que habría dicho `EXACT`.

Ninguno de los tres apareció revisando el razonamiento. **Los tres aparecieron al cambiar el
insumo.** El corolario práctico es que el mejor test de un instrumento de medición no es
auditarlo: es darle un caso que no vio antes.
