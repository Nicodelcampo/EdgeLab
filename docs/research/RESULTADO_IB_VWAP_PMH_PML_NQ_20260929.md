# Resultado IB→VWAP y PMH/PML, NQ NT8 Q3 — 2026-09-29

**Estado:** ejecutadas en sandbox; desarrollo, no confirmación ni rentabilidad neta validada.
Autorización de Nico: «Retoma y correas». Dataset privado Kaggle `nicolasbuttaro/edgelab-nq-nt8-2026q3-l2ctx`, versión 1. No se lanzó kernel Kaggle y no se tocó el holdout.

## Veredicto

- **IB→VWAP:** 5 operaciones en 56 sesiones disponibles, media +0.721131 R tras dos ticks, antes de comisión. **INCONCLUSA por muestra**: cinco está muy por debajo del mínimo 30 trades / 20 sesiones. No promover ni relajar el retest para fabricar muestra.
- **PMH/PML:** 36 operaciones/sesiones, media -0.068692 R tras dos ticks; ya era negativa antes de ese coste. **Punto muestral negativo**, no negativo estadísticamente demostrado.
- **Inferencia:** el runner registrado antes del run condiciona el bootstrap conjunto a que ambas primarias tengan ≥30 trades. IB no cumple; no se calculó max-T/IC/p y no hay “0/2 significativas” ni declaración de equivalencia. PM supera el mínimo individual, pero la inferencia de la familia permanece inconclusa. La etiqueta interna `INCONCLUSIVE_SAMPLE` de PM corresponde al gate conjunto, no a que 36<30.

## Métricas

R = resultado en ticks dividido por riesgo inicial entry-stop, sin sizing. 2 ticks = sensibilidad primaria, 0/4 ticks descriptivas.

| Estrategia | Operaciones | R media 0 ticks | R media 2 ticks | R media 4 ticks | Máx. drawdown (R) |
|---|---:|---:|---:|---:|---:|
| IB_VWAP | 5 | +0.735371 | +0.721131 | +0.706892 | 1.0200 |
| PMH_PML | 36 | -0.059787 | -0.068692 | -0.077597 | 5.5205 |

El drawdown es la curva descriptiva de suma de R por operación/sesión, no dinero ni tamaño de cuenta. Comisión de equilibrio muestral: IB USD 785.00 por ida/vuelta y contrato (sólo 5 trades; no extrapolar); PM USD -22.08: no existe comisión no negativa que mejore su media monetaria observada a positiva.

## Cohorte y decisiones reconciliadas

56 sesiones del catálogo, 2026-07-01 → 2026-09-25, contratos fijados por catálogo. Ambas cubren las barras exigidas. Son las sesiones presentes en v1, no todas las fechas Q3: no se completaron días ausentes tras el roll.

- IB_VWAP: {'no_signal': 51, 'trade': 5}
- PMH_PML: {'trade': 36, 'no_signal': 18, 'both_directions_same_bar': 1, 'target_already_reached_at_entry': 1}

Cada estrategia tiene exactamente 56 decisiones; máximo una operación por sesión. `no_signal` no se elimina del registro. En PM, ambas direcciones en una barra y objetivo ya pasado al entrar se contabilizan, no se rescatan con otra entrada.

## Método y procedencia

- Manifiesto inicial: `MANIFIESTO_IB_VWAP_Y_PMH_PML_NQ_20260929.md`.
- Precisiones de implementación previas a outcomes: `EJECUCION_IB_VWAP_PMH_PML_NQ_20260929.md`.
- Código, fixtures y preflight sellados en `01dd9a5c6a83157a667b74638dd303af0ffd4f49`.
- Runner SHA-256: `5308f2c1d0de2b0b1bfaaf2d15bd5a64606938fb40f68bc523caa246a60eedb5`. Los Parquet coinciden con los hashes de sus manifests. Catálogo/archivos/ventana y universo publicados en `artifacts/ib_vwap_pmh_pml_nq_20260929/preflight.json`.
- Baseline de consulta: `3fc19fc9479742faa7520ca00b98d43b4d592db1`; HEAD previo a resultados `01dd9a5…`; script aislado con hash, no se declara worktree limpia.
- Entorno: {'python': '3.13.14', 'numpy': '2.5.3', 'pandas': '3.0.6', 'pyarrow': '20.0.0'}.
- Perfil completo genérico no pudo leer bajo el límite de memoria (el fallback del profiler trató un Parquet como CSV); **no se interpreta como corrupción**. Se sustituyó por lectura Arrow de todos los lotes y perfiles de muestras por row-group. Todos los registros sin nulos ni inversión temporal; precios/volúmenes positivos. Constantes de instrumento/contrato/source_file en la muestra son esperadas por su grano, no columnas a eliminar.
- Timestamps duplicados se preservan por `sequence`, no se deduplican trades. Presencia en barras no certifica completitud absoluta.

## Validación independiente

- Fixtures: DST/zona horaria, frontera de barra y VWAP por ticks, breakout/retest posterior, sweep/dos cierres, ambigüedad de lados, entrada estrictamente posterior, stop/TP en largos y cortos, gap adverso, salida temporal, costes y bootstrap compartido determinista.
- 41 operaciones verificadas mediante **otro loop directamente sobre los ticks originales**, incluyendo primer tick posterior a señal, primera barrera o tiempo, precio de salida y R.
- Reconciliación de decisiones; máximo una entrada; sumas R independientes. Audit script/evidencia publicados.

## MEDIDO / NO MEDIDO

**MEDIDO:** backtest de estas dos implementaciones congeladas, en estas 56 sesiones y fuente NT8, sin etiquetas L2 ni optimización.

**NO MEDIDO:** fills market al bid/ask, latencia real, cola/impacto, comisiones aplicables, inferencia conjunta de la familia, confirmación, otros activos, otras ventanas/reglas y filtros L2.

Entrada por Last del primer tick posterior es **proxy**. Stop usa tick que cruza (gap incluido), objetivo usa precio teórico con ajuste máximo 0,5 tick al punto medio PM, y se descuentan dos ticks totales. Eso no demuestra ejecución real. No sumar dos veces el spread ni presentar comisión de equilibrio como tarifa validada.

## Próximo paso

No hay candidata confirmada. Para IB, ampliar **datos de desarrollo autorizados**, no las reglas tras ver cinco trades. Para PM, no buscar ahora un filtro ganador sobre esta misma muestra. Cualquier sensibilidad nueva o inferencia separada debe registrarse y etiquetarse exploratoria; confirmación necesita autorización aparte.

## Aporte al referente

Las dos ideas dejan de estar sin correr: IB queda inconclusa por muestra y PM tiene media observada negativa, con ejecución proxy y sin gastar el holdout.
