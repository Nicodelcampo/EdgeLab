# Paridad por sesión CME — los tres contratos, con veredictos separados

- **Fecha:** 2026-08-24 · **Rama:** `foundation/f0b-compatibility-probe`
- **Herramienta:** `tools/compare_session_parity.py` (commit `eda2a07`)
- **Firewall:** outcomes `false` · bloque sellado `false` · edge `false`
- **Responde al checkpoint pedido por el auditor** antes de decidir Puerta 1

---

## 1. El resultado

| contrato | 1 datos | 2 partición | 3 aritmética | 4 causal (limpias) | contaminadas |
|---|---:|---:|---:|---:|---:|
| **GC 02-26** | 27/28 | 24/28 | **178.762/178.776** = 99,992 % | **170.861/170.862** = 99,9994 % | 7.914 |
| **GC 06-26** | 38/48 | 36/48 | 166.228/168.782 = 98,49 % | **161.460/161.460** = 100 % | 7.322 |
| **GC 04-26** | 16/49 | 14/49 | 120.231/152.199 = 78,99 % | **97.523/97.523** = 100 % | 54.676 |

Contra lo que daba el harness canónico sobre las mismas corridas:

| contrato | cobertura global | aritmética por sesión |
|---|---:|---:|
| GC 02-26 | **0,77 %** | 99,992 % |
| GC 06-26 | **10,3 %** | 98,49 % |
| GC 04-26 | **1,3 %** | 78,99 % |

> **`SESSION_RECOVERABLE_PARITY = RECOVERED`.** El `FAIL` global era un artefacto
> del indexado por número de barra acumulado: una diferencia de tick desplaza toda
> la numeración posterior y la comparación se vuelve ruido. Con la clave
> `(cme_session_id, bucket_index_within_session, t_start)` la paridad se recupera
> en cada frontera de sesión, que es donde ambos lados reinician la partición.

**El resultado más fuerte es la capa 4:** sobre cubetas causalmente limpias,
`n_hist`, `a_thr` y `a_pass` coinciden **100 %** en GC 06-26 y GC 04-26, y
**170.861 de 170.862** en GC 02-26. Un solo desacuerdo causal en tres contratos.

---

## 2. El defecto que hizo falta arreglar para poder medir

La primera corrida del comparador dio **0/0 sesiones**: el join no producía nada.

```python
# bigtrap2absorption.py:186
trade_date = str(sess_id)

# bars.py:91 — session_ids() devuelve DÍAS DESDE EPOCH, no una fecha
dias = idx.normalize().view("int64") // 86_400_000_000_000
return dias + (idx.hour >= 17)
```

El kernel Python emite `td=20416`; NT8 emite `td=20251124`. **Cualquier join por
`td` entre los dos lados da cero silenciosamente.** El campo también viaja en los
`ZONE_CREATED` de Python (l. 404).

Es **P-39** otra vez: la etiqueta dice *trade date*, el contenido es un índice de
días. No lo parcheé en el kernel —cambiar el `.py` mientras se mide la paridad es
cambiar el instrumento durante la medición—; el comparador clava las sesiones por
ventana de `t_start`, que es lo único que ambos lados expresan igual.

---

## 3. La contabilidad de contaminación causal

`abs_ring` se crea una vez (l. 117) y sólo excluye residuales (l. 407): **cruza
las fronteras de sesión intacto.** La partición reinicia; el historial causal no.

Por eso una divergencia contamina `a_thr`/`a_pass` durante hasta
`abs_lookback = 500` cubetas no residuales posteriores, **aunque el conteo de
ticks de la sesión siguiente coincida exacto**.

El comparador lleva esa contabilidad explícita y **no reinicia el historial
artificialmente**: una cubeta sólo cuenta como causalmente limpia si pasaron 500
no-residuales sin divergencia. Las 7.914 / 7.322 / 54.676 contaminadas quedan
declaradas, no barridas.

Esta corrección es del auditor. Yo venía asumiendo que la frontera de sesión
restauraba la comparabilidad completa: restaura la **geometría**, no el **estado
causal**.

---

## 4. Lo que NO queda explicado

**GC 04-26 tiene 33 de 49 sesiones con diferencia de datos** y la aritmética cae
a 79 %. Parte es cobertura de cinta —el export arranca `20260115` y la cinta
`20260119`, así que las primeras sesiones son parciales— pero 33 sesiones es
mucho para atribuirlo sólo a eso.

**GC 06-26 tiene dos sesiones con cero ticks de cinta** (`20260319`, `20260320`):
la cinta arranca `20260323`. El export cubre más que la cinta.

⇒ Las ventanas de cinta y de chart **no coinciden**, y eso todavía no está
resuelto. Es un problema de insumo, no de kernel, pero está abierto.

---

## 5. Estado corregido

```
GLOBAL_ACCUMULATED_PARITY     = FAIL       (artefacto del indexado, explicado)
SESSION_RECOVERABLE_PARITY    = RECOVERED  (medido, 3/3 contratos)
KERNEL_PARITY_ON_EQUAL_INPUT  = ~EXACT     (causal 100%; aritmetica 99,99% en 02-26)
TAPE_VS_CHART_COVERAGE        = ABIERTO    (GC 04-26 33/49; GC 06-26 dos sesiones sin cinta)
FILTRO_CME                    = NO CONECTADO (53 ticks fuera de horario censados)
OUTCOMES                      = NOT_OPENED
BLOQUE_SELLADO                = NOT_OPENED
```

---

## Aporte al referente

Tres `FAIL` que parecían decir "el kernel calcula distinto" decían en realidad
"el comparador no puede recuperarse de una diferencia de tick". La distinción no
es cosmética: con el indexado global, **cualquier** kernel —correcto o no— daría
`FAIL` sobre una ventana de 50 sesiones, porque basta un tick para desalinear
todo. El instrumento no tenía resolución para la pregunta que se le hacía.

## Nota de método

El bug del `td` merece registro aparte: el comparador dio `0/0` y eso es un
resultado *visiblemente* imposible, así que se investigó. Si el kernel hubiera
emitido un `td` con formato de fecha pero mal calculado, el join habría producido
un subconjunto plausible y nadie habría mirado. **El modo de fallo ruidoso salvó
la medición**; es el mismo argumento que sostiene el `fail-closed` del meta en el
harness canónico.
