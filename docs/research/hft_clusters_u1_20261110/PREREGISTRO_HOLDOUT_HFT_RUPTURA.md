# Apertura exploratoria del holdout de HFT_RUPTURA — OP-2 en YM y «el cluster grande no defiende»

Estado: PRE-REGISTRO (2026-11-11, pedido explícito de Nico: «abrí el holdout para la regla de YM»). Escrito y committeado ANTES de
leer un solo tick del holdout. Modo exploratorio (decisión del 2026-11-08). **Una sola apertura de la familia HFT_RUPTURA**: por eso
incluye también la confirmación pendiente de «no defiende» (H1), que si no se mide acá pierde su única apertura.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF: EF4
exploratoria (no confirma por sí sola). Familia `HFT_RUPTURA`, cid `HFT_RUPTURA::holdout_exploratorio_20261111`.

## Advertencia previa (escrita antes de mirar)
YM **no pasó** la compuerta de `PREREGISTRO_OP2.md` para ir al holdout (pedía p < 0,10 en DESC y en réplica por separado; dio 0,29
y 0,38). Esta apertura es una excepción pedida por Nico y queda registrada como tal: no cuenta como «pasó el embudo».

## Datos
`nicolasbuttaro/edgelab-holdout-sellado` (ticks NT8 sellados), sesiones desde 2026-10-01 (`edgelab/holdout.py`), con las sesiones
excluidas declaradas (7-oct en CME; ES 29 y 30-oct). Activos: YM (H-YM), NQ y YM (H1). RTY no está sellado: H1 se mide sin RTY.
ES se procesa (tabla) pero no entra en ninguna prueba. El lector sellado no tiene la marca `outside_regular` (pausa 16–17 CT); en
desarrollo esos ticks se descartaban: en la pausa no hay negociación, la diferencia esperada es nula y queda declarada.

## Reglas congeladas (las mismas de desarrollo, sin cambios)
- **H-YM (pedido de Nico):** OP-2 en YM, cluster `K4_A025_V1800` (E0-b), evento D0, entrada a mercado en el tick del toque a favor de
  la llegada, stop X, **objetivo X** (geometría primaria `g1`; NO la 2X, que se ve mejor en DESC y no replica), salida a 900 s, empate
  stop. R neto = bruto − fricción / X (fricción de `edgelab/costos.py`). Código: `edgelab/research/op2_clusters.py`. H: R neto medio > 0.
- **H1 (no defiende):** real − control de `rompe` (carrera ±X tras el primer regreso al cluster), por sesión, NQ + YM, como en
  `tools/confirmar_no_defiende.py`. H: diferencia > 0.

## Estadístico y combinación (declarados antes)
- p del holdout: inversión de signo por sesión (`banco_eventos.estabilidad`, unilateral), con 5 sub-bloques.
- Probabilidades de azar de desarrollo: H-YM 0,286 (DESC) y 0,381 (réplica); H1 0,088 (DESC, activos independientes) y 0,052 (réplica).
- Combinación: **Fisher** de las tres p por hipótesis; BH q 0,10 sobre las dos combinadas.
- Veredicto por hipótesis: A_FAVOR_COMBINADO (nominada por BH y efecto del holdout > 0), EN_CONTRA (efecto del holdout ≤ 0),
  NO_CONCLUYENTE (positivo sin nominar). Análisis congelado: `tools/op2_holdout.py analizar`, una sola vez.

## Potencia (antes de mirar)
≈ 21 sesiones. YM da ≈ 0,85 operaciones por sesión → ≈ 18 operaciones; con desvío ≈ 1 R, MDE80 ≈ 0,6 R contra un efecto de
desarrollo de +0,03 R: **el holdout solo no puede confirmar ni matar H-YM** (un nulo acá no la mata: K21). H1 tiene más eventos
(NQ), MDE ≈ 0,3 contra +0,09: también baja. Lo que aporta la apertura es la combinación y la dirección; después se sigue en
forward con el e-proceso (`edgelab/funnel/secuencial.py`), válido mirando cada semana.

## Cómo podría refutarse
H-YM: R neto del holdout ≤ 0 (y en el forward el e-proceso no crece). H1: real − control ≤ 0 en el holdout.

## Nunca
Elegir otra geometría, otro activo, otra ventana o ajustar costos con estos datos; reabrir el holdout de HFT_RUPTURA.

## Curva de capital
`OP2_YM_CURVA.svg` / `.json` (`tools/op2_holdout.py`): IS = DESC jul-2025 → mar-2026, OOS = réplica abr → sep 2026, HOLDOUT
desde oct-2026 (se agrega al analizar). La curva IS/OOS se dibujó antes de esta apertura con datos ya mirados.
