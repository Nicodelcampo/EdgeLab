# Pre-registro — U1-ZONAS-ES y U1-ZONAS-NQ: la grilla completa de U1 con zonas de aVolZonePOI2, en los futuros

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Campañas `U1-ZONAS-ES`, `U1-ZONAS-NQ` (familias `U1_ZONAS_ES`, `U1_ZONAS_NQ`) por el embudo automático. Etapa EF2/EF3. Spec:
`SPEC_U1_ZONAS.md`. Pedido de Nico: reutilizar los indicadores con la lógica que mejor funcionó, y probar millones de variantes sin matar
de más.

## 1. Objeto y grilla
`edgelab/research/u1_zonas.py`: U1-INDAGA completa × escala causal mensual {0,5; 1; 2} (= U1-ORO-GRILLA) × indicador {aVolZonePOI2}
= 4.478.976 celdas por canal (total y reciente). Oráculo: con las zonas de LUX-IMB en el almacén reproduce U1-ORO-GRILLA fila por fila
(`tests/research/test_u1_zonas.py`).

## 2. Zonas (almacén target-free, ya medido antes de mirar retornos)
Kernel `nicolasbuttaro/almacen-zonas-avzp2` (`tools/kaggle_grilla/almacen_zonas_main.py`), dataset privado `nicolasbuttaro/edgelab-zonas-u1`.
aVolZonePOI2 sobre barras de 25 ticks del release con los parámetros de la réplica AVZP2. Censo: ES 58.936 zonas en 298 sesiones
(≈ 198 por sesión, alto mediano 1 tick); NQ 29.515 en 289 (≈ 102 por sesión, alto mediano 8 ticks); cobertura mensual pareja desde
ago-2025 (jul-2025 es calentamiento del umbral de 20 sesiones). Una zona está disponible al cierre de la primera vela M1 que cierra
en o después de su creación; vive 500 min (como U1).

## 3. Datos, ejecución y costos
Sensor = ejecución = el futuro (ES, NQ) del release. DESC 2025-08-01 → 2026-03-31; OOS 2026-04-01 → 2026-09-30 (réplica A3 de ES/NQ,
una vez por familia); holdout desde 2026-10-23 a N fijo. Fricción canónica `edgelab/costos.py` (ES 0,8877 pts; NQ 1,5455 pts).

## 4. Filtro
El del embudo actual: FDR q 0,10 sobre evaluables (≥ 30 operaciones), pistas en lote a réplica (un paso de LORD++), meseta que ordena,
OOS que mata sólo con potencia, INTEGRIDAD (placebo y latencia) antes del OOS.

## 5. Justificación económica
U1 cobra el regreso de un precio estirado a un área de actividad concentrada. aVolZonePOI2 marca volumen real concentrado (inventario),
en el futuro mismo, donde U1-B con huecos de LUX-IMB murió porque el libro tapa los huecos M1.

## 6. Cómo podría refutarse
Sin nominadas ni pistas confirmadas; nominadas que no pasan INTEGRIDAD; OOS en contra con potencia. Si U1-ZONAS rinde igual o menos
que U1 con LUX-IMB en el mismo instrumento, la fuente de zonas no agrega.

## 7. Multiplicidad y linaje
El embudo registra las pruebas de DESC antes de lanzar. Linaje ← `U1_ORO_GRILLA`, `AREAS_EXP_1_CRUZADO` (en este commit).
