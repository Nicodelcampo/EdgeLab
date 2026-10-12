# SCAN-1 — Barrido de franjas (07:00-14:30 CT) en GC, NQ, ES, YM y 6E: momentum y reversión, descubrimiento → réplica
**Estado: BORRADOR generado por el autopilot (regla R9_UNIVERSE_BY_ACCOUNT_THRESHOLD). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
El universo guiado por umbrales ubica los umbrales más bajos de cuenta en la apertura de EE. UU. (08:00-10:00 CT) de GC, NQ, ES y YM. Se barren 96 celdas por instrumento (franja × horizonte × predictor), con nulo de máximo en el descubrimiento (spot largo para ES y GC, 60 % inicial de los futuros para NQ, YM y 6E) y réplica de las 3 mejores celdas en la otra muestra. 495 celdas/pruebas al contador global; 20 pruebas reportadas para Holm.
Evidencia propia de origen: UNIVERSE_SCAN_1. Tipo de vacío: NO_PRIOR_EVIDENCE.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"mode": "slot_scan", "n_planned": 20, "nperm": 10000, "scans": [{"disc": "ES_spot", "name": "ES", "rep": "ES"}, {"disc": "GC_spot_old", "name": "GC", "rep": "GC"}, {"disc": "NQ", "name": "NQ", "rep": "NQ", "split": 0.6}, {"disc": "YM", "name": "YM", "rep": "YM", "split": 0.6}, {"disc": "6E", "name": "6E", "rep": "6E", "split": 0.6}], "seed": 20261016, "spot_ranges": {"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot_old": ["GC", "2022-07-01", "2025-06-30"]}}
```
Pruebas planeadas: 495 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.3 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

Definiciones congeladas (script `tools/study_slot_effect.py`, modo `slot_scan`):
- Celdas por instrumento (96): franja de inicio t ∈ {07:00, 07:30, …, 14:30} CT × horizonte h ∈ {15, 30, 60} min (solo si t+h ≤ 15:30) × predictor ∈ {«prev»: log(P_t / P_{t−h}); «rod»: log(P_t / P_cierre previo 15:00 CT)}. Retorno siguiente Y = log(P_{t+h} / P_t). P = apertura del minuto, último precio conocido del día (ffill); se descartan fechas con datos faltantes.
- Estadístico por celda: correlación de Pearson corr(X, Y), BILATERAL (momentum +, reversión −).
- Descubrimiento (por instrumento): z_c = corr·√n; máximo |z| sobre las 96 celdas; nulo de MÁXIMO con 10.000 permutaciones de las sesiones de Y (la misma permutación en todas las celdas); p = (1 + #{máx_nulo ≥ máx_obs}) / (1 + B).
- Réplica (por instrumento): las 3 celdas con mayor |z| del descubrimiento; en la muestra de réplica, con el signo del descubrimiento FIJADO, corr unilateral, nulo de signo aleatorio sobre Y (10.000 sorteos).
- Muestras: ES: descubrimiento en spot ES 2018-01-01 → 2025-06-30 y réplica en el futuro ES 2025-07 → 2026-09; GC: spot 2022-07-01 → 2025-06-30 y futuro 2025-07 → 2026-09; NQ, YM, 6E: futuros 2025-07 → 2026-09 con el primer 60 % de las sesiones para descubrir y el 40 % final para replicar. Semilla 20261016.
- Pruebas reportadas para Holm: 4 por instrumento (1 máximo + 3 réplicas) = 20; el contador global recibe 495 (480 celdas + 15 réplicas).
- Descriptivo (no es prueba): top-10 de celdas del descubrimiento con su correlación en la réplica.

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 495 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.3, "utility": "tradeable=1.0", "rho_required": 0.031, "feasibility": 1.0, "cost_factor": 2.0, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0300
