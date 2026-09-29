# Resultado CLIMA-NQ-EST-1: estabilidad temporal de los climas L2 de NQ (2026-09-29)

Pre-registro `PREREG_CLIMAS_NQ_ESTABILIDAD_20260929.md` (commiteado antes de medir). Target-free. Salida:
`l2_contexts_NQ/CLIMA_NQ_EST_1_resultado.json`. 40 sesiones de evaluación (29/07–23/09), 20 de entrenamiento.

| Estado | Veredicto | E1 mitades (IC 90 % dif.) | E2 eval / entren. | E3 racha mediana | Falla |
|---|---|---|---|---|---|
| calm | **FAIL** | 55,8 % → 76,2 % ([−0,31; −0,11]) | 66,2 % / 29,7 % | 18 min | E1, E2 |
| normal | **FAIL** | 22,0 % → 9,5 % ([+0,06; +0,19]) | 15,6 % / 38,2 % | 11 min | E1, E2 |
| volatile | **FAIL** | 12,3 % → 4,7 % ([+0,02; +0,14]) | 8,4 % / 20,8 % | 15 min | E1, E2, E5 |
| **toxic** | **PASS** | 9,9 % → 9,5 % ([−0,05; +0,05]) | 9,7 % / 11,3 % | 7 min | — |

Proporción semanal de *calm*: W31 15 % → W33 75 % → W39 **91 %**; *normal* y *volatile* se apagan en paralelo.
Sensibilidad sin las 7 sesiones desde el roll (no decide): los tres FAIL se mantienen; *toxic* pasa E1–E4 pero una sesión
supera el 15 % de sus minutos (E5).

## Lectura
1. **El modelo de 4 climas de NQ no es usable.** Sus estados base cambian de proporción de forma masiva y sostenida
   dentro de la propia evaluación: lo que en julio era *normal/volatile* en septiembre es casi todo *calm*. Pasó la compuerta
   de semillas porque es estable **entre inicializaciones**, no **en el tiempo**; la compuerta original no medía esto.
2. **La capa binaria *toxic* / no-*toxic* de NQ pasa** todos los criterios pre-registrados: nivel estable entre mitades y
   respecto de entrenamiento, rachas de 7 min, no es la hora ni unos pocos días. Es lo único usable, y sólo como binario.
3. **Consecuencia sobre NQ-CRUCE25-CLIMA** (`RESULTADO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md`): su nulo global sigue en pie,
   pero la lectura por *calm/normal/volatile* queda sin sentido porque esos estados no son estables en el tiempo. La celda
   *toxic* (+7 a +9 pp, sin potencia) es la única que se apoya en una etiqueta estable.
4. Contraste con ES: allí *toxic* derivó y aquí no; no se transporta nada entre instrumentos.

Siguiente paso posible (necesita manifiesto y OK de Nico): *toxic* / no-*toxic* de NQ como filtro de ejecución (spread
efectivo y deslizamiento, controlando hora y actividad).
