# E-R1 v0.3 — pre-registro de EXPLORE-001

**Estado:** **DRAFT. NO SELLADO.** Sellar es acto humano (§7 Paso 5).
**Fecha de redacción:** 2026-08-09 · Outcome-free · Holdout no tocado
**Redactado por:** Claude, bajo *«avanzá con el paso 3 y redactá E-R1»*.

> **Una celda queda ABIERTA y bloquea el sello: `f` y el MDE (§9).** Todo lo
> demás está cerrado. La celda abierta no es una omisión: es un hallazgo del
> Paso 3 que exige una medición que hoy no existe.

---

## 1. Hipótesis selladas

**Una sola hipótesis confirmatoria.**

| | indicador | `T` | dirección | rol |
|---|---|---:|---|---|
| **H1** | `BigTrap2` | **34** | **nativa** | confirmatoria de edge |

`aVolCellPOI2`, `VolTicksPOC2`, `Gaps2`, `HFTZones2` y `AACloseOpenDiffs` **no
entran**. Motivos por candidato en
[`DECISION_2026-08-09_direccion_y_alcance_de_EXPLORE-001.md`](../research/DECISION_2026-08-09_direccion_y_alcance_de_EXPLORE-001.md).

Autorizado por §6.4: *«completar "tres" no justifica admitir una hipótesis mal
definida»*.

**Se pierde la diversificación mecánica** que §3.3 buscaba. El resultado, sea
cual sea, habla de `BigTrap2` — no de una clase de fenómeno. Queda declarado.

## 2. Población de eventos

Zonas de `BigTrap2` sobre el universo de research:

```
201 sesiones · 4 contratos 6E · corte 2026-06-30
firewall: holdout 2026-07-01 → 12-31 SELLADO; INC-005 en cuarentena 07-01 → 07-16
```

**Población autoritativa: primeros toques post-`sep_min = 120`**, según la
enmienda `EXPLORE-001-2026-08-04_first_touch_decongestion`. **No** creaciones.

## 3. Disponibilidad

`BigTrap2` es de clase `bar_close`. Una zona queda disponible al **cierre de la
barra creadora**, nunca antes:

```
disp = bar_end[created_bar]
i0   = primer tick con ts > disp        (estrictamente posterior)
```

La barra creadora **nunca toca su propia zona** (`UpdateZones` corre antes de
crear). Barra 0 descartada: footprint potencialmente parcial.

## 4. Regla `k_T > 0`

```
k_T > 0   →  excursión válida
k_T == 0  →  ya_fuera_al_quedar_disponible: NO es ruptura, NO habilita retorno
retorno válido  ⇔  k_T > 0  ∧  j_retorno > k_T
```

Los `k_T == 0` **no se borran**: se publican como arquetipo separado. Medidos a
`T=34`: **19 sobre 17.192 zonas = 0,111 %**. La corrección es económicamente nula
(9,08 → 9,07).

La excursión es **bidireccional**: `k = min(k_arriba, k_abajo)`, el primero que
ocurra en cualquier sentido.

## 5. Dirección de H1 — congelada

Verificada en fuente (`bigtrap2.py:266` y `:274`):

| `kind` | agresión | posición de la zona | operación |
|---|---|---|---|
| `trapped_buyers` | compradora **por encima** del close | **resistencia**, arriba | **CORTO** |
| `trapped_sellers` | vendedora **por debajo** del close | **soporte**, abajo | **LARGO** |

> **⚠ Trampa de nomenclatura, declarada.** `is_bull = True` → `trapped_buyers` →
> operación **bajista**. El flag nombra **quién quedó atrapado**, no la dirección
> del trade. Invertirlo invierte la hipótesis entera.

**Balance verificado:** 8.741 / 8.451 (50,8 % / 49,2 %). Sin sesgo direccional
encubierto.

**Traducción descartada por medición, no por razonamiento.** La lectura *«sólo
cuenta la excursión que sale por el lado del atrapamiento»* da **49 eventos en 201
sesiones** (0,244/ses) a `T=34`. Muerta por potencia.
Artefacto: `concordancia_lado_bigtrap2.json`.

## 6. Entrada, horizonte, salida y censura

```
zona disponible
 → excursión de T=34 ticks, k_T > 0        ← setup
 → retorno a la banda, j > k_T             ← ENTRADA
 → dirección del §5
```

**Mecanismo, enunciable sin outcomes:** el precio se aleja, vuelve al nivel donde
quedaron los atrapados, y ahí ellos obtienen su salida —los largos bajo el agua
venden— empujando en contra del retorno.

**Salida y censura:** *(pendiente de cerrar junto con §9 — depende de la misma
medición)*. La zona muere por `ended_ms` del `lifecycle`; la censura por fin de
sesión debe declararse explícitamente antes de sellar.

## 7. Estimando y fricción

```
expectativa neta por evento elegible, en ticks
fricción round turn = 2,768 ticks, restada DENTRO del resultado de cada evento
umbral económico del estimando neto = 0 ticks
```

**Prohibido volver a restar 2,768 del lado derecho de la comparación.**

## 8. Dependencia, inferencia y multiplicidad

**Dependencia.** Estimación puntual sobre eventos elegibles; **la inferencia
remuestrea o agrupa por sesión**; bloque mínimo = día de sesión CT. Se reporta
como sensibilidad la media equal-weight diaria. Una diferencia material entre
pooling por evento y equal-weight **se declara, no se promedia**.

**Multiplicidad.** Presupuesto declarado y pagado por el barrido de resolución:

```
M_eff 21,2 → ~106     z 3,041 → 3,50     MDE +11,8 %     margen medido 1,60×
```

Correr **una** hipótesis en vez de tres es conservador respecto de eso.
**La holgura se declara y NO se aprovecha** — mismo principio que la spec ya
aplicó a Bonferroni: *«el costo real es menor — anotado, no aprovechado»*.

**Regla de decisión (§5.4), sin cambios:**

```
VIVE:   cota inferior del IC ajustado > 0
MUERE:  cota superior del IC ajustado < 0
GRIS:   el IC contiene 0  →  MUERE POR DEFECTO
```

Sin excepción escrita **antes** de outcomes, gris significa muerta. Una hipótesis
muerta no vuelve con parámetros retocados.

## 9. ⛔ CELDA ABIERTA — `f` y el MDE

**Esto bloquea el sello.**

`f` no está determinada, porque las dos poblaciones disponibles difieren en un
orden de magnitud:

| población | eventos/ses | fuente |
|---|---:|---|
| zonas del censo (sin `sep_min`) | 85,5 | `recuento_kT` |
| **primeros toques post-`sep_min`** | **9,08** | censo autoritativo |
| retornos válidos `T=34`, población del censo | 8,23 | `recuento_kT` |

§6.3 publica `f ≈ 8,3` para esta celda, y coincide con **8,23** — que sale de la
población **sin `sep_min`**, no de la autoritativa. Verificado: `recuento_kT.py`
no menciona `sep_min` en ninguna línea.

**Lo que falta:** un recuento de excursión + retorno **sobre la población de
primeros toques post-`sep_min`**. Ese módulo no existe.

**Por qué no lo estimo:** `f` entra directo al MDE, y el MDE decide si la celda es
ciega. §6.2 exige *«descartar geometrías ciegas al MDE de su frecuencia real»* —
con `f` indeterminada esa comprobación no se puede hacer.

## 10. Artefactos y hashes esperados

| artefacto | estado |
|---|---|
| `diag/tasa_senales/recuento_kT.json` | producido, `outcomes_accessed: false` |
| `diag/tasa_senales/censo_primeros_toques.json` | producido |
| `diag/tasa_senales/concordancia_lado_bigtrap2.json` | producido |
| recuento sobre primeros toques post-`sep_min` | **NO EXISTE — §9** |
| `docs/parity_coverage/` | montado |

## 11. Prohibiciones vigentes hasta sellar

Leer outcomes para elegir candidatos; elegir dirección después de ver resultados;
elegir el mejor `T` por P&L; reintroducir `k_T == 0`; incorporar
`AACloseOpenDiffs`; abrir el holdout; adjudicar automáticamente desde código;
modificar el artefacto original; tratar un resultado descriptivo como
confirmatorio; sustituir un candidato fallido después de outcomes; ejecutar menos
o más hipótesis que las selladas; ampliar la grilla después de ver resultados.

## 12. Qué falta para sellar

1. **Cerrar §9** — medir `f` sobre la población autoritativa. Bloqueante.
2. **Cerrar la salida y censura del §6.**
3. Verificación de paridad y de no-acceso al holdout (§7 Paso 5).
4. Confirmar que no quedan parámetros libres.
5. **Acto humano de Nico.** Este documento no se sella solo.

Y una lectura pendiente del referente: la interpretación de *«sólo si»* en §5.3,
de la que depende que H1 sea la única hipótesis.
