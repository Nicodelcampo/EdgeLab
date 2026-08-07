# Entrega — curva de diseño sobre el universo completo

**Fecha:** 2026-08-07 · **Para:** auditor · **De:** Claude (turno de Nico)
**Artefacto:** `diag/tasa_senales/curva_excursion_ticks.json`
**sha256:** `76e1c8767553ff7f74a80dec33c5adfc38293e76effe640c6a6ab8f18af07e66`
**Commit:** `dfff4fd` · **NORTH_STAR:** `21bb3b01a33e2b37…`

> **NO ES UNA CURVA ADJUDICADA.** El artefacto lleva `autoritativo: true` porque
> así se llamaba el campo cuando corrió; sólo significa «universo no recortado
> con `--limite-sesiones`». El nombre ya se corrigió a `universo_completo` +
> `estado_de_adjudicacion: "no_adjudicada"` (`64b6a4e`). Adjudicar es un acto de
> una persona y este script no lo puede escribir.

## 0. Lo que hay que leer si se lee una sola cosa

Dos hallazgos, y **el segundo contradice lo que yo esperaba**:

1. **No hay un `T` único** que ponga a los cinco indicadores en el mismo régimen
   de frecuencia. Cada uno alcanza la banda `f ≈ 7-12` en un umbral distinto —o
   no la alcanza nunca—.
2. **Los umbrales bajos de la grilla están contaminados, y peor en los
   indicadores que yo leía como limpios.** A `T=1`, el **58 %** de las zonas de
   `BigTrap2` **ya están fuera de la banda en el primer tick de su ventana**: su
   «ruptura» no la produjo el precio, la produjo la zona, que nació detrás de
   donde el precio ya estaba.

El (2) cae rápido con `T` y es ~0 desde `T=8`. Los dos juntos apuntan al mismo
lado de la grilla, lo cual es una suerte que conviene no confundir con un
diseño: la banda de frecuencia útil cae justo donde la contaminación se apaga.

## 1. Condiciones de la corrida

```
201 sesiones · 4 contratos · 5 indicadores · workers=4 (autorizado a priori)
~84.000 s de CPU · outcomes_accessed = false
firewall_corte_iso  2026-06-30 22:00:00+00:00
```

El corte es el **inicio de la sesión CT siguiente** a `MAX_FECHA`, no un corte
civil UTC. La v1 cortaba en `23:59:59 UTC` = 18:59 CT y dejaba entrar **2 horas
de la primera sesión sellada**; los pilotos corrían sobre diciembre 2025 y nunca
la dispararon, la corrida completa sí la habría disparado.

`universe_filter_report` declara 24 fechas descartadas por holdout.

## 2. Señales/sesión — arquetipo `retorno`

| indicador | T=1 | T=2 | T=3 | T=5 | T=8 | T=13 | T=21 | T=34 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HFTZones2 | 369,6 | 272,7 | 213,5 | 146,6 | 99,1 | 62,2 | 36,9 | 20,3 |
| Gaps2 | 260,6 | 161,2 | 127,5 | 89,3 | 60,9 | 38,6 | 23,6 | 13,1 |
| BigTrap2 | 72,4 | 64,2 | 56,6 | 44,8 | 33,4 | 22,8 | 14,6 | **8,3** |
| aVolCellPOI2 | 40,8 | 36,1 | 31,7 | 24,8 | 18,6 | 12,6 | **8,1** | 4,7 |
| VolTicksPOC2 | **6,8** | 6,1 | 5,4 | 4,4 | 3,4 | 2,4 | 1,5 | 0,9 |

Los dos arquetipos de ruptura están en el artefacto; su forma es la misma con
niveles ~10-20 % más bajos, y `ruptura_arriba` y `ruptura_abajo` son casi
simétricas en todos los indicadores (máxima asimetría: `HFTZones2` a T=1,
417,6 vs 419,1 — **0,4 %**). Esa simetría es un control que pasa: un sesgo
direccional acá habría sido señal de un defecto de construcción, no de mercado.

### 2.1 Consecuencia: un umbral **por indicador**, no un umbral

- `aVolCellPOI2` → **T≈21**
- `BigTrap2` → **T≈34**
- `VolTicksPOC2` → **nunca**: arranca en 6,8 a `T=1` y sólo baja
- `Gaps2`, `HFTZones2` → siguen en 13-20 **incluso a `T=34`**

Eso reemplaza «elegir un umbral» por «elegir un umbral por indicador», que es
una decisión distinta y **con otro costo de multiplicidad**. No la tomo yo.

## 3. El segundo hallazgo — eventos vacuos en los umbrales bajos

`diag/tasa_senales/sonda_alejamiento_cero.py` · salida
`sonda_alejamiento_cero.json`

### 3.1 De dónde salió

Los cuantiles del alejamiento acumulado antes de la primera reentrada daban,
para `Gaps2`, **p25 = p50 = p75 = 0,0**: en tres de cada cuatro zonas el precio
**no se alejó ni un tick** antes de «reentrar». Estable en los cuatro contratos.

Una reentrada sin salida previa no es una reentrada. La hipótesis obvia era que
la zona **ya contiene al precio** cuando queda disponible — para un kernel
`tick_create` la zona nace en `created_ms + 1 ms`, prácticamente en el instante
de creación, y un gap se construye alrededor del precio de ese momento.

**Esa hipótesis es la que yo esperaba, y por eso había que medirla en vez de
adoptarla.** Medida:

| indicador | clase | zonas | precio **dentro** al quedar disponible |
|---|---|---:|---:|
| Gaps2 | tick_create | 4.415 | **75,0 %** |
| HFTZones2 | tick_create | 4.360 | **67,1 %** |
| aVolCellPOI2 | bar_close | 55 | 23,6 % |
| VolTicksPOC2 | bar_close | 71 | 18,3 % |
| BigTrap2 | bar_close | 710 | 14,4 % |

La correspondencia con los cuantiles publicados es **exacta en los cinco**:
Gaps2 75,0 % ↔ `p75 = 0,0`; HFTZones2 67,1 % ↔ `p50 = 0,0` y `p75 = 1,0`;
aVolCellPOI2 23,6 % ↔ `p25 = 0,0` y `p50 = 1,5`; BigTrap2 14,4 % y
VolTicksPOC2 18,3 % ↔ `p25 > 0` en los dos. No es coincidencia: es el mecanismo.

### 3.2 Y al verificarlo apareció el problema de verdad, que va al revés

`eventos_de_zona` calcula la primera cruza sobre una acumulada que **arranca en
`i0`**. Si el precio ya está a `T` ticks o más del borde en el primer tick de la
ventana, entonces `rup_up[T] = 0`: una ruptura que no rompió nada. Y como
`retorno[T]` exige `j > k_T` con `k_T = min(rup_up, rup_dn)`, a partir de ahí
**cualquier vuelta a la banda cuenta como retorno sin que haya habido
excursión**.

Fracción de zonas ya a `T` ticks o más del borde en el primer tick de su ventana:

| indicador | clase | T=1 | T=2 | T=3 | T=5 | T=8 | T=13 | T=21 | T=34 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BigTrap2 | bar_close | **58,2 %** | 31,8 % | 17,2 % | 7,0 % | 2,7 % | 0,9 % | 0,3 % | 0,1 % |
| VolTicksPOC2 | bar_close | **53,5 %** | 33,8 % | 23,9 % | 16,9 % | 9,9 % | 4,2 % | 2,8 % | 2,8 % |
| aVolCellPOI2 | bar_close | **40,0 %** | 27,3 % | 16,4 % | 10,9 % | 5,5 % | 1,8 % | 0,0 % | 0,0 % |
| HFTZones2 | tick_create | 24,3 % | 3,1 % | 1,0 % | 0,3 % | 0,1 % | 0,1 % | 0,0 % | 0,0 % |
| Gaps2 | tick_create | 18,8 % | 3,4 % | 1,5 % | 0,5 % | 0,2 % | 0,1 % | 0,1 % | 0,0 % |

**Va exactamente al revés de lo que sugería 3.1.** Los `bar_close` —los que yo
leía como «los de excursión real», porque su `p50` era 3,5— son los que tienen
los umbrales bajos más contaminados. Su zona nace al **cierre de la barra
creadora**, o sea que el precio tuvo una barra entera para irse antes de que la
zona existiera. Los `tick_create` nacen pegados al precio y por eso arrancan
casi siempre adentro.

Las dos mediciones no se contradicen: **son la misma causa vista desde los dos
lados**. El reloj de disponibilidad decide dónde está el precio cuando empieza
la ventana, y eso contamina un arquetipo u otro según la clase.

### 3.3 Qué se puede decir con esto, y qué no

**Se puede decir:**

- `T=1` y `T=2` **no son utilizables** para los tres `bar_close` sin una
  corrección explícita: a `T=1` más de la mitad de los eventos de `BigTrap2` son
  vacuos.
- Desde `T=8` la contaminación es ≤ 9,9 % en todos, y ≤ 0,2 % en los
  `tick_create`.
- La decisión previa de **excluir el `0` de la grilla** —tomada por principio,
  «alejarse 0 ticks no es un alejamiento»— ahora tiene un número: sin ella,
  el 75 % de los «retornos» de `Gaps2` serían no-eventos.
- Los umbrales donde cada indicador alcanza la banda de frecuencia (`T≈21` y
  `T≈34`) tienen contaminación de **0,3 % y 0,1 %**.

**No se puede decir:**

- Que `VolTicksPOC2` y `aVolCellPOI2` decaigan como muestra la tabla. En esa
  corrida tienen **71 y 55 zonas**: la cola es ruido. `VolTicksPOC2` aparece
  plateando en 2,8 % entre `T=21` y `T=34` — con 71 zonas eso son **2 zonas**, y
  no distingo un plateau real de dos casos sueltos. Hay una corrida sobre 40
  sesiones para eso; hasta que cierre, esas dos filas son indicativas.
- Que la curva publicada esté mal. **Está bien medida**; lo que este hallazgo
  dice es **cómo hay que leerla**, y que los dos umbrales más bajos miden otra
  cosa.
- Nada sobre rentabilidad. No se tocó un outcome.

### 3.4 La pregunta que queda, y es de contrato

Una zona que nace **detrás** del precio y después lo ve volver: ¿eso es un
retorno a la zona, o es otro evento? Hoy el extractor cuenta las dos cosas
juntas. Son distinguibles —`k_T == 0` las separa— pero **cuál de las dos es la
hipótesis de EXPLORE-001 no lo decido yo**. Es una definición, no un parámetro.

## 4. Descartes

```
  indicador          clase           zonas  sin_created_bar  sin_tramo  sin_clase
  AACloseOpenDiffs   -              144511                0          0     144511
  BigTrap2           bar_close       17180                0          0          0
  Gaps2              tick_create     92544                2        788          0
  HFTZones2          tick_create    106626                0         33          0
  VolTicksPOC2       bar_close        1628                0          0          0
  aVolCellPOI2       bar_close        9089                0          0          0
```

**Las 2 zonas de `Gaps2` en `sin_created_bar` son el guard de `created_bar < 0`
disparando sobre datos reales.** `gaps2.py:12` declara que antes del primer
cierre primario vale `-1`, y en Python `bar_end[-1]` es la **última** barra. Sin
el guard esas dos zonas no fallaban: anclaban su disponibilidad al final de la
serie, en silencio. El defecto era real y apareció.

`AACloseOpenDiffs` queda afuera por `sin_clase`, no por falta de barra — ver §6.

## 5. Cambios de código que acompañan la entrega

| commit | qué |
|---|---|
| `5cb1fbb` | el detector de la puerta única confundía **prosa con código** |
| `64b6a4e` | identidad del checkpoint por **huella del código**; `autoritativo` → `universo_completo` |
| `617ae90` | `AACloseOpenDiffs` **sí** tenía la barra creadora: se llamaba `m1_bar` |
| `dfff4fd` | el artefacto de la curva |

### `git_head()` en la clave del checkpoint estaba mal en las dos direcciones

Demasiado **grueso**: commitear un README invalidaba 24 h de cómputo.
Demasiado **fino**, que es peor: en un árbol sucio el HEAD **no se mueve**, así
que se podía editar `bigtrap2.py`, relanzar, y el checkpoint viejo pasaba como
válido — mezclando dos kernels dentro de una misma curva sin un aviso.

Ahora la clave lleva el sha256 de los **bytes** del script, de `post_sepmin` y
del módulo de cada indicador medido.

### Limitación del checkpoint, ahora escrita

`indicadores` está en la clave: **agregar un indicador invalida el checkpoint
entero**. Sirve para reanudar una corrida interrumpida, nunca para extender una
cerrada. Es correcto —mezclar dos universos de indicadores falsearía el
denominador— pero hay que saberlo antes de planificar un «le agrego uno».

## 6. `AACloseOpenDiffs` — el motivo declarado era falso

El test decía «no tiene concepto de barra creadora en su ciclo de vida». **Sí lo
tiene**: se llama `m1_bar`, y la identidad está verificada —`_m1_bars(ticks)` ==
`build_time_bars(ticks, 1)`, 6.703 barras, `end_ns` idéntico—. Faltaba el
**nombre canónico**, y sin él el reloj de disponibilidad mandaba las 144.511
zonas al descarte. Un campo con otro nombre se leía como una capacidad ausente.

**Esto no lo mete en la curva.** El motivo real sigue en pie: no emite
`ZONE_TOUCHED`, y **qué cuenta como toque para un gap es una decisión de Nico
que no está tomada**. `CLASE_KERNEL` lo sigue excluyendo, y el test ahora avisa
si algún día aparece `ZONE_TOUCHED`, para que el motivo caducado se lleve a Nico
en vez de reactivarse por defecto.

## 7. Lo que esta entrega **no** habilita

- No autoriza correr nada sobre outcomes ni P&L.
- No sella E-R1 ni elige candidatos.
- No adjudica la curva: eso es del auditor.
- No resuelve el MDE de 1,14, que **sigue sin ser reproducible** desde lo
  documentado (`diag/multiplicidad/reconstruir_mde.py` da 2,41 a `f=1`, ratio
  2,11). Si el MDE real fuera 2,41, la banda «detectable y operable» a `f=1`
  estaría vacía — y eso cambia qué umbral tiene sentido pedir.

## 8. Lo que le toca a Nico

1. **Qué es un toque para `AACloseOpenDiffs`** (bloquea su entrada al estudio).
2. **§3.4**: si una zona que nace detrás del precio y lo ve volver cuenta como
   retorno, o es otro evento.
3. **D2** — versionar los oráculos: el manifiesto ya está construido
   (`docs/oraculos_manifiesto.json`), la política es su decisión.

## Aporte al referente

La curva de diseño sobre el universo completo existe, es outcome-free y
reproducible por hash. Reduce distancia hacia un edge neto de dos maneras: da la
frecuencia real por indicador y umbral —insumo directo del MDE y de la grilla
confirmatoria— y **descarta los dos umbrales más bajos como base de hipótesis**,
que sin esta medición habrían entrado al pre-registro con más de la mitad de sus
eventos vacuos.
