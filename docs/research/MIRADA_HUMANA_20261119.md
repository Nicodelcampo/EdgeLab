# Dónde la mirada global humana encontró (o puede encontrar) lo que el análisis mecánico de la noche pasó por alto (2026-11-19)

Estado: VIGENTE — revisión descriptiva sobre operaciones ya medidas (no cuenta pruebas). Pedido de Nico: «fijate en qué casos de los
descubrimientos o descartes de esta noche sucede el mismo fenómeno [que en Z] en el que la sensibilidad y estrategia humana, la manera
global de pensar humana, podrían complementar o ayudarte a descubrir algo que pasaste por alto».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## El patrón de Z
Las preguntas de Nico («tiene una curva parecida a R, ¿por qué no entra?», «¿pesa más que funcione en Russell o que sea un pico?») llevaron
a mirar **qué hace cada parámetro** en lugar de leer estadísticos de grilla. Resultado: la «variante rápida» era una celda vacía, las perillas
eran un solo eje (severidad del filtro), había dosis-respuesta en tres índices y la fábrica estaba en una meseta. La falla mecánica: tratar
una grilla como un conjunto de variantes independientes y una cifra promedio como una sola historia.

## Casos de la noche con el mismo fenómeno (verificados)
| Caso | Lectura mecánica de la noche | Lo que muestra mirar el mecanismo / la historia | Consecuencia |
|---|---|---|---|
| **A20** | INTERMEDIO desde 2017 con «81/81 variantes positivas» | 3 de sus 4 parámetros no cambian nada (todas ≈ 2.080 operaciones, R ≈ +0,055); sólo importa el stop duro. **Número efectivo de variantes 1,2**: la grilla es una sola estrategia repetida | Las «81/81» y el PBO de A20 no son evidencia de meseta. Su evidencia real es UNA serie: más débil de lo que decía el acta |
| **R** (control) | REGIMEN_ROBUSTO, 81/81 | Variantes realmente distintas: 57 a 1.947 operaciones, comparten en mediana 27 % de las operaciones de la fábrica, número efectivo ≈ 2,8; el umbral muestra la misma dosis-respuesta que Z (120 → +0,25; 80 → +0,15) | El veredicto se sostiene; R y Z son el mismo tipo de mecanismo (cuanto más selectivo, mejor) |
| **Pico de VIX** | «Apagado desde 2018» (−0,02 R) | El negativo lo hacen 3 meses de crisis (oct-2018, mar-2020, ene-2022); sin ellos +0,09 | No está apagado: pierde en los crashes. Hipótesis: filtro de crash definido ex ante |
| **IBS y Double Seven** | «Apagadas desde 2018» | En meses de crisis −0,53 y −0,80 R/op; fuera de ellos +0,03 y +0,07 | Mismo caso. (Turnaround Tuesday y cambio de mes, no: siguen planas) |
- Salvedad honesta: la lista de meses de crisis la elegí yo mirando la historia; vale para generar la hipótesis, no como resultado.

## Casos donde la mirada humana probablemente agregue (no verificados; ideas para pre-registrar)
1. **Confluencia de señales con bruto real y neto negativo** (RQ5/RQ6, FM1/FM2, Dual Thrust, SOM, Franklin): un operador combinaría «sólo
   cuando dos o tres coinciden en el día y la dirección»: menos operaciones, más ventaja por operación, la fricción pesa menos. El análisis
   las midió una por una y las descartó una por una.
2. **Filtro de crash para la reversión corta** (IBS, Double Seven, pico de VIX): definido ex ante (p. ej. VIX9D/VIX > 1 o caída de la SMA200),
   probado en REP. Sólo para cuenta de broker (varios días).
3. **Entrada al cierre en Carril 2:** se midió entrando a las 18:00 (desvío declarado); la literatura pone la ventaja en el cierre de las
   15:55. Una persona preguntaría primero si el desvío mató el efecto.
4. **«Severidad» como eje común:** R (umbral), Z (cubeta/EMA) y probablemente T comparten la idea «cuanto más selectivo el disparo, mejor»: un
   diseño propio podría usarlo como perilla única con dosis-respuesta pre-registrada (más fácil de validar que una grilla).

## Guardas nuevas (en la guía y en el registro de errores)
- **K55:** antes de leer una meseta, un PBO o «N/N variantes positivas», publicar el número de operaciones por celda y el número efectivo de
  variantes (participación de autovalores de las series mensuales). Una celda casi vacía no es una variante; una grilla de casi-copias no es
  evidencia de robustez. Y antes de recomendar una variante, mirar qué hace mecánicamente cada parámetro.
- **K56:** antes de declarar una regla «apagada» en una época, descomponer el promedio por episodio (meses): si unos pocos meses explican
  el signo, el veredicto es «pierde en X», no «murió».
