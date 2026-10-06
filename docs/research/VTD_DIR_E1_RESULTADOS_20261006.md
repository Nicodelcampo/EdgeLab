# VTD-DIR etapa 1 — predictores del lado del tramo largo en marcas VolTicksDef — resultados MNQ — 2026-10-06

- Propuesta + enmienda 1: `VTD_DIR_PROPUESTA_20261006.md`. Kernels `edgelab-vtddir-mnq-k1..k4` +
  `edgelab-vtddir-analisis-20261006`.
- JSON: `vtd_dir_20261006/VTD_DIR_RESULTADOS.json`. Registro: 110 pruebas (100 EMA + 10 fijas), familia `VTD_DIR`.
- Resultado: `asim_H = (U − D)/(U + D)` desde el close de la marca (150t); acierto = signo(pred) × asim. RTH.

## Formal — descubrimiento (MNQ 09-25, 12-25, 03-26; 1.062 marcas): **NADA PASA**
- **EMA (100 celdas, max-T):** 51 de 100 celdas positivas, media +0,002. Mejor p_maxT = 0,56 (EMA 240 min, "cerca
  < 0,5 ATR", n = 10). **El mapa es ruido: ni pico ni meseta.**
- **Fijos (Holm 10):** VWAP −0,003; desbalance +0,018; vela +0,027 (p 0,11); momentum +0,024; extremos +0,029
  (n = 72). Todos con Holm = 1. MDE ≈ 0,05.
- **Confirmación:** vacía, porque nada pasó el descubrimiento. Los contratos de confirmación no se usaron para ninguna
  prueba formal.

## Descriptivo — los 6 contratos (2.607 marcas): un indicio a tratar con cuidado
| predictor | marcas H10 | marcas H50 | barras al azar H10 |
|---|---|---|---|
| **vela marcada (P4)** | **+0,044** (se 0,012) | **+0,041** (se 0,013) | +0,003 |
| desbalance 20 barras (P3) | +0,034 (se 0,013) | +0,018 | +0,002 |
| momentum 50 (P5) | +0,027 (se 0,012) | +0,017 | +0,001 |
| EMA 200 barras, sin límite | +0,027 (se 0,011) | — | +0,002 |
| VWAP | +0,003 | −0,010 | +0,001 |

Lectura honesta:
- Los predictores de "flujo/impulso" (vela, desbalance, momentum, EMA corta) dan **pequeños positivos en las marcas y
  ≈ 0 en barras al azar**. Si fuera real: **en una marca VTD, el lado de la vela anticipa levemente el lado del tramo
  largo**. Un +0,044 en asim equivale a acertar el lado ≈ 52 % de las veces.
- **No se puede promover:**
  - (1) no pasó el descubrimiento formal (vela p = 0,11);
  - (2) el "+0,044" mezcla contratos de descubrimiento y de confirmación, mirados **después** del fallo formal. Usar
    esos contratos para elevarlo sería data snooping;
  - (3) en estos datos la asim media de las marcas es +0,031 (deriva alcista del período), y cualquier predictor que
    se incline hacia arriba en un rally recibe crédito. Hay que controlar la deriva.
- Por régimen de amplitud (descriptivo): sin patrón consistente. La vela da +0,03 / +0,06 / +0,05 (H10) y +0,00 /
  +0,05 / +0,07 (H50) en comprimido / medio / expandido. Hay una insinuación de que la vela funciona mejor fuera del
  régimen comprimido, pero sin potencia.

## Estado
- **EMA como filtro de dirección en marcas VTD (150t, MNQ):** sin efecto en toda la grilla. Coherente con la etapa 0:
  la tendencia no persiste a esta escala.
- **VWAP, extremos:** sin efecto.
- **Vela marcada (y, más débil, desbalance):** indicio descriptivo, **no confirmado**. El único camino limpio es
  pre-registrarlo y probarlo **una vez** en datos no usados: MGC, ES/MES, NQ y YM, con control de deriva (signo
  relativo al retorno medio de la sesión).
- Aun si se confirmara, con ≈ 52 % de acierto de lado el valor dependería de la asimetría típica (≥ 3:1 en el 57 % de
  los casos) y del costo. Eso exige un manifiesto de P&L con STOP aparte.
