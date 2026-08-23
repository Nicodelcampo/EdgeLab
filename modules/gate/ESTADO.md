# ⚠ GATE — **CIMIENTO, NO MÓDULO TERMINADO**

> **Este directorio NO es código de producción de research.** Es una especificación
> ejecutable importada desde afuera del repo, subida **tal cual llegó**, para que se pueda
> auditar. **Nada de acá está validado sobre datos reales del lab.**

- **Fecha de ingreso:** 2026-08-23
- **Rama:** `research/gate-regime-context` — deliberadamente **separada** de
  `foundation/f0b-compatibility-probe`
- **Origen:** `GATE_MODULE_HANDOFF.zip`, producido fuera de este repo
- **Estado global:** `CIMIENTO_SIN_VALIDAR`
- **Firewall:** no toca outcomes, no toca holdout, no toca ningún `.cs`

---

## 0. Por qué está en una rama aparte

El propio checklist del módulo lo pide (`docs/GATE_INTEGRATION_CHECKLIST.md` §A):
*«Rama dedicada — no mezclar con fix de NT8»*.

**No está integrado a nada.** No se importa desde `edgelab/`, no lo llama ningún script de
`tools/`, y no participa de ninguna corrida de paridad ni de censo. Vive en `modules/` — fuera
del paquete importable — precisamente para que esa desconexión sea visible en el árbol.

---

## 1. Qué es GATE

**No es una señal ni un edge.** Es un **etiquetador de contexto**: para cada evento exportado
por un indicador, dice en qué régimen de mercado estaba el instrumento en el instante `t0`.

```
NT8 exporta el evento  ->  GATE etiqueta el regimen en t0  ->  trial pre-registrado CTX-3
```

Regímenes: `0=calmo 1=normal 2=volatil 3=toxico`. El tóxico **no** es un estado entrenado: es
un overlay de VPIN sobre 0,55.

`model_id`: `gate_tf_causal_bal_v2_feat10_sticky90_vpin055` — 10 features, atención **causal
only**, sticky 0,9, z-score calculado sólo con datos de entrenamiento.

---

## 2. Qué está validado y qué no — **esto es lo que hay que auditar**

| paso | el módulo declara | **sobre qué datos corrió de verdad** |
|---|---|---|
| 1 · schema + adapter causal | HECHO (smoke) | fixture sintético **+ ticks 6E reales** |
| 2 · target-free | HECHO (demo) | **sintético** + una corrida 6E |
| 3 · pre-registro CTX-3 | HECHO (plantilla) | **nada** — es una plantilla con huecos |
| 4 · incremental vs `pct_rv` | HECHO (demo) | **100 % sintético** |
| 5 · `model_id` congelado | HECHO | — (ver defecto G-1) |

### 2.1 La única corrida con datos reales

`runs_examples/from_real_ticks/summary.json`:

```
instrumento        6E 09-26        (NO ES, que es el instrumento del pre-registro CTX-3)
ticks              400.000
barras             10.317
eventos              859           <-- SINTETICOS: uno cada 12 barras, no del indicador
corr(regimen,ancho)  0,0139        -> OK_LOW_CORR
cobertura           10 sesiones por celda,  piso exigido = 40   -> NO CUMPLE
```

> **Los 859 eventos los fabricó el propio pipeline** (`from_ticks.events_from_bars`, uno cada 12
> barras, con `width_ticks = 2 + (i % 5)`). **No salieron de BigTrap2Absorption ni de ningún
> indicador.** El `OK_LOW_CORR` está medido contra un ancho inventado.

⇒ **El paso 2 no está hecho sobre datos reales del lab.** El módulo lo dice en su propio
handoff §3 (*«Bloqueante real: labels sobre export de eventos ES/6E del lab (no sintéticos)»*),
pero la tabla del roadmap lo marca HECHO. Se registra la discrepancia.

---

## 3. Tres defectos encontrados en la lectura de ingreso

### G-1 · `config_sha256` **no se deriva del contenido** — MEDIDO

`schema/gate_model_id_frozen.json` declara:

```json
"config_sha256": "61667366ed4eb5c537f0c16e4b1e9136720419d5aa5e21a61658201892a1f8e8",
"note": "Fill config_sha256 after hashing this file's canonical JSON (sorted keys, no null hash field)."
```

**El hash está puesto Y la nota dice que falta ponerlo.** Verificado: ninguna variante canónica
—sin el campo, sin todo `reproducibility`, con el campo en `null`, con dos convenciones de
separadores— reproduce el valor declarado.

```
declarado en el archivo            61667366ed4eb5c537f0c16e4b1e9136720419d5aa5e21a61658201892a1f8e8
canonico real (regla de la nota)   911c4dbfc26e3f619dac7a1a18da19132e94ed4df865f32798904a1ffaf1a30b
sha256 del archivo en disco        1b1333329ac9a9d4943881269f56259ab5dfacb79706db7a0f342edee3c05bf1
```

**Es un placeholder.** Corresponde al ítem C-4 del propio checklist, que está **sin tildar**
(*«Hash verificado en CI o script local antes de cada corrida formal»*).

Es exactamente **P-39**: una etiqueta de identidad que no verifica su contenido. **No lo
corregí** — cambiar un artefacto declarado congelado es decisión de Nico y del auditor, no mía.

### G-2 · El pipeline **inventa el régimen** si no se lo dan, y no falla

`integration/edgelab_gate_integration/pipeline.py::_ensure_regime_on_bars()`:

```python
if "regime" in bars.columns:
    return bars
# ... si no: proxy por terciles de rvol / ret / mid, y sigue adelante
```

Lo declara en `notes` del artefacto (*«a quantile proxy was used»*), pero **no aborta**. Produce
labels con apariencia normal, `as_of_ok=true` y todo, sobre un régimen que **no es el del
detector**.

Es la misma familia que el `max_ticks=700000` que encontramos hoy en el harness de paridad
(`docs/research/PARIDAD_JUNIO_GC0826_2026-08-23.md` §2): **un default que produce un resultado
plausible sin avisar que no es el que pediste.** Para cablear está bien; para una corrida formal
debería fallar cerrado salvo flag explícito.

### G-3 · El pre-registro CTX-3 está en blanco donde más importa

`research/H-ES-CTX-3_PREREGISTRO.md` §4:

> *«Métrica: la misma primaria de la familia activa (p. ej. delta pareada de `ticks_por_ancho`
> **o** AbsMagnitude — **una sola**; rellenar al congelar con el acta viva)»*

**El estimando primario no está fijado.** También quedan abiertos la estructura de Holm (1
contraste vs 2 pruebas) y el MDE por celda. CTX-3 **no es congelable** hasta que las tres sean
una frase sin ambigüedad.

---

## 4. ⚠ Restricción de orden respecto de Puerta 1 — **leer antes de correr nada**

`specs/bt2_absorption_gate1_v1.json` (rama `foundation/f0b-compatibility-probe`) declara:

```
context_policy.context_hypothesis_status              NONE_PREREGISTERED
context_policy.candidate_must_be_orthogonal_to        [a_thr, time_of_day, tick_rate]
context_policy.matched_control_with_context_without_indicator_required   true
firewall.forbidden[0]                                 post_null_subgroup_search
```

**GATE es un candidato de contexto.** Meterlo antes de que Puerta 1 corra agrega una hipótesis
de contexto a un estudio que declaró explícitamente no tener ninguna.

> **Orden vinculante: Puerta 1 primero, GATE después.**

Coincide con lo que el propio roadmap de GATE pide desde el otro lado
(`docs/GATE_ROADMAP.md`): *«No medir estimando de familia (AbsMagnitude / ticks_por_ancho) hasta
cerrar 1–3»*.

Y si GATE llegara a proponerse como contexto de la familia, tendría que demostrar ortogonalidad
contra los tres ejes que **ya están medidos** en
`docs/research/B9_CONTEXTO_BT2_ABSORPTION_2026-08-23.md`:

| eje | medido sobre 115 sesiones GC |
|---|---|
| `a_thr` entre sesiones | 3,18× |
| `a_thr` intradía | 1,39× |
| tick rate intradía | 7,58× |
| spread | **ya descalificado**: `corr(a_thr, spread) = −0,50` |

Los features de GATE incluyen `rvol`, `spread_z`, `phase_open/mid/close` y `sess_rel` — **cuatro
de los diez son proxies directos de hora del día y spread.** La ortogonalidad no se puede
asumir: hay que medirla.

---

## 5. Lo que sí está bien construido

No todo son defectos. Tres cosas que merecen reconocerse:

1. **`merge_asof` backward con fail-closed.** Si no hay barra `≤ t0`, `as_of_ok=false` y el
   evento se cae. Sin forward-fill. El schema prohíbe explícitamente usar `t1`, z-score de
   muestra completa y atención bidireccional en el path de labels.
2. **El filtro de contaminación es un criterio de parada real, calibrado contra un fracaso
   propio.** Si `|corr(régimen, ancho_ticks)| ≥ 0,25`, CTX-3 **no se congela** — el umbral sale
   de que CTX-2 rechazó «fase de sesión» con `corr ≈ −0,255`.
3. **El paso 4 pregunta lo correcto**: F parcial anidado, `H0: coefs_gate = 0 | pct_rv`. No es
   «¿GATE separa?» sino «¿GATE aporta **por encima de** `pct_rv`?». Es la misma lógica de control
   emparejado que `N_RAND` aplica en Puerta 1.

---

## 6. Qué habría que hacer para que deje de ser cimiento

En orden, y **todo después de Puerta 1**:

1. **Resolver G-1**: decidir si el `config_sha256` se corrige al valor canónico o si se declara
   por escrito que el campo no es verificable.
2. **Resolver G-2**: `_ensure_regime_on_bars` falla cerrado salvo `--allow-proxy-regime`.
3. **Paso 1 y 2 sobre eventos reales.** Ya existen: **6.206 eventos K_ABS sobre 152 sesiones**
   de GC, con `t0`, `session_id`, `side` y geometría, del universo enmendado
   (`docs/research/ENMIENDA_UNIVERSO_GATE1_2026-08-23.md`). Eso resuelve de una el bloqueante
   que el handoff declara, y con 152 sesiones supera el piso de 40 por celda.
   **Salvedad**: el pre-registro CTX-3 dice ES, y esto es GC. Hay que decidir si CTX-3 cambia de
   instrumento o si se espera un export de ES.
4. **Medir ortogonalidad de GATE** contra `a_thr`, hora del día y tick rate (§4).
5. **Recién entonces** rellenar el estimando de CTX-3 y congelar.

---

## 7. Inventario de lo subido

| carpeta | contenido | validado |
|---|---|:-:|
| `HANDOFF_ORIGINAL.md` | el handoff tal como llegó, sin editar | — |
| `docs/` | roadmap 1–5 + checklist de integración | — |
| `schema/` | schema v1 + `model_id` congelado | ⚠ G-1 |
| `core/` | adapter, target-free, incremental, generador sintético | sintético |
| `integration/` | CLI, aliases NT8, ticks→barras | ⚠ G-2 |
| `research/` | pre-registro CTX-3 | ⚠ G-3 |
| `runs_examples/` | smokes (fixture + 6E) | eventos sintéticos |
| `referencia/` | documento externo de método + su auditoría | ver §8 |

**No se modificó ningún archivo del zip original**, salvo renombrar `HANDOFF.md` →
`HANDOFF_ORIGINAL.md` para que este `ESTADO.md` sea lo primero que se lee. Los defectos G-1,
G-2 y G-3 están **documentados, no parcheados**.

---

## 8. Referencia externa incorporada

`referencia/Regimenes_Corta_Duracion_Edge_Investigacion.md` (sha256 `b96b3555774f7b50…`, 331
líneas) — relevamiento de método y bibliografía sobre regímenes de corta duración, adjunto de
un workspace externo. **Es la especificación de diseño que GATE implementa**: los diez features
del `model_id` congelado salen casi textuales de su §3.1, cosa que hasta ahora no estaba
justificada en ninguna parte.

Auditado en `referencia/AUDITORIA_DOC_REGIMENES_2026-08-23.md`. Hallazgo principal, que toca
directamente a este módulo:

> **G-4 · `ofi_ema_z` está mal nombrado.** El documento advierte explícitamente que OFI de libro
> y trade imbalance de tape *«no son intercambiables»*. Nuestra cinta (`last;bid;ask;volume`, sin
> tamaños ni eventos de libro) **no permite OFI**, y la única implementación del módulo
> (`from_ticks.py:58-69`) calcula `sign(agresor) × volumen` — imbalance de tape. Renombrarlo
> obliga a un **nuevo `model_id`** por la propia `change_policy`.
>
> El L2 que sí permitiría OFI existe (12 sesiones de GC DEC26) pero tiene **cobertura 0 del
> universo front-month**. Es descargable: 2,1 GB comprimidos para las 152 sesiones.

La app web que acompañaba al documento **no se subió**: 100 % de datos sintéticos, nunca corrió
sobre datos reales.

---

## Aporte al referente

El módulo entra al repo auditable en vez de quedar en un zip, con la distancia entre lo que
declara y lo que corrió medida y escrita: de los cinco pasos marcados HECHO, **uno tiene datos
reales y con eventos fabricados por el propio pipeline**. Y se deja anotada la restricción de
orden que ninguno de los dos pre-registros ve por sí solo: GATE es un candidato de contexto para
una familia cuyo estudio declaró `NONE_PREREGISTERED`, así que el orden entre los dos no es
preferencia sino condición de validez.

## Nota de método

G-1 y G-2 son la misma clase de defecto que apareció tres veces hoy del lado de EdgeLab: **una
etiqueta que no verifica su contenido y un default que produce resultado plausible sin avisar.**
Que aparezcan también en un módulo escrito por fuera sugiere que no es un descuido local — es
lo que pasa cuando el artefacto se escribe antes de que exista el dato que lo llenaría.
