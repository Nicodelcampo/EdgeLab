# Supervisor: seguimiento durable de intentos remotos

Nuevo módulo `tools/research_ops/remote_watch.py`: journal SQLite finito en directorio privado, separado de la cola sintética y de memoria científica. Registra identidad inmutable account/kernel/version/source/bundle/plan; versiones diferentes son intentos diferentes.

El host registra una **reserva durable antes de llamar al proveedor**. Una consulta fallida o un proceso perdido consume presupuesto: no hay refund, reintento oculto ni sobrescritura de una reserva pendiente. `UNAVAILABLE` cierra la reserva explícitamente sin convertir ausencia en éxito. Terminal COMPLETE/ERROR/CANCELLED bloquea nuevas reservas de ese intento. COMPLETE significa únicamente estado observado de API, nunca censo, custodia, paridad o edge.

El host verifica metadata y source contra paquete antes de asociar respuesta a la versión. El módulo recibe sólo enums y hashes; no URLs firmadas, texto arbitrario, ticks, resultados científicos o credenciales. La cadena se reproduce y valida bajo transacción; expected_tip rechaza vistas locales obsoletas. Registro idéntico es noop; cambio de pins para misma versión es conflicto. Tabla ajena/symlink rechazados.

## Ejecución real finita en este hito

V2 138386707 se registró localmente; una consulta de status tuvo reserva previa y luego quedó RUNNING, con metadata/source exacto contrastados. `CONFLUENCE_REMOTE_WATCH_SNAPSHOT.json` guarda estado operativo agregado. La SQLite local vive fuera del repo y **no contiene datos de mercado**.

Las consultas anteriores a este módulo no quedaron mágicamente presupuestadas. Los límites sólo rigen llamadas hechas por este circuito cooperativo; no todas las herramientas de la sesión. No hay daemon ni scheduler/network adapter conectado: el host actual realiza MCP manualmente. No existe fencing entre hosts, witness remoto latest, autenticación del custodian, restore portable de este journal o autorreanudación. Hashes locales no protegen contra rollback del administrador.

## Límite de aprendizaje

Se preservan fallos/aprendizajes técnicos en documentos revisables. El writer canónico existente exige custodia/revisión/destino/anchors aprobados. Muestreo RSS del piloto no cumple su medición estricta; no lo proyectamos como peak medido, no falsificamos firma ni forzamos entrega al Brain. Próximo hito: conectar adquisición terminal acotada/allowlist y revisión semántica al journal, preservando esta separación.

14 pruebas negativas/positivas nuevas: restart, terminal, presupuesto persistente, pendiente tras crash, unavailable, política congelada, tip obsoleto, identidad conflictiva, versiones independientes, regresión de status, payload libre, corrupción y archivos ajenos/symlink.
