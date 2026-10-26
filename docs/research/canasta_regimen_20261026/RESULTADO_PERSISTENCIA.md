# Resultado — CANASTA-REGIMEN-1: persistencia del rendimiento de la grilla U1 (USA500, USA30, USATECH, XAU; feb-2023 → mar-2026)

Estado: RESULTADO (EF2, diagnóstico; holdout y réplica abr–sep intactos)
Fecha: 2026-10-26. Pre-registro: `PREREGISTRO_PERSISTENCIA.md` (commit anterior a la corrida). Datos crudos: `resultados/*_RESULTADO.json`
(kernels `embudo-canasta-*-persist-20230102`, dos cuentas de Kaggle). 64 pruebas registradas antes de lanzar.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Persistencia de régimen (la condición de la canasta): no detectada, con potencia limitada
Régimen = ρ(desfase 0) − ρ(desfase 12) entre el rendimiento de cada celda en formación y en prueba (Spearman, unidad = ventana).
| formación→prueba | USA30 | USA500 | USATECH | XAU |
|---|---|---|---|---|
| 1→1 | +0,046 (t 1,8) | +0,014 (t 0,5) | +0,009 (t 0,3) | **−0,054 (t −2,3)** |
| 3→1 | +0,020 (t 1,0) | −0,004 (t −0,2) | −0,011 (t −0,5) | −0,037 (t −1,8) |
| 3→3 | 0,000 (t 0,0) | −0,005 (t −0,1) | −0,035 (t −0,9) | −0,052 (t −2,1) |
| 6→3 | −0,008 (t −0,2) | +0,033 (t 1,0) | −0,019 (t −0,5) | −0,018 (t −0,9) |
| MDE (potencia 0,8) | 0,05–0,13 | 0,05–0,10 | 0,06–0,09 | 0,05–0,06 |

Regla pre-registrada (t ≥ 2 positivo en ≥ 2 instrumentos): **no se cumple en ningún horizonte**. El único t ≥ 2 es negativo (oro:
lo que persiste a 12 meses es MÁS que lo que persiste al mes siguiente). Lectura con alcance: en estas celdas, instrumentos y período, un
componente de régimen mayor que ≈ 0,05–0,10 de correlación de rangos queda descartado; uno menor no se puede distinguir.

## 2. Lo que sí persiste: calidad ESTÁTICA (y en USATECH, positiva)
La correlación total es chica pero positiva en casi todo (+0,02 a +0,08) y **no baja con el desfase de 12 meses**: lo que se repite
es qué celdas son buenas o malas en general, no qué celdas están en racha. El decil superior de formación, operado 12 meses después:
| P&L neto por operación (pts) | USA30 | USA500 | USATECH | XAU (USD/oz) |
|---|---|---|---|---|
| promedio de todas las celdas | −2,4 a −3,0 | −0,25 a −0,35 | **+0,08 a +0,76** | −0,30 a −0,33 |
| decil superior, desfase 0 | −1,4 a −0,7 | 0,00 a +0,17 | +0,8 a +2,0 | −0,22 a −0,14 |
| decil superior, desfase 12 | −1,3 a +1,6 | −0,02 a +0,39 | **+1,6 a +2,6** | −0,06 a +0,05 |

USATECH es el único donde la grilla U1 entera es positiva neta en promedio y donde el decil superior sigue positivo un año después.
Es coherente con lo que ya se sabía (U1 nació en USATECH y su mejor candidato, U1-CRUZADO, usa USATECH como señal), pero **parte de este
período (2025–2026) es el del descubrimiento de U1**: no es dato nuevo para la familia. Lo nuevo es 2023–2024.

## 3. La canasta como una regla (32 variantes)
Ninguna pasa BH q 0,10 sobre las 64 pruebas (la mejor: USATECH, formación 1 mes, k 10 por t: +2,68 pts/op, t 2,05, 62 % de meses
positivos; p unilateral ≈ 0,02 contra un umbral de BH ≈ 0,0016). En USATECH 7 de las 8 variantes dan neto total positivo; en USA30 y
XAU casi todas negativas; USA500 mixto. Consistente con §2: donde la grilla es buena (USATECH) cualquier canasta lo es; rotar por
rendimiento reciente no agrega.

## 4. Conclusión
- **Refutado, con este alcance**: «el rendimiento mensual a trimestral de las celdas de la grilla U1, en estos 4 CFD, feb-2023 → mar-2026,
  persiste por régimen lo suficiente para una canasta que rote por rendimiento reciente».
- **No refutado** (NO MEDIDO, ver `MEDIDO_NO_MEDIDO.md`): régimen definido por el estado del mercado, otras gramáticas, futuros con ticks,
  horizontes de días/semanas, otras reglas de canasta, y el período desde abr-2026.
- **Pista nueva**: calidad estática de U1 en USATECH (§2). La siguiente pregunta no es «qué celda está en racha» sino «qué tienen en
  común las celdas que son buenas en USATECH todos los años»: candidata a una campaña propia (pre-registro nuevo, réplica abr–sep 2026 en
  NQ, que es ventana A3 no usada por esta familia).
