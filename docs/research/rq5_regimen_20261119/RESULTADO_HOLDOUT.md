# RQ5-REGIMEN: holdout A5 hasta el 2026-09-30 — positivo pero no concluyente (resultado, 2026-11-20)

Estado: RESULTADO — apertura única, autorizada por Nico y registrada antes de calcular (`ADENDA_APERTURA_HOLDOUT.md`; `HOLDOUT_VENTANAS.jsonl`:
`RQ5_REGIMEN::holdout_A5_hasta_20260930`, que también consume la de `ROBOQUANT_A5`).
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- Datos: `HOLDOUT_OPS.csv.gz` y `HOLDOUT.json`.
- Regla congelada: la fábrica (RQ5 original).
- Ventana: meses HOLDOUT de A5 entre 2018-01 y 2026-09, cinco índices. Nada del terminal (desde 2026-10-01).

| | n | R neto/op | p (bootstrap por sesión, una cola) |
|---|---|---|---|
| **Cinco índices** | **1.871** | **+0,027** | **0,23** |
| Los cuatro que votan (NQ, ES, YM, RTY) | 1.497 | +0,038 | 0,16 |
| NQ | 367 | +0,077 | 0,06 |
| ES | 373 | +0,007 | 0,43 |
| YM | 368 | +0,047 | 0,18 |
| RTY | 389 | +0,024 | 0,31 |
| EMD (costo estimado) | 374 | −0,019 | 0,67 |
| Tramo 2025-09 → 2026-09 | 417 | +0,022 | — |

- **Fisher** (desarrollo 0,0445 × holdout 0,23): p 0,057. No llega a 0,05.
- **MDE80 del holdout:** 0,055 R; sd por operación 0,96.
- **Por mes** (27 meses HOLDOUT): +1,86 R/mes (cinco índices), 59 % de meses positivos.

Episodios: media +0,027 (n 1871); sin los 3 peores meses +0,052; sin los 3 mejores +0,002. Peores: 2025-09 −15,1; 2024-09 −11,1;
2020-04 −10,4. Mejores: 2021-07 +18,4; 2022-08 +15,3; 2018-04 +13,2.

**Lectura pre-registrada: NO_CONCLUYENTE.**
- La media es positiva, de la mitad del tamaño de desarrollo (+0,050 → +0,027), lo esperable por encogimiento.
- No es significativa: la potencia era 0,69 con el efecto entero y 0,28 con la mitad.
- Cuatro de cinco índices positivos (los cuatro que votan). NQ es el más fuerte, como en desarrollo.
- Sigue siendo una regla de cola derecha: sin sus 3 mejores meses queda ≈ 0.
- No refuta (K49) y no confirma. La apertura ya se usó: no se reintenta ni se ajusta.

## Justificación económica / cómo podría refutarse
- **Justificación:** sin cambios respecto de `RESULTADO.md` (momentum intradía temprano, neto habilitado por la fricción relativa baja).
- **Cómo podría refutarse:** queda sólo el forward. Con +0,027 R/op y ≈ 97 ops/mes en cinco índices, el e-proceso tarda ≈ 103 meses en
  decidir (supera el tope de 60, K27); con el efecto de desarrollo, ≈ 26 meses.

Aporte al referente: la confirmación limpia de RQ5 se hizo, autorizada por Nico, y no alcanza. La regla queda como positiva no confirmada:
encogida a la mitad, con NQ como el índice más claro.
