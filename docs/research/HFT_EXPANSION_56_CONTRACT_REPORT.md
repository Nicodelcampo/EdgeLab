# Informe de Ejecución Final — 56 Contratos Multiactivo 25T HFT

- **Estado Global**: `PASS_MULTI_CONTRACT_25T_HFT_EXPANSION`
- **Contratos Inventariados**: 56
- **Contratos Procesados y Verificados**: 55
- **Contratos Bloqueados Explícitamente**: 1
- **Bundles y Fragmentos en Catálogo**: 147
- **Tiempo Total**: 167.2 s

## Resumen por Instrumento

| Instrumento | Contratos | Completos | Bloqueados | Bundles Generados |
| :--- | :---: | :---: | :---: | :---: |
| **6B** | 5 | 5 | 0 | 5 |
| **6E** | 5 | 5 | 0 | 14 |
| **6J** | 5 | 5 | 0 | 14 |
| **ES** | 5 | 5 | 0 | 16 |
| **GC** | 5 | 5 | 0 | 18 |
| **MBT** | 6 | 6 | 0 | 6 |
| **MES** | 5 | 5 | 0 | 15 |
| **MNQ** | 5 | 5 | 0 | 14 |
| **NQ** | 5 | 4 | 1 | 14 |
| **YM** | 5 | 5 | 0 | 14 |
| **ZB** | 5 | 5 | 0 | 17 |

## Detalle de Bloqueos Explícitos

- **NQ 09-26**: `CUSTODY_RECUT_REQUIRED_PENDING_REVALIDATION` (bloqueado preventivamente sin adivinar ni forzar custodia).

## Verificaciones de Integridad Cumplidas

1. **Holdout Sellado**: Cero filas y cero zonas alcanzaron `1782856800000000000` (2026-06-30T22:00:00Z).
2. **Timestamp Monotónico**: `PASS_NONDECREASING_TIMESTAMPS` verificado en el 100% de los bundles.
3. **Aislamiento Causal de Sesión**: Reset formal e independiente de barras y motor HFT por sesión.
4. **Escritura Atómica**: Escritura en `.tmp` y reemplazo atómico.
5. **Paridad de Artefactos**: 100% de paridad SHA-256 entre payload JS y JSON.
