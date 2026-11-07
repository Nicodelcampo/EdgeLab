# ESPEJO-REGLA — orden del espejo para la grilla

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `ESPEJO_REGLA` / `edgelab.research.espejo_regla`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`

## Justificación económica

Un impulso que recorre precio sin aceptación no tiene por qué quedarse cuando el empuje afloja. Si la vuelta deshace el tramo, el recorrido de B hacia A es más grande que la fricción cuando el ancho pasa de unas decenas de ticks. Quien está del otro lado es quien compró el extremo B y no encuentra continuación.

## Cómo podría refutarse

Ninguna celda nominada por FDR q 0,10 en el descubrimiento, o las nominadas pierden contra el mismo cruce con la semejanza y la eficiencia barajadas. Un R neto que sólo aparece con objetivo 0,25·W no cuenta: ese residuo ya se midió el 2026-09-28.

## Población

Se enumera y se mide una:

1. Creación del impulso. No se opera.
2. Confirmación de B por retroceso 0,3·W. No se opera.
3. Primer cierre que cruza 0,25 o 0,50 del camino de vuelta, sin extremo nuevo más allá de B. **Es el evento.**
4. Toque de A. Es el objetivo, no la entrada.
5. Extremo nuevo más allá de B. Es el stop.
6. Vencimiento a 60 velas o fin de sesión. Es la salida por tiempo.
7. Estado continuo de la vuelta. No se mide en esta corrida.
8. Espejo de un espejo. No se mide.

La dirección de la orden es la de la vuelta. RTH es perilla (`solo_rth`), declarada antes de mirar. La sesión de fondo es la CME completa del lector de ticks. No se abre el holdout para elegir.

## Perillas

Eficiencia, volumen por tick y semejanza (`sim_abs`) salen crudas. Los cortes son los terciles del E0. Dirección y fracción de entrada son categorías. Una sola ejecución: stop más allá de B, objetivo en A.

## Linaje

Desciende de ESPEJO-IND, de ESPEJO-NICO-100T (0/8) y de la continuación en 100 ticks (seis instrumentos, R bruto no positivo). Hereda ese bruto. No es una familia nueva.
