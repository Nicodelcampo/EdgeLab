# Día de tendencia: predictores causales nuevos — resultado (punto 4, 2026-11-18)

Estado: RESULTADO — **ningún predictor pasa BH. GEX (gamma de los dealers, cierre previo) es el único candidato serio: dirección
esperada (menos gamma, más días de tendencia), dosis-respuesta igual en DESC y REP, mismo signo en los 4 índices, AUC 0,55. Queda
NO_CONCLUYENTE por falta de potencia, no refutado.**
- **Pre-registro:** `PREREGISTRO.md`. **Datos:** `TABLA.csv.gz` (sólo DESC y REP; HOLDOUT y EMBARGO fuera) y `RESULTADO.json`.
- **Herramienta:** `tools/dia_tendencia.py`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Resultado (REP, AUC con el signo elegido en DESC, bootstrap por fecha, BH q 0,10 sobre 21)
| Predictor | E1 AUC (p) | E3 AUC (p) | Índices con el mismo signo |
|---|---|---|---|
| **GEX** (bajo → tendencia) | **0,553** (0,031) | **0,555** (0,013) | 4/4 y 4/4 |
| Combinado (logística de DESC) | — | 0,552 (0,016) | — |
| Día de tendencia previo (signo −) | 0,518 (0,051) | 0,512 (0,111) | 4/4 |
| Open drive | — | 0,522 (0,069) | 3/4 |
| Eficiencia de Europa | 0,532 (0,127) | 0,503 | 4/4 / 2/4 |
| Vencimiento mensual (menos tendencia) | 0,516 (0,006) | 0,486 | 3/4 / 0/4 |
| DIX, vuelta de mes, NR7, día interior, ubicación del cierre previo, amplitud | 0,49–0,52 | 0,50–0,51 | — |

**Días de tendencia por tercil de GEX** (descriptivo):

| Bloque | E1: bajo / medio / alto | E3: bajo / medio / alto |
|---|---|---|
| DESC | 14,1 % / 13,3 % / 11,4 % | 21,0 % / 19,0 % / 15,7 % |
| REP | 15,8 % / 13,0 % / 11,3 % | 19,5 % / 19,0 % / 14,8 % |

## Lectura
- **Gamma de los dealers:** es la primera variable de la serie de estudios del día de tendencia con dirección económica correcta,
  dosis-respuesta y consistencia entre índices. Los días de gamma baja tienen alrededor de un 40 % más de días de tendencia que los de
  gamma alta. Coincide con GEX1/GEX1b (más amplitud con menos gamma).
- **Potencia:** el pre-registro supuso un EE del AUC de 0,016 (filas independientes). El real, con bootstrap por fecha, es 0,024–0,027:
  los cuatro índices del mismo día no son independientes, y GEX existe sólo desde 2011 (614 días REP). La potencia real para AUC 0,55
  era ≈ 0,3. **Lección:** la potencia de un predictor diario se calcula con días, no con filas instrumento × día.
- **El resto de las clases nuevas no anticipa** (AUC ≤ 0,53): calendario, estructura previa, Europa, open drive y amplitud. Se suma a
  F-DIA-TENDENCIA-NO-ANTICIPABLE.
- **Holdout A5 de la familia:** sigue sellado. Para GEX daría ≈ 880 días: potencia ≈ 0,6 para AUC 0,55 al nivel LORD, menor que 0,8
  (K27). **No se abre.**

## Siguiente
- **Confirmación de GEX:** necesita días nuevos. El forward desde la frontera, con GEX diario, es la fuente natural (e-proceso sobre la
  etiqueta). También sirve otra serie de gamma independiente, si existe.
- **Uso económico directo** (hipótesis nueva, pre-registro aparte): GEX bajo como filtro de T, ORB y Franklin. Esas reglas tienen el
  holdout mirado, así que la prueba económica también va al forward.
- **No repetir:** calendario (vencimiento y vuelta de mes), NR7, día interior, ubicación del cierre, DIX, Europa, open drive y amplitud
  como predictores del día de tendencia.
