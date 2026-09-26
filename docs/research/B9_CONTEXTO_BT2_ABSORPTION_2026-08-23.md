# B-9 — dinámica de `a_thr`, tick rate y spread sobre 115 sesiones

- **Fecha:** 2026-08-23 · **Base:** `b8b9193`
- **Firewall:** outcomes `false` · **target-free**: mide el umbral propio del indicador, no resultados
- **Responde a:** `specs/bt2_absorption_gate1_v1.json` → `context_policy.b9_metrics` y
  `b9_target_free_required: true`
- **Artefacto:** `docs/research/B9_CONTEXTO_BT2_ABSORPTION.json`
- **Universo:** cadena front-month GC, 2026-01-20 → 2026-06-30, kernel headline `AbsMagnitude`,
  cubetas no residuales y post burn-in (`n_hist >= 200`)

---

## 0. ⚠ Corrección previa: son **115 sesiones**, no 133

El conteo de 133 que se reportó en `PARIDAD_JUNIO_GC0826_2026-08-23.md` §4 estaba **mal**. Usó
la **fecha de calendario UTC** de la cinta como unidad. La sesión CME arranca a las 17:00 de
Chicago y cruza la medianoche, así que una sesión aparece en dos fechas UTC y se contaba dos
veces.

| contrato | conteo por fecha UTC (mal) | sesiones CME (correcto) |
|---|---:|---:|
| GC 04-26 | 55 | **48** |
| GC 06-26 | 49 | **42** |
| GC 08-26 | 29 | **25** |
| **TOTAL** | ~~133~~ | **115** |

Chequeo de sanidad: del 20-ene al 26-mar hay ~66 días corridos ≈ 47-48 hábiles. **48 es
creíble; 55 era imposible.**

### 0.1 Consecuencia: Puerta 1 corre sub-potenciada

`power_planning.if_G_lt_133 → attach_P1_UNDERPOWERED_FOR_2P5T`. **Se dispara.**

Fórmula del spec, validada reproduciendo sus propios números a 120
(`0.7613441` contra su `0.7613571`):

| sesiones | error estándar | semiancho IC95 | potencia vs 2,5 tk |
|---:|---:|---:|---:|
| **115** ← lo que hay | 0,02630 | 0,05154 | **74,4 %** |
| 120 (supuesto del spec) | 0,02574 | 0,05046 | 76,1 % |
| 133 (objetivo 80 %) | 0,02445 | 0,04793 | 80,3 % |
| 223 (efecto legacy) | 0,01888 | 0,03701 | 95,4 % |

⇒ **`P1_UNDERPOWERED_FOR_2P5T` queda adjunto.** Un resultado positivo todavía puede pasar; un
no-pass **no** se puede vender como refutación.

---

## 1. El hallazgo: los dos ejes están al revés de lo que se creía

| eje | variación de `a_thr` |
|---|---:|
| **ENTRE sesiones** (p50 por sesión) | **3,18×** — de 2,00 a 6,35 |
| **INTRADÍA** (p90/p10 dentro de sesión, mediana) | **1,51×** |
| **INTRADÍA agregado** (p50 por bin de 30 min) | **1,39×** — de 2,871 a 4,000 |

> **El auditor midió `1,08×` entre sesiones y concluyó que la variación entre días era
> despreciable y la intradía el riesgo vivo. Ese 1,08× salió de las 5 sesiones de agosto.**
> Sobre 115 sesiones el eje entre-sesiones es **3,18×** — el doble de grande que el intradía,
> no la mitad.

Distribución entre sesiones: `p10 = 3,00 · p50 = 3,83 · p90 = 4,43`, con cola hasta 6,35.

```
sesiones mas bajas          sesiones mas altas
  20260202  p50=2.00          20260616  p50=5.00
  20260205  p50=2.21          20260629  p50=5.00
  20260130  p50=2.33          20260126  p50=6.35
```

Las tres más bajas y la más alta caen todas en GC 04-26 (enero-febrero): no es un efecto de
contrato, es de régimen.

---

## 2. Intradía: el umbral es **mucho más estable que la actividad**

Bins de 30 minutos desde las 17:00 CT, agregados sobre las 115 sesiones:

| magnitud | mínimo | máximo | rango |
|---|---:|---:|---:|
| `a_thr` p50 | 2,871 (19:00) | 4,000 (04:30, 07:00, 13:00) | **1,39×** |
| **tick rate** | 0,53 /s (15:30) | 4,03 /s (09:00) | **7,58×** |
| spread p50 | 4 tk | 9 tk (17:00) | 2,25× |

**Ese contraste es el resultado importante.** Si el decil alto de `a_score` fuera un detector de
actividad con nombre de absorción, el umbral debería seguir al tick rate de cerca. La actividad
se mueve **7,6×** a lo largo del día y el umbral apenas **1,4×**.

Correlaciones entre bins:

```
corr(a_thr, tick_rate) = +0,399     acoplamiento debil
corr(a_thr, spread)    = -0,500     acoplamiento moderado, negativo
```

Forma horaria: el umbral está más bajo en la tarde-noche de Chicago (2,87–3,13 entre las 19:00
y las 23:00), sube durante la sesión asiática/europea y se planta en 3,75–4,00 durante el grueso
del día. El spread hace lo inverso: 9 ticks en la apertura de las 17:00 contra 4–5 el resto.

---

## 3. Qué queda descartado y qué no

| trampa | veredicto |
|---|---|
| **dirección ↔ tendencia** | **descartada** — mix 54,6/45,4 estable, sd 2,5 pp, no sigue el drift (medido en `MEZCLA_DIRECCIONAL_Y_NULO_2026-08-23.md`) |
| **umbral ↔ régimen intradía** | **debilitada**. 1,39× de umbral contra 7,58× de actividad, corr +0,40. El umbral no es un proxy de la actividad |
| **umbral ↔ régimen entre sesiones** | **es el eje grande: 3,18×.** Pero el diseño ya lo absorbe (§4) |

### 3.1 Y `spread` queda descalificado como candidato de contexto

`context_policy.candidate_must_be_orthogonal_to = [a_thr, time_of_day, tick_rate]`.

Con `corr(a_thr, spread) = −0,500`, **el spread no es ortogonal a `a_thr`**. Cualquier hipótesis
de contexto que lo use estaría re-empaquetando el umbral con otro nombre. Queda descartado como
candidato antes de que nadie lo proponga.

---

## 4. Lo bueno: el pre-registro ya controla los dos ejes

Ninguno de los dos hallazgos exige cambiar el diseño, porque el spec congelado ya los cubre:

| eje | qué lo absorbe | dónde está en el spec |
|---|---|---|
| entre sesiones (3,18×) | sesión como cluster, peso 1, sin pooling | `inference.cluster = cme_session`, `equal_session_weights`, `n_rand.pooled = false` |
| intradía (1,39×) | estrato de 30 min en el control aleatorio | `n_rand.strata[2] = chicago_30_minute_bin_from_17_00` |

**El control `N_RAND` sortea anclas dentro del mismo bin de 30 minutos de la misma sesión.** Un
evento de las 19:00 CT se compara contra ruido de las 19:00 CT del mismo día, con el umbral de
ese día. Los dos ejes de variación de `a_thr` quedan emparejados por construcción.

⇒ **B-9 no bloquea. Confirma que la precondición de contexto estaba bien diseñada**, y de paso
corrige por un factor de 3 la magnitud del eje que se creía chico.

---

## 5. Método

- **Kernel corrido por contrato** sobre la cinta completa, no sobre la serie continua encadenada.
  El anillo de 500 se calienta con las sesiones previas del mismo contrato. En el roll no hay
  arrastre entre contratos — es una decisión declarada, no un descuido; el censo definitivo
  deberá elegir explícitamente si el anillo cruza el roll.
- **Burn-in excluido**: `a_thr = NaN` durante exactamente las primeras **200 cubetas** de cada
  corrida (`n_hist < 200`), 600 en total. La primera versión de este análisis no las filtraba y
  `np.percentile` propagaba el `NaN`, dejando en blanco los 13 bins de apertura. Corregido.
- **Zona horaria vectorizada**: el offset de Chicago se resuelve con una comparación contra el
  cambio de horario de verano (2026-03-08 08:00 UTC), única transición en la ventana. La primera
  versión hacía `astimezone` por tick — 15,9 M llamadas, inviable.
- **Costo**: ~47 min de kernel sobre 15,9 M ticks (~6k ticks/s). Los arrays crudos quedan
  cacheados en `.npz`, así que recalcular cualquier métrica de B-9 es instantáneo.

---

## 6. Estado

```
PARITY_PRECONDITION   = SATISFIED   (GC 08-26, 2026-06-18..06-30, 100%)
B9                    = COMPLETO, TARGET-FREE, NO BLOQUEA
  entre sesiones      = 3,18x   <-- el eje grande, absorbido por cluster de sesion
  intradia            = 1,39x   <-- absorbido por el estrato de 30 min de N_RAND
  tick_rate           = 7,58x   <-- el umbral NO lo sigue (corr +0,40)
  spread              = DESCALIFICADO como candidato de contexto (corr -0,50 con a_thr)
SESIONES              = 115  (corregido desde 133)
P1_UNDERPOWERED_FOR_2P5T = SE DISPARA -> potencia 74,4% contra la vara de 2,5 ticks
N_RAND                = PREREGISTERED_NOT_RUN   <-- siguiente
OUTCOMES              = NOT_OPENED
```

---

## Aporte al referente

B-9 pasa de deuda abierta a precondición cerrada, y con un resultado que no era el esperado: el
eje de variación que se creía despreciable (entre sesiones, `1,08×` sobre 5 días) resulta ser el
grande (`3,18×` sobre 115), y el que se creía peligroso (intradía) resulta ser tres veces menor
que la actividad que supuestamente lo arrastra. Los dos quedan cubiertos por el diseño que ya
estaba congelado, así que el pre-registro no se toca — se confirma.

## Nota de método

El `1,08×` del auditor no era un error de cálculo: era un cálculo correcto sobre cinco días.
Extrapolado a 115 se convierte en `3,18×`. **La lección no es "midieron mal", es que una muestra
de cinco sesiones no tiene resolución para hablar de estabilidad entre sesiones** — que es
exactamente lo que este mismo documento acaba de decir de la Puerta 1 con 115. La diferencia es
que acá está declarado antes de usar el número, no después.

Y otra vez el mismo patrón del día: el error de las 133 sesiones apareció al **cambiar la unidad
de medida** (fecha UTC → sesión CME), no revisando la aritmética. Van cinco.
