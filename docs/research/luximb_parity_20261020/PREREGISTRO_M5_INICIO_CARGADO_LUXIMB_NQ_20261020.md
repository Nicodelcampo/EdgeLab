# Preregistro M5 — vuelta al inicio cargado (LUX-IMB, NQ, descubrimiento)

Estado: PRE-REGISTRADO antes de mirar. OK de Nico 2026-10-20 ("si, medi M5").
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Datos: descubrimiento HOLDOUT-A3, NQ 09-25 / 12-25 / 03-26 / 06-26 (hasta 31-mar-2026). Diseno hecho mirando NQ 09-26
(replicacion): replicacion no disponible; confirmacion, si hubiera, solo en holdout.

- **T:** `luximb_impulsos.py --modo inicio --p-rango 60 --min-ini 3 --share-ini 0.5 --rango-min-abs 60 --ctrl-modo amplitud`
  (umbrales causales por contrato, calentamiento 500).
- **C:** impulsos nunca marcados que alcanzan la misma amplitud (>= max(p60 causal, 60 pts)); se fijan en la primera vela
  que la alcanzan, cualquiera sea su reparto de zonas.
- Desenlace desde el cierre de la vela de marca, velas 25t, tope 240 min / fin de sesion: Tg = X - 0,75·R·s (borde del
  25 % inicial) vs Ex = X + 0,25·R·s; ambas en la misma vela -> Ex. P&L fade (objetivo Tg limite, stop Ex +1 tick, tiempo
  +1 tick, entrada al cierre con 1 tick, $4,50 RT) y continuacion (espejo). Sensibilidad 0/1/2 ticks.
- Hipotesis (6, Holm; bootstrap por dia NY 10.000): H1 P(Tg) T - C > 0; H2 P&L fade T > 0; H3 P&L continuacion T > 0;
  H4 H1 por direccion; H5 H1 cash 9:30-11 vs resto; H6 H1 T con resto vacio / no vacio vs C. (H4-H6: menor p del par x2.)
  MDE80 de H1 publicado. Canal no direccional: MFE/MAE en R a 60 min.
- Justificacion economica: el tramo inicial con muchos desequilibrios es precio "sin terminar de negociar"; si el
  mercado vuelve a buscarlo y el camino de vuelta esta limpio, deberia volver mas seguido que en un impulso igual sin ese inicio.
- Como podria refutarse: H1 sin diferencia con MDE <= 10 pp, o P&L neto <= 0 tras costos.
