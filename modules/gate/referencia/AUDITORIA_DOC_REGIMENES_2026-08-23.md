# Auditoría del documento de regímenes cortos — complemento

- **Fecha:** 2026-08-23 · **Rama:** `research/gate-regime-context`
- **Audita:** `Regimenes_Corta_Duracion_Edge_Investigacion.md`
  · sha256 `b96b3555774f7b503298780f8a9a13202530c7e47473b50454d10063baf4edac`
  · 17.328 bytes · 331 líneas
- **Origen:** adjunto de `Y87d0pCSl3dLKEcp-grok-workspace.zip`, producido fuera de este repo
- **Firewall:** no toca outcomes, holdout ni `.cs`

> **Qué es y qué no.** Es un **relevamiento de método y bibliografía**, no una medición.
> No contiene un solo número derivado de datos. Todas sus afirmaciones son citas o
> recomendaciones de diseño. Como tal es útil; leído como evidencia, no lo es.

---

## 0. Por qué sube solo el documento

El zip traía 293 archivos: una app web (TanStack Start + React + Vercel) con ~250 archivos de
andamiaje de Grok — skills de videojuegos, sprites, auth, PWA — irrelevantes acá.

El detector en TypeScript (`src/lib/regime/`, ~1.760 líneas) está **bien escrito**: filtro
causal `forwardPosteriors`, histéresis, `tradeCost` que cobra los flips de régimen, marca de
holdout, conteo de trials. Pero `simulate.ts` genera **390 barras sintéticas** con parámetros
hardcodeados y **no hay una sola línea que cargue datos**: ni fetch, ni archivo, ni parquet.
**Nunca corrió sobre datos reales** — confirmado por Nico.

⇒ Es un demo de la metodología, no una medición. No aporta nada que GATE no tenga en Python.
**Queda afuera del repo.** Sube el documento, que es lo único con contenido propio.

---

## 1. Lo que vale, y vale bastante

El documento es, de hecho, **la especificación de diseño que GATE implementa**. Los diez
features de `gate_model_id_frozen.json` (`rvol, er, ofi_ema_z, hurst, vpin, spread_z, sess_rel,
phase_open/mid/close`) salen casi textuales de su §3.1. Eso llena un hueco real: hoy el
`model_id` congelado lista los features **sin decir de dónde salen**.

Y coincide con lo que este lab viene haciendo, incluso donde duele:

| §10 del documento | dónde apareció acá |
|---|---|
| *«Z-score con estadísticas de toda la historia → look-ahead»* | `train_only_zscore_causal` de GATE |
| *«No cobrar costos en flips de régimen → métricas infladas»* | la vara de 2,5 ticks de Puerta 1 |
| *«Millones de estrategias sin corrección por multiplicidad»* | por qué Puerta 1 se corre una sola vez |
| *«El régimen no es el edge. Es el contexto (gate)»* | `ESTADO.md` §4, restricción de orden |
| *«HMM fit full-sample + decode suavizado → look-ahead»* | `bidirectional_allowed_in_production: false` |

Su §6 (embudo de 6 etapas) y §10 (tabla de anti-patrones) son las dos secciones más reusables.

---

## 2. Hallazgos

### D-1 · **OFI no es computable con la cinta que usamos, y GATE lo etiqueta mal** — MEDIDO

El propio documento es enfático en §3.1: *«Trade imbalance usa solo el tape. OFI
(Cont–Kukanov–Stoikov) usa altas, cancelaciones y cambios de tamaño en el mejor bid/ask.
**No son intercambiables.**»*

Verificado en tres lados:

**(a) Nuestra cinta no alcanza.** `GC 08-26.Last.txt` tiene 5 campos:

```
20260524 220000 5160000 ; 4566 ; 4566 ; 4566 ; 35
timestamp               ; last ; bid  ; ask  ; volume
```

Precios de BBO, **sin tamaños y sin eventos de libro**. No hay altas, cancelaciones ni cambios
de tamaño. **OFI propio: imposible desde acá.**

**(b) GATE nombra `ofi_ema_z` pero calcula trade imbalance.** Única implementación presente,
`integration/edgelab_gate_integration/from_ticks.py:58-69`:

```python
sign = np.where(agg == "buy", 1.0, np.where(agg == "sell", -1.0, 0.0))
t["signed_vol"] = sign * t["volume"]
signed = t["signed_vol"].resample("1min").sum().rename("signed")
```

Eso es **imbalance de tape**, exactamente lo que el documento dice que no es OFI.

**(c) La app de Grok sí computa OFI real** —`kyleLambda(ofi, ...)`, `bidSize`, `askSize`,
`depthImb`— **pero sobre el libro que ella misma inventa** en `simulate.ts`.

> **Es P-39 otra vez**: la etiqueta dice OFI, el contenido es imbalance de tape, y el documento
> que justifica el feature advierte explícitamente que no son lo mismo.

**Kyle λ arrastra el mismo problema**: se define como regresión de Δprecio sobre OFI. Con
imbalance de tape en lugar de OFI, es otro estimador, no el de Cont–Kukanov–Stoikov.

### D-2 · El L2 existe, pero **cero cobertura del universo de investigación**

Hay 12 sesiones de L2 de GC en `db/replay.csv/GC DEC26/`, con esquema suficiente para OFI
(`operation`, `position`, `price`, `volume` — altas/cambios/bajas por nivel):

```
20260621..20260626   dentro de la ventana temporal
20260816..20260821   fuera de la ventana
```

**Pero `GC DEC26` no es front month en ninguna de esas fechas.** El front month del
2026-05-28 al 06-30 es **`GC 08-26`** (`ENMIENDA_UNIVERSO_GATE1_2026-08-23.md`).

⇒ **Para las 152 sesiones del universo, la cobertura L2 del contrato front-month es 0.**

**Nico confirma que el L2 es descargable para cualquier activo**, así que esto es una compra,
no un bloqueo. Costo medido sobre los parquets existentes (**14,2 MB/sesión comprimido**, 12
sesiones = 170 MB):

| alcance | sesiones | parquet | CSV crudo de NT8 |
|---|---:|---:|---:|
| universo completo | 152 | **2,1 GB** | ~12,6 GB |
| GC 06-26 + 08-26 (may–jun) | 42 | 0,6 GB | ~3,5 GB |
| sólo GC 08-26 (jun) | 25 | 0,3 GB | ~2,1 GB |

*(referencia: los 38 parquets L2 que ya hay pesan 584 MB y salieron de ~3,5 GB de CSV)*

**Recomendación: no bajarlo todavía.** OFI sólo hace falta si GATE entra como contexto, y eso
está detrás de Puerta 1. Bajar 12,6 GB para un módulo que es cimiento es gastar antes de saber
si se usa. Si se decide avanzar, el orden barato es 25 sesiones primero (0,3 GB) para verificar
que OFI aporta sobre el imbalance de tape, y recién después las 152.

### D-3 · Ninguna mención de potencia estadística ni MDE

El documento tiene un embudo de 6 etapas (§6), un checklist de aceptación de 9 puntos (§9) y un
checklist de implementación de 10 (Anexo B). **Ninguno menciona potencia, MDE, ni tamaño de
muestra mínimo.** §9.4 pide *«número de trades suficiente»* sin definir suficiente.

Es un hueco grande para un documento que se propone como especificación de build. Todo el
trabajo de hoy en Puerta 1 terminó exactamente ahí: **115 sesiones daban 74,4 % de potencia y
hubo que ampliar a 152 para llegar a 85,2 %**. Un embudo que descarta hipótesis sin declarar su
potencia no distingue «no hay efecto» de «no lo pude ver».

### D-4 · El documento recomienda lo que CTX-2 ya rechazó

§1 lista como driver *«Bursts en :00 / :15 / :30 — algos sincronizados, rebalanceos»*, y §2
pone «fase de reloj» como escala de régimen.

**H-ES-CTX-2 rechazó «fase de sesión» con `corr ≈ −0,255` contra `ancho_ticks`** — dato que el
propio GATE usa para calibrar su umbral de contaminación (`CORR_ANCHO_REJECT = 0.25`).

No es una contradicción del documento —él no conoce CTX-2— pero **cualquier adaptación a GC
tiene que tratar la fase de reloj como candidato ya refutado localmente**, no como punto de
partida.

Y conecta con algo ya medido: cuatro de los diez features de GATE (`sess_rel`, `phase_open`,
`phase_mid`, `phase_close`) **son fase de reloj**.

### D-5 · La premisa de «micro-régimen» es más débil en GC de lo que el documento supone

Su tesis central (§1) es que los regímenes explotables son **locales en el tiempo**:
segundos–minutos.

`B9_CONTEXTO_BT2_ABSORPTION_2026-08-23.md` midió sobre 115 sesiones de GC:

| eje de variación de `a_thr` | medido |
|---|---:|
| **entre sesiones** | **3,18×** |
| intradía (p90/p10, mediana) | 1,51× |
| intradía agregado por bin de 30 min | 1,39× |

**En GC el eje grande es entre sesiones, no intradía** — más del doble. Eso no refuta la tesis
del documento, pero la invierte para nuestro instrumento: si se adapta a GC, el régimen relevante
parece ser **de sesión**, no de minutos.

Y eso importa para el diseño: un detector calibrado para cambiar de estado cada pocos minutos
va a producir flip-flop y costos de transición sobre un fenómeno que en GC se mueve por día.

### D-6 · §7.4 contradice §10

§7.4 lista StrategyQuant X, Build Alpha y Adaptrade como *«software de generación masiva de
estrategias»*, con la nota de que sin embudo producen sobreajuste. §10 clasifica *«millones de
estrategias sin corrección por multiplicidad»* como anti-patrón.

La nota atenúa pero no resuelve: es la sección más débil y la única sin valor para este lab.
**Ignorable.**

### D-7 · Las citas no son verificables como están

~30 referencias entre papers y repos, con **dos** identificadores concretos (`arXiv:2006.08307`
y un arXiv sin número). Sin DOIs, sin años en la mayoría. Los repos de GitHub sí son
direccionables.

Para un documento de referencia es una limitación práctica: varias afirmaciones de §4 y §5
descansan en literatura que no se puede ir a chequear desde el texto.

---

## 3. Qué sirve para adaptar a GC — y el documento ya lo tiene

Su §3.3 anticipa exactamente nuestra situación de datos:

| datos disponibles | features mínimas |
|---|---|
| **Solo trades / L1** | signed volume (z-score rolling) + realized vol + proxy de spread + Efficiency Ratio (1–5 min) |
| L2 / BBO | OFI + VPIN + Kyle λ + depth imbalance |

**La fila de arriba es la nuestra**, y es implementable hoy sobre las cintas que ya están en
disco, sin bajar un byte de L2.

De las siete familias de features de §3.1, con nuestra cinta:

| familia | ¿computable? |
|---|---|
| flujo firmado (tape) | **sí** — el agresor sale de comparar `last` contra bid/ask |
| toxicidad (VPIN) | **sí** — buckets de volumen + clasificación de agresor |
| impacto (Kyle λ) | **como proxy** — con imbalance de tape, no con OFI (D-1) |
| liquidez | **parcial** — spread sí; profundidad y Amihud-depth **no** |
| actividad | **sí** — tick rate ya medido en B-9 (0,53 a 4,03/s, 7,58×) |
| path / memoria (RV, Hurst, ER) | **sí** |
| entropía de posteriors | **sí** — es del detector, no del dato |

⇒ **Cinco de siete completas, una parcial, una bloqueada por L2.** Suficiente para una versión
GC honesta, siempre que **`ofi_ema_z` se renombre** a lo que efectivamente calcula.

---

## 4. Recomendaciones

1. **Renombrar `ofi_ema_z`.** Con nuestra cinta el feature es `signed_flow_ema_z` o
   `tape_imbalance_ema_z`. Cambiar el nombre de un feature obliga a un **nuevo `model_id`** por
   la propia `change_policy` del módulo — cosa que corresponde, porque el objeto medido no es el
   que el nombre declara.
2. **No bajar L2 todavía.** 12,6 GB para el universo completo, detrás de Puerta 1. Si se avanza,
   25 sesiones primero (0,3 GB) para ver si OFI aporta sobre el imbalance de tape.
3. **Agregar potencia al embudo** si se adopta §6: cada etapa que descarta debería declarar su
   MDE. Es el hueco D-3.
4. **Tratar la fase de reloj como refutada localmente**, no como punto de partida (D-4).
5. **Recalibrar la escala del detector para GC**: el eje grande es de sesión, no de minutos (D-5).
6. **Usar la plantilla L1 de §3.3** como base de la versión GC.

---

## 5. Veredicto

```
DOCUMENTO         UTIL COMO REFERENCIA DE METODO. No es evidencia.
APP WEB           DESCARTADA (sintetica, nunca corrio sobre datos reales)
D-1 OFI           CONFIRMADO -> requiere renombrar feature + nuevo model_id
D-2 L2            0 cobertura del universo. Descargable: 2,1 GB (152 sesiones)
D-3 POTENCIA      HUECO. Sin MDE en todo el embudo
D-4 FASE RELOJ    Ya refutada localmente por CTX-2 (corr -0,255)
D-5 ESCALA        En GC el regimen es de sesion (3,18x) mas que intradia (1,39x)
D-6 SS7.4         Ignorable, contradice SS10
D-7 CITAS         No verificables como estan
ORDEN             Puerta 1 primero. Este documento no cambia esa restriccion.
```

---

## Aporte al referente

El documento entra al repo con su distancia a los datos medida: es una buena especificación de
método que **nunca se ejecutó**, y su implementación de referencia corre sobre un mercado que
ella misma fabrica. Lo que sí aporta es la justificación bibliográfica que al `model_id`
congelado de GATE le faltaba — y, de paso, la evidencia de que uno de esos diez features está
mal nombrado.

## Nota de método

D-1 salió de **leer la advertencia del propio documento y después ir a ver qué calcula el
código**. El documento dice, textual, que OFI y trade imbalance «no son intercambiables»; el
módulo que lo cita como fundamento los intercambia. **El defecto no estaba escondido: estaba
publicado en la misma página que la regla que viola.**

Es el mismo patrón que apareció todo el día del lado de EdgeLab —el `a_score` del fill 11537_B,
el `dir` de los 377 eventos, el `max_ticks=700000`—. Van nueve, y la constante no es el
descuido: es que **nadie fue a cruzar la etiqueta contra el contenido** hasta que alguien
cambió el insumo o la unidad.
