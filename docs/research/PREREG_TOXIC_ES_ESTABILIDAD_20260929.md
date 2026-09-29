# TOXIC-ES-1: estabilidad de la capa *toxic* frente a no-*toxic* en ES — PRE-REGISTRO target-free (2026-09-29)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · OK de Nico: «si» (29/09).
**Origen:** auditor, tras el STOP de ES (`RESULTADO_CONTEXTOS_L2_ES_20260929.md`). *toxic* es un overlay determinista sobre
un score de flujo/spread/cancelaciones/agotamiento, desestacionalizado, con umbrales de entrenamiento (entrada q90 con 2
minutos de confirmación, salida q75 con 3). No depende de las semillas del HMM, que es lo que dio STOP. El STOP de los cuatro
climas sigue vigente; esto pregunta sólo si la capa binaria *toxic* / no-*toxic* es **estable en el tiempo**.

## Población (event-space enumerado)
Estado continuo por minuto, no evento. Alternativas escritas: (a) minutos elegibles etiquetados de evaluación [elegida:
es donde el modelo no se ajustó]; (b) también entrenamiento [sólo como referencia de la proporción]; (c) sólo RTH
[descartada como primaria: la capa se definió sobre toda la sesión]. 32 sesiones de evaluación de ES (23/07–11/09).
Datos ya existentes (`artifacts/l2_contexts/ES/labels.parquet`); sin re-extraer, sin re-ajustar umbrales, sin retornos.

## Criterios (todos deben pasar; fijados antes de mirar)
- **E1 deriva entre mitades:** proporción de minutos *toxic* en la 1.ª mitad de evaluación (16 sesiones) vs la 2.ª: la razón
  mayor/menor ≤ 2,0 **y** el IC 90 % bootstrap por sesión de la diferencia contiene 0.
- **E2 fuera de entrenamiento:** proporción en evaluación dentro de [0,5×; 2×] de la de entrenamiento.
- **E3 persistencia:** mediana de racha ≥ 5 min y < 50 % de las rachas de ≤ 3 min.
- **E4 no es la hora:** ninguna franja de 2 h concentra > 50 % de los minutos *toxic*, y un clasificador de sólo-hora
  (franja de 30 min, hora de Chicago) no supera a la mayoría por más de 2 puntos de exactitud.
- **E5 no es un par de días:** ninguna sesión aporta > 15 % de los minutos *toxic* de evaluación, y ≥ 75 % de las sesiones
  tienen al menos una racha *toxic*.
- **Sensibilidad (no decide):** todo repetido sin 11/08 y 12/08 (grabación incompleta); proporción semanal publicada.

## Resultado posible y alcance
PASS = la capa es estable en ES jul–sep y habilita proponer el paso 2 (información sobre costos/riesgo, con manifiesto y OK).
FAIL = la capa *toxic* de ES no es estable; no se usa. Ninguno de los dos dice nada de utilidad económica.
**Cómo podría refutarse:** deriva entre mitades, proporción fuera de rango respecto de entrenamiento, rachas de 1–3 min, o
concentración en una franja o en pocos días.
