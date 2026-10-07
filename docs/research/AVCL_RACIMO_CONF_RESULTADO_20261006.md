# AVCL-RACIMO-CONF — resultado de la prueba única pre-registrada — 2026-10-06

Pre-registro: `AVCL_RACIMO_PREREGISTRO_20261006.md` (commit `a578a7a1`, con enmienda técnica 1). Kernels
`edgelab-racc-{es,ym,rty,mgc}` + `edgelab-avcl-racimo-conf-20261006`. JSON: `avcl_racimo_conf_20261006/`.
Datos: ES, YM, RTY, MGC, 50t. Se excluyó RTY 12-25 por no tener zonas.

## Prueba formal: **CONFIRMA**
- β (racimo − aislada) de `s_50` = **−0,038** (SE 0,018). p unilateral = **0,020**. MDE 0,046.
- n = 4.229 zonas OFF en racimo y 2.741 aisladas.
- **En zonas OFF en racimo, el precio vuelve sobre la zona o la atraviesa más que en las aisladas**, en instrumentos que
  nunca se usaron para descubrirlo.

## Descriptivos
| | β s_50 | SE | n racimo / aislada |
|---|---|---|---|
| ES | −0,019 | 0,022 | 3.641 / 1.208 |
| YM | −0,152 | 0,084 | 95 / 461 |
| RTY | −0,018 | 0,063 | 184 / 277 |
| MGC | −0,123 | 0,037 | 309 / 795 |

- **Los 4 instrumentos son negativos.** ES, que domina la muestra, es el más débil (−0,019); MGC es el más fuerte.
- H10: −0,009. El efecto es de horizonte largo, igual que en MNQ.
- Criterio denso: −0,017.
- **Consolidación posterior, replicada:** `y_pre` H50 AT −0,053, OFF −0,037 (MNQ: −0,06).

## Lectura y alcance
- Es la **primera señal direccional confirmada fuera de muestra** del programa de zonas de volumen.
- Alcance preciso: zonas OFF en racimo (`burst ≥ 3`) de aVolClusterPOI, 50t, comparadas con zonas aisladas en el mismo
  contexto, a 50 barras, medido como asimetría de la excursión.
- **Es chica:** asim −0,04 ≈ acertar el lado ≈ 52 %. El efecto está por debajo del MDE pre-registrado, así que la
  confirmación es justa, no holgada.
- No es P&L. Que sea operable depende de la fricción y de cómo se convierta en entrada/stop. Con un acierto de lado del
  52 % hace falta una asimetría de pagos favorable, y ya sabemos que la asimetría existe en todos lados.
- Riesgo: ES aporta el 86 % de la muestra con un efecto chico. La confirmación se apoya en buena parte en MGC/YM, con
  muestras chicas.

## Siguiente
Manifiesto de P&L (STOP) para la regla direccional "en racimo OFF, operar el regreso hacia la zona": simulación tick a
tick con fricción por instrumento, contra el nulo de la misma regla en zonas aisladas y en pseudo-zonas, con
descubrimiento en MNQ y confirmación en los otros.
