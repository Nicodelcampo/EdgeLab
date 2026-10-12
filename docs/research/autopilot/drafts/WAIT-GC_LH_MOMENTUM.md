# WAIT-GC_LH_MOMENTUM — Confirmación prospectiva de GC (último 30 min) con datos posteriores al 2026-09-30
**Estado: BORRADOR generado por el autopilot (regla R6_NEW_LEAD_NEEDS_UNSEEN_DATA). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
La única muestra realmente independiente en el tiempo es posterior a 2026-09-30 (holdout cerrado). Requiere una decisión humana: pre-registro específico y apertura controlada, o esperar a que haya sesiones nuevas fuera del holdout formal.
Evidencia propia de origen: GC_LH_MOMENTUM. Tipo de vacío: NO_PRIOR_EVIDENCE.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{}
```
Pruebas planeadas: 1 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.5 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 1 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.5, "cost_factor": 1.0, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0000
