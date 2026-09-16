# Auditoría de Paridad por Activo: BigTrap2Absorption v1.1.1

- **Campaña:** `HP007-CAMP-002` (Fase Estructural — Checkpoint 1 Parcheado)
- **Fecha de Auditoría:** `2026-09-15`
- **Ancla Contractual:** Commit [`29cad93d6600ee4c07a7d716be35e4881d78f491`](https://github.com/Nicodelcampo/EdgeLab/commit/29cad93d6600ee4c07a7d716be35e4881d78f491) (`PARTIAL_MULTI_ASSET_CERTIFICATION`)
- **Rama Canónica:** `work/hp007-rejection-revisit-campaign-v2-canonical-20260915`
- **Repositorio:** `Nicodelcampo/EdgeLab`

---

## 1. Principio Epistemológico de Separación Causal

Conforme a la especificación técnica de EdgeLab, se mantiene la estricta separación ontológica:

$$\text{Contrato y Sesión Elegibles} \neq \text{Paridad de Indicador Validada} \neq \text{Campo Causal Validado} \neq \text{Hipótesis Estructural Confirmada}$$

Haber certificado la elegibilidad contractual de las raíces `ES`, `MES`, `NQ` e `YM` bajo `CONTRACT_REGIME_V2` **no presupone ni autoriza asumir paridad del indicador `BigTrap2Absorption`** en ninguno de ellos. La paridad de cada activo debe ser probada de manera independiente, contra oráculos reales exportados por el motor oficial de NinjaTrader 8.

---

## 2. Definición Técnica e Identidad Criptográfica del Indicador

### 2.1. Implementación Canónica C# (NinjaTrader 8)
- **Archivo:** [`nt8/BigTrap2Absorption.cs`](../../nt8/BigTrap2Absorption.cs)
- **Versión Declarada:** `v1.1.1`
- **Hash SHA-256:** `18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`
- **Mecanismo:** Absorción sobre flujo y desplazamiento:
  $$\Delta P_x = \text{close} - \text{open} \quad (\text{en ticks})$$
  $$\mathcal{A} = \frac{|\text{flujo}|}{1 + |\Delta P_x|} \quad [\text{ScoreMode} = \text{AbsMagnitude}]$$
  $$\text{Umbral} = \text{percentil rodante causal sobre las últimas } \text{AbsorptionLookback cubetas}$$

### 2.2. Implementación Canónica Python (EdgeLab Bridge)
- **Archivo:** [`edgelab/bridge/indicators/bigtrap2absorption.py`](../../edgelab/bridge/indicators/bigtrap2absorption.py)
- **Hash SHA-256:** `d5913b135b07049913eeee08df95a04a563dff7adc5313e2518089647004c24b`
- **Invariantes Clave:**
  - `floor_div` exacto para ticks negativos (idéntico a la aritmética C#).
  - Cálculo de percentiles causal sin fuga hacia el futuro.
  - Formato pipe con secuencia desde cero.
  - Descarte mandatorio de barra 0.

---

## 3. Matriz de Auditoría de Evidencia Real por Activo

Se realizó una inspección exhaustiva de los directorios `data/nt8_oracles/` y `runs/nt8_bridge/` buscando archivos de oráculos exportados directamente desde NinjaTrader 8:

| Activo | Tipo | Parquet de Ticks Auditado | Oráculo NT8 Real Disponible en Repo | Estado Formal de Paridad |
|---|---|---|---|---|
| **`NQ`** | Estándar | `NQ_06-26_ticks.parquet` | **NO** (Sólo existen oráculos antiguos de `aVolCluster` y `BigTrap2` v2.5.2 de 6E) | `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` |
| **`ES`** | Estándar | `ES_06-26_ticks.parquet` | **NO** | `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` |
| **`MES`** | Micro | `MES_06-26_ticks.parquet` | **NO** (Prohibido inferir desde `ES`) | `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` |
| **`YM`** | Estándar | `YM_06-26_ticks.parquet` | **NO** | `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` |

---

## 4. Política de Almacenamiento de Oráculos Fuera de Git

Para respetar las políticas de no versionar datos masivos, tamaño de repositorios y licencias de market data:
1. **Almacenamiento Desacoplado**:
   - Los archivos de eventos masivos exportados desde NinjaTrader 8 permanecen exclusivamente en **almacenamiento local** o en el **dataset privado de Kaggle**, **fuera del control de versiones de Git**.
2. **Artefactos Versionados en Git**:
   - En el repositorio Git se versionan únicamente los **manifiestos livianos** (`.manifest.json`), hashes criptográficos SHA-256, tamaños en bytes, metadatos de configuración y fixtures mínimos sintéticos necesarios para pruebas automatizadas.
3. **Procedimiento de Certificación**:
   - Al exportarse un oráculo localmente, el script de verificación calculará su hash SHA-256, comprobará concordancia al 100.00% (cero falsos positivos, cero falsos negativos) contra el kernel Python y registrará el certificado criptográfico en `docs/research/`.

---

## 5. Dictamen y Condición de Parada en Checkpoint 1

> [!CAUTION]
> **Veredicto Mandatorio de Parada**:
> `PARITY_STATUS = ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` para todas las raíces habilitadas.
> Conforme a las instrucciones del protocolo:
> *"Si la paridad por activo no queda probada, debe detenerse ahí. No debe compensar la falta de paridad avanzando hacia resultados estructurales."*
> 
> Por lo tanto, en este Checkpoint 1 se completa la integración ejecutable de infraestructura, los tests de regresión y el smoke censo sintético, pero **se detiene la investigación antes de realizar barridos amplios o inferencias sobre outcomes**.
