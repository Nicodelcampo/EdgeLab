# Decisiones del 2026-11-26: carteras por suma de estrategias decorrelacionadas y adaptación estructural al presente

Estado: VIGENTE — decisión de Nico, registrada por el agente.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Decisión (Nico, 2026-11-26)
> «No tenemos tantos datos como para predecir con suficiente probabilidad que valga la pena cortar estrategias según su rendimiento. Y el
> hecho de que en el tramo reciente hayan caído tanto relativamente hablando es sospechoso. La mejor jugada es sumar estrategias
> decorrelacionadas, ya que lo que mejor podemos predecir es que van a seguir decorrelacionadas. […] Lo mejor que podemos hacer es sumar más
> cantidad con curvas lo más estables posibles, porque es difícil que una estrategia pase todos los requisitos, pero promediadas entre todas
> la estadística va a mi favor. El enfoque debe estar en eso y en saber qué adaptar de la estrategia para que se adapte al presente».

## Consecuencias operativas
1. **No se apagan ni se pausan estrategias por su rendimiento reciente.** La pausa por curva de 3 meses de ESTABILIDAD-CARTERA no se adopta.
2. **La cartera crece por número de estrategias decorrelacionadas con ventaja esperada positiva**, a riesgo parejo. Se las elige por
   estabilidad (t mensual, % de años positivos, caída máxima) y baja correlación, no por R máximo.
3. **«Adaptar al presente» es estructural, no reoptimizar:**
   - se buscan parámetros en unidades absolutas (puntos, ticks, USD, horas fijas) que el cambio de nivel de precio o de volatilidad volvió
     activos o inertes;
   - se los lleva a unidades invariantes (ATR, % del precio) con el valor que tenían en su época de diseño;
   - es una sola variante declarada por estrategia, sin grilla.

## Datos que respaldan y acotan la decisión (2019-07 → 2026-09, USD con 1 micro)
- **16 series con Sharpe > 0,5:** Sharpe medio 0,90 y correlación mensual media 0,09.
- **Sharpe esperado de la cartera a riesgo parejo** con esos valores: 1,73 con 5 estrategias, 2,12 con 10 y 2,46 con 20. La suma real de
  las 16 da 2,05.
- **El límite:** promediar no convierte en positiva una ventaja nula. Con el Sharpe de cada una contraído a la mitad (selección sobre datos
  vistos), 10 estrategias dan ≈ 1,06 y 20 ≈ 1,23.
  - Cada estrategia que se suma tiene que tener ventaja esperada > fricción.
  - Una sin ventaja agrega costo y ruido, no estabilidad.

## Primer hallazgo de «adaptar al presente» (T de FundedSync)
- **Qué pasa:** el stop de T es el rango de apertura × multiplicador, acotado a [2, 100] **puntos fijos**. Con NQ a ≈ 30.000, el tope de
  100 puntos ata casi todas las operaciones (`remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz`):

| Año | 2017 | 2019 | 2021 | 2022 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| Operaciones con el stop en el tope de 100 pts | 0 % | 0 % | 29 % | 72 % | 33 % | 68 % | **93 %** |

- **Qué significa:** hoy T opera con un stop fijo de 100 puntos (≈ 0,33 % del precio), no con el stop por rango con el que se diseñó.
- **Qué se hace:** es el primer caso a medir con un tope proporcional al nivel de precio (o en ATR) igual al de su época de diseño, como
  variante única pre-registrada.
