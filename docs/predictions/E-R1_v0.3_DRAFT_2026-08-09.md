# E-R1 v0.3 — pre-registro de EXPLORE-001

**Estado:** **DRAFT. NO SELLADO.** Sellar es acto humano (§7 Paso 5).
**Fecha de redacción:** 2026-08-09 · Outcome-free · Holdout no tocado
**Redactado por:** Claude, bajo *«avanzá con el paso 3 y redactá E-R1»*.

> **`f` y el MDE quedaron CERRADOS** el 2026-08-09b: `f = 2,13/sesión`,
> margen 3,49×, **la celda no es ciega**.
> **Queda un solo parámetro libre: salida y censura (§6).** Cerrado eso, E-R1
> está listo para el acto humano de sello.

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

## 9. `f` y el MDE — **CERRADA** (2026-08-09b)

```
f = 2,13 eventos/sesion     MDE ~ 0,794     margen = 2,768/0,794 = 3,49x
                            NO es ciega; pasa tambien con el +11,8% del barrido
```

Condicion de validez: **el primer toque debe ser posterior a la excursion**.
Orden de composicion: **B**. Margen: **friccion/MDE**, definicion del spike-in.
Fundamento de las tres → [`DECISION_2026-08-09b`](../research/DECISION_2026-08-09b_condicion_orden_y_margen.md).

**Queda abierta una sola cosa para sellar: salida y censura (§6).**

El material de diagnostico que llevo a esta decision se conserva abajo.

### 9.1 Primero, la buena noticia: la entrada del §6 **es** el primer toque

La enmienda `first_touch_decongestion` fija *«la entrada primaria en el primer
toque posterior»*, ancla `first_touch_ms`. El §6 define la entrada como el retorno
a la banda tras la excursión. **Coinciden en la mayoría abrumadora de los casos**:
si la zona estaba vacía al quedar disponible, la primera vez que el precio entra a
la banda después de la excursión **es** su primer toque.

Medido: **94,7 %** de los retornos válidos de `BigTrap2` a `T=34` vienen de zonas
que no contenían al precio en `i0`. No hay conflicto de definición.

### 9.2 El problema real: **nadie aplicó los dos filtros juntos**

| medición | `sep_min` | excursión `T=34` | eventos |
|---|:-:|:-:|---:|
| censo autoritativo | **sí** | no | **1.825** (9,08/ses) |
| `recuento_kT` | **no** | **sí** | **1.655** (8,23/ses) |
| **lo que E-R1 necesita** | **sí** | **sí** | **no medido** |

Verificado: `recuento_kT.py` no menciona `sep_min` en ninguna línea.

> **⚠ Trampa numérica.** 1.825 y 1.655 se parecen, y §6.3 publica `f ≈ 8,3` que
> coincide con 8,23. **Es coincidencia entre dos filtros distintos**, no
> confirmación. Tomar cualquiera de los dos como `f` sería tomar una población a
> la que le falta un filtro.

Si los filtros fueran independientes, aplicar ambos daría del orden de
`1.825 × (1.655 / 17.192) ≈ 176` eventos — **~0,87/sesión, un orden de magnitud
menos**. No se sabe si son independientes, y **el producto de marginales no es una
medición**.

### 9.3 MEDIDO — ⚠ el veredicto «ciega» de esta sección quedó RETIRADO

> **Leí mal «margen».** No es *efecto/MDE*: la tabla canónica del spike-in lo
> define como **fricción/MDE**. Con la definición correcta **ninguna celda es
> ciega** — a `f = 2,13` el margen es **3,49×**.
> → [`CORRECCION_2026-08-09`](../research/CORRECCION_2026-08-09_el_margen_y_la_celda_no_es_ciega.md)
>
> Las **`f` medidas de abajo siguen siendo válidas**; lo retirado es la columna
> «margen» y su veredicto.

### 9.3-bis Lo medido (la tabla de margen de abajo NO vale — ver arriba)

Medido dos veces, por Claude (`f_ambos_filtros.py`) y por Codex
(`recuento_kT_primer_toque_run.py`), de forma independiente. **Discrepan en un
factor ~2** por la condición de validez; el desacuerdo está registrado sin
resolver en [`DESACUERDO_001`](../audits/DESACUERDO_001_condicion_de_validez.md).

| `f` medida | orden | quién | `N_eff`~ | `MDE`~ | margen~ | veredicto |
|---:|---|---|---:|---:|---:|---|
| 8,23 | *(sin `sep_min`)* | §6.3 publicada | 1.440 | 0,423 | **1,46** | entra |
| **3,64** | B | Codex | 680 | 0,616 | **1,00** | **MARGINAL** |
| **2,13** | B | Claude | 410 | 0,794 | **0,78** | **CIEGA** |
| 0,79 | A | Codex | 156 | 1,288 | 0,48 | CIEGA |
| 0,35 | A | Claude | 69 | 1,935 | 0,32 | CIEGA |

> **Con ninguno de los valores medidos la celda entra con el margen 1,60×
> declarado.** El mejor caso —la medición de Codex bajo el orden B— la deja
> **exactamente en el límite**.

**Advertencia sobre estos MDE.** `reconstruir_mde.py` reproduce la tabla publicada
(dif. máx. 0,0047 ticks), pero el propio script declara que **`N_eff(f)` está
TABULADO, no reconstruido**: sale de un bootstrap que no vuelve a correr. Los
`N_eff` de arriba salen de **interpolar** esa tabla. **Son estimaciones, no
mediciones.** El número exacto exige rehacer el bootstrap a la `f` medida.

### 9.4 Qué queda abierto

1. **Cuál condición de validez es la correcta** — `DESACUERDO_001`. Decide si el
   mejor caso es 3,64 o 2,13, y por lo tanto si la celda es marginal o ciega.
2. **Cuál orden de composición** — A o B. Difieren en factor 5-6.
3. **El `N_eff` real a la `f` medida**, con bootstrap, no interpolación.

Hasta cerrar los tres, **§6.2 no se puede aplicar** —*«descartar geometrías ciegas
al MDE de su frecuencia real»*— y **E-R1 no se puede sellar**.

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
