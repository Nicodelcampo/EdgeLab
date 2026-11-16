# Reels del 2026-11-16: resultado

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (commiteado antes de correr). Cifras: `RESULTADO.json`. Corrida `tools/reels_20261116.py
correr` sobre M1 Dukascopy 2012-01-20 → 2026-09-29, costos canónicos del futuro, R neto. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Nada miró el holdout.

Nota de código (antes de ver resultados de P&L): la primera corrida falló por unidades de tiempo (índice en µs, `astype(int64)//1e9` daba
fechas de 1970). Se corrigió en el lector y se relanzó; la salida fallida sólo mostró las medias de T, ya conocidas.

## Resumen
**Ninguna de las 18 pruebas de P&L pasa.** El sesgo de Franklin queda como pista de régimen (positivo sólo desde 2020 en NQ y ES), y como
filtro de T **pasa su regla**. Las dos velas y el revisit de viernes, tal como se ven en los reels, no tienen ventaja.

## E0 Hougaard: el «24 de 25» no se reproduce
Tasa de visita del mínimo del día de referencia en la RTH del día siguiente (2012–2026):

| Par | NQ: máx. menor / no menor | ES | YM |
|---|---|---|---|
| Viernes → lunes | **51 %** (n 310) / 34 % | 50 % / 33 % | 53 % / 35 % |
| Viernes → lunes, abre dentro | 46 % / 36 % | 45 % / 35 % | 51 % / 37 % |
| Miércoles (vs lunes) → jueves | 50 % / 45 % | 56 % / 44 % | 56 % / 47 % |
| Martes → miércoles (control) | 54 % / 42 % | 55 % / 44 % | 56 % / 47 % |
| Jueves → viernes (control) | 51 % / 37 % | 50 % / 38 % | 47 % / 38 % |

El efecto existe pero es otro: un máximo menor sube la probabilidad de visitar el mínimo de **≈ 35 % a ≈ 50 %**, en **cualquier** par de días
(no es propio del viernes), y está muy lejos del 96 %. Con 300 casos por celda, un 24/25 real (IC95 inferior ≈ 80 %) queda descartado.

## P&L (R neto por operación; A = 2012–2019, B = 2020 → 2026-09)
| Prueba | A: n / R | B: n / R (IC90) | B: p / MDE | Lectura |
|---|---|---|---|---|
| VIERNES_LUNES vie_lun NQ | 73 / −0,18 | 75 / −0,12 (−0,39 … +0,22) | 0,75 / 0,46 | sin efecto; sin potencia |
| VIERNES_LUNES vie_lun ES | 37 / −0,61 | 68 / −0,38 | 0,94 | en contra |
| VIERNES_LUNES vie_lun YM | 54 / +0,32 | 80 / −0,46 | 0,96 | en contra en B |
| VIERNES_LUNES mie_jue (NQ/ES/YM) | ≈ 0 / −0,31 / −0,16 | ≈ 0 en los tres | ≥ 0,56 | sin efecto |
| DOS_VELAS NQ | 1.718 / −0,12 | 1.673 / +0,02 (MDE 0,06) | 0,17 | ≈ 0; bruto +0,05 |
| DOS_VELAS ES | 1.128 / −0,21 | 1.668 / −0,04 | 0,96 | refutada |
| DOS_VELAS YM | 1.394 / −0,13 | 1.672 / −0,09 | 1,00 | refutada |
| FRANKLIN cierre NQ | 711 / −0,05 | 734 / **+0,10** (+0,02 … +0,18) | 0,018 / 0,12 | régimen desde 2020 |
| FRANKLIN 2R NQ | 711 / −0,06 | 734 / **+0,10** (+0,03 … +0,17) | 0,010 / 0,11 | régimen desde 2020 |
| FRANKLIN cierre ES | 433 / −0,14 | 642 / **+0,12** (+0,01 … +0,23) | 0,037 / 0,17 | régimen desde 2020 |
| FRANKLIN 2R ES | 433 / −0,17 | 642 / +0,07 | 0,089 | régimen desde 2020 |
| FRANKLIN (cierre/2R) YM | −0,11 / −0,14 | −0,06 / −0,03 | ≥ 0,73 | en contra |

- BH q 0,10 sobre 18: el menor p (0,010) no llega al umbral (0,0056): **ninguna nominada**.
- DOS_VELAS: las celdas `11h` y `16h` resultaron idénticas (la primera pareja de velas iguales aparece siempre antes de las 11:00); son
  una sola prueba en la práctica. El acierto es ≈ 50 % con 1:1: lo que se ve en el reel es la tasa de una moneda, menos la fricción.
- VIERNES_LUNES: el acierto (35–54 %) no tiene nada que ver con el 96 % de «visita». El backtest de AlphaZone (WR 24,6 %, PF alto) no se
  reproduce con la regla escrita en el reel.

## FRANKLIN como filtro de T (FUNDEDSYNC, NQ) — pasa su regla
| Tramo | a favor del sesgo: n / pts | resto: n / pts | diferencia (p) |
|---|---|---|---|
| A 2012–2019 | 669 / +0,9 | 498 / −0,0 | +0,9 (0,31) |
| B 2020 → 2026-09 | 810 / **+21,3** | 726 / +9,4 | **+11,9 (0,012)** |

Dirección repetida y p_B < 0,10, así que pasa la regla pre-registrada. Advertencias: en A el propio T vale ≈ 0, así que el filtro no tiene
qué mejorar; y B incluye 2020–2023, el tramo de descubrimiento de T. Además, «resto» no es «en contra»: incluye los días sin sesgo.
Se confirma sólo en datos nuevos.

## Qué sigue (propuesto, no ejecutado)
1. **FRANKLIN a datos no vistos**: apertura del holdout de la familia (oct–nov; futuros NQ/ES y USATECH/USA500 sellados) en modo exploratorio,
   regla congelada `cierre` en NQ+ES, con la probabilidad de azar de desarrollo declarada (p_B 0,018 y 0,037; Fisher) y el filtro de T en el
   forward de T+Z+R. Con ≈ 30 sesiones por instrumento el holdout tiene poca potencia (MDE ≈ 0,4 R): decide más el forward.
2. VIERNES_LUNES y DOS_VELAS, tal como están en los reels: NO_REPETIR. Lo que sí queda del E0 (un máximo menor sube la visita del mínimo
   ≈ +15 pp, en cualquier día) es un rasgo de contexto barato para el banco de eventos, no una regla.

## Medido / no medido
- MEDIDO: las tres reglas tal como se ven en los reels, en NQ/ES/YM, 2012–2026, R neto; E0 de visitas por par de días; FRANKLIN como filtro
  de T.
- NO MEDIDO: VP³ (motivos en el pre-registro); variantes de entrada de Franklin (retroceso al VWAP o al nivel de Londres): el reel no las
  define y elegirlas ahora sería mirar; filtros de noticias; versiones con ETH en lugar de RTH para el revisit.
