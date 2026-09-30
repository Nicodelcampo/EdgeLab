# L2 as-of GC y preparación de espejo — resultado de QA

**PASS mecánico / PREDICTIBILIDAD NO MEDIDA.** No modifica el detector GC,
C0–C4, MNQ, climas, visor ni datos. No abre outcomes, entrenamiento o P&L.

## Trabajo realizado

`tools/l2_asof_features.py` mide presión y soporte observables independientemente
del detector de zonas: spread, profundidad, desequilibrio de colas a 1/3/10
niveles, mid ponderado por colas y OFI entre endpoints publicados. Orienta
las features a la dirección del evento sin convertirlas en señales.

Publica el snapshot del grupo anterior sólo al llegar la primera fila REAL
de timestamp posterior. La fila nueva no forma parte del snapshot. No publica
EOF como si hubiera una fila posterior. Libro inválido reinicia historia.
OFI de 10 segundos incompletos es null; el prefijo observado se conserva aparte.
Precio objetivo fuera del top-10 es UNKNOWN, no cantidad cero ni cancelación.
Edad y soporte se conservan; el límite de edad operativo está por ratificar.

`tools/mirror_l2_attempts.py` registra geometrías A/B congeladas y conserva
TODOS los intentos, incluso pendientes, invalidados y tardíos. Un regreso ya
avanzado en la primera observación no se retrotrae a un cruce prospectivo.
El adapter admite sólo IMP_CONFIRMED con ledger raw explícito. No genera A/B
por sí mismo ni selecciona espejos completos. Elegibilidad geométrica y
observabilidad L2 son distintas; ninguna implica autorización de trade.

## Evidencia mecánica

- 39 tests sintéticos PASS: fórmulas, reflexión de precio/lados, publicación,
  futuro prohibido, invalidación, ventanas, prefijos y población de intentos.
- Replay de los dos ejemplos GC privados ya expuestos: 6.281.338 filas raw.
- 1.619 paquetes de QA contrastados independientemente con fronteras de filas
  raw, fórmulas de colas/mid, normalización, edad y visibilidad del precio fijo.
- 97 paquetes de prefijos reales coinciden exactamente con el replay completo.
- Conteos de gates concilian en ambos archivos. Último grupo queda no publicado.
- Cero eventos reales de zonas o espejos unidos, cero labels futuros, cero
  modelos predictivos, cero tests económicos.

La muestra de QA es sistemática cada 500 publicaciones válidas; NO son 1.619
trades ni casos independientes para potencia. Los agregados recorren todas
las filas. El precio fijo de QA procede del primer bid válido, no de una zona
IPC o A de un espejo. No demuestra defensa, absorción ni identidad de órdenes.

Los archivos 20260531/20260615 son ejemplos GC legacy de mayo/junio, NO febrero
25t, NO MNQ, NO confirmación independiente. Reloj absoluto no certificado:
se usa orden raw/tiempo relativo, sin asignar horas CME o sesiones completas.
Fuente MBP-10; source_row es orden de captura, no prioridad de cola del exchange.
L1 se utiliza como frontera raw, no se infiere agresor por sus códigos.

## Investigación y consecuencia para el diseño

Gould y Bonart documentan información de queue imbalance para el siguiente
cambio del mid en acciones, con heterogeneidad por tamaño relativo del tick.
Esto motiva la hipótesis, no demuestra llegada a A de un impulso en GC/MNQ.
Fuente: https://arxiv.org/html/1512.03492v1

Cont, Kukanov y Stoikov relacionan OFI con cambios contemporáneos de precio:
no se puede presentar esa relación como predicción del futuro regreso a A.
Aquí OFI es sólo la fórmula de touch entre endpoints publicados, no el flujo
completo intragrupo. Fuente: https://arxiv.org/html/1011.6402v3

Identidad comprobada: mid ponderado menos mid = spread × QI_touch / 2.
No contar ambos como dos evidencias independientes; no es un microprice calibrado.

El kernel existente `viewer/nt8_bridge/espejo_impulsos.js` en HEAD inicial
emite IMP_CONFIRMED en confirmación; puede desplazar progreso anterior a
`max(k,jc)`. Los registros terminales `impulses` incorporan estado_final,
bar_final y S2/S2v2 posteriores. No usarlos para seleccionar población o como
features del registro. La integración real requiere el ledger del instante
en que A/B se conocen, no bar_B retrospectivo.

## Procedencia y reproducibilidad

Plan: `PLAN_GC_L2_PRECALIBRACION_Y_ESPEJO_20260930.md`.
Evidencia: `artifacts/l2_event_research_20260930/evidence.json`.
Incluye hashes exactos de inputs/código, runtime, gates, prefijos y checks.
Ejecución en staging aislado a partir de HEAD
`767e30bcc5b54d35b6f19013d09f192520cafafc`; NO afirmación de ejecución de un
commit limpio posterior. PyArrow 25.0.0 instalado en dependencia aislada.

La primera implementación exponía la suma de OFI del prefijo como ventana.
Se corrigió target-free a null antes de completar 10 s y se repitió el replay
v2 en carpeta nueva; no se abrieron outcomes para decidir el cambio.
El profiler empaquetado devolvió ParserError para parquet; Arrow/pandas leen
correctamente. Se mantuvo validación completa de manifest/schema/nulos/grid/
orden; no se reparó o sustituyó raw. Paquetes privados y precios no se publican.

## Lo pendiente, sin bloquear calibración humana

1. Aprobar y congelar geometría GC, sin elegir perfiles por retorno.
2. Publicación raw/reloj GC febrero y callback del loader nativo. El smoke
   legacy NO se aplica directamente a parquet MNQ sin su adaptación validada.
3. Ledger A/B de TODOS los intentos; censo causal de soporte y densidad por sesión.
4. Ratificar instrumento, landmark, invalidación, plazo, edad, splits,
   mínimo útil/potencia y OK en el borrador de protocolo.
5. Sólo entonces contrastar baseline de precio con el MISMO baseline + L2
   fuera de muestra. Costs/fills constituyen una fase posterior.

No se amplían automáticamente las 52 sesiones MNQ. No se rescatan climas STOP.
Holdout octubre+ intacto. ABSTAIN de publicación GC no queda resuelto por el smoke.

## Aporte al referente

El núcleo de medición y el control de causalidad ya no dependen de calibrar
picos. Su utilidad predictiva sigue abierta y se probará contra un baseline
de precio, no contra el reconocimiento retrospectivo de espejos completos.