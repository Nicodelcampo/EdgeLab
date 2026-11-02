# Hallazgo: `areas_expansion.disparos` miraba el futuro (familia U1 completa) — 2026-11-02

Estado: VIGENTE. Lo encontró la sesión en la nube al portar U1-CRUZADO a JForex, a pedido de Nico. Referente: `docs/NORTH_STAR.md`.

## Qué pasa
Al empezar cada ciclo de alejamiento y regreso sobre un área, `disparos` calcula `ok = A >= H` sobre **todas las velas hasta el fin
del área** (`fin`, hasta 500 minutos adelante). Si ese lado nunca se aleja 1·H, hace `break` y descarta el área entera. Eso incluye
los ciclos posteriores del otro lado, aunque sus disparos ocurran **antes** de que se sepa que el primer lado no iba a alejarse.

En vivo eso no se puede saber. La versión causal, `areas_expansion.disparos_causales`, reinicia el ciclo cuando el precio vuelve
adentro antes de alejarse, y nunca corta el área por lo que va a pasar después.

## Prueba
- **Sintético** (`tests/research/test_u1_cruzado_papel.py`): los disparos de investigación son siempre un subconjunto de los
  causales. Faltaba el 19 % (668 de 3.510 en 180 días sintéticos).
- **U1-CRUZADO real** (kernels `u1_cruzado_causal`; resultados en `docs/research/cartera_20261101/u1_cruzado/causal_*.json`).
  Regla congelada E1A/T3/S3 con tope de 3×; puntos de NQ netos de fricción:

| Período | Causal (operable) | Investigación | Disparos que ocultaba |
|---|---|---|---|
| DESC ago-25 → mar-26 | 64 ops, **+4,4** por op (p por sesiones 0,31) | 52 ops, +21,3 | 12 ops, **−68,7** por op, 2/12 ganadoras |
| Réplica abr → sep-26 | 109 ops, **+15,6** por op (p 0,026) | 92 ops, +27,3 | 17 ops, **−48,1** por op, 6/17 ganadoras |

**Los disparos ocultos eran casi todos perdedores.** Tiene sentido: el área se cortaba justamente cuando el precio no volvía a
alejarse hacia el otro lado, y eso es lo que pasa cuando la operación hacia el área sale mal. El backtest de U1 operaba un
subconjunto elegido con el resultado.

## Alcance
- **Afectada:** toda familia que pase por `u1_indaga.disparos` → `areas_expansion.disparos`:
  - U1 / AREAS-EXP-1;
  - U1-CRUZADO;
  - U1-ES/YM-GRILLA y U1-ORO-GRILLA;
  - U1-ZONAS (AVCL, BT2, HFT, LUX) y U1-RACIMOS.

  Eso incluye **5 de las 7 reglas de la canasta del holdout**: U1-ZONAS-AVCL-NQ, U1-ORO, U1-RACIMOS-NQ, U1-YM y U1-ZONAS-NQ.
- **No afectadas por este mecanismo:** CVGAP (código propio) y las familias de rango, PRERANGE, ASIA y OTR930. Esto no es una
  auditoría de esas familias.
- **El holdout de U1-CRUZADO** del 2026-11-02 (18 ops, +25,8) se corrió con la versión de investigación. **No vale como estimación
  de lo operable.** Rehacerlo con la versión causal sobre la misma ventana es una segunda mirada a esas sesiones: lo decide Nico.
- **Por qué el chequeo de causalidad no lo vio:** `indicadores.causal` compara contra prefijos del contexto, y en los datos de
  prueba casi nunca se da el caso del corte con reinicio. Queda cubierto con un test específico.

## Qué se hizo
- `disparos_causales` y el parámetro `causal=` en `u1_indaga.disparos`, `u1_cruzado.senales` y `u1_cruzado.operar`. Los dos tienen
  `False` por defecto para no cambiar nada de lo medido sin decidirlo.
- La ficha de papel U1-CRUZADO pasa a la versión causal (`edgelab/research/u1_cruzado_causal.py`). Sus cotas y `mu_util` salen de
  las operaciones causales de desarrollo: 173 ops, `mu_util` 2,19, `sd_desarrollo` 77,0.
- El port a JForex implementa sólo la versión causal.

## Pendiente (decisión humana)
1. Cambiar el valor por defecto a `causal=True` en toda la familia U1 y re-medir. La canasta de 7 no se abre con U1 en versión de
   investigación.
2. Decidir si se rehace el holdout de U1-CRUZADO con la versión causal.
