# EdgeReplica: port y requisitos de activos

## Fuente y alcance

Fuente efectiva: EdgeReplica.txt adjuntado por el usuario, conservado como EdgeReplica.cs en el paquete descargable EdgeReplica_EdgeLab_port.zip. SHA-256 de los 12335 bytes: 3afb40ff37523be65476bc0dc6c15fd7826aaff1dc5f895f8f6e3041a6f76a5c. No se cargó ninguna DLL ni se usó licencia externa.

60 reglas fijadas en config/edge_replica/rules_v1.json: 20 COND=-1, 17 COND=0, 23 COND=+1. No se retunearon horarios, dirección, hold o condiciones. Root autorizado: MNQ exclusivamente. MNQ tick=0.25, valor=USD 0.50/tick/contrato; NQ es otro activo y otro multiplicador. Transferencia a otros activos requiere nuevo pre-registro y costes.

strategies/edge_replica.py es un port de **estado lógico / shadow**, NO un motor broker validado ni un reporte de PnL. Conserva pasos de la CS: fills presumidos de órdenes previas, exits por HOLD, envío de pendientes, nuevas señales. Las señales se generan en b1, se envían en b2 y se espejan fills en b3. HOLD empieza en el timestamp de envío, no en una supuesta señal inicial. Horas Chicago/DST, weekday civil original, DataFloor 2024-01-01 y filtro por última barra <= now-15 minutos de reloj (no 15 filas; máximo 4999 barras previas). COND=0 no requiere referencia, delta cero no satisface filtros direccionales.

**No confundir:** los eventos ASSUMED_ENTRY_FILL/ASSUMED_EXIT_FILL se registran al procesar b3, pero NO acreditan un fill observado a su hora de cierre. El supuesto del original es open de esa barra. Para precisión temporal/bid-ask hace falta tick trace y export de órdenes/ejecuciones NT8. No se agregaron SL/TP inexistentes ni un motor de scalp ajeno para fingir equivalencia.

## Problemas detectados en la propia CS

- No usa OnExecutionUpdate/OnOrderUpdate para confirmar aceptación/fills parciales/rechazos. Su diccionario lógico no prueba la posición broker.
- Entradas contrarias borran todos los lotes lógicos opuestos. La semántica real de órdenes gestionadas y netting debe contrastarse con NT8, no asumirse desde ese diccionario.
- SessionMargin=0 verifica remaining>=HOLD en b1, pero el envío se retrasa una barra. Puede alcanzar/sobrepasar el cierre; eso debe quedar como caso de discrepancia. No se cambió silenciosamente a otra estrategia con margen aumentado.
- Gaps, fines de sesión o fronteras pueden dejar órdenes pendientes; se preserva unresolved en vez de producir PnL de operaciones censuradas.
- Se rechaza mezclar contrato/regime; separar fronteras y documentar posiciones/pendientes censuradas. No afirmar continuidad de indicadores/posiciones ni inventar precio de salida.
- Las afirmaciones 577/577 DEC26 y 337/337 SEP26 son comentarios del autor, NO evidencia verificada aquí. Períodos SEP/DEC utilizados en reconstrucción/paridad no se pueden presentar como holdout independiente sin historial de exposición.

## Correcciones/barreras para la nueva ruta MNQ

edgelab/data/asset_safety.py aporta:
1. safe_group_ids y stream_safe_preholdout: elección de grupos enteros con timestamp stats estrictamente antes del cutoff, ANTES de leer ticks. Grupos mixtos/desconocidos quedan sellados y reportados; pérdida de cobertura NO significa sesión completa.
2. audited_volume_rows: no rellena huecos con cero ni marca complete_session=True sin evidencia; rechaza volumen NaN/infinito/negativo y duplicados de identidad.
3. validate_mnq_tick_batch: schema entero, timestamps/secuencia ordenados, sin duplicar identidad, bid<=ask y separación MNQ/NQ/contratos. Múltiples ticks legítimos en un mismo timestamp se preservan. No redondea/elimina/repara silenciosamente precios. UTC/DST, semántica LAST/volumen y calendario todavía deben adjudicarse por separado.

run_verified_shadow conecta el gate del PR65 y validate_contract_regime ANTES de llamar al reader; valida que cada barra recibida coincida con contrato, fecha CME y régimen autorizados. Un reader arbitrario aún puede ser inseguro: usar el lector protegido y hashes/cutoffs fijados, no pq.read_table y filtro posterior.

Estas barreras corrigen la NUEVA ruta de entrada y bloquean datos no probados. No rewired todos los builders históricos ni modifican el dataset. No se afirma que se haya reparado el contenido físico ni que exista una lista certificada de contratos líquidos.

## Verificación ejecutada

27 pruebas sintéticas + py_compile PASS en sandbox. Casos: snapshot de 60 reglas contra bytes CS, latencia b1/b2/b3, HOLD desde envío, referencia temporal con gaps, COND sin referencia/zero, weekday/DST, margen de sesión, reversals lógicos, censura final, timestamps ingenuos, micro/standard/roll, grupos sellados, quotes cruzadas, ticks legítimos coincidentes, duplicados reales, secuencia entre batches, ausencia/volumen cero/infinito/completitud.

Los fixtures ejecutables y fuente original están en EdgeReplica_EdgeLab_port.zip entregado al usuario. El hash del port de sandbox difiere del archivo del repo sólo por comentarios/docstrings condensados para publicación; lógica idéntica, pero verificar snapshot del repo por separado antes de considerarlo un gate de CI. No se compiló NinjaScript ni se ejecutó suite completa o dataset real.

## Estado y pasos obligatorios restantes

**PORTED_LOGICAL_SHADOW / MARKET_EVALUATION_BLOCKED**. Holdout no abierto, ningún resultado de trading producido.

- Sigue bloqueado el montaje del canónico en Kaggle (PR65): ningún hash/cobertura/liquidez nuevo verificado.
- Emitir certificado y volumen/spread por contrato/sesión; selección de D sólo con D-1 completo y límites por root congelados antes de rentabilidad. Tener más volumen relativo no basta para tamaño/capacidad.
- Entregar/exportar órdenes, ejecuciones y barras de NT8 con timezone/trading-hours/contract y períodos usados para reconstruir las reglas. Paridad independiente antes de promoción.
- Implementar/validar ejecución de mercados time-exit y netting en motor compartido; bid/ask/costes/slippage reales. No sustituirla por run_ledger con TP/SL ni por estadísticas del shadow.
- Pre-registro, universo de 60 reglas + prueba agregada con interacción de posiciones, multiplicidad completa y antecedentes desconocidos explícitos. Ablations horario/COND/dirección/hold predefinidas; ningún retune silencioso.
- D0/D1, sensibilidad a costes/feeds y validadores independientes (SPA/DSR/BH según diseño), negativos append-only; D2/holdout sólo cuando autorizado y no contaminado.
