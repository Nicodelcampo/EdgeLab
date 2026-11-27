# BONOS-RATIOS: el ratio ley NY / ley local vuelve a su media, pero cada vez menos (resultado, 2026-11-27)

Estado: RESULTADO — EF2 pre-registrado en [PREREGISTRO.md](PREREGISTRO.md) (4 pruebas, `RATIOS_BONOS_AR`). Sin P&L. Meses HOLDOUT y
TERMINAL de A5 sin leer. Herramienta: `python tools/bonos_ratios.py medir` (`RESULTADO.json`).

## 1. Resultado principal (Δ de las ruedas t+1 → t+6 sobre el desvío contra la media de 20 ruedas; pendiente < 0 = reversión)
| Par | DESC: pendiente (t) | BH q 0,10 | REP: pendiente (t) | Replica | Vida media (ruedas, DESC/REP) | Desvío de 2 sd |
|---|---|---|---|---|---|---|
| GD30/AL30 | −0,25 (−2,79) | sí | +0,03 (+0,14) | **no** | 13,5 / — | 3,9 % |
| GD35/AL35 | −0,21 (−1,87) | sí | −0,37 (−2,93) | **sí** | 16,5 / 9,0 | 3,1 % |
| GD38/AE38 | −0,17 (−1,53) | sí | −0,22 (−1,90) | **sí** | 19,9 / 15,7 | 3,5 % |
| GD41/AL41 | −0,14 (−1,50) | sí | −0,44 (−2,26) | **sí** | 23,7 / 7,5 | 4,1 % |

- **Hay reversión y no es rebote.** La medida salta una rueda, y sin el salto la reversión es apenas mayor (t −2,6 a −4,4). El rebote
  entre puntas existe (lag-1 de −0,1 a −0,3), pero no explica el efecto.
- **Escala:** la vida media es de 7 a 24 ruedas. A escala diaria, esto es swing de una a cuatro semanas, no el scalping intradía del video,
  que esta medición no cubre.

## 2. Lo que baja la confianza: el efecto se achica con el régimen
| Par | 2021-09 → 2023-11 (cepo) | 2023-12 → 2025-04 | 2025-04 → 2026-11 (sin cepo) | Desvío de 2 sd hoy |
|---|---|---|---|---|
| GD30/AL30 | t −1,82 | t −0,63 | t −1,53 | **0,8 %** |
| GD35/AL35 | t −2,75 | t −1,01 | t −1,31 | 1,1 % |
| GD38/AE38 | t −1,86 | t −1,58 | t +0,11 | 1,3 % |
| GD41/AL41 | t −3,15 | t −0,34 | t −0,43 | 1,7 % |

Lectura:
- Con cepo, la brecha de ley se movía 4–6 % (2 sd) y volvía en 2–3 semanas.
- Desde la salida del cepo, los desvíos de 2 sd son 0,8–1,7 % y la reversión no es significativa en ningún par.
- **Contra el costo de ≈ 0,36 % de ida y vuelta** (las dos patas más los derechos), el margen en cierres diarios es hoy de 2 a 5 veces el
  costo en el extremo de 2 sd, pero sin reversión demostrada en el régimen actual.
- GD30/AL30, el par más operado, es justamente el que no replica: es el más arbitrado.

## 3. Qué deja
- **Mecanismo:** la prima de ley vuelve a su media en pares del mismo flujo, y lo hace con fuerza en regímenes de cepo.
  Es información para la familia, no un edge operable hoy.
- **Lo que no se puede medir acá:** la versión del video es intradía. Para medirla hace falta grabar puntas hacia adelante (data912
  `/live/arg_bonds` o IOL), y queda pendiente como decisión de Nico.
  - Con los cierres diarios, en el régimen actual, no hay evidencia.

Diagnóstico de grilla: sin grilla. Ventana 20, horizonte 5 y salto 1, fijados por la charla; los diagnósticos (sin salto, regímenes,
lag-1) se publican completos.
Episodios: la reversión se apaga después de la salida del cepo (2025-04): t entre +0,11 y −1,53 en los 4 pares, contra −1,82 a −3,15
en 2021–2023.

Aporte al referente: mide con datos la idea del video y separa lo real (la prima de ley revierte, sobre todo con cepo) de lo operable hoy
(sin evidencia a escala diaria). Señala que el único camino que queda es el intradía grabado hacia adelante.

## Addendum de auditoría (2026-11-27, Antigravity)
- **Etiqueta de fecha vs custodia real:** el cuadro del §2 rotula `2025-04 → 2026-11`, pero en `tools/bonos_ratios.py` el filtro `ok = d.bloque.isin(["DESC","REP"]) & d.bloque_fut.isin(["DESC","REP"])` corta antes del `2026-10-01` (y excluye bordes que tocan `HOLDOUT`/`EMBARGO`). La custodia de `TERMINAL >= 2026-10-01` está intacta.
