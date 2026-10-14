# Ampliación pedida: BigTrap × AVOLZONEPOI2

Estado: selección paramétrica preparada y componentes sintéticos iniciales probados. **No lanzada, no protocolo de runtime completo.** La corrida anterior AVZ/racimo138437923/v1 está COMPLETE y se conserva como baseline; no sustituye esta ampliación ni descarta su hipótesis.

## Cobertura principal

9 configuraciones preexistentes seleccionadas por parámetros, no por respuestas ni densidad ganadora, con builder reproducible `build_crossfamily_roster.py` y roster `MNQ_CROSS_FAMILY_PARAMETER_ROSTER.json`:

- AVZP2:3 perfiles — denso tick25/ventana5/percentil70/Suma; referencia tick25/ventana10/95/Suma; otra escala tick200/ventana10/80/Densidad.
- BT2:3 perfiles — denso tick25/ratio1.5/volumenmínimo1/sinwick; referencia tick25/ratio3/volumen30/wick; otra escala tick200/ratio2/volumen15/wick.
- BT2A:3 perfiles — denso Tape25/pct50/AbsMagnitude; referencia Tape25/pct90/AbsMagnitude; otra escala Tape50/pct70/AbsDirectional. Otros parámetros y calibración nativos completos figuran en el roster, no se acortan.

18 cruces principales:9 AVZ×BT2 y9 AVZ×BT2A. AVZ×racimo y BT2×BT2A no son prioridades, porque son familias más emparentadas/derivadas. Racimos pueden quedar como contexto auxiliar posterior, no evidencia independiente ni reemplazo del cruce entre familias diferentes.

## Escenarios y poblaciones a integrar antes del envío

Separar zonas recientes por edad observada (0–20s,20–120s,120–600s); horizonte primario de exposición10min, declarado como medición, **no poda del indicador ni reset de historia/calibración**. Liveness/removals nativos BigTrap permanecen disponibles; AVZ no se presenta como si tuviera la misma invalidación. Disclose filtros y censos.

Medir disjuntas/contacto de borde/solapamiento parcial/contención/idénticas; orden de formación/edad/revisión/orientación del BigTrap; llegada desde arriba/abajo/interior; flujo, presión, eficiencia y velocidad previos; primer print observado posterior al nacimiento y revisitas; GAP_THROUGH sin inventar toque; fin de exposición/invalidation nativa/censura. Creación o reconocimiento de confluencia NO cuenta automáticamente como llegada física.

La comparación general conserva población de reloj común y oportunidades sin contacto. Escenarios son features/celdas descriptivas exclusivas cuando corresponda, no miles de tests IID ni selección del subconjunto ganador. El modelado necesita incluir interacciones **flujo continuo × geometría/edad/llegada** preespecificadas con capacidad igualada; el piloto anterior sólo agregó variables, no resolvió todas esas interacciones. Control de densidad/ocupación, zonas ficticias de geometría/exposición igualadas y réplica disjunta siguen siendo requisitos antes de atribución específica/confirmación. Congelar rango/split y thresholds antes de nuevas respuestas; ningún holdout ni P&L.

## Optimización y rigurosidad

-9detectores persistentes, no ejecutar18veces cada detector por cada cruce;2bar specs compartidos y2TapeWindowTicks. Features por config/anchor reutilizadas en todos sus cruces; labels comunes calculados una vez.
- No all-zone-pairs/triples global: índice de intervalos por configuración, combinar uniones locales/cercanías/relaciones pertinentes y censar soporte/exposición.
- Nuevo `ObservedPrintIndex`: construcción única de índices por nivel de precio y queries `[left,right)` sobre prefix causal en banda half-tick cerrada. Cuenta prints reales, primer/último observado; salto de1a10 NO toca banda4–6. Oráculo100tapes×100queries exacto. Caller todavía debe integrar clocks/cobertura, excluir print de creación y distinguir primer toque observado en ventana vs lifetime; el helper NO certifica eso solo. No se midió speedup Kaggle de este helper.
- BT2A sigue siendo el costo histórico dominante de grids amplios. Estudiar reutilización exacta del preprocesamiento de buckets por ventana/footprint, y percentiles deslizantes exactos; no compartir estado de thresholds/activos entre configuraciones que difieren. Paridad fast/native sintética obligatoria antes de reemplazar subpasos. La paridad NT8 aproximada aceptada no es cifra100% medida.
- No repetir QA de datasets resueltos. Un profiling de etapas/censos de soporte **dentro del mismo intento** no es otra campaña de validación. Presupuestos finitos y fail-no-truncation; no partial scientific success tras overflow.

## Pendiente real, no listo para lanzar

Integrar índice genérico multi-config y remociones/age expiry de exposición; consultas de print-clock y escenario/flow interactions; nulls/capacity/support; plan inmutable de lectura/split/costo; paquete aislado/negativos; nuevo journal single-attempt ligado al último terminal. No reutilizar journals zonev1 o modelo v3/v4, ni relanzar138437923/v1. No otro daemon, deploy, merge, Brainwriter ni aprobación autónoma.
