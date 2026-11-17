# «Hacia atrás» para las reglas de la v4 con señal en CFD: evaluación previa (2026-11-17)

Estado: VIGENTE — decisión de NO correr (guarda K27). Pedido de Nico: «arrancá con las 3 reglas» (ORO-ALM-CFD#4, ORO-ALM-CFD#18,
IF-LUX-CFD-NQ-R2#0). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. No se midió P&L nuevo.

## Ventanas libres por linaje (regla del proyecto: una mirada consume la ventana para la familia y las que derivan de ella)
| Regla | Datos de la señal | Ya usado por su linaje | Libre |
|---|---|---|---|
| IF-LUX-CFD-NQ-R2#0 | USATECH Dukascopy desde 2023-01-01 | AREAS_EXP_1_CRUZADO (U1-CRUZADO): OOS 2023-01 → 2025-07 (`areas_expansion_20261022/u1/PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md`) | **nada** |
| ORO-ALM-CFD#4, #18 | XAUUSD Dukascopy desde 2022-07-01 | U1_ORO_GRILLA: «atrás» 2023-01 → 2025-07 (`u1_oro_20261025/PREREGISTRO_U1_ORO_ATRAS.md`) | 2022-07-01 → 2022-12-30 |

## Potencia (K27, `tools/potencia_previa.py`)
Potencia previa: atras_oro2.csv (las dos reglas de oro, desarrollo): 8.0 ops/mes, R/op +0.453, sd 1.09 → en 6 meses ≈ 50 operaciones;
lectura de N 50 con la mitad del efecto: **potencia 0.43 (NO se abre)**. Una prueba así casi siempre termina NO_CONCLUYENTE: no se gasta.

## Qué sí destrabaría el «atrás»
Futuros anteriores a 2025-08 (ticks o M1 de NQ/ES/YM/GC 2022 → jul-2025, p. ej. exportados de NinjaTrader): ninguna de las 10 reglas
de la v4 tiene esos años usados en futuros, y las 7 que dependen de volumen/footprint sólo se pueden medir en futuros.
