# ORB-CFD — MEDIDO / NO MEDIDO (Dukascopy USA500, USATECH, USA30)
Registro vivo. Manifiesto: `ORB_CFD_FASE0B_MANIFIESTO_20261017.md`.

## Censo 0A (target-free) — MEDIDO (2026-10-17)
Kernel `edgelab-orb-cfd-census-v1`, `orb_cfd_results_20261017/EXP_ORB_CFD_0A_CENSUS.json`. Sin retornos ni precios posteriores al cierre del rango de 15 min. Mid = (bid+ask)/2, RTH por reloj 09:30-16:00 ET.
- **Días RTH:** USA500 2.257 (2018-01-02..2026-09-30); USATECH 966 y USA30 966 (2023-01-03..2026-09-30). Contra 173/161 de ORB_FUT.
- **Densidad:** mediana de cotizaciones en el rango de 15 min: USA500 ~1.000 (2018) a 2.900-4.100 (2020-26); USATECH 5.200-8.700; USA30 3.800-6.400. Primera cotización <= 300 s en >99 % de los días. Huecos > 120 s: USA500 8/4/4/5/0/1/2/0/1 por año; USATECH y USA30 <= 7.
- **Ancho y fricción:** ancho mediano del rango de 15 min USA500 6.3-19.7 pts, spread mediano 0.46-0.51 pts (spread/ancho 6.7 % en 2018 → 2.7 % en 2026); USATECH spread/ancho 2.3 % → 0.8 %. El spread del CFD **no es** el del futuro.
- **Guardas propuestas** (en el manifiesto): días válidos M/R = USA500 1.865/300, USATECH 628/296.

## Fase 0B-CFD sobre M (<= 2025-07-17) — MEDIDO (2026-10-17, opción A aprobada por Nico)
Kernel `edgelab-orb-cfd-0b-m-v1` (commit `fbe0ecdb`, congelado antes de correr), `orb_cfd_results_20261017/EXP_ORB_CFD_0B_M_RESULTS.json`. Guardas del manifiesto; 0 discrepancias entre los dos caminos de precio en todas las celdas. Días válidos: USA500 1.865/1.946, USATECH 628/655 (descartes: cierre temprano 52/24, huecos > 120 s 24/2).
Celda primaria (15 min, primer toque del mid, extensión al cierre 15:45):
| | N | media E | IC 95 % | MDE | p unilateral (nulo) | mitades | recortada 1 % | bootstrap mensual |
|---|---|---|---|---|---|---|---|---|
| USA500 | 1.863 | **+0,111 R** | [−0,005; +0,227] | 0,166 | **0,039** | +0,093 / +0,129 | +0,117 | [−0,005; +0,224] |
| USATECH | 628 | **+0,089 R** | [−0,077; +0,255] | 0,237 | **0,148** | +0,037 / +0,140 | +0,084 | [−0,079; +0,267] |
**Veredicto pre-registrado: ABSTENCIÓN en ambos.** Ambos son medibles (MDE <= 0,25 R: ya hay potencia, que era el objetivo), pero ninguno cumple `SEÑAL_EN_M` (USA500 tiene IC que roza el cero y p = 0,039 > 0,025; USATECH p = 0,148) ni `NO_GO` (el IC no cabe en ±0,10 R). **R (2025-07-18..2026-09-30) NO se abre**: el manifiesto lo reserva a `SEÑAL_EN_M`. Consecuencia: no hay equivalencia CFD↔futuro que evaluar todavía y nada se transporta a ES/NQ.
Lectura honesta:
- La media es **positiva y pequeña** (~+0,1 R bruto) con SD ~2,1-2,6 R: ~0,04 R por unidad de riesgo diario, antes de stop, costos y ejecución. Es consistente con el IC de futuros (−0,18 R, ±0,37), así que **no hay contradicción** entre CFD y futuros: sólo que éstos no podían ver un efecto de ese tamaño.
- Para *confirmar* un efecto de ~0,1 R con SD 2,5 R haría falta N ~ (2,8 × 2,5 / 0,1)² ≈ **4.900 días**. R tiene ~300 días (MDE ~0,3-0,4 R): **no puede confirmarlo ni refutarlo**. El límite sigue siendo N, y ya no se arregla con más datos Dukascopy.
- Descriptivo, sin inferencia (16 celdas, 8 por instrumento: 4 ventanas × 2 horizontes): USA500 da media positiva en las cuatro ventanas al cierre (5 min +0,21 R p = 0,011; 15 min +0,11; 30 min +0,09 p = 0,021; 60 min +0,05); USATECH 30 min +0,15 R p = 0,009, 5 min −0,01. **Son hipótesis nuevas nacidas del resultado**, no hallazgos: no se promueven; cualquiera necesitaría un manifiesto propio y datos que no hayan sido vistos. La mediana de E es ≈ 0,07-0,10 R, la fracción positiva 51-52 %.
- Por año (USA500, 15 min, cierre): −0,03 / +0,14 / 0,00 / +0,24 / +0,19 / +0,21 / −0,04 / +0,24 (2018→2025): inestable en el signo, 2 de 8 años en o bajo cero.

## NO MEDIDO
Conjunto R (2025-07-18..2026-09-30) sin abrir; equivalencia CFD↔futuro (sólo se evalúa si M da señal); cierre de barra, toque n-ésimo, latigazo, filtros; costos reales (futuros); USA30 (fuera de alcance); todo ≥ 2026-10-01 (no existe en los datasets).
