# EMA-SEP — contrarian cuando las 3 EMAs están muy separadas — resultados (MNQ y MGC, 10t) — 2026-10-07

Manifiesto: `EMASEP_CONTRA_MANIFIESTO_20261007.md` (+ enmienda 1: agotamiento, OK de Nico). Kernels `edgelab-sep-*`. Los
kernels mnq1 y mgc2 fallaron al arrancar (falla intermitente de Kaggle), se relanzaron sin cambios, y el análisis se
corrió con los 12 contratos. JSON: `emasep_20261007/`.

## Resultado: 0 de 972 celdas pasan max-T
| | celdas | con neto > 0 | mediana del neto (USD/trade) | mejor celda |
|---|---|---|---|---|
| MNQ | 486 | 3 | −2,52 | +0,32 (p90, clímax, límite +10t, SL80 R4; n = 2.649) |
| MGC | 486 | 111 | −2,73 | +12,2 (p90, desaceleración, límite, SL80 R4; n = 304) |

- **Ir en contra rinde algo mejor que la dirección al azar** (mediana de z ≈ +1 en MNQ, z máx 3,2), pero no alcanza
  después de la corrección por 972 celdas (mejor p max-T = 0,16). Tampoco cubre el costo en MNQ.
- MGC tiene celdas positivas, pero con pocos trades e IC que cruzan cero. Las 111 positivas son una fracción esperable
  con ruido y n chico, y ninguna sobrevive a max-T.
- Los filtros de agotamiento (desaceleración, clímax de velocidad) no cambian el panorama.
- Sin celdas que pasen, la **confirmación no se corrió**.

## Estado
`EMASEP 10t DESCARTADA` para esta definición. Señal débil a favor de la reversión (consistente con ES M1), demasiado
chica para cubrir la fricción. Una línea posible sería la reversión en escalas mayores (horas), donde el costo pesa
menos. Requiere un manifiesto nuevo.
