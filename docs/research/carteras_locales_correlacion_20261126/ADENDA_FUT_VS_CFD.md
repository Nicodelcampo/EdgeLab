# Adenda: curvas de capital de la cartera de futuros intradía y de la cartera CFD swing (2026-11-26)

Estado: PRE-REGISTRO — adenda de `PREREGISTRO.md`. Descriptivo; se commitea antes de calcular. No cuenta pruebas nuevas: es la misma
lectura de carteras ya medidas.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Pedido de Nico:** «suponiendo que no hay que rescatar, tengo la opción de operar futuros intradía y CFD swing. Pasame las curvas de la
  cartera de futuros y de la cartera de CFD. Sólo esas dos».

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7.

Diagnóstico de mecanismo: no aplica (sin grilla).

## Qué se grafica (fijo)
- **Cartera de futuros intradía:** INTRADIA8 de `cartera_nt8_20261125`, en USD con 1 micro, de 2019-07 a 2026-09.
  - MNQ: T, R, Z, V, RQ5 y Franklin.
  - MES: RQ5 y ES5N.
- **Cartera CFD swing:** la de FTMO Swing del veredicto maestro (`validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md`), en R
  (1 R por operación).
  - **C2_VZ** en ES y NQ, y **C2_EVRP** en ES y NQ: corridas NT8 de `candidatas_nt8_20261125/corridas_nt8_nuevas/` (`R_neto_mini`),
    2019-01 → 2026-09.
  - **Turtles GC** con entrada stop: `turtles_oro_20261117/ops/entrada_stop.csv.gz` (hasta 2026-08) y su forward de noviembre.
  - Se miden sobre precios de futuros, que son la referencia de los CFD (US500, US100, XAUUSD); los costos de CFD pueden diferir.
- **Para cada una:** curva acumulada, meses HOLDOUT de A5 marcados, por mes y t mensual, % de meses positivos, caída máxima y
  correlación mensual entre las dos.

## Justificación económica
Elegir entre las dos vías de operación sin rescate pendiente.

## Cómo podría refutarse
Si la cartera CFD swing no se sostiene en los meses HOLDOUT o la intradía cae en ellos.
