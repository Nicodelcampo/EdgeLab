# ORB NQ — propuesta para 5, 15 y 30 minutos con filtros

Estado: PROPUESTA — NO AUTORIZA P&L NI LANZAMIENTO
Fecha: 2026-11-08
Familia / módulo: ORB-NQ-FILTROS
North Star: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`
Procedencia: diseño y prototipo sin outcomes sobre base `70a373088af0289c32f8c5f1500cb2d560cd5a05`; ningún kernel. Pedido de Nico en `docs/DECISIONES_20261108.md`.

## Pregunta y evento

¿Una ruptura del rango inicial RTH de NQ tiene expectativa neta positiva, total o condicionada por día de la semana, hora de señal y volatilidad conocida antes de la entrada? Mecanismo hipotético: concentración de órdenes e información en la apertura; no presupone que haya un edge.

Unidad: primera ruptura **por duración y sesión**; cada sesión aporta como máximo tres señales correlacionadas. Una señal con filtros que no pasan no habilita una segunda entrada. No confundir tiempo de señal con hora exacta de fill. No se separan largo/corto para seleccionar resultados. No se operan otros instrumentos ni aperturas.

## Reglas propuestas, aún sujetas a aprobación

- Sesión regular de Nueva York, `America/New_York`, incluidas transiciones DST. Tres cajas: 09:30–09:35, 09:30–09:45 y 09:30–10:00 ET. Usar las velas M1 cuyos cierres están en `(09:30, fin]`; exigir cada minuto presente, válido y del mismo segmento contractual. Si no, esa caja no existe ese día.
- Primera vela M1 con cierre estrictamente fuera de la caja después de finalizarla y antes de 15:55 ET: largo por arriba, corto por abajo. Una señal por caja y sesión; ejecutar a mercado en el primer tick posterior, con precio realizable y fricción canónica. Sin reentradas. **Es ruptura por cierre M1**: no es idéntica a la ORB de stop apoyado de `strategies/orb.py`, ni a la señal de cierre de 5 min de ORB-HORARIOS. Documentar los gaps y los casos de fill inválido sin reemplazarlos con el cierre previo.
- Stop en el extremo opuesto de la caja; sin take-profit; salida a mercado al primer tick ejecutable de la regla de cierre. Salida normal 15:55 ET; antes si el calendario de sesión lo exige. Si el calendario de cierres tempranos no se puede verificar, excluir esa sesión por criterio establecido sin mirar su P&L. Si el precio de fill deja el stop del lado incorrecto, no se entra. Resolver orden intrabar con ticks, considerar gaps en el stop y medir el riesgo inicial desde el fill efectivo.
- Resultado = puntos netos tras spread/slippage/comisión, divididos por el riesgo inicial real. Costos canónicos NQ de `config/costos/costos_canonicos.json`, SHA-256 `bbddeaa6f6267585fc153f242042f1ca61e9f1827ecbabdc0698ca296c9d229c`: escenario base y adverso, sin cobrar dos veces spread si el fill ya usa bid/ask. El costo se aplica **antes** de dividir por el riesgo. Aclarar si el registro sólo tiene last y el spread se modela.
- **Noticias:** prohibido abrir o mantener posición durante ventana USD tier1 y tier2 del calendario conocido. Propuesta conservadora hasta implementar salida anticipada: antes de entrar, excluir la señal si cualquier ventana bloqueada conocida interseca desde el fill previsto hasta el cierre programado; sin usar la salida realizada para filtrar. Ventanas cerradas ±1 minuto, con el calendario y reglas de `edgelab/noticias.py`. Debe evitarse también el fill dentro de la ventana; verificar el calendario disponible en cada fecha como se conocía entonces. SHA del CSV actual `8a152d092314c42498638cbee2144cef0851b013a8536ed0b661c3fdb8381234`. **El calendario no incluye todos los eventos rojos** (véase `config/noticias/FUENTES.md`); completitud y point-in-time son bloqueantes, no se afirma cumplimiento integral hasta resolverlos.

## Filtros y multiplicidad

Todos los filtros se conocen en la vela de señal; hora = hora del **cierre de señal**, en ET, no hora de inicio de la caja ni del fill. El fill posterior debe seguir siendo válido. Niveles, definidos antes de ver P&L:

- Duración: 5, 15, 30 min, sin combinar duraciones.
- Día de trade date: lunes, martes, miércoles, jueves, viernes o cualquiera: 6 niveles. La fecha ET de la señal RTH debe coincidir con el trade date del dato.
- Hora señal: [09:35, 10:30), [10:30, 12:00), [12:00, 14:00), [14:00, 15:55) ET, o cualquiera: 5 niveles. Una caja no puede generar señales antes de terminar.
- ATR: TR M1 y media simple de 14 velas terminadas hasta la señal, en puntos NQ; sin cruzar sesión, huecos de un minuto ni segmento contractual. Terciles bajo, medio, alto o cualquiera: 4 niveles. Dos cortes se determinan sólo con señales válidas E0 de descubrimiento, de las tres duraciones combinadas, sin retornos; se congelan para cualquier evaluación posterior. Si faltan ATR o los cortes degeneran, no asignar la señal a una categoría ni inferir un régimen; publicar cobertura y revisar antes de resultados.

Hipótesis predefinidas: **3 × 6 × 5 × 4 = 360 celdas nominales** por canal, inclusive las variantes sin filtro, sin descontar celdas sin potencia. Dos canales predefinidos, total y últimos tres meses de descubrimiento, 720 contrastes nominales; asignar alfa 0,05 por canal y controlar maxT/step-down por sesión sobre la familia completa de cada canal, respetando dependencia entre duraciones y filtros. Contar evaluables y no evaluables; no crear una familia separada para la mejor duración o filtro. Las pruebas previas y otras búsquedas ORB son antecedentes, no desaparecen por cambiar nombre: no afirmar control global histórico sin un registro y presupuesto agregados. Mostrar número bruto y método para el efectivo, sin inventar independencia.

## Datos, contaminación y límites

- Fuente candidata: ticks futuros NQ del release `nicolasbuttaro/edgelab-liquid-ticks-20261014` v4, manifiesto SHA-256 `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`. Uso privado aprobado externamente en `docs/infra/RELEASE_APPROVAL_20261014.md`: verificar autorización, manifest y hashes con `purpose=research`, `verify_hash=True`, cobertura por sesión/contrato, rolls, y licencia antes de usarlo. No sustituir con USATECH CFD para validar ejecución NQ.
- Descubrimiento propuesto: sesiones disponibles entre 2025-08-05 y 2026-03-31, inclusivos. Comprobar catálogo y registrar sesiones faltantes, días cortos, calentamiento y acceso antes de fijar el universo. La historia usada para definir cortes es exploratoria.
- Abril–septiembre 2026 ya se examinó en campañas ORB relacionadas: no llamarlo réplica independiente por cambiar longitudes, filtros o salida. Confirmación válida requiere una ventana no consumida, específicamente aprobada y congelada; mientras tanto las nominaciones serían exploratorias.
- Holdout desde la sesión del 2026-10-01 permanece sellado. Ni precios ni outcomes de ese tramo intervienen en cortes, decisiones ni esta campaña.
- Antecedente: `docs/research/orb0100_20261021/RESULTADOS_ORB_HORARIOS_Y_FRANJAS_20261021.md` reportó cero celdas cribadas en la grilla de 704. Sus reglas difieren: no constituye un resultado de este diseño ni una prueba de que este diseño funciona.

## Integridad y condiciones para ejecutar

1. Revisar independientemente y aprobar este manifiesto; registrarlo en un commit propio antes de cualquier medición de outcomes. Pedir OK explícito de Nico para este diseño y datos. E0 target-free por separado **no** equivale a permiso para P&L.
2. El archivo `patches_for_review/orb_nq_20261108/senales_orb.py` es únicamente un prototipo de señales target-free; no es un módulo de campaña ni un simulador, y no declara autorización para ejecutar datos reales. Validar sus bordes, fechas DST, causalidad por disparo y equivalencia con un oráculo independiente. Pruebas sintéticas: `python -m pytest -q patches_for_review/orb_nq_20261108/test_senales_orb.py` → 10 pasadas en el entorno local de pruebas. Cubren tres rangos, corte causal por señal, huecos en caja/post-caja, ATR, segmentos, orden y transiciones DST; no certifican el motor integrado ni ejecución.
3. Integrar la ejecución al embudo con coste y R por fill, tiempo y news interval, EOD real, entradas/salidas causales, corte de contrato y validación punto-en-tiempo. El filtro `EXCLUIR_EVENTOS` de `grilla_generica.py` comprueba la cercanía de la señal y **no garantiza** que la operación no cruce noticias. No usarlo como sustituto.
4. La rama base emplea cola normal en `grilla_masiva.estadisticas`; Nico eligió t de Student en el trabajo previo. Incorporar y verificar el cambio aprobado en el código exacto, o resolver formalmente el conflicto antes de cualquier tamiz FDR. MaxT no habilita a presentar como corregidos los p/q de un FDR que usa otra cola. No reducir tolerancias para pasar pruebas.
5. Pasar preflight estático/dinámico, ruido con potencia, control plantado, causalidad por disparo, ejecución escalar vs lote y casos de huecos, news y DST. Validar potencia, memoria, n de sesiones y costo adverso. Registrar versiones, dataset y hashes, SHA del código limpio, manifest, filtros, exclusiones, tiempos y salida por cada corrida.
6. Descubrimiento sólo después de estos controles y del OK; congelar celdas/cortes antes de cualquier evaluación posterior. Reportar universo, celdas evaluables, intervalos, MDE/potencia, ambas direcciones agregadas y resultado del canal no direccional. Celdas con poca muestra = sin potencia, no refutadas. No promocionar sin réplica independiente y las demás compuertas vigentes.

## Estado y pendientes

`python tools/docs_index.py --check` en la base y el índice regenerado señala dos documentos previos del régimen estructural que carecen de `Estado:`; no se modificaron porque no son parte de esta campaña. El índice debe quedar limpio antes de integrar.

Cuota de GPU de la cuenta `nicolasbuttaro` consultada el 2026-11-08: 30 h semanales, 0 usadas/reservadas; se renueva 2026-11-14 UTC. Es sólo cuota GPU y no garantiza CPU ni ejecución. El MCP de Kaggle `save_notebook` guarda **y ejecuta**: no invocarlo como si fuera una preparación inocua. Ningún kernel lanzado; falta adaptar el runner del repo a las credenciales disponibles o crear una orquestación equivalente segura y trazable. Los resultados/P&L no se han consultado para esta propuesta.

Aporte al referente: se concreta el pedido en una búsqueda conjunta de 360 variantes de ORB; el prototipo y la propuesta no son una corrida ni evidencia de un edge.
