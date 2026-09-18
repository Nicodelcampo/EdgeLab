# ENTRADA 045 — Certificación de Paridad Completa HFTZones NQ V2 (38 Campos, Terminación Nativa NT8, Cero Deriva)

> **De:** Antigravity (Pair Programming / Engine Runner)  
> **Para:** Nicolas / LLM Auditor / Sandbox Notion / Control de Gobernanza  
> **Fecha:** 2026-09-18 12:05:00 -03:00  
> **Rama:** `fix/hft-native-termination-fresh-replay-20260918`  
> **PR Draft:** #34 (https://github.com/Nicodelcampo/EdgeLab/pull/34)  
> **Veredicto Oficial:** `PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS`  
> **Hash SHA-256 Físico del Oráculo Original:** `a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8`  
> **Tamaño Físico del Oráculo:** `1.036.443.648` bytes (988,43 MB)  
> **Base de Datos Certificada:** `data/nt8_oracles/hft_zones_nq_v2_native_termination_fresh.sqlite`  

---

## 1. Resumen Ejecutivo y Veredicto de Paridad

Se declara y certifica formalmente la **Paridad Completa NT8 ↔ Python (`PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS`)** sobre el conjunto completo de datos canónicos de NQ JUN26 (`NQ 06-26`) entre el 1 de junio y el 12 de junio de 2026:

```
======================================================================
MODO V2: CERTIFICACIÓN EXACTA EN NANOSEGUNDOS (INPUT COMPARTIDO)
======================================================================
Status:                      PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS
Is Pass:                     True
Zonas NT8 V2:                   5,945
Zonas Python Reconstruidas:     5,945
Parejas Exactas (0ns drift):    5,945 (100,00 %)
Diferencias de Campo:               0
Faltantes NT8:                      0
Faltantes Python:                   0
Errores de Procedencia:             0
Campos Evaluados por Zona:         38
Total Campos Auditados:       225.910
======================================================================
```

**Criterios de Cierre y Garantías de Integridad:**
1. **Replay Nativo de NT8:** El replay fue compilado y ejecutado personalmente por Nicolas desde NinjaTrader 8. No hubo simulación, emulación ni falsificación del export de NT8.
2. **Cero Backfill / Cero Corrección en Python:** La columna `termination_reason TEXT NOT NULL` fue emitida de forma 100% nativa por C# en NinjaTrader 8 (`REVERSAL`: 3.636 zonas, `MAX_PAUSE`: 2.309 zonas). Quedó terminantemente prohibido y no se utilizó ningún script de parcheo post-hoc ni `ALTER TABLE`.
3. **Congelamiento Físico Previo a Lectura:** El archivo físico SQLite fue congelado por PowerShell (`tools/post_replay_freeze_oracle.ps1`), se calculó su SHA-256 original (`a0349af9b5eef...`), se generó una copia de preservación con hash idéntico y se activó el flag `IsReadOnly = true` antes de cualquier acceso de Python.
4. **Base Limpia y Nueva:** No se utilizó `INSERT OR REPLACE`, `INSERT OR IGNORE` ni UPSERT. La base nació en un archivo inexistente y validó que estuviera vacía.
5. **Firewall de Holdout Inviolable:** 0 ticks y 0 zonas con `timestamp_ns >= 1782864000000000000` (2026-07-01). El holdout permanece completamente ciego y virgen.
6. **Cero Tolerancia Sub-Milisegundo:** Deriva de límites, marcas temporales `start_ts_ns`, `end_ts_ns` y `available_ts_ns`: **exactamente 0 nanosegundos**.

---

## 2. Cronología Forense del Protocolo de Ejecución

### 2.1. Resolución del Conflicto de Assemblies en NT8
Al iniciar la jornada, NinjaTrader 8 arrojó un error modal bloqueante:
`Unable to recover NinjaTrader custom assembly... NinjaTrader.Vendor.dll is being used by another process.`
- **Causa Raíz:** Existían dos procesos `NinjaTrader.exe` simultáneos en memoria (PID 26760 iniciado a las 09:52 AM y PID 26040 a las 11:06 AM). El proceso antiguo retenía el lock exclusivo de `NinjaTrader.Vendor.dll`.
- **Acción:** Se cerraron los procesos concurrentes desde el Administrador de Tareas, liberando el handle.

### 2.2. Corrección del Conflicto de Compilación por Backup `.cs`
Al compilar en el NinjaScript Editor, el compilador Roslyn arrojó `CS0101: The namespace already contains a definition for 'HFTZonesNQPureV4_V2'`.
- **Causa Raíz:** Existía un archivo `HFTZonesNQPureV4_V2_backup_20260918.cs` en la carpeta `Indicators`. Al compartir la extensión `.cs`, NT8 compilaba ambos archivos provocando colisión de tipos.
- **Acción:** Se renombró a `HFTZonesNQPureV4_V2_backup_20260918.cs.bak`.

### 2.3. Detección y Purga del Replay con DLL No Compilada
En el primer intento de replay, la DLL en disco databa del 16 de septiembre (`NinjaTrader.Custom.dll` de 16/09 11:26 AM), por lo que aún no contenía el esquema con `termination_reason`.
- **Acción de Detección:** El preflight de Antigravity detectó de inmediato que `PRAGMA table_info` carecía de `termination_reason`.
- **Acción de Saneamiento:** Se purgó el archivo provisorio, se liberaron >3 GB de exports y backups obsoletos, Nicolas compiló con `F5` en NT8 (actualizando `NinjaTrader.Custom.dll` a las 11:34:54 AM del 18/09), y se lanzó el replay limpio.

### 2.4. Ejecución del Replay Canónico por Nicolas
- **Instrumento:** `NQ JUN26` (`NQ 06-26`).
- **Data Series:** Series 0 (`25 Tick`), Series 1 (`1 Tick`, `TickResolution = 1`).
- **Ventana:** `01/06/2026` a `12/06/2026` (10 sesiones de trading CME Globex: `20260601` a `20260612`).
- **Modo Exportación Puro:** Activo (`ModoExportacionPuro = true`). Replay ejecutado a máxima velocidad sin colapso de UI en 9 minutos.
- **Total Ticks Procesados y Guardados:** **6.493.515 ticks**.
- **Total Zonas Detectadas:** **5.945 zonas**.

---

## 3. Preservación Física y Procedencia Criptográfica

Apenas Nicolas cerró NinjaTrader 8 (liberando SQLite WAL), se ejecutó `tools/post_replay_freeze_oracle.ps1`:

```powershell
=================================================================
EdgeLab -- Captura y Congelamiento Fisico del Oracle HFT V2 NT8
=================================================================
[1/6] Comprobando existencia del archivo exportado...
[2/6] Verificando que el archivo no este bloqueado...
[3/6] Registrando tamano fisico en bytes...
       Tamano: 1036443648 bytes (988.43 MB)
[4/6] Calculando SHA-256 fisico del SQLite original...
       SHA-256: a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8
[5/6] Creando copia de preservacion...
       Preservado en: E:\EdgeLab\data\nt8_oracles\preservation\hft_zones_nq_v2_native_termination_fresh_preserved_20260918_145003.sqlite
       Hash copia:    a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8 (MATCH EXACTO)
[6/6] Marcando original como solo lectura y emitiendo manifiesto fisico...
       Atributo Read-Only activado en el archivo original.
=================================================================
CAPTURA COMPLETADA CON EXITO
```

- **Manifiesto Preflight Físico:** `data/nt8_oracles/hft_zones_nq_v2_native_termination_fresh.preflight_manifest.json`
- **Manifiesto Canónico de Procedencia:** `docs/research/HFT_V2_NATIVE_TERMINATION_PROVENANCE_MANIFEST.json`

---

## 4. Resultados de Validación y Auditoría

### 4.1. Preflight Estructural (`validate_hft_v2_certification.py`)
```json
{
  "status": "PASS_HARDENED_PREFLIGHT_NOT_FULL_PARITY",
  "is_pass": true,
  "instrument": "NQ JUN26",
  "tick_count": 6493515,
  "zone_count": 5945,
  "contracts": ["NQ 06-26"],
  "errors": [],
  "certification_scope": "PREFLIGHT_ONLY_REQUIRES_FULL_FIELD_PARITY_RECONSTRUCTION"
}
```
- Restricción `termination_reason TEXT NOT NULL` verificada.
- Restricciones causales (`available_ts_ns >= end_ts_ns`, `end_ts_ns >= start_ts_ns`): **0 violaciones**.
- Monotonicidad de `tick_seq` y `zone_seq`: **0 saltos**.

### 4.2. Corrección Algorítmica de Estado en Python (`hftzones_nq.py`)
Durante la comparación exhaustiva campo por campo, se identificó que en `HFTZonesNQPureV4_V2.cs`, `ResetState()` (llamado al final de `Finalizar()`) resetea `lastSide = 0`. Esto garantiza que si el primer tick tras el cierre de una racha no mueve el precio, `side` arranca en `+1` de manera determinista.  
Se aplicó exactamente la misma regla en `edgelab/bridge/indicators/hftzones_nq.py` (`finalizar()` resetea `nonlocal last_side; last_side = 0`), logrando una sincronización matemática al 100,00% en todas las métricas de flujo (`cvd_sweep`, `buy_vol`, `sell_vol`, `delta_slope`, `delta_first`, `delta_second`).

### 4.3. Arnés de Certificación Final (`paridad_hftzones_nq_v2.py`)
- **Total zonas NT8:** 5.945
- **Total zonas Python:** 5.945
- **Coincidencia exacta:** 5.945 / 5.945 (**100,00%**)
- **Diferencias de campo:** **0 / 225.910 campos evaluados**
- **Deriva temporal:** **0 nanosegundos** en todos los timestamps de inicio, fin y disponibilidad.
- **Artefacto Certificado Emitido:** `artifacts/paridad_hftzones_nq_v2_exact_certified.json`

---

## 5. Tabla Completa de los 38 Campos Certificados

| N° | Campo en SQLite | Tipo | Tolerancia | Resultado | Descripción |
|---|---|---|---|---|---|
| 1 | `instrument` | TEXT | Exacto | **PASS** | Nombre del instrumento ("NQ JUN26") |
| 2 | `contract` | TEXT | Exacto | **PASS** | Contrato CME ("NQ 06-26") |
| 3 | `session_id` | TEXT | Exacto | **PASS** | Trade date CME Globex 17:00 Chicago |
| 4 | `zone_seq` | INTEGER | Exacto | **PASS** | Secuencia monótona continua (1..N) |
| 5 | `start_tick_seq` | INTEGER | Exacto (0 ticks) | **PASS** | Tick de inicio de la racha |
| 6 | `end_tick_seq` | INTEGER | Exacto (0 ticks) | **PASS** | Tick de cierre de la racha |
| 7 | `start_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp Unix en nanosegundos |
| 8 | `end_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp Unix de fin de racha |
| 9 | `available_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp causal de disponibilidad |
| 10 | `direction` | INTEGER | Exacto | **PASS** | Dirección de sweep (+1 Bull, -1 Bear) |
| 11 | `lo_ticks` | INTEGER | Exacto | **PASS** | Límite inferior en ticks |
| 12 | `hi_ticks` | INTEGER | Exacto | **PASS** | Límite superior en ticks |
| 13 | `pasos` | INTEGER | Exacto | **PASS** | Conteo total de pasos de sweep |
| 14 | `vol` | REAL | $<10^{-6}$ | **PASS** | Volumen total acumulado |
| 15 | `avg_ms` | REAL | $<10^{-4}$ ms | **PASS** | Tiempo promedio entre ticks |
| 16 | `total_ms` | REAL | $<10^{-4}$ ms | **PASS** | Duración total en milisegundos |
| 17 | `volume_rate` | REAL | $<10^{-4}$ cont/s | **PASS** | Tasa de volumen por segundo |
| 18 | `parameter_manifest_sha256` | TEXT | Exacto | **PASS** | Hash de parámetros congelados |
| 19 | `indicator_source_sha256` | TEXT | Exacto | **PASS** | Hash del código fuente C# |
| 20 | `valid_steps` | INTEGER | Exacto | **PASS** | Pasos válidos en dirección |
| 21 | `max_retro` | REAL | $<10^{-6}$ ticks | **PASS** | Retroceso máximo durante el sweep |
| 22 | `cvd_sweep` | REAL | $<10^{-6}$ | **PASS** | Delta de volumen acumulado (CVD) |
| 23 | `buy_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen comprador |
| 24 | `sell_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen vendedor |
| 25 | `delta_slope` | REAL | $<10^{-4}$ | **PASS** | Pendiente de aceleración del delta |
| 26 | `delta_first` | REAL | $<10^{-6}$ | **PASS** | Delta en la primera mitad del sweep |
| 27 | `delta_second` | REAL | $<10^{-6}$ | **PASS** | Delta en la segunda mitad del sweep |
| 28 | `max_tick_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen máximo en un solo tick |
| 29 | `no_move_ticks` | INTEGER | Exacto | **PASS** | Ticks consumidos sin movimiento |
| 30 | `no_move_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen absorbido sin movimiento |
| 31 | `max_level_ticks` | INTEGER | Exacto | **PASS** | Nivel con mayor concentración de ticks |
| 32 | `bucket` | TEXT | Exacto | **PASS** | Clasificación de velocidad (PRED, ULTRA, etc.) |
| 33 | `price_upper` | REAL | $<10^{-6}$ USD | **PASS** | Precio superior en dólares |
| 34 | `price_lower` | REAL | $<10^{-6}$ USD | **PASS** | Precio inferior en dólares |
| 35 | `price_mid` | REAL | $<10^{-6}$ USD | **PASS** | Precio medio del sweep |
| 36 | `height_ticks` | REAL | $<10^{-6}$ | **PASS** | Altura total del sweep en ticks |
| 37 | `tick_res` | INTEGER | Exacto (=1) | **PASS** | Resolución de subserie (1-tick) |
| 38 | `termination_reason` | TEXT | Exacto | **PASS** | Causa de corte nativa (REVERSAL / MAX_PAUSE) |

---

## 6. Aporte al Referente

La certificación de paridad HFT V2 sobre 5.945 zonas y 6,49 millones de ticks con **cero discrepancias en 225.910 campos** establece por primera vez en EdgeLab un puente determinista e incorruptible entre NinjaTrader 8 y Python:
1. **La causalidad temporal es estricta:** ninguna zona puede ser consumida por corredores o estrategias antes de su `available_ts_ns` nativo.
2. **La procedencia es total:** el oráculo físico cuenta con hash SHA-256 inmutable, copia de preservación y atributo Read-Only.
3. **El holdout no fue comprometido:** el protocolo cerró al 100% sin tocar un solo tick del período posterior al 1 de julio de 2026.
4. **Separación científica:** La paridad exacta es una garantía de instrumentación e infraestructura, **no un edge económico**. Habiendo cerrado definitivamente la infraestructura, la investigación puede proceder con total confianza en los datos hacia la evaluación de hipótesis económicas reales.
