# Landscape target-free — resultado **PARCIAL** 13/51, GC 02-26

- **Fecha:** 2026-08-24 · **Rama:** `fix/sweep-finalize-contract-scope`
- **Corrida:** `bt2a_sweep_20260824_7953443_gc0226`, HEAD `7953443`, worktree limpio
- **Estado:** **13 de 51 configs · un solo contrato · EN CURSO**
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · `promotion_eligible=false` · **nada declara edge**

> **Esto NO elige ganador y no puede.** Es target-free: mide población, geometría y
> sensibilidad por eje. Más zonas **no** es mejor.

---

## 1. `TapeWindowTicks` — la curva completa

```
TW      cubetas      zonas   zonas/1000cub
  5   1.313.893         12       0,01
 10     656.958        497       0,76
 15     437.978      2.156       4,92
 25     262.794      3.878      14,76   <- headline
 50     131.406      2.740      20,85
100      65.711        944      14,37
```

### 1.1 Esto **resuelve una duda que yo mismo había dejado abierta**

Cuando reporté el colapso hacia abajo (`TW<25`), escribí:

> *«El lado de arriba está sin medir. Si las zonas siguen subiendo, la lectura cambia:
> pasaría de "25 es un piso" a "25 es un punto arbitrario en una rampa".»*

**Medido: no siguen subiendo.** El conteo absoluto **tiene máximo en 25** y cae a 2.740 en
50 y a 944 en 100.

**Lo que esto sí hace:** elimina la objeción específica de «punto arbitrario en una rampa».
**Lo que NO hace:** justificar `TW=25`. Un máximo de población podría ser igualmente el
punto de máximo ruido. Target-free no distingue las dos cosas.

### 1.2 La densidad y el conteo no coinciden

La densidad por cubeta **sigue subiendo hasta TW=50** (20,85/1000), pero hay la mitad de
cubetas. El máximo de conteo absoluto y el de densidad **están en valores distintos del
parámetro**. Cualquier afirmación futura sobre «TW óptimo» tiene que decir óptimo *de qué*.

---

## 2. Dos parámetros que no mueven nada — y uno merece sospecha

| eje | valor | zonas | `a_pass` |
|---|---|---:|---:|
| **`MinHistoryBuckets`** | 200 *(headline)* | **3.878** | **27.450** |
| | 50 | **3.878** | **27.450** |
| `AbsorptionLookback` | 200 | 3.914 | 27.842 |
| | 500 *(headline)* | 3.878 | 27.450 |
| | 1000 | 3.828 | 27.314 |

**`AbsorptionLookback`**: ±1,1 % de rango sobre un cambio de **5×** en el parámetro.
Sensibilidad muy baja. Candidato a no-op.

**`MinHistoryBuckets`**: salida **idéntica en los dos números**, bajando el burn-in de 200
a 50.

**`MinHistoryBuckets`**: salida **idéntica en los dos números**. La sospecha inmediata
—que el parámetro no llegara al kernel— **se verificó y es falsa**:

```python
min_history = max(1, int(p["MinHistoryBuckets"]))
...
elif len(abs_ring) >= min_history:
```

Está cableado. La explicación es otra y es estructural:

```
cinta GC 02-26 arranca            2025-11-05
primera sesion REPORTABLE          2025-11-26
warm-up antes de la ventana        21 dias  ~90.000 cubetas
```

`min_history` se compara contra `len(abs_ring)`. Para cuando empieza la ventana
reportable, el anillo lleva **decenas de miles** de entradas: `50` y `200` son
indistinguibles porque los dos quedaron atrás hace 90.000 cubetas.

> **Es no-op real, pero no del parámetro: del diseño de la medición.** Con una ventana
> reportable que arranca 21 días después del inicio de la cinta, **ningún valor de
> `MinHistoryBuckets` por debajo de ~90.000 puede tener efecto**. El eje está en la
> grilla pero es inobservable en este setup.
>
> Consecuencia concreta: el `assert` fail-closed del harness que exige
> `min_history == 200` está protegiendo un valor que, en esta configuración, **no
> cambia ningún resultado**. No está mal, pero es ceremonia, no control.

---

## 3. `AbsorptionPct` se comporta como el dial que es

```
80  ->  6.599 zonas   54.097 a_pass
85  ->  5.275         40.794
90  ->  3.878         27.450     <- headline
95  ->  2.078         13.989
```

Monótono, cada 5 puntos ≈ **×0,7** las zonas. Es un umbral percentil: no cambia el objeto
detectado, cambia cuánto de él pasa. Es el eje más predecible de los medidos.

---

## 4. `ScoreMode` — los dos modos no son variantes cosméticas

```
AbsMagnitude     3.878 zonas   27.450 a_pass
AbsDirectional   6.274 zonas   28.325 a_pass
```

**62 % más zonas con prácticamente el mismo `a_pass`.** El umbral pasa casi igual de
seguido; de esos pases salen muchas más zonas.

### 4.1 Consecuencia para el incidente de exposición

`INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24` registra que la exposición previa a outcomes se
midió sobre el export **AbsDirectional**. Si ese modo produce **62 % más zonas** que el
headline, el conjunto de eventos contaminado es **sustancialmente mayor** que el del
headline en la misma ventana.

No cambia la matriz de exposición —las 11 sesiones de Puerta 1 y la sellada `20260608`
siguen siendo las mismas— pero sí cambia **cuántos eventos** dentro de esas sesiones
estuvieron expuestos. **No cuantificado.**

---

## 5. Lo que NO se puede leer de acá

- **Ningún ganador.** No se miraron outcomes y no se pueden mirar.
- **Nada sobre otros contratos.** Es GC 02-26, 48 sesiones. Los otros tres del universo no
  se midieron.
- **Nada definitivo sobre no-op.** Faltan 38 configs, incluidas todas las interacciones.
- **Ninguna justificación de los valores del headline.** Que `TW=25` esté en un máximo de
  población no dice que sea el correcto para nada.

## 6. Estado

```
status esperado al cerrar  COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS
promotion_eligible         false   (subconjunto de contratos)
configs                    13/51
contratos                  1/4
CAMPAIGN_OUTCOMES_OPENED   false
```

---

## Aporte al referente

La pregunta que motivó el barrido —si `TW=25` era un valor congelado sin justificar—
tiene ahora media respuesta medida: no está en una rampa, está en un máximo de población.
Eso retira una objeción concreta sin conceder que el valor esté justificado, que es la
distinción que se pierde cuando un censo se resume como «la configuración funciona».

## Nota de método

El resultado más útil de las 13 configs no es una curva sino una **sospecha**:
`MinHistoryBuckets` devolvió salida idéntica al headline en los dos números, y la
tentación es anotarlo como no-op y seguir. Pero «no-op» y «parámetro que no llega al
kernel» producen exactamente el mismo dato, y el censo no los distingue. Lo barato ahora
es dejar la duda escrita; lo caro es descubrir en tres semanas que un eje del barrido
nunca se movió.
