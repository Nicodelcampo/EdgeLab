# Resultado ES-ESCALONADAS, descubrimiento feb-2026 (2026-09-30)

Manifiesto `MANIFIESTO_ES_ESCALONADAS_OUTCOMES_20260930.md` (OK de Nico) · runner `tools/es_escalonadas_outcomes.py`
(commit `c81b25f`, anterior a la corrida) · salida `es_escalonadas/resultado_202602.json`. Replay tick a tick sobre
22,8 M operaciones NT8 de ES 03-26 (22 sesiones; velas 25t verificadas contra el bundle), bid/ask, comisión 0,40 ticks.

## Resultado
- **R neto negativo en las 32 celdas** (−0,12 a −0,42 R por operación). **R bruto también negativo en las 32**
  (−0,03 a −0,29): con riesgos de 3–5 ticks, cruzar el spread en la entrada y en el stop ya consume ≈ 0,3 R.
- Contra el control emparejado (t crítico max-T 3,26): **confirmación por velas: 0/16** (dif. −0,01 a +0,07 R).
  **Confirmación por precio: 6/16 sobreviven** (planas T4/T8/T12/T16 con stop +1 y T4/T8 con stop +2; empinadas T8 +1),
  dif. +0,10 a +0,27 R, con n de 900 a 2.700 y 20 sesiones.

## Lectura
1. **No hay edge operable:** ninguna variante gana dinero ni en bruto. Una diferencia positiva contra un control que
   pierde más no es rentabilidad.
2. **Los 6 «sobrevivientes» probablemente no son de la zona sino de la mecánica de entrada.** Las mismas zonas con
   entrada por velas no se separan del control; sólo la entrada por stop (esperar que el precio ya se mueva 2 ticks a
   favor) lo hace, y el control entra a mercado en una vela al azar. **Falla de diseño del control, escrita ahora:**
   para la confirmación por precio el control debió usar la misma mecánica (vela al azar, orden stop a 2 ticks en la
   dirección elegida). Sin ese control, los 6 no se pueden atribuir a la escalera. No se promueven.
3. Por eso **no se abre la réplica de marzo**: no hay nada operable que replicar y los sobrevivientes están
   contaminados por el control. Marzo sigue sin mirar.
4. Para lo que viene: el filtro de tendencia (pedido de Nico) no puede convertir un R bruto negativo en positivo si el
   problema es el costo relativo al stop; cualquier variante nueva necesita riesgos mayores (menos peso del spread) y un
   control con la misma mecánica de entrada. Todo eso es un pre-registro nuevo.
