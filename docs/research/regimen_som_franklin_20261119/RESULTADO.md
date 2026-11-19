# REGIMEN-SOM-FRANKLIN: las dos son señales reales (el bruto es una meseta), pero ninguna es un régimen neto como T (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (2 pruebas en `SOM`, 2 en `FRANKLIN`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS.csv.gz`, `RESULTADO.json`, `PREFIJO.json`. Etapa EF3
(2006 → 2026-09-29, desarrollo ya mirado). Procedimientos de T-REGIMEN: grilla, vecinos, PBO, quiebre sup-F, años, prefijo.

## 1. Veredictos (reglas fijadas antes de correr)
| | SOM (NQ+ES+YM, `sin_finde`, 81 variantes) | Franklin (NQ+ES, 32 celdas) |
|---|---|---|
| **(a) Señal bruta, 20 años** | **SENAL_ROBUSTA**: 81/81 con bruto > 0 (fábrica +0,055, mediana +0,053), vecinos 8/8, PBO 0,08 | **SENAL_ROBUSTA**: 32/32 con bruto > 0 (fábrica +0,115, mediana +0,062), vecinos 7/7, PBO 0,009 |
| Quiebre de la fábrica en R neto | 2017-11-13, p 0,02 (significativo) | 2020-03-24, p 0,27 (no significativo → ventana completa) |
| **(b) Régimen neto** en la ventana de decisión | 81/81 con neto > 0 desde 2017-11 (mediana +0,027; fábrica +0,030), vecinos 8/8, pero **PBO 0,84** → **SOBREAJUSTE_PROBABLE** por la regla | 7/32 con neto > 0 en 20 años (mediana −0,027; fábrica +0,005) → **SOBREAJUSTE_PROBABLE** |
| Antes / después del quiebre (fábrica, R neto) | −0,031 / +0,030; 0/81 positivas antes | −0,036 / +0,087 (quiebre no significativo) |
| Años positivos de la fábrica (neto) | 10/21 | 11/21 |
| Prefijo (corte 2015-06-30) | 2.223 operaciones idénticas | 953 idénticas |

## 2. Lectura
- **Las dos señales son reales**: el bruto es una meseta sobre todo su vecindario de parámetros, estable 20 años y sin look-ahead. Franklin
  además tiene un poco de ajuste: la celda elegida (+0,115) rinde casi el doble de la mediana de su grilla (+0,062), coherente con que se
  eligió dentro de esta misma grilla (K38).
- **Ninguna es un régimen neto como T.** SOM sí tiene un quiebre en 2017 y desde ahí todas sus variantes dan neto positivo, pero chico
  (+0,03 R) y con PBO 0,84: con 81 variantes casi iguales y un efecto chico, elegir la «mejor» por desempeño es ruido. Eso no prueba que la
  fábrica esté sobreajustada (es una entre muchas parecidas), pero la regla pre-registrada lo clasifica así y no se cambia después de mirar.
  Franklin no tiene quiebre significativo y su neto de 20 años es ≈ 0.
- Comparación con T (REGIMEN_ROBUSTO: +0,15 R neto con mediana de la grilla, PBO 0,17) y con R (AtrPhase, +0,21 de mediana, PBO 0,23): SOM y
  Franklin tienen ventaja bruta de la misma calidad estadística, pero 3–5 veces menos neto. El cuello de botella sigue siendo la fricción por
  operación, y los esquemas de tamaño no confirmaron (`../neto_pistas_20261119/RESULTADO.md` §B).
- **Qué queda vivo:** SOM y Franklin como señales (para canasta y para condicionar otras reglas), no como operables sueltas. Para operarlas
  hace falta una ejecución que baje la fricción en R sin perder bruto: la curva bruto–stop en puntos (F-VENTAJA-EN-PUNTOS-NO-ESCALA) todavía no
  se midió en ellas.
