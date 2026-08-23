# Paridad de junio sobre GC 08-26 — **cierra la deuda de Puerta 0**, y aparece un defecto del harness

- **Fecha:** 2026-08-23 · **Base:** `5aede17`
- **Firewall:** outcomes `false` · **no se abrió junio como outcomes** — esto es paridad de
  implementación, target-free
- **Cierra:** la deuda declarada en `FIRMA_FINAL_PUERTA0_BT2_ABSORPTION_2026-08-23.md` §7
  («la firma es sobre GC 12-26; el censo corre sobre junio, que no tiene paridad medida»)
- **Artefacto:** `docs/research/PARIDAD_BT2_ABSORPTION_JUNIO_GC0826.json`

---

## 1. Resultado: 100 %, y con **mejor cobertura que la firma de agosto**

| capa | junio · GC 08-26 | agosto · GC 12-26 (firmado) |
|---|---|---|
| cubetas comparables | **29.033 / 29.033** | 27.328 / 28.042 |
| **excluidas pre-ancla** | **0** | 714 |
| **cobertura del export** | **100 %** | 97,45 % |
| `signed_flow` / `d_ticks` / `a_score` / `n_ticks` / `residual` | **29.033/29.033** cada uno | 27.328/27.328 |
| umbral causal post burn-in | **28.527 / 28.527** | 26.824 / 26.824 |
| capa residual D-2 | **6 / 6** en los 4 campos | 4 / 4 |
| zonas | **394 / 394** | 365 / 365 |
| fills | **394 / 394** | 365 / 365 |
| `only_nt8` / `only_python` | **0 / 0** en todas | 0 / 0 |
| veredicto | **`PASSED_PUERTA_0`** | `PASSED_PUERTA_0` |

**Cero excluidas pre-ancla** es la diferencia importante: la cinta arranca **antes** que el
export (2026-05-24 contra 2026-06-21), así que el ancla cae en `bar=1` y se compara el export
**entero**. En agosto la cinta arrancaba 5 h después de la apertura CME y quedaban 714 cubetas
sin cotejar.

⇒ **La paridad ya no es sólo de GC 12-26.** Está medida en dos contratos distintos, dos meses
distintos y dos longitudes de sesión distintas, con el mismo `.cs` y el mismo kernel.

### 1.1 Insumos

| | |
|---|---|
| export | `bt2_absorption__AbsMagnitude__GC0826jun__TW25.csv` · `e4a3c60b0390…` · 19.776.429 B |
| meta | `version=1.1.1`, `score_mode=AbsMagnitude`, `tape_window=25`, `tick_size=0.1`, 1 sola meta, `seq` monotónico hasta 74.128 |
| ventana | `2026-06-21T19:00:01` → `2026-06-30T17:59:22` ART · 7 sesiones (`20260622`…`20260630`) |
| cinta | `GC 08-26.Last.txt` · **`f75dba6d32c4911b952c1d873ead7b1d75b42e288345b6039a2d6697ccc96cb6`** · 213.951.580 B · **4.525.912 ticks** |
| `.cs` / kernel | `18d16312…` / `0d162a60…` — sin cambios respecto de la firma |
| D-3 | 397 pares zona↔fill validados, **0 violaciones** |
| D-4 | procedencia `.cs` OK (892 L repo == 892 L instalado) |

---

## 2. ⚠ Defecto encontrado: **el loader trunca en 700.000 ticks**

`tools/sweep_bigtrap2_tickframes.py:25`

```python
def load_canonical_ticks(filepath: Path, tick_size: float = 0.10, max_ticks: int = 700000):
```

y `tools/verify_layer_parity.py:165` lo llama **sin pasar `max_ticks`**.

> **La cinta de la firma, `GC 12-26.Last.txt`, tiene 683.188 ticks: quedó 16.812 ticks por
> debajo del tope.** Puerta 0 pasó sin tocar el corte por un margen del 2,4 %.

Con `GC 08-26.Last.txt` (4.525.912 ticks) el loader entrega 700.000 y la corrida **se rompe**
—`tape_slice_idx = None` → `TypeError`—, porque la ventana del oráculo (21–30 de junio) cae
fuera de los primeros 700.000 ticks (que llegan a principios de junio).

**Falló cerrado por accidente, no por diseño.** El caso peligroso es el otro: si la ventana del
oráculo hubiera caído **dentro** de los primeros 700.000 ticks, el ancla habría enganchado, la
comparación habría corrido sobre una cinta truncada y el veredicto habría salido `EXACT` sin
que nada avisara. Es P-39 otra vez: el nombre `load_canonical_ticks` no dice «canónica hasta
700 k».

### 2.1 Consecuencia para el censo

**Bloqueante.** Las tres cintas del censo superan el tope por un factor grande:

| cinta | ticks | ¿pasa el tope? |
|---|---:|:-:|
| `GC 04-26.Last.txt` | ~6,7 M | **no** |
| `GC 06-26.Last.txt` | ~4,5 M | **no** |
| `GC 08-26.Last.txt` | 4.525.912 | **no** |

Corrido tal cual, el censo mediría **los primeros 700 k ticks de cada contrato** y reportaría
sesiones que no existen en el resultado. Hay que resolverlo **antes** de correrlo.

### 2.2 Fix propuesto — **no aplicado**

No parcheo el instrumento. Consistente con lo que el propio proyecto decidió para `features.py`
(*«cambiar la API mientras se redacta su manifiesto es cambiar el instrumento durante la
medición»*), y acá además el instrumento está **firmado**.

Propuesta, para que la decida Nico y el auditor:

1. `load_canonical_ticks` **falla cerrado** si trunca: si llega a `max_ticks` con líneas
   pendientes, `raise` en vez de devolver una cinta parcial silenciosa. Es el arreglo que
   convierte el defecto en imposible, no sólo en improbable.
2. `verify_layer_parity.py` toma **`--tape`** por CLI en vez de tener `GC 12-26.Last.txt`
   hardcodeado en la l. 124, y pasa `max_ticks` explícito.

Los dos son mecánicos y ninguno toca kernel ni `.cs`.

### 2.3 Y por eso este artefacto **no es reproducible desde el repo**

El JSON de junio se produjo con una **copia parchada** del harness, fuera del repo, con
exactamente dos cambios: la ruta de la cinta y `max_ticks=50_000_000`. Está declarado en el
propio JSON (`_provenance_warning`).

**El resultado es válido y está medido; la reproducibilidad por un tercero no está.** Hasta que
entre el fix de §2.2, este artefacto es de menor rango que el de agosto. Lo digo acá para que
no se lea como equivalente.

---

## 3. Inventario del censo: **133 sesiones**, encadenadas por volumen

Las tres cintas nuevas, con el roll resuelto por volumen día a día (no por calendario):

| contrato | sesiones | desde → hasta |
|---|---:|---|
| GC 04-26 | **55** | 2026-01-20 → 2026-03-26 |
| GC 06-26 | **49** | 2026-03-27 → 2026-05-26 |
| GC 08-26 | **29** | 2026-05-27 → 2026-06-30 |
| **TOTAL** | **133** | 2026-01-20 → 2026-06-30 |

**Contra las ~113 que el auditor calculó** para detectar un efecto tamaño BigTrap2 (+0,053).
Alcanza, con margen.

### 3.1 Los rolls no son ambiguos

Las seis fechas en disputa se resuelven con 3–6× de diferencia de volumen:

```
20260323 -> 04-26   (04-26: 327.430  vs  06-26:  58.625)
20260324 -> 04-26   (04-26: 176.574  vs  06-26:  33.988)
20260325 -> 04-26   (04-26: 176.140  vs  06-26:  39.820)
20260326 -> 04-26   (04-26: 162.423  vs  06-26:  62.855)
20260525 -> 06-26   (06-26:  44.958  vs  08-26:  10.808)
20260526 -> 06-26   (06-26: 101.634  vs  08-26:  35.324)
```

Ninguna está cerca del empate.

Y la garantía del auditor se mantiene: **ningún camino cruza sesión**, así que el roll no puede
contaminar un evento.

### 3.2 ⚠ La regla de roll congelada **no se puede aplicar**: el solape es demasiado corto

El auditor congeló: *«dos sesiones completas consecutivas con mayor volumen del contrato
sucesor, roll efectivo en la sesión siguiente y sin volver atrás»*. Contrastada contra las
cintas, **nunca se dispara**:

```
solape 04-26 -> 06-26  (5 fechas)         solape 06-26 -> 08-26  (4 fechas)
  20260323  04-26=327.430  06-26= 58.625    20260524  06-26=  8.103  08-26=  1.247
  20260324  04-26=176.574  06-26= 33.988    20260525  06-26= 44.958  08-26= 10.808
  20260325  04-26=176.140  06-26= 39.820    20260526  06-26=101.634  08-26= 35.324
  20260326  04-26=162.423  06-26= 62.855    20260527  06-26=  1.603  08-26=145.701  <- gana
  20260327  04-26=  2.422  06-26=145.068 <- gana   (ultima fecha de 06-26 en la cinta)
            (ultima fecha de 04-26 en la cinta)
```

**El sucesor gana una sola vez, y esa vez es el último día del predecesor en la cinta.** No hay
un segundo día para confirmar: la regla pide dos consecutivas y la data se termina en la
primera.

**Por qué no importa para el resultado, y por qué sí importa para la regla.** El cruce no es
ruidoso: pasa de 2,6× a favor del predecesor a **60×** a favor del sucesor en un día (y de 2,9×
a **91×** en el segundo roll). La regla de dos confirmaciones existe para protegerse de un
cruce oscilante; acá no hay oscilación que filtrar. El roll queda en `20260327` y `20260527` sin
ambigüedad, que es exactamente donde lo puso el argmax por volumen de §3.

Pero **la regla, tal como está escrita, es inaplicable a estos insumos** y hay que enmendarla.
Y el solape no se puede alargar: la db de NT8 tiene GC 04-26 hasta `20260327` y GC 06-26 hasta
`20260527` — son sus rangos completos, no un recorte del export.

Enmienda mínima propuesta, para que la decida el auditor:

> …o, si la serie del predecesor termina antes de acumular las dos confirmaciones, el roll es
> efectivo en la primera sesión en que el sucesor supera al predecesor, **siempre que la razón
> de volúmenes sea ≥ 10×**. Ambos rolls de esta cadena la cumplen con holgura (60× y 91×).

---

## 4. Estado

```
PUERTA_0            = FINAL_PUERTA0_SIGNED   (GC 12-26, agosto, 97,45% del export)
PUERTA_0_JUNIO      = PASSED                 (GC 08-26, junio, 100% del export)
                      -> artefacto NO reproducible desde el repo (ver 2.3)
CINTAS_CENSO        = LISTAS  -> 133 sesiones, 2026-01-20 -> 2026-06-30
ROLL                = RESUELTO por volumen, sin empates
LOADER_700K         = DEFECTO ABIERTO, BLOQUEANTE del censo, fix propuesto sin aplicar
MEZCLA_DIRECCIONAL  = 54,6 / 45,4  (medida, estable, no sigue el drift)
UMBRAL_1,25         = A RECALIBRAR contra el nulo a esa mezcla
CENSO_JUNIO         = NOT_RUN
OUTCOMES            = NOT_OPENED
```

---

## Aporte al referente

La paridad deja de ser un hecho de un contrato y pasa a ser un hecho del kernel: dos contratos,
dos meses, dos longitudes de sesión, `EXACT` en las dos, y en junio sobre el **100 %** del
export en vez del 97,45 %. Y el censo tiene 133 sesiones disponibles contra las ~113 que la
potencia exige — la restricción que parecía dura resulta que ya estaba resuelta en el disco.

## Nota de método

El tope de 700.000 del loader convivió con una cinta de 683.188 ticks. Un margen del 2,4 % es
lo único que separó a Puerta 0 de haberse firmado sobre una cinta truncada sin que nadie lo
notara — y el modo de falla no habría sido un error, habría sido un `EXACT`. Es el tercer caso
en dos días de la misma familia: `a_score` impreso y descartado en el fill `11537_B`, `dir`
impreso y nunca contado, y ahora un default que sólo era inocuo por 16.812 ticks. **Ninguno de
los tres se encontró revisando el razonamiento; los tres aparecieron al cambiar el insumo.**
