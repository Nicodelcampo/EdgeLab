# Pre-registro — GAP-RTH: relanzamiento de C-TICKS F4 «cierre de gap» en índices con años de datos

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `GAP_RTH`. Etapa del embudo: **EF2/EF3** (descubrimiento en datos de desarrollo; confirmación en la réplica abr–sep 2026).
Origen: `docs/research/RELANZAMIENTO_ANALISIS_VIEJOS_20261025.md` (prioridad 1).

## 1. Por qué relanzar
C-TICKS F4 (`docs/research/CAMPANA_TICKS_MULTI_RESULTADOS_20260923.md`) tuvo MCPT p 0,001 en ES y NQ y 0,019 en YM, ES positiva en
4/4 variantes, pero murió «sin potencia»: 25–56 operaciones en 4 meses de barras de 5 min. Además usaba el MCPT viejo de G2 (enmienda
G2-A1), costos del feed NT8 y comisión supuesta. Hoy hay 3,7 años de USATECH, USA500 y USA30 (Dukascopy, recortados antes del holdout),
inferencia por sesiones con tamiz FDR y costos canónicos.

## 2. Población (enumerada antes de congelarla)
Eventos posibles alrededor de la apertura RTH: (a) gap de apertura contra el cierre RTH previo; (b) gap contra el cierre de la sesión
CME (16:00 CT); (c) ruptura del rango nocturno; (d) primer toque del cierre previo; (e) estado continuo «distancia al cierre previo» en
cada minuto. Se mide **(a)**, que es lo que F4 midió y lo único con evidencia previa; (c) ya se midió (F3, sin señal); (b), (d) y (e)
quedan NO MEDIDOS. Un día = un evento como máximo por celda.

## 3. Regla (`edgelab/research/gap_rth.py`, simulador `edgelab/research/bracket.py::sim`)
- Hora de Nueva York. gap = cierre de la vela M1 de las 09:29 − cierre RTH previo (cierre de la última vela RTH del día hábil anterior,
  si esa vela es de las 15:55 o después). ATR_d = media de los rangos RTH (09:30–15:59) de los 14 días previos.
- Si |gap| > g × ATR_d: orden a mercado **en contra del gap**, en el primer tick desde las 09:30:00, a su precio.
- Objetivo límite a `frac` × |gap| desde la entrada; stop a mercado a `k` × |gap| (k = 0: sin stop); salida por tiempo a `h` velas
  M1 desde la del llenado o a la última vela RTH.
- Grilla: g ∈ {0,15; 0,3; 0,45; 0,6; 0,9} × frac ∈ {1; 0,5} × h ∈ {30, 60, 120, fin del día} × k ∈ {0; 1} = **80 celdas**.
- Diferencias con F4 (declaradas): velas M1, decisión con el cierre de las 09:29 (F4 decidía con la apertura, que es el mismo precio que
  llenaba), objetivo por distancia.

## 4. Datos, ventanas y costos
- Descubrimiento (sensor como proxy, con los costos del futuro): USATECH→NQ, USA500→ES, USA30→YM, sesiones 2023-01-03 → 2026-03-31.
  Canales: **total** y **reciente** (≥ 2025-07-01, declarada ahora). 80 × 3 × 2 = **480 pruebas**.
- Canal de desarrollo en los futuros NQ, ES, YM (2025-07-01 → 2026-03-31): descriptivo, fuera del tamiz; sirve para ver si el proxy
  CFD se parece al futuro.
- Costos: `edgelab/costos.py`, fricción por viaje en puntos: NQ 1,5455 (adversa 2,0455), ES 0,8877 (1,3877), YM 5,052 (7,052).
- Nada desde la sesión del 2026-10-01 (frontera única `edgelab/holdout.py`).

## 5. Estadístico y decisión
- Media neta por operación, bootstrap de sesiones (20.000), p unilateral (H1: media > 0), IC90, MDE publicado. Celdas con < 30
  operaciones: no evaluables (p = 1, fuera del `m` del FDR, D6).
- Tamiz `escalera.tamiz_fdr` (Storey, q 0,10) sobre las evaluables de los dos canales.
- Réplica (una vez por familia, sesiones abr → sep 2026 en los futuros, no miradas por GAP_RTH): entran las nominadas elegidas con
  `escalera.elegir_pistas_replica` (k = 20, cota inferior del IC90 > 0, distintas en ≥ 2 perillas), congeladas, en su futuro. Un solo
  lote por LORD++ (`edgelab/funnel/libro_lord.py`, Simes + BH). Confirmada = rechaza en el lote y media neta > 0 en la réplica.
- Sin nominadas: SIN_CANDIDATAS con el MDE por canal; se pasan igual a réplica las pistas con IC90 inferior > 0 (ATJ-25).
- Una confirmada no es edge: pasa al holdout a N fijo por el protocolo de apertura.

## 6. Justificación económica
La apertura RTH concentra órdenes acumuladas durante la noche; un gap grande respecto de la volatilidad suele estar hecho con poca
liquidez nocturna y el flujo de la apertura lo corrige en parte. Es un efecto documentado en la literatura (gap fade) y F4 vio timing
significativo en tres índices.

## 7. Cómo podría refutarse
Ninguna celda nominada en ningún instrumento con potencia (MDE publicado menor que la fricción); o nominadas sólo en el proxy CFD y
negativas en el canal de desarrollo de los futuros; o media neta ≤ 0 en la réplica abr–sep. Un efecto sólo en 2023 que desaparece en
«reciente» tampoco sirve (edges actuales).

## 8. Multiplicidad, linaje y riesgos
- Registro global `gap_rth/desc`, 480 pruebas, antes de correr. Linaje `GAP_RTH` ← C-TICKS (100 pruebas, fuera del registro global
  porque es anterior a él) declarado con n heredado 100.
- Riesgos: el CFD no es el futuro (horario, gap del CFD ≠ gap del futuro si el CFD cotiza de noche distinto); la decisión a las 09:29
  usa el último precio del CFD; feriados y medias jornadas se pierden (sin cierre previo válido).
- Código: `edgelab/research/gap_rth.py`, `tools/kaggle_grilla/gap_rth_main.py`, tests `tests/research/test_gap_rth.py`
  (sha256 en el commit de este pre-registro).

sha256 al pre-registrar: `edgelab/research/gap_rth.py` `47b78f90a9252cacd9755b83f0ba3c746b460127201983b2c13a85b802553ab5` ·
`tools/kaggle_grilla/gap_rth_main.py` `461a4788d266259e3f60c530d54336695b992c87dfd822015eab6877c90ddf44` ·
`tests/research/test_gap_rth.py` `2b2f400177b972219b359cfcbd4a377bd9dfcbb369af4b6cb5c3bd6ede963972`.
