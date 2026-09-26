# Sensibilidad de aVolClusterPOI a ruido de ±1 en el volumen por tick (2026-09-02)

**`DIAGNOSTIC_NO_CODE_CHANGED`.** Kernel `avolcluster-sensitivity-20260902`, code_commit
`41eebbc`. 33.804.950 ticks del intervalo operable, 3 semillas, 399,7 s en 4 vCPU.
`outcomes_accessed=false`, `holdout_accessed=false`.

## La pregunta

El ruido real medido contra NT8 es de ±1 a ±5 unidades de volumen por celda
(`avolcluster_parity_full_20260902/`). ¿Cuánto cambian las zonas si se perturba el volumen
por tick en esa magnitud? El número decide si conviene insistir con este indicador o pasar
a uno que no dependa de un perfil de volumen por precio.

## Resultado: dos tercios de las zonas cambian

| semilla | zonas base | zonas perturbadas | idénticas | **turnover** |
|---|---|---|---|---|
| 11 | 409 | 395 | 212 | **0,642** |
| 22 | 409 | 388 | 186 | **0,696** |
| 33 | 409 | 397 | 214 | **0,639** |

**Turnover medio: 0,659.** Perturbando el volumen de dos tercios de los ticks en ±1
(`pct_ticks_perturbed ≈ 0,667`), **cambia el 66 % de las zonas**.

El detalle que lo hace grave: **la cantidad de zonas casi no se mueve** (409 → 388-397, un
3-5 %), pero **son otras zonas**. El indicador produce una cantidad estable de resultados
que son, en dos de cada tres casos, distintos. Un consumidor que sólo mirara el conteo no
notaría nada.

## Bug en la métrica secundaria, declarado

`blocks_decision_changed = 28.147 = 100 %` en las tres semillas **es incorrecto y debe
ignorarse**. El código compara `d0` (lista de strings de decisión) contra `b1` (lista de
dicts de bloque): un string nunca iguala a un dict, así que cuenta el 100 % siempre. Error
de quien escribió el kernel, no un hallazgo.

**No afecta el resultado principal.** El turnover de zonas se calcula sobre conjuntos de
claves `(bottom, top, kind)` correctamente construidos, y es la cifra que sostiene la
conclusión.

## Qué implica

1. **La paridad exacta con NT8 es, para este indicador, probablemente inalcanzable.** No
   porque el algoritmo esté mal traducido — se verificó idéntico línea por línea — sino
   porque el diseño amplifica diferencias mínimas: mediana de ~66 celdas × 2 como umbral
   binario. Cualquier discrepancia de reconstrucción del volumen, del tamaño que sea, se
   propaga a la geometría.
2. **Refuerza el precedente** `BIGTRAP2_PARIDAD_IMPOSIBLE_2026-08-21.md`: hay indicadores
   cuya paridad exacta no es alcanzable por construcción, no por falta de esfuerzo.
3. **Da criterio para elegir indicador.** Un detector que no agregue volumen por celda de
   precio —como `HFTZonesNQImpulseV2_5`, que trabaja sobre secuencia de ticks y calibra
   medianas sobre miles de muestras de sesión— no tiene este amplificador. **No está
   medido**: compararlo exige correr el mismo test sobre él.

## Lo que este test NO dice

- No mide la sensibilidad del otro indicador. Sin ese número, la comparación es cualitativa.
- No prueba un solo nivel de ruido: se perturbó ±1 sobre dos tercios de los ticks. No se
  midió una curva de ruido menor, que diría si hay un régimen tolerable.
- No reclasifica el gate de paridad, que sigue en `FAIL`.
