# Contrato de features de modelos EXTERNOS pre-entrenados

**Fecha**: 2026-07-26 · **Referente**: `docs/NORTH_STAR.md` sha256
`21bb3b01a33e2b37…` · **Estado**: infraestructura construida, **modelo no
adoptado**.

Aplica a Kronos y a cualquier modelo pre-entrenado que quiera producir features
para el pipeline. Es el análogo de `kernel_contract.md` (kernels determinísticos)
y de `nt8_indicator_parity_contract.md` (paridad NT8), para una clase de feature
que ninguno de los dos cubre.

---

## 0-bis. REGLA DE AISLAMIENTO (Decisión 1 de Nico, 2026-07-26)

> **Ningún modelo externo corre dentro del entorno principal.**

`torch`/`transformers` **no entran al lock**. Kronos —y cualquier sucesor— corre
en un **entorno sidecar**: un venv separado, fuera de
`requirements/core-bridge-dev.lock`, documentado aparte. El repo principal
**sólo lee columnas cacheadas** producidas vía `pit_store`, con `weights_sha256`
y `seed` declarados.

**Por qué esto es más que higiene de dependencias.** El entorno principal es hoy
un lock liviano y auditable donde la suite corre en ~27 s sin GPU. Meter 2,5 GB de
PyTorch lo convertiría en un entorno que hay que reproducir con cuidado, y —lo
importante— **acoplaría la validación de paridad NT8 a la disponibilidad de un
modelo**. El día que una versión de torch rompa algo, se caería la verificación
del bridge, que no tiene nada que ver.

El corte también es conceptual: el sidecar **produce**, el principal **valida**.
Un artefacto cacheado con identidad content-addressed se puede auditar aunque el
modelo que lo generó ya no exista.

### Contrato del sidecar

| | |
|---|---|
| entorno | venv separado, fuera del lock principal |
| qué produce | JSONL de `PredictionRecord` vía `PITFeatureStore.to_jsonl()` |
| qué debe declarar | `ModelIdentity` completa: `weights_sha256`, `seed`, `lookback`, `horizon`, `n_paths`, `bar_spec` |
| qué lee el principal | **sólo** el JSONL cacheado, vía `PITFeatureStore.from_jsonl()` |
| cómputo | **CPU, muestreo POR EVENTO exclusivamente** (Decisión 2). Sin GPU, sin bar-a-bar |
| gates antes de consumir | X0–X4, en `edgelab/external/` — corren en el principal, sin torch |

**Decisión 2 en concreto**: por evento, 6E, ~1500 nacimientos de zona ⇒ ~0,8 h en
CPU. Bar-a-bar sobre 700k barras serían 16,2 días — descartado, no por costo sino
porque predecir en todas las barras es pagar 466× por información que no se usa.
La pregunta es sobre el régimen **cuando nace una zona**.

## 0. Por qué necesita contrato propio

Un kernel del bridge y un modelo pre-entrenado se parecen en la salida y en nada
más:

| | kernel del bridge | modelo pre-entrenado |
|---|---|---|
| reproducibilidad | mismo código + params ⇒ misma salida | depende de **pesos externos** que pueden moverse bajo el mismo tag |
| determinismo | total | **estocástico** (Monte Carlo) salvo que se siembre |
| auditabilidad | línea por línea contra NT8 | caja negra; sólo se audita la **forma** de la salida |
| dominio | construido para futuros intradía | preentrenado en cripto/acciones ⇒ **fuera de distribución** |
| costo | milisegundos | segundos por llamada |

Tratarlos con el mismo nivel de confianza sería el error. Por eso el paquete vive
en `edgelab/external/` y no en `edgelab/bridge/`.

---

## 1. Identidad — `ModelIdentity`

`config_id` no alcanza. Un modelo externo exige, además de los params:

| campo | por qué es obligatorio |
|---|---|
| `weights_sha256` | el **nombre no identifica**: el mismo tag de HuggingFace puede apuntar a pesos distintos en dos momentos. Sin el hash del archivo real, dos corridas no son comparables |
| `seed` | con `n_paths > 1` la salida es estocástica. Sin semilla el backtest no es reproducible, y un resultado irreproducible no es evidencia |
| `context_bars` vs `lookback_bars` | si `lookback > context` el modelo **trunca en silencio** y el feature deja de ser lo que dice ser. Rechazado en construcción |
| `n_paths`, `horizon_bars`, `bar_spec` | cambian la salida ⇒ entran al `model_id` |

`model_id` = sha256 de todo eso, 16 hex. Cambiar cualquiera produce otro id, y
por lo tanto otro store: **nunca** se mezclan dos modelos en la misma columna.

---

## 2. La regla central — TRES timestamps, no uno

Toda la trampa de look-ahead se reduce a confundir instantes. El contrato exige
los tres, separados:

| campo | qué es |
|---|---|
| `generated_at_ns` | cierre de la **última barra que el modelo pudo ver** |
| `target_ts_ns` | el instante que la predicción **describe** |
| `available_at_ns` | cuándo la predicción **existe y se puede usar** |

**Invariantes, verificadas en construcción:**

```
generated_at_ns  <  target_ts_ns          # si no, no es una predicción
generated_at_ns <=  available_at_ns       # si no, existe antes que sus datos
```

### El bug que esto previene

```python
# LO QUE TODO EL MUNDO ESCRIBE — y está mal
pred = predictor.predict(df)      # sobre la serie ENTERA
df["p_up"] = pred["p_up"]         # join por índice
```

El índice que devuelve el modelo es `target_ts`, no `generated_at`. Ese `join` le
da a cada barra una predicción hecha con datos de **esa misma barra o
posteriores**. No hay ninguna línea tramposa: el bug está en el índice. Es el
mecanismo exacto que produce un AUC de 0,9997.

`PITFeatureStore` indexa por `available_at` y sirve estrictamente as-of, así que
ese código no se puede escribir. `causality.diagnose_join()` además diagnostica
el caso antes de que llegue al store.

### `available_at` no es igual a `generated_at`

Generar 30 caminos Monte Carlo sobre 400 barras de contexto lleva **segundos**.
Tratar la predicción como disponible en el mismo instante en que se generó es un
look-ahead más chico que el del `join`, pero sigue siendo look-ahead: en vivo esa
predicción no habría estado lista. La latencia se declara y se **mide**, no se
asume cero.

Mismo vocabulario que `edgelab.research.sim`, a propósito.

---

## 3. Prueba de causalidad — **target-free**

La prueba definitiva no necesita P&L, retornos ni etiquetas:

> **Invariancia por truncamiento.** Si `f` es causal, para todo `t`
> `f(datos[:t+1])[t] == f(datos_completos)[t]`.

Una función que mira hacia adelante **no puede** cumplirlo: al truncar, lo que
miraba deja de existir. Es una prueba **positiva** de causalidad, no una
sospecha, y corre sobre datos sintéticos — no consume oráculo ni toca el holdout.

Esto importa por dos razones prácticas:

1. El método habitual (ver un AUC sospechoso) llega **tarde**: exige haber
   corrido una búsqueda sobre retornos, que en este proyecto está bajo STOP.
2. Un AUC bajo **no descarta** un leak chico que igual invalida el resultado.

`causality.assert_causal()` muestrea posiciones de forma determinista y
**sesgada hacia el final** de la serie: un leak de pocas barras es invisible en
el medio pero no tiene dónde esconderse en las últimas posiciones.

El detector se prueba contra `LeakyMockPredictor`, que mira `bars[i+horizon]` a
propósito. Sin ese test, el firewall sería decoración.

---

## 4. Frescura — `max_staleness_ns`

Sin límite, un hueco de cómputo (se cortó el precomputado, falló la GPU, hubo
feriado) hace que una predicción vieja se propague hacia adelante durante horas y
el backtest la trate como fresca. Con el límite, el feature pasa a `NaN` y la
estrategia tiene que decidir **explícitamente** qué hacer sin él.

El valor sale de la cadencia: `feasibility.staleness_de_cadencia(cadencia, bar_ns)`.
Predecir cada 15 barras y después tratar el valor como fresco 15 barras es una
decisión — conviene que sea explícita. En régimen cambiante una `sigma_pred` de
hace 15 minutos puede describir otro mundo.

---

## 5. Factibilidad — **antes** de gastar

Un feature que no se puede computar sobre el rango de backtest no es un feature,
es una idea. `feasibility.py` lo contesta en un segundo.

**MNQ 1 min, 2 años (~700k barras), Kronos-small, 30 caminos, ~2 s/llamada, CPU:**

| política | llamadas | horas | ¿una noche? |
|---|---:|---:|---|
| todas las barras | 700 000 | 388,9 | **NO** (16,2 días) |
| cada 5 barras | 140 000 | 77,8 | NO |
| cada 15 barras | 46 666 | 25,9 | NO |
| cada 60 barras | 11 666 | 6,5 | sí |
| **por evento (n=1500)** | **1 500** | **0,8** | **sí** |

Con GPU (~0,15 s/llamada, batch 8) hasta bar-a-bar entra en 3,7 h — o sea que la
decisión CPU/GPU **cambia qué experimentos son posibles**, no sólo cuánto tardan.

> El muestreo **por evento** es a la vez el más barato y el más alineado con el
> proyecto: las zonas ya son el evento de interés. La pregunta de CAMP-002 no es
> "¿qué predice Kronos a cada minuto?" sino "¿el régimen previsto **cuando nace
> una zona** dice algo sobre esa zona?". Predecir en todas las barras sería pagar
> 466× por información que no se usa.

---

## 6. Gates que un feature externo debe pasar

En orden, **fail-closed**: no se avanza al siguiente sin el anterior.

| gate | qué exige | consume |
|---|---|---|
| **X0 identidad** | `ModelIdentity` válida, con `weights_sha256` real y semilla | nada |
| **X1 causalidad** | `assert_causal` verde + `store.audit()` limpio | nada (sintético) |
| **X2 factibilidad** | costo medido —no estimado— y política de muestreo declarada | una corrida chica |
| **X3 reproducibilidad** | dos corridas con la misma identidad ⇒ features byte-idénticas | dos corridas |
| **X4 OOD declarado** | riesgo de distribución escrito **antes** de mirar resultados | nada |
| **X5 lift** | manifiesto de campaña + **OK de Nico** | **STOP** |

**X5 está bajo la regla STOP del `CLAUDE.md`**: toda búsqueda sobre P&L/retornos
exige manifiesto, número efectivo de hipótesis, riesgos y datos faltantes, con
aprobación previa. La campaña está pre-registrada y **sin correr** en
`docs/campaigns/CAMP-002_kronos_regime_filter.md`.

---

## 7. Riesgos declarados de Kronos (antes de cualquier resultado)

1. **Fuera de distribución.** El preentrenamiento es mayormente cripto y
   acciones. Futuros intradía —ETH/RTH, gaps de overnight, GLOBEX— es otro
   régimen de microestructura, y es **el dominio del proyecto entero**. No es un
   detalle a verificar después: es la hipótesis principal a refutar.
2. **Contaminación de muestra.** Kronos se preentrenó con datos que
   probablemente **incluyen el período de backtest**. No es look-ahead —el
   modelo no ve el futuro de *esta* serie— pero sí significa que ya "vio"
   regímenes parecidos. Es irreparable con zero-shot y hay que declararlo en
   cualquier resultado positivo.
3. **Dependencias.** `torch` + `transformers` ≈ 2,5 GB, contra la regla "sin
   dependencias pesadas nuevas; sin CUDA" del `CLAUDE.md`. **No los instalé.**
4. **Expansión del espacio de búsqueda.** Tres features nuevas multiplican las
   hipótesis. Es la misma razón por la que F9 está pausada, y por eso CAMP-002
   fija el número efectivo de hipótesis **antes** de correr.

---

## 8. Qué está construido y qué no

| pieza | estado |
|---|---|
| `contract.py` — identidad + record + ABC | ✅ |
| `pit_store.py` — store as-of con los tres timestamps | ✅ |
| `causality.py` — detector adversarial target-free | ✅ |
| `mock.py` — predictor honesto **y** tramposo | ✅ |
| `feasibility.py` — costo antes de gastar | ✅ |
| `kronos.py` — adaptador | ✅ interfaz, ❌ modelo (no instalado) |
| tests | ✅ 28, sin torch |
| muestreo real de Kronos | ❌ requiere decisión de dependencias |
| evaluación de lift | ❌ **STOP** — requiere OK de Nico |

Que todo esto corra **sin torch** no es comodidad: es lo que permite que el
firewall causal se verifique en cada commit, y que el día que Kronos entre lo
haga detrás de una interfaz ya probada. El orden inverso —instalar primero,
construir los controles después— es cómo se llega a un AUC de 0,9997.
