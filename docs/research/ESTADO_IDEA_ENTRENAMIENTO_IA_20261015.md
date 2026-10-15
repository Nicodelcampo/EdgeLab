# Estado de la idea de entrenamiento con IA (grilla precio×volumen y libro L2) — 2026-10-15

Estado: VIGENTE (se actualiza al cierre de cada hito)
Fecha: 2026-10-15
Familia / módulo: EXP-REV-GRID / reversal-grid + pista de libro L2
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)

## 1. La idea, tal como quedó
Predecir, en un momento de decisión posterior a una expansión, si el precio **revierte hacia ella** antes de continuar y **cuándo**, a partir de una ventana amplia y multiescala de operaciones (tiempo × precio, volumen y conteo; los rectángulos del indicador son capas opcionales, no el marco). Cambios respecto de la primera formulación:
- **Objetivo:** primer paso R / C / ninguna, con censura explícita y cabeza de riesgos competitivos en tiempo discreto (no punto exacto de giro, no softmax 2D).
- **Economía:** P&L con timeouts marcados a mercado y fricción por instrumento (ES ≈ 3,4–3,5 ticks ida y vuelta). `p_eq = (Y+c)/(X+Y)`.
- **Comparación decisiva:** contra un baseline continuo fuerte (hora, volatilidad, trayectoria, intensidad), no contra el azar.
- **Espejo:** robustez, no nulo. **No significación ≠ refutación.** Particiones según HOLDOUT-A3 y, para L2, la enmienda del 2026-09-24.

## 2. Panel de modelos (decisión de Nico, 2026-10-15)
Escalera, cada rama contra el baseline y con presupuesto y semillas declarados: baselines (logística/elastic net, LightGBM, MLP) → CNN multiescala pequeña + contexto → DeepLOB-style → Transformer chico → modelo fundacional (extractor congelado, luego LoRA sólo con el fold de entrenamiento) → aprendizaje por refuerzo como capa de política, al final, con simulador de fills.

## 3. Dos pistas
| pista | datos | horizonte | estado |
|---|---|---|---|
| **A. Grilla de operaciones (ticks)** | release v4 de ticks (ES; otras con la misma lógica) | segundos a 60 min | **otro agente**: pipeline causal ticks→barras→expansiones→tiles probado en una sesión de ES (92 → 108 tests en Kaggle, igualdad exacta de grillas); borrador de protocolo con etiqueta 32 vs 32 ticks, horizonte 300 s (propuesta, **no congelada**); caché privada de sesión creada pero reutilización no medida (la herramienta bloqueó la lectura) |
| **B. Libro L2 (MBP-10)** | ES en L2, jun–14-oct-2026 (≈100 sesiones, contratos 09-26 y 12-26) | ≤ 60 s (partición 3/4 y 1/4) | datos y herramienta listos: reconstrucción del libro 80× más rápida con igualdad exacta (`tools/l2_fast_book.py`), agregaciones de todos los instrumentos en `E:\l2_agg`, dataset privado de ES en subida a Kaggle (`tools/build_l2_release.py`) |

## 4. Qué se midió que condiciona la idea
- La familia del corredor (`EmaCorridorTrend`) **no** da un efecto neto en ES: `HA` bruto +1,5 ticks, neto −2,0; ningún filtro (T1–T5) se distingue del azar (p = 0,239). Detalle: `CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`. Consecuencia: **el indicador no debe asumirse como selector útil**; en EXP-REV-GRID es una capa a evaluar por ablación, no una premisa.
- Más de la mitad de las carreras de barrera de 100T con barrera de zona son timeouts: el diseño de etiqueta tiene que modelarlos, no ajustarlos después de ver resultados.
- ES histórico (299 sesiones) está **expuesto** (la línea del corredor inspeccionó toda la ventana, incluida abr–sep): no es réplica limpia para nada relacionado.

## 5. Decisiones de Nico registradas (2026-10-15)
Entran DeepLOB, Transformers, fundacionales y RL; se sube a Kaggle privado el L2 **solo de ES** (parquet comprimido); descarga L2 sólo de ES por ahora; el AddOn de descarga se actualizó para NT 8.1.8.3.

## 6. Pendiente de decidir (bloquea entrenamiento real)
1. **Horizonte prioritario:** corto (libro, ≤ 60 s) o largo (grilla, 15–60 min) primero.
2. **Etiqueta, barreras y costos** (propuesta del otro agente: 32 vs 32 ticks, 300 s; a discutir con la fricción de ES y la proporción de timeouts).
3. **Calendario fijo de particiones y presupuesto de modelos/semillas**; número efectivo de hipótesis.
4. **Auditoría del L2** (payload, reloj P-84, sesiones marcadas: ES 2026-08-11 y ES 12-26 del 2026-07-17) y aprobación del manifiesto del dataset (hoy `research_allowed=false`).
5. **Manifiesto congelado y OK de Nico** (regla STOP) antes de cualquier búsqueda sobre retornos.
6. Cierre de la revisión cruzada con Gemini sobre el resultado del corredor (ver `REPORTE_PARA_GEMINI_REVISION_CORREDOR_20261015.md`).

## 7. Próximos pasos propuestos (sin retornos)
- Publicar el dataset L2 de ES y verificarlo (lista de archivos y SHA-256).
- Borrador de manifiesto para la pista B (libro, horizonte corto) y generador de ventanas desde `E:\l2_agg`.
- Unificar con el otro agente la definición de etiqueta y de calendario (una sola para A y B si es posible).
- Auditoría independiente del manifiesto antes de entrenar.

*Aporte al referente:* concentra en un solo lugar qué idea de entrenamiento sigue viva, con qué datos y bajo qué reglas, y qué la bloquea, para que el próximo paso reduzca la distancia a un edge neto y no repita lo que ya midió negativo.

## Actualización (2026-10-15, tarde)
- **Decisión de Nico:** la pista L2 entrena con los pocos datos disponibles; la pista sin L2 entrena con **todo el historial de ticks** (ver costo respecto de HOLDOUT-A3 en `RESULTADOS_PILOTO_SOPORTE_EXP_REV_GRID_20261015.md`).
- **Piloto de soporte medido** (ES, 178 sesiones de descubrimiento): 32 vs 32 ticks a 300 s resuelve sólo 18,5 % (81,5 % timeouts); 32/32 a 1800 s resuelve 61,7 %. La etiqueta del borrador del otro agente debe cambiar de horizonte.
- **Revisión cruzada con Gemini:** confirma que el corredor no tiene efecto neto; ver `REVISION_RESPUESTA_GEMINI_20261015.md` para las cinco reservas.
- **L2 de ES en Kaggle:** subida en curso (nuevo intento desde el directorio del dataset para evitar un error de ruta del CLI en Windows).
- **Piloto de horizontes cortos (pista L2):** a ≤ 60 s en ES, barreras de 8 ticks exigen 72 % de acierto y barreras de 16–24 ticks vencen por timeout en 85–95 % de los casos: **la pista L2 de horizonte corto con entradas a mercado no tiene viabilidad económica en ES**; replantear como (a) información calibrada del mid con entradas pasivas y modelo de llenado, o (b) libro como contexto en horizontes de 5–30 min. Decisión pendiente de Nico.

