# PNL-1 — P&L neto de reglas operables de las pistas en reserva: GC último 30 min (2 variantes) y celdas de SCAN-1 en GC y ES
**Estado: BORRADOR generado por el autopilot (regla R10_RESERVE_LEADS_TO_NET_PNL). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
Convierte las pistas en reserva en reglas operables y mide el P&L neto de costos por muestra, estabilidad (trimestres, 5 mejores días), resistencia a costos × 1,5 y frecuencia; la prueba confirmatoria es solo la de GC último 30 min (2 variantes) en el spot 2022-25, que no se usó para esta prueba. Las celdas de SCAN-1 se reportan de forma descriptiva (su muestra ya se consumió en la réplica).
Evidencia propia de origen: GC_LH_MOMENTUM, UNIVERSE_SCAN_1, PNL_EVAL_1. Tipo de vacío: NEW_MECHANISM.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- L_IDM_JUMPS: Los saltos del día (retornos extremos) predicen positivamente el retorno de la última media hora: los grandes movimientos disparan cobertura parcial intradía y una parte queda para el final del día; en mercados con volatilidad creciente (gamma corto de los creadores) se exacerba. (Baltussen, Da, Lammers, Martens (2021), Hedging demand and market intraday momentum, JFE — secciones de saltos y volatilidad (lectura 2026-10-13 vía consulta sobre el PDF de academicweb.nd.edu/~zda/intramom.pdf))
- L_IDM_COMMODITIES: El estudio incluye futuros de commodities (oro, plata, cobre, platino, paladio, crudo, etc.): el coeficiente conjunto del resto del día sobre la última media hora es positivo y significativo (1,21; t 3,63), Sharpe 1,42 de una estrategia de timing; la predictibilidad fuera de muestra es positiva solo en ~40-50 % de los contratos de commodities y monedas; el efecto es estable entre 1974-1999 y 2000-2020. (Baltussen et al. (2021), mismo artículo (lectura vía consulta sobre el PDF))
Literatura en contra / límites:
- L_IDM_COMMODITIES_LIMIT: En commodities la predictibilidad fuera de muestra es débil o inconsistente por contrato (≈ 40-50 % de contratos con R² OOS positivo): un único activo en un período corto no es evidencia fuerte. (Baltussen et al. (2021), resultados fuera de muestra; Understanding intraday momentum strategies, J. Futures Markets)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"mode": "strategy_pnl", "n_planned": 2, "nperm": 20000, "rules": [{"descriptive": ["GC_spot_new"], "dir": "momentum", "discovery": ["GC"], "entry": "14:30", "filter": "none", "hold_min": 30, "inst": "GC", "name": "GC_ROD_LH_ALL", "oos": ["GC_spot_old"], "pred": "rod"}, {"descriptive": ["GC_spot_new"], "dir": "momentum", "discovery": ["GC"], "entry": "14:30", "filter": "bigmove_q67", "hold_min": 30, "inst": "GC", "name": "GC_ROD_LH_BIG", "oos": ["GC_spot_old"], "pred": "rod"}, {"descriptive": ["GC", "GC_spot_new"], "dir": "momentum", "discovery": ["GC_spot_old"], "entry": "13:30", "filter": "none", "hold_min": 15, "inst": "GC", "name": "GC_PREV15_1330_MOM", "pred": "prev_15"}, {"descriptive": ["ES"], "dir": "reversion", "discovery": ["ES_spot"], "entry": "07:30", "filter": "none", "hold_min": 60, "inst": "ES", "name": "ES_PREV60_0730_REV", "pred": "prev_60"}, {"descriptive": ["ES"], "dir": "momentum", "discovery": ["ES_spot"], "entry": "12:30", "filter": "none", "hold_min": 30, "inst": "ES", "name": "ES_PREV30_1230_MOM", "pred": "prev_30"}], "seed": 20261017, "spot_ranges": {"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot_new": ["GC", "2025-07-01", "2026-09-30"], "GC_spot_old": ["GC", "2022-07-01", "2025-06-30"]}}
```
Pruebas planeadas: 5 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.3 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

Definiciones congeladas (script `tools/study_slot_effect.py`, modo `strategy_pnl`):
- Una operación por día y regla: entrada a la apertura del minuto `entry` (CT) y salida a la apertura `entry + hold_min`; dirección = signo del predictor × (+1 momentum, −1 reversión). Predictor: `prev_h` = log(P_entrada / P_{entrada−h min}); `rod` = log(P_entrada / P cierre previo 15:00 CT). Filtro `bigmove_q67`: solo si |predictor| ≥ cuantil 2/3 expansivo de las sesiones previas (causal, mínimo 60).
- P&L en USD por contrato = signo × (P_salida − P_entrada) × multiplicador (GC 100 oz, ES 50 USD/pt) − costo de ida y vuelta (GC 24,80; ES 30,00; supuestos de `edgelab/autopilot/universe.py`). Precio spot = punto medio bid/ask de la apertura del minuto.
- Reglas, muestras y roles (cfg abajo): `discovery` = muestra donde se halló la pista (descriptiva); `oos` = muestra confirmatoria; `descriptive` = otras fuentes.
- Prueba confirmatoria (solo `oos`): estadístico = media neta por operación; nulo = dirección aleatoria independiente por operación (20.000 sorteos); p unilateral; **p = 1 si la media neta ≤ 0**. Holm sobre 2 pruebas (GC_ROD_LH_ALL y GC_ROD_LH_BIG en el spot 2022-07 → 2025-06). Semilla 20261017.
- Descriptivo (no es prueba): media neta, desvío, aciertos, P&L por trimestre, parte de los 5 mejores días, P&L total con costos × 1,5, drawdown, operaciones por mes, y el P&L diario (para simular challenges y el control sin ventaja fuera del kernel).

## Transparencia sobre lo ya mirado (antes de este pre-registro)
- `GC_ROD_LH_ALL` y `GC_ROD_LH_BIG`: la pista nació en el futuro de GC 2025-26 (`discovery`). En el spot 2022-2025 (`oos`) ya se miró antes la correlación del tercil de |ROD| alto (+0,026) y el P&L bruto medio de seguir el signo (+0,66 pb, por debajo del costo): se espera que no pasen; la prueba sirve para cerrar la pista en su forma operable.
- Celdas de SCAN-1 (`GC_PREV15_1330_MOM`, `ES_PREV60_0730_REV`, `ES_PREV30_1230_MOM`): su muestra de réplica (futuros 2025-26) ya se consumió en SCAN-1 sin éxito: aquí son DESCRIPTIVAS, no confirmatorias.

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 5 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.3077, "power": 0.3, "utility": "tradeable=1.0", "rho_required": null, "feasibility": 1.0, "cost_factor": 1.225, "prior_hits": "0/0", "literature_pro": 2, "literature_contra": 1} → 0.0754
