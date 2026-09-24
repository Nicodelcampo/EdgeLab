# Protocolo de réplica V-RND en ES, GC y 6E (pre-registrado, 2026-09-24)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**OK de Nico:** "OK para replicar V-RND en ES, GC y 6E" (chat, 24/09).
**Familia:** ABS-CTX (`FAMILIA_ABS_CTX_NQ_20260924.md`), variante **V-RND**: absorción en un número redondo → el nivel se rompe.
**Estado:** CONGELADO antes de mirar cualquier respuesta de precio de ES, GC o 6E alrededor de absorciones. Este archivo se commitea **antes** de correr `tools/vrnd_replicate.py`.

## Hipótesis (fijada en NQ; se prueba tal cual)

Cerca de un número redondo, la absorción predice un movimiento **en contra** de la dirección que implica (el nivel absorbido cede). Lejos de un número redondo, no predice nada.

- **Estimando:** `I = [Y(abs ∧ R) − Y(ctrl ∧ R)] − [Y(abs ∧ ¬R) − Y(ctrl ∧ ¬R)]`.
- **Y** = movimiento del precio medio a 60 s, en ticks, con signo en la dirección implícita (bid absorbido = arriba).
- **Signo esperado:** I < 0.

**Justificación económica (Osler 2003, 2005):** las órdenes límite se agrupan **en** los números redondos y los stops **justo detrás**. La absorción consume esa pared; cuando cede, los stops aceleran la ruptura.

**Cómo podría refutarse:**
- I ≥ 0 con un MDE chico en los instrumentos independientes;
- o un efecto que depende de un solo instrumento.

## Definición de "número redondo" por instrumento

Se transporta la regla, no el número. En NQ, el redondo era un múltiplo de 100 pts, que equivale al **0,334 % del precio**. Para cada instrumento se toma la denominación redonda estándar más cercana (en escala logarítmica) al 0,334 % de su precio de julio. La ventana es el **2 % del espaciado** (en NQ, 8 de 400 ticks).

| Instrumento | Precio jul-2026 | 0,334 % | Denominaciones candidatas | **Redondo** | Ventana | Efecto de NQ escalado en % |
|---|---:|---:|---|---|---:|---:|
| NQ (origen) | 29.959 | 100 | 50, 100, 250, 500 | 100 pts = 400 t | 8 t | −10,5 t |
| ES | 7.582 | 25,3 | 10, 25, 50, 100 | **25 pts = 100 t** | **2 t** | −2,7 t |
| GC | 4.159 | 13,9 | 5, 10, 25, 50 | **10 USD = 100 t** | **2 t** | −3,6 t |
| 6E | 1,1465 | 0,00383 | 0,0025, 0,005, 0,01 | **0,0050 = 100 t** | **2 t** | −2,0 t |

**Sensibilidad** (se reporta y no decide): la denominación siguiente hacia arriba (ES 50, GC 25, 6E 0,0100) con la misma ventana.

## Datos y particiones (enmienda L2: jul–oct es desarrollo)

**Sesiones:** del 01/07/2026 al 21/08/2026, la misma ventana que `P-NQL2-EXP`.

| Instrumento | Contrato | Partición nueva en el ledger | Notas |
|---|---|---|---|
| ES | ES 09-26 | `P-VRND-ES` | Ids `ES-L2:<fecha>`. Distinto de `P-TBZ-*`, que es 25T pre-holdout |
| GC | por día, el de más trades entre GC 08-26 y GC 12-26 (regla target-free) | `P-VRND-GC` | Ids `GC-L2:<fecha>` |
| 6E | 6E 09-26 | `P-VRND-6E` | Ids `VRND-6E:<fecha>` (ver nota) |

**Nota 6E.** Esas fechas ya estaban declaradas en `P-6E-REG-L2HOLDOUT` (FUTURE), autorizadas por Nico sólo para validar proxies target-free de 6E-REGIMES.
- La enmienda L2 firmada el 24/09 las pasa a desarrollo, y Nico autorizó esta réplica.
- Se usa otro espacio de nombres **a propósito y a la vista**: el solapamiento con `P-6E-REG-L2HOLDOUT` queda escrito acá y en la descripción de la partición.
- La consecuencia es que **esas sesiones ya no sirven como confirmación ciega de ninguna hipótesis de 6E-REGIMES que use precio posterior**.

**Exclusiones (target-free, fijas):**
- menos de 5.000 trades o 5.000 cotizaciones;
- reloj no certificado (P-84, pausa diaria con trades);
- sesiones que aparecen en una frontera `FAIL_*` del chequeo de continuidad de su contrato (ES: 11/08 y 12/08).

## Medición (idéntica a la corrida C de NQ)

- **Detector:** `AbsorptionTracker` causal, latencia 250 ms.
- **Controles:** 5 por evento, en (t0 + 960 s, t0 + 2.700 s]; mismo tercil de volumen de 60 s, misma distancia al tope del libro, a 60 s o más de cualquier absorción. Es la lección `LES-CTRL-TIMING-20260924`.
- **Horizonte máximo del filtro:** 900 s, igual que en NQ.
- **Bootstrap por sesión:** 2.000 réplicas, semilla 20260924.

**Salidas por instrumento:**
- I, IC 95 % y MDE (= 2,8 × desvío bootstrap);
- los dos componentes: R solo y absorción sola;
- n de eventos en R y sesiones con eventos en R;
- spread p50 de los eventos en R.

**Secundarios, sólo descriptivos:** 30 y 300 s, y la sensibilidad de denominación.

## Criterios (fijados ahora)

Veredicto por instrumento:

| Veredicto | Condición |
|---|---|
| **REPLICA** | límite superior del IC de I (60 s) < 0 |
| **REPLICA_ECONOMICA** | REPLICA y además \|I\| ≥ spread p50 de los eventos en R |
| **NO_REPLICA** | el IC cruza 0 y el MDE ≤ \|efecto de NQ escalado\| |
| **SIN_POTENCIA** | el IC cruza 0 y el MDE > \|efecto de NQ escalado\|, o hay menos de 30 eventos en R |
| **CONTRADICE** | límite inferior del IC > 0 |

**Decisión de familia:**
- **V-RND pasa a la confirmación en `P-NQL2-CONF`** si **GC o 6E** (independientes de NQ) dan REPLICA y ninguno de los tres da CONTRADICE.
- ES sólo suma como apoyo: está correlacionado con NQ.
- Si los tres dan NO_REPLICA o alguno CONTRADICE, V-RND queda **muerta en su alcance declarado** (absorción × redondo, 60 s, estos cuatro instrumentos).
- Si predomina SIN_POTENCIA, se espera más L2.

**Número de pruebas:** 3, una celda por instrumento. No se mira ninguna otra celda de estos instrumentos en esta corrida.

## Aporte al cerebro (reutilizable)

`tools/vrnd_replicate.py` recibe el instrumento, la base de datos, el tick, el redondo y la ventana. Se puede volver a correr sin chat cuando llegue L2 nuevo (octubre, contratos 12-26), con el mismo protocolo y sin decisiones nuevas.
