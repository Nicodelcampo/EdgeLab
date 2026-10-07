# EMASEP-MGC150 — contrarian por separación de 3 EMAs en MGC 150t — resultados — 2026-10-07

Enmienda 2 de `EMASEP_CONTRA_MANIFIESTO_20261007.md`. Kernel `edgelab-sep-mgc150` (v1 falló al arrancar y se relanzó
sin cambios). JSON: `emasep_mgc150_20261007/`.

## Resultado: 0 de 486 celdas pasan, y la prueba no tiene potencia
- En 150t hay **muy pocas señales**: entre 4 y 34 por contrato y percentil. En descubrimiento quedan 38–98 trades por
  celda; 216 celdas tienen n ≥ 30.
- Neto mediano **+1,9 USD/trade**, con 122 de 216 celdas positivas. La mejor celda es p95, límite +10t, SL80 R2 BE:
  +34 USD/trade (n = 55, IC [+7, +62]), con **p max-T = 0,53**.
- Contra la dirección al azar: z máximo ≈ 2,3. Con 486 celdas, eso es lo esperable por ruido.
- Sin celdas que pasen, la confirmación no se corrió.

## Estado
`EMASEP-MGC150: SIN EFECTO DETECTADO, NO CONCLUYENTE` por falta de N, no por evidencia de ausencia. Los números
positivos no se pueden distinguir del ruido con ≈ 60 trades por celda.

Para decidirlo hacen falta **más eventos**:
- más historia de MGC/GC (por ejemplo, GC en M1 o ticks de años anteriores);
- o una grilla mucho más chica (1 umbral, 1 entrada, 1 salida) declarada de antemano.

Esta enmienda fue elegida después de ver 10t: cualquier seguimiento debe pre-registrarse con una celda única.
