# HFTV4-RETORNO — ¿el precio vuelve a las zonas HFT de las que se alejó? — manifiesto — 2026-10-06

Pedido de Nico: "esté validada la paridad o no, aplicá el indicador al MNQ y medí si estas zonas sirven para ganarle al
azar; veo que el precio suele retornar a ellas". Hash NORTH_STAR:
`ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. Información (probabilidad de retorno), **no P&L**.

## Indicador
`edgelab/bridge/indicators/hftzones_nq.py` (port de `HFTZonesNQPureV4`, paridad HP-007 V2 5.438/5.438 en NQ).
- Umbrales: `ACCEPT_DEFAULTS` (los certificados). Pueden diferir de los del chart de Nico; se declara.
- Familia **propia (HFTV4)**: no se transportan resultados de AVCL ni VTD.

## Evento (la flecha nueva, misma lógica que el `.cs`)
Sobre barras de 50t de MNQ (6 contratos, 2025-07 → 2026-09, sesiones aprobadas, RTH, holdout no leído):
1. Zona = barrido aceptado. Disponible desde la primera barra que cierra después de `ts_avail`.
2. Se excluyen las **V**: el último precio del barrido retrocedió ≥ 50 % de la altura desde el extremo.
3. **Flecha** = primera barra en que el precio queda a ≥ 3 alturas de la zona (por arriba o por abajo) **sin haber
   tocado antes los dos bordes**. Dirección = la del alejamiento. Ventana de búsqueda: 2.000 barras, dentro de la sesión.
4. Todo es causal: se decide con barras ya cerradas.

## Nulo: pseudo-zonas con la misma regla
- Barras al azar de la misma franja de 30 min. A cada una se le asigna la **altura y la dirección** de una zona real de
  esa franja, con el borde extremo en el close (como termina un barrido).
- Se les aplica la **misma** regla de V (no aplica), alejamiento y flecha.
- 3 pseudo-zonas por zona real.

## Resultados (desde la barra de la flecha)
- **Retorno:** el precio vuelve a tocar el borde cercano de la zona dentro de T barras (misma sesión), con
  T ∈ {50, 200, 1.000}.
- **Relleno:** el precio llega al borde lejano (recorre la zona entera).
- **Excursión en contra antes del retorno** (en alturas), y tiempo hasta el retorno: descriptivos, insumo para las
  lógicas de entrada de Nico.

## Estimador
β de zona real contra pseudo-zona en un modelo lineal de probabilidad, con FE (franja, tercil de amplitud, decil de la
distancia en ticks al borde en el momento de la flecha) y SE por sesión. Bilateral.

## Pruebas formales (4, Holm)
P(retorno) con T = 200 y T = 1.000; P(relleno) con T = 200 y T = 1.000.

## Justificación económica
Si los barridos HFT dejan liquidez pendiente o niveles que el mercado vuelve a testear, el precio volvería a la zona más
que a una banda cualquiera a la misma distancia. Eso habilita entradas de reversión hacia la zona.

## Cómo podría refutarse
P(retorno) real ≈ P(retorno) pseudo, con el MDE publicado: el retorno que se ve en el chart sería la probabilidad de
cruce de cualquier nivel cercano (el precio vuelve a casi todo), no algo propio de la zona.

## Lecciones aplicadas
Sin ventanas pasadas como denominador. Grupos de comparación definidos **sólo con el pasado**: la pseudo-zona usa
exactamente la misma regla causal.
