# DeltaSweep NQ en la cadena estándar — pre-registro (2026-11-14)

Estado: VIGENTE. Etapa EF2 (exploratorio). North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345.

## Antecedente (registrado retroactivamente)
Nico corrió DeltaSweep NQ en Kaggle el 13-nov (cuenta nicolasbuttaro: `edgelab-deltasweep-nq-291s`, `-v4-focalizado`,
`-lim-flecha-secuencias-nq-291s`; 291 sesiones, réplica desde 2026-04-01) fuera del contador: 6.344 + 108 + 2.075 = **8.527 celdas**,
ahora registradas en `TRIAL_REGISTRY_GLOBAL.jsonl` (familia DELTASWEEP_NQ). Resultado: 0 nominadas por FDR q 0,10 en las tres;
walk-forward −0,046 R (157 op.) y −0,10 R (30 op.); disparo crudo plano a 30/60/180 s (49 % aciertos). Las mejores celdas de réplica
eran secuencias (2 o 3 disparos seguidos, misma dirección) — pero se ORDENARON por réplica, así que esa réplica ya no es limpia.
Código: `edgelab/research/deltasweep_nq.py` (copiado sin cambios del output del kernel, sha del código 91797121…).

## A. DELTASWEEP-SEQ (`edgelab/research/deltasweep_seq.py`)
Disparo (compuerta V4 ancho / V4 estricto / absorción, spread ≤ 2 ticks) × secuencia (suelto, 2 seguidos ≤ 60 s, 2 seguidos ≤ 600 s,
3 seguidos ≤ 600 s) × régimen (NY 09:30–12:00 / 09:30–16:00) = 24 definiciones; control = el disparo suelto. Entrada a mercado en la
vela M1 siguiente, a favor del disparo; brackets fijos 160/160, 160/320, 200/400, 80/160 ticks. NQ, DESC y REP. Motor único, R neto.

## B. LUXIMB-AMARILLA-DS (`edgelab/research/luximb_amarilla_ds.py`)
Contexto: la regla viva de LUXIMB-AMARILLA (ctrl|W2|e2|DESPUES). Entrada en el primer disparo DeltaSweep a favor dentro de 30 o 120 min
(V4W, V4S, absorción, o 2 seguidos V4W) en vez de al cierre; control = entrada al cierre («base»). Objetivo 50 % / 75 %, stop en el
extremo. Sólo NQ. El holdout de la familia LUXIMB_AMARILLA ya se usó: B se juzga en desarrollo y forward.

## Justificación económica
Un barrido de delta que fracasa (flip con recuperación del nivel) marca agresores atrapados; dentro de un contexto que ya predice el
regreso, debería mejorar el precio de entrada o filtrar los regresos que no siguen.

## Cómo podría refutarse
A: las secuencias no superan al disparo suelto ni al nulo de la búsqueda en R neto, en DESC y REP. B: entrar con el gatillo no mejora
el R neto ni la tasa de stops frente a «base» (mismo contexto) en los dos períodos.

## Riesgos y datos faltantes
Secuencias y brackets sugeridos por una búsqueda ya mirada (incluida la réplica): el veredicto final exige forward. El motor es M1:
entra en la vela siguiente al disparo, no al tick (más conservador que su corrida). USATECH no tiene bid/ask: sólo NQ.
