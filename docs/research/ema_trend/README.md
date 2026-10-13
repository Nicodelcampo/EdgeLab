# Zonas de tendencia estable respecto de una EMA (NQ 25T, EMA 200)

**Propósito (palabras del usuario, 2026-10-13):** encontrar las típicas *trendlines*. Detectarlas por picos o toques repetidos a una línea es más complicado; se usa una EMA porque es más permisiva y más fácil de programar las «interacciones». Además permite distintos tipos de zonas: con más picos, más empinadas, menos empinadas, etc. Luego esas zonas se usan como área de desplazamiento de posibles trades (cuando el precio se da la vuelta, ¿es más probable que las atraviese/continúe atravesándolas?). Las capturas del usuario son **ejemplos de la lógica**, no un objetivo a ajustar al detalle: basta con que marque varias zonas útiles con una distancia aceptable para operar.

## Implicancias de diseño
- Cada zona debe llevar atributos para clasificarla en tipos: pendiente de la EMA (en ATR por barra), distancia media precio-EMA (ATR y puntos), duración, y **número de picos/toques** (swings que se acercan a la EMA sin cruzarla).
- **Distancia aceptable = LONGITUD de la zona** (no la distancia precio-EMA): duración en barras y recorrido del precio a lo largo de la zona (puntos), con un mínimo para que sirva como área de desplazamiento de trades. La distancia precio-EMA es solo un atributo secundario.
- Solo contexto: no hay evidencia de edge. La pregunta operativa (¿atraviesan las zonas más de lo que rebotan?) requiere medición pre-registrada aparte, como VIO-1.

## Archivos
`nt8/EmaStableTrend_original.cs` (versión del otro agente), `edgelab/research/ema_zones.py`, `tools/ema_digitize.py`, `tools/ema_calibrate_screens.py`, `tools/ema_zones_study.py`, `templates.json` (geometría de píxeles de las capturas), `calibration.json`.
