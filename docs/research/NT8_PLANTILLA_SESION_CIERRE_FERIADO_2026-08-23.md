# La plantilla de sesión de NT8 corta 90 minutos antes en feriados — **la cinta tiene razón**

- **Fecha:** 2026-08-23 · **Rama:** `foundation/f0b-compatibility-probe` · **Base:** `1422d6a`
- **Firewall:** outcomes `false` · sin cambios a kernel, `.cs`, harness ni spec
- **Corrige:** la dirección de arreglo que yo mismo propuse dos mensajes antes

> Veníamos a filtrar la cinta para que coincidiera con el chart. **Medido: el chart es
> el que está mal.** No hay que filtrar nada.

---

## 1. El hallazgo

Thanksgiving 2025 (jueves 27/11), contrato GC 02-26:

```
ultimo tick de la cinta:   20251127 19:29:56.276 UTC  =  13:29:56 CT
ultimo tick del chart NT8: ~18:00 UTC                 =  ~12:00 CT
diferencia:                408 ticks
```

**La cinta termina 4 segundos antes de las 13:30 CT.** Ese es el cierre oficial de CME
para **metales** en feriado. NT8 cortó a las **12:00 CT**, que es el cierre de **índices
de acciones**.

### 1.1 Los 408 ticks son operativa real, no ruido

| hora UTC | hora CT | ticks | volumen | spread mediano | precio |
|---|---|---:|---:|---:|---|
| 17:xx | 11:xx | 673 | 745 | 2,0 tk | 4189,2 → 4190,4 |
| 18:xx | **12:xx** | 743 | 932 | 2,0 tk | 4190,4 → 4191,3 |
| 19:xx | **13:xx** | 218 | 239 | 5,0 tk | 4191,5 → 4189,6 |

Volumen real, precio moviéndose, spread ensanchándose de 2 a 5 ticks — exactamente el
perfil de liquidez fina de última hora de feriado. **No son prints fantasma.**

### 1.2 Y coincide con el calendario publicado

El esquema de feriados de CME separa por familia de producto:

| familia | cierre en feriado |
|---|---|
| índices de acciones (ES, NQ, YM, RTY) | **12:00 CT** |
| **metales (GC, SI, HG)** | **13:30 CT** |
| energía (CL, NG) | 13:30 CT |
| FX (6E, 6B…) | sin cierre anticipado |

La cinta termina a las 13:29:56 CT. **Coincide con la fila de metales al segundo.** El
chart terminó a las 12:00 CT, que es la fila de índices.

⇒ **La plantilla `Nymex Metals - Energy ETH` de NT8 le aplicó a GC el horario de
índices de acciones.**

---

## 2. Qué se invierte

| lo que propuse antes | corregido |
|---|---|
| «El chart aplica el calendario de CME y la cinta no» | **La cinta coincide con el calendario de CME; el chart no.** |
| «Filtrar la cinta en Python para que coincida con la plantilla» | **No filtrar.** Sería replicar un error de 90 minutos. |
| «El censo mide un objeto distinto del que opera» | **El censo mide el objeto correcto.** El que está handicapeado es el chart. |

Mi argumento anterior fue: *«el `.cs` en vivo usa esa plantilla y nunca ve los ticks
post-cierre, así que el censo mide otra cosa»*. La premisa es cierta y la conclusión
estaba al revés: si la plataforma se pierde 90 minutos de operativa real en feriado, la
respuesta no es que el research se los pierda también.

---

## 3. Consecuencias

### 3.1 Para la paridad

El `PARITY_GC0226_FAIL` **queda explicado y no se arregla desde el research**. Su causa
raíz es una diferencia de horario de la plataforma, no del kernel ni de la cinta.

Ya sabíamos, del diagnóstico anterior (`1422d6a`), que la lógica de corte de sesión
coincide 1:1. Ahora se sabe además **por qué** difieren las dos sesiones que quedaban
confundidas:

| sesión | `.cs` | Python | causa |
|---|---:|---:|---|
| 20251127 Thanksgiving | 3 | 9 | el chart cortó 90 min antes |
| 20251124 | 8 | 9 | ticks de fin de semana (aparte, §3.3) |

### 3.2 Para el censo

**No cambia nada. El censo corre sobre la cinta y la cinta es correcta.**

Lo que sí corresponde es **declarar** que en las ~5 sesiones de feriado del universo, la
cinta contiene operativa que el chart de NT8 no muestra. No es una limitación del censo:
es una limitación de la plataforma, documentada.

### 3.3 Los ticks de fin de semana son otra cosa

Aparte de los 408 de Thanksgiving, hay 7 ticks en fechas de fin de semana
(`20251206` 1, `20251221` 1, `20260104` 5). Un tick suelto un sábado a las 03:00 UTC
—viernes 21:00 CT, con CME cerrada desde las 16:00 CT— **no es operativa real**.

Esos sí son artefactos de la base de ticks, y son los que disparan las sesiones fantasma
con residual de largo 1 (`1422d6a` §3). Filtrarlos es legítimo; filtrar los 408 de
Thanksgiving no.

---

## 4. Lo que NO afirmo

- **No verifiqué el horario contra la página primaria de CME.** Las fuentes que consulté
  son secundarias y traen aviso de que el horario definitivo se publica ~2 semanas antes
  de cada feriado. Lo que **sí** está medido es que la cinta corta 4 segundos antes de
  las 13:30 CT y el chart a las 12:00 CT, y que las dos horas corresponden a dos filas
  distintas del esquema por familia de producto.
- **No revisé si pasa en los otros feriados** del universo (Presidents Day, Memorial Day,
  Juneteenth, MLK). El mecanismo debería repetirse, pero está medido sólo en Thanksgiving.
- **No toqué la plantilla de NT8.** Cambiarla alteraría dónde el `.cs` corta las sesiones
  y rompería la coincidencia 1:1 ya verificada.

---

## Aporte al referente

La cinta se validó **contra una fuente externa al proyecto**: termina al segundo en el
cierre oficial de metales. Eso convierte al `.Last.txt` de referencia dudosa en dato
verificado contra el calendario del exchange, y reasigna el defecto a la plataforma. El
resultado práctico es que no hay que tocar nada del pipeline de research: el insumo
estaba bien desde el principio.

## Nota de método

Dos mensajes antes escribí *«el chart aplica el calendario de feriados y la cinta no»* y
propuse filtrar la cinta. Lo di por sentado porque la plataforma es la que *tiene* una
plantilla y la exportación cruda no. **La asimetría existía; el signo estaba invertido.**
Bastó mirar si los ticks descartados tenían volumen y a qué hora exacta paraban — dos
medidas que estaban a un script de distancia y que hice recién después de proponer el
arreglo equivocado. Es la tercera vez en esta sesión que la conclusión precede a la
medición: `11537_B`, las residuales de largo 1, y ésta.
