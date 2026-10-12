# Segundo intento: capacidad del runner, no auditoría de datasets

V1 terminó con ERROR/exit 1, después de 25 sesiones de formación y 2899645 captures privadas hasta 2026-06-15. Watchdog no reportó límite de RSS/tiempo; peak child RSS observado 910565376 bytes. El target no se completó y no hay receipt de censo exitoso. Los aggregates de v1 y su code/bundle pins permanecen intactos.

La hipótesis principal es el límite de 3000000 captures, pero v1 no exportaba la categoría exacta de excepción. No presentar esa hipótesis como causa confirmada. V2 añade un failure receipt con **categorías constantes** y su SHA sellado por bootstrap; jamás expone mensajes de excepción, traceback, ticks, precios, zone IDs o privados.

`MNQ_CONFLUENCE_MARKET_PILOT_RETRY_PLAN.json` conserva fuente, versión, target, rango de formación, las 96 configuraciones completas y cuatro racimos. Sólo amplía presupuesto de captures a 12M y SQLite a 4 GiB; AS/RSS/CPU/wall y límites de ticks siguen como antes. El plan v1 no se sobrescribe. No se reduce warmup, se reinicia por chunks, cambia selección por outcomes o reabre holdout.

V2 incorpora la selección de candidatos de racimo equivalente sweep/Fenwick, comparada con la función literal; el detector/rule de formación y desempates permanecen iguales. `arrival.py` lazy/first_passage y la propuesta de respuestas son trabajo para la fase siguiente: el piloto actual sigue sin arrivals/labels, P&L, modelos predictivos, nulls de ocupación ni inferencia.

La reejecución es un nuevo intento de ingeniería sobre el mismo scope. No es nueva QA de fuentes, nuevo censo científico confirmado ni multiplicación de evidencia independiente. La captura/estado del intento fallido viven en tmp de Kaggle y no se pueden restaurar con el runner actual; no inventar resume ni transportar privados fuera de Kaggle.

Interpretación: target_capture_counts cuenta disponibilidad en el día target, no una certificación de origen físico dentro de esa sesión. GeometryReplay excluye carry del brazo primario usando el origen consumido. Intersecciones cerradas pueden incluir contactos de borde half-tick sin nivel de print entero: los counts geométricos no garantizan un toque posible u observado. Esas oportunidades deben separarse al conectar la fase de llegadas y controles; no reinterpretar las counts como éxitos de mercado.
