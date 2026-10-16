# IDM-2 — Momentum de la última media hora en GC: ¿lo explican los saltos del día? Prueba en spot 2022-2025 (muestra no usada para esta versión) y en otros activos
**Estado: BORRADOR generado por el autopilot (regla R7_MECHANISM_COMPLEMENT_OF_LEAD). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
La literatura asocia el efecto a los saltos del día (cobertura de gamma tras grandes movimientos). En GC 2025-26 la correlación se concentra en movimientos grandes (+0,376 contra −0,051) y en 2026Q1. Esta prueba separa saltos y movimiento continuo y la corre sobre spot 2022-2025 de GC, donde esta descomposición no se miró (la versión «tercil grande» sí se miró y dio +0,026, por eso no se pre-registra).
Evidencia propia de origen: GC_LH_MOMENTUM. Tipo de vacío: NEW_MECHANISM.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- L_IDM_JUMPS: Los saltos del día (retornos extremos) predicen positivamente el retorno de la última media hora: los grandes movimientos disparan cobertura parcial intradía y una parte queda para el final del día; en mercados con volatilidad creciente (gamma corto de los creadores) se exacerba. (Baltussen, Da, Lammers, Martens (2021), Hedging demand and market intraday momentum, JFE — secciones de saltos y volatilidad (lectura 2026-10-13 vía consulta sobre el PDF de academicweb.nd.edu/~zda/intramom.pdf))
- L_IDM_COMMODITIES: El estudio incluye futuros de commodities (oro, plata, cobre, platino, paladio, crudo, etc.): el coeficiente conjunto del resto del día sobre la última media hora es positivo y significativo (1,21; t 3,63), Sharpe 1,42 de una estrategia de timing; la predictibilidad fuera de muestra es positiva solo en ~40-50 % de los contratos de commodities y monedas; el efecto es estable entre 1974-1999 y 2000-2020. (Baltussen et al. (2021), mismo artículo (lectura vía consulta sobre el PDF))
Literatura en contra / límites:
- L_IDM_COMMODITIES_LIMIT: En commodities la predictibilidad fuera de muestra es débil o inconsistente por contrato (≈ 40-50 % de contratos con R² OOS positivo): un único activo en un período corto no es evidencia fuerte. (Baltussen et al. (2021), resultados fuera de muestra; Understanding intraday momentum strategies, J. Futures Markets)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"mode": "idm_jump", "n_planned": 8, "reference_sources": ["GC"], "sources": ["GC_spot_old", "ES_spot", "ES", "NQ", "YM", "ZB", "6E", "6J"], "spot_ranges": {"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot_old": ["GC", "2022-07-01", "2025-06-30"]}}
```
Pruebas planeadas: 8 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.35 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

Definiciones congeladas (script `tools/study_slot_effect.py`, modo `idm_jump`, por fecha local CT):
- Precio = apertura del minuto en una rejilla de 5 min (primer valor de cada bloque). Retornos r = log-diferencias sucesivas entre puntos de rejilla disponibles desde el 15:00 CT de la sesión anterior hasta el 14:30 CT (una brecha de mantenimiento/fin de semana cuenta como un retorno).
- σ = 1,4826 · mediana(|r|) de las 20 sesiones previas (causal; se exige ≥ 5 sesiones previas). Salto = |r| > 4σ. ROD = Σ r; ROD_salto = Σ r de los saltos; ROD_cont = ROD − ROD_salto. LH = log(P 15:00 / P 14:30).
- Modelo: OLS LH ~ 1 + ROD_salto + ROD_cont. Estadístico = coeficiente de ROD_salto. H1: > 0 (unilateral). Nulo: signo aleatorio independiente sobre LH, 20.000 sorteos, semilla 20261013.
- `reference_sources` (GC futuro 2025-26) se informan pero NO entran en Holm: es la muestra que originó la pista. La prueba de la pista es `idmj/GC_spot_old` (spot 2022-07-01 → 2025-06-30).
- Descriptivo (no es prueba): participación de sesiones con salto, coeficiente de ROD_cont, rango del coeficiente de salto al excluir cada trimestre.

## Transparencia sobre lo ya mirado (antes de este pre-registro)
- En GC 2025-26 (futuro y spot, misma muestra que originó la pista) se miraron: correlación por trimestre, sin 2026Q1, sin los 10 días más influyentes, terciles de |ROD|, economía bruta de seguir el signo. Son descriptivos y no cuentan como pruebas.
- En el spot 2022-2025 se miró **una** cosa antes de pre-registrar: el tercil de |ROD| alto (causal expansivo) dio corr +0,026 (n = 309). Por eso esa versión del refinamiento no se pre-registra ni se usa; la descomposición en saltos NO se calculó en ese tramo.
- El pipeline de saltos se verificó en sintético y en spot 2025-26 (misma muestra de la pista, no la de la prueba primaria).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 8 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.3077, "power": 0.35, "cost_factor": 1.414, "prior_hits": "0/0", "literature_pro": 2, "literature_contra": 1} → 0.0761
