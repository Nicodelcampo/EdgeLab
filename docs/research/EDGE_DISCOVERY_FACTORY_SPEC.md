# Edge Discovery Factory: Investigación Autónoma, Creativa y Adversarial de Edge

> **Especificación Maestra y Arquitectura Canónica**  
> **Origen:** Issue GitHub #42 (Nicodelcampo/EdgeLab)  
> **Worktree:** `E:\EdgeLab-edgefactory`  
> **Rama:** `local/edge-discovery-factory-foundation-20260919`  
> **Fecha de Materialización:** 2026-09-19  
> **Referente Canónico:** `docs/NORTH_STAR.md`  

---

## 1. Visión

Construir sobre EdgeLab una plataforma autónoma de descubrimiento de edge que maximice simultáneamente:

- Volumen y diversidad de hipótesis sistemáticas;
- Creatividad analítica en la combinación de indicadores, geometrías y microestructuras;
- Utilización rigurosa de indicadores, corredores y herramientas existentes;
- Calidad, trazabilidad y reutilización de la evidencia empírica;
- Probabilidad de hallar efectos reales con expectativa económica neta positiva;
- Mínima intervención humana en la fase exploratoria y preclínica;
- Protección estricta y adversarial contra lookahead, multiplicidad, sobreajuste (data snooping) y resultados espurios.

Edge Discovery Factory no es una batería estática de backtests ni un optimizador de fuerza bruta que selecciona el mejor resultado aparente. Es un sistema científico autónomo que formula preguntas, diseña experimentos controlados, genera placebos sintéticos, somete a prueba adversarial sus propios hallazgos, prioriza qué investigar a continuación y registra con igual jerarquía los resultados positivos y negativos.

### Principio Operativo Rector

> **"Explorar ampliamente, medir causalmente, registrar todo y promover muy poco."**

---

## 2. Etapas Científicas

Todo resultado o hipótesis en Edge Discovery Factory pertenece de manera obligatoria y verificable a una de las siguientes etapas científicas:

1. **`TARGET_FREE_CENSUS`**:
   - Caracterización puramente observacional y descriptiva de las microestructuras (frecuencia, tamaño, densidad, duración, correlaciones geométricas).
   - Prohibido evaluar etiquetas de retorno, MAE/MFE, targets o PnL.
2. **`EXPLORATORY_RESULT`**:
   - Descubrimiento inicial y mapeo de relaciones dentro del subconjunto de entrenamiento causal (In-Sample / Discovery Set).
   - Generación de señales candidatas y superficies de parámetros.
3. **`VALIDATION_RESULT`**:
   - Evaluación fuera de muestra temporal (Out-of-Sample) y multicontrato sin reaprendizaje de parámetros.
   - Aplicación de correcciones por multiplicidad (Holm-Bonferroni, Benjamini-Hochberg FDR) sobre toda la familia ensayada.
4. **`CONFIRMATORY_RESULT`**:
   - Evaluación pre-registrada, con hipótesis congelada, modelo de fricción adverso y réplica multiactivo.
   - Requiere revisión humana explícita antes de cualquier conclusión definitiva.
5. **`FALSIFIED_RESULT`**:
   - Hipótesis o candidatos que no sobrevivieron a pruebas de estrés, placebos, variación paramétrica o fricción.
   - Conservados de forma permanente en el registro de resultados negativos.
6. **`ABSTAIN_INSUFFICIENT_EVIDENCE`**:
   - Muestras insuficientes, quiebre de supuestos de liquidez, o divergencia entre fuentes oráculo.

---

## 3. Prerrequisitos de Integridad y Gates

Antes de habilitar cualquier análisis causal o posterior evaluación de hipótesis sobre una combinación activo–indicador, deben satisfacerse los siguientes gates machine-readable:

- `DATA_CUSTODY_PASS`: SHA-256 de 64 caracteres verificado contra el archivo fuente y ledger de custodia.
- `SESSION_RESET_PASS`: Reinicio estricto de buffers, percentiles, acumuladores y estado interno al límite de cada sesión CME.
- `CONTRACT_BOUNDARY_PASS`: Cero barras o zonas que crucen fechas de vencimiento o expiración contractual.
- `BAR_IDENTITY_PASS`: Paridad exacta `bars_25t = ceil(session_ticks / 25)` y consistencia de `bar_key`.
- `CAUSAL_AVAILABLE_TS_PASS`: Verificación de que `origin_ts <= end_ts <= signal_available_ts < executable_fill_ts`.
- `HOLDOUT_FIREWALL_PASS`: Cero ticks, barras o zonas procesadas o leídas con timestamp `>= 1782856800000000000` (2026-07-01 00:00:00 UTC).
- `ENGINE_PARITY_PASS`: Paridad demostrada contra oráculo NT8 o clasificación explícita como `PARITY_ABSTAIN`.
- `CORRIDOR_VIEWPORT_INVARIANCE_PASS`: El motor de corredores y cálculo de densidad debe ser estrictamente determinista e independiente del viewport del visor.

---

## 4. Interfaz Canónica de Eventos

Todos los indicadores (BigTrap2Absorption, HFTZones, Gaps2, VolTicksPOC2, etc.) y motores de microestructura deben emitir sus eventos adhiriendo a la siguiente interfaz canónica machine-readable:

```text
instrument              : string (ej. "ES", "6E", "NQ", "ZB")
contract                : string (ej. "ES 12-25", "6E 09-25")
session_id              : string (ej. "ES_20251117_RTH")
indicator               : string (ej. "BigTrap2Absorption", "HFTZones_V2")
indicator_version       : string (ej. "2.1.0")
config_id               : string (SHA256 truncado a 16 chars de la config)
zone_id                 : string (identificador único dentro del contrato)
origin_ts               : int64 (nanosegundos UTC de inicio de formación)
signal_available_ts     : int64 (nanosegundos UTC en que la señal es observable)
executable_fill_ts      : int64 (nanosegundos UTC de primera ejecución posible)
bar_key                 : string (ej. "tick_25")
side                    : string ("BULL" | "BEAR" | "NEUTRAL")
bottom                  : float64 (precio inferior de la zona)
top                     : float64 (precio superior de la zona)
state                   : string ("ACTIVE" | "TERMINATED" | "TOUCHED" | "CONSUMED")
termination_reason      : string ("OPPOSITE_TOUCH" | "VOLUME_EXHAUSTION" | "SESSION_END" | "NONE")
availability_quality    : string ("EXPLICIT_EXACT" | "EXPLICIT_FALLBACK" | "ORIGIN_FALLBACK_UNVERIFIED")
source_sha256           : string (SHA256 de 64 caracteres del tick data fuente)
engine_version          : string (versión de software del extractor)
```

### Regla Fundamental de Disponibilidad Causal
- Toda zona con `availability_quality == "ORIGIN_FALLBACK_UNVERIFIED"` tiene prohibido el ingreso a datasets causales (`zone_events`).
- Dichas zonas sólo pueden residir en el almacén exploratorio segregado (`zone_events_exploratory`).

---

## 5. Motores de Edge Discovery Factory

### 5.1 Motor 1: Censo Autónomo Target-Free
Analiza sin acceso a retornos futuros:
- Frecuencia y periodicidad de zonas por sesión y horario;
- Distribución de espesor en ticks (`top - bottom`);
- Duración observable hasta terminación o fin de sesión;
- Densidad espacial (KDE) y vacíos de liquidez;
- Corredores entre zonas activas y distancias relativas;
- Matriz de concurrencia y conflicto entre diferentes indicadores.

### 5.2 Motor 2: Generador Creativo de Hipótesis
Formula preguntas analíticas estructuradas combinando mecanismos económicos y microestructuras:
- **Continuación:** Expansión rápida al atravesar corredores de baja densidad.
- **Reversión/Rechazo:** Absorción institucional en murallas de alta densidad.
- **Confluencia:** Fortalecimiento de barreras por coincidencia de múltiples indicadores independientes.
- **Consumo y Fatiga:** Degeneración de la capacidad de rechazo tras $N$ retoques sucesivos.
- **Pared Opuesta:** Progresión desde la frontera de origen hasta la pared opuesta de un corredor.
- **Discordancia:** Zonas alcistas en un indicador con absorción bajista en otro como indicador de cambio de régimen.
- **Régimen Horario:** Dependencia de la efectividad respecto a la sesión (Londres, RTH, Globex, Asia).

### 5.3 Motor 3: Diseñador de Experimentos y Controles Placebo
Para cada hipótesis, formaliza:
- Definición de entrada causal (`executable_fill_ts`);
- Reglas de exclusión preclínicas (ej. proximidad a noticias Tier-1);
- Placebos de tiempo (entradas aleatorias con distribución de llegada idéntica);
- Placebos de dirección (inversión de lado LONG vs SHORT);
- Pareo de controles (muestras con idéntica volatilidad y hora pero sin zona);
- Modelos de fricción (spread bid/ask real, comisiones CME, slippage adverso).

### 5.4 Motor 4: Explorador Paramétrico y Mapeo de Superficies
- Rastreo de mesetas paramétricas estables, evitando máximos locales puntiagudos (overfitted spikes);
- Evaluación de vecinos paramétricos inmediatos ($k \pm 1$ ticks, factores $\pm 10\%$);
- Pruebas de transferibilidad directa entre contratos continuos y entre activos correlacionados (ej. ES $\leftrightarrow$ MES, NQ $\leftrightarrow$ MNQ).

### 5.5 Motor 5: Falsificador Adversarial
Aplica pruebas destructivas sistemáticas a cualquier efecto preliminar:
- **Leave-One-Session-Out (LOSO)** y **Leave-One-Contract-Out (LOCO)**;
- Exclusión de las $k$ sesiones más rentables (prueba de vulnerabilidad a outliers);
- Fricción duplicada y triplicada (prueba de muerte por spread);
- Corrección de Holm-Bonferroni y FDR Benjamini-Hochberg contabilizando cada intento;
- Test de Sharpe Desinflado (Deflated Sharpe Ratio / Bailey-de Prado) y Probability of Backtest Overfitting (PBO).

### 5.6 Motor 6: Planificador y Priorizador Autónomo
Ordena la cola de investigación mediante una función de utilidad:
$$\text{Priority} = \frac{\mathbb{E}[\text{Information Gain}] \times \text{Novelty} \times \text{Reusability}}{\text{Compute Cost} \times (1 + \text{Multiplicity Penalty})}$$

---

## 6. Almacenes Canónicos y Esquema Físico

Todos los datos se estructuran en formatos abiertos de alta eficiencia (Parquet columnar, JSON Schema estricto):

- `artifacts/edge_factory/zone_events/`: Particionado por `instrument/contract/month/`.
- `artifacts/edge_factory/zone_events_exploratory/`: Zonas no causales o con fallback.
- `artifacts/edge_factory/corridor_events/`: Eventos de corredor y vacíos de liquidez.
- `artifacts/edge_factory/session_inventory/`: Metadatos e inventario de sesiones.
- `artifacts/edge_factory/hypothesis_registry.jsonl`: Registro append-only de hipótesis.
- `artifacts/edge_factory/experiment_registry.jsonl`: Registro inmutable de ejecuciones.
- `artifacts/edge_factory/negative_results_registry.jsonl`: Registro permanente de hipótesis falsificadas.
- `artifacts/edge_factory/manifests/`: Manifiestos de integridad y hashes SHA-256.

---

## 7. Criterios de Promoción de Hipótesis

Para que una hipótesis avance entre etapas científicas:

| De Etapa | A Etapa | Requisitos Obligatorios |
| :--- | :--- | :--- |
| `PROPOSED` | `TARGET_FREE_CENSUS` | Definición causal completa, schemas validados, features target-free disponibles. |
| `TARGET_FREE_CENSUS` | `EXPLORATORY` | Muestra $\ge 300$ eventos en Train, distribución no degenerada, sin datos faltantes. |
| `EXPLORATORY` | `VALIDATION` | Expectativa neta $> 0$ bajo fricción base, meseta paramétrica contigua $\ge 3$ celdas, superación de controles placebo. |
| `VALIDATION` | `CONFIRMATORY` | Robustez en LOCO $\ge 80\%$ de contratos, $p$-valor ajustado FDR $< 0.05$, estabilidad temporal confirmada. |
| `CONFIRMATORY` | `PRODUCTION_CANDIDATE` | **Revisión humana y autorización explícita de Nicolas**, auditoría de slippage y ordenes reales. |

---

## 8. Política de Holdout y Cuarentena

- **Ventana de Holdout:** `2026-07-01` en adelante (`timestamp_ns >= 1782856800000000000`).
- **Aislamiento Total:** El holdout jamás se lee, procesa, decodifica o incluye en features, censos o exploraciones.
- **Acceso Único:** Solo se utilizará una única vez, para candidatos de nivel `CONFIRMATORY` con pre-registro firmado.
- **Falla Inmediata:** Si un proceso toca una fila del holdout, el runner aborta de inmediato con `HOLDOUT_BREACH_ABORT`.

---

## 9. Política de Resultados Negativos y Falsificación

- Ningún resultado negativo se elimina, sobreescribe ni oculta.
- Un test nulo o una hipótesis destruida por fricción es un activo científico que ahorra computación futura y previene el sesgo de supervivencia.
- El registro `negative_results_registry` conserva el motivo de falla, la correlación con otras hipótesis y la cota superior del efecto descartado.

---

## 10. Política de Autonomía y Límites Operativos

- La Factory opera de forma autónoma durante ejecuciones prolongadas respetando siempre:
  - Concurrencia controlada (default 1 proceso pesado, hilos restringidos);
  - Prioridad de proceso `BELOW_NORMAL_PRIORITY_CLASS`;
  - Límite de memoria RSS $< 1.5$ GB por proceso de extracción;
  - Escritura atómica (`*.tmp` $\rightarrow$ `os.replace`);
  - Checkpoints incrementales tras cada fragmento.
- **Intervención Humana Requerida Exclusivamente Para:**
  - Desbloqueo o reclasificación de custodia de contratos;
  - Modificación de contratos científicos o reglas maestras (`AGENTS.md`, `NORTH_STAR.md`);
  - Apertura final del holdout;
  - Asignación de capital y despliegue en cuentas reales.

---

## 11. Criterios de Detención Sistémica

Cualquiera de los siguientes eventos detiene inmediatamente la ejecución de la Factory:
1. Violación del firewall de holdout (`holdout_rows_decoded > 0`);
2. Inconsistencia o colisión en la identidad de hashes de datos fuente;
3. Fuga de memoria acumulativa que supere el presupuesto de 1.5 GB tras recolección de basura;
4. Divergencia en paridad JSON/JS o corrupción de checkpoint;
5. Contaminación causal (`signal_available_ts < origin_ts` o lookahead en features).
