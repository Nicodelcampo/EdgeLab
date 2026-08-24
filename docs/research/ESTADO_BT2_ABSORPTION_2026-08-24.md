# Estado consolidado — BigTrap2Absorption · corte del 2026-08-24

- **Rama:** `foundation/f0b-compatibility-probe` · **HEAD:** `1eeaa45`
- **Alcance:** GC, universo pre-holdout `2025-11-26 .. 2026-06-30`
- **Este documento es un índice, no una medición.** Todo lo que afirma está en un
  artefacto commiteado; acá sólo se ordena.

> **Nada de esto declara edge.** El estimando de Puerta 1 no se corrió.

---

## 1. Vector de estado

```
PUERTA_0_FIRMADA                = SI      (GC 12-26 agosto, GC 08-26 junio)
KERNEL_PARITY_ON_EQUAL_INPUT    = ~EXACT
GLOBAL_ACCUMULATED_PARITY       = FAIL    (artefacto del indexado global de barras)
SESSION_RECOVERABLE_PARITY      = RECOVERED
TAPE_VS_CHART_COVERAGE          = ABIERTO
UNIVERSO                        = 152 sesiones, cadena rule-based, 4 rolls auditados
SPLIT                           = 133 / 19, congelado ANTES de outcomes
POTENCIA                        = 85,0 % contra la vara de 2,5 ticks (G=151 con evento)
N_RAND_CAPACIDAD                = OK, 0 de 4.661 estratos flacos
B9_CONTEXTO                     = MEDIDO sobre las 152
CAMPAIGN_OUTCOMES_OPENED        = false
PREEXISTING_OUTCOME_EXPOSURE    = YES     <- ver seccion 5
SWEEP_TARGET_FREE               = EN CURSO (GC 02-26, 51 configs OAT)
PUERTA_1                        = NO CORRIDA
```

---

## 2. Paridad `.cs` ↔ Python

| ventana | contrato | veredicto | artefacto |
|---|---|---|---|
| agosto, 5 sesiones | GC 12-26 | **PASS** 27.328/27.328 | `FIRMA_FINAL_PUERTA0_BT2_ABSORPTION_2026-08-23.md` |
| junio, 15 sesiones | GC 08-26 | **PASS** | `PARIDAD_JUNIO_GC0826_2026-08-23.md` |
| diciembre, 30 sesiones | GC 02-26 | FAIL global · **RECUPERADA por sesión** | `PARIDAD_BT2_ABSORPTION_GC0226_2026-08-24.md` |
| 51 sesiones | GC 04-26 | FAIL global · recuperada por sesión | `PARIDAD_POR_SESION_3_CONTRATOS_2026-08-24.md` |
| 50 sesiones | GC 06-26 | FAIL global · recuperada por sesión | idem |

**El `FAIL` global no era del kernel.** El comparador indexaba por número de barra
**acumulado**, así que una sola diferencia de tick corría toda la numeración posterior y
destruía la comparación. Reindexado por `(cme_session_id, bucket_index_within_session,
t_start)`, GC 02-26 pasa de **0,77 %** de cobertura a **99,992 %** de aritmética exacta
y **99,9994 %** de capa causal.

Lo que **sigue abierto** es distinto: la cinta (`.Last.txt`, base de ticks cruda) y el
chart de NT8 **no contienen siempre los mismos ticks**. Documentado en
`NT8_PLANTILLA_SESION_CIERRE_FERIADO_2026-08-23.md` — en feriado la plantilla de sesión
de NT8 corta 90 minutos antes que la cinta.

> **No convertir `TAPE_VS_CHART_COVERAGE` en defecto del kernel, ni declararlo resuelto.**

---

## 3. Universo y split

`ENMIENDA_UNIVERSO_GATE1_2026-08-23.md` · `CADENA_FRONTMONTH_GC.json` ·
`AUDITORIA_ROLLS_152.json`

Cadena front-month por volumen, con la regla congelada de dos confirmaciones:

| contrato | sesiones | desde → hasta |
|---|---:|---|
| GC 02-26 | 48 | `20251126 → 20260128` |
| GC 04-26 | 43 | `20260129 → 20260327` |
| GC 06-26 | 42 | `20260330 → 20260527` |
| GC 08-26 | 24 | `20260528 → 20260630` |

Los cuatro rolls pasan los cuatro chequeos: sin sesión duplicada, bordes contiguos,
monotonía sin retroceso, y la sesión de roll pertenece al sucesor.

**Split `133 / 19` congelado antes de abrir outcomes** (`eda2a07`,
`specs/bt2_absorption_gate1_split_v1.json`). Intersección de los dos bloques: **0**.

---

## 4. Lo medido target-free

| medición | resultado | artefacto |
|---|---|---|
| **B-9 contexto** | `a_thr` entre sesiones **3,38×**; intradía **1,30–1,50×** | `B9_Y_NRAND_SOBRE_152_2026-08-23.md` |
| **capacidad N_RAND** | `N_RAND_CAPACITY_OK`, 10.289 eventos, 4.661 estratos, **0 flacos** | `NRAND_CAPACIDAD_ESTRATOS_2026-08-23.md` |
| **mezcla direccional** | 206 long / 171 short = **54,6 / 45,4**, sd 2,5 pp | `MEZCLA_DIRECCIONAL_Y_NULO_BT2_ABSORPTION_2026-08-23.md` |
| **filtro horario CME** | 53 ticks de fin de semana descartados; los de feriado **se conservan** | `FILTRO_HORARIO_CME_2026-08-24.md` |

**El eje grande del contexto es entre sesiones, no intradía** — y eso importa porque los
dos ejes estaban al revés en la medición previa sobre 115 sesiones.

---

## 5. Exposición previa a outcomes ⚠

`docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`

Doce archivos sin seguimiento, ajenos a la campaña, encontrados en el worktree **antes**
de lanzar el sweep. Once con outcomes, uno target-free.

| clasificación | valor |
|---|:-:|
| `P1_133_OUTCOME_EXPOSURE` | **YES** — 11 de 133 |
| `SEALED_19_OUTCOME_EXPOSURE` | **YES** — `20260608` |
| `TEMPORAL_HOLDOUT_EXPOSURE` | **YES** — 4 contratos |
| `CONTEXT_FILTER_SEARCH` | **YES** — hora del día × outcomes |
| `CROSS_ASSET_OUTCOME_SEARCH` | **YES** |
| `YM_FAMILY_EXPOSURE` | **YES** |

Enmienda en `specs/bt2_absorption_gate1_exposure_amendment_2026-08-24.json`, **sin editar
los specs congelados**. No reduce el universo: exige sensibilidad con y sin las 11
sesiones expuestas, y si el veredicto cambia entre ambas, `INCONCLUSIVE`.

> **`CAMPAIGN_OUTCOMES_OPENED = false` no es `OUTCOMES_NOT_OPENED`.** Las dos líneas van
> siempre juntas. El flag del runner describe **únicamente** la campaña del 2026-08-24.

---

## 6. Sweep target-free en curso

`specs/bt2_absorption_target_free_sweep_v1.json` · `BT2_ABSORPTION_SWEEP_OVERNIGHT_2026-08-24.md`

99 configuraciones (51 OAT sobre los 21 parámetros + 48 de interacciones), headline único
`bt2a_275e8b83b4e1922d` idéntico a `DEFAULTS`. Las 19 selladas quedan fuera de métricas,
fingerprints y solapamientos.

**Corriendo sobre GC 02-26 solamente**, con `--contracts`. Motivo medido, no supuesto:

```
7 config x GC 02-26   246 341 502 813 1234 1703 3157 s   -> dispersion 13x
proyeccion 4 contratos              10,6 - 49,4 h
proyeccion GC 02-26 solo            11,5 - 16,2 h
```

La dispersión de 13× es sobre **la misma cinta**: el costo lo manda cuántas zonas genera
cada configuración, no cuántos ticks hay. Eso ya es una señal de sensibilidad de
población, sólo que manifestada como tiempo de cómputo.

Un subconjunto de contratos **no puede leerse como corrida completa**: el estado pasa a
`COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS` y el resultado declara `contracts_measured`,
`contracts_omitted` y `full_contract_coverage`.

---

## 7. Lo que NO está hecho

- **Puerta 1 no se corrió.** No existe runner y no se va a escribir sin decisión explícita.
- **El sweep no eligió ganador** y no puede: no mira outcomes.
- **`TAPE_VS_CHART_COVERAGE` sigue abierto.**
- **Paridad medida sobre 2 de 4 contratos** del universo por oráculo directo; los otros
  dos, recuperados por sesión.
- **Sin hipótesis de contexto pre-registrada.** `NONE_PREREGISTERED` dejó de valer para
  GC 12-26 y YM 09-26 por §5, pero para el universo GC pre-holdout sigue vigente.

---

## Aporte al referente

Veinte commits de la jornada quedan con un punto de entrada único, y con la distinción
que más fácil se pierde al resumir: **`FAIL` de comparador y `FAIL` de kernel no son lo
mismo**, y acá el primero se convirtió en el segundo tres veces antes de medirlo bien.
Queda también separado, con fecha medida y no inferida, lo que esta campaña abre —nada—
de lo que el proyecto ya tenía abierto.

## Nota de método

Tres veces hoy declaré causa antes de medirla: el `FAIL` global como defecto de kernel,
el inventario del drop en 11 cuando eran 12, y dos estimaciones de tiempo erradas por 5×
y por 3×. Las tres las corrigió una medición posterior, y en dos de los tres casos la
corrección la disparó **un guardrail que aborta**, no una revisión mía: `clean_commit()`
encontró el doceavo archivo, y los parciales con `elapsed_seconds` desmintieron la
proyección. El patrón que queda anotado es que **el instrumento que se niega a correr
vale más que el que reporta**.
