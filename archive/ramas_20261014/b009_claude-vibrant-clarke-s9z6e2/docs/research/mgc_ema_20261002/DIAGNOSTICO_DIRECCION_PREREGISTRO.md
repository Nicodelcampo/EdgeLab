# MGC EMA — diagnóstico de dirección y concentración (pre-registro, 2026-10-03)

Estado: EXPLORATORIO, sin holdout. Escrito ANTES de correr. Headline congelado: normal, entrada inmediata, SL 200, TP 400, BE off.
Objeto: decidir si el PnL positivo se debe a información direccional de la señal o a deriva/concentración. No se agregan celdas ni se cambian parámetros.

## Pruebas
1. Descomposición long/short del headline (tick-exact).
2. Control de dirección aleatoria: mismas señales y mismos horarios, dirección sorteada (a) i.i.d. por señal y (b) por sesión (se invierte toda la sesión con p=0.5). 2000 sorteos, semilla 20261003. p = P(neto_nulo >= neto_real).
3. Concentración: neto sin el mejor mes; neto sin los 5 mejores días de salida; fracción del neto aportada por el mejor mes.
4. Partición D0/D1/D2 del split del embudo (hash 05e0728d…) y por contrato, tick-exact.

## Reglas de decisión (fijadas antes de ver resultados)
- DESCARTAR direccionalidad si p(a) > 0.05 o p(b) > 0.05.
- DESCARTAR por deriva si un solo lado (long o short) aporta > 100 % del neto, o el lado contrario es <= 0.
- FRÁGIL si el neto sin el mejor mes es <= 0 o sin los 5 mejores días es <= 0.
- Sólo si pasa todo: el headline sigue como candidato para confirmación futura; sigue sin ser edge validado (DSR 0/42, BH 0/42, SPA 0.342).
- Ningún resultado de este diagnóstico abre D2 ni el holdout (trade_date >= 20260401).

## Enmienda 1 (escrita tras ver los resultados 1–4, antes de correr la 5)
Resultados 1–4 (`direction_diag.json`): neto 9.918,5; long +3.645,5 / short +6.273; p(i.i.d.)=0,022; p(sesión)=0,037; sin mejor mes +5.358; sin 5 mejores días +2.345,5; D0 +3.169,5 / D1 +2.004,5 / D2 +4.744,5. Pasan todas las reglas anteriores.
Esos nulos evalúan UNA celda elegida a posteriori como la mejor. Falta corregir por selección:
5. Máximo sobre las 21 celdas normales del grid pre-registrado (SL {100,150,200} × TP {150..450}) bajo dirección sorteada por sesión, 500 sorteos, semilla 20261004. Estadístico = máximo del neto tick-exact entre celdas. p_max = P(max_nulo >= 9.918,5).
Regla: p_max > 0,05 → NO se rechaza que el mejor del grid surja sin información direccional → el edge queda DESCARTADO como evidencia (no confirmado). p_max <= 0,05 → sigue como candidato.

## Resultado de la prueba 5 (reglas aplicadas tal como estaban escritas)
Máximo real 9.918,5; máximo nulo: media 3.113, q95 11.676; **p_max = 0,0998** (500 sorteos; error Monte Carlo ≈ 0,013). Con p_max > 0,05 se aplica la regla: NO se rechaza que el mejor del grid surja sin información direccional. Veredicto: EDGE NO CONFIRMADO / DESCARTADO COMO EVIDENCIA.
