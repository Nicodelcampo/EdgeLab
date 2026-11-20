# CANASTA-CORRELACION: T, R, Z-banda y RQ5 diversifican; A20 no cubre, suma riesgo (resultado, 2026-11-20)

Estado: RESULTADO — descriptivo, pre-registrado (`PREREGISTRO.md`), 1 lectura contada.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `RESULTADO.json`, `SERIES_DIARIAS_R.csv.gz` (R diario por estrategia). Herramienta `tools/canasta_correlacion.py`.
- **Ventana:** los 70 meses DESC y REP de A5 entre 2018-01 y 2025-07. Se cuenta 1 R por operación.
- **Corrección del pre-registro (texto, antes de leer):** decía «91 meses». Esa cifra es el calendario completo; con DESC + REP son 70.

Episodios: el peor mes de todas las canastas con RQ5 sólo en NQ es 2019-11, y 2020-03 si RQ5 va en cuatro índices. La caída máxima de la
canasta con A20 viene de A20 en 2018–2021, sus años negativos.

## Correlación mensual (Pearson)

|  | A20 | T | R | Z-banda | RQ5 (4 índices) | RQ5 NQ | NQ % mes |
|---|---|---|---|---|---|---|---|
| A20 | 1 | 0,25 | 0,32 | 0,06 | 0,24 | 0,38 | **−0,51** |
| T | | 1 | 0,14 | −0,04 | 0,16 | 0,25 | −0,10 |
| R | | | 1 | 0,17 | 0,24 | 0,27 | −0,02 |
| Z-banda | | | | 1 | −0,05 | 0,08 | −0,13 |
| RQ5 (4 índices) | | | | | 1 | 0,62 | −0,12 |

**Correlación diaria:** T–RQ5 NQ 0,47, R–RQ5 NQ 0,37, A20–T 0,28. Z-banda está en ≈ 0 con todas.

- Las correlaciones entre T, R, Z-banda y RQ5 son bajas o moderadas (−0,05 a 0,27 mensual): **sí diversifican**.
- **A20 no cubre.** Es la única con beta corta (−0,51 contra NQ), pero también está correlacionada en positivo con las demás (0,25–0,38).
  Gana los mismos días de tendencia bajista que ellas. En los meses alcistas en que pierde, ellas no la compensan lo suficiente.

## Por estrategia (R por mes, 1 R por operación)

| | R/mes | t mensual | % meses + | Peor mes | Caída máx. (R) |
|---|---|---|---|---|---|
| A20 | +0,59 | 0,49 | 46 % | −18,3 | −94,3 |
| T | +2,03 | 3,60 | 57 % | −5,9 | −16,7 |
| R | +1,32 | 3,50 | 64 % | −3,2 | −8,2 |
| Z-banda | +0,63 | 2,93 | 54 % | −3,2 | −5,4 |
| RQ5 NQ | +1,00 | 2,61 | 63 % | −6,3 | −18,8 |
| RQ5 (4 índices) | +2,44 | 1,99 | 61 % | −21,4 | −60,3 |

## Canastas

| Canasta | R/mes | t mensual | % meses + | Peor mes | Caída máx. (R) | R/mes con NQ > +3 % | R/mes con NQ < −3 % |
|---|---|---|---|---|---|---|---|
| **T + R + Z-banda + RQ5 NQ** | **+4,98** | **5,17** | **71 %** | −10,4 | **−23,1** | +2,8 | +4,9 |
| Las cinco en NQ (+A20) | +5,58 | 3,00 | 57 % | −24,9 | −90,3 | −1,8 | +13,2 |
| Las cinco, con RQ5 en 4 índices | +7,02 | 3,01 | 59 % | −28,8 | −101,7 | −2,3 | +15,1 |
| Canasta B (T + R + Z-banda) | +3,98 | 5,21 | 70 % | −7,2 | −19,5 | +2,6 | +3,6 |

**Descriptivo, sólo 2022-01 → 2025-07** (régimen elegido mirando la curva de A20, 34 meses):

| Canasta | R/mes | t | % meses + | Caída máx. (R) |
|---|---|---|---|---|
| Sin A20 | +6,24 | 4,57 | 82 % | −13,7 |
| Con A20 | +8,89 | 3,51 | 65 % | −35,8 |

## Lectura
- **La mejor combinación medida es T + R + Z-banda + RQ5 NQ.**
  - Respecto de la canasta B, sumar RQ5 NQ sube el R por mes de +3,98 a +4,98 con el mismo t (5,2).
  - La caída máxima apenas cambia: −19,5 → −23,1 R.
  - Gana en los tres tipos de mes de NQ.
- **A20 sube el R por mes, pero baja el t de 5,2 a 3,0 y cuadruplica la caída máxima** (−23 → −90 R).
  - Pierde en los meses fuertes al alza (−1,8 R/mes en la canasta con A20).
  - Incluso desde 2022 la caída máxima pasa de −14 a −36 R.
  - En una cuenta prop con MLL fija, A20 a 1 R por operación es el componente que quema cuentas. Si entra, que sea con un tamaño mucho
    menor que las demás. Ese tamaño no está medido.
- **RQ5 en cuatro índices** tiene más R por mes, pero ES, YM y RTY suman varianza (peor mes −21). En una canasta NQ conviene RQ5 sólo en NQ.
- **Nada de esto es confirmación.** Son operaciones de desarrollo ya vistas. La confirmación es el forward.
