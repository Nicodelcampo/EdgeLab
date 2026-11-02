# Pre-registro: CVGAP-ES-C y CVGAP-CFD-ES-C en PAPEL con e-proceso (2026-11-02)

Estado: VIGENTE, registrado antes de ver cualquier resultado del holdout de estas reglas. Decisión de Nico (2026-11-02): «pasalas a la
cartera en papel con e-proceso». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5 (seguimiento forward). Marco: `docs/CARTERA_VIVA.md`.

## Por qué
Operan unas 8 y 5 veces por mes. Con el N fijo de 150 de su acta de holdout, la decisión tardaría de 1,5 a 2,5 años. El e-proceso se
puede mirar todos los días y decide en cuanto la evidencia alcanza, con la garantía de Ville.

## Regla congelada
La de `embudo/<cid>/ACTA_HOLDOUT.json`, sin tope, sin cambios:
- celda y cortes del DESC causal;
- ejecución en ES;
- fricción canónica de ES.

Nominación forzada: `PREREGISTRO_NOMINACION_FORZADA.md`.

## Ventana
- **Desde la sesión 2026-10-01.** Las corridas del holdout de octubre estaban lanzadas y sin mirar cuando se registró esto: octubre
  cuenta como forward.
- Sólo sesiones válidas (`SELLADO_CONTEO`).

## Monitor por ficha
Una observación por operación. Los parámetros se fijan con las operaciones causales de DESC + réplica de la celda, que salen de
corridas ANALIZAR_REGLA sobre desarrollo, nunca del holdout:
- **Cotas:** 3 × la peor y la mejor operación de desarrollo.
- **`mu_util`:** 0,5 × min(media DESC, media réplica). Si alguna es ≤ 0, la ficha no se da de alta.
- **`sd_desarrollo`:** desvío por operación.
- **Retiro:** por futilidad, por drawdown mayor a 8 × la pérdida máxima declarada o por violar una cota. Promoción por e-proceso de
  edge, según las reglas de la cartera.

**Entran a la canasta** desde la primera sesión en que se las evalúa, como cualquier ficha (`canasta.py`).

**El acta de holdout a N fijo sigue vigente en paralelo.** El papel no la reemplaza.

## Cómo podría refutarse
Futilidad del e-proceso o media forward ≤ 0.

## Registro
2 pruebas en `TRIAL_REGISTRY_GLOBAL.jsonl` (`cartera_forward/CVGAP-ES-C`, `cartera_forward/CVGAP-CFD-ES-C`).
