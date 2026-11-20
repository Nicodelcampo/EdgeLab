# LUXIMB-AMARILLA — MEDIDO / NO MEDIDO

Estado: VIGENTE.

## MEDIDO
| fecha | qué | resultado |
|---|---|---|
| 2026-11-11 | Exploración DESC/REP, NQ y USATECH (144 definiciones × 6 ejecuciones × VWAP) | 5 celdas sobre el nulo en un solo corte cada una, todas sin condición de zonas y con regreso al borde interno; ninguna repite. Zonas −0,03 R vs control; volumen +0,04 R. Pocos casos (adenda cumplida). |
| 2026-11-11 | R (relajada) y R2 (impulsos largos, ≥ 2/día, P40): consistencia en 4 cortes | R 264/12.384 y R2 236/12.810 celdas positivas y elegibles en los 4 cortes, menos que el 1/16 del azar; la mejor de R2 (l40z4, W2, e2, ANTES, contra VWAP NY) da ≥ +0,24 R en cada corte con n ≥ 30, elegida entre 12.810. |
| 2026-11-11 | Exploración R2 con el nulo de la búsqueda | Celdas sobre el p95 del nulo en los 4 cortes (6/20/6/6), todas de la forma DESPUES + objetivo 50 % + VWAP lejos, con y sin zonas; celdas exactas distintas por corte. PISTA_VIVA `F-AMARILLA-DESPUES-VWAP-LEJOS`. R: sobre el nulo sólo en USATECH (25 DESC, 4 REP). |

| 2026-11-11 | HOLDOUT desde 2026-10-01 (NQ+USATECH, congeladas 845c37fc, acta ACTA_HOLDOUT.md) | obj 50 %: +0,086 R, n 11, 11/11 ganadoras, p 0,002, Fisher 0,001 → SIN_POTENCIA (n chico). obj 75 % con caja amarilla: −0,117 R (n 12); obj 75 % sin filtro: −0,236 R (n 18) → EN_CONTRA_SIN_POTENCIA. Desde 23-oct: n 3 / 3 / 7, mismos signos. |

| 2026-11-12 | R3 stops cortos (desarrollo, amarilla, VWAP diario lejos, n 77/90) | obj 50 %: stop en extremo +0,066 R (95 % ganadoras, 4/4 cortes); borde+0,1 +0,006, borde+0,5 −0,005, mitad +0,013. obj 75 %: extremo +0,145; stops cortos +0,09 a +0,12 pero negativos en los dos DESC. Achicar el stop NO mejora: se pierde más por stops de lo que se gana por R. |

## NO MEDIDO
- Forward con e-proceso de obj 50 % hasta n ≥ 30 (el holdout de la familia ya se usó).
