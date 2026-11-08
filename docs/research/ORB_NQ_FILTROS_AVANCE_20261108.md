# Avance — ORB NQ 5, 15 y 30 con filtros

Estado: PROVISIONAL — E0 COMPLETO, NO CONGELAR; P&L NO MEDIDO
Fecha: 2026-11-08
Familia / módulo: ORB-NQ-FILTROS
Procedencia: código E0 commit `a38f5a3524394f1d31289b89b665a94411296196`; simulador sintético commit `6f27b97376c144a768df501f093d4c936e06356f`; kernel privado `nicolasbuttaro/orb-nq-e0-target-free-20261108` versiones 1–4; release fijada `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`.

## Pedido y aprobación

Nico aprobó en chat el diseño de `ORB_NQ_FILTROS_MANIFIESTO_20261108.md`: NQ RTH, cajas de 5, 15 y 30 min, filtros día/hora/ATR, cierre M1 como señal, ejecución en el siguiente tick, stop al otro lado, sin TP y salida programada. La aprobación autoriza completar guardas y correr descubrimiento **cuando se cumplan**, no levantar las guardas ni abrir holdout. Decisión registrada en `docs/DECISIONES_20261108.md`.

## Hecho

- El prototipo de señales y un conductor E0 independiente generan únicamente señales, conteos y cortes de ATR; no calcula retornos, fills ni P&L. E0 solicita la release por el lector oficial con `purpose=research`, `verify_hash=True`, hash de manifiesto fijado y selección segura por row groups. Los cortes están rotulados preliminares: no congelar antes de verificar población, calendario y noticias.
- Un simulador separado y todavía **no integrado** ensaya con ticks sintéticos el riesgo desde el fill, gap de stop, fricción antes de dividir por riesgo y veto de noticias ex ante. Si una salida demorada cruza una ventana bloqueada, aborta; no excluye trades por su resultado. Está bajo `patches_for_review/` y no debe usarse sobre datos reales como si fuera un motor auditado.
- Comando local: `PYTHONPATH=. python -m pytest -q patches_for_review/orb_nq_20261108/test_senales_orb.py patches_for_review/orb_nq_20261108/test_e0_orb.py patches_for_review/orb_nq_20261108/test_simulador_orb.py` → **23 pasadas**, exclusivamente con sintéticos. Entorno aislado: Python 3.13, numpy 2.5.4, pandas 3.1.1 y pytest 9.2.0. No es preflight integral, prueba de paridad ni revisión independiente.

## Incidente Kaggle E0

- Dataset privado verificado por metadatos: `nicolasbuttaro/edgelab-liquid-ticks-20261014`, versión vigente 4, incluye `data/NQ_ticks.parquet`; verificación de archivos y hash en runtime estaba pendiente en los intentos 1–3.
- Kernel privado, sin internet ni GPU. Tres versiones en estado `ERROR`. Versión 1: no se encontró `release_manifest.json`. Versión 2 comprobó tanto búsqueda con symlinks como contenido de `/kaggle/input`: `INPUT_ROOT: []`; versión 3 con `datasetDataSources` y `datasetDataSourcesSetter` produjo lo mismo. No se probó que la causa sea un campo específico del MCP: sólo que el dataset **no quedó montado**. Se detuvo antes de abrir precios; no hubo E0 ni outcomes.
- Código embebido verificado por SHA contra el commit E0. Wrapper v1 SHA-256 `f950cf7d8d776ade8b256f6f46feca6179be1a041fe0588bd844e62536ce1c55`; v2/v3 `993d0cc16e0bbfeac641845bf093721dee7504df1f4b6aecae9ab580a85fa6d0`. El slug real se copió de la respuesta de Kaggle; no inventar uno.
- La disponibilidad de GPU no garantiza cuota de CPU. No volver a lanzar versiones idénticas: resolver adjunto con un canal funcional y verificar versión, privado, manifest y hash. Si se utiliza UI en vez del MCP, obtener aprobación de Nico antes de cambiar de vía y no activar internet ni GPU innecesariamente.

## E0 ejecutado — versión 4

Se adjuntó mediante la interfaz el dataset privado `nicolasbuttaro/edgelab-liquid-ticks-20261014` y se guardó y ejecutó la versión 4, con estado `COMPLETE`. La ejecución encontró la release y verificó el manifiesto fijado y los archivos por hash con el lector oficial; NQ SHA-256 `cccc7c807ead85389aa48a2eaff728106f5c9cd1a9e67f74f69c7f272ea78a89`. Se seleccionaron row groups del 2025-08-05 al 2026-03-31, sin deserializar holdout. Los hashes de módulos embebidos coinciden con los registrados en el log; la verificación abarcó todos los archivos de la release, no solamente NQ.

El output `E0_ORB_NQ_PRELIMINAR.json` contiene conteos de sesiones y señales, y cortes preliminares de ATR. Permanece en Kaggle privado: antes de sacar datos de la cuenta corresponde revisar la licencia CME. Los cortes son descriptivos, no congelados ni prueba de rentabilidad. Las sesiones reportadas son sesiones presentes en el archivo, no una validación de cobertura del calendario. No se filtraron noticias ni se verificaron los cierres anticipados; no se pueden considerar aún población elegible o selección definitiva de filtros.

Notebook privado: https://www.kaggle.com/code/nicolasbuttaro/orb-nq-e0-target-free-20261108 (versión 4, output y logs). No se calcularon fills, stops, retornos ni P&L.

## Continuación — bordes sintéticos y calendario

- Se corrigió el prototipo del simulador: el primer fill debe tener timestamp **estrictamente mayor** que el cierre de señal. Si varios ticks comparten el instante de la señal, no se inventa su orden intrananosegundo. El E0 de la versión 4 no usa este simulador; sus resultados no se modificaron.
- Se añadió un límite exclusivo de sesión que debe suministrar y justificar el llamador. Una posición sin salida antes de ese límite aborta en vez de valorar un tick de otra sesión. Es una barrera adicional, no prueba de captura completa ni de una demora de salida aceptable; falta certificar sesión y contrato, política de huecos y disponibilidad antes de medir.
- Resultado local: **28 pruebas sintéticas aprobadas**, incluidas dos de los bordes temporales y una comparación de 1.000 casos seudorrandómicos con una implementación escalar de prueba. No es revisión humana independiente, paridad contra el motor de producción, ni autorización para datos reales. El prototipo continúa en `patches_for_review/`.
- Hallazgo de calendario: `docs/research/cme_equity_index_calendar_20260902/cme_equity_index_session_calendar_v1.json` cubre las fechas propuestas de descubrimiento y marca sesiones normales, cerradas y de cierre anticipado con fuentes CME. Fue capturado el 2026-09-02, después del descubrimiento; por sí solo **no acredita que cada horario se conocía en el momento histórico** ni demuestra captura íntegra de ticks. El propio README señala que el 2025-11-28 tuvo una sesión discontinua no representada por el modelo de intervalo continuo. Antes de usarlo hay que validar su alcance, las excepciones y su disponibilidad ex ante.
- `NQSessionEligibilityGateV1` descarta cierres anticipados y se abstiene ante calendario/captura desconocidos, pero sus parámetros por defecto para captura y roll no prueban evidencia; métricas de volumen o ticks de toda la sesión pueden introducir información posterior a la señal. No se enchufó al runner ni se usó como certificación de elegibilidad. La completitud y point-in-time de noticias sigue sin resolverse.
- La corrección Student-t aprobada sigue sin integrar: el borrador previo no supera una prueba estadística histórica que sí pasa con la base. No se relajó su umbral. Resolver ese conflicto y la prueba de ruido es condición anterior al tamiz; los ensayos sintéticos de simulador no lo sustituyen.

## Continuación — diagnóstico del tamiz con ruido sintético

Se comparó el control histórico en **1.000 semillas nuevas** (`1000..1999`, elegidas antes de esta corrida, luego de examinar `0..999`). Es la misma construcción sintética, no una nueva distribución ni un control de mercado: 160 sesiones, factor común simétrico por sesión, error t(4) por operación, `min_n=10`, `q=alfa=0,10` y 299 permutaciones de signo por sesión. Esto **no calibra** la grilla ORB de 360 celdas, cuyo nivel es 0,05 por canal, ni el preflight de U1, que usa otra grilla. No se usaron datos reales ni holdout.

| Tamiz en nula global | Corridas con ≥1 nominación / 1.000 | Proporción e IC 95% Wilson |
|---|---:|---:|
| maxT por sesión | 91 | 9,1% [7,5%, 11,0%] |
| t por operación + Storey | 181 | 18,1% [15,8%, 20,6%] |
| t por operación + BH | 118 | 11,8% [9,9%, 13,9%] |
| normal por operación + Storey | 216 | 21,6% [19,2%, 24,3%] |
| normal por operación + BH | 148 | 14,8% [12,7%, 17,1%] |

Bajo esta nula global, cualquier nominación es falsa; estas proporciones estiman la frecuencia de al menos un falso positivo y también el FDR global de este escenario. Las simulaciones están emparejadas por semilla. La comparación descriptiva t+Storey vs maxT dio 95 semillas sólo con nominación de t+Storey y 5 sólo con nominación de maxT (prueba binomial exacta bilateral sobre discordancias `p ≈ 1,25e-22`). Comparaciones múltiples y selección de este escenario tras conocer el test anterior: no extrapolar estos p como garantía general. Los IC son por proporción, no intervalos de la diferencia emparejada.

**Hallazgo de contrato:** el test histórico se llama BH, pero invoca `GM.criba` sin `metodo`, cuyo default es **Storey**, no BH puro. La cola t reduce nominaciones bajo esta nula frente a la normal, pero no basta para garantizar calibración con dependencia intrasesión y estimación adaptativa. maxT tiene fundamento con simetría de signos por sesión — impuesta en esta simulación, **no acreditada en NQ real**. La tasa observada por sí sola tampoco lo valida universalmente. No se cambió el umbral >2 ni se integró el parche Student-t; ambos siguen sujetos a revisión. Las 9 pruebas restantes de `test_criba_maxt.py` pasaron en la base, incluido el caso de señal plantada, y se excluyó explícitamente el test de relación histórica de esa ejecución. Las 2 pruebas numéricas del borrador t pasaron contra SciPy y la referencia del proyecto; eso verifica el cálculo, no la validez estadística bajo dependencia.

Reproducción desde la raíz del repo: `NUMBA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=. python patches_for_review/orb_nq_20261108/control_t_sintetico.py`. Base `713c98083349bd015245d826fd8b3821e320c02b`; Python 3.13, numpy 2.4.6, scipy 1.18.1 y numba 0.68.1. El script de revisión calcula la cola t con SciPy independientemente del parche pendiente, compara ambas colas y ambos métodos, y no reemplaza código de producción.

## Control sintético de la forma de grilla ORB

Se ensayó **un solo canal** maxT con 360 celdas nominales `3 × 6 × 5 × 4`, 160 sesiones, `min_n=30`, alfa 0,05, 299 inversiones de signo por sesión y 500 semillas nuevas `3000..3499`, fijadas antes de la corrida. Cada sesión sintética tiene una señal por duración; día, hora y ATR son categorías simuladas independientes del ruido. Las tres duraciones comparten un factor simétrico por sesión. No se usaron precios, calendario real, exclusión de noticias ni salidas del E0.

- Nula global: hubo al menos una nominación en **26/500 = 5,2%**, IC 95% Wilson [3,6%, 7,5%]. Es compatible con 5% en este único escenario, no una certificación del control de error en datos reales o bajo nulas parciales.
- Mediana **39 de 360 celdas evaluables** por conteo (rango 37–39), con este generador deliberadamente simplificado. Es una advertencia de escasez de muestra en cruces finos, **no** una estimación de las celdas evaluables de ORB real ni una medición de potencia real.
- Con ventaja sintética fija +0,7 en la duración 15 y objetivo predeterminado sin filtros, la celda se nominó 499/500 veces (IC Wilson [98,9%, 100,0%]); se trata de un efecto artificial grande en la escala de este generador, no evidencia ni potencia esperada para NQ.
- Se verificaron las 360 sumas, sumas cuadradas y conteos contra máscaras directas para una semilla, y una señal por duración/sesión. Los contrastes no incluyen todavía el segundo canal reciente, incertidumbre del calendario, ausencias, ni distribuciones asimétricas. La simetría de signos por sesión es construida en la nula, no demostrada para mercado.

Reproducción: `NUMBA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=. python patches_for_review/orb_nq_20261108/control_grid_sintetico.py` con las versiones del entorno del control anterior. No habilita integración ni ejecución de P&L: sigue pendiente el análisis de potencia y de hipótesis con el universo elegible real, sin usar outcomes para selección.

## Continuación — inventario privado de sesiones y noticias

Se versionó `patches_for_review/orb_nq_20261108/diagnostico_universo.py` en el commit `d628f8899d66941661362c3da7b5e335e4411cc0` (SHA-256 del archivo `bd93536030f30ed90734267373fb85d96f4c8f69345eacb793e419636636eddb`). Su código fija hashes del calendario y CSV, valida el hash canónico del calendario y usa el lector oficial para verificar la release completa y los pies del NQ; el diagnóstico no deserializa columnas de precios. Clasifica fechas presentes en row groups frente al calendario y cruza presencia de eventos listados durante la sesión completa, sin declarar aptitud operativa. La ausencia de eventos listados **no demuestra ausencia de noticias**, y la presencia en el footer no demuestra captura íntegra o ticks RTH. El calendario y las noticias son retrospectivos y no están certificados point-in-time.

La versión **5** del notebook privado terminó `COMPLETE` y guardó `E0_ORB_NQ_UNIVERSO_PRIVADO.json` dentro de Kaggle. El inventario señala fechas de clase normal sin grupos, fechas de cierre anticipado con grupos y un grupo en una fecha clasificada como cerrada. Hay que contrastar estas discrepancias con la fuente y el horario aplicable; ninguna se convierte automáticamente en sesión operable o defecto. El detalle por fecha permanece en el output privado, sujeto a la revisión de licencia antes de sacar datos de Kaggle. Las 37 pruebas sintéticas del conjunto ORB pasan, incluidas 9 del inventario y los bordes de DST y ventanas cerradas.

**Incidente de ejecución:** al guardar la versión 5, el editor conservó otra celda de la versión anterior y `Save & Run All` ejecutó también el E0 previo. Ese E0 sí deserializó precios del intervalo pre-holdout para contar señales y generar cortes preliminares; sus resultados se repitieron sin calcular fills, stops, retornos ni P&L. Las guardas de fecha y footer mantuvieron excluido el holdout. El inventario nuevo únicamente verificó archivos y leyó sus metadatos. Antes de otra ejecución en el editor, revisar **todas** las celdas y su orden: sustituir el contenido de una celda no elimina las demás. No inferir elegibilidad ni congelar cortes a partir de esta repetición.

## Continuación — contraste privado de las discrepancias

Se ejecutó en Kaggle un notebook **nuevo y privado**, con una sola celda, CPU y sin internet: https://www.kaggle.com/code/nicolasbuttaro/orb-nq-contraste-metadatos-privado-20261108. Su versión 1 terminó `COMPLETE` y dejó `ORB_NQ_CONTRASTE_METADATOS_PRIVADO.json` dentro de Kaggle. Antes de leer, verificó el SHA-256 fijado del manifiesto y los hashes de los tres archivos de metadatos contra él. Consultó el índice de sesiones, las decisiones de selección y el calendario derivado; no abrió el parquet de ticks, ni calculó señales, fills, resultados o P&L. El filtro se aplicó sobre fechas pre-holdout; los hashes abarcan los archivos completos de metadatos. La salida detallada queda privada y no se redistribuye sin revisión de licencia.

- Las tres fechas sin row group investigadas constan en el índice como `UNDETERMINED`: la decisión de contrato quedó bloqueada por cobertura desconocida de un competidor en D−1. Esto explica su exclusión **según el registro de la release**; no demuestra que faltaran todos los datos de mercado ni autoriza seleccionar otro contrato a posteriori. Una de esas fechas además es de cierre anticipado y está excluida de antemano del diseño ORB provisional.
- Para la fecha que el calendario CME congelado clasifica `CLOSED`, el calendario derivado de la release figura `SHORT` y el índice contiene una decisión `SELECTED`. Como el calendario derivado utiliza actividad observada, esto puede contaminar la definición de D−1 de la sesión posterior. El calendario oficial reconstruido se obtuvo retrospectivamente y tiene limitaciones documentadas; la diferencia exige adjudicar fuente, calendario aplicable y disponibilidad histórica, no modificar silenciosamente las decisiones. El README de calendario ya documenta un tick residual en un escaneo anterior: **no se verificó que sea el mismo dato o causa en esta release**.
- Acción previa a cualquier medición: conciliar el calendario oficial con el derivado y la traza de selección del contrato, revisar los exports pertinentes y reconstruir con política y disponibilidad point-in-time aprobadas. No inferir que corregir el calendario por sí solo recupera sesiones; cambios en D−1 pueden afectar decisiones y el régimen posterior. El inventario de grupos no demuestra cobertura completa.
- Riesgo adicional a revisar: la adjudicación de fuentes por contrato y sesión usa minutos activos y hueco máximo de la **sesión completa** (`edgelab/data/liquid_release/census.py`). Es una regla de reconstrucción sin seleccionar por P&L, pero usa información posterior a la señal: verificar su admisibilidad point-in-time y la sensibilidad a fuentes alternativas antes de usarla como simulación operable. No se ha cuantificado su impacto en ORB.

## Bloqueos antes de P&L

1. Release adjuntada y hashes verificados en E0; falta contrastar sesiones presentes, contratos, días cortos y calibración inicial con el registro. No tocar octubre ni el holdout.
2. Acreditar calendario de noticias completo y conocido en cada instante histórico. El CSV vigente omite algunos eventos de alto impacto; el filtro estándar comprueba cercanía de señal, no toda la vida de la posición. No reemplazar el veto preventivo por exclusiones retrospectivas.
3. Integrar y auditar el simulador: primero asegurar contrato/sesión y disponibilidad hasta cierre sin selección por desenlace, control de fill y tiempo, bid/ask o costo modelado sin doble conteo, stop con gaps y normalización neta por riesgo real. Validar contra un oráculo independiente. Lo escrito hoy es un prototipo local, no cumple todavía esas condiciones de producción.
4. Grilla conjunta, controles de potencia y multiplicidad predeclarados, y tamiz coherente con la cola t aprobada por Nico. La rama base aún usa normal en `grilla_masiva.estadisticas`; no presentar sus p/q como si usaran t. Preflight y revisión independiente pendientes.
5. Abril–septiembre ya se examinó en ORB relacionada; no llamarlo réplica independiente. El índice de docs detecta dos fallas previas de encabezado `Estado:` en documentos del diagnóstico de régimen estructural; corregir por la vía correspondiente antes de integrar a CI.

**Resultado económico: NO MEDIDO.** No hay conclusión de rentabilidad ni selección de filtro ganador.

Aporte al referente: la estrategia quedó especificada y aprobada, el riesgo y las noticias tienen prototipos probados sintéticamente, y E0 terminó con datos pre-holdout, sin resultados económicos; las versiones 1–3 fallaron cerradas sin leer precios.
