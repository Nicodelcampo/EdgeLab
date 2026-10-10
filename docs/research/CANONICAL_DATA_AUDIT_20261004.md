# Revisión de saneamiento y liquidez — 2026-10-04

## Dictamen

**NOT_CERTIFIED_FOR_NEW_STRATEGY / BLOCKED_BY_CUSTODY_AND_INTEGRATION**.
Revisión estática del código y listado autenticado, NO auditoría de filas completa. No hay evidencia nueva que permita afirmar SANITIZED_VERIFIED ni que todos los consumidores usen sólo contratos líquidos. No se modifica el dataset, no se borra historia, no se reejecuta una estrategia ni se abren D2/holdout.

Base de código: ab9a0540c43ad7f68a015a9f22892633a555cd6d.
Dataset principal inspeccionado por metadatos: nicolasbuttaro/edgelab-ticks-nt8-canonical, versión 1. Catálogo publicado: MES, MNQ, MYM, RTY, YM; contiene manifiestos, sesiones, archivos por contrato, AUDIT_MANIFEST.json y files.sha256. Estos nombres NO constituyen descarga/hash/P0/P1A comprobados. El archivo de MGC se etiqueta explícitamente RAW / NOT certified canonical y debe mantenerse separado.

## Hallazgos del código

1. **ALTA — rutas contradictorias de NQ.** databuild/build_nq_clean.py decide el roll con el volumen del mismo día, agrupa fechas sin conversión declarada a UTC/CME y aplica back-adjustment aditivo. No debe alimentar la nueva ejecución tick-exact. edgelab/data/continuous_contract.py implementa un contrato causal, sin ajuste, con identidad y reset; no se comprobó que todos los consumidores lo invoquen.
2. **ALTA — completitud declarada sin prueba.** databuild/build_mgc_canonical.py::build_regime crea complete_session=True para todas las fechas entre primer/último día e inventa volumen 0 con get(d,{}).get('volume',0). Confunde ausencia con actividad cero. date_range usa días de semana, no un calendario CME validado de feriados/cierres cortos. MIN_USABLE_ROWS=100000 por archivo NO certifica liquidez por sesión.
3. **ALTA — selección no garantiza liquidez absoluta.** contract_regime.py usa correctamente D-1 y roll monotónico, pero _normalize_volumes acepta infinito positivo y build_contract_regime puede inicializar/mantener eligible=True con todos los volúmenes cero. Ser líder relativo tampoco asegura spread operable o capacidad para el tamaño de orden.
4. **ALTA — filtro posterior a lectura.** continuous_contract.py ejecuta pq.read_table sobre el contrato entero antes de recortar intervalos. session_inventory y write_canonical de MGC recorren todas las filas antes del filtro de holdout. Son riesgos de no-read establecidos por inspección; NO prueban por sí solos que haya ocurrido contaminación en una corrida concreta.
5. **MEDIA — semántica y procedencia pendientes.** Verificar tick grid antes de rint (MGC lo redondea), nulls, secuencia, bid<=ask, volúmenes negativos, sincronía de quotes, zona/DST, calendario, sesiones truncadas y fuente micro/estándar. No eliminar ticks legítimos sólo por compartir timestamp, precio o cantidad. Deduplicación por identidad y procedencia, no por igualdad económica.
6. **ALTA — wiring no demostrado.** Las búsquedas de símbolos en el índice de main devolvieron sólo sus definiciones para build_continuous_series y assert_run_manifest_uses_regime. Esto indica falta de evidencia de integración, no una prueba exhaustiva de ausencia de llamadas dinámicas.

## Prueba en Kaggle y bloqueo concreto

Notebook privado: https://www.kaggle.com/code/nicolasbuttaro/edgelab-canonical-metadata-audit-20261004.
Intentos v1/v2: /kaggle/input vacío, AssertionError antes de cualquier fila.
v3: kagglehub confirmó que no había versiones adjuntas y respondió: New Datasets cannot be attached in non-interactive sessions. Los parámetros de fuentes del MCP no produjeron un montaje usable.
Ninguna corrida produjo el informe de saneamiento: tick_rows_read=0, ni se examinó liquidez reservada. Solicitar el montaje manual del dataset v1 en ese notebook o una ruta de lectura autenticada funcional, sin reintentos a ciegas.
El listado incluye nuevas fuentes mnq-tick-data y mnq-parquet; NO se elevan a canónicas por aparición, nombre o conversión a Parquet.

## Liquidez que se exigirá antes de evaluar la estrategia CS

- Identidad del contrato y fuente preservada; nada de micro/estándar mezclados, CONT sintético o back-adjustment para fills.
- Calendarizar sesiones CME de forma DST-aware incluyendo feriados y sesiones abreviadas.
- Usar cantidad realmente negociada, no número de mensajes/ticks como sustituto.
- Elección causal con sesión COMPLETA D-1; roll hacia delante, sin rollback ni ganador ex post.
- Límites por instrumento de volumen mínimo y spread p99 máximo, congelados antes de ver rentabilidad. No hay umbral universal ni se inventa aquí un certificado.
- Completitud/quotes/tick grid y cobertura deben tener auditoría independiente; desconocido implica exclusión.
- Capacidad para el tamaño real y profundidad/quotes requieren verificaciones adicionales; un LAST+bid/ask no demuestra fills de libro ni tamaño disponible.
- No contar gaps reales como cero, no rellenar sesiones faltantes y no suavizar saltos de roll. Estado y lookbacks reiniciados en las fronteras.

## Barrera añadida (propuesta, no merge ni integración global)

edgelab/data/research_data_gate.py proporciona require_research_eligibility: exige certificado verificado, checks, identidad y hashes fijados, fecha permitida preholdout, D-1 exacto del calendario, evidencia de sesión completa, volumen finito positivo, límites previamente fijados y spread observado. Rechaza ausencia de prueba, volumen cero/NaN/infinito, ajustes y fechas reservadas. Debe ejecutarse ANTES de cualquier lectura, junto con validate_contract_regime.

16 pruebas sintéticas pasaron en sandbox. No son auditoría de mercado, suite completa ni certificación de filas. Los hashes garantizan integridad, no autoridad; un JSON firmado por su propio autor no reemplaza adjudicación independiente. El certificado de prueba usa SYNTHETIC_TEST_ONLY y nunca debe promoverse.

Los consumidores existentes NO están automáticamente protegidos. Hasta conectar la barrera al adaptador de la futura CS y emitir pruebas de saneamiento/custodia, las nuevas corridas deben permanecer bloqueadas. No se reescriben los manifiestos/ledgers históricos; rectificaciones enlazadas y append-only.

## Ruta pendiente, en orden

1. Montaje autenticado de la versión fijada; comparar bytes y SHA-256 con inventario externo, no solamente con un fichero local autoconsistente.
2. Auditoría estructural y de filas permitidas, fail-closed en grupos mixtos o sin timestamp statistics. Mantener las fechas reservadas fuera del lector; respetar D2 y el límite de cada campaña, no sustituirlos por una fecha genérica.
3. Tabla auditada de sesiones/volumen/spread por contrato, calendario completo y negativos explícitos.
4. Emitir manifiesto causal, lista de sesiones elegibles y certificado revisado; excluir y reportar fallos, sin limpiar silenciosamente la fuente.
5. Integrar gate al adaptador CS de NT8; comprobar paridad de señales/órdenes/fills, causalidad y resets, costes y ejecución tick-exact. Pre-registro y ablations antes de multiplicidad/SPA/DSR/BH y eventual holdout autorizado por separado.
