# OP-1 — fade del nivel limpio con fills pasivos realistas (desarrollo en abr → sep 2026)

Estado: PRE-REGISTRO (2026-11-10, antes de generar la tabla operable y antes del resultado de REBOTE_NIVEL_SESION). Familia
`REBOTE_NIVEL_SESION` (OP-1 es su traducción operable; misma multiplicidad). Etapa: EF3 (desarrollo con P&L); la confirmación es el
holdout. Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Plan: `PLAN_OPERABLE_Y_CUERDAS.md` §2, §7.

## Regla operable (congelada)
- Nivel: «reloj» (cada 600 s, último precio) o «pivote» (máximo/mínimo de 1 min confirmado, W = 3); banda X/4; vida 1.800 s.
- Orden límite en el borde del nivel, **activa recién cuando el precio está a ≥ X/2** de la banda (antes se llenaría en el acto);
  compra en el borde superior si el precio se fue arriba, venta en el inferior si se fue abajo; vence con la vida del nivel.
- Fill (`edgelab/research/fill_pasivo.py`): «atraviesa» (un trade ≥ 1 tick más allá del límite; **el que decide**) y «toca»
  (optimista, sólo informativo).
- Stop X; objetivo X (**primaria**), X/2 y 2X (informativas); salida por tiempo a 900 s; empate stop/objetivo = stop.
- R neto = R bruto − fricción / X (`op_costo_r`, de `edgelab/costos.py`).
- Filtro «nivel limpio»: la celda de distancia × ventana a zonas que deje el banco de REBOTE_NIVEL_SESION, por esta regla mecánica:
  la primera hipótesis previa nominada (orden: `dist_zona_1800`, `dist_zona_3600`, `dist_cluster`, todas estrato > 1 X); si no hay,
  la primera celda nominada en B con signo de rebote; si no hay, la previa 1.

## Prueba (desarrollo, no confirma nada)
Primaria: niveles «reloj», modelo «atraviesa», objetivo X, filtro de la regla → media de R neto por sesión, estabilidad en 5
sub-bloques y p por inversión de signo. Se informa también «todos los niveles» y «el resto» (nivel limpio − resto: ¿el filtro agrega?),
y la grilla descriptiva tipo × modelo × geometría (12 celdas). Análisis: `tools/op1_niveles.py` (committeado antes de la tabla).

**Nulo de referencia medido antes:** en una caminata al azar sintética, la misma orden con fill «atraviesa» da R bruto ≈ −0,07 (g1):
la selección adversa sola cuesta casi lo mismo que la fricción. El rebote de +0,08 medido como carrera desde el borde NO alcanza;
OP-1 paga sólo si el filtro lleva el rebote bruto a ≳ +0,15.

## Decisión
Pasa a la canasta del holdout (una apertura, regla 08/11, probabilidad de azar de desarrollo declarada) si la primaria da R neto > 0
con ≥ 4/5 bloques positivos y p < 0,10. Si no: OP-1 queda NO_REPETIR con esta geometría y se prioriza OP-3 (veto).

## Pruebas contadas
1 primaria + 23 descriptivas = 24 (`op1/desarrollo`), en la familia REBOTE_NIVEL_SESION.

## Cómo podría refutarse
R neto ≤ 0 en la primaria o inestable; o el nivel limpio no rinde más que el resto (el filtro no agrega).
