# Capacidad de estratos de `N_RAND` — **`N_RAND_CAPACITY_OK`**

- **Fecha:** 2026-08-23 · **Base:** `135a3af`
- **Firewall:** outcomes `false` · **target-free** — cuenta anclas candidatas, no mide resultados
- **Responde a:** `specs/bt2_absorption_gate1_v1.json` → `n_rand.sparse_stratum_policy`
- **Artefacto:** `docs/research/NRAND_CAPACIDAD_ESTRATOS.json`

---

## 1. Veredicto

```
N_RAND_CAPACITY_OK
estratos con evento : 3.173
estratos flacos     : 0
```

**Ningún estrato queda sin capacidad.** `PRECONDITION_FAILED_SPARSE_STRATUM` **no** se dispara,
y no hace falta ensanchar ningún bin — lo que el spec prohíbe explícitamente
(`silent_bin_expansion: false`).

| contrato | sesiones | eventos | estratos | flacos | anclas elegibles | `cap=ticks` |
|---|---:|---:|---:|---:|---:|---:|
| GC 04-26 | 50 | 2.668 | 1.307 | **0** | 6.773.687 | 55,7 % |
| GC 06-26 | 42 | 2.156 | 1.155 | **0** | 4.403.616 | 36,6 % |
| GC 08-26 | 25 | 1.382 | 711 | **0** | 2.768.328 | 39,7 % |
| **total** | **115** ⁽¹⁾ | **6.206** | **3.173** | **0** | **13.945.631** | — |

⁽¹⁾ GC 04-26 aporta 50 sesiones acá contra 48 en B-9: B-9 exige `n_hist >= 200` (excluye el
burn-in) y esto no, porque la elegibilidad de un ancla no depende del umbral.

### 1.1 Holgura

```
anclas candidatas por evento:   min 29 | p01 255 | p10 603 | p50 1.393
```

El sorteo es **sin reemplazo dentro de cada réplica**, así que la condición dura es
`anclas >= eventos` en cada estrato. **El peor estrato de los 3.173 tiene 29 anclas para su
evento.** La mediana tiene 1.393. No hay caso apretado.

---

## 2. Cómo se contó

**Estrato** = `sesión CME × contrato × bin de 30 min desde las 17:00 CT × cap_driver`, tal como
lo congela `n_rand.strata`.

**Ancla elegible** = índice de tick cuyo **horizonte completo cae dentro de la misma sesión
CME**. El horizonte es el primero que ligue entre 2.000 ticks y 900 segundos
(`horizon.first_cap_wins`), y el borde de sesión es duro
(`horizon.session_boundary: hard`, `cross_session_label: EXCLUDED_FILL_CROSSES_SESSION`).

El ancla real se **excluye** de su propio estrato (`n_rand.exclude_exact_real_anchor: true`);
los vecinos no (`exclude_neighboring_windows: false`).

### 2.1 El borde de sesión casi no cuesta

```
ticks en ventana    14.001.325
anclas elegibles    13.945.631   (99,6 %)
descartadas          55.694      (0,4 %, horizonte cruza el cierre)
```

Era el riesgo principal —que los bins pegados al cierre se quedaran sin candidatos— y no se
materializa: el horizonte de 2.000 ticks / 900 s es corto contra una sesión de 23 h.

### 2.2 El `cap_driver` no está equilibrado, y varía por contrato

| contrato | liga primero el tope de ticks | liga primero el reloj |
|---|---:|---:|
| GC 04-26 | 55,7 % | 44,3 % |
| GC 06-26 | 36,6 % | 63,4 % |
| GC 08-26 | 39,7 % | 60,3 % |

El auditor midió **47,7 % / 52,3 %** sobre las 5 sesiones de agosto y lo llamó *«moneda al
aire»*. Sobre 115 sesiones **oscila entre 36,6 % y 55,7 % según el contrato** — o sea que cuál
de los dos horizontes manda depende del régimen de actividad del período, no es una constante.

**No cambia nada del diseño** —`cap_driver` ya es uno de los cuatro estratos, justamente para
que esto quede emparejado— pero confirma que era necesario estratificarlo. Es el tercer caso del
día en que un número medido sobre 5 sesiones no sobrevive a 115.

---

## 3. Población de eventos

```
6.206 eventos K_ABS en 115 sesiones  =  54,0 por sesion
```

Contra el mínimo de `n >= 200` que pedía el protocolo original para Puerta 1: **sobra por 31×**.

La restricción de Puerta 1 **no es la cantidad de eventos, es la cantidad de sesiones** — la
inferencia usa la sesión como cluster con peso 1
(`inference.cluster: cme_session`, `equal_session_weights: true`), así que el `n` efectivo es
**115**, no 6.206. Por eso `P1_UNDERPOWERED_FOR_2P5T` sigue en pie: 74,4 % de potencia contra la
vara de 2,5 ticks.

---

## 4. Estado — **todos los pasos target-free cerrados**

```
PUERTA_0                 = FINAL_PUERTA0_SIGNED        (GC 12-26, agosto)
PARITY_PRECONDITION      = SATISFIED                   (GC 08-26, 2026-06-18..06-30, 100%)
LOADER_700K              = CORREGIDO, fail-closed, sin regresion
HARNESS                  = --tape + tick_size del meta -> ya no atado a GC
B9_CONTEXTO              = COMPLETO, NO BLOQUEA
   entre sesiones 3,18x | intradia 1,39x | tick_rate 7,58x | spread descalificado
NRAND_CAPACIDAD          = N_RAND_CAPACITY_OK          (0 de 3.173 estratos flacos)
SESIONES                 = 115
EVENTOS                  = 6.206  (54,0 por sesion)
P1_UNDERPOWERED_FOR_2P5T = ADJUNTO                     (potencia 74,4%)
ROLL_RULE                = enmienda propuesta, sin decidir
OUTCOMES                 = NOT_OPENED
```

**No queda ningún requisito previo pendiente.** Lo único que falta para correr Puerta 1 es la
decisión de abrir outcomes, que es de Nico.

---

## Aporte al referente

La última precondición de Puerta 1 queda cerrada con margen, y con el riesgo que se temía
—bins flacos cerca del cierre— medido y descartado: sólo el 0,4 % de los ticks pierde
elegibilidad por horizonte cruzado. El peor estrato de 3.173 tiene 29 anclas para un evento.

## Nota de método

Dos correcciones a cosas que este mismo asistente dijo hoy:

1. **El kernel no es lento.** Reporté «~6k ticks/s, 47 min» en B-9. Falso: el kernel corre a
   **~60k ticks/s** — esta corrida procesó los mismos 15,9 M ticks en **4 minutos**. Los 47
   minutos eran mi propio bucle parseando 500.000 strings de evento con `dict(...split...)`. El
   cuello era el análisis, no el motor.
2. **El `cap_driver` no es 50/50.** Va de 36,6 % a 55,7 % según el contrato.

Y otra vez el patrón: ninguna de las dos apareció razonando. La primera apareció al **medir el
mismo trabajo por otro camino**; la segunda, al **ampliar la muestra**. Van siete en el día.
