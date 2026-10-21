# Preregistro — GC nocturno (ORB-HORARIOS), datos no mirados abr-jun 2026 (escrito ANTES de construir/correr)

Pedido de Nico 2026-10-21: "proba GC nocturno con datos no mirados". Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Origen: pista descriptiva de ORB-HORARIOS (no paso BH): en GC, ventanas 22:30-02:30 ET positivas en descubrimiento.
Datos: GC release v4, contratos 06-26 y 08-26, **sesiones 2026-04-01 .. 2026-06-30** (nunca miradas por ninguna familia de GC
con desenlaces). Jul-sep 2026 de GC = holdout segun CLAUDE.md ("los demas instrumentos siguen hasta el 30-jun"): NO se toca.
Reglas identicas a `tools/orb0100/orb_horarios.py` (rango de 15 min, primera vela de 5 min que cierra fuera, mercado +1 tick,
SL otro lado, salida a 6 h o 16:55 ET; R0 = TP 0,5R sin filtro; R1 = TP 1,5R + VWAP; costos GC $4,50 RT, tick 0,1).
- **H1 (primaria)**: racimo nocturno = ventanas 22:30, 23:00, 23:30, 00:00, 00:30, 01:00, 01:30, 02:00, 02:30 ET x {R0, R1}
  (18 celdas); media de R por operacion de todas sus operaciones, bootstrap por dia (10.000). CONFIRMA si IC 95 % > 0;
  REFUTA si media <= 0; si no, NO_CONCLUYENTE.
- Secundarias (descriptivas): las 4 celdas destacadas en descubrimiento: 01:00 R0, 23:00 R1, 02:30 R1, 22:30 R1.
Nada se ajusta despues; si confirma, la siguiente prueba es el holdout GC jul-sep, una vez.

## Resultado (2026-10-21) — `RESULTADOS_GC_NOCTURNO.json`, `tools/orb0100/gc_nocturno.py`
- **H1 racimo nocturno: -0,028 R/op** (948 operaciones, 64 sesiones), IC 95 % [-0,110, +0,057] -> **REFUTA** (media <= 0).
- Destacadas en descubrimiento, ahora: 01:00 R0 -0,12; 23:00 R1 -0,02; 02:30 R1 -0,13; 22:30 R1 -0,10 (todas negativas).
- Por mes: abr -0,10, may -0,04, jun +0,06. Por celda: 9 de 18 negativas, las positivas sin patron (00:00 R1, 02:00 R1 ~+0,21).
Lectura: la pista de GC nocturno era ruido del barrido (lo esperable con 704 celdas). Cerrada. Holdout GC jul-sep intacto.
