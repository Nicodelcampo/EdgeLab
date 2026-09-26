# Enmienda pre-outcome — decongestión de primeros toques

Estado: CONGELADA ANTES DE EJECUTAR EL CENSO DE PRIMEROS TOQUES.

## Problema

La separación de 120 minutos estaba implementada sobre creaciones de zonas,
pero EXPLORE-001 define la entrada primaria en el primer toque posterior. La
restricción representa capacidad de exposición, por lo que debe operar sobre el
instante de entrada y no sobre el instante en que nació una zona todavía no
operable.

## Contrato

- ancla: `first_touch_ms`;
- separación: 120 minutos;
- alcance: por fecha de sesión `America/Chicago`;
- algoritmo: greedy cronológico, conservando el primer evento elegible;
- frontera de sesión: reinicia la separación; una sesión no suprime otra;
- empate de timestamp: zona con `created_ms` más antiguo; luego `zone_id`;
- outcomes: prohibidos.

## Justificación del desempate

BigTrap2 registra toques al cierre de barra, por lo que varias zonas pueden
compartir timestamp. Elegir por side sería una preferencia direccional. FIFO
prioriza la zona que llevaba más tiempo expuesta sin consultar retornos; el
`zone_id` sólo resuelve un empate residual de creación.

## Efecto de autoridad

Las tasas de creaciones siguen siendo diagnósticas. H1–H3 sólo pueden congelarse
con tasas producidas por esta población y esta política, después de pasar los
gates de integridad y cobertura.
