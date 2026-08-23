# Auditoría independiente y adversarial — Puerta 0 · BigTrap2Absorption

- **Fecha:** 2026-08-23 · **Auditor:** Claude Opus 5, pasada independiente
- **Rama:** `foundation/f0b-compatibility-probe` · **HEAD:** `67ca337` (= tip mínimo exigido)
- **Árbol:** limpio en todo lo auditado (`edgelab/`, `tools/verify_layer_parity.py`, `nt8/`, `docs/research/`)
- **Firewall:** outcomes `false` · MFE/MAE/retornos/barreras/SL/TP/P&L **no abiertos** · junio **no abierto** · agosto usado sólo para identidad de implementaciones
- **Cambios al repo en esta pasada:** ninguno fuera de este documento. No se tocó kernel, `.cs`, harness ni artefactos.

> **No me apoyé en los resúmenes previos.** Re-corrí el harness, re-derivé cada
> número desde el código y los datos, y medí por separado cada chequeo adversarial.

---

# PARTE 1 — Auditoría independiente de Fase A

## 1.0 Reproducción de los números declarados

Re-corrida de `tools/verify_layer_parity.py` en `67ca337`. **Los veinte números
declarados reproducen exactamente**, sin excepción:

| magnitud | declarado | re-corrida | |
|---|---:|---:|:-:|
| `parsed_nt8_score_events` | 28.042 | 28.042 | ✅ |
| `parsed_python_score_events` | 27.329 | 27.329 | ✅ |
| `excluded_before_anchor` | 714 | 714 | ✅ |
| `excluded_after_export` | 1 | 1 | ✅ |
| `comparable_total` | 27.328 | 27.328 | ✅ |
| `only_nt8` / `only_python` | 0 / 0 | 0 / 0 | ✅ |
| `duplicate_score/zone/fill_keys` | 0 / 0 / 0 | 0 / 0 / 0 | ✅ |
| `signed_flow`, `d_ticks`, `a_score`, `n_ticks`, `residual` | 27.328/27.328 c/u | idem | ✅ |
| burn-in (cubetas no residuales) | 500 | 500 | ✅ |
| `a_pass`, `n_hist`, `a_thr` | 26.824/26.824 c/u | idem | ✅ |
| zonas / fills post burn-in | 626/626 · 626/626 | idem | ✅ |

**Determinismo confirmado por diff:** el JSON reescrito por mi re-corrida difiere
del commiteado en **un solo campo — `timestamp`**. Todos los valores medidos son
byte-idénticos. Restauré el artefacto a `HEAD` después de comprobarlo.

```
- "timestamp": "2026-08-23T05:53:01.112365+00:00",
+ "timestamp": "2026-08-23T06:02:59.623345+00:00",
   (unica linea del diff)
```

Hashes verificados en la re-corrida — coinciden con el JSON:

```
.cs    18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641
kernel 0d162a6092c31228ec0f4f9539b4afc0cb5031737263db4369dea2ad03697ab2
export c6eaeb210eeb029930f8157ac76380954700eed80dd5bf5b05df18a5ee9c19d7
```

## 1.1 Tabla PASS/FAIL por chequeo exigido

| # | chequeo | veredicto | evidencia |
|:-:|---|:-:|---|
| 1 | la clave `(global_bar, t_start_utc)` no depende circularmente del resultado esperado | **PASS** | §1.2 |
| 2 | `global_bar = first_matched + local − 1` válido en los 4 cortes residuales | **PASS** | §1.3 |
| 3 | precisión de `parse_art_to_utc_ns` | **FAIL — defecto D-1** | §1.4 |
| 4 | burn-in de 500 cubetas **no residuales**, no 500 números de barra | **PASS parcial — defecto D-2** | §1.5 |
| 5 | emparejamiento `nt8_fills[i] ↔ nt8_zones[i]` con assertions | **FAIL — defecto D-3** | §1.6 |
| 6 | el veredicto general incluye las diez dimensiones | **PASS** | §1.7 |
| 7 | el visor dice `PARCIAL`, no `EXACT` | **PASS** | §1.8 |
| + | P-34: identidad `.cs` repo ↔ instalado | **PASS con hueco — D-4** | §1.9 |

## 1.2 Chequeo 1 — no hay circularidad · **PASS**

- Lado NT8: `key = (int(s["bar"]), parse_art_to_utc_str(s["t_start"]))`. Ambos
  componentes salen **del export**. No tocan la salida de Python.
- Lado Python: `global_bar = first_matched_bar + loc_bar − 1`. El único término
  importado es `first_matched_bar`, que sale del ancla — y el ancla se busca
  recorriendo los `ABS_SCORE` del export contra `tape_ts_map`, construido desde
  **la cinta**. **En ningún punto entra la salida del kernel Python.**

No hay circularidad. La clave es una alineación por offset entre dos
numeraciones independientes, anclada por coincidencia de timestamp con la cinta.

## 1.3 Chequeo 2 — el offset resiste los cuatro cortes · **PASS, y es autoverificante**

Medido: los `ABS_SCORE` con `residual=True` en el export son **exactamente 4**
— los cuatro cortes de sesión.

El punto fuerte del diseño: la clave es **compuesta**. Si el offset se corriera
en cualquier corte, todas las claves posteriores dejarían de coincidir por su
componente `t_start_utc`, y aparecerían en `only_nt8` / `only_python`. Ambos
conjuntos valen **0 sobre 27.328/27.328 comparables**.

> La afirmación «el offset es constante» **no está asumida: está falsada y
> sobrevivió** en todo el rango comparable. Este es el acierto central del harness.

## 1.4 Defecto D-1 — `parse_art_to_utc_ns` pierde precisión · real, **impacto nulo medido**

```python
return int(dt_utc.timestamp() * 1_000_000_000) + ns_extra
```

`datetime.timestamp()` devuelve `float`. En el epoch de agosto 2026 (~1,787e9 s)
el **ULP de un `double` es 238,4 ns** — más grande que el dígito de 100 ns que la
función suma aparte. Medido contra una referencia entera (`timedelta`, sin float):

| | |
|---|---|
| muestras sintéticas evaluadas | 200.000 |
| discrepancias | **193.723 = 96,86 %** |
| peor error | **240 ns** |

**Pero sobre los datos reales el impacto es cero, y está medido:**

| | |
|---|---|
| `t_start` reales en el export | 28.042 |
| donde `harness ≠ exacto` | **0 (0,000 %)** |
| séptimo dígito (100 ns) en esos 28.042 | **`0` en el 100 %** |

Corrí además el ancla completa con **las dos** implementaciones: ambas dan
`posición 714 → bar NT8 715` y **el mismo conjunto de 27.328/28.042 (97,45 %)**.

> **Los 714 excluidos pre-ancla NO son un artefacto del float.** Fue mi primera
> hipótesis y la fuente la desmintió: el parser exacto excluye los mismos 714.

**Por qué igual es un defecto que hay que cerrar:** la benignidad depende de dos
accidentes —que la cinta traiga granularidad de microsegundo y que el redondeo
del `double` caiga favorable en los 28.042 casos—. Ninguno está garantizado para
otra cinta, otro instrumento u otra ventana. Secundario:
`.replace(tzinfo=ZoneInfo(...))` es la forma frágil de localizar; hoy es inocua
porque Argentina no tiene DST desde 2009, pero rompe en cualquier tz con DST.

**No bloquea Fase A** — y no podría haber fabricado el PASS: un error de parseo
produce *fallos* de match, no coincidencias falsas, y `duplicate_score_keys = 0`
descarta colisiones.

## 1.5 Defecto D-2 — la capa de umbral causal **nunca evalúa los 4 cortes de sesión**

El burn-in **sí** cuenta cubetas no residuales, no números de barra:

```python
if s.get("residual") == "False":
    burn_in_count += 1
    if burn_in_count > burn_in_target:
        post_burnin_score_keys.append(key)
```

**Pero el `append` está dentro del `if residual == "False"`.** Consecuencia: las
cubetas residuales **nunca** entran al conjunto comparado, estén antes o después
del burn-in. La aritmética lo confirma exactamente:

```
27.328 comparables - 500 burn-in - 26.824 post-burn-in = 4
                                                         ^ los 4 cortes de sesion
```

> **Las 4 cubetas residuales están en la capa aritmética (27.328/27.328) pero
> quedan fuera de `a_pass` / `n_hist` / `a_thr`.** Son exactamente las cubetas de
> mayor riesgo para un bug de reinicio de sesión en el historial de absorción, y
> son las únicas que la capa causal no mira.

Cobertura perdida: 4/27.328 = 0,015 %. **No bloquea** el enunciado de regresión
direccional, pero el JSON no debería llamar `EXACT` a una capa que excluye la
clase de cubeta que más probablemente rompería.

## 1.6 Defecto D-3 — emparejamiento posicional zona↔fill sin ninguna assertion

```python
for i, f in enumerate(nt8_fills):
    z = nt8_zones[i]
    c_bar = int(z["created_bar"])
```

**No existe ninguna de las cinco assertions exigidas.** Además hay un
`IndexError` latente si `len(nt8_fills) > len(nt8_zones)`, y desalineación
silenciosa si es menor.

Verifiqué el supuesto empíricamente sobre el export probado:

| invariante | resultado |
|---|---|
| `count(ZONE_CREATED)` == `count(FILL)` | **647 == 647** ✅ |
| `signal_at(fill)` == `available_at(zona)` (normalizados UTC) | **0 violaciones** ✅ |
| `side(fill)` == `side(zona)` | **0 violaciones** ✅ |
| `seq(fill) > seq(zona)` | **0 violaciones** ✅ |

> El supuesto **se sostiene de hecho** en este export. El defecto es que **no está
> verificado por el código**: es un invariante no declarado del `.cs` del que el
> harness depende en silencio. Vector de corrupción acotado —sólo `created_bar`
> viaja por el emparejamiento posicional; `sig_utc` y `side` salen del propio
> fill— pero un `created_bar` errado desplaza el fill de partición.

**No bloquea Fase A** porque está medido y da 0. **Sí bloquea Fase B** sin las
assertions: nada garantiza que se sostenga en otra corrida.

## 1.7 Chequeo 6 — el veredicto general cubre las diez dimensiones · **PASS**

`regression_verdict: PASSED_PUERTA_0` se emite sobre: `flow`, `d_ticks`,
`a_score`, `n_ticks`, `residual`, `a_pass`, `n_hist`, `a_thr`, `zonas`, `fills`,
más `only_nt8 == only_python == 0` y `duplicate_* == 0` (estas últimas como
`assert`, que detienen la corrida). El JSON declara además
`headline_validated: false` y `tested_hypothesis: "AbsDirectional regression parity"`.

**El artefacto es honesto sobre su propio alcance.** No presenta la regresión
direccional como el headline.

## 1.8 Chequeo 7 — el visor dice PARCIAL · **PASS**

`tools/visor_server.py:68`:

```python
"BigTrap2Absorption": ("PARCIAL", "AbsDirectional exacto sobre cobertura comparable
 (27.328 cubetas, 626 zonas/fills post burn-in EXACT 100%); headline AbsMagnitude pendiente")
```

Etiqueta correcta y glosa correcta.

## 1.9 Defecto D-4 — hueco en la cadena de procedencia del `.cs` (P-34)

| | sha256 |
|---|---|
| `nt8/BigTrap2Absorption.cs` (repo, hasheado por el JSON) | `18d16312…` |
| instalado en NT8 (`OneDrive\Documentos\...\Indicators\`) | `0af1f759…` |

**Difieren.** Diagnóstico: el `diff` es **exactamente y sólo** el bloque
`#region NinjaScript generated code` (57 líneas, 893–949) que NT8 autogenera.
Verificado:

```
sha256 de las primeras 892 lineas del INSTALADO = 18d163123662dc...  (identico al repo)
tools/check_nt8_cs.py  repo      -> [OK]   892 lineas CRLF, 0 regiones
tools/check_nt8_cs.py  instalado -> [WARN] 949 lineas CRLF, 1 region generada
```

> **El kernel que corrió ES el kernel del repo.** La región sólo registra
> sobrecargas de fábrica; no puede alterar el resultado. **No es violación de
> fondo de P-34.**

El hueco es documental: el JSON registra un `cs_sha256` que **no coincide con
ningún archivo existente en NT8**, así que un tercero no puede cerrar la cadena
por hash sin re-derivar el recorte de 892 líneas, como tuve que hacer yo. El JSON
debería registrar además `cs_installed_sha256` y `cs_kernel_lines`.

Nota de ubicación: el `.cs` vive en `OneDrive\Documentos\NinjaTrader 8\`, **no**
en `Documents\NinjaTrader 8\`. Los `exports\`, en cambio, sí están bajo
`Documents\NinjaTrader 8\exports\`. Las dos rutas conviven y el harness usa una
de cada árbol.

## 1.10 Veredicto de Fase A

```
FASE_A_DIRECTIONAL_ACCEPTED
```

**Defectos bloqueantes: ninguno.** Ninguno de los cuatro pudo fabricar el PASS:

- **D-1** produce fallos de match, no coincidencias falsas; medido en **0** sobre datos reales.
- **D-2** *reduce* cobertura (−4 cubetas); no infla el resultado.
- **D-3** verificado empíricamente con **0 violaciones** en los 647 pares.
- **D-4** es documental; el kernel es byte-idéntico.

**Lo que Fase A establece:** la regresión `AbsDirectional` tiene paridad exacta
`.cs`↔Python sobre 27.328 cubetas comparables (97,45 % del export), con las cinco
capas aritméticas al 100 %, umbral causal al 100 % sobre 26.824 post-burn-in, y
626/626 zonas y fills, con conjuntos laterales vacíos y cero claves duplicadas.

**Lo que Fase A NO establece:** nada sobre el headline. `AbsMagnitude` no fue
ejecutado por NT8 en ningún export existente — verifiqué los dos disponibles y
**ambos declaran `score_mode=AbsDirectional`**.

**Los cuatro defectos deben cerrarse ANTES de Fase B**, no por Fase A. Ver §2.2:
Fase B tiene un vector de PASS silencioso que Fase A no tenía.

---

# PARTE 2 — Protocolo de Fase B: headline `AbsMagnitude`

## 2.1 Auditoría previa del `.cs` — la rama existe y es correcta

**B1 — `ScoreMode=AbsMagnitude` ejecuta `|signed_flow| / (1 + |d_ticks|)`: ✅ VERIFICADO.**

`nt8/BigTrap2Absorption.cs:351-362`:

```csharp
double dPx = (double)(s.CloseTick - s.OpenTick);   // diferencia ENTERA de ticks
double denom;
if (ScoreMode == BT2AbsScoreMode.AbsDirectional) {
    double sgn = signedFlow > 0 ? 1.0 : (signedFlow < 0 ? -1.0 : 0.0);
    denom = 1.0 + Math.Max(0.0, sgn * dPx);
} else {
    denom = 1.0 + Math.Abs(dPx);          // <-- AbsMagnitude
}
double aScore = Math.Abs(signedFlow) / denom;
```

Espejo exacto en `edgelab/bridge/indicators/bigtrap2absorption.py:232-239`
(`denom = 1.0 + abs(d_ticks)`; `a_score = abs(signed_flow) / denom`). Mismo orden
de operaciones, mismos operandos. `dPx` sale de una resta **entera** de ticks: no
hay exposición de representación en el denominador.

**B2 — el meta incluye `score_mode`: ✅ VERIFICADO.** `.cs:754`,
`",score_mode=" + ScoreMode`, dentro del `# meta` que se escribe una sola vez por
apertura.

**B3 — corrida única: ✅ VERIFICADO POR DISEÑO.** `OpenLog()` (`.cs:733-771`):

- inserta `__TW<N>` en el nombre automáticamente;
- **auto-incrementa** `_2`, `_3`, … mientras el archivo exista (`for k=2; File.Exists(path) && k<1000`);
- abre con `new StreamWriter(path, false)` sobre una ruta que por construcción no existe ⇒ **nunca append, nunca overwrite**;
- `eventSeq++` monotónico — verificado en el export probado: monotónico hasta 71.927, **un solo `# meta`**;
- fail-closed: si la apertura falla, `eventWriterFailed = true` y avisa *«la corrida NO produce evidencia»*.

**B4 — los demás params del meta coinciden con el headline: ✅ VERIFICADO** en el
export direccional (`tape_window=25`, `absorption_pct=90`, `absorption_lookback=500`,
`min_history=200`, `min_stacked_rows=2`, `min_trap_frac=0.2`,
`require_flow_side_match=True`). El único que debe cambiar es `score_mode`.

**B5 — el arnés usa el modo declarado por el meta: ✅ PERO NO ES FAIL-CLOSED.** Ver §2.2.

## 2.2 ⚠ El vector de PASS silencioso de Fase B — **hay que cerrarlo antes de correr**

```python
run_params = dict(DEFAULTS)
if "score_mode" in meta: run_params["ScoreMode"] = meta["score_mode"]
```

y en el kernel: `DEFAULTS["ScoreMode"] = "AbsMagnitude"`.

| escenario | Fase A (direccional) | Fase B (headline) |
|---|---|---|
| el meta trae `score_mode` | correcto | correcto |
| **el meta NO lo trae** | Python corre AbsMagnitude vs export AbsDirectional ⇒ **falla ruidosamente** | Python corre AbsMagnitude vs export AbsMagnitude ⇒ **PASA sin haber verificado nunca que NT8 corrió esa rama** |

> **En Fase A el fallback fallaba fuerte; en Fase B pasaría en silencio.** Es el
> mismo código y el riesgo se invierte. **`assert meta["score_mode"] == "AbsMagnitude"`
> es obligatorio antes de correr Fase B**, no una mejora opcional.

## 2.3 Instrucciones exactas para Nico en NT8

**Precondición** — dejar el `.cs` instalado en v1.1.1 sin recompilar cambios:
las primeras 892 líneas del instalado deben hashear `18d163123662dc0e…`.
No editar el `.cs`.

**Parámetros del indicador** (el que difiere del direccional en **negrita**):

| parámetro | valor |
|---|---|
| **ScoreMode** | **`AbsMagnitude`** |
| TapeWindowTicks | `25` |
| AbsorptionPct | `90` |
| AbsorptionLookback | `500` |
| MinHistoryBuckets | `200` |
| MinStackedRows | `2` |
| MinTrapFrac | `0.20` |
| RequireFlowSideMatch | `true` |
| TicksPerRow `1` · ImbalanceMode `Diagonal` · TrapVolumeSource `AggressiveSide` · ImbalanceRatio `3.0` | |
| MinDeltaFilter `0` · MinTrapVolume `0` · MinExportVolume `1` | |
| UseWickFilter `true` · WickZonePct `30` · InvalidationMode `CloseThrough` · MaxAgeBars `2000` · MaxTouches `0` | |

**`EventLogPath`** — escribir exactamente:

```
C:\Users\nicoc\Documents\NinjaTrader 8\exports\bt2_absorption__AbsMagnitude.csv
```

> **El indicador agrega `__TW25` solo.** El archivo resultante será
> `bt2_absorption__AbsMagnitude__TW25.csv`, que es el nombre pedido. **No escribir
> `__TW25` a mano** o saldría `..._AbsMagnitude__TW25__TW25.csv`.

**Datos y ventana:** GC DEC26, misma ventana target-free de agosto que el
direccional (la cinta de paridad es
`OneDrive\Documentos\DataNT8\GC 12-26.Last.txt`, 683.188 ticks). **Merge de
contratos: desactivado.** **No abrir junio.**

**Después de exportar, verificar antes de entregar:**

1. Que el archivo se llame `bt2_absorption__AbsMagnitude__TW25.csv` **sin sufijo `_2`**.
   Si aparece `_2`, es que ya existía uno: borrar el previo y reexportar, o
   entregar el `_2` diciéndolo explícitamente.
2. Que la salida de NT8 (`Print`) diga `escribiendo <esa ruta>`.
3. `head -1` del archivo: debe contener `score_mode=AbsMagnitude` y `tape_window=25`.
4. Que haya **una sola** línea `# meta` en todo el archivo.

## 2.4 Checklist de aceptación de Fase B

Puerta 0 del headline se declara cerrada **sólo si las diez condiciones dan verde**:

| # | condición | criterio |
|:-:|---|---|
| 1 | el meta declara `score_mode=AbsMagnitude` | **assert fail-closed**, no fallback |
| 2 | corrida única | 1 sola `# meta`, `seq` monotónico, sin `_N` inesperado |
| 3 | aritmética | `signed_flow`, `d_ticks`, `a_score`, `n_ticks`, `residual` = 100 % del comparable |
| 4 | umbral causal post-burn-in | `a_pass`, `n_hist`, `a_thr` = 100 % |
| 5 | **cubetas residuales incluidas** en la capa de umbral (cierre de D-2) | los 4 cortes evaluados, no excluidos |
| 6 | zonas | `matched == comparable`, `only_nt8 = only_python = 0` |
| 7 | fills | idem, **con las 5 assertions de D-3 activas** |
| 8 | conjuntos laterales | `only_nt8 == 0` y `only_python == 0` en todas las capas |
| 9 | claves duplicadas | `duplicate_score/zone/fill_keys == 0` |
| 10 | procedencia | `cs_sha256` **y** `cs_installed_sha256` en el JSON; ambos derivados y declarados |

**El visor pasa de `PARCIAL` a `EXACT` sólo si las diez cierran.** Si alguna
falla, el visor queda en `PARCIAL` y el JSON declara
`headline_abs_magnitude.validated = false`.

## 2.5 Qué debe modificar Antigravity al recibir el export

Cinco archivos. **Ninguno es el kernel** — tocar `bigtrap2absorption.py` para
perseguir el resultado invalida la medición.

| # | archivo | cambio |
|:-:|---|---|
| 1 | `tools/verify_layer_parity.py` | (a) parametrizar `csv_file` y `out_json` por CLI — hoy están hardcodeados en `:101` y `:653`; (b) **D-1**: reemplazar `int(dt.timestamp()*1e9)` por aritmética entera con `timedelta`, y construir el `datetime` con `tzinfo=` en vez de `.replace()`; (c) **D-2**: mover `post_burnin_score_keys.append(key)` fuera del `if residual == "False"` — el burn-in sigue contando sólo no-residuales, pero el conjunto comparado incluye las residuales; (d) **D-3**: las 5 assertions antes de usar `created_bar`; (e) **§2.2**: `assert meta["score_mode"] == esperado`, fail-closed; (f) **D-4**: registrar `cs_installed_sha256` y `cs_kernel_lines` |
| 2 | `docs/research/PARIDAD_BT2_ABSORPTION_PUERTA0_ABSMAGNITUDE.json` | **artefacto nuevo y separado.** No pisar el direccional |
| 3 | consolidado de paridad | distinguir `directional_regression.validated = true` de `headline_abs_magnitude.validated = true/false` |
| 4 | `tools/visor_server.py:68` | `PARCIAL` → `EXACT` **sólo** si las diez condiciones de §2.4 cierran |
| 5 | `docs/parity_coverage/` | entrada de BigTrap2Absorption con las dos ramas y sus estados |

> Recomendación de método: correr el harness corregido **primero contra el export
> direccional existente** y confirmar que los 27.328/626/626 siguen dando idéntico.
> Si un fix de D-1/D-2/D-3 mueve un número de Fase A, el fix está mal. Recién
> después correrlo contra AbsMagnitude.

## 2.6 Lo que esta auditoría NO hizo

- No abrí outcomes, MFE, MAE, retornos, barreras, SL/TP ni P&L.
- No abrí junio.
- No cambié parámetros ni edité el kernel, el `.cs`, el harness o los artefactos.
- No propuse mejoras del indicador.
- No declaré edge.
- No acepté «la fórmula es trivial»: auditar la fórmula en el `.cs` (§2.1) **no
  sustituye** el export. Que la rama esté bien escrita no prueba que NT8 la
  ejecute con estos parámetros sobre esta cinta.

---

## Aporte al referente

Fase A queda aceptada con evidencia re-derivada de forma independiente, y los
cuatro defectos que la sostenían en silencio quedan medidos en vez de supuestos:
tres de ellos son invariantes no declarados que **hoy se cumplen y nadie estaba
verificando**. El aporte concreto es haber identificado que el mismo fallback de
`score_mode` que en Fase A fallaba ruidosamente, en Fase B **pasaría en silencio**
— es decir, que Puerta 0 del headline es estructuralmente más fácil de aprobar por
error que la regresión que ya pasó, y por eso el orden correcto es cerrar los
defectos antes de correr, no después de ver el resultado.

---

# CIERRE EXPLÍCITO DE LA AUDITORÍA

Ordenado por el auditor. Vinculante para quien implemente los hardenings.

## C-1 · Veredicto de Fase A

```
FASE_A_DIRECTIONAL_ACCEPTED
```

## C-2 · Headline

**El headline `AbsMagnitude` queda PENDIENTE.** Fase A no dice nada sobre él.

## C-3 · D-1 — conversión temporal entera, obligatoria

`parse_art_to_utc_ns` **debe** corregirse con **conversión temporal entera**,
**sin `datetime.timestamp()` float**. El ULP del `double` en el epoch de agosto
2026 es 238,4 ns, mayor que la granularidad de 100 ns que la función pretende
preservar. La corrección usa `timedelta` entero contra el epoch.

## C-4 · D-2 — capa separada para las 4 cubetas residuales

D-2 **requiere una capa separada** que evalúe explícitamente los 4 cortes de
sesión hoy excluidos. Criterio de aceptación de esa capa:

| magnitud | esperado |
|---|---|
| `residual` | **4/4** |
| `a_pass = False` | **4/4** |
| `n_hist` | **4/4** |
| `a_thr` | **4/4** |
| zonas creadas | **0/4** |

## C-5 · D-3 — assertions automáticas antes de usar `created_bar`

El emparejamiento posicional `nt8_fills[i] ↔ nt8_zones[i]` **requiere assertions
automáticas** de:

- `len(zones) == len(fills)`
- `signal_at == available_at`, normalizados a UTC
- `side` idéntico
- `seq` compatible

Si cualquiera falla, la corrida se detiene. No se acepta emparejamiento
posicional sin estas cuatro.

## C-6 · Fase B — aborto fail-closed

Fase B **debe abortar** si:

```python
meta.get("score_mode") != "AbsMagnitude"
```

Sin fallback a `DEFAULTS`. Motivo en §2.2: el mismo fallback que en Fase A
fallaba ruidosamente, en Fase B pasaría en silencio.

## C-7 · Hash del `.cs` instalado

La diferencia de hash entre `nt8/BigTrap2Absorption.cs` (`18d16312…`) y el
instalado en NT8 (`0af1f759…`) queda explicada **exclusivamente** por las **57
líneas de región generada** (`#region NinjaScript generated code`, líneas
893–949). Las primeras 892 líneas del instalado hashean `18d163123662dc0e…`,
idéntico al archivo del repo. **El kernel que corrió es el kernel del repo.**

## C-8 · Estado de la puerta

**Puerta 0 completa sigue ABIERTA.**

---

## Nota de método

Mi primera hipótesis fue que los `excluded_before_anchor = 714` eran un artefacto
del defecto de punto flotante D-1. **La fuente la desmintió**: el parser exacto
excluye exactamente los mismos 714 y produce el mismo ancla. La dejo escrita
porque el error importa — si no la hubiera medido contra los 28.042 timestamps
reales, habría reportado como bloqueante un defecto cuyo impacto medido es cero.
