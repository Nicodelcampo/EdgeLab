# SLOT-1 — Reversión de 15 min a las 04:30 CT en otros activos (generalización del hallazgo débil de GC)
**Estado: BORRADOR generado por el autopilot (regla R1_REPLICATE_WEAK_LEAD_IN_UNUSED_SAMPLE). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
GC 04:30 tiene el mismo signo en dos muestras pero no pasa Holm; GC ya consumió sus datos, así que la prueba limpia es otros activos con el mismo horario.
Evidencia propia de origen: GC_0430_REV15, OU_OTHER. Tipo de vacío: NO_PRIOR_EVIDENCE.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- L_IDX_REVERSALS: Existen reversiones intradía en futuros de índices de EE. UU. tras grandes cambios de precio en ciertas horas (estudio de 15 años). (Intraday price reversals in the US stock index futures market: A 15-year study, https://www.researchgate.net/publication/222520781)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"horizon_min": 15, "mode": "slot_corr", "n_planned": 7, "slots": ["04:30"], "sources": ["ES", "NQ", "YM", "6E", "6J", "ZB", "ES_spot"], "spot_ranges": {"ES_spot": ["ES", "2018-01-01", "2025-06-30"]}}
```
Pruebas planeadas: 7 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.35 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 7 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2727, "power": 0.35, "cost_factor": 1.225, "prior_hits": "0/0", "literature_pro": 1, "literature_contra": 0} → 0.0779
