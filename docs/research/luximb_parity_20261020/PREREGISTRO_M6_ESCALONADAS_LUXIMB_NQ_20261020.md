# Preregistro M6 — ruptura de escalonadas 150t sobre area cargada de OG/VI (NQ, descubrimiento)

Estado: PRE-REGISTRADO antes de mirar. OK de Nico 2026-10-20 ("si, medi M6").
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Datos: descubrimiento HOLDOUT-A3, NQ 09-25 / 12-25 / 03-26 / 06-26 (hasta 31-mar-2026), release v4. Diseno mirando NQ 09-26
(replicacion): replicacion no disponible para esta familia.

- Detector: `luximb_escalonadas.py --ticks 150 --max-step 42 --min-pull 14 --conf 16 --min-zonas 0` (todas).
  **T** = zonas_area >= 3; **C** = zonas_area 0-2 (misma configuracion de escalonada).
- Entrada: cierre de la vela 150t de deteccion (E), +1 tick de slippage; la carrera arranca en la primera vela 25t posterior
  al final de esa vela 150t (conservador: no se usa el interior de la vela de deteccion).
- Barreras: techo (H): ruptura = precio <= area_lo; rechazo = precio >= ultimo pico conocido + 1 tick. Piso (L) espejado.
  Ambas en la misma vela 25t -> rechazo. Si E ya esta mas alla de la ruptura: ruptura inmediata en E. Tope 240 min o fin de sesion.
- P&L: seguir la ruptura (objetivo = barrera de ruptura, limite; stop = barrera de rechazo +1 tick; tiempo -> ultimo cierre
  +1 tick) y su espejo (rechazo). $4,50 RT (0,225 pts). Sensibilidad 0/1/2 ticks. MFE/MAE a 60 min en unidades del area.
- Hipotesis (6, Holm; bootstrap por dia NY 10.000): H1 P(ruptura) T - C > 0; H2 P&L seguir ruptura T > 0; H3 P&L rechazo
  T > 0; H4 H1 techo / piso; H5 H1 cash 9:30-11 / resto; H6 H1 con T de densidad (zonas/10 pts) >= / < mediana de T, vs C.
  (H4-H6: menor p del par x2.) MDE80 de H1 publicado.
- Justificacion economica: una escalonada que se apoya en un area llena de desequilibrios sin negociar estaria absorbiendo
  ordenes; al agotarse, la ruptura deberia ser mas probable que en una escalonada sobre area limpia.
- Como podria refutarse: H1 sin diferencia con MDE <= 10 pp, o P&L neto <= 0 tras costos.
