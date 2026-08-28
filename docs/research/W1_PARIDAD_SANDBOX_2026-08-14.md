# W1 — Réplica de paridad en sandbox (6E 09-26, junio) — 2026-08-14

**Etiqueta: RÉPLICA DIAGNÓSTICA NO ADJUDICADORA.** Ejecutada por el auditor externo en el sandbox de Notion, sobre el paquete W1 subido por chat (`paquete_w1_6E_0926_auditor.zip`). No abrió outcomes, P&L ni holdout. Las etiquetas formales PASS/FAIL las emite la máquina local gobernada; acá se mide identidad, estructura y paridad (P1A/P2).

**Insumos (identidad verificada mecánicamente en ambos extremos):**

| pieza | identidad |
|---|---|
| `nt8/BigTrap2.cs` (HEAD `2ad04ec`) | blob `ee984f6e…` — byte-idéntico al `.cs` que corre en NT8 local → **P-08 cerrada** |
| `aVolClusterPOI.cs` (v0.5) | blob `d512d91a…` tras normalizar CRLF |
| kernel `bigtrap2.py` | blob `b235153c…` (sellado) |
| kernel `avolclusterpoi.py` | blob `e472a068…` |
| oráculo BT2 v2.5.2 time:1 90d | blob `fb41f33a…` |
| oráculo aVol 6E | blob `08c2b25e…` |
| parquet 6E 09-26 | sha256 `46413432…` (ver §5/P-12: su manifiesto no lo describe) |
| bridge Python montado en sandbox | 12 archivos del repo, 11 verificados byte-exactos por git-blob; excepción declarada: `edgelab/data/nt8_contract.py` no cerró por blob bajo ninguna variante EOL/BOM (sus constantes se verificaron una a una; es catálogo, no kernel; sin efecto en la corrida) |

---

## 1. Verificación estructural del parquet (independiente del manifiesto)

- Ventana real: **2026-05-31 17:00 CT → 2026-06-30 15:59:58 CT** (solo junio + la apertura dominical). El paquete pedía 90 días (04-01→06-30): no los cubre. Consecuencia directa en §3.
- 1.103.973 filas. Monotonía ✓, `sequence` 0→1103972 ✓, contrato único `6E 09-26` ✓ (R1), agresor buy/sell sin unclassified ✓, máx 212 ticks/ts (D2 OK), **cero ticks en la ventana de mantenimiento 16–17 CT de junio** (firma D1 ausente ✓), 27 días CT, hueco máximo 53 h (fin de semana) ✓.
- Schema con `price_ticks/bid/ask` enteros en grilla (D3 imposible por construcción) y columna `contract` (D4 cerrada).
- Lector de parquet propio (Thrift compact + páginas v1 + zstd vía ctypes), escrito en el sandbox; el footer declara las 1.103.973 filas que se decodificaron.

## 2. P1A + barras propias vs M1 nativo NT8 (`6E_1min.csv`)

- **P1A: PASS.** 25.221 barras M1 construidas desde ticks, `quote_fraction` 1.0, 0 `FOOTPRINT_MISMATCH` (en Python la identidad footprint↔barra es estructural: mismo slice).
- Convención del CSV nativo: timestamp = **cierre** de barra (25.204 exactas contra 17 con la otra hipótesis).
- **25.204 / 25.219 minutos con contraparte son EXACTOS en OHLCV (99,94 %).** Pero: **15 minutos con diffs y 52 minutos del CSV sin barra propia** (2 propios sin CSV).
- Los 15 con diffs son minutos donde el `.Last.txt` y las barras nativas de NT8 no coinciden (p.ej. 06-09 12:37 vol 30 vs 26; 06-11 11:32 el parquet trae un trade extra en 23125 → low 23125 vs 23126; 06-25 12:48 vol 227 vs 37). **Las dos rutas de datos de NT8 divergen a nivel minuto en ~0,3 % de los minutos** — la misma firma que el propio `.cs` reporta desde adentro con sus `FOOTPRINT_MISMATCH` (§3) y que EXPORT_REQUISITOS cataloga como D1–D5.

## 3. BigTrap2 v2.5.2 time:1 — divergencia de emisión (BLOCKED, adjudicación local)

- Oráculo (carga 90d, 04-01→06-30): **9 TRAPs, todos 04-01→04-16** (back-month, vol 3–8), después cero. 11 `FOOTPRINT_MISMATCH` (04-17→06-25, patrón semanal de cierre de sesión + cluster 06-11).
- Kernel Python (blob `b235153c`, params del meta del oráculo) sobre junio verificado: **3.759 TRAPs** (`min_export_volume=1`), 0 mismatches.
- Lectura del `.cs` (blob `ee984f6e`): la política de rotura `sesionNoConfiable` se arma en `VerificarOHLC` cuando el OHLC del bloque no cierra y **solo se baja en la frontera de sesión siguiente**; `EmitirBarra` con la sesión marcada hace `nSuprimidas++; return;` — o sea, **la supresión corta también el export de TRAP, no solo la creación de zonas**. El patrón del oráculo (último TRAP 04-16 10:56, primer mismatch 04-17 16:25, silencio total después) es compatible con supresión persistente, pero el reset semanal no explica el silencio lunes–jueves: queda abierta la hipótesis de **deriva permanente del pareo FIFO tras el primer mismatch**. El CSV del oráculo no trae los eventos de control que el `.cs` sí emite (`SESION_RESINCRONIZADA`, `ANCLAJE_*`, `BARRA_PROCESADA`) — posiblemente filtrados al exportar — y sin ellos no se distingue una cosa de la otra.
- Verificación independiente de los 5 mismatches de junio: en **4/5 mi barra (desde ticks) coincide con el lado `blk` (subserie de ticks) del `.cs` y no con su `bar` nativo** → el parquet está del lado del `.Last.txt`; el nativo de NT8 es el que difiere. En 06-25 12:48 mi barra tiene vol 227 vs 37 del CSV nativo: discrepancia mayor, revisar local.
- **Estado: BLOCKED para BT2.** Los 9 TRAPs de abril quedaron fuera de cobertura (parquet de junio); junio enfrenta 3.759 vs 0. La adjudicación exige (a) parquet de 90 días, (b) log de eventos COMPLETO del `.cs` sin filtrar tipos, (c) corrida local gobernada. → P-13.

## 4. aVolClusterPOI v0.5 — 72/72 exactas; 4 extras marginales (WARN diagnóstico)

- Oráculo 6E (06-17→06-30; 171 eventos, 72 creaciones). El oráculo declara su propio estado de warmup: `session_index` arranca en 7 el 06-17 y `samples=21` = 7 sesiones × 3 bloques/bucket → la instancia NT8 cargó ~06-08. La réplica inició el perfil Python en la sesión 06-08 (mismo estado, es la cura del defecto H3 del dictamen AVOLT).
- **Resultado: 72/72 creaciones del oráculo reproducidas**, con **max |Δscore| = 0,0** (detección byte-exacta), Δsamples = 0 y Δsession = 0 en todos los pares, direcciones idénticas, Δbar_index constante +3261 (origen de conteo distinto, benigno).
- Δthreshold ≠ 0 en solo **2/72** pares (ambos −31, sesión 7, bucket 43, el primer día comparado): el contenido de historia difiere en ese bucket.
- **4 zonas extra en Python** (06-18 14:01; 06-24 14:36; 06-29 14:26 — score 1094 contra umbral 1093 — y 06-29 14:46): emisiones al filo del umbral. Hipótesis causal medida: las 15+52 divergencias de barras del §2 caen dentro de bloques de warmup, alteran scores de historia y mueven el percentil 98 lo suficiente para voltear emisiones marginales. Prueba decisiva disponible en local: replay con las barras nativas del CSV M1 en vez de las construidas desde ticks (o saneando los 15 minutos) — si los extras desaparecen, la cadena queda demostrada.
- **Sensibilidad H3 cuantificada**: arrancando el perfil en 06-01 (todo el parquet) el núcleo se mantiene (72/72) pero los extras explotan a **71**. El estado de warmup es de primer orden para la tasa de emisión: declarar siempre el arranque de la instancia NT8 (ya quedó en el §"Paquete de validación" del plan de saldo).
- **Estado: WARN diagnóstico.** Gate estricto de paridad: 4 `MISSING_IN_NT8` → FAIL; lectura honesta: núcleo 72/72 exacto + 4 emisiones marginales explicables por la divergencia de barras medida en §2. La etiqueta formal la pone la corrida local gobernada.

## 5. Defectos del paquete (procedencia)

- **P-11**: `avolcluster_v05_ES_0926.csv` es copia byte-idéntica del ES_0626 (mismo blob `2d2328cf`) y su meta declara `instrument=ES 06-26` → **el oráculo de ES 09-26 no existe**; re-exportar.
- **P-12**: el parquet W1 cubre solo junio (no 90d) y su manifiesto de build declara 3.182.270 filas + otro hash (`2377b076…`) — describe otro build. Se procesó bajo la etiqueta de réplica diagnóstica verificando el dato independientemente; por la regla del proyecto, sin esa verificación era cuarentena.
- Higiene menor: `avolcluster_v05_07jun2026.csv` == `avolcluster_v05_junio2026.csv` (duplicado con dos nombres; el nombre quedó viejo: el contenido cubre 06-17→06-30); `tools/replay_p2_es_0626.py` está escrito contra una API vieja del bridge (`SessionProfile(window_bars=…)`, `fps.raw`, `bars.close_time_ns`) y no correría contra el bridge vigente; `MANIFESTO_W1.json` declara `git_head_local=05d24d1` (pre-rebase; hoy es `bda944a`).

## 6. Qué sigue (en orden)

1. Nico/local: re-export aVol ES 09-26 (P-11); parquet 90d con manifiesto regenerado desde el archivo final (P-12); oráculo BT2 con log de eventos completo (P-13).
2. Local gobernado: replay aVol con barras nativas vs ticks para cerrar los 4 extras; corrida BT2 con log completo para adjudicar el silencio.
3. Sandbox: re-corro la réplica cuando lleguen los paquetes corregidos; el arnés queda escrito y es re-ejecutable.

---

Aporte al referente: primera réplica sandbox con identidad sellada punta a punta (blobs de `.cs`, kernels, oráculos y parquet verificados antes de computar nada). La paridad de aVol quedó medida al nivel más fino que el proyecto tuvo (72/72 con Δscore = 0), la divergencia de BT2 quedó localizada (política de supresión + pareo FIFO) con la prueba decisiva identificada, y la divergencia minuto a minuto entre las dos rutas de datos de NT8 quedó cuantificada (0,3 %) con evidencia desde ambos lados. Nada de esto emite etiqueta de efecto: es paridad y estructura, nunca outcomes.
