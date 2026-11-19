# FRANKLIN: búsqueda de mejoras antes del holdout (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «antes de abrir el holdout fijate si podés mejorar Franklin». North Star
sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2 → EF3** (exploración chica + confirmación no mirada
de esas variantes). Código: `estrategias_scrapeadas.franklin_variantes` (test de causalidad por prefijo y de igualdad con la base),
corrida `tools/reels_20261116.py franklin_mejoras`.

## Lo que ya se vio (declarado)
La regla base (`1000`, `rango`, `ninguno`, salida al cierre) se midió 2012–2026 en NQ/ES/YM (`RESULTADO.md`): positiva desde 2020 y negativa
antes. Así que el tramo de confirmación de abajo **ya está visto para la base**; las variantes no se vieron en ningún tramo.

## Variantes (32 por instrumento; salida siempre al cierre, que es la palanca F-SALIDA-TECNICA-REGALA-LA-GANANCIA)
- Hora de decisión: 09:45 · 10:00 · 10:30 · `primera` (el primer cierre alineado de 09:59, 10:29, 10:59 u 11:29; más operaciones).
- Stop: `rango` (extremo opuesto de 09:30 → decisión) · `atr` (0,5 × ATR20 RTH desde la entrada; palanca F-STOP-GRANDE-FRENTE-A-FRICCION).
- Filtro: `ninguno` · `vwap_ny` (además del lado correcto del VWAP anclado a las 09:30: el reel de RobotEdge) · `sin_gap` (fuera los días con
  |gap| ≥ 0,5 ATR20: el sesgo puede ser sólo el gap, Kemet) · las dos.
Cada una tiene un mecanismo declarado y ninguna usa un umbral elegido mirando.

## Selección y confirmación
- **Exploración E = 2020-01-01 → 2022-12-31**, NQ y ES (64 pruebas). Elegible: R neto > 0 en NQ **y** en ES, n ≥ 60 por instrumento y
  fricción mediana ≤ 0,08 R. Se congelan las **3 mejores** por la media de los dos R (NQ y ES con igual peso).
- **Confirmación C = 2023-01-01 → 2026-09-29**, NQ+ES juntos: p unilateral (bootstrap por sesión), **BH q 0,10 sobre las 3**, y además R(C) de
  la variante > R(C) de la base. Ganadora: la confirmada con mejor puntaje en E. Si ninguna confirma, al holdout va la base.
- Descriptivo (no decide): 2012–2019, YM y **Russell (US2000 → RTY), que nunca se midió con Franklin**, para la base y las finalistas.
- Holdout después: la ganadora (o la base) en NQ+ES, modo exploratorio, con la probabilidad de azar de desarrollo declarada en su acta.

## Justificación económica / cómo podría refutarse
Decidir antes (09:45) captura más del recorrido; más tarde (10:30) o en el primer alineamiento confirma la aceptación y suma días. El stop por
ATR baja la fricción en R. Los dos VWAP exigen compradores (o vendedores) en control desde la apertura, y sacar los gaps evita que la
alineación sea sólo el gap. Se refuta si ninguna variante confirma en C, o si la mejora no aparece en Russell.

## Contador
Registro global `reels_20261116/FRANKLIN_MEJORAS`: 64 (exploración) + 3 (confirmación) = 67. Linaje: FRANKLIN.
