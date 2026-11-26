# Carteras NT8: multiactivo como diversificador y gestión del riesgo en cuentas fondeadas

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF2 (exploratorio y descriptivo: no promueve reglas; decide composición y tamaño de carteras con reglas ya existentes).  
Familia: `DIVERSIFICACION_MULTIACTIVO` (13 pruebas: las series nuevas por activo de la Parte A). La Parte B (gestión) no suma pruebas
de ventaja: elige políticas de tamaño con criterio declarado y validación fuera de tiempo.  
Antecedentes: `fundedsync_multiactivo_oro_20261122` (matriz 15×6; T y R multiactivo NQ/ES, N débil; Z se invierte fuera de NQ; 0/60
en oro), `rq5_regimen_20261119` (RQ5 YM negativo en DESC, RTY +0,046 R decae 2024–25), `som_transfer_20261117` (F-SOM-TRANSFER-NO),
`franklin_confirmacion_20261118` (YM negativo), EXP-8 (F-CARTERA-INV-VOL-BAJA-DD), `cartera_lucid_20261125` (F-CARTERA-LUCID-150K-1MICRO);
NO_REPETIR F-FRENO-DIARIO-NO, F-REGIMEN-OFFLINE.  
Cambio respecto a falla previa: no se repite la transferencia como búsqueda de ventaja (ya medida); se mide si una serie de otro
activo REDUCE el riesgo de la cartera (correlación, drawdown, probabilidad de cobro), con su ventaja contraída a la mitad o a cero.
El freno diario se evalúa sólo como regla de la cuenta (pérdida diaria de Lucid), no como control de quema.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (K33 costos: M2K con spread ESTIMADO declarado abajo; K40; K51).  
Potencia previa: 2019-07 → 2026-09 ≈ 1.800 sesiones; una correlación diaria con la cartera tiene error ≈ 0,024 (detecta |ρ| ≥ 0,05);
las probabilidades de cobro se estiman con 4.000 trayectorias por configuración (error ≈ 0,008).  
Diagnóstico de mecanismo: se publican para cada serie su R/op, correlación con la cartera base y el cambio en drawdown y probabilidad
de cobro al sumarla; para cada política de tamaño, su ranking en dos mitades de tiempo (estabilidad) y su resultado con media cero.  
Pedido de Nico (2026-11-25): «investigá las técnicas y mejores prácticas… corridas en Kaggle… indagar en el multiactivo y sus pros y
contras como diversificadores y estabilizadores… para los activos sin costos medidos, investigá sus costos en internet y usá esos».

## Justificación económica
Una cuenta fondeada se pierde por el drawdown, no por la media: dos series con la misma ventaja y correlación baja bajan la
volatilidad diaria y suben la probabilidad de llegar al objetivo antes que al piso (juego favorable: conviene «apostar chico»,
Dubins–Savage). Pero una serie de otro activo sin ventaja propia agrega costo y varianza; sólo vale si su correlación es baja y su
media no es negativa.

## Parte A — Multiactivo (13 series nuevas, reglas sin cambios, motor EdgeLabCartera en modo broker)
RQ5, Franklin y ES5N (reglas en ATR o en rangos: sin escala de precio) en YM, RTY y GC; RQ5 ya medido en NQ/ES; Franklin en ES;
ES5N en NQ; T y R con los parámetros ES_Core en ES. Costos: `edgelab/costos.py` en micros (MNQ, MES, MYM, MGC medidos; **M2K con
spread ESTIMADO = spread medido de RTY, 1,5 ticks, y comisión de Lucid 0,50 por lado, leída en support.lucidtrading.com el
2026-11-25**). Por serie: R/op neto en micros, operaciones/mes, correlación diaria con la cartera intradía base (8 de
`cartera_lucid_20261125`), y efecto en drawdown y en probabilidad de cobro de la 150K al sumarla a 1 micro.
Lectura: una serie es **diversificadora** si su correlación con la base es < 0,10 y al sumarla no baja la probabilidad de cobro con
media contraída; **estabilizadora** si además gana en los meses malos de la base. CL, ZN, 6E: sin historia M1 de NT8 (sólo ticks
desde 2025): no se miden acá.

## Parte B — Gestión del tamaño en cuentas Lucid (descriptiva, simulación de reglas oficiales)
Bootstrap por bloques de 10 sesiones del vector diario conjunto (conserva la correlación entre estrategias). Políticas:
asignación (1/N, inverso-volatilidad 12 m, HRP 12 m), contratos base (1–4 micros por estrategia), tamaño dinámico (fijo; según el
colchón al piso, estilo Grossman–Zhou; escalón ×2 cuando el piso se fija; mitad después de perder la mitad del colchón), freno
diario de la cuenta (ninguno, 30 % o 50 % de la pérdida máxima) y tope diario de ganancia en evaluación (ninguno o el de la
consistencia). Cuentas 25K, 50K, 150K y el estado actual de la 25K en rescate (saldo 24.270, piso 24.000 sin verificar).
**Criterio declarado**: por cuenta, mayor probabilidad de cobrar más que el precio con la media contraída a la mitad; entre las que
quedan a ≤ 0,02, mayor valor esperado. **Validación**: la elección se repite en 2019-07 → 2023-12 y se evalúa en 2024-01 → 2026-09; se
publica la correlación de rangos entre mitades. Para el rescate, el objetivo es pasar la evaluación desde el estado actual.

## Cómo podría refutarse
- El multiactivo no sirve como diversificador si ninguna serie cumple correlación < 0,10 sin bajar la probabilidad de cobro.
- La gestión dinámica no sirve si su ventaja sobre el tamaño fijo desaparece fuera de tiempo (correlación de rangos ≤ 0) o con
  media cero se vuelve la mejor (señal de que sólo explota la varianza).
