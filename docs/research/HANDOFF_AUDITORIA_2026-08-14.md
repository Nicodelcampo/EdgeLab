# HANDOFF — Auditoría externa y réplica de paridad — 2026-08-14

**Para**: el próximo agente / Nico. Si el chat se pierde, este archivo + `PENDIENTE.md` + `docs/research/PLAN_SALDO_AUDITORIA_2026-08-14.md` + los `W1_*`/`W3_*` alcanzan para continuar. Todo lo que acá se afirma fue medido y tiene evidencia referenciada.

---

## 0. TL;DR

W1 (identidad del kernel + paridad 6E 09-26) y W3 (paridad ES 09-26) quedaron **CERRADAS a nivel diagnóstico** con cuatro mediciones, todas con identidad sellada punta a punta:

| medición | resultado |
|---|---|
| aVolClusterPOI v0.5, 6E 09-26, 17→30 jun | **72/72 creaciones del oráculo reproducidas, Δscore = 0 exacto**; 4 extras marginales (causa medida: divergencia minuto-level de las dos rutas de datos NT8) |
| BigTrap2 time:1, junio (post-fix) | **3.628/3.638 EXACT (99,73 %)**; resto 100 % atribuido (128 colas suprimidas documentadas, 1 barra de borde, 2 field_diff de 1 tick, 8 del lado Python de las cuales 7 = defecto del parquet junio-only) |
| BigTrap2 time:1, abril+mayo (P-12) | **171/171 EXACT (100 %)**, incluidos los 9 TRAPs pre-rotura uno por uno; 1 extra del kernel dentro de una cola suprimida documentada |
| aVolClusterPOI v0.5, ES 09-26, may→jun (W3) | **100 % exacta antes del defecto de datos del 11-jun (119/119, todos los campos); 98,7 % después (307/311)**; global 442/467 con Δtiempo/Δbucket/Δdistance = 0 en todas las emparejadas; el 11-jun diverge por datos (P-15), no por kernel |

---

## 1. Cronología de commits del día

| commit | qué |
|---|---|
| `03d1104` | auditoría externa (D1–D9; P-08/09/10) |
| `84dcfcd` | plan de saldo (cola W1–W8) |
| `2ad04ec` | sync `BigTrap2.cs` v2.5.2 → **P-08 cerrada** (blob `ee984f6e`) |
| `e7d6a86e` | W1 R1: aVol 72/72; silencio BT2 localizado; P-11/12/13 abiertas |
| `78de4d6` | oráculo ES 09-26 genuino (P-11) |
| `f77a3be` | **fix de frontera de sesión en time:1** (`.cs` blob `62b0c951`) |
| `c899970` | oráculo BT2 completo: 3.807 TRAPs, 9 SESION_RESINCRONIZADA con contadores |
| `ac7508da` | W1 R2: P-13 cerrada medida; veredicto P-12; P-14 nueva |
| `6707c8a` | HANDOFF + P-12 cerrada (171/171) + causa raíz P-14 + lector sandbox |
| `2e05ac9` | evaluación del auditor de V3VolumeHeatmapExt/V2GapsHeatmap |
| (último) | **W3 cerrada (ES 09-26): 100 % pre-06-11, 98,7 % post; P-15 nueva (defecto 06-11 ES)** |

---

## 2. Estado de las P (detalle en `PENDIENTE.md`)

RESUELTA: P-01, P-02, P-03, P-04, P-08, P-11, P-12, P-13.
ABIERTA: P-05 (CI: confirmar el run en Actions), P-06 (panel SMD, diferida), P-07/M0 (licencia, humana), P-09 (regenerar JSON AVOLT), P-10 (3 merges, decisión de Nico), P-14 (defecto 6E 25-jun — causa raíz identificada: el build junio-only, no la fuente), **P-15 (defecto ES 11-jun — nuevo, detectado por W3)**.

---

## 3. Qué se aprendió hoy (lo no obvio)

1. **La política `sesionNoConfiable` en time:1 nunca reseteaba** (el bloque de frontera quedaba detrás del `return` del camino de tiempo) → supresión permanente tras el primer mismatch. El oráculo viejo (9 TRAPs) era un indicador suprimido, no un mercado sin traps. El fix de `f77a3be` lo curó; los 9 resyncs del oráculo nuevo cuadran 1:1 con las 9 sesiones marcadas del viejo.
2. **Las dos rutas de datos de NT8 divergen en ~0,3 % de los minutos** (barras nativas vs `.Last.txt`): medido desde ambos lados. En 6E es ruido menor; en ES el 11-jun cambió la fase de bloques de aVol (~2 barras) — mismo patrón de defecto, dos veces en un día (P-14, P-15). **La batería de ingesta necesita el chequeo "0 minutos faltantes en horario activo contra la serie nativa" como gate permanente.**
3. **El warmup del perfil aVol es de primer orden**: arrancar mal la historia multiplica las emisiones espurias ×18. El oráculo declara su arranque vía `session_index`/`samples`; replicarlo exactamente es obligatorio. En W3 el replay reprodujo (22, 25) del primer evento del oráculo sin ajuste.
4. **Un oráculo "suprimido" es indistinguible de uno "sin detecciones"** → decisión de Nico registrada: futuras versiones del `.cs` MARCAN los eventos en el log en vez de suprimirlos. Y subir el string `version` (sigue diciendo 2.5.2 con el código ya cambiado).
5. **"Front-month natural" NO valida al back-month**: los 9 TRAPs de abril eran del 09-26 (spread de 40–48 ticks vs el 06-26, rangos sin solape + control negativo de 2.985 traps sin coincidencias). Mismo contrato + misma ventana (H2) no admite sustitución.
6. **Los formatos de oráculo difieren por indicador**: BigTrap2 = pipe (`seq|iso|type|payload`); aVol = CSV con comas y header (con `reason` llevando el KIND en eventos de creación). Documentado en `W3_PARIDAD_SANDBOX_2026-08-14.md` §5.

---

## 4. Lo que sigue (cola ordenada, con dueños)

1. **P-14 + P-15 (local)**: regenerar los parquets de junio (6E: adoptar el build 90d; ES: regenerar el mensual) y auditar por qué los builds perdieron minutos (25-jun 6E, 11-jun ES). Agregar el chequeo de minutos faltantes a la batería de ingesta. Luego re-run de W1/W3 esperando los mismos criterios.
2. **Anomalía 06-24 08:56 (6E, local)**: barra OHLCV idéntica en ambas rutas y aun así el oráculo emite y el kernel no → mirar clasificación bid/ask de ese minuto (tasa: 1/3.638).
3. **tick:5/10 de BT2 (la campaña del plan)**: exportar oráculos (el `.cs` auto-sufija `__Tick5`/`__Tick10`); ahí los eventos de control SÍ existen (camino de ticks). Los parquets canónicos entran por chat partidos por mes.
4. **P-05/P-07/P-09/P-10**: CI (mirar Actions), licencia (humana), JSON AVOLT (regenerar), merges (Nico decide).
5. **W2** (curva de especificación descriptiva) corre en local cuando haya ventana de cómputo.
6. **Unificaciones cosméticas detectadas por W3**: kernel aVol debe emitir `direction=NEUTRAL` (no `None`) en AT_PRICE; alinear el conteo de sesiones en la frontera domingo→lunes (drift desde el 21-jun); ciclo de vida aVol (302 INVALIDATED/297 FIRST_TOUCH) como comparación futura.

---

## 5. Receta de réplica sandbox (Notion) — para el próximo agente

El sandbox de Notion corrió hoy réplicas de paridad completas, target-free, no adjudicadoras. Trampas y herramientas duramente aprendidas:

- **El filesystem se borra solo** (hoy se wipeó 3 veces, una entera): todo resultado durable se commitea al repo EN CUANTO se mide. Nada de valor vive en `/data`.
- **Sin red** en el sandbox: los archivos entran como adjuntos de chat (`uploadFile`). GitHub no se puede bajar al sandbox; el contenido del repo se trae vía MCP `get_file_contents` y se verifica con **git-blob sha1** (`sha1("blob <len>\\0" + contenido)`), normalizando EOL. **No re-transcribir archivos de memoria: siempre re-traerlos del repo** (hoy una re-transcripción derivó y falló la verificación de blob — la verificación lo detectó).
- **Lector de parquet propio** (no hay pyarrow/duckdb): versionado en `tools/sandbox_pqread.py` — Thrift compact footer, páginas v1/v2, PLAIN + RLE/bitpack-hybrid, diccionarios, zstd vía `ctypes`, snappy puro.
- **Procesos largos**: `nohup ... &` a veces muere al volver de la llamada; `setsid bash -c '...' < /dev/null &` es el patrón que sobrevive. `tmux` no levantó servidor.
- **Timezones**: oráculos `.cs` en la tz del chart (hoy: ART); parquets en UTC offset 0 declarado (no re-verificado, ver nota del manifiesto); sesiones CME en CT (17:00→16:00, DST-aware). El ancla de bucket de aVol es `(cierre de barra − 1 s)` relativo al inicio de sesión, buckets de 30 min.
- **Convención de barras**: timestamp = cierre; sin barras vacías; barra 0 descartada (BT2).
- **Antes de computar nada**: verificar sha256 de cada archivo contra lo declarado; mismatch → cuarentena (fail-closed).
- Paquetes de oráculo: `.cs` pusheado (la verificación es contra el blob del repo), CSV con meta intacta, un archivo por resolución por corrida, ventana y arranque de la instancia declarados, merge de contratos SIEMPRE off.

---

## 6. Sobre `V3VolumeHeatmap` / `V2GapsHeatmap`

Evaluación completa en `docs/research/EVAL_INDICADORES_HEATMAP_2026-08-14.md`. Resumen: metodología "primero paridad, después medición" correcta; los claims de microestructura son hipótesis con evidencia previa negativa en este proyecto; la persistencia del heatmap de volumen es parcialmente manufacturada por la regla de congelado; overlap con familias existentes (Gaps2, aVol*); F9 sigue pausada; si se incorporan, primero log sellado + cómputo data-driven (hoy dependen de la ventana visible) + paridad, y recién después medición pre-registrada.

---

## 7. Gobernanza (recordatorio inviolable)

- Holdout sellado 2026-07-01 → 2026-12-31: solo validaciones target-free con log. (El parquet 6E 90d incluye ~5 h post-sello de la noche del 06-30 — usado solo para paridad de abril+mayo; declarado. El ES mensual no pasa del 30-jun.)
- Nada de outcomes/P&L sin manifiesto de campaña + OK explícito de Nico (regla STOP).
- El sandbox emite diagnósticos, nunca etiquetas de efecto ni PASS formales (esos salen de la máquina local gobernada).
- Parquets inmutables (el que falla se reexporta, no se parchea); manifiesto regenerado desde el archivo final; merge de contratos OFF; un archivo por resolución por corrida.

---

## 8. Identidades clave (hashes verificados hoy)

| pieza | identidad |
|---|---|
| parquet 6E 09-26 90d (04-01→06-30) | sha256 `1311bc5ea91a111d95f17da84d9a6ee6323920686b0b0873c04d8f3dc94a9652`, 1.131.047 filas |
| parquet 6E 09-26 junio-only (con defecto 25-jun, P-14) | sha256 `46413432b8a68590d775cb67f915c85c6f83eb99459b77abb82a8a3f0b249aae`, 1.103.973 filas |
| parquet 6E 06-26 (mar→15-jun) | sha256 `becc5625aec898919e10bd847f8adb1f05ea06300eb786834c383b3012e34ca2`, 5.550.120 filas |
| parquets ES 09-26 mensuales (abr/may/jun) | sha256 `fd9a4839a24fb5ea…` / `65e26fa587f5a590…` / `e11d664d51d7ea88…` (junio con defecto 11-jun, P-15) |
| oráculo BT2 completo (post-fix) | blob `0837ef7e…`, sha256 `4c76a0f2aa292e2afa461b0b09fdd92916c1b22dcbead1e016e1791805e9f474`, 9.709 eventos |
| `.cs` canónico BigTrap2 (con fix de frontera) | blob `62b0c951b537f3450283d5bb17994dcf4a0c51f5` |
| `.cs` aVolClusterPOI v0.5 | blob `d512d91a606d41609b21ef244c896ead1dc52a10` |
| kernels Python | bigtrap2.py `b235153c…`, avolclusterpoi.py `e472a06899e3…` (sellados) |
| oráculos aVol | 6E `08c2b25e…`; ES 06-26 `2d2328cf…`; ES 09-26 `bd8b7265…` (sha256 `7e2b4701…`) |

---

Aporte al referente: el proyecto cerró su primer día de paridad medida de punta a punta — dos instrumentos, dos indicadores, cuatro ventanas — con un auditor externo corriendo réplicas independientes; cada afirmación tiene hash y evidencia, y cada divergencia quedó clasificada entre "defecto de datos a regenerar" y "artefacto cosmético a unificar". Esto es lo que el NORTH_STAR pide que sea la norma.
