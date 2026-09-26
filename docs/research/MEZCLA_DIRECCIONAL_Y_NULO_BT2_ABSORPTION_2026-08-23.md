# Mezcla direccional del headline y recalibración del umbral de Puerta 1

- **Fecha:** 2026-08-23 · **Autoriza:** Nico
- **Rama:** `foundation/f0b-compatibility-probe` · **Base:** `61af99b` (`FINAL_PUERTA0_SIGNED`)
- **Firewall:** outcomes `false` · junio **no abierto** · MFE/MAE/retornos/P&L **no abiertos**
- **Insumo:** `bt2_absorption__AbsMagnitude__TW25.csv` (`c521ef99…`, 18.804.897 bytes)
- **Responde a:** pedido #1 del auditor (contar la mezcla direccional de los 377 eventos)

> Esto **no abre outcomes**. Cuenta el `dir` de los eventos ya exportados, que es un
> campo del propio log. Es censo target-free.

---

## 1. Primero: el auditor recibió el archivo equivocado

Su sospecha era correcta y cierra byte a byte.

| archivo | bytes | `score_mode` |
|---|---:|---|
| `bt2_absorption__TW25_2.csv` | **18.744.439** | `AbsDirectional` |
| `bt2_absorption__AbsMagnitude__TW25.csv` | **18.804.897** | `AbsMagnitude` |

Los 18.744.439 bytes que reportó son **exactamente** el direccional. El headline es el
otro. Todo lo que sigue está medido sobre el correcto.

---

## 2. La mezcla direccional del headline

**377 eventos · 206 `dir=long` / 171 `dir=short` · 54,6 % / 45,4 %.**

(`dir=long` ⇔ `side=trapped_sellers`; `dir=short` ⇔ `side=trapped_buyers`. La
correspondencia es 1:1 en los 377.)

### 2.1 Por sesión, contra el nulo medido por el auditor

| `td` | n | `%long` | nulo sólo-largo | drift (tk) |
|---|---:|---:|---:|---:|
| 2026-08-17 | 41 | 51,2 % | 1,1000 | +229 |
| 2026-08-18 | 55 | 56,4 % | 0,8000 | −839 |
| 2026-08-19 | 117 | 53,0 % | **1,6071** | +1893 |
| 2026-08-20 | 77 | 54,5 % | 1,0533 | −49 |
| 2026-08-21 | 87 | 57,5 % | 1,2857 | +846 |

```
media 54,5 %   sd 2,5 pp   rango 51,2 - 57,5
corr(%long, drift)             = -0,26   (n=5, no concluyente)
corr(%long, nulo solo-largo)   = -0,26   (n=5, no concluyente)
```

### 2.2 Lectura

**Absolución parcial, y conviene decirla con precisión.**

La mezcla está **sesgada pero es estable, y no persigue la tendencia**. La versión más
grave de la trampa —que el decil alto de `a_score` sea un detector de régimen con
nombre de indicador, que es P-39 aplicado al portador— **no es lo que ocurre acá**. En
la sesión con el drift más grande de las cinco (08-19, +1893 tk) el indicador fue el
**menos** largo de los cuatro días sesgados.

**Lo que no salva:** 54,6 no es 50. Con la escala del propio auditor (un 60/40 regala
0,04–0,08 de ratio), un 54,6/45,4 regala del orden de **0,02–0,04** — entre el **8 % y
el 16 %** de toda la distancia de 1,00 a 1,25.

**El umbral hay que recalibrarlo contra el nulo medido a esa mezcla, no interpolando.**
La propia tabla del auditor muestra que promediar ratios da mal: el 08-19,
`(0,6222 + 1,6071)/2 = 1,11` contra un 50/50 medido de `0,9993`. Ratio de medianas ≠
mediana de ratios.

---

## 3. Consecuencias para el protocolo

### 3.1 B-1 — el umbral de 1,25 no es interpretable solo

Confirmado y agravado por la medición del auditor: el nulo balanceado es **1,0034**
(sd 0,0070 entre sesiones, una roca), pero el nulo **sólo-largo** es **1,2121** con
**sd 0,30**, y llega a **1,6071** en una sesión — por encima del umbral, sin señal.

⇒ **El brazo `N_RAND` deja de ser control de Puerta 2 y pasa a ser precondición de
Puerta 1.** El control no va después del gate: va **dentro**, o el gate no mide el
indicador. Es la misma exigencia que F2.9 impuso a la línea del imán (`K0` vs `N0`),
aplicada a la variable de contexto que allí no se había controlado: la dirección.

### 3.2 B-8 — 5 sesiones no tienen potencia, y eso corta en dos direcciones

Potencia medida por el auditor, con pareo intra-sesión (`sd` por sesión ≈ 0,282):

| efecto a detectar | sesiones necesarias |
|---|---:|
| tamaño 1,25 (`+0,247` sobre el nulo) | **~5** |
| tamaño BigTrap2 (`1,056 − 1,0034 = +0,053`) | **~113** |

> **Una Puerta 1 corrida sobre 5 sesiones es no interpretable en las dos direcciones.**
> Si da `PASS`, lo más probable es deriva direccional o ruido. Si da `FAIL`, no se
> aprendió nada, porque nunca hubo potencia para detectar un efecto del tamaño que esta
> familia produce.

**Corrección explícita a lo que este mismo asistente recomendó antes en la sesión:**
se había sugerido *«dejá que Puerta 1 dé plano y recién ahí declarás el contexto»*. Eso
presuponía que un nulo de Puerta 1 sería informativo. **Con estos números no lo es.**
La hipótesis de «nulo global, real en el contexto correcto» hoy **no se puede rechazar
ni aceptar** — no porque sea infalsable, sino porque el instrumento no tiene
resolución. Es argumento para conseguir las sesiones, no para condicionar sobre cinco.

### 3.3 El horizonte son dos horizontes

Medido por el auditor: liga el reloj de 900 s el **47,7 %** de las veces y el tope de
2000 ticks el **52,3 %**; la tasa de ticks varía de 1,25 a 2,32 tk/s entre sesiones
(86 % de dispersión). ⇒ cuál de los dos manda es, de hecho, otra variable de contexto
no declarada, y cambia por sesión.

---

## 4. Deuda real de Puerta 0 que queda abierta

`FINAL_PUERTA0_SIGNED` se firmó sobre **GC 12-26, 17–21 ago 2026**. Si el censo corre
sobre **junio con front-month continuo**, ese contrato **no tiene paridad medida**.

⇒ Hace falta un **oráculo de 2 sesiones de junio** en el contrato nuevo, para
spot-check. Es la única cosa que sigue necesitando NinjaTrader. Sin eso, la firma no
cubre lo que se va a correr.

Sobre el roll: la corrección del auditor —de «contrato único sin roll» a **front-month
continuo con cada sesión etiquetada por contrato**— es correcta, y su argumento de
seguridad también: **ningún camino cruza sesión**, así que el roll no puede contaminar
un evento. Es la misma solución que F2.9 usó para sus 201 sesiones.

---

## 5. Lo que NO hace falta exportar, y por qué

| pedido | veredicto | razón |
|---|---|---|
| export NT8 para escalar sesiones | **no hace falta** | Puerta 0 firmada compra el derecho a correr sólo el kernel Python. Para ≥30 sesiones alcanza tick data cruda. |
| L2 / profundidad | **no sirve** | `build_footprints` clasifica agresor con `bid_ticks`/`ask_ticks` — campos 3 y 4 del `.Last.txt`. El kernel **nunca toca profundidad**. Verificado en el `.cs` al firmar Puerta 0. |
| parquets | **no** | mismo motivo, y el sandbox del auditor no tiene `pyarrow`. |

---

## 6. Estado

```
PUERTA_0            = FINAL_PUERTA0_SIGNED  (GC 12-26, agosto)
PUERTA_0_JUNIO      = NO_MEDIDA  -> requiere oraculo de 2 sesiones
MEZCLA_DIRECCIONAL  = MEDIDA  ->  54,6 / 45,4  (sd 2,5 pp, no sigue el drift)
NULO_EMPIRICO       = 1,0034 balanceado (sd 0,0070) / 1,2121 solo-largo (sd 0,30)
B-1                 = RESUELTO y AGRAVADO -> N_RAND es precondicion de Puerta 1
B-8                 = CUANTIFICADO -> ~113 sesiones para un efecto tamano BigTrap2
UMBRAL_1,25         = A RECALIBRAR contra el nulo a mezcla 54,6/45,4, medido
CENSO_JUNIO         = NOT_RUN
OUTCOMES_JUNIO      = NOT_OPENED
```

---

## Aporte al referente

El pedido #1 del auditor se cierra sin exportar nada: el `dir` ya estaba impreso en el
log firmado. Y el resultado discrimina entre las dos versiones de la hipótesis de
contexto. La fea —el indicador como detector de régimen disfrazado— queda descartada
por la estabilidad del mix entre sesiones. La cara cara sigue viva pero **no medible
con cinco sesiones**, y ahora se sabe exactamente cuántas hacen falta: ~113.

## Nota de método

El sesgo direccional estaba impreso en cada `ZONE_CREATED` desde el primer export y
nadie lo contó. Hicieron falta cinco rondas de auditoría de Puerta 0 y un nulo medido
por fuera para que alguien preguntara cuántos long y cuántos short había. **El campo no
faltaba: faltaba la pregunta.** Es el mismo patrón que el `a_score` del fill `11537_B`
—el dato desambiguador impreso y descartado— dos veces en dos días.
