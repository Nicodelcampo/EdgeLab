# AVCL-DIST — distribución completa del desplazamiento — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_DIST_MANIFIESTO_20261006.md`. Kernel `edgelab-avcl-dist-20261006`, 134 s, sobre el cache de VOL-2.
- JSON: `avcl_vol1_20261005/AVCL_DIST_RESULTADOS.json`. 6 pruebas más en el registro, familia `AVCL_DIST`.
- Origen: el pedido de Nico de no quedarse con la media del canal direccional (SR-DIR).

## Formal (6, Holm, bilaterales). Cola = movimiento ≥ 1 rango previo (R) en H barras
| prueba | Δ prob. contra control | tasa control | Holm |
|---|---|---|---|
| OFF H10 cola de **alejamiento** | **+1,08 pp** | 7,8 % | <1e-4 |
| OFF H10 cola de **regreso** | **+1,11 pp** | 9,4 % | <1e-4 |
| OFF H50 alejamiento | +0,42 pp | 6,9 % | 0,068 |
| OFF H50 regreso | −0,03 pp | 8,1 % | 0,88 |
| AT H10 cola sin signo | **+3,81 pp** | 17,5 % | <1e-4 |
| OFF H10 cola sin signo | **+1,96 pp** | 17,5 % | <1e-4 |

## Lectura pre-registrada: **expansión bidireccional**
A 10 barras, **las dos colas suben lo mismo** (+1,1 pp cada una, unos +12–14 % relativo). La curva de cuantiles de
`s/R` está **estirada simétricamente**: p5 −1,31 contra −1,24, p95 +1,21 contra +1,14, mediana ≈ igual.
La media ≈ 0 de SR-DIR **no escondía una dirección**: escondía un **ensanchamiento de los dos lados**. A H50 todo vuelve
a ≈ 0, igual que la curva B de VOL-2.

Implicancia: el sello sirve para **volatilidad / rango** (breakout bilateral, ensanchar el stop en la ventana,
estructuras sin dirección), no para elegir lado. Las capturas de Nico (alejamientos grandes) son reales, pero la otra
mitad de los casos sale con la misma fuerza hacia el otro lado.

## Descriptivos que importan
- **Zona angosta** (quintil inferior de ancho): las dos colas suben **+3,5 pp y +3,3 pp** (unos +40 % relativo).
  Es el subconjunto donde el efecto es grande. **Zona ancha**: las dos colas *bajan* (−1,4 / −1,1 pp).
- **Alta anomalía (Q5)**: la cola de **regreso** sube +2,4 pp contra +0,65 pp la de alejamiento. Es una asimetría hacia
  "volver" en las zonas más intensas. Es descriptiva y queda como hipótesis a pre-registrar.
- Umbral 2R (colas extremas): +0,1 pp (MDE 0,15). No hay engorde de colas extremas; el estiramiento es moderado.
- AT: |mov|/R estirado en toda la distribución (mediana 0,54 contra 0,48 a H10).

## Estado
`EXPANSIÓN BIDIRECCIONAL CONFIRMADA (H10) — sin sesgo direccional, ni en la media ni en las colas`. Los subconjuntos
con más señal son las zonas angostas (las dos colas) y las de alta anomalía (asimetría de regreso, no confirmada).
