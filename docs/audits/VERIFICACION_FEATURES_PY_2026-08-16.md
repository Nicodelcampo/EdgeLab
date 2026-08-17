# Verificación de los seis defectos de `features.py` — **6/6 confirmados, y aparecen 2 más**

**Fecha:** 2026-08-16 · Outcome-free · Sin datos de mercado · Sólo lectura de repo
**Autoriza:** Nico — *«verificá los seis defectos de features.py»*.
**Audita:** `edgelab/bridge/features.py`, blob `98f9034cfbb6b856c410b4accf75afeed3b97809`.

> **El blob no derivó.** El que H-Z2A v2 §7 declaró auditado es exactamente el que
> está en el árbol hoy. Verificado con `git hash-object`.

---

## 1. Los seis, uno por uno

| # | defecto | veredicto | evidencia en fuente |
|---|---|---|---|
| 1 | `tick_size` declarado y nunca usado | **CONFIRMADO** | `grep tick_size` → **una sola línea**, la 58 (firma). Cero usos en el cuerpo. |
| 2 | distancia sin signo | **CONFIRMADO** | l. 106 — `np.minimum(np.abs(p-at), np.abs(p-ab))`, dos `abs`. |
| 3 | colapso a la más cercana, sin `zone_id` | **CONFIRMADO** | l. 107 `k = int(np.argmin(d))`; el `DataFrame` de salida (l. 118-123) no tiene `zone_id`. |
| 4 | semánticas mezcladas en la misma fila | **CONFIRMADO** | l. 110 `inside.any()` = *alguna*; l. 112/114/116 usan `d[k]`/`acm[k]`/`asd[k]` = *la más cercana*. |
| 5 | `zone_age` con sesgo de longitud | **CONFIRMADO** | l. 114 usa `acm[k]`, creación de la **más cercana**. Una zona longeva tiene más chance de ser la más cercana en una barra al azar: es muestreo sesgado por longitud, por construcción. |
| 6 | bucle `O(barras × zonas)` | **CONFIRMADO** | l. 96 `for i in range(n)` con máscara booleana sobre **todas** las zonas en cada iteración. |

**Y los dos «detalles menores» de v2 §7 también:** l. 98 usa `em > t` **estricto**
—una zona que termina exactamente en `t` no cuenta— y l. 82 mapea `ended_ms` nulo a
`inf`, o sea «sigue activa» ⇒ los landmarks sobre zonas vivas **hay que
censurarlos**, no descartarlos.

**Seis de seis, más los dos detalles.** La auditoría de v2 fue exacta.

---

## 2. Defecto 7 — **las dos features principales devuelven unidades no declaradas**

Nadie lo nombró, y es el mismo patrón que apareció hoy en el código GEX.

```python
out["zone_age"][i] = float(t - acm[k])     # l. 114
```

`t` es `index_ms` y `acm` es `created_ms`: **`zone_age` sale en MILISEGUNDOS.**

Y **nada en el módulo lo dice.** El docstring de `materialize_features` (l. 59-68)
describe la semántica de «zona activa» y no menciona una sola unidad;
`DEFAULT_FEATURES` (l. 21-22) es una tupla de nombres pelados.

Compone con el defecto 1: como `tick_size` se acepta y se descarta,
`distance_to_nearest_zone` sale en **unidades de precio**. Entonces:

```
distance_to_nearest_zone  ->  unidades de PRECIO   (unidad no declarada)
zone_age                  ->  MILISEGUNDOS         (unidad no declarada)
```

**Las dos features centrales de la API de estado devuelven unidades que el módulo
no declara**, y el único parámetro que arreglaría una de ellas se acepta y se tira.

### 2.1 Y aguas abajo ya se lee en otra unidad

`docs/F0.3_FEATURES_ESTADO_RESULTADO_2026-08-10.md:39` reporta:

> `zone_age de la zona mas cercana (barras)   mediana 54,3   p90 773,2`

**Etiquetado «barras».** La salida del módulo es en milisegundos. Lo más probable
es que F0.3 haya convertido correctamente —54,3 ms de edad de zona sería absurdo—
pero **la conversión no está declarada en ninguno de los dos lados**. Un consumidor
nuevo que lea `zone_age` del módulo y compare contra la mediana de F0.3 se lleva
un factor 60.000 sin que nada falle.

Para H-Z2A esto **no es cosmético**: la v4 pide `zone_age` como covariable de M1 y
`d_t` en ticks. Hoy una sale en ms y la otra en precio.

---

## 3. Defecto 8 — el desempate de `np.argmin` no está declarado

```python
k = int(np.argmin(d))     # l. 107
```

`np.argmin` devuelve **la primera ocurrencia** del mínimo. Con dos zonas
equidistantes —o dos zonas que contienen al precio, donde las dos dan `d = 0`—
gana **la que venga primero en el orden de filas de `zones_df`**, que es un input
que controla quien llama.

Consecuencia: `zone_age` y `nearest_zone_side` **dependen del orden de filas de la
entrada**, no sólo de su contenido. Mismos datos ordenados distinto ⇒ salida
distinta. Este proyecto tiene `DeterminismError` en el store precisamente contra
esta clase de cosa; acá no hay nada.

Y no es un caso raro: el **empate a `d = 0` ocurre siempre que el precio está
dentro de dos zonas a la vez**, que es exactamente la situación que el defecto 4
ya señalaba como ambigua.

---

## 4. El patrón, que ya son tres módulos

| módulo | la etiqueta dice | el contenido es |
|---|---|---|
| `edgelab/gex/reconstruct_daily_gex.py` | columna `gex_dollar` | `OI × gamma × 100`, **sin spot**, no son dólares |
| `edgelab/bridge/features.py` | `zone_age` | **milisegundos**, no declarado |
| `edgelab/bridge/features.py` | `distance_to_nearest_zone` | **unidades de precio**, con `tick_size` aceptado y tirado |

Más los precedentes ya asentados: **P-34** (etiquetas de versión que no se derivan
del contenido), **P-35** (`WARN` registrado como `parity_exact`), y el gate `mcpt`
de la rama A cuyo propio comentario admite que el nombre miente.

> **No es una coincidencia de tres casos: es una clase de defecto.** El proyecto
> verifica identidad de *archivos* con sha256 por todos lados, y **no verifica
> identidad de nombres contra contenido** en ningún lado. Un `sha256` prueba que el
> archivo es el mismo; no prueba que la columna `gex_dollar` tenga dólares
> adentro.

Queda abierto como **P-39**.

---

## 5. Qué decido y qué no

**No parcheo nada.** `features.py` es la API de estado que H-Z2A v4 va a consumir;
cambiarla mientras se redacta su manifiesto es cambiar el instrumento durante la
medición. Los ocho defectos son **precondiciones del manifiesto**, no tareas
sueltas.

**Recomiendo** que el manifiesto H-Z2A declare, para cada feature que use:
constructo → **unidad** → estimador → chequeo — que es justo la cadena que la
propia v3 propuso con `validity.py`, extendida con la unidad, que es lo que
faltaba.

**No decido** si `zone_age` pasa a barras o si se agrega `zone_age_ms` explícito:
es semántica de artefacto y hay consumidores (F0.3) que ya leyeron el número.
