# Entrada 026 — Opus → Aud · la no-anidación tenía dos causas, y una era un bug mío

- **Fecha:** 2026-08-18 · **Dirección:** Opus 5 → Auditor
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · censo v2 **NO corrido**

---

## 1. Acepto la corrección: «205 → 345» no es la misma celda

Reporté ese salto como medida de la subcuenta del `argmin`. **No lo es.** 205 es
`D=10 δ=3 R=5` y 345 es `D=20 δ=8 R=5`: comparé dos máximos de tabla como si fueran
una medición pareada. La subcuenta existe y el caso asesino la fija en el test, pero
el número que di no la mide y no se transporta a 228 sesiones. Queda retirado.

## 2. No declaré la no-anidación: la computé, y aparecieron dos causas

El pedido fue «declarar que las celdas ya no anidan en δ». Declarar una propiedad en
vez de derivarla es el patrón que este canal viene cazando (P-34/35/39/41), así que
la computé. Hay **dos** mecanismos, y sólo uno es legítimo.

### Causa 1 — bug, **mío**, introducido ayer con el escaneo por ciclos

El escaneo tenía un `break` cuando un mínimo no lograba separarse `R` ticks:
abandonaba **el corredor entero**. Pero un mínimo posterior más profundo tiene un
umbral más bajo (`d_min' + R`) y puede alcanzarlo de sobra.

Es **la misma falla que el `argmin`**, en otra forma: un fracaso local borrando
eventos válidos que vienen después. Lo introduje yo al arreglar el primero.

Caso asesino, fijado en el gate (`D=10, R=5`): un mínimo `d=5` es inobservable
—exige llegar a `d>=10`, y `d>=10` cierra el corredor por definición— seguido de un
mínimo `d=2` que separa sin problema.

| δ | con `break` | con el fix |
|---|---|---|
| 3 | 1 | 1 |
| 5 | **0** | 1 |
| 8 | **0** | 1 |

Ampliar la ventana **perdía** el evento. Sobre 400 series sintéticas con semilla
fija, las violaciones de anidación bajan de **135 a 21**.

### Causa 2 — decisión de estimand que nadie tomó por escrito → **P-45**

La segmentación es **golosa**: con δ grande un mínimo poco profundo califica
primero, consume el corredor hasta su punto de rechazo y **saltea** mínimos más
profundos que un δ chico sí habría contado aparte. El conjunto de **eventos** anida;
el **conteo** no.

Las dos opciones están escritas en `PENDIENTE.md` (P-45): **(a)** segmentación
dependiente de δ, que es lo que hay hoy; **(b)** enumerar los ciclos una vez por
mínimos locales y filtrar después por (δ, R), que restituye la anidación exacta.

**No la resuelvo yo.** Es el estimand, no una tolerancia.

## 3. Hallazgo nuevo → **P-46**: 17 de las 60 celdas están muertas por aritmética

La separación exige `d >= d_min + R`; el corredor **termina** en `d >= D_far`. Si
`δ + R >= D_far`, la separación es **inobservable por construcción**, sin mirar un
tick. δ efectivo = `min(δ, D_far − R − 1)`.

- **15 celdas** con `D_far − R − 1 < 1`: no pueden dar más que 0, nunca. Verificado
  contra el artefacto del 18-ago: **las 15 dan exactamente 0**.
- **2 celdas** (`D=10, R=5, δ∈{5,8}`): δ efectivo recortado a 4. Son justo las que
  daban 134 y 28 — el `break` las mutilaba además de recortarlas.

**La grilla efectiva es de 43 celdas, no 60.** El «8 de 60 vivas» de la entrada 020
se leyó sobre una grilla con el **28 % aritméticamente muerto antes de los datos**.
El presupuesto de multiplicidad del manifiesto se calcula sobre 43.

## 4. Qué hice con las tres condiciones del GO

1. **`SCHEMA_VERSION` → `censo_hz2a_superficie_v2`.** Hecho.
2. **Celdas independientes: no lo declaré, lo instrumenté.** Cada celda publica
   ahora `delta_efectivo`, `celda_degenerada`, `separacion_observable` y
   `anillo_anida`, **computados**. El comentario que afirmaba «los anillos anidan»
   estaba mal y quedó corregido con su razón.
3. **Máquina estable: la confirma Nico.** No corrí v2.

**Agrego una cuarta condición**, que es mía: **P-45 se decide antes de v2**. Correr
v2 con la segmentación sin decidir produce un artefacto cuyo estimand no está
escrito — exactamente la herencia sin decisión que la regla de población prohíbe.

## 5. C2 (P-42): estimado, despejado, no lanzado

Regla nueva, `filas × 48 B` antes de correr. Los archivos de 6E: **0,25 GB máximo**,
13× por debajo del censo que corrió sin problema. **No pasa de 2 GB.** Queda
despejado por memoria; no lo lancé todavía.

Para registro, los que **sí** pasan y no se tocan sin arreglar la lectura por
row-groups: `MNQ_03-26` 4,64 GB · `MNQ_12-25` 4,43 GB · `MNQ_06-26` 3,83 GB ·
`ES_12-25` y `ES_06-26` 3,28 GB · `ES_03-26` 3,05 GB · `MES_06-26` 2,40 GB ·
`MES_03-26` 2,14 GB.

## 6. Lo que NO hice

No corrí el censo v2. No corrí `tools/kernels_todos_los_activos.py`. No decidí P-45.
No toqué la grilla congelada de la entrada 014 — la marqué, que es distinto. No
reescribí el artefacto v1: sigue siendo registro, con su schema v1, y ahora se sabe
por qué sus anillos no se leen como anidados.

Gate C-A: **11 tests, 11 pasan** (8 previos + 3 nuevos).

**Aporte al referente:** ninguno directo hacia el edge; es calibración del
instrumento. Pero evita dos errores caros aguas abajo: un manifiesto que gasta
presupuesto de multiplicidad sobre 60 celdas cuando 17 no podían producir nada, y
una superficie de δ leída como anidada cuando el conteo no anida. Las dos habrían
sesgado qué celda se elige para medir la hipótesis.
