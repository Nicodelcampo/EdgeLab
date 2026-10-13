# VIO-1 — Zonas violeta (lógica de aVolClusterPOI) sobre las zonas de aVolZonePOI2 en MGC 25 ticks: ¿el precio que vuelve a una distancia D de la zona llega más a la zona que a D más lejos? ¿hay un TP/SL con esperanza neta positiva?
**Estado: BORRADOR generado por el autopilot (regla R11_USER_HYPOTHESIS). No vale como pre-registro hasta que un humano lo revise y lo committee ANTES de lanzar.**

## Por qué existe (procedencia)
Nico observó en el gráfico de MGC 12-26 (25 ticks) patrones del precio respecto de las zonas violeta de aVolClusterPOI. Esa lógica (alejarse rápido y lejos con poco volumen operado adentro) no tiene paridad verificada; se porta aquí y se aplica a las zonas de aVolZonePOI2, cuya paridad NT8 sí está verificada (25 ticks, MNQ). Se mide, a nivel de tick, la probabilidad de llegar a la zona frente a alejarse cuando el precio, ya alejado, vuelve a una distancia D, para 36 configuraciones de TP/SL.
Evidencia propia de origen: VIO_ZONES_MGC. Tipo de vacío: NEW_MECHANISM.
Literatura a favor (LITERATURE_CLAIM_UNVERIFIED, no es evidencia propia):
- (ninguna)
Literatura en contra / límites:
- (ninguna)

## Qué se prueba y con qué muestra
Configuración exacta (se pasa al kernel tal cual y se verifica que figure aquí):
```
{"D": [10, 16, 20, 30, 40, 60], "bar_ticks": 25, "cost_ticks": 6.8, "desde": "2025-07-01", "hasta": "2026-09-30", "inst": "MGC", "mode": "vio1", "n_planned": 4, "nperm": 10000, "seed": 20261018, "split": 0.6, "tick_usd": 1.0, "violet_params": {}, "zone_params": {"ob_away_heights": 6.0, "ob_max_inside_pct": 4.0, "racimo_altura_ticks": 30, "racimo_bars": 500, "racimo_min": 6}}
```
Pruebas planeadas: 39 (se cuentan en el registro global antes de lanzar). Potencia supuesta: 0.35 (supuesto declarado, no medida).
La muestra no reutiliza la que originó la pista (ver `unused_samples` de la evidencia).

Definiciones congeladas (script `tools/vio1_zones.py`; lógica violeta en `edgelab/research/violet_zones.py`, portada de `nt8/aVolClusterPOI_violet_v05.cs`):
- Datos: MGC, sesiones aprobadas 2025-07-01 → 2026-09-30 (líder por sesión del resolver), sin la pausa CME 16:00-17:00 CT; barras de 25 ticks (trades); footprint total NT8 (`build_total_footprint_csr_nt8`).
- Zonas: `edgelab.bridge.indicators.avolzonepoi2.run` con la configuración 25T de paridad verificada (detección por defecto 10/×2/gap 1/mín. 2/Suma/15 min/p95/20 sesiones/mín. 20; OB 6 alturas, 8 ticks, 4 %; racimo 6/500/30). Se usan TODAS las zonas detectadas.
- Violeta (parámetros por defecto del .cs): dirección = signo del cierre de la barra de creación respecto de la zona (0 = adentro: no aplica); se alejó = separación máxima ≥ max(40 ticks, ⌈2 × ancho⌉) dentro de 30 barras; poco volumen = volumen operado dentro de la zona hasta ese momento / score ≤ umbral adaptativo causal (cuantil q = 20 % / proporción de zonas que se alejan; 0,35 mientras haya menos de 20 alejadas o 20 resueltas); invalidación por cierre de barra del lado equivocado; la decisión se fija una vez.
- Evento (a nivel de TICK): tras la barra de decisión, el precio se aleja a más de D ticks de la zona y luego vuelve a D (entrada con orden límite en D). Ventana: hasta la invalidación de la zona o el fin de la sesión CME (16:00 CT). D ∈ {10, 16, 20, 30, 40, 60} ticks (MGC: 1 tick = 0,10 = USD 1).
- Resultado por configuración (a, b) con a ∈ {D/2, D} ticks hacia la zona (TP; a = D llega al borde de la zona) y b ∈ {D/2, D, 2D} alejándose (SL): 36 configuraciones; sin barrera al fin de la ventana se sale a mercado. P&L en ticks; costo de ida y vuelta supuesto 6,8 ticks (USD 6,8 por contrato: comisión 4,80 + 2 ticks de deslizamiento; supuesto conservador).
- Descubrimiento (60 % inicial de las sesiones): esperanza bruta por evento de cada configuración; nulo de MÁXIMO por cambio de signo por sesión (conjunto en las 36 configuraciones, 10.000 sorteos; H0 = esperanza bruta 0). Réplica (40 % final): las 3 mejores configuraciones del descubrimiento, con media neta (bruta − 6,8) > 0 exigida (p = 1 si ≤ 0), nulo de signo por sesión. Holm sobre 4 pruebas (1 máximo + 3 réplicas); el contador global recibe 39 (36 configuraciones + 3 réplicas). Semilla 20261018.
- Descriptivo (no es prueba): para cada configuración, P(TP), P(SL), P(sin barrera), P(TP) de equilibrio b/(a+b), esperanza bruta en cada mitad, eventos por sesión; y el MISMO análisis para las zonas que se alejaron pero NO son violeta (control).

## Transparencia sobre lo ya mirado (antes de este pre-registro)
- La hipótesis nace de la inspección visual de Nico del gráfico MGC 12-26 (25 ticks) con aVolClusterPOI (captura del 2026-10-12, que incluye fechas posteriores al 2026-09-30 que este estudio NO lee). Esas impresiones visuales pueden coincidir con períodos de la muestra: por eso se separa descubrimiento (60 % inicial) y réplica (40 % final); la muestra no es virgen.
- La lógica violeta no tiene paridad verificada (solo el .cs); su portado a Python se prueba con casos sintéticos (`tests/test_violet_zones.py`) y se verificó que corre de punta a punta sobre un tramo de ES (sin resultados de MGC). Las zonas de aVolZonePOI2 sí tienen paridad NT8 verificada (MNQ 25T); su paridad en MGC no se verificó.
- No se miró ningún resultado de MGC antes de este pre-registro.

## Nulo y decisión
Nulo de signo aleatorio / permutación por bloques según el modo; Holm sobre 39 pruebas planeadas al nivel familiar que apostó el alpha-investing del autopilot (≤ 0,05). Un estadístico no finito es «no evaluable» y no entra al ranking.
**Falsación:** si ninguna prueba pasa Holm, la pista se degrada a NULL y no se vuelve a proponer sin datos nuevos.
**Si pasa:** es un hallazgo exploratorio; promover requiere réplica pre-registrada en datos no usados. No hay P&L, holdout ni promoción en este estudio.

## Puntuación de valor esperado de información
{"p0": 0.2, "power": 0.35, "utility": "tradeable=1.0", "rho_required": null, "feasibility": 1.0, "cost_factor": 2.0, "prior_hits": "0/0", "literature_pro": 0, "literature_contra": 0} → 0.0350
