# AVCL-SR-DIR — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_SR_DIR_MANIFIESTO_20261006.md`. Kernel `edgelab-avcl-sr-dir-20261006`, sobre el cache de VOL-2, unos 2 min.
- JSON: `avcl_vol1_20261005/AVCL_SR_DIR_RESULTADOS.json`. 5 pruebas más en el registro.

## Formal (RTH, bilateral, Holm 5): NINGUNA significativa, con potencia alta
| prueba | efecto | MDE | Holm |
|---|---|---|---|
| D1 H10 (alejarse de la zona, ticks) | +0,13 | 0,39 | 1 |
| D1 H50 | +0,39 | 0,81 | 0,72 |
| D2 X=8 (P respeta real − espejo) | −0,4 pp (65,2 % contra 65,7 %) | 1,4 pp | 1 |
| D2 X=16 | −0,04 pp (59,4 % contra 59,4 %) | 1,5 pp | 1 |
| D2 X=32 | +0,9 pp (55,9 % contra 55,0 %) | 1,6 pp | 0,55 |

Descriptivo:
- D1 H200 RTH: +2,4 ticks (p 0,026 sin corregir, MDE 3,0). Soporte +3,3; resistencia +1,9.
- Soporte y resistencia por separado, y ETH: todos ≈ 0.
- AT crudo: deriva ≈ 0 a 10, 50 y 200 barras.

## Lo que hay que leer antes de concluir (alcance preciso de la muerte)
**El primer toque medido es inmediato.** Real y espejo se tocan en el 95 % de los casos, con **demora mediana de
3 barras**. Las zonas OFF nacen pegadas al precio, comparadas con su ancho (unos 30 ticks), así que el "primer toque" de
este protocolo es casi siempre el roce inicial y no un **regreso** del precio después de haberse ido.

- **Lo que queda muerto:** respeto en el primer toque inmediato, y dirección del desplazamiento a 10/50 barras
  después de la creación. Sólo con esta población, esta definición de lado y estos umbrales.
- **Lo que NO se midió, y probablemente es lo que Nico ve en el chart:**
  - el **regreso** a la zona después de que el precio se alejó al menos k ticks (revisita);
  - toques n-ésimos;
  - zonas antiguas con confluencia.

  Siguiendo la memoria "un nulo puede ser del estimador": antes de cerrar la función de soporte/resistencia hay que
  medir la revisita, con la misma lógica de zona espejo.

## Coherencia con VOL-2
La zona agrega rango (VOL-2), pero sin sesgo de dirección respecto de su lado a 10/50 barras. El desplazamiento
existe, pero va **hacia cualquiera de los dos lados**: es un sello de "se mueve", no de "hacia dónde".

## Estado
`D1/D2 (toque inmediato) SIN EFECTO, potencia alta`. Soporte/resistencia por **revisita**: NO MEDIDO.
Es el siguiente candidato natural; con el cache tarda unos 2 minutos.
