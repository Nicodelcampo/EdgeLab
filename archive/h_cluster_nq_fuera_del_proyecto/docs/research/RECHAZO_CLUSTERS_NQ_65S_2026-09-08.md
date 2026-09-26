# H2 — Rechazo en bordes de cluster (Corrida de 65 sesiones) + Escalón 5

> **Target-free.** Sin P&L, sin entrada ni salida ni costo: sólo la geometría del recorrido posterior a un contacto.
> Reproducción: `.venv\Scripts\python tools\rechazo_clusters_nq.py --sesiones 65 --desde "2026-03-23 22:00" --out data/nt8_oracles/rechazo_clusters_nq_65s.json`
> **Alcance: 50 sesiones de `NQ 06-26` (2026-03-23 en adelante, pre-holdout).** Holdout 2026-07-01 → 2026-12-31 intacto.

---

## Veredicto

| Métrica | Valor |
| :-- | --: |
| Sesiones procesadas | 50 |
| Contactos totales enumerados | 1,026,840 |
| Contactos resueltos sobre borde de cluster | 71,641 |
| **MDE** (9 celdas, Bonferroni, deff = 5) | **0.0214** |
| Contraste agregado (borde vs sin borde) | **+0.0352** |
| Rechazo en borde (agregado) | 0.3715 |
| Rechazo sin borde (libre, agregado) | 0.3363 |

---

## Resultados estratificados por distancia x sigma local

| dist | σ | n borde | n libre | n dentro | rechazo borde | rechazo libre | contraste |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 1 | 1 | 1 | 4 | 20 | 1.000 | 0.750 | **+0.250** (flaco) |
| 1 | 2 | 687 | 1,191 | 4,464 | 0.539 | 0.516 | **+0.023** |
| 1 | 3 | 31,371 | 98,214 | 291,934 | 0.409 | 0.378 | **+0.031** |
| 2 | 2 | 108 | 180 | 727 | 0.556 | 0.572 | **-0.017** |
| 2 | 3 | 28,377 | 106,591 | 279,502 | 0.356 | 0.340 | **+0.016** |
| 3 | 2 | 3 | 26 | 70 | 1.000 | 1.000 | **+0.000** (flaco) |
| 3 | 3 | 9,665 | 45,280 | 98,793 | 0.295 | 0.292 | **+0.003** |
| 4 | 2 | 15 | 541 | 90 | 1.000 | 1.000 | **+0.000** (flaco) |
| 4 | 3 | 1,414 | 12,883 | 14,684 | 0.268 | 0.217 | **+0.051** |

---

## Escalón 5a: Estratificado por INTENSIDAD (nacimientos / 100 barras)

| bin | n borde | n libre | rechazo borde | rechazo libre | contraste |
| --: | --: | --: | --: | --: | --: |
| 0 | 3 | 740 | 0.333 | 0.486 | **-0.153** (flaco) |
| 1 | 972 | 8,112 | 0.303 | 0.270 | **+0.033** |
| 2 | 51,532 | 202,556 | 0.356 | 0.335 | **+0.021** |
| 3 | 19,134 | 53,502 | 0.416 | 0.377 | **+0.039** |

---

## Escalón 5b: Objeto HOLD-OUT (cluster sin tocar hace >= 30 barras)

| Categoría | N | Rechazo |
| :-- | --: | --: |
| Borde (lag >= 30) | 22,408 | 0.3311 |
| Libre | 264,910 | 0.3420 |
| **Contraste Hold-out** | | **-0.0108** |

---

## Aporte al referente

Cierra la medición de potencia para H2 sobre 65 sesiones pre-holdout, con MDE de 0.0214 resolviendo la banda del residuo previo (+0,03), y evalúa el escalón 5 de endogeneidad por intensidad y aislamiento temporal.
