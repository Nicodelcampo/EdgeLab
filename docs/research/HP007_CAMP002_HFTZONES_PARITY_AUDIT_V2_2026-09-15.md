# Auditoría y Certificación V2 de Paridad: Zonas Base HFT de NQ

- **Campaña:** `HP007-CAMP-002` (Fase Estructural — Paridad de Zonas Base)
- **Fecha de Auditoría:** `2026-09-15`
- **Rama Canónica Exclusiva:** `fix/hftzones-nq-parity-certification-v2-20260915`
- **Worktree:** `E:/EdgeLab_worktrees/fix-hftzones-nq-parity-certification-v2-20260915`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491)
- **Ancestros Certificados:** `924b0ac`, `06b5507`, `7f4d855`
- **Activo Bajo Examen:** `NQ` (Contrato `NQ JUN26` / `NQ 06-26`)

---

## 1. Principio Epistemológico de Separación Causal y Alcance

$$\text{Contrato Elegible (CONTRACT\_REGIME\_V2)} \neq \text{Paridad HFTZones (Zonas Base)} \neq \text{Paridad BigTrap2Absorption} \neq \text{Campo Causal} \neq \text{Edge/Outcomes}$$

1. **Objeto Exclusivo de Certificación**: Únicamente las **ZONAS BASE HFT** producidas por el detector de rachas e impulsos.
2. **Fuera de Alcance**: Clusters, corredores, campos de densidad, hipótesis de revisita, traversas, P&L, selección de parámetros por outcomes y apertura del holdout.
3. **Regla de No-Traslado**: La paridad de HFTZones **no certifica** BigTrap2Absorption. Se mantiene estrictamente `BT2A_PARITY_NQ = ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN`.

---

## 2. Fase A: Identidad del Indicador Real

Se localizó, aisló y versionó en `nt8/` la copia fuente exacta utilizada para producir el oráculo SQLite:

- **Archivo Fuente Local:** `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTZonesNQPureV4.cs`
- **Copia Gobernada en Repositorio:** [`nt8/HFTZonesNQPureV4.cs`](../../nt8/HFTZonesNQPureV4.cs)
- **Clase C#:** `NinjaTrader.NinjaScript.Indicators.HFTZonesNQPureV4`
- **Versión Declarada:** `4.1.0`
- **SHA-256 Literal:** `841cdbcccbe54ca525e20456d38d1ece0beec5fdd7b820de980bbb01acebeb63`
- **Tamaño:** 74,522 bytes
- **Calculate:** `Calculate.OnBarClose`
- **Tick Replay:** Activo en Data Series histórica
- **Serie Primaria (`BarsInProgress == 0`):** `NQ JUN26, 25 Tick`
- **Subserie HFT (`BarsInProgress == 1`):** `NQ JUN26, 1 Tick` (`TickResolution = 1`)
- **Timezone:** Wall-clock UTC registrado en ticks
- **Ventana de Exportación:** Sesiones del `2026-06-03` al `2026-06-11`

### 2.1. Comparación con `nt8/HFTClusterZonesNQ.cs`
Se ejecutó un diff estructural entre `HFTZonesNQPureV4.cs` y `nt8/HFTClusterZonesNQ.cs`:
- La función de barrido `ProcesarSweeps()` y sus helpers (`Iniciar`, `Continuar`, `Finalizar`) presentan **identidad matemática del 100.00%**.
- La fórmula de retroceso relativo (`Math.Max(MaxRetrocesoTicks, (RetrocesoPctHeight / 100.0) * sweepHeight)`), pausas máximas (`MaxPausaMs = 100`), conteo de pasos, CVD y filtros de compuerta son idénticos.
- Las únicas diferencias son puramente cosméticas (nombres de métodos con sufijo `Sweep` y tags visuales) y la invocación de clusters en la versión clusterizada.

---

## 3. Fase B: Auditoría Forense de las Anomalías de Conteo

El comparador V1 reportó 4.795 zonas NT8, 4.829 zonas Python, 4.792 exactas, 3 zonas NT8 sin pareja y 37 zonas Python adicionales. Se investigó exhaustivamente la causa raíz de cada discrepancia:

### 3.1. Diagnóstico de las 3 Zonas NT8 sin Pareja Python (`sin_par`)

| ID NT8 | Timestamp start_ts / end_ts (UTC) | dir | Precios [lo, hi] | Pasos / Valid | Total Vol | Altura (ticks) | Ticks en NT8 | Ticks en Parquet | Causa Raíz Demostrada |
|---|---|---|---|---|---|---|---|---|---|
| **4081** | `2026-06-10 15:59:59.764` | +1 | [28845.25, 28854.50] | 62 / 44 | 62.0 | 37 | **1.579** | **8** | Ráfaga masiva de cierre omitida en parquet |
| **4090** | `2026-06-10 16:01:10.180` | +1 | [28849.75, 28896.50] | 859 / 610 | 919.0 | 187 | **1.509** | **14** | Ráfaga masiva de post-cierre omitida en parquet |
| **4518** | `2026-06-11 14:35:06.036` | +1 | [28835.50, 28847.50] | 60 / 42 | 70.0 | 48 | **3.630** | **13** | Ráfaga de apertura US omitida en parquet |

**Hallazgo Crítico**:
- En NT8, la tabla `hft_flow` registró `1.579 ticks` en el segundo 15:59:59, `1.509 ticks` en 16:01:10 y `3.630 ticks` en 14:35:06.
- El archivo `NQ_06-26_ticks.parquet` sólo registró 8, 14 y 13 ticks en esos mismos segundos respectivamente (desconexión o dropout en la captura del stream crudo que construyó el parquet).
- Al faltar el 99% de los ticks en el parquet durante esos segundos, el motor Python nunca recibió los datos para construir esas 3 zonas.

### 3.2. Diagnóstico de las 37 Zonas Python sin Pareja en NT8

- **Fecha de Ocurrencia:** **100% de las 37 zonas ocurrieron el 2026-06-11**.
- **Ventana Temporal:** Entre las `14:50:08 UTC` y las `15:20:47 UTC`.
- **Causa Raíz en NT8:** En la base de datos SQLite de NT8, entre las `14:49:50 UTC` (zona id 4535) y las `15:28:50 UTC` (zona id 4536), **hay un vacío absoluto de captura de 39 minutos**:
  * `hft_flow` en esa ventana: **0 registros**.
  * `hft_zones` en esa ventana: **0 zonas**.
- Por el contrario, `NQ_06-26_ticks.parquet` cuenta con cobertura continua durante esos 39 minutos, donde el motor Python detectó legítimamente 37 zonas válidas.
- **Fuera de esa brecha de 39 minutos, la concordancia entre Python y NT8 es del 100.00%**.

### 3.3. Demolición Empírica del Mito de `INSERT OR IGNORE`
Se auditó si las zonas adicionales en Python provenían de zonas con el mismo milisegundo descartadas por SQLite:
- `Start_ms` duplicados en zonas aceptadas por Python: **0 zonas**.
- Por lo tanto, el `INSERT OR IGNORE` de SQLite **no intervino en la discrepancia de 34 zonas**. La discrepancia es estrictamente atribuible a las asimetrías de captura en los inputs crudos:
  $$\text{Zonas NT8} (4.795) - \text{Faltantes en Parquet} (3) + \text{Exceso por Gap NT8} (37) = 4.829 = \text{Zonas Python}$$

---

## 4. Fase C: Comparador Endurecido V2 y Tests Sintéticos

Se desarrolló e integró el comparador simétrico [`tools/paridad_hftzones_nq_v2.py`](../../tools/paridad_hftzones_nq_v2.py):
1. **Matching Uno-a-Uno**: Detección estricta de reutilización (`duplicate_match_reuse`) y colisiones ambiguas (`ambiguous_collisions`).
2. **Tolerancias Explícitas**:
   - Geometría: 0 ticks de tolerancia (`1e-9`).
   - Contadores y Pasos: 0 de tolerancia (exactos enteros).
   - Volúmenes y CVD: `1e-6`.
   - Duraciones y Velocidades: `1e-4` ms / rate.
3. **Poblaciones Simétricas Evaluadas**: Informa tanto `NT8_WITHOUT_PYTHON` como `PYTHON_WITHOUT_NT8`.
4. **Campos Efectivamente Comparados**: Informa exactamente $4.792 \times 20 = 95.840$ campos para las parejas 1-a-1.

### 4.1. Suite de Tests Sintéticos (`tests/bridge/test_paridad_hftzones_v2.py`)
Se crearon y pasaron al 100% (11/11) los tests sintéticos que certifican:
1. Zonas con mismo `start_ms` y distinta dirección.
2. Colisión ambigua con misma clave.
3. Zona Python adicional.
4. Zona NT8 adicional.
5. Prohibición de reutilizar parejas.
6. Detección de discrepancia geométrica de 1 tick.
7. Tratamiento de diferencias sub-milisegundo.
8. Zonas de duración 0 ms sin colisión.
9. Simulación de descarte por `INSERT OR IGNORE`.
10. Invarianza ante permutación del orden de filas.
11. Caso de igualdad perfecta con código de salida cero.

---

## 5. Fase D: Corrección del Logger / Oráculo V2

Para erradicar la ambigüedad de claves temporales en milisegundos y el ocultamiento de errores mediante `INSERT OR IGNORE`, se implementó el nuevo componente gobernado:

- **Archivo C#:** [`nt8/HFTZonesNQPureV4_V2.cs`](../../nt8/HFTZonesNQPureV4_V2.cs)
- **SHA-256 Literal:** `96bff987aec542d19a24e9d00deccb350ba7da12246f5a254b8efc2b92c4a0dc`
- **Versión:** `4.2.0-V2-Hardened`

### 5.1. Innovaciones del Schema V2
1. **Clave Primaria Monotónica**:
   ```sql
   CONSTRAINT ux_zone_v2 UNIQUE (instrument, contract, session_id, zone_seq)
   ```
   * `session_id`: Fecha de la sesión de trading en formato `yyyyMMdd`.
   * `zone_seq`: Secuencia monotónica entera que reinicia en 0 al cruzar frontera de sesión.
2. **Resolución en Nanosegundos Epoch**:
   * `start_ts_ns`, `end_ts_ns`, `available_ts_ns` (timestamp en nanosegundos en el que la zona se cierra y queda disponible causalmente).
3. **Política de Falla Visible**:
   * Se eliminó completamente `INSERT OR IGNORE`. Cualquier colisión o violación estructural produce una excepción visible e interrumpe la persistencia.
4. **Linaje y Metadata**:
   * Incluye `source_indicator_sha256` y `parameter_manifest_sha256`.

---

## 6. Fase E: Estados Documentales y Gates de Certificación

### 6.1. Estado Oficial de Paridad HFTZones NQ
Debido a que el oráculo histórico V1 presenta 3 zonas originadas en ráfagas omitidas por el parquet y 37 zonas omitidas por un gap de captura en NT8, la certificación definitiva queda bloqueada hasta contar con la re-exportación bajo el schema V2:

$$\mathbf{PARITY\_NQ\_HFTZONES\_STATUS = PROVISIONAL\_NEAR\_EXACT\_BLOCKED\_BY\_ORACLE\_SCHEMA}$$

### 6.2. Matriz de Evaluación de Gates

| Gate | Requisito | Estado | Observación |
|---|---|---|---|
| `SOURCE_IDENTITY` | SHA-256 de `.cs` auditado y gobernado en repo | **PASS** | `841cdbcccbe54ca5...` registrado |
| `PARAMETER_IDENTITY` | Defaults idénticos comprobados | **PASS** | Cero violaciones de gate en 4.795 zonas |
| `INPUT_WINDOW_IDENTITY` | Cobertura de ticks 100% idéntica entre NT8 y Parquet | **FAIL_CLOSED** | Parquet omite ráfagas (3 zonas); NT8 tuvo gap de 39m (37 zonas) |
| `MATCHING_ONE_TO_ONE` | Sin colisiones ambiguas ni reuso | **PASS** | 4.792 parejas estrictas 1-a-1 |
| `NT8_WITHOUT_PYTHON` | Cero zonas huérfanas en oráculo | **FAIL_CLOSED (3)** | Requiere re-exportación alineada V2 |
| `PYTHON_WITHOUT_NT8` | Cero zonas huérfanas en espejo | **FAIL_CLOSED (37)**| Requiere re-exportación alineada V2 |
| `AMBIGUOUS_COLLISIONS` | Cero colisiones en clave | **PASS** | 0 colisiones detectadas |
| `DUPLICATE_MATCH_REUSE`| Cero reutilizaciones | **PASS** | 0 reusos detectados |
| `FIELD_DIFFERENCES` | Cero discrepancias numéricas en parejas | **PASS** | 0 diferencias en 95.840 campos evaluados |
| `GEOMETRY_DIFFERENCES` | Cero ticks de deriva en límites | **PASS** | 0 ticks de deriva en 4.792 parejas |
| `DIRECTION_DIFFERENCES`| Cero desacuerdos en dirección | **PASS** | 0 desacuerdos en 4.792 parejas |
| `ORDER_DIFFERENCES` | Secuencia y orden temporal idénticos | **PASS** | Monotonía preservada |
| `GATE_VIOLATIONS` | Cero violaciones de umbral en oráculo | **PASS** | Parámetros certificados |

---

## 7. Instrucciones para Ejecución Manual V2 en NinjaTrader 8

Para que Nicolas ejecute la exportación V2 limpia cuando lo disponga:

1. Copiar `nt8/HFTZonesNQPureV4_V2.cs` a `Documents\NinjaTrader 8\bin\Custom\Indicators\`.
2. Compilar en NinjaTrader 8 (F5).
3. Abrir gráfica de `NQ JUN26` (Data Series 1: `25 Tick`, Data Series 2: `1 Tick`).
4. Cargar el indicador `HFTZonesNQPureV4_V2`.
5. Configurar propiedades:
   * `EnableDbLogging = true`
   * `SoloLogEnVivo = false`
   * `DbPath = E:\EdgeLab\data\nt8_oracles\hft_zones_nq_v2.sqlite`
6. Recargar datos históricos (Ctrl + R).
7. Al concluir la exportación, notificar la ruta para ejecutar la auditoría V2 automatizada y levantar el estado provisional a `PASS_CERTIFIED`.

---

## 8. Aporte Metodológico al Referente

Esta auditoría demuestra cómo la formalización rigurosa de la capa de zonas base erradica supuestos no comprobados (como atribuir conteos dispares a comportamientos de base de datos en lugar de a discrepancias de captura de mercado). Al certificar que 4.792 zonas emparejadas tienen **deriva numérica cero en 95.840 campos**, se asegura que la geometría que alimentará el posterior campo de densidad proviene de un motor determinista y replicable. No obstante, se mantiene la estricta separación científica: **la paridad técnica de un indicador no constituye por sí misma un edge estadístico ni garantiza retornos futuros**.
