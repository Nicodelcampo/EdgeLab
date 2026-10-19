# CLIMA-NQ-EST-1: estabilidad temporal de los 4 climas L2 de NQ — PRE-REGISTRO target-free (2026-09-29)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8` · OK de Nico: «dale» (29/09).
**Por qué:** los climas de NQ pasaron su compuerta (semillas, cobertura, hora) pero nunca se midió su estabilidad en el
tiempo; en ES la capa *toxic* falló justo ahí (TOXIC-ES-1). Antes de construir un filtro de ejecución sobre NQ, esto.

## Población
Estado continuo por minuto: minutos elegibles etiquetados de las **40 sesiones de evaluación** de NQ (29/07–23/09), el
modelo con PASS (`artifacts/l2_contexts/NQ/`), sin re-entrenar ni tocar umbrales. Referencia: las 20 de entrenamiento.
Mismo event-space y mismas alternativas escritas que TOXIC-ES-1.

## Criterios
**Los mismos E1–E5 de `PREREG_TOXIC_ES_ESTABILIDAD_20260929.md`, sin cambiar umbrales**, aplicados a cada estado por
separado (calm, normal, volatile, toxic) como binario estado / resto. Código: `tools/toxic_es_estabilidad.py --inst NQ`.
- Un estado es **usable** sólo si pasa E1–E5.
- **El modelo de 4 climas es usable como tal sólo si pasan los 4.** Si pasa un subconjunto, se usa sólo ese binario (p. ej.
  *toxic* / no-*toxic*), nunca los 4 climas.
- Advertencia escrita antes de mirar: E4 (≤ 50 % en una franja de 2 h) y E5 (≤ 15 % en una sesión) pueden fallar en los
  estados raros por construcción; si pasa, ese estado igual queda fuera. No se relajan.
- **Sensibilidad (no decide):** sin las 7 sesiones desde el roll (15/09–23/09); proporción semanal publicada.

## Cómo podría refutarse
Deriva entre mitades de evaluación (la 2.ª mitad incluye el roll), proporción fuera de [0,5×; 2×] de entrenamiento,
rachas cortas, concentración horaria o en pocos días.
