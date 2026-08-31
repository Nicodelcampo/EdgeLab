# HP-006 — ZB L2 order book + ML: imbalance/OFI de baseline, DeepLOB-family de challenger (V1, 2026-08-31)

- **Fecha:** 2026-08-31 (ART) · **Estado:** `HYPOTHESIS_REGISTERED_DATA_GATE_PENDING`
- **Autor:** Notion AI — Auditor Cuantitativo
- **Origen (verbatim, chat):** Nico, ~15:49 ART: "para el zb si es mejor usar l2?" → "Si puedo obtener L2 del zb, incluso para empezar a entrenar ahora. ahi aplica deeplob y redes neuronales?" → "Si, hace research de mejores prácticas para esto considerando el referente del proyecto y asentalo".
- **Registro:** entrada HP-006 en `docs/HIPOTESIS_PENDIENTES.md` (HP-005 queda reservada para el diseño GC SL/TP/BE, `BT2A_GC_SLTP_BREAKEVEN_DESIGN_V1_2026-08-30.md` §14, rama `research/bt2a-gc-sltp-breakeven-design-v1-20260830`).
- **Consistencia con líneas previas:** existe `docs/research/BT2A_GATE2_L2_START_HERE_2026-08-26.md` (`GATE_L2 = VALIDATION_IMPLEMENTED_REAL_DATA_EVIDENCE_PENDING`, rama `work/bt2a-gate2-l2-hardening-20260826`) — esa línea es validación sobre datos existentes; esta HP es una línea de DATO NUEVO + ML. Ortogonales, no se pisan.
- **NO autoriza:** compra de datos, entrenamiento con etiquetas, acceso a outcomes, ni campaña. Las puertas están en §3 y §5.

## 1. La hipótesis

ZB es estructuralmente el mejor paciente del universo EdgeLab para señal de libro:

- **Tick grueso:** $31,25 por tick (1/32) — el más caro de los 11 activos del censo (medido, `bundle_index.json` 2026-08-15) — con volatilidad baja relativa → grilla de precios tosca → colas persistentes. Con colas persistentes, la posición en cola y el imbalance son información real, no ruido (la clase "large-tick" de la literatura de microestructura).
- **Libro de rates profundo y lento:** menos flickering HFT que en equity index. En NQ/ES el libro visible parpadea y habla el tape (donde vive la campaña BT2A — coherente, no contradictorio); en ZB el libro parado es parte del mensaje.
- **El contraste medido:** ZB tiene solo 27,2M ticks — la cinta líquida más lenta del proyecto — pero cada tick vale $31,25. Poca cinta, mucho valor por nivel.

**Hipótesis testeable:** el contexto L2 de ZB (imbalance de colas top-k + order flow imbalance) predice movimientos de corto horizonte con poder estadístico que **sobrevive al costo** (fricción ~$31,25/tick por lado: la más alta en dólares del universo) — con baseline simple como piso obligatorio y la familia DeepLOB como challenger, nunca como punto de partida.

## 2. Research de mejores prácticas (2026-08-31) → traducción a doctrina EdgeLab

### 2.1 El baseline canónico existe y es exactamente nuestro caso
Gould & Bonart, "Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book" (arXiv 1512.03492): el imbalance de las colas bid/ask predice la dirección del próximo movimiento del mid, con efecto monotónico en el imbalance. **Piso de la línea:** regresión logística sobre imbalance top-k + OFI, evaluada por sesión. Nada se entrena antes de que este piso exista medido. https://arxiv.org/abs/1512.03492

### 2.2 OFI le gana al libro crudo (ordena las features)
Kolm et al., "Deep order flow imbalance: Extracting alpha at multiple horizons from the limit order book" (Mathematical Finance, 2023): los modelos entrenados sobre order FLOW imbalance superan a los entrenados sobre el libro crudo; el horizonte efectivo de pronóstico ≈ dos cambios de precio promedio; y el **information richness ratio** (log de updates de libro / cambios de precio) predice qué activos son predecibles. Traducción: las features principales son OFI/imbalance (baratas, auditables); el tensor de 10 niveles es el challenger. https://onlinelibrary.wiley.com/doi/10.1111/mafi.12413

### 2.3 Accuracy ≠ señal operable (LOBFrame)
Briola et al., "Deep limit order book forecasting: a microstructural guide" (Quantitative Finance 2025, código abierto LOBFrame): las propiedades microestructurales del activo determinan si DL sirve; alta capacidad de forecast NO implica señal accionable; proponen evaluar por probabilidad de **completar la transacción** (fill + costo), no por accuracy/F1. Traducción directa a doctrina: la métrica del veredicto es expectativa neta por señal clusterizada por sesión con el ledger de costos encima — las métricas de ML son diagnóstico, nunca veredicto. https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/

### 2.4 La arquitectura no es la frontera (TLOB 2025)
TLOB (arXiv 2502.15757): un MLP simple adaptado (MLPLOB) SUPERA al SoTA (DeepLOB incluido) en FI-2010 y en datos reales — "challenging the necessity of complex architectures"; la predictibilidad DECLINA con el tiempo (−6,68 puntos de F1 hacia datos recientes: el mercado se hace más eficiente); y las etiquetas cost-aware deterioran la clasificación pero son la única que responde la pregunta económica. Consecuencias: (a) el challenger simple entra antes que DeepLOB; (b) walk-forward obligatorio; (c) la etiqueta spread-aware es la que cuenta. https://arxiv.org/abs/2502.15757

### 2.5 La trampa de normalización (y la crisis de replicación)
DeepLOB original (arXiv 1808.03668): z-score dinámico con estadísticos de los 5 días ANTERIORES en su versión LSE (la honesta); el benchmark FI-2010 viene PRE-normalizado — y la literatura de replicación (LOBCAST; research del día en Notion, página 27e983a1) midió hasta 28 puntos porcentuales de brecha declarado-vs-reproducido. **Reglas de hierro:** estadísticos de normalización fit en train solamente, aplicados a validación/test sin refit; etiquetas como target, nunca como input; splits por sesión completa, nunca por ventana. https://arxiv.org/abs/1808.03668

### 2.6 El N efectivo no son los eventos
Con etiquetas de ventana futura, el N estadístico ≈ sesiones/ventanas no solapadas, no los millones de updates del libro (misma lección que P-44 para ticks). La potencia se calcula ANTES de entrenar, no después de ver el F1.

## 3. Fases (cada una con su puerta)

- **F0 — Data gate:** obtener L2 de ZB. Si viene del mismo canal (feed CME vía NinjaTrader/Continuum controlado por el usuario), cae bajo `docs/research/DATA_LICENSE_DECISION.md` (APPROVED 2026-08-28: custodia y cómputo privados solamente, dataset privado, sin redistribución). Lo que esa decisión NO autoriza: abrir outcomes ni campañas (sus puertas 1-6 aplican intactas). Store nuevo: ETL L2 con manifest y hashes propios.
- **F1 — Censo microestructural target-free:** IR ratio de ZB, persistencia de colas, estabilidad de profundidad, distribución de spread. Si el IR es bajo, la línea muere acá, barata. Cero etiquetas.
- **F2 — Baseline:** logística sobre imbalance top-k + OFI, por sesión, con IC clusterizado. Medido.
- **F3 — Challenger:** entrenar con etiquetas = acceso a ventanas futuras = acceso a outcomes → **requiere spec propio congelado + token de ejecución**, en Kaggle, holdout afuera. Orden de challengers: MLPLOB-style primero; DeepLOB/TLOB solo si el simple deja espacio. Walk-forward por contrato/sesión obligatorio (TLOB midió la deriva temporal).
- **F4 — Claim:** cadena G2/G3/G4 completa; holdout, una apertura. Nada de esto lo otorga este documento.

## 4. Cómo muere (refutaciones pre-escritas)

- IR ratio bajo en F1 → DL no viable en ZB; línea cerrada con evidencia.
- Baseline ≈ challenger en F3 → la complejidad no paga; se publica el baseline (si sobrevive neto) o se cierra.
- Expectativa neta ≤ 0 con fricción de ~$31,25/tick → EXECUTION_NEGATIVE honesto.
- Decaimiento walk-forward marcado → frágil a régimen, no accionable.
- LOBCAST como prior: si el baseline reproduce lo publicado pero el challenger no lo supera, la literatura de arquitecturas no aplica a este dato — y eso también es un resultado.

## 5. Lo que NO autoriza

Compra de datos (decisión comercial de Nico, separada); entrenamiento con etiquetas (spec + token propios, §3-F3); tocar el L2 de ES cuarentenado (P-56/P-57 — y es otro activo); tocar el holdout; ninguna modificación a la campaña NQ viva (Gate 1 en curso, SL/TP/BE condicionada).

## 6. Cómputo

DeepLOB-class entrena en horas en un T4 de Kaggle (cuota ~30 h/sem GPU + ~20 h/sem TPU, separadas — ver `KAGGLE_SCATTER_GATHER_MULTI_KERNEL_POLICY_V1_2026-08-31.md` §4.1). El cuello es dato congelado y disciplina estadística, no FLOPs.

## Aporte al referente

La primera línea de ML sobre libro del proyecto nace con la doctrina puesta: baseline canónico antes que red, challenger simple antes que DeepLOB, normalización sin leakage, métrica económica en vez de accuracy, N honesto, y la data gate separada de la puerta científica. Si ZB L2 entra, entra por la puerta de adelante.
