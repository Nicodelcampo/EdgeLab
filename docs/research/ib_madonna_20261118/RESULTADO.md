# IB-MADONNA: resultado (2026-11-18)

Estado: RESULTADO — corrida RELANZADA con el código corregido (sólo velas de 5 min completas; la v1 está en `descartada_v1/`). Los números coinciden con la v1 hasta el tercer decimal (V3 +0,043 en lugar de +0,044). pre-registro `PREREGISTRO.md`, diseño `DISENO.md`. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `CALIBRACION.json` (13/16, recalibrada), `DESC.json`, `CORRIDA.json` y
`OPS_DESC_REP.csv.gz`.

## Veredicto: 0 nominadas en DESC. La Madonna (fade del primer rechazo en el borde del IB) PIERDE en bruto, con potencia
| Variante | n | R bruto | EE | años + | neto operable (n) |
|---|---|---|---|---|---|
| V0 Madonna | 3.334 | −0,128 | 0,031 | 20 % | −0,092 (175) |
| V1 balance | 2.073 | −0,098 | 0,039 | 30 % | — |
| V2 IB ancho | 1.562 | −0,162 | 0,046 | 40 % | — |
| V3 aceptación → continuación | 4.265 | **+0,044** | 0,018 | 60 % | −0,002 (1.909) |
| V4 ruptura fallida | 2.735 | +0,021 | 0,025 | 65 % | −0,053 (620) |
| V5 objetivo VWAP | 3.334 | −0,147 | 0,029 | 10 % | — |
| V6 hacia el cierre previo | 1.745 | −0,133 | 0,042 | 15 % | — |
| V7 clímax de volumen | 515 | −0,202 | 0,072 | 25 % | — (no calibra) |
| V8 impulso LUX-IMB | 668 | −0,108 | 0,063 | 20 % | — |
| V9 sin Open-Drive | 3.157 | −0,123 | 0,032 | 20 % | — |
| V10 doble prueba | 1.387 | −0,029 | 0,034 | 35 % | — |

- **Contrastes de filtros:** −0,09 a +0,09, ninguno con nivel. El mejor, V1 − complemento, da +0,079 con p 0,094.
- **V3** tiene p 0,0073 frente al umbral BH de 0,0063: no se nomina. Su neto operable es ≈ 0.

## Qué significa
- **El primer rechazo del borde del IB no defiende:** el precio vuelve a atravesarlo más de lo que llega a la mitad.
  - En 20 años y tres índices, el fade pierde −0,13 R en bruto antes de costos.
  - Coincide con F-OP1-FADE-NIVEL-LIMPIO (el primer regreso a un nivel de la sesión no rebota) y con «los clusters grandes no defienden».
  - Ningún filtro de contexto (balance, IB ancho, gap, volumen, impulso, Open-Drive) lo da vuelta.
- **Las variantes a favor de la ruptura son las únicas positivas en bruto** (V3 +0,044; V4, la ruptura fallida, ≈ 0). Ninguna paga los
  costos.
- **Pista nueva (NO adoptada; requiere pre-registro propio):** la «Madonna inversa», operar hacia la ruptura después del rechazo. El signo
  de V0 la sugiere, pero no es el espejo exacto de V0 (cambian el stop y el objetivo). Se probaría en los meses REP, que nadie usó, como
  hipótesis nueva.
- **Holdout A5:** sin abrir.
