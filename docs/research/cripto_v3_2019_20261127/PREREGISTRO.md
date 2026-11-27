# CRIPTO-V3-2019: la canasta CRIPTO-PIT v3, sin cambios, en el período anterior a su muestra (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — antes de calcular cualquier P&L. Lo único mirado es el universo punto en el tiempo (target-free: volumen y
fecha de alta) y el calendario de bloques A5.

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3:** réplica fuera de período con la regla congelada.
- **Familia:** `CRIPTO_BINANCE`. Esta prueba es nueva y se suma a las anteriores de la familia.
- **Pruebas:** 1, la canasta.

Cambio respecto a falla previa:
- La REP de cripto v3 quedó iterada entre v1 y v3, y su HOLDOUT A5 de 18 meses dio t 0,60. Lo único que no vio nadie es el tramo
  anterior a 2021, que la corrida original usó sólo para calentar los indicadores.
- Se corren las mismas reglas, costos y pesos de canasta, sin tocarlos:
  - pesos: XSMOM 0,3858, BetaNeut 0,3568, BAB 0,2574;
  - costos: 20 pb + funding.
- El código se reusa con tres parámetros nuevos de valor por defecto idéntico en `cripto_pit.py`, `cripto_pit_v2.py` y
  `cripto_pit_v3.py`: el período del universo, el primer mes de descarga y la ventana de evaluación. Las cachés de datos son propias.

Antecedentes:
- `cripto_pit_v3_20261127/RESULTADO.md`;
- `holdout_a5_nocme_20261127/RESULTADO.md` y `REVISION_CLAUDE.md`;
- `confianza_sin_forward_20261127/RESULTADO.md` (Sharpe deflactado 0,07).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7:
- K32: todo por EdgeLab, con `exigir_contada`;
- K36: causalidad. El universo usa el volumen de los 30 días previos al mes; los pesos se deciden al cierre de t;
- A5: sólo meses DESC y REP. Los meses HOLDOUT de 2019–2020 quedan sin leer, porque la única apertura de `CRIPTO_BINANCE` ya se usó.

Potencia previa: **muy baja; esto es un control de signo, no una confirmación.**
- El universo tiene ≥ 10 monedas elegibles recién desde 2020-04. Antes, Binance tenía pocos perpetuos USDT-M: 3 en 2020-03, 11 en
  2020-04 y 24 desde 2020-05.
- Meses DESC/REP evaluables: 2020-05 a 2020-10, unos 6.
- Con el Sharpe de desarrollo (1,29) la t esperada es ≈ 0,9 y la potencia ≈ 0,18; con el del HOLDOUT (0,49), ≈ 0,07.
- Se publica igual, con su error estándar, porque es el único tramo de cripto que nadie miró.

Diagnóstico de mecanismo: sin grilla. Son las tres reglas de la canasta y las dos excluidas (Basis carry, ResidMom), con sus parámetros
de `cripto_pit_v3.py`. Costos 10/20/30/40 pb, como en el original.

## Lectura (decidida antes)
- **Primaria:** canasta con 20 pb + funding, meses DESC+REP entre 2019-10 y 2020-12. CONFIRMA si la t mensual es ≥ 1,645;
  NO_CONCLUYENTE si la media es > 0; EN_CONTRA si la media es ≤ 0.
- Con potencia ≈ 0,18:
  - un resultado EN_CONTRA resta poco, salvo que sea grande;
  - un resultado a favor suma poco.
- **Descriptivo:** cada regla, cada costo, cada mes y la correlación con BTC.

## Justificación económica
El momentum transversal y el BAB en perpetuos (ver `cripto_pit_v3_20261127/PREREGISTRO.md`) deberían estar presentes desde que existe
el mercado de perpetuos líquidos. En 2020 había menos monedas y más concentración, lo que podría reducir la dispersión.

## Cómo podría refutarse
Una canasta con media ≤ 0 en el único tramo no mirado, sumada al HOLDOUT A5 débil (t 0,60) y al Sharpe deflactado de 0,07, dejaría a
cripto v3 sin evidencia en ningún tramo limpio. Si pasa eso, se baja de prioridad.
