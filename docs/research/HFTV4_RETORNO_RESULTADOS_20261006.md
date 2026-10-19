# HFTV4-RETORNO — ¿el precio vuelve a las zonas HFT de las que se alejó? — resultados MNQ — 2026-10-06

Manifiesto: `HFTV4_RETORNO_MANIFIESTO_20261006.md` (aprobado a priori por Nico). Kernels `edgelab-hftret-mnq-k1..k4` +
`edgelab-hftv4-retorno-20261006`. JSON: `hftv4_retorno_20261006/`.

**Muestra:** 6 contratos MNQ, 50t, RTH.
- **138.225 flechas reales** (sin V) contra **473.103 de pseudo-zonas** con la misma regla.
- Se excluyeron 115.783 zonas en V. 443.668 zonas reales nunca dieron flecha.

## Formal (Holm 4): significativo, pero el efecto es mínimo
| | zona real | pseudo-zona | β (FE) | z |
|---|---|---|---|---|
| vuelve al borde cercano ≤ 200 barras | 76,8 % | 75,0 % | **+0,9 pp** | 6,0 |
| vuelve ≤ 1.000 barras | 89,6 % | 88,6 % | +0,6 pp | 5,4 |
| recorre la zona entera ≤ 200 | 69,7 % | 67,7 % | +0,9 pp | 5,4 |
| recorre la zona entera ≤ 1.000 | 86,1 % | 84,9 % | +0,6 pp | 5,3 |

## Lectura
- **Lo que Nico ve es cierto:** el precio vuelve a la zona en el 77 % de los casos antes de 200 barras y en el 90 %
  antes de 1.000.
- **Pero vuelve casi igual a una banda cualquiera** a la misma distancia (75 % / 89 %). Es la probabilidad de cruce de
  un nivel cercano en un mercado que va y viene. La zona HFT agrega **≈ 1 punto porcentual**: es estadísticamente real
  (n enorme), pero económicamente despreciable.
- **Perfil del camino de vuelta, igual al de las pseudo-zonas:** mediana de 27 barras hasta el retorno, y en el medio
  el precio se aleja todavía más, con una mediana de **6 alturas más** (p75 de 12 y p90 de 25). Una entrada de
  reversión hacia la zona en el momento de la flecha soporta, típicamente, una excursión en contra de varias veces lo
  que ya recorrió.
- Por tipo: Ultra +1,5 pp, Predator +0,6 pp, Absorb +0,7 pp. Ninguno cambia el panorama.

## Estado
`RETORNO A ZONAS HFT ≈ RETORNO A CUALQUIER NIVEL (+1 pp)`. No es base para una lógica de reversión: el "suele volver"
es la tasa base del mercado, y el costo de esperar la vuelta (excursión de 6 alturas) es el mismo que con un nivel al
azar.
