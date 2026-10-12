# IDM-1 — Momentum intradía «resto del día → última media hora» y su modulación por gamma bajo
**Estado: BORRADOR generado por el autopilot (regla R2_BRIDGE_INFO_LEAD_TO_PUBLISHED_MECHANISM). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
GEX-1 midió la interacción en una ventana de 90 min (p Holm 0,43, signo esperado); la literatura define 30 min en muchas clases de activos. La ventana nueva y el cruce con gamma son pruebas nuevas, no repeticiones.
Evidencia propia de origen: GEX_I2D_ROD_LH, GEX_AMPLITUDE. Tipo de vacío: NEW_MECHANISM.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- L_IDM_GAMMA: El retorno del día hasta 30 min antes del cierre predice (positivamente) el de la última media hora en futuros de varias clases de activos; es más fuerte cuando los creadores de mercado están cortos en gamma. (Baltussen, Da, Lammers, Martens (2021), Hedging demand and market intraday momentum, J. Financial Economics, https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598)
- L_IDM_FIRST_HALF_HOUR: El primer retorno de media hora (y el overnight) predice el de la última media hora en ETF/índices. (Gao, Han, Li, Zhou, Market Intraday Momentum (JFE 2018); Li, Sakkas, Urquhart, Intraday Time Series Momentum: International Evidence)
Literatura en contra / límites:
- L_IDM_CONTRA: Fuera de muestra y con costos la estrategia de momentum intradía con el retorno overnight desaparece o se debilita; la predictibilidad intradía varía con el período. (Understanding intraday momentum strategies, Journal of Futures Markets, https://onlinelibrary.wiley.com/doi/10.1002/fut.22375; Aleti, Bollerslev, Siggaard (2025), Intraday Market Return Predictability Culled from the Factor Zoo)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"gamma_source": "ES_spot", "mode": "idm", "n_planned": 10, "sources": ["ES", "NQ", "YM", "GC", "ZB", "6E", "6J", "ES_spot", "GC_spot"], "spot_ranges": {"ES_spot": ["ES", "2018-01-01", "2025-06-30"], "GC_spot": ["GC", "2022-07-01", "2025-06-30"]}}
```
Pruebas planeadas: 10 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.55 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 10 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.3077, "power": 0.55, "cost_factor": 1.581, "prior_hits": "0/0", "literature_pro": 2, "literature_contra": 1} → 0.1070
