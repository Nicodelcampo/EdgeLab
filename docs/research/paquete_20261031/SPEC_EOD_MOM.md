# EOD-MOM — pre-registro (2026-10-31)

Estado: VIGENTE (pre-registrado antes de cualquier corrida sobre datos reales; aprobado por Nico en la sesión en la nube, 31-oct).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa del embudo: EF2 → embudo automático.
Módulo: `edgelab/research/eod_momentum.py`. Campañas: EOD-ES, EOD-NQ, EOD-YM (familias `EOD_MOM_<INST>`).

## Fuente
Gao, Han, Li y Zhou (2018), *Market Intraday Momentum*, Journal of Financial Economics 129(2) (citado en las estrategias guardadas,
@davidtrades_model post #27); flujo de cobertura de opciones 0DTE al cierre (@wisefoxtraders posts #4, #13, #20). También es el
pendiente #5 de Gonza (`PENDIENTES_PRIORIZADOS_20261031.md`, INTRADAY-MOM-EOD).

## Justificación económica
Rebalanceos forzados al cierre (productos apalancados diarios, coberturas de gamma) operan en la dirección del día durante la última
media hora; la penúltima concentra a los informados que llegan tarde. Es la única ventana que ninguna regla de EdgeLab cubre: si
existe, diversifica la canasta (las 7 reglas vigentes operan en la apertura o en Asia).

## Espacio de eventos y estados
Candidatos: retorno de la primera media hora, de la penúltima, del día completo, cruce de VWAP al cierre, rango del día, gap de
apertura. **Se mide**: las dos señales del paper (r1, rp) y su acuerdo; el retorno del día completo queda fuera (está dentro de la
eficiencia del día como estado). Evento único por sesión y regla: decisión al cierre de la vela de las 15:30 ET.

## Qué se mide
- r1 = cierre a las 10:00 − apertura de la vela de las 09:30; rp = cierre a las 15:30 − cierre a las 15:00 (hora NY con verano).
- Entrada en el primer tick de la vela siguiente a las 15:30; salida forzada en la apertura de la vela de las 15:59 (salida por
  línea) o antes por stop. Ejecuciones (3): stop a 1, 2 o 5 rangos de la media hora 15:00–15:30.
- Perillas: regla (signo r1, signo rp, ambas de acuerdo), magnitud |r|/rango del día (terciles, extremos), régimen RV30/RV390
  (terciles, extremos) y eficiencia del día 09:30–15:30 (cualquiera, ≥ 0,25, ≥ 0,42). **243 celdas por canal.**

## Períodos
DESC 2025-08-05..2026-03-31, OOS 2026-04-01..2026-09-30, holdout desde la sesión del 2026-10-01.

## Cómo se refuta
0 nominadas por FDR en DESC sin pistas que repliquen; media ≤ 0 en OOS u holdout; si sólo funciona con stop de catástrofe y pierde
con stops de 1–2 rangos, el efecto no es operable con riesgo acotado. Con ~160 sesiones de DESC por regla la potencia individual es
baja: se lee también la canasta de pistas.

## Controles
`tests/research/test_paquete_20261031.py`: causalidad, salida a las 15:59, paridad lote/escalar, ruido sin efecto, efecto plantado.
