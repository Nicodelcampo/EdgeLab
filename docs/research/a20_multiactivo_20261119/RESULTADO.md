# A20-MULTIACTIVO: A20 no se transfiere a YM, RTY ni EMD (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (27 pruebas en `A20_MULTIACTIVO`, registradas antes de correr).
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- Datos: `OPS.csv.gz` (sólo meses DESC y REP de A5; HOLDOUT y EMBARGO descartados sin leer) y `RESULTADO.json`.
- Lectura: meses DESC del régimen 2018-01 → 2025-07.

| Índice | Ops/mes | Fricción/R | R bruto | R neto (fábrica) | p | MDE80 | 2022+ | Vecinos positivos |
|---|---|---|---|---|---|---|---|---|
| YM | 19,3 | 0,082 | +0,017 | −0,074 | 0,88 | 0,18 | −0,076 | 0 / 8 |
| RTY | 19,0 | 0,083 | +0,064 | −0,034 | 0,72 | 0,19 | −0,015 | 0 / 8 |
| EMD (costo estimado) | 19,8 | 0,085 | +0,028 | −0,080 | 0,86 | 0,20 | −0,074 | 0 / 8 |
| *NQ (referencia, A20-REGIMEN)* | *20* | *≈ 0,03* | | *+0,052* | | | *+0,185* | |

Diagnóstico de grilla: 27 variantes; operaciones por celda 967/1046/1137 (mín/mediana/máx); 0 celdas casi vacías (< 157 op.); número
efectivo de variantes 1,79; perillas inertes: p2 (multiplicador del SuperTrend), p4 (stop duro); Spearman(operaciones, R) −0,844.

Episodios: media −0,063 (n 3142, fábrica de los tres índices); sin los 3 peores meses −0,024; sin los 3 mejores −0,129.

**Veredicto pre-registrado: NO_TRANSFIERE.**
- La fábrica es negativa en los tres índices y los 24 vecinos también.
- El bruto es apenas positivo (+0,02 a +0,06 R) y la fricción relativa (≈ 0,08 R) es casi tres veces la de NQ.
- Los nulos no son significativos (MDE80 0,18–0,20 R): no refutan A20, pero tampoco la sostienen fuera de NQ.

Por el pre-registro: A20 queda sólo en NQ y sólo en forward. No se abre holdout de estos índices.

## Justificación económica / cómo podría refutarse
- **Justificación:** el mecanismo (seguir la tendencia intradía) no da neto donde la fricción relativa es alta. Lo de NQ es compatible
  con una ventaja de fricción, no con un mecanismo general.
- **Cómo podría refutarse:** el forward de A20 en NQ con media ≤ 0.

Aporte al referente: A20 no se generaliza, así que no se apuesta tamaño a ella fuera de NQ; queda como serie de vigilancia en forward.
