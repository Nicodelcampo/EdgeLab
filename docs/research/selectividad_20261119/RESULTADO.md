# SELECTIVIDAD: cuanto más limpio el día de tendencia, peor le va al día siguiente en la misma dirección — refutada con dosis-respuesta inversa (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (2 pruebas en `SELECTIVIDAD_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS.csv.gz`, `DESC.json`, `REP.json` (sin nominadas: REP no se leyó).
DESC de A5, NQ+ES+YM+RTY, motor calibrado K28; prueba de causalidad por prefijo del percentil: idéntico.

| Prueba | Valor | ee | p | BH |
|---|---|---|---|---|
| P1 pendiente R neto por banda (1→5) | **−0,037** | 0,013 | 0,997 | no |
| P2 R neto banda 5 (pureza ≥ percentil 95) | −0,196 (n 458) | 0,082 | 0,992 | no |

| Banda (percentil de pureza) | n | R neto | R bruto | fricción R mediana |
|---|---|---|---|---|
| B1 [0; 50) | 4.543 | −0,066 | +0,044 | 0,095 |
| B2 [50; 70) | 1.775 | −0,102 | +0,008 | 0,097 |
| B3 [70; 85) | 1.342 | −0,131 | −0,024 | 0,092 |
| B4 [85; 95) | 915 | −0,196 | −0,095 | 0,087 |
| B5 [95; 100] | 458 | −0,196 | −0,089 | 0,096 |

| R neto por instrumento (B1 → B5) | B1 | B2 | B3 | B4 | B5 |
|---|---|---|---|---|---|
| NQ | −0,047 | −0,064 | −0,174 | −0,208 | −0,167 |
| ES | −0,113 | −0,106 | −0,111 | −0,325 | −0,303 |
| YM | −0,077 | −0,187 | −0,060 | −0,165 | −0,242 |
| RTY (desde 2017) | +0,034 | +0,033 | −0,259 | +0,029 | +0,088 |

| R neto por época | B1 | B2 | B3 | B4 | B5 |
|---|---|---|---|---|---|
| 2006–11 | −0,177 | −0,211 | −0,218 | −0,178 | −0,326 |
| 2012–17 | −0,154 | −0,203 | −0,126 | −0,301 | −0,386 |
| 2018–25 | +0,045 | +0,013 | −0,094 | −0,153 | −0,024 |

Episodios: media -0.196 (n 458); sin los 3 peores meses -0.148; sin los 3 mejores -0.272; peores {'201007': -9.75, '201206': -9.44, '202105': -6.28}; mejores {'202502': 9.57, '201910': 10.17, '202303': 10.2}.

Diagnóstico de mecanismo: una sola perilla (percentil de pureza), cinco bandas fijas y disjuntas; la operación es de apertura a cierre del día
siguiente con stop 0,25 × ATR20. Diferencia con Z: Z entra el día siguiente con objetivo temprano (sale por objetivo en ≈ 93 % de las
operaciones) y filtra con la EMA de cubetas; acá se mantiene hasta el cierre.
- El signo inverso (fade del día de tendencia limpio) aparece en los datos pero no estaba pre-registrado: si se quiere probar, es una hipótesis
  nueva sobre datos no mirados (REP o forward), no una conclusión de esta corrida.
