# Inventario de Datos y Contratos Aptos para HP-007 (FASE 1)

**Fecha:** 2026-09-15  
**Rama de Campaña:** `work/hp007-causal-campaign-v1-20260915`  
**HEAD:** `20f2de397db7427893630bc626c4d4966b1122cf`  
**Holdout Oficial:** `2026-07-01 -> 2026-12-31` (Sellado e Intacto)

---

## 1. Declaración de Política de Continuidad y Veredicto Cross-Asset

Conforme a la restricción dura #6 y al estándar `CONTRACT_REGIME_STANDARD_2026-09-01.md`:  
> *«Solo pueden entrar a la campaña formal los activos cuya cadena de contratos haya sido certificada bajo previous_complete_session_volume_leader_monotonic_v1. Si la certificación no está terminada, no inventar continuidad; ejecutar únicamente sobre contratos individuales certificados y marcar el análisis cross-asset continuo como ABSTAIN.»*

**Veredicto Cross-Asset Continuo:** `ABSTAIN` (Certificación de completitud multi-contrato pendiente).  
**Alcance Formal Aprobado:** Contratos individuales pre-holdout certificados de **6E (Euro FX Futures, CME Globex)**: `6E 03-26` y `6E 06-26` (con `6E 12-25` disponible para extensión).

---

## 2. Tabla de Inventario de Contratos Auditados

| Contrato | Ticks Totales | Ticks Pre-Holdout | Rango Temporal (UTC) | Clasificación | SHA-256 Parquet |
|---|---|---|---|---|---|
| **6E 03-26** | 5,064,128 | 5,064,128 | 2025-12-08T03:01:04Z -> 2026-03-16T14:16:00Z | `PRE_HOLDOUT_CLEAN` | `b54120bfd99b97f2...` |
| **6E 06-26** | 5,554,201 | 5,554,201 | 2026-03-09T03:00:03Z -> 2026-06-15T14:13:12Z | `PRE_HOLDOUT_CLEAN` | `124b37507b95a102...` |
| **6E 12-25** | 4,512,656 | 4,512,656 | 2025-09-08T03:03:58Z -> 2025-12-15T15:11:57Z | `PRE_HOLDOUT_CLEAN` | `ea8b9f2119296584...` |
| **6E 09-25** | 2,539,857 | 2,539,857 | 2025-07-25T20:00:00Z -> 2025-09-15T14:13:49Z | `PRE_HOLDOUT_CLEAN` | `6719bf4b9057805d...` |
| **6E 09-26 (PARCIAL PRE-HOLDOUT)** | 2,784,986 | 1,085,216 | 2026-06-08T03:03:12Z -> 2026-08-04T05:05:58Z | `PARTIAL_CONTAINS_HOLDOUT` | `6ffcdf041f8d77a2...` |

---

## 3. Especificaciones Técnicas por Contrato Apto

### 6E 03-26
- **Root:** `6E` | **Tick Size:** `5e-05` | **Tick Value:** `$6.25 USD`
- **Ruta Fuente:** `E:\EdgeLab\data\nt8\6E\6E_03-26_ticks.parquet`
- **SHA-256 Parquet:** `b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76`
- **SHA-256 Fuente Original:** `e9ad8a81f1c9bc0faefc20b6b41bfa52458106d44a2d11804e640f9c1094d783`
- **Ticks Pre-Holdout:** `5,064,128` | **Ticks en Holdout:** `0`
- **Estado de Secuencia:** `MONOTONIC_STABLE`
- **Bid/Ask Disponible:** `True` | **L2 Disponible:** `False`
- **Regime ID:** `STANDALONE_CONTRACT_IS` | **Estado:** `CERTIFIED_INDIVIDUAL_PRE_HOLDOUT`

### 6E 06-26
- **Root:** `6E` | **Tick Size:** `5e-05` | **Tick Value:** `$6.25 USD`
- **Ruta Fuente:** `E:\EdgeLab\data\nt8\6E\6E_06-26_ticks.parquet`
- **SHA-256 Parquet:** `124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1`
- **SHA-256 Fuente Original:** `79fa75771479ea25c24f61c77778337f14d5e6c5c99a55902f57e6401b566f12`
- **Ticks Pre-Holdout:** `5,554,201` | **Ticks en Holdout:** `0`
- **Estado de Secuencia:** `MONOTONIC_STABLE`
- **Bid/Ask Disponible:** `True` | **L2 Disponible:** `False`
- **Regime ID:** `STANDALONE_CONTRACT_IS` | **Estado:** `CERTIFIED_INDIVIDUAL_PRE_HOLDOUT`

### 6E 12-25
- **Root:** `6E` | **Tick Size:** `5e-05` | **Tick Value:** `$6.25 USD`
- **Ruta Fuente:** `E:\EdgeLab\data\nt8\6E\6E_12-25_ticks.parquet`
- **SHA-256 Parquet:** `ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336`
- **SHA-256 Fuente Original:** `49233f19a77d33b22201947d71d347b832cb158e2c61235a6ff2b2ddf837d8ff`
- **Ticks Pre-Holdout:** `4,512,656` | **Ticks en Holdout:** `0`
- **Estado de Secuencia:** `MONOTONIC_STABLE`
- **Bid/Ask Disponible:** `True` | **L2 Disponible:** `False`
- **Regime ID:** `STANDALONE_CONTRACT_IS` | **Estado:** `CERTIFIED_INDIVIDUAL_PRE_HOLDOUT`

### 6E 09-25
- **Root:** `6E` | **Tick Size:** `5e-05` | **Tick Value:** `$6.25 USD`
- **Ruta Fuente:** `E:\EdgeLab\data\nt8\6E\6E_09-25_ticks.parquet`
- **SHA-256 Parquet:** `6719bf4b9057805d09594eb803e01b50ffc2146fae3ad4ebaf52e8935bb8cea0`
- **SHA-256 Fuente Original:** `21782ee740d43f577a4e5f985526e9e6fe3c18f09a0dbea74fea047527d2952b`
- **Ticks Pre-Holdout:** `2,539,857` | **Ticks en Holdout:** `0`
- **Estado de Secuencia:** `MONOTONIC_STABLE`
- **Bid/Ask Disponible:** `True` | **L2 Disponible:** `False`
- **Regime ID:** `STANDALONE_CONTRACT_IS` | **Estado:** `CERTIFIED_INDIVIDUAL_PRE_HOLDOUT`

### 6E 09-26 (PARCIAL PRE-HOLDOUT)
- **Root:** `6E` | **Tick Size:** `5e-05` | **Tick Value:** `$6.25 USD`
- **Ruta Fuente:** `E:\EdgeLab\data\nt8\6E\6E_09-26_ticks.parquet`
- **SHA-256 Parquet:** `6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4`
- **SHA-256 Fuente Original:** `93c4119a3bfcd0523af006a3c10f4f9bd673955716681060ffabe35378698294`
- **Ticks Pre-Holdout:** `1,085,216` | **Ticks en Holdout:** `1,699,770`
- **Estado de Secuencia:** `MONOTONIC_STABLE`
- **Bid/Ask Disponible:** `True` | **L2 Disponible:** `False`
- **Regime ID:** `MIXED_REQUIRES_FIREWALL_SPLIT` | **Estado:** `RESTRICTED_PRE_HOLDOUT_ONLY`
