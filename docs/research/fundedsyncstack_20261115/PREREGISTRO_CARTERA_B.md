# Cartera B: FUNDEDSYNC T + Z + R como cartera aparte (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de cualquier dato forward de la cartera B. Pedido de Nico: «mantenerla como una cartera aparte,
diversificada y diferenciada, y hacerle seguimiento como tal». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Composición (congelada; ficha `CARTERA_B_OPERATIVA.json`)
- **T** (FtmEngine), **Z** (ZetaTrendDay), **R** (AtrPhase), valores de fábrica, **1 MNQ cada una**; Z y R con stop de catástrofe 0,5 × ATR20
  (vía MAE). Variante paralela (no reemplaza): T filtrado por el sesgo Franklin (`reels_20261116/ACTA_HOLDOUT_FRANKLIN.md`).
- Por qué aparte y no dentro de la 50K de la v2: en una cuenta de drawdown arrastrado de 2.000 la quema sube a 12–22 %; en cuenta propia de
  drawdown fijo la quema es 0,1–2,5 % (abajo). El criterio de quema se mide en la cuenta que le corresponde.

## Evidencia de desarrollo (descriptiva; 1 MNQ por regla)
2020 → 2026-09: +80 mil USD, t 7,9, drawdown máximo −2.256; todos los años positivos (+3,8k a +17k). Pasa / quema con media contraída: 50K
arrastrada 35 % / 12 %; fija 3.500 (120 días) 64 % / 0,9 %; fija 5.000 64 % / 0,1 %. Desde ago-2025: 55/22, 81/2,5, 82/0,4. Con la v2:
correlación diaria 0,09, mensual 0,23; 0 días con las dos < −300 USD (v2 10, B 8). Límites: T es lo sólido (holdout Fisher 0,020); Z aporta
poco; R tiene 5 operaciones fuera de muestra; los parámetros de fábrica pueden venir de estos mismos años → el forward decide.

## Seguimiento (sin calendario fijo: cuando Nico sube datos sellados)
`python tools/seguimiento_forward.py <HASTA>` corre todo (cartera v2/v3, T+Z+R, Franklin) y escribe para la cartera B, desde 2026-11-14:
USD por día, acumulado, drawdown desde el máximo, distancia a los límites de la cuenta de referencia (drawdown fijo 3.500 y objetivo 3.500,
hasta que Nico fije la cuenta real) y e-proceso de la canasta (el de `PREREGISTRO_TANDA2.md` L2). Vista conjunta con la v2: correlación
diaria, días con pérdida simultánea y peor día sumado.

## Lectura (declarada)
- EDGE si el e-proceso de la canasta llega a 10. ALERTA si el drawdown forward supera 2.256 (el máximo de desarrollo) o la distancia al
  límite de la cuenta baja de 1.000. Diversificación vigente mientras la correlación diaria forward sea < 0,3 con ≥ 20 sesiones comunes.
- Nada cambia composición, tamaño ni stops por lo que muestre el forward; un cambio es una versión nueva con su pre-registro.

## Justificación económica / cómo podría refutarse
T: ruptura del rango de apertura con capa de vecinos; Z: días de tendencia; R: fase de ATR. Son mecanismos distintos de los de la v2 (zonas,
gaps, preapertura), por eso la correlación baja. Se refuta si el forward en USD queda ≤ 0 con el e-proceso a favor de la nula, o si la
correlación con la v2 sube a ≥ 0,3.
