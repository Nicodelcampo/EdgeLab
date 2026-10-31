# TAU-TENDENCIA — pre-registro (2026-10-31)

Estado: VIGENTE (pre-registrado antes de cualquier corrida sobre datos reales; aprobado por Nico en la sesión en la nube, 31-oct).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo: EF2 (descubrimiento) → embudo automático.
Módulo: `edgelab/research/tau_tendencia.py`; salida en `areas_expansion.simular_cierre_linea`. Campañas: TAU-NQ, TAU-ES, TAU-GC
(familias `TAU_TENDENCIA_<INST>`, independientes entre sí).

## Fuente
Tori Trades, "The Trend Is Your Friend Until the End: A Stopping-Time Theory of Swing Trading with Trendlines and Market Structure"
(26-oct-2026), del paquete del 31-oct: Def. 3.1 (pivotes y estructura), Def. 3.2 y ec. (1) (línea y tiempo de parada τ), Prop. 3.4
(la línea es momentum adaptativo), Prop. 3.5 (ángulo normalizado θ̃ = arctan(β̂/σ̂)) y Prop. 3.6 (significancia con t de Newey-West
sobre retornos, nunca el t de la regresión en niveles).

## Justificación económica
La persistencia de los retornos (reacción lenta, efecto disposición) hace que mantener la posición mientras el precio respeta la
línea de la estructura capture el tramo de tendencia. El aporte específico para EdgeLab es el **pago**: las reglas con acta ganan
seguido poco y pierden de a mucho (W/L 0,23–0,35); una salida que sólo corta cuando la estructura se rompe deja correr las ganancias.

## Espacio de eventos y estados (antes de congelar la población)
Eventos posibles alrededor de una línea de tendencia: creación de la estructura (cambio a HH/HL o LH/LL), toque de la línea, n-ésimo
toque (lo mide TORI-TREND-TOQUE3, otra familia), ruptura de la línea (τ, lo mide TORI como gatillo), ruptura del último pivote
horizontal, throwback, expiración (fin de sesión). Estado continuo: distancia a la línea, pendiente, θ̃. **Se mide**: entrada en la
creación de la estructura y en la ruptura del último pivote a favor (los dos disparos del paper); la línea entra como SALIDA, no como
gatillo. Se descarta como población el toque (ya cubierto por TORI) y el estado continuo (lo cubre la perilla θ̃).

## Qué se mide
- Pivotes de orden 3, 5 y 8 (velas M1) confirmados p velas después; todo se reinicia en cada sesión.
- Disparos ESTRUCTURA y RUPTURA (columna `tipo`). Entrada en el primer tick de la vela siguiente.
- Ejecuciones (4): TAU con δ = 0; 0,5; 1 × ATR14 de la entrada; y el control FIJO_2R (mismo stop, objetivo 2R, sin línea).
  Stop duro: último pivote contrario ∓ 1 tick. Tope del simulador: 240 velas y fin de sesión.
- Perillas: orden de pivote (3), disparo (2), θ̃ a favor (terciles del E0, extremos), t_NW a favor (cualquiera, ≥ 1, ≥ 2) y
  eficiencia de Kaufman de 60 velas de la sesión (cualquiera, ≥ 0,25, ≥ 0,42; `regimen_sesion.er_sesion`, con corte de sesión).
- **648 celdas por canal** (`grilla_generica.n_celdas`). Umbrales fijos elegidos antes de mirar datos reales.

## Períodos
DESC 2025-08-05..2026-03-31, OOS 2026-04-01..2026-09-30, holdout desde la sesión del 2026-10-01 (una apertura, con acta).

## Cómo se refuta
0 celdas nominadas por FDR q ≤ 0,10 en DESC sin pistas que repliquen; falla en INTEGRIDAD (placebo ≥ 25 % o latencia de 1 vela
destructiva); media ≤ 0 en OOS u holdout. **Refutación específica del pago**: si en las celdas nominadas el control FIJO_2R iguala o
supera a TAU en la misma población, la ventaja de la salida τ queda refutada aunque la entrada sobreviva.

## Controles
`tests/research/test_paquete_20261031.py`: causalidad, líneas sin futuro (truncar la serie no cambia las líneas calculadas), paridad
lote/escalar, ruido sin efecto y efecto plantado (retornos con autocorrelación 0,5: TAU gana más que sobre ruido).
