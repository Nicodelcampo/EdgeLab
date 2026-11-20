# A20 en NQ: el holdout A5 hasta el 2026-09-30 no está limpio (nota, 2026-11-20)

Estado: VIGENTE — respuesta al pedido de Nico «abrí el holdout de la misma manera a A20 en el activo que funciona». No se registra apertura.
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Por qué no hay apertura limpia:
- **A20-REGIMEN miró todos los meses.** NETO-PISTAS (`RZ_OPS.csv.gz`) calculó A20 en todas las sesiones de NQ de 2008 a 2026-09. A20-REGIMEN
  y la revisión del 19-nov leyeron la ventana 2017-11 → 2026-09 completa, con los meses HOLDOUT de A5 incluidos. Esos meses ya formaron
  parte de la elección de la ventana y del veredicto.
- **Lo que queda limpio no sirve sin otra decisión:**
  - el terminal (desde la sesión del 2026-10-01) es de la familia FUNDEDSYNC, que ya usó su apertura con T, Z y R;
  - el forward.

Lo que dan esos meses (descriptivo; NO es un holdout: son datos ya usados), fábrica en NQ, 2018-01 → 2026-09, R neto por operación:

| Bloque A5 | n | R/op |
|---|---|---|
| DESC | 1.161 | +0,080 |
| REP | 382 | −0,038 |
| HOLDOUT | 506 | +0,128 |
| EMBARGO | 37 | +0,016 |

Lectura:
- Los tres bloques salen de la misma ventana elegida mirando.
- Que REP sea negativo y HOLDOUT positivo es variación entre submuestras de una regla de cola derecha (sd ≈ 2,3 R), no confirmación.

Aporte al referente: evita presentar como confirmación datos que ya decidieron el veredicto. La única confirmación limpia de A20 es el forward.
