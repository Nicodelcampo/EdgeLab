# Picos robustos: diseño y variantes (M1)

Estado: PROPUESTA
Fecha: 2026-11-19 · Origen: dibujo y pedido de Nico (patrones en W con piernas de confirmación, pierna central y cercanía entre picos).
Código: `edgelab/research/picos_robustos.py` · capa del visor: `tools/picos_robustos_visor.py` → `viewer/nt8_bridge/bundles/picos_rob/` ·
tests: `tests/research/test_picos_robustos.py`.

## 1. Qué mide

Un **par** son dos picos consecutivos del mismo lado: P_k con P_k+1, siempre con el siguiente y nunca hacia atrás. Los techos se
miden así; los pisos son el espejo.

```
            P1 ·─── d ───· P2        d  = |P1 − P2|              cercanía entre picos
           /    \       /   \        C  = (P1+P2)/2 − V          excursión de la pierna central
       L1 /      \  C  /     \ L2    L1 = pierna de confirmación izquierda (cuánto subió hasta P1)
         /        \   /       \      L2 = pierna de confirmación derecha (cuánto se alejó después de P2)
        T0         · V         T2    A  = ATR(30) M1 causal en la vela que confirma P2 (unidad)
```

| Factor | Fórmula | Qué traduce del pedido |
|---|---|---|
| fL validez | `1 − exp(−(min(L1,L2)/A) / l0)` | Con piernas de confirmación cortas el pico casi no vale nada. |
| fC central/piernas | `1 − exp(−ρ/ρ0)`, `ρ = C / media(L1,L2)` | Si la central es corta frente a las piernas, el par pesa poco. |
| fK cercanía | `exp(−δ/δ0)`, `δ = d / C` | Cuanto más cerca están los picos, más fuerte el par. La misma distancia pesa menos cuanto más se alejó el precio entre los dos picos. |
| fS tamaño | `1 − exp(−(C/A) / c0)` | La cercanía vale más cuanto mayor fue la excursión. |

Puntaje del par: `S = 100 · combinación(fL, fC, fK, fS)`. Base: l0 = 3, ρ0 = 0,5, δ0 = 0,15, c0 = 4 (en unidades de A).

Los swings salen de un zigzag alterno con umbral `R = r·A` por vela (mínimo 4 ticks). Se reinicia en cada sesión (hueco de más de
30 min).

**Grupo:** se encadenan picos consecutivos del mismo lado mientras cada par nuevo cumpla `δ ≤ 0,35` y el pico nuevo quede a
`≤ 0,35·C` del nivel del grupo. El valor bruto es `n_eff · log(1 + tamaño)`, con:
- `n_eff = 1 + Σ S/100`: cantidad de picos, pesada por la calidad de cada par;
- tamaño = mediana de C/A.

El **valor del grupo** es el percentil de ese bruto contra los grupos ya terminados de las 20 sesiones anteriores, con un mínimo
de 30 grupos. Así cada grupo se compara por tamaño y cantidad con los demás.

## 2. Causalidad

- Un swing se conoce en `cf`, la vela en que el precio se alejó R del extremo.
- El par se emite en la `cf` de P2 con **`Sc`**, que usa L2 medida sólo hasta esa vela.
- **`Sf`** usa la L2 completa. Sirve para mirar, **no** para operar en `cf`.
- El percentil de grupo usa sólo grupos terminados antes.
- El `q` del visor es un percentil sobre todo el período y es **sólo de dibujo**. El test `test_causalidad_corte` verifica que
  cortar la serie no cambia ningún `Sc` ya confirmado.

## 3. Variantes

| Variante | Diferencia | Pregunta que responde |
|---|---|---|
| `A_MULT` | Piernas = swing anterior/siguiente del zigzag; producto | Base literal del dibujo. |
| `B_NIVEL` | Pierna = desde la última vez que el precio estuvo en el nivel del pico (tope 600 velas) | ¿La pierna «real» se ve mejor que el último retroceso? |
| `C_SUMA` | Como B, suma ponderada (0,25/0,25/0,30/0,20) | ¿Un factor flojo debe anular el par (producto) o sólo restar? |
| `D_UMBRAL` | Compuertas duras: piernas ≥ 2 A, ρ ≥ 0,5, δ ≤ 0,25; puntaje = fK·fS | ¿Sirve una definición binaria de «es pico»? Pasa ~4 %, unos 15 pares por día. |
| `E_MULTI` | Como B en tres escalas (r = 1, 2, 4); el mismo P2 queda en la escala mayor | Aparecen dobles techos con un pico intermedio chico. |
| `F_FIJO` | Como B con A fijo por sesión (mediana del ATR de 20 sesiones previas) | ¿La normalización intradía ayuda o confunde Asia con RTH? |

Medido sobre NQ M1 ene–mar 2026, 74 días, `B_NIVEL`, en unidades de A (p10 / p50 / p90):

| Medida | p10 | p50 | p90 |
|---|---|---|---|
| A | 4,3 pts | 9,3 pts | 20,1 pts |
| L1 | 1,1 | 2,3 | 10,2 |
| L2 final | 1,1 | 1,9 | 3,9 |
| C | 1,4 | 2,1 | 3,5 |
| δ | 0,08 | 0,41 | 0,94 |
| ρ | 0,35 | 1,05 | 2,04 |

Con r = 1 salen unos 360 pares por día: es el conjunto candidato y el puntaje filtra. Grupos de 3 o más picos: unos 37 por día.

## 4. Cómo elegir en el visor

`http://localhost:8765/?asset=NQ_M1_2026_ENE_MAR&pr=B_NIVEL`. En el panel ⛰ hay:
- selector de variante;
- puntaje final o causal;
- percentil mínimo;
- casillas de piernas y grupos.

**Elegir sobre ene–mar 2026**, que es la ventana de descubrimiento de la partición A3. jun–sep 2026 es réplica: también tiene la
capa, pero mirarla para elegir la gasta. **El criterio es geométrico:** si los pares de percentil alto son los que Nico llamaría
«picos fuertes» según el dibujo. No vale mirar qué hizo el precio después. Si gana una variante, se congelan sus parámetros antes
de medir cualquier información condicional.

## 5. Justificación económica y cómo podría refutarse

- **Justificación:** un nivel defendido dos veces tras una excursión grande, con piernas amplias a los dos lados, concentra
  órdenes que vuelven a aparecer: stops del otro lado y liquidez en reposo. Si eso existe, el puntaje ordena niveles por la
  probabilidad de reacción o de barrido.
- **Cómo podría refutarse:**
  - Etapa target-free: Nico no distingue a ojo los pares de percentil alto de los de percentil bajo. En ese caso el puntaje no
    capta lo que describe el dibujo.
  - Etapa de información, con su propio pre-registro, linaje y conteo en el registro global: la reacción o ruptura en la
    revisita no varía con el puntaje (`Sc`) con potencia suficiente y MDE publicado, en los dos canales (direccional y no
    direccional). En ese caso el puntaje no informa nada.
  - Esta propuesta no mide nada de eso: no corre desenlaces.
