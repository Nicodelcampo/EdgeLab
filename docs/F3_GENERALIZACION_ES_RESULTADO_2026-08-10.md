# F3 — generalización a ES · RESULTADO

**Fecha** 2026-08-10 · **Artefacto** `F3_generalizacion_ES__8613ae84003a.json`
**Módulo** `diag/tasa_senales/F3_generalizacion_ES.py`
**Justificación previa** `JUSTIFICACION_POBLACION_GENERALIZACION_ES_2026-08-10.md`
**Outcomes** `false` · **Multiplicidad gastada** cero · **Holdout** intacto
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

**Condición de refutación pre-declarada**: brecha pareada ≥ 23 pp (mitad de la
de 6E, ~47) para «generaliza». Evaluada automáticamente por el propio módulo,
antes de que un humano leyera el número.

---

## Resultado

| | 6E `time:1` | 6E `tick:25` | **ES `time:1`** |
|---|---|---|---|
| REAL tocada | 97,9 % | 98,8 % | **98,2 %** |
| NULO-B tocada | 50,6 % | 51,9 % | **50,3 %** |
| REAL rota | 96,1 % | 97,2 % | **96,7 %** |
| NULO-B rota | 95,4 % | 96,7 % | **95,8 %** |
| brecha tocar (pareada) | 47,07 pp | 46,77 pp | **47,75 pp** |
| sesiones REAL>NULO (tocar) | 201/201 | 201/201 | **201/201** |
| sesiones REAL>NULO (rota) | 80/201 | 103/201 | **99/201** |

**`CONDICION DE REFUTACION: GENERALIZA`** — declarado por el propio módulo,
sin intervención posterior.

---

## Por qué esto importa más que la réplica de `tick:25`

`tick:25` cambiaba la construcción de la barra dentro del **mismo mercado**
(6E). ES es una **clase de activo distinta** — índice de renta variable, no
FX — con microestructura, horario de liquidez y participantes diferentes. Que
la brecha pareada caiga en **47,75 pp**, prácticamente el mismo número que las
otras dos mediciones independientes, es la tercera confirmación convergente
del mismo efecto bajo condiciones cada vez más distintas entre sí.

El patrón «tocar sí, romper no» también se sostiene: rota está a 0,9 pp
(pareada) igual que en 6E y `tick:25`, con la sesión ganadora dividida casi a
la mitad (99/201) — la resistencia sigue sin distinguir a lo real de lo
aleatorio, en ningún mercado probado hasta ahora.

---

## Qué NO establece

No es paridad NT8 para ES — este módulo, igual que `tick:25`, es evidencia
interna Python. No se corrió sobre NQ ni YM (quedan en la cola, con catálogo y
parquet ya listos). No toca outcomes ni el holdout.

---

## Aporte al referente

Tercera réplica independiente del hallazgo central de la sesión, la primera
que cruza clase de activo. Con tres confirmaciones convergentes (6E `time:1`,
6E `tick:25`, ES `time:1`) la hipótesis de que BigTrap2 identifica niveles de
atracción dejó de depender de un mercado o una resolución de barra particular
— es, hasta donde se probó, una propiedad más general del objeto.
