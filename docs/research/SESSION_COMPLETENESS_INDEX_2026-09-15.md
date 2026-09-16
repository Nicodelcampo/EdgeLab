# Índice Compacto de Completitud y Regímenes Contractuales (2026-09-15)

> [!WARNING]
> **ADVERTENCIA DE CONSUMO DE CONTEXTO:**
> Los archivos [`UNIVERSAL_SESSION_COMPLETENESS_2026-09-15.json`](UNIVERSAL_SESSION_COMPLETENESS_2026-09-15.json) y los manifiestos individuales en [`contract_regimes/`](contract_regimes/) contienen más de **150.000 líneas combinadas**.
> **NO CARGAR ESTOS JSON COMPLETOS EN EL CONTEXTO DE AGENTES O LLMS.**
> Para auditoría habitual, verificación de rolls, hashes y estado de certificación, use exclusivamente este índice compacto.

---

## 1. Estado Global de Certificación

- **Estado Formal:** `PARTIAL_MULTI_ASSET_CERTIFICATION`
- **Desglose Práctico de Activos (11 Raíces):**
  - **4 Plenamente Habilitadas:** `ES`, `MES`, `NQ`, `YM` (calendario CME estructurado y parquets sin discontinuidades de cobertura).
  - **1 Condicional:** `MNQ` (requiere exclusión formal por código de sus dos ventanas con gaps pre-holdout: `2026-03-21 → 2026-04-05` y `2026-06-11 → 2026-06-24`; los episodios que toquen estos intervalos deben eliminarse).
  - **6 en Abstención:** `6B`, `6E`, `6J`, `GC`, `ZB`, `MBT` (evaluados estrictamente como `ABSTAIN_CALENDAR_EVIDENCE_REQUIRED` por ausencia de calendario oficial primario incorporado).
- **Fecha de Auditoría:** `2026-09-15`
- **Política Causal:** `previous_complete_session_volume_leader_monotonic_v1`
- **Aislamiento de Holdout:** 100% verificado (`holdout_violation: False`, ningún tick $\ge$ `2026-06-30T22:00:00Z`).

---

## 2. Resumen Ejecutivo por Activo

| Raíz | Clase de Activo | Contratos | Filas Totales | Volumen Total | Sesiones Elegibles / Total | Estado Práctico | Manifiesto SHA-256 |
|---|---|---|---|---|---|---|---|
| **ES** | Equity Index | 5 | 262.806.610 | 347.672.482 | 28 / 322 | **HABILITADO** | `85c483f4ba09be19...` |
| **MES** | Equity Index Micro | 5 | 167.065.860 | 298.212.276 | 27 / 322 | **HABILITADO** | `dbf71ab8ae8edb88...` |
| **NQ** | Equity Index | 5 | 119.153.201 | 129.503.221 | 27 / 322 | **HABILITADO** | `d796c34696b5cd99...` |
| **YM** | Equity Index | 5 | 21.051.454 | 22.737.066 | 18 / 322 | **HABILITADO** | `7ffe42cc9af807c5...` |
| **MNQ** | Equity Index Micro | 5 | 334.506.728 | 381.459.605 | 27 / 322 | **CONDICIONAL (Gaps)** | `375b20504045e5ee...` |
| **6B** | FX (GBP) | 5 | 7.791.752 | 18.093.062 | 0 / 262 | **ABSTENCIÓN** | `d910012bd4aeec69...` |
| **6E** | FX (EUR) | 5 | 18.755.187 | 36.698.275 | 0 / 263 | **ABSTENCIÓN** | `71fe8beead5d4cc0...` |
| **6J** | FX (JPY) | 5 | 14.627.578 | 31.496.193 | 0 / 260 | **ABSTENCIÓN** | `4b33d26e043101d7...` |
| **GC** | Metales (Gold) | 5 | 38.154.926 | 43.210.065 | 0 / 258 | **ABSTENCIÓN** | `95d0cd2b2e2e34bb...` |
| **ZB** | Tasas (30Y Bond) | 5 | 27.204.693 | 92.973.549 | 0 / 250 | **ABSTENCIÓN** | `edcf9b67834de554...` |
| **MBT** | Cripto (Micro BTC)| 6 | 4.581.994 | 8.018.213 | 0 / 239 | **ABSTENCIÓN** | `9317a8bb71856363...` |
| **TOTAL**| **11 Activos** | **56** | **1.015.108.799**| **1.407.249.709** | — | — | — |

---

## 3. Hashes Criptográficos de Manifiestos de Régimen

Ubicación: [`contract_regimes/`](contract_regimes/)

- `ES`: `85c483f4ba09be19aeef9d7d4c22998a4da49e0b82ebfe260c6d70ae4efd9e79`
- `MES`: `dbf71ab8ae8edb885c34cb36a583e87d55883a48e77a296e85579d4df8cb5f44`
- `NQ`: `d796c34696b5cd997097ca19532588147d337a5441a106f369931b67a149b5c3`
- `MNQ`: `375b20504045e5eeea89100063fa79d038202d6fe0e737bf64e650ec6947702f`
- `YM`: `7ffe42cc9af807c5717bc67a78440cf6e2b9a710bc87b99c9cb6d1ba4e3230b8`
- `6B`: `d910012bd4aeec697ffccfc80f970ea45610a2046ff9d9f9cf0df7c677f52554`
- `6E`: `71fe8beead5d4cc0d1f7c8ec1b0f513f5fb4707166e5fb0f75e7a9bfa95f32a5`
- `6J`: `4b33d26e043101d7820129cf6cf2bfa9d012489c6d3701625950d603a115e5a2`
- `GC`: `95d0cd2b2e2e34bb049e496a920235339c09c53644fcfbb8e54e4c2780ca124e`
- `ZB`: `edcf9b67834de554b73b53f6834b6b663b65287f4c54625b1f6ce64295efc94e`
- `MBT`: `9317a8bb71856363bbaf093e430ad8a57ebcbb2b8be5d7b5bf46ae7c73ffbb7f`

---

## 4. Guía Operativa para la Campaña HP-007

1. **Activos de la Campaña Formal:**
   - La campaña estructural de rechazo-alejamiento-revisita (HP-007) debe utilizar exclusivamente: **`ES`, `MES`, `NQ`, `YM`**.
2. **Invalidez de 6E para la Campaña Formal:**
   - Queda invalidada la idea de continuar formalmente sobre los dos contratos de `6E` utilizados en `HP007-CAMP-001`. Dichos resultados quedan estrictamente como evidencia exploratoria histórica previa.
3. **Uso de `MNQ` Condicionado:**
   - Si se incorpora, debe ser como sensibilidad separada, excluyendo por código sus dos ventanas de gaps (`2026-03-21 → 2026-04-05` y `2026-06-11 → 2026-06-24`) y publicando el número de episodios excluidos.
4. **Regla Mandatoria de Censura de Episodios en Rollovers:**
   - **Ningún episodio puede cruzar un cambio de contrato o un `state_reset_flag == True`**.
   - Ante un roll, se reinician completamente: estado de BigTrap2Absorption, zonas activas, touches, campos de liquidez, normalizadores y la máquina de estados del episodio.
   - Cualquier episodio activo en el instante de un roll debe terminar taxativamente como **`CENSORED_CONTRACT_ROLL`** (y no como cruce, rechazo ni `DATA_EDGE`).
   - Taxonomía obligatoria de censura:
     - `CENSORED_SESSION_END`
     - `CENSORED_CONTRACT_ROLL`
     - `CENSORED_DATA_EDGE`
     - `CENSORED_MAX_FOLLOWUP`
5. **No Transferencia Automática de Paridad:**
   - Contrato y sesión elegibles $\neq$ Paridad del indicador validada $\neq$ Campo causal validado $\neq$ Hipótesis estructural confirmada.
   - La paridad debe auditarse independientemente para cada activo antes de interpretar señales.
