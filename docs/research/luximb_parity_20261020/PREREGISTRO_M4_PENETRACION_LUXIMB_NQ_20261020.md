# Preregistro M4 — penetracion de vuelta dentro del impulso (LUX-IMB, NQ, descubrimiento)

Estado: PRE-REGISTRADO antes de mirar desenlaces. OK de Nico 2026-10-20 ("OK" al manifiesto M4 presentado en chat).
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Mismos eventos que M1-M3 (`desc/imp_NQ_*.json`, v5): T = 330 marcados, C = 2.046 control (<= 2 zonas). Solo descubrimiento.

- A origen, X extremo en la marca, R = |X - A|, s = +1 si sube. Alturas p en {0,25; 0,382; 0,5; 0,618; 0,75}: L_p = X - p·R·s.
- Ventana: velas 25t desde el cierre de la marca hasta 240 min o fin de sesion (hueco > 30 min).
- Toque: primera vela 25t que alcanza L_p. Carrera desde la vela SIGUIENTE: A primero (rebalanceo) vs X primero; si una vela
  toca ambos cuenta X. Sin toque de ninguno al final de la ventana: "tiempo".
- P&L por altura: entrada limite en L_p a favor del rebalanceo, objetivo A (sin slippage), stop X (+1 tick), tiempo -> ultimo
  cierre (+1 tick), comision $4,50 RT (0,225 pts).
- Hipotesis (10, Holm): por altura, Hp_a P(A) T - C > 0 y Hp_b P&L neto T > 0. Bootstrap por dia NY, 10.000, IC 95 %.
  Se publican las 5 alturas, n y MDE80 de cada una. Las alturas se solapan (no son independientes).
- Justificacion economica: si los desequilibrios atravesados se negocian al volver, una vez que el precio se mete en el
  impulso deberia seguir hasta el origen mas que en un impulso sin desequilibrios.
- Como podria refutarse: ninguna altura con Hp_a o Hp_b significativa tras Holm.
