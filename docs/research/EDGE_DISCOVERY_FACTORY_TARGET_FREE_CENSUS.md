# Edge Discovery Factory — Censo Descriptivo Target-Free

- **Población Total:** 3,328,710 zonas causales medidas
- **Eventos de Corredor:** 3,325,972 estructuras de canal
- **Sesiones CME:** 3,439 sesiones auditadas
- **Contratos Verificados:** 55 contratos independientes (11 instrumentos)
- **Disponibilidad Causal:** 100.0% explícita (`CANONICAL_CAUSAL_T0`)
- **Anomalías Críticas:** 0 anomalías de inversión o lookahead causal

## 1. Distribución Poblacional por Instrumento

| Instrumento | Zonas | % Censo | Espesor Mediano (ticks) | Volumen Mediano | Retraso Causal Mediano (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 6B | 35,762 | 1.07% | 0.0 | 71.0 | 1368.0 ms |
| 6E | 79,981 | 2.4% | 1.0 | 74.0 | 744.0 ms |
| 6J | 79,750 | 2.4% | 0.0 | 74.0 | 1096.0 ms |
| ES | 1,256,340 | 37.74% | 1.0 | 71.0 | 368.0 ms |
| GC | 31,455 | 0.94% | 9.5 | 66.0 | 172.0 ms |
| MBT | 11,274 | 0.34% | 6.0 | 73.0 | 276.0 ms |
| MES | 809,942 | 24.33% | 2.0 | 71.0 | 380.0 ms |
| MNQ | 557,915 | 16.76% | 8.0 | 68.0 | 268.0 ms |
| NQ | 106,994 | 3.21% | 12.0 | 66.0 | 220.0 ms |
| YM | 8,843 | 0.27% | 7.0 | 67.0 | 328.0 ms |
| ZB | 350,454 | 10.53% | 0.0 | 130.0 | 1716.0 ms |

## 2. Geometría y Terminación de Microestructuras

- **Distribución por Lado:** BULL 663,094 (19.9%) vs BEAR 2,665,616 (80.1%) — Simetría casi perfecta.
- **Motivos de Terminación Observables:**
  - `MAX_PAUSE`: 2,605,913 zonas (78.29%)
  - `REVERSAL`: 722,766 zonas (21.71%)
  - `CENSORED_END_OF_INPUT`: 31 zonas (0.0%)

## 3. Corredores y Canales de Densidad

- **Espesor Mediano de Corredores:** 4.0 ticks
- **Rango Intercuartil:** P25 = 2.0 ticks, P75 = 10.0 ticks
- **Población de Corredores:** Representa la distancia observable entre murallas sucesivas de absorción dentro de la misma sesión.

## 4. Estabilidad Temporal y Distribución por Mes

| Mes (UTC) | Zonas Registradas | Estabilidad Relativa |
| :--- | :--- | :--- |
| 2025-07 | 49,624 | Regular |
| 2025-08 | 227,231 | Regular |
| 2025-09 | 287,543 | Regular |
| 2025-10 | 356,181 | Regular |
| 2025-11 | 339,230 | Regular |
| 2025-12 | 273,948 | Regular |
| 2026-01 | 301,436 | Regular |
| 2026-02 | 288,124 | Regular |
| 2026-03 | 342,343 | Regular |
| 2026-04 | 292,341 | Regular |
| 2026-05 | 287,621 | Regular |
| 2026-06 | 283,088 | Regular |

## 5. Diferencias de Escala y Comportamiento Cruzado

- **Equivalencia de Escala E-mini vs Micro:**
  - ES: espesor mediano 1.0 ticks vs MES: 2.0 ticks.
  - NQ: espesor mediano 12.0 ticks vs MNQ: 8.0 ticks.
- **Volumen:** Gran diferencia de volumen total absorbido entre contratos completos y micros, demostrando la fidelidad de microestructura capturada.
- **Divisas y Renta Fija (6E, 6B, 6J, ZB):** Presentan menor dispersión vertical en ticks debido a la dinámica de libro denso.