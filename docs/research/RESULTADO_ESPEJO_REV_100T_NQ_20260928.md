# ESPEJO-REV-100T — NQ (Lucid) — resultado (2026-09-28): primera corrida parcial + re-corrida con sesiones sorteadas

Kaggle `edgelab-espejo-rev100t-nq-20260928`. **Advertencia de muestra:** el tope de cómputo (8.000 eventos por
configuración) corta en orden cronológico y en NQ se alcanzó a las **20 de 171 sesiones** (jul–ago 2025). Es un
resultado de un tramo, no del descubrimiento completo: hay que re-correr con sorteo de sesiones en todo el período.

**12 celdas sobreviven el máximo estadístico (t crítico 3,57).**

## A) Cruce (idea de Nico), nivel 4, todos (n 9.107)
| Llega hacia B | Todos | O bajo | O medio | O alto |
|---|---|---|---|---|
| 25 % | 0,737 (exc +0,022) | 0,539 (+0,020) | 0,739 (+0,031) | 0,936 (+0,015) |
| 50 % | 0,644 (+0,010) | 0,461 (+0,004) | 0,627 (+0,015) | 0,845 (+0,011) |
| 75 % | 0,542 (−0,001) | 0,372 | 0,510 | 0,744 |
| 100 % | 0,470 (+0,001) | 0,305 | 0,429 | 0,677 |
- Supera al azar sólo en los primeros tramos del cruce (25 % y algo del 50 %): +2 a +4,5 pp; el 75 % y 100 % no.
- El overshoot cambia mucho la probabilidad cruda (alto: 94 % llega al 25 %), **pero casi todo lo explica el nulo**
  (la barrera de falla queda lejos): el exceso no crece con O.
- Con la configuración de la captura («no lista» + ineficiente), 25 %: +8,5 pp (n 235), sobrevive.

## B) TP/SL de reversión
R bruto negativo en todas las celdas (−0,001 a −0,076 W). Sobreviven 4 con exceso +1 a +2 % y R negativo, en TP 0,25 W:
el mismo patrón sospechoso del nulo en objetivos cortos que en CONT.

## Lectura
Pista débil a favor de tu idea en el primer cuarto del cruce, más fuerte con «no lista» + ineficiente, pero con muestra
cronológica recortada. No hay configuración de reversión rentable en bruto.

## Re-corrida con sesiones sorteadas (28/09, `artifacts/espejo/rev100t_kaggle/NQ_v2/`)
16 sesiones sorteadas en todo el período (ago-2025 → mar-2026), **ninguna en común con la primera corrida** (20 sesiones
de jul–ago): funciona como réplica interna sobre otra muestra. t crítico 3,52; 6 celdas sobreviven, todas del cruce al 25 %.
| Nivel | 25 % | 50 % | 75 % | 100 % |
|---|---|---|---|---|
| N3 | 0,741 (+0,022) | 0,653 (+0,016) | 0,552 (+0,005) | 0,476 (+0,004) |
| N4 | 0,746 (+0,026) | 0,659 (+0,015) | 0,561 (+0,003) | 0,487 (+0,003) |
| N5 | 0,752 (+0,029) | 0,671 (+0,020) | 0,578 (+0,009) | 0,503 (+0,007) |
Overshoot medio en el 25 %: +3,7 a +4,6 pp (sobrevive en los tres niveles).
**El exceso del primer cuarto del cruce se repite en una muestra disjunta** (+2 a +4,6 pp), y se apaga hacia el 75–100 %.
TP/SL de reversión: R bruto máximo +0,047 W, ninguna celda sobrevive.
Límite: con el tope de 8.000 eventos, NQ usa ~16 sesiones por corrida (cientos de eventos por sesión); el IC por sesión es ancho.
