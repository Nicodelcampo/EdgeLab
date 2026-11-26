# Enmienda al veredicto maestro del 2026-11-24: estados corregidos

Estado: VIGENTE (enmienda; el veredicto original no se edita)  
Fecha: 2026-11-25  
Decisión de Nico (2026-11-25): las estrategias etiquetadas VALIDADA/CONFIRMADA sin respaldo en el registro de EdgeLab pasan a
**BAJO_REVISION**; se prueban igual en NT8 si su frecuencia es aceptable. Turtles oro queda **fuera** de las pruebas. No se
cambia la configuración de ninguna cuenta hasta probar todas las estrategias y que Nico vea sus curvas.
Detalle y fuentes: `docs/research/inventario_estrategias_20261125/INVENTARIO_ESTRATEGIAS_NT8_20261125.md`.

| Estrategia | Etiqueta del 24-nov | Estado corregido | Motivo (registro) |
|---|---|---|---|
| `C2_VZ` | CONFIRMADA | BAJO_REVISION | `F-CARRIL2-LOTE2-VOL`: 0/12 en BH; la réplica se abrió fuera de protocolo (sin nominadas). |
| `C2_EVRP` | CONFIRMADA | BAJO_REVISION | Mismo lote (p 0,13 en DESC). |
| `ES5N_ES_CFD` | VALIDADA | BAJO_REVISION | Control negativo de ES5 en `F-EXTERNAS-ESTRUCTURALES-REFUTADA`; promovido después de mirar. |
| `RQ5_ES` | VALIDADA | BAJO_REVISION | `F-RQ5-HOLDOUT-NO-CONCLUYENTE`: ES +0,007 R/op en el holdout. |
| `SOM_ES_CFD` | VALIDADA | BAJO_REVISION | `F-SOM-QUANTLAB-NQ`: la evidencia es de NQ; ES sólo 2020+ débil. |
| `ESCoreUS500` | VALIDADA | BAJO_REVISION | Sin campaña de los módulos FundedSync en ES en el registro. |
| `Core5_R25` (módulos en NQ) | VALIDADA | BAJO_REVISION (pistas vivas T, R, Z-banda, V) | Pistas vivas en NQ, ninguna confirmada. |
| `Turtles_GC_CFD` | VALIDADA | **FUERA de las pruebas** | `F-TURTLES-ORO-MESETA-C`: no replica 2004-2010; 5,3 ops/año. |

Las carteras y el Monte Carlo del §4 del veredicto se calcularon con estas etiquetas: quedan **sin efecto** hasta que las
pruebas individuales terminen. Edges promovidos: 0.
