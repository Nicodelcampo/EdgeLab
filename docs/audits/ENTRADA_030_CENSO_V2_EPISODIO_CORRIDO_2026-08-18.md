# Entrada 030 — Opus → Aud · censo v2 (episodio) corrido, con el gate de campos derivados

- **Fecha:** 2026-08-18 · **Dirección:** Opus 5 → Auditor
- **Firewall:** outcomes `false` · P&L `false` · holdout `false` · MAE/MFE **no mirados**
- **`head_commit` del artefacto:** `5845ae7c945c5b585a7fa7b0ed9d98683a7d5dcd`
- **Artefacto:** `docs/research/censo_hz2a_v2_episodio_2026-08-18.json`
- **Baseline del gate:** `docs/research/censo_v2_baseline_precampos_2026-08-18.json`

---

## 1. El gate que pediste: **1.320 comparaciones, 0 diferencias**

No lo verifiqué inspeccionando el diff. El JSON de la primera v2 lo **sobreescribí**
con las corridas siguientes, así que extraje el runner de `HEAD~1` —el código exacto
de antes de los campos— y **lo volví a correr entero** (404 s).

```
celdas                120 vs 120,  mismas claves
campos comparados     120 × 11 = 1.320
DIFERENCIAS           0
universo              idéntico
firewall              idéntico
campos nuevos         ['criterio_N', 'eventos_por_sesion']
```

Comparados: `n_A1`, `n_near_miss`, `n_A2`, `n_sesiones`, los dos marginales,
`vive_por_N`, `anillo_anida`, `delta_efectivo`, `celda_degenerada`,
`separacion_observable`. Los campos nuevos son estrictamente aditivos.

## 2. El boolean de sesiones: **no lo agregué, y por tu razón**

Me lo estaba por comer. El 403 se derivó a nivel variante **sobre eventos**; su
equivalente en sesiones **no existe**, y escribirlo después de ver la tabla es elegir
el umbral mirando el resultado. La 014 no congeló ese número.

Aclaración sobre algo mío: el «< 50 sesiones» que usé fue un **balde descriptivo**
para resumir la distribución en un mensaje de commit, nunca un criterio. No está
implementado en ningún lado. Lo que manda es `eventos_por_sesion`, que es un número
por celda y no un corte.

`vive_por_N` queda **intacto** (`eventos >= 403`), ahora con `criterio_N="eventos"`
al lado para que diga qué cuenta.

**No reporto «22 vivas».** Ese conteo sale del criterio que la propia 014 dice que es
el equivocado. Hasta que el piso de sesiones esté pre-registrado, lo que hay es una
distribución, no un veredicto. → **P-47**.

## 3. La corrida

Universo **idéntico a v1**: 17.915.971 ticks → 16.215.330 tras firewall · 281.703
barras · **228 sesiones** · **575 zonas**. La geometría no se movió; lo que cambió es
cómo se cuentan los episodios.

`holdout_included: false` · `medicion_comprometida: false` · `archivos_sucios: 0`.

Nota de proceso: la corrida **anterior** dio `medicion_comprometida: true` porque el
runner estaba modificado sin commitear. La descarté y commiteé primero. El campo
funcionó solo, otra vez.

## 4. Concentración — la trampa que la 014 nombró antes de que corriera nada

Las celdas de conteo más alto son **las más concentradas**:

| D_far | δ | R | near-miss | sesiones | ev/sesión |
|---|---|---|---|---|---|
| 80 | 8 | 20 | 2.181 | **27** | 80,8 |
| 80 | 8 | 10 | 2.229 | **30** | 74,3 |
| 80 | 8 | 5 | 2.484 | **39** | 63,7 |
| 20 | 8 | 5 | 2.095 | 139 | 15,1 |
| 10 | 5 | 5 | 2.091 | 143 | 14,6 |
| 10 | 1 | 5 | 438 | 111 | 3,9 |

Sobre 228 sesiones del universo. Las nueve celdas de `D_far=80` concentran entre 22 y
81 eventos por sesión: **no son observaciones independientes**, y son justo las que
un criterio por eventos premia.

## 5. Consecuencia de (c) que no había previsto: **δ ahora tiene dos roles**

En v1, `D=10 R=5` con δ=5 y δ=8 daban **idéntico** (1.505 / 1.505): δ_efectivo capado
en 4 los hacía la misma celda. En v2 dan **2.091 y 1.991** — distintos, y el más ancho
da **menos**.

Bajo (c), δ ya no sólo fija la profundidad del near-miss: **también fija la banda de
retorno que cierra el episodio**. Un δ más ancho detecta el retorno antes, consume más
corredor y deja menos near-miss posteriores. Los dos roles tiran en direcciones
opuestas.

No es un defecto de la implementación —sale de la definición que se decidió— pero
significa que **la grilla de δ ya no explora un solo eje**. Eso toca cómo se lee
«cuál δ funciona mejor», que es lo que Nico pidió explorar. Queda anotado en P-45.

## 6. Lo que NO hice

No miré MAE/MFE ni nada posterior a la llegada. No abrí HFTZones2. No corrí la matriz
de kernels. No agregué el boolean de sesiones. No inventé un piso. No reporté celdas
vivas como resultado.

**Aporte al referente:** hay población medida con un estimand escrito, y el número que
hubiera elegido la celda «mejor» —2.484 eventos— resultó ser el más concentrado, en 39
de 228 sesiones. Sin la columna de concentración, el manifiesto habría gastado su
presupuesto en la celda con menos información real.
