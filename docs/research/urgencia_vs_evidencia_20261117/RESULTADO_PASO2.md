# Paso 2: contracción empírica por selección — resultado (2026-11-17)

Estado: CERRADO — pre-registro `PREREGISTRO_PASO2.md`. Datos: `RESULTADO_PASO2.json` (`tools/contraccion_empirica.py`).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Resultado
| | Pares | Campañas | b (por el origen) | IC90 (bootstrap de campañas) | r medio (desvíos por operación) | Réplicas > 0 |
|---|---|---|---|---|---|---|
| Todas | 1.704 | 135 | **−0,26** | [−0,32, −0,20] | −0,077 | 37 % |
| < 1.000 pruebas | 61 | 30 | −0,25 | [−0,37, −0,13] | −0,070 | 36 % |
| 1.000–20.000 | 465 | 33 | −0,19 | [−0,30, −0,09] | −0,083 | 38 % |
| > 20.000 | 1.178 | 72 | −0,28 | [−0,37, −0,20] | −0,075 | 36 % |
Descriptivos: con ordenada libre a −0,04, b −0,15 (más ventaja en descubrimiento, algo PEOR réplica: tercil alto −0,11 contra −0,06);
el recorte de Harvey-Liu del embudo predecía ≈ 0 conservado (`conservado` medio 0,0003): optimista, pero cerca.

## La salvedad que manda (integridad antes de interpretación)
**104 de las 135 campañas replicaron en la misma ventana (2026-04-01 → 09-30)** y casi todas descubrieron en la misma (2025-08 → 2026-03).
No son 135 réplicas independientes sino, en la práctica, **un solo par de períodos**: el IC del bootstrap por campaña es demasiado angosto,
y la contracción por selección no se puede separar de un cambio común entre esos dos semestres. En las 28 campañas con otra fecha de corte,
b ≈ −0,04 y r ≈ −0,02 (casi cero).

## Lectura
1. **Lo elegido por el embudo en descubrimiento no conservó nada en su réplica**: en promedio perdió un poco (−0,08 desvíos por operación).
   Es la lección de `F-SELECCION-EN-GRILLAS-GRANDES` (cae a ≈ 0), ahora medida sobre todo el embudo y con signo levemente negativo.
2. **La regla pre-registrada se aplica con su salvedad**: el IC de b excluye la «mitad» → la media de partida para lo elegido en una sola
   criba es **≈ 0, no la mitad** (el signo negativo depende de un único cambio de período y no se usa como constante).
3. **Para las carteras** (elegidas con descubrimiento Y réplica > 0, la ventana donde casi todo lo demás falló) b es una cota inferior; su
   evidencia limpia es el holdout (v2: 31 sesiones, ≈ $108 por sesión contra ≈ $98 de desarrollo, t 1,8) y el forward.
4. **Consecuencia práctica**: la columna «contraída» de las simulaciones de Lucid (James-Stein entre las reglas de la cartera, ≈ mitad) es
   **optimista**. Hasta que el forward acumule evidencia, la expectativa honesta por cuenta está entre «cero» (+$35 a +$100) y «contraída»;
   el paso 3 lo resuelve con la evidencia forward (filtro de Kalman desde una media de partida ≈ 0) en vez de con un factor fijo.
