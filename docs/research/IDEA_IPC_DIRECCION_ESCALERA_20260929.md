# IDEA (registrada, NO ejecutada): la escalera de picos del IPC anticipa la dirección de salida — 2026-09-29

**Origen:** Nico, 4 capturas de MNQ 25t (feb-2026) con el IPC híbrido v0.1: piso ×4 con mínimos ascendentes → el precio
sale hacia arriba; techo ×5/×4 con máximos descendentes → sale hacia abajo.
**Hipótesis:** al confirmarse una zona IPC, la carrera «+X ticks en la dirección de la escalera» vs «ruptura del último
pico» se gana más que en momentos al azar emparejados (hora ±30 min, volatilidad previa).
**Justificación económica (a escribir en el pre-registro):** una escalera de picos que no se superan sería absorción
pasiva que cede de un lado; si la liquidez del lado opuesto se agota, la salida sigue la pendiente.
**Cómo podría refutarse:** exceso ≤ 0 contra el control emparejado, o sólo en el canal no direccional.

## Alertas escritas antes de medir
- Las 4 capturas son selección (4 de 14.487 zonas del mes).
- Descriptivo ya visto: 12.209/14.487 zonas (84 %) terminan BROKEN (una mecha supera el último pico = salida en contra),
  pero sobre toda la vida de la zona (≤ 60 velas), no en la carrera desde la confirmación.
- Antecedentes (otra familia/instrumento, no se transportan): pivotes MES barridos como el azar; IPC-NIVEL formación 1/8.
- Con ~700 zonas por sesión el detector v0.1 marca casi cualquier oscilación: **antes del test, bajar la densidad**
  con juicio ✓/✗ de Nico y congelar parámetros (sospechoso principal: `visit_exit_ticks = 14`).

## Condiciones para correrlo
Evento = `available_at` de la confirmación (eventos causales), nunca el dibujo final. Febrero-2026 = descubrimiento;
réplica una sola vez en otro mes. Dos canales (direccional y no direccional) + MDE. Mira outcomes: **manifiesto + OK de Nico.**
