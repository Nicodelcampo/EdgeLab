# Auditoría Opus — espacio de búsqueda y contrato de datos multiframe

**Fecha:** 2026-08-11  
**Rama:** `research/bigtrap2-multiframe-ml`  
**Objeto auditado:** carta rectora, `..._search_space_v0.json`, `..._dataset_contract_v0.json`  
**Resultado:** 9 defectos; 4 bloqueantes. `v0` queda como linaje histórico; `v1` corrige lo bloqueante.

Ninguna corrección de esta auditoría ejecuta datos, abre outcomes ni toca el holdout.

---

## B1 — BLOQUEANTE: no existía política de muestreo de cutoffs

`v0` describe filas por `cutoff_ns` pero nunca define **cómo se generan**. Si los cutoffs se generan únicamente cuando hay una absorción, el dataset queda condicionado a la señal y desaparece el grupo de control.

Efecto: se vuelve imposible estimar el contraste central,

\[
P(Y \mid \text{frames activos}) \;-\; P(Y \mid \text{sin frames})
\]

y el modelo sólo puede comparar señal contra señal.

**Corrección v1:** `cutoff_policy` obligatoria, con grilla temporal regular independiente del indicador, más cutoffs event-driven opcionales marcados por `cutoff_origin`. Se exige una proporción mínima de filas sin ningún frame activo (`min_null_window_fraction`), verificada por el validador.

---

## B2 — BLOQUEANTE: la tabla de folds no puede representar CV anidada

`v0` usa clave `(session_id, fold_plan_id)` con una única columna `partition`. En validación cruzada una sesión es test en un fold y train en otros, de modo que la pertenencia no es una propiedad de la sesión sino del par sesión×fold. Además `purged` y `embargoed` sólo tienen sentido relativos a un fold.

**Corrección v1:** clave `(fold_plan_id, outer_fold, session_key)` con `role ∈ {train, test, purged, embargoed, excluded}` y tabla análoga para folds internos. El validador exige que ninguna sesión sea simultáneamente `train` y `test` en el mismo fold externo.

---

## B3 — BLOQUEANTE: colisión de `session_id` entre contratos

`events_long` y `windows_ml` incluyen `instrument`/`contract`, pero `folds` estaba claveada sólo por `session_id`. Dos contratos pueden compartir la misma fecha de sesión, de modo que una sesión de 6E 09-26 y otra de 6E 12-26 colapsarían en la misma fila de fold, filtrando información entre particiones.

**Corrección v1:** clave global

```text
session_key = instrument | contract | session_date
```

presente en las tres tablas y usada como unidad de agrupamiento.

---

## B4 — BLOQUEANTE: invariante causal refería columnas inexistentes

`v0` exige `target_start_ns > cutoff_ns`, pero ninguna tabla declaraba `target_start_ns`, `target_end_ns` ni `label_horizon_ns`. Sin esas columnas el invariante no es verificable y el embargo no puede calcularse.

**Corrección v1:** tabla `targets_long` con `target_id`, `target_start_ns`, `target_end_ns`, `label_horizon_ns`, `y_value`, `censored`. El embargo se deriva del máximo `label_horizon_ns` efectivamente presente.

---

## A5 — Cardinalidad de `active_frame_set`

Un JSON libre por fila produce cientos de categorías raras que los árboles memorizan.

**Corrección v1:** codificación canónica ordenada, `frame_set_hash` estable, diccionario aparte y `min_rows_per_frame_set` para colapsar categorías raras.

---

## A6 — El tamaño de ventana es un parámetro molesto, no una feature libre

Ocho ventanas retrospectivas multiplican por ocho el espacio sin aportar una hipótesis nueva.

**Corrección v1:** ventana declarada `nuisance_parameter` con exigencia de meseta: un candidato debe conservar signo y magnitud en ventanas vecinas.

---

## A7 — Faltaba contabilidad de tamaño efectivo y multiplicidad

El `v0` enumeraba SPA/StepM/PBO sin decir **cuánto** cuesta buscar tanto. Con la sesión como unidad de agrupamiento el tamaño efectivo es 201, no el número de ventanas.

MDE de un efecto medio por sesión, \(\alpha=0{,}05\) bilateral y potencia \(0{,}80\):

\[
\mathrm{MDE}=\frac{(z_{0{,}975}+z_{0{,}80})\,\sigma}{\sqrt{n}}
=\frac{2{,}80\,\sigma}{\sqrt{201}}\approx 0{,}197\,\sigma
\]

Con 17 frames el catálogo combinatorio es

```text
17 individuales
136 pares
680 tríos
= 833 combinaciones
```

Bajo control familiar tipo Bonferroni con \(m=833\):

\[
z\approx 4{,}01\quad\Rightarrow\quad \mathrm{MDE}\approx 0{,}34\,\sigma
\]

Y multiplicando por ocho ventanas, \(m=6\,664\):

\[
z\approx 4{,}48\quad\Rightarrow\quad \mathrm{MDE}\approx 0{,}375\,\sigma
\]

Es decir: buscar todo de una vez casi **duplica** el efecto mínimo detectable. La amplitud debe obtenerse por etapas, no por producto cartesiano simultáneo.

**Corrección v1:** `staged_screening` obligatorio — individuales sobre el universo completo, promoción sólo de mesetas, y pares/tríos restringidos a frames sobrevivientes, con `multiplicity_family` declarada antes de mirar resultados.

---

## A8 — Desbalance de clases y elección de métrica

Si el evento es raro, ROC-AUC puede lucir alto sin valor económico.

**Corrección v1:** publicar tasa base por celda, priorizar PR-AUC, log loss y calibración, y exigir `min_positive_events_per_cell`.

---

## A9 — Umbral de complejidad indefinido

«Superar al baseline» no es criterio.

**Corrección v1:** un modelo complejo debe mejorar la métrica primaria OOF en al menos el incremento pre-registrado, con IC bootstrap agrupado por sesión que excluya cero, y ganar en al menos 4 de 5 folds externos.

---

## Conclusión de la auditoría

El marco general resiste, pero `v0` no era ejecutable sin B1–B4: habría producido un dataset sin controles, folds inválidos, posible fuga entre contratos e invariantes imposibles de verificar.

`v1` corrige esos cuatro puntos y agrega las reglas de tamaño efectivo. El siguiente paso sigue siendo infraestructura fail-closed — validador, tests y notebook `00` — antes de construir features o entrenar cualquier modelo.
