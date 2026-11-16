# VWAP banda 3 (reversión) — acta de apertura del holdout (2026-11-16)

Estado: VIGENTE — escrita y commiteada ANTES de lanzar. Pedido de Nico (2026-11-16): usar el holdout que ya pasó (desde el 1-oct) en vez de
semanas de papel; «queremos lo que funciona ahora». Modo exploratorio (2026-11-08). Familia `M1_INTRADIA`, sin aperturas previas.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5 (confirmación exploratoria).

## Regla congelada (sin ajuste)
`edgelab/research/m1_intradia.py::vwap_banda`, variante **K = 3, REV, objetivo VWAP, stop EXT** (extremo del día + 0,5 desvío): VWAP
anclado 09:30 NY con su desvío ponderado; desde las 10:00, primer cierre de 1 min fuera de ±3 desvíos → a mercado hacia el VWAP; cierre
15:55; piso de riesgo 0,5 desvío. Barras de 1 min construidas de los ticks sellados con volumen REAL (desarrollo: volumen de ticks de
Dukascopy). Fricción canónica del futuro por ida y vuelta (`edgelab/costos.py`, base): NQ 1,5455 pts, YM 5,052 pts, ES 0,8877 pts.
Kernel: `tools/kaggle_grilla/vwapb_holdout_main.py` (`python tools/m1_intradia.py lanzar_vwapb_holdout`), probado en ticks sintéticos.

## Hipótesis
- **H**: R neto medio por operación > 0 en la canasta **NQ + YM** (los dos índices con R neto > 0 en el tramo reciente de desarrollo).
- ES se mide como control y no decide (en desarrollo, S&P −0,05 R neto en el tramo reciente).

## Desarrollo y p declarada: 0,5
M1 2012 → 2026-09 (`RESULTADO.md`): dosis banda 3 > banda 2 en bruto (+0,161 vs +0,085, t 4,5 en 2012–2019) y en 2025-08 → 2026-09
(+0,16 a +0,24), negativa 2020–2023 y ≈ 0 2024 → 2025-07; neto en el tramo reciente (spread de CFD): Nasdaq +0,13, Dow +0,11. No superó el
nulo de la búsqueda en neto y el régimen no se pudo anticipar (`RESULTADO_REGIMEN_VWAPB.md`). Por eso p de desarrollo = 0,5. En futuros el
costo de YM es el doble que el spread del CFD del Dow: el neto puede ser menor que en desarrollo.

## Ventana: sesiones selladas desde 2026-10-01 hasta la última sellada (2026-11-13), NQ, YM y ES; sin `SESIONES_EXCLUIDAS_HOLDOUT`
Qué del holdout se miró en el linaje: LUXIMB-AMARILLA (11-nov, n 11, objetivo 50 % +0,086 R) usó un filtro «lejos del VWAP diario,
hacia él» sobre otra entrada (caja amarilla). Pariente lejano y su resultado era conocido: puede sesgar a favor; se reporta también la
mitad de noviembre (sesiones de noviembre no miradas por ningún pariente).

## Potencia (declarada antes)
≈ 0,3–0,5 operaciones por sesión e índice → ≈ 20–30 operaciones NQ + YM en ≈ 30 sesiones; desvío de R ≈ 1 → error estándar ≈ 0,2 R.
**Sin potencia** para confirmar +0,1–0,2 R: el resultado da dirección, se registra y la familia queda sin más aperturas.

## Justificación económica / cómo podría refutarse
Un cierre a 3 desvíos del VWAP de la sesión es una extensión que los participantes de valor (VWAP como referencia de ejecución) tienden a
devolver en el día. Refutación: R neto ≤ 0 en el holdout y en forward con n ≥ 30.
