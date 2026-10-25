# ORO_0530_UTC — MEDIDO / NO MEDIDO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cada resultado).

## MEDIDO
| fecha | qué | datos | resultado |
|---|---|---|---|
| 2026-10-25 | Parte A: perfil de actividad por minuto UTC (target-free) | XAU 2023-01 → 2026-09 (967 ses.), GC 2025-08 → 2026-09 (270) | burst a las 05:30 UTC: 1,65 (XAU) y 2,75 (GC) contra 0,6 antes; fijo en UTC (verano y invierno), todos los años |
| 2026-10-25 | Parte B no direccional (`rango_h`, 16 pruebas) | ídem, total y reciente | 16/16 nominadas: rango ×1,8 (5 min) a ×1,6 (30 min) contra una hora antes |
| 2026-10-25 | Parte B direccional (deriva, arranque, previo; 48 pruebas) | ídem | 0/48 nominadas; MDE XAU total 0,21–0,94 USD, GC/reciente 0,6–3,5 USD; fricción GC 0,605 |

## NO MEDIDO
- Ruptura direccionalmente neutra (bracket OCO alrededor del rango previo a las 05:30) con costos de GC y slippage de stop medido
  en el burst. Es la forma operable del canal nominado; requiere pre-registro propio.
- Causa del burst (Shanghai 13:30 Beijing): coincide en hora y en DST, no está probada.
- Efecto direccional chico en GC y en la ventana reciente: sin potencia (MDE ≥ el costo).
