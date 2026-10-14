# GC: presión, avance y trayectorias intermedias — protocolo nuevo

## Pregunta y límites
¿La relación continua entre presión y avance tiene población observable suficiente para una investigación posterior, y dónde se concentran los recorridos de avance, confinamiento y retroceso? Este experimento es **descriptivo, target-free y sólo de entrenamiento**. No mide respuesta futura, edge, rentabilidad ni absorción física certificada. No rescata los negativos ni sustituye el proxy A/E anterior.

Se reutilizan exactamente GC_12-26, fuente v2 SHA `3a9686bf35f3311fff5e5736fedf63bb95bb009cd4a3a7ae8d668280c2fde734`, las seis sesiones originales de training del 3–10 de agosto y la calibración del 31 de julio SHA `539b4ba21975510eafeac107c48b415618ba502802283d8860218631b058573d`. No se lee evaluación, no se reestima calibración y no se repite QA del dataset. Identidad de transporte no certifica procedencia, calendario o liquidez; las limitaciones de fuente heredadas continúan visibles en el handoff de reparación local.

Plan congelado: `GC_PRESSURE_PROGRESS_PLAN.json`, digest `95a9012db0b498cb783600b7aed0dd956b6669fe5dece304ba4a9c98ad771d37`. La fuente y el plan deben estar guardados en GitHub antes del envío.

## Medidas y población
- Se conserva el motor existente: ventanas 5/20/60 s, anclas de 5 s sobre prints observados, gap máximo 10 s. El atlas usa el par de ventanas **20 s previos + 20 s actuales**, ambas terminadas a la ancla.
- Dirección: signo del volumen firmado de la ventana previa; misma observabilidad, cobertura de signo ≥80% y calibración por fase/dirección que el censo anterior. UNKNOWN queda separado, nunca NEITHER ni cero imputado.
- Presión actual y previa: volumen negociado del lado de esa dirección, dividido respectivamente por q80 actual/previo de la calibración congelada. Es una escala contextual, no profundidad del libro ni capacidad.
- Descriptores continuos: presión normalizada actual/previa, avance dirigido actual/previo en ticks de midpoint, avance absoluto, rango, recorrido, razón de presión y razón de cantidad de trades.
- Medias, cuantiles 10/25/50/75/90 y tres correlaciones Pearson **descriptivas**: presión/avance absoluto, presión/avance dirigido, razón de presión/avance dirigido. Las correlaciones constantes se reportan como indefinidas, no cero. Sin test de significación, inferencia, tuning o independencia.
- Desgloses: cada fecha y cada celda OTHER/RTH × dirección. El reloj RTH común heredado no certifica el calendario particular de GC. Pooled pondera anclas, no sustituye medias por sesión. Cuantiles globales se calculan de arrays originales en Kaggle, no promediando cuantiles por sesión.

## Dos vistas conjuntas exhaustivas, no selección de ganador
1. Presión normalizada actual × avance dirigido actual: presión `<0,5`, `[0,5,1)`, `[1,2)`, `≥2`; avance `<−4`, `[−4,−2)`, `[−2,2)`, `[2,4)`, `≥4` ticks. Son **20 celdas**, incluidos ceros.
2. Avance dirigido previo × actual: la misma partición de avance en ambas ventanas, **25 trayectorias** mutuamente excluyentes. Permite distinguir, por ejemplo, avance previo/avance actual, avance previo/pequeño neto actual y avance previo/retroceso actual. “Pequeño neto” puede incluir excursiones grandes: el rango y recorrido se conservan; no llamarlo confinamiento físico sin medirlos.

Límites inferiores inclusivos/superiores exclusivos (`searchsorted_right`); −2 entra al pequeño neto y +2 sale. No reetiquetar “pequeño” a posteriori para mejorar soporte. No son 45 modelos ni 45 ensayos de respuesta: sólo tablas descriptivas del mismo universo, no pruebas independientes.

## Solapamiento y soporte antes de evaluación
Además del censo completo, elegir por sesión la **primera ancla elegible**, luego la primera elegible al menos 40 s después de la última seleccionada. La selección es global por fecha, no por celda, dirección, intensidad o resultado. Sus dos ventanas no se solapan con el par previo; no garantiza episodios ni sesiones estadísticamente independientes. El contador se reinicia por fecha, no por fase.

Readiness descriptivo ex ante: ≥2.000 anclas elegibles, ≥200 ventanas sin solapamiento y ≥4 fechas con ≥30 de esas ventanas. Reportar las cuatro celdas de fase/dirección con ≥30 ventanas y todas las celdas sin soporte. Estos límites son administrativos para valorar cobertura, **no potencia estadística** ni autorización automática de evaluación. No se exige que cada uno de los 20/25 bins supere el umbral ni se elige un primario por su resultado posterior.

## Eficiencia y rigor
Una lectura de cada sesión, prefijos existentes, ningún detector de zonas, ningún modelo/label, matrices pequeñas y arrays privados acotados para cuantiles. No generar un grid de configuraciones del indicador mientras la representación no tenga soporte. Reutilizar el pin, transportador, calibración y guard de rowgroups prepayload existentes. Memoria AS 6 GiB/RSS 4 GiB; CPU/wall 600 s, parent 1.200 s, notebook 1.800 s; 8 M ticks total, 250 k anclas por sesión, agregado ≤512 KiB. No se promete aceleración frente a otra carga; registrar tiempo real.

Tests sintéticos: todos los bins y límites, no solapamiento por fecha, UNKNOWN, orden/finitud, plan y calibración inmutables, rechazo de holdout/outcomes, bloqueo de constructor de respuesta/fit, bundle aislado y controles de agregado. Auditor host: hash/custodia, matrices completas, márgenes comunes, suma por fecha/celda, readiness y **paridad del censo prelabel** contra el recibo anterior `4886936d6dbff45cd77f7e0b029b19f04a8f0383793da4154adacedfa350170f`. No reconstruye el tape en el host ni afirma validar todos los cuantiles independientemente.

## Entrega y siguiente decisión
Una nueva intención, un notebook privado CPU, máximo seis consultas reservadas antes de hacerlas. No reenvío ante envío ambiguo, ni reset de journals. Recuperar únicamente boot + agregado/failure, nunca ZIP/ticks/arrays/logs. Registrar implementación, resultados y negativos, propuesta de aprendizaje, límites y hito siguiente en repo. Sin Brain canónico, merge, P&L, holdout ni daemon/24×7.

Si hay población, el siguiente hito es **otro protocolo** que compare una representación continua fijada con baseline/capacidad igualada, sobre sesiones de desarrollo disjuntas cuya inspección previa sea declarada. No activar automáticamente ese hito. Si no hay, registrar el fallo de observabilidad o cobertura antes de ampliar configuraciones. Fases de reparación de dataset y aprobación causal no se sustituyen por este diagnóstico.
