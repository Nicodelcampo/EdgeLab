# Replicacion ORB0100 en NQ abr-sep 2026 — preregistro (escrito ANTES de correr)

OK de Nico 2026-10-21 ("si, corre la replicacion en NQ"). Una sola corrida para la familia ORB0100 (HOLDOUT-A3).
Regla congelada (= celda de partida, `tools/orb0100/orb0100_v2.py`, funciones `senales`/`operar`): rango 01:00-01:15 ET,
primera vela de 5 min que cierra fuera, a favor del VWAP de sesion, entrada a mercado al cierre +1 tick, SL otro lado del
rango (+1 tick), TP 1,5R, cierre forzado 16:00 ET, costos MNQ ($1,24 RT; 0,62 pts) — tambien se informa con costos NQ.
Datos: NQ release v4, contratos 06-26 / 09-26 / 12-26, sesiones 2026-04-01 .. 2026-09-25 (ultimo dato disponible).
Criterio: **CONFIRMA** si media neta (pts/op, MNQ) > 0 y limite inferior del IC 95 % (bootstrap) > 0; **REFUTA** si media <= 0;
si no, NO_CONCLUYENTE. Nada se ajusta despues.

## Resultado (2026-10-21)
n = 92, acierto 45,7 %, **+6,85 pts/op neto MNQ** (IC 95 % [-6,7, +20,7]), PF 1,26, max DD $678 (MNQ); con costos NQ +7,24.
Por mes: abr +4,7, may +4,3, jun +11,3, jul +16,1, ago +4,8, sep -4,3. **Veredicto: NO_CONCLUYENTE** (media > 0, IC incluye 0).
Lectura: positiva en los tres tramos de NQ (IS 2025 +5,5; OOS 2026T1 +15,4; replicacion +6,8), ninguno significativo solo;
no transporta a otros activos (V2). Replicacion de la familia ORB0100 consumida. Queda el holdout (>= 2026-10-01).
