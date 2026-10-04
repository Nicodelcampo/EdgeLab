# MGC EMA 200/500/2000 — pruebas de familia e información direccional (pre-registro, 2026-10-04)

Estado: escrito ANTES de correr. Solo datos de descubrimiento (`trade_date <= 20260331`). Holdout (`>= 20260401`) cerrado y sin tocar. No se agregan celdas ni parámetros. Contador global de pruebas: +2 campañas de prueba (T1, T2).

## Motivo
El veredicto anterior (`p_max = 0,0998`) pesa el mejor de 21 celdas. Ese estadístico castiga la selección, pero tampoco puede confirmar nada: es poco potente. Estas pruebas miden información direccional **sin** quedarse con el máximo.

## T1 — media de la familia (21 celdas normales)
- Estadístico: media del neto tick-exact sobre las 21 celdas normales del grid ya pre-registrado (SL {100,150,200} × TP {150,…,450}; costo 0,5 ticks RT, ejecución EdgeLab causal). Sin elegir ninguna celda.
- Nulo: dirección sorteada por sesión (ε=±1 con p=0,5), mismas señales y horarios. 2.000 sorteos, semilla 20261005.
- p = P(media nula ≥ media real). Umbral 0,05.
- Predicción registrada antes de correr: media real ≈ 2.392 ticks por celda (50.238,5 / 21, de `direction_maxnull.json`); p esperado ≈ 0,3.

## T2 — información direccional por horizonte (sin SL/TP)
- Universo: las 1.643 señales del continuo corregido (cruce EMA200/EMA500 con EMA500 del mismo lado de EMA2000, decisión al cierre de barra, entrada en el tick siguiente).
- Retorno por señal y horizonte: `dirección × (mid(t+h) − mid(entrada))` en ticks, con mid = (bid+ask)/2, h ∈ {15 min, 30 min, 1 h, 2 h, 4 h} de reloj, truncado al último tick de la misma sesión y contrato. Bruto de costos (es una prueba de información, no de rentabilidad). Se cuentan todas las señales, también las que el simulador de operaciones omite por posición abierta.
- Estadístico por horizonte: suma de retornos de las señales. Nulo: dirección sorteada por sesión (suma por sesión × ε). z_h = suma real / desvío del nulo.
- Prueba: máximo de z_h sobre los 5 horizontes, 200.000 sorteos del nulo por sesión, semilla 20261005. p_max = P(max z nulo ≥ max z real). Umbral 0,05. Se reportan además z_h y p_h por horizonte (informativos).

## T3 — descriptivo (sin prueba)
- Estimación ajustada por maldición del ganador: neto del headline − media del máximo nulo (3.113 ticks de `direction_maxnull.json`), por trade.
- Trades necesarios para 80 % de potencia, una cola, α = 0,05: n = ((1,645 + 0,84) · sd / efecto)², con sd por trade del ledger tick-exact del headline.

## Regla de decisión (fijada antes de ver resultados)
- T1 p > 0,05 **y** T2 p_max > 0,05 → no hay información direccional distinguible del azar de selección con los datos disponibles: el candidato queda **DESCARTADO COMO EVIDENCIA** con lo que hay (no equivale a probar que no existe).
- T1 p ≤ 0,05 **o** T2 p_max ≤ 0,05 → la señal conserva información direccional; sigue sin ser edge validado hasta una confirmación fuera de muestra.
- Ningún resultado de estas pruebas autoriza abrir el holdout.
