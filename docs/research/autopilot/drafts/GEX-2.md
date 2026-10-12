# GEX-2 — Amplitud intradía con gamma bajo en NQ y YM spot (réplica con instrumentos distintos)
**Estado: BORRADOR generado por el autopilot (regla R4_EXTEND_POWER). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
El efecto existe en USA500 spot y MES no tiene potencia (9 sesiones). Instrumentos correlacionados: réplica parcialmente independiente. Necesita adaptar gex1b_run a otros spots.
Evidencia propia de origen: GEX_AMPLITUDE. Tipo de vacío: NO_PRIOR_EVIDENCE.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{}
```
Pruebas planeadas: 12 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.6 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 12 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.6, "utility": "info=0.3", "rho_required": null, "feasibility": 1.0, "cost_factor": 1.581, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0228
