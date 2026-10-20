# Preregistro — LUX-IMB impulsos: rebalanceo (M1), control sin zonas (M2), continuacion (M3). NQ, descubrimiento

Estado: PRE-REGISTRADO antes de mirar ningun desenlace. OK de Nico 2026-10-20 ("Si a ambas": sumar contratos y medir M1-M3).
Referente rector: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Familia: LUX-IMB-IMPULSOS (registrada aparte de BigTrap2/HFT/corredor; no transporta poblaciones, costos ni presupuesto).

## Datos y particiones (HOLDOUT-A3)
- **Desenlaces solo en DESCUBRIMIENTO**: NQ 09-25 (2025-08-05..09-16), 12-25 (09-17..12-15), 03-26 (12-16..2026-03-16),
  06-26 (2026-03-17..03-31). Ticks `release_v4/NQ_ticks.parquet`, un contrato por tramo, sin back-adjust.
- **Replicacion (abr-sep 2026): comprometida para esta familia.** La definicion se diseno mirando NQ 09-26 (jun-sep) en el
  visor (target-free, pero es "mirar para disenar", regla 1 de HOLDOUT-A3). No se usa abr-sep para desenlaces. Queda a
  decision de Nico si la familia conserva replicacion en abr-may o confirma solo en holdout (>= 2026-10-01).
- Holdout no se toca.

## Poblacion y event-space
Event-space enumerado: todos los impulsos ESPEJO-IND de M1 (activacion -> extremo -> confirmacion). Familias de momento
consideradas: activacion, cumplimiento de criterios en curso (elegida), extremo final (retrospectivo, descartado: no causal),
confirmacion por retroceso (descartada por Nico: llega tarde). Definicion congelada: `LUXIMB-IMPULSOS-v5-reparto`
(`tools/luximb_parity/luximb_impulsos.py`, valores por defecto: vida 500, p80 amplitud y zonas, sin rapidez, tercios <= 60 %).
Umbrales causales por contrato (calentamiento 500 impulsos).
- **Tratados (T):** impulsos marcados.
- **Control (M2):** impulsos no marcados que en curso alcanzan la misma amplitud causal (>= p80) con **<= 2 zonas** atravesadas;
  se fijan en la primera vela que cumple. Mismo tratamiento de desenlace.

## Desenlace (desde el cierre de la vela M1 de la marca)
A = origen, X = extremo conocido en la marca, R = |X - A|, s = +1 si sube. Entrada E = cierre M1 de la vela de marca.
- Objetivo de rebalanceo Tg = X - 0,5·R·s; extension Ex = X + 0,25·R·s.
- Carrera sobre velas 25t con hora >= cierre de la marca: gana la primera barrera tocada; si una vela 25t toca ambas, cuenta
  **Ex** (conservador para M1). Tope: 240 minutos o fin de sesion (hueco > 30 min) -> "tiempo".
- **M1** P(Tg primero). **M3** P(Ex primero). Se reportan juntos con "tiempo".
- P&L por operacion (puntos NQ): fade = vender si s=+1 en E, objetivo Tg (limite, sin slippage), stop Ex (+1 tick slippage),
  tiempo -> cierre al ultimo precio (+1 tick). Continuacion = espejo (objetivo Ex, stop Tg). Costos NQ declarados (no
  medidos aun para esta familia): 1 tick de slippage en la entrada + $4,50 RT (0,225 pts). Sensibilidad 0/1/2 ticks.
- Canal no direccional: MFE y MAE en unidades de R a 60 minutos, distribucion completa, T y C.

## Inferencia (clustering por dia NY)
Bootstrap por dia, 10.000 replicas, IC 95 %. Hipotesis (Holm, familia de 7):
H1 P(Tg) T - C > 0; H2 P&L neto fade T > 0; H3 P&L neto continuacion T > 0; H4-H6 H1 por estrato: direccion (sube/baja),
apertura cash 9:30-11 NY vs resto, fraccion de zonas opuestas < / >= 0,5 (estrato solo de T; se contrasta T-estrato vs C);
H7 P&L neto fade T - C > 0. Se publica MDE (80 %) de H1.

## Justificacion economica
Un barrido rapido que atraviesa muchos desequilibrios deja precio sin negociar; si el mercado vuelve a negociarlo,
deberia verse como retroceso mayor que el de un impulso igual de grande que no cruzo desequilibrios (M2).

## Como podria refutarse
H1 sin diferencia (IC incluye 0 con MDE <= 10 pp), o P&L neto <= 0 tras costos. Una muerte aplica solo a esta definicion,
este desenlace y NQ.
