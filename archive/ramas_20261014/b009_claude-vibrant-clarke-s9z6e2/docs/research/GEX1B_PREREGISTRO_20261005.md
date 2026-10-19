# GEX-1b — extensión de GEX-1 por falta de potencia (pre-registro, 2026-10-05)

Escrito **antes de correr**. Pedido del usuario: «correla más allá de esa info, porque son muy pocas sesiones con gamma negativo». GEX-1 (manifiesto `GEX1_REGISTRO_Y_MANIFIESTO_20261006.md`) queda intacto como familia propia (12 pruebas, definición gex_{t-1} < 0).

## Por qué
Con gex_{t-1} < 0 hay solo **9 sesiones en MES** (2025-07 a 2026-09) y **39 en el spot USA500** (2023-01 a 2025-06): el MDE de GEX-1 es de 0,5 a 0,7. En el histórico del DIX (2011 a 2026) solo el 8,9 % de los días tiene gex < 0 y en 2023-2026 son 42.

## Qué se agrega (mismas fuentes, mismas seis métricas, mismas sesiones)
Fuentes y períodos como en GEX-1: MES NT8 2025-07-01 a 2026-09-30 (con las 8 sesiones sin fuente omitidas y declaradas) y spot USA500 Dukascopy 2023-01-01 a 2025-06-30. Métricas: I1a, I1b, I2n, ac1, ac1abs y I2d, calculadas por sesión RTH (08:30-15:00 CT) igual que en GEX-1. Datos del DIX: solo filas anteriores a 2026-10-01.

Dos definiciones nuevas de «gamma baja», fijadas ahora:
- **Q (cuantil):** gex_{t-1} por debajo del **percentil 20 de todos los gex anteriores a t** (ventana expansiva desde 2011, mínimo 250 días). Es causal; da del orden de 100 a 150 sesiones «bajas» por fuente. Estadístico: igual que GEX-1 (media de la métrica en bajas menos resto; para I2d, diferencia de pendientes).
- **C (continua):** estadístico = **−correlación de Pearson** entre gex_{t-1} y la métrica (cinco métricas); para I2d, **−β** del término de interacción r_rest × gex_{t-1} (estandarizado) en la regresión r_last ~ r_rest + gex + r_rest·gex. Todo con el signo orientado a «menos gamma, más efecto».

## Prueba
Nulo por permutación en bloques de 20 sesiones de la etiqueta (Q) o del vector gex_{t-1} (C), 20.000 sorteos, semilla 20261007, unilateral. **Familia: 6 métricas × 2 definiciones × 2 fuentes = 24 pruebas, Holm al 5 %.** MDE = (z_{1−0,05/24} + 0,84) × desvío del nulo. Control descriptivo por quintiles de σ previo. Contador global de pruebas: +24.

## Regla de lectura (fijada antes)
Una prueba «pasa» si Holm ≤ 0,05 con el signo esperado. Se informa además si la misma métrica pasa en las dos fuentes. Sigue siendo **solo información**, no una regla operable.

## Expectativa registrada
Que I1a e I1b (amplitud) pasen en el spot con ambas definiciones, como en GEX-1; que en MES el signo coincida y gane potencia con Q y C. Esperaría poco o nada en I2d, I2n, ac1 y ac1abs.

## Límites
- No son pruebas independientes de GEX-1: usan los mismos días (y Q y C se solapan entre sí); Holm sobre 24 es conservador.
- Los días de gamma baja son pocos y se agrupan en rachas: por eso se permutan bloques.
- MES y spot no se solapan en el tiempo, pero ambos miden el mismo S&P: no agregan evidencia independiente sobre el mismo día, solo sobre períodos distintos.
- Se descarta cualquier fila del DIX o sesión desde 2026-10-01.
