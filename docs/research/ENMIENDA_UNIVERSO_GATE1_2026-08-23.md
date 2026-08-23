# Enmienda al universo de Puerta 1 — de 3 contratos / 115 sesiones a **5 contratos / 152 sesiones**

- **Fecha:** 2026-08-23 · **Base:** `fe63e39`
- **Enmienda:** `specs/bt2_absorption_gate1_v1.json` → `universe.source_contracts_full_ranges`
- **Firewall:** **outcomes `NOT_OPENED`** al momento de escribir esto. Ni un solo resultado mirado.
- **Artefacto:** `docs/research/CADENA_FRONTMONTH_GC.json`

> **Esta enmienda se decide a ciegas.** Sube la potencia; no selecciona sobre resultados, porque
> todavía no hay resultados. Queda asentada con fecha **antes** de abrir outcomes, que es la
> única condición que la hace legítima.

---

## 1. Qué cambia

| | spec congelado | enmendado |
|---|---|---|
| contratos | GC 04-26, 06-26, 08-26 | **+ GC 12-25, GC 02-26** |
| ventana | 2026-01-20 → 2026-06-30 | **2025-11-26 → 2026-06-30** |
| sesiones | 115 | **152** |
| potencia vs 2,5 ticks | 74,4 % | **85,2 %** |
| `P1_UNDERPOWERED_FOR_2P5T` | **se disparaba** | **se cae** |

`research_end_inclusive = 2026-06-30` **no se toca**. Todo el crecimiento es hacia atrás; el
borde de arriba es la frontera de holdout y queda intacta.

## 2. Por qué

`power_planning.sessions_for_80pct_2_5_ticks = 133` y el universo de 3 contratos daba **115**.
El spec preveía ese caso con `if_G_lt_133 → attach_P1_UNDERPOWERED_FOR_2P5T`: correr igual, con
la etiqueta puesta.

**Correr sub-potenciado tiene un costo asimétrico.** Con 74,4 %, un no-pass no distingue «no hay
efecto» de «no lo pude ver» — y como la corrida gasta multiplicidad y no se repite, ese
resultado ambiguo sería definitivo. Ampliar hacia atrás cuesta un export y sube la potencia a
85,2 %.

## 3. La cadena, con los cuatro rolls determinados por la regla congelada

`universe.continuous_rule`: dos sesiones consecutivas con mayor volumen del sucesor, roll
efectivo la sesión siguiente, monótono, un contrato por sesión.

```
20251126   12-25 -> 02-26    vol      7.545  vs   167.294    22x
20260129   02-26 -> 04-26    vol     10.737  vs   535.108    50x
20260330   04-26 -> 06-26    vol          0  vs   145.613     -
20260528   06-26 -> 08-26    vol          0  vs   133.692     -
```

| contrato | sesiones | desde → hasta |
|---|---:|---|
| GC 02-26 | 44 | 2025-11-26 → 2026-01-28 |
| GC 04-26 | 42 | 2026-01-29 → 2026-03-27 |
| GC 06-26 | 42 | 2026-03-30 → 2026-05-27 |
| GC 08-26 | 24 | 2026-05-28 → 2026-06-30 |
| **TOTAL** | **152** | **2025-11-26 → 2026-06-30** |

### 3.1 GC 12-25 entra como referencia de roll, no como universo

Las 64 sesiones de GC 12-25 anteriores al 2025-11-26 **quedan excluidas**. Su atribución de
front month no es determinable: haría falta GC 10-25 o GC 08-25 para aplicarles la regla, y no
los hay.

**El universo arranca en el primer roll que la regla determina.** Así la cadena es rule-based de
punta a punta, sin ningún umbral elegido a mano. GC 12-25 se descarga y se conserva sólo para
fijar ese primer roll.

Incluir las 64 daría 216 sesiones y 94,8 % de potencia — **se rechaza**: cambiar 9,6 puntos de
potencia por 64 sesiones cuya asignación de contrato es arbitraria es exactamente el tipo de
canje que el pre-registro existe para impedir.

---

## 4. ⚠ Corrección: la regla de roll **sí se puede aplicar**

`PARIDAD_JUNIO_GC0826_2026-08-23.md` §4.1 afirmó que la regla congelada era **inaplicable** —
que el sucesor ganaba una sola vez, el último día del predecesor— y propuso una enmienda por
razón de volumen ≥ 10×.

**Falso, y se retira.** El error fue usar **fecha de calendario UTC** como unidad de sesión en
vez de **sesión CME**, el mismo error que produjo el conteo de 133. Con la unidad correcta la
regla dispara limpio en los **cuatro** bordes.

⇒ **La enmienda de roll propuesta en §4.1 queda retirada. `continuous_rule` se mantiene como
está.** Lo único que se enmienda es el universo.

---

## 5. Lo que hay que rehacer

La cadena vieja no era sólo más corta: tenía **rolls distintos** (GC 04-26 arrancaba el
`20260120`, ahora el `20260129`). Así que los dos análisis target-free ya corridos quedan sobre
un universo que ya no es el vigente:

| análisis | estado | motivo |
|---|---|---|
| paridad Puerta 0 | **vale** | es identidad de implementación, no depende del universo |
| **B-9 contexto** | **rehacer** | corrido sobre 115 sesiones y rolls viejos |
| **capacidad N_RAND** | **rehacer** | ídem |

El código y el caché ya están (`tools/bt2_absorption_b9_context.py`,
`tools/bt2_absorption_nrand_capacity.py`), así que es correr, no escribir.

**Ninguno de los dos abre outcomes.**

---

## 6. Estado

```
UNIVERSO            ENMENDADO: 5 contratos, 152 sesiones, 2025-11-26 -> 2026-06-30
                    (research_end_inclusive intacto)
ROLLS               4/4 determinados por la regla congelada. Enmienda de roll RETIRADA.
POTENCIA            85,2% vs 2,5 tk   |   63,9% vs efecto legacy +0,053
P1_UNDERPOWERED     SE CAE
PUERTA_0            SIGNED + precondicion de junio SATISFIED
B9                  A REHACER sobre el universo nuevo
NRAND_CAPACIDAD     A REHACER sobre el universo nuevo
OUTCOMES            NOT_OPENED
```

---

## Aporte al referente

El universo pasa de 115 a 152 sesiones y la potencia de 74,4 % a 85,2 %, con la decisión tomada
**antes** de mirar un solo resultado y documentada con fecha. `P1_UNDERPOWERED_FOR_2P5T` se cae,
así que el resultado de Puerta 1 va a ser interpretable en las dos direcciones — que era la
única razón para hacer esto.

Y la cadena queda **rule-based de punta a punta**: los cuatro rolls salen de la regla congelada,
ninguno de un criterio inventado sobre la marcha. Eso costó descargar un contrato que no entra
al universo.

## Nota de método

Se rechazó la opción de 216 sesiones (94,8 % de potencia) porque 64 de ellas tienen atribución
de contrato arbitraria. **Más potencia no es mejor si se compra con una decisión discrecional
dentro de un pre-registro** — el punto del pre-registro no es maximizar la potencia, es que
nadie pueda elegir después.

Y otra vez: el error de la regla de roll —octavo del día— apareció al **cambiar la unidad de
medida**, no revisando el argumento. Es el mismo que produjo el conteo de 133. Un solo error de
unidad, dos conclusiones equivocadas, ninguna detectada por relectura.
