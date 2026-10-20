# Resultados M6 — ruptura de escalonadas 150t sobre area cargada (LUX-IMB, NQ, descubrimiento)

Estado: MEDIDO. Veredicto: **SIN EFECTO A FAVOR** (Holm 1,0 en las 6). Preregistro
`PREREGISTRO_M6_ESCALONADAS_LUXIMB_NQ_20261020.md` (commit `2ef3c810`, antes de mirar). Codigo `luximb_m6.py`, eventos
`RESULTADOS_M6_NQ_eventos.csv`, escalonadas `desc_m6/`.

| grupo | n | dias | P(ruptura) | P(rechazo) | P&L seguir ruptura 0/1/2 ticks | P&L rechazo 1 tick |
|---|---|---|---|---|---|---|
| T area con >= 3 zonas | 1.036 | 166 | 0,582 | 0,418 | -0,13 / -0,49 / -0,84 | -0,71 |
| C area con 0-2 zonas | 3.206 | 173 | 0,618 | 0,382 | -0,11 / -0,46 / -0,80 | -0,74 |

| hipotesis | estimacion | IC 95 % (por dia) |
|---|---|---|
| H1 P(ruptura) T - C | **-3,6 pp** | [-7,1, -0,2] |
| H2 P&L seguir ruptura T | -0,49 pts | [-0,90, -0,06] |
| H3 P&L rechazo T | -0,71 pts | [-1,15, -0,30] |
| H4 techo / piso | -4,0 / -3,2 pp | [-8,6, +0,6] / [-8,5, +2,2] |
| H5 cash / resto | +4,2 / -6,8 pp | [-2,4, +10,9] / [-10,9, -2,8] |
| H6 densidad alta / baja | -1,9 / -5,2 pp | [-6,4, +2,6] / [-9,9, -0,6] |

MDE80 de H1 = 4,9 pp (buena potencia: 1.036 vs 3.206).

Lectura:
1. La hipotesis preregistrada (mas ruptura con zonas) **no se sostiene**: el efecto va en contra. Con area cargada la
   escalonada rompe ~3,6 pp MENOS y es rechazada mas. El IC bilateral excluye 0, pero la prueba preregistrada era
   unilateral a favor y la direccion opuesta no estaba pre-registrada: queda como **pista**, no como hallazgo.
2. Economicamente no hay nada: seguir la ruptura y operar el rechazo pierden neto en T y en C (la carrera es corta,
   el costo pesa). Las zonas no cambian el P&L (-0,49 vs -0,46).
3. Por contrato la direccion negativa aparece en 3 de 4 (09-25, 12-25, 06-26 con n=16); 03-26 ~0.
4. Recorrido a 60 min (en unidades del area): MFE p50 0,85 T vs 1,16 C; MAE 0,94 vs 1,25 — con zonas el precio se mueve
   MENOS en ambas direcciones (canal no direccional): el area cargada "frena" el precio.

Alcance: muere "las zonas favorecen la ruptura de la escalonada" para esta configuracion en NQ descubrimiento.
Pista no promovida: "area cargada -> menos recorrido / mas rechazo" (requiere preregistro propio y otra muestra; replicacion
de NQ comprometida; candidata natural ES descubrimiento).

Aporte al referente: descarta la ruptura y deja una regularidad no direccional (menos recorrido sobre zonas) con
potencia buena, que es el primer efecto con IC fuera de 0 en esta familia.
