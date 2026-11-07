# Curso y traducción — canasta estática, sólo lo que está congelado

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / `RANGO_PREAPERTURA`
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`

## Curso

H-REG-1 y H-REG-2 no pasan. Seguir rotando por racha o por el tercil de la sesión previa no acerca un edge neto. La canasta que el control estático repite es `PREAPERTURA-ES`, `PREAPERTURA-NQ` y `DRC-YM-4`, medida sólo sobre la serie publicada.

Lo que corresponde ahora:

1. No abrir el holdout. El R diario no fue recomputado contra ticks.
2. No traducir `DRC-YM-4`. La familia `DOBLE_RETROCESO` no tiene módulo en el checkout. Inventarla no es una estrategia.
3. Traducir de preapertura sólo los ejes que la coordenada fija sin cortes perdidos. El tercil de ancho (`alto` en ES, `bajo` en NQ) queda fuera de la orden.
4. La orden sirve para simulación y paper en NT8 (ES o NQ, 1 minuto) y, como proxy de CFD, en JForex. No es una promoción y no se opera con dinero real.

## Qué ejecuta la orden

| | ES | NQ |
| --- | --- | --- |
| Intento | 0, el primer cierre fuera del rango | 1, la reentrada después de tocar la mitad |
| Stop | un tick más allá del borde opuesto | igual |
| Salida | cierre de la vela de las 15:55 ET | igual |
| Rango | velas que cierran de 09:16 a 09:30 ET, al menos 12 | igual |
| Entradas hasta | 11:30 ET | igual |
| Cuerpo, volumen, eficiencia | cualquiera | cualquiera |
| Ancho / ATR | no se filtra | no se filtra |

Código: `edgelab/research/rango_preapertura_operable.py`, `nt8/strategies/RangoPreapertura.cs`, `tools/jforex/RangoPreapertura.java`.

En NT8, ES usa `Intento = 0` y NQ usa `Intento = 1`. En JForex el default es USA500 con intento 0; para el caso NQ, instrumento `USATECHIDXUSD` e intento 1. El CFD no es el futuro que produjo la serie.

## Qué falta para acercarse a un edge

Recuperar los cortes del E0 de `ancho_rango`, o recomputar la celda contra ticks de pre-holdout, y recién ahí una sola apertura de holdout de esta canasta. Sin eso, paper de esta orden mide la regla de reloj, no la celda publicada.
