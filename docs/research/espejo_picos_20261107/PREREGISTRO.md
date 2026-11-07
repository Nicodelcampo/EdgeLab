# Pre-registro: ESPEJO-PICOS — el espejo clasificado por qué picos tomó la ida (07/11/2026)

Estado: PRE-REGISTRO (commiteado antes de lanzar, pedido de Nico «lanzá los picos»). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF2**. La base sin condicionales ya se observó: `espejo_macro_10t_20261107/RESULTADO_BARRIDO.md` (sin edge; NQ réplica
−0,18 R/op).

## Hipótesis (Nico)

Si el primer impulso existió para tomar picos de liquidez, cuando los tomó el motivo desapareció. Entonces la vuelta completa el espejo
(llega a A) o va más allá.

**Cómo podría refutarse:**
- los espejos con picos tomados no llegan a A ni lo pasan más seguido que los que no tomaron ninguno, a igual ancho, duración y
  horario; o
- la diferencia no se ve en R neto.

## Definición (`edgelab/research/espejo_picos.py`, tests en `tests/research/test_espejo_picos.py`)

- **Detector:** el del espejo con la base corregida: topes en tiempo (60 / 120 min) y ancho mínimo laxo de 5 viajes, como
  ESPEJO-MACRO-10T-ANCHO. Con la base original ES no tenía eventos. Los módulos padre no se tocan.
- **Pico:** pivote del lado del impulso de w velas de 10 ticks, confirmado antes de A y vivo (sin romper) hasta A. Los picos vivos
  forman una escalera, como en `tools/peaks_rule.py`.
- **Tipo** (perilla, decisión de Nico: los dos):
  - **cualquiera:** todo pico vivo en las 2000 velas previas a A;
  - **consecutivo:** sólo los de series de 3 o más con separación ≤ 60 velas (w = 3) o ≤ 200 velas (w = 10).
- **Escala del pivote:** w = 3 o w = 10.
- **Antigüedad del pico** (enmienda de Nico, 07/11, antes de cualquier corrida: «si son recientes tienen una importancia distinta»):
  edad = tiempo desde la vela del pico hasta A. Perilla de grupo con bandas disjuntas:
  - **recientes:** confirmados hasta 30 min antes de A (la ida dura como máximo 60 min: es la liquidez de la sesión en curso);
  - **viejos:** más de 30 min antes de A;
  - **todos.**
  La banda se aplica antes de armar las series, así que «consecutivo reciente» es una serie de picos recientes. «Quedan» se cuenta
  dentro de la misma banda.
- **Qué tomó la ida:**
  - cantidad de picos tomados: 0, 1–2, 3+ o cualquiera;
  - posición media dentro del impulso: inicio, medio o final;
  - sobrepaso del último pico tomado: ≤ 0,10 W, ≤ 0,25 W o más;
  - si quedaron picos vivos más allá del extremo.
- **Perillas del padre que quedan:** fracción de entrada (25 / 50 / 75 %), ancho en viajes (≥ 5 / 10 / 20) y RTH. Los retrocesos
  quedan fijos en el laxo (0,40).
- **Ejecuciones (8):** stop en B (1 tick o 10 % de W) × objetivo A, 1,25 W, 1,5 W (más allá de A, la hipótesis) o 2R.
- **Tamaño:** 777.600 celdas por canal (259.200 × 3 bandas de antigüedad).

## Enmienda del 07/11 (antes de correr)

Las cuatro campañas se lanzaron al conductor a las 23:16 y quedaron en cola sin subir nada a Kaggle (sin handle, sin datos vistos).
Se frenó el conductor, se agregó la antigüedad, se borraron los estados sin corrida y se relanzó con este documento. Ningún resultado
de esta familia existía al enmendar.

## Orden de medición

1. **Información, sin P&L:** probabilidad de llegar a A y de pasarlo (1,25 W y 1,5 W) por clase y por antigüedad (recientes contra
   viejos), contra el control emparejado. El
   control son los espejos sin picos tomados con el mismo ancho, duración y horario.
2. **Embudo en R:** ESPEJOPICOS-{NQ,ES,YM,GC}, con linaje hijo de la variante en tiempo de cada activo (y de la de ancho en ES e
   YM): hereda su multiplicidad bruta.

## Después (fase 2)

La misma estructura de «qué tomó la ida» con:
- niveles de sesión (máximos y mínimos del día previo, overnight, OR30, VWAP);
- gaps;
- volumen de la ida y clímax en B;
- OG/VI de LuxAlgo, zonas HFT, aVolZone y BigTrap2.
