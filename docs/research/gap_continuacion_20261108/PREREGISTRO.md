# Pre-registro — GAP-CONTINUACION (regla de Kemet Capital, mitad no medida)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-11-08.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `GAP_CONTINUACION`. Etapa del embudo: **EF2/EF3** (descubrimiento en desarrollo; réplica abr–sep en futuros).
Origen: estrategias que juntó Nico (reel de Kemet Capital «Gap SP500»): «un gap chico se rellena 9 de 10; uno de 20 pts o más no
vuelve 2 de 3 veces; si a las 10:30 sigue abierto, sólo 1 de 4 se cierra después». Primera de las cuatro, por orden de prioridad
(motivo económico claro, frecuencia diaria, regla completa). Las otras tres: Italian Founder (rupturas GC), AlphaZone (EMA9+VWAP),
FlexingJoe (ORB+EMA20, última: ORB ya se refutó el 2026-11-08).

## 1. Qué ya está medido
La mitad «gap chico → relleno» es GAP_RTH (`docs/research/gap_rth_20261025/`): réplica SIN_POTENCIA, estimación ≈ 0. No se repite.
Se mide sólo la mitad nueva: **continuación de un gap grande que sigue sin rellenar**.

## 2. Población (enumerada antes de congelarla)
Alrededor del gap de apertura: (a) relleno del gap (medido, GAP_RTH); (b) continuación inmediata a las 09:30 (sin condición de
tiempo); (c) **continuación condicionada a que el gap siga abierto a la hora T** (lo que dice el reel); (d) relleno tardío después de
T; (e) estado continuo «gap abierto» por minuto. Se mide **(c)**; (b), (d), (e) quedan NO MEDIDOS. Un evento por día y celda.

## 3. Regla (`edgelab/research/gap_continuacion.py`, reutiliza `gap_rth.dias` y `bracket.sim`)
- gap = cierre de la vela 09:29 ET − cierre RTH previo; ATR = media de rangos RTH de los 14 días previos (mismo que GAP_RTH).
- Si |gap| > g·ATR y ninguna vela entre 09:30 y la anterior a T tocó el cierre previo: mercado **a favor del gap** en el primer tick de
  la vela T. Stop: en el cierre previo («cierre») o a 0,5 ATR («atr05»). Sin objetivo. Salida a `hold` minutos o en la última vela RTH.
- Grilla: g ∈ {0,15; 0,3; 0,45; 0,6; 0,9} × stop ∈ {cierre, atr05} × hold ∈ {120, fin del día} × T ∈ {10:00, 10:30} = **40 celdas**.
- El umbral absoluto del reel (10/20 pts de ES) se reemplaza por ATR: 20 pts no significan lo mismo en 2023 que en 2026 (lo dice el
  propio análisis del reel).

## 4. Datos, ventanas, costos
- Descubrimiento: USATECH→NQ, USA500→ES, USA30→YM (Dukascopy) 2023-01-03 → 2026-03-31, canales **total** y **reciente** (≥ 2025-07-01,
  declarada ahora): 40 × 3 × 2 = **240 pruebas**. Canal de desarrollo en futuros NQ/ES/YM jul-2025 → mar-2026: descriptivo, fuera del tamiz.
- Costos de `edgelab/costos.py` (puntos por viaje): NQ 1,5455, ES 0,8877, YM 5,052; adversos 2,0455 / 1,3877 / 7,052.
- Nada desde la sesión del 2026-10-01 (`edgelab/holdout.py`).

## 5. Estadístico y decisión
- **R por operación** = (bruto − fricción) / distancia del stop. Bootstrap de sesiones (20.000), p unilateral, IC90, MDE. < 30 ops: no evaluable.
- Tamiz `escalera.tamiz_fdr` q 0,10. Réplica única abr–sep 2026 en los futuros con las nominadas (o pistas con IC90 inferior > 0,
  ATJ-25), lote LORD++. Confirmada = rechaza en el lote y media R > 0 en réplica. Una confirmada no es edge: holdout por protocolo.

## 6. Justificación económica
Un gap grande respecto de la volatilidad suele traer información nueva (noticias nocturnas); si la apertura no lo corrige en la primera
media hora u hora, el flujo informado domina sobre la reversión y el día tiende a seguir en esa dirección (día de tendencia). Es la tesis
«ruido vs información» del tamaño del gap.

## 7. Cómo podría refutarse
Sin nominadas con potencia (MDE < 0,1 R); nominadas sólo en el CFD y negativas en el canal de futuros; o media R ≤ 0 en la réplica.
Un efecto sólo en 2023–2024 que desaparece en «reciente» tampoco sirve.

## 8. Multiplicidad, linaje, riesgos
- Registro global `gap_continuacion/desc`, 240 pruebas, antes de correr. Linaje `GAP_CONTINUACION` ← `GAP_RTH` (480).
- Riesgos: el CFD no es el futuro; la condición «no tocado» usa velas M1 (un toque intra-vela cuenta); feriados y medias jornadas se pierden.

## Resultado (2026-11-08)
0 nominadas de 208 evaluables; media −0,149 R en total, MDE 0,13: refutada. Ver `../estrategias_scrapeadas_20261108/RESULTADO_DESC.md`.
