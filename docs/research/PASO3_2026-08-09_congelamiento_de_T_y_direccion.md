# Paso 3 — `T` congelado, dirección verificada, y un bloqueante para sellar

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado · Sin NT8
**Autoriza:** Nico — *«avanzá con el paso 3 y redactá E-R1»*.
**Artefacto nuevo:** `diag/tasa_senales/concordancia_lado_bigtrap2.json`

---

## 1. `T = 34` para H1, y la trampa que había que esquivar

§7 Paso 3 pre-registra `H1 BigTrap2 ≈ T=34` y ordena: **«No se selecciona un
argmax»**.

La tabla corregida invita justamente a eso. Retornos válidos por sesión:

| `T` | 1 | 2 | 3 | 5 | 8 | 13 | 21 | **34** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `BigTrap2` | 23,20 | 33,77 | **38,57** | 37,61 | 31,09 | 22,09 | 14,35 | **8,23** |

El pico está en `T=3` con 38,57 — **4,7 veces** el valor de `T=34`. Elegirlo sería
exactamente el argmax prohibido.

**`T = 34` se mantiene**, tal como estaba pre-registrado.

### 1.1 La regla de banda contigua no se puede evaluar completa, y se declara

El propio módulo lo advertía antes de correr: `T=34` es el **último punto** de
`T_DESIGN`, así que **no tiene vecino superior**. §7 Paso 3 exige *«estabilidad
entre puntos adyacentes»* y en ese borde sólo hay un lado.

Vecino inferior: `T=21` → 14,35. Contra `T=34` → 8,23. Es un descenso monótono y
suave, sin discontinuidad. **Se acepta el borde declarándolo**, que es una de las
dos salidas que el módulo dejaba abiertas. La otra —extender la grilla— ampliaría
el espacio después de haber visto la curva.

## 2. La dirección de `BigTrap2`, verificada en el kernel

`bigtrap2.py:266` y `:274` lo dicen en sus propios comentarios:

```
Trapped buyers:  agresion compradora que quedo por ENCIMA del close
Trapped sellers: agresion vendedora que quedo por DEBAJO del close
```

- **`trapped_buyers`** — compraron caro, la barra cerró debajo. Largos bajo el
  agua. La zona queda **arriba** del precio: **resistencia**. Señal **bajista**.
- **`trapped_sellers`** — vendieron barato, la barra cerró arriba. Cortos bajo el
  agua. La zona queda **abajo**: **soporte**. Señal **alcista**.

> ### Trampa de nomenclatura, a declarar explícitamente en E-R1
> `is_bull = True` → `trapped_buyers` → zona **arriba** → operación **bajista**.
> **El flag nombra quién quedó atrapado, no la dirección de la operación.**
> Quien lo lea rápido invierte la hipótesis entera.

Los dos lados están **balanceados**: 8.741 `trapped_buyers` contra 8.451
`trapped_sellers` sobre 17.192 zonas (50,8 % / 49,2 %). No hay sesgo direccional
encubierto.

## 3. Lo que medí, y por qué mató la traducción que iba a adoptar

`recuento_kT.py` mide el evento **agnóstico de dirección**: `k = min(ku, kd)`, el
precio se aleja `T` ticks hacia **cualquier** lado. Verificado: ese módulo tiene
**cero** referencias a `kind`, `is_bull` o `trapped`.

Pero `BigTrap2` tiene dirección nativa. Así que la traducción concreta podía ser:

**Lectura (a).** Sólo cuenta la excursión que sale **por el lado del
atrapamiento** — el precio atraviesa la zona y la rompe donde están los
atrapados.

Parecía elegante: el atrapamiento aportaría información y no sólo geometría. La
medí antes de adoptarla.

| `T` | concordante | discordante | `f` concordante/ses |
|---|---:|---:|---:|
| 8 | 338 | 7.000 | 1,682 |
| 21 | 82 | 3.599 | 0,408 |
| **34** | **49** | **2.346** | **0,244** |

**La lectura (a) está muerta.** A `T=34` da **49 eventos en 201 sesiones**,
0,244/sesión. Ninguna potencia lo sostiene.

Y en retrospectiva es geométricamente obvio: una zona `trapped_buyers` está
**arriba** del precio. Para salir «por el lado del atrapamiento» el precio tiene
que **atravesar la zona entera** y después alejarse `T` ticks más. Alejarse hacia
abajo, en cambio, es libre. De ahí el factor **48×** entre discordantes y
concordantes.

**Lo registro porque la descarté midiendo, no razonando.** Sin la medición la
habría escrito en E-R1.

## 4. La traducción que queda en pie

**Lectura (b).** El evento operable es el **retorno a la banda**, y la dirección
la da el lado atrapado:

```
zona disponible
 → excursión de T ticks (k_T > 0), en cualquier dirección   ← el setup
 → retorno a la banda (j > k_T)                             ← LA ENTRADA
 → dirección: trapped_buyers -> corto ; trapped_sellers -> largo
```

El mecanismo es enunciable sin outcomes: el precio se aleja, después vuelve al
nivel donde quedaron los atrapados, y ahí **ellos obtienen su salida** —los largos
bajo el agua venden— lo que empuja el precio en contra del retorno.

Y encaja con lo publicado: §6.3 declara para `BigTrap2` a `T=34` una **`f` ≈ 8,3**,
y los retornos válidos medidos dan **8,23/sesión**. Coinciden.

## 5. El bloqueante: esa coincidencia revela una discrepancia de población

Que §6.3 coincida con **8,23** es informativo, y no del todo tranquilizador.

**8,23/ses sale de la población del censo: 17.192 zonas, sin `sep_min`.**
Verificado: `recuento_kT.py` no menciona `sep_min` en ninguna línea.

**La población autoritativa es otra**: primeros toques post-`sep_min`, que la
enmienda `first_touch_decongestion` declara la entrada primaria — **9,08/sesión**,
1.825 eventos en 201 sesiones, contra las 85,5 zonas/sesión del censo.

| población | eventos/ses | de dónde |
|---|---:|---|
| zonas del censo | 85,5 | `recuento_kT`, sin `sep_min` |
| **primeros toques post-`sep_min`** | **9,08** | censo autoritativo, PRED-007 |
| retornos válidos `T=34` (censo) | 8,23 | `recuento_kT` |

**Formulación precisa, después de leer la enmienda.** No es un conflicto de
definición de evento: la enmienda fija la entrada en el primer toque, y para el
94,7 % de los retornos válidos de `T=34` la zona estaba vacía en `i0`, así que
**el retorno tras la excursión ES el primer toque**. Los dos coinciden.

El problema es otro: **nadie aplicó los dos filtros juntos.**

| medición | `sep_min` | excursión `T=34` | eventos |
|---|:-:|:-:|---:|
| censo autoritativo | **sí** | no | 1.825 |
| `recuento_kT` | no | **sí** | 1.655 |
| **lo que E-R1 necesita** | **sí** | **sí** | **no medido** |

> **Trampa numérica.** 1.825 y 1.655 se parecen, y §6.3 publica ≈ 8,3 que coincide
> con 8,23. **Es coincidencia entre dos filtros distintos**, no confirmación.
> Si fueran independientes, aplicar ambos daría del orden de 176 eventos —
> **~0,87/sesión, un orden de magnitud menos**. Y el producto de marginales no es
> una medición.

**No lo resuelvo por inferencia.** Es exactamente el tipo de decisión que §5.3
manda congelar en E-R1 con el número delante, y el número correcto todavía no
está medido: haría falta un recuento de excursión+retorno **sobre la población de
primeros toques post-`sep_min`**, que es un módulo que no existe. Y si `f` resulta
ser ~0,87/ses en vez de ~8,3, **la celda muy probablemente sea ciega al MDE**, lo
que cambiaría H1 entera.

## 6. Qué decido y qué no

**Decido** congelar `T = 34` para H1, con el borde superior de la grilla
declarado (§1.1).

**Decido** la traducción direccional del §2 —verificada en fuente, con la trampa
de nomenclatura explícita— y descarto la lectura (a) **por medición**.

**No decido** `f` ni, por lo tanto, el MDE aplicable. §5 es el bloqueante para
sellar E-R1, y requiere una medición que no existe.

**No toco** outcomes, holdout ni NT8.
