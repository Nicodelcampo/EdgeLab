# Avances y relanzamientos — 2026-11-03

Estado: INFORME — fotografía del trabajo, no habilita corridas. Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Rama de revisión del PR #189, base inspeccionada `82e02f267fa5a3050a22db5bd30b832f6b917dfa`. La rama Gemini auditada tiene HEAD `c73bbb60` y no está integrada a este PR.

## Hecho

- Decisión humana aprobada: cola t unilateral con n−1 grados de libertad en el tamiz; ver `docs/DECISIONES_20261103_COLA_T_FDR.md`. Implementación y tests numéricos preparados localmente, **no integrados**: falla una aserción estadística histórica. En el mismo entorno, 22 tests del lote pasan y uno falla; esa prueba pasa en HEAD original. El test de diferencia BH/maxT exigía >2, pero da 198/1000 vs 110/1000 con cola t. No se redujo el umbral post hoc. Revisar su objetivo y reemplazo válido antes de integrar. La suite completa previa quedó interrumpida y no hay resultado global; el CI de Python 3.12 de HEAD anterior pasó, no certifica el cambio local.
- `preflight edgelab.research.u1_confirma`: ejecutado sobre sintéticos y el cambio local, límite de tiempo 240 s y memoria virtual ~3,3 GB; terminó por timeout sin resultado. **No establece que pase ni que falle.** No se lanzó la campaña.
- Revisión de los 12 módulos Gemini: `REVISION_GEMINI_12_FAMILIAS_20261103.md`. Pruebas conjuntas elegidas: 10 pasan. Se identificaron correcciones requeridas, pero no se aplicaron ni se integraron.
- Mapa de linajes de TP en zonas y diseño causal de las dos vías: `MAPA_OBJETIVOS_ZONAS_INTENTO_FALLIDO_20261103.md`. Sin nuevos outcomes ni selección sobre holdout.

## Qué relanzar y qué no

| Ítem | Acción y condición |
|---|---|
| U1-6E-CONFIRMA-GBP-C-R | Candidato al relanzamiento que Nico pidió tras aprobar la cola t. Primero resolver prueba, integrar y ejecutar el preflight completo con recursos suficientes. La configuración declara `nicobuttaro`, mientras la conexión Kaggle observada autentica `nicolasbuttaro`; verificar acceso a cada dataset y autorizar/cambiar cuenta con trazabilidad. El sensor/ejecución DESC es EURUSD spot con costo proxy 6E, no ejecución real en 6E. |
| Nominaciones históricas DESC | Recalcular exactamente todo el ajuste conjunto, incluidos m y pi0 de Storey, desde S/Q/C o p completos y código versionado. La aproximación por p antiguo no demuestra los nuevos q ni que la corrección sólo quite nominaciones. No sobrescribir resultados originales. |
| Familias ya refutadas o que fallaron integridad/topes | No repetir por inercia ni reinterpretar como ganadoras. Revisar sólo si el recálculo conjunto o un defecto material da razón precisa, y bajo linaje y ventanas aplicables. |
| 33 PISTAS_VIVAS | No relanzar indiscriminadamente: PISTAS_VIVAS no equivale a confirmada. La selección de mejores pistas puede tener maldición del ganador; considerar canasta/forward según actas, no elegir en holdout. |
| VWAP-REV | Si se vuelve a estudiar, una hija con mecanismo y disparo previamente especificados, estudio de potencia y multiplicidad heredada; no reciclar la misma réplica como independiente. |
| 12 familias Gemini | Mantener apagadas. Resolver noticias durante operación, calendarios de Londres/Tokio, costo USDJPY, datos y solapamientos; luego E0 y preregistro revisado antes de outcomes. |
| Canasta v5 | Mantener regla firmada y medir hacia adelante; primera revisión a 20 sesiones válidas nuevas. Falta exportación de noviembre de NT8 según último corte. El Debian figuraba pausado en el último control de la sesión previa; verificar estado actual antes de asumir que el seguimiento corre. |

## Kaggle y estado de validación

La conexión observada en la sesión previa autenticó como `nicolasbuttaro`, con cuota disponible; el acceso privado a `nicobuttaro` fue denegado. No cambia la titularidad de sus kernels ni acredita acceso a todos los datasets. No se ejecutaron nuevas corridas Kaggle ni se abrió holdout para este trabajo.
