# SCAN-1 — resultado (barrido de franjas, 5 instrumentos × 96 celdas; 20 pruebas reportadas, 495 al contador global; 112 s)

Datos crudos: `SCAN1_RESULTADOS.json` (incluye el top-10 descriptivo por instrumento). Nivel familiar apostado 0,0189.

## Veredicto: sin hallazgo replicado (0 de 15 réplicas pasan Holm)
| Instrumento | Descubrimiento (muestra) | Máximo \|z\| vs cuantil 95 del nulo | p (nulo de máximo) | Holm 20 | Réplica de las 3 mejores celdas |
|---|---|---|---:|---:|---|
| **ES** | spot 2018-01 → 2025-06 (n = 2.317) | 8,98 vs 3,95 | 0,0006 | 0,011 | 0 de 3 (p 0,27 a 0,75) |
| **GC** | spot 2022-07 → 2025-06 (n = 931) | 4,88 vs 3,52 | 0,0005 | 0,010 | 0 de 3 (p 0,08 a 0,70) |
| NQ | 60 % inicial futuros (n = 166) | 3,60 vs 3,50 | 0,038 | 0,64 | 0 de 3 |
| YM | 60 % inicial futuros (n = 159) | 4,02 vs 3,55 | 0,011 | 0,20 | 0 de 3 |
| 6E | 60 % inicial futuros (n = 172) | 2,93 vs 3,60 | 0,28 | 1,0 | 0 de 3 |

## Lectura
- **ES y GC muestran estructura intradía real en el spot de la muestra larga** (el máximo supera con holgura al nulo de máximo) **que no se sostiene en los futuros de 2025-26**: p. ej. ES `07:30_h60_prev` (reversión −0,19 en 2018-25) da +0,05 en la réplica; GC `13:30_h15_prev` (momentum +0,16) da +0,13 con el mismo signo pero no pasa (p 0,20; los pocos días extremos de 2026 inflan el nulo de signo). Es consistente con lo ya visto: los efectos intradía de estos activos son chicos y cambian con el régimen.
- **NQ, YM y 6E:** con ~165 sesiones de descubrimiento ni siquiera el máximo es robusto (NQ y YM pasan solo a nivel nominal; no sobreviven a Holm).
- **Tamaño frente al umbral:** las correlaciones de las mejores celdas (|ρ| 0,10-0,30 en el descubrimiento, ≈ 0 a 0,16 en la réplica) están en el orden del ρ requerido de `UNIVERSO.md` solo en las celdas del descubrimiento, y desaparecen al replicar. Nada llega a nivel B según el mandato.
- Los umbrales de cuenta no se usaron para descartar: se descartó por no replicar.

## Correcciones de sistema que salieron de esta corrida
1. El primer cierre contó como «acierto» los rechazos solo de descubrimiento y acreditó +0,05 de alfa. Corregido: con diseño de descubrimiento→réplica, **el acierto exige rechazo en una réplica** (`analyze.decide`, con test). Se revirtió el alfa (0,0892 → 0,0200), se corrigió el libro y se anexó la corrección a la evidencia y al Edge Brain (append-only).
2. ES y GC quedan en la evidencia como `NOT_TIME_STABLE` (estructura en el descubrimiento sin réplica), sin muestra pendiente: no generan candidatas de «datos nuevos».
**Costo:** 495 al contador global; riqueza de alfa 0,0200.
