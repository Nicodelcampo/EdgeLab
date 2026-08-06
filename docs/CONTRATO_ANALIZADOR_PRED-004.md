# Contrato del analizador de PRED-004 — **v5**, re-congelado 2026-08-05

> **G0 + G1 de las tres iteraciones independientes.** Ocho reproducciones en rojo
> primero (`fd127f0`), después el parche. Ninguna corrección se aplicó sin haber
> demostrado antes el estado defectuoso.
>
> `contrato_sha` **v1** `6d0e87b7…` · **v2** `109f41c1…` · **v3** `a92c220d…` — retirados
> `contrato_sha` **v4** `8c7e6920…` — retirado por la enmienda N1
> `contrato_sha` **v5** = **`23981e56799b4f7f2dbbd889f0cc54011df5818b5d164e7f8d9e865c7a087dce`**
> `sha256` de `nt8/BigTrap2.cs` **v2.4** = `9b63959a…398258e3` — **sin tocar en esta ronda**

## Lo que decide esta versión

Las tres iteraciones (GPT, Grok, Kimi) coinciden en un diagnóstico que la v3 no
tenía: **el instrumento fallaba fuera de las ramas que la batería ejercitaba.**
La v3 daba 38/38 y tenía una rama que tiraba `NameError`.

## G1 — los siete arreglos, cada uno con su reproducción previa

| # | hallazgo | estado antes | reparación |
|---|---|---|---|
| 1 | **H-GPT-1** — la rama `denom == 0` usa `verif`, **no definido en el módulo** | `NameError` | expresión correcta + la rama publica **los mismos campos** que la salida normal |
| 2 | **H-GPT-2** — `--resolucion` era `default=None` y cada modo hacía `if resolucion:` | omitirla salteaba el chequeo entero | `required=True` en los tres subparsers **y** ABSTAIN a nivel API |
| 3 | **H-KIMI-3** — `footprint_mismatch_total` y `tasa_mismatch_total` no compartían población | el "menor 3" de v3 corrigió la tasa y **no** el contador | poblaciones explícitas + `nota_poblaciones` en el JSON |
| 4 | **H-GROK-4 / H-KIMI-7** — un log `version=2.3` con `BARRA_PROCESADA` se medía igual | procedencia no verificada | `--exigir-version`, ABSTAIN de procedencia |
| 5 | **H-GPT-6** — P3 certificaba OHLC**V** sin haber visto la V | PASS silencioso | los **cinco** pares son precondición; si falta uno ⇒ `NO_APLICA` |
| 6 | **H-GROK-3** — comentarios de warmup con la semántica vieja por anclaje | invitaba a reintroducir H2 | limpiados, con test que lo vigila |
| 7 | **H-GPT-1b** — la rama ABSTAIN publicaba menos campos que la normal | no se distinguía abstención de salida **truncada** | dict común `comunes` + test de igualdad de claves |

### Por qué H-GPT-1 importa más que su arreglo

`verif` aparecía en **una sola línea** del módulo y no estaba definido en ningún
lado. La rama tiraba `NameError`. Sobrevivió porque
`test_p1p2_denominador_cero_es_ABSTAIN_no_PASS` **nunca la alcanzaba**: su
fixture no tenía `BARRA_PROCESADA`, así que abstenía antes, en
`primera_ok is None`.

**Es la tercera instancia del mismo modo de falla:** B3 (P4 inalcanzable), H2
(denominador inexistente) y ahora esta. El patrón es siempre el mismo — *el
nombre de un test promete una alcanzabilidad que su fixture no entrega*.

## Hallazgo propio: **dos emisores de `FOOTPRINT_MISMATCH` con esquemas distintos**

No está en ninguna de las tres iteraciones.

| emisor | pares | volumen |
|---|---|---|
| `BigTrap2.cs:541` (`ReportarMismatch`) | **5** | **sí** |
| `BigTrap2.cs:601` (rotura de bloque) | **4** | **no** |

GPT-6 escribió *"`ReportarMismatch` parece emitir los cinco pares"* — es cierto y
es **incompleto**. Consecuencias:

1. El fixture que GPT-6 propuso como **adversarial** es en realidad
   **`emisor_fiel`**: reproduce literalmente el payload de `.cs:601`.
2. **Tres fixtures míos eran infieles** — emitían sólo `open_blk`/`open_bar`, un
   esquema que **ningún** emisor produce. Corregidos.

### Consecuencia que requiere decisión de Nico

Con la regla nueva (**fail-closed**), basta un par procesado sin el esquema
entero para que P3 sea `NO_APLICA`. Como `.cs:601` **nunca** emite volumen, una
captura real con roturas de bloque daría **P3 = `NO_APLICA` de forma
permanente**.

Las dos salidas, y no la elijo yo:

- **A — dejarlo así.** P3 se pronuncia sólo cuando el esquema alcanza. Honesto,
  pero P3 podría no dar veredicto nunca en capturas reales.
- **B — corregir aguas arriba**, que `.cs:601` emita `vol_blk`/`vol_bar`. Es
  tocar el `.cs` otra vez, y **hay que verificar antes si ese emisor es
  alcanzable en el camino de tiempo**, porque si lo es, cambia el payload y toca
  P5 directamente. Esa verificación es N1.

Hoy queda en **A**, que es la conservadora. `p3_pares_procesados_esquema_completo`
y `..._incompleto` se publican para que la cobertura de P3 sea **visible y no
haya que inferirla del veredicto**.

## Lo que NO se tocó, a propósito

- **N1** (corrimiento de `seq`) — sigue abierto. Delegado a inventario
  independiente. Las tres iteraciones coinciden en que no se resuelve eligiendo
  la opción cómoda, y Kimi agrega que además **bloquea** la doble contabilidad
  emisor/analizador (H-KIMI-5).
- **`BigTrap2.cs`** — sin cambios en esta ronda. Pin sin mover.
- **T6 / gate de compilación** — no se declara cerrado por regex. El test H1
  detecta el `ok` conocido y **no demuestra que el archivo compile**.
- **K1 / admisibilidad del oráculo de P5** frente a la cuarentena INC-005 —
  bloqueante de P5, en curso por separado.

## Batería

**46/46.** Las ocho reproducciones de G0 pasaron de rojo a verde sin que ninguna
se haya escrito después de ver el arreglo: están en `fd127f0`, un commit
anterior al parche.

**Regla que se agrega a la de citar la línea del `.cs`:** todo test sintético
declara si su fixture es **`emisor_fiel`** o **`emisor_adversarial`**. La
distinción no es cosmética — descubrir que el fixture "adversarial" de GPT-6 era
en realidad fiel a `.cs:601` fue lo que destapó los dos esquemas.


---

## v5 — enmienda N1, **aprobada por Nico el 2026-08-05**

Fundamento completo: [`N1_INVENTARIO_SEQ.md`](N1_INVENTARIO_SEQ.md).

**Qué cambia.** P5 comparaba identidad bit a bit **incluyendo el `seq`
absoluto**. Eso era incomparable por construcción: `eventSeq++` es un contador
**compartido** (`.cs:892`) y el predicado de `FOOTPRINT_MISMATCH` cambió entre
versiones —v2.1 (`.cs:218`) mira **volumen**, v2.4 (`VerificarOHLC`) mira
**OHLC**: predicados **disjuntos**— así que el conteo difiere y corre el `seq`
de todo evento económico posterior.

**P5 habría dado FAIL por el contador, no por la regresión que busca.** Y el
contrato ya había decidido que `FOOTPRINT_MISMATCH` no se compara
(`P5_TIPOS_ECONOMICOS` lo excluye): juzgar su efecto sobre el `seq` contradecía
esa decisión.

**Qué NO cambia — y es lo que separa la enmienda de hacer trampa.** El
corrimiento **no se borra**: se publica como `delta_seq_min/max/distintos`,
`seq_corrido` y `footprint_mismatch_por_lado`, **que es su causa**. Meter `seq`
en `P5_PAYLOAD_IGNORABLE` habría sido eliminar la diferencia; esto es separarla
de la comparación económica **y reportarla**.

Un `delta_seq` **no uniforme** no se explica por un contador compartido: es un
hallazgo, y `delta_seq_distintos` lo deja visible.

### Los seis tests existen para probar que la enmienda no afloja P5

| test | qué prueba |
|---|---|
| `seq_corrido_con_economia_identica_es_PASS` | el caso real: antes daba FAIL, y por el contador |
| `el_corrimiento_se_PUBLICA_no_se_borra` | los seis campos están; si faltaran, sería una lista ignorable disfrazada |
| `la_causa_del_corrimiento_queda_al_lado` | el delta sin su causa es un número hueco |
| `NO_afloja_payload` | cambiar un campo económico **sigue siendo FAIL** |
| `NO_afloja_orden_ni_timestamp` | un económico que aparece o desaparece se caza igual |
| `delta_no_uniforme_queda_visible` | lo que el contador **no** explica queda a la vista |

**Batería: 52/52.**
