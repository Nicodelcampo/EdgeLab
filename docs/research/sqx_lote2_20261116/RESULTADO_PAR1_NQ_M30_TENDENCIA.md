# SQX lote 2 — par 1 (Nasdaq M30 tendencia, plano 15:55 NY): INVÁLIDO, cola en pausa (2026-11-16)
Estado: RESULTADO (no evaluable). Real 13.997 generadas / 3 aceptadas; nulo 23.872 / 11 aceptadas (contadas en el registro global).
- Ninguna estrategia llega a 200 operaciones: las aceptadas tienen 52–75 operaciones en 2012–2016 y **0 en el OOS 2017–2019**; abren a las
  00:00 del servidor (17:00 NY) y casi nunca operan. El umbral del nulo queda indefinido (n ≥ 200 vacío): el par no mide nada.
- Diagnóstico provisorio: la plantilla TrendFollowing del Builder genera reglas de ruptura pensadas para marcos altos; en M30 con cierre al
  final del día casi no disparan, y los filtros de SQX rechazan casi todo (3 aceptadas de 14.000). No es un resultado sobre el Nasdaq.
- La cola se pausó (par 2 detenido a los 73 s, 796 generadas, contadas) y la revisión horaria se deshabilitó. Rediseño antes de seguir
  (propuesto a Nico): generación aleatoria sin plantilla, M15/M30, filtro de aceptación ≥ 200 operaciones en construcción, mismo nulo.
