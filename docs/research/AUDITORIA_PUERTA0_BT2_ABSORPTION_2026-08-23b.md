# Auditoria Puerta 0 (segunda) — 2026-08-23

**Commit**: `71c80bd` · **files[]**: 4 (JSON, kernel, harness, visor).
**No se toco holdout. No se midieron outcomes.**

## Lo que mejoro

Chat, mensaje del commit, JSON y `visor_server.py` **dicen lo mismo**.
Veredictos salen de `matched == total`. El harness llama a `run()`.
`tested_params.ScoreMode = AbsDirectional` (el del export). El headline
AbsMagnitude queda declarado aparte. Eso cierra el defecto P-34 de `bb13d8c`.

## Veredicto

**Puerta 0 sigue FAIL.** Correctamente rotulada.

Los porcentajes del JSON son reales respecto del emparejamiento que corrio.
Ese emparejamiento **no mide** si el kernel reproduce una cubeta del `.cs`.

## El 2,39 % no es la aritmetica

`verify_layer_parity.py` hace dos cosas que rompen la identidad de cubeta:

1. Corta el export NT8 con `iso_ts >= "2026-08-17T03:00:00"`. Los timestamps
   del CSV estan en ART (arranca `2026-08-16T19:00:03`). La cinta arranca
   `2026-08-17 03:00:00` UTC = `00:00` ART. El corte trata ART como UTC y
   tira las primeras ~3 h del lunes. Por eso `uncovered` paso de 714 a **968**.
2. Despues compara `py_scores[i]` contra `covered_nt8_scores[i]` por indice.
   Python empieza al primer tick de la cinta; NT8 filtrado empieza 3 h despues.
   Son cubetas distintas. `signed_flow` 646/27.074 es el ruido de ese desfase.

Ayer, siguiendo `t_start` con offset 3 h, `signed_flow` y `d_ticks` dieron
27.328/27.328 sobre la misma cinta y el mismo CSV
(`PARIDAD_BT2_ABSORPTION_2026-08-22.md`). La matematica de cubeta **ya se
midio exacta** cuando el ancla es el timestamp. Este FAIL no la refuta.

## Zonas y fills, sobreestimados

Zona: match por `lo/hi/vol/side` contra **cualquier** zona NT8 del rango, sin
tiempo. Fill: `side + fill_px`, sin `signal_at`. 569/610 y 571/610 no son
identidad de evento. El chat dice que el parser indexa por `created_bar` /
`fill_at`; el codigo no lo usa para el match.

## Que falta (sigue siendo Puerta 0, no junio)

Emparejar por `t_start` (o timestamp de `BARRA_PROCESADA`) con el offset ART/UTC
ya medido. Recien ahi el `signed_flow` del `run()` es comparable. Si despues de
alinear sigue en 2 %, ahi si el kernel esta roto.
