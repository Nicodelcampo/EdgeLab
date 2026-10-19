# IDEA (Nico, 26/09): agotamiento por flujo → barrido del último extremo participante → reversión confirmada — PENDIENTE

**Estado:** registrada y parametrizada; sin medir. Nace de VREV-A (§6): el agotamiento por precio no alcanzó, y el agotamiento por flujo quedó abierto.

## La secuencia (no se entra en el agotamiento)
1. **Zona de agotamiento por flujo:** en el extremo de un alejamiento, el delta (compras − ventas agresoras) deja de acompañar al precio. Por ejemplo, nuevo extremo con delta menor o de signo contrario (divergencia), o mucho volumen con poco avance (absorción).
2. **Barrido:** el precio **toma el último máximo o mínimo «participante» de esa zona** (el extremo donde hubo volumen o delta), pasándolo por `sweep_ticks`.
3. **Reversión confirmada:** después del barrido, el precio revierte `rev_dist` (en ATR), con `rev_delta` a favor, con un **coeficiente de desplazamiento** `rev_disp` (avance neto / recorrido, o avance por volumen) y una **velocidad** `rev_speed`, dentro de `rev_max_bars`.
4. **Recién ahí la entrada.** Las variantes de SL y TP no están atadas al VWAP: stop detrás del extremo barrido, objetivo por R múltiple, trailing, estructura previa o VWAP como una opción más.

## Parámetros (todos con control deslizante en el diseñador y barridos en grilla pre-registrada)
`exh_div_type` (divergencia de delta / absorción), `exh_window`, `last_extreme_def` (máximo de la vela de mayor volumen o delta de la zona), `sweep_ticks`, `sweep_max_bars`, `rev_dist`, `rev_delta_min`, `rev_disp_min`, `rev_speed_min`, `rev_max_bars`, `sl_mode`, `tp_mode`.

## Restricción de datos (verificada en el proyecto)
El lado del agresor de research-v2 es **válido en NQ (99 %)** y **no en ES (80 %, P-93)**. En YM y MYM **no está verificado**: hay que correr `tools/aggressor_validate.py` antes de usarlo. Orden propuesto: NQ primero, después YM/MYM si su agresor valida. Para ES hace falta el L2 de NT8.

## Controles (lo aprendido)
- Mismo estado y actividad en otra sesión a la misma hora (N-REVVOL).
- **Entrada al azar con las mismas salidas.**
- **Nulo de secuencia:** la misma reversión confirmada (paso 3) **sin** agotamiento ni barrido previos. Contesta si la secuencia completa agrega algo sobre «el precio revirtió x con fuerza».

## Diseñador en el visor (26/09)
Parámetros → **🌊 Agotamiento por flujo → barrido → reversión (diseño)**. Necesita la capa de delta `bundles/delta/<activo>.json` (`tools/build_delta_layer.py`, sólo NQ por ahora, alineada y verificada vela por vela contra el bundle). Construida para NQ 03-26 de dic-2025 a mar-2026.
- **Dibujo:** caja de la zona de agotamiento, línea del último extremo participante, marca de barrido, tramo de reversión confirmada, entrada en la apertura siguiente y SL/TP. Clic en una zona muestra delta de la zona, avance, datos de la reversión (distancia, delta, desplazamiento, velocidad) y RR.
- **Primera observación de diseño (sin desenlaces):** con los valores iniciales, 480 de 488 zonas de NQ en enero terminan «barridas», porque el último extremo participante suele quedar por debajo del extremo final y el precio lo supera casi siempre. La definición del extremo participante y el barrido mínimo son lo primero a ajustar.
