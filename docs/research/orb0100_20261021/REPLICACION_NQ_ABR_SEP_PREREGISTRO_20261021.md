# Replicacion ORB0100 en NQ abr-sep 2026 — preregistro (escrito ANTES de correr)

OK de Nico 2026-10-21 ("si, corre la replicacion en NQ"). Una sola corrida para la familia ORB0100 (HOLDOUT-A3).
Regla congelada (= celda de partida, `tools/orb0100/orb0100_v2.py`, funciones `senales`/`operar`): rango 01:00-01:15 ET,
primera vela de 5 min que cierra fuera, a favor del VWAP de sesion, entrada a mercado al cierre +1 tick, SL otro lado del
rango (+1 tick), TP 1,5R, cierre forzado 16:00 ET, costos MNQ ($1,24 RT; 0,62 pts) — tambien se informa con costos NQ.
Datos: NQ release v4, contratos 06-26 / 09-26 / 12-26, sesiones 2026-04-01 .. 2026-09-25 (ultimo dato disponible).
Criterio: **CONFIRMA** si media neta (pts/op, MNQ) > 0 y limite inferior del IC 95 % (bootstrap) > 0; **REFUTA** si media <= 0;
si no, NO_CONCLUYENTE. Nada se ajusta despues.
