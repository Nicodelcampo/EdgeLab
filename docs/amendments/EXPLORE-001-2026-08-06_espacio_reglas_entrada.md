# Enmienda pre-outcome — espacio de reglas de entrada (EXPLORE-001)

> **ESTADO: DRAFT v0.1 — 2026-08-06.** Escrito por el auditor a pedido de Nico.
> **NO ESTÁ SELLADO.** Nico sella, recorta o rechaza **antes** de cualquier corrida
> que mire retornos. Outcomes: **prohibidos** al redactar y al sellar.
>
> Referente: `docs/NORTH_STAR.md` sha256 `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`
> Gates: `docs/edge_validation_contract.md`
> ESPEC: `docs/ESPEC_TEST_EXPLORE-001.md` (§2-ter, §3.1–3.2)
> Decongestión ya congelada: `docs/amendments/EXPLORE-001-2026-08-04_first_touch_decongestion.md`
> Contrato de población: `docs/D3_CENSO_AUTORITATIVO_PRIMEROS_TOQUES.md`
>
> **SELLADO ≠ AUTORIZACIÓN DE CORRIDA.** Tras el sello falta: (i) OK final de
> Nico, (ii) censo autoritativo de primeros toques sobre el universo de la puerta
> única, (iii) llenar §3.3 de la ESPEC con las 3 hipótesis, (iv) manifiesto de
> campaña que cite el hash de **esta** enmienda sellada.

## Justificación económica

Sin un espacio de reglas de entrada **cerrado y declarado antes de ver
resultados**, el primer gate de EXPLORE-001 no puede empezar: cualquier umbral
elegido después de mirar la curva o el censo sería data snooping. Esta enmienda
declara el espacio **ancho y cerrado** —no elige un umbral ganador— y cobra el
presupuesto de multiplicidad por adelantado.

Buscar ancho **no** es lo que el pre-registro prohíbe. Lo prohibido es: decidir el
espacio después de ver resultados; no contar lo buscado; reportar el ganador sin
corrección. Una grilla grande es pre-registro válido si se declara antes y se
paga (`ESPEC` §2-ter ya lo hizo para resoluciones de BigTrap2).

## Cómo podría refutarse esta enmienda (antes de sellar)

- Si algún eje de la grilla no es operable con el contrato de eventos actual
  (p.ej. un indicador sin `ZONE_TOUCHED`), ese eje **no entra** al sello — se
  recorta acá, no después de ver tasas.
- Si Nico reduce la grilla, el `N_eff` baja y se reescribe **antes** del sello.
- Si se descubre que un valor de la grilla es inalcanzable por construcción
  (p.ej. T=0 en gaps donde el open es borde), se **excluye del espacio** con
  motivo escrito, no se deja y se descarta ex-post al ver resultados.

---

## 1. Qué sella y qué no

| Sella (inmutable tras OK de Nico) | No sella (sigue abierto) |
|---|---|
| Definición de **evento de entrada** | Cuáles 3 hipótesis llenan §3.3 |
| Grilla cerrada de umbrales T y arquetipos | Resultado de la curva de excursión |
| Regla de banda contigua / anti-argmax | `M_eff` numérico final (ver §6) |
| Política de toque misma-barra | Captura PRED-004 en tick |
| Herencia de decongestión 120 min | Apertura holdout / P5 económico |
| Fricción 2,768 dentro del estadístico | Manifiesto de campaña completo |

**La curva de excursión informa dónde cae `f` por celda; no bloquea el sello ni
autoriza ampliar la grilla después.**

---

## 2. Evento de entrada (definición única)

### 2.1 Población

La entrada primaria de EXPLORE-001 es el **primer toque operable** de una zona,
**no** la creación de la zona.

Contrato de extracción (ya implementado, no se relaja):

- un evento por zona: el `ZONE_TOUCHED` con `touch_count == 1`;
- campos exigidos para entrar al censo autoritativo: `zone_id` string no vacío,
  `touch_count` int, `bar_index` int, `unix_ms` int;
- invariantes anti look-ahead: `touch_bar > created_bar` **y**
  `first_touch_ms > created_ms`.

Fuente de autoridad de tasas para congelar H1–H3: censo de primeros toques +
política de decongestión de §2.3. Las tasas de **creaciones** siguen siendo
**solo diagnósticas** (enmienda 2026-08-04).

### 2.2 Definición de «toque» / alejamiento (Nico)

Un primer toque **no basta** como disparo de estrategia si el precio no se ha
alejado. La regla de entrada exige un **umbral de alejamiento previo T**
(ticks), medido desde el borde relevante de la zona según arquetipo y `kind`.

**Dos arquetipos, siempre desglosados por `kind` del indicador** (nunca colapsar
arquetipos ni kinds al reportar):

| arquetipo | tesis | qué mide la supervivencia a T |
|---|---|---|
| **retorno** | el precio se aleja ≥ T y **vuelve** hacia la zona | fade / mean-reversion |
| **ruptura** | el precio se aleja ≥ T **de** la zona en la dirección de break | continuación |

Fundamento (corrección de Nico a la curva v1): no es lo mismo un gap (volver es
natural) que una burbuja de absorción / BigTrap (si hay atrapados, el precio se
va **de** la zona). Medir un solo arquetipo en todos los indicadores es el
evento equivocado para la mitad del espacio.

### 2.3 Toque en la misma barra de creación — regla fail-closed

Hallazgo de código (no parcheado a propósito): `Gaps2`, `HFTZones2` y
`AACloseOpenDiffs` pueden registrar un «toque» en la **misma barra** que creó la
zona.

**Regla sellada propuesta:**

> Todo evento con `touch_bar <= created_bar` o `first_touch_ms <= created_ms`
> **queda fuera de la población de entrada**. No se reinterpreta como señal. No
> se «arregla» el kernel en silencio para pasar el censo.

Consecuencia: si un indicador solo produce esos eventos, su tasa autoritativa es
cero o `sin_poblacion` — eso es un resultado de diseño, no un bug a ocultar.

`AACloseOpenDiffs` (cero `ZONE_TOUCHED` con creaciones > 0) se clasifica
`sin_poblacion`, **nunca** como censo COMPLETE de tasa 0
(`D3_CENSO_…` §3-bis).

### 2.4 Decongestión (ya congelada — se hereda sin cambio)

De `EXPLORE-001-2026-08-04_first_touch_decongestion.md`:

- ancla: `first_touch_ms`;
- separación: **120 minutos**;
- alcance: por fecha de sesión `America/Chicago`;
- algoritmo: greedy cronológico, conserva el primer elegible;
- frontera de sesión reinicia la separación;
- empate de timestamp: `created_ms` más antiguo; luego `zone_id`;
- outcomes: prohibidos.

---

## 3. Grilla cerrada del espacio de reglas de entrada

**Declarada hoy. Cerrada. No ampliable después de ver resultados.** Si sobra,
recortar **antes** del sello.

### 3.1 Ejes

| Eje | Valores | Notas |
|---|---|---|
| **Indicador** (elegibilidad) | Solo los que pasen el contrato de §2.1 al momento del censo autoritativo | Hoy sin duda: `BigTrap2`. Otros entran **solo** tras normalizar eventos (camino A de D3), verificado que no rompe paridad |
| **Arquetipo** | `retorno`, `ruptura` | siempre cruzado con `kind` |
| **`kind`** | el que emite el indicador (p.ej. `trapped_buyers` / `trapped_sellers` en BigTrap2) | no se inventan kinds; no se agregan lados a mano |
| **Umbral T (ticks de alejamiento)** | **`1, 2, 3, 5, 8, 13, 21`** | grilla anidada; T=0 **excluido** (mediría que un gap «empieza donde empieza», p50=0 en AACloseOpenDiffs) |
| **bar_spec (familia BigTrap2 / H1)** | `tick:10,15,25,50,100` + control `time:1` | ya declarado en ESPEC §2-ter; **no se reabre** |
| **Separación** | 120 min fijo | §2.4 |
| **Dirección** | régimen A nativo si el indicador emite side usable; si no, régimen B bilateral (`ESPEC` §2-bis) | **prohibido** elegir dirección después de ver resultado |

### 3.2 Qué cuenta como celda cobrada al presupuesto

Toda tupla

```text
(indicador, arquetipo, kind, T[, bar_spec si aplica])
```

que se **evalúe** (aunque se abandone) se cobra. Celdas no corridas porque el
indicador fue `rechazado` / `sin_poblacion` en el censo **no** se cobran como
hipótesis económicas; se registran como no elegibles.

### 3.3 Criterio anti-pico (specification curve) — obligatorio

Generaliza ESPEC §2-ter a **todo eje ordenado** de esta grilla (T y, en H1,
resolución):

> Una hipótesis sobre un eje ordenado **VIVE** sólo si pasa una **banda contigua
> de ≥ 3 valores adyacentes** del eje. Un pico aislado con vecinos muertos se
> declara **MUERTO** aunque su celda aislada pase el umbral estadístico.
>
> **Entregable: la CURVA completa del eje × expectativa neta con IC — nunca el
> argmax.**

Fundamento: si el efecto es real, varía con suavidad en el eje. Buscar ancho con
esta regla **aumenta** la confianza: cada vecino es réplica.

### 3.4 N_eff de referencia (pre-sello, no definitivo)

Conteo **bruto de celdas nominales** si solo BigTrap2 es elegible y se cruzan
ambos arquetipos × kinds nativos (2) × T (7) × resoluciones de familia (5) +
control time:1 separado:

```text
familia tick:  2 arquetipos × 2 kinds × 7 T × 5 resoluciones = 140
control time:1: 2 × 2 × 7 = 28
nominal ≈ 168 celdas anidadas
```

La grilla es **anidada** (no partición): casi todas las celdas comparten trades
con sus vecinas; el `n` por celda no se divide como en un grid disjunto.

**`N_eff` efectivo para corrección de multiplicidad NO se sella en este DRAFT.**
Ver §6 (D43 abierto: `M_eff=21,2` asertado es inadmisible como umbral de muerte).
Al sellar, Nico elige una de las opciones de §6; el número queda escrito en el
manifiesto de campaña, no se improvisa al ver resultados.

---

## 4. Estadístico y muerte (hereda ESPEC; no se reabre)

- Estadístico primario: **expectativa NETA por trade en ticks**, fricción
  **2,768 ya restada dentro** del estadístico; umbral = 0
  (`ESPEC` §3.1). Prohibido restar fricción otra vez a la derecha.
- Fricción: comisión real Lucid **$2,40/lado** + slippage base 1 tick/lado →
  **2,768 ticks RT**. Desglose broker/exchange/NFA **no acreditable** desde la
  fuente; total sí. CAMP-001 **no se reabre** (negativo con costos subestimados).
- Muerte: VIVE / MUERE / GRIS=muere por defecto (`ESPEC` §3.2), más banda
  contigua §3.3 de **esta** enmienda.
- Holdout: una sola apertura por candidato tras G3; frontera sello 2026-07-01
  (regla 95).

---

## 5. Relación con PRED-004 y la primera campaña

| Hecho (tip `626877f`+) | Efecto |
|---|---|
| Política ABSTAIN + `contrato_sha` **`4ac53dba…`** alineado | instrumento no puede PASS con `seq_corrido=true` |
| T3a SATISFECHO — oráculo P5 sha **`7d0f464f…`** | identidad del artefacto OK |
| K1 ADMISIBLE (regresión acotada) | P5 usable como referencia, no limpia cuarentena |
| Paridad `BigTrap2` `time:1` en PASS | **PRED-004 no bloquea la primera campaña sobre time:1** |
| PRED-004 sigue bloqueando H1 en **barras de tick** | tick:10/25/… exigen captura autorizada + fila holdout |

**Correr P5 (contenido económico del oráculo) sigue exigiendo** fila en
`holdout_access_log.md` con `purpose=target_free_validation` **antes** de leer
zonas/precios — T3a solo verificó identidad estructural.

---

## 6. Abierto al sellar — decisiones de Nico (menú corto)

Marcar una por fila al sellar:

| # | Decisión | Opciones |
|---|---|---|
| S1 | Grilla T | **(a)** aceptar `1,2,3,5,8,13,21` · **(b)** recortar a: _______ · **(c)** rechazar enmienda |
| S2 | Arquetipos | **(a)** ambos obligatorios en todo indicador elegible · **(b)** otro: _______ |
| S3 | Misma-barra | **(a)** fail-closed §2.3 · **(b)** otro: _______ |
| S4 | Multiplicidad | **(a)** posponer `M_eff` numérico al manifiesto de campaña con método de autovalores / Romano-Wolf declarado · **(b)** fijar método ahora: _______ |
| S5 | Indicadores en el primer censo autoritativo | **(a)** solo los que pasen §2.1 hoy · **(b)** esperar normalización de contrato (D3 camino A) antes de cualquier gate |
| S6 | Primera campaña formal | **(a)** puede arrancar en `BigTrap2` `time:1` bajo esta enmienda + ESPEC · **(b)** no arrancar hasta PRED-004 tick cerrado |

**Propuesta del auditor (no es sello):** S1a, S2a, S3a, S4a, S5a, S6a.

---

## 7. Checklist de sello (Nico)

- [ ] Leí §2–§3 y las opciones de §6
- [ ] No miré outcomes / holdout / retornos de estrategia al decidir
- [ ] Recortes a la grilla (si hay) están escritos **arriba**, no en un chat
- [ ] Firmo: estado pasa a **SEALED v1.0** con fecha y hash al pie
- [ ] Se agrega fila en `docs/campaigns/INDEX.md` (enmiendas) y se cita el hash
      en el próximo manifiesto de campaña

```
SELLADO POR: __________________  FECHA (UTC): __________________
```

## STOP

Este DRAFT **no autoriza ninguna corrida económica**. No llena §3.3. No abre el
holdout. No instala `.cs`. Tras SEALED, el implementador puede: (1) correr el
censo autoritativo de primeros toques, (2) proponer H1–H3 en una pasada, (3)
redactar el manifiesto de campaña que herede este hash.

<!-- SHA256-BODY-ABOVE -->

**sha256 del cuerpo (hasta el marcador):** *(se calcula al sellar; en DRAFT no se publica un hash de identidad para no fingir inmutabilidad)*

**Estado:** DRAFT v0.1 — 2026-08-06 — pendiente de Nico.
