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

## Bloqueos antes de P&L

1. Release adjuntada y hashes verificados en E0; falta contrastar sesiones presentes, contratos, días cortos y calibración inicial con el registro. No tocar octubre ni el holdout.
2. Acreditar calendario de noticias completo y conocido en cada instante histórico. El CSV vigente omite algunos eventos de alto impacto; el filtro estándar comprueba cercanía de señal, no toda la vida de la posición. No reemplazar el veto preventivo por exclusiones retrospectivas.
3. Integrar y auditar el simulador: primero asegurar contrato/sesión y disponibilidad hasta cierre sin selección por desenlace, control de fill y tiempo, bid/ask o costo modelado sin doble conteo, stop con gaps y normalización neta por riesgo real. Validar contra un oráculo independiente. Lo escrito hoy es un prototipo local, no cumple todavía esas condiciones de producción.
4. Grilla conjunta, controles de potencia y multiplicidad predeclarados, y tamiz coherente con la cola t aprobada por Nico. La rama base aún usa normal en `grilla_masiva.estadisticas`; no presentar sus p/q como si usaran t. Preflight y revisión independiente pendientes.
5. Abril–septiembre ya se examinó en ORB relacionada; no llamarlo réplica independiente. El índice de docs detecta dos fallas previas de encabezado `Estado:` en documentos del diagnóstico de régimen estructural; corregir por la vía correspondiente antes de integrar a CI.

**Resultado económico: NO MEDIDO.** No hay conclusión de rentabilidad ni selección de filtro ganador.

Aporte al referente: la estrategia quedó especificada y aprobada, el riesgo y las noticias tienen prototipos probados sintéticamente, y E0 terminó con datos pre-holdout, sin resultados económicos; las versiones 1–3 fallaron cerradas sin leer precios.
