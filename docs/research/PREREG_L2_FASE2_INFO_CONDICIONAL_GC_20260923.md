# Pre-registro: L2 Fase 2, información condicional del libro después de la latencia (GC 08-26)

**Estado:** CONGELADO antes de mirar cualquier retorno. Cualquier cambio posterior va como enmienda fechada y no reemplaza este texto.
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Autorización:** Nico dio OK a la Fase 2 (2026-09-23). Regla STOP: este manifiesto se presenta y se corre con su confirmación sobre este texto.
**Plan:** `docs/research/PLAN_L2_POST_DEEP_RESEARCH_20260923.md` §3 (Fase 2). **Antecedentes:** `L2_FASE0_RESULTADOS_20260923.md`.

## 1. Hipótesis

**H1:** con el libro observado con retraso de latencia (L = 250 ms; la latencia medida es p90 234 ms, P-77), los features del L2 **agregan** información sobre el cambio futuro del mid **por encima** de un modelo solo con trades, a horizontes alcanzables.

- **Justificación económica:** OFI, desequilibrio de colas y microprice resumen presión de compra y venta todavía no reflejada en el precio (Cont–Kukanov–Stoikov 2014; Stoikov 2018). Si esa información sobrevive a 250 ms y a horizontes de 30–300 s, es la materia prima de un filtro o señal de minutos. La Fase 0 midió que a 300 s alcanza con acertar la dirección el 56–62 % de las veces para cubrir los costos de este feed.
- **Cómo podría refutarse:** el aporte incremental del L2 (M1 − M0) tiene un intervalo cuyo límite inferior es ≤ 0 en los tres horizontes, en ambos canales.

## 2. Población y espacio de eventos

- **Espacio:** estado continuo, un muestreo por segundo. No hay eventos, así que no se elige creación, toque ni similares: se mide en cada segundo válido de la sesión. Es la opción de mayor potencia (regla "separar evento de estado").
- **Excluido por regla fija:** bootstrap (hasta tener 10 niveles por lado + 60 s), la pausa CME (18:00–19:00 ART) y los segundos cuyo horizonte cruza el fin de la sesión o la pausa.
- **Sesiones:** GC 08-26 pre-holdout usables según `l2_phase0.defect_reasons` con P-75. Son 30 sesiones, del 27/05 al 30/06/2026, fuente `E:\DatosNT8\gc_aug26_canonical_parquets`.
- **Holdout:** no se toca (rechazo por código).

## 3. Partición (cronológica, por sesiones completas)

- **Desarrollo:** las primeras **20** sesiones. Walk-forward de 4 pliegues con ventana expansiva y embargo de 1 sesión.
- **Test de desarrollo:** las últimas **10** sesiones, que se abren **una sola vez** al final.
- Normalización: media y desvío de cada feature estimados **solo en entrenamiento**.

## 4. Features (fijos, sin búsqueda)

Todos calculados con el estado del libro y los trades **hasta t − L**, al cierre de pseudo-eventos.

- **M0, solo trades:**
  - Flujo firmado (delta, con la regla de cotización) en 5, 30 y 60 s.
  - Cantidad de trades en 30 s.
  - Volatilidad realizada del mid en 60 s.
  - Bloque horario (6 dummies de 4 h).
- **M1 = M0 +:**
  - OFI del mejor nivel en 5 y 30 s.
  - OFI multinivel 1–5 (suma simple de niveles, **sin** PCA ajustada) en 30 s.
  - Desequilibrio de cola en el nivel 1 y en los niveles 1–5.
  - Microprice − mid (en ticks).
  - Spread.
  - Profundidad en el nivel 1 y en los niveles 1–10.
- **Excluidos a propósito:** los conteos de iceberg, absorción y liquidez fugaz. Sus umbrales son percentiles **de la sesión completa**, así que usan información futura dentro de la sesión (fuga). Entran en una fase posterior con umbrales causales.

## 5. Etiquetas y horizontes

- **Horizontes:** h ∈ {30, 60, 300} s (todos ≥ 3·L).
- **Canal direccional:** mid(t+h) − mid(t) en ticks. El reloj arranca en t (llegada), no en t − L.
- **Canal no direccional:** |mid(t+h) − mid(t)|.
- **Distribución completa:** se reportan los cuantiles del error y los deciles de la predicción, no solo la media.

## 6. Modelo (fijo, sin tuning)

- **Ridge** con α = 1,0 sobre features estandarizados, un modelo por canal y horizonte.
- Sin búsqueda de hiperparámetros, sin selección de features, una sola semilla (el modelo es determinista).

## 7. Métrica e inferencia

- **Primaria:** para cada sesión de test, la correlación de rangos (IC de Spearman) entre predicción y realizado. **Estadístico:** ΔIC = IC(M1) − IC(M0), promediado por sesión.
- **Inferencia:** bootstrap por sesión con 10.000 remuestreos. Se rechaza H0 si el límite inferior del IC 95 % corregido es > 0.
- **Multiplicidad:** 3 horizontes × 2 canales = **6 pruebas primarias**. Bonferroni: α = 0,05/6 por prueba, es decir IC de 99,17 %.
- **MDE:** se calcula en el desarrollo, antes de abrir el test: MDE = (z(1−α/12) + z(0,8)) · sd(ΔIC por sesión en los pliegues) / √10. Se publica junto al resultado.
- **Traducción económica, solo si la primaria rechaza H0 a 300 s en el canal direccional:** en el test, entre las muestras del decil superior de |predicción|, la tasa de acierto del signo contra el umbral de costo de la Fase 0 (0,56–0,62 según la hora). Es un diagnóstico, no una estrategia.

## 8. Ablaciones (diagnósticas, no suman pruebas)

- L = 0 y L = 500 ms: curva de decaimiento con la latencia.
- M1 con el libro de **otra sesión** (placebo): debe dar ΔIC ≈ 0.
- M1 sin bloque horario.

## 9. N efectivo, riesgos y datos faltantes

- **N de pruebas primarias:** 6. Todo lo demás es diagnóstico y así se reporta.
- **Riesgos:**
  - 30 sesiones de un solo contrato en un período de roll (mayo–junio).
  - Costos del feed de NT8 sin paridad independiente (P-76).
  - Agresor inferido.
  - Autocorrelación del muestreo de 1 s (mitigada: la unidad de inferencia es la sesión).
  - Muestra de test chica (10 sesiones): un nulo aquí puede ser falta de potencia; por eso se publica el MDE.
- **Faltante:** réplica en otro instrumento. 6E pre-holdout tiene muy pocas sesiones utilizables (08/06–16/06 se perdieron por el bug ×10; quedan ~4 de fines de junio). Solo se hace una réplica descriptiva en 6E; **no** cuenta como confirmación.
- **Qué se hace con cada resultado:**
  - Si rechaza a 300 s en el canal direccional: se pasa a meta-labeling (M3) y ejecución (M4) con un pre-registro nuevo.
  - Si no rechaza en ninguno: la hipótesis de "predicción direccional con el libro" queda cerrada **para GC 08-26, mayo–junio 2026, este feed y L = 250 ms** (con alcance preciso), y el L2 se usa solo para costos, ejecución y contexto.

## 10. Registro

Resultado, MDE y ablaciones se publican completos en `docs/research/L2_FASE2_RESULTADOS_*.md` y en el registro MEDIDO del mismo commit. Se registran también en el Edge Brain: contraejemplo o lección candidata PROPOSED/LOW.
