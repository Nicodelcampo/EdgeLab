# Manifiesto — U1-CRUZADO: señal U1 en USATECH, operación en NQ (2026-10-23)

Estado: VIGENTE — registrado antes de correr. Pedido de Nico (2026-10-23): «no importa que no se pueda operar tal cual, tomá eso y
ahora sí probá P&L; como se mueven parecido, podría aplicar la estrategia en el USATECH y operar en el NQ».

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familia: AREAS-EXP-1. Código: `edgelab/research/u1_cruzado.py` (tests `tests/research/test_u1_cruzado.py`), kernel `tools/kaggle_grilla/kernel_u1_cruzado.py`.

## Regla congelada
- **Señal:** U1 tal cual (N ≥ 3 zonas LUX-IMB en 40 pts, A/H ≥ 8, regreso al 75 %), calculada sólo con USATECH (Dukascopy, mid).
- **Operación en NQ:**
  - **Base:** NQ − USATECH al cierre del minuto de la señal.
  - **Niveles:** objetivo y stop de USATECH + base, redondeados al tick de NQ; el stop siempre hacia afuera.
  - **Entrada:** primer tick de la vela siguiente de NQ.
  - **Resolución:** todo con los ticks de NQ.
  - **Fricción:** canónica de NQ, 1,5455 pts.
  - Sin vela de NQ en ese minuto, no se opera (se cuenta).
- **Ejecuciones:** 2. `E1A/T1/S3` (borde cercano) y `E1A/T3/S3` (borde lejano), con el stop más allá del extremo. Son 2 pruebas.

## Justificación económica
USATECH (CFD sobre el Nasdaq 100) y NQ siguen el mismo índice. Las zonas del CFD marcan dónde el precio dejó huecos. Si la vuelta a
esas áreas tiene contenido, tiene que pagar también en el futuro, que es lo operable. El CFD sólo es el sensor.

## Cómo podría refutarse
- La media neta en NQ ≤ 0, o muy por debajo del P&L de las mismas señales en USATECH: el traslado no funciona (base, horario, feed).
- Que funcione en un período y no en el otro no refuta (régimen), pero tampoco confirma.

## Qué es y qué no es
- **Datos:** 2025-08-05 → 2026-03-31 y 2026-04-01 → 2026-09-30, en corridas separadas.
- **Es desarrollo, no confirmación.** U1 se encontró y se indagó en USATECH en estos mismos meses: las señales ya se vieron. Lo
  nuevo es el P&L en NQ de esas señales.
- **Confirmar exige forward** (USATECH y NQ desde el 2026-10-01), con una regla de pérdida máxima por operación. Hoy el stop más
  allá del extremo no tiene tope; ver la regla nueva de la guía.
- **Pruebas:** 2 ejecuciones × 2 períodos = 4, registradas como `u1_cruzado/{p1,p2}`.

## Resultado (2026-10-23) — desarrollo, no confirmación
| período | ejecución | operaciones NQ | media neta NQ | IC90 (sesiones) | p | acierto | mismas señales en USATECH |
|---|---|---:|---:|---|---:|---:|---:|
| 2025-08 → 2026-03 | T1 (borde cercano) | 49 | **+16,8** | [6,3, 26,4] | 0,001 | 82 % | +17,8 |
| 2025-08 → 2026-03 | T3 (borde lejano) | 52 | **+21,5** | [10,4, 32,7] | 0,002 | 77 % | +20,9 |
| 2026-04 → 2026-09 | T1 | 90 | **+21,1** | [11,9, 30,2] | < 0,001 | 82 % | +17,5 |
| 2026-04 → 2026-09 | T3 | 92 | **+28,4** | [15,7, 40,9] | < 0,001 | 79 % | +23,7 |

- **El traslado funciona:** las señales de USATECH operadas en NQ dan lo mismo o más que en el propio CFD. La base NQ − USATECH
  (mediana 100 a 133 pts) se absorbe al trasladar los niveles. 10 de 13 meses son positivos.
- **El sensor importa:** U1 calculada con las zonas del propio NQ daba +0,4 en 2025-08 → 2026-03 (`SPEC_U1_INDAGA.md`); con las
  zonas del CFD, operando el mismo NQ, da +16,8. La señal está en las zonas del CFD (feed de cotizaciones de 24 h, otros huecos M1),
  no en las del futuro.
- **Cola izquierda:** la peor operación pierde −157 (P1) y −218 (P2) pts; se gana el 77–82 % de las veces.
- **Por qué no confirma:**
  - U1 se eligió en USATECH en estos mismos meses: descubrimiento en agosto–marzo, réplica y selección en abril–septiembre.
  - La familia probó millones de celdas.
  - El resultado en NQ está atado a esa selección. Muestra que la idea se traslada al instrumento operable, pero es evidencia de
    desarrollo.
- **Confirmación pendiente:** forward desde el 2026-10-01 en USATECH y NQ. Es apertura del holdout de este candidato y requiere
  decisión de Nico, el pedido de los ticks de USATECH de octubre (Dukascopy) y una regla de pérdida máxima por operación.
