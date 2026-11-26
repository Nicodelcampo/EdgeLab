# Inventario de estrategias candidatas: estado real, activos, riesgo y código NT8

Estado: VIGENTE (revisión del 2026-11-25; no mide nada nuevo)  
Fecha: 2026-11-25  
Pedido de Nico: repasar todas las estrategias (activos, riesgos, configuración por activo), determinar si son correctas y
probarlas una por una en NT8 (paridad, veto de noticias, sizing por época y volatilidad, frecuencia).  
Fuentes: `docs/research/FACTORES.jsonl` (registro), `docs/research/*/RESULTADO*.md`, `nt8/strategies/*.cs`,
`docs/research/validacion_maestra_20261124/VEREDICTO_MAESTRO_CARTERAS_20261124.md` (Antigravity).

## 1. Hallazgo principal: las etiquetas «VALIDADA» del 2026-11-24 no coinciden con el registro de EdgeLab

El veredicto maestro de Antigravity marca como VALIDADAS estrategias que el embudo de EdgeLab dejó en otro estado. La
validación maestra **no está en el contador global de pruebas** (`TRIAL_REGISTRY_GLOBAL.jsonl` no tiene ninguna campaña
`validacion_maestra`), usa tablas de fricción propias (`validate_local_tier2_rep.py`) y, en CARRIL2, abrió la réplica de
reglas que el pre-registro no había nominado.

| Estrategia | Antigravity (24-nov) | Registro EdgeLab (fuente) | Lectura |
|---|---|---|---|
| `C2_VZ` (compresión VIX, ES+NQ) | CONFIRMADA, satélite estrella | `F-CARRIL2-LOTE2-VOL`: 0/12 en BH, SIN_EVIDENCIA; **REP no se leyó (sin nominadas)** | La réplica que cita Antigravity se abrió fuera de protocolo, después de mirar el DESC. No es evidencia admisible. |
| `C2_EVRP` (ES+NQ) | CONFIRMADA | Mismo lote: +0,066 R, p 0,13 | Ídem. |
| `ES5N_ES_CFD` (10:00 NY) | VALIDADA | `F-EXTERNAS-ESTRUCTURALES-REFUTADA` (NO_REPETIR): 0/16 en BH. ES5N era el **control negativo** de ES5 en esa campaña (`externas_estructurales_a5_20261118/CAMPANA.json`) | Promover el control porque le fue bien es selección después de mirar; no es una hipótesis pre-registrada. |
| `Turtles_GC_CFD` (oro, viernes) | VALIDADA, satélite oro | `F-TURTLES-ORO-MESETA-C`: +0,22 R/op 2011-26, **réplica 2004-10 no replica** (+0,03, p 0,36); 5,3 ops/año; «sola, no» | Pista viva, no validada; 196 meses para decidir por forward. |
| `RQ5_ES` | VALIDADA, «único satélite intradía» | `F-RQ5-HOLDOUT-NO-CONCLUYENTE`: holdout NO_CONCLUYENTE; **ES +0,007 R/op** (NQ +0,077, YM +0,047) | En ES es justamente el activo más débil del holdout. |
| `SOM_ES_CFD` | VALIDADA | `F-SOM-QUANTLAB-NQ`: pasa en **NQ**; «ES sólo desde 2020 (+0,04/+0,02), YM negativo»; holdout NQ +0,16 R/op (n 29) | Pista viva en NQ; en ES no hay validación. |
| `ESCoreUS500` (módulos FundedSync en ES) | VALIDADA, core CFD | No hay campaña de los módulos en ES en el registro | Sin evidencia propia en ES. |
| T, R, Z (FundedSync, NQ) | Dentro de Core5 | `F-FUNDEDSYNC-T-KNN` y `F-CANASTA-TZR` PISTA_VIVA (NQ; T sin señal antes de 2020) | Las pistas más sólidas del registro, en NQ. |
| V (FundedSync) | — | `F-FS-IL-REMEDICION-V-CANDIDATA`: t 2,87 2022-26 tras corregir la traducción | Candidata nueva (NQ). |
| W, A1/SOMEOD como FundedSync original | En Portfolio | `F-FUNDEDSYNC-SIN-VENTAJA` (NO_REPETIR): ≈ 0 o negativo neto 2012-26, 60-110 ops/mes | No usar tal cual. |
| FRANKLIN | Observación | Pista viva; ES falló REP | Forward. |

**Edges promovidos: 0** (sin cambios). Ninguna de estas estrategias está confirmada; las más sólidas son pistas vivas en
**NQ** (T, R, Z-banda, RQ5, SOM, V). Probarlas en NT8 sigue teniendo valor —verifica ejecución, sizing, veto y paridad—,
pero no convierte una pista en edge.

## 2. Qué hay en NT8 (`nt8/strategies/`)

| Archivo | Qué es | Activo para el que está escrito | Estado |
|---|---|---|---|
| `EdgeLabFundedSyncCore.cs` | Motor común: 7 módulos (R, Z, T, V, W, N, SOMEOD), coordinador, sizing, guardas prop, **veto de noticias** | NQ/MNQ (presets) y ES/MES (`ES_Core_US500`) | Base de las demás. |
| `EdgeLabFundedSyncPortfolio.cs` | Cartera de módulos por preset y perfil de firma; veto de noticias con propiedades | NQ/MNQ; ES/MES con `ES_Core_US500` | Usar para pruebas de cartera, no de estrategias sueltas. |
| `EdgeLabFundedSyncSingleModule.cs` | Un módulo solo, parámetros expuestos | **NQ/MNQ** (valor de punto fijo 2) | Base natural para «una estrategia a la vez». |
| `EdgeLabFundedSyncCore5AltaConv.cs`, `Core6.cs`, `SnipersRZ.cs` | Combinaciones fijas de módulos | NQ/MNQ | Redundantes con Portfolio. |
| `EdgeLabRQ5.cs` | RQ5 (banda de ruido intradía) | NQ (defaults); sin perfiles por activo | Paper/forward. |
| `EdgeLabCanasta.cs` | RQ5 en NQ + índices, guarda de cuenta | NQ | Paper/forward. |
| `EdgeLabAtrPhaseStop.cs` | R con stop de catástrofe 0,25×ATR20 | NQ | Paper. |
| `EdgeLabCvgapESC.cs` | CVGAP-ES-C | ES | **Refutada** (`F-CVGAP…`, −0,044 R/op en 18 años): retirar. |
| `RangoPreapertura.cs` | Rango 09:16-09:30 | ES/NQ | **PREAPERTURA refutada / artefacto**: retirar. |
| `EdgeGold0415.cs` | Corto 04:17 CT en oro | GC | Exploratorio sin pre-registro: no operar. |
| `EdgeLabExecutionProbe.cs`, `EdgeLabSignalReplay.cs`, `EdgeLabSpiralBasketExecutor.cs` | Infraestructura (auditoría de ejecución, réplica de señales, ejecutor de canastas) | — | Herramientas. |

**No existen en NT8:** C2_VZ, C2_EVRP, Turtles oro (MGC/GC), SOM en ES, ES5N.

## 3. Riesgo y sizing en el código NT8 (verificado leyendo el código)

- **Cómo se calcula el tamaño:** `contratos = round(R$ × peso / (stop_en_puntos × valor_del_punto))`, con 1 contrato si
  el stop cuesta ≤ R$×peso/0,55 (`EdgeLabFundedSyncCore.cs`, `OpenSleeveNow`). Como los stops están en ATR, **el tamaño ya
  se adapta a precio, época y volatilidad**: el riesgo en dólares por operación queda fijo y cambia la cantidad de
  contratos. Lo que falta verificar es el redondeo cuando la cantidad es chica (1-3 micros), donde el riesgo real se aleja
  del objetivo.
- **Defecto 1 — `SingleModule` asume MNQ:** `MicroPointValue = 2.0` fijo. En MES (5 USD/punto) el riesgo real sería
  2,5 veces el configurado; en MGC (10 USD/punto), 5 veces.
- **Defecto 2 — conversión a minis:** con gráfico de NQ/ES entero se redondea `micros/10` hacia arriba desde 0,5:
  5 micros → 1 mini, el doble del riesgo buscado; 4 micros → 0.
- **Defecto 3 — sin tope neto:** `MaxMicros` es por módulo; con varios módulos abiertos en el mismo sentido la posición
  suma (ya detectado en `LucidFlex_25K_Rescate`: hasta 6 micros).

## 4. Diseño propuesto para probarlas una por una en NT8

Una estrategia NT8 por regla, con una propiedad **«Activo»** (lista: los activos en los que esa regla tiene evidencia en el
registro). Elegir el activo carga su configuración (parámetros de la regla, valor del punto, tick, sesión, horarios) y la
estrategia **verifica que el gráfico sea ese instrumento**; si no coincide, no opera. Combinaciones sin evidencia no
aparecen en la lista (o aparecen marcadas EXPLORATORIO y no operan en cuenta real).

Cada corrida del Strategy Analyzer escribe un CSV de operaciones (entrada/salida/lado/contratos/riesgo en USD/motivo de
salida, incluido `NEWS_VETO`) que se compara contra el motor Python con `edgelab/veto_noticias.py`:
1. **Paridad**: mismas operaciones, mismos minutos (descontando el calentamiento inicial, que en NT8 no reproduce la historia).
2. **Veto**: cuántas operaciones anula o cierra la noticia, y que coincidan con Python.
3. **Sizing**: riesgo en USD por operación a lo largo de los años (objetivo vs real) y contratos por época.
4. **Frecuencia**: operaciones por mes contra la esperada en el registro.

Orden sugerido (de más a menos evidencia, todas en NQ/MNQ salvo indicación): T → R → Z-banda → RQ5 (NQ; ES/YM como
comparación) → SOM (NQ) → V. Turtles oro, C2_VZ/C2_EVRP y ES5N quedan fuera hasta que Nico decida qué hacer con su estado.
