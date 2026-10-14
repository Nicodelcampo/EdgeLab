# GC: diagnóstico de soporte de absorción A — terminado

## Resultado y decisión

En las seis sesiones originales de training (3, 4, 5, 6, 7 y 10 de agosto de 2026), sobre **707.465 ticks**, se observaron **76.284 anclas**: **44.374 elegibles** y **31.910 UNKNOWN**, que no se convierten en NEITHER. Solo **2** cumplen la conjunción A de cinco condiciones: A_ONLY=2, BOTH=0, E_ONLY=2.656, NEITHER=41.716. Ambas A están en OTHER:-1, una el 3 y otra el 5 de agosto. Anclas solapadas no son eventos independientes; OTHER/RTH conserva el reloj común previo, no certifica una sesión específica de GC.

| Requisito considerado | Cumplen el requisito individual | Cumplen los otros cuatro, sin exigir este |
| --- | ---: | ---: |
| Presión actual alta | 11.291 | 170 |
| Presión previa alta | 11.418 | 9 |
| Avance absoluto pequeño | 7.821 | 3 |
| Rango pequeño | 9.093 | 2 |
| Recorrido pequeño | 8.959 | 39 |

Las columnas no son aditivas ni etapas de un funnel. Se recontaron las 32 máscaras conjuntas, no se cambió ningún filtro. Al exigir presión actual a los 170 que cumplen los otros cuatro, quedan 2. Es el mayor cuello de botella condicional en cada una de las seis sesiones y cada una de las cuatro celdas agregadas fase/dirección. El criterio menos frecuente individualmente es avance pequeño: su frecuencia marginal no identifica el cuello de botella conjunto.

Omitir un solo requisito deja como máximo 170 anclas: sigue por debajo de las 2.000 requeridas por el plan científico anterior. **No es ausencia física de absorción, evidencia de edge ni autorización para quitar filtros.** El resultado primario A/E anterior continúa inconcluso por falta de soporte; sus recibos y negativos quedan intactos.

## Ejecución reproducible

- Kaggle privado CPU: kernel **138584908**, versión **1**, `edgelab-gc-a-support-diagnostic-v1`, COMPLETE en el primer poll. Una intención cerrada, un job, un poll; journals originales `gc-a-support-0201ee0951f6-{dispatch,watch}.sqlite`, sin reset/reenvío.
- Fuente `1e86c07d7985ea091f09d5ff8f111603e0885020`, bundle `b4eca447bb5a993626e7b623891394340c2ac8cd6390f10f1c5fda3bbbcab265`, plan `0201ee0951f602d1699e93d10b843d59cdf800072205b23b4266675767685cc9`.
- Recibo agregado inmutable: **68.611 bytes**, SHA256 `4886936d6dbff45cd77f7e0b029b19f04a8f0383793da4154adacedfa350170f`.
- Auditor independiente: **PASS_TARGET_FREE_TRAINING_CONJUNCT_RECOUNT_NOT_EDGE**. Recuento de condiciones/máscaras y cruces por fecha/celda; comparación exacta del censo previo tras normalizar ceros. No acceso host a ticks, outcomes o modelos privados; quantiles de training retenidos tal como los calculó el runner, no reestimados ni promediados entre sesiones.
- Runner **18,908 s**; boot total **23,960 s**, transporte **2,666 s**; RSS muestreado **184.668.160 bytes**, no certificado del pico real. No se reclama speedup frente a otra carga.
- Antes del envío: **959 Research Ops + 18 navegación + 11 focales PASS**. Después del cierre: **9 focales PASS**, incluyendo cuatro nuevas pruebas sobre serialización de ceros. Los 959 corresponden al snapshot prelaunch, no a una regresión completa de los archivos de cierre.
- Código/protocolo/plan/package en `GC_A_SUPPORT_*`; postproceso reproducible `tools/research_ops/audits/summarize_gc_a_support.py`. Desde raíz: `python tools/research_ops/audits/summarize_gc_a_support.py --raw docs/research/evidence/gc-a-support/raw --ops docs/research/ops --out /tmp/gc-a-support-analysis`.

## Aprendizajes y siguiente hito

1. La conjunción presión alta + poco avance/rango/recorrido es demasiado escasa con esta definición. No alcanza aumentar configuraciones sobre un proxy sin soporte.
2. Registrar una **nueva propuesta**, no modificar la calibración congelada: representar de forma continua presión versus progreso del precio y definir explícitamente trayectorias con estados intermedios. Verificar soporte sin outcomes antes de elegir evaluación nueva; no optimizar contra resultados de la evaluación anterior.
3. La primera comparación host dio una falsa alarma: el recibo anterior omite estados de conteo cero y el nuevo los incluye. Normalizar el universo declarado, con pruebas negativas; **no** tocar recibos ni repetir la corrida o auditar de nuevo el dataset por esa diferencia de serialización.
4. Reusar transporte/calibración resueltos y diagnósticos target-free baratos; no repetir QA de datos sin evidencia de cambio.
5. EdgeBrain: `GC_A_SUPPORT_KNOWLEDGE_PROPOSAL.json` es **PROPOSED_NOT_CANONICAL**. Ninguna escritura canónica automática, promoción, merge, despliegue Debian/daemon, holdout desde octubre ni P&L.

## Custodia y límites

El snapshot público terminal no sustituye los journals originales del servidor. La continuidad Debian debe seguir el handoff y las barreras de autoridad; no recrear SQLite desde JSON ni reenviar una intención ambigua. Este cierre declara solo esta campaña terminal, no verifica toda la cuenta Kaggle. Los enlaces firmados permanecen en el notebook privado y expiran; no se publican. Ticks, features, modelos y logs privados nunca salieron de Kaggle. No se lanzó una segunda investigación por este cierre.
