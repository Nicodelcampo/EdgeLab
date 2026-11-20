# DeltaSweep NQ — medido y no medido

Estado: VIGENTE (2026-11-14). Pre-registro: `PREREGISTRO.md`. Exploración: `EXPLORACION.md`, `amarilla/EXPLORACION.md`.

## MEDIDO
| Fecha | Qué | Resultado |
|---|---|---|
| 2026-11-14 | A. DELTASWEEP-SEQ en la cadena estándar (NQ, entrada M1 siguiente, R neto) | Mejor forma: 2 disparos V4 ancho seguidos ≤ 600 s en NY 09:30–12:00, 160/320 ticks: DESC +0,26 R (n 82), REP +0,28 R (n 65); disparo suelto (control) +0,04 / +0,03. Con VWAP en contra: +0,58 R (n 51, t 2,75). **Ninguna celda supera el p95 del nulo de la búsqueda** (t 3,44–3,55) en ningún corte. Absorción (V2A) negativa en todo. V4 estricto con secuencia: n chico. La réplica no es limpia (las secuencias se eligieron mirando REP en las corridas del 13-nov). |
| 2026-11-14 | B. LUXIMB-AMARILLA-DS: gatillo DeltaSweep dentro de la caja amarilla | Base (entrar al cierre) ≈ 0 en este corte (−0,01 DESC / +0,01–0,02 REP). El gatillo no mejora en DESC (V4W −0,03 a −0,12; V4S −0,10 a +0,03) y sólo V4S mejora en REP (+0,12 a +0,20, n 17–54). Nada sobre el nulo. Sin efecto consistente. |
| 2026-11-14 | C. DELTASWEEP-PAT v2: patrones de 2–5 disparos (PERM/V4W/V3/V5 × gaps 10/30/60/300 s × dispersión dp/dt 8/16/32 ticks o escalera × NY AM/RTH × 7 entradas/salidas; ≈ 79.000 celdas) | **Ninguna celda sobre el p95 del nulo** en ningún corte (t máx 2,6–3,3 contra 4,1–4,2). Forma (160/320, todos los filtros, R neto medio ponderado): en DESC todo ≈ −0,04 a −0,12 R y **empeora con n** en PERM y V3; en REP mejora levemente con n = 3–4 (+0,03 a +0,07) pero no replica DESC. Dispersión: dt8 es la menos mala en REP (+0,05) y nada en DESC (−0,04); el tiempo entre disparos no ordena nada. V5 con n 4–5 positivo pero con 64–312 operaciones solapadas. **Refutada la hipótesis de patrón** (criterio del pre-registro: nada pasa y no hay forma monótona). Más casos dieron potencia y confirmaron el nulo. |

## NO MEDIDO
- Forward de V4W|S2g600|AM (congelar y seguir en sesiones nuevas): es la única forma con signo y magnitud parecidos en DESC y REP.
- Entrada al tick (límite en la flecha) en lugar de la vela M1 siguiente.
