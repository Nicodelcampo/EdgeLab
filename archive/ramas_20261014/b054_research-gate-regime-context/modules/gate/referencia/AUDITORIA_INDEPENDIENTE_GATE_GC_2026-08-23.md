# Auditoría independiente de GATE y adaptación a GC — complemento técnico

- **Fecha:** 2026-08-23
- **Rama auditada:** `research/gate-regime-context`
- **Tip de entrada:** `8d631e68f86eca72e94777bfc52a1d5fb1ac6d3c`
- **Alcance:** módulo GATE, documento externo de regímenes y auditoría previa.
- **Firewall:** revisión estática y target-free; no se abrieron outcomes, holdout ni P&L; no se modificó `.cs`, kernel, harness ni el protocolo de Puerta 1.
- **Carácter:** complemento independiente. No reemplaza `AUDITORIA_DOC_REGIMENES_2026-08-23.md`.

---

## 0. Veredicto ejecutivo

```text
CLASIFICACIÓN          FOUNDATION_ONLY / CIMENTO EXPERIMENTAL
ESTADO OPERATIVO       NOT_OPERATIONAL
CORRIDA FORMAL         PROHIBIDA EN EL TIP AUDITADO
EDGE                    NO EVALUADO / NO DECLARABLE
ADAPTACIÓN GC          POSIBLE, pero requiere contrato y model_id nuevos
ORDEN                   cerrar precondiciones y Puerta 1 antes de outcomes con GATE
```

La separación arquitectónica es correcta: indicador exporta, GATE etiqueta offline y un trial posterior decide si el contexto informa. También son correctas la intención de usar joins point-in-time, el firewall de outcomes y la pregunta incremental contra un baseline.

Pero el tip auditado no contiene un detector congelado ejecutable. Contiene una especificación, demos sintéticas, un adaptador y artefactos de cableado. Además hay bloqueantes de empaquetado, causalidad, identidad semántica y diseño inferencial que impiden considerar formal cualquier label producido por el pipeline actual.

La conclusión es más restrictiva que la auditoría previa: **no alcanza con renombrar OFI y corregir el hash**. Primero hay que volver ejecutable y fail-closed el contrato completo.

---

## 1. Qué se subió realmente

La historia de la rama separa dos cargas:

1. `bc92a557cbc7b840cdc1d70568739764b690294b`
   - incorpora el módulo GATE;
   - `files[] = 30`, `+6.252/-0`;
   - incluye `modules/README.md` y 29 archivos bajo `modules/gate/`;
   - el commit inmediatamente anterior en la historia es `f543730c...`, la enmienda del universo de 152 sesiones.
2. `8d631e68f86eca72e94777bfc52a1d5fb1ac6d3c`
   - `files[] = 3`, `+628/-0`;
   - agrega los dos documentos de `modules/gate/referencia/`;
   - además modifica `modules/gate/ESTADO.md` con la sección de referencia y G-4.

Por lo tanto, `8d631e6` no subió sólo dos archivos: fueron **dos altas y una modificación**. El conteo verificable del ingreso original tampoco es 28 sino 30 archivos en el commit, aunque dos estén fuera del inventario funcional central.

La app web no está en la rama. Desde el repo se puede verificar su ausencia, pero no se pueden auditar de forma independiente ni sus 293 archivos ni la calidad del TypeScript descartado sin el zip original. Su exclusión es prudente; las afirmaciones sobre su contenido quedan como provenance externa, no como evidencia reproducida acá.

---

## 2. Hallazgos bloqueantes nuevos

### I-1 · El módulo no corre desde el layout subido — **BLOCKER, verificado por fuente**

`core/gate_adapter.py` define:

```python
SCHEMA_PATH = Path(__file__).resolve().parent / "gate_context_schema_v1.json"
```

pero el único schema está en:

```text
modules/gate/schema/gate_context_schema_v1.json
```

No existe `modules/gate/core/gate_context_schema_v1.json`. `validate_events()` llama `load_schema()` antes de etiquetar, por lo que el flujo falla con `FileNotFoundError` en el layout versionado.

Además, `pipeline.py` importa `gate_adapter` como módulo de nivel superior y depende de un `PYTHONPATH` manual que incluya `core/`. Aun configurándolo como pide el handoff, la ruta del schema sigue rota.

**Consecuencia:** los artefactos de ejemplo no demuestran que el commit actual sea reproducible. Fueron generados en otro layout (`/home/workdir/artifacts/...`).

**Cierre requerido:** paquete instalable o imports relativos, ruta única al schema y un smoke test ejecutado desde la raíz limpia del repo.

### I-2 · No hay un modelo congelado; hay un nombre de modelo — **BLOCKER**

`gate_model_id_frozen.json` declara:

```text
architecture = BalancedTransformer_or_HMM3_forward
preferred    = TF_causal_bal
```

`or` no identifica una arquitectura única. Tampoco se versionan:

- pesos o checkpoint;
- hash de pesos;
- ventana de entrenamiento y contratos;
- definición exacta y ventanas de los diez features;
- labels de entrenamiento;
- versión del código de entrenamiento e inferencia;
- manifest de datos y normalizadores.

El pipeline formal no carga un Transformer ni un HMM. Si recibe una columna `regime`, la acepta; si no, fabrica un proxy. Por tanto el `model_id` no está ligado a inferencia alguna.

**Consecuencia:** dos productores incompatibles pueden emitir el mismo `model_id` y ambos pasar por GATE.

**Cierre requerido:** un solo estimador, checkpoint inmutable, manifest completo y verificación automática `model_id ↔ config ↔ weights ↔ code ↔ feature contract`.

### I-3 · El join no está aislado por símbolo, contrato ni sesión y no tiene tolerancia — **BLOCKER**

`asof_regime_at_t0()` ejecuta un `merge_asof` global sólo por timestamp:

```python
pd.merge_asof(ev_sorted, bars, left_on="t0", right_on="ts", direction="backward")
```

No usa `by=symbol`, contrato ni `session_id`, y tampoco fija `tolerance`.

Esto permite que:

- un evento tome una barra de otro instrumento/contrato si se concatenan series;
- un evento al inicio de una sesión tome la última barra de la sesión anterior;
- una barra arbitrariamente vieja produzca `as_of_ok=true`.

El schema exige `symbol`, pero `validate_events()` sólo requiere `event_id`, `t0` y `session_id`; el output además descarta `symbol`.

**Cierre requerido:** join por identidad de mercado y sesión, tolerancia máxima predeclarada, conservación de `symbol/contract/session_id` y tests adversariales de cruce de sesión/roll.

### I-4 · `as_of_ok` no significa “todas las features disponibles” — **BLOCKER**

El schema define `as_of_ok=true` sólo si todas las features están disponibles en `t0`. El código verifica únicamente:

```python
merged["ts"].notna() & merged["regime"].notna()
```

Los posteriors pueden quedar `NaN`, `vpin` puede quedar `NaN` y `sticky_age_bars` puede ser `-1`, aun con `as_of_ok=true`.

**Cierre requerido:** validación de dominio y completitud de todos los campos requeridos; posterior finito, suma compatible con 1, régimen válido, VPIN finito si el overlay lo usa, sticky no negativo y feature timestamp explícito.

### I-5 · Hay look-ahead intrabar en la ruta ticks → barras — **BLOCKER**

`from_ticks.py` usa `resample("1min")` con los defaults de pandas y conserva el índice de inicio del minuto. Ese registro agrega ticks de todo el intervalo, pero queda timestampado al comienzo. Luego `merge_asof(..., direction="backward")` puede asignarlo a un evento ocurrido dentro de ese mismo minuto.

Ejemplo conceptual:

```text
bar timestamp 10:00:00 contiene ticks hasta 10:00:59
evento t0      10:00:15
merge_asof     acepta la barra 10:00:00
```

El evento recibe información posterior a `t0`. Afecta OHLC, volumen, signed flow, spread, tick count, RV, VPIN proxy y ER.

**Cierre requerido:** separar `bar_start` de `feature_available_at`; etiquetar al cierre efectivo del bin o desplazar una barra completa; test con un tick centinela posterior al evento que no pueda alterar el label.

### I-6 · La ruta proxy usa cuantiles de muestra completa — **BLOCKER**

`_ensure_regime_on_bars()` calcula:

```python
q1, q2 = np.nanquantile(x, [0.33, 0.66])
```

sobre toda la serie. Aunque el proxy se declare “sólo cableado”, es un régimen definido con futuro y viola la prohibición del propio schema contra normalización full-sample. Después emite artefactos normales con `as_of_ok=true`.

Además el CLI cae silenciosamente a fixtures si falta `--events` o `--bars`:

```python
if args.fixture or not args.events or not args.bars:
```

Un argumento omitido produce un run sintético exitoso, no un error.

**Cierre requerido:** eliminar el proxy del path formal; `--allow-proxy-regime` y `--fixture` deben ser flags explícitos, incompatibles con `--formal`; faltar un input debe abortar.

### I-7 · La semántica temporal del evento no está congelada — **HIGH**

El alias de `t0` acepta como equivalentes:

```text
t_start, bucket_start, zone_start, StartTime, fill_time
```

No son el mismo instante económico. `fill_time` puede ser posterior a la decisión; `bucket_start` puede ser anterior a que exista la evidencia completa del evento. La causalidad del join no corrige una definición equivocada de `t0`.

**Cierre requerido:** elegir un único `decision_available_at` por familia de eventos, derivado del contrato exportado y con assertion de que ninguna feature ni geometría usada para detectar el evento aparece después.

### I-8 · El ejemplo vuelve a usar fecha UTC como sesión — **HIGH**

`events_from_bars()` construye:

```python
"trade_date": str(bars["time"].iloc[i])[:10]
```

Eso es fecha calendario UTC, no sesión CME. Es exactamente la unidad que ya produjo dos conclusiones erróneas en la cadena de GC.

Aunque los eventos sean sintéticos, el artefacto se presenta como validación sobre ticks reales y alimenta la cobertura por sesión.

**Cierre requerido:** una sola función versionada `cme_session_id`, compartida con Puerta 1 y probada en apertura 17:00 CT, medianoche UTC, DST, fines de semana y rolls.

---

## 3. Identidad semántica: OFI no es el único nombre problemático

### I-9 · `ofi_ema_z` es tape imbalance — **CONFIRMA D-1 / G-4**

La auditoría previa es correcta: `sign(aggressor) × volume` agregado no es OFI de libro. Con L1 sin tamaños ni eventos BBO no se puede reconstruir Cont–Kukanov–Stoikov.

Esto afecta directamente al `model_id` actual porque `ofi_ema_z` sí figura entre sus diez features. Requiere nombre y `model_id` nuevos.

### I-10 · El `vpin` de la ruta real tampoco es VPIN canónico — **HIGH, hallazgo nuevo**

`from_ticks.py` calcula:

```python
tape_imb = signed_volume / volume
vpin = abs(tape_imb).rolling(30).mean()
```

sobre barras de un minuto. El documento de referencia define VPIN mediante buckets sincronizados por volumen. El código implementa una media móvil de imbalance absoluto por tiempo, que puede ser un proxy útil, pero no es el objeto que declara `vpin055`.

El estado `toxico` depende del umbral 0,55. Por lo tanto el error cambia labels, no sólo nombres.

**Cierre requerido:** o implementar VPIN con buckets de volumen y congelar todos sus parámetros, o renombrar a `abs_tape_imbalance_30m` y emitir otro `model_id`.

### I-11 · Kyle λ no contamina hoy los diez features congelados — **corrección de alcance**

Kyle λ aparece en el documento de referencia y sería problemático si se estima con el proxy mal nombrado. Pero **no figura** en la lista de diez features de `gate_model_id_frozen.json`.

Así que:

- `ofi_ema_z`: defecto actual del model_id;
- VPIN: defecto actual de la ruta ticks;
- Kyle λ: deuda de una adaptación futura, no prueba adicional contra el modelo congelado actual.

### I-12 · El documento externo es referencia, no “la especificación que GATE implementa” — **MEDIUM**

El documento aporta racional de familias, causalidad y anti-patrones. Pero no fija:

- ventanas exactas;
- transformaciones;
- entrenamiento;
- estados y mapeo semántico;
- pesos;
- thresholds salvo ejemplos generales;
- contrato de disponibilidad temporal.

Sus siete familias no son una especificación exacta de los diez features. Las fases de reloj aparecen como tesis general, no como aprobación para GC.

Debe quedar clasificado como **referencia de diseño**, no como provenance suficiente del `model_id`.

---

## 4. El “Transformer” es un demo, no un estimador reproducible

### I-13 · El entrenamiento no optimiza la red que usa `forward()` — **BLOCKER para ese candidato**

En `MiniTransformerRegime.fit()` sólo se actualizan `W_out`, `b_out` y `W_in`, usando un surrogate:

```python
H0 = tanh(X @ W_in)
```

La inferencia real de `forward()` pasa por atención, residuals y FFN. Los pesos `W_q`, `W_k`, `W_v`, `W_o`, `W_ff1` y `W_ff2` quedan aleatorios; el gradiente aplicado no corresponde a la función forward que se evalúa.

No hay checkpoint guardado. En consecuencia, “Transformer causal balanceado” describe un experimento sintético, no un modelo entrenado utilizable.

### I-14 · La imputación “causal” mira el futuro al comienzo — **HIGH**

`impute_causal()` hace:

```python
first = idx[0]
col[:first] = col[first]
```

Rellena el prefijo faltante con el primer valor observado posteriormente. Eso es backfill desde el futuro. Luego sí hace forward-fill causal.

**Cierre requerido:** warmup excluido o valor derivado sólo del train previo; nunca rellenar hacia atrás. Registrar cuántas barras/eventos se excluyen.

---

## 5. El filtro target-free todavía no protege de contaminación

### I-15 · El veredicto usa una codificación ordinal arbitraria — **HIGH**

`corr_regime_ancho()` calcula Pearson entre `ancho_ticks` y códigos `0,1,2,3`, y el veredicto usa sólo ese valor. Pero `toxico=3` es un overlay, no necesariamente “más” del mismo eje latente. Una asociación fuerte no monotónica puede cancelar y producir Pearson cercano a cero.

El código calcula point-biserial por estado, pero no lo incorpora al gate.

**Cierre requerido:** predeclarar un diagnóstico omnibus y por estado, con IC/bootstrap por sesión. Como mínimo, gatear también por el máximo `|one-vs-rest|`; preferiblemente usar diferencias estandarizadas/η² y una prueba de permutación a nivel sesión.

### I-16 · Cobertura no equivale a potencia — **HIGH**

`session_coverage()` cuenta sesiones con al menos un evento en cada uno de cuatro estados. CTX-3 propone dos celdas agregadas (`operable` y `estrés`) y su inferencia es por sesión. Una sesión con un evento cuenta igual que una con cientos, y no se reportan eventos utilizables por sesión/celda ni balance efectivo.

El piso de 40 es una regla de cobertura, no un MDE.

**Cierre requerido:** capacidad por celda primaria, distribución de eventos por sesión, número de sesiones con ambas celdas si el contraste es pareado, y MDE bajo la inferencia exacta elegida.

### I-17 · El paso incremental no implementa todavía la inferencia del pre-registro — **HIGH**

`gate_incremental_vs_pctrv.py` usa OLS y F/LR estándar sobre una demo, más una regla `ΔR² > 0,01`. CTX-3, en cambio, declara bootstrap de sesiones, IC 95 % y Holm. No hay robustez a heterocedasticidad, permutación, ni justificación congelada del 1 %.

El concepto incremental es correcto; el motor estadístico formal todavía no está alineado.

---

## 6. Correcciones a la lectura previa para GC

### 6.1 B-9 sobre 115 no puede cerrar la escala de GATE

La conclusión “en GC el régimen es de sesión, no de minutos” se apoya en B-9 de 115 sesiones y rolls viejos. El universo fue enmendado a 152 sesiones y el propio proyecto declaró B-9 pendiente de rehacer.

Los valores 3,18× entre sesiones y 1,39× intradía son una **señal de diseño**, no un hecho congelable para la adaptación GC hasta reproducirlos sobre 152.

### 6.2 Las proyecciones de L2 son presupuestos, no mediciones del universo

Los 14,2 MB/sesión salen de 12 sesiones DEC26 y se extrapolan. Actividad, profundidad, contrato y compresión pueden cambiar. Los 0,3/0,6/2,1 GB son estimaciones útiles de orden de magnitud, no tamaños garantizados.

### 6.3 Las 6.206 observaciones no “resuelven” cobertura

Son eventos del universo viejo de 115 sesiones según el artefacto N_RAND actualmente versionado; B-9 y N_RAND deben rehacerse sobre 152. Además, disponibilidad de eventos no implica que existan labels GATE válidos ni potencia por celda.

---

## 7. Adaptación honesta a GC

### 7.1 Versión L1/trades inicial

Crear un candidato nuevo, explícitamente no congelado, por ejemplo:

```text
gate_gc_l1_causal_v0
```

Features candidatas que sí describe la cinta:

- `realized_vol_*`;
- `efficiency_ratio_*`;
- `tape_imbalance_ema_z_*`;
- `spread_ticks_z_*`;
- `tick_rate_z_*`;
- memoria/path sólo tras validar warmup y causalidad.

No llamar OFI a signed flow. No llamar VPIN a una media por tiempo. No incluir `phase_*` en el candidato inicial: primero debe demostrar aporte ortogonal a hora/tick rate y superar la lección de CTX-2.

### 7.2 Identidad mínima de un model_id nuevo

El manifest debe fijar, como mínimo:

- instrumento y contratos de train/validation;
- calendario y `cme_session_id`;
- frecuencia y `feature_available_at`;
- fórmula y ventana exacta de cada feature;
- warmup y política de missing;
- normalizadores y hashes;
- arquitectura única y versión de librerías;
- seed, pesos y hash de checkpoint;
- sticky/histeresis;
- definición exacta del overlay tóxico;
- hash canónico verificado por script;
- hashes de inputs y commit de código.

### 7.3 L2 como prueba incremental, no requisito implícito

Después de Puerta 1, usar primero 25 sesiones front-month comparables para una pregunta target-free y predeclarada:

```text
¿OFI/depth real agrega estabilidad o información de régimen por encima de
trade imbalance + RV + spread + actividad, sobre exactamente las mismas sesiones?
```

Ese piloto sirve para validar features y costo de adquisición; no para declarar edge. Sólo si hay valor incremental y el pipeline causal está cerrado conviene ampliar L2 a 152 sesiones.

### 7.4 Controles de ortogonalidad obligatorios

Antes de cualquier outcome condicionado, medir a nivel sesión y evento:

- asociación con `a_thr`;
- hora de Chicago/bin de 30 min;
- tick rate;
- spread;
- contrato/roll;
- volumen y duración de sesión;
- ancho del evento, con tests no sólo ordinales.

El control relevante no es sólo “corr baja”. Debe existir comparación emparejada `con indicador vs sin indicador` dentro de contexto, y un baseline explícito sin GATE.

---

## 8. Orden de trabajo recomendado

### En `foundation/f0b-compatibility-probe`

1. Auditar la enmienda de universo y los cuatro rolls en la unidad sesión CME.
2. Rehacer B-9 sobre 152 sesiones.
3. Rehacer capacidad N_RAND sobre 152 sesiones.
4. Congelar artefactos/spec coherentes y recién entonces pedir decisión humana para abrir Puerta 1.
5. Ejecutar Puerta 1 una vez, según el pre-registro vigente.

### En `research/gate-regime-context`, sin outcomes

1. Reparar layout/imports/schema y agregar tests desde checkout limpio.
2. Eliminar defaults fail-open (fixtures y proxy implícitos).
3. Corregir joins por identidad/sesión/tolerancia y disponibilidad intrabar.
4. Corregir semántica de sesión CME y de `t0`.
5. Elegir L1 honesto o L2 real; renombrar OFI/VPIN y emitir model_id nuevo.
6. Implementar un detector real con checkpoint y manifest reproducible.
7. Rediseñar el gate target-free y la capacidad/MDE por celdas.

### Después de Puerta 1

1. Decidir si GATE merece continuar como contexto.
2. Si continúa, crear un pre-registro **GC específico**. No editar silenciosamente `H-ES-CTX-3`, cuyo instrumento declarado es ES.
3. Correr labels reales target-free y ortogonalidad.
4. Congelar estimando, contraste, Holm, MDE y reglas de cierre.
5. Sólo entonces abrir outcomes condicionados.

---

## 9. Matriz de decisión

| Componente | Estado en `8d631e6` | Decisión |
|---|---|---|
| documento de regímenes | referencia útil, sin medición | conservar como bibliografía |
| app web | ausente; descarte no reproducible desde repo | mantener afuera |
| schema/adaptador | intención correcta, layout y fail-closed incompletos | reparar antes de ejecutar |
| as-of join | backward, pero sin identidad/tolerancia y con leak intrabar | no apto formal |
| detector | no existe como artefacto congelado | implementar o descartar |
| `ofi_ema_z` | tape imbalance mal nombrado | nuevo nombre + model_id |
| `vpin055` | proxy temporal, no VPIN canónico | implementar o renombrar |
| Transformer | demo sintética, entrenamiento no corresponde al forward | no usar |
| target-free | diagnóstico preliminar, gate incompleto | rediseñar |
| CTX-3 | ES, estimando/contraste/MDE abiertos | no congelable |
| adaptación GC L1 | factible | prototipo posterior a reparaciones |
| L2 completo | descargable pero prematuro | piloto 25 sesiones después de P1 |

---

## 10. Cierre

GATE sí merece quedar en una rama propia como cimiento porque contiene una arquitectura de separación útil y preguntas correctas. Pero el valor actual es documental y de prototipado, no operacional.

El riesgo dominante no es que “el régimen no tenga edge”. Es anterior: **hoy el pipeline puede producir labels plausibles cuya fuente, instante de disponibilidad, identidad de sesión, modelo y semántica no coinciden con lo declarado**.

Por eso el próximo paso correcto no es correr GATE sobre 6.206 eventos ni descargar 152 sesiones L2. Es cerrar el contrato causal y reproducible; en paralelo, completar B-9 y N_RAND sobre 152 y preservar el orden vinculante:

```text
Puerta 1 primero -> decisión de continuar GATE -> pre-registro GC -> outcomes condicionados
```
