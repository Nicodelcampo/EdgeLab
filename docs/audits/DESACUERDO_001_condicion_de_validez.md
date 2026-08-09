# Desacuerdo 001 — Claude ⇄ Codex sobre la condición de validez

**Fecha:** 2026-08-09 · Outcome-free · **Sin resolver. Lo dirime Nico o el referente.**
**Origen:** Tarea 1 de `CANAL_CODEX.md`, medida de forma independiente por los dos.

---

## 1. El valor del ejercicio: la composición coincidió, la semántica no

Los dos módulos implementan **los dos órdenes de composición de forma idéntica** —
misma llamada a `decongest_first_touch_events`, mismas dos ramas. Ahí no hay
disputa.

La discrepancia está en **qué cuenta como evento válido**, y da un factor ~2.

| | Codex | Claude |
|---|---:|---:|
| candidatos (primeros toques en universo) | 16.098 | 15.577 |
| válidos antes de `sep_min` | **1.648** | **776** |
| **orden A** — decongestionar, después exigir | **158** · 0,79/ses | **71** · 0,35/ses |
| **orden B** — exigir, después decongestionar | **732** · 3,64/ses | **429** · 2,13/ses |
| violaciones de orden temporal | 0 | 0 |

## 2. Dónde está exactamente

**Codex** (`recuento_kT_primer_toque_run.py`, versión de `dc987cd`):

```python
k, j = por_t[T]                                   # de eventos_kT()
valid = k is not None and k > 0 and j is not None and j > k
```

Su `j` viene de `recuento_kT.eventos_kT`: es **el primer reingreso a la banda
posterior a la excursión**, sea o no el primer toque de esa zona.

**Claude** (`f_ambos_filtros.py`):

```python
i_toque = searchsorted(ts, first_touch_ms) - i0
e["excursion_ok"] = bool(i_toque > k)             # el PRIMER TOQUE, después de k
```

Exijo que **el primer toque de esa zona** sea posterior a la excursión.

**Codex es la condición más débil**, y por eso cuenta más del doble. Dato que lo
confirma: su 1.648 es casi exactamente los **1.655** retornos válidos que
`recuento_kT` mide sobre la población **sin** `sep_min`. Está reproduciendo la
semántica de `j` del censo, no la de primer toque.

## 3. Mi posición, y no la declaro ganadora

La población autoritativa es la de primeros toques, y la enmienda dice
*«EXPLORE-001 define **la entrada primaria** en el primer toque posterior»*. Si
la entrada es el primer toque, entonces §3.1 exige que el primer toque venga
**después** de la excursión:

```
zona disponible
 → precio todavía no cumplió la excursión T
 → cruce posterior del umbral T
 → desenlace posterior          ← la entrada
```

Bajo la condición de Codex entran eventos donde **el primer toque ocurrió ANTES
de la excursión**: se entraría en un momento en que el setup todavía no pasó, y
lo que valida el evento es un reingreso posterior que **no es la entrada**. Es la
misma forma del defecto que toda la disciplina de `k_T > 0` existe para impedir.

**Contra-argumento que reconozco:** si la entrada real fuera el reingreso `j` y
el «primer toque» de la enmienda fuera sólo el **ancla de decongestión**,
entonces Codex tiene razón y mi condición descarta eventos legítimos. La enmienda
dice *«entrada primaria»*, que me inclina a mi lectura — pero no la zanja.

**No lo resuelvo.** Codex se quedó sin cuota antes de publicar su informe y no
puede defender su posición; adjudicar ahora sería ganar por incomparecencia.

## 4. Segundo desacuerdo, menor y sin diagnosticar

**Candidatos: 16.098 contra 15.577**, 521 de diferencia (3,2 %), los dos después
de filtrar por universo.

Usamos funciones distintas de fecha de sesión: Codex `sesion_ct(ms * 1_000_000)`,
yo `session_date_ct(ms)`. Distintas firmas y distintas unidades. **No verifiqué si
coinciden en los bordes de sesión.** Podría ser un defecto de cualquiera de los
dos, o ninguno. Queda abierto.

## 5. Lo que NO depende del desacuerdo

Con cualquiera de los dos números, tres cosas se sostienen:

1. **`f` está muy por debajo del ≈ 8,3 publicado en §6.3.** Entre 2,13 y 3,64 en
   el orden B; entre 0,35 y 0,79 en el orden A.
2. **Los dos órdenes difieren en un factor 5-6.** La pregunta de composición no
   era académica.
3. **`f ≈ 8,3` venía de la población sin `sep_min`.** Confirmado por partida
   doble.

Y hay coincidencia fuerte en los controles: **cero violaciones de orden temporal**
en ambos, y mi tasa cruda de primeros toques —77,50/ses— reproduce los 77,54 de
PRED-007 medidos por otro módulo.

## 6. Estado de PRED-008

Predicción registrada **antes** de las dos mediciones: `f_ambos < 3,0 ev/sesión`,
punto estimado 1,2, refutada si ≥ 3,0.

| medición | orden A | orden B | veredicto de P1 |
|---|---:|---:|---|
| Claude | 0,35 | **2,13** | **CONFIRMADA** |
| Codex | 0,79 | **3,64** | **REFUTADA** por poco |

**El veredicto de la predicción depende de cuál condición sea la correcta.** Se
deja abierto en vez de elegir la medición que la confirma — que sería,
justamente, elegir el resultado.

El punto estimado de 1,2 quedó bajo en los dos casos: subestimé la correlación
entre filtros. En el orden B sobreviven a `sep_min` el 55 % de los eventos con
excursión (429 de 776), contra el 11,7 % de supervivencia global. Los eventos con
excursión válida están **más separados en el tiempo** que los primeros toques en
general, tal como el razonamiento anticipaba — pero mucho más de lo que
cuantifiqué.
