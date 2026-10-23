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
