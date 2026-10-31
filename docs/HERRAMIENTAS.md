# Herramientas del repo (`tools/`)

Estado: VIGENTE. Generado por `python tools/existente.py catalogo --write`; no editar a mano.

**Antes de escribir un script, módulo o función:** `python tools/existente.py buscar "qué querés hacer"`. Si algo de acá o de `docs/MODULES.md` ya lo hace, se reutiliza (importándolo o reemplazando su lector, como `tools/barrido_horario_etapa_c_parquet.py` hace con `one`). Si se construye igual, el commit dice qué se encontró y por qué no sirve. `tests/test_existente.py` falla si un script nuevo no está acá o si aparece una función copiada.

551 scripts.

| script | qué hace (primera línea del docstring) |
|---|---|
| `tools/_manifiesto_comun.py` | Lógica compartida de los manifiestos de identidad. **Un solo lugar.** |
| `tools/actualizar_y_arrancar_debian_v2.py` | Bootstrap de un solo paso para que el Agente del Debian se actualice a la troncal y arranque en Modo Multi-Agente Espiral v2. |
| `tools/aggressor_validate.py` | Valida la columna `aggressor` de research-v2 contra el agresor por cotización del L2 (target-free). |
| `tools/agotamiento.py` | AGOT-EXT: agotamiento en extremo (divergencia de RSI y de delta). Manifiesto aprobado por Nico el 25/09 |
| `tools/agregar_velas.py` | Bundle de velas Nt a partir de un bundle 25t, agrupando de a k velas DENTRO de cada sesión (como el 100t del visor). |
| `tools/analisis_profundo_corredores.py` | tools/analisis_profundo_corredores.py |
| `tools/analizar.py` | Analizador de estrategias (como el Strategy Analyzer de NT8) sobre el simulador sellado y los costos canónicos. |
| `tools/analizar_embudo.py` | Reporte del analizador (estilo Strategy Analyzer) de las celdas que dieron positivo en el backtest y no confirmaron en el embudo. |
| `tools/apply_hft_v2_headless_patch.py` | Fail-closed source patch for HFTZonesNQPureV4_V2 export mode. |
| `tools/atlas_asimetrico.py` | Atlas nulo — grilla ASIMÉTRICA P/N y horizontes finos. **NULL / DESCRIPTIVO.** |
| `tools/atlas_excursiones_nulas.py` | ATLAS DE EXCURSIONES NULAS — **NULL / DESCRIPTIVO. NO ES UN EDGE.** |
| `tools/atras_celdas.py` | ATRAS (2026-10-26): celdas positivas sin señal de las campañas con señal en CFD, sobre la historia NUNCA mirada antes de su DESC. |
| `tools/audit_analytical_store_parity.py` | (sin docstring) |
| `tools/audit_avzvol_mnq_metadata.py` | Read-only AVZVOL candidate MNQ metadata review. NEVER a quality/research PASS. |
| `tools/audit_avzvol_o5_boundary_exports.py` | Opt-in internal-label boundary audit of exposed O5; no prices/new endpoints. |
| `tools/audit_avzvol_o5_postwindow_labels.py` | Audit all 200 existing post-window bar labels, never optimize/filter O5 effects. |
| `tools/audit_avzvol_outputs.py` | Audit pinned preholdout AVZVOL event covariates; no tests/returns/controls. |
| `tools/audit_avzvol_trigger_observability.py` | Pinned exposed-export FOOTER audit; no price/outcome payload or market replay. |
| `tools/audit_bundle_compression.py` | (sin docstring) |
| `tools/audit_canonical_ticks.py` | (sin docstring) |
| `tools/audit_capture_event_v2.py` | CLI mínima para auditar un TSV de CaptureEventProbeV2. |
| `tools/audit_censo_gate.py` | Gate fail-closed entre censo_integridad y cualquier análisis de señales. |
| `tools/audit_consolidated.py` | Auditoría de datasets de ticks consolidados por activo (corre en Kaggle con los datasets adjuntos y edgelab-data-catalog). |
| `tools/audit_edge_factory_schemas.py` | (sin docstring) |
| `tools/audit_es_escalonadas_targetfree.py` | Target-free custody/geometry audit. No raw price trajectories or returns. |
| `tools/audit_foundation_comprehensive.py` | (sin docstring) |
| `tools/audit_kaggle_aggregates.py` | Structural QA only. Never emits sanitation/liquidity certification or permission. |
| `tools/audit_kaggle_coverage.py` | Full date/interval diagnostics, never calendar/liquidity certification. |
| `tools/audit_kaggle_notebook_source.py` | Inspect a saved Kaggle get_notebook_info JSON; NEVER execute its source. |
| `tools/audit_kaggle_raw_ticks.py` | Structural canonical_tick_v1 QA only, never sanitation/liquidity approval. |
| `tools/audit_mnq_l2_v2_first_session.py` | (sin docstring) |
| `tools/auditar_corridas_nube_20261029.py` | Herramienta ejecutable de auditoría de las corridas cosechadas y preparadas desde la sesión en la nube (Olas 1-10). |
| `tools/auditar_procedencia.py` | Barre un directorio temporal y busca evidencia que sostenga afirmaciones vivas. |
| `tools/autopilot_activar_escalera.py` | Activa la regla de decisión `escalera_v1` en el autopilot del Debian, en dos pasos (decisión de Nico, 2026-10-22: «hacé lo que |
| `tools/autopilot_doctor.py` | Chequeo previo al arranque del autopilot en el Debian (solo lectura). Sale con 0 si todo lo imprescindible está bien. |
| `tools/autopilot_generate.py` | Genera candidatas (borradores) a partir de la evidencia propia, la literatura y los resultados vivos; las ordena por valor esperado de información. |
| `tools/autopilot_protect.py` | SOLO HUMANO: regenera config/autopilot/protected.json (hashes de gates, guardas del propio autopilot, pre-registros ya usados). |
| `tools/autopilot_smoke.py` | Corrida de humo del autopilot (benchmark, sin hipótesis): carga una semana de M1 de GC por la ruta normal (verifica el manifiesto de lanzamiento) y escribe un JSON mínimo. |
| `tools/autopilot_watchdog.py` | Vigilante EXTERNO del autopilot: corre en su propio timer, así detecta lo que el ciclo no puede ver de sí mismo. |
| `tools/avcl_cache_stage1.py` | AVCL cache etapa 1 (AVCL-VOL-2, manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_cierre.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_dist.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_exit.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_grid_stage1.py` | AVCL-CIERRE etapa 1 (manifiesto docs/research/AVCL_CIERRE_MANIFIESTO_20261006.md): 13 celdas + delta de zona. |
| `tools/avcl_pre.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_racimo.py` | AVCL-RACIMO (manifiesto docs/research/AVCL_RACIMO_MANIFIESTO_20261006.md). Lee caches de zonas/barras |
| `tools/avcl_racimo_audit.py` | AVCL-RACIMO-AUDIT: aislada CAUSAL (sin look-ahead) + control de movimiento previo. Basado en AVCL-RACIMO. Lee caches de zonas/barras |
| `tools/avcl_racimo_audit_ypre.py` | AVCL-RACIMO-AUDIT: aislada CAUSAL (sin look-ahead) + control de movimiento previo. Basado en AVCL-RACIMO. Lee caches de zonas/barras |
| `tools/avcl_racimo_conf.py` | AVCL-RACIMO (manifiesto docs/research/AVCL_RACIMO_MANIFIESTO_20261006.md). Lee caches de zonas/barras |
| `tools/avcl_racimo_conf_stage1.py` | AVCL-RACIMO-CONF etapa 1 (pre-registro docs/research/AVCL_RACIMO_PREREGISTRO_20261006.md, a578a7a1): celda base 50t. |
| `tools/avcl_sr_dir.py` | AVCL-SR-DIR (manifiesto docs/research/AVCL_SR_DIR_MANIFIESTO_20261006.md). Lee el cache de AVCL-VOL-2. |
| `tools/avcl_vol1_fast.py` | AVCL-VOL-1 — etapa 1 (no direccional). Manifiesto: docs/research/AVCL_VOL1_MANIFIESTO_20261005.md (OK de Nico). |
| `tools/avcl_vol1_run.py` | AVCL-VOL-1 — etapa 1 (no direccional). Manifiesto: docs/research/AVCL_VOL1_MANIFIESTO_20261005.md (OK de Nico). |
| `tools/avcl_vol2_ab.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avcl_vol3_robust.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
| `tools/avolcluster_census.py` | Censo Estructural Target-Free para export de aVolCellPOI2 / aVolCluster. |
| `tools/avzp2_ob_stage1.py` | AVZP2-REBOTE etapa 1 (manifiesto docs/research/AVZP2_REBOTE_MANIFIESTO_20261007.md): enmienda 1: rojas vs pseudo-zonas que cumplen la regla OB. |
| `tools/avzp2_pnl_sim.py` | AVZP2-PNL-ES: simulador de brackets tick a tick (docs/research/AVZP2_PNL_MANIFIESTO_PROPUESTO_20261014.md). |
| `tools/avzp2_racimo_grid_stage1.py` | AVZP2-RACIMO-GRILLA etapa 1 (36 definiciones de racimo) (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md): desenlaces desde la formación del racimo, real vs pseudo apareado por ocupación. |
| `tools/avzp2_racimo_grid_stage2.py` | AVZP2-RACIMO-GRILLA análisis (manifiesto docs/research/AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md). |
| `tools/avzp2_racimo_grid_vol_stage2.py` | AVZP2-RACIMO-GRILLA, enmienda 2: auditoría de O5 por volumen e intensidad previos |
| `tools/avzp2_racimo_replica_stage1.py` | AVZP2-RACIMO-GRILLA etapa 1 (36 definiciones de racimo) (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md): desenlaces desde la formación del racimo, real vs pseudo apareado por ocupación. |
| `tools/avzp2_racimo_replica_stage2.py` | AVZP2-RACIMO-REPLICA análisis (manifiesto docs/research/AVZP2_RACIMO_REPLICA_ES_NQ_MANIFIESTO_20261014.md + enmienda de la auditoría externa). |
| `tools/avzp2_racimo_stage1.py` | AVZP2-RACIMO etapa 1 (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md): desenlaces desde la formación del racimo, real vs pseudo apareado por ocupación. |
| `tools/avzp2_racimo_stage2.py` | AVZP2-RACIMO análisis (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md). |
| `tools/avzp2_rebote_stage1.py` | AVZP2-REBOTE etapa 1 (manifiesto docs/research/AVZP2_REBOTE_MANIFIESTO_20261007.md): primer regreso y rebote, zonas reales vs pseudo. |
| `tools/avzp2_rebote_stage2.py` | AVZP2-REBOTE análisis (manifiesto docs/research/AVZP2_REBOTE_MANIFIESTO_20261007.md). |
| `tools/avzvol_design_smoke.py` | Synthetic AVZVOL match smoke only. Research STOP before input access. |
| `tools/avzvol_detector_tape_smoke.py` | Invented offline tape demonstration; no input path or market execution mode. |
| `tools/avzvol_reaction_smoke.py` | Synthetic continuation vs failed-break classifier; no market input support. |
| `tools/avzvol_response_smoke.py` | Synthetic measurement demo only, no market loader or implicit policies. |
| `tools/axf.py` | AXF: agotamiento por flujo → barrido del último extremo participante → reversión confirmada. NQ, exploración. |
| `tools/barrido_horario_dukascopy_fetch.py` | Descarga de ticks de XAU/USD de Dukascopy (solo las horas UTC que cubren la franja 04:15 CT). Uso: python tools/barrido_horario_dukascopy_fetch.py AAAA-MM-DD AAAA-MM-DD etiqueta  (escribe en ./raw/). Límite de velocidad  |
| `tools/barrido_horario_etapa_a.py` | Etapa A del barrido horario (PREREGISTRO_ETAPA_A.md). Solo datos previos al holdout. |
| `tools/barrido_horario_etapa_b_gc.py` | Etapa B GC (PREREGISTRO_ETAPA_B_GC.md). Solo datos previos al holdout. |
| `tools/barrido_horario_etapa_c_parquet.py` | Etapa C con el dataset unificado de Dukascopy (enmienda C3): usa la misma función `one` de barrido_horario_etapa_c_spot.py, con ticks leídos del parquet. |
| `tools/barrido_horario_etapa_c_spot.py` | Etapa C (PREREGISTRO_ETAPA_C_GC_SPOT.md + enmienda C1): celda GC 04:15 CT sobre XAU/USD spot de Dukascopy. |
| `tools/barrido_horario_p1_h1h2.py` | Enmienda P1 (REVISION_EMBUDO_DISCOVERY_Y_PLAN_ORO_20261004.md §3.2/§4): H1 (celda congelada) y H2 (corto sin condición) a las 04:15 CT sobre XAU/USD spot, |
| `tools/barrido_opp_tables.py` | LOCAL ONLY. Independent-opportunity outcome tables for ANY (weekday, slot, hold, filter, direction), same timing semantics as the replica. |
| `tools/bateria_cobertura_bootstrap.py` | BATERÍA DE COBERTURA — auditoría de F-MET 3 antes de congelarlo. |
| `tools/bateria_cobertura_estimando_ratio.py` | Cobertura de G2 para theta_trade=sum_d(u_d)/sum_d(v_d). |
| `tools/bench_grilla.py` | Benchmark reproducible del núcleo de grilla masiva (2026-10-24). Datos sintéticos, sin mercado: mide tiempo, no edges. |
| `tools/bigtrap2_inventory.py` | Inventario TARGET-FREE de BigTrap2 sobre los folds de desarrollo (time:1). |
| `tools/blind_espejo_eventos.py` | Eventos de espejo para la calibración A CIEGAS «¿hay picos acumulados antes de A?» (idea de Nico, 30/09). |
| `tools/blind_espejo_outcomes.py` | Exploración pedida por Nico (30/09): ¿los espejos que juzgó «con picos» antes de A tienen ventaja sobre los «sin picos»? |
| `tools/brain_register_20260928.py` | Registro en el Cerebro (hipocampo) de lo medido y aprendido el 27–28/09/2026. Idempotente por episodio: si un |
| `tools/bt2_absorption_audit_rolls.py` | (sin docstring) |
| `tools/bt2_absorption_b9_context.py` | (sin docstring) |
| `tools/bt2_absorption_census.py` | Censo target-free de BigTrap2Absorption. |
| `tools/bt2_absorption_frontmonth_chain.py` | (sin docstring) |
| `tools/bt2_absorption_nrand_capacity.py` | (sin docstring) |
| `tools/bt2_absorption_param_sweep.py` | Barrido target-free, reanudable y fail-closed de BigTrap2Absorption. |
| `tools/bt2_absorption_power.py` | Auditoria reproducible de potencia para Puerta 1 de BigTrap2Absorption. |
| `tools/build_agg_tick_bundle.py` | Bundle de velas de N·25 ticks a partir del bundle de 25t (IPC macro, etiquetado). |
| `tools/build_avzp2_kernels.py` | Arma (y opcionalmente sube) los kernels de Kaggle de la familia AVZP2 a partir de un script de etapa 1 del repo. |
| `tools/build_avzp2_replica_kernel.py` | Arma el kernel de Kaggle de la réplica AVZP2 (etapa 1 + análisis integrados) para UN instrumento, con el detector VALIDADO. |
| `tools/build_delta_layer.py` | Capa de delta por vela (volumen agresor comprador y vendedor) para un bundle de 25 ticks del visor. |
| `tools/build_edge_factory_target_free_store.py` | (sin docstring) |
| `tools/build_emacorridortrendvol.py` | (sin docstring) |
| `tools/build_es_espejo_bundle.py` | (sin docstring) |
| `tools/build_es_ext_2026q3.py` | Canoniza la extensión jul-sep 2026 de ES o NQ (enmienda HOLDOUT-A1, 26/09) desde la historia del AddOn de NT8. |
| `tools/build_espejo_slice_bundle.py` | Bundle liviano para ver espejos en el visor (28/09, pedido de Nico): toma un bundle mensual de 25t y conserva las |
| `tools/build_espejo_triads.py` | Tandas de a tres espejos para que Nico los ORDENE por semejanza (target-free, a ciegas). Pedido de Nico, 28/09. |
| `tools/build_event_store_all5.py` | Build canonical Event Store coordinates for GC all 5 contracts. |
| `tools/build_gex_viewer_layer.py` | Capa GEX del visor (sólo dibujo, target-free) + bundle ES 09-26 de 1m/5m para verla. |
| `tools/build_hft_corridor_bundle.py` | Build a target-free NQ HFT corridor bundle. |
| `tools/build_hft_corridor_bundle_from_sqlite.py` | Build a causal, target-free viewer bundle from the frozen HFT V2 SQLite. |
| `tools/build_ipc_spec_preview.py` | Vista previa CIEGA de la replicación IPC (modo «race» de spec_review.html). |
| `tools/build_kaggle_audit_manifest.py` | Manifiesto auditable, por archivo, para un paquete de dataset de Kaggle con datos L2. |
| `tools/build_kaggle_bundle.py` | Indice, sello y staging del bundle de Kaggle - v2 fail-closed. |
| `tools/build_l2_catalog.py` | Catálogo canónico de sesiones L2 (E:\l2_parquet): contrato líder por sesión CME y exclusión de sesiones ilíquidas. |
| `tools/build_l2_contexts.py` | Contextos L2 (4 climas) para ES, MES y MNQ: mismo pipeline que tools/build_l2_contexts_nq.py (sin cambios de |
| `tools/build_l2_contexts_nq.py` | Contextos L2 (4 climas) en NQ según docs/research/PROTOCOLO_CONTEXTOS_L2_NQ_20260928.md (auditoría 051 §1). |
| `tools/build_l2_gate_contexts.py` | Build causal GC L2 GATE contexts from paired nt8_l1/l2 v2 Parquets. |
| `tools/build_l2_release.py` | Arma (y opcionalmente publica) un dataset PRIVADO de Kaggle con el L2 de UN instrumento. |
| `tools/build_l2_viewer_bundle.py` | Bundle de visor con PROFUNDIDAD L2 de una sesion: heatmap del libro (Bookmap-like) + cinta de trades + velas. |
| `tools/build_lux_imb_m1_bundles.py` | Barras M1 desde ticks pre-holdout + zonas LUX-IMB (OG + VI) para todos los activos, como bundles del visor. |
| `tools/build_mes_nqlit_bundles.py` | Bundles de MES 25 ticks con las zonas HFT calculadas con los parámetros LITERALES de NQ (`NQ_LITERAL_TRANSFER`), como |
| `tools/build_mgc_25t_arrays.py` | (sin docstring) |
| `tools/build_mgc_tick_arrays.py` | (sin docstring) |
| `tools/build_multiasset_25t_hft_bundles.py` | Build viewer-ready 25-tick + HFT bundles from an explicit audited plan. |
| `tools/build_mym_canonical.py` | Constructor y canonizador de ticks y régimen contractual para MYM (Micro E-mini Dow). |
| `tools/build_mym_viewer_bundle.py` | Generador del bundle de visor para MYM (Micro E-mini Dow). |
| `tools/build_nt8_ticks.py` | Reconstruye el parquet canónico F2 desde el `.Last.txt` de NT8. |
| `tools/build_release.py` | Arma la release líquida: UN Parquet de ticks por activo, sólo sesiones con contrato líquido elegido causalmente. |
| `tools/build_research_history_ledger.py` | Ingesta retroactiva al Hipocampo durable: hipótesis de research ya cerradas o falsadas. |
| `tools/build_spec_preview.py` | Vista previa CIEGA de una especificación de entradas, para revisión visual antes de correr (Nico confirma). |
| `tools/build_tbz_e2_layer.py` | Capa TBZ-E2 para el visor unificado: TODA la lógica medida, sobre el gráfico continuo de 25 ticks. |
| `tools/build_viewer.py` | build_viewer.py — exporta un STORE a un bundle para el visor v2 (F6.5). |
| `tools/build_zone_def_batch.py` | Tanda ✓/✗ para validar definiciones de zona de IPC (target-free, a ciegas). Diseño: DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md §5. |
| `tools/calibrate_hftzones_universal_profiles.py` | Perfiles escalados de HFTZones (motor NQ congelado) para todos los activos. **Target-free**: solo ticks. |
| `tools/camp001_dryrun.py` | Dry run de CAMP-001 — SIN acceso a retornos ni P&L. |
| `tools/camp001_integrity.py` | CAMP-001 A3 — INTEGRIDAD ANTES DE ABRIR. |
| `tools/camp001_preflight.py` | CAMP-001 A1 — PREFLIGHT. Resuelve la configuración EFECTIVA y la contrasta |
| `tools/camp001_report.py` | CAMP-001 A4 — REPORTE EN UNIDADES DE EDGE. |
| `tools/camp001_run.py` | CAMP-001 A2 — EJECUCIÓN INMUTABLE. |
| `tools/campaign_ticks_multi.py` | Campaña multi-instrumento sobre ticks (5 familias x 4 variantes x 5 instrumentos = 100 pruebas). |
| `tools/campaign_ticks_multi_rerun.py` | Re-corrida CORREGIDA de F3/F4 de la campaña multi-instrumento (bug de apertura RTH, 2026-09-23). |
| `tools/canasta.py` | Canasta de estrategias de régimen (edgelab/funnel/canasta.py): estado, altas desde el embudo, operaciones forward y retiros. |
| `tools/cartera_diaria.py` | Ciclo diario de la cartera viva (docs/CARTERA_VIVA.md). Lo corre el Debian después del cierre de CME (timer |
| `tools/censo_es_nq.py` | CENSO DE INTEGRIDAD para `es_full_ticks` y `nq_ticks_clean`. |
| `tools/censo_integridad.py` | CENSO DE INTEGRIDAD — todos los días de todos los parquets. |
| `tools/censo_zonas_nq.py` | Censo target-free de zonas HFT sobre NQ, con barrido de umbrales gratis. |
| `tools/check_installed_core.py` | Core-only installed-wheel smoke; no Arrow, CUDA, network or market data. |
| `tools/check_installed_kaggle_quality.py` | Installed wheel functional smoke: invented timestamps only, no network/prices. |
| `tools/check_installed_runtime.py` | Installed-wheel import smoke. No market-data read; run outside source tree. |
| `tools/check_modules.py` | Valida config/modules.json contra el arbol real del repo y genera docs/MODULES.md. |
| `tools/check_nt8_cs.py` | Verifica un `.cs` de NinjaScript antes de instalarlo en NT8. |
| `tools/check_remote_metadata.py` | (sin docstring) |
| `tools/check_research_data_gate.py` | Check pinned eligibility metadata only. Never opens market-data source files. |
| `tools/cobertura_release_preholdout.py` | Cobertura por activo del release líquido de Kaggle hasta la apertura del holdout, desde su índice de sesiones (sin ticks). |
| `tools/compare_session_parity.py` | Comparador de paridad por sesion CME, con veredictos separados por capa. |
| `tools/compilar_nt8_cs.py` | T6 — gate REAL de compilación de un NinjaScript. Sin abrir NinjaTrader. |
| `tools/compile_emacorridortrendvol.py` | (sin docstring) |
| `tools/convert_l2_to_parquet.py` | Batch conversion script for CME Level 2 depth CSV files to compressed Parquets. |
| `tools/correr_gates.py` | Corre los gates de paridad de todos los oráculos y clasifica los FAIL. |
| `tools/corridor_anchors.py` | Anclas del sector de volumen de EmaCorridorTrendVol (espejo en Python de ComputeAnchors del indicador de NT8). |
| `tools/corridor_hft_census/build_census_script.py` | Arma el kernel de Kaggle del censo corredor x HFT: Pasada 2 + DET_NT8 + dev addon (sin main_dev) + port HFT Flat + census_addon. |
| `tools/corridor_hft_census/census_addon.py` | (sin docstring) |
| `tools/corridor_pass2/build_dev_script.py` | Construye el script de Kaggle de la Adenda D: Pasada 2 (sin su main) + variante de detector DET_NT8 + adenda + main_dev(). |
| `tools/corridor_pass2/corridor_dev_events_addon.py` | (sin docstring) |
| `tools/corridor_pass2/dev_filters_analysis.py` | Adenda D — analisis local de la tabla de eventos de desarrollo (ES, 299 sesiones). |
| `tools/corridor_pass2/edgelab_es_corridor_pass2_falsification_v4_sym.py` | EDGELAB — PASADA 2: BATERÍA COMPLETA ANTI-OVERFIT Y FALSACIÓN DE FALSOS EDGES |
| `tools/corridor_pass2/ema_corridor_trend.py` | EmaCorridorTrend v4.0 — Detector de Zonas y Corredores Tendenciales Estables sobre EMA. |
| `tools/daily_data_health.py` | Chequeo diario de datos (R0: captura continua). Detecta que la captura se haya cortado y que el respaldo de L2 este al dia. |
| `tools/data_catalog_build.py` | Construye el catálogo legible (docs/data_catalog) desde el inventario crudo. |
| `tools/data_curate.py` | Selección de datos APROBADOS para análisis: aplica reglas fijas, por sesión, al catálogo y escribe docs/data_catalog/{curated.json,CURATED.md,REEXPORT.md}. |
| `tools/data_find.py` | Responde «¿qué datos hay de X entre estas fechas y de dónde los saco?» usando docs/data_catalog/catalog.json. |
| `tools/data_inventory.py` | Inventario crudo de TODOS los datasets propios de Kaggle: lista de archivos, textos pequeños (README, manifiestos) y un escaneo de cada parquet de ticks |
| `tools/data_resolver.py` | Genera docs/data_catalog/RESOLVER.json: UNA respuesta por (instrumento, sesión) — qué dataset/archivo/contrato leer y |
| `tools/deep_falsification_probe.py` | tools/deep_falsification_probe.py |
| `tools/demo_vectorbt_zones.py` | Demo end-to-end (F8): estrategia vectorbt que combina zonas de 2+ indicadores |
| `tools/deploy_nq_25t_bundle.py` | Deploy NQ 25-tick candles and HFT certified zones (5,438 zones) to viewer bundles. |
| `tools/diagnose_es_context_intervals_20260929.py` | (sin docstring) |
| `tools/diagnostico_decaimiento_temporal.py` | tools/diagnostico_decaimiento_temporal.py |
| `tools/discovery_audit_report.py` | Convierte los JSON de auditoría (artifacts/discovery/audit/audit_*.json) en tablas Markdown. Descriptivo: no excluye nada. |
| `tools/discovery_cache.py` | Arma el caché (barras + filas de ejecución) y la auditoría de datos de uno o más activos. Una sola lectura de ticks para todas las familias. |
| `tools/discovery_scan.py` | Barrido de descubrimiento sobre un activo o un grupo de activos pre-fijado. Pasos: tensores -> (calibrar) -> barrer en D0 -> replicar en D1 (D2 sellado) -> registrar. |
| `tools/docs_index.py` | Genera docs/INDEX.md y docs/INDEX.csv: catalogo de toda la documentacion del repo, por familia, con fecha, estado y titulo. |
| `tools/download_options_gex_history.py` | Downloads canonical historical options chains and computes daily GEX history (SPY / QQQ). |
| `tools/dukascopy_descarga.py` | Descarga autónoma de ticks de Dukascopy por HTTP (sin JForex; corre en el Debian). Formato público del datafeed: |
| `tools/dukascopy_diario.py` | Descarga diaria de Dukascopy para el embudo (la corre edgelab-datos-dukascopy.timer en el Debian). |
| `tools/edge_brain_cli.py` | Command-line interface for the Edge Discovery Brain. |
| `tools/edge_brain_load_data_perf.py` | Carga en el Edge Brain (hipocampo durable, append-only y encadenado por hash) el aprendizaje de la corrida GEX-1 de Kaggle del 2026-10-05: |
| `tools/edge_brain_load_speed_pins_20261012.py` | Carga en el Edge Brain (append-only, idempotente) los aprendizajes de 2026-10-12: perfil a escala real, manifiesto de lanzamiento, estadísticos por construcción y fallos silenciosos en Kaggle. Lecciones solo PROPOSED/LOW |
| `tools/edgelab_catalog.py` | Read-only repository navigation. No market data, network or module imports. |
| `tools/edgereplica_usatech.py` | EdgeReplica (60 reglas) sobre USATECH CFD Dukascopy M1 bid/ask. Pre-registro: docs/research/edgereplica_usatech/PREREG.md. |
| `tools/ema_calibrate_screens.py` | Calibra el detector de zonas EMA-estables contra las capturas del usuario (1 píxel ≈ 1 barra de 25 ticks; escala ajustada con la propia EMA dibujada). |
| `tools/ema_digitize.py` | Digitaliza capturas de NinjaTrader (velas rojo/verde, EMA naranja, línea azul del usuario) a series por columna de píxeles. |
| `tools/ema_feedback_lines.py` | Mide las líneas azules de las capturas del usuario (22-31): extensión, pendiente, desplazamiento en ATR, toques, distancia media y máxima al precio. Sirve para calibrar qué líneas el usuario considera buenas o malas. |
| `tools/ema_post_zone.py` | EMAZ-D3 — volumen tras el fin de la zona CON la corrección del sesgo: referencia en la barra de ruptura (conocida en tiempo real) y control emparejado por el contramovimiento previo. |
| `tools/ema_spot_t2.py` | EMA 200/500/2000 de MGC reproducida en XAU/USD spot (enmienda P1 §4.2): prueba primaria T2 (información direccional bruta por horizonte, sin SL/TP). |
| `tools/ema_zones_study.py` | Descriptivo (NO es una prueba de hipótesis): ¿cómo se comporta el detector de zonas EMA-estables en la HISTORIA de NQ (25 ticks, EMA 200, sesiones aprobadas hasta 2026-09-30)? |
| `tools/emaalign_stage1.py` | EMA-ALIGN etapa 1 (manifiesto docs/research/EMAALIGN_ESTRATEGIA_MANIFIESTO_20261007.md): EMA 200/500/2000 en 2t, 54 celdas, tick a tick. |
| `tools/emaalign_stage2.py` | EMA-ALIGN análisis (manifiesto docs/research/EMAALIGN_ESTRATEGIA_MANIFIESTO_20261007.md). |
| `tools/emasep_stage1.py` | EMA-SEP etapa 1 (manifiesto docs/research/EMASEP_CONTRA_MANIFIESTO_20261007.md): contrarian por separacion de 3 EMAs, 10t. |
| `tools/emasep_stage2.py` | EMA-SEP análisis (manifiesto docs/research/EMASEP_CONTRA_MANIFIESTO_20261007.md + enmienda de agotamiento). |
| `tools/embudo_correr.py` | Corre el embudo automático sobre una o más campañas hasta que terminan o quedan esperando datos del holdout (mismo código que |
| `tools/embudo_simulacion_potencia.py` | Simulación con verdad conocida: ¿cuántos edges reales confirma cada diseño de decisión y cuántos falsos deja pasar? |
| `tools/emisor_senales_nt8.py` | Emisor de Señales y Validador de Paridad para NinjaTrader 8 (`EdgeLabSpiralBasketExecutor.cs`, 2026-10-29). |
| `tools/equivalence_check.py` | Mide qué tan buen sustituto es una serie de ticks de otra fuente (p. ej. spot XAU/USD de Dukascopy) para la EMA 200/500/2000 de barras de 25 ticks de MGC. |
| `tools/equivalence_m1_gc.py` | Equivalencia de M1 spot (Dukascopy) con GC para horas fijas. Umbrales en docs/research/equivalence_20261004/PREREGISTRO_EQUIVALENCIA_M1.md. |
| `tools/es_escalonadas_outcomes.py` | ES-ESCALONADAS outcomes — docs/research/MANIFIESTO_ES_ESCALONADAS_OUTCOMES_20260930.md (OK de Nico 30/09). |
| `tools/es_escalonadas_v2.py` | ES-ESCALONADAS v2 — docs/research/MANIFIESTO_ES_ESCALONADAS_V2_20260930.md (OK de Nico 30/09, enmienda 100 celdas). |
| `tools/es_ipc_tick_support.py` | Frozen ES families on UTC-day 25-record bars; no return labels or L2 claims. |
| `tools/escalera_candidatos_20261022.py` | Aplica la escalera del embudo (edgelab/funnel/escalera.py) a los dos candidatos reales del sprint 20-22/10, con costos canónicos. |
| `tools/escalonadas_det.py` | Zonas escalonadas de ES (familias PLANAS y EMPINADAS) con su vela de DETECCIÓN en tiempo real. |
| `tools/escalonadas_exact4.py` | Exact-four completed-bar geometry. No backfill, fills or price outcomes. |
| `tools/escalonadas_posicion_visual.py` | Posición visual del visor (SL fijo en ticks, TP en R, BE en R) sobre las zonas escalonadas — exploración de Nico 30/09. |
| `tools/espejo_cont_100t.py` | ESPEJO-CONT-100T-FILTROS — pedido de Nico 28/09 (corrida en Kaggle, datos Lucid). |
| `tools/espejo_cont_tpsl.py` | ESPEJO-CONT-TPSL — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_ESPEJO_CONTINUACION_TPSL_20260928.md |
| `tools/espejo_curva.py` | Diagnóstico de la curva de ESPEJO-MACRO al 75 % (2026-09-27, pedido de Nico: «¿la curva parece pareja?»). |
| `tools/espejo_gc_p1p2.py` | Candidato GC (reversión tras el espejo) — controles P1 y P2 pedidos por el auditor (062/063), OK de Nico 29/09. |
| `tools/espejo_macro.py` | ESPEJO-MACRO: el espejo de impulsos grandes en velas de tiempo (5 y 15 min), SPY descubre y ES replica. |
| `tools/espejo_mas_alla.py` | ESPEJO-MÁS-ALLÁ, Fase 0 (manifiesto `docs/research/MANIFIESTO_ESPEJO_MAS_ALLA_BORRADOR_20260927.md`). |
| `tools/espejo_nico_descubrimiento.py` | ESPEJO-NICO-100T — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md |
| `tools/espejo_null_control.py` | Control empírico del nulo de CONT/REV (pedido de Nico 28/09, Kaggle). |
| `tools/espejo_nulo_sintetico.py` | Auditoría 056 §4/§6: ¿es P(completar)=f el nulo correcto con velas 100t, toque por mecha y horizonte censurado? |
| `tools/espejo_rev_100t.py` | ESPEJO-REV-100T — pedido de Nico 28/09 (Kaggle, datos Lucid). Manifiesto: docs/research/MANIFIESTO_ESPEJO_REV_100T_20260928.md |
| `tools/espejo_semejanza.py` | ESPEJO-SIM: ¿la vuelta que se parece al impulso (velocidad y forma de las ondas) completa el espejo? |
| `tools/espejo_semejanza_diag.py` | Diagnóstico target-free de la semejanza v1 vs v2 de ESPEJO-IND (2026-09-27). Sin desenlaces ni P&L. |
| `tools/espejo_semejanza_nico.py` | Semejanza «a lo Nico» entre la ida A→B y la vuelta, validada contra sus órdenes por tandas de a tres (target-free). |
| `tools/espejo_vollimp.py` | ESPEJO-VOLLIMP-100T — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_ESPEJO_VOLUMEN_LIMPIEZA_100T_20260928.md |
| `tools/estado.py` | estado.py — UN comando que dice dónde estás parado. Correlo al abrir sesión. |
| `tools/eurusd_escalonadas_grid.py` | EURUSD-ESCALONADAS-ESCALAS — docs/research/eurusd_escalonadas_20261021/MANIFIESTO_EURUSD_ESCALONADAS_ESCALAS_20261021.md |
| `tools/eventos_desde_noticias.py` | Genera `edgelab/research/eventos_datos.py` desde el calendario canónico de noticias (`edgelab/noticias.py`, |
| `tools/evx.py` | EVX: cruces EMA × VWAP de sesión. Etapas E0 (censo) y E1 (información, sin P&L). |
| `tools/exec_qi.py` | EXEC-QI: costo de entrar pasivo vs agresivo, condicionado al desequilibrio del libro (QI). |
| `tools/exec_qi_nt8_compare.py` | EXEC-QI, validación de fills: lee los CSV de EdgeLabExecQIProbe (NT8) y compara. |
| `tools/existente.py` | Antes de construir, buscar lo que ya existe (pedido de Nico, 2026-10-24: «la mayoría de las herramientas ya se encuentran |
| `tools/explo_asimetria_excursion.py` | Exploración (descriptiva, sin decisión): asimetría de la excursión posterior a la creación de zonas. |
| `tools/explo_edgereplica_mgc_20261006.py` | Exploración (decisión de Nico 2026-10-06, sin custodia de holdout): EdgeReplica en MNQ 12-26 y celda MGC 04:15 |
| `tools/export_head_snapshot.py` | Exporta un snapshot de CÓDIGO del commit HEAD como un .tar.gz chico, para que un auditor externo lo descargue de una vez y corra los tests. |
| `tools/falsification_battery.py` | tools/falsification_battery.py |
| `tools/finalize_release.py` | Ensambla la release a partir de las partes por activo: manifiesto global, metadatos y README para agentes. |
| `tools/fixture_p0.py` | fixture_p0.py — Fase A del puente NT8 → EdgeLab: selección de fixture + gate P0. |
| `tools/gc_current_logic_l2_census.py` | GC May31 current-logic event census; target-free, never mirror.run/outcomes. |
| `tools/gc_exact4_prepare.py` | Local metadata capture / exact4 target-free census. Never computes outcomes. |
| `tools/gc_exact4_review.py` | Audit private exact4 census; bind layers to the original chart bundle. |
| `tools/gc_exact4_variants.py` | Resolve proposals only against an explicitly captured GC baseline. |
| `tools/gc_kaggle_tick_l2_probe.py` | Target-free exact-tape GC join; strict earlier publication, no same-ts book. |
| `tools/gc_l2_asof_smoke.py` | GC legacy-example QA ONLY; generic features are in l2_asof_features. |
| `tools/gc_l2_fixed_price_probe.py` | GC R02/I-3 feasibility probe. No price outcome, aggressor inference or P&L. |
| `tools/gc_l2_historical_controls.py` | Target-free P1: historical controls, observed recovery, not price prediction. |
| `tools/gc_pressure_atlas_v2.py` | GC: presión, avance y trayectorias — V2 sobre la release canónica (manifiesto docs/research/GC_PRESSURE_PROGRESS_V2_MANIFIESTO_20261014.md). |
| `tools/gc_pressure_panel.py` | C2 and prospective mirror50 pressure panel. No future labels or fitted model. |
| `tools/gen_avcl_sim.py` | Genera nt8/aVolClusterPOISim.cs a partir de aVolClusterPOI.cs (que NO se modifica: tiene paridad validada). |
| `tools/generate_cme_policy_pdf.py` | Generates an official, rigorous 1-page PDF compliance memorandum regarding CME Market Data & Kaggle policies. |
| `tools/generate_density_field_golden_vectors.py` | Genera los vectores dorados que atan `density_field.js` a `density_field.py`. |
| `tools/generate_hypothesis_backlog.py` | (sin docstring) |
| `tools/generate_kaggle_canonical_manifest.py` | EdgeLab Global Canonical Migration Manifest Generator |
| `tools/generate_parity_partial_json.py` | Fail-closed partial V2 parity census. Partial evidence never certifies globally. |
| `tools/generate_test_evidence.py` | Generates test execution evidence artifact conforming to test_execution_evidence_v2. |
| `tools/generate_visual_inspection_charts.py` | Visual inspection charts generator for HP007-CAMP-002 (Causal & Viewport-Invariant). |
| `tools/gex/gex_levels.py` | gex_levels.py — Genera el archivo de niveles GEX que lee el indicador NT8. |
| `tools/gex1_run.py` | GEX-1 (manifiesto docs/research/GEX1_REGISTRO_Y_MANIFIESTO_20261006.md, OK de Nico 2026-10-06). Sólo información. |
| `tools/gex1_run_kaggle.py` | GEX-1 (manifiesto docs/research/GEX1_REGISTRO_Y_MANIFIESTO_20261006.md, OK de Nico 2026-10-06). Sólo información. |
| `tools/gex1b_run.py` | GEX-1b (docs/research/GEX1B_PREREGISTRO_20261005.md): extensión por potencia de GEX-1. Sólo información. |
| `tools/ghost_cov_scan.py` | (sin docstring) |
| `tools/ghost_holdout_cesta.py` | Enmienda 5 (antes de HOLDOUT-A4; hoy jul-sep es desarrollo): cesta 1 MES + 1 RTY + 1 YM, holdout (sesiones >= 2026-07-01). Una sola apertura. |
| `tools/ghost_holdout_cesta_es_nq.py` | Enmienda 6: cesta 1 ES + 1 NQ, sesiones completas del catálogo (2026-07-01 a 2026-09-25). Una sola apertura. |
| `tools/grid_support_pilot/support_pilot_kernel.py` | Piloto de SOPORTE de etiquetas para EXP-REV-GRID (sin modelo, sin indicador, sin entrenar). |
| `tools/grid_support_pilot/support_pilot_l2window.py` | Soporte de etiquetas (primer paso) sobre la ventana L2 de ES usando los trades del L1 local (E:/l2_parquet). |
| `tools/hft_reversion_cortes.py` | HFT-REV-EXP, enmienda 1: cortes por contexto de la reversión en el primer retorno (D = 20; R = 40 y 80). |
| `tools/hft_reversion_explore.py` | HFT-REV-EXP: ¿una zona HFTZonesNQPureV4 anticipa la reversión cuando el precio vuelve a ella? (exploratorio) |
| `tools/hftv4_retorno_stage1.py` | HFTV4-RETORNO etapa 1 (manifiesto docs/research/HFTV4_RETORNO_MANIFIESTO_20261006.md): zonas HFTZonesNQPureV4 + flecha + pseudo-zonas. |
| `tools/hftv4_retorno_stage2.py` | HFTV4-RETORNO análisis (manifiesto docs/research/HFTV4_RETORNO_MANIFIESTO_20261006.md). |
| `tools/holdout_canasta.py` | Holdout de la CANASTA de pistas de una familia que terminó PISTAS_VIVAS (decisión de Nico, 2026-10-26, auditoría del filtro: |
| `tools/holdout_exploratorio.py` | Mirada EXPLORATORIA al holdout de una campaña del embudo (decisión de Nico, 2026-10-26: «mirar igual, sabiendo el costo»). |
| `tools/ib_vwap_pmh_pml_nq_20260929.py` | Fixed NQ IB/VWAP and PMH/PML development backtest. |
| `tools/ib_vwap_pmh_pml_nq_raw_audit_20260929.py` | Independent trade execution check directly against raw Parquet ticks. |
| `tools/ingest_cycle001_lessons.py` | Build the CYCLE-001 genesis ledger for the durable Experimental Hippocampus. |
| `tools/ipc.py` | IPC: ¿las acumulaciones de picos consecutivos son imanes? Etapa A (información), ES y NQ, exploración. |
| `tools/ipc_macro.py` | IPC macro: la misma lógica sobre ES en velas de 500 ticks. Etapa A. |
| `tools/ipc_mnq_hybrid.py` | MNQ IPC hybrid v0.1: geometry only, append-only causal events. |
| `tools/ipc_nivel.py` | IPC-NIVEL (Nico, 28/09): el precio se dio vuelta ≥ 2 veces en el mismo nivel, con mucho recorrido entre vueltas. |
| `tools/ipc_nivel_hft.py` | IPC-NIVEL × HFT (MES) — pedido prioritario de Nico 28/09: discriminar los niveles de picos según la cercanía y |
| `tools/ipc_nivel_regreso.py` | IPC-NIVEL-REGRESO (MES) — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_IPC_NIVEL_REGRESO_VIRGEN_MES_20260928.md |
| `tools/ipc_nivel_run.py` | IPC-NIVEL-MES — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_IPC_NIVEL_MES_20260928.md |
| `tools/ipc_robust.py` | IPC-ROB: prueba de robustez del positivo de la etapa A 25t. Manifiesto: docs/research/MANIFIESTO_IPC_ROBUSTEZ_20260928.md. |
| `tools/ivc_largo.py` | IVC-L: información de horizonte largo con historia de años sobre proxies ETF (manifiesto |
| `tools/kaggle_areas/areas_main.py` | (sin docstring) |
| `tools/kaggle_areas/construir_kernel.py` | Kernel de AREAS-EXP-1 con el empaquetador genérico (tools/kaggle_grilla/construir_kernel.py). |
| `tools/kaggle_auth.py` | Autenticación de curl contra la API de Kaggle, para los dos formatos de credencial. |
| `tools/kaggle_cobertura_preholdout.py` | Cobertura REAL de los datos en Kaggle hasta la apertura del holdout (pedido de Nico, 2026-10-22). Corre DENTRO de un kernel. |
| `tools/kaggle_data.py` | Baja un archivo de un dataset propio de Kaggle con la credencial que el entorno ya inyecta para www.kaggle.com (reintenta ante 429). |
| `tools/kaggle_data_entrypoint.py` | Offline Kaggle dataset discovery; no secret handling or research approval. |
| `tools/kaggle_dataset.py` | Sube una carpeta como NUEVA VERSIÓN de un dataset PRIVADO existente de Kaggle, con la credencial que el entorno ya inyecta para www.kaggle.com. |
| `tools/kaggle_discovery_gpu.py` | Script para un kernel PRIVADO de Kaggle con GPU (T4). Sin internet; no lee datos de mercado, solo tensores ya construidos. |
| `tools/kaggle_discovery_parity_kernel.py` | (sin docstring) |
| `tools/kaggle_drive_bridge.py` | EdgeLab <-> Google Drive <-> Kaggle local bridge and chunked transfer tool (versión endurecida). |
| `tools/kaggle_grilla/almacen_zonas_main.py` | (sin docstring) |
| `tools/kaggle_grilla/construir_kernel.py` | Empaquetador GENÉRICO de kernels de Kaggle autocontenidos (reutilizable por cualquier corrida de grilla masiva). |
| `tools/kaggle_grilla/construir_kernel_experimento.py` | Kernel autocontenido para CUALQUIER experimento de grilla genérica (edgelab/research/grilla_generica.py). |
| `tools/kaggle_grilla/construir_kernel_u1_cruzado.py` | python tools/kaggle_grilla/construir_kernel_u1_cruzado.py tools/kaggle_grilla/kernel_u1_cruzado.py |
| `tools/kaggle_grilla/embudo_main.py` | (sin docstring) |
| `tools/kaggle_grilla/gap_rth_main.py` | (sin docstring) |
| `tools/kaggle_grilla/grilla_main.py` | (sin docstring) |
| `tools/kaggle_grilla/nul2_maxt_main.py` | (sin docstring) |
| `tools/kaggle_grilla/orb0100_atras_main.py` | (sin docstring) |
| `tools/kaggle_grilla/oro_0530_main.py` | (sin docstring) |
| `tools/kaggle_grilla/oro_0530_ruptura_main.py` | (sin docstring) |
| `tools/kaggle_grilla/prerange_hft_e0_main.py` | (sin docstring) |
| `tools/kaggle_grilla/prerange_zonas_e0_main.py` | (sin docstring) |
| `tools/kaggle_grilla/u1_cruzado_main.py` | (sin docstring) |
| `tools/kaggle_grilla/u1_oro_main.py` | (sin docstring) |
| `tools/kaggle_hippocampus_ingest.py` | Verified aggregate evidence -> existing durable Hipocampo. Never a trial/edge. |
| `tools/kaggle_kernel.py` | Lanza y consulta kernels PRIVADOS de Kaggle (con GPU opcional) por la API de www.kaggle.com, usando la credencial que el entorno inyecta |
| `tools/kaggle_launch.py` | Lanza un kernel de Kaggle SOLO si todos los datos que necesita existen hoy en Kaggle. Antes de gastar tiempo de kernel: |
| `tools/kaggle_publish_release.py` | Publica la release como dataset PRIVADO de Kaggle y verifica lo publicado. |
| `tools/kaggle_space_index.py` | Genera KAGGLE_SPACE_INDEX.md/json: el mapa del espacio de Kaggle (datasets por estado y kernels por familia). |
| `tools/kaggle_space_label.py` | Señaliza el espacio de datasets de Kaggle según config/kaggle_space_map_*.json. |
| `tools/kaggle_spec_v2.py` | Technical aggregate jobs only, NOT certified research data. |
| `tools/kernels_todos_los_activos.py` | ¿Corren los 6 kernels en TODOS los activos, o sólo en 6E? |
| `tools/l2_absorption_geometry_check.py` | Chequeo de construcción de SUG-ABS-BARRIER antes de gastar la partición reservada (2026-09-24). |
| `tools/l2_asof_features.py` | Causal, instrument-neutral MBP-10 observables; no forecast or price outcomes. |
| `tools/l2_atlas_absorption.py` | Atlas L2 — primer lote: absorción en GC 08-26 pre-holdout (docs/research/ATLAS_CAPA_DESCRIPTIVA_20260924.md). |
| `tools/l2_daily_intake.py` | Orquesta el intake de UNA sesion L2 nueva: CSV crudo ya presente en disco -> parquet |
| `tools/l2_detector_nulls.py` | Plan L2 0.6: ¿los detectores provisionales (iceberg, spoof, absorcion) superan a su nulo? TARGET-FREE. |
| `tools/l2_fast_book.py` | Reconstruccion rapida del libro L2 (MBP-10) por sesion con Numba: snapshots por segundo + celdas de trades. |
| `tools/l2_intake_sweep.py` | Barrido de intake L2: procesa todos los CSV nuevos de una carpeta y valida la continuidad. |
| `tools/l2_labels_utc.py` | Etiquetas de clima L2 NQ → versión UTC para research (Entrada 067, punto 2). |
| `tools/l2_pairing_preflight.py` | Instrument-neutral custody and exact ordered-tape preflight. Never outcomes. |
| `tools/l2_phase0_metrics.py` | Fase 0 L2 sobre sesiones PRE-HOLDOUT: QA por sesion, lista de dias defectuosos, tabla de costos y reloj. |
| `tools/l2_phase2_info.py` | L2 Fase 2 — informacion condicional del libro tras la latencia (GC 08-26, pre-holdout). |
| `tools/l2_public_pilot.py` | P0: exploratory BTC minute-flow proxies; no strategy or fill simulation. |
| `tools/literatura.py` | Búsqueda de literatura para EdgeLab con APIs oficiales y gratuitas (no Google Scholar: sus términos prohíben el |
| `tools/luximb_parity/build_luximb_fx_bundle.py` | Bundle del visor para FX de Dukascopy (JForex: timestamp UTC, bid, ask, last=mid): velas M1 y 25t + zonas LUX-IMB. |
| `tools/luximb_parity/build_luximb_nq_m1_bundle.py` | Bundle del visor: NQ (un contrato, sin merge ni back-adjust) en velas M1 + zonas LUX-IMB (OG + VI). |
| `tools/luximb_parity/build_luximb_spot_m1_bundle.py` | Bundle del visor con velas M1 de Dukascopy (spot/CFD, p. ej. USATECH ~ NQ) + zonas LUX-IMB (OG+VI). Target-free. |
| `tools/luximb_parity/comparar_zonas_futuro_vs_cfd.py` | ¿Las zonas LUX-IMB (OG/VI) del futuro y del CFD nacen en el mismo lugar y momento? Target-free (sólo geometría y tiempo). |
| `tools/luximb_parity/comportamiento_coincidentes.py` | ¿El precio del futuro se comporta distinto en las zonas LUX-IMB que también nacen en el índice (CFD) que en las que no? |
| `tools/luximb_parity/convertir_tick_history.py` | Convierte EdgeLab Tick History (<yyyyMMdd>.Last.utc.txt: 'yyyyMMdd HHmmss fffffff;last;bid;ask;volume', UTC) al formato |
| `tools/luximb_parity/describir_impulsos.py` | Descripcion target-free de los impulsos marcados (nada posterior a la marca). Uso: describir_impulsos.py <bundle> <impulsos.json>... |
| `tools/luximb_parity/gc_150t_full_experiment.py` | Experimento Completo GC 150t Escalonadas: |
| `tools/luximb_parity/gc_150t_grid_visual.py` | Exploración visual (Fase 1): grilla de 300 combinaciones de SL/TP/BE para escalonadas 150t en GC. |
| `tools/luximb_parity/luximb_dash_periodos.py` | Tablero del visor (simulacion visual) recalculado por contrato de NQ, mas la version realista de M11. |
| `tools/luximb_parity/luximb_escalonadas.py` | Picos escalonados (detector existente `tools/escalonadas_det.py`, familia «IPC estilo NQ», confirmacion por precio) |
| `tools/luximb_parity/luximb_holdout_regla_visor.py` | REGLA CONGELADA para el holdout (>= 2026-10-01): fade "fin de caja -> inicio de zona" de LUX-IMB en NQ. |
| `tools/luximb_parity/luximb_impulsos.py` | Impulsos amplios, rapidos y que atraviesan muchas zonas LUX-IMB (OG + VI) vivas. Target-free: solo geometria. |
| `tools/luximb_parity/luximb_m10.py` | M10 — transporte de H1 (M9-H_m), H2 (M5) y H3 (M8-A1 vida 200) a MYM, GC, 6E, 6B, 6J, MBT (descubrimiento). |
| `tools/luximb_parity/luximb_m10b.py` | M10b: H3 controlando por cobertura previa de las franjas (precio ya visitado). Ver enmienda M10b en el manifiesto M10. |
| `tools/luximb_parity/luximb_m11.py` | M11: grilla SL/TP/BE del fade "fin de caja -> inicio de zona", IS/OOS/ES. |
| `tools/luximb_parity/luximb_m4_penetracion.py` | M4: penetracion de vuelta dentro del impulso. Reglas en |
| `tools/luximb_parity/luximb_m5.py` | M5: vuelta al inicio cargado. Reglas: docs/research/luximb_parity_20261020/PREREGISTRO_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md |
| `tools/luximb_parity/luximb_m6.py` | M6: ruptura de escalonadas 150t sobre area cargada. Reglas: |
| `tools/luximb_parity/luximb_m7_es.py` | M7: "un area cargada de OG/VI frena el precio" — escalonadas en ES, descubrimiento. |
| `tools/luximb_parity/luximb_m7b.py` | M7b: control por volatilidad previa de M7-H2. Reglas: docs/research/luximb_parity_20261020/MANIFIESTO_M7B_CONTROL_VOLATILIDAD_ES_20261020.md |
| `tools/luximb_parity/luximb_m8_analisis.py` | M8 — Parte A (desbalance por vida, ajustado por contexto) y Parte B (GBM franjas vs GBM contexto). |
| `tools/luximb_parity/luximb_m8_features.py` | M8 — variables de franjas (adelante / interior / atras) por vida de zona + contexto + desenlaces, por impulso. |
| `tools/luximb_parity/luximb_m9.py` | M9: distancia y tiempo de la vuelta + zonas tomadas / restantes -> ¿llega a A antes que a X? |
| `tools/luximb_parity/luximb_outcomes.py` | Desenlaces M1/M2/M3 de los impulsos LUX-IMB segun |
| `tools/luximb_parity/luximb_recalculo_canonico_release.py` | Recálculo del candidato LUX-IMB (regla del visor, congelada el 2026-10-21) sobre el release canónico de Kaggle con costos canónicos. |
| `tools/luximb_parity/parity_luximb.py` | Paridad NT8 -> Python del ImbalanceDetectorLuxAlgoMTF (OG/VI sobre velas M1), en tres capas. |
| `tools/luximb_parity/vi_coincidentes_reaccion_rep.py` | Prueba pre-registrada (`docs/research/luximb_parity_20261020/PREREGISTRO_VI_COINCIDENTES_REACCION_20261022.md`): ¿los VI del |
| `tools/m1_speed_check.py` | Compara `edgelab_data.load_m1` (rápida) con `_load_m1_slow` (original): tiempo y igualdad exacta. Uso: EDGELAB_DATA_ROOTS=/data/fakeroot python tools/m1_speed_check.py GC 2026-04-01 2026-06-30 |
| `tools/make_agent_readme.py` | Escribe README_AGENTES.md de la release con tablas calculadas a partir de las partes por activo. |
| `tools/make_discovery_family_specs.py` | Genera las especificaciones por familia (config/discovery/families/*.json) y los grupos de activos. Cada familia = una hipótesis económica. |
| `tools/make_release_report.py` | Genera docs/infra/LIQUID_RELEASE_20261014.md y ISSUE_RESOLUTION_LOG_20261014.json desde los metadatos de la release. |
| `tools/manifiesto_datos.py` | Identidad de los parquets de `data/` — hashes versionados, contenido afuera. |
| `tools/manifiesto_oraculos.py` | Manifiesto de identidad de `oracles/` — hashes versionados, contenido afuera. |
| `tools/mapa_info_costo_analisis.py` | IVC: mapa de información contra costo (manifiesto docs/research/MANIFIESTO_MAPA_INFO_COSTO_20260926.md §5-6). |
| `tools/mapa_info_costo_kaggle.py` | IVC: grilla de 5 minutos con estados causales y retornos futuros del medio, por sesión (manifiesto |
| `tools/mcpt_mgc_ema.py` | Full-pipeline intraday permutation test for the MGC EMA headline. |
| `tools/medir_spread_main.py` | Kernel de Kaggle: spread MEDIDO de un futuro del release con el criterio del atlas v4 (para instrumentos sin spread en costos). |
| `tools/metaanalisis_embudo.py` | Meta-análisis entre instrumentos de UNA regla congelada a partir de los estados del embudo (2026-10-26). |
| `tools/mgc_direction_diagnostic.py` | MGC EMA headline: long/short split, random-direction nulls, concentration, D0/D1/D2. Pre-registered in |
| `tools/mgc_direction_maxnull.py` | Enmienda 1 del pre-registro: nulo de máximo sobre 21 celdas normales con dirección sorteada por sesión. |
| `tools/mgc_family_t1.py` | PREREGISTRO_FAMILIA_20261004 T1: media de las 21 celdas normales bajo dirección sorteada por sesión. |
| `tools/mgc_family_t2.py` | PREREGISTRO_FAMILIA_20261004 T2: información direccional por horizonte, sin SL/TP, nulo por sesión. |
| `tools/migrate_canonical_ticks.py` | (sin docstring) |
| `tools/migrate_edgelab_to_kaggle.py` | (sin docstring) |
| `tools/mirror_l2_attempts.py` | Frozen causal A/B attempts, not a retrospective completed-mirror detector. |
| `tools/mirror_landmark.py` | Freeze a causal A/B candidate; expose progress landmarks without outcomes. |
| `tools/missing_exports_report.py` | Lista de exports NT8 que faltan para completar o mejorar la release (por activo, contrato y rango de fechas). |
| `tools/mm_qi.py` | MM-QI: provisión pasiva de liquidez filtrada por QI (manifiesto docs/research/MANIFIESTO_MM_QI_L2_20260924.md, |
| `tools/mnq_escalonadas_grid.py` | MNQ-ESCALONADAS-ESCALAS — docs/research/MANIFIESTO_MNQ_ESCALONADAS_ESCALAS_20260930.md (+ enmienda 1). |
| `tools/mnq_l2_prepare.py` | One-command LOCAL export. Target-free only; no return/fill/SL/TP engine. |
| `tools/mnq_l2_prepare_v2.py` | V2 DIAGNOSTIC CANDIDATE: observed publication boundary + peak-time snapshots. |
| `tools/noticias_calendario.py` | Construye `config/noticias/calendario_usd_tier1.csv` desde las transcripciones de `config/noticias/crudo/`. |
| `tools/noticias_impacto_operaciones.py` | Cuenta (target-free) cuántas operaciones/eventos ya publicados cruzan una ventana de noticia (`edgelab.noticias`). |
| `tools/nq_cruce25_clima.py` | NQ-CRUCE25-CLIMA — pre-registro docs/research/MANIFIESTO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md (v2, tras Entrada 067). |
| `tools/nq_l2_explore.py` | Exploración L2 de NQ (manifiesto docs/research/MANIFIESTO_NQ_L2_EXPLORACION_20260924.md, OK de Nico 2026-09-24). |
| `tools/nq_l2_synergy.py` | Absorción como amplificador de contexto, NQ L2 (manifiesto docs/research/MANIFIESTO_NQ_L2_SINERGIA_ABSORCION_20260924.md, |
| `tools/nt8_limpiar_csproj.py` | Saca del proyecto de NinjaTrader los artefactos de build que compila como fuente. |
| `tools/nt8_reexport_merge.py` | Fusiona la re-exportación NT8 del 2026-10-04/05 (AddOn EdgeLab Tick History) con el parquet canónico previo de |
| `tools/orb0100/gc_nocturno.py` | GC nocturno en abr-jun 2026 (preregistro PREREGISTRO_GC_NOCTURNO_20261021.md). Uso: gc_nocturno.py <out.json> <bundle>... |
| `tools/orb0100/orb0100.py` | ORB0100: rango 01:00-01:15 NY, ruptura por cierre de vela de 5 min. Grilla del manifiesto |
| `tools/orb0100/orb0100_replica.py` | Replicacion NQ abr-sep 2026 de la celda congelada (preregistro REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md). |
| `tools/orb0100/orb0100_v2.py` | ORB0100 V2: variantes alrededor de 1,5R/rango/mercado/VWAP en 8 activos (descubrimiento). |
| `tools/orb0100/orb_franjas.py` | ORB0100 NQ + franjas OG/VI. Reglas: docs/research/orb0100_20261021/MANIFIESTO_ORB0100_FRANJAS_OGVI_20261021.md |
| `tools/orb0100/orb_horarios.py` | ORB-HORARIOS: barrido de 44 ventanas x 2 reglas x 8 activos + embudo de confirmacion. |
| `tools/ou1_study.py` | OU-1 — diagnóstico de reversión (Ornstein-Uhlenbeck) por activo × escala, y chequeo de mecanismo en las celdas de GC. |
| `tools/ou2_mid.py` | OU-2 — ¿la reversión de ZB a 5-15 min sobrevive con el precio medio bid/ask? (descarta el rebote bid-ask). SOLO información. |
| `tools/paridad_avolzonepoi2.py` | Paridad aVolZonePOI2 NT8 <-> Python: bloques (score, nivel, franja), zonas y clasificación orderblock. |
| `tools/paridad_avolzonesimple.py` | Paridad NT8 ↔ Python de AVolZoneSimple, capa 1: el algoritmo. |
| `tools/paridad_hftimpulse.py` | Paridad NT8 ↔ Python de HFTImpulseZones_P. |
| `tools/paridad_hftzones_nq.py` | Paridad del motor de zonas HFT: NT8 (`.cs`) contra el espejo Python. |
| `tools/paridad_hftzones_nq_v2.py` | Comparador y arnés de paridad HFTZones NQ V2. |
| `tools/paridad_oraculo.py` | Driver de paridad kernel Python <-> oraculo NT8, para un indicador y un contrato. |
| `tools/paridad_proveedor_lucid_nt8.py` | Paridad de proveedor Lucid (research-v2) ↔ NinjaTrader (solape jul-2025 → jun-2026), sesión por sesión. Target-free. |
| `tools/paridad_volticksdef.py` | (sin docstring) |
| `tools/patch_emacorridortrendvol_anchors.py` | (sin docstring) |
| `tools/patch_hft_v2_oracle_termination.py` | Agrega y puebla la columna termination_reason en hft_zones_v2 de forma causal y determinista. |
| `tools/peaks_learn.py` | Detector de «picos consecutivos» (acumulaciones de liquidez) aprendido de las etiquetas de Nico. Versión 0. |
| `tools/peaks_learn_v1.py` | Detector de «picos consecutivos» v1: candidatos amplios + rasgos por zona + clasificador validado entre sesiones. |
| `tools/peaks_rule.py` | Detector de «picos consecutivos» v2 — regla de Nico: **cada pico no supera al anterior**. |
| `tools/pivotes_barrido.py` | PIVOTES-BARRIDO-MES — OK de Nico 28/09. Manifiesto: docs/research/MANIFIESTO_PIVOTES_BARRIDO_MES_20260928.md |
| `tools/pred004_analyze.py` | pred004_analyze.py — el instrumento que mide PRED-004 COMO FUE ESCRITA. |
| `tools/propfirm_ev_report.py` | Reporte de prop firms: para cada cuenta del catálogo, (1) el EV del participante sin ventaja (control de Hall), |
| `tools/propfirm_match.py` | La cuenta que mejor le calza a una estrategia (camino inverso del universo): dado instrumento, σ de la operación (ticks) y z bruto por operación (esperanza bruta / σ), |
| `tools/propfirm_refresh.py` | Refresca las reglas públicas de Lucid con el crawler existente (`edgelab.propfirm.crawl`) y avisa si cambió alguna página respecto de la línea base. |
| `tools/propfirm_reglas_cruce.py` | Cruce de las reglas detalladas por firma (incluidas las «escondidas»: topes por número de retiro, colchón, días |
| `tools/propfirm_thresholds.py` | Umbrales por cuenta, independientes del instrumento: σ de la operación (USD, ya con el tamaño) × costo/σ → z bruto mínimo y ρ requerido (ρ = z/0,8). |
| `tools/query_remote_kaggle.py` | (sin docstring) |
| `tools/r2_recorrido_vs_friccion.py` | R2: recorrido bruto disponible vs friccion de viaje redondo. Manifiesto: docs/research/R2_RECORRIDO_VS_FRICCION_MANIFIESTO_20261014.md |
| `tools/r3_direccion.py` | R3: direccion a 15-60 min (familias A: persistencia de retorno, B: presion de flujo agresor). Manifiesto APROBADO y congelado: |
| `tools/rank_hft_corridor_configs.py` | Evaluate target-free visual ranking of HFT corridor configurations. |
| `tools/razon_de_varianzas.py` | RAZÓN DE VARIANZAS (Lo–MacKinlay 1988) — ¿hay algo que ganarle a la tabla nula? |
| `tools/rebuild_hft_bundles_scaled.py` | Regenera los bundles 25t + HFT de los activos no-NQ con el perfil escalado (SCALED_FUNNEL_V1). |
| `tools/reconstruct_avzvol_candidate_bar_map.py` | Timestamp-only structural QA of candidate AVZVOL bar identity, NOT research. |
| `tools/reconstruir_kernels.py` | Reconstruye TODOS los kernels commiteados con los módulos actuales (error O6 de |
| `tools/recortar_spot_holdout.py` | Recorta un dataset SPOT de Dukascopy en la frontera del holdout (HOLDOUT-A4) y deja la carpeta lista para subirla como |
| `tools/rectify_kaggle_manifest.py` | Rectify the Kaggle manifest from records plus captured remote inventory. |
| `tools/recut_holdout.py` | Re-corte fisico del holdout sobre los parquets que lo contienen (P-18). |
| `tools/refresh_decisions.py` | Recalcula las decisiones por sesión de una release YA escrita (p. ej. tras corregir el calendario derivado) SIN reescribir |
| `tools/regimen_escala_m1.py` | Etapa 0 en escala mayor (decisión de Nico, 2026-10-06): ¿persiste la tendencia (eficiencia) o la dirección en barras |
| `tools/regimen_etapa0.py` | Etapa 0 de VTD-DIR: validación target-free del detector de régimen (edgelab/regimes/state.py). |
| `tools/regimes_6e_stage1.py` | Familia 6E-REGIMES, etapa 1 target-free (protocolo: docs/research/FAMILIA_6E_REGIMENES_LIQUIDEZ_20260924.md). |
| `tools/registrar_campanias_20261020.py` | Registro retroactivo en el contador GLOBAL de las campanias con desenlaces corridas entre 2026-10-20 y 2026-10-22 |
| `tools/registrar_resultado_h2_65s.py` | Registra los resultados de la corrida de 65 sesiones de H2 + Escalon 5 en documentacion y git. |
| `tools/registro_global.py` | Contador GLOBAL de pruebas del proyecto (revisión 2026-10-04): consolida los registros por familia en un único |
| `tools/release_io.py` | Lector mínimo y seguro de la release `liquid_tick_v1` para scripts de research del repo de investigación. |
| `tools/replay_p2_es_0626.py` | P2 Parity Replay for ES 06-26 aVolClusterPOI v0.5. |
| `tools/reportes.py` | Índice de los reportes del repo — generado del disco, nunca escrito a mano. |
| `tools/research_ema_reversion_nq.py` | tools/research_ema_reversion_nq.py |
| `tools/research_hft_absorption_probe.py` | tools/research_hft_absorption_probe.py |
| `tools/research_ops/__init__.py` | Bounded operational prototype; not a research authority or ccbus replacement. |
| `tools/research_ops/admission.py` | Conservative metadata-only memory admission. Not a lease or job launcher. |
| `tools/research_ops/audits/audit_liquid_release.py` | Bounded independent liquid-release audit. Real inputs execute only in Kaggle. |
| `tools/research_ops/benchmark.py` | Fixed synthetic prior-bar range benchmark, not market replay or engine parity. |
| `tools/research_ops/checkpoints.py` | Durable, tamper-evident checkpoint ledger for frozen longevity work-plan units. |
| `tools/research_ops/cli.py` | CLI: explicit synthetic proposals, finite daemon, read-only observation. |
| `tools/research_ops/context_benchmark.py` | Bounded synthetic benchmark using the production NumPy/Pandas expressions. |
| `tools/research_ops/context_memo.py` | Bounded sequential memo for trusted, immutable causal context readers. |
| `tools/research_ops/design.py` | Structured proposal intake only; completeness never grants research authority. |
| `tools/research_ops/dispatch.py` | Durable read-only research budget ledger. Binds one reviewed plan + one frozen reviewer |
| `tools/research_ops/knowledge.py` | Bounded recall bridge: canonical EdgeBrain replay + canonical SSRN context packs. |
| `tools/research_ops/observer.py` | Read-only adapter for existing campaign state. No job control or raw data access. |
| `tools/research_ops/preflight.py` | Metadata-only canonical gate bridge. Never authorizes execution or coerces exploratory sources. |
| `tools/research_ops/research_cycle.py` | Knowledge-first finite research planning. No model, network, shell or market execution. |
| `tools/research_ops/snapshots.py` | Portable synthetic queue snapshots. No provider, remote storage or auto-resume. |
| `tools/research_ops/store.py` | Transactional finite queue with operational audit events. Never opens market data. |
| `tools/research_ops/work_plan.py` | Frozen longevity work-unit inventory. Metadata planning only, not execution. |
| `tools/research_ops/worker.py` | Fixed synthetic action only. Resource limits are NOT an untrusted-code sandbox. |
| `tools/resolve_nt8_bar_boundaries.py` | resolve_nt8_bar_boundaries.py — Resolutor de Frontera de Barras NT8 contra Stream de Ticks. |
| `tools/resolve_ssrn_semantic_debt.py` | (sin docstring) |
| `tools/resolver_desde_release.py` | Genera `docs/data_catalog/RESOLVER.json` desde el release líquido canónico (decisión de Nico, 2026-10-22). |
| `tools/review_avzvol_candidate_boundary_effect.py` | Opt-in sensitivity of ALREADY EXPOSED O5 to candidate post-boundary witnesses. |
| `tools/review_avzvol_control_comparability.py` | Outcome-blind covariate and support QA of exposed controls; not causal matching. |
| `tools/review_avzvol_entry_distance.py` | (sin docstring) |
| `tools/review_avzvol_entry_hypotheses.py` | Review ALREADY EXPOSED retest geometry to triage entry hypotheses, not trades. |
| `tools/review_avzvol_expiry_metadata.py` | Metadata-only comparison of pinned MNQ summaries to loaded official expiry table. |
| `tools/review_avzvol_exposed_direction.py` | Opt-in review of existing direction/continuation exports; no new market outcomes. |
| `tools/review_avzvol_exposed_o5.py` | AVZVOL exposed-export descriptive review, not a market/certification runner. |
| `tools/review_avzvol_indicator_screen.py` | Reproduce a descriptive screen of already-exposed export labels. |
| `tools/review_avzvol_o5_robustness.py` | Descriptive robustness of exposed O5, not new endpoints or certified research. |
| `tools/run_batch_gc_jun26.py` | Batch converter para todas las sesiones de GC JUN26 excepto la sellada 20260618.csv. |
| `tools/run_campaign.py` | run_campaign.py — runner de campañas de fuerza bruta (F6.4). |
| `tools/run_edge_factory_census.py` | (sin docstring) |
| `tools/run_funnel_arrays.py` | CPU exploratory outcome runner with a supplied frozen split (+ optional EF0 custody and E4 multiplicity). |
| `tools/run_mgc_ema_screen.py` | (sin docstring) |
| `tools/run_mgc_nonema_funnel.py` | Target-free D0/D1 funnel for three fixed non-EMA MGC families. D2 stays sealed. |
| `tools/run_mgc_tick_exact_finalists.py` | (sin docstring) |
| `tools/run_mgc_tick_exact_grid.py` | Tick-exact validation of the immutable 42-cell MGC EMA core registry. |
| `tools/run_nt8_bridge.py` | CLI del bridge NT8 -> EdgeLab: kernels + paridad + visor multi-run. |
| `tools/run_overnight_master.py` | Master Overnight Orchestrator for EdgeLab (2026-08-26). |
| `tools/run_synthetic_smoke_census.py` | Reproducible runner for synthetic geometric bands software smoke census. |
| `tools/run_visual_configurations.py` | Causal configuration runner and density field evaluation script for HP007-CAMP-002. |
| `tools/sandbox/kaggle_streaming_parity.py` | Paridad streaming vs batch del acumulador de integridad. |
| `tools/sandbox/l3_power.py` | Potencia de la carrera simetrica L3, con la aritmetica exacta del spec. |
| `tools/sandbox/l3_touch_rule_bias.py` | L3 audit: cuando la regla de toque rompe el nulo de la carrera simetrica. |
| `tools/sandbox_pqread.py` | Lector minimo de parquet para ambientes sin pyarrow/duckdb (sandbox de auditoria). |
| `tools/select_canonical_visual_sessions.py` | Target-free reproducible session selection script for HP007-CAMP-002. |
| `tools/simulador_challenges_propfirm.py` | Simulador y Optimizador Monte Carlo de Challenges de Cuentas Fondeadas (`tools/simulador_challenges_propfirm.py`, 2026-10-29). |
| `tools/ssrn_brain_cli.py` | (sin docstring) |
| `tools/ssrn_corpus_bootstrap.py` | Materialize the in-repo CerebroSSRN corpus (Edge Brain bibliographic hippocampus). |
| `tools/store_audit.py` | store_audit.py — gate P3 sobre el store del bridge (F6.3). |
| `tools/strategy_viability.py` | Viabilidad de reglas operables según el MANDATO (P&L neto, estabilidad, challenge, control sin ventaja). Lee el STUDY_RESULTS.json de un estudio `strategy_pnl`. |
| `tools/streaming_escalonadas.py` | Causal completed-bar emission of the existing price-confirmed geometry. |
| `tools/study_slot_effect.py` | Estudio paramétrico de efectos por franja horaria (CT) con nulo de signos y Holm. La configuración llega por STUDY_CFG (JSON) y debe figurar TEXTUALMENTE en el pre-registro |
| `tools/summarize_mgc_tick_stability.py` | (sin docstring) |
| `tools/sweep_bigtrap2_tickframes.py` | Barrido de Tickframes para BigTrap2 (10t, 25t, 50t, 100t, 200t) sobre Oro (GC). |
| `tools/tabla_decision_pnk.py` | TABLA DE DECISIÓN P/N/K — para elegir la geometría ANTES de mirar zonas. |
| `tools/tbz_e2.py` | TBZ-E2: la expansión como área de patinaje. Diseño y enmiendas: docs/research/TBZ_E2_PARAMETRIZACION_HOLISTICA_20260924.md |
| `tools/tbz_stage1.py` | Familia TBZ, etapa E1 target-free (protocolo: docs/research/FAMILIA_TBZ_FRANJAS_BAJA_PERMANENCIA_20260924.md). |
| `tools/tbzx_espejo.py` | TBZX: impulsos de poco volumen por tick; qué hace el precio AFUERA de la franja y cómo REINGRESA. |
| `tools/tbzx_iter2.py` | TBZX iteración 2 (manifiesto §8): lo que puede engañar y lo que da robustez. |
| `tools/tbzx_r3_brain.py` | TBZX-R3 en el cerebro: partición, lecciones de método y una observación por corrida (con auditoría de controles). |
| `tools/tbzx_r3_macro.py` | TBZX-R3 iteración 4: escenarios macro contra la fricción (manifiesto §10, fijado antes de medir). |
| `tools/tbzx_reingreso_kaggle.py` | TBZX-R3: se crea la zona -> se aleja D -> vuelve -> se introduce p -> retrocede r -> entrada; TP y SL en {3, 6, 10, 20}. |
| `tools/test_corredores_vacio.py` | tools/test_corredores_vacio.py |
| `tools/test_cortes_sesion_gc0226.py` | Prueba: el kernel Python, corta las sesiones igual que el .cs? |
| `tools/test_js_match.py` | (sin docstring) |
| `tools/tickbar_diag.py` | TICKBAR-001 B2b — comparador que CLASIFICA la causa del mismatch en tick bars. |
| `tools/tickbar_diag_v2.py` | TICKBAR-001 classifier v2: separates bar cuts from event attribution. |
| `tools/toxic_es_estabilidad.py` | TOXIC-ES-1 (docs/research/PREREG_TOXIC_ES_ESTABILIDAD_20260929.md) y CLIMA-NQ-EST-1 |
| `tools/trace_avzvol_postexpiry_identities.py` | Trace bounded post-expiry source identities; never decode prices or outcomes. |
| `tools/trend_micro.py` | TREND-MICRO: rupturas con filtro de microestructura. Manifiesto con iteración 1: |
| `tools/u1/u1_regimen_rango.py` | U1-CRUZADO: régimen de rango como explicación del nulo 2023-25 (PREREGISTRO_REGIMEN_RANGO_U1.md). Sólo datos ya en el repo. |
| `tools/u1_densidad_analisis.py` | Análisis B de PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md: ¿las señales U1 por sesión siguen al mercado (rango) o al feed (ticks)? |
| `tools/u1_oos_fix27_eval.py` | Evaluación A de PREREGISTRO_OOS_FIX27_Y_DENSIDAD_U1.md: OOS de U1-CRUZADO en USATECH 2023-01 → 2025-07 con el fix 27. |
| `tools/u1b_seguimiento.py` | Seguimiento secuencial de U1-B (acta: docs/research/areas_expansion_20261022/u1/ACTA_SEGUIMIENTO_U1B.md). |
| `tools/ulp_exposure.py` | AUDIT-002 — exposición MEDIDA a la familia de bugs de 1 ULP. |
| `tools/ulp_exposure_expr.py` | Exposicion MEDIDA de las expresiones de precio de los .cs que `ulp_exposure.py` no cubre (triaje 2026-10-14, ulp_sweep). |
| `tools/ulp_sweep.py` | Barrido ESTÁTICO de la regla de diseño: ningún umbral de precio en `double`. |
| `tools/universe_design.py` | Cruza el mapa de volatilidad (UNIVERSE_SIGMA.json) con los umbrales de las cuentas (THRESHOLDS.json): para cada celda instrumento × franja × horizonte elige el tamaño |
| `tools/universe_sigma.py` | Mapa descriptivo de volatilidad por instrumento × franja horaria (CT) × horizonte, para diseñar el universo de corridas (no prueba ninguna hipótesis; no mira retornos futuros condicionados a nada). |
| `tools/validate_hft_v2_certification.py` | Fail-closed preflight for an HFTZones V2 shared-input SQLite export. |
| `tools/validate_hft_v2_export_readiness.py` | Static guardrails for the audited HFT V2 exporter source. |
| `tools/validate_l2_session_boundaries.py` | Valida la continuidad entre sesiones L2 consecutivas de un mismo instrumento+contrato. |
| `tools/validate_mgc_ema.py` | (sin docstring) |
| `tools/validate_nq0626_parity_run.py` | validate_nq0626_parity_run.py — validación post-corrida de paridad aVolClusterPOI NQ 06-26 |
| `tools/variante_tau_actas.py` | Variante τ de las reglas con acta (2026-10-31): mismas entradas congeladas, salida por tiempo de parada, sobre el DESC de cada regla. |
| `tools/vendor/__init__.py` | (sin docstring) |
| `tools/vendor/notion_phenomena.py` | Bounded target-free clock-window measurements, not a phenomenon classifier. |
| `tools/verificar_artefactos.py` | Revisión read-only de procedencia: cada artefacto citado en |
| `tools/verificar_citas_entrega.py` | Puerta fail-closed: toda ruta citada por un documento de entrega tiene que |
| `tools/verify_density_parity_real_bundle.py` | Paridad Python <-> JS del campo de densidad sobre bundles REALES del visor. |
| `tools/verify_discovery_cpu_gpu.py` | Paridad sintética del motor de descubrimiento: CPU sin bloqueo == CPU por bloques == GPU. No lee datos de mercado. |
| `tools/verify_funnel_cpu_gpu.py` | Synthetic CPU/CUDA parity. No market data, split or D2 files required. |
| `tools/verify_indices.py` | Verificador fail-closed de los indices sellados del bundle Kaggle. |
| `tools/verify_kaggle_download.py` | Verifica una release PUBLICADA en Kaggle: descarga cada archivo desde Kaggle (no desde la copia local) y compara tamaño y SHA-256 con el |
| `tools/verify_layer_parity.py` | Harness canónico de verificación de paridad por capa (Puerta 0) para BigTrap2Absorption. |
| `tools/verify_lux_imb_vs_6e_oracle.py` | Validacion PARCIAL de LUX-IMB (OG + VI) en Python contra las zonas que NT8 exporto para 6E Continuo. |
| `tools/verify_mgc_stateful_kernel.py` | (sin docstring) |
| `tools/verify_parity_by_session.py` | Paridad `.cs` <-> kernel Python con clave **relativa a la sesion**. |
| `tools/verify_parity_gc0226.py` | Harness forense de paridad BigTrap2Absorption <-> export NT8 sobre calendario irregular. |
| `tools/verify_release.py` | Verifica una release ya escrita, de forma independiente del escritor. |
| `tools/verify_tree.py` | tools/verify_tree.py@v1 |
| `tools/vio1_zones.py` | VIO-1 — zonas VIOLETA (lógica de aVolClusterPOI v0.5) aplicadas a las zonas de aVolZonePOI2 (paridad NT8 verificada, config 25T) en MGC 25 ticks. |
| `tools/vrev.py` | VREV: reversión al VWAP desde un alejamiento X·ATR, con confirmaciones. E1 con economía incluida. |
| `tools/vrev2.py` | VREV-A (reversión al VWAP tras agotamiento) y VCONT (continuación tras el primer alejamiento). E1. |
| `tools/vrnd_replicate.py` | Réplica pre-registrada de V-RND (absorción en número redondo → ruptura) en otros instrumentos. |
| `tools/vtd_bracket_stage1.py` | VTD-BRACKET etapa 1 (manifiesto docs/research/VTD_BRACKET_MANIFIESTO_20261006.md): simulacion tick a tick del bracket bilateral. |
| `tools/vtd_bracket_stage2.py` | VTD-BRACKET análisis (manifiesto docs/research/VTD_BRACKET_MANIFIESTO_20261006.md). |
| `tools/vtd_dir_stage1.py` | VTD-DIR etapa 1 (propuesta docs/research/VTD_DIR_PROPUESTA_20261006.md + enmienda 1): features de direccion en barras 150t. |
| `tools/vtd_dir_stage2.py` | VTD-DIR etapa 1, análisis (propuesta docs/research/VTD_DIR_PROPUESTA_20261006.md + enmienda 1). |
| `tools/vtd_stage1.py` | VTD-VOL-1 etapa 1 (manifiesto docs/research/VTD_VOL1_MANIFIESTO_20261006.md): VolTicksDef 150t/50t + AVCL base 50t. |
| `tools/vtd_vela_test.py` | VTD-VELA — prueba única pre-registrada (docs/research/VTD_VELA_PREREGISTRO_20261006.md, commit 074b8461). |
| `tools/vtd_vol1.py` | AVCL-VOL-2 A+B — etapa 2 (manifiesto docs/research/AVCL_VOL2_AB_MANIFIESTO_20261006.md). |
