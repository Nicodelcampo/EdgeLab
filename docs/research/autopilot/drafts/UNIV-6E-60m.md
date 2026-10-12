# UNIV-6E-60m — Barrido de franjas de 60 min en 6E (celdas con menor umbral de cuenta)
**Estado: BORRADOR generado por el autopilot (regla R9_UNIVERSE_BY_ACCOUNT_THRESHOLD). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
Mejores franjas por umbral: 07:30 CT (ρ* 0.103, 1 6E, Topstep|Trading_Combine_50K); 07:00 CT (ρ* 0.105, 1 6E, Topstep|Trading_Combine_50K); 09:00 CT (ρ* 0.121, 1 6E, Topstep|Trading_Combine_50K); 08:30 CT (ρ* 0.123, 1 6E, Topstep|Trading_Combine_50K). Requiere un script de barrido de esas franjas (momentum y reversión, bilateral, nulo de máximo) y su pre-registro.
Evidencia propia de origen: . Tipo de vacío: NO_PRIOR_EVIDENCE.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{}
```
Pruebas planeadas: 12 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.3 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 12 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.3, "utility": "tradeable=1.0", "rho_required": 0.103, "feasibility": 1.0, "cost_factor": 1.732, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0346
