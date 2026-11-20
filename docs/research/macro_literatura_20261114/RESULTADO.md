# Ideas de la literatura medidas directo — resultado (v2, 2026-11-15)

Estado: RESULTADO (EF3). Pre-registro: `PREREGISTRO.md` (con la nota de la v1 descartada por spreads). Datos: `RESULTADO.json`
(Kaggle `nicolasbuttaro/edgelab-macro-literatura` v2). 148 variantes; nulo de la búsqueda: umbral p95 del máximo t en DESC = **4,02**.

## Veredicto: ninguna pista (ninguna variante supera el umbral; la mejor llega a t 1,9)
| Canasta | DESC neto | OOS neto | RECIENTE neto | PSEUDO neto | Bruto DESC / OOS | Lectura |
|---|---|---|---|---|---|---|
| TSMOM L20/60/120/250 | −0,010 a +0,003 | −0,016 a −0,006 | −0,043 a −0,006 | −0,022 a +0,025 | −0,002 a +0,011 / −0,007 a +0,003 | ≈ 0 en bruto: sin señal en esta forma |
| FIN DE MES N1/N3 | −0,05 / −0,03 | −0,09 / −0,08 | −0,09 / −0,11 | +0,10 / +0,14 (n 18) | −0,03 / −0,07 | negativo salvo el último año (n chico) |
| NOCHE | −0,001 | −0,004 | −0,003 | −0,005 | **+0,032 / +0,017** | señal bruta chica que el spread se come |
| MOMENTUM INTRADÍA (IMOM) | −0,11 (t −9) | −0,13 | −0,12 | −0,10 | −0,001 / −0,008 | ≈ 0 en bruto; el costo de una operación de 1 h lo hunde |

Por activo, lo mejor: TSMOM L120/L250 en oro, S&P y Nasdaq (+0,02 a +0,16 R en RECIENTE y PSEUDO), lejos del umbral (t ≤ 1,9).

## Alcance (qué muere y qué no)
- Muere exactamente esto: TSMOM **semanal sin fin de semana** (lunes → viernes), riesgo de 2 desvíos de la operación semanal, en CFD
  de Dukascopy; cambio de mes con salida el viernes; noche lunes–jueves; IMOM en H1. El TSMOM publicado es MENSUAL con tenencia
  continua: la restricción «nada abierto el fin de semana» lo convierte en otra regla (re-entrada semanal) y eso no se probó.
- Lección: en CFD, lo que dura horas (IMOM, NOCHE) no paga el spread aunque tenga algo de señal bruta (NOCHE +0,03 R).
- Edges actuales: esto no dice que no funcionen «ahora»; dice que en ninguno de los cuatro tramos (incluido PSEUDO) hay ventaja
  medible en estas formas.
