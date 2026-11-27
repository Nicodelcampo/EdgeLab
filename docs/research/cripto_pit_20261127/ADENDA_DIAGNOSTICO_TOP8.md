# CRIPTO-PIT — adenda: diagnóstico supervivencia contra amplitud (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO (adenda diagnóstica, escrita después de ver `RESULTADO.md`; no cambia su lectura).

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- Etapa EF3 (diagnóstico sobre DESC y REP ya mirados). Familia `CRIPTO_BINANCE`. Pruebas: 2 (1/N con 10 y 20 pb).
- Herramienta: `python tools/cripto_pit.py medir --top 8`.

Cambio respecto a falla previa: `RESULTADO.md` atribuyó la REP negativa a la selección de monedas sin probarlo. Pasar de las 8 monedas
de hoy a 25 cambió dos cosas a la vez: la supervivencia (ahora incluye las dadas de baja) y la amplitud (más monedas chicas). Esta adenda
separa las dos. El universo punto en el tiempo se limita a sus 8 primeras por volumen (rango ≤ 8), con las mismas reglas y la misma
escala (8 / n_elegibles = 1).

Antecedentes: `cripto_pit_20261127/RESULTADO.md`; `auditoria_cartera_20261126/RESULTADO.md` §4.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 USD sobre $10.000; diagnóstico sobre datos ya mirados: no promueve nada).

Potencia previa: la misma que el pre-registro (REP de 12 meses: no distingue efectos menores a ≈ $250/mes). Es un diagnóstico, no una
confirmación.

Diagnóstico de mecanismo: sin grilla. Las reglas están congeladas; sólo cambia el universo.

## Justificación económica
Si la ventaja de la tendencia cripto existe en las monedas grandes y se diluye en las chicas (más costo y más ruido), el top-8 punto en el
tiempo conserva la REP positiva y la explicación es la amplitud, no la supervivencia. Si el top-8 también da REP negativa, lo que explica
la diferencia es la selección de monedas con información de hoy.

## Cómo se lee (decidido antes)
- REP del 1/N > 0 con 20 pb → la diferencia es amplitud: un universo top-8 es la forma a seguir (en papel, sin abrir el holdout).
- REP ≤ 0 → la diferencia es selección (supervivencia): se mantiene la lectura de `RESULTADO.md`.

## Cómo podría refutarse
La atribución «supervivencia» queda refutada si el top-8 punto en el tiempo replica (REP > 0) con 20 pb.
