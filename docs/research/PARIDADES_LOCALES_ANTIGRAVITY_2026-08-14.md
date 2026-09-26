# Informe de Paridades Locales (Antigravity) — 2026-08-14

> [!IMPORTANT]
> **DECLARACIÓN DE ALCANCE Y GOBERNANZA:**
> Las tres mediciones de paridad documentadas en este informe fueron ejecutadas en el entorno local por **Antigravity (asistente de ingeniería)** sobre los datasets canónicos de 90 días.
> **NO constituyen un cierre formal de auditoría externa.** 
> El **auditor externo / sandbox independiente debe correr su propia réplica** sobre estos oráculos para emitir el veredicto oficial y sellar el pase formal.

---

## 1. Resumen de Mediciones Locales (Entorno Local EdgeLab)

Todas las mediciones se corrieron sobre el parquet canónico `6E_09-26_ticks.parquet` de 90 días (1.131.047 ticks, `SHA256: 1311bc5ea91a111d95f17da84d9a6ee6323920686b0b0873c04d8f3dc94a9652`) en la ventana completa `2026-04-01T00:00:00` a `2026-06-30T23:59:59`:

| Indicador | Versión | Oráculo Incorporado (CSV) | Zonas NT8 | Zonas Coincidentes (Exact Match) | Tasa de Paridad Local | Estado de Auditoría |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`AACloseOpenDiffs`** | v1.2 | `data/nt8_oracles/gaps2_v22_6E_0926_90d.csv` | 18.020 | **18.004 / 18.020** | **99.91 %** | 🟡 *Pendiente de réplica auditor* |
| **`VolTicksPOC2`** | v2.1 | `data/nt8_oracles/voltickspoc2_v22_6E_0926_90d.csv` | 152 | **151 / 152** | **98.68 %** | 🟡 *Pendiente de réplica auditor* |
| **`Gaps2`** | v2.0 | `data/nt8_oracles/Gaps2_events_nt8_6E_0926_90d.csv` | 11.442 | **11.435 / 11.442** | **99.94 %** | 🟡 *Pendiente de réplica auditor* |

---

## 2. Detalle de Oráculos Incorporados al Repositorio

### A. `AACloseOpenDiffs` (v1.2)
* **Archivo:** `data/nt8_oracles/gaps2_v22_6E_0926_90d.csv`
* **Tamaño:** 2.17 MB (18.024 líneas)
* **SHA-256:** `16b31bccb47a4fbd57788f7d7f9da5765a9d787b79b1aedeb93196dbce902a94`
* **Resultado del cotejo local:**
  * Coincidentes exactas ($\Delta t = 0\text{ ms}$, precio exacto): **18.004 zonas (99.91%)**
  * Diferencias geométricas: 4 zonas
  * Diferencias de timestamp: 1 zona
  * Missing en NT8: 60 zonas (colas de borde) / Missing en Python: 11 zonas.

### B. `VolTicksPOC2` (v2.1)
* **Archivo:** `data/nt8_oracles/voltickspoc2_v22_6E_0926_90d.csv`
* **Tamaño:** 217 KB (2.178 líneas)
* **SHA-256:** `b24c7107eada15c0121b02e99b2210a7e1bc687760d59817031d246b974b5336`
* **Resultado del cotejo local:**
  * Coincidentes exactas ($\Delta t = 0\text{ ms}$, precio exacto): **151 zonas (98.68%)**
  * Diferencia de features: 1 zona (toques: 2 en Python vs 8 en NT8)
  * Missing: 1 zona de borde en Python / 1 zona en frontera de warmup NT8.

### C. `Gaps2` (v2.0 Canónico)
* **Archivo:** `data/nt8_oracles/Gaps2_events_nt8_6E_0926_90d.csv`
* **Tamaño:** 9.15 MB (56.089 líneas)
* **SHA-256:** `a7654570d20e059c28842069d38273651e8998ca2280cab188e08cfa6b3d3402`
* **Resultado del cotejo local:**
  * Coincidentes exactas: **11.435 zonas (99.94%)**
  * Diferencia de features: 2 zonas
  * Immature tail: 3 zonas
  * Missing de borde: 6 en NT8 / 5 en Python.

---

## 3. Instrucciones de Réplica para el Auditor Externo

El auditor puede reproducir estas tres validaciones de forma target-free ejecutando en el sandbox:

```bash
# 1. AACloseOpenDiffs
python tools/run_nt8_bridge.py \
    --data data/nt8/6E_0926_90d/6E_09-26_ticks.parquet \
    --contract "6E 09-26" --instrument "6E" \
    --start-utc 2026-04-01T00:00:00 --end-utc 2026-06-30T23:59:59 \
    --bars time:1 --indicator AACloseOpenDiffs \
    --oracle "AACloseOpenDiffs=data/nt8_oracles/gaps2_v22_6E_0926_90d.csv" \
    --chart-tz "America/Argentina/Buenos_Aires" \
    --out runs/parity_aacloseopendiffs_90d

# 2. VolTicksPOC2
python tools/run_nt8_bridge.py \
    --data data/nt8/6E_0926_90d/6E_09-26_ticks.parquet \
    --contract "6E 09-26" --instrument "6E" \
    --start-utc 2026-04-01T00:00:00 --end-utc 2026-06-30T23:59:59 \
    --bars time:1 --indicator VolTicksPOC2 \
    --oracle "VolTicksPOC2=data/nt8_oracles/voltickspoc2_v22_6E_0926_90d.csv" \
    --chart-tz "America/Argentina/Buenos_Aires" \
    --out runs/parity_voltickspoc2_90d

# 3. Gaps2
python tools/run_nt8_bridge.py \
    --data data/nt8/6E_0926_90d/6E_09-26_ticks.parquet \
    --contract "6E 09-26" --instrument "6E" \
    --start-utc 2026-04-01T00:00:00 --end-utc 2026-06-30T23:59:59 \
    --bars time:1 --indicator Gaps2 \
    --oracle "Gaps2=data/nt8_oracles/Gaps2_events_nt8_6E_0926_90d.csv" \
    --chart-tz "America/Argentina/Buenos_Aires" \
    --out runs/parity_gaps2_canonical_90d
```
