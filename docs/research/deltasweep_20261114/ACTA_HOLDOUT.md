# DELTASWEEP-SEQ — acta de apertura del holdout (2026-11-16)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar. Pedido de Nico (2026-11-16): usar el holdout que ya pasó (desde el 1-oct) en lugar
de semanas de papel. Modo exploratorio (Nico, 2026-11-08). Familia `DELTASWEEP_NQ`, sin aperturas previas (`HOLDOUT_VENTANAS.jsonl`).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5 (confirmación exploratoria).

## Hipótesis congelada (una, sin ajuste)
`docs/research/deltasweep_20261114/CONGELADAS_20261116_eb56b3f0.json` (módulo `edgelab.research.deltasweep_seq`, motor único):
H1 = `V4W|S2g600|AM` · `M_sl1.0_tp2.0_N` · `todos` — segundo disparo V4W a ≤ 600 s del primero, en la mañana; mercado, stop 1, objetivo 2.
Desarrollo (NQ, DESC 2025-08 → 2026-03 + REP 2026-04 → 09): n 147, +0,268 R neto, t 2,35 (DESC +0,26 n 82; REP +0,28 n 65).

## p de desarrollo declarada: 0,5
La celda NO supera el nulo de la búsqueda (p95 del máximo t 3,44; mediana 2,60): su t es típico del mejor por azar. Además la forma se eligió
mirando REP (13-nov). Por eso se declara 0,5 (sin evidencia de desarrollo). Combinación: Fisher (desarrollo, holdout), informativa.

## Ventana: NQ, sesiones selladas desde 2026-10-01 (hasta la última sellada, 2026-11-13); se excluyen las de `SESIONES_EXCLUIDAS_HOLDOUT`
Qué del holdout se miró en este linaje: LUXIMB-AMARILLA (holdout 11-nov) usó filtro `vwapD_lejos_hacia` sobre otra entrada (caja amarilla);
LUXIMB-AMARILLA-DS (gatillo DeltaSweep dentro de la caja) no abrió holdout. Ninguna operación de H1 se miró.

## Potencia (declarada antes)
≈ 0,55 operaciones por sesión → ≈ 15–17 operaciones en ≈ 30 sesiones; desvío de R ≈ 1,4 → error estándar ≈ 0,35 R. **Sin potencia**
para confirmar ni refutar +0,27 R: el resultado da dirección y se registra; la familia queda sin más aperturas y H1 sigue en forward.

## Justificación económica / cómo podría refutarse
Dos barridos de delta seguidos en la mañana marcan un desequilibrio persistente de agresores que el primero solo no confirma; el segundo
gatilla la continuación. Refutación: R neto ≤ 0 en el holdout y en forward con n ≥ 30 operaciones.
