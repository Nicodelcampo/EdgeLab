# Confirmación congelada de H-ZONAS (LUXIMB-HVN) — USATECH 2023-01-03 → 2025-07-31

Estado: PRE-REGISTRO de confirmación (2026-11-11, OK de Nico: «las dos»). Escrito y committeado ANTES de generar la tabla.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4.
Familia `LUXIMB_HVN`; reserva de LORD++ `LUXIMB_HVN::confirmacion_h_zonas_20261111` (paso 1, nivel 0,0109); 2 pruebas registradas
(`luximb_hvn/confirmacion_h_zonas`).

## Qué se congela (de `EXPLORACION.md` y `F-LUXIMB-ZONAS-VS-CONTROL`)
- **H1:** en la entrada al confirmar (E0, a mercado hacia A) con stop 0,5·D y objetivo 1,0·D, el R neto medio de las expansiones del
  visor (`D3_20_a0_z2`: ≥ 3 zonas OG/VI en el 25 % inicial) es MAYOR que el de las expansiones del control sin condición de zonas que
  no son del visor (`D3_20_a0_z0` y no z2). Desarrollo: +0,04 / +0,17 / +0,09 / +0,005 (4/4 ≥ 0).
- **H2:** lo mismo con stop 0,35·D (no mirado en desarrollo; fricción ≈ 0,06 R).

## Datos
USATECH (Dukascopy, `edgelab-dukascopy-nq-usatech`), 2023-01-03 → 2025-07-31, con el MISMO kernel y código que las tablas de
desarrollo (`tools/luximb_hvn.py lanzar USATECH 20230103 20250731`). Declarado: esa ventana la usó U1 (ancestro del linaje vía
EXPANSION_ZONAS) para SU regla; ninguna regla de LUX-IMB se midió ahí. Los primeros ≈ 500 tramos no marcan (percentiles causales).
Costos: los de NQ como referencia (USATECH no es operable tal cual).

## Análisis (congelado en `tools/luximb_hvn_confirmar.py`, una sola vez)
Diferencia de R neto medio visor − control; p por permutación de etiquetas dentro de cada sesión (10.000); 5 sub-bloques
cronológicos; decisión con la reserva de LORD++ (Simes + BH sobre las dos p). CONFIRMADA = confirmada por LORD++ y ≥ 4/5
sub-bloques positivos; EN_CONTRA = diferencia ≤ 0; si no, NO_CONFIRMADA (con su MDE).

## Potencia (antes de mirar)
≈ 830 eventos del visor y ≈ 10.000 de control esperados: error de la diferencia ≈ 0,04 R, MDE80 ≈ 0,1 R contra +0,075 de
desarrollo, y el nivel de LORD++ es 0,011: **la potencia es baja**; un NO_CONFIRMADA con diferencia positiva no mata la pista.

## Cómo podría refutarse
Diferencia ≤ 0 en USATECH 2023–2025 (con potencia para 0,1 R) o menos de 3/5 sub-bloques positivos.

## Nunca
Cambiar definiciones, ejecuciones, costos o ventana después de ver la tabla; correr el análisis dos veces.
