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
