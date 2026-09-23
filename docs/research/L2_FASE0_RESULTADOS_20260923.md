# L2 Fase 0: resultados sobre GC pre-holdout (2026-09-23)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Plan:** `docs/research/PLAN_L2_POST_DEEP_RESEARCH_20260923.md`, puntos 0.1–0.4.
**Qué es y qué no es:** es target-free. Mide integridad, costo mecánico, reloj de cambios de mid y volatilidad (movimiento **absoluto** del mid). **No** hay retorno de ninguna regla, dirección ni selección. Solo se usaron sesiones anteriores al holdout, con rechazo por código (`holdout_guard`).

**Procedencia:**
- Código: `edgelab/research/l2_phase0.py` y `tools/l2_phase0_metrics.py`, commit `dd279c1`. La corrida se hizo sobre un árbol con archivos sin trackear (`tree_dirty=true`), así que se registra como tal.
- Datos:
  - `E:\DatosNT8\gc_aug26_canonical_parquets`: GC 08-26, 30 sesiones del 27/05 al 30/06.
  - `E:\DatosNT8\replay.csv\GC JUN26\parquet_out`: GC 06-26, 26 sesiones.
  - Las dos son conversiones anteriores al bug ×10, con 0 inversiones de reloj verificadas.
- Artefactos locales: `artifacts/l2_phase0/GC_GC_08-26/{qa.jsonl,blocks.parquet,abs_moves.parquet}`.

## 1. Días defectuosos (reglas fijadas antes de mirar nada)

La regla está en `l2_phase0.defect_reasons`: eventos inválidos, inversiones de reloj, más de 1 % de libro cruzado, libro que nunca llega a 10 niveles por lado, o menos de 3.600 s medibles.

| Contrato | Sesiones | Usables | Excluidas |
|---|---:|---:|---|
| GC 08-26 | 30 | **29** | 20260611 (`INVALID_EVENTS=1`: el DELETE del nivel 10, ver S3 de `L2_VISOR_RESOLUCION_20260923.md`) |
| GC 06-26 | 26 | 4 | 20260601 (1 evento inválido) y **20260603–20260626: `BOOK_NEVER_FULL`**. En junio es el contrato que vence y su libro nunca llega a 10 niveles por lado. No es un defecto del dato sino una población distinta (el contrato no operable). Queda fuera de la tabla de costos. |

## 2. Costos mecánicos, GC 08-26 (29 sesiones, en ticks de 0,1)

Medianas entre sesiones de cada bloque, en reloj ART:

- **Spread cotizado.** Mediana de ~4 ticks en casi todo el día, ~3,4–3,6 ticks entre las 13:30 y las 16:30 ART, y 5,5–6,2 de noche. El tiempo con **spread de 1 tick es ~0 %**.
- **Profundidad en el mejor nivel:** ~1,5–1,9 contratos.
- **Barrido.** Costo contra el mid de 1 contrato: p50 2 ticks (1,5 en las mejores horas). De 5: ~3 ticks. De 10, p90: ~5 ticks.
- **Spread efectivo de los trades:** medio spread de ~1,5–2,2 ticks, ponderado por volumen.

**Advertencia central (abierta).** En el oro principal se espera spread de 1 tick y más profundidad. Las cotizaciones L1 crudas confirman lo mismo dentro de este feed (20260615: spread p50 = 4 ticks, 1,5 % del tiempo a 1 tick, tamaño mediano 2). O el mercado de GC 08-26 era así en ese período, o **el feed/replay de NT8 no representa el libro completo**. No se puede resolver con datos propios: lo resuelve el **test de paridad contra Databento** (Fase 4 del plan). Hasta entonces, estos costos valen **para este feed** y no se usan como costo de ejecución real.

## 3. Reloj de eventos (plan 0.4)

Mediana de segundos hasta el k-ésimo cambio de mid, desde cada segundo:

| Bloque ART | k=2 | k=10 | k=100 |
|---|---:|---:|---:|
| 10:30–11:30 (apertura NY) | 0,14–0,18 | ~1,0 | ~10 |
| Resto del día | 0,3–0,8 | 2–5 | 20–50 |
| 17:00–18:00 | 1,2–1,5 | 7–9 | 76–95 |
| 18:00–19:00 (pausa CME) | — | — | — (excluir) |

**Límite 2 del plan: NO descarta.** Con una latencia supuesta de 250 ms, el umbral es 3 × latencia = 0,75 s. Los **2 cambios** (el horizonte donde la literatura ubica la información del libro) ocurren antes de ese umbral en casi todas las horas, así que están fuera de alcance, como anticipaban los dos informes. En cambio, **10 cambios (1–9 s) y 100 (10–95 s) sí están al alcance**. Se recalcula con la latencia medida (Fase 1).

## 4. Movimiento absoluto contra costo (límite 1 del plan)

Mediana del |Δmid| a 60 s y a 300 s, en ticks, contra un costo round-trip = spread p50 + 0,5 tick de comisión **[comisión SUPUESTA, no verificada]**:

- A **60 s**: ratio movimiento/costo **1,0–3,3**. Para que una apuesta direccional con movimiento simétrico m y costo c tenga expectativa positiva hace falta acertar la dirección con p > 0,5 + c/(2m), o sea **0,65–0,83**. Es inalcanzable en la práctica.
- A **300 s**: ratio **2,3–8,1**. Hace falta p > **0,56** en la apertura de NY (10–11 h ART, ratio ~8) y ~**0,62** en el resto de las horas activas (ratio ~4).

**Límite 1 del plan: NO descarta a 5 minutos, sí a 1 minuto.** Hay espacio económico a partir de varios minutos, sobre todo en la apertura de NY, **siempre que** el costo real se parezca a este (ver advertencia del §2) y que exista alguna señal. Esto **no** dice que la haya: dice cuánta precisión haría falta para que valga la pena buscarla.

## 5. Qué queda de la Fase 0

- **0.5** Consistencia del agresor inferido entre el L2 y los ticks (dos inferencias) y sensibilidad a signos invertidos.
- **0.6** Nulos de los detectores (iceberg, spoof y absorción/residual de impacto).
- **Latencia real** (`nt8/EdgeLabLatencyProbe.cs`, lo corre Nico) → recalcular §3 y §4 con la latencia medida.

## Cómo podría refutarse

- **§2:** si Databento MBP-10 del mismo contrato y los mismos días muestra spread de 1 tick la mayor parte del tiempo, los costos de este feed están inflados y la conclusión "hace falta p > 0,62 a 5 min" es demasiado exigente.
- **§4:** si la comisión real supera 0,5 tick por round-trip, todos los umbrales de p suben.

Aporte al referente: hay un primer número económico concreto. Con este feed, apostar la dirección a 1 minuto necesita acertar 65–83 % de las veces, así que se descarta. A 5 minutos hace falta 56–62 %, que es exigente pero no absurdo. Eso ubica cualquier trabajo futuro con el libro en horizontes de minutos y como filtro de señales. Además queda abierta una duda seria sobre si el feed de NT8 muestra el libro completo.
