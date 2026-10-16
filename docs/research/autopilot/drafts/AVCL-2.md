# AVCL-2 — Dirección tras la creación de un cluster de volumen (etapa 2 de AVCL-VOL-1)
**Estado: BORRADOR generado por el autopilot (regla R5_INFO_TO_DIRECTION). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
El rango adelante sube tras el cluster (Holm 0,0006); falta la dirección. Es campaña de la sesión local (necesita su manifiesto).
Evidencia propia de origen: AVCL_RANGE. Tipo de vacío: NEW_MECHANISM.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{}
```
Pruebas planeadas: 12 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.5 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 12 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.5, "utility": "bridgeable=0.6", "rho_required": null, "feasibility": 1.0, "cost_factor": 4.899, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0122
