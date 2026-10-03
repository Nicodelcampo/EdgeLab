# MGC EMA 200/500/2000 — veredicto con los datos disponibles (2026-10-03)

**Veredicto: el edge NO se valida. Con las 4 pistas de contrato disponibles (sin MGC_10-25 ni MGC_10-26) no hay evidencia que sobreviva la corrección por selección. Holdout (trade_date >= 20260401) sin abrir.**

## Reproducción
Raw `nicolasbuttaro/edgelab-mgc-nt8-raw-parquet-20261002` bajado de Kaggle por API. Canónico reproducido: 56.575.239 ticks, SHA-256 `87aac766…3e4`; artefacto de barras `8c52391adf32f82b9c84`; headline tick-exact 623 trades, +9.918,5 ticks (idéntico al registro).

## Qué se midió (pre-registro: DIAGNOSTICO_DIRECCION_PREREGISTRO.md)
| Prueba | Resultado | Regla |
|---|---|---|
| Long / short | +3.645,5 / +6.273 | ambos > 0: pasa |
| Dirección aleatoria i.i.d. (2000) | p = 0,022 | pasa |
| Dirección aleatoria por sesión (2000) | p = 0,037 | pasa |
| Sin mejor mes (marzo, 46 % del neto) | +5.358 | pasa |
| Sin 5 mejores días | +2.345,5 | pasa |
| D0 / D1 / D2 del embudo | +3.169,5 / +2.004,5 / +4.744,5 | los tres > 0 |
| **Máximo de 21 celdas, dirección por sesión (500)** | **p_max = 0,0998** | **> 0,05: NO pasa** |

## Lectura
- El headline por sí solo luce direccional, pero fue elegido a posteriori como el mejor de 21 celdas. Al compararlo con el mejor de 21 celdas bajo dirección sorteada, el resultado es compatible con azar (p ≈ 0,10). Coincide con DSR 0/42, BH 0/42 y SPA p = 0,342.
- Hay señal de dirección (las celdas inversas pierden ~9.000 ticks) pero la selección del TP/SL consume la significancia. Un resultado más fuerte exige una celda congelada y datos que no se usaron para elegirla.
- Aviso de custodia: **el «D2» del embudo (20260217–20260331) ya fue visto** por el OOS 30 % y por la validación de 123 días; no es confirmación limpia. El único tramo no visto es el holdout.

## Holdout: no se abre
Poder bajo: ~5 trades/día, sd por trade ≈ 291 ticks, efecto en muestra ≈ 16 ticks/trade (sobreestimado por selección). Con n trades el error estándar es 291/√n: con ~250 trades ≈ 18 ticks, t ≈ 1. Una apertura única no podría confirmar ni refutar. Abrirlo sólo tiene sentido con una celda congelada y muestra suficiente (más contratos/regímenes).

## Qué haría falta para cambiar el veredicto
1. Más historia con el mismo contrato de datos (MGC_10-25 / 10-26 u otro metal/instrumento con la misma señal, definida de antemano).
2. Celda única congelada (SL 200 / TP 400) y réplica fuera de muestra real; o evaluar el mismo sistema en otros activos sin reoptimizar.
3. Sólo entonces, apertura única del holdout.

Reproducir: `python tools/mgc_direction_diagnostic.py`, `python tools/mgc_direction_maxnull.py` (PYTHONPATH=raíz; raw en /data/raw/mgc).
