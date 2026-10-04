# edgelab.equivalence

Mide qué tan buen sustituto es una serie de otra fuente (spot, CFD de índices) para la serie de futuros con la que se diseñó una estrategia. **No da por buena la equivalencia: la mide en el solape donde existen las dos.**

## Qué hace
- `match_bar_size`: cuántos eventos del sustituto forman una barra para igualar el ritmo de las barras de `n` eventos de futuros (razón de eventos por día + distancia de Kolmogorov-Smirnov entre duraciones, solo en el solape). Iguala el ritmo, no el contenido: un tick de Dukascopy es un cambio de cotización, uno de NinjaTrader es una operación ejecutada.
- `sync_resample`: precio del sustituto en el cierre de cada barra de futuros. Mide la equivalencia de **precio** (base, ruido) sin tocar la formación de barras.
- `ema_cross_signals`: la señal de MGC (EMA 200 cruza a EMA 500 con EMA 500 del mismo lado de EMA 2000; barras de 25 ticks). **Reproduce exactamente las 1.643 señales originales** de los artefactos de MGC (verificado).
- `signal_agreement`: precisión, exhaustividad y F1 de las señales del sustituto contra las de futuros, con tolerancia de tiempo; `outcome_agreement`: resultado a horizonte fijo de todas las señales, agregado por día, correlación diaria.

## Uso
`python tools/equivalence_check.py --spot spot_xauusd_ticks.csv --out artifacts/equivalence` con columnas `time` (epoch ms o ns, o ISO UTC), `bid`, `ask`. Usar solo MGC previo al holdout (2025-10-07 a 2026-03-31: el solape necesario del spot). `--selftest` prueba la cañería con un sustituto sintético hecho de los ticks de MGC: con un sustituto casi perfecto da F1 ≈ 0,98 y correlación diaria ≈ 0,99; ese es el **techo de la herramienta, no un resultado**.

## Reglas de lectura (fijar antes de ver el resultado real)
- Un sustituto solo se usa para extender la muestra si en el solape supera umbrales escritos de antemano (F1 de señales y correlación diaria de resultados). Si no los supera, no se usa.
- Solo vale para estrategias que dependen del precio. No sirve para volumen operado, agresor, absorción ni libro.
- Los costos y la ejecución se modelan siempre con el instrumento real, nunca con el spread del sustituto.
- Un resultado en el sustituto que confirme una estrategia de futuros es evidencia más débil y se declara como tal.
