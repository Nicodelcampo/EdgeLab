# Estado actualizado de la integración EdgeReplica

Sustituye solamente el conteo inicial 52 del informe EDGE_REPLICA_BRIDGE_INTEGRATION_20261004.md: ahora son 54 tests EdgeReplica PASS (32 existentes + 22 nuevos), más 16 tests independientes del gate PASS. Los módulos exigen identidad instrument/contract/source_file/source_row de cada tick y conservan primera/última identidad original en el reporte; no reindexan sequence. No es una prueba de deduplicación de raw ni de la identidad de cada barra completa.

El informe anterior describe las convenciones recuperadas del repo, calendario y causas por las que evidencia antigua no puede transferirse directamente al nuevo canónico. La nueva lectura por callback debe estar físicamente acotada por fuente/custodia/etapa ANTES de devolver ticks; filtrar después de pq.read_table no cumple ese contrato. El adaptador no implementa ni certifica por sí solo ese reader Parquet, ni feriados/cierres tempranos/expiry de MNQ.

Flujo disponible: gate existente -> make_shadow_reader -> barras cerradas sin ffill -> run_verified_shadow. Cada sesión es un segmento diagnóstico reseteado/censurado; no equivale todavía a una corrida continua de ejecución NT8. La prueba conectada usa gate y aprobaciones MOCK explícitamente sintéticos. first_quote_fill es un componente de referencia separado para órdenes horarias: no integra por sí solo netting, parciales, rechazos, comisiones, slippage, profundidad o edad de quotes. Sus presupuestos deben congelarse antes de medir resultados.

No hay nueva corrida de mercado, PnL, adjudicación de edge, ni apertura de holdout. No se cambió el dataset. Continúan pendientes la certificación sobre la versión actual de sesiones/roll D-1/liquidez y una ejecución económica completa independiente. Mantener PR en draft. No interpretar tests PASS como SANITIZED_VERIFIED, paridad nativa o promoción.

Reproducir: python3 -m unittest discover -s tests -p 'test_edge_replica*.py' -q
