# OU-2 — Reversión de ZB a 5-15 min con precio medio bid/ask (descarta rebote bid-ask)
**Estado: BORRADOR generado por el autopilot (regla R3_ARTIFACT_CHECK). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
Si la reversión sobrevive con precio medio es de otra naturaleza; si desaparece, queda cerrado. Requiere un script que reconstruya mid desde bid_ticks/ask_ticks (no existe aún).
Evidencia propia de origen: ZB_REV_5_15. Tipo de vacío: DATA_DEFINITION.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- L_BOUNCE: La autocorrelación negativa intradía en precios de transacción es mayormente rebote bid-ask para escalas < 20 min; desaparece al muestrear a 5 min o más en FX; se ve más en futuros de tick grueso. (Goodhart (1989); Cont (2001) stylized facts; resumen en finance.martinsewell.com/stylized-facts/dependence; arXiv 2606.29591 (rebote bid-ask y reversión de horizonte corto en índices))

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{}
```
Pruebas planeadas: 4 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.6 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 4 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.1818, "power": 0.6, "utility": "info=0.3", "cost_factor": 2.449, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 1} → 0.0134
