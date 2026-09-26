# HFT-REV-EXP — ¿la zona HFTZonesNQPureV4 anticipa la reversión? (MNQ, exploratorio, 2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pedido de Nico (2026-09-26):** en algunos casos el precio vuelve a una zona HFT y revierte (verde → rebote alcista,
roja → rebote bajista). La mayoría de las veces no pasa. ¿Pasa por algo distinto al azar? ¿Tiene un mecanismo? ¿Se
puede anticipar cuándo? Arrancar exploratorio: cuántas zonas hay así, excursión y penetración promedio.
**Estado:** exploratorio y descriptivo. No es una búsqueda sobre P&L: no hay entradas, costos ni selección de celdas.
Todas las celdas se publican. Si algo aparece, la confirmación va a un manifiesto aparte con el STOP de siempre.

## Registro de familia

- **Indicador:** `HFTZonesNQPureV4`, motor `HFTZonesUniversal`, perfil `SCALED_FUNNEL_V1` de MNQ (el del visor de la
  captura). Parámetros congelados en `edgelab/bridge/indicators/hftzones_universal_profiles.json`. Paridad con NT8:
  `PARITY_ABSTAIN` en MNQ (lo que se mide es el port de Python, no el chart).
- **Independiente** de HFTZones-ES (5 mediciones, sin efecto) y de BigTrap2 imán (cerrado). No se transportan
  resultados, poblaciones ni presupuesto de multiplicidad.
- **Datos:** `MNQ_09-25_ticks.parquet` (Kaggle `edgelab-ticks-mnq-preholdout`, sha256 `ae98f789…b927`), jul–sep 2025.
  Corte duro en 2026-04-01: nada de confirmación ni holdout.

## Espacio de eventos (escrito antes de congelar la población)

| Familia | Qué sería | ¿Se mide acá? |
|---|---|---|
| Creación | la zona recién formada | no (el precio está en el borde: no hay «vuelta») |
| Aproximación | el precio se acerca sin tocar | no |
| **Primer retorno al borde cercano** | se aleja D ticks y vuelve a tocar el borde | **sí: es lo que muestran las capturas** |
| Toque n-ésimo | segundo y siguientes retornos | no (queda para después) |
| Invalidación | cruza el borde lejano antes de alejarse | se cuenta, no se mide desenlace |
| Expiración | fin de sesión sin retorno | se cuenta como «no vuelve» |
| Confluencia | varias zonas superpuestas | no (se puede cortar después con el mismo censo) |
| Estado continuo | distancia a la zona activa más cercana en cada barra | no (alternativa con más potencia; próximo paso si el evento no alcanza) |

**Por qué el primer retorno:** es el fenómeno de las capturas y el único que responde «¿la zona anticipa la
reversión cuando el precio vuelve?». **Cómo podría refutarse la elección de población:** si la tasa de reversión del
primer retorno no difiere de los controles pero sí la del estado continuo o la del toque n-ésimo, esta población era la
equivocada.

## Definiciones

- Verde (`HFT_BUY`): borde cercano = techo, borde lejano = piso, reversión esperada alcista. Roja: al revés.
- Alejamiento D ∈ {8, 20, 40} ticks; reversión R ∈ {16, 40, 80, 160} ticks desde el borde cercano; ruptura = borde
  lejano + 2 ticks. Horizonte: hasta el fin de la sesión.
- Por evento se registra: si revierte o rompe, la penetración máxima antes del desenlace (ticks y % del ancho W), el
  tiempo hasta el toque y hasta el desenlace, y MFE/MAE a 5, 15 y 60 min desde el toque.

## Controles (mismo seguidor de camino)

1. **Nivel:** por cada zona real, 3 zonas falsas de igual ancho, color y hora, con el borde cercano en un precio que el
   mercado operó en los 30 min previos. Si la zona real no revierte más que esto, la zona no aporta nada.
2. **Polaridad:** la misma zona real leída con el color opuesto. Responde si el color importa.
3. **Caminata aleatoria:** P = (W + 2) / (R + W + 2), sin memoria.

Diferencias con IC 95 % por bootstrap de sesiones (las zonas de una misma sesión no son independientes).

## Justificación económica y cómo podría refutarse

- **Mecanismo candidato:** un barrido rápido comprador deja órdenes límite pasivas del otro lado o posiciones de
  quienes barrieron; al volver al precio, esas posiciones se defienden y el precio rebota.
- **Explicación alternativa:** el rebote es genérico en cualquier nivel reciente (reversión a la media de corto plazo).
  Es lo que pasó con BigTrap2 imán (F2.8: un control sin zona con la misma geometría daba lo mismo).
- **Se refuta** si la tasa de reversión real no supera al control de nivel con IC que excluya el cero, en el tamaño de
  reversión útil (R ≥ 40 ticks). Todo nulo publica su MDE.

## Resultado — MNQ 09-25 (2026-09-26)

**Procedencia:** código `tools/hft_reversion_explore.py` idéntico al de `b4bcfd1`. La corrida arrancó con el archivo
sin commitear y el contenido no cambió después. Artefacto `artifacts/research/hft_rev_exp/MNQ_09-25/reporte.json`
(sha256 `214ee3f6afb7536e…`). 36 sesiones, 29.635 zonas.

### Cuántas zonas hay «así»

| Paso | D = 20 ticks | D = 40 ticks |
|---|---|---|
| Zonas | 29.635 (≈ 820 por sesión) | 29.635 |
| Se alejan D y vuelven al borde | 6.224 (21 %) | 3.670 (12 %) |
| Revierten 40 ticks (10 pts) antes de romper | 1.617 (26 % de las que vuelven) | 26 % |
| Revierten 80 ticks (20 pts) | 963 (15,5 %) | 15,8 % |

### Penetración y excursión (D = 20)

- **Antes de revertir, el precio entra 6 ticks de mediana (1,5 pts)**, 6,9 de media, 14 en el percentil 90. Es la
  mitad del ancho de la zona (49 % de W en promedio).
- **Tiempo hasta el toque:** 48 s de mediana.
- **Excursión desde el toque, simétrica:**

| Horizonte | MFE media | MAE media |
|---|---|---|
| 5 min | +68 t | −68 t |
| 1 h | +209 t | −197 t |

  No hay sesgo direccional apreciable. Las zonas reales se mueven más que las del control de nivel (1 h: ±200 contra
  ±180): **aparecen en momentos de más volatilidad, no de más dirección.**

### ¿Distinto al azar? Todas las celdas

| D | R | Real | Caminata aleatoria | Real − nivel [IC 95 %] | Real − polaridad [IC 95 %] |
|---|---|---|---|---|---|
| 8 | 40 | 0,250 | 0,244 | +1,1 pp [−0,1, +2,4] | +2,5 pp [+1,2, +3,9] |
| 20 | 40 | 0,260 | 0,253 | +1,9 pp [+0,8, +3,1] | +2,7 pp [+1,1, +4,4] |
| 20 | 80 | 0,155 | 0,148 | +1,5 pp [+0,6, +2,4] | +2,4 pp [+1,0, +3,7] |
| 40 | 40 | 0,264 | 0,258 | +2,4 pp [+0,9, +3,9] | +1,9 pp [−0,2, +4,0] |
| 40 | 80 | 0,158 | 0,151 | +1,8 pp [+0,8, +2,8] | +1,6 pp [−0,0, +3,2] |
| 40 | 160 | 0,082 | 0,083 | +1,1 pp [+0,0, +2,2] | +0,8 pp [−0,6, +2,3] |

Las 12 celdas están en `reporte.md`. **MDE ≈ 1,5 pp** (media amplitud del IC ≈ 1,1 pp × 1,4).

### Lectura

1. **La mayoría de las reversiones que se ven en el chart son las que daría el azar.**
   - Con el ancho típico de la zona, una caminata sin memoria revierte 40 ticks el 25 % de las veces; la zona real,
     el 26 %.
   - Lo que el ojo ve como «la zona predijo el giro» es, casi siempre, la geometría: 3 de cada 4 veces el precio
     atraviesa, y la vez que no, queda dibujada.
2. **Hay un exceso chico pero real, de +1 a +2,5 pp**, contra el control de nivel y contra la polaridad opuesta. Crece
   con el alejamiento previo D. El color importa un poco: la zona revierte más en su dirección que leída al revés. Es
   del mismo orden que la información de TBZX en ES (+2–3 pp) y del mapa IVC: existe y es mucho más chica que la
   fricción.
3. **El mecanismo candidato no queda demostrado.** Un exceso de 1–2 pp es compatible con órdenes pasivas defendidas,
   pero también con la reversión de corto plazo después de un alejamiento grande: el control de nivel también se
   aleja D. Separarlos exige el control de estado de abajo.
4. **Por subtipo:** Predator y Ultra se comportan igual. Absorb (zonas de < 4 ticks) revierte poco, lo que la
   caminata predice para su ancho.

### Qué sigue (exploratorio, sin P&L)

- **¿Cuándo pasa?** El exceso promedio es chico; la pregunta es si se concentra. Próximo corte, sobre el mismo censo:
  velocidad y volumen del barrido, edad de la zona al toque, confluencia con otras zonas, tendencia de 15/60 min, hora
  del día y lado. Se publica el landscape completo con corrección por multiplicidad y se compara siempre contra el
  control de nivel.
- **Replicación** en MNQ 12-25 y 03-26 (pre-abril) antes de creer cualquier corte.
- **Población alternativa:** estado continuo (distancia a la zona activa más cercana en cada barra), con más potencia.
