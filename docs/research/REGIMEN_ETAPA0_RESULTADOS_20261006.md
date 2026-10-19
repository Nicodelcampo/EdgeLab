# Etapa 0 de VTD-DIR — detector de régimen: validación target-free — 2026-10-06

Módulo `edgelab/regimes/state.py`; script `tools/regimen_etapa0.py`. Exploratorio, un contrato por instrumento: MNQ
12-26 y MGC 12-26, barras de 150t, hasta el 2026-09-30. Sin mirar dirección.

## Eje 1 — eficiencia (tendencia contra rango): **NO DETECTABLE en estas escalas**
- Estados por E_N contra un nulo de random walk (incrementos permutados dentro de la sesión), N ∈ {20, 50, 200}.
- Ocupación: unos 1/3 por estado, igual que el nulo.
- Persistencia P(mismo estado en la ventana siguiente): 0,27–0,38 contra un nulo de 0,28–0,41, sin patrón consistente
  entre instrumentos.
- E siguiente según el estado actual: igual en los tres.
- Autocorrelación de E entre ventanas contiguas: **−0,04 a +0,04**.

Lectura: en barras de 150t, de 20 a 200 barras (unos minutos a un par de horas), **que el precio venga "en tendencia"
no anticipa que siga en tendencia**. La eficiencia del recorrido se comporta como un random walk. Un filtro de "mercado
en tendencia contra rango" basado en el recorrido reciente **no tiene base** a esta escala. Es coherente con el
fracaso de la campaña EMA de MGC y con la advertencia del corpus [210].

## Eje 2 — amplitud (expansión contra compresión): **MUY PERSISTENTE**
- Correlación de log(amplitud por minuto) entre ventanas contiguas:
  - MNQ: **0,79 / 0,80 / 0,78** (N = 20 / 50 / 200);
  - MGC: **0,69 / 0,64 / 0,37**;
  - nulo (ventanas emparejadas al azar): ≈ 0.
- Es la agrupación de la volatilidad. **Cuidado:** incluye la estacionalidad horaria (apertura / mediodía / cierre),
  que no se descontó. Falta separar cuánto es "hora del día" y cuánto es "régimen".

## Consecuencias para VTD-DIR (enmienda propuesta)
- El moderador de régimen de la Etapa 1 pasa a ser **la amplitud** (expansión / compresión, terciles de la amplitud
  relativa a la misma hora en 20 sesiones), no la eficiencia.
- La eficiencia queda como descriptivo.
- Los predictores de **persistencia de tendencia** (EMA, momentum) parten con una expectativa baja a esta escala. Los
  de **flujo** (desbalance de órdenes, vela de VTD) y de **referencia de sesión** (VWAP, extremos) no dependen de esa
  persistencia y siguen siendo los candidatos más fuertes.
