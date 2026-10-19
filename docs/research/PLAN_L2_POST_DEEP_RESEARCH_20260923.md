# Plan L2 después de los dos deep research (2026-09-23)

**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
**Fuentes:** `docs/research/external/DEEP_RESEARCH_L2_A_20260923.md` (A) y `..._B_20260923.md` (B), producidos a partir de `SOLICITUD_DEEP_RESEARCH_L2_20260923.md`. Son material externo: sus cifras marcadas [NO VERIFICADO] no se usan como hechos.

## 1. En qué coinciden los dos (lo tomo como punto de partida)

1. Predecir el mid-price con el libro **no** es un edge para nosotros. La señal dura ~2 cambios de mid (Kolm et al. 2023, en acciones) y nuestra latencia estimada es de 100–300 ms.
2. Donde el L2 aporta es en medir costos, en funcionar como filtro o contexto de señales de minutos (*meta-labeling*) y en decidir si ejecutar pasivo o agresivo.
3. Se empieza con modelos simples: OFI/QI/microprice con logística o ridge, y después LightGBM. Deep learning solo con mucha más historia.
4. Ablación de latencia obligatoria (libro retrasado 100/250/500 ms). Si el efecto muere a 250 ms, no existe para EdgeLab.
5. Los fills pasivos sobre MBP son optimistas: se exige un escenario pesimista positivo.
6. VPIN no se usa. Spoofing, iceberg y absorción sobre MBP son **features de estado a testear**, no señales ni evidencia de intención.
7. Unas 30 sesiones pre-holdout de GC no tienen potencia. Hace falta historia comprada o réplica entre instrumentos.

## 2. Dónde divergen, y cómo lo resuelvo

| Tema | A | B | Decisión |
|---|---|---|---|
| Agresor de los ticks como verdad de referencia | Lo usa para validar la heurística del L2 | Advierte que puede ser inferido | **Verificado hoy: es inferido.** En GC 08-26 (2.804.464 ticks), `buy` ⇔ precio ≥ ask y `sell` ⇔ precio ≤ bid en el 100 % de los casos. Es la regla de cotización, no el tag 5797. Compararlo con el L2 mide consistencia, no exactitud. La verdad de referencia requiere trades con agresor nativo (Databento `trades`). |
| Databento | "$125 ≈ 14 meses de MBO de ES", compra recomendada | Pedir cotización y revisar licencia antes | Cotizar con `metadata.get_cost` y leer la licencia **antes** de comprar. La cifra de A sale de la página del proveedor y no está verificada por nosotros. |
| Kaggle GPU | P100 o 2×T4, 30 h/semana | P100 retirada el 15-sep-2026; la cuota actual no está verificada | Vale B, porque es más reciente. Verificar en la UI. De todos modos es irrelevante hasta tener más historia. |
| MDE con 30 sesiones | 0,37–0,55 σ (significancia) y 0,51–0,69 σ (con potencia 0,8) | Esquema general, pide simular | Se publica el MDE por simulación con bootstrap por sesión en cada pre-registro. |
| Horizontes de la grilla | 5 s – 900 s | Incluye 100 ms – 30 s como grilla de investigación | Horizonte mínimo = 3 × latencia medida. Por debajo, solo como diagnóstico. |

## 3. Qué se hace, en orden

### Fase 0: sin mirar retornos, sin STOP (arranco ya)
- **0.1 Pseudo-eventos.** Agrupar filas con el mismo timestamp de 100 ns, con sensibilidad ε = 0,1–5 ms, y calcular features solo al cierre del grupo. Nuevo `edgelab/data/l2_events.py`, con tests.
- **0.2 Invariantes y exclusiones.**
  - Excluir el bootstrap hasta tener 10 niveles por lado y 60 s desde la última ráfaga de ADD.
  - Marcar huecos (Δt > p99,99 por hora).
  - Mantener una **lista versionada de días defectuosos** (11/08, días "Success" sin L2, días con DELETE fuera de rango) antes de cualquier análisis.
  - Distribuir por hora el ~0,3 % de desacuerdo con L1.
- **0.3 Tabla de costos por instrumento, bloque de 30 min y tamaño** (receta A-D.3 / B-D3):
  - Spread cotizado y efectivo.
  - Profundidad 1..10.
  - Costo de barrer N = 1, 2, 5, 10 contratos.
  - *Realized spread* a 5 y 60 s.
  - Resultado: un parquet versionado.
  - La comisión real la pone Nico, porque depende del broker o la prop firm.
  - **Solo datos pre-holdout.** Los costos no se calibran con julio–diciembre.
- **0.4 Reloj de eventos.** Tiempo físico mediano de 2, 10 y 100 cambios de mid, por instrumento y hora. Decide qué horizontes están al alcance con nuestra latencia.
- **0.5 Consistencia del agresor.** Comparar el agresor inferido en el L2 contra el de los ticks en los días que se solapan, sabiendo que las dos son inferencias. Más una prueba de sensibilidad: invertir al azar y en ráfagas el p % de los signos y medir cuánto se mueven delta y OFI.
- **0.6 Nulos de los detectores.**
  - Iceberg: tasa de recarga ≥3 frente a un nulo de tiempos de ADD permutados dentro de la sesión.
  - Spoof: contra el mismo tipo de nulo.
  - Absorción, reformulada como **residual de impacto** `r = ΔP − β̂·OFI` (A-B.8).
  - Si un detector no supera a su nulo, se da de baja del visor como "folklore".

### Fase 1: medición de latencia (la corre Nico en NT8, en cuenta sim)
- Add-on de registro: timestamps de decisión, envío, ack ("Working") y fill, más el tick local del fill, sobre 1 contrato micro en sim y después en real.
- Resultado: la distribución p50/p90/p99. Reemplaza la grilla supuesta.

### Fase 2: información condicional (**requiere OK de Nico, regla STOP**)
- M0 (sin libro) contra M1 (logística sobre OFI integrado, QI, microprice − mid, spread y profundidad) en GC pre-holdout.
- Etiqueta de costo a h ≥ 3 × latencia, con libro retrasado según la latencia medida. Ablaciones: placebo, sin la hora del día y trades-only.
- Réplica sin retocar en 6E, con presupuesto de multiplicidad propio.
- **Se descarta si** no hay IC inferior > 0 a h ≥ 30 s con L = p90 medido, o si no supera a M0.
- Antes de correr: paquete STOP con manifiesto, N efectivo, MDE y riesgos.

### Fase 3: donde el L2 tiene mejor encaje con nuestra latencia
- **M3, meta-labeling:** features L2 en el instante de eventos de familias vivas sobre ticks (aVolClusterPOI, "vela extrema → carrera asimétrica"). Pregunta: ¿el filtro mejora la expectativa neta del primario?
- **M4, ejecución:** pasiva contra agresiva según QI, con cola pesimista y markouts. Pregunta: ¿ahorra costo?
- Las dos pasan por STOP.

### Fase 4: historia comprada (la decide Nico)
- Cotización de Databento: 1 mes de MBP-10, MBO y `trades` de GC, 6E y ES, con licencia leída.
- Test de paridad NT8 contra Databento en 5 días solapados: si la correlación de OFI/QI/spread a 1 s es < 0,95, hay que recalibrar.
- `trades` con tag 5797 da la **verdad de referencia del agresor**.
- Recién con 12 meses o más de datos: M2 (LightGBM) a escala, M10 (universal pooled) y, como mucho, una CNN chica.

## 4. Qué NO hacemos (los dos informes coinciden)

- No usar VPIN.
- No usar FI-2010 como referencia.
- No reportar accuracy o F1 como evidencia.
- No entrenar DeepLOB o Transformers con 30 días.
- No generar datos sintéticos para descubrir edges.
- No aceptar fills al toque del precio.
- No calcular features dentro de un mismo grupo de timestamp.
- No perseguir lead-lag por debajo del segundo.
- No transportar costos entre instrumentos.
- No rescatar subgrupos post hoc.

## 5. Impacto sobre lo ya construido

- **Visor:** iceberg, spoof y absorción quedan como herramientas de hipótesis. Se agrega la marca de pseudo-eventos y un panel de invariantes violados (recomendado por A y B), y se conserva el censo *as-of*.
- **Detector de absorción** (`AbsorptionTracker`, S4 de `L2_VISOR_RESOLUCION_20260923.md`): se mantiene, pero su versión investigable es el residual de impacto (0.6).
- **Holdout:** sin cambios. La propuesta de correr la frontera sigue suspendida (regla 95 / INC-006).

## Cómo podría refutarse este plan

- Si 0.4 muestra que en GC y 6E 100 cambios de mid ocurren en menos de 3 × latencia en casi todas las horas, **ningún** horizonte de información del libro es alcanzable y se pasa directo a la Fase 3 (M3/M4).
- Si 0.3 muestra costos de round-trip mayores a los movimientos típicos a 1–5 min, la Fase 2 no tiene espacio económico.

Aporte al referente: los dos informes convergen en que, con nuestra latencia, el valor del L2 está en costos, ejecución y contexto, no en predecir el próximo tick. Este plan ordena el trabajo en esa dirección y deja las mediciones que pueden descartar el enfoque antes de gastar en modelos.
