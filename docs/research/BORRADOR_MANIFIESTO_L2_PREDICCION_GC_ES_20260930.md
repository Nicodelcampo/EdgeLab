# Borrador — L2 incremental en GC C2 / ES PLANAS / espejo

**DRAFT_NOT_APPROVED_NOT_EXECUTABLE.** Continuar la preparación no autoriza abrir futuros de señal. No usar la captura May31 ni febrero calibrado como confirmación; son descubrimiento/QA expuesto. GC C2 y ES PLANAS permanecen congelados; no sweep de detector, porcentaje o features. Climas ES STOP y Junio15 ABSTAIN no se rescatan.

## Propuesta primaria (no ejecutada)
Pregunta: en el primer cruce prospectivo del50% del recorrido B→A, ¿el libro agrega predicción de llegada aA antes de invalidarB, respecto de la información de precio disponible? Registrar TODOS los intentos desde A/B causal, no condicionar a espejos completados. Excluir del cohort prospectivo los que ya estaban al50% en primera observación y los que ya alcanzaronA, sin borrar receipts. Horizonte original del detector, no extender por resultado.

Propuesta de endpoint: primer toque trade aA antes de superarB y antes de horizonte. Definir dirección simétrica; nuevoB invalida, timeout no llegada; huecos/truncamiento requieren censura explícita. La comparación usa primer trade posterior al tiempo/fila de decisión; nada del mismo timestamp decide retrospectivamente. Política de empates/prints iguales/huecos debe cerrarse en manifiesto final con ejemplos sintéticos antes de run.

Baseline propuesto: geometría conocida (distancia A/B, duración primer impulso), hora, movimiento/recorrido/prints/volumen de10s y spread. Modelo aumentado añade sólo QI_touch y OFI_endpoint10s/profundidad_touch orientados; no duplicar microprice ni transportar HMM NQ. Logistic regularizada sencilla, escalado y ajuste sólo en training; todos los números de regularización, semilla y features finales se sellan antes de labels. No copiar split aleatorio por evento de la literatura.

Evaluación cronológica por sesiones completas, embargo/purga de horizontes solapados y clusters de sesión; sin eventos de la misma sesión a ambos lados. Métrica primaria propuesta: mejora de Brier OOS respecto baseline, misma población observable; calibración/coverage secundarias. No elegir umbral de entrada por evaluación. Separar instrumentos, no sumar eventos como iid. Densidad bruta≥4 no reemplaza #sesiones ni MDE: calcular planificación de potencia sin outcomes, conservar SIN_POTENCIA si falta muestra.

## Escalonadas: endpoint pendiente de aprobación
GC C2 y ES PLANAS: registrar en primera confirmación causal y separar publicación real de trig teórico. Propuesta a decidir: carrera +1R contra stop2ticks más allá del último pico conocido, entrada ejecutable después de publicación, horizonte fijado antes de resultados. No se ejecuta porque precio de entrada/fill, objetivo y horizonte todavía no están aprobados. No usar una métrica favorable del espejo para afirmar ventaja en zonas.

## Antes de aprobar
1. Sesiones y archivos nuevos listados con hashes, clocks, procedencia, permisos temporales y custodia; no tocar holdout sin autorización documentada de su enmienda.
2. Reglas completas de decisión/endpoint/censura y simulación de costos por instrumento (comisión propia, bid/ask, latencia, slippage); sin rellenar precios inobservables.
3. Split y N mínimo de sesiones de evaluación, MDE, única primaria/familia de contrastes y corrección de multiplicidad si zonas e instrumentos se prueban conjuntamente.
4. Firma/OK de Nico sobre ese manifiesto completo. Hasta entonces únicamente preflight/QA y simulaciones de ingeniería sin outcomes reales.
