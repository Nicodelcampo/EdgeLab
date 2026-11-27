# BONOS-RATIOS: ¿el ratio ley NY / ley local de bonos argentinos vuelve a su media? (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — antes de calcular cualquier pendiente. Lo único mirado son la calidad de los datos (fechas, volumen nulo, rango nulo)
y la cantidad de ruedas limpias por bloque.

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2**, exploratoria y sin P&L: mide sólo si hay reversión. **Familia nueva:** `RATIOS_BONOS_AR`.
- **Pruebas:** 4, un par cada una, en DESC; las nominadas se replican una vez en REP.
- Origen: la charla de Gus Lucioni (`biblioteca_ideas_20261028/RATIOS_BONOS_LUCIONI_20261126_RESUMEN.md`). Nico pidió medirlo «sin
  perder calidad».

Cambio respecto a falla previa: es una familia nueva y no hay antecedente propio. Lecciones que se aplican desde el diseño:
- **Rebote entre puntas y cierres no sincrónicos.** Fabrican reversión falsa en el primer día: la medida principal salta una rueda.
- **Fuga por la ventana:** se excluyen las ruedas cuya media móvil o ventana futura toca meses sellados.
- **Fricción:** la amplitud del desvío se compara contra el costo de ida y vuelta de las dos patas (K-fricción).

Antecedentes:
- `biblioteca_ideas_20261028/RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md` §5: data912, con spread de puntas de la foto del 2026-11-27 de
  AL30 0,09 % y GD30 0,22 %;
- `F-SELECCION-ADVERSA-PASIVA`: márgenes del orden del spread.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7:
- K32: todo por EdgeLab, con `exigir_contada`;
- K36: causalidad. La media y el desvío usan las ruedas t−20..t−1; la ventana futura, t+1..t+6;
- A5: bloques por mes; HOLDOUT y TERMINAL sin leer.

Potencia previa:
- **Ruedas limpias por par:** 417 en DESC y 169 en REP.
- **Efecto detectable:** con bootstrap por bloques de 20 ruedas, la pendiente mínima detectable con potencia 0,8 es ≈ 2,5 errores
  estándar. Se publica el error estándar de cada par como MDE.
- Antecedente de magnitud: la charla describe desvíos de 0,2–0,5 % que vuelven en el día.

Diagnóstico de mecanismo: sin grilla. Valores fijados por la charla, no buscados:
- ventana de 20 ruedas («el último mes»);
- horizonte de 5 ruedas;
- salto de 1 rueda.

Se publican también, como diagnóstico, la versión sin salto (para ver cuánto es rebote), el lag-1 de las diferencias, los tres regímenes y
la amplitud del desvío (1 y 2 desvíos estándar) contra el costo.

## Datos
- **Fuente:** data912 `/historical/bonds`, cierres diarios en pesos, del 2021-09-16 al 2026-11-26 (`data/bonos_ar/PROCEDENCIA.json`,
  con sha256).
- **Pares del mismo flujo** (cambia sólo la ley): GD30/AL30, GD35/AL35, GD38/AE38 y GD41/AL41. Las especies D quedan afuera: GD30D
  tiene 20 días con volumen nulo y 50 con rango nulo.
- **Ruedas:** se usan sólo las de volumen > 0 en las dos patas.

## Hipótesis y lectura (decididas antes)
- **H_par:** en d_t = ln(GD/AL)_t − media móvil de 20 ruedas, la pendiente de Δ = r_{t+6} − r_{t+1} sobre d_t es < 0.
  - Prueba de una cola con bootstrap por bloques.
  - Lectura en DESC con BH q 0,10 sobre los 4 pares.
  - Las nominadas se replican una vez en REP: REPLICA si la pendiente es < 0 y la t ≤ −1,645.
- **Viabilidad (descriptiva):** se compara el desvío de 2 sd con el costo de ida y vuelta de ≈ 0,36 %, que suma las dos patas y los
  derechos. Si el desvío típico de 2 sd no supera el costo, la operación del video no es viable con cierres diarios, aunque haya
  reversión.
- **Regímenes declarados:**
  - 2021-09 → 2023-11, con cepo;
  - 2023-12 → 2025-04-13, cambio de gobierno con cepo parcial;
  - 2025-04-14 →, salida del cepo.

## Justificación económica
- Los dos bonos de cada par pagan los mismos cupones y amortizaciones del mismo emisor: sólo cambia la jurisdicción.
- La diferencia de precio refleja una prima por ley NY, que cambia lento, más los flujos puntuales de quien entra o sale de una especie.
  La segunda parte debería revertir en días.
- La reversión es más fuerte cuanto más pareja es la liquidez de las dos patas.

## Cómo podría refutarse
- **Sin reversión:** pendiente ≥ 0 o no significativa en DESC, o que no replica en REP. Entonces lo que se ve en el gráfico intradía no
  sobrevive a escala diaria.
- **Sólo rebote:** reversión que aparece sin salto y desaparece con salto.
- **Sin margen:** reversión real, pero con desvíos de 2 sd menores que el costo.
- **Fuera de este alcance:** el intradía y el spread real son otra medición, que requiere grabar puntas.
